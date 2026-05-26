"""
战斗 / 地图 随机事件引擎

设计思路:
  - 12 类事件分类,每类有固定 prompt 模板 + 触发权重
  - 根据当前 context(地图怪物 / 角色状态 / 友好度 / 最近战斗)动态计算权重
  - LLM 生成时,按所选 type 用专属模板,确保叙事一致且效果合理
  - effects 由 LLM 在 type 允许的范围内填,主动 clamp 防溢出

效果上等同于"无限事件"(LLM 即时填充内容),但分类约束避免重复 / 错乱。
"""

import random
from typing import Dict, List, Optional, Tuple

# ════════════════════════════════════════════════════════════
# 12 类事件元数据
# ════════════════════════════════════════════════════════════
EVENT_TYPES = {
    "item_drop": {
        "label": "拾遗", "icon": "🎁",
        "weight": 25,        # 基础权重
        "require_enemies": False,
        "good_chance": 0.85, # 多为好事
        "prompt_hint": "在山路边发现遗落的小物件",
    },
    "treasure": {
        "label": "机缘", "icon": "✨",
        "weight": 12,
        "require_enemies": False,
        "good_chance": 1.0,
        "prompt_hint": "灵药 / 秘境入口 / 古经的偶遇",
    },
    "reinforcement": {
        "label": "援军", "icon": "🐯",
        "weight": 8,
        "require_enemies": True,
        "good_chance": 0.1,  # 几乎坏事
        "prompt_hint": "现有怪物呼朋唤友,多了一只同族",
    },
    "boss_ambush": {
        "label": "强袭", "icon": "👹",
        "weight": 3,         # 罕见
        "require_enemies": True,
        "good_chance": 0.0,
        "prompt_hint": "怪物所属帮派的高阶 Boss 突然现身,极其凶险",
    },
    "wanderer": {
        "label": "邂逅", "icon": "🚶",
        "weight": 15,
        "require_enemies": False,
        "good_chance": 0.55,
        "prompt_hint": "路过散修,可能赠物 / 挑战 / 闲聊",
    },
    "stampede": {
        "label": "兽潮", "icon": "🌪️",
        "weight": 5,
        "require_enemies": False,
        "good_chance": 0.05,
        "prompt_hint": "野兽奔腾,扬起阵阵尘土,玩家可能被踩踏",
    },
    "ghost": {
        "label": "亡魂", "icon": "👻",
        "weight": 6,
        "require_enemies": False,
        "good_chance": 0.30,
        "prompt_hint": "曾被击败的怪物魂魄归来,可能寻仇也可能道谢",
    },
    "marketplace": {
        "label": "墟市", "icon": "🏪",
        "weight": 8,
        "require_enemies": False,
        "good_chance": 0.85,
        "prompt_hint": "山中野市,神秘商人摆摊售物",
    },
    "hermit": {
        "label": "高人", "icon": "👴",
        "weight": 4,         # 罕见
        "require_enemies": False,
        "good_chance": 0.95,
        "prompt_hint": "深山隐修长者传授感悟,可加属性点 / 修为",
    },
    "sect_messenger": {
        "label": "宗令", "icon": "📜",
        "weight": 7,
        "require_enemies": False,
        "good_chance": 0.65,
        "prompt_hint": "门派密使带来消息,影响友好度",
    },
    "weather": {
        "label": "天象", "icon": "⛈️",
        "weight": 6,
        "require_enemies": False,
        "good_chance": 0.45,
        "prompt_hint": "灵气潮汐 / 风雨突变,影响 qi 或 hp",
    },
    "trial": {
        "label": "心魔", "icon": "🌀",
        "weight": 4,
        "require_enemies": False,
        "good_chance": 0.20,  # 风险高奖励高
        "prompt_hint": "心魔试炼,消耗 hp/qi 换取大量 exp",
    },
}


def select_event_type(
    visible_enemies: List[dict],
    character: dict,
    recent_battles: List[dict],
) -> Tuple[str, dict]:
    """根据当前 context 加权选择 event type。

    动态加权规则:
    - 有怪物 → enable require_enemies 类
    - HP < 30% → 减少 boss_ambush / stampede / trial 权重(玩家虚弱时少坑爹)
    - 疲劳 > 70 → 增加 hermit / treasure 权重(给惊喜)
    - 缘分 FATE 高 → 增加 treasure / hermit / item_drop 权重
    - 友好度全负 → 增加 reinforcement / boss_ambush 权重(树敌多)
    - 最近 2 场都败北 → 减少 boss_ambush(怜悯)
    """
    has_enemies = len(visible_enemies) > 0
    hp = character.get("hp", 100)
    max_hp = character.get("max_hp", 100)
    hp_ratio = hp / max(1, max_hp)
    fatigue = character.get("fatigue", 0)
    max_fat = character.get("max_fatigue", 80)
    fate = character.get("attrs", {}).get("fate", 5)
    factions = character.get("factions", {})
    avg_fac = sum(factions.values()) / max(1, len(factions))
    recent_defeats = sum(1 for b in recent_battles[-2:] if b.get("result") == "defeat")

    candidates = []
    for etype, meta in EVENT_TYPES.items():
        if meta["require_enemies"] and not has_enemies:
            continue
        w = meta["weight"]

        # 玩家虚弱 — 减少凶险事件
        if hp_ratio < 0.3 and etype in ("boss_ambush", "stampede", "trial"):
            w = w * 0.3
        # 疲劳高 — 多惊喜
        if fatigue / max(1, max_fat) > 0.7 and etype in ("hermit", "treasure"):
            w = w * 2
        # 缘分高 — 多好事
        if fate > 7 and etype in ("treasure", "hermit", "item_drop"):
            w = w * (1 + (fate - 7) * 0.2)
        # 树敌多 — 多袭击
        if avg_fac < -20 and etype in ("reinforcement", "boss_ambush"):
            w = w * 1.8
        # 连败 — 怜悯
        if recent_defeats >= 2 and etype == "boss_ambush":
            w = w * 0.2

        candidates.append((etype, max(0.1, w), meta))

    total = sum(c[1] for c in candidates)
    r = random.random() * total
    cum = 0
    for etype, w, meta in candidates:
        cum += w
        if r <= cum:
            return etype, meta
    return candidates[-1][0], candidates[-1][2]


def build_event_prompt(
    event_type: str,
    character: dict,
    visible_enemies: List[dict],
    recent_battles: List[dict],
    enemy_ids: List[str],
    item_ids: List[str],
) -> str:
    """根据事件类型生成专属 LLM prompt"""
    meta = EVENT_TYPES.get(event_type, EVENT_TYPES["wanderer"])
    factions = character.get("factions", {})
    attrs = character.get("attrs", {})

    # 通用 context
    base = f"""你是《灵枢笔录》游戏的奇遇生成器。本次事件类型:【{meta['label']}】 {meta['icon']}
事件主题:{meta['prompt_hint']}

【玩家】{character.get('name','执笔者')}({character.get('sect_name','?')} · {character.get('realm_name','炼气')} · Lv.{character.get('level',1)})
HP {character.get('hp',0)}/{character.get('max_hp',100)} · 灵气 {character.get('qi',0)}/{character.get('max_qi',600)} · 疲劳 {character.get('fatigue',0)}/{character.get('max_fatigue',80)}
8 属性:{attrs}
友好度:{factions}

【当前地图】{len(visible_enemies)} 只怪物可见
怪物列表:{[(e.get('name'), e.get('clan'), e.get('level')) for e in visible_enemies[:6]]}
最近战斗:{recent_battles[-2:] if recent_battles else '无'}

【可用资源 — LLM 只能从下列 ID 中选取,绝不允许凭空造】
怪物 ID:{enemy_ids[:25]}
物品 ID:{item_ids[:25]}
门派 ID:{list(factions.keys())}
"""

    # 事件类型专属约束
    type_rules = {
        "item_drop":     "效果:drop_item_id 必须填(从 item_ids 选);hp/qi 可有微小奖励(±3)。不要触发战斗。",
        "treasure":      "效果:hp/qi 至少 1 项 ≥ +15。fate 高的可加 drop_item_id。不触发战斗。",
        "reinforcement": "效果:spawn_enemy_id 必填(从 enemy_ids 选,优先与现有怪物同 clan)。force_battle 可选 true。",
        "boss_ambush":   "效果:spawn_enemy_id 必填且优先 boss_ 开头的(若没有就选最高级 enemy)。force_battle: true。hp_delta 0(战斗本身扣血)。这是大事件,叙事 150 字。",
        "wanderer":      "效果:50% 概率赠 drop_item_id(低稀有度),50% 概率触发战斗。faction_delta 可 ±1~3。",
        "stampede":      "效果:hp_delta -10 ~ -20(被踩),qi_delta +0 ~ +20(灵气波动)。不触发战斗。",
        "ghost":         "效果:exp_delta +3 ~ +10 仅代表外传章命题强度,不直接加修为。fate 高可 drop_item_id。10% 触发战斗。",
        "marketplace":   "效果:drop_item_id 必填(中稀有度物品,模拟「低价购入」)。hp/qi 无变化。",
        "hermit":        "效果:exp_delta +10 ~ +25 仅代表外传章命题强度,qi_delta +30 ~ +80,fatigue_delta +0 ~ +3。叙事中暗示「悟出一线天道」。",
        "sect_messenger":"效果:faction_delta 必填(对玩家自己派 +3 ~ +5),其他派可 ±1。exp_delta +5 仅代表外传章命题强度。",
        "weather":       "效果:qi_delta -50 ~ +50(灵气潮汐),fatigue_delta +0 ~ +5。不触发战斗。",
        "trial":         "效果:hp_delta -15 ~ -25(撕裂心神),qi_delta -50 ~ -100,但 exp_delta +20 ~ +40 仅代表外传章命题强度。",
    }

    return base + f"""
【本类型规则】{type_rules.get(event_type, '一般规则')}

【输出严格 JSON】(不要 markdown,不要解释):
{{
  "type": "{event_type}",
  "name": "事件名 4-8 字 中式",
  "narrative": "60-120 字描写,带 ** 标记关键词",
  "effects": {{
    "hp_delta": int(-30 到 +30),
    "qi_delta": int(-100 到 +100),
    "exp_delta": int(-10 到 +50,只代表外传章命题强度,不直接加修为),
    "fatigue_delta": int(0 到 +15),
    "faction_delta": {{"门派id": ±1~5}} 或 {{}},
    "drop_item_id": "item_id 或 null",
    "spawn_enemy_id": "enemy_id 或 null",
    "force_battle": true/false
  }}
}}
约束:数值绝不允许瞬死(hp_delta < -30 禁止)。effects 所有字段必须存在。"""


# ════════════════════════════════════════════════════════════
# 入口:生成事件(选 type → build prompt → LLM 调用由外层完成)
# ════════════════════════════════════════════════════════════
def pick_and_build(
    visible_enemies: List[dict],
    character: dict,
    recent_battles: List[dict],
    enemy_ids: List[str],
    item_ids: List[str],
) -> Tuple[str, dict, str]:
    """返回 (event_type, type_meta, llm_prompt)"""
    etype, meta = select_event_type(visible_enemies, character, recent_battles)
    prompt = build_event_prompt(etype, character, visible_enemies, recent_battles, enemy_ids, item_ids)
    return etype, meta, prompt

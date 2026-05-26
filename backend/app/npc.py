"""地图 NPC 弟子系统 — Round 2

设计:
- 地图 10% 概率生成跨派 NPC 弟子,等级随玩家小幅浮动
- 5 种意图:pass / spar(切磋) / hostile(真斗) / trade(墟市) / teach(传授)
- 意图分布按等级差(强敌偏 hostile, 弱敌偏 pass)
- 数值:用对方派 base × realm_mult × 0.8(避免太难)
- 立绘:复用 players/{sect}/{realm}.png
"""
from __future__ import annotations
import json
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

from .sects import get_sect
from .combat_balance import balanced_enemy_stats


# ════════════════════════════════════════════════════════════
# 名字池 — 5 派 × 10 个修真风格名字
# ════════════════════════════════════════════════════════════
NAMES_BY_SECT = {
    "canglan": [
        "墨苍隐", "剑九霄", "韩沧澜", "云剑心", "陈墨痕",
        "白霜舞", "李寒月", "玄沧明", "苏剑书", "柳青锋",
    ],
    "tianji": [
        "鲁机巧", "齿轮翁", "万机生", "马掌门", "天枢君",
        "孔明算", "唐机心", "宋衡道", "周轮回", "杜推演",
    ],
    "xuanji": [
        "陈幻方", "李深思", "韩极简", "玄无声", "苏破局",
        "周虚空", "墨默想", "白冥道", "钱奇点", "孙极渊",
    ],
    "qingming": [
        "古朴生", "石根基", "周博学", "张稳重", "陈千古",
        "李厚土", "孙铜钟", "韩万卷", "墨千秋", "玉磐石",
    ],
    "yueyin": [
        "夜阑影", "月隐灵", "千年蛰", "苏夜行", "柳无声",
        "白月华", "墨幽明", "韩疾风", "陈寂夜", "玄翻盘",
    ],
}


def _load_disciple_templates() -> dict:
    """Load the 200 disciple templates generated from the character bible."""
    root = Path(__file__).resolve().parents[2]
    path = root / "frontend" / "src" / "data" / "disciples.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        by_sect: dict = {}
        for d in payload.get("disciples", []):
            by_sect.setdefault(d.get("sect_id"), []).append(d)
        return by_sect
    except Exception:
        return {}


DISCIPLES_BY_SECT = _load_disciple_templates()

# rank → 等级标签 + 数值乘数
RANK_TABLE = [
    # (rank_key, name, level_floor, level_ceiling, stat_mult, exp_mult)
    ("外门",  4,   25,  0.70, 0.8),
    ("内门",  26,  60,  0.85, 1.0),
    ("核心",  61,  120, 1.00, 1.2),
    ("长老",  121, 999, 1.15, 1.5),
]

# 意图 emoji
INTENT_ICON = {
    "pass":    "🚶",
    "spar":    "🤝",
    "hostile": "⚔️",
    "trade":   "🛒",
    "teach":   "📖",
}

# 意图标签
INTENT_LABEL = {
    "pass":    "路过",
    "spar":    "切磋",
    "hostile": "敌意",
    "trade":   "行商",
    "teach":   "传道",
}

# 派别专属掉落(被击败时)
SECT_DROPS = {
    "canglan": ["item_skill_essence_basic", "item_skill_essence_mid", "item_fur_white"],
    "tianji":  ["item_skill_essence_basic", "item_skill_essence_mid", "item_qi_dust"],
    "xuanji":  ["item_skill_essence_basic", "item_skill_codex_universal", "item_serpent_skin"],
    "qingming":["item_skill_essence_basic", "item_skill_essence_mid", "item_herb_basic"],
    "yueyin":  ["item_skill_essence_basic", "item_skill_codex_universal", "item_feather_white"],
}


@dataclass
class NpcSpawn:
    """NPC 弟子运行时实体(不持久,每次 spawn 新建)"""
    id: str
    name: str
    sect_id: str
    sect_name: str
    rank: str             # 外门 / 内门 / 核心 / 长老
    level: int
    title: str            # "沧澜·内门弟子"
    intent: str           # pass / spar / hostile / trade / teach
    hp: int
    max_hp: int
    atk: int
    def_: int
    spd: int
    rewards_exp: int
    rewards_qi: int
    drops: list = field(default_factory=list)
    image_url: str = ""
    image_emoji: str = "👤"
    description: str = ""
    clan: str = "修士"    # 兼容 enemy.clan 字段(前端要)
    tier: str = "mid"
    # 标记
    is_npc: bool = True
    portrait_kind: str = "player"
    portrait_id: str = ""


def _level_to_realm(level: int) -> str:
    """根据等级映射到 9 境界,与 sects.tiers 同步"""
    if level <= 10:   return "qi"
    if level <= 25:   return "foundation"
    if level <= 45:   return "golden"
    if level <= 65:   return "yuanying"
    if level <= 85:   return "huashen"
    if level <= 105:  return "hetishi"
    if level <= 125:  return "dacheng"
    if level <= 150:  return "dujie"
    return "feisheng"


def _pick_rank(level: int) -> tuple:
    """根据等级选 rank, 同时返回数值倍率"""
    for rank, lo, hi, stat_mult, exp_mult in RANK_TABLE:
        if lo <= level <= hi:
            return rank, stat_mult, exp_mult
    return RANK_TABLE[-1][0], RANK_TABLE[-1][3], RANK_TABLE[-1][4]


def _pick_intent(player_level: int, npc_level: int, player_friendliness: int = 0) -> str:
    """根据等级差选意图

    强 NPC(>+20%): pass 30 spar 10 hostile 40 trade 10 teach 10
    同级:           pass 40 spar 30 hostile 15 trade 10 teach 5
    弱 NPC(<-20%): pass 60 spar 15 hostile 10 trade 10 teach 5

    友好度低时 hostile +20%(从其它类型借)
    """
    diff_pct = (npc_level - player_level) / max(player_level, 1)
    if diff_pct > 0.2:
        weights = {"pass": 30, "spar": 10, "hostile": 40, "trade": 10, "teach": 10}
    elif diff_pct < -0.2:
        weights = {"pass": 60, "spar": 15, "hostile": 10, "trade": 10, "teach": 5}
    else:
        weights = {"pass": 40, "spar": 30, "hostile": 15, "trade": 10, "teach": 5}
    # 友好度低 → 敌意更高
    if player_friendliness < -10:
        bonus = 20
        weights["hostile"] += bonus
        for k in ("pass", "spar"):
            weights[k] = max(5, weights[k] - bonus // 2)
    keys = list(weights.keys())
    probs = list(weights.values())
    return random.choices(keys, weights=probs, k=1)[0]


def generate_npc(player_sect_id: str, player_level: int,
                 player_friendliness_by_sect: dict = None) -> NpcSpawn:
    """生成一个 NPC

    Args:
        player_sect_id: 玩家所属派(NPC 不会同派)
        player_level: 玩家等级
        player_friendliness_by_sect: {sect_id: int} 友好度,用于影响 intent
    """
    # 1. 选派(不要和玩家同派)
    other_sects = [s for s in NAMES_BY_SECT.keys() if s != player_sect_id]
    npc_sect = random.choice(other_sects)
    sect_conf = get_sect(npc_sect)
    sect_name = sect_conf.name if sect_conf else npc_sect

    # 2. 选定一个真实弟子模板。优先选择等级接近玩家者,避免地图上全是陌生泛用名。
    templates = DISCIPLES_BY_SECT.get(npc_sect) or []
    if templates:
        near_span = max(6, int(player_level * 0.12))
        near = [d for d in templates if abs(int(d.get("level", player_level)) - player_level) <= near_span]
        template = random.choice(near) if near else None
        if not template:
            name = random.choice(NAMES_BY_SECT[npc_sect])
            offset_max = max(1, int(player_level * 0.10))
            npc_level = max(1, player_level + random.randint(-offset_max, offset_max))
            rank, _stat_mult, _exp_mult = _pick_rank(npc_level)
            story_hook = ""
            appearance = ""
            disciple_template_id = ""
        else:
            name = template.get("name") or random.choice(NAMES_BY_SECT[npc_sect])
            npc_level = int(template.get("level") or player_level)
            rank = template.get("rank") or _pick_rank(npc_level)[0]
            story_hook = template.get("story_hook") or ""
            appearance = template.get("appearance") or ""
            disciple_template_id = template.get("id") or ""
    else:
        name = random.choice(NAMES_BY_SECT[npc_sect])
        offset_max = max(1, int(player_level * 0.10))
        npc_level = max(1, player_level + random.randint(-offset_max, offset_max))
        rank, _stat_mult, _exp_mult = _pick_rank(npc_level)
        story_hook = ""
        appearance = ""
        disciple_template_id = ""

    # 3. rank + 标题
    title = f"{sect_name} · {rank}弟子"

    # 5. 意图
    friendliness = (player_friendliness_by_sect or {}).get(npc_sect, 0)
    intent = _pick_intent(player_level, npc_level, friendliness)

    # 6. 数值:走统一战斗平衡,避免 NPC 生成时乘一次、进战斗后再乘一次。
    tier_map = {"外门":"low", "内门":"mid", "核心":"high", "长老":"myth"}
    npc_id = f"npc_{uuid.uuid4().hex[:10]}"
    probe = type("NpcBalanceProbe", (), {
        "id": npc_id,
        "tier": tier_map.get(rank, "mid"),
        "level": npc_level,
        "clan": f"{sect_name}弟子",
        "evasion": 0.05,
    })()
    stats = balanced_enemy_stats(probe, {"sect": player_sect_id})
    hp = stats["hp"]
    atk = stats["atk"]
    def_ = stats["def_"]
    spd = stats["spd"]
    rewards_exp = stats["rewards_exp"]
    rewards_qi = stats["rewards_qi"]

    # 7. 立绘。真实弟子优先使用 200 人独立画像,缺失时回退到境界通用立绘。
    realm_key = _level_to_realm(npc_level)
    if disciple_template_id:
        portrait_url = f"/images/portraits/disciples/{npc_sect}/{disciple_template_id}.png"
        portrait_id = f"{npc_sect}/{disciple_template_id}"
        portrait_kind = "disciple"
    else:
        portrait_url = f"/images/portraits/players/{npc_sect}/{realm_key}.png"
        portrait_id = f"{npc_sect}/{realm_key}"
        portrait_kind = "player"

    # 8. 掉落(只有 hostile 真斗会触发)
    drops = list(SECT_DROPS.get(npc_sect, [])) if intent == "hostile" else []

    # 9. 描述
    desc_map = {
        "pass":    f"路遇{name},行色匆匆。{story_hook}",
        "spar":    f"{name}见你修为不俗,欲与你切磋一番。{appearance}",
        "hostile": f"{name}目露锋芒,似被某段旧事牵动。{story_hook}",
        "trade":   f"{name}背着行囊,似在沿途行商。{appearance}",
        "teach":   f"{sect_name}{rank}弟子{name}凝视良久,似想传你一招。{story_hook}",
    }

    return NpcSpawn(
        id=npc_id,
        name=name,
        sect_id=npc_sect,
        sect_name=sect_name,
        rank=rank,
        level=npc_level,
        title=title,
        intent=intent,
        hp=hp, max_hp=hp,
        atk=atk, def_=def_, spd=spd,
        rewards_exp=rewards_exp,
        rewards_qi=rewards_qi,
        drops=drops,
        image_url=portrait_url,
        image_emoji="👤",
        description=desc_map.get(intent, ""),
        clan=f"{sect_name}弟子",
        tier=tier_map.get(rank, "mid"),
        portrait_kind=portrait_kind,
        portrait_id=portrait_id,
    )


def npc_to_spawn_dict(npc: NpcSpawn) -> dict:
    """转 ExploreMap.vue spawn 期望的字段格式(兼容 enemy_to_dict)"""
    return {
        "id": npc.id,
        "name": npc.name,
        "clan": npc.clan,
        "tier": npc.tier,
        "level": npc.level,
        "hp": npc.hp, "max_hp": npc.max_hp,
        "atk": npc.atk, "def_": npc.def_, "spd": npc.spd,
        "evasion": 0.05,
        "image_emoji": npc.image_emoji,
        "image_url": npc.image_url,
        "description": npc.description,
        "rewards": {"exp": npc.rewards_exp, "qi": npc.rewards_qi},
        # NPC 专属字段
        "is_npc": True,
        "sect_id": npc.sect_id,
        "sect_name": npc.sect_name,
        "rank": npc.rank,
        "title": npc.title,
        "intent": npc.intent,
        "intent_icon": INTENT_ICON.get(npc.intent, "👤"),
        "intent_label": INTENT_LABEL.get(npc.intent, "未知"),
        "drops": npc.drops,
        "portrait_kind": npc.portrait_kind,
        "portrait_id": npc.portrait_id,
    }


def npc_to_enemy_dict(npc: NpcSpawn, friendly: bool = False) -> dict:
    """转 BattleEngine 能用的 enemy 数据(兼容 enemy_to_dict)
    friendly=True 时 hp 降到 1 即停(切磋模式)
    """
    return {
        "id": npc.id,
        "name": npc.name,
        "clan": npc.clan,
        "tier": npc.tier,
        "level": npc.level,
        "hp": npc.hp, "max_hp": npc.max_hp,
        "atk": npc.atk, "def_": npc.def_, "spd": npc.spd,
        "evasion": 0.05,
        "image_emoji": npc.image_emoji,
        "image_url": npc.image_url,
        "description": npc.description,
        "rewards_exp": npc.rewards_exp,
        "rewards_qi": npc.rewards_qi,
        "drops": npc.drops,
        "is_npc": True,
        "friendly": friendly,
        "sect_id": npc.sect_id,
        "sect_name": npc.sect_name,
        "rank": npc.rank,
        "intent": "spar" if friendly else "hostile",
        "portrait_kind": npc.portrait_kind,
        "portrait_id": npc.portrait_id,
    }


# ════════════════════════════════════════════════════════════
# 临时 NPC 缓存(用于 spawn → engage 流程)
# ════════════════════════════════════════════════════════════
_npc_cache: dict = {}     # npc_id → NpcSpawn
_NPC_CACHE_MAX = 200      # 防内存膨胀


def cache_npc(npc: NpcSpawn) -> None:
    _npc_cache[npc.id] = npc
    if len(_npc_cache) > _NPC_CACHE_MAX:
        # 删最早的(简单 FIFO,字典 3.7+ 保插入序)
        for k in list(_npc_cache.keys())[:50]:
            _npc_cache.pop(k, None)


def get_cached_npc(npc_id: str) -> Optional[NpcSpawn]:
    return _npc_cache.get(npc_id)

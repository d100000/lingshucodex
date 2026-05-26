"""
8 大属性系统 — 修真世界的角色数值之源

每个属性都有明确的能力对应,所有派生数值都由此推导。
拜入门派时基础值由 sect 决定,LLM 随机机缘再加 5-10 点。
升级时玩家每级获得 3 自由点 + 1 派系倾向点。
"""

from typing import Dict, List
import random

# ════════════════════════════════════════════════════════════
# 8 大属性元数据
# ════════════════════════════════════════════════════════════
ATTRIBUTES = {
    "str": {"name": "力", "icon": "🥊", "desc": "物理攻击力,武器威力"},
    "qi":  {"name": "元", "icon": "💧", "desc": "灵气上限,法术加成"},
    "vit": {"name": "躯", "icon": "🛡️", "desc": "生命上限,抗性"},
    "agi": {"name": "敏", "icon": "🌪️", "desc": "速度,闪避"},
    "wis": {"name": "意", "icon": "👁️", "desc": "暴击率,心法领悟"},
    "end": {"name": "韧", "icon": "🪨", "desc": "防御,疲劳上限"},
    "fate":{"name": "缘", "icon": "🍀", "desc": "运气,奇遇概率,掉落"},
    "ins": {"name": "悟", "icon": "📜", "desc": "成章领悟,章节命题"},
}
ATTR_KEYS = list(ATTRIBUTES.keys())

# ════════════════════════════════════════════════════════════
# 5 派初始 8 属性(每派总和 50)
# ════════════════════════════════════════════════════════════
SECT_INITIAL_ATTRS = {
    "canglan": {  # 深思高暴击高悟
        "str": 7, "qi": 5, "vit": 6, "agi": 6,
        "wis": 9, "end": 5, "fate": 5, "ins": 7,
    },
    "tianji": {  # 均衡通用
        "str": 5, "qi": 7, "vit": 6, "agi": 7,
        "wis": 8, "end": 6, "fate": 6, "ins": 5,
    },
    "xuanji": {  # 灵气 + 高悟性
        "str": 4, "qi": 9, "vit": 5, "agi": 6,
        "wis": 7, "end": 4, "fate": 6, "ins": 9,
    },
    "qingming": {  # 高韧 + 学问
        "str": 5, "qi": 6, "vit": 7, "agi": 5,
        "wis": 7, "end": 8, "fate": 5, "ins": 7,
    },
    "yueyin": {  # 敏 + 缘 + 暴击
        "str": 5, "qi": 5, "vit": 5, "agi": 9,
        "wis": 7, "end": 4, "fate": 8, "ins": 7,
    },
}


def get_initial_attrs(sect_id: str) -> Dict[str, int]:
    """取该派初始 8 属性(默认沧澜)"""
    return dict(SECT_INITIAL_ATTRS.get(sect_id, SECT_INITIAL_ATTRS["canglan"]))


def random_bless(attrs: Dict[str, int], min_total: int = 5, max_total: int = 10) -> List[Dict]:
    """拜入仪式 — 随机给 5-10 点机缘(模拟 LLM 卜算)

    返回机缘事件列表,如 [{attr:"str", delta:2, note:"天生勇武"}, ...]
    """
    total = random.randint(min_total, max_total)
    blessings = []
    notes = {
        "str": ["天生勇武", "气血充盈", "肉身强横"],
        "qi":  ["灵根纯净", "聚灵之体", "玄气贯顶"],
        "vit": ["筋骨厚实", "百毒不侵", "龟息玄功"],
        "agi": ["身轻如燕", "御风之灵", "电掣之姿"],
        "wis": ["慧眼如炬", "心如明镜", "天眼初开"],
        "end": ["铁骨铮铮", "金刚不坏", "韧若苍松"],
        "fate":["七星福运", "莫名机缘", "因果相牵"],
        "ins": ["顿悟之灵", "通天之资", "笔下千秋"],
    }

    while total > 0:
        # 加权随机 — 每次 ±1~2
        delta = random.choice([1, 1, 1, 2])
        delta = min(delta, total)
        attr = random.choice(ATTR_KEYS)
        attrs[attr] = attrs.get(attr, 0) + delta
        blessings.append({
            "attr": attr,
            "attr_name": ATTRIBUTES[attr]["name"],
            "attr_icon": ATTRIBUTES[attr]["icon"],
            "delta": delta,
            "note": random.choice(notes.get(attr, ["天降异象"])),
        })
        total -= delta

    return blessings


# ════════════════════════════════════════════════════════════
# 境界倍率 — 让数值从百级到十万级(仙侠数值膨胀)
# ════════════════════════════════════════════════════════════
def realm_multiplier(level: int) -> float:
    """等级 → 战斗数值倍率
    Lv1=1x, Lv25=35x, Lv50=175x, Lv100=1100x, Lv200=8000x
    """
    if level <= 1:
        return 1.0
    return 1.0 + level * 0.2 + (level / 10) ** 2.8


# ════════════════════════════════════════════════════════════
# 派生数值公式
# ════════════════════════════════════════════════════════════
def derive_stats(attrs: Dict[str, int], level: int = 1) -> Dict:
    """根据 8 属性 + 等级算出全部派生数值"""
    s = attrs
    m = realm_multiplier(level)  # 境界膨胀倍率

    return {
        # ★ 战斗数值:乘境界倍率(后期爆炸增长)
        "atk":         int((20 + s.get("str", 0) * 2.5) * m),
        "max_qi":      int((600 + s.get("qi",  0) * 30) * m),
        "max_hp":      int((80  + s.get("vit", 0) * 8) * m),
        "spd":         int((75  + s.get("agi", 0) * 1.5) * m),
        "def_":        int((8 + s.get("end", 0) * 1.2) * m),

        # ★ 百分比属性:不随等级膨胀
        "evasion":     round(0.03 + s.get("agi", 0) * 0.004, 3),
        "crit_rate":   round(0.05 + s.get("wis", 0) * 0.008, 3),
        "crit_dmg":    round(1.5 + s.get("wis", 0) * 0.02, 2),
        "max_fatigue": int(80 + s.get("end", 0)),
        "luck":        round(0.5 + s.get("fate", 0) * 0.01, 3),
        "exp_mult":    round(1.0 + s.get("ins", 0) * 0.02, 3),  # 历史兼容字段,燃灵修为不再使用倍率
    }


# ════════════════════════════════════════════════════════════
# 友好度初始化(对所有派 0 中立)
# ════════════════════════════════════════════════════════════
def init_factions(own_sect: str) -> Dict[str, int]:
    """对各派初始友好度 — 自己派 +30 起步,其余 0"""
    from .sects import ALL_SECTS
    factions = {sid: 0 for sid in ALL_SECTS.keys()}
    factions[own_sect] = 30
    return factions


# ════════════════════════════════════════════════════════════
# 构建完整角色(创角时调用)
# ════════════════════════════════════════════════════════════
def build_initial_character(
    user_id: str,
    sect_id: str,
    name: str,
    base_url: str,
    api_key: str,
) -> Dict:
    """创角主入口 — 组合 8 属性 + 派生 + 友好度 + 疲劳 + 战斗历史"""
    attrs = get_initial_attrs(sect_id)
    blessings = random_bless(attrs)  # 拜入机缘
    derived = derive_stats(attrs)
    factions = init_factions(sect_id)

    from .sects import get_sect
    sect = get_sect(sect_id)

    char = {
        "user_id": user_id,
        "name": name,
        "sect": sect_id,
        "sect_name": sect.name if sect else "",
        "level": 1,
        "exp": 0,
        "realm": "qi",
        "realm_name": "炼气期",
        "base_url": base_url.rstrip("/"),
        "api_key": api_key.strip(),
        # ★ 8 属性
        "attrs": attrs,
        "blessings": blessings,  # 拜入机缘 log

        # ★ 派生数值(由 attrs 算出,前端展示用)
        **derived,
        "hp": derived["max_hp"],     # 初始满血
        "qi": derived["max_qi"],     # 初始满灵气
        "fatigue": 0,                # 初始无疲劳

        # ★ 友好度(对各派)
        "factions": factions,

        # ★ 战斗历史(��奇遇 LLM 用)
        "battle_history": [],        # ��近 N 场 [{ enemy_name, result, round_count }]

        # ★ 奇遇历史
        "fortune_log": [],

        # ★ 本命书 / 燃灵成章
        "cultivation_total": 0,
        "token_total": 0,
        "novel_words_total": 0,
        "chapters_count": 0,
        "current_volume": 1,
        "current_chapter_no": 0,
        "daily_token_used": 0,
        "monthly_token_used": 0,
        "budget_chapter": 0,
        "budget_daily": 0,
        "budget_monthly": 0,
        "budget_confirm_required": False,

        # ★ Round 1: 技能系统
        "learned_skills": [],
        "equipped_skills": [],
    }
    sync_learned_skills(char)
    return char


def sync_learned_skills(char: Dict) -> List[Dict]:
    """根据 sect + realm 同步可学技能(幂等,可重复调用):
       - 新增"应解锁但未学"的招式(Lv1)
       - equipped_skills 空时 auto-equip basic_strike + 5 个常用
    返回:新学到的 skill_id 列表
    """
    from .skill_templates import skills_for_sect_at_realm, ALL_SKILLS
    learned = char.get("learned_skills") or []
    learned_ids = {ls["skill_id"] for ls in learned}
    sect = char.get("sect", "canglan")
    realm = char.get("realm", "qi")
    newly = []
    for s in skills_for_sect_at_realm(sect, realm):
        if s.id not in learned_ids:
            learned.append({"skill_id": s.id, "level": 1})
            newly.append(s.id)
    char["learned_skills"] = learned

    equipped = char.get("equipped_skills") or []
    if not equipped and learned:
        pool = [ALL_SKILLS[ls["skill_id"]] for ls in learned if ls["skill_id"] in ALL_SKILLS]
        eq = ["basic_strike"] if any(s.id == "basic_strike" for s in pool) else []
        others = sorted([s for s in pool if s.id != "basic_strike" and s.tier != "ult"],
                        key=lambda s: s.qi_cost)
        for s in others[:5]:
            eq.append(s.id)
        char["equipped_skills"] = eq[:6]
    return newly


# ════════════════════════════════════════════════════════════
# 升级时重新算派生(attrs 变了重算 max_hp 等)
# ════════════════════════════════════════════════════════════
def refresh_derived(char: Dict) -> None:
    """根据 char.attrs + level 重新覆盖派生数值。in-place 修改。"""
    attrs = char.get("attrs", {})
    if not attrs:
        return
    level = char.get("level", 1)
    derived = derive_stats(attrs, level)
    # 派生覆盖,但 hp/qi/fatigue 当前值保留(不超 max)
    for k, v in derived.items():
        char[k] = v
    char["hp"] = min(char.get("hp", char["max_hp"]), char["max_hp"])
    char["qi"] = min(char.get("qi", char["max_qi"]), char["max_qi"])


# ════════════════════════════════════════════════════════════
# 统一升级处理 — 任何加 exp 之后都必须调用,否则不会升级!
# ════════════════════════════════════════════════════════════
TIER_TO_REALM = {
    "炼气": "qi", "筑基": "foundation", "金丹": "golden",
    "元婴": "yuanying", "化神": "huashen", "合体": "hetishi",
    "大乘": "dacheng", "渡劫": "dujie", "飞升": "feisheng",
}


def check_level_up(char: Dict) -> list:
    """检查 char.exp 是否足够升级 — 可连升多级。

    返回升级信息列表(空列表表示没升级)。
    [{level: int, new_realm: "金丹"(可选)}, ...]

    必须在所有加 exp 的位置调用!
    """
    from .sects import get_tier_for_level
    leveled = []
    while char["exp"] >= next_level_need(char["level"]):
        next_needed = next_level_need(char["level"])
        char["exp"] -= next_needed
        char["level"] += 1
        # 每升 1 级 +2 随机属性点
        attrs = char.get("attrs", {})
        if attrs:
            for _ in range(2):
                k = random.choice(list(attrs.keys()))
                attrs[k] = attrs.get(k, 0) + 1
            char["attrs"] = attrs
            refresh_derived(char)
        # 升级回满
        char["hp"] = char.get("max_hp", char.get("hp", 100))
        char["qi"] = char.get("max_qi", char.get("qi", 600))
        # 境界推进
        new_tier = get_tier_for_level(char.get("sect", "canglan"), char["level"])
        old_realm_name = char.get("realm_name", "")
        if new_tier and new_tier.name != old_realm_name:
            char["realm_name"] = new_tier.name
            char["realm"] = TIER_TO_REALM.get(new_tier.name, char.get("realm", "qi"))
            # ★ Round 1: 突破境界 → 自动学习新解锁的本派招式
            newly_learned = sync_learned_skills(char)
            leveled.append({"level": char["level"], "new_realm": new_tier.name,
                            "newly_learned_skills": newly_learned})
        else:
            leveled.append({"level": char["level"]})
    return leveled


def next_level_need(current_level: int) -> int:
    """No hard cap: level 200+ uses a mild soft curve for long-term pacing."""
    next_level = max(1, int(current_level or 1)) + 1
    base = next_level * 100
    if next_level <= 200:
        return base
    return int(base * (1 + (next_level - 200) * 0.004))

"""技能模板库 — 56 招式(6 通用 + 5 派 × 10 招)

数值设计:
- power: 1.0 = 基础攻击 (basic_strike)
- qi_cost: 灵气消耗
- crit_bonus: 暴击率额外加成 0-0.30
- max_level=5,每级 power +8%, qi_cost -4% (最低 80%),crit +1%

升级消耗:
  Lv1→2: 1× item_skill_essence_basic
  Lv2→3: 2× item_skill_essence_mid
  Lv3→4: 3× item_skill_essence_high
  Lv4→5: 5× item_skill_essence_supreme
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SkillTemplate:
    id: str
    name: str
    sect: str               # 'any' | 'canglan' | 'tianji' | 'xuanji' | 'qingming' | 'yueyin'
    realm_unlock: str       # qi / foundation / golden / ...
    type: str               # attack / heal / buff / ult
    qi_cost: int
    power: float
    hit_rate: float = 0.95
    crit_bonus: float = 0.0
    description: str = ""
    icon: str = "⚔️"
    max_level: int = 5
    # 流派(用于天命/buff 效果识别)
    tier: str = "basic"     # basic / normal / special / ult


# 升级消耗映射
UPGRADE_COST = {
    2: ("item_skill_essence_basic", 1),
    3: ("item_skill_essence_mid", 2),
    4: ("item_skill_essence_high", 3),
    5: ("item_skill_essence_supreme", 5),
}


# ════════════════════════════════════════════════════════════
# 通用招式 (6 招) — 任何门派可用
# ════════════════════════════════════════════════════════════
COMMON_SKILLS = [
    SkillTemplate("basic_strike", "灵气一击", "any", "qi", "attack",
                  8, 1.0, 0.98, description="基本的灵气攻击,稳定可靠", icon="⚡", tier="basic"),
    SkillTemplate("focus", "凝神咒", "any", "qi", "buff",
                  15, 0, description="集中精神,下一击 ATK +50%", icon="🌀", tier="normal"),
    SkillTemplate("lingdan", "灵丹", "any", "qi", "heal",
                  20, 0, description="服用一颗灵丹,恢复 30% HP", icon="💊", tier="basic"),
    SkillTemplate("ice_strike", "寒冰诀", "any", "foundation", "attack",
                  25, 1.5, 0.88, description="冰元素攻击,有几率冻结", icon="❄️", tier="special"),
    SkillTemplate("body_guard", "护体罡气", "any", "foundation", "buff",
                  18, 0, description="罡气护体,本战防御 +30%", icon="🛡️", tier="normal"),
    SkillTemplate("swift_wind", "御风诀", "any", "foundation", "buff",
                  12, 0, description="御风而行,本战速度 +30%", icon="🌪️", tier="normal"),
]


# ════════════════════════════════════════════════════════════
# 沧澜剑派 (10 招) — 剑意 / 深思
# ════════════════════════════════════════════════════════════
CANGLAN_SKILLS = [
    SkillTemplate("canglan_init", "剑诀·初", "canglan", "qi", "attack",
                  12, 1.2, 0.92, crit_bonus=0.05,
                  description="沧澜剑派入门式,凝聚剑意一击", icon="🗡️", tier="normal"),
    SkillTemplate("canglan_intent", "剑意凝聚", "canglan", "qi", "buff",
                  10, 0,
                  description="凝聚剑意,下一击暴击率 +30%", icon="✨", tier="normal"),
    SkillTemplate("canglan_flow", "流云剑式", "canglan", "foundation", "attack",
                  20, 1.6, 0.90, crit_bonus=0.08,
                  description="行云流水,连绵不绝", icon="☁️", tier="special"),
    SkillTemplate("canglan_bagua", "八卦剑阵", "canglan", "golden", "attack",
                  35, 1.9, 0.85, crit_bonus=0.10,
                  description="布下八卦剑阵,大范围伤害", icon="✴️", tier="special"),
    SkillTemplate("canglan_nine_first", "沧澜九式·初", "canglan", "yuanying", "ult",
                  60, 2.5, 0.88, crit_bonus=0.12,
                  description="九式之首,沧海无澜深不见底", icon="🌊", tier="ult"),
    SkillTemplate("canglan_soul", "千秋剑魂", "canglan", "huashen", "ult",
                  90, 3.0, 0.85, crit_bonus=0.15,
                  description="千秋剑魂凝聚,一击撼天", icon="⚔️", tier="ult"),
    SkillTemplate("canglan_ten_thousand", "万剑诀", "canglan", "hetishi", "ult",
                  120, 3.6, 0.82, crit_bonus=0.18,
                  description="万剑齐发,天地震颤", icon="🗡️", tier="ult"),
    SkillTemplate("canglan_nine_final", "沧澜九式·终", "canglan", "dacheng", "ult",
                  160, 4.2, 0.80, crit_bonus=0.20,
                  description="九式之终,一笔诛仙", icon="💎", tier="ult"),
    SkillTemplate("canglan_break_heaven", "渡劫剑·破天", "canglan", "dujie", "ult",
                  220, 5.2, 0.78, crit_bonus=0.22,
                  description="一剑破天,渡劫之姿", icon="🌟", tier="ult"),
    SkillTemplate("canglan_ascend_nine", "飞升剑·九霄", "canglan", "feisheng", "ult",
                  300, 6.5, 0.75, crit_bonus=0.25,
                  description="飞升大成,九霄之上独我一剑", icon="☄️", tier="ult"),
]


# ════════════════════════════════════════════════════════════
# 天机阁 (10 招) — 机关 / 全能
# ════════════════════════════════════════════════════════════
TIANJI_SKILLS = [
    SkillTemplate("tianji_gear", "齿轮诀", "tianji", "qi", "attack",
                  10, 1.1, 0.95,
                  description="齿轮飞旋,机关初成", icon="⚙️", tier="normal"),
    SkillTemplate("tianji_calc", "万象推演", "tianji", "qi", "buff",
                  12, 0,
                  description="推演万象,下一击命中 +20%", icon="🔮", tier="normal"),
    SkillTemplate("tianji_array", "机关阵图", "tianji", "foundation", "attack",
                  22, 1.4, 0.92,
                  description="布机关阵,伤害稳定", icon="🌐", tier="special"),
    SkillTemplate("tianji_thousand", "千机锁", "tianji", "golden", "attack",
                  32, 1.7, 0.90,
                  description="千道机关锁定要害", icon="🔒", tier="special"),
    SkillTemplate("tianji_wheel", "天机轮", "tianji", "yuanying", "ult",
                  55, 2.3, 0.92,
                  description="天机轮转,推演无穷", icon="⚙️", tier="ult"),
    SkillTemplate("tianji_void", "万象虚空", "tianji", "huashen", "ult",
                  85, 2.9, 0.90,
                  description="万象归一,虚空一击", icon="🌀", tier="ult"),
    SkillTemplate("tianji_destiny", "天机算尽", "tianji", "hetishi", "ult",
                  115, 3.4, 0.88,
                  description="算尽天机,百中有百", icon="📜", tier="ult"),
    SkillTemplate("tianji_universe", "万象归元", "tianji", "dacheng", "ult",
                  155, 4.0, 0.85,
                  description="万象皆归一元", icon="🔯", tier="ult"),
    SkillTemplate("tianji_break_law", "渡劫·破律", "tianji", "dujie", "ult",
                  210, 5.0, 0.82,
                  description="破天道之律,自创规则", icon="⚡", tier="ult"),
    SkillTemplate("tianji_ascend_god", "飞升·机神", "tianji", "feisheng", "ult",
                  290, 6.3, 0.80,
                  description="化身机关之神,操万法", icon="🌟", tier="ult"),
]


# ════════════════════════════════════════════════════════════
# 玄机宗 (10 招) — 暴击 / 深思
# ════════════════════════════════════════════════════════════
XUANJI_SKILLS = [
    SkillTemplate("xuanji_think", "深思一击", "xuanji", "qi", "attack",
                  10, 1.15, 0.95, crit_bonus=0.08,
                  description="深思而后动,首击破敌", icon="💭", tier="normal"),
    SkillTemplate("xuanji_phantom", "幻方咒", "xuanji", "qi", "buff",
                  10, 0,
                  description="幻方推演,本战暴击 +15%", icon="🔷", tier="normal"),
    SkillTemplate("xuanji_break", "破局诀", "xuanji", "foundation", "attack",
                  18, 1.5, 0.90, crit_bonus=0.12,
                  description="一招破局,直击要害", icon="💢", tier="special"),
    SkillTemplate("xuanji_extreme", "极简一式", "xuanji", "golden", "attack",
                  28, 1.8, 0.88, crit_bonus=0.15,
                  description="化繁为简,一击中的", icon="◼️", tier="special"),
    SkillTemplate("xuanji_million", "千局推演", "xuanji", "yuanying", "ult",
                  55, 2.4, 0.90, crit_bonus=0.18,
                  description="千局之中,选最优解", icon="🎯", tier="ult"),
    SkillTemplate("xuanji_silent", "幽思无声", "xuanji", "huashen", "ult",
                  85, 2.9, 0.88, crit_bonus=0.20,
                  description="幽暗之思,无声制敌", icon="🌑", tier="ult"),
    SkillTemplate("xuanji_singular", "奇点一击", "xuanji", "hetishi", "ult",
                  115, 3.5, 0.85, crit_bonus=0.22,
                  description="时空奇点,一击穿透", icon="⚛️", tier="ult"),
    SkillTemplate("xuanji_void_thought", "虚空冥思", "xuanji", "dacheng", "ult",
                  155, 4.1, 0.82, crit_bonus=0.24,
                  description="虚空冥想,直入对方心识", icon="🧠", tier="ult"),
    SkillTemplate("xuanji_break_origin", "渡劫·破源", "xuanji", "dujie", "ult",
                  210, 5.1, 0.80, crit_bonus=0.26,
                  description="破天地之源", icon="💫", tier="ult"),
    SkillTemplate("xuanji_ascend_origin", "飞升·本源", "xuanji", "feisheng", "ult",
                  290, 6.4, 0.78, crit_bonus=0.30,
                  description="本源觉醒,洞察天道", icon="🌌", tier="ult"),
]


# ════════════════════════════════════════════════════════════
# 青冥派 (10 招) — 防御 / 持久
# ════════════════════════════════════════════════════════════
QINGMING_SKILLS = [
    SkillTemplate("qingming_root", "根基诀", "qingming", "qi", "buff",
                  10, 0,
                  description="夯实根基,本战 HP 上限 +15%", icon="🌳", tier="normal"),
    SkillTemplate("qingming_strike", "稳重一击", "qingming", "qi", "attack",
                  12, 1.1, 0.96,
                  description="稳扎稳打,命中极高", icon="🪨", tier="normal"),
    SkillTemplate("qingming_classic", "千古经文", "qingming", "foundation", "buff",
                  20, 0,
                  description="经文护体,本战防御 +25%", icon="📜", tier="special"),
    SkillTemplate("qingming_solid", "坚毅之拳", "qingming", "golden", "attack",
                  30, 1.6, 0.94,
                  description="坚毅一拳,稳定输出", icon="✊", tier="special"),
    SkillTemplate("qingming_ancient", "古训重击", "qingming", "yuanying", "ult",
                  60, 2.3, 0.92,
                  description="承袭古训,一击千钧", icon="🏛️", tier="ult"),
    SkillTemplate("qingming_pile", "千卷藏锋", "qingming", "huashen", "ult",
                  90, 2.8, 0.90,
                  description="万卷古籍中的锋芒", icon="📚", tier="ult"),
    SkillTemplate("qingming_world", "天地为证", "qingming", "hetishi", "ult",
                  120, 3.4, 0.88,
                  description="天地为证,出手如山", icon="🏔️", tier="ult"),
    SkillTemplate("qingming_immortal", "古朴长生", "qingming", "dacheng", "ult",
                  160, 4.0, 0.86,
                  description="古朴长生诀,生生不息", icon="🌲", tier="ult"),
    SkillTemplate("qingming_break_stone", "渡劫·磐石", "qingming", "dujie", "ult",
                  215, 5.0, 0.84,
                  description="化身磐石,渡天劫", icon="⛰️", tier="ult"),
    SkillTemplate("qingming_ascend_earth", "飞升·后土", "qingming", "feisheng", "ult",
                  290, 6.2, 0.82,
                  description="飞升后土之尊,稳如苍穹", icon="🌐", tier="ult"),
]


# ════════════════════════════════════════════════════════════
# 月隐宫 (10 招) — 速度 / 闪避
# ════════════════════════════════════════════════════════════
YUEYIN_SKILLS = [
    SkillTemplate("yueyin_shadow", "月影一击", "yueyin", "qi", "attack",
                  11, 1.15, 0.94,
                  description="月光化影,一击闪过", icon="🌙", tier="normal"),
    SkillTemplate("yueyin_swift", "夜行如风", "yueyin", "qi", "buff",
                  10, 0,
                  description="夜行无声,速度 +30%", icon="💨", tier="normal"),
    SkillTemplate("yueyin_hide", "月隐之姿", "yueyin", "foundation", "buff",
                  18, 0,
                  description="月光遮身,本战闪避 +15%", icon="🌑", tier="special"),
    SkillTemplate("yueyin_assassin", "千年蛰伏", "yueyin", "golden", "attack",
                  30, 1.7, 0.90, crit_bonus=0.10,
                  description="蛰伏出手,一击致命", icon="🗡️", tier="special"),
    SkillTemplate("yueyin_memory", "千年回忆", "yueyin", "yuanying", "ult",
                  55, 2.4, 0.92,
                  description="召唤千年记忆,一击翻盘", icon="📿", tier="ult"),
    SkillTemplate("yueyin_seal", "夜阑长封", "yueyin", "huashen", "ult",
                  85, 2.9, 0.90,
                  description="夜阑深处,封印千年", icon="🌃", tier="ult"),
    SkillTemplate("yueyin_overturn", "翻盘一击", "yueyin", "hetishi", "ult",
                  115, 3.5, 0.88,
                  description="蛰伏千年,一击翻天", icon="🌠", tier="ult"),
    SkillTemplate("yueyin_eternal", "月隐永夜", "yueyin", "dacheng", "ult",
                  155, 4.1, 0.86,
                  description="月光化作永夜,笼罩天地", icon="🌚", tier="ult"),
    SkillTemplate("yueyin_break_dark", "渡劫·夜阑", "yueyin", "dujie", "ult",
                  210, 5.1, 0.84,
                  description="化身夜阑之灵,渡过天劫", icon="🌌", tier="ult"),
    SkillTemplate("yueyin_ascend_moon", "飞升·月华", "yueyin", "feisheng", "ult",
                  290, 6.4, 0.82,
                  description="月华飞升,清辉照苍穹", icon="☪️", tier="ult"),
]


# 汇总
ALL_SKILLS_LIST = COMMON_SKILLS + CANGLAN_SKILLS + TIANJI_SKILLS + XUANJI_SKILLS + QINGMING_SKILLS + YUEYIN_SKILLS
ALL_SKILLS = {s.id: s for s in ALL_SKILLS_LIST}


# ════════════════════════════════════════════════════════════
# 境界顺序(用于"达到此境界则解锁")
# ════════════════════════════════════════════════════════════
REALM_ORDER = ["qi", "foundation", "golden", "yuanying", "huashen", "hetishi", "dacheng", "dujie", "feisheng"]


def get_skill(skill_id: str) -> Optional[SkillTemplate]:
    return ALL_SKILLS.get(skill_id)


def skills_for_sect_at_realm(sect_id: str, current_realm: str) -> List[SkillTemplate]:
    """返回:玩家在该境界应该已经解锁的所有本派 + 通用招式(累计)"""
    try:
        max_idx = REALM_ORDER.index(current_realm)
    except ValueError:
        max_idx = 0
    unlocked = []
    for s in ALL_SKILLS_LIST:
        if s.sect not in ("any", sect_id):
            continue
        try:
            si = REALM_ORDER.index(s.realm_unlock)
        except ValueError:
            si = 0
        if si <= max_idx:
            unlocked.append(s)
    return unlocked


# ════════════════════════════════════════════════════════════
# 数值计算(按 learned level)
# ════════════════════════════════════════════════════════════
def _bounded_level(template: SkillTemplate, level: int) -> int:
    """Clamp persisted skill levels to the template range for legacy saves."""
    try:
        lv = int(level or 1)
    except (TypeError, ValueError):
        lv = 1
    return max(1, min(template.max_level, lv))


def effective_power(template: SkillTemplate, level: int) -> float:
    """每级 power +8%"""
    level = _bounded_level(template, level)
    return round(template.power * (1 + 0.08 * (level - 1)), 3)


def effective_qi_cost(template: SkillTemplate, level: int) -> int:
    """每级 qi_cost -4%,最低 80% 原值"""
    level = _bounded_level(template, level)
    factor = max(0.80, 1 - 0.04 * (level - 1))
    return max(1, int(round(template.qi_cost * factor)))


def effective_battle_qi_cost(template: SkillTemplate, level: int, max_qi: int | float) -> int:
    """Battle cost: percentage of max qi with the old fixed cost as the floor."""
    level = _bounded_level(template, level)
    fixed_floor = effective_qi_cost(template, level)
    pct_by_tier = {"basic": 0.01, "normal": 0.02, "special": 0.04, "ult": 0.07}
    pct = pct_by_tier.get(template.tier, 0.02)
    level_factor = max(0.76, 1 - 0.06 * (level - 1))
    scaled = int(round(max(1, float(max_qi or 1)) * pct * level_factor))
    return max(fixed_floor, scaled)


def effective_crit_bonus(template: SkillTemplate, level: int) -> float:
    """每级 crit +1%"""
    level = _bounded_level(template, level)
    return round(template.crit_bonus + 0.01 * (level - 1), 3)


def skill_to_dict(template: SkillTemplate, level: int = 1, learned: bool = False, equipped: bool = False) -> dict:
    """转字典 + 计算当前等级数值,供前端展示"""
    level = _bounded_level(template, level)
    return {
        "id": template.id,
        "name": template.name,
        "sect": template.sect,
        "realm_unlock": template.realm_unlock,
        "type": template.type,
        "tier": template.tier,
        "qi_cost": effective_qi_cost(template, level),
        "qi_cost_base": template.qi_cost,
        "power": effective_power(template, level),
        "power_base": template.power,
        "hit_rate": template.hit_rate,
        "crit_bonus": effective_crit_bonus(template, level),
        "description": template.description,
        "icon": template.icon,
        "level": level,
        "max_level": template.max_level,
        "learned": learned,
        "equipped": equipped,
        "next_upgrade": (
            None if level >= template.max_level
            else {
                "to_level": level + 1,
                "material_id": UPGRADE_COST[level + 1][0],
                "material_count": UPGRADE_COST[level + 1][1],
            }
        ),
    }

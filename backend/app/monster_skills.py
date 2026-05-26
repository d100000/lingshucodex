"""怪物招式表 — 12 族 × 4 招式 = 48 招

设计:
- 每族 4 级招式:basic / mid / high / ult
- 怪物等级决定可用招式池(L<=30 只用 basic/mid;L<=70 加 high;L>70 全开)
- 招式带名字、倍率、命中、暴击调整、特殊效果

效果字段(可选):
- hit_bonus: 命中率叠加(可正可负)
- crit_bonus: 暴击率叠加
- effect: "bleed" / "stun" / "qi_drain" 等(暂时仅用于叙事提示)
"""

from dataclasses import dataclass, field

@dataclass
class Skill:
    id: str
    name: str
    tier: str             # basic / mid / high / ult
    power: float          # ATK 倍率
    hit_rate: float       # 基础命中率
    crit_bonus: float = 0  # 暴击率额外叠加
    effect: str = ""       # 特殊效果(叙事用)
    description: str = ""  # 简介


# 4 个 tier 的默认数值参考:
# basic: 1.0x / 命中 0.92 / 暴击+0
# mid:   1.3x / 命中 0.88 / 暴击+5%
# high:  1.7x / 命中 0.82 / 暴击+10%
# ult:   2.4x / 命中 0.75 / 暴击+20%

SKILL_TABLE: dict[str, list[Skill]] = {

    # ============ 山林狐妖族 ============
    "山林狐妖族": [
        Skill("fox_basic", "妖光一闪", "basic", 1.0, 0.92, 0,
              description="狐尾轻摆,凝出一道朦胧妖光"),
        Skill("fox_mid",   "媚惑迷踪", "mid",   1.3, 0.88, 0.05,
              effect="confuse", description="九尾摇晃,以媚术扰乱心神"),
        Skill("fox_high",  "九尾剑舞", "high",  1.7, 0.82, 0.10,
              effect="multi", description="九条妖尾化作剑影,缠绕翻飞"),
        Skill("fox_ult",   "天狐神威", "ult",   2.4, 0.75, 0.20,
              effect="dread", description="九尾凝聚妖丹精华,神威骤现"),
    ],

    # ============ 灵雀飞鸟族 ============
    "灵雀飞鸟族": [
        Skill("bird_basic","啄影",    "basic", 1.0, 0.95, 0,
              description="尖喙划破空气,如影闪现"),
        Skill("bird_mid",  "翅风斩",  "mid",   1.3, 0.90, 0.03,
              effect="wind", description="羽翅鼓动,卷起一片刀锋之风"),
        Skill("bird_high", "凌空疾袭","high",  1.8, 0.85, 0.12,
              effect="dive", description="从高空俯冲而下,速度难以捕捉"),
        Skill("bird_ult",  "凤鸣九霄","ult",   2.5, 0.78, 0.18,
              effect="awe", description="凤血觉醒,鸣声震彻九天"),
    ],

    # ============ 蛇蟒族 ============
    "蛇蟒族": [
        Skill("serp_basic","吐信",    "basic", 0.9, 0.90, 0,
              description="蛇信吐出,沾染微毒"),
        Skill("serp_mid",  "毒齿咬",  "mid",   1.3, 0.85, 0,
              effect="poison", description="毒齿咬入,毒液蔓延"),
        Skill("serp_high", "蟒缠万钧","high",  1.8, 0.80, 0.05,
              effect="bind", description="巨蟒缠身,骨骼咯咯作响"),
        Skill("serp_ult",  "鳞甲反噬","ult",   2.3, 0.78, 0.15,
              effect="venom", description="毒鳞炸裂,化作万千毒针"),
    ],

    # ============ 猛兽族 ============
    "猛兽族": [
        Skill("beast_basic","利爪劈", "basic", 1.1, 0.90, 0.02,
              description="尖爪一挥,带起破空之声"),
        Skill("beast_mid",  "撕咬",   "mid",   1.4, 0.87, 0.08,
              effect="bleed", description="獠牙咬入,鲜血迸溅"),
        Skill("beast_high", "暴怒之扑","high", 1.9, 0.82, 0.15,
              effect="rage", description="瞳孔赤红,化作一道凶影直扑"),
        Skill("beast_ult",  "百兽之王","ult",  2.6, 0.75, 0.25,
              effect="terror", description="兽王长啸,百兽臣服"),
    ],

    # ============ 草木精怪族 ============
    "草木精怪族": [
        Skill("herb_basic","藤蔓缠", "basic", 0.9, 0.92, 0,
              description="藤蔓自地而起,层层缠绕"),
        Skill("herb_mid",  "毒花散", "mid",   1.2, 0.88, 0,
              effect="poison", description="花粉漫天,见者迷醉"),
        Skill("herb_high", "千年根脉","high", 1.7, 0.85, 0.05,
              effect="drain", description="深根吸取灵气,反哺自身"),
        Skill("herb_ult",  "神农怒木","ult",  2.4, 0.78, 0.15,
              effect="root", description="树王怒吼,大地为之震颤"),
    ],

    # ============ 鬼族 ============
    "鬼族": [
        Skill("ghost_basic","阴风扑", "basic", 1.0, 0.88, 0.05,
              description="阴风骤起,寒意刺骨"),
        Skill("ghost_mid",  "鬼火灼", "mid",   1.3, 0.83, 0.08,
              effect="burn", description="鬼火幽幽,焚烧魂魄"),
        Skill("ghost_high", "夺魂索", "high",  1.8, 0.78, 0.18,
              effect="soul", description="无形索链,直勾灵魂"),
        Skill("ghost_ult",  "阎罗审判","ult",  2.5, 0.72, 0.25,
              effect="judge", description="阴司判官现形,生死簿展开"),
    ],

    # ============ 龙族 ============
    "龙族": [
        Skill("dragon_basic","龙息",  "basic", 1.2, 0.92, 0.05,
              description="一口龙息喷出,蕴含天威"),
        Skill("dragon_mid",  "龙鳞甲","mid",  1.5, 0.88, 0.05,
              effect="defend", description="鳞甲反光,寒芒射出"),
        Skill("dragon_high", "龙吟九霄","high",2.0, 0.85, 0.15,
              effect="awe", description="一声龙吟,百兽臣服"),
        Skill("dragon_ult",  "真龙天罚","ult",2.8, 0.78, 0.25,
              effect="heaven", description="真龙化形,天威降临"),
    ],

    # ============ 神兽族 ============
    "神兽族": [
        Skill("div_basic", "神光", "basic", 1.3, 0.95, 0.08,
              description="周身金光大盛,正气浩然"),
        Skill("div_mid",   "四方阵","mid",  1.6, 0.90, 0.10,
              effect="seal", description="四方神兽印展开"),
        Skill("div_high",  "神兽真灵","high",2.1, 0.85, 0.18,
              effect="bless", description="本命真灵显化,威压十方"),
        Skill("div_ult",   "天命降世","ult",2.9, 0.80, 0.28,
              effect="divine", description="天命所归,圣光照亮苍穹"),
    ],

    # ============ 上古凶兽族 ============
    "上古凶兽族": [
        Skill("anc_basic", "凶煞", "basic", 1.3, 0.88, 0.08,
              description="凶煞之气扑面,凡人不敢直视"),
        Skill("anc_mid",   "远古之触","mid", 1.6, 0.82, 0.12,
              effect="ancient", description="自远古而来的死寂之力"),
        Skill("anc_high",  "鸿蒙吞天","high",2.2, 0.78, 0.20,
              effect="void", description="一口吞下苍穹星辰"),
        Skill("anc_ult",   "盘古遗烈","ult", 3.0, 0.72, 0.30,
              effect="primordial", description="鸿蒙开天的一斧再现"),
    ],

    # ============ 魔修族 ============
    "魔修族": [
        Skill("dem_basic", "血刃", "basic", 1.1, 0.90, 0.05,
              description="以自身鲜血凝刃"),
        Skill("dem_mid",   "嗜魂咒","mid",  1.4, 0.85, 0.10,
              effect="drain_qi", description="低声咒语,夺人灵气"),
        Skill("dem_high",  "魔焰焚天","high",1.9, 0.80, 0.18,
              effect="burn", description="黑色魔焰,焚尽一切"),
        Skill("dem_ult",   "魔王降世","ult",2.7, 0.72, 0.28,
              effect="demon", description="化身魔王,神挡杀神"),
    ],

    # ============ 仙器之灵族 ============
    "仙器之灵族": [
        Skill("art_basic", "器灵闪光","basic",1.2, 0.92, 0.06,
              description="器灵苏醒,银光乍现"),
        Skill("art_mid",   "古剑反射","mid", 1.5, 0.88, 0.08,
              effect="reflect", description="古剑反弹,以彼之道还彼之身"),
        Skill("art_high",  "千年器威","high",2.0, 0.83, 0.16,
              effect="ancient_weapon", description="千年法宝威能尽显"),
        Skill("art_ult",   "斧劈天门","ult", 2.8, 0.76, 0.24,
              effect="open_heaven", description="盘古遗斧再现,天门洞开"),
    ],

    # ============ 异域生灵族 ============
    "异域生灵族": [
        Skill("alien_basic","维度切割","basic",1.2, 0.88, 0.10,
              description="不属于本界的锋利"),
        Skill("alien_mid",  "异界凝视","mid", 1.5, 0.83, 0.15,
              effect="madness", description="一眼即可让人发狂"),
        Skill("alien_high", "时间裂隙","high",2.1, 0.78, 0.20,
              effect="time", description="撕开时间,在过去与未来同时攻击"),
        Skill("alien_ult",  "界外神谕","ult", 3.1, 0.70, 0.33,
              effect="god", description="界外神祇之意,本界天道亦无法阻挡"),
    ],
}


def get_skills_for_clan(clan: str) -> list[Skill]:
    return SKILL_TABLE.get(clan, SKILL_TABLE["山林狐妖族"])


def pick_skill_for_enemy(clan: str, level: int) -> Skill:
    """根据怪物等级随机选择一个招式。

    等级分段:
    - L 1-30:  basic 70%, mid 30%
    - L 31-70: basic 40%, mid 40%, high 20%
    - L 71-100: basic 20%, mid 30%, high 35%, ult 15%
    - L > 100: mid 20%, high 40%, ult 40%
    """
    import random
    skills = get_skills_for_clan(clan)
    if not skills:
        return None
    by_tier = {s.tier: s for s in skills}

    if level <= 30:
        weights = [("basic", 70), ("mid", 30)]
    elif level <= 70:
        weights = [("basic", 40), ("mid", 40), ("high", 20)]
    elif level <= 100:
        weights = [("basic", 20), ("mid", 30), ("high", 35), ("ult", 15)]
    else:
        weights = [("mid", 20), ("high", 40), ("ult", 40)]

    tiers, w = zip(*weights)
    picked = random.choices(tiers, weights=w, k=1)[0]
    return by_tier.get(picked) or skills[0]


def skill_to_dict(s: Skill) -> dict:
    return {
        "id": s.id, "name": s.name, "tier": s.tier,
        "power": s.power, "hit_rate": s.hit_rate,
        "crit_bonus": s.crit_bonus,
        "effect": s.effect, "description": s.description,
    }


# 招式 tier 中文
TIER_LABEL = {
    "basic": "凡品", "mid": "灵品",
    "high": "宝品", "ult": "仙品",
}

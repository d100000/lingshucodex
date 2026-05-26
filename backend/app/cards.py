"""战斗卡牌 — MVP 阶段 8 张通用 + 各派 2 张专属"""

from dataclasses import dataclass

@dataclass
class Card:
    id: str
    name: str
    sect_requirement: str   # "any" / "canglan" / "tianji" / ...
    type: str               # attack / defend / heal / buff / debuff
    qi_cost: int
    power: float            # ATK 倍率
    hit_rate: float
    description: str
    icon: str               # emoji
    crit_bonus: float = 0.0

CARDS = {
    # 通用入门牌
    "basic_strike": Card(
        id="basic_strike", name="灵气一击", sect_requirement="any",
        type="attack", qi_cost=8, power=1.0, hit_rate=0.95,
        description="最基础的灵气攻击,稳定可靠",
        icon="⚡",
    ),
    "focus": Card(
        id="focus", name="凝神咒", sect_requirement="any",
        type="buff", qi_cost=15, power=0,
        hit_rate=1.0,
        description="集中精神,下一击 ATK +50%",
        icon="🌀",
    ),
    "ice_strike": Card(
        id="ice_strike", name="寒冰诀", sect_requirement="any",
        type="attack", qi_cost=25, power=1.5, hit_rate=0.85,
        description="冰元素攻击,有几率冻结",
        icon="❄️",
    ),
    "lingdan": Card(
        id="lingdan", name="灵丹", sect_requirement="any",
        type="heal", qi_cost=20, power=0, hit_rate=1.0,
        description="服用一颗灵丹,恢复 30% HP(消耗 20 灵气)",
        icon="💊",
    ),

    # 沧澜剑派专属
    "canglan_init": Card(
        id="canglan_init", name="剑诀·初", sect_requirement="canglan",
        type="attack", qi_cost=12, power=1.2, hit_rate=0.9,
        description="沧澜剑派入门式,凝聚剑意一击",
        icon="🗡️",
    ),
    "canglan_nine": Card(
        id="canglan_nine", name="沧澜九式", sect_requirement="canglan",
        type="attack", qi_cost=60, power=2.5, hit_rate=0.85,
        description="七段连击,每段递增 +10%",
        icon="🌊",
    ),

    # 天机阁专属
    "tianji_gear": Card(
        id="tianji_gear", name="机关连发", sect_requirement="tianji",
        type="attack", qi_cost=20, power=1.4, hit_rate=0.92,
        description="多段机关攻击,稳定输出",
        icon="⚙️",
    ),
    "tianji_wanxiang": Card(
        id="tianji_wanxiang", name="万象归元", sect_requirement="tianji",
        type="attack", qi_cost=50, power=2.0, hit_rate=0.88,
        description="范围 AOE,所有敌人均受伤",
        icon="✨",
    ),
}

def get_card(card_id: str):
    """v1: 老 cards 表;v2 fallback: skill_templates.py(技能系统的卡)"""
    c = CARDS.get(card_id)
    if c:
        return c
    # ★ Round 1: 从新技能模板拿(并伪装成 Card 接口)
    try:
        from .skill_templates import get_skill
        tpl = get_skill(card_id)
        if tpl:
            # 用动态 dataclass 适配:复用 Card 字段名(id/name/sect_requirement/type/qi_cost/power/hit_rate/...)
            return Card(
                id=tpl.id,
                name=tpl.name,
                sect_requirement=tpl.sect,
                type=tpl.type,
                qi_cost=tpl.qi_cost,
                power=tpl.power,
                hit_rate=tpl.hit_rate,
                crit_bonus=tpl.crit_bonus,
                description=tpl.description,
                icon=tpl.icon,
            )
    except Exception:
        pass
    return None

def get_cards_for_sect(sect_id: str) -> list:
    """返回该派可用卡组(通用 + 专属)"""
    return [
        c for c in CARDS.values()
        if c.sect_requirement == "any" or c.sect_requirement == sect_id
    ]

def card_to_dict(c: Card):
    return {
        "id": c.id, "name": c.name, "type": c.type,
        "qi_cost": c.qi_cost, "power": c.power,
        "description": c.description, "icon": c.icon,
    }

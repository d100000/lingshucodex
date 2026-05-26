"""炼丹炼器 — 配方系统

设计原则:
- 低级丹药解决回血/回灵(打坐替代品,批量用)
- 中级装备提供构筑差异
- 高级灵宝接 Boss 和故事线
- 所有材料都有 ≥1 个配方用途
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Recipe:
    id: str
    name: str
    desc: str
    category: str  # pill / weapon / material / special
    materials: List[Tuple[str, int]]  # [(item_id, count), ...]
    result_id: str
    result_count: int = 1
    unlock_level: int = 1
    unlock_quest: Optional[str] = None  # 需要完成某任务才解锁


# ════════════════════════════════════════════════════════════
# 丹药配方(10 个)
# ════════════════════════════════════════════════════════════
PILL_RECIPES = [
    Recipe("recipe_pill_01", "回春丹", "恢复 20% HP",
           "pill", [("item_herb_basic", 3), ("item_qi_dust", 2)],
           "item_lingdan_basic", 2, unlock_level=1),

    Recipe("recipe_pill_02", "聚灵散", "恢复 20% 灵气",
           "pill", [("item_herb_basic", 2), ("item_serpent_skin", 1)],
           "item_focus_pill", 2, unlock_level=3),

    Recipe("recipe_pill_03", "解毒丸", "清除中毒状态",
           "pill", [("item_poison_sac", 2), ("item_herb_basic", 1)],
           "item_antidote", 3, unlock_level=5),

    Recipe("recipe_pill_04", "铁骨丹", "临时 +15% 防御(1 战)",
           "pill", [("item_beast_fur", 3), ("item_herb_basic", 2)],
           "item_iron_pill", 1, unlock_level=8),

    Recipe("recipe_pill_05", "灵犀丹", "临时 +10% 暴击(1 战)",
           "pill", [("item_feather_white", 2), ("item_focus_pill", 1)],
           "item_crit_pill", 1, unlock_level=10),

    Recipe("recipe_pill_06", "中品回春丹", "恢复 50% HP",
           "pill", [("item_herb_mid", 3), ("item_lingdan_basic", 2)],
           "item_lingdan_mid", 1, unlock_level=15),

    Recipe("recipe_pill_07", "疾风散", "临时 +20% 速度(1 战)",
           "pill", [("item_feather_rainbow", 2), ("item_swift_claw", 1)],
           "item_speed_pill", 1, unlock_level=18),

    Recipe("recipe_pill_08", "破境丹", "获得大量修为经验",
           "pill", [("item_yaodan", 3), ("item_herb_mid", 5), ("item_lingdan_mid", 2)],
           "item_pill_breakthrough", 1, unlock_level=25),

    Recipe("recipe_pill_09", "高品回春丹", "恢复 100% HP",
           "pill", [("item_herb_high", 3), ("item_pill_breakthrough", 1)],
           "item_lingdan_high", 1, unlock_level=35),

    Recipe("recipe_pill_10", "仙灵丹", "永久 +1 随机属性",
           "pill", [("item_dragon_scale", 3), ("item_pill_breakthrough", 2), ("item_herb_high", 5)],
           "item_pill_immortal", 1, unlock_level=50),
]

# ════════════════════════════════════════════════════════════
# 法宝配方(5 个)
# ════════════════════════════════════════════════════════════
WEAPON_RECIPES = [
    Recipe("recipe_wpn_01", "狐尾护符", "佩戴:+5% 闪避",
           "weapon", [("item_fur_white", 5), ("item_charm_doll", 2)],
           "item_fox_charm", 1, unlock_level=8),

    Recipe("recipe_wpn_02", "鹰眼护目镜", "佩戴:+8% 暴击率",
           "weapon", [("item_eagle_eye", 3), ("item_feather_rainbow", 3)],
           "item_eagle_goggles", 1, unlock_level=15),

    Recipe("recipe_wpn_03", "蛇鳞甲", "佩戴:+12% 防御",
           "weapon", [("item_serpent_scale_white", 3), ("item_serpent_skin", 5)],
           "item_serpent_armor", 1, unlock_level=20),

    Recipe("recipe_wpn_04", "龙骨杖", "佩戴:+15% 法术伤害",
           "weapon", [("item_dragon_scale", 5), ("item_ancient_horn", 2)],
           "item_dragon_staff", 1, unlock_level=35),

    Recipe("recipe_wpn_05", "凤凰羽扇", "佩戴:+10% 全属性",
           "weapon", [("item_phoenix_feather", 3), ("item_dragon_essence", 2), ("item_starlight", 1)],
           "item_phoenix_fan", 1, unlock_level=50),
]

# ════════════════════════════════════════════════════════════
# 材料升级配方(5 个)
# ════════════════════════════════════════════════════════════
MATERIAL_RECIPES = [
    Recipe("recipe_mat_01", "精炼白毛", "3 白毛 → 1 红毛",
           "material", [("item_fur_white", 3)],
           "item_fur_red", 1, unlock_level=5),

    Recipe("recipe_mat_02", "精炼白羽", "3 白羽 → 1 彩羽",
           "material", [("item_feather_white", 3)],
           "item_feather_rainbow", 1, unlock_level=8),

    Recipe("recipe_mat_03", "精炼草药", "5 初级草药 → 1 中级草药",
           "material", [("item_herb_basic", 5)],
           "item_herb_mid", 1, unlock_level=10),

    Recipe("recipe_mat_04", "精炼妖丹", "3 妖丹 → 1 龙鳞",
           "material", [("item_yaodan", 3)],
           "item_dragon_scale", 1, unlock_level=20),

    Recipe("recipe_mat_05", "精炼龙鳞", "3 龙鳞 → 1 龙精",
           "material", [("item_dragon_scale", 3)],
           "item_dragon_essence", 1, unlock_level=35),
]


# ════════════════════════════════════════════════════════════
# 汇总
# ════════════════════════════════════════════════════════════
ALL_RECIPES = PILL_RECIPES + WEAPON_RECIPES + MATERIAL_RECIPES
RECIPES_BY_ID = {r.id: r for r in ALL_RECIPES}

# 反向索引:材料 → 可用于哪些配方
MATERIAL_USAGE = {}
for r in ALL_RECIPES:
    for mat_id, _ in r.materials:
        MATERIAL_USAGE.setdefault(mat_id, []).append(r.id)


def get_recipe(recipe_id: str) -> Optional[Recipe]:
    return RECIPES_BY_ID.get(recipe_id)


def list_available_recipes(level: int) -> List[Recipe]:
    """返回当前等级可用的配方"""
    return [r for r in ALL_RECIPES if r.unlock_level <= level]


def get_material_usages(item_id: str) -> List[str]:
    """返回某材料可用于的配方 ID 列表"""
    return MATERIAL_USAGE.get(item_id, [])


def can_craft(recipe: Recipe, inventory: dict) -> bool:
    """判断背包是否足够合成"""
    for mat_id, need in recipe.materials:
        if inventory.get(mat_id, 0) < need:
            return False
    return True


def recipe_to_dict(r: Recipe) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "desc": r.desc,
        "category": r.category,
        "materials": [{"item_id": m[0], "count": m[1]} for m in r.materials],
        "result_id": r.result_id,
        "result_count": r.result_count,
        "unlock_level": r.unlock_level,
    }

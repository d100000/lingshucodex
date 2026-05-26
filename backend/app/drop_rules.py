"""Shared drop-rate rules for battle rewards and UI hints."""

SKILL_DROP_ITEM_IDS = {
    "item_skill_essence_basic",
    "item_skill_essence_mid",
    "item_skill_essence_high",
    "item_skill_essence_supreme",
    "item_skill_codex_universal",
}

SKILL_DROP_BY_TIER = {
    "low": "item_skill_essence_basic",
    "mid": "item_skill_essence_mid",
    "high": "item_skill_essence_high",
    "myth": "item_skill_essence_supreme",
}


def is_skill_drop_item(item) -> bool:
    if not item:
        return False
    item_id = getattr(item, "id", "")
    item_type = getattr(item, "type", "")
    return item_id in SKILL_DROP_ITEM_IDS or item_type == "skill_book"


def skill_drop_item_for_enemy(enemy) -> str:
    return SKILL_DROP_BY_TIER.get(getattr(enemy, "tier", ""), "item_skill_essence_basic")


def skill_drop_rate_for_enemy(enemy) -> float:
    """Skill essence drop chance grows with monster level.

    Low monsters start around 24%, mid monsters climb through 30%-70%,
    high monsters are very likely, and myth monsters guarantee the drop.
    """
    tier = getattr(enemy, "tier", "")
    level = max(1, int(getattr(enemy, "level", 1) or 1))
    if tier == "myth":
        return 1.0
    if tier == "high":
        return min(0.98, 0.78 + max(0, level - 40) * 0.008)
    if tier == "mid":
        return min(0.72, 0.28 + max(0, level - 15) * 0.018)
    return min(0.36, 0.20 + level * 0.012)


def drop_rate_label(rate: float) -> str:
    if rate >= 1:
        return "必掉"
    return f"{round(rate * 100)}%"

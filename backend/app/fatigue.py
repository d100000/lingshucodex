"""Round-based fatigue helpers.

Fatigue is now a round resource: player actions add fatigue, and the
"next round" world tick resets fatigue while restoring HP/QI by ratio.
"""

from __future__ import annotations

from typing import Any


FATIGUE_COSTS = {
    "meditate": 1,
    "inventory_use": 1,
    "craft": 2,
    "fortune": 3,
    "npc_pass": 1,
    "npc_trade": 1,
    "npc_teach": 3,
    "daily_claim": 1,
    "skill_equip": 1,
    "skill_upgrade": 2,
    "monster_chapter": 3,
    "boss_chapter": 5,
    "battle_round": 2,
    "battle_victory": 3,
    "battle_defeat": 6,
    "battle_fled": 2,
    "battle_pacified": 2,
    "spar_round": 1,
    "spar_win": 2,
    "spar_loss": 3,
    "meditate_inner": 4,
    "retreat_long": 10,
}


def max_fatigue(char: dict[str, Any]) -> int:
    return max(1, int(char.get("max_fatigue", 80) or 80))


def fatigue_is_full(char: dict[str, Any]) -> bool:
    return int(char.get("fatigue", 0) or 0) >= max_fatigue(char)


def add_fatigue(char: dict[str, Any], action: str, amount: int | None = None) -> dict[str, int | bool | str]:
    """Add fatigue and clamp to max. Returns a small delta payload."""
    cap = max_fatigue(char)
    before = max(0, int(char.get("fatigue", 0) or 0))
    gain = int(FATIGUE_COSTS.get(action, 1) if amount is None else amount)
    gain = max(0, gain)
    after = min(cap, before + gain)
    char["fatigue"] = after
    return {
        "action": action,
        "before": before,
        "after": after,
        "gain": after - before,
        "max": cap,
        "is_full": after >= cap,
    }


def add_battle_fatigue(char: dict[str, Any], result: str, rounds: int, friendly: bool = False) -> dict[str, int | bool | str]:
    if friendly:
        base_action = "spar_loss" if result in {"defeat", "spar_loss"} else "spar_win"
        per_round = FATIGUE_COSTS["spar_round"]
    else:
        result_action = {
            "victory": "battle_victory",
            "defeat": "battle_defeat",
            "fled": "battle_fled",
            "pacified": "battle_pacified",
        }.get(result, "battle_victory")
        base_action = result_action
        per_round = FATIGUE_COSTS["battle_round"]
    amount = FATIGUE_COSTS.get(base_action, 2) + max(0, int(rounds or 0)) * per_round
    return add_fatigue(char, base_action, amount)


def next_round_recovery(char: dict[str, Any], hp_pct: float = 0.30, qi_pct: float = 0.40) -> dict[str, int]:
    """Reset fatigue and restore HP/QI by max-value percentages."""
    max_hp = max(1, int(char.get("max_hp", 100) or 100))
    max_qi = max(1, int(char.get("max_qi", 600) or 600))
    old_hp = max(0, int(char.get("hp", max_hp) or 0))
    old_qi = max(0, int(char.get("qi", max_qi) or 0))
    old_fatigue = max(0, int(char.get("fatigue", 0) or 0))

    hp_gain = max(1, int(max_hp * hp_pct))
    qi_gain = max(1, int(max_qi * qi_pct))
    char["hp"] = min(max_hp, old_hp + hp_gain)
    char["qi"] = min(max_qi, old_qi + qi_gain)
    char["fatigue"] = 0
    char["meditate_streak"] = 0

    return {
        "hp_delta": char["hp"] - old_hp,
        "qi_delta": char["qi"] - old_qi,
        "fatigue_delta": -old_fatigue,
        "hp": char["hp"],
        "qi": char["qi"],
        "fatigue": 0,
    }

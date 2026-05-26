"""Central combat balance helpers.

The static monster and boss tables describe identity, tier, drops and lore.
This module turns those records into final battle numbers against a level
baseline, so combat pacing stays stable across levels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .attributes import derive_stats, get_initial_attrs
from .sects import get_tier_for_level


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class StatProfile:
    hp_ratio: float
    enemy_damage_pct: float
    player_turns: float
    spd: float
    qi_reward_pct: float
    exp_per_level: float


TIER_PROFILES: dict[str, StatProfile] = {
    "low": StatProfile(0.80, 0.035, 2.6, 0.95, 0.04, 4.0),
    "mid": StatProfile(1.05, 0.050, 3.6, 1.00, 0.07, 6.0),
    "high": StatProfile(1.55, 0.070, 5.0, 1.05, 0.10, 9.0),
    "myth": StatProfile(2.60, 0.085, 6.8, 1.08, 0.14, 14.0),
    "boss_story": StatProfile(4.50, 0.090, 10.0, 1.00, 0.18, 24.0),
    "boss_arc": StatProfile(7.00, 0.110, 14.0, 1.05, 0.24, 40.0),
    "boss_final": StatProfile(10.00, 0.130, 18.0, 1.08, 0.32, 70.0),
}


NPC_TIER_PROFILES: dict[str, StatProfile] = {
    "low": StatProfile(0.75, 0.030, 2.5, 0.98, 0.03, 3.0),
    "mid": StatProfile(0.95, 0.040, 3.3, 1.00, 0.04, 4.0),
    "high": StatProfile(1.20, 0.055, 4.2, 1.04, 0.06, 6.0),
    "myth": StatProfile(1.55, 0.070, 5.3, 1.08, 0.08, 9.0),
}


@dataclass(frozen=True)
class ClanProfile:
    hp: float = 1.0
    atk: float = 1.0
    def_: float = 1.0
    spd: float = 1.0
    evasion_bonus: float = 0.0


CLAN_PROFILES: dict[str, ClanProfile] = {
    "山林狐妖族": ClanProfile(0.90, 0.95, 0.85, 1.10, 0.02),
    "灵雀飞鸟族": ClanProfile(0.75, 0.95, 0.75, 1.30, 0.04),
    "蛇蟒族": ClanProfile(1.05, 0.90, 1.05, 0.90, 0.00),
    "猛兽族": ClanProfile(1.10, 1.10, 0.95, 1.05, 0.01),
    "草木精怪族": ClanProfile(1.35, 0.80, 1.15, 0.75, 0.00),
    "鬼族": ClanProfile(0.85, 1.05, 0.75, 1.10, 0.04),
    "龙族": ClanProfile(1.25, 1.15, 1.15, 1.00, 0.02),
    "神兽族": ClanProfile(1.20, 1.15, 1.20, 1.05, 0.02),
    "上古凶兽族": ClanProfile(1.35, 1.25, 1.10, 0.95, 0.01),
    "魔修族": ClanProfile(0.95, 1.20, 0.90, 1.05, 0.03),
    "仙器之灵族": ClanProfile(1.10, 1.05, 1.35, 0.90, 0.00),
    "异域生灵族": ClanProfile(1.00, 1.25, 1.00, 1.15, 0.03),
}


def _expected_attrs(sect_id: str, level: int) -> dict[str, float]:
    attrs = get_initial_attrs(sect_id)
    bless_avg = 7.5 / 8
    level_avg = max(0, level - 1) * 2 / 8
    return {key: value + bless_avg + level_avg for key, value in attrs.items()}


def expected_player_stats(sect_id: str = "canglan", level: int = 1) -> dict[str, int | float]:
    level = max(1, int(level or 1))
    stats = derive_stats(_expected_attrs(sect_id, level), level)
    tier = get_tier_for_level(sect_id, level)
    atk_mult = tier.atk_multiplier if tier else 1.0
    stats["battle_atk"] = int(stats["atk"] * atk_mult)
    stats["atk_mult"] = atk_mult
    return stats


def player_battle_stats(character: dict) -> dict[str, int | float]:
    sect_id = character.get("sect", "canglan")
    level = max(1, int(character.get("level", 1) or 1))
    tier = get_tier_for_level(sect_id, level)
    atk_mult = tier.atk_multiplier if tier else 1.0
    atk = int(character.get("atk", 20) * atk_mult)
    return {
        "max_hp": int(character.get("max_hp", 100)),
        "battle_atk": atk,
        "def_": int(character.get("def_", 8)),
        "spd": int(character.get("spd", 75)),
        "max_qi": int(character.get("max_qi", 600)),
        "atk_mult": atk_mult,
    }


def _is_boss(enemy: Any) -> bool:
    return hasattr(enemy, "title") and hasattr(enemy, "sect_id")


def _is_npc(enemy: Any) -> bool:
    return str(getattr(enemy, "id", "")).startswith("npc_")


def _profile_key(enemy: Any) -> str:
    if _is_boss(enemy):
        if getattr(enemy, "id", "") == "boss_final_void":
            return "boss_final"
        if int(getattr(enemy, "level", 1) or 1) >= 100:
            return "boss_arc"
        return "boss_story"
    return getattr(enemy, "tier", "mid") or "mid"


def _individual_mod(enemy: Any, field: str) -> float:
    if str(getattr(enemy, "id", "")).startswith("npc_") or _is_boss(enemy):
        return 1.0
    raw = max(1, float(getattr(enemy, field, 1) or 1))
    tier = getattr(enemy, "tier", "mid")
    baselines = {
        "hp": {"low": 180, "mid": 1000, "high": 8000, "myth": 30000},
        "atk": {"low": 25, "mid": 80, "high": 260, "myth": 650},
        "def_": {"low": 8, "mid": 28, "high": 100, "myth": 260},
    }
    baseline = baselines.get(field, {}).get(tier, raw)
    return clamp((raw / max(1, baseline)) ** 0.10, 0.88, 1.18)


def _baseline_player_power(level: int) -> float:
    if level < 11:
        return 1.2
    if level < 26:
        return 1.6
    if level < 46:
        return 1.9
    if level < 66:
        return 2.5
    if level < 86:
        return 3.0
    if level < 106:
        return 3.6
    if level < 126:
        return 4.2
    if level < 151:
        return 5.2
    return 6.5


def _baseline_enemy_power(level: int) -> float:
    if level <= 30:
        return 1.15
    if level <= 70:
        return 1.45
    if level <= 100:
        return 1.85
    return 2.25


def _legacy_formula_atk_for_damage(target_damage: float, defender_def: int | float, power: float) -> int:
    return max(1, int(target_damage * (100 + max(0.0, float(defender_def or 0))) / max(1.0, float(power or 1) * 100)))


def _legacy_formula_def_for_damage(attacker_atk: int | float, power: float, target_damage: float) -> int:
    if target_damage <= 0:
        return 0
    defense = max(1.0, float(attacker_atk or 1)) * max(0.0, float(power or 0)) * 100 / target_damage - 100
    return max(0, int(defense))


def balanced_enemy_stats(enemy: Any, character: dict | None = None) -> dict[str, int | float | str]:
    level = max(1, int(getattr(enemy, "level", 1) or 1))
    sect_id = (character or {}).get("sect", "canglan")
    base = expected_player_stats(sect_id, level)
    profile_key = _profile_key(enemy)
    profile_pool = NPC_TIER_PROFILES if _is_npc(enemy) else TIER_PROFILES
    profile = profile_pool.get(profile_key, profile_pool["mid"])
    clan = CLAN_PROFILES.get(getattr(enemy, "clan", ""), ClanProfile())
    late_hp_mult = 1.0
    late_atk_mult = 1.0

    hp_ratio = profile.hp_ratio * clan.hp * _individual_mod(enemy, "hp")
    if not _is_boss(enemy):
        hp_cap = {"low": 1.0, "mid": 1.25, "high": 2.0, "myth": 3.2}.get(profile_key, 1.25)
        if _is_npc(enemy):
            hp_cap = {"low": 0.9, "mid": 1.05, "high": 1.35, "myth": 1.7}.get(profile_key, 1.05)
        hp_ratio = min(hp_ratio, hp_cap)
    hp = int(base["max_hp"] * hp_ratio * late_hp_mult)

    target_player_damage = max(1.0, hp / max(1.0, profile.player_turns * clan.def_))
    defense = _legacy_formula_def_for_damage(
        base["battle_atk"],
        _baseline_player_power(level),
        target_player_damage,
    )

    target_enemy_damage = max(1.0, base["max_hp"] * profile.enemy_damage_pct * clan.atk)
    atk = _legacy_formula_atk_for_damage(
        target_enemy_damage,
        base["def_"],
        _baseline_enemy_power(level),
    )
    spd = int(base["spd"] * profile.spd * clan.spd)
    evasion = clamp(float(getattr(enemy, "evasion", 0.05) or 0.05) + clan.evasion_bonus, 0.02, 0.42)

    rewards_qi = max(10, int(base["max_qi"] * profile.qi_reward_pct))
    rewards_exp = max(0, int(level * profile.exp_per_level))
    return {
        "profile": profile_key,
        "hp": max(1, hp),
        "max_hp": max(1, hp),
        "atk": max(1, atk),
        "def_": max(0, defense),
        "spd": max(1, spd),
        "evasion": round(evasion, 3),
        "rewards_exp": rewards_exp,
        "rewards_qi": rewards_qi,
    }


def mitigation(defender_def: int | float, attacker_atk: int | float) -> float:
    defender_def = max(0.0, float(defender_def or 0))
    raw = defender_def / (100 + defender_def)
    return clamp(raw, 0.08, 0.72)


def combat_damage(attacker_atk: int | float, defender_def: int | float, power: float,
                  crit: bool = False, crit_dmg: float = 1.5, variance: float = 1.0) -> int:
    base = max(1.0, float(attacker_atk or 1)) * max(0.0, float(power or 0))
    damage = base * 100 / (100 + max(0.0, float(defender_def or 0))) * variance
    if crit:
        damage *= max(1.0, float(crit_dmg or 1.5))
    return max(1, int(damage))


def expected_combat_damage(attacker_atk: int | float, defender_def: int | float, power: float,
                           crit_rate: float = 0.0, crit_dmg: float = 1.5) -> int:
    normal = combat_damage(attacker_atk, defender_def, power, False, crit_dmg, 1.0)
    crit = combat_damage(attacker_atk, defender_def, power, True, crit_dmg, 1.0)
    rate = clamp(float(crit_rate or 0.0), 0.0, 0.95)
    return max(1, int(normal * (1 - rate) + crit * rate))


def combat_hit_rate(base_hit: float, evasion: float, low: float = 0.65, high: float = 0.98) -> float:
    return round(clamp(float(base_hit or 0.9) - float(evasion or 0), low, high), 3)

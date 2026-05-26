#!/usr/bin/env python3
"""Print combat balance snapshots for key levels."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.combat_balance import balanced_enemy_stats, expected_combat_damage, expected_player_stats
from app.enemies import ENEMIES
from app.monster_skills import get_skills_for_clan


def skill_power_for_level(level: int) -> float:
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


def enemy_average_power(clan: str, level: int) -> float:
    skills = get_skills_for_clan(clan)
    by_tier = {skill.tier: skill.power for skill in skills}
    if level <= 30:
        weights = {"basic": 0.70, "mid": 0.30}
    elif level <= 70:
        weights = {"basic": 0.40, "mid": 0.40, "high": 0.20}
    elif level <= 100:
        weights = {"basic": 0.20, "mid": 0.30, "high": 0.35, "ult": 0.15}
    else:
        weights = {"mid": 0.20, "high": 0.40, "ult": 0.40}
    return sum(by_tier.get(tier, 1.0) * weight for tier, weight in weights.items())


def sample_enemy(level: int):
    return min(ENEMIES.values(), key=lambda enemy: abs(enemy.level - level))


def main() -> None:
    print(
        "level,player_hp,player_atk,player_def,enemy,enemy_level,tier,"
        "enemy_hp,enemy_hp_ratio,enemy_atk,enemy_def,"
        "player_hit,player_hit_pct,enemy_hit,enemy_hit_pct,player_turns,enemy_turns"
    )
    for level in [10, 30, 60, 100, 160]:
        player = expected_player_stats("canglan", level)
        enemy = sample_enemy(level)
        stats = balanced_enemy_stats(enemy, {"sect": "canglan"})
        player_damage = expected_combat_damage(
            player["battle_atk"],
            stats["def_"],
            skill_power_for_level(level),
            crit_rate=0.20,
            crit_dmg=1.8,
        )
        enemy_damage = expected_combat_damage(
            stats["atk"],
            player["def_"],
            enemy_average_power(enemy.clan, enemy.level),
            crit_rate=0.10,
            crit_dmg=1.6,
        )
        print(
            f"{level},{player['max_hp']},{player['battle_atk']},{player['def_']},"
            f"{enemy.name},{enemy.level},{enemy.tier},"
            f"{stats['hp']},{stats['hp'] / max(1, player['max_hp']):.2f},{stats['atk']},{stats['def_']},"
            f"{player_damage},{player_damage / max(1, stats['hp']):.2%},"
            f"{enemy_damage},{enemy_damage / max(1, player['max_hp']):.2%},"
            f"{stats['hp'] / max(1, player_damage):.1f},"
            f"{player['max_hp'] / max(1, enemy_damage):.1f}"
        )


if __name__ == "__main__":
    main()

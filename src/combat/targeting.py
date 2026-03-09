"""Rank-based target selection for the ATB lane combat system."""

import random
from src.combat.unit import CombatUnit


def get_front_enemy(enemies: list[CombatUnit]) -> CombatUnit | None:
    """Return the alive enemy at the lowest rank (front-most)."""
    alive = [u for u in enemies if u.alive]
    if not alive:
        return None
    return min(alive, key=lambda u: u.rank)


def get_lowest_hp_enemy(enemies: list[CombatUnit]) -> CombatUnit | None:
    """Return the alive enemy with the lowest HP."""
    alive = [u for u in enemies if u.alive]
    if not alive:
        return None
    return min(alive, key=lambda u: u.hp)


def get_front_rank_enemies(enemies: list[CombatUnit], max_rank: int = 2) -> list[CombatUnit]:
    """Return alive enemies in the front ranks (rank <= max_rank)."""
    return [u for u in enemies if u.alive and u.rank <= max_rank]


def get_auto_attack_target(source: CombatUnit,
                           enemies: list[CombatUnit]) -> CombatUnit | None:
    """Auto-attacks always target the front-most enemy."""
    return get_front_enemy(enemies)


def get_targets(targeting: str, source: CombatUnit,
                allies: list[CombatUnit],
                enemies: list[CombatUnit],
                ability_range: str = "ranged") -> list[CombatUnit]:
    """Return list of valid targets based on targeting type and ability range."""
    alive_enemies = [u for u in enemies if u.alive]
    alive_allies = [u for u in allies if u.alive]

    if targeting == "single_enemy":
        if ability_range == "melee":
            # Melee: can only hit front ranks (1-2)
            front = get_front_rank_enemies(enemies, max_rank=2)
            if front:
                return [min(front, key=lambda u: u.rank)]
            # Fallback: hit whoever is available
            return [get_front_enemy(enemies)] if alive_enemies else []
        else:
            # Ranged: target front-most by default
            target = get_front_enemy(enemies)
            return [target] if target else []

    elif targeting == "front_two":
        # Hits enemies at ranks 1 and 2 (Cleaving Flame, Piercing Arrow)
        front = get_front_rank_enemies(enemies, max_rank=2)
        return sorted(front, key=lambda u: u.rank) if front else []

    elif targeting == "all_enemies":
        return alive_enemies

    elif targeting == "single_ally":
        if alive_allies:
            # Pick lowest HP ally
            return [min(alive_allies, key=lambda u: u.hp)]
        return []

    elif targeting == "all_allies":
        return alive_allies

    elif targeting == "self":
        return [source]

    # Default: front-most enemy
    target = get_front_enemy(enemies)
    return [target] if target else []

"""Target selection logic for abilities and auto-attacks."""

import random
import math
from src.combat.unit import CombatUnit


def get_nearest_enemy(source: CombatUnit,
                      enemies: list[CombatUnit]) -> CombatUnit | None:
    """Return the nearest alive enemy by distance."""
    alive = [u for u in enemies if u.alive]
    if not alive:
        return None
    return min(alive, key=lambda u: math.hypot(u.x - source.x, u.y - source.y))


def get_targets(targeting: str, source: CombatUnit,
                allies: list[CombatUnit],
                enemies: list[CombatUnit]) -> list[CombatUnit]:
    """Return list of valid targets based on targeting type."""
    alive_enemies = [u for u in enemies if u.alive]
    alive_allies = [u for u in allies if u.alive]

    if targeting == "single_enemy":
        nearest = get_nearest_enemy(source, enemies)
        return [nearest] if nearest else []

    elif targeting == "all_enemies":
        return alive_enemies

    elif targeting == "single_ally":
        if alive_allies:
            return [random.choice(alive_allies)]
        return []

    elif targeting == "all_allies":
        return alive_allies

    elif targeting == "self":
        return [source]

    # Default: nearest enemy
    nearest = get_nearest_enemy(source, enemies)
    return [nearest] if nearest else []

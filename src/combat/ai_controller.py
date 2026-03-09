"""AI controller for non-player ally units and enemies."""

import random
from src.combat.unit import CombatUnit
from src.combat.ability import AbilityRegistry
from src.combat.realtime_battle import RealtimeBattle
from config import (
    PLAYER_ZONE_X_MIN, PLAYER_ZONE_X_MAX,
    PLAYER_ZONE_Y_MIN, PLAYER_ZONE_Y_MAX,
    ENEMY_ZONE_X_MIN, ENEMY_ZONE_X_MAX,
    ENEMY_ZONE_Y_MIN, ENEMY_ZONE_Y_MAX,
)


class AIController:
    """Controls AI-driven units: ally positioning and ability usage."""

    def __init__(self, battle: RealtimeBattle, ability_registry: AbilityRegistry):
        self.battle = battle
        self.ability_registry = ability_registry

    def update(self, dt: float, player_unit: CombatUnit | None = None):
        """Update all AI-controlled units."""
        for unit in self.battle.player_units:
            if not unit.alive:
                continue
            # Skip the player-controlled unit
            if unit.id == self.battle.player_controlled_id:
                continue
            self._update_ally(unit, dt, player_unit)
            self._try_use_ability(unit)

        for unit in self.battle.enemy_units:
            if not unit.alive:
                continue
            self._update_enemy(unit, dt)
            self._try_use_ability(unit)

    def _update_ally(self, unit: CombatUnit, dt: float,
                     player_unit: CombatUnit | None):
        """Move ally to follow player with offset."""
        if not player_unit:
            return

        # Determine formation offset based on unit index
        allies = [u for u in self.battle.player_units
                  if u.id != self.battle.player_controlled_id and u.alive]
        try:
            idx = allies.index(unit)
        except ValueError:
            idx = 0

        # Spread vertically around player, offset behind
        offsets = [(-60, -80), (-60, 80), (-80, 0)]
        ox, oy = offsets[idx % len(offsets)]
        target_x = max(PLAYER_ZONE_X_MIN, min(PLAYER_ZONE_X_MAX,
                                                player_unit.x + ox))
        target_y = max(PLAYER_ZONE_Y_MIN, min(PLAYER_ZONE_Y_MAX,
                                                player_unit.y + oy))

        # Smooth lerp toward target
        lerp_speed = 3.0
        unit.x += (target_x - unit.x) * lerp_speed * dt
        unit.y += (target_y - unit.y) * lerp_speed * dt

    def _update_enemy(self, unit: CombatUnit, dt: float):
        """Enemies hold position with slight vertical drift."""
        # Gentle vertical oscillation
        import math
        drift = math.sin(unit.time_alive * 0.5 + hash(unit.name) % 10) * 0.3
        unit.y += drift
        # Clamp to enemy zone
        unit.y = max(ENEMY_ZONE_Y_MIN, min(ENEMY_ZONE_Y_MAX, unit.y))

    def _try_use_ability(self, unit: CombatUnit):
        """Try to fire an ability if off cooldown (random chance per frame)."""
        if unit.is_stunned:
            return
        # Small chance per frame to check abilities (avoids instant-firing)
        if random.random() > 0.02:  # ~1.2 checks per second at 60fps
            return

        for ability_id in unit.ability_ids:
            if unit.can_use_ability(ability_id):
                self.battle.fire_ability(unit, ability_id)
                break

"""AI controller for non-player units in ATB lane combat."""

import random
from src.combat.unit import CombatUnit
from src.combat.ability import AbilityRegistry
from src.combat.realtime_battle import RealtimeBattle


class AIController:
    """Controls AI-driven units: auto-ability usage (no positioning needed)."""

    def __init__(self, battle: RealtimeBattle, ability_registry: AbilityRegistry):
        self.battle = battle
        self.ability_registry = ability_registry

    def update(self, dt: float, player_unit: CombatUnit | None = None):
        """Update all AI-controlled units (ability usage only)."""
        for unit in self.battle.player_units:
            if not unit.alive:
                continue
            if unit.id == self.battle.player_controlled_id:
                continue
            self._try_use_ability(unit)

        for unit in self.battle.enemy_units:
            if not unit.alive:
                continue
            self._try_use_ability(unit)

    def _try_use_ability(self, unit: CombatUnit):
        """Try to fire an ability if off cooldown (random chance per frame)."""
        if unit.is_stunned:
            return
        # Small chance per frame to check abilities (~1.2 checks/sec at 60fps)
        if random.random() > 0.02:
            return

        for ability_id in unit.ability_ids:
            if unit.can_use_ability(ability_id):
                self.battle.fire_ability(unit, ability_id)
                break

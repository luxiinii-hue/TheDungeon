"""Real-time combat engine — replaces turn-based auto_battle.py."""

import random
from dataclasses import dataclass
from src.combat.unit import CombatUnit
from src.combat.ability import AbilityRegistry, AbilityDef
from src.combat.targeting import get_nearest_enemy, get_targets
from src.combat.projectile import Projectile
from config import (
    PROJECTILE_BASE_SPEED, PROJECTILE_ABILITY_SPEED,
    DAMAGE_ARMOR_FACTOR, CLASS_ATTACK_SPRITES
)


@dataclass
class BattleAction:
    """Event emitted by the battle engine for the UI to consume."""
    type: str  # "attack", "ability", "hit", "dodge", "defeat", "victory",
               # "lose", "burn_tick", "stun_applied", "reflect", "summon"
    source: str = ""
    target: str = ""
    ability_name: str = ""
    damage: int = 0
    heal: int = 0
    message: str = ""


# Class-themed auto-attack colors
CLASS_ATTACK_COLORS = {
    "acoc1": (150, 80, 255),   # Shadow Wraith — purple
    "acoc2": (80, 140, 220),   # Flame Knight — blue
    "acoc3": (200, 100, 180),  # Goblin Mage — pink
    "acoc4": (200, 60, 60),    # Nightfang — red
    "acoc5": (80, 180, 80),    # Briarfoot — green
}


class RealtimeBattle:
    def __init__(self, player_units: list[CombatUnit],
                 enemy_units: list[CombatUnit],
                 ability_registry: AbilityRegistry,
                 player_controlled_id: str = "",
                 asset_manager=None):
        self.player_units = player_units
        self.enemy_units = enemy_units
        self.ability_registry = ability_registry
        self.player_controlled_id = player_controlled_id
        self.asset_manager = asset_manager
        self.projectiles: list[Projectile] = []
        self.result: str | None = None
        self._actions: list[BattleAction] = []

    @property
    def all_units(self) -> list[CombatUnit]:
        return self.player_units + self.enemy_units

    def update(self, dt: float) -> list[BattleAction]:
        """Main per-frame update. Returns actions generated this frame."""
        if self.result is not None:
            return []

        self._actions = []

        # Tick all units
        for unit in self.all_units:
            if not unit.alive:
                continue
            unit.time_alive += dt
            unit.tick_cooldowns_rt(dt)

            # Tick buffs (burn damage, stun expiry)
            burn_dmg = unit.tick_buffs_rt(dt)
            if burn_dmg > 0:
                unit.take_damage(burn_dmg)
                self._actions.append(BattleAction(
                    type="burn_tick", target=unit.name,
                    damage=burn_dmg,
                    message=f"{unit.name} takes {burn_dmg} burn damage!",
                ))
                if not unit.alive:
                    self._actions.append(BattleAction(
                        type="defeat", target=unit.name,
                        message=f"{unit.name} has been defeated!",
                    ))
                    self._check_result()

            if unit.is_stunned:
                continue

            # Auto-attack timer (skip for player-controlled unit — they auto-attack too)
            unit.attack_timer += dt
            if unit.attack_timer >= unit.attack_interval:
                unit.attack_timer -= unit.attack_interval
                self._spawn_auto_attack(unit)

        # Update projectiles
        for proj in self.projectiles:
            proj.update(dt)

        # Check collisions
        self._check_collisions()

        # Remove dead projectiles
        self.projectiles = [p for p in self.projectiles if p.alive]

        # Check result
        self._check_result()

        return self._actions

    def fire_ability(self, unit: CombatUnit, ability_id: str) -> bool:
        """Fire an ability from a unit. Returns True if fired successfully."""
        if not unit.alive or unit.is_stunned:
            return False
        if not unit.can_use_ability(ability_id):
            return False

        ability = self.ability_registry.get(ability_id)
        if not ability:
            return False

        enemies = self.enemy_units if unit.team == "player" else self.player_units
        allies = self.player_units if unit.team == "player" else self.enemy_units

        # Handle self-targeting abilities (summon, buffs)
        if ability.targeting == "self":
            self._execute_self_ability(unit, ability)
            unit.put_on_cooldown(ability_id, ability.cooldown)
            return True

        # Spawn ability projectile
        targets = get_targets(ability.targeting, unit, allies, enemies)
        if not targets:
            return False

        self._spawn_ability_projectile(unit, ability, targets[0])
        unit.put_on_cooldown(ability_id, ability.cooldown)
        return True

    def _spawn_auto_attack(self, unit: CombatUnit):
        """Spawn an auto-attack projectile from a unit."""
        enemies = self.enemy_units if unit.team == "player" else self.player_units
        target = get_nearest_enemy(unit, enemies)
        if not target:
            return

        direction = 1 if unit.team == "player" else -1
        damage = self._calc_auto_damage(unit)
        color = CLASS_ATTACK_COLORS.get(unit.id, (200, 180, 120))

        sprite_path = CLASS_ATTACK_SPRITES.get(unit.id, "")
        size = (20, 20) if sprite_path else (12, 6)

        sprite_surf = None
        if sprite_path and self.asset_manager:
            try:
                sprite_surf = self.asset_manager.get_scaled(sprite_path, size[0], size[1])
                if direction == -1:
                    sprite_surf = pygame.transform.flip(sprite_surf, True, False)
            except Exception:
                pass

        # Boss spread attack: fire 3 projectiles with vertical spread
        is_boss = getattr(unit, '_is_boss', False)
        offsets = [0, -40, 40] if is_boss else [0]

        for y_offset in offsets:
            proj = Projectile(
                x=unit.x + direction * 40,
                y=unit.y + y_offset,
                direction=direction,
                speed=PROJECTILE_BASE_SPEED,
                damage=damage,
                source_name=unit.name,
                team=unit.team,
                color=color,
                size=size,
                sprite=sprite_surf,
            )
            proj.ability_mods = list(unit.ability_mods)
            proj.passive = unit.passive
            self.projectiles.append(proj)

        self._actions.append(BattleAction(
            type="attack", source=unit.name,
            message=f"{unit.name} fires!",
        ))

    def _spawn_ability_projectile(self, unit: CombatUnit, ability: AbilityDef,
                                  target: CombatUnit):
        """Spawn a projectile for an ability."""
        direction = 1 if unit.team == "player" else -1
        damage = self._calc_ability_damage(unit, ability)

        # Use ability projectile config or defaults
        pc = ability.projectile
        speed = pc.speed if pc else PROJECTILE_ABILITY_SPEED
        size = (pc.size_w, pc.size_h) if pc else (20, 12)
        color = pc.color if pc else (255, 200, 80)
        is_aoe = pc.is_aoe if pc else (ability.targeting == "all_enemies")

        sprite_surf = None
        if pc and pc.sprite and self.asset_manager:
            try:
                sprite_surf = self.asset_manager.get_scaled(pc.sprite, size[0], size[1])
                if direction == -1:
                    sprite_surf = pygame.transform.flip(sprite_surf, True, False)
            except Exception:
                pass

        proj = Projectile(
            x=unit.x + direction * 40,
            y=unit.y,
            direction=direction,
            speed=speed,
            damage=damage,
            source_name=unit.name,
            team=unit.team,
            ability_name=ability.name,
            color=color,
            size=size,
            sprite=sprite_surf,
        )
        proj.ability_mods = list(unit.ability_mods)
        proj.passive = unit.passive
        proj.is_aoe = is_aoe
        # Store effects for application on hit
        proj._ability_effects = ability.effects
        self.projectiles.append(proj)

        self._actions.append(BattleAction(
            type="ability", source=unit.name,
            ability_name=ability.name,
            message=f"{unit.name} uses {ability.name}!",
        ))

    def _execute_self_ability(self, unit: CombatUnit, ability: AbilityDef):
        """Handle self-targeting abilities (summon, buffs)."""
        for effect in ability.effects:
            if effect.type == "summon":
                self._actions.append(BattleAction(
                    type="summon", source=unit.name,
                    target=effect.enemy_id,
                    damage=effect.value,
                    message=f"{unit.name} summons reinforcements!",
                ))
        self._actions.append(BattleAction(
            type="ability", source=unit.name, target=unit.name,
            ability_name=ability.name,
            message=f"{unit.name} uses {ability.name}!",
        ))

    def _check_collisions(self):
        """Check projectile-unit collisions."""
        for proj in self.projectiles:
            if not proj.alive:
                continue

            # Determine targets (opposing team)
            targets = self.enemy_units if proj.team == "player" else self.player_units
            hit_units = []

            for unit in targets:
                if not unit.alive:
                    continue
                if proj.hits(unit.unit_rect):
                    hit_units.append(unit)
                    if not proj.is_aoe:
                        break  # single-target stops at first hit

            for unit in hit_units:
                self._apply_hit(proj, unit)

            if hit_units and not proj.is_aoe:
                proj.alive = False
            elif hit_units and proj.is_aoe:
                proj.alive = False  # AoE also consumed, but hit everyone in path

    def _apply_hit(self, proj: Projectile, target: CombatUnit):
        """Apply projectile damage to a target unit."""
        # Phase passive: 25% dodge
        if target.passive == "phase" and random.random() < 0.25:
            self._actions.append(BattleAction(
                type="dodge", source=proj.source_name, target=target.name,
                ability_name=proj.ability_name,
                message=f"{target.name} phases through the attack!",
            ))
            return

        # Apply armor reduction to damage
        effective_armor = target.armor
        if "piercing" in proj.ability_mods:
            effective_armor = int(effective_armor * 0.5)
        final_damage = max(1, proj.damage - int(effective_armor * DAMAGE_ARMOR_FACTOR))
        actual = target.take_damage(final_damage)

        # Find source unit for reflect/vampiric
        source_unit = self._find_unit(proj.source_name)

        # Flame aura reflect
        reflect_damage = 0
        if target.passive == "flame_aura" and actual > 0 and source_unit:
            reflect_damage = max(1, int(actual * 0.2))
            source_unit.take_damage(reflect_damage)

        # Vampiric mod
        heal = 0
        if "vampiric" in proj.ability_mods and actual > 0 and source_unit:
            heal = max(1, int(actual * 0.2))
            source_unit.hp = min(source_unit.max_hp, source_unit.hp + heal)

        action_type = "hit"
        msg = f"{proj.source_name} hits {target.name} for {actual} damage!"
        if proj.ability_name:
            msg = f"{proj.ability_name} hits {target.name} for {actual} damage!"

        self._actions.append(BattleAction(
            type=action_type, source=proj.source_name, target=target.name,
            ability_name=proj.ability_name, damage=actual, heal=heal,
            message=msg,
        ))

        if reflect_damage > 0:
            self._actions.append(BattleAction(
                type="reflect", source=target.name, target=proj.source_name,
                damage=reflect_damage,
                message=f"{target.name}'s Flame Aura reflects {reflect_damage} damage!",
            ))

        # Apply ability effects on hit
        if hasattr(proj, '_ability_effects'):
            for effect in proj._ability_effects:
                if effect.type == "stun":
                    target.add_buff("stun", effect.duration + 1)
                    self._actions.append(BattleAction(
                        type="stun_applied", source=proj.source_name,
                        target=target.name,
                        message=f"{target.name} is stunned for {effect.duration}s!",
                    ))

        # Burning mod
        if "burning" in proj.ability_mods:
            target.add_buff("burn", 3, value=3)
            self._actions.append(BattleAction(
                type="burn_applied", source=proj.source_name,
                target=target.name,
                message=f"{target.name} is burning!",
            ))

        # Check defeat
        if not target.alive:
            self._actions.append(BattleAction(
                type="defeat", target=target.name,
                message=f"{target.name} has been defeated!",
            ))

        if source_unit and not source_unit.alive:
            self._actions.append(BattleAction(
                type="defeat", target=source_unit.name,
                message=f"{source_unit.name} has been defeated!",
            ))

    def _calc_auto_damage(self, unit: CombatUnit) -> int:
        """Calculate auto-attack damage (no armor applied here — applied on hit)."""
        raw = max(1, unit.strength)
        # Rage passive
        if unit.passive == "rage" and unit.hp < unit.max_hp * 0.5:
            raw = int(raw * 1.25)
        return raw

    def _calc_ability_damage(self, unit: CombatUnit, ability: AbilityDef) -> int:
        """Calculate ability damage (before armor)."""
        raw = ability.base_damage + int(unit.strength * ability.scaling)
        # Piercing mod reduces armor effect — handled on hit
        # Mana surge passive: +10% per 5 seconds alive
        if unit.passive == "mana_surge":
            bonus = 1.0 + 0.1 * int(unit.time_alive / 5.0)
            raw = int(raw * bonus)
        # Rage passive
        if unit.passive == "rage" and unit.hp < unit.max_hp * 0.5:
            raw = int(raw * 1.25)
        return raw

    def _find_unit(self, name: str) -> CombatUnit | None:
        for u in self.all_units:
            if u.name == name:
                return u
        return None

    def _check_result(self) -> str | None:
        if self.result:
            return self.result
        players_alive = any(u.alive for u in self.player_units)
        enemies_alive = any(u.alive for u in self.enemy_units)
        if not enemies_alive:
            self.result = "victory"
            self._actions.append(BattleAction(
                type="victory", message="Victory!"))
            return "victory"
        if not players_alive:
            self.result = "lose"
            self._actions.append(BattleAction(
                type="lose", message="Defeat..."))
            return "lose"
        return None

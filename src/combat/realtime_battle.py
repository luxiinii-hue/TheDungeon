"""ATB (Active Time Battle) lane combat engine."""

import random
from dataclasses import dataclass
from src.combat.unit import CombatUnit
from src.combat.ability import AbilityRegistry, AbilityDef
from src.combat.targeting import get_auto_attack_target, get_targets
from src.combat.projectile import Projectile
from config import (
    PROJECTILE_TRAVEL_SPEED, PROJECTILE_ABILITY_SPEED,
    DAMAGE_ARMOR_FACTOR, CLASS_ATTACK_SPRITES,
    PLAYER_RANK_X, ENEMY_RANK_X, COMBAT_Y_CENTER, RANK_Y_STAGGER,
)


@dataclass
class BattleAction:
    """Event emitted by the battle engine for the UI to consume."""
    type: str  # "attack", "ability", "hit", "dodge", "defeat", "victory",
               # "lose", "burn_tick", "stun_applied", "reflect", "summon",
               # "rank_slide"
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


def rank_to_pos(rank: int, team: str) -> tuple[float, float]:
    """Convert a rank (1-4) and team to screen x,y coordinates."""
    if team == "player":
        x = PLAYER_RANK_X[min(rank, len(PLAYER_RANK_X) - 1)]
    else:
        x = ENEMY_RANK_X[min(rank, len(ENEMY_RANK_X) - 1)]
    y = COMBAT_Y_CENTER + (rank - 1) * RANK_Y_STAGGER
    return float(x), float(y)


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

        # Assign sequential ranks and set initial positions
        self._assign_ranks(self.player_units)
        self._assign_ranks(self.enemy_units)
        self._sync_positions()

    @property
    def all_units(self) -> list[CombatUnit]:
        return self.player_units + self.enemy_units

    def _assign_ranks(self, units: list[CombatUnit]):
        """Assign sequential ranks 1..N to alive units, sorted by default_rank."""
        alive = [u for u in units if u.alive]
        alive.sort(key=lambda u: u.rank)
        for i, u in enumerate(alive):
            u.rank = i + 1

    def _sync_positions(self):
        """Set unit x,y from their rank."""
        for unit in self.all_units:
            unit.x, unit.y = rank_to_pos(unit.rank, unit.team)

    def _slide_ranks(self, team_units: list[CombatUnit]):
        """After a death, slide surviving units forward (close rank gaps)."""
        alive = [u for u in team_units if u.alive]
        alive.sort(key=lambda u: u.rank)
        changed = False
        for i, u in enumerate(alive):
            new_rank = i + 1
            if u.rank != new_rank:
                old_rank = u.rank
                u.rank = new_rank
                u.x, u.y = rank_to_pos(new_rank, u.team)
                self._actions.append(BattleAction(
                    type="rank_slide", target=u.name,
                    message=f"{u.name} moves to rank {new_rank}",
                ))
                changed = True
        return changed

    def update(self, dt: float) -> list[BattleAction]:
        """Main per-frame ATB tick. Returns actions generated this frame."""
        if self.result is not None:
            return []

        self._actions = []

        # Tick all living units
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
                    self._handle_death(unit)

            # ATB speed bar tick
            if unit.alive and unit.tick_speed_bar(dt):
                self._spawn_auto_attack(unit)

        # Update projectiles and check arrivals
        for proj in self.projectiles:
            if not proj.alive:
                continue
            proj.update(dt)
            if proj.arrived:
                self._apply_projectile_hit(proj)
                proj.alive = False

        # Remove dead projectiles
        self.projectiles = [p for p in self.projectiles if p.alive]

        # Check win/lose
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

        # Get targets based on rank targeting
        targets = get_targets(ability.targeting, unit, allies, enemies,
                              ability_range=ability.range)
        if not targets:
            return False

        # Handle support abilities that don't spawn projectiles
        if ability.targeting in ("single_ally", "all_allies"):
            self._execute_support_ability(unit, ability, targets)
            unit.put_on_cooldown(ability_id, ability.cooldown)
            return True

        # Spawn ability projectile(s)
        if ability.targeting == "all_enemies":
            # AoE: one projectile that hits all
            self._spawn_ability_projectile(unit, ability, targets[0], is_aoe=True)
        elif ability.targeting == "front_two":
            # Hits ranks 1 and 2 — spawn one projectile per target
            for t in targets:
                self._spawn_ability_projectile(unit, ability, t)
        else:
            self._spawn_ability_projectile(unit, ability, targets[0])

        unit.put_on_cooldown(ability_id, ability.cooldown)
        return True

    def _spawn_auto_attack(self, unit: CombatUnit):
        """Spawn an auto-attack projectile from a unit."""
        enemies = self.enemy_units if unit.team == "player" else self.player_units
        target = get_auto_attack_target(unit, enemies)
        if not target:
            return

        damage = self._calc_auto_damage(unit)
        color = CLASS_ATTACK_COLORS.get(unit.id, (200, 180, 120))

        sprite_path = CLASS_ATTACK_SPRITES.get(unit.id, "")
        size = (20, 20) if sprite_path else (12, 6)

        sprite_surf = None
        if sprite_path and self.asset_manager:
            try:
                sprite_surf = self.asset_manager.get_scaled(sprite_path, size[0], size[1])
                if unit.team == "enemy":
                    import pygame
                    sprite_surf = pygame.transform.flip(sprite_surf, True, False)
            except Exception:
                pass

        proj = Projectile(
            x=unit.x, y=unit.y,
            target_x=target.x, target_y=target.y,
            speed=PROJECTILE_TRAVEL_SPEED,
            damage=damage,
            source_name=unit.name,
            team=unit.team,
            color=color,
            size=size,
            sprite=sprite_surf,
        )
        proj.ability_mods = list(unit.ability_mods)
        proj.passive = unit.passive
        proj.target_name = target.name
        self.projectiles.append(proj)

        self._actions.append(BattleAction(
            type="attack", source=unit.name,
            message=f"{unit.name} fires!",
        ))

    def _spawn_ability_projectile(self, unit: CombatUnit, ability: AbilityDef,
                                  target: CombatUnit, is_aoe: bool = False):
        """Spawn a projectile for an ability."""
        damage = self._calc_ability_damage(unit, ability)

        pc = ability.projectile
        speed = pc.speed if pc else PROJECTILE_ABILITY_SPEED
        size = (pc.size_w, pc.size_h) if pc else (20, 12)
        color = pc.color if pc else (255, 200, 80)

        sprite_surf = None
        if pc and pc.sprite and self.asset_manager:
            try:
                sprite_surf = self.asset_manager.get_scaled(pc.sprite, size[0], size[1])
                if unit.team == "enemy":
                    import pygame
                    sprite_surf = pygame.transform.flip(sprite_surf, True, False)
            except Exception:
                pass

        proj = Projectile(
            x=unit.x, y=unit.y,
            target_x=target.x, target_y=target.y,
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
        proj.target_name = target.name
        proj._ability_effects = ability.effects
        self.projectiles.append(proj)

        self._actions.append(BattleAction(
            type="ability", source=unit.name,
            ability_name=ability.name,
            message=f"{unit.name} uses {ability.name}!",
        ))

    def _execute_self_ability(self, unit: CombatUnit, ability: AbilityDef):
        """Handle self-targeting abilities (summon, buffs, self_move)."""
        for effect in ability.effects:
            if effect.type == "summon":
                self._actions.append(BattleAction(
                    type="summon", source=unit.name,
                    target=effect.enemy_id,
                    damage=effect.value,
                    message=f"{unit.name} summons reinforcements!",
                ))
            elif effect.type == "self_move":
                self._apply_position_effect(unit, unit, effect.type, effect.value)
        self._actions.append(BattleAction(
            type="ability", source=unit.name, target=unit.name,
            ability_name=ability.name,
            message=f"{unit.name} uses {ability.name}!",
        ))

    def _execute_support_ability(self, unit: CombatUnit, ability: AbilityDef,
                                  targets: list[CombatUnit]):
        """Handle ally-targeting support abilities (block, heals)."""
        for target in targets:
            for effect in ability.effects:
                if effect.type == "block":
                    target.block += effect.value
                    self._actions.append(BattleAction(
                        type="hit", source=unit.name, target=target.name,
                        ability_name=ability.name,
                        message=f"{target.name} gains {effect.value} block!",
                    ))
                elif effect.type == "heal":
                    healed = min(effect.value, target.max_hp - target.hp)
                    target.hp += healed
                    self._actions.append(BattleAction(
                        type="hit", source=unit.name, target=target.name,
                        ability_name=ability.name, heal=healed,
                        message=f"{target.name} healed for {healed}!",
                    ))
        self._actions.append(BattleAction(
            type="ability", source=unit.name,
            ability_name=ability.name,
            message=f"{unit.name} uses {ability.name}!",
        ))

    def _apply_position_effect(self, source: CombatUnit, target: CombatUnit,
                                effect_type: str, value: int):
        """Handle push, pull, and self_move rank changes."""
        team_units = (self.player_units if target.team == "player"
                      else self.enemy_units)
        alive = [u for u in team_units if u.alive]
        max_rank = len(alive)

        if effect_type == "push":
            new_rank = min(max_rank, target.rank + value)
        elif effect_type == "pull":
            new_rank = max(1, target.rank - value)
        elif effect_type == "self_move":
            # Positive = forward (lower rank), negative = backward
            new_rank = max(1, min(max_rank, target.rank - value))
        else:
            return

        if new_rank == target.rank:
            return

        # Find unit currently at the destination rank and swap
        occupant = next((u for u in alive if u.rank == new_rank), None)
        old_rank = target.rank
        if occupant and occupant != target:
            occupant.rank = old_rank
            occupant.x, occupant.y = rank_to_pos(old_rank, occupant.team)
            self._actions.append(BattleAction(
                type="rank_slide", target=occupant.name,
                message=f"{occupant.name} swaps to rank {old_rank}",
            ))

        target.rank = new_rank
        target.x, target.y = rank_to_pos(new_rank, target.team)
        direction = "forward" if new_rank < old_rank else "back"
        self._actions.append(BattleAction(
            type="rank_slide", target=target.name,
            message=f"{target.name} pushed {direction} to rank {new_rank}",
        ))

    def _apply_projectile_hit(self, proj: Projectile):
        """Apply damage when a projectile arrives at its target."""
        if proj.is_aoe:
            # Hit all alive enemies on the opposing team
            targets = self.enemy_units if proj.team == "player" else self.player_units
            for target in targets:
                if target.alive:
                    self._apply_hit(proj, target)
        else:
            # Hit the named target (if still alive)
            target = self._find_unit(proj.target_name)
            if target and target.alive:
                self._apply_hit(proj, target)
            else:
                # Target died in transit — hit front-most enemy instead
                enemies = self.enemy_units if proj.team == "player" else self.player_units
                alive = [u for u in enemies if u.alive]
                if alive:
                    fallback = min(alive, key=lambda u: u.rank)
                    self._apply_hit(proj, fallback)

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

        # Apply armor reduction
        effective_armor = target.armor
        has_pierce = "piercing" in proj.ability_mods
        if hasattr(proj, '_ability_effects'):
            if any(e.type == "armor_pierce" for e in proj._ability_effects):
                has_pierce = True
        if has_pierce:
            effective_armor = int(effective_armor * 0.5)
        final_damage = max(1, proj.damage - int(effective_armor * DAMAGE_ARMOR_FACTOR))
        actual = target.take_damage(final_damage)

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

        msg = f"{proj.source_name} hits {target.name} for {actual} damage!"
        if proj.ability_name:
            msg = f"{proj.ability_name} hits {target.name} for {actual} damage!"

        self._actions.append(BattleAction(
            type="hit", source=proj.source_name, target=target.name,
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
                elif effect.type in ("push", "pull"):
                    self._apply_position_effect(
                        self._find_unit(proj.source_name) or target,
                        target, effect.type, effect.value)
                elif effect.type == "atb_delay":
                    target.reduce_atb(effect.value)
                    self._actions.append(BattleAction(
                        type="hit", source=proj.source_name,
                        target=target.name,
                        message=f"{target.name}'s speed bar reduced!",
                    ))
                elif effect.type == "armor_pierce":
                    pass  # Handled via proj flag below

        # Burning mod
        if "burning" in proj.ability_mods:
            target.add_buff("burn", 3, value=3)
            self._actions.append(BattleAction(
                type="burn_applied", source=proj.source_name,
                target=target.name,
                message=f"{target.name} is burning!",
            ))

        # Check defeats
        if not target.alive:
            self._actions.append(BattleAction(
                type="defeat", target=target.name,
                message=f"{target.name} has been defeated!",
            ))
            self._handle_death(target)

        if source_unit and not source_unit.alive:
            self._actions.append(BattleAction(
                type="defeat", target=source_unit.name,
                message=f"{source_unit.name} has been defeated!",
            ))
            self._handle_death(source_unit)

    def _handle_death(self, unit: CombatUnit):
        """Handle rank sliding when a unit dies."""
        if unit.team == "player":
            self._slide_ranks(self.player_units)
        else:
            self._slide_ranks(self.enemy_units)
        self._check_result()

    def _calc_auto_damage(self, unit: CombatUnit) -> int:
        """Calculate auto-attack damage (before armor — applied on hit)."""
        raw = max(1, unit.strength)
        if unit.passive == "rage" and unit.hp < unit.max_hp * 0.5:
            raw = int(raw * 1.25)
        return raw

    def _calc_ability_damage(self, unit: CombatUnit, ability: AbilityDef) -> int:
        """Calculate ability damage (before armor)."""
        raw = ability.base_damage + int(unit.strength * ability.scaling)
        if unit.passive == "mana_surge":
            bonus = 1.0 + 0.1 * int(unit.time_alive / 5.0)
            raw = int(raw * bonus)
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

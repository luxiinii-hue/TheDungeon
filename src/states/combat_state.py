"""ATB lane combat state."""

import random
import pygame
from src.states.base_state import BaseState
from src.core.state_machine import GameState
from src.entities.enemy import EnemyData
from src.combat.ability import AbilityRegistry
from src.combat.unit import CombatUnit
from src.combat.realtime_battle import RealtimeBattle, BattleAction, rank_to_pos
from src.combat.ai_controller import AIController
from src.animation.idle_animator import IdleAnimator
from src.animation.combat_animator import CombatAnimator
from src.animation.particles import (
    ParticleEmitter, ABILITY_PARTICLES,
    spawn_hit_sparks, spawn_death_burst,
)
from src.animation.ability_animator import AbilityAnimator
from src.ui.health_bar import draw_health_bar
from src.ui.text_renderer import draw_text
from src.ui.ability_hud import AbilityHUD
from src.ui.speed_bar import draw_speed_bar
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GRAY, GOLD, RED, BLUE, GREEN,
    DARK_GRAY, PANEL_BG, PANEL_BORDER, ORANGE, PURPLE, CYAN,
    FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE,
    PLAYER_RANK_X, ENEMY_RANK_X, COMBAT_Y_CENTER, RANK_Y_STAGGER,
    CLASS_COLORS,
)


# Map character roles to class names for speed bar coloring
ROLE_TO_CLASS = {
    "warlock": "warlock", "paladin": "paladin", "sorcerer": "sorcerer",
    "barbarian": "barbarian", "ranger": "ranger",
}


class CombatScreenState(BaseState):
    def enter(self, **kwargs):
        self.tier = kwargs.get("tier", "normal")
        self.difficulty = kwargs.get("difficulty", 1)
        am = self.game.asset_manager
        run = self.game.run_manager

        # Load ability registry
        self.ability_registry = AbilityRegistry()
        self.ability_registry.load(am.load_json("abilities.json"))

        # Create player combat units (sorted by default_rank)
        self.player_units: list[CombatUnit] = []
        self.player_animators: dict[str, IdleAnimator] = {}
        self.player_roles: dict[str, str] = {}  # unit_id -> role for class color

        alive_team = run.get_alive_team()
        for char in alive_team:
            hp_override = run.team_hp[char.id]
            unit = CombatUnit.from_character(
                char,
                ability_mods=run.ability_mods.get(char.id, []),
                stat_boosts=run.stat_boosts.get(char.id, {}),
                unlocked_abilities=run.unlocked_abilities.get(char.id, []),
            )
            unit.hp = hp_override
            unit.max_hp = run.team_max_hp[char.id]
            self.player_units.append(unit)
            self.player_roles[unit.id] = getattr(char, 'role', 'warlock')

            # Create idle animator
            img = am.load_image(char.sprite)
            sprite_h = 100
            aspect = img.get_width() / img.get_height()
            sprite_w = int(sprite_h * aspect)
            scaled = am.get_scaled(char.sprite, sprite_w, sprite_h)
            self.player_animators[unit.id] = IdleAnimator(scaled, char.idle_config)

        # Sort by default_rank so front-liners are rank 1
        self.player_units.sort(key=lambda u: u.rank)

        # Player-controlled unit is the first one
        self.player_controlled = self.player_units[0] if self.player_units else None
        player_id = self.player_controlled.id if self.player_controlled else ""

        # Load and create enemy units
        enemies_data = am.load_json("enemies.json")
        all_enemies = [EnemyData.from_dict(e) for e in enemies_data]

        # Build template lookup for engine-side summoning
        enemy_templates = {e.id: e for e in all_enemies}

        tier_enemies = [e for e in all_enemies if e.tier == self.tier]
        if not tier_enemies:
            tier_enemies = [e for e in all_enemies if e.tier == "normal"]

        num_enemies = min(3, max(1, self.difficulty))
        if self.tier == "boss":
            num_enemies = 1
            tier_enemies = [e for e in all_enemies if e.tier == "boss"]
            if not tier_enemies:
                tier_enemies = [e for e in all_enemies if e.tier == "elite"]

        chosen = [random.choice(tier_enemies) for _ in range(num_enemies)]

        self.enemy_units: list[CombatUnit] = []
        self.enemy_data = chosen
        self.enemy_animators: dict[str, IdleAnimator | None] = {}

        for i, edata in enumerate(chosen):
            unit = CombatUnit.from_enemy(edata)
            unit.rank = i + 1  # sequential ranks
            self.enemy_units.append(unit)

            if edata.sprite:
                img = am.load_image(edata.sprite)
                sprite_h = 100
                if edata.tier == "boss":
                    sprite_h = 130
                aspect = img.get_width() / img.get_height()
                sprite_w = int(sprite_h * aspect)
                scaled = am.get_scaled(edata.sprite, sprite_w, sprite_h)
                self.enemy_animators[unit.name] = IdleAnimator(scaled, edata.idle_config)
            else:
                self.enemy_animators[unit.name] = None

        # Apply relic: start_block
        for relic in run.relics:
            if relic.get("effect") == "start_block":
                for unit in self.player_units:
                    unit.block += int(relic.get("value", 0))

        # ATB battle engine
        self.battle = RealtimeBattle(
            self.player_units, self.enemy_units,
            self.ability_registry, player_id,
            asset_manager=am,
            enemy_templates=enemy_templates,
        )

        # AI controller
        self.ai = AIController(self.battle, self.ability_registry)

        # Animation systems
        self.combat_animator = CombatAnimator()
        self.particle_emitter = ParticleEmitter()
        self.ability_animator = AbilityAnimator()

        # HUD
        self.ability_hud = AbilityHUD(am)

        # Action log
        self.action_log: list[tuple[str, float]] = []
        self.max_log_lines = 5

        # End state
        self.end_delay = 0.0
        self.transitioning = False
        self.paused = False

        # Tracking for position tweening
        self.previous_positions: dict[str, tuple[float, float]] = {}
        for unit in self.player_units + self.enemy_units:
            self.previous_positions[unit.name] = (unit.x, unit.y)

        # Gothic city background: stairs for boss, street for normal/elite
        if self.tier == "boss":
            self.bg_filename = "Backgrounds/gothic_city/gothic_stairs.png"
        else:
            self.bg_filename = "Backgrounds/gothic_city/gothic_street.png"

    def update(self, dt: float):
        if self.paused:
            return
        # Update idle animators
        for animator in self.player_animators.values():
            animator.update(dt)
        for animator in self.enemy_animators.values():
            if animator:
                animator.update(dt)
        self.combat_animator.update(dt)
        self.particle_emitter.update(dt)
        self.ability_animator.update(dt)

        # Age action log
        self.action_log = [(m, a + dt) for m, a in self.action_log if a + dt < 6.0]

        # Handle end transition
        if self.transitioning:
            self.end_delay -= dt
            if self.end_delay <= 0:
                run = self.game.run_manager
                if self.battle.result == "victory":
                    hp_map = {u.id: u.hp for u in self.player_units}
                    run.update_hp_after_combat(hp_map)
                    total_gold = sum(e.gold_reward for e in self.enemy_data)
                    run.gold += total_gold
                    run.enemies_defeated += len(self.enemy_data)
                    if self.tier == "boss":
                        self.game.state_machine.transition(
                            GameState.RESULT, result="win")
                    else:
                        self.game.state_machine.transition(GameState.REWARD)
                else:
                    self.game.state_machine.transition(
                        GameState.RESULT, result="lose")
            return

        if self.battle.result and not self.transitioning:
            self.transitioning = True
            self.end_delay = 2.0
            return

        # AI ability usage
        self.ai.update(dt, self.player_controlled)

        # ATB battle engine update
        actions = self.battle.update(dt)
        for action in actions:
            self._process_action(action)

        # Trigger slides for rank changes
        for unit in self.player_units + self.enemy_units:
            if unit.name in self.previous_positions:
                old_x, old_y = self.previous_positions[unit.name]
                if old_x != unit.x or old_y != unit.y:
                    dx = old_x - unit.x
                    dy = old_y - unit.y
                    self.combat_animator.add_slide_offset(unit.name, dx, dy, 0.3)
            self.previous_positions[unit.name] = (unit.x, unit.y)

        # Projectile trails
        from src.animation.particles import spawn_projectile_trail
        for proj in self.battle.projectiles:
            if random.random() < 0.4:
                spawn_projectile_trail(self.particle_emitter, proj.x, proj.y, proj.color)

    def _process_action(self, action: BattleAction):
        """Trigger visual effects based on battle actions."""
        if action.message:
            self.action_log.append((action.message, 0.0))
            if len(self.action_log) > self.max_log_lines:
                self.action_log = self.action_log[-self.max_log_lines:]

        if action.type == "hit" and action.damage > 0:
            target_unit = self._find_unit(action.target)
            if target_unit:
                tx, ty = target_unit.x, target_unit.y
                self.combat_animator.add_shake(action.target, intensity=3, duration=0.15)
                self.combat_animator.add_flash(action.target, color=(255, 255, 200), duration=0.1)

                if action.ability_name and action.ability_name in ABILITY_PARTICLES:
                    ABILITY_PARTICLES[action.ability_name](self.particle_emitter, tx, ty)
                else:
                    spawn_hit_sparks(self.particle_emitter, tx, ty)

                if action.ability_name:
                    ability_def = self.ability_registry.get_by_name(action.ability_name)
                    if ability_def and ability_def.animation:
                        self.ability_animator.spawn_from_config(tx, ty, ability_def.animation)

                self.particle_emitter.add_floating_number(
                    tx, ty - 40, str(action.damage), (255, 80, 80))

            if action.heal > 0:
                source_unit = self._find_unit(action.source)
                if source_unit:
                    self.particle_emitter.add_floating_number(
                        source_unit.x, source_unit.y - 40,
                        f"+{action.heal}", (80, 255, 80))

        elif action.type == "defeat":
            target_unit = self._find_unit(action.target)
            if target_unit:
                self.combat_animator.add_flash(action.target, color=(255, 0, 0), duration=0.4)
                spawn_death_burst(self.particle_emitter, target_unit.x, target_unit.y)

        elif action.type == "dodge":
            target_unit = self._find_unit(action.target)
            if target_unit:
                self.combat_animator.add_flash(action.target, color=(100, 200, 255), duration=0.2)
                self.particle_emitter.add_floating_number(
                    target_unit.x, target_unit.y - 40, "DODGE", (100, 200, 255))

        elif action.type == "reflect":
            target_unit = self._find_unit(action.target)
            if target_unit:
                self.particle_emitter.add_floating_number(
                    target_unit.x, target_unit.y - 40,
                    str(action.damage), (255, 150, 50))

        elif action.type == "summon":
            self._handle_summon(action)

    def _handle_summon(self, action: BattleAction):
        """Create visual representation for a unit summoned by the engine."""
        unit_name = action.target
        # Find the new unit in the engine's enemy list
        new_unit = None
        for u in self.battle.enemy_units:
            if u.name == unit_name:
                new_unit = u
                break
        if not new_unit:
            return

        # Track in our local lists if not already present
        if new_unit not in self.enemy_units:
            self.enemy_units.append(new_unit)

        # Get sprite info from stashed enemy data
        edata = getattr(new_unit, '_summon_edata', None)
        if edata and edata not in self.enemy_data:
            self.enemy_data.append(edata)

        # Create animator if we don't have one yet
        if unit_name not in self.enemy_animators:
            if edata and edata.sprite:
                am = self.game.asset_manager
                img = am.load_image(edata.sprite)
                sprite_h = 100
                aspect = img.get_width() / img.get_height()
                sprite_w = int(sprite_h * aspect)
                scaled = am.get_scaled(edata.sprite, sprite_w, sprite_h)
                self.enemy_animators[unit_name] = IdleAnimator(
                    scaled, edata.idle_config)
            else:
                self.enemy_animators[unit_name] = None

        # Spawn entry particles at the new unit's position (purple burst)
        spawn_death_burst(self.particle_emitter, new_unit.x, new_unit.y, color=(200, 80, 255))

        # Track position for slide animation
        self.previous_positions[unit_name] = (new_unit.x, new_unit.y)

    def _find_unit(self, name: str) -> CombatUnit | None:
        for u in self.player_units + self.enemy_units:
            if u.name == name:
                return u
        return None

    def _get_bg(self) -> pygame.Surface:
        if not hasattr(self, "_bg_cache"):
            bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            try:
                # Load the randomly chosen gothic city background
                bg = self.game.asset_manager.get_scaled(
                    self.bg_filename, SCREEN_WIDTH, SCREEN_HEIGHT)
            except Exception as e:
                print(f"Error loading background {self.bg_filename}: {e}")
                # Procedural Darkest Dungeon style corridor fallback
                bg.fill((15, 10, 15))
                pygame.draw.polygon(bg, (25, 20, 25), [
                    (0, COMBAT_Y_CENTER + 80),
                    (SCREEN_WIDTH, COMBAT_Y_CENTER + 80),
                    (SCREEN_WIDTH, SCREEN_HEIGHT),
                    (0, SCREEN_HEIGHT)
                ])
                pygame.draw.rect(bg, (10, 5, 10), (0, 0, SCREEN_WIDTH, COMBAT_Y_CENTER + 80))
                for x in range(100, SCREEN_WIDTH, 300):
                    pygame.draw.rect(bg, (20, 15, 20), (x, 50, 40, COMBAT_Y_CENTER + 30))
                    # Torches
                    pygame.draw.circle(bg, (255, 150, 50), (x + 20, COMBAT_Y_CENTER - 100), 15)
                    pygame.draw.circle(bg, (255, 200, 100), (x + 20, COMBAT_Y_CENTER - 100), 8)

            ground_shadow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(ground_shadow, (10, 15, 25, 120),
                             (0, COMBAT_Y_CENTER + 80, SCREEN_WIDTH, SCREEN_HEIGHT))
            bg.blit(ground_shadow, (0, 0))
            dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            dark.fill((10, 10, 20, 60))
            bg.blit(dark, (0, 0))
            self._bg_cache = bg
        return self._bg_cache

    def draw(self, surface: pygame.Surface):
        surface.blit(self._get_bg(), (0, 0))

        # Draw lane divider (subtle center line)
        mid_x = (PLAYER_RANK_X[1] + ENEMY_RANK_X[1]) // 2
        pygame.draw.line(surface, (40, 40, 50),
                         (mid_x, COMBAT_Y_CENTER - 80),
                         (mid_x, COMBAT_Y_CENTER + 120), 1)

        # Draw units at rank positions
        self._draw_team(surface, self.player_units, self.player_animators,
                        is_player=True)
        self._draw_team_enemies(surface)

        # Draw projectiles
        for proj in self.battle.projectiles:
            proj.draw(surface)

        # Particles and ability animations
        self.particle_emitter.draw(surface)
        self.ability_animator.draw(surface)

        # HUD
        self._draw_ability_hud(surface)
        self._draw_action_log(surface)

        # Ability tooltip (drawn on top of HUD)
        self.ability_hud.draw_tooltip(surface)

        # Result overlay
        if self.battle.result:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            surface.blit(overlay, (0, 0))
            if self.battle.result == "victory":
                text, color = "VICTORY!", GOLD
            else:
                text, color = "DEFEAT...", RED
            draw_text(surface, text, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                      size=FONT_SIZE_LARGE, color=color, center=True, font_type="title")

        # Pause / escape overlay
        if self.paused:
            self._draw_pause_overlay(surface)

    def _draw_team(self, surface: pygame.Surface,
                   units: list[CombatUnit],
                   animators: dict[str, IdleAnimator],
                   is_player: bool = False):
        """Draw units at their rank positions with UI, sorted by depth."""
        import math
        from config import SPEED_BAR_WIDTH

        # Sort units by their y position to ensure correct depth rendering (painter's algorithm)
        sorted_units = sorted(units, key=lambda u: u.y)

        for unit in sorted_units:
            animator = animators.get(unit.name) if not is_player else animators.get(unit.id)
            ox, oy = self.combat_animator.get_offset(unit.name)
            cx = int(unit.x + ox)
            foot_y = int(unit.y + oy)

            # Player-controlled indicator
            if is_player and unit.id == self.battle.player_controlled_id and unit.alive:
                t = pygame.time.get_ticks() / 1000.0
                pulse_alpha = 80 + int(40 * math.sin(t * 6))
                glow_surf = pygame.Surface((70, 20), pygame.SRCALPHA)
                pygame.draw.ellipse(glow_surf, (*GOLD, pulse_alpha), glow_surf.get_rect())
                pygame.draw.ellipse(glow_surf, (*WHITE, pulse_alpha + 60),
                                    glow_surf.get_rect(), 2)
                surface.blit(glow_surf, (cx - 35, foot_y - 15))

            # Draw Sprite
            if unit.alive and animator:
                animator.draw(surface, cx, foot_y)
            elif not is_player and unit.alive and not animator:
                # Placeholder for enemies without sprites
                body = pygame.Rect(cx - 30, foot_y - 50, 60, 50)
                pygame.draw.ellipse(surface, (180, 60, 60), body)
                pygame.draw.ellipse(surface, (140, 40, 40), body, 2)
            elif not unit.alive and animator:
                dead_surf = animator.base.copy()
                dead_surf.fill((60, 60, 60, 160), special_flags=pygame.BLEND_RGBA_MULT)
                dead_surf = pygame.transform.rotate(dead_surf, -90 if is_player else 90)
                surface.blit(dead_surf, (cx - dead_surf.get_width() // 2,
                                         foot_y - dead_surf.get_height() + 10))

            # UI Elements
            name_color = WHITE if unit.alive else DARK_GRAY
            draw_text(surface, unit.name, cx, foot_y + 10,
                      size=FONT_SIZE_SMALL, color=name_color, center=True)

            # Rank label
            if unit.alive:
                rank_x_offset = -45 if is_player else 45
                draw_text(surface, f"R{unit.rank}", cx + rank_x_offset, foot_y - 100,
                          size=10, color=GRAY, center=True)

            # HP bar (centered above unit)
            hp_color = RED if unit.alive else DARK_GRAY
            draw_health_bar(surface, cx - 40, foot_y - 115, 80, 8,
                            unit.hp, unit.max_hp, color=hp_color)

            # Speed bar (ATB) (centered below name)
            if unit.alive:
                role = self.player_roles.get(unit.id, "warlock") if is_player else None
                draw_speed_bar(surface, cx - SPEED_BAR_WIDTH // 2, foot_y + 25,
                               unit.speed_bar, unit_class=role,
                               time_active=unit.time_alive)

                # Turn Indicator when ready
                if unit.speed_bar >= 1.0:
                    t = pygame.time.get_ticks() / 1000.0
                    bob = int(math.sin(t * 10) * 4)
                    draw_text(surface, "READY!", cx, foot_y - 130 + bob,
                              size=14, color=GOLD, center=True)

            # Block indicator
            if unit.block > 0:
                block_x_offset = -50 if is_player else 50
                pygame.draw.circle(surface, BLUE, (cx + block_x_offset, foot_y - 111), 10)
                draw_text(surface, str(unit.block), cx + block_x_offset, foot_y - 111,
                          size=12, color=WHITE, center=True)

            # Flash overlay
            flash = self.combat_animator.get_flash(unit.name)
            if flash:
                flash_surf = pygame.Surface((100, 120), pygame.SRCALPHA)
                flash_surf.fill(flash)
                surface.blit(flash_surf, (cx - 50, foot_y - 100))

    def _draw_team_enemies(self, surface: pygame.Surface):
        """Draw enemy units (delegates to the unified _draw_team method)."""
        self._draw_team(surface, self.enemy_units, self.enemy_animators, is_player=False)

    def _draw_ability_hud(self, surface: pygame.Surface):
        """Draw ability cooldown bar at bottom for player-controlled unit."""
        if self.player_controlled:
            self.ability_hud.draw(surface, self.player_controlled, self.ability_registry)

    def _draw_action_log(self, surface: pygame.Surface):
        """Draw action log at bottom-left."""
        log_x = 20
        log_y = SCREEN_HEIGHT - 160
        for i, (msg, age) in enumerate(reversed(self.action_log)):
            alpha = max(0, min(255, int(255 * (1.0 - age / 6.0))))
            if alpha <= 0:
                continue
            color = (*WHITE[:3], alpha) if alpha < 255 else WHITE
            draw_text(surface, msg, log_x, log_y + i * 16,
                      size=12, color=color, center=False)

    def _draw_pause_overlay(self, surface: pygame.Surface):
        dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 160))
        surface.blit(dark, (0, 0))

        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        panel = pygame.Rect(cx - 180, cy - 100, 360, 200)
        pygame.draw.rect(surface, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, panel, width=2, border_radius=10)

        draw_text(surface, "Return to Menu?", cx, cy - 60,
                  size=FONT_SIZE_LARGE, color=GOLD, center=True, font_type="title")
        draw_text(surface, "Current run progress will be lost.", cx, cy - 20,
                  size=FONT_SIZE_SMALL, color=GRAY, center=True)

        # Yes button
        self._pause_yes_rect = pygame.Rect(cx - 150, cy + 20, 130, 40)
        color_yes = (70, 50, 50)
        if self._pause_yes_rect.collidepoint(pygame.mouse.get_pos()):
            color_yes = (100, 60, 60)
        pygame.draw.rect(surface, color_yes, self._pause_yes_rect, border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, self._pause_yes_rect, width=1, border_radius=6)
        draw_text(surface, "Yes, Leave", cx - 85, cy + 40,
                  size=FONT_SIZE_SMALL, color=RED, center=True)

        # No button
        self._pause_no_rect = pygame.Rect(cx + 20, cy + 20, 130, 40)
        color_no = (50, 60, 50)
        if self._pause_no_rect.collidepoint(pygame.mouse.get_pos()):
            color_no = (60, 80, 60)
        pygame.draw.rect(surface, color_no, self._pause_no_rect, border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, self._pause_no_rect, width=1, border_radius=6)
        draw_text(surface, "Resume", cx + 85, cy + 40,
                  size=FONT_SIZE_SMALL, color=GREEN, center=True)

    def handle_event(self, event: pygame.event.Event):
        if self.transitioning:
            return

        # Pause menu handling
        if self.paused:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.paused = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if hasattr(self, '_pause_yes_rect') and self._pause_yes_rect.collidepoint(mx, my):
                    self.game.state_machine.transition(GameState.TITLE)
                elif hasattr(self, '_pause_no_rect') and self._pause_no_rect.collidepoint(mx, my):
                    self.paused = False
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = True
                return
            # Ability hotkeys 1-4
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                idx = event.key - pygame.K_1
                self._fire_ability_by_index(idx)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            clicked_ability_id = self.ability_hud.handle_click(mx, my)
            if clicked_ability_id and self.player_controlled:
                self.battle.fire_ability(self.player_controlled, clicked_ability_id)

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.ability_hud.update_hover(mx, my, self.ability_registry)

    def _fire_ability_by_index(self, idx: int):
        if not self.player_controlled:
            return
        if idx < len(self.player_controlled.ability_ids):
            ability_id = self.player_controlled.ability_ids[idx]
            self.battle.fire_ability(self.player_controlled, ability_id)

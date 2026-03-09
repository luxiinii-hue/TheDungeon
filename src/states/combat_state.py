"""Real-time side-scroller combat state."""

import random
import pygame
from src.states.base_state import BaseState
from src.core.state_machine import GameState
from src.entities.enemy import EnemyData
from src.combat.ability import AbilityRegistry
from src.combat.unit import CombatUnit
from src.combat.realtime_battle import RealtimeBattle, BattleAction
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
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GRAY, GOLD, RED, BLUE, GREEN,
    DARK_GRAY, PANEL_BG, PANEL_BORDER, ORANGE, PURPLE, CYAN,
    FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE,
    PLAYER_ZONE_X_MIN, PLAYER_ZONE_X_MAX,
    PLAYER_ZONE_Y_MIN, PLAYER_ZONE_Y_MAX,
    ENEMY_ZONE_X_MIN, ENEMY_ZONE_X_MAX,
    ENEMY_ZONE_Y_MIN, ENEMY_ZONE_Y_MAX,
    PLAYER_MOVE_SPEED, UNIT_HITBOX_W, UNIT_HITBOX_H,
    CLASS_COLORS,
)


class CombatScreenState(BaseState):
    def enter(self, **kwargs):
        self.tier = kwargs.get("tier", "normal")
        self.difficulty = kwargs.get("difficulty", 1)
        am = self.game.asset_manager
        run = self.game.run_manager

        # Load ability registry
        self.ability_registry = AbilityRegistry()
        self.ability_registry.load(am.load_json("abilities.json"))

        # Create player combat units
        self.player_units: list[CombatUnit] = []
        self.player_animators: dict[str, IdleAnimator] = {}

        alive_team = run.get_alive_team()
        for i, char in enumerate(alive_team):
            hp_override = run.team_hp[char.id]
            unit = CombatUnit.from_character(
                char,
                ability_mods=run.ability_mods.get(char.id, []),
                stat_boosts=run.stat_boosts.get(char.id, {}),
            )
            unit.hp = hp_override
            unit.max_hp = run.team_max_hp[char.id]

            # Set initial position — spread vertically in player zone
            num = len(alive_team)
            spacing = (PLAYER_ZONE_Y_MAX - PLAYER_ZONE_Y_MIN) / max(num, 1)
            unit.x = PLAYER_ZONE_X_MAX - 80
            unit.y = PLAYER_ZONE_Y_MIN + spacing * (i + 0.5)
            self.player_units.append(unit)

            # Create idle animator
            img = am.load_image(char.sprite)
            sprite_h = 100
            aspect = img.get_width() / img.get_height()
            sprite_w = int(sprite_h * aspect)
            scaled = am.get_scaled(char.sprite, sprite_w, sprite_h)
            self.player_animators[unit.id] = IdleAnimator(scaled, char.idle_config)

        # Player-controlled unit is the first one
        self.player_controlled = self.player_units[0] if self.player_units else None
        player_id = self.player_controlled.id if self.player_controlled else ""

        # Load and create enemy units
        enemies_data = am.load_json("enemies.json")
        all_enemies = [EnemyData.from_dict(e) for e in enemies_data]

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
            # Position enemies in enemy zone
            spacing = (ENEMY_ZONE_Y_MAX - ENEMY_ZONE_Y_MIN) / max(num_enemies, 1)
            unit.x = ENEMY_ZONE_X_MIN + 80
            unit.y = ENEMY_ZONE_Y_MIN + spacing * (i + 0.5)
            # Mark boss units for spread attack pattern
            unit._is_boss = (edata.tier == "boss")
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

        # Real-time battle engine
        self.battle = RealtimeBattle(
            self.player_units, self.enemy_units,
            self.ability_registry, player_id,
            asset_manager=am
        )

        # AI controller
        self.ai = AIController(self.battle, self.ability_registry)

        # Animation systems
        self.combat_animator = CombatAnimator()
        self.particle_emitter = ParticleEmitter()
        self.ability_animator = AbilityAnimator()
        
        # HUDs
        self.ability_hud = AbilityHUD(am)

        # Action log
        self.action_log: list[tuple[str, float]] = []
        self.max_log_lines = 5

        # Movement input state
        self.keys_held: set[int] = set()

        # End state
        self.end_delay = 0.0
        self.transitioning = False

        # Ability cooldown display cache
        self._ability_hud_rects: list[pygame.Rect] = []

    def update(self, dt: float):
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

        # Player movement (WASD)
        if self.player_controlled and self.player_controlled.alive:
            self._handle_movement(dt)
            
            # Near-miss dodge detection (Task 3.4)
            px, py = self.player_controlled.x, self.player_controlled.y
            for proj in self.battle.projectiles:
                if proj.team == "enemy" and proj.alive:
                    # If projectile has just safely passed behind the player
                    if proj.x < px - 20 and not getattr(proj, '_near_miss_checked', False):
                        proj._near_miss_checked = True
                        if abs(proj.y - py) < 80:  # It was close vertically
                            self.particle_emitter.add_floating_number(px, py - 80, "Dodge!", (180, 220, 255))
                            self.combat_animator.add_flash(self.player_controlled.name, color=(200, 230, 255), duration=0.15)
                            from src.animation.particles import spawn_shield_bash
                            spawn_shield_bash(self.particle_emitter, px, py)

        # AI for allies and enemies
        self.ai.update(dt, self.player_controlled)

        # Battle engine update
        actions = self.battle.update(dt)
        for action in actions:
            self._process_action(action)

        # Projectile trails
        from src.animation.particles import spawn_projectile_trail
        for proj in self.battle.projectiles:
            if random.random() < 0.4:
                spawn_projectile_trail(self.particle_emitter, proj.x, proj.y, proj.color)

    def _handle_movement(self, dt: float):
        pc = self.player_controlled
        dx, dy = 0.0, 0.0
        if pygame.K_w in self.keys_held or pygame.K_UP in self.keys_held:
            dy -= 1
        if pygame.K_s in self.keys_held or pygame.K_DOWN in self.keys_held:
            dy += 1
        if pygame.K_a in self.keys_held or pygame.K_LEFT in self.keys_held:
            dx -= 1
        if pygame.K_d in self.keys_held or pygame.K_RIGHT in self.keys_held:
            dx += 1

        if dx != 0 or dy != 0:
            # Normalize diagonal movement
            if dx != 0 and dy != 0:
                dx *= 0.707
                dy *= 0.707
            pc.x += dx * PLAYER_MOVE_SPEED * dt
            pc.y += dy * PLAYER_MOVE_SPEED * dt
            # Clamp to player zone
            pc.x = max(PLAYER_ZONE_X_MIN, min(PLAYER_ZONE_X_MAX, pc.x))
            pc.y = max(PLAYER_ZONE_Y_MIN, min(PLAYER_ZONE_Y_MAX, pc.y))

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

                # Ability impact animation
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
        """Spawn a summoned enemy unit."""
        enemy_id = action.target
        num_to_spawn = max(1, action.damage)
        am = self.game.asset_manager
        all_enemies_raw = am.load_json("enemies.json")
        all_enemy_data = [EnemyData.from_dict(e) for e in all_enemies_raw]
        template = next((e for e in all_enemy_data if e.id == enemy_id), None)
        if not template:
            return
        for _ in range(num_to_spawn):
            spawn_name = f"{template.name} {len(self.enemy_units) + 1}"
            raw = next(e for e in all_enemies_raw if e["id"] == enemy_id)
            edata_copy = EnemyData.from_dict(raw)
            edata_copy.name = spawn_name
            new_unit = CombatUnit.from_enemy(edata_copy)
            # Position near existing enemies
            new_unit.x = ENEMY_ZONE_X_MIN + random.randint(0, 100)
            new_unit.y = random.uniform(ENEMY_ZONE_Y_MIN + 40, ENEMY_ZONE_Y_MAX - 40)
            self.enemy_units.append(new_unit)
            self.enemy_data.append(edata_copy)
            self.battle.enemy_units.append(new_unit)
            if template.sprite:
                img = am.load_image(template.sprite)
                sprite_h = 100
                aspect = img.get_width() / img.get_height()
                sprite_w = int(sprite_h * aspect)
                scaled = am.get_scaled(template.sprite, sprite_w, sprite_h)
                self.enemy_animators[new_unit.name] = IdleAnimator(
                    scaled, template.idle_config)
            else:
                self.enemy_animators[new_unit.name] = None

    def _find_unit(self, name: str) -> CombatUnit | None:
        for u in self.player_units + self.enemy_units:
            if u.name == name:
                return u
        return None

    def _get_bg(self) -> pygame.Surface:
        if not hasattr(self, "_bg_cache"):
            bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            try:
                # Composite the 4 layers of background 2 for a side-scroller feel
                base_path = "Potential assets/backgrounds/background 2/"
                for layer_name in ["1.png", "2.png", "3.png", "4.png"]:
                    img = self.game.asset_manager.get_scaled(
                        base_path + layer_name, SCREEN_WIDTH, SCREEN_HEIGHT)
                    bg.blit(img, (0, 0))
                
                # Add a subtle ground shadow
                ground_shadow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.rect(ground_shadow, (10, 15, 25, 120), (0, ENEMY_ZONE_Y_MAX - 20, SCREEN_WIDTH, SCREEN_HEIGHT))
                bg.blit(ground_shadow, (0, 0))

                # Slight darkening for atmosphere, but less than before
                dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                dark.fill((10, 10, 20, 60))
                bg.blit(dark, (0, 0))
            except Exception:
                bg.fill((20, 18, 25))
            self._bg_cache = bg
        return self._bg_cache

    def draw(self, surface: pygame.Surface):
        surface.blit(self._get_bg(), (0, 0))

        # Draw zone indicators (subtle)
        self._draw_zones(surface)

        # Draw units
        self._draw_units(surface, self.player_units, self.player_animators, is_player=True)
        self._draw_enemy_units(surface)

        # Draw projectiles
        for proj in self.battle.projectiles:
            proj.draw(surface)

        # Particles and ability animations
        self.particle_emitter.draw(surface)
        self.ability_animator.draw(surface)

        # HUD
        self._draw_ability_hud(surface)
        self._draw_action_log(surface)

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

    def _draw_zones(self, surface: pygame.Surface):
        """Draw subtle zone boundary lines."""
        # Player zone right edge
        pygame.draw.line(surface, (40, 40, 60),
                          (PLAYER_ZONE_X_MAX, PLAYER_ZONE_Y_MIN),
                          (PLAYER_ZONE_X_MAX, PLAYER_ZONE_Y_MAX), 1)
        # Enemy zone left edge
        pygame.draw.line(surface, (60, 40, 40),
                          (ENEMY_ZONE_X_MIN, ENEMY_ZONE_Y_MIN),
                          (ENEMY_ZONE_X_MIN, ENEMY_ZONE_Y_MAX), 1)

    def _draw_units(self, surface: pygame.Surface,
                    units: list[CombatUnit],
                    animators: dict[str, IdleAnimator],
                    is_player: bool = False):
        """Draw player units at their x,y positions."""
        import math
        for unit in units:
            animator = animators.get(unit.id)
            ox, oy = self.combat_animator.get_offset(unit.name)
            cx = int(unit.x + ox)
            foot_y = int(unit.y + oy)

            # Player-controlled indicator (Task 3.3) - Draw behind the unit
            if is_player and unit.id == self.battle.player_controlled_id and unit.alive:
                t = pygame.time.get_ticks() / 1000.0
                pulse_alpha = 80 + int(40 * math.sin(t * 6))
                glow_rect = pygame.Rect(cx - 35, foot_y - 15, 70, 20)
                glow_surf = pygame.Surface((70, 20), pygame.SRCALPHA)
                pygame.draw.ellipse(glow_surf, (*GOLD, pulse_alpha), glow_surf.get_rect())
                pygame.draw.ellipse(glow_surf, (*WHITE, pulse_alpha + 60), glow_surf.get_rect(), 2)
                surface.blit(glow_surf, glow_rect)

            if unit.alive and animator:
                animator.draw(surface, cx, foot_y)
            elif not unit.alive and animator:
                # Draw a darkened "corpse" sprite (Task 3.7)
                dead_surf = animator.base.copy()
                dead_surf.fill((60, 60, 60, 160), special_flags=pygame.BLEND_RGBA_MULT)
                # Lay the sprite down
                dead_surf = pygame.transform.rotate(dead_surf, -90)
                surface.blit(dead_surf, (cx - dead_surf.get_width() // 2, foot_y - dead_surf.get_height() + 10))
            elif not unit.alive:
                grey = pygame.Surface((60, 60), pygame.SRCALPHA)
                grey.fill((60, 60, 60, 100))
                surface.blit(grey, (cx - 30, foot_y - 60))

            # Name
            name_color = WHITE if unit.alive else DARK_GRAY
            draw_text(surface, unit.name, cx, foot_y + 45,
                      size=FONT_SIZE_SMALL, color=name_color, center=True)

            # HP bar
            hp_color = RED if unit.alive else DARK_GRAY
            draw_health_bar(surface, cx - 40, foot_y - 115, 80, 8,
                            unit.hp, unit.max_hp, color=hp_color)

            # Block indicator
            if unit.block > 0:
                pygame.draw.circle(surface, BLUE, (cx - 50, foot_y - 111), 10)
                draw_text(surface, str(unit.block), cx - 50, foot_y - 111,
                          size=12, color=WHITE, center=True)

            # Flash overlay
            flash = self.combat_animator.get_flash(unit.name)
            if flash:
                flash_surf = pygame.Surface((100, 120), pygame.SRCALPHA)
                flash_surf.fill(flash)
                surface.blit(flash_surf, (cx - 50, foot_y - 100))

    def _draw_enemy_units(self, surface: pygame.Surface):
        """Draw enemy units at their x,y positions."""
        for unit in self.enemy_units:
            animator = self.enemy_animators.get(unit.name)
            ox, oy = self.combat_animator.get_offset(unit.name)
            cx = int(unit.x + ox)
            foot_y = int(unit.y + oy)

            if unit.alive and animator:
                animator.draw(surface, cx, foot_y)
            elif unit.alive:
                # Procedural fallback
                body = pygame.Rect(cx - 30, foot_y - 50, 60, 50)
                pygame.draw.ellipse(surface, (180, 60, 60), body)
                pygame.draw.ellipse(surface, (140, 40, 40), body, 2)
            elif not unit.alive and animator:
                # Draw a darkened "corpse" sprite (Task 3.7)
                dead_surf = animator.base.copy()
                dead_surf.fill((60, 60, 60, 160), special_flags=pygame.BLEND_RGBA_MULT)
                # Lay the sprite down (enemies face left, so rotate 90)
                dead_surf = pygame.transform.rotate(dead_surf, 90)
                surface.blit(dead_surf, (cx - dead_surf.get_width() // 2, foot_y - dead_surf.get_height() + 10))
            elif not unit.alive:
                grey = pygame.Surface((60, 50), pygame.SRCALPHA)
                grey.fill((60, 60, 60, 100))
                surface.blit(grey, (cx - 30, foot_y - 50))

            name_color = WHITE if unit.alive else DARK_GRAY
            draw_text(surface, unit.name, cx, foot_y + 10,
                      size=FONT_SIZE_SMALL, color=name_color, center=True)

            hp_color = RED if unit.alive else DARK_GRAY
            draw_health_bar(surface, cx - 40, foot_y - 115, 80, 8,
                            unit.hp, unit.max_hp, color=hp_color)

            if unit.block > 0:
                pygame.draw.circle(surface, BLUE, (cx + 50, foot_y - 111), 10)
                draw_text(surface, str(unit.block), cx + 50, foot_y - 111,
                          size=12, color=WHITE, center=True)

            flash = self.combat_animator.get_flash(unit.name)
            if flash:
                flash_surf = pygame.Surface((100, 100), pygame.SRCALPHA)
                flash_surf.fill(flash)
                surface.blit(flash_surf, (cx - 50, foot_y - 100))

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

    def handle_event(self, event: pygame.event.Event):
        if self.transitioning:
            return

        if event.type == pygame.KEYDOWN:
            self.keys_held.add(event.key)
            # Ability hotkeys 1-4
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                idx = event.key - pygame.K_1
                self._fire_ability_by_index(idx)

        elif event.type == pygame.KEYUP:
            self.keys_held.discard(event.key)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check ability HUD clicks
            mx, my = event.pos
            clicked_ability_id = self.ability_hud.handle_click(mx, my)
            if clicked_ability_id and self.player_controlled:
                self.battle.fire_ability(self.player_controlled, clicked_ability_id)

    def _fire_ability_by_index(self, idx: int):
        if not self.player_controlled:
            return
        if idx < len(self.player_controlled.ability_ids):
            ability_id = self.player_controlled.ability_ids[idx]
            self.battle.fire_ability(self.player_controlled, ability_id)

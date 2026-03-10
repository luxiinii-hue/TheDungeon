"""Team selection state — pick 2 from 5 characters, fantasy guild-hall aesthetic."""

import math
import pygame
from src.states.base_state import BaseState
from src.core.state_machine import GameState
from src.entities.character import CharacterData
from src.animation.idle_animator import IdleAnimator
from src.animation.tween import pulse
from src.ui.button import Button
from src.ui.panel import CharacterPanel
from src.ui.tooltip import Tooltip
from src.ui.text_renderer import draw_text
from src.combat.ability import AbilityRegistry
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GRAY, GOLD,
    FONT_SIZE_TITLE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL,
    PANEL_BG, PANEL_BORDER, CLASS_COLORS,
)


class TeamSelectState(BaseState):
    def enter(self, **kwargs):
        am = self.game.asset_manager
        chars_data = am.load_json("characters.json")
        self.characters = [CharacterData.from_dict(c) for c in chars_data]
        self.time = 0.0

        # Load sprites and create idle animators
        self.animators: list[IdleAnimator] = []
        self.sprites: list[pygame.Surface] = []
        for char in self.characters:
            img = am.load_image(char.sprite)
            sprite_h = 200
            aspect = img.get_width() / img.get_height()
            sprite_w = int(sprite_h * aspect)
            scaled = am.get_scaled(char.sprite, sprite_w, sprite_h)
            self.sprites.append(scaled)
            self.animators.append(IdleAnimator(scaled, char.idle_config))

        # Selection state — ordered list: first = Leader (player-controlled), second = Ally (AI)
        self.selected: list[int] = []

        # Character slots for click detection
        self.slot_rects: list[pygame.Rect] = []
        self.leader_btn_rects: list[pygame.Rect] = []
        slot_width = 200
        gap = 20
        num = len(self.characters)
        total_width = num * slot_width + (num - 1) * gap
        start_x = (SCREEN_WIDTH - total_width) // 2
        for i in range(num):
            x = start_x + i * (slot_width + gap)
            self.slot_rects.append(pygame.Rect(x, 170, slot_width, 380))
            # Leader button centered above each card
            btn_w = 80
            btn_h = 26
            self.leader_btn_rects.append(pygame.Rect(
                x + (slot_width - btn_w) // 2, 170 - btn_h - 6, btn_w, btn_h))

        # Info panel — wide bottom bar with horizontal layout
        self.info_panel = CharacterPanel(40, SCREEN_HEIGHT - 160, SCREEN_WIDTH - 80, 140)

        # Begin Run button
        self.begin_btn = Button(
            SCREEN_WIDTH - 250, SCREEN_HEIGHT - 60, "Begin Run",
            on_click=self._on_begin,
        )
        self.back_btn = Button(
            40, SCREEN_HEIGHT - 60, "Back",
            width=200, height=40,
            on_click=self._on_back,
        )

        self.tooltip = Tooltip()
        self.ability_registry = AbilityRegistry()
        self.ability_registry.load(am.load_json("abilities.json"))

        # Pre-render background
        self._bg_surface = self._render_background()

    def _render_background(self) -> pygame.Surface:
        """Guild hall background with vignette."""
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        try:
            img = self.game.asset_manager.get_scaled(
                "Backgrounds/gothic_city/gothic_entrance.png",
                SCREEN_WIDTH, SCREEN_HEIGHT)
            bg.blit(img, (0, 0))
        except Exception:
            bg.fill((25, 20, 30))

        # Dark tint so characters pop against the background
        tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        tint.fill((10, 8, 20, 180))
        bg.blit(tint, (0, 0))

        # Vignette overlay
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        # Top and bottom darkening
        for i in range(80):
            alpha = int(120 * (1.0 - i / 80))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (0, i), (SCREEN_WIDTH, i))
            pygame.draw.line(vignette, (0, 0, 0, alpha),
                             (0, SCREEN_HEIGHT - 1 - i), (SCREEN_WIDTH, SCREEN_HEIGHT - 1 - i))
        # Side darkening
        for i in range(60):
            alpha = int(80 * (1.0 - i / 60))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (i, 0), (i, SCREEN_HEIGHT))
            pygame.draw.line(vignette, (0, 0, 0, alpha),
                             (SCREEN_WIDTH - 1 - i, 0), (SCREEN_WIDTH - 1 - i, SCREEN_HEIGHT))
        bg.blit(vignette, (0, 0))

        return bg

    def _on_begin(self):
        if len(self.selected) != 2:
            return
        # First selected = Leader (player-controlled), second = Ally (AI)
        team = [self.characters[i] for i in self.selected]
        self.game.state_machine.transition(GameState.MAP, team=team)

    def _on_back(self):
        self.game.state_machine.transition(GameState.TITLE)

    def update(self, dt: float):
        self.time += dt
        for animator in self.animators:
            animator.update(dt)

    def draw(self, surface: pygame.Surface):
        # Background
        surface.blit(self._bg_surface, (0, 0))

        # Torch flicker — warm light pulse in upper corners
        torch_alpha = int(pulse(self.time, 2.5, 15, 40))
        torch_size = 120
        torch_surf = pygame.Surface((torch_size * 2, torch_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(torch_surf, (220, 140, 40, torch_alpha),
                           (torch_size, torch_size), torch_size)
        surface.blit(torch_surf, (-torch_size + 40, -torch_size + 40))
        surface.blit(torch_surf, (SCREEN_WIDTH - torch_size - 40, -torch_size + 40))

        # Title
        draw_text(surface, "Choose Your Team", SCREEN_WIDTH // 2, 50,
                  size=FONT_SIZE_TITLE, color=GOLD, center=True, font_type="title")

        # Decorative line with diamond accents
        line_y = 95
        line_w = 300
        cx = SCREEN_WIDTH // 2
        pygame.draw.line(surface, PANEL_BORDER, (cx - line_w, line_y), (cx + line_w, line_y), 2)
        # Center diamond
        diamond_size = 6
        diamond = [(cx, line_y - diamond_size), (cx + diamond_size, line_y),
                   (cx, line_y + diamond_size), (cx - diamond_size, line_y)]
        pygame.draw.polygon(surface, GOLD, diamond)
        # Side diamonds
        for dx in [-line_w + 10, line_w - 10]:
            sd = [(cx + dx, line_y - 4), (cx + dx + 4, line_y),
                  (cx + dx, line_y + 4), (cx + dx - 4, line_y)]
            pygame.draw.polygon(surface, PANEL_BORDER, sd)

        draw_text(surface, "Select 2 champions", SCREEN_WIDTH // 2, 115,
                  size=FONT_SIZE_SMALL, color=GRAY, center=True)

        # Draw character slots
        for i, (char, animator, rect) in enumerate(
                zip(self.characters, self.animators, self.slot_rects)):
            is_selected = i in self.selected

            # Selected glow — pulsing golden aura behind card
            if is_selected:
                glow_alpha = int(pulse(self.time, 1.2, 30, 80))
                glow_rect = rect.inflate(12, 12)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (218, 165, 32, glow_alpha),
                                 (0, 0, glow_rect.width, glow_rect.height),
                                 border_radius=14)
                surface.blit(glow_surf, glow_rect.topleft)

            # Card background
            bg_color = (40, 38, 55) if is_selected else PANEL_BG
            pygame.draw.rect(surface, bg_color, rect, border_radius=10)

            # Double border — outer border
            outer_color = GOLD if is_selected else PANEL_BORDER
            outer_width = 3 if is_selected else 1
            pygame.draw.rect(surface, outer_color, rect, width=outer_width,
                             border_radius=10)
            # Inner lighter border
            if is_selected:
                inner_rect = rect.inflate(-8, -8)
                pygame.draw.rect(surface, (180, 150, 80), inner_rect, width=1,
                                 border_radius=8)

            # Corner diamond accents
            corners = [
                (rect.left + 10, rect.top + 10),
                (rect.right - 10, rect.top + 10),
                (rect.left + 10, rect.bottom - 10),
                (rect.right - 10, rect.bottom - 10),
            ]
            d_color = GOLD if is_selected else (100, 90, 70)
            for (dx, dy) in corners:
                ds = 3
                pygame.draw.polygon(surface, d_color,
                                    [(dx, dy - ds), (dx + ds, dy),
                                     (dx, dy + ds), (dx - ds, dy)])

            # Locked indicator
            if not char.unlocked:
                overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 120))
                surface.blit(overlay, rect.topleft)
                draw_text(surface, "[LOCKED]", rect.centerx, rect.centery,
                          size=FONT_SIZE_MEDIUM, color=GRAY, center=True)
                continue

            # Character sprite with idle animation
            sprite_cx = rect.centerx
            foot_y = rect.y + 50 + 200
            animator.draw(surface, sprite_cx, foot_y)

            # Name
            draw_text(surface, char.name, sprite_cx, rect.bottom - 95,
                      size=FONT_SIZE_MEDIUM, color=WHITE, center=True)

            # Class badge — colored pill with class name
            role_color = CLASS_COLORS.get(char.role, GRAY)
            badge_text = char.role.capitalize()
            badge_w = max(60, len(badge_text) * 9 + 16)
            badge_h = 22
            badge_x = sprite_cx - badge_w // 2
            badge_y = rect.bottom - 72
            badge_rect = pygame.Rect(badge_x, badge_y, badge_w, badge_h)
            # Badge background (darker version of class color)
            dark_role = tuple(max(0, c - 60) for c in role_color)
            pygame.draw.rect(surface, dark_role, badge_rect, border_radius=badge_h // 2)
            pygame.draw.rect(surface, role_color, badge_rect, width=1,
                             border_radius=badge_h // 2)
            draw_text(surface, badge_text, sprite_cx, badge_y + badge_h // 2,
                      size=FONT_SIZE_SMALL, color=role_color, center=True)

            # Stat row — compact HP/STR/SPD
            stat_y = rect.bottom - 40
            stat_items = [
                (f"HP:{char.max_hp}", (200, 80, 80)),
                (f"STR:{char.strength}", (220, 180, 80)),
                (f"SPD:{char.speed}", (80, 180, 220)),
            ]
            stat_total_w = sum(len(s) * 7 + 12 for s, _ in stat_items)
            sx = sprite_cx - stat_total_w // 2
            for stat_text, stat_color in stat_items:
                draw_text(surface, stat_text, sx, stat_y,
                          size=FONT_SIZE_SMALL, color=stat_color)
                sx += len(stat_text) * 7 + 12

            # Leader button above card
            if char.unlocked:
                is_leader = (len(self.selected) > 0 and self.selected[0] == i)
                is_ally = (i in self.selected and not is_leader)
                lbtn = self.leader_btn_rects[i]
                mouse_on = lbtn.collidepoint(pygame.mouse.get_pos())

                if is_leader:
                    btn_bg = (80, 65, 20)
                    btn_border = GOLD
                    btn_label = "LEADER"
                    btn_text_color = GOLD
                elif is_ally:
                    btn_bg = (30, 40, 60)
                    btn_border = (150, 180, 220)
                    btn_label = "ALLY"
                    btn_text_color = (150, 180, 220)
                else:
                    btn_bg = (45, 42, 55) if mouse_on else (35, 32, 45)
                    btn_border = GRAY if mouse_on else (60, 55, 65)
                    btn_label = "Leader"
                    btn_text_color = GRAY

                pygame.draw.rect(surface, btn_bg, lbtn, border_radius=lbtn.height // 2)
                pygame.draw.rect(surface, btn_border, lbtn, width=1, border_radius=lbtn.height // 2)
                draw_text(surface, btn_label, lbtn.centerx, lbtn.centery,
                          size=FONT_SIZE_SMALL, color=btn_text_color, center=True)

        # Info panel for hovered character
        self.info_panel.draw(surface)

        # Status text
        count = len(self.selected)
        status_color = GOLD if count == 2 else WHITE
        draw_text(surface, f"{count}/2 selected", SCREEN_WIDTH // 2,
                  SCREEN_HEIGHT - 170,
                  size=FONT_SIZE_MEDIUM, color=status_color, center=True)
        hint = "Click card to select/deselect. Click 'Leader' button to set who you control."
        draw_text(surface, hint, SCREEN_WIDTH // 2,
                  SCREEN_HEIGHT - 150,
                  size=FONT_SIZE_SMALL, color=GRAY, center=True)

        # Buttons
        if len(self.selected) == 2:
            self.begin_btn.draw(surface)
        self.back_btn.draw(surface)

        self.tooltip.draw(surface)

    def handle_event(self, event: pygame.event.Event):
        if self.begin_btn.handle_event(event):
            return
        if self.back_btn.handle_event(event):
            return

        if event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(event.pos) and self.characters[i].unlocked:
                    self.info_panel.set_character(self.characters[i])
                    break

            # Check ability hover for tooltip
            mx, my = event.pos
            tooltip_shown = False
            for arect, ability_id in self.info_panel.ability_rects:
                if arect.collidepoint(mx, my):
                    ability = self.ability_registry.get(ability_id)
                    if ability:
                        lines = [
                            (ability.description, GRAY),
                            (f"Damage: {ability.base_damage}  CD: {ability.cooldown}  Target: {ability.targeting.replace('_', ' ')}", WHITE),
                        ]
                        for eff in ability.effects:
                            if eff.type == "stun":
                                lines.append((f"Effect: Stun ({eff.duration} turn)", (100, 200, 255)))
                            elif eff.type == "summon":
                                lines.append((f"Effect: Summon {eff.enemy_id.replace('_', ' ').title()}", (200, 100, 255)))
                        icon = None
                        if ability.icon:
                            try:
                                icon = self.game.asset_manager.load_image(ability.icon)
                            except Exception:
                                pass
                        self.tooltip.show(mx, my, ability.name, lines, icon)
                        tooltip_shown = True
                    break
            if not tooltip_shown:
                self.tooltip.hide()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check leader buttons first
            for i, lbtn in enumerate(self.leader_btn_rects):
                if lbtn.collidepoint(event.pos) and self.characters[i].unlocked:
                    if i in self.selected:
                        # Already selected — make them leader (move to front)
                        self.selected.remove(i)
                        self.selected.insert(0, i)
                    else:
                        # Not selected — make them leader, drop current leader if full
                        if len(self.selected) >= 2:
                            self.selected.pop(0)
                        self.selected.insert(0, i)
                    return

            # Card click — toggle selection (added as ally)
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(event.pos) and self.characters[i].unlocked:
                    if i in self.selected:
                        self.selected.remove(i)
                    elif len(self.selected) < 2:
                        self.selected.append(i)
                    break

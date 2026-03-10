"""Branching map display and navigation."""

import random
import math
import pygame
from src.states.base_state import BaseState
from src.core.state_machine import GameState
from src.map.map_generator import generate_map
from src.map.map_node import MapNode
from src.map.run_manager import RunManager
from src.ui.button import Button
from src.ui.text_renderer import draw_text
from src.ui.health_bar import draw_health_bar
from src.ui.tooltip import Tooltip
from src.animation.tween import pulse
from src.animation.torch_animator import TorchAnimator
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GRAY, GOLD, RED, GREEN, BLUE,
    DARK_GRAY, ORANGE, PURPLE, CYAN, PANEL_BG, PANEL_BORDER,
    FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE, FONT_SIZE_TITLE,
    MAP_NODE_RADIUS,
)

# Node type colors
NODE_COLORS = {
    "combat": (180, 60, 60),
    "elite": (200, 140, 40),
    "shop": (60, 180, 60),
    "treasure": (218, 165, 32),
    "rest": (80, 140, 200),
    "event": (160, 80, 200),
    "boss": (200, 40, 40),
    "start": (180, 60, 60),
}

NODE_LABELS = {
    "combat": "Battle",
    "elite": "Elite",
    "shop": "Shop",
    "treasure": "Treasure",
    "rest": "Rest",
    "event": "Event",
    "boss": "BOSS",
    "start": "Start",
}


class MapState(BaseState):
    def enter(self, **kwargs):
        self.time = 0.0

        # Initialize run if team is passed (first entry)
        if "team" in kwargs:
            map_nodes = generate_map()
            self.game.run_manager = RunManager(kwargs["team"], map_nodes)

        self.run = self.game.run_manager

        # Shop/event overlay state
        self.overlay = None  # None, "shop", "event", "rest", "treasure"
        self.overlay_data = None
        self.event_result_message = None
        self.event_result_timer = 0.0
        self.show_menu_confirm = False
        self.tooltip = Tooltip()
        self.torch_animator = TorchAnimator(self.game.asset_manager)

    def update(self, dt: float):
        self.time += dt
        self.torch_animator.update(dt)
        if self.event_result_timer > 0:
            self.event_result_timer -= dt
            if self.event_result_timer <= 0:
                self.event_result_message = None
                self.overlay = None
                self.overlay_data = None

    def _get_bg(self) -> pygame.Surface:
        if not hasattr(self, "_bg_cache"):
            bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            try:
                img = self.game.asset_manager.get_scaled(
                    "Backgrounds/gothic_city/gothic_street.png",
                    SCREEN_WIDTH, SCREEN_HEIGHT)
                bg.blit(img, (0, 0))
                # Dark blue tint for dungeon map feel
                tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                tint.fill((5, 5, 20, 180))
                bg.blit(tint, (0, 0))
            except Exception:
                bg.fill((15, 12, 20))
            self._bg_cache = bg
        return self._bg_cache

    def draw(self, surface: pygame.Surface):
        surface.blit(self._get_bg(), (0, 0))
        self.torch_animator.draw(surface, "gothic_street")

        # Draw connections first
        for node in self.run.map_nodes:
            for cid in node.connections:
                target = self.run.map_nodes[cid]
                color = DARK_GRAY if node.visited else (50, 50, 60)
                pygame.draw.line(surface, color,
                                 (node.screen_x, node.screen_y),
                                 (target.screen_x, target.screen_y), 2)

        # Draw nodes
        for node in self.run.map_nodes:
            self._draw_node(surface, node)

        # Sidebar: team info
        self._draw_sidebar(surface)

        # Overlay
        if self.overlay:
            self._draw_overlay(surface)

        if self.show_menu_confirm:
            self._draw_menu_confirm(surface)

    def _draw_node(self, surface: pygame.Surface, node: MapNode):
        color = NODE_COLORS.get(node.node_type, GRAY)
        is_available = node.id in self.run.available_node_ids
        is_visited = node.visited

        # Attempt to load icon
        icon_name = node.node_type if node.node_type != "start" else "combat"
        icon_path = f"UI/icons/node_{icon_name}.png"
        try:
            icon = self.game.asset_manager.load_image(icon_path)
            w, h = icon.get_size()
            rect = icon.get_rect(center=(node.screen_x, node.screen_y))
            
            if is_visited:
                dim_icon = icon.copy()
                dim_icon.fill((80, 80, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(dim_icon, rect)
            elif is_available:
                p = pulse(self.time, 1.5, 0.7, 1.0)
                r = int(MAP_NODE_RADIUS * p)
                glow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
                glow_alpha = int(pulse(self.time, 1.5, 30, 80))
                pygame.draw.circle(glow_surf, (*color, glow_alpha), (r * 2, r * 2), r * 2)
                surface.blit(glow_surf, (node.screen_x - r * 2, node.screen_y - r * 2))
                surface.blit(icon, rect)
            else:
                dim_icon = icon.copy()
                dim_icon.fill((120, 120, 120, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(dim_icon, rect)
        except Exception:
            # Fallback to circle
            if is_visited:
                color = tuple(c // 3 for c in color)
                pygame.draw.circle(surface, color, (node.screen_x, node.screen_y), MAP_NODE_RADIUS)
                pygame.draw.circle(surface, DARK_GRAY, (node.screen_x, node.screen_y), MAP_NODE_RADIUS, width=2)
            elif is_available:
                p = pulse(self.time, 1.5, 0.7, 1.0)
                r = int(MAP_NODE_RADIUS * p)
                glow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
                glow_alpha = int(pulse(self.time, 1.5, 30, 80))
                pygame.draw.circle(glow_surf, (*color, glow_alpha), (r * 2, r * 2), r * 2)
                surface.blit(glow_surf, (node.screen_x - r * 2, node.screen_y - r * 2))
                pygame.draw.circle(surface, color, (node.screen_x, node.screen_y), r)
                pygame.draw.circle(surface, WHITE, (node.screen_x, node.screen_y), r, width=2)
            else:
                dim_color = tuple(c // 2 for c in color)
                pygame.draw.circle(surface, dim_color, (node.screen_x, node.screen_y), MAP_NODE_RADIUS)
                pygame.draw.circle(surface, (60, 60, 70), (node.screen_x, node.screen_y), MAP_NODE_RADIUS, width=1)

        # Label
        label = NODE_LABELS.get(node.node_type, "?")
        label_color = WHITE if is_available else GRAY
        if is_visited:
            label_color = DARK_GRAY
        draw_text(surface, label, node.screen_x, node.screen_y + MAP_NODE_RADIUS + 12,
                  size=FONT_SIZE_SMALL, color=label_color, center=True)

    def _draw_sidebar(self, surface: pygame.Surface):
        """Draw team HP and gold on the right side."""
        sidebar_x = SCREEN_WIDTH - 260
        sidebar_rect = pygame.Rect(sidebar_x, 20, 240, SCREEN_HEIGHT - 40)
        pygame.draw.rect(surface, PANEL_BG, sidebar_rect, border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, sidebar_rect, width=1, border_radius=8)

        y = 40
        draw_text(surface, "Team", sidebar_x + 120, y,
                  size=FONT_SIZE_MEDIUM, color=GOLD, center=True)
        y += 35

        for char in self.run.team:
            hp = self.run.team_hp[char.id]
            max_hp = self.run.team_max_hp[char.id]
            draw_text(surface, char.name, sidebar_x + 15, y,
                      size=FONT_SIZE_SMALL, color=WHITE)
            y += 20
            draw_health_bar(surface, sidebar_x + 15, y, 210, 16,
                            hp, max_hp, color=RED)
            y += 30

        y += 10
        try:
            coin_icon = self.game.asset_manager.load_image("UI/icons/coin.png")
            surface.blit(coin_icon, (sidebar_x + 15, y - 2))
            draw_text(surface, f"Gold: {self.run.gold}", sidebar_x + 45, y,
                      size=FONT_SIZE_MEDIUM, color=GOLD)
        except Exception:
            draw_text(surface, f"Gold: {self.run.gold}", sidebar_x + 15, y,
                      size=FONT_SIZE_MEDIUM, color=GOLD)
        y += 30

        draw_text(surface, f"Floor: {self.run.floors_cleared + 1}", sidebar_x + 15, y,
                  size=FONT_SIZE_SMALL, color=GRAY)
        y += 25

        if self.run.relics:
            draw_text(surface, "Relics:", sidebar_x + 15, y,
                      size=FONT_SIZE_SMALL, color=GRAY)
            y += 20
            for relic in self.run.relics:
                draw_text(surface, f"  {relic['name']}", sidebar_x + 15, y,
                          size=FONT_SIZE_SMALL, color=PURPLE)
                y += 18

    def _draw_overlay(self, surface: pygame.Surface):
        """Draw overlay for rest/event/shop/treasure."""
        # Darken background
        dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 150))
        surface.blit(dark, (0, 0))

        cx = SCREEN_WIDTH // 2 - 100
        cy = SCREEN_HEIGHT // 2

        if self.overlay == "rest":
            self._draw_rest_overlay(surface, cx, cy)
        elif self.overlay == "event":
            self._draw_event_overlay(surface, cx, cy)
        elif self.overlay == "shop":
            self._draw_shop_overlay(surface, cx, cy)
        elif self.overlay == "treasure":
            self._draw_treasure_overlay(surface, cx, cy)

    def _draw_rest_overlay(self, surface, cx, cy):
        panel = pygame.Rect(cx - 300, cy - 200, 600, 400)
        pygame.draw.rect(surface, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, panel, width=2, border_radius=10)

        draw_text(surface, "Rest Site", cx, cy - 150,
                  size=FONT_SIZE_LARGE, color=BLUE, center=True, font_type="title")

        if self.event_result_message:
            draw_text(surface, self.event_result_message, cx, cy,
                      size=FONT_SIZE_MEDIUM, color=GREEN, center=True)
        else:
            draw_text(surface, "Heal 30% of max HP", cx, cy - 40,
                      size=FONT_SIZE_MEDIUM, color=WHITE, center=True)
            draw_text(surface, "Click to rest", cx, cy + 20,
                      size=FONT_SIZE_SMALL, color=GRAY, center=True)

    def _draw_event_overlay(self, surface, cx, cy):
        if not self.overlay_data:
            return

        event = self.overlay_data["event"]
        panel = pygame.Rect(cx - 250, cy - 200, 500, 400)
        pygame.draw.rect(surface, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, panel, width=2, border_radius=10)

        draw_text(surface, event["name"], cx, cy - 170,
                  size=FONT_SIZE_LARGE, color=PURPLE, center=True, font_type="title")

        # Word-wrap event text
        self._draw_wrapped_text(surface, event["text"], cx - 220, cy - 120, 440,
                                FONT_SIZE_SMALL, GRAY)

        if self.event_result_message:
            draw_text(surface, self.event_result_message, cx, cy + 80,
                      size=FONT_SIZE_MEDIUM, color=GOLD, center=True)
        else:
            # Draw choice buttons
            y = cy + 20
            for i, choice in enumerate(event["choices"]):
                btn_rect = pygame.Rect(cx - 200, y, 400, 40)
                color = (50, 50, 65)
                if btn_rect.collidepoint(pygame.mouse.get_pos()):
                    color = (70, 70, 90)
                pygame.draw.rect(surface, color, btn_rect, border_radius=6)
                pygame.draw.rect(surface, PANEL_BORDER, btn_rect, width=1, border_radius=6)
                draw_text(surface, choice["text"], cx, y + 20,
                          size=FONT_SIZE_SMALL, color=WHITE, center=True)
                y += 50

    def _draw_shop_overlay(self, surface, cx, cy):
        panel = pygame.Rect(cx - 300, cy - 200, 600, 400)
        pygame.draw.rect(surface, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, panel, width=2, border_radius=10)

        # Draw NPC on the left
        try:
            npc_image = self.game.asset_manager.get_scaled("Other NPCs/Dungeon_of_the_Acoc7.png", 200, 200)
            npc_rect = npc_image.get_rect(center=(cx - 150, cy + 20))
            # Idle bob
            bob = int(math.sin(self.time * 2.0) * 5)
            npc_rect.y += bob
            surface.blit(npc_image, npc_rect)
            
            # Speech bubble
            draw_text(surface, "Got gold? I've got goods...", cx - 150, cy - 100,
                      size=FONT_SIZE_SMALL, color=WHITE, center=True, font_type="title")
        except Exception:
            pass

        draw_text(surface, "Shop", cx + 100, cy - 170,
                  size=FONT_SIZE_LARGE, color=GREEN, center=True, font_type="title")
        draw_text(surface, f"Gold: {self.run.gold}", cx + 100, cy - 130,
                  size=FONT_SIZE_MEDIUM, color=GOLD, center=True)

        tooltip_shown = False
        if self.overlay_data and "items" in self.overlay_data:
            mouse_pos = pygame.mouse.get_pos()
            y = cy - 80
            for i, item in enumerate(self.overlay_data["items"]):
                if item.get("bought"):
                    continue
                btn_rect = pygame.Rect(cx - 50, y, 300, 50)
                can_afford = self.run.gold >= item.get("cost", 0)
                is_hovered = btn_rect.collidepoint(mouse_pos)
                color = (50, 65, 50) if can_afford else (50, 40, 40)
                if is_hovered and can_afford:
                    color = (70, 90, 70)
                pygame.draw.rect(surface, color, btn_rect, border_radius=6)
                pygame.draw.rect(surface, PANEL_BORDER, btn_rect, width=1, border_radius=6)

                text = f"{item['name']} - {item.get('cost', 0)}g"
                text_color = WHITE if can_afford else GRAY
                draw_text(surface, text, cx - 40, y + 8,
                          size=FONT_SIZE_SMALL, color=text_color)
                draw_text(surface, item.get("description", ""), cx - 40, y + 28,
                          size=FONT_SIZE_SMALL, color=GRAY)

                if is_hovered:
                    self._show_item_tooltip(mouse_pos[0], mouse_pos[1], item)
                    tooltip_shown = True
                y += 60

        if not tooltip_shown:
            self.tooltip.hide()

        # Close button
        draw_text(surface, "Press ESC to leave", cx, cy + 170,
                  size=FONT_SIZE_SMALL, color=GRAY, center=True)

        self.tooltip.draw(surface)

    def _show_item_tooltip(self, mx: int, my: int, item: dict):
        lines: list[tuple[str, tuple]] = []
        rtype = item.get("type", "")
        desc = item.get("description", "")
        if desc:
            lines.append((desc, GRAY))
        if rtype == "stat_boost":
            lines.append((f"+{item.get('value', 0)} {item.get('stat', '').replace('_', ' ').title()}", GREEN))
        elif rtype == "ability_mod":
            lines.append((f"Effect: {item.get('effect', '')}", ORANGE))
        elif rtype == "relic":
            lines.append(("Applies to entire team", CYAN))
        cost = item.get("cost", 0)
        if cost > 0:
            can_afford = self.run.gold >= cost
            cost_color = GOLD if can_afford else RED
            lines.append((f"Cost: {cost}g", cost_color))
        rarity = item.get("rarity", "common")
        rarity_colors = {"common": WHITE, "uncommon": GREEN, "rare": GOLD}
        lines.append((f"Rarity: {rarity.capitalize()}", rarity_colors.get(rarity, WHITE)))
        self.tooltip.show(mx, my, item.get("name", ""), lines)

    def _draw_treasure_overlay(self, surface, cx, cy):
        panel = pygame.Rect(cx - 200, cy - 100, 400, 200)
        pygame.draw.rect(surface, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(surface, PANEL_BORDER, panel, width=2, border_radius=10)

        if self.event_result_message:
            draw_text(surface, self.event_result_message, cx, cy,
                      size=FONT_SIZE_MEDIUM, color=GOLD, center=True)
        else:
            draw_text(surface, "Treasure!", cx, cy - 60,
                      size=FONT_SIZE_LARGE, color=GOLD, center=True, font_type="title")
            draw_text(surface, "Click to open", cx, cy + 10,
                      size=FONT_SIZE_MEDIUM, color=WHITE, center=True)

    def _draw_wrapped_text(self, surface, text, x, y, max_width, size, color):
        words = text.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if len(test) * (size * 0.4) > max_width:
                draw_text(surface, line, x, y, size=size, color=color)
                y += size + 4
                line = word
            else:
                line = test
        if line:
            draw_text(surface, line, x, y, size=size, color=color)

    def _handle_node_click(self, node: MapNode):
        """Handle clicking an available node."""
        self.run.visit_node(node.id)
        self.run.floors_cleared += 1

        if node.node_type in ("combat", "start"):
            self._start_combat(node, "normal")
        elif node.node_type == "elite":
            self._start_combat(node, "elite")
        elif node.node_type == "boss":
            self._start_combat(node, "boss")
        elif node.node_type == "rest":
            self.overlay = "rest"
        elif node.node_type == "event":
            self._open_event()
        elif node.node_type == "shop":
            self._open_shop()
        elif node.node_type == "treasure":
            self.overlay = "treasure"

    def _start_combat(self, node: MapNode, tier: str):
        self.game.state_machine.transition(
            GameState.COMBAT,
            tier=tier,
            difficulty=node.difficulty,
        )

    def _open_event(self):
        am = self.game.asset_manager
        events = am.load_json("events.json")
        team_ids = {c.id for c in self.run.team}
        eligible = [e for e in events
                    if "requires_char" not in e or e["requires_char"] in team_ids]
        event = random.choice(eligible) if eligible else random.choice(events)
        self.overlay = "event"
        self.overlay_data = {"event": event}

    def _open_shop(self):
        am = self.game.asset_manager
        rewards = am.load_json("rewards.json")
        # Pick 3-4 random items for the shop
        items = random.sample(rewards, min(4, len(rewards)))
        # Add cost to items
        shop_items = []
        for item in items:
            shop_item = dict(item)
            shop_item["bought"] = False
            shop_items.append(shop_item)
        self.overlay = "shop"
        self.overlay_data = {"items": shop_items}

    def _handle_rest(self):
        self.run.heal_team(0.3)
        self.event_result_message = "Your team rests and heals."
        self.event_result_timer = 1.5

    def _handle_treasure(self):
        gold = random.randint(15, 30)
        self.run.gold += gold
        self.event_result_message = f"Found {gold} gold!"
        self.event_result_timer = 1.5

    def _handle_event_choice(self, choice_index: int):
        event = self.overlay_data["event"]
        choice = event["choices"][choice_index]
        outcomes = choice["outcomes"]

        # Weighted random outcome
        weights = [o["weight"] for o in outcomes]
        outcome = random.choices(outcomes, weights=weights, k=1)[0]

        otype = outcome.get("type", "none")
        if otype == "heal":
            for char in self.run.team:
                hp = self.run.team_hp[char.id]
                max_hp = self.run.team_max_hp[char.id]
                self.run.team_hp[char.id] = min(max_hp, hp + outcome["value"])
        elif otype == "damage":
            for char in self.run.team:
                self.run.team_hp[char.id] = max(1, self.run.team_hp[char.id] - outcome["value"])
        elif otype == "gold":
            self.run.gold += outcome["value"]
        elif otype == "stat_boost":
            alive = self.run.get_alive_team()
            if alive:
                target = random.choice(alive)
                self.run.apply_stat_boost(target.id, outcome["stat"], outcome["value"])
        elif otype == "trade":
            alive = self.run.get_alive_team()
            if alive:
                target = random.choice(alive)
                hp_cost = outcome.get("hp_cost", 0)
                self.run.team_hp[target.id] = max(1, self.run.team_hp[target.id] - hp_cost)
                self.run.apply_stat_boost(target.id, outcome["stat"], outcome["value"])
        elif otype == "ability_unlock":
            char_id = outcome.get("char_id", "")
            ability_id = outcome.get("ability_id", "")
            hp_cost = outcome.get("hp_cost", 0)
            if char_id and ability_id:
                self.run.unlock_ability(char_id, ability_id)
                if hp_cost and char_id in self.run.team_hp:
                    self.run.team_hp[char_id] = max(1, self.run.team_hp[char_id] - hp_cost)

        self.event_result_message = outcome.get("message", "Something happened.")
        self.event_result_timer = 2.0

    def _handle_shop_buy(self, item_index: int):
        items = self.overlay_data["items"]
        # Find the nth non-bought item
        visible_idx = 0
        for item in items:
            if item.get("bought"):
                continue
            if visible_idx == item_index:
                cost = item.get("cost", 0)
                if self.run.gold >= cost:
                    self.run.gold -= cost
                    item["bought"] = True
                    self._apply_reward(item)
                return
            visible_idx += 1

    def _apply_reward(self, reward: dict):
        rtype = reward.get("type", "")
        if rtype == "stat_boost":
            alive = self.run.get_alive_team()
            if alive:
                target = random.choice(alive)
                self.run.apply_stat_boost(target.id, reward["stat"], reward["value"])
        elif rtype == "ability_mod":
            alive = self.run.get_alive_team()
            if alive:
                target = random.choice(alive)
                self.run.apply_ability_mod(target.id, reward["effect"])
        elif rtype == "ability_unlock":
            char_id = reward.get("char_id", "")
            ability_id = reward.get("ability_id", "")
            if char_id and ability_id:
                self.run.unlock_ability(char_id, ability_id)
        elif rtype == "relic":
            self.run.apply_relic(reward)

    def _draw_menu_confirm(self, surface):
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

        self._menu_yes_rect = pygame.Rect(cx - 150, cy + 20, 130, 40)
        color_yes = (70, 50, 50)
        if self._menu_yes_rect.collidepoint(pygame.mouse.get_pos()):
            color_yes = (100, 60, 60)
        pygame.draw.rect(surface, color_yes, self._menu_yes_rect, border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, self._menu_yes_rect, width=1, border_radius=6)
        draw_text(surface, "Yes, Leave", cx - 85, cy + 40,
                  size=FONT_SIZE_SMALL, color=RED, center=True)

        self._menu_no_rect = pygame.Rect(cx + 20, cy + 20, 130, 40)
        color_no = (50, 60, 50)
        if self._menu_no_rect.collidepoint(pygame.mouse.get_pos()):
            color_no = (60, 80, 60)
        pygame.draw.rect(surface, color_no, self._menu_no_rect, border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, self._menu_no_rect, width=1, border_radius=6)
        draw_text(surface, "Resume", cx + 85, cy + 40,
                  size=FONT_SIZE_SMALL, color=GREEN, center=True)

    def handle_event(self, event: pygame.event.Event):
        # Menu confirm handling
        if self.show_menu_confirm:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.show_menu_confirm = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if hasattr(self, '_menu_yes_rect') and self._menu_yes_rect.collidepoint(mx, my):
                    self.game.state_machine.transition(GameState.TITLE)
                elif hasattr(self, '_menu_no_rect') and self._menu_no_rect.collidepoint(mx, my):
                    self.show_menu_confirm = False
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.overlay:
                self.overlay = None
                self.overlay_data = None
                self.event_result_message = None
                return
            self.show_menu_confirm = True
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Handle overlay clicks
            if self.overlay == "rest" and not self.event_result_message:
                self._handle_rest()
                return
            elif self.overlay == "treasure" and not self.event_result_message:
                self._handle_treasure()
                return
            elif self.overlay == "event" and not self.event_result_message:
                cx = SCREEN_WIDTH // 2 - 100
                cy = SCREEN_HEIGHT // 2
                y = cy + 20
                event_data = self.overlay_data["event"]
                for i, choice in enumerate(event_data["choices"]):
                    btn_rect = pygame.Rect(cx - 200, y, 400, 40)
                    if btn_rect.collidepoint(pos):
                        self._handle_event_choice(i)
                        return
                    y += 50
                return
            elif self.overlay == "shop":
                cx = SCREEN_WIDTH // 2 - 100
                cy = SCREEN_HEIGHT // 2
                y = cy - 80
                items = self.overlay_data.get("items", [])
                visible_idx = 0
                for item in items:
                    if item.get("bought"):
                        continue
                    btn_rect = pygame.Rect(cx - 50, y, 300, 50)
                    if btn_rect.collidepoint(pos):
                        self._handle_shop_buy(visible_idx)
                        return
                    y += 60
                    visible_idx += 1
                return
            elif self.overlay:
                return

            # Handle map node clicks
            for node in self.run.map_nodes:
                if node.id in self.run.available_node_ids:
                    dx = pos[0] - node.screen_x
                    dy = pos[1] - node.screen_y
                    if dx * dx + dy * dy <= MAP_NODE_RADIUS * MAP_NODE_RADIUS * 4:
                        self._handle_node_click(node)
                        return

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
from src.map.path_renderer import (
    bezier_points, control_point, draw_path, draw_glowing_path,
)
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GRAY, GOLD, RED, GREEN, BLUE,
    DARK_GRAY, ORANGE, PURPLE, CYAN, PANEL_BG, PANEL_BORDER,
    FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE, FONT_SIZE_TITLE,
    MAP_NODE_RADIUS, MAP_PATH_GLOW_MIN, MAP_PATH_GLOW_MAX,
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

# Map sets mapping
NODE_TO_SET = {
    "combat": "set_14",
    "elite": "set_12",
    "shop": "set_15",
    "treasure": "set_01",
    "rest": "set_08",
    "event": "set_04",
    "boss": "set_10",
    "start": "set_17",
}


class MapState(BaseState):
    def enter(self, **kwargs):
        try:
            print("MapState: Entering...")
            self.time = 0.0

            # Initialize run if team is passed (first entry)
            if "team" in kwargs:
                print("MapState: Initializing run...")
                map_nodes = generate_map()
                self.game.run_manager = RunManager(kwargs["team"], map_nodes)
                
                # Start background music
                try:
                    if pygame.mixer.get_init():
                        print("MapState: Loading music...")
                        # Use renamed file without spaces
                        pygame.mixer.music.load("audio/music/break_their_will.ogg")
                        # Volume controlled by global settings
                        vol = getattr(self.game.settings, 'volume', 0.3)
                        if getattr(self.game.settings, 'muted', False):
                            vol = 0.0
                        pygame.mixer.music.set_volume(vol)
                        pygame.mixer.music.play(-1)
                        print("MapState: Music playing.")
                except Exception as e:
                    print(f"Could not load music: {e}")

            self.run = self.game.run_manager
            
            # Safety check for run manager
            if not self.run:
                print("Error: MapState entered without an active RunManager")
                self.game.state_machine.transition(GameState.TITLE)
                return

            # Pre-render paths
            print("MapState: Rendering paths...")
            self._bridge_cache_surface = None
            self._available_connections = []
            self._render_bridges()
            print("MapState: Enter complete.")

            self.overlay = None
            self.overlay_data = None
            self.event_result_message = None
            self.event_result_timer = 0.0
            self.show_menu_confirm = False
            self.tooltip = Tooltip()
        except Exception as e:
            print(f"MapState Enter Crash: {e}")
            import traceback
            traceback.print_exc()
            # If enter crashes, we might need a fallback or just let draw() handle the error state
            self._enter_error = e

    def _render_bridges(self):
        """Pre-render static (visited + locked) paths as bezier curves."""
        self._bridge_cache_surface = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._available_connections: list[tuple] = []

        if not self.run or not self.run.map_nodes:
            return

        for node in self.run.map_nodes:
            for cid in node.connections:
                if cid >= len(self.run.map_nodes):
                    continue
                target = self.run.map_nodes[cid]
                ctrl = control_point(node, target)
                pts = bezier_points(
                    (node.screen_x, node.screen_y), ctrl,
                    (target.screen_x, target.screen_y))

                state = self._classify_connection(node, target)
                if state == "available":
                    self._available_connections.append(pts)
                else:
                    draw_path(self._bridge_cache_surface, pts, state)

    def _classify_connection(self, source, target) -> str:
        """Return 'visited', 'available', or 'locked'."""
        if source.visited and target.visited:
            return "visited"
        if target.id in self.run.available_node_ids:
            return "available"
        return "locked"

    def update(self, dt: float):
        self.time += dt
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
                # Even lighter tint (120 instead of 160) to avoid "Black Screen" look
                tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                tint.fill((5, 5, 20, 120))
                bg.blit(tint, (0, 0))
            except Exception:
                bg.fill((40, 40, 55))
            self._bg_cache = bg
        return self._bg_cache

    def draw(self, surface: pygame.Surface):
        try:
            surface.blit(self._get_bg(), (0, 0))

            # Draw pre-rendered static paths (visited + locked)
            if self._bridge_cache_surface:
                surface.blit(self._bridge_cache_surface, (0, 0))

            # Draw available paths with animated glow
            glow_alpha = int(pulse(self.time, 1.5, MAP_PATH_GLOW_MIN,
                                   MAP_PATH_GLOW_MAX))
            for pts in self._available_connections:
                draw_glowing_path(surface, pts, glow_alpha)

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
        except Exception as e:
            surface.fill((20, 0, 0))
            draw_text(surface, f"Draw Error: {e}", 20, 20, size=20, color=RED)
            import traceback
            trace = traceback.format_exc().splitlines()
            for i, line in enumerate(trace[-10:]):
                draw_text(surface, line, 20, 50 + i * 20, size=14, color=WHITE)

    def _draw_node(self, surface: pygame.Surface, node: MapNode):
        am = self.game.asset_manager
        is_available = node.id in self.run.available_node_ids
        is_visited = node.visited

        try:
            # Gameplay Icon in the Center
            icon_name = node.node_type if node.node_type != "start" else "combat"
            icon = am.load_image(f"UI/icons/node_{icon_name}.png")

            # Larger icon for better readability
            icon_size = 32 if node.node_type != "boss" else 48
            icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))

            if is_visited or not is_available:
                icon = icon.copy()
                icon.fill((120, 120, 140, 255), special_flags=pygame.BLEND_RGBA_MULT)

            icon_rect = icon.get_rect(center=(node.screen_x, node.screen_y))
            surface.blit(icon, icon_rect)

            if is_available:
                # Breathing Glow for available path
                p = pulse(self.time, 1.5, 0, 80)
                glow_size = icon_size + 12
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                color = NODE_COLORS.get(node.node_type, GOLD)
                pygame.draw.rect(glow_surf, (*color, int(p)), glow_surf.get_rect(), border_radius=8, width=2)
                surface.blit(glow_surf, (node.screen_x - glow_size//2, node.screen_y - glow_size//2))

        except Exception:
            # Emergency Fallback to simple circle
            pygame.draw.circle(surface, NODE_COLORS.get(node.node_type, GRAY), (node.screen_x, node.screen_y), MAP_NODE_RADIUS)

        # Label below
        label = NODE_LABELS.get(node.node_type, "?")
        label_color = WHITE if is_available else GRAY
        if is_visited: label_color = DARK_GRAY
        draw_text(surface, label, node.screen_x, node.screen_y + 35, size=14, color=label_color, center=True)
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
            
            # Heart icon for health
            try:
                heart_icon = self.game.asset_manager.load_image("UI/icons/heart.png")
                surface.blit(heart_icon, (sidebar_x + 15, y - 2))
                draw_text(surface, char.name, sidebar_x + 45, y,
                          size=FONT_SIZE_SMALL, color=WHITE)
            except Exception:
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
            npc_image = self.game.asset_manager.get_scaled("Other NPCs/Pepruvia_NPC_Shop.png", 200, 200)
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
                    # Check within a reasonable interaction radius (30px)
                    if dx * dx + dy * dy <= 30 * 30:
                        self._handle_node_click(node)
                        return

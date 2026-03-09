"""Post-combat reward selection — pick 1 of 3."""

import random
import pygame
from src.states.base_state import BaseState
from src.core.state_machine import GameState
from src.ui.text_renderer import draw_text
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GRAY, GOLD, GREEN, BLUE,
    PANEL_BG, PANEL_BORDER, PURPLE, ORANGE,
    FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE, FONT_SIZE_TITLE,
)

RARITY_COLORS = {
    "common": WHITE,
    "uncommon": GREEN,
    "rare": GOLD,
}

RARITY_WEIGHTS = {
    "common": 60,
    "uncommon": 30,
    "rare": 10,
}


class RewardState(BaseState):
    def enter(self, **kwargs):
        run = self.game.run_manager
        am = self.game.asset_manager

        # Generate 3 reward options
        all_rewards = am.load_json("rewards.json")
        self.rewards = self._generate_rewards(all_rewards, 3)

        # Card rects for clicking
        self.card_rects: list[pygame.Rect] = []
        card_width = 240
        card_height = 200
        total_width = 3 * card_width + 2 * 30
        start_x = (SCREEN_WIDTH - total_width) // 2
        for i in range(3):
            x = start_x + i * (card_width + 30)
            self.card_rects.append(pygame.Rect(x, 250, card_width, card_height))

        self.selected = None
        self.hovered = -1

        # Sub-selection for stat boosts (pick which character)
        self.awaiting_char_select = False
        self.char_rects: list[pygame.Rect] = []

    def _generate_rewards(self, all_rewards: list[dict], count: int) -> list[dict]:
        """Generate weighted random rewards."""
        # Group by rarity
        by_rarity: dict[str, list[dict]] = {}
        for r in all_rewards:
            rarity = r.get("rarity", "common")
            by_rarity.setdefault(rarity, []).append(r)

        result = []
        for _ in range(count):
            # Pick rarity
            rarities = list(RARITY_WEIGHTS.keys())
            weights = [RARITY_WEIGHTS[r] for r in rarities]
            rarity = random.choices(rarities, weights=weights, k=1)[0]

            pool = by_rarity.get(rarity, by_rarity.get("common", []))
            if pool:
                reward = random.choice(pool)
                result.append(dict(reward))
            elif all_rewards:
                result.append(dict(random.choice(all_rewards)))

        return result

    def _apply_reward(self, reward: dict, char_id: str | None = None):
        run = self.game.run_manager
        rtype = reward.get("type", "")

        if rtype == "stat_boost" and char_id:
            run.apply_stat_boost(char_id, reward["stat"], reward["value"])
        elif rtype == "ability_mod" and char_id:
            run.apply_ability_mod(char_id, reward["effect"])
        elif rtype == "relic":
            run.apply_relic(reward)
        elif rtype == "ability_unlock":
            target_char = reward.get("char_id", "")
            ability_id = reward.get("ability_id", "")
            if target_char and ability_id:
                run.unlock_ability(target_char, ability_id)

        # Return to map
        self.game.state_machine.transition(GameState.MAP)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill((15, 12, 20))

        draw_text(surface, "Choose a Reward", SCREEN_WIDTH // 2, 60,
                  size=FONT_SIZE_TITLE, color=GOLD, center=True, font_type="title")

        gold_earned = sum(e.gold_reward for e in [])  # Already added in combat
        draw_text(surface, f"Gold: {self.game.run_manager.gold}",
                  SCREEN_WIDTH // 2, 120,
                  size=FONT_SIZE_MEDIUM, color=GOLD, center=True)

        # Draw reward cards
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = -1

        for i, (reward, rect) in enumerate(zip(self.rewards, self.card_rects)):
            is_hovered = rect.collidepoint(mouse_pos)
            if is_hovered:
                self.hovered = i

            rarity = reward.get("rarity", "common")
            rarity_color = RARITY_COLORS.get(rarity, WHITE)

            # Card background
            bg = (50, 50, 65) if is_hovered else PANEL_BG
            pygame.draw.rect(surface, bg, rect, border_radius=10)
            border_color = rarity_color if is_hovered else PANEL_BORDER
            pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)

            # Rarity label
            draw_text(surface, rarity.capitalize(), rect.centerx, rect.y + 20,
                      size=FONT_SIZE_SMALL, color=rarity_color, center=True)

            # Reward name
            draw_text(surface, reward["name"], rect.centerx, rect.y + 55,
                      size=FONT_SIZE_MEDIUM, color=WHITE, center=True)

            # Type indicator
            rtype = reward.get("type", "")
            type_color = GREEN if rtype == "stat_boost" else (ORANGE if rtype == "ability_mod" else PURPLE)
            draw_text(surface, rtype.replace("_", " ").title(),
                      rect.centerx, rect.y + 85,
                      size=FONT_SIZE_SMALL, color=type_color, center=True)

            # Description
            desc = reward.get("description", "")
            self._draw_wrapped(surface, desc, rect.x + 15, rect.y + 110,
                               rect.width - 30, FONT_SIZE_SMALL, GRAY)

        # Character selection sub-prompt
        if self.awaiting_char_select:
            self._draw_char_select(surface)

    def _draw_wrapped(self, surface, text, x, y, max_width, size, color):
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

    def _draw_char_select(self, surface: pygame.Surface):
        """Draw character selection overlay for stat boosts."""
        dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 150))
        surface.blit(dark, (0, 0))

        draw_text(surface, "Apply to which character?",
                  SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80,
                  size=FONT_SIZE_LARGE, color=GOLD, center=True, font_type="title")

        run = self.game.run_manager
        alive = run.get_alive_team()
        self.char_rects = []

        total_width = len(alive) * 200 + (len(alive) - 1) * 20
        start_x = (SCREEN_WIDTH - total_width) // 2
        y = SCREEN_HEIGHT // 2 - 20

        for i, char in enumerate(alive):
            rect = pygame.Rect(start_x + i * 220, y, 200, 80)
            self.char_rects.append(rect)

            is_hovered = rect.collidepoint(pygame.mouse.get_pos())
            bg = (60, 60, 75) if is_hovered else PANEL_BG
            pygame.draw.rect(surface, bg, rect, border_radius=8)
            border = GOLD if is_hovered else PANEL_BORDER
            pygame.draw.rect(surface, border, rect, width=2, border_radius=8)

            draw_text(surface, char.name, rect.centerx, rect.y + 20,
                      size=FONT_SIZE_MEDIUM, color=WHITE, center=True)
            draw_text(surface, char.role.capitalize(), rect.centerx, rect.y + 50,
                      size=FONT_SIZE_SMALL, color=GRAY, center=True)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.awaiting_char_select:
                run = self.game.run_manager
                alive = run.get_alive_team()
                for i, rect in enumerate(self.char_rects):
                    if rect.collidepoint(event.pos) and i < len(alive):
                        self._apply_reward(self.selected, alive[i].id)
                        return
            else:
                for i, rect in enumerate(self.card_rects):
                    if rect.collidepoint(event.pos) and i < len(self.rewards):
                        reward = self.rewards[i]
                        rtype = reward.get("type", "")
                        if rtype == "relic":
                            # Apply immediately (team-wide)
                            self._apply_reward(reward)
                        else:
                            # Need character selection
                            self.selected = reward
                            self.awaiting_char_select = True
                        return

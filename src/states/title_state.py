"""Title screen state."""

import pygame
from src.states.base_state import BaseState
from src.ui.button import Button
from src.ui.text_renderer import draw_text
from src.core.state_machine import GameState
from src.animation.tween import pulse
from src.animation.torch_animator import TorchAnimator
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GOLD, GRAY,
    PANEL_BORDER,
    FONT_SIZE_TITLE, FONT_SIZE_SMALL, FONT_SIZE_MEDIUM,
)

BG_PATH = "Backgrounds/gothic_city/gothic_entrance.png"


class TitleState(BaseState):
    def enter(self, **kwargs):
        self.time = 0.0
        cx = SCREEN_WIDTH // 2
        self.start_button = Button(
            cx - 100, 420, "Start Game",
            on_click=self._on_start,
        )
        self.quit_button = Button(
            cx - 100, 490, "Quit",
            on_click=self._on_quit,
        )
        self._bg = self._render_bg()
        self.torch_animator = TorchAnimator(self.game.asset_manager)

    def _render_bg(self) -> pygame.Surface:
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        try:
            img = self.game.asset_manager.get_scaled(BG_PATH, SCREEN_WIDTH, SCREEN_HEIGHT)
            bg.blit(img, (0, 0))
        except Exception:
            bg.fill((15, 12, 20))

        # Heavy dark overlay with purple tint for fantasy feel
        tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        tint.fill((10, 5, 20, 180))
        bg.blit(tint, (0, 0))

        # Vignette
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(100):
            alpha = int(150 * (1.0 - i / 100))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (0, i), (SCREEN_WIDTH, i))
            pygame.draw.line(vignette, (0, 0, 0, alpha),
                             (0, SCREEN_HEIGHT - 1 - i), (SCREEN_WIDTH, SCREEN_HEIGHT - 1 - i))
        for i in range(80):
            alpha = int(100 * (1.0 - i / 80))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (i, 0), (i, SCREEN_HEIGHT))
            pygame.draw.line(vignette, (0, 0, 0, alpha),
                             (SCREEN_WIDTH - 1 - i, 0), (SCREEN_WIDTH - 1 - i, SCREEN_HEIGHT))
        bg.blit(vignette, (0, 0))
        return bg

    def _on_start(self):
        self.game.state_machine.transition(GameState.TEAM_SELECT)

    def _on_quit(self):
        self.game.running = False

    def update(self, dt: float):
        self.time += dt
        self.torch_animator.update(dt)

    def draw(self, surface: pygame.Surface):
        surface.blit(self._bg, (0, 0))
        self.torch_animator.draw(surface, "gothic_entrance")
        cx = SCREEN_WIDTH // 2

        # Title
        draw_text(surface, "Dungeon of the Acoc", cx, 180,
                  size=FONT_SIZE_TITLE, color=GOLD, center=True, font_type="title")

        # Decorative line
        line_y = 230
        line_w = 250
        pygame.draw.line(surface, PANEL_BORDER, (cx - line_w, line_y), (cx + line_w, line_y), 2)
        diamond = [(cx, line_y - 5), (cx + 5, line_y), (cx, line_y + 5), (cx - 5, line_y)]
        pygame.draw.polygon(surface, GOLD, diamond)

        # Subtitle
        draw_text(surface, "A Gothic Auto-Battler", cx, 260,
                  size=FONT_SIZE_SMALL, color=GRAY, center=True)

        # Pulsing prompt
        prompt_alpha = int(pulse(self.time, 1.0, 100, 255))
        draw_text(surface, "Choose your fate", cx, 340,
                  size=FONT_SIZE_MEDIUM, color=(*GOLD[:3], prompt_alpha), center=True,
                  font_type="title")

        self.start_button.draw(surface)
        self.quit_button.draw(surface)

    def handle_event(self, event: pygame.event.Event):
        self.start_button.handle_event(event)
        self.quit_button.handle_event(event)

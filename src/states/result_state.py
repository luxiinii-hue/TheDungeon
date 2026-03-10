"""Win/Lose result screen with run summary."""

import pygame
from src.states.base_state import BaseState
from src.core.state_machine import GameState
from src.ui.button import Button
from src.ui.text_renderer import draw_text
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GOLD, RED, GRAY,
    PANEL_BORDER,
    FONT_SIZE_TITLE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL,
)


class ResultState(BaseState):
    def enter(self, **kwargs):
        self.result = kwargs.get("result", "lose")
        self.fade_alpha = 0.0

        cx = SCREEN_WIDTH // 2
        self.title_btn = Button(
            cx - 100, 550, "Return to Title",
            on_click=self._on_title,
        )
        self._bg = self._render_bg()

    def _render_bg(self) -> pygame.Surface:
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        try:
            img = self.game.asset_manager.get_scaled(
                "Backgrounds/gothic_city/gothic_entrance.png",
                SCREEN_WIDTH, SCREEN_HEIGHT)
            bg.blit(img, (0, 0))
        except Exception:
            bg.fill((15, 12, 20))

        # Heavy dark overlay — result text needs to be very readable
        tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        tint.fill((5, 5, 15, 210))
        bg.blit(tint, (0, 0))

        # Vignette
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(100):
            alpha = int(150 * (1.0 - i / 100))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (0, i), (SCREEN_WIDTH, i))
            pygame.draw.line(vignette, (0, 0, 0, alpha),
                             (0, SCREEN_HEIGHT - 1 - i), (SCREEN_WIDTH, SCREEN_HEIGHT - 1 - i))
        bg.blit(vignette, (0, 0))

        return bg

    def _on_title(self):
        self.game.run_manager = None
        self.game.state_machine.transition(GameState.TITLE)

    def update(self, dt: float):
        if self.fade_alpha < 255:
            self.fade_alpha = min(255, self.fade_alpha + dt * 300)

    def draw(self, surface: pygame.Surface):
        surface.blit(self._bg, (0, 0))

        alpha = int(self.fade_alpha)
        cx = SCREEN_WIDTH // 2

        if self.result == "win":
            title = "VICTORY!"
            color = GOLD
            subtitle = "The city has been liberated!"
        else:
            title = "DEFEATED"
            color = RED
            subtitle = "The city claims another soul."

        title_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        draw_text(title_surf, title, cx, 150,
                  size=FONT_SIZE_TITLE, color=(*color, alpha), center=True, font_type="title")
        draw_text(title_surf, subtitle, cx, 240,
                  size=FONT_SIZE_MEDIUM, color=(*GRAY, alpha), center=True)

        # Run summary
        run = getattr(self.game, "run_manager", None)
        if run:
            y = 310
            draw_text(title_surf, "Run Summary", cx, y,
                      size=FONT_SIZE_MEDIUM, color=(*WHITE, alpha), center=True)
            y += 40
            draw_text(title_surf, f"Floors Cleared: {run.floors_cleared}",
                      cx, y, size=FONT_SIZE_SMALL, color=(*GRAY, alpha), center=True)
            y += 25
            draw_text(title_surf, f"Enemies Defeated: {run.enemies_defeated}",
                      cx, y, size=FONT_SIZE_SMALL, color=(*GRAY, alpha), center=True)
            y += 25
            draw_text(title_surf, f"Gold Earned: {run.gold}",
                      cx, y, size=FONT_SIZE_SMALL, color=(*GOLD, alpha), center=True)
            y += 25

            if run.relics:
                draw_text(title_surf, f"Relics: {len(run.relics)}",
                          cx, y, size=FONT_SIZE_SMALL, color=(*GRAY, alpha), center=True)
                y += 25

            # Team status
            y += 10
            draw_text(title_surf, "Team:", cx, y,
                      size=FONT_SIZE_SMALL, color=(*WHITE, alpha), center=True)
            y += 25
            for char in run.team:
                hp = run.team_hp.get(char.id, 0)
                status = f"{char.name} - {'Alive' if hp > 0 else 'Fallen'}"
                s_color = (*GOLD, alpha) if hp > 0 else (*RED, alpha)
                draw_text(title_surf, status, cx, y,
                          size=FONT_SIZE_SMALL, color=s_color, center=True)
                y += 22

        surface.blit(title_surf, (0, 0))

        if self.fade_alpha >= 200:
            self.title_btn.draw(surface)

    def handle_event(self, event: pygame.event.Event):
        if self.fade_alpha >= 200:
            self.title_btn.handle_event(event)

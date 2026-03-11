"""Global settings overlay for volume control."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, PANEL_BG, PANEL_BORDER, WHITE, GOLD, GRAY, RED, GREEN, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE
from src.ui.text_renderer import draw_text
from src.ui.icons import get_icon

class SettingsOverlay:
    def __init__(self):
        self.active = False
        self.volume = 0.3
        self.muted = False
        
        # Dimensions
        self.width = 400
        self.height = 300
        self.rect = pygame.Rect((SCREEN_WIDTH - self.width) // 2, (SCREEN_HEIGHT - self.height) // 2, self.width, self.height)
        
        # Gear icon rect
        self.gear_rect = pygame.Rect(SCREEN_WIDTH - 50, 10, 40, 40)
        
        # UI Rects
        self.slider_bg = pygame.Rect(self.rect.x + 50, self.rect.y + 120, 300, 20)
        self.slider_handle = pygame.Rect(0, 0, 16, 40)
        self._update_handle()
        
        self.mute_btn = pygame.Rect(self.rect.centerx - 60, self.rect.y + 180, 120, 40)
        self.close_btn = pygame.Rect(self.rect.centerx - 60, self.rect.y + 240, 120, 40)
        
        self.dragging = False

    def _update_handle(self):
        self.slider_handle.centerx = self.slider_bg.x + int(self.volume * self.slider_bg.width)
        self.slider_handle.centery = self.slider_bg.centery

    def set_volume(self, vol: float):
        self.volume = max(0.0, min(1.0, vol))
        if pygame.mixer.get_init() and not self.muted:
            pygame.mixer.music.set_volume(self.volume)
        self._update_handle()

    def toggle_mute(self):
        self.muted = not self.muted
        if pygame.mixer.get_init():
            if self.muted:
                pygame.mixer.music.set_volume(0.0)
            else:
                pygame.mixer.music.set_volume(self.volume)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the event was consumed by the overlay."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.active and self.gear_rect.collidepoint(event.pos):
                self.active = True
                return True
                
            if self.active:
                if self.close_btn.collidepoint(event.pos):
                    self.active = False
                elif self.mute_btn.collidepoint(event.pos):
                    self.toggle_mute()
                elif self.slider_bg.collidepoint(event.pos) or self.slider_handle.collidepoint(event.pos):
                    self.dragging = True
                    self._handle_drag(event.pos[0])
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._handle_drag(event.pos[0])
                return True
                
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.active:
                self.active = False
                return True
                
        return self.active

    def _handle_drag(self, mouse_x: int):
        rel_x = mouse_x - self.slider_bg.x
        vol = rel_x / self.slider_bg.width
        self.set_volume(vol)

    def draw(self, surface: pygame.Surface):
        # Draw gear icon
        gear_img = get_icon("gear", size=(32, 32))
        if gear_img:
            # Draw a circle behind it to make it pop
            pygame.draw.circle(surface, (30, 30, 40), self.gear_rect.center, 20)
            pygame.draw.circle(surface, GOLD, self.gear_rect.center, 20, 2)
            surface.blit(gear_img, (self.gear_rect.x + 4, self.gear_rect.y + 4))
        else:
            pygame.draw.circle(surface, (30, 30, 40), self.gear_rect.center, 20)
            pygame.draw.circle(surface, GOLD, self.gear_rect.center, 20, 2)
            draw_text(surface, "O", self.gear_rect.centerx, self.gear_rect.centery, size=24, color=GOLD, center=True, font_type="title")

        if not self.active:
            return

        # Dark overlay
        dark = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 180))
        surface.blit(dark, (0, 0))

        # Panel
        pygame.draw.rect(surface, PANEL_BG, self.rect, border_radius=15)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, width=3, border_radius=15)

        # Inner gothic details
        inner_rect = self.rect.inflate(-20, -20)
        pygame.draw.rect(surface, (20, 20, 25), inner_rect, border_radius=10)
        pygame.draw.rect(surface, (50, 50, 60), inner_rect, width=1, border_radius=10)

        draw_text(surface, "Settings", self.rect.centerx, self.rect.y + 40, size=FONT_SIZE_LARGE, color=GOLD, center=True, font_type="title")

        # Slider
        draw_text(surface, "Music Volume", self.rect.centerx, self.rect.y + 90, size=FONT_SIZE_MEDIUM, color=GRAY, center=True)
        pygame.draw.rect(surface, (10, 10, 15), self.slider_bg, border_radius=10)

        # Fill part of slider
        fill_rect = pygame.Rect(self.slider_bg.x, self.slider_bg.y, int(self.volume * self.slider_bg.width), self.slider_bg.height)
        if fill_rect.width > 0:
            pygame.draw.rect(surface, (120, 40, 40) if self.muted else (140, 100, 180), fill_rect, border_radius=10)

        pygame.draw.rect(surface, (80, 80, 100), self.slider_bg, width=2, border_radius=10)

        # Handle (diamond shaped)
        diamond = [
            (self.slider_handle.centerx, self.slider_handle.top),
            (self.slider_handle.right, self.slider_handle.centery),
            (self.slider_handle.centerx, self.slider_handle.bottom),
            (self.slider_handle.left, self.slider_handle.centery),
        ]
        pygame.draw.polygon(surface, GOLD, diamond)
        pygame.draw.polygon(surface, WHITE, diamond, 1)

        # Mute button
        mute_color = (60, 30, 30) if self.muted else (40, 40, 50)
        pygame.draw.rect(surface, mute_color, self.mute_btn, border_radius=5)
        pygame.draw.rect(surface, PANEL_BORDER, self.mute_btn, width=1, border_radius=5)

        music_img = get_icon("music", size=(32, 32))
        if music_img:
            img_to_draw = music_img
            if self.muted:
                img_to_draw = music_img.copy()
                img_to_draw.fill(RED, special_flags=pygame.BLEND_RGB_MULT)
            surface.blit(img_to_draw, (self.mute_btn.centerx - 16, self.mute_btn.centery - 16))
        else:
            draw_text(surface, "Unmute" if self.muted else "Mute", self.mute_btn.centerx, self.mute_btn.centery, size=FONT_SIZE_MEDIUM, color=WHITE, center=True)

        # Close button
        pygame.draw.rect(surface, (50, 50, 60), self.close_btn, border_radius=5)
        pygame.draw.rect(surface, PANEL_BORDER, self.close_btn, width=1, border_radius=5)

        x_img = get_icon("x", size=(32, 32))
        if x_img:
            surface.blit(x_img, (self.close_btn.centerx - 16, self.close_btn.centery - 16))
        else:
            draw_text(surface, "Close", self.close_btn.centerx, self.close_btn.centery, size=FONT_SIZE_MEDIUM, color=WHITE, center=True)
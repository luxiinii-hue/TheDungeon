"""Styled text utility."""

import os
import pygame
from config import WHITE, FONT_TITLE_PATH, FONT_BODY_PATH


_font_cache: dict[tuple[int, str], pygame.font.Font] = {}


def get_font(size: int, font_type: str = "body") -> pygame.font.Font:
    key = (size, font_type)
    if key not in _font_cache:
        path = FONT_TITLE_PATH if font_type == "title" else FONT_BODY_PATH
        if os.path.exists(path):
            _font_cache[key] = pygame.font.Font(path, size)
        else:
            _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]


def draw_text(surface: pygame.Surface, text: str, x: int, y: int,
              size: int = 24, color=WHITE, center: bool = False,
              font_type: str = "body", shadow: bool = False):
    font = get_font(size, font_type)
    text_surf = font.render(text, True, color)
    if center:
        rect = text_surf.get_rect(center=(x, y))
    else:
        rect = text_surf.get_rect(topleft=(x, y))
        
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect()
        if center:
            shadow_rect.center = (rect.centerx + 1, rect.centery + 1)
        else:
            shadow_rect.topleft = (rect.x + 1, rect.y + 1)
        surface.blit(shadow_surf, shadow_rect)
        
    surface.blit(text_surf, rect)
    return rect

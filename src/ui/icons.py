"""Icon loading and caching utility."""

import os
import pygame
from config import ASSET_DIR

_icon_cache: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}

def get_icon(name: str, size: tuple[int, int] = (24, 24)) -> pygame.Surface | None:
    """Load an icon from the character assets/UI/icons folder, scale it, and cache it."""
    key = (name, size)
    if key not in _icon_cache:
        path = os.path.join(ASSET_DIR, "UI", "icons", f"{name}.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                if img.get_size() != size:
                    img = pygame.transform.smoothscale(img, size)
                _icon_cache[key] = img
            except pygame.error:
                _icon_cache[key] = None
        else:
            _icon_cache[key] = None
    return _icon_cache[key]

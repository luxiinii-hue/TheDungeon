"""Animated torch/lantern light effects for gothic city backgrounds."""

import math
import random
import pygame
from src.core.asset_manager import AssetManager

# Torch positions per background (x, y, scale, glow_radius)
# Coordinates are in 1280x720 space (game resolution)
TORCH_POSITIONS: dict[str, list[tuple[int, int, float, int]]] = {
    "gothic_entrance": [
        # Path torches (bottom left to center)
        (185, 565, 0.6, 25),
        (280, 540, 0.6, 25),
        (375, 515, 0.6, 22),
        (470, 490, 0.5, 20),
        # Cathedral lit windows
        (720, 200, 0.4, 18),
        (820, 180, 0.4, 18),
        (900, 170, 0.35, 15),
        (680, 280, 0.35, 15),
        (960, 250, 0.35, 15),
        # Moon glow
        (165, 95, 0.3, 35),
    ],
    "gothic_street": [
        # Left wall lanterns
        (55, 345, 0.7, 28),
        (155, 310, 0.6, 22),
        # Right wall lanterns
        (1175, 330, 0.7, 28),
        (1085, 310, 0.6, 22),
        # Center area candles/lights
        (490, 395, 0.4, 16),
        (785, 395, 0.4, 16),
        # Upper cathedral glow
        (640, 160, 0.3, 20),
        # Moon
        (480, 55, 0.3, 30),
    ],
    "gothic_stairs": [
        # Left wall lantern
        (130, 340, 0.7, 28),
        (85, 405, 0.5, 20),
        # Stair area candles
        (565, 285, 0.4, 15),
        (680, 250, 0.4, 15),
        # Golden door glow
        (780, 140, 0.5, 30),
        (870, 160, 0.45, 25),
        # Banner torches
        (620, 90, 0.35, 14),
        (930, 90, 0.35, 14),
    ],
}

# Warm colors for different light types
GLOW_COLOR_WARM = (255, 160, 60)   # Torch orange
GLOW_COLOR_COOL = (180, 200, 255)  # Moon blue-white


class TorchAnimator:
    """Draws animated spark sprites and glow at predefined torch positions."""

    def __init__(self, asset_manager: AssetManager):
        self.am = asset_manager
        self.time = 0.0
        self.frames: list[pygame.Surface] = []
        self._load_frames()

        # Per-torch random phase offsets for varied animation
        self._phase_offsets: dict[str, list[float]] = {}

    def _load_frames(self):
        """Load spark animation frames."""
        for i in range(1, 9):
            try:
                frame = self.am.load_image(f"Animations/effects/spark/spark{i}.png")
                self.frames.append(frame)
            except Exception:
                pass

    def _get_offsets(self, bg_key: str) -> list[float]:
        if bg_key not in self._phase_offsets:
            positions = TORCH_POSITIONS.get(bg_key, [])
            self._phase_offsets[bg_key] = [random.uniform(0, 6.28) for _ in positions]
        return self._phase_offsets[bg_key]

    def update(self, dt: float):
        self.time += dt

    def draw(self, surface: pygame.Surface, bg_key: str):
        """Draw torch light effects for the given background.

        bg_key should be one of: "gothic_entrance", "gothic_street", "gothic_stairs"
        """
        positions = TORCH_POSITIONS.get(bg_key, [])
        if not positions or not self.frames:
            return

        offsets = self._get_offsets(bg_key)
        num_frames = len(self.frames)

        for i, (tx, ty, scale, glow_r) in enumerate(positions):
            phase = offsets[i]
            t = self.time + phase

            # Flickering glow circle
            flicker = 0.7 + 0.3 * math.sin(t * 5.0 + phase * 2.0)
            glow_alpha = int(40 * flicker)
            r = int(glow_r * (0.9 + 0.1 * math.sin(t * 7.0)))

            # Use warm color for torches, cool for moon-like positions
            is_moon = (glow_r >= 30)
            glow_color = GLOW_COLOR_COOL if is_moon else GLOW_COLOR_WARM

            glow_surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*glow_color, glow_alpha), (r * 2, r * 2), r * 2)
            surface.blit(glow_surf, (tx - r * 2, ty - r * 2))

            # Inner brighter core
            core_r = max(2, r // 3)
            core_alpha = int(60 * flicker)
            core_surf = pygame.Surface((core_r * 4, core_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, (*glow_color, core_alpha),
                               (core_r * 2, core_r * 2), core_r * 2)
            surface.blit(core_surf, (tx - core_r * 2, ty - core_r * 2))

            # Spark sprite animation (skip for moon/window lights)
            if not is_moon and scale >= 0.5:
                frame_idx = int((t * 10) % num_frames)
                frame = self.frames[frame_idx]
                fw, fh = frame.get_size()
                sw = int(fw * scale)
                sh = int(fh * scale)
                if sw > 0 and sh > 0:
                    scaled = pygame.transform.smoothscale(frame, (sw, sh))
                    # Tint to warm orange
                    scaled.fill((*GLOW_COLOR_WARM, 180), special_flags=pygame.BLEND_RGBA_MULT)
                    surface.blit(scaled, (tx - sw // 2, ty - sh // 2))

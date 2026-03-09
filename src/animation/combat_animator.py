"""Combat animations: attack lunge, damage flash, card play."""

import pygame
import math


class CombatAnimator:
    def __init__(self):
        self._anims: list[dict] = []
        self._slides: dict[str, dict] = {}  # name -> slide info

    def add_flash(self, target: str, color: tuple = (255, 255, 255),
                  duration: float = 0.15):
        self._anims.append({
            "type": "flash",
            "target": target,
            "color": color,
            "duration": duration,
            "elapsed": 0.0,
        })

    def add_shake(self, target: str, intensity: float = 4.0,
                  duration: float = 0.2):
        self._anims.append({
            "type": "shake",
            "target": target,
            "intensity": intensity,
            "duration": duration,
            "elapsed": 0.0,
        })

    def add_slide_offset(self, target: str, dx: float, dy: float, duration: float = 0.3):
        """Adds a visual offset that smoothly decays to zero."""
        # If already sliding, add to current offset
        current_dx, current_dy = 0.0, 0.0
        if target in self._slides:
            slide = self._slides[target]
            t = slide["elapsed"] / slide["duration"]
            current_dx = slide["dx"] * (1.0 - t)
            current_dy = slide["dy"] * (1.0 - t)
            
        self._slides[target] = {
            "dx": dx + current_dx,
            "dy": dy + current_dy,
            "duration": duration,
            "elapsed": 0.0,
        }

    def update(self, dt: float):
        for anim in self._anims:
            anim["elapsed"] += dt
        self._anims = [a for a in self._anims if a["elapsed"] < a["duration"]]
        
        # Update slides
        for slide in self._slides.values():
            slide["elapsed"] += dt
        self._slides = {k: v for k, v in self._slides.items() if v["elapsed"] < v["duration"]}

    def get_offset(self, target: str) -> tuple[float, float]:
        """Get x,y offset for a target from active shake and slide animations."""
        ox, oy = 0.0, 0.0
        
        # Add shakes
        for anim in self._anims:
            if anim["type"] == "shake" and anim["target"] == target:
                t = anim["elapsed"] / anim["duration"]
                fade = 1.0 - t
                intensity = anim["intensity"] * fade
                ox += math.sin(anim["elapsed"] * 50) * intensity
                oy += math.cos(anim["elapsed"] * 37) * intensity * 0.5
                
        # Add slides
        if target in self._slides:
            slide = self._slides[target]
            t = slide["elapsed"] / slide["duration"]
            # Ease out quad
            fade = (1.0 - t) * (1.0 - t)
            ox += slide["dx"] * fade
            oy += slide["dy"] * fade
            
        return ox, oy

    def get_flash(self, target: str) -> tuple | None:
        """Get flash color for target if active, else None."""
        for anim in self._anims:
            if anim["type"] == "flash" and anim["target"] == target:
                t = anim["elapsed"] / anim["duration"]
                alpha = int(255 * (1.0 - t))
                return (*anim["color"][:3], alpha)
        return None

    @property
    def is_animating(self) -> bool:
        return len(self._anims) > 0 or len(self._slides) > 0

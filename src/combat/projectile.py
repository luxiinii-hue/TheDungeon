"""Targeted projectile for ATB lane combat — flies to a target position."""

import pygame
import math
from config import SCREEN_WIDTH


class Projectile:
    def __init__(self, x: float, y: float, target_x: float, target_y: float,
                 speed: float, damage: int, source_name: str,
                 team: str, ability_name: str = "",
                 color: tuple = (255, 200, 80),
                 size: tuple = (12, 6),
                 sprite: pygame.Surface | None = None):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = speed
        self.damage = damage
        self.source_name = source_name
        self.team = team  # "player" or "enemy"
        self.ability_name = ability_name
        self.color = color
        self.width, self.height = size
        self.sprite = sprite
        self.alive = True
        self.arrived = False  # True when projectile reaches target
        
        # Calculate rotation angle once if target is fixed (targeted flight)
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        self.angle = math.degrees(math.atan2(-dy, dx)) # -dy because pygame y goes down

        # Pre-rotate sprite if it exists
        self.rotated_sprite = None
        if self.sprite:
            # We assume the base sprite faces right (0 degrees)
            self.rotated_sprite = pygame.transform.rotate(self.sprite, self.angle)

        # Carry ability mods and passive info for damage processing
        self.ability_mods: list[str] = []
        self.passive: str | None = None
        self.is_aoe = False
        # Target unit name for damage application
        self.target_name: str = ""

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height / 2),
            self.width, self.height,
        )

    def update(self, dt: float):
        """Move toward target position. Sets arrived=True when close enough."""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist < self.speed * dt:
            # Arrived at target
            self.x = self.target_x
            self.y = self.target_y
            self.arrived = True
        else:
            # Move toward target
            nx = dx / dist
            ny = dy / dist
            self.x += nx * self.speed * dt
            self.y += ny * self.speed * dt
            
            # Update angle if target moves (optional, but good for dynamic targets)
            self.angle = math.degrees(math.atan2(-dy, dx))
            if self.sprite:
                self.rotated_sprite = pygame.transform.rotate(self.sprite, self.angle)

        # Safety: despawn if off-screen
        if self.x < -50 or self.x > SCREEN_WIDTH + 50:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        if not self.alive:
            return
        if self.rotated_sprite:
            surface.blit(self.rotated_sprite,
                         (int(self.x - self.rotated_sprite.get_width() / 2),
                          int(self.y - self.rotated_sprite.get_height() / 2)))
        else:
            # Fallback: colored ellipse
            # Let's draw an angled line/ellipse or a rect
            # Since drawing an angled ellipse is hard, we can just draw a circle
            r = self.rect
            pygame.draw.ellipse(surface, self.color, r)
            core = pygame.Rect(r.x + 2, r.y + 1, r.width - 4, r.height - 2)
            bright = tuple(min(255, c + 60) for c in self.color)
            if core.width > 0 and core.height > 0:
                pygame.draw.ellipse(surface, bright, core)

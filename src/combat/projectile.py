"""Projectile entity for real-time combat."""

import pygame
from config import SCREEN_WIDTH


class Projectile:
    def __init__(self, x: float, y: float, direction: int,
                 speed: float, damage: int, source_name: str,
                 team: str, ability_name: str = "",
                 color: tuple = (255, 200, 80),
                 size: tuple = (12, 6),
                 sprite: pygame.Surface | None = None):
        self.x = x
        self.y = y
        self.direction = direction  # +1 = right (player), -1 = left (enemy)
        self.speed = speed
        self.damage = damage
        self.source_name = source_name
        self.team = team  # "player" or "enemy"
        self.ability_name = ability_name
        self.color = color
        self.width, self.height = size
        self.sprite = sprite
        self.alive = True
        # Carry ability mods and passive info for damage processing
        self.ability_mods: list[str] = []
        self.passive: str | None = None
        self.is_aoe = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height / 2),
            self.width, self.height,
        )

    def update(self, dt: float):
        self.x += self.speed * self.direction * dt
        # Despawn if off-screen
        if self.x < -50 or self.x > SCREEN_WIDTH + 50:
            self.alive = False

    def hits(self, unit_rect: pygame.Rect) -> bool:
        if not self.alive:
            return False
        return self.rect.colliderect(unit_rect)

    def draw(self, surface: pygame.Surface):
        if not self.alive:
            return
        if self.sprite:
            surface.blit(self.sprite,
                          (int(self.x - self.sprite.get_width() / 2),
                           int(self.y - self.sprite.get_height() / 2)))
        else:
            # Fallback: colored ellipse
            r = self.rect
            pygame.draw.ellipse(surface, self.color, r)
            # Bright core
            core = pygame.Rect(r.x + 2, r.y + 1, r.width - 4, r.height - 2)
            bright = tuple(min(255, c + 60) for c in self.color)
            if core.width > 0 and core.height > 0:
                pygame.draw.ellipse(surface, bright, core)

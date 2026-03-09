"""Sprite-based ability animations for combat."""

import os
import math
import pygame
from dataclasses import dataclass, field
from config import ASSET_DIR


def _tint_surface(surface: pygame.Surface, tint: tuple[int, int, int]) -> pygame.Surface:
    """Apply RGB tint to a surface using multiplicative blend."""
    tinted = surface.copy()
    tint_layer = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    tint_layer.fill((*tint, 255))
    tinted.blit(tint_layer, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return tinted


def load_animation_frames(frames_dir: str, scale: int,
                          tint: tuple[int, int, int] | None = None) -> list[pygame.Surface]:
    """Load all PNG frames from a directory, sorted by name, scaled and optionally tinted."""
    full_dir = os.path.join(ASSET_DIR, frames_dir)
    if not os.path.isdir(full_dir):
        return []
    files = sorted(f for f in os.listdir(full_dir) if f.lower().endswith(".png"))
    frames = []
    for fname in files:
        path = os.path.join(full_dir, fname)
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        aspect = w / h
        if aspect >= 1:
            new_w = scale
            new_h = int(scale / aspect)
        else:
            new_h = scale
            new_w = int(scale * aspect)
        img = pygame.transform.smoothscale(img, (new_w, new_h))
        if tint:
            img = _tint_surface(img, tint)
        frames.append(img)
    return frames


@dataclass
class SpellAnimation:
    """Multi-frame spell effect playing at a fixed position."""
    frames: list[pygame.Surface]
    x: float
    y: float
    duration: float
    age: float = 0.0

    @property
    def alive(self) -> bool:
        return self.age < self.duration

    @property
    def current_frame(self) -> pygame.Surface:
        if not self.frames:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        progress = self.age / self.duration
        idx = min(int(progress * len(self.frames)), len(self.frames) - 1)
        return self.frames[idx]


@dataclass
class MeleeSlashAnimation:
    """Weapon icon that slashes diagonally across the target."""
    sprite: pygame.Surface
    x: float
    y: float
    duration: float
    age: float = 0.0
    slash_distance: float = 60.0

    @property
    def alive(self) -> bool:
        return self.age < self.duration


@dataclass
class TweenSlamAnimation:
    """Massive attack that rears up and slams down (like Abyssal Smash)."""
    sprite: pygame.Surface
    x: float
    y: float
    duration: float
    age: float = 0.0

    @property
    def alive(self) -> bool:
        return self.age < self.duration


class AbilityAnimator:
    """Manages active ability animations during combat."""

    def __init__(self):
        self.spell_anims: list[SpellAnimation] = []
        self.melee_anims: list[MeleeSlashAnimation] = []
        self.slam_anims: list[TweenSlamAnimation] = []
        self._frame_cache: dict[str, list[pygame.Surface]] = {}

    def _get_frames(self, frames_dir: str, scale: int,
                    tint: tuple[int, int, int] | None) -> list[pygame.Surface]:
        """Load and cache animation frames."""
        cache_key = f"{frames_dir}|{scale}|{tint}"
        if cache_key not in self._frame_cache:
            self._frame_cache[cache_key] = load_animation_frames(frames_dir, scale, tint)
        return self._frame_cache[cache_key]

    def spawn_spell(self, x: float, y: float, frames_dir: str,
                    scale: int = 80, duration: float = 0.6,
                    tint: tuple[int, int, int] | None = None):
        """Spawn a multi-frame spell animation at (x, y)."""
        frames = self._get_frames(frames_dir, scale, tint)
        if frames:
            self.spell_anims.append(SpellAnimation(
                frames=frames, x=x, y=y, duration=duration,
            ))

    def spawn_melee(self, x: float, y: float, sprite_path: str,
                    scale: int = 64, duration: float = 0.3,
                    tint: tuple[int, int, int] | None = None):
        """Spawn a melee slash animation at (x, y)."""
        full_path = os.path.join(ASSET_DIR, sprite_path)
        if not os.path.exists(full_path):
            return
        img = pygame.image.load(full_path).convert_alpha()
        img = pygame.transform.smoothscale(img, (scale, scale))
        if tint:
            img = _tint_surface(img, tint)
        self.melee_anims.append(MeleeSlashAnimation(
            sprite=img, x=x, y=y, duration=duration,
        ))

    def spawn_tween_slam(self, x: float, y: float, sprite_path: str,
                         scale: int = 200, duration: float = 0.8,
                         tint: tuple[int, int, int] | None = None):
        """Spawn a large tweening slam animation (like Abyssal Smash)."""
        full_path = os.path.join(ASSET_DIR, sprite_path)
        if not os.path.exists(full_path):
            return
        img = pygame.image.load(full_path).convert_alpha()
        
        # The AoEStun.png asset includes Nightfang on the far left. 
        # We need to crop him out so only the giant claw remains.
        w, h = img.get_size()
        if w > 500:
            # Crop out the left ~300 pixels (Nightfang)
            crop_rect = pygame.Rect(300, 0, w - 300, h)
            cropped_img = pygame.Surface(crop_rect.size, pygame.SRCALPHA)
            cropped_img.blit(img, (0, 0), crop_rect)
            img = cropped_img
            w, h = img.get_size()
            
        # Scale proportionally
        aspect = w / h
        new_w = scale
        new_h = int(scale / aspect)
        img = pygame.transform.smoothscale(img, (new_w, new_h))
        if tint:
            img = _tint_surface(img, tint)
        self.slam_anims.append(TweenSlamAnimation(
            sprite=img, x=x, y=y, duration=duration,
        ))

    def spawn_from_config(self, x: float, y: float, animation_config: dict):
        """Spawn animation from an ability's animation config dict."""
        if not animation_config:
            return
        anim_type = animation_config.get("type", "")
        tint = animation_config.get("tint")
        if tint:
            tint = tuple(tint)
        scale = animation_config.get("scale", 80)
        duration = animation_config.get("duration", 0.6)

        if anim_type == "spell":
            frames_dir = animation_config.get("frames_dir", "")
            self.spawn_spell(x, y, frames_dir, scale, duration, tint)
        elif anim_type == "melee_slash":
            sprite = animation_config.get("sprite", "")
            self.spawn_melee(x, y, sprite, scale, duration, tint)
        elif anim_type == "tween_slam":
            sprite = animation_config.get("sprite", "")
            self.spawn_tween_slam(x, y, sprite, scale, duration, tint)

    def update(self, dt: float):
        for anim in self.spell_anims:
            anim.age += dt
        self.spell_anims = [a for a in self.spell_anims if a.alive]

        for anim in self.melee_anims:
            anim.age += dt
        self.melee_anims = [a for a in self.melee_anims if a.alive]
        
        for anim in self.slam_anims:
            anim.age += dt
        self.slam_anims = [a for a in self.slam_anims if a.alive]

    def draw(self, surface: pygame.Surface):
        # Draw spell animations
        for anim in self.spell_anims:
            frame = anim.current_frame
            progress = anim.age / anim.duration
            if progress > 0.7:
                fade = 1.0 - (progress - 0.7) / 0.3
                alpha = max(0, int(255 * fade))
                frame = frame.copy()
                frame.set_alpha(alpha)
            surface.blit(frame, (
                int(anim.x - frame.get_width() // 2),
                int(anim.y - frame.get_height() // 2),
            ))

        # Draw melee slash animations
        for anim in self.melee_anims:
            progress = anim.age / anim.duration
            offset_x = anim.slash_distance * (0.5 - progress)
            offset_y = -anim.slash_distance * (0.5 - progress)
            angle = -135 * progress
            rotated = pygame.transform.rotate(anim.sprite, angle)
            if progress > 0.6:
                fade = 1.0 - (progress - 0.6) / 0.4
                alpha = max(0, int(255 * fade))
                rotated.set_alpha(alpha)
            surface.blit(rotated, (
                int(anim.x + offset_x - rotated.get_width() // 2),
                int(anim.y + offset_y - rotated.get_height() // 2),
            ))

        # Draw slam animations
        for anim in self.slam_anims:
            progress = anim.age / anim.duration
            
            # Phase 1: Windup (0.0 to 0.4) - scale up and rotate back slightly
            # Phase 2: Slam impact (0.4 to 0.5) - rotate forward fast
            # Phase 3: Hold & fade (0.5 to 1.0)
            
            scale_mult = 1.0
            angle = 0.0
            
            if progress < 0.4:
                # Windup
                p = progress / 0.4
                scale_mult = 0.8 + 0.4 * p  # 0.8 to 1.2
                angle = 15.0 * p            # rotate back 15 degrees
            elif progress < 0.5:
                # Slam down
                p = (progress - 0.4) / 0.1
                scale_mult = 1.2 - 0.2 * p  # 1.2 to 1.0
                angle = 15.0 - 30.0 * p     # swing forward to -15
            else:
                # Hold and fade
                scale_mult = 1.0
                angle = -15.0
            
            # Apply transformations
            w, h = anim.sprite.get_size()
            scaled = pygame.transform.smoothscale(anim.sprite, (int(w * scale_mult), int(h * scale_mult)))
            rotated = pygame.transform.rotate(scaled, angle)
            
            # Fade out at the end
            if progress > 0.7:
                fade = 1.0 - (progress - 0.7) / 0.3
                alpha = max(0, int(255 * fade))
                rotated.set_alpha(alpha)
                
            # Offset y so it hits the ground properly
            surface.blit(rotated, (
                int(anim.x - rotated.get_width() // 2),
                int(anim.y - rotated.get_height() + 20), # Anchor bottom near target
            ))

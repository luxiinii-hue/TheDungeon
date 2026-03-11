"""Bezier curve path rendering for the dungeon map."""

import math
import random
import pygame
from config import (
    MAP_PATH_VISITED_COLOR, MAP_PATH_AVAILABLE_COLOR, MAP_PATH_LOCKED_COLOR,
    MAP_PATH_OUTLINE_COLOR, MAP_PATH_WIDTH, MAP_PATH_CURVE_SEGMENTS,
)


def bezier_points(p0: tuple[int, int], p1: tuple[int, int],
                  p2: tuple[int, int], segments: int = MAP_PATH_CURVE_SEGMENTS
                  ) -> list[tuple[int, int]]:
    """Quadratic bezier: p0=start, p1=control, p2=end."""
    points = []
    for i in range(segments + 1):
        t = i / segments
        inv = 1 - t
        x = inv * inv * p0[0] + 2 * inv * t * p1[0] + t * t * p2[0]
        y = inv * inv * p0[1] + 2 * inv * t * p1[1] + t * t * p2[1]
        points.append((int(x), int(y)))
    return points


def control_point(source, target) -> tuple[int, int]:
    """Compute a bezier control point for the connection between two nodes."""
    mid_x = (source.screen_x + target.screen_x) / 2
    mid_y = (source.screen_y + target.screen_y) / 2

    col_diff = target.col - source.col
    offset_x = col_diff * 20

    # Deterministic jitter per connection
    rng = random.Random(source.id * 1000 + target.id)
    offset_x += rng.randint(-15, 15)

    return (int(mid_x + offset_x), int(mid_y))


def _draw_thick_aalines(surface: pygame.Surface, color: tuple, closed: bool,
                        points: list[tuple[int, int]], width: int):
    """Draw anti-aliased lines with thickness by offsetting multiple passes."""
    if len(points) < 2:
        return
    if width <= 1:
        pygame.draw.aalines(surface, color, closed, points)
        return
    # Center pass
    pygame.draw.aalines(surface, color, closed, points)
    # Offset passes for thickness
    half = width // 2
    for dx in range(-half, half + 1):
        for dy in range(-half, half + 1):
            if dx == 0 and dy == 0:
                continue
            if abs(dx) + abs(dy) > half:
                continue
            shifted = [(x + dx, y + dy) for x, y in points]
            pygame.draw.aalines(surface, color, closed, shifted)


def draw_dashed(surface: pygame.Surface, color: tuple,
                points: list[tuple[int, int]], width: int = 2,
                dash_len: int = 8, gap_len: int = 6):
    """Draw a dashed line along a list of points."""
    if len(points) < 2:
        return
    drawing = True
    accum = 0.0
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        seg_len = math.hypot(x1 - x0, y1 - y0)
        if drawing:
            pygame.draw.line(surface, color, (x0, y0), (x1, y1), width)
        accum += seg_len
        threshold = dash_len if drawing else gap_len
        if accum >= threshold:
            drawing = not drawing
            accum = 0.0


def draw_path(surface: pygame.Surface, points: list[tuple[int, int]],
              state: str):
    """Draw a map path with style based on state ('visited', 'available', 'locked')."""
    if len(points) < 2:
        return

    if state == "locked":
        # Dashed dark line, thin outline
        draw_dashed(surface, MAP_PATH_OUTLINE_COLOR, points, width=3)
        draw_dashed(surface, MAP_PATH_LOCKED_COLOR, points, width=2)
    elif state == "visited":
        # Solid dim line with outline
        _draw_thick_aalines(surface, MAP_PATH_OUTLINE_COLOR, False, points,
                            MAP_PATH_WIDTH + 2)
        _draw_thick_aalines(surface, MAP_PATH_VISITED_COLOR, False, points,
                            MAP_PATH_WIDTH)
    else:  # available — drawn dynamically, this is the static fallback
        _draw_thick_aalines(surface, MAP_PATH_OUTLINE_COLOR, False, points,
                            MAP_PATH_WIDTH + 2)
        _draw_thick_aalines(surface, MAP_PATH_AVAILABLE_COLOR, False, points,
                            MAP_PATH_WIDTH)


def draw_glowing_path(surface: pygame.Surface, points: list[tuple[int, int]],
                      glow_alpha: int):
    """Draw an available path with animated glow."""
    if len(points) < 2:
        return

    # Outline
    _draw_thick_aalines(surface, MAP_PATH_OUTLINE_COLOR, False, points,
                        MAP_PATH_WIDTH + 2)
    # Main path
    _draw_thick_aalines(surface, MAP_PATH_AVAILABLE_COLOR, False, points,
                        MAP_PATH_WIDTH)

    # Glow layer
    glow_color = (*MAP_PATH_AVAILABLE_COLOR, glow_alpha)
    glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    _draw_thick_aalines(glow_surf, glow_color, False, points,
                        MAP_PATH_WIDTH + 6)
    surface.blit(glow_surf, (0, 0))

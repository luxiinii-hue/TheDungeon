"""Speed bar widget for the ATB combat system."""

import pygame
import math
from config import (
    SPEED_BAR_WIDTH, SPEED_BAR_HEIGHT, SPEED_BAR_BG_COLOR,
    SPEED_BAR_BORDER_COLOR, SPEED_BAR_FILL_COLOR_READY, CLASS_COLORS, WHITE
)


def draw_speed_bar(surface: pygame.Surface, x: int, y: int, 
                   fill_percentage: float, unit_class: str = None, 
                   time_active: float = 0.0):
    """
    Draws an Active Time Battle (ATB) speed bar.
    
    Args:
        surface: The pygame Surface to draw onto.
        x: Top-left X coordinate.
        y: Top-left Y coordinate.
        fill_percentage: Value between 0.0 and 1.0 indicating how full the bar is.
        unit_class: The class of the unit (determines bar color).
        time_active: Time in seconds since the bar started (used for ready animation).
    """
    # Clamp percentage
    fill_percentage = max(0.0, min(1.0, fill_percentage))
    
    # Determine the fill color
    if fill_percentage >= 1.0:
        # Flash slightly between Gold and White when ready
        flash_val = (math.sin(time_active * 10.0) + 1.0) / 2.0  # 0 to 1
        r = int(SPEED_BAR_FILL_COLOR_READY[0] + (255 - SPEED_BAR_FILL_COLOR_READY[0]) * flash_val * 0.5)
        g = int(SPEED_BAR_FILL_COLOR_READY[1] + (255 - SPEED_BAR_FILL_COLOR_READY[1]) * flash_val * 0.5)
        b = int(SPEED_BAR_FILL_COLOR_READY[2] + (255 - SPEED_BAR_FILL_COLOR_READY[2]) * flash_val * 0.5)
        fill_color = (r, g, b)
    else:
        # Default to a generic color or class specific color
        fill_color = CLASS_COLORS.get(unit_class, (100, 150, 200))
    
    # Draw Background
    bg_rect = pygame.Rect(x, y, SPEED_BAR_WIDTH, SPEED_BAR_HEIGHT)
    pygame.draw.rect(surface, SPEED_BAR_BG_COLOR, bg_rect, border_radius=2)
    
    # Draw Fill
    if fill_percentage > 0:
        fill_width = int(SPEED_BAR_WIDTH * fill_percentage)
        fill_rect = pygame.Rect(x, y, fill_width, SPEED_BAR_HEIGHT)
        pygame.draw.rect(surface, fill_color, fill_rect, border_radius=2)
    
    # Draw Border
    pygame.draw.rect(surface, SPEED_BAR_BORDER_COLOR, bg_rect, width=1, border_radius=2)
    
    # Draw a little marker at 100%
    if fill_percentage >= 1.0:
        # Draw a tiny glow around the edges
        glow_rect = bg_rect.inflate(2, 2)
        pygame.draw.rect(surface, fill_color, glow_rect, width=1, border_radius=3)

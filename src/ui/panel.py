"""Stat display panels."""

import pygame
from config import PANEL_BG, PANEL_BORDER, WHITE, GRAY, GOLD, GREEN, FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, CLASS_COLORS
from src.ui.text_renderer import draw_text
from src.ui.icons import get_icon


class Panel:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)

    def draw(self, surface: pygame.Surface):
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(surface, (10, 10, 15), shadow_rect, border_radius=8)
        pygame.draw.rect(surface, PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, width=2, border_radius=8)


class CharacterPanel(Panel):
    def __init__(self, x: int, y: int, width: int, height: int):
        super().__init__(x, y, width, height)
        self.char_data = None
        self.ability_rects: list[tuple[pygame.Rect, str]] = []

    def set_character(self, char_data):
        self.char_data = char_data

    def draw(self, surface: pygame.Surface):
        if self.char_data is None:
            return

        super().draw(surface)
        cd = self.char_data
        self.ability_rects.clear()

        # Horizontal layout: Name+Role | Stats | Abilities | Description
        px = self.rect.x + 15
        py = self.rect.y + 15

        # Column 1: Name and role
        draw_text(surface, cd.name, px, py, size=FONT_SIZE_MEDIUM, color=GOLD)
        py += 28
        role_color = CLASS_COLORS.get(cd.role, GREEN)
        draw_text(surface, cd.role.capitalize(), px, py, size=FONT_SIZE_SMALL, color=role_color)

        # Column 2: Stats (offset right)
        stat_x = self.rect.x + 200
        stat_y = self.rect.y + 15
        stats = [
            ("HP", cd.max_hp, "heart"),
            ("STR", cd.strength, "sword"),
            ("ARM", cd.armor, "shield"),
            ("SPD", cd.speed, "boot"),
        ]
        for stat_name, stat_val, icon_name in stats:
            icon = get_icon(icon_name, size=(20, 20))
            if icon:
                surface.blit(icon, (stat_x, stat_y - 2))
                draw_text(surface, f"{stat_name}: {stat_val}", stat_x + 28, stat_y,
                          size=FONT_SIZE_SMALL, color=WHITE)
            else:
                draw_text(surface, f"{stat_name}: {stat_val}", stat_x, stat_y,
                          size=FONT_SIZE_SMALL, color=WHITE)
            stat_y += 24

        # Column 3: Abilities
        ability_x = self.rect.x + 400
        ability_y = self.rect.y + 15
        draw_text(surface, "Abilities:", ability_x, ability_y, size=FONT_SIZE_SMALL, color=GOLD)
        ability_y += 22
        for ability_id in cd.abilities:
            display_name = ability_id.replace('_', ' ').title()
            draw_text(surface, display_name, ability_x + 10, ability_y,
                      size=FONT_SIZE_SMALL, color=WHITE)
            # Store rect for tooltip hit detection
            text_w = len(display_name) * 9
            self.ability_rects.append((
                pygame.Rect(ability_x + 10, ability_y - 2, text_w, 20),
                ability_id,
            ))
            ability_y += 22

        # Column 4: Description
        desc_x = self.rect.x + 650
        desc_y = self.rect.y + 15
        draw_text(surface, "Info:", desc_x, desc_y, size=FONT_SIZE_SMALL, color=GOLD)
        desc_y += 22
        max_w = self.rect.right - desc_x - 15
        words = cd.description.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if len(test) * 8 > max_w:
                draw_text(surface, line, desc_x, desc_y, size=FONT_SIZE_SMALL, color=GRAY)
                desc_y += 20
                line = word
            else:
                line = test
        if line:
            draw_text(surface, line, desc_x, desc_y, size=FONT_SIZE_SMALL, color=GRAY)

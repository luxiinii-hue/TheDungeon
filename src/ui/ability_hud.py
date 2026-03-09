"""Ability HUD widget for the bottom of the screen."""

import pygame
from src.combat.unit import CombatUnit
from src.combat.ability import AbilityRegistry
from src.ui.text_renderer import draw_text
from src.core.asset_manager import AssetManager
from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, GRAY, GOLD, DARK_GRAY

class AbilityHUD:
    def __init__(self, asset_manager: AssetManager):
        self.asset_manager = asset_manager
        self.rects: list[tuple[pygame.Rect, str]] = []
        self.hud_y = SCREEN_HEIGHT - 80
        self.icon_size = 60
        self.spacing = 70

    def draw(self, surface: pygame.Surface, unit: CombatUnit, registry: AbilityRegistry):
        self.rects = []
        if not unit:
            return

        num_abilities = len(unit.ability_ids)
        total_width = num_abilities * self.spacing - (self.spacing - self.icon_size)
        start_x = (SCREEN_WIDTH - total_width) // 2

        for i, ability_id in enumerate(unit.ability_ids):
            ability = registry.get(ability_id)
            if not ability:
                continue

            btn_x = start_x + i * self.spacing
            btn_rect = pygame.Rect(btn_x, self.hud_y, self.icon_size, self.icon_size)
            self.rects.append((btn_rect, ability_id))

            cd_remaining = unit.cooldowns.get(ability_id, 0)
            on_cooldown = cd_remaining > 0

            # Background
            bg_color = (40, 40, 55) if not on_cooldown else (25, 25, 35)
            pygame.draw.rect(surface, bg_color, btn_rect, border_radius=6)

            # Icon
            if ability.icon:
                try:
                    icon_img = self.asset_manager.get_scaled(ability.icon, self.icon_size - 4, self.icon_size - 4)
                    surface.blit(icon_img, (btn_x + 2, self.hud_y + 2))
                except Exception:
                    pass
            else:
                # Text fallback if no icon
                label = ability.name[:8]
                draw_text(surface, label, btn_x + self.icon_size // 2, self.hud_y + self.icon_size // 2 - 8,
                          size=11, color=WHITE if not on_cooldown else GRAY, center=True)

            # Border
            border_color = GOLD if not on_cooldown else DARK_GRAY
            pygame.draw.rect(surface, border_color, btn_rect, 2, border_radius=6)

            # Hotkey label (top left corner)
            hotkey_rect = pygame.Rect(btn_x - 6, self.hud_y - 6, 20, 20)
            pygame.draw.rect(surface, (20, 20, 20), hotkey_rect, border_radius=4)
            pygame.draw.rect(surface, GOLD, hotkey_rect, 1, border_radius=4)
            draw_text(surface, str(i + 1), btn_x + 4, self.hud_y + 4,
                      size=14, color=GOLD, center=True)

            # Cooldown sweep overlay
            if on_cooldown:
                cd_frac = cd_remaining / ability.cooldown if ability.cooldown > 0 else 0
                overlay_h = int(self.icon_size * cd_frac)
                overlay_rect = pygame.Rect(btn_x, self.hud_y + self.icon_size - overlay_h, self.icon_size, overlay_h)
                overlay = pygame.Surface((self.icon_size, overlay_h), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                # Need to use subsurface or clip if border radius is large, but rect is fine
                surface.blit(overlay, overlay_rect)
                
                # Cooldown text
                draw_text(surface, f"{cd_remaining:.1f}", btn_x + self.icon_size // 2, self.hud_y + self.icon_size // 2,
                          size=18, color=WHITE, center=True)

    def handle_click(self, mx: int, my: int) -> str | None:
        """Returns ability_id if clicked, else None."""
        for btn_rect, ability_id in self.rects:
            if btn_rect.collidepoint(mx, my):
                return ability_id
        return None

"""
hud.py

On-screen HUD: Iris's leaf-shaped HP bar, remaining lives, ability
cooldown icons, and (Scenes 3-4) the Murk Meter (PROJECT_BRIEF.md
section 4 & 8). A scene creates one HUD and calls draw() every frame,
passing the player so it can read her hp/lives/cooldowns.
"""

import pygame

from config.settings import UI_IMG_DIR, SCREEN_W, COLORS, POLLEN_BURST_COOLDOWN
from src.core.asset_loader import load_image

HP_BAR_SIZE = (160, 40)
LIFE_ICON_SIZE = (28, 28)
COOLDOWN_ICON_SIZE = (48, 48)
MARGIN = 16

MURK_METER_SIZE = (200, 22)
MURK_METER_ICON_SIZE = 44
MURK_METER_Y = 30  # independent of MARGIN — change this alone to move just the meter vertically


class HUD:
    def __init__(self):
        self.hp_bar_images = {
            "full": load_image(UI_IMG_DIR / "hp_bar_full.png", size=HP_BAR_SIZE),
            "75": load_image(UI_IMG_DIR / "hp_bar_75.png", size=HP_BAR_SIZE),
            "50": load_image(UI_IMG_DIR / "hp_bar_50.png", size=HP_BAR_SIZE),
            "25": load_image(UI_IMG_DIR / "hp_bar_25.png", size=HP_BAR_SIZE),
            "empty": load_image(UI_IMG_DIR / "hp_bar_empty.png", size=HP_BAR_SIZE),
        }
        self.life_icon = load_image(UI_IMG_DIR / "life_icon.png", size=LIFE_ICON_SIZE)
        self.cooldown_icons = {
            "pollen_burst": load_image(UI_IMG_DIR / "icon_pollen_burst.png", size=COOLDOWN_ICON_SIZE),
        }
        self.murk_meter_icon = load_image(UI_IMG_DIR / "murk_meter.png", size=(MURK_METER_ICON_SIZE, MURK_METER_ICON_SIZE))

    def draw(self, surface, player, murk_meter=None):
        self._draw_hp_bar(surface, player)
        self._draw_lives(surface, player)
        self._draw_cooldowns(surface, player)
        # murk_meter is only set by scenes that need it (3-4) — see
        # base_scene.py's draw(), which passes getattr(self, "murk_meter", None).
        if murk_meter is not None:
            self._draw_murk_meter(surface, murk_meter)

    def _draw_hp_bar(self, surface, player):
        hp_fraction = player.hp / player.max_hp if player.max_hp else 0
        surface.blit(self.hp_bar_images[self._hp_bar_key(hp_fraction)], (MARGIN, MARGIN))

    @staticmethod
    def _hp_bar_key(hp_fraction):
        if hp_fraction > 0.875:
            return "full"
        elif hp_fraction > 0.625:
            return "75"
        elif hp_fraction > 0.375:
            return "50"
        elif hp_fraction > 0.125:
            return "25"
        else:
            return "empty"

    def _draw_lives(self, surface, player):
        y = MARGIN + HP_BAR_SIZE[1] + 8
        for i in range(player.lives):
            x = MARGIN + i * (LIFE_ICON_SIZE[0] + 4)
            surface.blit(self.life_icon, (x, y))

    def _draw_cooldowns(self, surface, player):
        x = MARGIN
        y = MARGIN + HP_BAR_SIZE[1] + 8 + LIFE_ICON_SIZE[1] + 8

        # Pollen Burst is locked until Scene 3 (see scene3_spire.py) — no
        # icon until then, same idea as the old Lumen Bloom gating.
        if getattr(player, "pollen_burst_unlocked", False):
            self._draw_cooldown_icon(
                surface, "pollen_burst", player.pollen_cooldown_timer, POLLEN_BURST_COOLDOWN, (x, y)
            )

    def _draw_cooldown_icon(self, surface, name, remaining, total, pos):
        surface.blit(self.cooldown_icons[name], pos)

        if remaining > 0:
            fraction_remaining = remaining / total
            overlay_height = int(COOLDOWN_ICON_SIZE[1] * fraction_remaining)
            overlay = pygame.Surface((COOLDOWN_ICON_SIZE[0], overlay_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, pos)

    def _draw_murk_meter(self, surface, murk_meter):
        """Top-right bar (PROJECT_BRIEF.md section 8) — fills purple as
        the Murk Meter climbs toward full."""
        width, height = MURK_METER_SIZE
        x = SCREEN_W - width - MARGIN
        y = MURK_METER_Y

        icon_y = y + (height - MURK_METER_ICON_SIZE) // 2  # vertically centered against the bar, whatever its size
        surface.blit(self.murk_meter_icon, (x - MURK_METER_ICON_SIZE - 6, icon_y))

        pygame.draw.rect(surface, COLORS["ui_bg"], (x, y, width, height))
        fill_width = int(width * murk_meter.fraction())
        pygame.draw.rect(surface, COLORS["murk_purple"], (x, y, fill_width, height))
        pygame.draw.rect(surface, COLORS["ui_border"], (x, y, width, height), 2)

        font = pygame.font.Font(None, 20)
        label = font.render("Murk Meter", True, COLORS["white"])
        surface.blit(label, (x, y - 20))

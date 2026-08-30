"""
boss_base.py

Shared logic for full multi-phase bosses (Sky Wisp, Fungal Warden,
Aurelian Titan): a screen-wide health bar and HP-threshold phase
transitions (PROJECT_BRIEF.md section 6: "Boss HP reaches ~50% -> enter
next phase: background shifts, attack pattern changes, music
intensifies"). The Murk Crawler Elite (Scene 1) is a mini-boss, simple
enough that it's just a plain Enemy subclass and doesn't need this.
"""

import pygame

from config.settings import SCREEN_W, COLORS
from src.entities.enemy import Enemy


class Boss(Enemy):
    """Base class for a multi-phase boss fight.

    Subclasses set PHASE_THRESHOLDS — HP fractions, descending, where
    each entry is the fraction at which that phase begins (index 0 is
    always the starting phase at 1.0) — and override on_phase_change()
    and on_death() to react.
    """

    PHASE_THRESHOLDS = (1.0, 0.5)
    NAME = "Boss"

    # Health bar dimensions — class attributes (like NAME/PHASE_THRESHOLDS
    # above) so a specific boss can override just its own bar's size
    # without affecting every other boss that shares this base class.
    HEALTH_BAR_MARGIN = 40   # left/right margin from the screen edges
    HEALTH_BAR_HEIGHT = 22
    HEALTH_BAR_Y = 20        # top of the bar, in screen space

    def __init__(self, x, y, width, height, max_hp, contact_damage):
        # Bosses drive their own movement rather than patrolling back and
        # forth, so patrol bounds collapse to a single point.
        super().__init__(x, y, width, height, max_hp, x, x, 0, contact_damage)
        self.phase = 0
        self.death_anim_done = False

    def take_damage(self, amount):
        was_alive = not self.is_dead
        super().take_damage(amount)
        self._check_phase_transition()
        if was_alive and self.is_dead:
            self.on_death()

    def _check_phase_transition(self):
        hp_fraction = self.hp_fraction()
        new_phase = 0
        for i, threshold in enumerate(self.PHASE_THRESHOLDS):
            if hp_fraction <= threshold:
                new_phase = i
        if new_phase > self.phase:
            self.phase = new_phase
            self.on_phase_change(self.phase)

    def on_phase_change(self, phase_index):
        """Override to react to entering a new phase: change attack
        pattern, swap sprites, shift the background, intensify music."""
        pass

    def on_death(self):
        """Override for death-specific behaviour beyond the death
        animation (e.g. Aurelian Titan reverting to a peaceful form)."""
        pass

    def hp_fraction(self):
        return self.hp / self.max_hp if self.max_hp else 0

    def draw_health_bar(self, surface):
        """Boss health bar across the top of the screen. Drawn directly
        in screen space (not offset by the camera) since it's a HUD
        element, not part of the world."""
        margin = self.HEALTH_BAR_MARGIN
        bar_width = SCREEN_W - margin * 2
        bar_height = self.HEALTH_BAR_HEIGHT
        x, y = margin, self.HEALTH_BAR_Y

        pygame.draw.rect(surface, COLORS["ui_bg"], (x, y, bar_width, bar_height))
        fill_width = int(bar_width * self.hp_fraction())
        pygame.draw.rect(surface, COLORS["hp_red"], (x, y, fill_width, bar_height))
        pygame.draw.rect(surface, COLORS["ui_border"], (x, y, bar_width, bar_height), 2)

        font = pygame.font.Font(None, bar_height)
        label = font.render(self.NAME, True, COLORS["white"])
        surface.blit(label, (x, y - bar_height))

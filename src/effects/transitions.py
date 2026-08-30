"""
transitions.py

Scene-transition and screen effects: a wipe transition (bar sweeping
across the screen), Scene 4's dual-background crossfade, and a
reusable screen-shake helper.
"""

import random

import pygame

from config.settings import SCREEN_W, SCREEN_H


class WipeTransition:
    """A solid bar that sweeps in to cover the screen, then holds until
    told to reveal, then sweeps back out. The hold is deliberate: it
    gives the scene manager a moment with the screen fully covered to
    swap the actual scene content before anything is shown again."""

    def __init__(self, color=(0, 0, 0), duration=0.5):
        self.color = color
        self.duration = duration
        self.time = 0.0
        self.covering = True  # True while sweeping in / holding covered, False while sweeping out

    @property
    def covered(self):
        """True once the wipe fully covers the screen — the scene
        manager should swap scenes and then call start_reveal()."""
        return self.covering and self.time >= self.duration

    @property
    def done(self):
        """True once the wipe has fully swept back off-screen."""
        return not self.covering and self.time >= self.duration

    def start_reveal(self):
        """Begin sweeping back out. Call this once the scene behind the
        wipe has been swapped, while `covered` is True."""
        self.covering = False
        self.time = 0.0

    def update(self, dt):
        if self.time < self.duration:
            self.time = min(self.duration, self.time + dt)

    def draw(self, surface):
        progress = min(1.0, self.time / self.duration)
        width = int(SCREEN_W * progress)

        if self.covering:
            rect = pygame.Rect(0, 0, width, SCREEN_H)
        else:
            rect = pygame.Rect(width, 0, SCREEN_W - width, SCREEN_H)

        pygame.draw.rect(surface, self.color, rect)


class BackgroundCrossfade:
    """Blends between two background images based on a 0..1 fraction —
    Scene 4's corrupted -> restored background as the boss loses HP."""

    def __init__(self, corrupted_image, restored_image):
        self.corrupted_image = corrupted_image
        self.restored_image = restored_image

    def draw(self, surface, restored_fraction):
        """restored_fraction: 0 = fully corrupted, 1 = fully restored."""
        restored_fraction = max(0.0, min(1.0, restored_fraction))

        surface.blit(self.corrupted_image, (0, 0))

        faded_restored = self.restored_image.copy()
        faded_restored.set_alpha(int(255 * restored_fraction))
        surface.blit(faded_restored, (0, 0))


class ScreenShake:
    """Reusable camera-offset shake. Call trigger() on impact, then add
    get_offset() into your camera's draw offset every frame."""

    def __init__(self):
        self.duration = 0.0
        self.magnitude = 0

    def trigger(self, duration=0.3, magnitude=8):
        self.duration = duration
        self.magnitude = magnitude

    @property
    def active(self):
        return self.duration > 0

    def update(self, dt):
        if self.duration > 0:
            self.duration -= dt

    def get_offset(self):
        if self.duration <= 0:
            return (0, 0)
        return (
            random.randint(-self.magnitude, self.magnitude),
            random.randint(-self.magnitude, self.magnitude),
        )

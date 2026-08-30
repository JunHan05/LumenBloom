"""
shockwave.py

An expanding, fading ring drawn directly with pygame.draw.circle (no
image needed) — used for boss ground-slams and the Lumen Bloom
ultimate's radial burst (PROJECT_BRIEF.md section 5 & 8).
"""

import pygame


class Shockwave:
    def __init__(self, center, max_radius=150, speed=300, color=(255, 255, 255), width=4):
        self.center = center
        self.radius = 0.0
        self.max_radius = max_radius
        self.speed = speed
        self.color = color
        self.width = width

    @property
    def alive(self):
        return self.radius < self.max_radius

    def update(self, dt):
        self.radius += self.speed * dt

    def draw(self, surface, camera_offset=(0, 0)):
        if not self.alive or self.radius <= 0:
            return

        alpha = max(0, 255 - int(255 * (self.radius / self.max_radius)))
        diameter = int(self.radius * 2)

        ring_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(
            ring_surface, (*self.color, alpha),
            (int(self.radius), int(self.radius)), int(self.radius), self.width,
        )

        pos = (
            self.center[0] - camera_offset[0] - self.radius,
            self.center[1] - camera_offset[1] - self.radius,
        )
        surface.blit(ring_surface, pos)

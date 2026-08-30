"""
platforms.py

Moving platforms: the sinking mushroom-cap platform (Scene 1) and the
swaying wooden platform (Scene 2).
"""

import math

import pygame

from config.settings import TILES_IMG_DIR, TILE_SIZE
from src.core.asset_loader import load_image


class Platform:
    """Base class for a platform Iris can stand on. `rect` is what the
    collision code reads each frame; subclasses move it around."""

    def __init__(self, x, y, width, height, image_filename):
        self.rect = pygame.Rect(x, y, width, height)
        self.image = load_image(TILES_IMG_DIR / image_filename, size=(width, height))

    def update(self, dt, player_rect):
        pass  # static by default; subclasses override to move

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class SinkingPlatform(Platform):
    """A mushroom-cap platform that sinks slightly while Iris stands on it
    and rises back once she steps off (Scene 1, PROJECT_BRIEF.md section 5)."""

    def __init__(self, x, y, width, height, image_filename="mushroom_platform.png",
                 sink_depth=10, sink_speed=60):
        super().__init__(x, y, width, height, image_filename)
        self.origin_y = y
        self.sink_depth = sink_depth
        self.sink_speed = sink_speed  # pixels per second

    def update(self, dt, player_rect):
        standing_on = (
            player_rect.bottom <= self.rect.top + 4
            and player_rect.right > self.rect.left
            and player_rect.left < self.rect.right
        )
        target_y = self.origin_y + self.sink_depth if standing_on else self.origin_y

        if self.rect.y < target_y:
            self.rect.y = min(self.rect.y + self.sink_speed * dt, target_y)
        elif self.rect.y > target_y:
            self.rect.y = max(self.rect.y - self.sink_speed * dt, target_y)


class SwayingPlatform(Platform):
    """A wooden plank platform hanging on a branch that sways side to
    side (Scene 2, PROJECT_BRIEF.md section 5)."""

    def __init__(self, x, y, width, height, image_filename="swaying_platform.png",
                 sway_amplitude=40, sway_speed=1.0):
        super().__init__(x, y, width, height, image_filename)
        self.origin_x = x
        self.sway_amplitude = sway_amplitude
        self.sway_speed = sway_speed  # radians per second
        self.time = 0.0

    def update(self, dt, player_rect):
        self.time += dt
        self.rect.x = int(self.origin_x + math.sin(self.time * self.sway_speed) * self.sway_amplitude)


class MushroomLift(Platform):
    """A vertical elevator platform that shuttles between a top and
    bottom position forever — reuses the same mushroom-cap art as
    SinkingPlatform (PROJECT_BRIEF.md section 9 only lists one
    mushroom_platform.png, no separate lift sprite). Iris rides it
    exactly the way she rides SinkingPlatform/SwayingPlatform —
    BaseScene's passenger check is purely rect-position-based and needs
    no changes for a platform moving on a new axis. Unlike
    SwayingPlatform's sine sway, this is a straight-line ping-pong so
    both ends can optionally hold a pause before reversing, and
    reliably parks Iris exactly at top_y/bottom_y rather than
    approaching them asymptotically."""

    def __init__(self, x, top_y, bottom_y, width=TILE_SIZE, height=16,
                 image_filename="mushroom_platform.png", speed=60, pause_time=0.0):
        super().__init__(x, top_y, width, height, image_filename)
        self.top_y = top_y
        self.bottom_y = bottom_y
        self.speed = speed
        self.pause_time = pause_time
        self.pause_timer = 0.0
        self.moving_down = True

    def update(self, dt, player_rect):
        if self.pause_timer > 0:
            self.pause_timer = max(0.0, self.pause_timer - dt)
            return

        target_y = self.bottom_y if self.moving_down else self.top_y
        if self.rect.y < target_y:
            self.rect.y = min(self.rect.y + self.speed * dt, target_y)
        else:
            self.rect.y = max(self.rect.y - self.speed * dt, target_y)

        if self.rect.y == target_y:
            self.moving_down = not self.moving_down
            self.pause_timer = self.pause_time

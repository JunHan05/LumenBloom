"""
murk_crawler.py

Murk Crawler — regular enemy in Scene 1 (The Glowcap Grotto). A mushroom
creature with a purple cap and glowing red eyes that patrols a fixed
stretch of floor (PROJECT_BRIEF.md section 6). The mini-boss guarding
the gate to Lumen Shard 1 is the Jinn Monster (jinn_monster.py) —
visually unrelated to this Crawler, despite the shared "elite" role.
"""

import pygame

from config.settings import ENEMIES_IMG_DIR
from src.core.asset_loader import load_animation_frames
from src.entities.enemy import Enemy

WALK_FRAME_COUNT = 4
DEATH_FRAME_COUNT = 3
FRAME_DURATION = 0.15

MAX_HP = 40
CONTACT_DAMAGE = 10
PATROL_SPEED = 60  # pixels per second
WIDTH, HEIGHT = 72, 72


class MurkCrawler(Enemy):
    def __init__(self, x, y, patrol_left, patrol_right):
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, patrol_left, patrol_right,
                          PATROL_SPEED, CONTACT_DAMAGE)

        # Prefers separate numbered pose files (murk_crawler_walk_1.png,
        # _2.png, ...) over a single sliced sheet — see
        # asset_loader.load_animation_frames().
        self.walk_frames = load_animation_frames(
            ENEMIES_IMG_DIR, "murk_crawler_walk", WALK_FRAME_COUNT, size=(WIDTH, HEIGHT))
        self.death_frames = load_animation_frames(
            ENEMIES_IMG_DIR, "murk_crawler_death", DEATH_FRAME_COUNT, size=(WIDTH, HEIGHT))

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.walk_frames[0]

        # True once the death animation has played through fully — the
        # scene checks this to know when it's safe to remove the sprite.
        self.death_anim_done = False

    def take_damage(self, amount):
        was_alive = not self.is_dead
        super().take_damage(amount)
        if was_alive and self.is_dead:
            # Switching animations: restart from frame 0 so we don't
            # carry over an index the death sheet may not have.
            self.frame_index = 0
            self.frame_timer = 0.0

    def update(self, dt, player=None):
        if self.is_dead:
            self._animate_death(dt)
        else:
            self.patrol(dt)
            self._animate_walk(dt)

    def _animate_walk(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.walk_frames)

        frame = self.walk_frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _animate_death(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            if self.frame_index < len(self.death_frames) - 1:
                self.frame_index += 1
            else:
                self.death_anim_done = True

        frame = self.death_frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def draw(self, surface, camera_offset=(0, 0)):
        # +9px vertical offset when alive to remove transparent padding so feet touch the floor
        y_offset = 9 if not self.is_dead else 0
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y + y_offset - camera_offset[1]))

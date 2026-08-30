"""
briarling.py

Briarling — regular enemy in Scene 2 (The Skybloom Reach). A horned
grey creature carrying a wooden club that runs fast and fires thorn
projectiles at Iris (PROJECT_BRIEF.md section 6).
"""

import pygame

from config.settings import ENEMIES_IMG_DIR
from src.core.asset_loader import load_animation_frames, load_image
from src.entities.enemy import Enemy
from src.entities.projectile import Projectile

RUN_FRAME_COUNT = 18
ATTACK_FRAME_COUNT = 12
DEATH_FRAME_COUNT = 15
FRAME_DURATION = 0.1

MAX_HP = 50
CONTACT_DAMAGE = 12
PATROL_SPEED = 110  # faster than Murk Crawler's 60 — "runs fast"
WIDTH, HEIGHT = 80, 80

DETECTION_RANGE = 260
ATTACK_COOLDOWN = 1.8
PROJECTILE_SPEED = 260
PROJECTILE_DAMAGE = 12


class Briarling(Enemy):
    def __init__(self, x, y, patrol_left, patrol_right):
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, patrol_left, patrol_right,
                          PATROL_SPEED, CONTACT_DAMAGE)

        size = (WIDTH, HEIGHT)
        self.run_frames = load_animation_frames(ENEMIES_IMG_DIR, "briarling_run", RUN_FRAME_COUNT, size=size)
        self.attack_frames = load_animation_frames(ENEMIES_IMG_DIR, "briarling_attack", ATTACK_FRAME_COUNT, size=size)
        self.death_frames = load_animation_frames(ENEMIES_IMG_DIR, "briarling_death", DEATH_FRAME_COUNT, size=size)
        self.thorn_image = load_image(ENEMIES_IMG_DIR / "thorn_projectile.png", size=(14, 14))

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.run_frames[0]

        self.attacking = False
        self.attack_cooldown_timer = 0.0
        self.death_anim_done = False
        self.pending_projectile = None

    def take_damage(self, amount):
        was_alive = not self.is_dead
        super().take_damage(amount)
        if was_alive and self.is_dead:
            self.frame_index = 0
            self.frame_timer = 0.0

    def update(self, dt, player=None):
        if self.is_dead:
            self._animate_death(dt)
            return

        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)

        if self.attacking:
            self._animate_attack(dt)
        else:
            self.patrol(dt)
            self._animate_run(dt)
            if player is not None and self.attack_cooldown_timer <= 0:
                distance = abs(player.rect.centerx - self.rect.centerx)
                if distance <= DETECTION_RANGE:
                    self._start_attack(player)

    def _start_attack(self, player):
        self.attacking = True
        self.frame_index = 0
        self.frame_timer = 0.0
        self.attack_cooldown_timer = ATTACK_COOLDOWN
        self.facing_right = player.rect.centerx >= self.rect.centerx

    def _animate_run(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.run_frames)
        frame = self.run_frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _animate_attack(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index += 1
            if self.frame_index == len(self.attack_frames) - 1:
                self._fire_projectile()
            if self.frame_index >= len(self.attack_frames):
                self.attacking = False
                self.frame_index = 0

        if self.attacking:
            frame = self.attack_frames[min(self.frame_index, len(self.attack_frames) - 1)]
            self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _fire_projectile(self):
        direction = 1 if self.facing_right else -1
        velocity = (PROJECTILE_SPEED * direction, 0)
        self.pending_projectile = Projectile(
            self.rect.centerx, self.rect.centery, velocity, self.thorn_image, PROJECTILE_DAMAGE,
        )

    def take_pending_projectile(self):
        """Scene calls this once per frame to collect a freshly-fired
        projectile (or None) so it can be added to the scene's list."""
        projectile = self.pending_projectile
        self.pending_projectile = None
        return projectile

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
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))

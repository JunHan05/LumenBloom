"""
jinn_monster.py

Jinn Monster — mini-boss guarding the sealed gate to Lumen Shard 1 in
Scene 1 (The Glowcap Grotto). A floating blue genie (CraftPix "Jinn"
sprite pack) that hovers in place, firing a swirling magic-orb
projectile at Iris from range or slamming down for a close-range
shockwave-ring + damage burst if she gets close. (The floor-fracture
mechanic from PROJECT_BRIEF.md section 6 now belongs to Bug Boss's
Stomp instead — see scenes/scene1_grotto.py's
_update_hazard_ground_cracks().)
"""

import math

import pygame

from config.settings import ENEMIES_IMG_DIR, SFX_DIR
from src.core.asset_loader import load_animation_frames, load_sound, play_sound
from src.entities.enemy import Enemy
from src.entities.projectile import Projectile

IDLE_FRAME_COUNT = 3
ATTACK_FRAME_COUNT = 4
DEATH_FRAME_COUNT = 6
HURT_FRAME_COUNT = 2
PROJECTILE_FRAME_COUNT = 11
FRAME_DURATION = 0.18
HURT_FLASH_DURATION = 0.2

MAX_HP = 150
CONTACT_DAMAGE = 15
# The Jinn source art (128x128) has generous transparent padding around
# the actual character — only about 30% width / 60% height is visible
# pixels. A larger bounding box compensates so the mini-boss actually
# reads as bigger than Iris ("larger, tougher" per the brief), not
# smaller once scaled down.
WIDTH, HEIGHT = 128, 128

# Ranged attack (magic-orb projectile) — used while Iris keeps her distance.
DETECTION_RANGE = 350
ATTACK_COOLDOWN = 2.0
PROJECTILE_SPEED = 220
PROJECTILE_DAMAGE = 15
PROJECTILE_SIZE = 32

# Melee slam — used when Iris closes to short range instead. A
# shockwave-ring visual + burst damage, no floor fracture (that moved to
# Bug Boss's Stomp — see scene1_grotto.py). Still gives Scene 1 a real
# "stay at range or get punished up close" push-pull instead of a
# one-note ranged turret; SLAM_CRACK_RADIUS sizes the cosmetic shockwave
# ring (not an actual crack) and, matching it, SLAM_DAMAGE_RANGE.
SLAM_TRIGGER_RANGE = 90
SLAM_COOLDOWN = 4.0
SLAM_CRACK_RADIUS = 2.3
SLAM_DAMAGE_RANGE = 80
SLAM_DAMAGE = 18

# Hover drift while idle, so it isn't a stationary target between attacks.
HOVER_RANGE_X = 40
HOVER_BOB_Y = 14
HOVER_SPEED = 1.3


class JinnMonster(Enemy):
    """Mini-boss guarding the sealed gate to Lumen Shard 1. Hovers in
    place (no ground patrol) and picks a ranged magic-orb shot or a
    melee floor-slam depending on how close Iris is."""

    def __init__(self, x, y):
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, x, x, 0, CONTACT_DAMAGE)

        size = (WIDTH, HEIGHT)
        self.idle_frames = load_animation_frames(
            ENEMIES_IMG_DIR, "jinn_monster_idle", IDLE_FRAME_COUNT, size=size)
        self.attack_frames = load_animation_frames(
            ENEMIES_IMG_DIR, "jinn_monster_attack", ATTACK_FRAME_COUNT, size=size)
        self.death_frames = load_animation_frames(
            ENEMIES_IMG_DIR, "jinn_monster_death", DEATH_FRAME_COUNT, size=size)
        self.hurt_frames = load_animation_frames(
            ENEMIES_IMG_DIR, "jinn_monster_hurt", HURT_FRAME_COUNT, size=size)
        # The swirling magic-orb effect (11 frames) plays as an animated
        # projectile rather than a single static image.
        self.projectile_frames = load_animation_frames(
            ENEMIES_IMG_DIR, "jinn_monster_projectile", PROJECTILE_FRAME_COUNT,
            size=(PROJECTILE_SIZE, PROJECTILE_SIZE))

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.idle_frames[0]
        self.hurt_flash_timer = 0.0

        self.hover_origin_x = x
        self.hover_origin_y = y  # midbottom y
        self.hover_time = 0.0

        self.attacking = False
        self.attack_cooldown_timer = 0.0
        self.slam_cooldown_timer = 0.0
        self.current_attack_is_slam = False
        self.death_anim_done = False
        self.pending_projectile = None  # scene collects this once per frame
        self.pending_slam = None        # scene collects this once per frame
        self._slam_sound = load_sound(SFX_DIR / "boss_slam.wav")

    def take_damage(self, amount):
        was_alive = not self.is_dead
        super().take_damage(amount)
        if was_alive and self.is_dead:
            self.frame_index = 0
            self.frame_timer = 0.0
        elif was_alive:
            self.hurt_flash_timer = HURT_FLASH_DURATION

    def update(self, dt, player=None):
        if self.hurt_flash_timer > 0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        if self.is_dead:
            self._animate_death(dt)
            return

        if player is not None:
            self.facing_right = player.rect.centerx >= self.rect.centerx

        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        if self.slam_cooldown_timer > 0:
            self.slam_cooldown_timer = max(0.0, self.slam_cooldown_timer - dt)

        if self.attacking:
            self._animate_attack(dt)
        else:
            self._update_hover(dt)
            self._animate_idle(dt)
            if player is not None:
                distance = abs(player.rect.centerx - self.rect.centerx)
                if distance <= SLAM_TRIGGER_RANGE and self.slam_cooldown_timer <= 0:
                    self._start_attack(is_slam=True)
                elif distance <= DETECTION_RANGE and self.attack_cooldown_timer <= 0:
                    self._start_attack(is_slam=False)

        if self.hurt_flash_timer > 0:
            frame = self.hurt_frames[0]
            self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _update_hover(self, dt):
        self.hover_time += dt
        sway = math.sin(self.hover_time * HOVER_SPEED) * HOVER_RANGE_X
        bob = math.sin(self.hover_time * HOVER_SPEED * 1.7) * HOVER_BOB_Y
        self.rect.centerx = int(self.hover_origin_x + sway)
        self.rect.bottom = int(self.hover_origin_y + bob)

    def _start_attack(self, is_slam):
        self.attacking = True
        self.current_attack_is_slam = is_slam
        self.frame_index = 0
        self.frame_timer = 0.0
        if is_slam:
            self.slam_cooldown_timer = SLAM_COOLDOWN
        else:
            self.attack_cooldown_timer = ATTACK_COOLDOWN

    def _animate_idle(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.idle_frames)
        frame = self.idle_frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _animate_attack(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index += 1
            if self.frame_index == len(self.attack_frames) - 1:
                if self.current_attack_is_slam:
                    self._trigger_slam_impact()
                else:
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
            self.rect.centerx, self.rect.centery, velocity, None, PROJECTILE_DAMAGE,
            frames=self.projectile_frames,
        )

    def take_pending_projectile(self):
        """Scene calls this once per frame to collect a freshly-fired
        projectile (or None) so it can be added to the scene's list."""
        projectile = self.pending_projectile
        self.pending_projectile = None
        return projectile

    def _trigger_slam_impact(self):
        play_sound(self._slam_sound)
        self.pending_slam = {
            "center": self.rect.midbottom,
            "crack_radius": SLAM_CRACK_RADIUS,
            "damage_range": SLAM_DAMAGE_RANGE,
            "damage": SLAM_DAMAGE,
        }

    def take_pending_slam(self):
        """Scene calls this once per frame; returns the slam's impact
        details exactly once, the moment it lands."""
        slam = self.pending_slam
        self.pending_slam = None
        return slam

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

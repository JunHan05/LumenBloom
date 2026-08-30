"""
enemy.py

Base Enemy class shared by every regular enemy: health, back-and-forth
patrol movement, contact damage to Iris, and death bookkeeping. Each
enemy in src/entities/enemies/ subclasses this and only needs to supply
its own sprite sheets, stats, and patrol range.
"""

import pygame

from config.settings import SFX_DIR
from src.core.asset_loader import load_sound, play_sound


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, max_hp, patrol_left, patrol_right,
                 patrol_speed, contact_damage):
        super().__init__()

        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.midbottom = (x, y)
        # Shared by every enemy/boss subclass — one generic "hit" cue on
        # any take_damage() call, regardless of which ability landed it.
        self._hit_sound = load_sound(SFX_DIR / "enemy_hit.wav")

        self.max_hp = max_hp
        self.hp = max_hp
        self.is_dead = False

        self.patrol_left = patrol_left
        self.patrol_right = patrol_right
        self.patrol_speed = patrol_speed
        self.facing_right = True

        self.contact_damage = contact_damage

        # Tendril Whip ("hits an enemy -> pulls it toward her") overrides
        # patrol movement for a short duration while pull_timer is active.
        self.pull_target = None
        self.pull_speed = 0
        self.pull_timer = 0.0

        # Lumen Bloom ("stunning enemies hit") freezes patrol movement for
        # a duration, same idea as the pull timer above.
        self.stunned_timer = 0.0

    def apply_stun(self, duration):
        """Freeze patrol movement for `duration` seconds — Lumen Bloom."""
        self.stunned_timer = max(self.stunned_timer, duration)

    def apply_pull(self, target_point, speed, duration):
        """Start being pulled toward target_point (Iris's position) for
        `duration` seconds — used by Tendril Whip."""
        self.pull_target = target_point
        self.pull_speed = speed
        self.pull_timer = duration

    def _update_pull(self, dt):
        target_x, target_y = self.pull_target
        dx = target_x - self.rect.centerx
        dy = target_y - self.rect.centery
        distance = (dx * dx + dy * dy) ** 0.5
        if distance > 1:
            self.rect.x += self.pull_speed * dt * (dx / distance)
            self.rect.y += self.pull_speed * dt * (dy / distance)
        self.pull_timer -= dt

    def patrol(self, dt):
        """Walk back and forth between patrol_left and patrol_right,
        turning around at each edge.

        Every enemy subclass calls this for its horizontal movement, so
        the Tendril Whip pull-check lives here (rather than in update())
        to guarantee it applies even though each subclass overrides
        update() with its own animation logic and calls patrol()
        directly instead of super().update()."""
        if self.pull_timer > 0:
            self._update_pull(dt)
            return

        if self.is_dead:
            return

        if self.stunned_timer > 0:
            self.stunned_timer -= dt
            return

        if self.facing_right:
            self.rect.x += self.patrol_speed * dt
            if self.rect.right >= self.patrol_right:
                self.rect.right = self.patrol_right
                self.facing_right = False
        else:
            self.rect.x -= self.patrol_speed * dt
            if self.rect.left <= self.patrol_left:
                self.rect.left = self.patrol_left
                self.facing_right = True

    def take_damage(self, amount):
        """Apply damage from a player ability. Marks the enemy dead at
        0 HP; subclasses handle the death animation and removal."""
        if self.is_dead:
            return

        self.hp -= amount
        play_sound(self._hit_sound)
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True

    def check_contact_damage(self, player):
        """If touching Iris, deal contact damage. Player.take_damage()
        has its own invulnerability window, so calling this every frame
        while overlapping is safe and won't over-damage her."""
        if not self.is_dead and self.rect.colliderect(player.rect):
            player.take_damage(self.contact_damage)

    def update(self, dt, player=None):
        """player is accepted (but unused by the base class) so every
        enemy type shares one call signature — scenes can loop over a
        mixed list of enemies and just call enemy.update(dt, player)."""
        self.patrol(dt)

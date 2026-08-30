"""
projectile.py

Generic projectile fired by enemies/bosses — spore projectiles (Murk
Crawler Elite), thorn projectiles (Briarling), etc. A single class
covers all of them; each shooter just picks a different image, speed,
and damage.
"""

import pygame


class Projectile(pygame.sprite.Sprite):
    FRAME_DURATION = 0.06  # only used when `frames` is given (animated projectile)

    def __init__(self, x, y, velocity, image, damage, max_range=600, frames=None):
        """image: a single static image, used unless `frames` is given.
        frames: optional list of frames to cycle through instead — e.g.
        the Jinn's swirling magic-orb projectile."""
        super().__init__()
        self.frames = frames
        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = frames[0] if frames else image
        self.rect = self.image.get_rect(center=(x, y))
        self.start_x = x
        self.start_y = y
        self.vx, self.vy = velocity
        self.damage = damage
        self.max_range = max_range
        self.spent = False  # True once the scene should remove it

    def update(self, dt, solid_rects=None):
        if self.frames:
            self.frame_timer += dt
            if self.frame_timer >= self.FRAME_DURATION:
                self.frame_timer = 0.0
                self.frame_index = (self.frame_index + 1) % len(self.frames)
                center = self.rect.center
                self.image = self.frames[self.frame_index]
                self.rect = self.image.get_rect(center=center)

        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt

        traveled = ((self.rect.centerx - self.start_x) ** 2 +
                    (self.rect.centery - self.start_y) ** 2) ** 0.5
        if traveled >= self.max_range:
            self.spent = True

        if solid_rects:
            for solid in solid_rects:
                if self.rect.colliderect(solid):
                    self.spent = True
                    break

    def check_hit_player(self, player):
        """Returns True (and marks itself spent) if it hits Iris."""
        if not self.spent and self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.spent = True
            return True
        return False

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class HomingPetal(Projectile):
    """A petal that curves toward a target over time rather than flying
    in a straight line — Aurelian Titan's petal barrage (Scene 4,
    PROJECT_BRIEF.md section 5), "deflectable with Glow Slash" via
    deflect() instead of exploding on Iris."""

    TURN_RATE = 3.0  # how quickly (radians/second, roughly) it can curve

    def __init__(self, x, y, velocity, image, damage, target, max_range=900):
        super().__init__(x, y, velocity, image, damage, max_range)
        self.target = target
        self.speed = (velocity[0] ** 2 + velocity[1] ** 2) ** 0.5

    def update(self, dt, solid_rects=None):
        if not self.spent and self.target is not None and not self.target.is_dead:
            dx = self.target.rect.centerx - self.rect.centerx
            dy = self.target.rect.centery - self.rect.centery
            distance = (dx * dx + dy * dy) ** 0.5
            if distance > 1:
                desired_vx = dx / distance * self.speed
                desired_vy = dy / distance * self.speed
                turn = min(1.0, self.TURN_RATE * dt)
                self.vx += (desired_vx - self.vx) * turn
                self.vy += (desired_vy - self.vy) * turn
        super().update(dt, solid_rects)

    def deflect(self):
        """Glow Slash knocks it out of the air instead of it hitting Iris."""
        self.spent = True

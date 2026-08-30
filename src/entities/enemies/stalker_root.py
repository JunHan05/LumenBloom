"""
stalker_root.py

Stalker Root — regular enemy in Scene 2 (The Skybloom Reach). A mossy
stone-golem creature that hides underground and ambushes Iris when she
walks near, briefly grabbing her before retreating back underground
(PROJECT_BRIEF.md section 6). Each placed instance is a one-time
ambush — once it retreats, it's done.
"""

import pygame

from config.settings import ENEMIES_IMG_DIR
from src.core.asset_loader import load_animation_frames
from src.entities.enemy import Enemy

EMERGE_FRAME_COUNT = 18
GRAB_FRAME_COUNT = 12
RETREAT_FRAME_COUNT = 15
FRAME_DURATION = 0.12
EMERGE_FRAME_DURATION = 0.05

MAX_HP = 80
CONTACT_DAMAGE = 15
WIDTH, HEIGHT = 96, 96
AMBUSH_RANGE = 120  # how close Iris must be (horizontally) to trigger the ambush

STATE_HIDDEN = "hidden"
STATE_EMERGING = "emerging"
STATE_GRABBING = "grabbing"
STATE_RETREATING = "retreating"


class StalkerRoot(Enemy):
    def __init__(self, x, y):
        # Patrol slowly left and right after emerging
        patrol_left = x - 96
        patrol_right = x + 96
        patrol_speed = 45
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, patrol_left, patrol_right,
                         patrol_speed, CONTACT_DAMAGE)

        size = (WIDTH, HEIGHT)
        self.emerge_frames = load_animation_frames(ENEMIES_IMG_DIR, "stalker_root_emerge", EMERGE_FRAME_COUNT, size=size)
        self.grab_frames = load_animation_frames(ENEMIES_IMG_DIR, "stalker_root_grab", GRAB_FRAME_COUNT, size=size)
        self.retreat_frames = load_animation_frames(ENEMIES_IMG_DIR, "stalker_root_retreat", RETREAT_FRAME_COUNT, size=size)

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.emerge_frames[0]
        self.state = STATE_HIDDEN
        self.death_anim_done = False
        self._just_emerged = False

    def take_pending_emergence(self):
        """Scene calls this once per frame; returns True exactly once when emerging."""
        if self._just_emerged:
            self._just_emerged = False
            return True
        return False

    def take_damage(self, amount):
        if self.state == STATE_HIDDEN:
            return  # can't be hurt while hidden underground
        self.hp -= amount
        if self.hp <= 0 and not self.is_dead:
            self.is_dead = True
            self.state = STATE_RETREATING
            self.frame_index = 0
            self.frame_timer = 0.0

    def check_contact_damage(self, player):
        # Only grabs during the grab state, not while hidden/emerging/retreating.
        if self.state == STATE_GRABBING and not self.is_dead and self.rect.colliderect(player.rect):
            player.take_damage(self.contact_damage)

    def update(self, dt, player=None):
        if self.is_dead:
            if self.state == STATE_RETREATING:
                self._animate(dt, self.retreat_frames, next_state=None, on_finish=self._finish_death)
            else:
                self.death_anim_done = True
            return

        if self.state == STATE_HIDDEN:
            if player is not None and abs(player.rect.centerx - self.rect.centerx) <= AMBUSH_RANGE:
                self._start_emerging()
        elif self.state == STATE_EMERGING:
            self._animate(dt, self.emerge_frames, next_state=STATE_GRABBING, frame_duration=EMERGE_FRAME_DURATION)
        elif self.state == STATE_GRABBING:
            self.patrol(dt)
            self._animate_loop(dt, self.grab_frames)

    def _start_emerging(self):
        self.state = STATE_EMERGING
        self.frame_index = 0
        self.frame_timer = 0.0
        self._just_emerged = True

    def _animate(self, dt, frames, next_state, on_finish=None, frame_duration=FRAME_DURATION):
        self.frame_timer += dt
        if self.frame_timer >= frame_duration:
            self.frame_timer = 0.0
            if self.frame_index < len(frames) - 1:
                self.frame_index += 1
            elif on_finish is not None:
                on_finish()
            elif next_state is not None:
                self.state = next_state
                self.frame_index = 0
        frame = frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _animate_loop(self, dt, frames):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(frames)
        frame = frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _finish_death(self):
        self.death_anim_done = True

    def draw(self, surface, camera_offset=(0, 0)):
        if self.state == STATE_HIDDEN:
            return  # hidden underground, nothing to draw
        # +6px vertical offset so roots rest flush on the floor surface
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y + 6 - camera_offset[1]))

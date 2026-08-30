"""
sky_wisp.py

Sky Wisp — the boss of Scene 2 (The Skybloom Reach). A purple/gold
winged dragon that hovers and dives at Iris. Phase 2 (below 50% HP)
dives faster and roars, summoning Briarlings (PROJECT_BRIEF.md
sections 5 & 6).
"""

import math

import pygame

from config.settings import BOSSES_IMG_DIR
from src.core.asset_loader import load_animation_frames
from src.entities.bosses.boss_base import Boss

FLY_FRAME_COUNT = 5
DIVE_FRAME_COUNT = 4
ROAR_FRAME_COUNT = 6
HURT_FRAME_COUNT = 2
DEATH_FRAME_COUNT = 5
FRAME_DURATION = 0.12
HURT_FLASH_DURATION = 0.2

MAX_HP = 400
CONTACT_DAMAGE = 20
WIDTH, HEIGHT = 240, 240

HOVER_RANGE = 250       # how far it drifts side to side while hovering
HOVER_SPEED = 0.7       # radians/second of the horizontal sway
HOVER_BOB_AMPLITUDE = 40   # pixels up/down for the vertical bob
HOVER_BOB_SPEED = 1.8   # vertical bob is faster than horizontal sway (out-of-phase figure-8)

DIVE_COOLDOWN_P1 = 3.0
DIVE_SPEED_P1 = 260
DIVE_COOLDOWN_P2 = 1.6   # phase 2: dives more often...
DIVE_SPEED_P2 = 380      # ...and faster

ROAR_DURATION = 0.6


class SkyWisp(Boss):
    NAME = "Sky Wisp"
    PHASE_THRESHOLDS = (1.0, 0.5)

    def __init__(self, x, y):
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, CONTACT_DAMAGE)

        size = (WIDTH, HEIGHT)
        self.fly_frames = load_animation_frames(BOSSES_IMG_DIR, "sky_wisp_fly", FLY_FRAME_COUNT, size=size)
        self.dive_frames = load_animation_frames(BOSSES_IMG_DIR, "sky_wisp_dive", DIVE_FRAME_COUNT, size=size)
        self.roar_frames = load_animation_frames(BOSSES_IMG_DIR, "sky_wisp_roar", ROAR_FRAME_COUNT, size=size)
        self.hurt_frames = load_animation_frames(BOSSES_IMG_DIR, "sky_wisp_hurt", HURT_FRAME_COUNT, size=size)
        self.death_frames = load_animation_frames(BOSSES_IMG_DIR, "sky_wisp_death", DEATH_FRAME_COUNT, size=size)

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.fly_frames[0]
        self.hurt_flash_timer = 0.0

        self.hover_origin_x = x
        self.hover_y = y
        self.hover_time = 0.0

        self.flight_state = "hover"  # hover, diving, roaring
        self.dive_cooldown_timer = DIVE_COOLDOWN_P1
        self.dive_target_y = y
        self.dive_phase = None  # "descending" or "ascending", set in _start_dive
        self.roar_timer = 0.0
        self.should_summon_briarlings = False  # scene reads & clears this
        self._pending_dive_impact = None  # set when the boss lands a dive; scene reads & clears this

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.is_dead:
            self.hurt_flash_timer = HURT_FLASH_DURATION

    def on_phase_change(self, phase_index):
        """Entering phase 2: roar and flag the scene to summon Briarlings."""
        self.flight_state = "roaring"
        self.roar_timer = 0.0
        self.frame_index = 0
        self.frame_timer = 0.0
        self.should_summon_briarlings = True

    def take_pending_summon(self):
        """Scene calls this once per frame; returns True exactly once,
        the moment the boss roars into phase 2."""
        if self.should_summon_briarlings:
            self.should_summon_briarlings = False
            return True
        return False

    def take_pending_dive_impact(self):
        """Scene calls this once per frame; returns the impact position
        (center tuple) exactly once per dive landing, or None."""
        impact = self._pending_dive_impact
        self._pending_dive_impact = None
        return impact

    def update(self, dt, player=None):
        if self.hurt_flash_timer > 0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        if self.is_dead:
            self._animate(dt, self.death_frames, loop=False, on_finish=self._mark_death_done)
        elif self.flight_state == "roaring":
            self.roar_timer += dt
            self._animate(dt, self.roar_frames, loop=True)
            if self.roar_timer >= ROAR_DURATION:
                self.flight_state = "hover"
                self.dive_cooldown_timer = self._current_dive_cooldown()
        elif self.flight_state == "hover":
            self._update_hover(dt, player)
            self._animate(dt, self.fly_frames, loop=True)
            if self.dive_cooldown_timer > 0:
                self.dive_cooldown_timer -= dt
            elif player is not None:
                self._start_dive(player)
        elif self.flight_state == "diving":
            self._update_dive(dt)
            self._animate(dt, self.dive_frames, loop=True)

        if self.hurt_flash_timer > 0 and not self.is_dead:
            frame = self.hurt_frames[0]
            self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _current_dive_cooldown(self):
        return DIVE_COOLDOWN_P1 if self.phase == 0 else DIVE_COOLDOWN_P2

    def _current_dive_speed(self):
        return DIVE_SPEED_P1 if self.phase == 0 else DIVE_SPEED_P2

    def _update_hover(self, dt, player):
        self.hover_time += dt
        # Horizontal sway — slow sine wave across the arena
        sway_x = math.sin(self.hover_time * HOVER_SPEED) * HOVER_RANGE
        # Vertical bob — faster sine wave (out-of-phase) so the path is a
        # smooth figure-8 instead of a flat left-right slide
        bob_y = math.sin(self.hover_time * HOVER_BOB_SPEED) * HOVER_BOB_AMPLITUDE
        self.rect.centerx = int(self.hover_origin_x + sway_x)
        self.rect.y = int(self.hover_y + bob_y)
        if player is not None:
            self.facing_right = player.rect.centerx >= self.rect.centerx

    def _start_dive(self, player):
        self.flight_state = "diving"
        self.dive_phase = "descending"
        self.dive_target_y = player.rect.centery
        self.frame_index = 0
        self.frame_timer = 0.0

    def _update_dive(self, dt):
        # One-way phase transition (descending -> ascending -> hover)
        # rather than re-deriving direction from a position comparison
        # each frame — comparing centery to dive_target_y every frame
        # flip-flops right at the crossing point and never resolves.
        dive_speed = self._current_dive_speed()
        if self.dive_phase == "descending":
            self.rect.y += int(dive_speed * dt)
            if self.rect.centery >= self.dive_target_y:
                # Signal the scene that the dive just landed
                self._pending_dive_impact = self.rect.midbottom
                self.dive_phase = "ascending"
        else:
            self.rect.y -= int(dive_speed * dt)
            if self.rect.y <= self.hover_y:
                self.rect.y = self.hover_y
                self.flight_state = "hover"
                self.dive_cooldown_timer = self._current_dive_cooldown()

    def _animate(self, dt, frames, loop, on_finish=None):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            if self.frame_index < len(frames) - 1:
                self.frame_index += 1
            elif loop:
                self.frame_index = 0
            elif on_finish is not None:
                on_finish()
        frame = frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _mark_death_done(self):
        self.death_anim_done = True

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))

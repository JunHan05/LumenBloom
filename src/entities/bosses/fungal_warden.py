"""
fungal_warden.py

Fungal Warden — the boss of Scene 3 (The Hollow Spire). A tall hooded
figure in an earthy cloak with glowing eyes (PROJECT_BRIEF.md section
6). Phase 1 patrols and ground-slams, cracking nearby floor tiles.
Phase 2 (below 50% HP) plants itself in place, alternating a wider
slam with a spore rain around Iris (section 5).

Like Sky Wisp, this boss only signals its attacks (pending_slam /
pending_spore_rain) rather than touching the tilemap, screen shake, or
player HP directly — the scene is the only thing that owns those
systems, so it resolves what each signal actually does.
"""

import pygame

from config.settings import BOSSES_IMG_DIR, TILE_SIZE
from src.core.asset_loader import load_animation_frames
from src.entities.bosses.boss_base import Boss

WALK_FRAME_COUNT = 24
SLAM_FRAME_COUNT = 12
SPORE_RAIN_FRAME_COUNT = 12
HURT_FRAME_COUNT = 12
DEATH_FRAME_COUNT = 15
FRAME_DURATION = 0.15
HURT_FLASH_DURATION = 0.2

MAX_HP = 500
CONTACT_DAMAGE = 20
WIDTH, HEIGHT = 140, 140

PATROL_SPEED = 50
PATROL_RANGE = 3 * TILE_SIZE  # each side of its starting point, phase 1 only

SLAM_COOLDOWN_P1 = 3.2
SLAM_COOLDOWN_P2 = 2.6
SLAM_IMPACT_FRAME = 7           # frame index the slam actually lands on
SLAM_CRACK_RADIUS_P1 = 1        # tiles, fed to tilemap.crack_tiles_near
SLAM_CRACK_RADIUS_P2 = 2        # "wider slam" in phase 2
SLAM_DAMAGE_RANGE_P1 = 90       # pixels either side of the Warden
SLAM_DAMAGE_RANGE_P2 = 150
SLAM_DAMAGE = 25

SPORE_RAIN_COOLDOWN = 4.5
SPORE_RAIN_DURATION = 2.0
SPORE_RAIN_RADIUS = 110
SPORE_RAIN_DAMAGE_PER_SECOND = 15


class FungalWarden(Boss):
    NAME = "Fungal Warden"
    PHASE_THRESHOLDS = (1.0, 0.5)

    def __init__(self, x, y):
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, CONTACT_DAMAGE)

        size = (WIDTH, HEIGHT)
        self.walk_frames = load_animation_frames(BOSSES_IMG_DIR, "fungal_warden_walk", WALK_FRAME_COUNT, size=size)
        self.slam_frames = load_animation_frames(BOSSES_IMG_DIR, "fungal_warden_slam", SLAM_FRAME_COUNT, size=size)
        self.spore_rain_frames = load_animation_frames(
            BOSSES_IMG_DIR, "fungal_warden_spore_rain", SPORE_RAIN_FRAME_COUNT, size=size)
        self.hurt_frames = load_animation_frames(BOSSES_IMG_DIR, "fungal_warden_hurt", HURT_FRAME_COUNT, size=size)
        self.death_frames = load_animation_frames(BOSSES_IMG_DIR, "fungal_warden_death", DEATH_FRAME_COUNT, size=size)

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.walk_frames[0]
        self.hurt_flash_timer = 0.0

        # Boss.__init__ collapses patrol bounds to a single point (most
        # bosses drive their own movement) — Fungal Warden is the
        # exception, it genuinely walks a patrol in phase 1, so it
        # widens those bounds back out and reuses Enemy.patrol() as-is.
        self.patrol_left = x - PATROL_RANGE
        self.patrol_right = x + PATROL_RANGE
        self.patrol_speed = PATROL_SPEED

        self.action_state = "walk"  # walk, slam, spore_rain
        self.slam_cooldown_timer = SLAM_COOLDOWN_P1
        self.spore_rain_cooldown_timer = SPORE_RAIN_COOLDOWN
        self.spore_rain_elapsed = 0.0
        self.slam_impact_done = False

        self.pending_slam = None        # scene reads once via take_pending_slam()
        self.pending_spore_rain = None  # scene reads once via take_pending_spore_rain()

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.is_dead:
            self.hurt_flash_timer = HURT_FLASH_DURATION

    def on_phase_change(self, phase_index):
        """Entering phase 2: stop patrolling and switch to the tighter
        phase-2 attack pacing (PROJECT_BRIEF.md section 5: "Phase 2:
        stationary, rains spores from above, wider slam")."""
        self.action_state = "walk"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.slam_cooldown_timer = SLAM_COOLDOWN_P2
        self.spore_rain_cooldown_timer = SPORE_RAIN_COOLDOWN

    def update(self, dt, player=None):
        if self.hurt_flash_timer > 0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        if self.is_dead:
            self._animate(dt, self.death_frames, loop=False, on_finish=self._mark_death_done)
        elif self.action_state == "slam":
            self._update_slam(dt, player)
        elif self.action_state == "spore_rain":
            self._update_spore_rain(dt, player)
        else:
            self._update_walk(dt, player)

        if self.hurt_flash_timer > 0 and not self.is_dead:
            frame = self.hurt_frames[0]
            self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _update_walk(self, dt, player):
        if self.phase == 0:
            self.patrol(dt)
        elif player is not None:
            # Phase 2: stationary, just keep facing Iris.
            self.facing_right = player.rect.centerx >= self.rect.centerx

        self._animate(dt, self.walk_frames, loop=True)

        self.slam_cooldown_timer -= dt
        if self.phase >= 1:
            self.spore_rain_cooldown_timer -= dt

        if self.slam_cooldown_timer <= 0:
            self._start_slam()
        elif self.phase >= 1 and self.spore_rain_cooldown_timer <= 0:
            self._start_spore_rain()

    def _start_slam(self):
        self.action_state = "slam"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.slam_impact_done = False

    def _update_slam(self, dt, player):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            if self.frame_index < len(self.slam_frames) - 1:
                self.frame_index += 1
                if self.frame_index == SLAM_IMPACT_FRAME and not self.slam_impact_done:
                    self._trigger_slam_impact()
            else:
                self.action_state = "walk"
                self.frame_index = 0
                self.slam_cooldown_timer = SLAM_COOLDOWN_P2 if self.phase >= 1 else SLAM_COOLDOWN_P1

        frame = self.slam_frames[min(self.frame_index, len(self.slam_frames) - 1)]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _trigger_slam_impact(self):
        self.slam_impact_done = True
        wide = self.phase >= 1
        grid_x = self.rect.centerx // TILE_SIZE
        grid_y = self.rect.bottom // TILE_SIZE
        self.pending_slam = {
            "grid_pos": (grid_x, grid_y),
            "center": self.rect.midbottom,
            "crack_radius": SLAM_CRACK_RADIUS_P2 if wide else SLAM_CRACK_RADIUS_P1,
            "damage_range": SLAM_DAMAGE_RANGE_P2 if wide else SLAM_DAMAGE_RANGE_P1,
            "damage": SLAM_DAMAGE,
        }

    def take_pending_slam(self):
        """Scene calls this once per frame; returns the slam's impact
        details exactly once, the moment it lands."""
        slam = self.pending_slam
        self.pending_slam = None
        return slam

    def _start_spore_rain(self):
        self.action_state = "spore_rain"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.spore_rain_elapsed = 0.0
        self.pending_spore_rain = {
            "center": self.rect.center,
            "radius": SPORE_RAIN_RADIUS,
            "duration": SPORE_RAIN_DURATION,
            "damage_per_second": SPORE_RAIN_DAMAGE_PER_SECOND,
        }

    def take_pending_spore_rain(self):
        """Scene calls this once per frame; returns the spore rain's
        parameters exactly once, the moment it starts."""
        spore_rain = self.pending_spore_rain
        self.pending_spore_rain = None
        return spore_rain

    def _update_spore_rain(self, dt, player):
        self._animate(dt, self.spore_rain_frames, loop=True)
        self.spore_rain_elapsed += dt
        if self.spore_rain_elapsed >= SPORE_RAIN_DURATION:
            self.action_state = "walk"
            self.frame_index = 0
            self.spore_rain_cooldown_timer = SPORE_RAIN_COOLDOWN

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
        # +14px vertical offset to remove transparent bottom padding so the feet rest flush on the floor
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y + 14 - camera_offset[1]))

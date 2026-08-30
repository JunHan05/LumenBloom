"""
bug_boss.py

Bug Boss — Scene 1's true final boss, fought beyond a breakable door
past Jinn Monster's arena (scenes/scene1_grotto.py). Stays passive
until Iris crosses into its arena; once awake it walks toward her
whenever she's out of melee range (bug_boss_walk), then attacks with a
close-range lunging strike (bug_boss_attack, punctuated by a
bug_boss_slash_fx overlay at the moment it lands) or, if her range and
its ranged cooldown line up, a ground-shockwave "Stomp" instead (only
dodgeable by jumping — see world/hazards.py's GroundSpikeWave).
"""

import pygame

from config.settings import BOSSES_IMG_DIR, SFX_DIR, TILE_SIZE
from src.core.asset_loader import load_animation_frames, load_sound, play_sound
from src.entities.bosses.boss_base import Boss

IDLE_FRAME_COUNT = 1
WALK_FRAME_COUNT = 5
ATTACK_FRAME_COUNT = 10
SLASH_FX_FRAME_COUNT = 2
STOMP_FRAME_COUNT = 4
HURT_FRAME_COUNT = 1
DEATH_FRAME_COUNT = 9
FRAME_DURATION = 0.15
HURT_FLASH_DURATION = 0.2

MAX_HP = 350
CONTACT_DAMAGE = 20
WIDTH, HEIGHT = 182, 114  # source art's native trimmed crop (~1.6:1), displayed at full size

# Chasing: whenever Iris is out of MELEE_RANGE and no attack is ready
# yet, the boss walks toward her instead of just standing still — but
# never more than PATROL_RANGE from where it spawned, so it can't be
# lured out of its own arena.
#
# Both WALK_SPEED and ATTACK_LUNGE_SPEED are kept with a large safety
# margin under Iris's own top speed (300px/s at the game's nominal
# 60fps) rather than just barely under it. Her movement is frame-based
# (a fixed px/frame, not scaled by dt), while this boss's movement is
# time-based (scaled by dt) — so her *real-world* speed quietly drops
# if the actual framerate ever dips below 60, while the boss's doesn't.
# At 30fps she's only moving 150px/s; a lunge speed close to her
# nominal 300 would already outpace her there. Keeping both well below
# even her half-framerate speed means the boss can't out-chase her
# during an ordinary hitch, not just under perfect 60fps.
WALK_SPEED = 55
PATROL_RANGE = 6 * TILE_SIZE

# Melee "Attack" — a close-range lunge, used once Iris is within
# MELEE_RANGE. The boss actually dashes forward (ATTACK_LUNGE_SPEED)
# while its windup frames play, matching the lunge already drawn into
# the art, so its rect (and the slash_fx overlay, which tracks it live)
# arrive together instead of the effect appearing to lag behind a
# body that visually dove forward but never actually moved.
# bug_boss_slash_fx plays as a cosmetic overlay at the same instant the
# hit lands (ATTACK_IMPACT_FRAME).
MELEE_RANGE = 130
ATTACK_COOLDOWN = 2.2
ATTACK_IMPACT_FRAME = 6
ATTACK_LUNGE_SPEED = 90  # px/second, only while frame_index < ATTACK_IMPACT_FRAME
ATTACK_DAMAGE_RANGE = 140
ATTACK_DAMAGE = 25

# Ranged "Stomp" — a ground shockwave used only while Iris is between
# MELEE_RANGE and STOMP_MAX_RANGE; beyond that it's too far for the
# wave to ever reach (world/hazards.py's GroundSpikeWave fizzles out
# after the same ~8 tiles), so the boss stops throwing it uselessly and
# just walks or waits instead.
STOMP_COOLDOWN = 3.0
STOMP_IMPACT_FRAME = 2
STOMP_DAMAGE = 20
STOMP_MAX_RANGE = 8 * TILE_SIZE


class BugBoss(Boss):
    """Scene 1's final boss. Single-phase — it tracks which side Iris
    is on, walks toward her when she's out of reach, and reacts once
    she wakes it up by crossing trigger_x."""

    NAME = "Bug Boss"
    PHASE_THRESHOLDS = (1.0,)  # single phase: never transitions

    def __init__(self, x, y, trigger_x):
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, CONTACT_DAMAGE)

        size = (WIDTH, HEIGHT)
        self.idle_frames = load_animation_frames(BOSSES_IMG_DIR, "bug_boss_idle", IDLE_FRAME_COUNT, size=size)
        self.walk_frames = load_animation_frames(BOSSES_IMG_DIR, "bug_boss_walk", WALK_FRAME_COUNT, size=size)
        self.attack_frames = load_animation_frames(BOSSES_IMG_DIR, "bug_boss_attack", ATTACK_FRAME_COUNT, size=size)
        self.stomp_frames = load_animation_frames(BOSSES_IMG_DIR, "bug_boss_stomp", STOMP_FRAME_COUNT, size=size)
        self.hurt_frames = load_animation_frames(BOSSES_IMG_DIR, "bug_boss_hurt", HURT_FRAME_COUNT, size=size)
        self.death_frames = load_animation_frames(BOSSES_IMG_DIR, "bug_boss_death", DEATH_FRAME_COUNT, size=size)
        # Native size, not scaled to (WIDTH, HEIGHT) — its 2 frames have
        # very different silhouettes/aspect ratios (a diagonal streak vs
        # a wide horizontal one), so forcing one box would stretch them.
        self.slash_fx_frames = load_animation_frames(BOSSES_IMG_DIR, "bug_boss_slash_fx", SLASH_FX_FRAME_COUNT)

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.idle_frames[0]
        self.hurt_flash_timer = 0.0

        # Iris approaches from the left, so the boss starts facing her
        # entry direction instead of Enemy's default facing_right=True.
        self.facing_right = False

        self.trigger_x = trigger_x
        self.aggro = False  # one-way switch: once True, never goes back to passive
        self.spawn_x = self.rect.centerx  # walk() never strays more than PATROL_RANGE from this

        self.action_state = "idle"  # idle, walk, attack, stomp
        self.attack_cooldown_timer = ATTACK_COOLDOWN
        self.stomp_cooldown_timer = STOMP_COOLDOWN

        self.pending_stomp = None       # scene reads once via take_pending_stomp()
        self.pending_attack_hit = None  # scene reads once via take_pending_attack_hit()
        self.pending_slash_fx = None    # scene reads once via take_pending_slash_fx()

        self._attack_sound = load_sound(SFX_DIR / "boss_slam.wav")

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.is_dead:
            self.hurt_flash_timer = HURT_FLASH_DURATION

    def check_contact_damage(self, player):
        """Override Enemy's default touch-damage — only the Attack and
        Stomp hits (pending_attack_hit / pending_stomp) should hurt
        Iris; merely brushing against its body should not."""
        pass

    def update(self, dt, player=None):
        if self.hurt_flash_timer > 0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        if self.is_dead:
            self._animate(dt, self.death_frames, loop=False, on_finish=self._mark_death_done)
            return

        if player is not None:
            self.facing_right = player.rect.centerx >= self.rect.centerx
            if not self.aggro and player.rect.centerx >= self.trigger_x:
                self.aggro = True

        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        if self.stomp_cooldown_timer > 0:
            self.stomp_cooldown_timer = max(0.0, self.stomp_cooldown_timer - dt)

        if self.action_state == "attack":
            self._update_attack(dt)
        elif self.action_state == "stomp":
            self._update_stomp(dt)
        elif self.action_state == "walk":
            self._update_walk(dt, player)
        else:
            self._animate(dt, self.idle_frames, loop=True)
            if self.aggro and player is not None:
                self._decide_next_action(player)

        if self.hurt_flash_timer > 0 and not self.is_dead:
            frame = self.hurt_frames[0]
            self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _decide_next_action(self, player):
        distance = abs(player.rect.centerx - self.rect.centerx)
        if distance <= MELEE_RANGE and self.attack_cooldown_timer <= 0:
            self._start_attack()
        elif MELEE_RANGE < distance <= STOMP_MAX_RANGE and self.stomp_cooldown_timer <= 0:
            self._start_stomp()
        elif distance > MELEE_RANGE:
            # Neither attack is ready yet (or Iris is beyond even the
            # Stomp's reach) — close the distance instead of standing
            # there or throwing a shockwave that could never land.
            self._start_walk()

    def _start_walk(self):
        self.action_state = "walk"
        self.frame_index = 0
        self.frame_timer = 0.0

    def _update_walk(self, dt, player):
        self._animate(dt, self.walk_frames, loop=True)
        if player is None:
            return

        direction = 1 if player.rect.centerx >= self.rect.centerx else -1
        self.rect.x += WALK_SPEED * dt * direction

        # Never wander more than PATROL_RANGE from the spawn point —
        # Iris can't lure it out of its own arena.
        min_centerx = self.spawn_x - PATROL_RANGE
        max_centerx = self.spawn_x + PATROL_RANGE
        self.rect.centerx = max(min_centerx, min(max_centerx, self.rect.centerx))

        distance = abs(player.rect.centerx - self.rect.centerx)
        pinned_at_boundary = self.rect.centerx in (min_centerx, max_centerx)
        # Stop walking once close enough to attack, once within Stomp
        # range with that cooldown ready, or once it's hit the edge of
        # its patrol range and simply can't get any closer (rather than
        # animating in place forever).
        stomp_ready_in_range = distance <= STOMP_MAX_RANGE and self.stomp_cooldown_timer <= 0
        if distance <= MELEE_RANGE or stomp_ready_in_range or pinned_at_boundary:
            self.action_state = "idle"
            self.frame_index = 0

    def _start_attack(self):
        self.action_state = "attack"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.attack_cooldown_timer = ATTACK_COOLDOWN

    def _update_attack(self, dt):
        if self.frame_index < ATTACK_IMPACT_FRAME:
            # Dash forward through the windup so the hitbox actually
            # arrives where the art's lunge is heading, instead of the
            # sprite diving forward while the rect stays put.
            direction = 1 if self.facing_right else -1
            self.rect.x += ATTACK_LUNGE_SPEED * dt * direction
            min_centerx = self.spawn_x - PATROL_RANGE
            max_centerx = self.spawn_x + PATROL_RANGE
            self.rect.centerx = max(min_centerx, min(max_centerx, self.rect.centerx))

        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index += 1
            if self.frame_index == ATTACK_IMPACT_FRAME:
                self._trigger_attack_hit()
            if self.frame_index >= len(self.attack_frames):
                self.action_state = "idle"
                self.frame_index = 0

        frame = self.attack_frames[min(self.frame_index, len(self.attack_frames) - 1)]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _trigger_attack_hit(self):
        play_sound(self._attack_sound)
        self.pending_attack_hit = {
            "center": self.rect.center,
            "damage_range": ATTACK_DAMAGE_RANGE,
            "damage": ATTACK_DAMAGE,
        }
        # No frozen position here — the scene anchors the slash_fx
        # overlay to this boss instance directly, so it tracks rect
        # live (including the lunge above) rather than lagging behind.
        self.pending_slash_fx = {
            "facing_right": self.facing_right,
        }

    def take_pending_attack_hit(self):
        """Scene calls this once per frame; returns the melee attack's
        impact details exactly once, the moment it lands."""
        hit = self.pending_attack_hit
        self.pending_attack_hit = None
        return hit

    def take_pending_slash_fx(self):
        """Scene calls this once per frame; returns the cosmetic
        slash-streak overlay's spawn details exactly once, alongside
        take_pending_attack_hit()."""
        fx = self.pending_slash_fx
        self.pending_slash_fx = None
        return fx

    def _start_stomp(self):
        self.action_state = "stomp"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.stomp_cooldown_timer = STOMP_COOLDOWN

    def _update_stomp(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index += 1
            if self.frame_index == STOMP_IMPACT_FRAME:
                self._trigger_stomp()
            if self.frame_index >= len(self.stomp_frames):
                self.action_state = "idle"
                self.frame_index = 0

        frame = self.stomp_frames[min(self.frame_index, len(self.stomp_frames) - 1)]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _trigger_stomp(self):
        play_sound(self._attack_sound)
        direction = 1 if self.facing_right else -1
        self.pending_stomp = {
            "x": self.rect.centerx,
            "floor_y": self.rect.bottom,
            "direction": direction,
            "damage": STOMP_DAMAGE,
        }

    def take_pending_stomp(self):
        """Scene calls this once per frame; returns the Stomp's ground-
        wave parameters exactly once, the moment it launches."""
        stomp = self.pending_stomp
        self.pending_stomp = None
        return stomp

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

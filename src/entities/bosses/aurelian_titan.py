"""
aurelian_titan.py

Aurelian Titan — the final boss of Scene 4 (The Last Radiance). A giant
tree/root creature with a bark body and leaves (PROJECT_BRIEF.md
section 6). Three phases: P1 traps Iris in root cages, P2 adds a
homing petal barrage and comet drops, P3 combines all three attacks,
faster, with the sprite scaled up ~1.2x (section 5).

Like the other bosses, this one only signals its attacks — the scene
owns the arena, the player's cage state, and spawning
petals/comets/craters, so it resolves what each signal actually does.
"""

import math
import random

import pygame

from config.settings import BOSSES_IMG_DIR, SFX_DIR
from src.core.asset_loader import load_animation_frames, load_sound, play_sound
from src.entities.bosses.boss_base import Boss
from src.effects.particles import Particle

# One shared frame set covers root-cage/petal-barrage/comet casts alike —
# there's only a single "slam" animation, not a separate cast per attack
# kind, so every attack telegraphs with the same wind-up.
IDLE_FRAME_COUNT = 5
CAST_FRAME_COUNT = 20
HURT_FRAME_COUNT = 17
DEATH_FRAME_COUNT = 22

IDLE_FRAME_DURATION = 0.15
CAST_FRAME_DURATION = 0.045
HURT_FRAME_DURATION = 0.05
DEATH_FRAME_DURATION = 0.08
HURT_FLASH_DURATION = 0.2

MAX_HP = 800
CONTACT_DAMAGE = 25
WIDTH, HEIGHT = 300, 250
PHASE3_SCALE = 1.2  # "sprite scaled up ~1.2x in code", applied on top of the size above

CAST_IMPACT_FRACTION = 0.6  # how far into the (now much longer) cast the attack actually fires

IDLE_SHAKE_AMPLITUDE = (2, 1)  # (x px, y px) — "rooted: shakes in place" while idling

ROOT_CAGE_DURATION = 2.5
ROOT_CAGE_COOLDOWN_P1 = 4.0
ROOT_CAGE_COOLDOWN_P3 = 2.5

PETAL_COUNT_P2 = 5
PETAL_COUNT_P3 = 8
PETAL_SPEED_P2 = 180
PETAL_SPEED_P3 = 260
PETAL_DAMAGE = 10
PETAL_BARRAGE_COOLDOWN_P2 = 5.0
PETAL_BARRAGE_COOLDOWN_P3 = 3.2

COMET_COOLDOWN_P2 = 6.0
COMET_COOLDOWN_P3 = 3.8
COMET_FALL_SPEED_P2 = 260
COMET_FALL_SPEED_P3 = 380
COMET_DAMAGE = 30

# Reveal, on first becoming visible (see draw()/_draw_reveal()): a dark
# backlit silhouette resolves into full color over REVEAL_DURATION, with a
# faster punch-in overshoot (scaled slightly oversized, easing down to
# 1.0x) layered on top for the first PUNCH_DURATION of that same window.
REVEAL_DURATION = 1.1
PUNCH_DURATION = 0.35
PUNCH_SCALE_START = 1.3
REVEAL_GLOW_COLOR = (255, 140, 40)

# Idle ambient embers — small motes drifting up off the Titan so it never
# reads as fully static between attacks. Self-contained (own Particle
# list), since the scene's shared ParticleSystem isn't reachable from here.
AMBIENT_EMBER_INTERVAL = 0.35
AMBIENT_EMBER_COLOR = (255, 170, 80)


class AurelianTitan(Boss):
    NAME = "Aurelian Titan"
    PHASE_THRESHOLDS = (1.0, 0.66, 0.33)
    # Same defaults as Boss for now (40/22/20) — change any of these to
    # resize/reposition just the Titan's bar without touching Sky Wisp's
    # or the Fungal Warden's, which still use Boss's defaults.
    HEALTH_BAR_MARGIN = 250
    HEALTH_BAR_HEIGHT = 22
    HEALTH_BAR_Y = 30

    def __init__(self, x, y):
        super().__init__(x, y, WIDTH, HEIGHT, MAX_HP, CONTACT_DAMAGE)

        size = (WIDTH, HEIGHT)
        self.idle_frames = load_animation_frames(BOSSES_IMG_DIR, "aurelian_titan_idle", IDLE_FRAME_COUNT, size=size)
        # "aurelian_titan_slam" is the one cast animation shared by every
        # attack kind (root cage / petal barrage / comet slam) — there's no
        # separate windup per attack type in the asset set.
        self.cast_frames = load_animation_frames(BOSSES_IMG_DIR, "aurelian_titan_slam", CAST_FRAME_COUNT, size=size)
        self.hurt_frames = load_animation_frames(BOSSES_IMG_DIR, "aurelian_titan_hurt", HURT_FRAME_COUNT, size=size)
        self.death_frames = load_animation_frames(
            BOSSES_IMG_DIR, "aurelian_titan_death", DEATH_FRAME_COUNT, size=size)
        self.cast_impact_frame = max(1, int(len(self.cast_frames) * CAST_IMPACT_FRACTION))

        self.frame_index = 0
        self.frame_timer = 0.0
        self.image = self.idle_frames[0]
        self.hurt_flash_timer = 0.0
        self.scaled_up = False

        # Shared wind-up roar for every attack kind (root cage / petal
        # barrage / comet slam all telegraph with the same cast animation,
        # so one sound covers all three) plus a one-shot death cue.
        self._attack_sound = load_sound(SFX_DIR / "titan_attack.wav")
        self._death_sound = load_sound(SFX_DIR / "titan_death.wav")

        self.action_state = "idle"  # idle, root_cage, petal_barrage, comet_slam
        self.action_impact_done = False
        self.root_cage_cooldown_timer = ROOT_CAGE_COOLDOWN_P1
        self.petal_barrage_cooldown_timer = PETAL_BARRAGE_COOLDOWN_P2
        self.comet_cooldown_timer = COMET_COOLDOWN_P2

        self.pending_root_cage = None      # scene reads once via take_pending_root_cage()
        self.pending_petal_barrage = None  # scene reads once via take_pending_petal_barrage()
        self.pending_comet = None          # scene reads once via take_pending_comet()
        self.pending_phase_change = None   # scene reads once via take_pending_phase_change()

        self._idle_time = 0.0
        self._idle_jitter = (0, 0)

        # Reveal state (see REVEAL_DURATION/PUNCH_DURATION above) — starts
        # counting from this instance's first real update() call, which
        # naturally lands on the frame it's first appended to the scene's
        # enemies list (it isn't updated at all before then).
        self._reveal_timer = 0.0

        self._ambient_particles = []
        self._ambient_timer = AMBIENT_EMBER_INTERVAL

    def take_damage(self, amount):
        was_dead = self.is_dead
        super().take_damage(amount)
        if self.is_dead and not was_dead:
            play_sound(self._death_sound, layers=5)
        elif not self.is_dead:
            self.hurt_flash_timer = HURT_FLASH_DURATION

    def on_phase_change(self, phase_index):
        self.action_state = "idle"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.pending_phase_change = phase_index  # scene triggers its P3-entry screen shake off this

        if phase_index == 1:
            # P2: root cages stop; petal barrage + comet drops begin.
            self.petal_barrage_cooldown_timer = PETAL_BARRAGE_COOLDOWN_P2
            self.comet_cooldown_timer = COMET_COOLDOWN_P2
        elif phase_index == 2:
            # P3: everything, faster, bigger.
            self.root_cage_cooldown_timer = ROOT_CAGE_COOLDOWN_P3
            self.petal_barrage_cooldown_timer = PETAL_BARRAGE_COOLDOWN_P3
            self.comet_cooldown_timer = COMET_COOLDOWN_P3
            self._apply_phase3_scale()

    def _apply_phase3_scale(self):
        if self.scaled_up:
            return
        self.scaled_up = True

        def scale_all(frames):
            new_size = (int(WIDTH * PHASE3_SCALE), int(HEIGHT * PHASE3_SCALE))
            return [pygame.transform.scale(f, new_size) for f in frames]

        self.idle_frames = scale_all(self.idle_frames)
        self.cast_frames = scale_all(self.cast_frames)
        self.hurt_frames = scale_all(self.hurt_frames)
        self.death_frames = scale_all(self.death_frames)

        old_center = self.rect.center
        self.rect = pygame.Rect(0, 0, int(WIDTH * PHASE3_SCALE), int(HEIGHT * PHASE3_SCALE))
        self.rect.center = old_center

    def update(self, dt, player=None):
        if self._reveal_timer < REVEAL_DURATION:
            self._reveal_timer += dt

        for particle in self._ambient_particles:
            particle.update(dt)
        self._ambient_particles = [p for p in self._ambient_particles if p.alive]

        if self.hurt_flash_timer > 0:
            self.hurt_flash_timer = max(0.0, self.hurt_flash_timer - dt)

        if self.is_dead:
            self._animate(dt, self.death_frames, DEATH_FRAME_DURATION, loop=False, on_finish=self._mark_death_done)
        elif self.stunned_timer > 0:
            # Lumen Bloom's stun (Enemy.stunned_timer) — the Titan never
            # calls patrol() so the base class's stun check never runs;
            # interrupt whatever cast is in progress here instead. Reuses
            # the hurt frames as a "reeling" visual rather than adding a
            # dedicated stun animation that isn't in the asset list.
            self.stunned_timer -= dt
            self._animate(dt, self.hurt_frames, HURT_FRAME_DURATION, loop=True)
        elif self.action_state == "root_cage":
            self._update_cast(dt, self._trigger_root_cage, self._finish_root_cage)
        elif self.action_state == "petal_barrage":
            self._update_cast(dt, self._trigger_petal_barrage, self._finish_action)
        elif self.action_state == "comet_slam":
            self._update_cast(dt, self._trigger_comet, self._finish_action)
        else:
            self._update_idle(dt, player)

        if self.hurt_flash_timer > 0 and not self.is_dead:
            frame = self.hurt_frames[0]
            self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _update_idle(self, dt, player):
        if player is not None:
            # Flipped from the naive ">=" comparison — the source art
            # faces the opposite way from what that comparison assumed,
            # so this mirrors which side counts as "facing right".
            self.facing_right = player.rect.centerx < self.rect.centerx
        self._animate(dt, self.idle_frames, IDLE_FRAME_DURATION, loop=True)

        # Rooted in place, so idle reads as straining against its own
        # roots rather than standing still — a tiny position wobble,
        # applied only at draw time (never to rect/hitbox).
        self._idle_time += dt
        self._idle_jitter = (
            int(math.sin(self._idle_time * 9.0) * IDLE_SHAKE_AMPLITUDE[0]),
            int(math.sin(self._idle_time * 13.0) * IDLE_SHAKE_AMPLITUDE[1]),
        )

        self._ambient_timer -= dt
        if self._ambient_timer <= 0:
            self._ambient_timer = AMBIENT_EMBER_INTERVAL
            self._spawn_ambient_ember()

        root_cage_available = self.phase in (0, 2)
        barrage_available = self.phase >= 1

        if root_cage_available:
            self.root_cage_cooldown_timer -= dt
        if barrage_available:
            self.petal_barrage_cooldown_timer -= dt
            self.comet_cooldown_timer -= dt

        if root_cage_available and self.root_cage_cooldown_timer <= 0:
            self._start_action("root_cage")
        elif barrage_available and self.petal_barrage_cooldown_timer <= 0:
            self._start_action("petal_barrage")
        elif barrage_available and self.comet_cooldown_timer <= 0:
            self._start_action("comet_slam")

    def _start_action(self, action_state):
        self.action_state = action_state
        self.frame_index = 0
        self.frame_timer = 0.0
        self.action_impact_done = False
        self._idle_jitter = (0, 0)
        play_sound(self._attack_sound, layers=5)

    def _update_cast(self, dt, on_impact, on_finish):
        frames = self.cast_frames
        self.frame_timer += dt
        if self.frame_timer >= CAST_FRAME_DURATION:
            self.frame_timer = 0.0
            if self.frame_index < len(frames) - 1:
                self.frame_index += 1
                if self.frame_index == self.cast_impact_frame and not self.action_impact_done:
                    self.action_impact_done = True
                    on_impact()
            else:
                on_finish()

        frame = frames[min(self.frame_index, len(frames) - 1)]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _finish_action(self):
        self.action_state = "idle"
        self.frame_index = 0

    def _trigger_root_cage(self):
        self.pending_root_cage = {"duration": ROOT_CAGE_DURATION}
        self.root_cage_cooldown_timer = ROOT_CAGE_COOLDOWN_P3 if self.phase >= 2 else ROOT_CAGE_COOLDOWN_P1

    def _finish_root_cage(self):
        self._finish_action()

    def _trigger_petal_barrage(self):
        wide = self.phase >= 2
        self.pending_petal_barrage = {
            "center": self.rect.center,
            "count": PETAL_COUNT_P3 if wide else PETAL_COUNT_P2,
            "speed": PETAL_SPEED_P3 if wide else PETAL_SPEED_P2,
            "damage": PETAL_DAMAGE,
        }
        self.petal_barrage_cooldown_timer = PETAL_BARRAGE_COOLDOWN_P3 if wide else PETAL_BARRAGE_COOLDOWN_P2

    def _trigger_comet(self):
        wide = self.phase >= 2
        self.pending_comet = {
            "fall_speed": COMET_FALL_SPEED_P3 if wide else COMET_FALL_SPEED_P2,
            "damage": COMET_DAMAGE,
        }
        self.comet_cooldown_timer = COMET_COOLDOWN_P3 if wide else COMET_COOLDOWN_P2

    def take_pending_root_cage(self):
        pending = self.pending_root_cage
        self.pending_root_cage = None
        return pending

    def take_pending_petal_barrage(self):
        pending = self.pending_petal_barrage
        self.pending_petal_barrage = None
        return pending

    def take_pending_comet(self):
        pending = self.pending_comet
        self.pending_comet = None
        return pending

    def take_pending_phase_change(self):
        """Scene reads this once to react to a phase transition (P3 entry
        screen shake, a "PHASE n" banner, etc.) — same take-once pattern
        as the pending attack signals above."""
        pending = self.pending_phase_change
        self.pending_phase_change = None
        return pending

    def _animate(self, dt, frames, frame_duration, loop, on_finish=None):
        self.frame_timer += dt
        if self.frame_timer >= frame_duration:
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

    def _spawn_ambient_ember(self):
        """One small mote drifting up off the Titan's silhouette — purely
        cosmetic, self-contained so idle doesn't need the scene's shared
        ParticleSystem to read as alive between attacks."""
        x = self.rect.centerx + random.uniform(-self.rect.width * 0.3, self.rect.width * 0.3)
        y = self.rect.top + random.uniform(0, self.rect.height * 0.6)
        velocity = (random.uniform(-8, 8), random.uniform(-30, -12))
        self._ambient_particles.append(Particle(
            x, y, velocity, color=AMBIENT_EMBER_COLOR, radius=random.randint(1, 3),
            lifetime=random.uniform(1.0, 1.8), gravity=-6,
        ))

    def draw(self, surface, camera_offset=(0, 0)):
        jitter_x, jitter_y = self._idle_jitter if self.action_state == "idle" and not self.is_dead else (0, 0)
        pos = (self.rect.x - camera_offset[0] + jitter_x, self.rect.y - camera_offset[1] + jitter_y)

        reveal_progress = min(1.0, self._reveal_timer / REVEAL_DURATION)
        if reveal_progress < 1.0:
            self._draw_reveal(surface, pos, reveal_progress)
        else:
            surface.blit(self.image, pos)

        for particle in self._ambient_particles:
            particle.draw(surface, camera_offset)

    def _draw_reveal(self, surface, pos, progress):
        """First REVEAL_DURATION seconds on screen: a dark silhouette,
        backlit by an orange glow (echoing the crater it just rose from),
        resolving into full color — with a fast punch-in overshoot
        (oversized, easing to 1.0x) layered on top for extra weight."""
        center = (pos[0] + self.rect.width // 2, pos[1] + self.rect.height // 2)

        glow_alpha = int(160 * (1.0 - progress))
        if glow_alpha > 0:
            glow_radius = int(max(self.rect.width, self.rect.height) * 0.6)
            glow = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*REVEAL_GLOW_COLOR, glow_alpha), (glow_radius, glow_radius), glow_radius)
            surface.blit(glow, (center[0] - glow_radius, center[1] - glow_radius), special_flags=pygame.BLEND_ADD)

        # Full-color frame first, then a black silhouette faded out on top
        # of it — reads as the silhouette "burning away" to reveal color.
        composite = self.image.copy()
        silhouette = self.image.copy()
        silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        silhouette.set_alpha(int(255 * (1.0 - progress)))
        composite.blit(silhouette, (0, 0))

        punch_progress = min(1.0, self._reveal_timer / PUNCH_DURATION)
        scale = PUNCH_SCALE_START + (1.0 - PUNCH_SCALE_START) * punch_progress
        if scale != 1.0:
            width, height = composite.get_size()
            composite = pygame.transform.smoothscale(composite, (max(1, int(width * scale)), max(1, int(height * scale))))

        surface.blit(composite, composite.get_rect(center=center))

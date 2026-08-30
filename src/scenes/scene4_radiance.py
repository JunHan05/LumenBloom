"""
scene4_radiance.py

Scene 4 — The Last Radiance (Member 4). A brief flashback cutscene of
the Murk Comet striking the Lumen Core opens onto a circular,
non-scrolling arena directly above it. Iris fights the three-phase
Aurelian Titan — root cages, then a homing petal barrage and comet
drops, then everything combined and scaled up — while the arena stays
corrupted for the whole fight. On defeat, gameplay freezes for a
purification cutscene (golden restoration burst -> white fade), the
background hard-switches to its restored art, and Iris collects the
final Lumen Shard (PROJECT_BRIEF.md section 5).
"""

import math

import pygame

from config.settings import (
    TILE_SIZE, SCREEN_W, SCREEN_H, COLORS, BACKGROUNDS_IMG_DIR, EFFECTS_IMG_DIR, SFX_DIR, TILES_IMG_DIR,
)
from src.core.asset_loader import load_image, load_animation_frames, load_sound, play_sound, stop_music
from src.scenes.base_scene import BaseScene
from src.world.platforms import Platform
from src.world.hazards import BurningCrater, MurkMeter
from src.world.collectibles import GlowOrb, LumenToken, LumenShard
from src.entities.projectile import Projectile, HomingPetal
from src.entities.bosses.aurelian_titan import AurelianTitan
from src.effects.transitions import BackgroundCrossfade
from src.effects.shockwave import Shockwave

LEVEL_COLS = 20                         # 20 * 64 = 1280 = SCREEN_W: a non-scrolling arena
LEVEL_ROWS = 11                         # 11 * 64 = 704 < SCREEN_H: no vertical scroll either
LEVEL_WIDTH = LEVEL_COLS * TILE_SIZE

# The land is baked into the corrupted/restored background art itself
FLOOR_Y = int(SCREEN_H * 3 / 4)
GROUND_COLLISION_HEIGHT = 48

# Iris's max single-jump height is roughly JUMP_STRENGTH^2 / (2*GRAVITY) = 16^2 / (2*0.9) =~ 142px
# Keep each ledge tier's vertical gap comfortably under that so every tier is
# reachable with a single well-timed jump.
PLATFORM_TIER_GAP = 120
LOW_TIER_Y = FLOOR_Y - PLATFORM_TIER_GAP
MID_TIER_Y = LOW_TIER_Y - PLATFORM_TIER_GAP
HIGH_TIER_Y = MID_TIER_Y - PLATFORM_TIER_GAP

PLATFORM_SIZE = (128, 32)
PLATFORM_SPOTS = [
    (2 * TILE_SIZE, LOW_TIER_Y), (16 * TILE_SIZE, LOW_TIER_Y),     # low pair
    (5 * TILE_SIZE, MID_TIER_Y), (13 * TILE_SIZE, MID_TIER_Y),     # mid pair
    (8 * TILE_SIZE, HIGH_TIER_Y), (11 * TILE_SIZE, HIGH_TIER_Y),   # high pair
]  # (x, y) in pixels — "six fixed crystal ledges at varying heights"

CUTSCENE_DURATION = 3.0
CUTSCENE_IMPACT_TIME = 1.8  # when the comet "hits" mid-cutscene and explodes
CUTSCENE_COMET_SOUND_LEAD = 1.8  # comet audio starts this long before the visual impact — equal to
# CUTSCENE_IMPACT_TIME, so it fires right at the start of the cutscene (t=0) instead of partway in

CAGE_MASH_TARGET = 6  # direction key presses needed to break out early

COMET_SPAWN_Y = -80
COMET_FRAME_COUNT = 4
CAGE_FRAME_COUNT = 11
CAGE_VISUAL_SIZE = (160, 160)  # "half times longer" — 1.5x the original (120, 170) so it fully wraps Iris
CAGE_VERTICAL_OFFSET = 70      # "a bit lower" — was 30; biases the visual down so it covers her, not just her head
COMET_ROTATION_DEGREES = 45    # "rotates 45 degrees to left" — pygame.transform.rotate is counter-clockwise

BLIGHT_HIT_SPIKE = 8.0        # Blight Meter jump when a boss attack lands (doc: "spikes when hit")
BLIGHT_VIGNETTE_START = 0.5   # fraction of the meter at which the danger vignette starts fading in

DEFEAT_BANNER_DURATION = 3.0
PHASE3_SHAKE_DURATION = 0.9
PHASE3_SHAKE_MAGNITUDE = 14

# Titan reveal, the moment the cutscene ends and the boss becomes visible —
# a bigger shake than the comet impact gets, since this is the fight's real
# "it's alive" beat (see AurelianTitan's own silhouette/punch-in reveal).
TITAN_REVEAL_SHAKE_DURATION = 0.6
TITAN_REVEAL_SHAKE_MAGNITUDE = 18

# Pulsing arena-edge glow while the boss is mid-cast — a visual telegraph
# that pairs with its attack roar, readable during the ~0.9s windup before
# the attack actually lands (AurelianTitan.CAST_IMPACT_FRACTION).
TELEGRAPH_BORDER = 40
TELEGRAPH_PULSE_SPEED = 10.0

# Persistent scorch decals, baked once into a dedicated layer so ground
# damage visibly accumulates across the fight instead of resetting.
COMET_SCORCH_RADIUS = TILE_SIZE * 2
CUTSCENE_SCORCH_RADIUS = 90
CAGE_SCORCH_RADIUS = TILE_SIZE

# The Titan's opening line, shown the instant the cutscene ends and the
# fight actually starts — a taunt over the final Lumen Shard it now
# guards, playing its "wither"/corruption theme against Iris's own
# "bloom" abilities (Lumen Bloom, Glow Slash).
TITAN_INTRO_LINE = "This shard is mine now, little bloom. Wither with the rest of Aurelia!!!"
TITAN_INTRO_BANNER_DURATION = 3.5

# Phase-entry announcements (P2 at phase index 1, P3 at index 2), shown in
# a red dialogue box in place of the old plain-text "PHASE n" banner.
PHASE_ANNOUNCE_LINES = {
    1: "Roots were only the beginning. Feel the sky turn against you!",
    2: "Enough!!! Wither now, all of you!!!!!",
}
PHASE_ANNOUNCE_DURATION = 3.0

# Purification defeat sequence: FREEZE (purify anim plays) -> EXPAND (golden
# restoration burst grows from the boss core) -> FADE (white 255 -> 0) ->
# back to normal play, with the Lumen Shard now spawned to collect.
EXPAND_RADIUS_PER_SECOND = 30 * 60  # "+30px/frame" at a 60fps baseline
FADE_DURATION = 1.5

IRIS_SCENE_SCALE = 0.6  # "make Iris half smaller" — scoped to this scene only, see _shrink_iris()


def _build_grid():
    # No '#' floor row — the ground is painted into the background art
    # itself; collision for it comes from _GroundCollision instead.
    grid = [['.' for _ in range(LEVEL_COLS)] for _ in range(LEVEL_ROWS)]
    return [''.join(row) for row in grid]


class _GroundCollision:
    """Collision-only floor strip — no tile image to draw, since the land
    is already part of the corrupted/restored background art. Matches the
    Platform duck-type (rect / update / draw) so it drops straight into
    BaseScene's platform list and gets included in solid_rects for free."""

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def update(self, dt, player_rect):
        pass

    def draw(self, surface, camera_offset=(0, 0)):
        pass


class Scene4Radiance(BaseScene):
    def __init__(self, player):
        # The background is a corrupted/restored crossfade, not scrolling
        # parallax layers — _draw_background() is overridden below, so
        # background_layers is passed empty and never used by the base
        # class's tiling logic. tileset_filename is None: _build_grid()
        # has no '#'/'X' tiles (the land is painted into the background
        # art), and TileMap skips loading a tileset image entirely when
        # the grid has none — see tilemap.py's has_tiles check.
        super().__init__(player, [], _build_grid(), None,
                          LEVEL_WIDTH, level_height=SCREEN_H)

        self.background_crossfade = BackgroundCrossfade(
            corrupted_image=load_image(BACKGROUNDS_IMG_DIR / "scene4" / "corrupted.png", size=(SCREEN_W, SCREEN_H)),
            restored_image=load_image(BACKGROUNDS_IMG_DIR / "scene4" / "restored.png", size=(SCREEN_W, SCREEN_H)),
        )
        # Scorch/crater marks accumulate here permanently (never cleared
        # frame-to-frame) — blitted once per hit, drawn under everything
        # else in _draw_background(). Reset to blank the moment the land
        # is purified, in _end_defeat_sequence().
        self.decal_layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        self.platforms = [
            Platform(x=x, y=y, width=PLATFORM_SIZE[0], height=PLATFORM_SIZE[1],
                     image_filename="corrupted_ledge.png")
            for x, y in PLATFORM_SPOTS
        ]
        self.platforms.append(_GroundCollision(0, FLOOR_Y, LEVEL_WIDTH, GROUND_COLLISION_HEIGHT))

        # The boss is kept out of self.enemies until the opening cutscene
        # finishes, so it can't start attacking (or even be visible)
        # while Iris is frozen watching the flashback.
        self.boss = AurelianTitan(x=10 * TILE_SIZE, y=FLOOR_Y)
        self.enemies = []

        self.shard = LumenShard(x=10 * TILE_SIZE, y=FLOOR_Y - 40)
        self.shard_spawned = False  # appears only once the purification sequence finishes
        self.collectibles = [
            GlowOrb(x=PLATFORM_SPOTS[0][0] + 64, y=PLATFORM_SPOTS[0][1] - 30),
            GlowOrb(x=PLATFORM_SPOTS[1][0] + 64, y=PLATFORM_SPOTS[1][1] - 30),
            GlowOrb(x=PLATFORM_SPOTS[2][0] + 64, y=PLATFORM_SPOTS[2][1] - 30),
            GlowOrb(x=PLATFORM_SPOTS[3][0] + 64, y=PLATFORM_SPOTS[3][1] - 30),
            LumenToken(x=PLATFORM_SPOTS[4][0] + 64, y=PLATFORM_SPOTS[4][1] - 30),
            LumenToken(x=PLATFORM_SPOTS[5][0] + 64, y=PLATFORM_SPOTS[5][1] - 30),
        ]

        self.petal_image = load_image(EFFECTS_IMG_DIR / "petal.png", size=(30, 30))
        self.comet_frames = [
            pygame.transform.rotate(frame, COMET_ROTATION_DEGREES)
            for frame in load_animation_frames(EFFECTS_IMG_DIR, "comet", COMET_FRAME_COUNT, size=(96, 96))
        ]
        self.cage_frames = load_animation_frames(EFFECTS_IMG_DIR, "root_cage", CAGE_FRAME_COUNT, size=CAGE_VISUAL_SIZE)
        self.danger_vignette_image = load_image(EFFECTS_IMG_DIR / "danger_vignette.png", size=(SCREEN_W, SCREEN_H))
        self.comets = []  # falling Projectile instances, managed separately (see _update_comets)

        self._comet_sound = load_sound(SFX_DIR / "comet.wav")
        self._crater_sound = load_sound(SFX_DIR / "burning_crater.wav")
        self._cage_sound = load_sound(SFX_DIR / "root_cage.wav")

        # Root cage state (Phase 1 / 3 attack) — freezes Iris in place
        self._cage_timer = 0.0
        self._cage_total = 0.0
        self._cage_mash_count = 0
        self._cage_anchor = None

        # Blight Meter — the doc's Murk Meter, reused here: fills with
        # corruption pressure, spikes when a boss attack lands, and drains
        # Iris passively (with a dark vignette) once full. hud.py already
        # knows how to draw it; the scene just has to own+update one.
        self.murk_meter = MurkMeter()
        self._last_player_hp = self.player.hp

        # Boss dialogue box — a VN-style speaker box (name tag + panel +
        # wrapped text). `speaker` may be left "" for a nameless system
        # message (phase-change announcements, defeat text).
        self._dialogue_speaker = ""
        self._dialogue_text = ""
        self._dialogue_timer = 0.0
        self._dialogue_duration = 0.0
        self._dialogue_color = COLORS["murk_purple"]
        self._dialogue_name_font = pygame.font.Font(None, 28)
        self._dialogue_text_font = pygame.font.Font(None, 30)

        # Purification defeat sequence — see the state machine in
        # _update_defeat_sequence()/_begin_defeat_sequence() below.
        self._defeat_started = False
        self._defeat_stage = None  # None -> "freeze" -> "expand" -> "fade" -> None (done)
        self._defeat_anchor = None
        self._expand_radius = 0.0
        self._fade_timer = 0.0
        # Background stays fully corrupted for the whole fight and only flips
        # to fully restored once, right after the white fade-out finishes in
        # _end_defeat_sequence() — see _draw_background().
        self._background_restored = False

        self.cutscene_active = True
        self.cutscene_timer = CUTSCENE_DURATION
        self._cutscene_exploded = False
        self._cutscene_comet_sound_played = False
        self._cutscene_comet_y = None  # set while the comet is still falling; None once it's landed
        self.shockwaves = []

        # Running clock driving the arena-edge telegraph pulse (see
        # _draw_attack_telegraph) — only advances during real gameplay,
        # not the cutscene or defeat sequence.
        self._pulse_time = 0.0

        # x=1 tile keeps her clear of the low-left crystal ledge at col 2
        # (x 128-256) — with the floor this close beneath it, spawning
        # under the ledge's edge would clip her body through it.
        self.player.rect.midbottom = (TILE_SIZE, FLOOR_Y)
        self.respawn_point = self.player.rect.midbottom
        self._shrink_iris()

    def _shrink_iris(self):
        """Scale Iris down to IRIS_SCENE_SCALE for this scene only — the
        Titan and its arena are built at a much larger scale than Scenes
        1-3, so a full-size Iris reads oversized here. Rescales her cached
        animation frames and her standing/crouch hitbox dimensions
        (Player.update()'s crouch logic reads those, not a hardcoded 96/48,
        specifically so a resize like this survives crouching without
        snapping back). Guarded so re-entering the scene (e.g. a Game Over
        restart, which reuses the same Player instance) doesn't shrink her
        a second time."""
        if getattr(self.player, "_scene4_scale_applied", False):
            return
        self.player._scene4_scale_applied = True

        scale = IRIS_SCENE_SCALE
        for state, frames in self.player.animations.items():
            self.player.animations[state] = [
                pygame.transform.smoothscale(
                    frame, (max(1, int(frame.get_width() * scale)), max(1, int(frame.get_height() * scale)))
                )
                for frame in frames
            ]

        self.player.standing_width = max(1, int(self.player.standing_width * scale))
        self.player.standing_height = max(1, int(self.player.standing_height * scale))
        self.player.crouch_height = max(1, int(self.player.crouch_height * scale))

        old_bottom = self.player.rect.bottom
        old_centerx = self.player.rect.centerx
        new_height = self.player.crouch_height if self.player.crouching else self.player.standing_height
        self.player.rect = pygame.Rect(0, 0, self.player.standing_width, new_height)
        self.player.rect.bottom = old_bottom
        self.player.rect.centerx = old_centerx

        state_frames = self.player.animations[self.player.state]
        self.player.frame_index = min(self.player.frame_index, len(state_frames) - 1)
        self.player.image = state_frames[self.player.frame_index]

    # --- Input ---------------------------------------------------------

    def handle_scene_event(self, event):
        if self._cage_timer > 0 and event.type == pygame.KEYDOWN and event.key in (
            pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s,
        ):
            self._cage_mash_count += 1

    def on_glow_slash_hit(self, hitbox, damage):
        """Petal barrage is "deflectable with Glow Slash" — knock any
        HomingPetal caught in the swing out of the air instead of letting
        it reach Iris."""
        for projectile in self.projectiles:
            if isinstance(projectile, HomingPetal) and not projectile.spent and hitbox.colliderect(projectile.rect):
                projectile.deflect()

    # --- Update ----------------------------------------------------------

    def update_scene(self, dt):
        if self.cutscene_active:
            self._update_cutscene(dt)
            return

        self._dialogue_timer = max(0.0, self._dialogue_timer - dt)
        self._pulse_time += dt

        if self._defeat_stage is not None:
            self._update_defeat_sequence(dt)
            return

        self._update_caged(dt)
        self._update_boss_attacks(dt)
        self._update_comets(dt)
        self._update_phase_change()
        if not self._defeat_started:
            # Boss is dead and the meter was already wiped in
            # _begin_defeat_sequence() — leave it at 0 rather than letting
            # it start passively refilling while Iris collects the final
            # shard with no more boss attacks to justify it.
            self._update_blight_meter(dt)
        self.hazards = [h for h in self.hazards if not getattr(h, "expired", False)]

        if self.boss.is_dead and not self._defeat_started:
            self._defeat_started = True
            self._begin_defeat_sequence()

    def _update_cutscene(self, dt):
        self.cutscene_timer -= dt
        elapsed = CUTSCENE_DURATION - self.cutscene_timer

        if not self._cutscene_comet_sound_played and elapsed >= CUTSCENE_IMPACT_TIME - CUTSCENE_COMET_SOUND_LEAD:
            self._cutscene_comet_sound_played = True
            play_sound(self._comet_sound)

        if elapsed < CUTSCENE_IMPACT_TIME:
            progress = max(0.0, elapsed / CUTSCENE_IMPACT_TIME)
            self._cutscene_comet_y = int(progress * (SCREEN_H // 2))
            # Embers trail just above the falling comet's tail.
            self.particles.emit_embers((SCREEN_W // 2, self._cutscene_comet_y + 16), count=2)
        else:
            self._cutscene_comet_y = None

        if not self._cutscene_exploded and elapsed >= CUTSCENE_IMPACT_TIME:
            self._cutscene_exploded = True
            self.particles.emit_explosion((SCREEN_W // 2, SCREEN_H // 2))
            self.screen_shake.trigger(duration=0.5, magnitude=14)
            self.shockwaves.append(Shockwave(
                (SCREEN_W // 2, SCREEN_H // 2), max_radius=260, speed=520,
                color=COLORS["warn_orange"], width=6,
            ))
            self._add_scorch_decal((SCREEN_W // 2, SCREEN_H // 2), CUTSCENE_SCORCH_RADIUS)
            play_sound(self._crater_sound)

        for shockwave in self.shockwaves:
            shockwave.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.alive]

        if self.cutscene_timer <= 0:
            self.cutscene_active = False
            self.enemies.append(self.boss)
            self.screen_shake.trigger(duration=TITAN_REVEAL_SHAKE_DURATION, magnitude=TITAN_REVEAL_SHAKE_MAGNITUDE)
            self._set_dialogue(self.boss.NAME, TITAN_INTRO_LINE, TITAN_INTRO_BANNER_DURATION)

    def _update_caged(self, dt):
        root_cage = self.boss.take_pending_root_cage()
        if root_cage is not None:
            self._cage_timer = root_cage["duration"]
            self._cage_total = root_cage["duration"]
            self._cage_mash_count = 0
            self._cage_anchor = self.player.rect.center
            self._add_scorch_decal(self._cage_anchor, CAGE_SCORCH_RADIUS)
            play_sound(self._cage_sound, layers=5)

        if self._cage_timer > 0:
            self._cage_timer -= dt
            self.player.rect.center = self._cage_anchor
            self.player.velocity_x = 0
            self.player.velocity_y = 0
            if self._cage_mash_count >= CAGE_MASH_TARGET:
                self._cage_timer = 0

    def _update_boss_attacks(self, dt):
        petal_barrage = self.boss.take_pending_petal_barrage()
        if petal_barrage is not None:
            self._fire_petal_barrage(petal_barrage)

        comet = self.boss.take_pending_comet()
        if comet is not None:
            self._spawn_comet(comet)

    def _update_phase_change(self):
        phase_index = self.boss.take_pending_phase_change()
        if phase_index is None:
            return
        announce_line = PHASE_ANNOUNCE_LINES.get(phase_index)
        if announce_line is not None:
            self._set_dialogue(self.boss.NAME, announce_line, PHASE_ANNOUNCE_DURATION, color=COLORS["hp_red"])
        if phase_index == 2:
            # P3 entry: "everything combined at faster cadence with screen
            # shake on entry" (doc).
            self.screen_shake.trigger(duration=PHASE3_SHAKE_DURATION, magnitude=PHASE3_SHAKE_MAGNITUDE)

    def _update_blight_meter(self, dt):
        if self.player.hp < self._last_player_hp - 0.01:
            self.murk_meter.value = min(MurkMeter.MAX_VALUE, self.murk_meter.value + BLIGHT_HIT_SPIKE)
        self.murk_meter.update(dt, self.player)
        self._last_player_hp = self.player.hp

    def _fire_petal_barrage(self, petal_barrage):
        center = petal_barrage["center"]
        count = petal_barrage["count"]
        speed = petal_barrage["speed"]
        damage = petal_barrage["damage"]

        dx = self.player.rect.centerx - center[0]
        dy = self.player.rect.centery - center[1]
        base_angle = math.atan2(dy, dx)

        # Fan the launch headings out across a wide arc rather than firing
        # every petal in an identical straight line — each one curves the
        # rest of the way toward Iris on its own (HomingPetal.update()),
        # so this spread is really just about the barrage reading as a
        # burst instead of a single stacked line.
        spread = math.radians(70)
        for i in range(count):
            angle = base_angle + (i / max(1, count - 1) - 0.5) * spread
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            petal = HomingPetal(center[0], center[1], velocity, self.petal_image, damage,
                                 target=self.player, max_range=1600)
            self.projectiles.append(petal)

    def _spawn_comet(self, comet_data):
        target_x = max(TILE_SIZE, min(LEVEL_WIDTH - TILE_SIZE, self.player.rect.centerx))
        # Comet falls only until it reaches Iris's current height 
        # (her feet at cast time), not all the way to the arena floor.
        fall_distance = max(1, self.player.rect.bottom - COMET_SPAWN_Y)
        comet = Projectile(target_x, COMET_SPAWN_Y, (0, comet_data["fall_speed"]),
                            self.comet_frames[0], comet_data["damage"], max_range=fall_distance,
                            frames=self.comet_frames)
        self.comets.append(comet)
        play_sound(self._comet_sound)

    def _update_comets(self, dt):
        for comet in self.comets:
            was_spent = comet.spent
            comet.update(dt)
            comet.check_hit_player(self.player)
            if comet.spent and not was_spent:
                self._on_comet_impact(comet)
        self.comets = [c for c in self.comets if not c.spent]

    def _on_comet_impact(self, comet):
        self.screen_shake.trigger(duration=0.4, magnitude=12)
        self.particles.emit_explosion(comet.rect.center)
        self._add_scorch_decal(comet.rect.center, COMET_SCORCH_RADIUS)
        crater_width, crater_height = TILE_SIZE * 4, TILE_SIZE * 2
        self.hazards.append(BurningCrater(
            x=comet.rect.centerx - crater_width // 2, y=comet.rect.centery - crater_height // 2,
            width=crater_width, height=crater_height,
        ))
        play_sound(self._crater_sound)

    # --- Purification defeat sequence ---------------------------------------

    def _set_dialogue(self, speaker, text, duration, color=None):
        self._dialogue_speaker = speaker
        self._dialogue_text = text
        self._dialogue_timer = duration
        self._dialogue_duration = duration
        self._dialogue_color = color if color is not None else COLORS["murk_purple"]

    def _begin_defeat_sequence(self):
        """Boss HP hit 0 this frame. Freeze gameplay while the purify
        (death) animation plays — everything else about defeat happens
        once that animation finishes, in _update_defeat_sequence()."""
        self._defeat_stage = "freeze"
        self._defeat_anchor = self.player.rect.center
        self.projectiles = []
        self.comets = []
        self.hazards = []
        self._cage_timer = 0.0
        # The corruption is lifting — the Blight Meter (and its dark
        # vignette/passive damage) has no reason to persist once the
        # source of it is dead, so wipe it rather than leaving Iris stuck
        # with a full meter through the purification sequence and shard
        # pickup that follow.
        self.murk_meter.value = 0.0
        self.screen_shake.trigger(duration=0.3, magnitude=5)
        self._set_dialogue("", "THE CORRUPTION LIFTS...", DEFEAT_BANNER_DURATION, color=COLORS["hp_green"])
        # Cut the boss theme immediately rather than letting it run under
        # titan_death.wav (AurelianTitan.take_damage()) — the scene's music
        # would otherwise keep playing all the way through the purification
        # sequence and drown it out. Victory music picks up later, once the
        # scene actually finishes (scene_manager.py's _on_scene_complete()).
        stop_music()

    def _update_defeat_sequence(self, dt):
        self._freeze_player()

        if self._defeat_stage == "freeze":
            if self.boss.death_anim_done:
                self._defeat_stage = "expand"
                self._expand_radius = 0.0
                self.particles.emit_petals(self.boss.rect.center)  # purification burst

        elif self._defeat_stage == "expand":
            self._expand_radius += EXPAND_RADIUS_PER_SECOND * dt
            if self._expand_radius >= self._distance_to_farthest_corner(self.boss.rect.center):
                # Circle now covers the screen -> the white fade begins.
                self._defeat_stage = "fade"
                self._fade_timer = 0.0

        elif self._defeat_stage == "fade":
            self._fade_timer += dt
            if self._fade_timer >= FADE_DURATION:
                self._end_defeat_sequence()

    def _freeze_player(self):
        self.player.rect.center = self._defeat_anchor
        self.player.velocity_x = 0
        self.player.velocity_y = 0

    def _end_defeat_sequence(self):
        self._defeat_stage = None
        # White fade has fully covered and is about to lift -> swap to the
        # restored background now, so the reveal lands right as the fade
        # clears rather than having been gradually visible mid-fight.
        self._background_restored = True
        # Every scorch mark burns away as the land is purified — a fresh,
        # blank layer rather than clear()'ing so decal_layer itself stays
        # a plain SRCALPHA surface (same construction as __init__'s).
        self.decal_layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._restore_ledges()
        self._on_boss_defeated()
        self._set_dialogue("", "Claim the final Lumen Shard.", DEFEAT_BANNER_DURATION, color=COLORS["hp_green"])

    def _restore_ledges(self):
        """Swap every crystal ledge's corrupted art for its restored
        counterpart, same beat as the background switching over. Platform
        only exposes the image it loaded at construction time, so this
        reloads and overwrites it directly rather than needing a setter
        on the shared class — _GroundCollision has no `image` attribute,
        hence the isinstance guard."""
        for platform in self.platforms:
            if isinstance(platform, Platform):
                platform.image = load_image(TILES_IMG_DIR / "restored_ledge.png",
                                             size=(platform.rect.width, platform.rect.height))

    def _on_boss_defeated(self):
        self.shard_spawned = True
        self.collectibles.append(self.shard)

    @staticmethod
    def _distance_to_farthest_corner(center):
        cx, cy = center
        corners = ((0, 0), (SCREEN_W, 0), (0, SCREEN_H), (SCREEN_W, SCREEN_H))
        return max(math.hypot(cx - x, cy - y) for x, y in corners)

    # --- Draw --------------------------------------------------------------

    def _draw_background(self, surface, offset):
        """Overrides BaseScene's scrolling-layer tiler — Scene 4's
        background is corrupted/restored art, not parallax layers (see
        PROJECT_BRIEF.md section 5). A hard switch rather than a gradual
        HP-tied crossfade: stays fully corrupted for the whole fight and
        flips to fully restored only once, set by _end_defeat_sequence()."""
        restored_fraction = 1.0 if self._background_restored else 0.0
        self.background_crossfade.draw(surface, restored_fraction)
        surface.blit(self.decal_layer, (0, 0))

    def _add_scorch_decal(self, center, radius):
        """Burn a flattened soot mark into the persistent decal layer —
        an ellipse (not a circle) so it reads as lying flat on the
        ground rather than floating. Never cleared, so marks accumulate
        across the fight (see decal_layer's comment in __init__)."""
        diameter = radius * 2
        band_height = max(2, int(diameter * 0.45))
        mark = pygame.Surface((diameter, band_height), pygame.SRCALPHA)
        pygame.draw.ellipse(mark, (15, 12, 10, 130), (0, 0, diameter, band_height))
        pygame.draw.ellipse(mark, (70, 35, 15, 90), (0, 0, diameter, band_height),
                             width=max(2, int(radius * 0.12)))
        self.decal_layer.blit(mark, (center[0] - radius, center[1] - band_height // 2))

    def draw_scene(self, surface, camera_offset):
        if self.cutscene_active:
            self._draw_cutscene(surface)
            return

        for comet in self.comets:
            comet.draw(surface, camera_offset)

        self._draw_root_cage(surface, camera_offset)

        if not self.boss.death_anim_done:
            self.boss.draw_health_bar(surface)

        if self._defeat_stage in ("expand", "fade"):
            # BaseScene's enemy loop drops the boss the instant its death
            # animation finishes (death_anim_done), but it still needs to
            # be visible — in its final purified pose — while the
            # restoration burst and white fade play out.
            self.boss.draw(surface, camera_offset)
            self._draw_defeat_overlay(surface)
        elif self._defeat_stage is None:
            self._draw_blight_vignette(surface)
            self._draw_attack_telegraph(surface)

        self._draw_dialogue_box(surface)

    def _draw_attack_telegraph(self, surface):
        """Pulsing red glow along the arena edges while the Titan is
        mid-cast (from _start_action's roar until the attack's on_impact
        fires) — a readable visual tell paired with _attack_sound, over
        the ~0.9s windup before any attack actually lands."""
        telegraphing = (self.boss.action_state != "idle"
                         and not self.boss.is_dead
                         and not self.boss.action_impact_done)
        if not telegraphing:
            return
        pulse = (math.sin(self._pulse_time * TELEGRAPH_PULSE_SPEED) + 1) / 2  # 0..1
        alpha = int(60 + 90 * pulse)
        border = TELEGRAPH_BORDER
        color = (*COLORS["hp_red"], alpha)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        pygame.draw.rect(overlay, color, (0, 0, SCREEN_W, border))
        pygame.draw.rect(overlay, color, (0, SCREEN_H - border, SCREEN_W, border))
        pygame.draw.rect(overlay, color, (0, 0, border, SCREEN_H))
        pygame.draw.rect(overlay, color, (SCREEN_W - border, 0, border, SCREEN_H))
        surface.blit(overlay, (0, 0))

    def _draw_root_cage(self, surface, camera_offset):
        if self._cage_timer <= 0 or self._cage_total <= 0 or self._cage_anchor is None:
            return
        progress = 1.0 - (self._cage_timer / self._cage_total)
        frame_index = min(len(self.cage_frames) - 1, int(progress * len(self.cage_frames)))
        frame = self.cage_frames[frame_index]
        anchor = (self._cage_anchor[0] - camera_offset[0], self._cage_anchor[1] - camera_offset[1] + CAGE_VERTICAL_OFFSET)
        surface.blit(frame, frame.get_rect(midbottom=anchor))

    def _draw_blight_vignette(self, surface):
        fraction = self.murk_meter.fraction()
        if fraction <= BLIGHT_VIGNETTE_START:
            return
        progress = (fraction - BLIGHT_VIGNETTE_START) / (1 - BLIGHT_VIGNETTE_START)
        overlay = self.danger_vignette_image.copy()
        overlay.set_alpha(int(255 * progress))
        surface.blit(overlay, (0, 0))

    def _draw_defeat_overlay(self, surface):
        if self._defeat_stage == "expand":
            self._draw_restoration_burst(surface)
        elif self._defeat_stage == "fade":
            self._draw_restoration_burst(surface)
            progress = min(1.0, self._fade_timer / FADE_DURATION)
            alpha = max(0, 255 - int(255 * progress))
            if alpha > 0:
                white = pygame.Surface((SCREEN_W, SCREEN_H))
                white.fill(COLORS["white"])
                white.set_alpha(alpha)
                surface.blit(white, (0, 0))

    def _draw_restoration_burst(self, surface):
        """Golden expanding circle from the boss core. No restoration_burst
        art exists yet, so this is a procedural radial gradient built from
        concentric alpha circles — swap for a sprite by replacing this
        method's body once that asset exists."""
        radius = self._expand_radius
        if radius <= 2:
            return
        center = (self.boss.rect.centerx, self.boss.rect.centery)
        diameter = int(radius * 2)
        layer = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        steps = 6
        for i in range(steps, 0, -1):
            fraction = i / steps
            alpha = int(70 * fraction)
            pygame.draw.circle(layer, (*COLORS["glow_gold"], alpha), (diameter // 2, diameter // 2),
                                int(radius * fraction))
        surface.blit(layer, layer.get_rect(center=center), special_flags=pygame.BLEND_ADD)

    def _draw_dialogue_box(self, surface):
        """A VN-style speaker box (name tag + panel + wrapped text) for
        boss dialogue and system messages. Fades in/out over its first
        and last 0.3s on screen."""
        if self._dialogue_timer <= 0:
            return

        fade_duration = 0.3
        elapsed = self._dialogue_duration - self._dialogue_timer
        alpha_progress = max(0.0, min(1.0, elapsed / fade_duration, self._dialogue_timer / fade_duration))
        self._render_dialogue_panel(surface, self._dialogue_speaker, self._dialogue_text,
                                     self._dialogue_color, alpha_progress)

    def _render_dialogue_panel(self, surface, speaker, text, color, alpha, box_y=None):
        """Shared box renderer behind _draw_dialogue_box (timed speaker
        lines) and _draw_cutscene (an always-on narration line during the
        opening flashback) — same look, different callers. `speaker` may
        be "" to render a nameless narration box with no name tag row."""
        max_text_width = SCREEN_W - 240
        lines = self._wrap_dialogue_text(text, self._dialogue_text_font, max_text_width)
        line_surfaces = [self._dialogue_text_font.render(line, True, COLORS["white"]) for line in lines]
        name_surface = self._dialogue_name_font.render(speaker.upper(), True, color) if speaker else None

        padding = 20
        line_spacing = 4
        name_gap = 10
        widths = [s.get_width() for s in line_surfaces]
        if name_surface is not None:
            widths.append(name_surface.get_width())
        box_width = max(widths) + padding * 2
        box_height = (sum(s.get_height() for s in line_surfaces)
                      + line_spacing * (len(lines) - 1) + padding * 2)
        if name_surface is not None:
            box_height += name_surface.get_height() + name_gap

        panel = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        panel.fill((*COLORS["ui_bg"], int(220 * alpha)))
        pygame.draw.rect(panel, (*color, int(255 * alpha)), panel.get_rect(), width=3, border_radius=8)

        y = padding
        if name_surface is not None:
            name_surface.set_alpha(int(255 * alpha))
            panel.blit(name_surface, (padding, y))
            y += name_surface.get_height() + name_gap
        for line_surface in line_surfaces:
            line_surface.set_alpha(int(255 * alpha))
            panel.blit(line_surface, (padding, y))
            y += line_surface.get_height() + line_spacing

        box_x = (SCREEN_W - box_width) // 2
        if box_y is None:
            box_y = SCREEN_H - box_height - 50
        surface.blit(panel, (box_x, box_y))

    @staticmethod
    def _wrap_dialogue_text(text, font, max_width):
        """Greedy word-wrap, same approach as IntroScene._wrap_text."""
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_cutscene(self, surface):
        surface.fill(COLORS["black"])
        elapsed = CUTSCENE_DURATION - self.cutscene_timer
        if self._cutscene_comet_y is not None:
            frame = self.comet_frames[int(elapsed * 10) % len(self.comet_frames)]
            # Centered on the frame's actual (post-45-degree-rotation)
            # width — the old hardcoded -24 assumed the pre-rotation 96px
            # width, leaving the comet ~43px right of true center.
            surface.blit(frame, (SCREEN_W // 2 - frame.get_width() // 2, self._cutscene_comet_y))
        self.particles.draw(surface)
        for shockwave in self.shockwaves:
            shockwave.draw(surface)

        self._render_dialogue_panel(surface, "", "The Murk Comet strikes the Lumen Core...",
                                     COLORS["warn_orange"], alpha=1.0)

    def on_collect(self, collectible):
        if collectible is self.shard:
            self.finished = True

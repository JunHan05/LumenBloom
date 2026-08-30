"""
scene1_grotto.py

Scene 1 — The Glowcap Grotto (Member 1). Underground cave lit by
glowing fungi. Iris starts on an entry ledge boxed in by cave walls,
drops down onto a sink-tier floor patrolled by a Saw Trap, drops again
into a sunken pit guarded by a Murk Crawler squad and an Arrow Trap,
rides a Mushroom Lift back up, crosses an acid-pool hazard, climbs a
hand-placed chain of ledges (hazarded by 2 falling speleothems), and —
beyond that — reaches the Jinn Monster's arena (sealed gate, Lumen
Shard 1) per PROJECT_BRIEF.md section 5.

Past Jinn Monster there's now a second act: a breakable door (3 Glow
Slash/Pollen Burst hits) leads to the Bug Boss's arena, a 20-tile
stretch added beyond the original level end. Lumen Shard 1 now sits
past the Bug Boss instead of past Jinn Monster.

Layout under active hand-editing: rows/columns get nudged directly in
the constants below rather than rebuilt from a reference image. See
the LEDGES note further down for the current known gap.
"""

import pygame

from config.settings import TILE_SIZE, SCREEN_W, SCREEN_H, BACKGROUNDS_IMG_DIR, SFX_DIR
from src.core.asset_loader import load_image, load_sound, play_sound
from src.scenes.base_scene import BaseScene
from src.world.platforms import MushroomLift, Platform
from src.world.hazards import AcidPool, FallingSpeleothem, SawTrap, ArrowTrap, GroundSpikeWave
from src.world.collectibles import GlowOrb, LumenShard, CheckpointGate
from src.effects.shockwave import Shockwave
from src.effects.cave_lighting import CaveLighting
from src.entities.enemies.murk_crawler import MurkCrawler
from src.entities.enemies.jinn_monster import JinnMonster
from src.entities.bosses.bug_boss import BugBoss

LEVEL_COLS = 68  # 48 original + 20 for the Bug Boss's arena beyond the door
LEVEL_ROWS = 38
LEVEL_WIDTH = LEVEL_COLS * TILE_SIZE
LEVEL_HEIGHT = LEVEL_ROWS * TILE_SIZE

# --- Entry ledge: Iris starts here, boxed in by cave-wall columns on
# both sides. Walking off the floor's right edge drops her through open
# air onto the sink-tier floor below, then off that floor's edge again
# into the pit — each drop forced purely by the floor simply ending,
# no blocking wall needed on the drop path itself.
ENTRY_FLOOR_ROW = 26
ENTRY_FLOOR_COLS = range(1, 10)   # 7 tiles

# --- Sink-tier floor: solid, with a Saw Trap patrolling partway across
# it (start/end positions per the reference layout's two "S" marks).
SINK_FLOOR_ROW = 31
SINK_FLOOR_COLS = range(3, 13)   # 9 tiles
SAW_TRAP_START_COL = 5
SAW_TRAP_END_COL = 10

# --- Boundary/divider walls: (column, row_range) pairs, each independent
# so every wall can have its own height without sharing a row range.
WALLS = [
    (0,  range(22, 38)),   # left boundary, full height
    (12, range(24, 32)),   # short, guards the entry ledge
    (15, range(32, 38)),   # mid-level divider, 6 tiles tall
    (34, range(17, 32))
]

# --- Sunken pit: wide enough to sit under both the entry and sink
# tiers' full column ranges, so a fall off either tier's right edge
# always finds pit floor below rather than the lift (which starts
# further right, past the pit's own edge, so it can't intercept a fall
# meant for the pit). A Murk Crawler squad patrols the floor, with an
# Arrow Trap covering the stretch just past them; a checkpoint sits at
# the far end, right before the Mushroom Lift back up.
PIT_FLOOR_ROW = 37
PIT_FLOOR_COLS = range(1, 15)    # cols 2-13; col 13 doubles as the lift's rest tile
PIT_ARROW_TRAP_COL = 11          # sits past the crawlers, before the checkpoint/lift
CHECKPOINT_COL = 12
LIFT_COL = 14

# --- Single-tile mushroom-cap platforms: (column, row) pairs, each its
# own isolated ledge (drawn via mushroom_tiles.png — see self.platforms
# in __init__, not part of the tile grid). The first is the landing
# spot right after the Mushroom Lift, before the hazard pool; the rest
# are a hand-placed climbing chain toward the boss arena, filling in
# for the floating-platform shaft that was removed. NOT verified
# against real jump physics yet — the first hop, (16,32)->(16,31),
# doesn't chain cleanly in simulation, so treat this whole chain as
# unconfirmed until tested in-game.
LEDGES = [
    (16, 32),
    (16, 31),
    (15, 31),
    (17, 29),
    (19, 28),
    (21, 27),
    (19, 24),
    (22, 23),
    (25, 22),
    (28, 20),
    (30, 19),
    (32, 17),
]

# --- Second checkpoint: the final ledge above, right where Iris lands
# after the climb and right before Jinn Monster's arena — saves the
# whole ledge-climb + acid-bar crossing from having to be redone on
# death this late in the level.
CHECKPOINT2_COL = 35   
CHECKPOINT2_ROW = 17

# --- 2 falling speleothems (rock formations dropping from the cave
# ceiling) hazard this ledge-climbing "stairs" section instead of
# gating Jinn Monster's arena — each one's floor_y lands it directly on
# one of the LEDGES tiles above, so a badly-timed jump means landing on
# that ledge right as it splashes. Ceiling sits comfortably above the
# higher of the two landing spots (row 22) so the telegraph stays clear.
DRIP_CEILING_ROW = 14
DRIP_LANDING_SPOTS = [(21, 27), (25, 22)]  # (col, floor_row), both drawn from LEDGES above

# --- Acid-pool hazard, same height as the ledge. A shallow catch one
# row below (same idea as every other hazard gap in this scene) means
# walking straight across at floor height just means "take damage
# crossing it," not "fall forever" — LEDGES above is the intended way
# past it instead.
HAZARD_BAR_ROW = 31
HAZARD_BAR_COLS = range(17, 34)   # cols 17-25
HAZARD_CATCH_ROW = HAZARD_BAR_ROW + 1

# --- Jinn Monster arena: solid floor — its slam is a shockwave-ring +
# damage burst only (no floor fracture; the traveling ground-crack
# look now belongs to Bug Boss's Stomp instead, see
# _update_hazard_ground_cracks()).
BOSS_FLOOR_ROW = 17
BOSS_ARENA_COLS = range(35, 43)
BOSS_X_COL = 41

# --- Sealed gate (opens on Jinn Monster's death) + a short corridor
# leading to a breakable door.
GATE_COL = 43
GATE_ROW_TOP = 15
POST_GATE_FLOOR_COLS = range(44, 47)   # cols 44-46, between the gate and the door

# --- Breakable door: starts solid, takes 3 Glow Slash/Pollen Burst hits
# to smash through (see BreakableDoor below). Same 2-tile-tall opening
# as the sealed gate above it.
DOOR_COL = 47
DOOR_ROW_TOP = GATE_ROW_TOP
DOOR_ROWS = range(DOOR_ROW_TOP, BOSS_FLOOR_ROW)

# --- Bug Boss arena: the new 20-tile stretch beyond the door (cols
# 48-67). The first few tiles are a safe approach; crossing
# BUG_ARENA_TRIGGER_COL wakes the boss, at which point the scene seals
# DOOR_COL shut behind Iris (reusing the same tilemap column the door
# broke open) so the fight can't be skipped — it reopens once the boss
# dies. Lumen Shard 1 now sits at the far end, past the boss.
BUG_ARENA_FLOOR_COLS = range(48, LEVEL_COLS)   # cols 48-67
BUG_ARENA_TRIGGER_COL = 51                      # first 3 tiles (48-50) are safe
BUG_BOSS_X_COL = 60
SHARD_COL = 64
END_WALL_COL = LEVEL_COLS - 1                   # caps the level so Iris can't wander off the far edge

JINN_SLAM_COLOR = (80, 180, 230)  # cool magic-blue, distinct from Scene 3's murk-purple slam


class BreakableDoor:
    """A solid wall blocking the corridor beyond Jinn Monster's sealed
    gate, standing between Iris and the Bug Boss's arena. Unlike the
    sealed gate above (which opens automatically once its guarding boss
    dies), this one only opens once Iris has actually attacked it
    HITS_TO_BREAK times with Glow Slash or Pollen Burst — the scene
    removes the matching tilemap wall tiles the instant it breaks."""

    HITS_TO_BREAK = 3

    def __init__(self, col, rows):
        self.rect = pygame.Rect(
            col * TILE_SIZE, rows.start * TILE_SIZE,
            TILE_SIZE, len(rows) * TILE_SIZE,
        )
        self.hits_remaining = self.HITS_TO_BREAK
        self.broken = False

    def hit(self):
        """Register one attack against the door. Returns True the
        instant it breaks, so the caller opens the tilemap wall exactly
        once."""
        if self.broken:
            return False
        self.hits_remaining -= 1
        if self.hits_remaining <= 0:
            self.broken = True
            return True
        return False


class SlashEffect:
    """Brief visual-only slash-streak overlay shown the instant the Bug
    Boss's melee attack lands (bug_boss.py's pending_slash_fx) — plays
    through its frames once, then disappears. Purely cosmetic; the
    attack's own pending_attack_hit signal handles the actual damage,
    same split as every other boss-attack visual in this project.

    Anchored to the boss instance itself (read live via anchor.rect.center
    every frame) rather than a position snapshot taken at spawn time —
    the boss's attack lunges forward through its windup frames, so a
    frozen position would visibly lag behind it."""

    FRAME_DURATION = 0.08

    def __init__(self, frames, anchor, facing_right):
        self.frames = frames if facing_right else [pygame.transform.flip(f, True, False) for f in frames]
        self.frame_index = 0
        self.frame_timer = 0.0
        self.anchor = anchor
        self.done = False

    @property
    def expired(self):
        return self.done

    def update(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= self.FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index += 1
            if self.frame_index >= len(self.frames):
                self.done = True

    def draw(self, surface, camera_offset=(0, 0)):
        if self.done:
            return
        frame = self.frames[self.frame_index]
        center = self.anchor.rect.center
        rect = frame.get_rect(center=(center[0] - camera_offset[0], center[1] - camera_offset[1]))
        surface.blit(frame, rect)


def _build_grid():
    grid = [['.' for _ in range(LEVEL_COLS)] for _ in range(LEVEL_ROWS)]

    for col in ENTRY_FLOOR_COLS:
        grid[ENTRY_FLOOR_ROW][col] = '#'

    for col in SINK_FLOOR_COLS:
        grid[SINK_FLOOR_ROW][col] = '#'

    for col, rows in WALLS:
        for row in rows:
            grid[row][col] = '#'

    for col in PIT_FLOOR_COLS:
        grid[PIT_FLOOR_ROW][col] = '#'

    for col in HAZARD_BAR_COLS:
        grid[HAZARD_CATCH_ROW][col] = '#'

    for col in BOSS_ARENA_COLS:
        grid[BOSS_FLOOR_ROW][col] = '#'

    for col in POST_GATE_FLOOR_COLS:
        grid[BOSS_FLOOR_ROW][col] = '#'

    for row in range(GATE_ROW_TOP, BOSS_FLOOR_ROW):
        grid[row][GATE_COL] = '#'

    for row in DOOR_ROWS:
        grid[row][DOOR_COL] = '#'   # the breakable door — starts solid

    for col in BUG_ARENA_FLOOR_COLS:
        grid[BOSS_FLOOR_ROW][col] = '#'

    for row in range(BOSS_FLOOR_ROW - 6, BOSS_FLOOR_ROW):
        grid[row][END_WALL_COL] = '#'   # caps the level past the arena's far edge

    return [''.join(row) for row in grid]


class Scene1Grotto(BaseScene):
    def __init__(self, player):
        # Scene 1 uses a single background image rather than 3 parallax
        # layers — simpler to source, and it still scrolls slightly
        # slower than the foreground (scroll_factor 0.5) for a basic
        # sense of depth.
        background_layers = [
            (load_image(BACKGROUNDS_IMG_DIR / "scene1" / "layer1_far.png", size=(SCREEN_W, SCREEN_H)), 0.5),
        ]

        super().__init__(player, background_layers, _build_grid(), "grotto_tileset.png",
                          LEVEL_WIDTH, level_height=LEVEL_HEIGHT)

        entry_floor_y = ENTRY_FLOOR_ROW * TILE_SIZE
        sink_floor_y = SINK_FLOOR_ROW * TILE_SIZE
        pit_floor_y = PIT_FLOOR_ROW * TILE_SIZE
        hazard_bar_y = HAZARD_BAR_ROW * TILE_SIZE
        boss_floor_y = BOSS_FLOOR_ROW * TILE_SIZE

        self.platforms = [
            # Rides Iris from the pit floor back up to the ledge — flush
            # with each floor's walkable surface at either end.
            MushroomLift(x=LIFT_COL * TILE_SIZE, top_y=hazard_bar_y, bottom_y=pit_floor_y,
                         speed=70, pause_time=0.4),
        ] + [
            # The ledge-climbing chain, now drawn as mushroom-cap platforms
            # (matching PROJECT_BRIEF.md's "mushroom-cap platforms" for this
            # scene) instead of plain cave tiles. Same full-tile collision
            # footprint as the grid tiles they replaced, so the already-
            # verified jump spacing is untouched — Platform objects and
            # solid grid tiles feed the exact same solid_rects list in
            # BaseScene.update(), so swapping one for the other changes
            # nothing physics-wise.
            Platform(x=col * TILE_SIZE, y=row * TILE_SIZE, width=TILE_SIZE, height=TILE_SIZE,
                     image_filename="mushroom_tiles.png")
            for col, row in LEDGES
        ]

        speleothems = [
            FallingSpeleothem(x=col * TILE_SIZE, ceiling_y=DRIP_CEILING_ROW * TILE_SIZE, floor_y=row * TILE_SIZE)
            for col, row in DRIP_LANDING_SPOTS
        ]
        for i, speleothem in enumerate(speleothems[1:], start=1):
            speleothem.start_offset(i * 0.6)

        self.hazards = [
            AcidPool(x=HAZARD_BAR_COLS.start * TILE_SIZE, y=hazard_bar_y,
                      width=len(HAZARD_BAR_COLS) * TILE_SIZE, height=TILE_SIZE),
            *speleothems,
            # Patrols the sink-tier floor between two fixed points.
            SawTrap(start_pos=(SAW_TRAP_START_COL * TILE_SIZE, sink_floor_y - TILE_SIZE),
                    end_pos=(SAW_TRAP_END_COL * TILE_SIZE, sink_floor_y - TILE_SIZE),
                    speed=90, pause_time=0.3),
            # Sits past the crawler squad in the pit, firing leftward
            # back toward Iris as she crosses.
            ArrowTrap(x=PIT_ARROW_TRAP_COL * TILE_SIZE, y=pit_floor_y, direction=-1,
                      fire_interval=2.2, arrow_speed=260, damage=12, max_distance=350),
        ]

        self.boss = JinnMonster(x=BOSS_X_COL * TILE_SIZE, y=boss_floor_y)
        self.bug_boss = BugBoss(x=BUG_BOSS_X_COL * TILE_SIZE, y=boss_floor_y,
                                 trigger_x=BUG_ARENA_TRIGGER_COL * TILE_SIZE)
        self.enemies = [
            MurkCrawler(x=2.5 * TILE_SIZE, y=pit_floor_y, patrol_left=2 * TILE_SIZE, patrol_right=4 * TILE_SIZE),
            MurkCrawler(x=4.5 * TILE_SIZE, y=pit_floor_y, patrol_left=4 * TILE_SIZE, patrol_right=6 * TILE_SIZE),
            MurkCrawler(x=6.5 * TILE_SIZE, y=pit_floor_y, patrol_left=6 * TILE_SIZE, patrol_right=8 * TILE_SIZE),
            self.boss,
            self.bug_boss,
        ]

        self.door = BreakableDoor(DOOR_COL, DOOR_ROWS)
        self._arena_sealed = False

        # Checkpoint gates activate rather than being "collected" (they
        # don't disappear), so they aren't Collectibles — updated and
        # drawn separately below instead of via self.collectibles. Two
        # of them: the original at the pit/lift, and a second right
        # after the LEDGES climb (CHECKPOINT2_COL/ROW above).
        self.checkpoints = [
            CheckpointGate(x=CHECKPOINT_COL * TILE_SIZE, y=pit_floor_y),
            CheckpointGate(x=CHECKPOINT2_COL * TILE_SIZE, y=CHECKPOINT2_ROW * TILE_SIZE),
        ]
        self.shard = LumenShard(x=SHARD_COL * TILE_SIZE, y=boss_floor_y - 40)

        self.collectibles = [
            GlowOrb(x=3 * TILE_SIZE, y=entry_floor_y - 40),
            GlowOrb(x=6 * TILE_SIZE, y=sink_floor_y - 40),
            # Shard is NOT added here — it only appears once the Bug Boss
            # dies (see _update_bug_boss()), so it can't be run past and
            # grabbed without actually beating him.
        ]
        self._shard_spawned = False

        self.shockwaves = []
        self.slash_effects = []

        # Iris "falls in from a crack above" — spawn her mid-air over the
        # entry ledge and let gravity carry her down.
        self.player.rect.midbottom = (3.5 * TILE_SIZE, 24 * TILE_SIZE)

        self.respawn_point = self.player.rect.midbottom
        self.gate_open = False
        self._gate_open_sound = load_sound(SFX_DIR / "gate_open.wav")
        self._door_hit_sound = load_sound(SFX_DIR / "enemy_hit.wav")

        # Pollen Burst (unlocks Scene 3) and Tendril Whip (unlocks Scene 2's
        # chest) are both locked by Player's own defaults — nothing to set
        # here, Iris only has Glow Slash in Scene 1.

        self.lighting = CaveLighting()

    def update_scene(self, dt):
        for checkpoint in self.checkpoints:
            checkpoint.update(dt)
            if checkpoint.check_activate(self.player):
                self.respawn_point = checkpoint.rect.midbottom

        self._update_boss_attacks(dt)
        self._update_shockwaves(dt)
        self._update_bug_boss(dt)
        self._update_hazard_ground_cracks()
        self.lighting.update(dt, self.player.rect, self.tilemap)

        if not self.gate_open and self.boss.is_dead and self.boss.death_anim_done:
            self.gate_open = True
            play_sound(self._gate_open_sound)
            for row in range(GATE_ROW_TOP, BOSS_FLOOR_ROW):
                self.tilemap.open_gate_at(GATE_COL, row)

    def _update_boss_attacks(self, dt):
        slam = self.boss.take_pending_slam()
        if slam is not None:
            self._on_boss_slam(slam)

    def _on_boss_slam(self, slam):
        self.screen_shake.trigger(duration=0.3, magnitude=8)
        self.shockwaves.append(Shockwave(
            slam["center"], max_radius=slam["crack_radius"] * TILE_SIZE * 2,
            color=JINN_SLAM_COLOR,
        ))
        if not self.player.is_dead and abs(self.player.rect.centerx - slam["center"][0]) <= slam["damage_range"]:
            self.player.take_damage(slam["damage"])

    def _update_shockwaves(self, dt):
        for shockwave in self.shockwaves:
            shockwave.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.alive]

    def _update_bug_boss(self, dt):
        boss = self.bug_boss

        # The moment Iris wakes the boss, seal the door shut behind her
        # (reusing the same column it broke open at) so the fight can't
        # be skipped — it reopens once the boss is defeated.
        if boss.aggro and not self._arena_sealed:
            self._arena_sealed = True
            for row in DOOR_ROWS:
                self.tilemap.close_gate_at(DOOR_COL, row)

        stomp = boss.take_pending_stomp()
        if stomp is not None:
            self.hazards.append(GroundSpikeWave(
                x=stomp["x"], floor_y=stomp["floor_y"],
                direction=stomp["direction"], damage=stomp["damage"],
            ))

        attack_hit = boss.take_pending_attack_hit()
        if attack_hit is not None:
            self._on_bug_boss_attack_hit(attack_hit)

        slash_fx = boss.take_pending_slash_fx()
        if slash_fx is not None:
            self.slash_effects.append(SlashEffect(
                boss.slash_fx_frames, boss, slash_fx["facing_right"],
            ))

        self.hazards = [h for h in self.hazards if not getattr(h, "expired", False)]

        for effect in self.slash_effects:
            effect.update(dt)
        self.slash_effects = [e for e in self.slash_effects if not e.expired]

        if self._arena_sealed and boss.is_dead and boss.death_anim_done:
            self._arena_sealed = False
            for row in DOOR_ROWS:
                self.tilemap.open_gate_at(DOOR_COL, row)

        # Spawn the shard only once the boss death animation finishes.
        if boss.is_dead and boss.death_anim_done and not self._shard_spawned:
            self._shard_spawned = True
            self.collectibles.append(self.shard)
            self.particles.emit_petals(self.shard.rect.center, count=30)

    def _update_hazard_ground_cracks(self):
        """Bug Boss's Stomp (GroundSpikeWave) makes the floor look like
        it's cracking directly under the wave as it travels — purely
        cosmetic, and only for the tile(s) the wave currently overlaps;
        recomputed from scratch every frame so a tile's crack look
        disappears the instant the wave has moved past it, rather than
        the permanent crack-then-break of an 'X' tile (see Jinn
        Monster's now-solid arena floor above)."""
        covered = set()
        for hazard in self.hazards:
            if isinstance(hazard, GroundSpikeWave):
                row = hazard.floor_y // TILE_SIZE
                col_start = hazard.rect.left // TILE_SIZE
                col_end = (hazard.rect.right - 1) // TILE_SIZE
                for col in range(col_start, col_end + 1):
                    covered.add((col, row))
        self.tilemap.set_temp_cracked_positions(covered)

    def _on_bug_boss_attack_hit(self, hit):
        self.screen_shake.trigger(duration=0.25, magnitude=6)
        self.particles.emit_dust_impact(hit["center"])
        if not self.player.is_dead and abs(self.player.rect.centerx - hit["center"][0]) <= hit["damage_range"]:
            self.player.take_damage(hit["damage"])

    def draw_scene(self, surface, camera_offset):
        for checkpoint in self.checkpoints:
            checkpoint.draw(surface, camera_offset)
        for shockwave in self.shockwaves:
            shockwave.draw(surface, camera_offset)
        for effect in self.slash_effects:
            effect.draw(surface, camera_offset)
        self.lighting.draw(surface, camera_offset, self.player.rect.center)
        if self.bug_boss.aggro:
            self.bug_boss.draw_health_bar(surface)

    def on_glow_slash_hit(self, hitbox, damage):
        self._check_door_hit(hitbox)

    def on_pollen_burst_hit(self, center, radius, damage):
        # Pollen Burst's hit area is circular, not a rect — approximate
        # with a small square around its center for the door's simple
        # AABB hit-test.
        probe = pygame.Rect(0, 0, radius * 2, radius * 2)
        probe.center = center
        self._check_door_hit(probe)

    def _check_door_hit(self, hitbox):
        if self.door.broken or not hitbox.colliderect(self.door.rect):
            return
        play_sound(self._door_hit_sound)
        self.particles.emit_dust_impact(self.door.rect.center, count=8)
        if self.door.hit():
            play_sound(self._gate_open_sound)
            self.screen_shake.trigger(duration=0.2, magnitude=6)
            for row in DOOR_ROWS:
                self.tilemap.open_gate_at(DOOR_COL, row)

    def on_collect(self, collectible):
        if collectible is self.shard:
            self.finished = True

"""
scene3_spire.py

Scene 3 — The Hollow Spire (Member 3). A corrupted fortress overtaken
by fungus. Iris hops and climbs her way through the entrance corridor,
destroys Murk Spore clusters to keep the Murk Meter in check, climbs a
vertical shaft of wall ledges, and finds a vine switch right beside the
sealed wall to the boss that breaks it open the instant it's hit —
then defeats the two-phase Fungal Warden and collects Lumen Shard 3
(PROJECT_BRIEF.md section 5).
"""

from config.settings import TILE_SIZE, COLORS, BACKGROUNDS_IMG_DIR, SFX_DIR
from src.core.asset_loader import load_image, load_sound, play_sound
from src.scenes.base_scene import BaseScene
from src.world.hazards import MurkPool, MurkSporeCluster, MurkMeter, MyceliumTendril
from src.world.collectibles import GlowOrb, LumenShard, CheckpointGate, VineSwitch
from src.entities.enemies.murk_crawler import MurkCrawler
from src.entities.bosses.fungal_warden import FungalWarden
from src.effects.shockwave import Shockwave

LEVEL_COLS = 70
LEVEL_ROWS = 18
LEVEL_WIDTH = LEVEL_COLS * TILE_SIZE
LEVEL_HEIGHT = LEVEL_ROWS * TILE_SIZE

# Two floor heights: the entrance/spore-room/shaft-base corridor down
# low, and the post-climb corridor + boss arena up high. The vertical
# shaft (section 5: "wall ledges in a vertical shaft section") bridges
# the two. Both corridors now also have their own smaller up-and-down
# beats (gaps to hop, staircases to climb) rather than being one flat
# walk from end to end.
LOWER_FLOOR_ROW = 15
UPPER_FLOOR_ROW = 6
LOWER_FLOOR_Y = LOWER_FLOOR_ROW * TILE_SIZE
UPPER_FLOOR_Y = UPPER_FLOOR_ROW * TILE_SIZE

# --- Entrance: a plain 1-tile hop right past the spawn point — simple,
# since it's the very first thing Iris meets.
ENTRANCE_GAP_COL = 9

# --- A bonus staircase in the lower corridor — same rule as the main
# shaft further down (each step 2 rows up / 1 col over except the
# first, which is only 1 row up — flush enough not to clip Iris's head
# on the standing jump that starts the climb), always climbing the
# same direction so no jump ever re-approaches a ledge from the wrong
# side. The floor stays solid underneath the whole climb, so a missed
# jump just drops her back to the ground instead of costing the
# attempt. Purely optional now — the switch lives by the boss wall
# instead (see SWITCH_COL below), so this is just an extra bit of
# platforming, mirroring the upper corridor's own bonus staircase.
LOWER_PLATEAU_ROW = LOWER_FLOOR_ROW - 7   # 8
LOWER_PLATEAU_COLS = range(16, 19)        # 3-tile standing platform
LOWER_STAIRS = []
_row, _col = LOWER_FLOOR_ROW - 1, 13
while _row >= LOWER_PLATEAU_ROW:
    LOWER_STAIRS.append((_row, _col))
    _row -= 2
    _col += 1
del _row, _col

MURK_POOL_COLS = range(20, 22)          # dip in the floor, instant-damage pool
SPORE_CLUSTER_COLS = (22, 26)           # separated destructible growths in lower corridor
LOWER_SPORE_CLUSTER_COL = 17            # 2nd spore placed on the lower plateau
PIT_COLS = range(27, 30)                # 2-tile-deep trench — a detour, nothing hidden there now

# Vertical shaft: single-tile stepping-stone ledges climbing as a
# one-direction staircase (always rightward), flanked by
# SHAFT_LEFT_COL/SHAFT_RIGHT_COL but with no solid wall tiles there —
# every jump in this engine rises to the same ~134px apex regardless of
# the target's height (there's no variable jump-height mechanic), so a
# wall anywhere near a ledge risks Iris bonking her head on it mid-arc
# before she's cleared its column. The ledges themselves are the only
# support she needs; drifting off the side just drops her back to a
# floor below.
#
# Each step rises 2 tiles (128px) and shifts 1 column (64px) rightward
# — verified empirically (not just by height math) by simulating
# Player.update() against test rigs, chained across several ledges in a
# row: a zigzag that reverses direction partway up reliably fails,
# because jumping *back* toward an earlier ledge clips its far corner
# the same way a too-close same-direction step does. A staircase that
# only ever climbs one way never re-approaches a tile from the wrong
# side, which is what makes it reliable.
#
# The staircase climbs all the way up to UPPER_FLOOR_ROW itself (not
# stopping a couple of rows short) — the corridor's floor only starts
# *after* SHAFT_RIGHT_COL, so the last ledge has open sky above it
# rather than sitting 2 tiles under a wide overhanging floor (which
# would clip Iris's head the same way switch 1's ledge did).
# Landing the final step flush with the corridor's row turns what would
# otherwise be one last cramped jump into a plain walk onto solid
# ground.
SHAFT_LEFT_COL = 30
SHAFT_RIGHT_COL = 35
SHAFT_ROW_TOP = UPPER_FLOOR_ROW         # 6
SHAFT_ROW_BOTTOM = LOWER_FLOOR_ROW - 1  # 14
SHAFT_ROW_STEP = 2
SHAFT_LEDGES = []
_row, _col = SHAFT_ROW_BOTTOM, SHAFT_LEFT_COL + 1
while _row >= SHAFT_ROW_TOP:
    SHAFT_LEDGES.append((_row, _col))
    _row -= SHAFT_ROW_STEP
    _col += 1
del _row, _col
# (row, col), bottom to top

CHECKPOINT_COL = 40
UPPER_GAP_COL = 41                      # another plain 1-tile hop, mirrors the entrance's
POST_SHAFT_CRAWLER_COL = 38
PRE_GATE_CRAWLER_COL = 43

# --- A second, smaller staircase in the upper corridor — same rule as
# switch 1's (first step 1 row up, then 2 rows up / 1 col over,
# monotonic direction). Purely optional: the floor below stays solid
# the whole way, so this is a bonus detour for a spore cluster, not a
# mandatory jump like switch 1's climb.
UPPER_PLATEAU_ROW = UPPER_FLOOR_ROW - 3  # 3
UPPER_PLATEAU_COLS = range(47, 49)       # 2-tile bonus platform
UPPER_STAIRS = []
_row, _col = UPPER_FLOOR_ROW - 1, 46
while _row >= UPPER_PLATEAU_ROW:
    UPPER_STAIRS.append((_row, _col))
    _row -= 2
    _col += 1
del _row, _col
UPPER_SPORE_CLUSTER_COL = 47            # a 4th cluster, sitting on the bonus platform

GATE_COL = 50
SWITCH_COL = GATE_COL - 1                # right in front of the sealed wall
# Sealed floor-to-ceiling (row 0, the top of the level) rather than
# just a few tiles tall — the upper-corridor bonus staircase means Iris
# can reach real height nearby (jump apex is ~2.1 tiles from *any*
# standing height, not just from UPPER_FLOOR_ROW), so a shorter door
# risks being jumped clean over instead of actually blocking the only
# way to the boss.
GATE_ROW_TOP = 0
BOSS_COL = 60
SHARD_COL = 66
# A 5th cluster inside the arena itself — without one here, a Fungal
# Warden fight that runs long has no way to bring the Murk Meter back
# down mid-fight (regrowth alone doesn't help if Iris never returns to
# an earlier room to use it).
ARENA_SPORE_CLUSTER_COL = 53


def _build_grid():
    grid = [['.' for _ in range(LEVEL_COLS)] for _ in range(LEVEL_ROWS)]

    # --- Lower corridor: entrance -> bonus climb -> spore room -> pit -> shaft base ---
    for col in range(2, SHAFT_RIGHT_COL + 1):
        grid[LOWER_FLOOR_ROW][col] = '#'
    grid[LOWER_FLOOR_ROW][ENTRANCE_GAP_COL] = '.'

    for row, col in LOWER_STAIRS:
        grid[row][col] = '#'
    for col in LOWER_PLATEAU_COLS:
        grid[LOWER_PLATEAU_ROW][col] = '#'

    for col in MURK_POOL_COLS:
        grid[LOWER_FLOOR_ROW][col] = '.'
        grid[LOWER_FLOOR_ROW + 1][col] = '#'  # shallow: catches Iris one tile down, no free-fall

    for col in PIT_COLS:
        grid[LOWER_FLOOR_ROW][col] = '.'
        grid[LOWER_FLOOR_ROW + 2][col] = '#'  # trench floor, 2 tiles down

    # --- Vertical shaft ---
    # The bottom ledge (SHAFT_LEDGES[0]) sits only 1 tile above the main
    # floor — flush enough that Iris's body would collide with it while
    # just walking up. The interior columns (plus the right edge) are a
    # full open gap now — no shallow catch — so missing the shaft
    # ledges means a real fall, not a one-tile save.
    for col in range(SHAFT_LEFT_COL + 1, SHAFT_RIGHT_COL + 1):
        grid[LOWER_FLOOR_ROW][col] = '.'
    for row, col in SHAFT_LEDGES:
        grid[row][col] = '#'

    # --- Upper corridor: shaft top -> checkpoint -> gap -> bonus climb -> boss door -> arena ---
    # Starts just past the shaft's last ledge (not at SHAFT_LEFT_COL) —
    # see the SHAFT_LEDGES comment above for why the floor can't overhang
    # the climbing columns.
    for col in range(SHAFT_RIGHT_COL + 1, LEVEL_COLS - 2):
        grid[UPPER_FLOOR_ROW][col] = '#'
    grid[UPPER_FLOOR_ROW][UPPER_GAP_COL] = '.'

    for row, col in UPPER_STAIRS:
        grid[row][col] = '#'
    for col in UPPER_PLATEAU_COLS:
        grid[UPPER_PLATEAU_ROW][col] = '#'

    for row in range(GATE_ROW_TOP, UPPER_FLOOR_ROW):
        grid[row][GATE_COL] = '#'

    return [''.join(row) for row in grid]


class Scene3Spire(BaseScene):
    def __init__(self, player):
        background_layers = [
            (load_image(BACKGROUNDS_IMG_DIR / "scene3" / "layer1.png"), 0.1),
            (load_image(BACKGROUNDS_IMG_DIR / "scene3" / "layer2.png"), 0.3),
            (load_image(BACKGROUNDS_IMG_DIR / "scene3" / "layer3.png"), 0.5),
            (load_image(BACKGROUNDS_IMG_DIR / "scene3" / "layer4.png"), 0.7),
            (load_image(BACKGROUNDS_IMG_DIR / "scene3" / "layer5.png"), 0.9),
        ]

        super().__init__(player, background_layers, _build_grid(), "spire_tileset.png",
                          LEVEL_WIDTH, level_height=LEVEL_HEIGHT)

        # --- Hazards (auto-updated by BaseScene's hazard loop) ---
        self.hazards = [
            MurkPool(x=MURK_POOL_COLS.start * TILE_SIZE, y=LOWER_FLOOR_Y,
                     width=len(MURK_POOL_COLS) * TILE_SIZE, height=TILE_SIZE),
        ]

        # --- Mycelium Tendrils: wall-mounted barriers that shoot across
        # corridors on a timer (PROJECT_BRIEF.md section 5). Three placed
        # at different positions, staggered so they never all extend at once.
        # x for direction=1  → base LEFT  edge on the wall face
        # x for direction=-1 → base RIGHT edge on the wall face
        t1 = MyceliumTendril(x=14 * TILE_SIZE, y=LOWER_FLOOR_Y, direction=1,  reach=TILE_SIZE * 4)
        t1.start_offset(0.0)
        # T2: 5 columns right of previous position (col 30), right edge at col 31
        t2 = MyceliumTendril(x=31 * TILE_SIZE, y=LOWER_FLOOR_Y, direction=-1, reach=TILE_SIZE * 3)
        t2.start_offset(1.2)
        # T3: upper corridor col 45, shoots leftward
        t3 = MyceliumTendril(x=46 * TILE_SIZE, y=UPPER_FLOOR_Y, direction=-1, reach=TILE_SIZE * 4)
        t3.start_offset(2.0)
        self.tendrils = [t1, t2, t3]


        # --- Murk Spore clusters (custom hit-detection via on_*_hit hooks) ---
        self.spore_clusters = [
            MurkSporeCluster(x=17 * TILE_SIZE, y=LOWER_PLATEAU_ROW * TILE_SIZE - TILE_SIZE),
            MurkSporeCluster(x=28 * TILE_SIZE, y=(LOWER_FLOOR_ROW + 2) * TILE_SIZE - TILE_SIZE),
            MurkSporeCluster(x=UPPER_SPORE_CLUSTER_COL * TILE_SIZE,
                              y=UPPER_PLATEAU_ROW * TILE_SIZE - TILE_SIZE),
            MurkSporeCluster(x=ARENA_SPORE_CLUSTER_COL * TILE_SIZE, y=UPPER_FLOOR_Y - TILE_SIZE),
        ]
        self.murk_meter = MurkMeter()

        # --- The one vine switch, right in front of the sealed wall —
        # hitting it breaks the wall open immediately (see
        # update_scene()). Floats at roughly Iris's own chest height
        # (-48px, not just -4px off the floor) so Glow Slash's narrow
        # hitbox band — centered on her body, not her feet — actually
        # reaches it, not just Pollen Burst's much wider radius.
        self.switch = VineSwitch(x=SWITCH_COL * TILE_SIZE + TILE_SIZE // 2, y=UPPER_FLOOR_ROW * TILE_SIZE - 48)
        self.gate_open = False
        self._gate_open_sound = load_sound(SFX_DIR / "gate_open.wav")

        # --- Enemies: Murk Crawlers that each respawn once (section 5) ---
        self._crawler_spawns = [
            {"x": 5 * TILE_SIZE, "y": LOWER_FLOOR_Y, "patrol_left": 3 * TILE_SIZE, "patrol_right": 8 * TILE_SIZE},
            {"x": POST_SHAFT_CRAWLER_COL * TILE_SIZE, "y": UPPER_FLOOR_Y,
             "patrol_left": (SHAFT_RIGHT_COL + 1) * TILE_SIZE, "patrol_right": 40 * TILE_SIZE},
            {"x": PRE_GATE_CRAWLER_COL * TILE_SIZE, "y": UPPER_FLOOR_Y,
             "patrol_left": 42 * TILE_SIZE, "patrol_right": 45 * TILE_SIZE},
        ]
        for spawn in self._crawler_spawns:
            spawn["enemy"] = MurkCrawler(spawn["x"], spawn["y"], spawn["patrol_left"], spawn["patrol_right"])
            spawn["respawns_left"] = 0   # killed permanently — no respawn
            spawn["respawn_timer"] = None

        self.boss = FungalWarden(x=BOSS_COL * TILE_SIZE, y=UPPER_FLOOR_Y)
        self.enemies = [spawn["enemy"] for spawn in self._crawler_spawns] + [self.boss]

        # --- Boss attack fallout ---
        self.shockwaves = []
        self._spore_rain_zone = None
        self._spore_rain_particle_timer = 0.0

        # --- Checkpoint & collectibles ---
        self.checkpoint = CheckpointGate(x=CHECKPOINT_COL * TILE_SIZE, y=UPPER_FLOOR_Y)
        self.shard = LumenShard(x=SHARD_COL * TILE_SIZE, y=UPPER_FLOOR_Y - 40)
        self.collectibles = [
            GlowOrb(x=ENTRANCE_GAP_COL * TILE_SIZE, y=LOWER_FLOOR_Y - 40),
            GlowOrb(x=42 * TILE_SIZE, y=UPPER_FLOOR_Y - 40),
            # Shard is NOT added here — it only appears after the boss dies
        ]
        self._shard_spawned = False

        self.player.rect.midbottom = (3 * TILE_SIZE, LOWER_FLOOR_Y)
        self.respawn_point = self.player.rect.midbottom

        # Pollen Burst unlocks starting here — locked in Scenes 1-2.
        self.player.pollen_burst_unlocked = True

    # --- Ability hits on the switch / spore clusters (base_scene.py hooks) ---

    def on_glow_slash_hit(self, hitbox, damage):
        # Glow Slash (X) can hit the vine switch but NOT destroy spore clusters
        # — clusters only respond to Pollen Burst (Z)
        if hitbox.colliderect(self.switch.rect):
            self.switch.hit()

    def on_pollen_burst_hit(self, center, radius, damage):
        if self._within_radius(self.switch.rect, center, radius):
            self.switch.hit()
        for cluster in self.spore_clusters:
            if not cluster.destroyed and self._within_radius(cluster.rect, center, radius):
                self._destroy_cluster(cluster)

    @staticmethod
    def _within_radius(rect, center, radius):
        dx = rect.centerx - center[0]
        dy = rect.centery - center[1]
        return (dx * dx + dy * dy) ** 0.5 <= radius

    def _destroy_cluster(self, cluster):
        cluster.hit()
        self.murk_meter.reduce()

    # --- Per-frame scene logic ---

    def update_scene(self, dt):
        self.checkpoint.update(dt)
        if self.checkpoint.check_activate(self.player):
            self.respawn_point = self.checkpoint.rect.midbottom

        for cluster in self.spore_clusters:
            cluster.update(dt)

        # Update tendrils and check if they hit the player
        for tendril in self.tendrils:
            tendril.update(dt)
            tendril.apply_damage(self.player, dt)

        self.murk_meter.update(dt, self.player)

        self._update_crawler_respawns(dt)
        self._update_boss_attacks(dt)
        self._update_shockwaves(dt)
        self._update_spore_rain_zone(dt)

        if not self.gate_open and self.switch.active:
            self.gate_open = True
            play_sound(self._gate_open_sound)
            self.screen_shake.trigger(duration=0.2, magnitude=6)
            for row in range(GATE_ROW_TOP, UPPER_FLOOR_ROW):
                self.tilemap.open_gate_at(GATE_COL, row)

        # Spawn the shard only once the boss death animation finishes
        if self.boss.is_dead and self.boss.death_anim_done and not self._shard_spawned:
            self._shard_spawned = True
            self.collectibles.append(self.shard)
            self.particles.emit_petals(self.shard.rect.center, count=30)

    def _update_crawler_respawns(self, dt):
        RESPAWN_DELAY = 3.0
        for spawn in self._crawler_spawns:
            enemy = spawn["enemy"]
            if spawn["respawns_left"] <= 0:
                continue

            if enemy.is_dead and enemy.death_anim_done:
                if spawn["respawn_timer"] is None:
                    spawn["respawn_timer"] = 0.0
                else:
                    spawn["respawn_timer"] += dt
                    if spawn["respawn_timer"] >= RESPAWN_DELAY:
                        spawn["respawns_left"] -= 1
                        spawn["respawn_timer"] = None
                        new_enemy = MurkCrawler(spawn["x"], spawn["y"],
                                                 spawn["patrol_left"], spawn["patrol_right"])
                        spawn["enemy"] = new_enemy
                        self.enemies.append(new_enemy)

    def _update_boss_attacks(self, dt):
        slam = self.boss.take_pending_slam()
        if slam is not None:
            self._on_boss_slam(slam)

        spore_rain = self.boss.take_pending_spore_rain()
        if spore_rain is not None:
            self._spore_rain_zone = {
                "center": spore_rain["center"],
                "radius": spore_rain["radius"],
                "damage_per_second": spore_rain["damage_per_second"],
                "timer": spore_rain["duration"],
            }

    def _on_boss_slam(self, slam):
        self.screen_shake.trigger(duration=0.35, magnitude=10)
        self.tilemap.crack_tiles_near(*slam["grid_pos"], radius=slam["crack_radius"])
        self.shockwaves.append(Shockwave(
            slam["center"], max_radius=slam["crack_radius"] * TILE_SIZE * 2,
            color=COLORS["murk_purple"],
        ))
        if not self.player.is_dead and abs(self.player.rect.centerx - slam["center"][0]) <= slam["damage_range"]:
            self.player.take_damage(slam["damage"])

    def _update_shockwaves(self, dt):
        for shockwave in self.shockwaves:
            shockwave.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.alive]

    def _update_spore_rain_zone(self, dt):
        zone = self._spore_rain_zone
        if zone is None:
            return

        zone["timer"] -= dt
        if not self.player.is_dead and abs(self.player.rect.centerx - zone["center"][0]) <= zone["radius"]:
            self.player.hp = max(0, self.player.hp - zone["damage_per_second"] * dt)
            if self.player.hp <= 0:
                self.player.is_dead = True

        self._spore_rain_particle_timer += dt
        if self._spore_rain_particle_timer >= 0.15:
            self._spore_rain_particle_timer = 0.0
            cx = zone["center"][0]
            self.particles.emit_spore_rain(x_range=(cx - zone["radius"], cx + zone["radius"]),
                                            y=zone["center"][1] - 200)

        if zone["timer"] <= 0:
            self._spore_rain_zone = None

    # --- Draw ---

    def draw_scene(self, surface, camera_offset):
        self.checkpoint.draw(surface, camera_offset)
        self.switch.draw(surface, camera_offset)
        for tendril in self.tendrils:
            tendril.draw(surface, camera_offset)
        for cluster in self.spore_clusters:
            cluster.draw(surface, camera_offset)
        for shockwave in self.shockwaves:
            shockwave.draw(surface, camera_offset)

        if not self.boss.death_anim_done:
            self.boss.draw_health_bar(surface)

        self.murk_meter.draw_vignette(surface)

    def on_collect(self, collectible):
        if collectible is self.shard:
            self.finished = True

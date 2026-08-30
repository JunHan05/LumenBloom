"""
scene2_skybloom.py

Scene 2 — The Skybloom Reach (Member 2). Jungle treetops high above
ground. Iris fights Briarlings, crosses gaps with the newly-unlocked
Tendril Whip (falling is fatal — no floor to catch her), survives a
Stalker Root ambush and a wind gust, then faces the Sky Wisp dragon
before collecting Lumen Shard 2 (PROJECT_BRIEF.md section 5).
"""

import random
import pygame

from config.settings import TILE_SIZE, BACKGROUNDS_IMG_DIR, IMAGES_DIR, SCREEN_W, SCREEN_H
from src.core.asset_loader import load_image
from src.scenes.base_scene import BaseScene

class EnvironmentDecoration:
    """A static decorative sprite in the level environment (e.g. tree, bush, rock)."""
    def __init__(self, image, x, y, size):
        self.image = pygame.transform.scale(image, size)
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))
from src.world.platforms import SwayingPlatform
from src.world.collectibles import GlowOrb, LumenShard, CheckpointGate, Chest
from src.entities.enemies.briarling import Briarling
from src.entities.enemies.stalker_root import StalkerRoot
from src.entities.bosses.sky_wisp import SkyWisp
from src.effects.shockwave import Shockwave

LEVEL_COLS = 58
LEVEL_ROWS = 12
LEVEL_WIDTH = LEVEL_COLS * TILE_SIZE
FLOOR_ROW = 9

CHECKPOINT_COL = 25
WIND_ZONE_COLS = range(21, 24)
WIND_ZONE_2_COLS = range(32, 36)  # Second storm section across cols 32 to 35
WIND_PUSH_SPEED = 120  # stronger wind — heavy storm

# Falling into a gap is fatal
FALL_DEATH_MARGIN = 250


def _build_grid():
    grid = [['.' for _ in range(LEVEL_COLS)] for _ in range(LEVEL_ROWS)]

    # Lower Ground Floor (Row 9) — Starting area
    for col in range(1, 14):
        grid[FLOOR_ROW][col] = '#'

    # First grapple wall (Column 15, Rows 3–7) — climb to upper section
    for row in range(3, 8):
        grid[row][15] = '#'

    # Upper Floor Part 1 (Row 5): cols 16–21
    for col in range(16, 22):
        grid[5][col] = '#'

    # Upper Floor Part 2 (Row 5): cols 24–31 (extended)
    for col in range(24, 32):
        grid[5][col] = '#'

    # Second grapple wall (Column 35, Rows 3–7) — Tendril Whip anchor
    for row in range(3, 8):
        grid[row][35] = '#'

    # Upper Floor Part 3 (Row 5): cols 36–46 — NEW section after second gap
    for col in range(36, 47):
        grid[5][col] = '#'

    # Ground Floor Boss Arena (Row 9): cols 42–56 — extended boss area
    for col in range(42, LEVEL_COLS - 2):
        grid[FLOOR_ROW][col] = '#'

    return [''.join(row) for row in grid]


class Scene2Skybloom(BaseScene):
    def __init__(self, player):
        background_layers = [
            (load_image(BACKGROUNDS_IMG_DIR / "scene2" / "layer-01.png"), 0.2),
            (load_image(BACKGROUNDS_IMG_DIR / "scene2" / "layer2_mid.png"), 0.5),
            (load_image(BACKGROUNDS_IMG_DIR / "scene2" / "layer3_near.png"), 0.8),
        ]

        super().__init__(player, background_layers, _build_grid(), "skybloom_tileset.png", LEVEL_WIDTH)

        floor_y = FLOOR_ROW * TILE_SIZE
        upper_y = 5 * TILE_SIZE

        # Swaying platform in the middle of the upper floor gap
        self.platforms = [
            # First gap (cols 22–23) — original swaying platform
            SwayingPlatform(x=22 * TILE_SIZE, y=upper_y, width=TILE_SIZE, height=16,
                             sway_amplitude=24, sway_speed=1.2),
            # Second gap (cols 32–35) — wider, requires Tendril Whip or timing
            SwayingPlatform(x=33 * TILE_SIZE, y=upper_y, width=TILE_SIZE, height=16,
                             sway_amplitude=28, sway_speed=1.6),
        ]

        # Lock player's Tendril Whip initially in Scene 2 until they find the chest
        self.player.tendril_whip_unlocked = False
        self.chest = None
        self.chest_spawned = False
        self.tutorial_timer = 0.0
        self.tutorial_text = ""

        self.boss = SkyWisp(x=50 * TILE_SIZE, y=floor_y - 4.5 * TILE_SIZE)
        self.first_stalker = StalkerRoot(x=10 * TILE_SIZE, y=floor_y)
        self.enemies = [
            # Lower Floor minions
            Briarling(x=5 * TILE_SIZE, y=floor_y, patrol_left=3 * TILE_SIZE, patrol_right=8 * TILE_SIZE),
            self.first_stalker,
            # Upper Floor Part 1 minions
            Briarling(x=20 * TILE_SIZE, y=upper_y, patrol_left=19 * TILE_SIZE, patrol_right=21 * TILE_SIZE),
            StalkerRoot(x=27 * TILE_SIZE, y=upper_y),
            # Upper Floor Part 3 minions — new extended section
            Briarling(x=39 * TILE_SIZE, y=upper_y, patrol_left=37 * TILE_SIZE, patrol_right=43 * TILE_SIZE),
            Briarling(x=44 * TILE_SIZE, y=upper_y, patrol_left=41 * TILE_SIZE, patrol_right=46 * TILE_SIZE),
        ]

        self.boss_spawned = False
        self.in_dialogue = False
        self.dialogue_finished = False
        self.gate_open = False

        # Boss visual effects
        self.shockwaves = []          # expanding rings when the boss dive-impacts
        self._feathers_emitted = False  # guard so feather rain fires exactly once

        # Storm / wind zone effects
        self._in_wind_zone = False
        # Parallax rain: foreground (fast, bright) + background (slow, dim)
        self._rain_fg = [(random.randint(0, SCREEN_W), random.randint(0, SCREEN_H))
                         for _ in range(50)]
        self._rain_bg = [(random.randint(0, SCREEN_W), random.randint(0, SCREEN_H))
                         for _ in range(30)]
        # Wind speed-streaks: fast horizontal lines flying across the screen
        self._wind_streaks = []   # each entry: [x, y, length, speed, alpha]

        # Lightning flash state (active during boss fight)
        self._lightning_timer = random.uniform(3.0, 7.0)
        self._lightning_alpha = 0.0    # 0 = no flash, up to 200 = white flash
        self._lightning_bolt  = []     # list of (x, y) points for the bolt shape
        
        self.dialogue_lines = []
        self.dialogue_index = 0
        self.prev_dialogue_press = False

        self.checkpoint = CheckpointGate(x=CHECKPOINT_COL * TILE_SIZE, y=upper_y)
        self.shard = LumenShard(x=53 * TILE_SIZE, y=floor_y - 40)

        self.collectibles = [
            GlowOrb(x=22 * TILE_SIZE, y=upper_y - 40),
            GlowOrb(x=41 * TILE_SIZE, y=upper_y - 40),  # second orb in new section
        ]

        # Pre-populate screen with falling ambient leaves
        for _ in range(35):
            x = random.uniform(0, LEVEL_WIDTH)
            y = random.uniform(-20, SCREEN_H)
            self.particles.emit_ambient_leaves((x, x), y, count=1)

        # Iris starts at the bottom-left
        self.player.rect.midbottom = (2 * TILE_SIZE, floor_y)

        self.respawn_point = self.player.rect.midbottom
        self.fall_death_y = floor_y + FALL_DEATH_MARGIN

        # Load environment decorations
        decor_dir = IMAGES_DIR / "decorations" / "scene2"

        def make_decor(img_name, x, y, size):
            img = load_image(decor_dir / img_name)
            return EnvironmentDecoration(img, x, y, size)

        # Trees: large background decorations drawn behind tiles/entities
        self.background_trees = [
            make_decor("tree_01.png", int(2.5 * TILE_SIZE),  floor_y, (200, 260)),
            make_decor("tree_02.png", int(10.5 * TILE_SIZE), floor_y, (200, 260)),
            make_decor("tree_01.png", int(18.5 * TILE_SIZE), upper_y, (200, 260)),
            make_decor("tree_02.png", int(28.5 * TILE_SIZE), upper_y, (200, 260)),
            make_decor("tree_01.png", int(40.5 * TILE_SIZE), upper_y, (200, 260)),  # new
            make_decor("tree_02.png", int(50.5 * TILE_SIZE), floor_y, (200, 260)),  # new
        ]

        # Foreground decorations: drawn on top of tiles but behind players/enemies
        self.foreground_decorations = [
            # Bushes
            make_decor("bush_01.png", int(3.5 * TILE_SIZE),  floor_y, (64, 48)),
            make_decor("bush_02.png", int(8.5 * TILE_SIZE),  floor_y, (64, 48)),
            make_decor("bush_03.png", int(17.5 * TILE_SIZE), upper_y, (64, 48)),
            make_decor("bush_01.png", int(27.5 * TILE_SIZE), upper_y, (64, 48)),
            make_decor("bush_03.png", int(41.5 * TILE_SIZE), upper_y, (64, 48)),  # new
            make_decor("bush_02.png", int(48.5 * TILE_SIZE), floor_y, (64, 48)),  # new
            # Rocks
            make_decor("rock_01.png", int(5.5 * TILE_SIZE),  floor_y, (60, 40)),
            make_decor("rock_02.png", int(19.5 * TILE_SIZE), upper_y, (60, 40)),
            make_decor("rock_03.png", int(37.5 * TILE_SIZE), upper_y, (60, 40)),  # new
            make_decor("rock_01.png", int(46.5 * TILE_SIZE), floor_y, (60, 40)),  # new
            # Fences
            make_decor("fence.png", int(11.5 * TILE_SIZE), floor_y, (64, 40)),
            make_decor("fence.png", int(29.5 * TILE_SIZE), upper_y, (64, 40)),
            make_decor("fence.png", int(43.5 * TILE_SIZE), upper_y, (64, 40)),  # new
            # Signposts
            make_decor("signpost.png", int(6.2 * TILE_SIZE),  floor_y, (48, 64)),
            make_decor("signpost.png", int(25.5 * TILE_SIZE), upper_y, (48, 64)),
        ]

    def update(self, dt, keys):
        if self.in_dialogue:
            # Dialogue active: pause physics, player, and enemy updates.
            # Only update camera, particles, and transitions.
            self.particles.update(dt)
            self.camera.update(self.player.rect)
            
            # Advancing dialogue
            current_press = keys[pygame.K_RETURN] or keys[pygame.K_SPACE]
            if current_press and not self.prev_dialogue_press:
                self.dialogue_index += 1
                if self.dialogue_index >= len(self.dialogue_lines):
                    self.in_dialogue = False
                    self.dialogue_finished = True
            self.prev_dialogue_press = current_press
            return

        super().update(dt, keys)

    def update_scene(self, dt):
        self.checkpoint.update(dt)
        if self.checkpoint.check_activate(self.player):
            self.respawn_point = self.checkpoint.rect.midbottom

        if self.tutorial_timer > 0:
            self.tutorial_timer = max(0.0, self.tutorial_timer - dt)

        # Emit ambient leaves at the top of the screen (about 12% chance per frame)
        if random.random() < 0.12:
            cam_x = self.camera.offset_x
            cam_y = self.camera.offset_y
            self.particles.emit_ambient_leaves(
                x_range=(cam_x - 100, cam_x + SCREEN_W + 100),
                y=cam_y - 20,
                count=1
            )

        # Animate rain — two parallax layers when in wind zone
        if self._in_wind_zone:
            # Foreground: fast, blown hard sideways
            self._rain_fg = [
                ((x - random.randint(4, 8)) % SCREEN_W, (y + random.randint(6, 12)) % SCREEN_H)
                for x, y in self._rain_fg
            ]
            # Background: slower, more vertical
            self._rain_bg = [
                ((x - random.randint(1, 3)) % SCREEN_W, (y + random.randint(2, 5)) % SCREEN_H)
                for x, y in self._rain_bg
            ]
            # Spawn wind speed-streaks from the right edge
            if random.random() < 0.25:
                self._wind_streaks.append([
                    float(SCREEN_W + random.randint(0, 80)),  # x — off right edge
                    float(random.randint(0, SCREEN_H)),        # y
                    random.randint(60, 180),                   # length
                    random.uniform(500, 900),                  # speed px/s
                    random.randint(60, 150),                   # alpha
                ])
            # Move streaks leftward and remove those that left the screen
            for s in self._wind_streaks:
                s[0] -= s[3] * dt
            self._wind_streaks = [s for s in self._wind_streaks if s[0] + s[2] > 0]
        else:
            self._wind_streaks.clear()

        # Lightning flashes during boss fight
        if self.boss_spawned and not self.boss.is_dead:
            self._lightning_timer -= dt
            if self._lightning_timer <= 0:
                self._lightning_alpha = 200.0
                self._lightning_timer = random.uniform(4.0, 9.0)
                self._lightning_bolt  = self._generate_lightning_bolt()
        if self._lightning_alpha > 0:
            self._lightning_alpha = max(0.0, self._lightning_alpha - 400 * dt)

        # Check Stalker Root emergence for explosive soil burst particle effect
        for enemy in self.enemies:
            if isinstance(enemy, StalkerRoot) and enemy.take_pending_emergence():
                self.particles.emit_soil_burst(enemy.rect.midbottom, count=18)

        # Spawn chest once the first stalker root is defeated
        if self.first_stalker.is_dead and not self.chest_spawned:
            floor_y = FLOOR_ROW * TILE_SIZE
            self.chest = Chest(self.first_stalker.rect.centerx, floor_y)
            self.chest_spawned = True
            self.particles.emit_soil_burst(self.chest.rect.center, count=20)

        # Update chest interaction to unlock whip and show non-pausing tutorial toast
        if self.chest is not None:
            if self.chest.check_open(self.player):
                self.tutorial_text = "Tendril Whip Unlocked! Press [X] in mid-air to grapple green vine walls."
                self.tutorial_timer = 6.5

        # Check if all regular enemies are defeated
        regular_enemies = [e for e in self.enemies if e is not self.boss]
        
        # Trigger boss encounter when minions are dead and player enters boss arena
        if len(regular_enemies) == 0 and not self.boss_spawned:
            if self.player.rect.centerx >= 44 * TILE_SIZE:
                self.enemies.append(self.boss)
                self.boss_spawned = True
                self.dialogue_lines = [
                    ("Sky Wisp", "Intruder! Why do you climb the ancient branches of Skybloom?"),
                    ("Iris", "I seek the second Lumen Shard to bloom this dying world."),
                    ("Sky Wisp", "The shard belongs to the winds of the canopy! Begone, or face my wrath!"),
                ]
                self.in_dialogue = True
                self.dialogue_index = 0
                self.prev_dialogue_press = True # Prevent skipping on first frame

        # Apply hazards/boss actions only when not in dialogue
        if not self.in_dialogue:
            self._apply_wind_gust(dt)
            if self.boss_spawned:
                if self.boss.take_pending_summon():
                    self._summon_briarlings()
                # Dive impact → screen shake + shockwave ring
                impact_pos = self.boss.take_pending_dive_impact()
                if impact_pos is not None:
                    self._on_boss_dive_impact(impact_pos)

        self._update_shockwaves(dt)
        self._check_fall_death()

        # Spawn the shard once the boss is defeated
        if self.boss_spawned and self.boss.is_dead and self.boss.death_anim_done:
            # Feather rain fires exactly once when the boss death animation ends
            if not self._feathers_emitted:
                self.particles.emit_feathers(self.boss.rect.center, count=30)
                self._feathers_emitted = True
            if self.shard not in self.collectibles:
                self.collectibles.append(self.shard)
                self.particles.emit_petals(self.shard.rect.center, count=30)

    def _apply_wind_gust(self, dt):
        zone1_start = WIND_ZONE_COLS.start * TILE_SIZE
        zone1_end = WIND_ZONE_COLS.stop * TILE_SIZE
        in_zone1 = (zone1_start <= self.player.rect.centerx <= zone1_end)

        zone2_start = WIND_ZONE_2_COLS.start * TILE_SIZE
        zone2_end = WIND_ZONE_2_COLS.stop * TILE_SIZE
        in_zone2 = (zone2_start <= self.player.rect.centerx <= zone2_end)

        self._in_wind_zone = in_zone1 or in_zone2
        if self._in_wind_zone:
            self.player.rect.x -= int(WIND_PUSH_SPEED * dt)
            # Resolve collisions with solids to prevent clipping through walls
            solid_rects = self.tilemap.get_solid_rects() + [p.rect for p in self.platforms]
            for solid in solid_rects:
                if self.player.rect.colliderect(solid):
                    self.player.rect.left = solid.right
            # Leaves blown sideways
            emitter_x = zone1_end if in_zone1 else zone2_end
            if random.random() < 0.3:
                self.particles.emit_wind_leaves(
                    x=emitter_x, y_range=(self.player.rect.y - 100, self.player.rect.y + 50)
                )
            # Heavier debris chunks blown with the leaves
            if random.random() < 0.15:
                self.particles.emit_debris(
                    x=emitter_x, y_range=(self.player.rect.y - 80, self.player.rect.y + 40)
                )

    def _on_boss_dive_impact(self, impact_pos):
        """Triggered once per dive landing: screen shake + purple/gold shockwave ring."""
        self.screen_shake.trigger(duration=0.25, magnitude=7)
        self.shockwaves.append(Shockwave(
            impact_pos, max_radius=180,
            color=(200, 160, 240),  # soft purple to match Sky Wisp's colour
        ))

    def _update_shockwaves(self, dt):
        for shockwave in self.shockwaves:
            shockwave.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.alive]

    def _check_fall_death(self):
        if not self.player.is_dead and self.player.rect.top > self.fall_death_y:
            self.player.hp = 0
            self.player.is_dead = True

    def _generate_lightning_bolt(self):
        """Build a random jagged zigzag bolt path from the top of the screen
        down to about 65% of screen height — looks like a real cloud-to-ground
        strike rather than a full-screen line."""
        pts = []
        x = random.randint(SCREEN_W // 4, 3 * SCREEN_W // 4)
        y = 0
        pts.append((x, y))
        while y < int(SCREEN_H * 0.65):
            x = max(40, min(SCREEN_W - 40, x + random.randint(-55, 55)))
            y += random.randint(25, 65)
            pts.append((x, y))
        return pts

    def _summon_briarlings(self):
        spawn_x = self.boss.rect.centerx
        floor_y = FLOOR_ROW * TILE_SIZE
        for offset in (-2, 2):
            self.enemies.append(Briarling(
                x=spawn_x + offset * TILE_SIZE, y=floor_y,
                patrol_left=spawn_x - 4 * TILE_SIZE, patrol_right=spawn_x + 4 * TILE_SIZE,
            ))

    def _draw_background(self, surface, offset):
        # 1. Draw standard background layers
        super()._draw_background(surface, offset)
        # 2. Draw background trees (behind tiles)
        for tree in self.background_trees:
            tree.draw(surface, offset)

    def draw_scene(self, surface, camera_offset):
        # Draw foreground decorations
        for decor in self.foreground_decorations:
            decor.draw(surface, camera_offset)

        self.checkpoint.draw(surface, camera_offset)
        if self.chest is not None:
            self.chest.draw(surface, camera_offset)

        # Draw shockwave rings from boss dive impacts
        for shockwave in self.shockwaves:
            shockwave.draw(surface, camera_offset)

        # Storm effects when Iris is in the wind zone
        if self._in_wind_zone:
            # 1. Dark storm overlay
            storm_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            storm_surf.fill((20, 20, 40, 90))
            surface.blit(storm_surf, (0, 0))

            # 2. Background rain — dim, short, drifts slowly
            for rx, ry in self._rain_bg:
                pygame.draw.line(surface, (90, 120, 155),
                                 (int(rx), int(ry)), (int(rx) - 6, int(ry) + 9), 1)

            # 3. Wind speed-streaks — fast horizontal lines (anime speed-line style)
            if self._wind_streaks:
                streak_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                for s in self._wind_streaks:
                    sx, sy, slen = int(s[0]), int(s[1]), int(s[2])
                    salpha = int(s[4])
                    ex = min(sx + slen, SCREEN_W)
                    if ex > 0:
                        pygame.draw.line(streak_surf, (220, 230, 255, salpha),
                                         (max(0, sx), sy), (ex, sy), 1)
                surface.blit(streak_surf, (0, 0))

            # 4. Foreground rain — bright, long, blown hard sideways
            for rx, ry in self._rain_fg:
                pygame.draw.line(surface, (160, 190, 220),
                                 (int(rx), int(ry)), (int(rx) - 14, int(ry) + 20), 1)

        # Lightning — real jagged bolt + ambient flash
        if self._lightning_alpha > 0:
            bolt_alpha = int(self._lightning_alpha)
            if self._lightning_bolt:
                bolt_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                # Outer glow: wide, faint blue-white halo
                for i in range(len(self._lightning_bolt) - 1):
                    p1, p2 = self._lightning_bolt[i], self._lightning_bolt[i + 1]
                    pygame.draw.line(bolt_surf, (180, 210, 255, bolt_alpha // 4), p1, p2, 10)
                # Inner core: sharp, bright white
                for i in range(len(self._lightning_bolt) - 1):
                    p1, p2 = self._lightning_bolt[i], self._lightning_bolt[i + 1]
                    pygame.draw.line(bolt_surf, (255, 255, 255, bolt_alpha), p1, p2, 2)
                surface.blit(bolt_surf, (0, 0))
            # Ambient screen flash behind the bolt
            flash_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, bolt_alpha // 4))
            surface.blit(flash_surf, (0, 0))

        # Only draw health bar when spawned, active (not in dialogue), and not dead
        if self.boss_spawned and not self.in_dialogue and not self.boss.death_anim_done:
            self.boss.draw_health_bar(surface)

        # Draw dialogue overlay
        if self.in_dialogue:
            self._draw_dialogue(surface)

        # Draw tutorial toast if active
        if self.tutorial_timer > 0:
            self._draw_tutorial_toast(surface)

    def _draw_tutorial_toast(self, surface):
        toast_w, toast_h = 750, 48
        toast_x = (SCREEN_W - toast_w) // 2
        toast_y = 70
        
        toast_surface = pygame.Surface((toast_w, toast_h), pygame.SRCALPHA)
        # Deep forest green and golden theme
        toast_surface.fill((15, 25, 15, 220))
        pygame.draw.rect(toast_surface, (255, 215, 100), (0, 0, toast_w, toast_h), 2)
        
        font = pygame.font.Font(None, 24)
        text_surf = font.render(self.tutorial_text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(toast_w // 2, toast_h // 2))
        toast_surface.blit(text_surf, text_rect)
        
        surface.blit(toast_surface, (toast_x, toast_y))

    def _draw_dialogue(self, surface):
        speaker, text = self.dialogue_lines[self.dialogue_index]
        
        # Semi-transparent dark blue container box
        dialogue_surface = pygame.Surface((1080, 140), pygame.SRCALPHA)
        dialogue_surface.fill((15, 15, 25, 230))
        
        # Golden border
        pygame.draw.rect(dialogue_surface, (255, 215, 100), (0, 0, 1080, 140), 2)
        
        # Speaker Name
        speaker_font = pygame.font.Font(None, 36)
        speaker_surf = speaker_font.render(speaker, True, (255, 215, 100))
        dialogue_surface.blit(speaker_surf, (20, 15))
        
        # Speech text
        text_font = pygame.font.Font(None, 28)
        text_surf = text_font.render(text, True, (255, 255, 255))
        dialogue_surface.blit(text_surf, (20, 55))
        
        # Progress prompt
        prompt_font = pygame.font.Font(None, 20)
        prompt_surf = prompt_font.render("Press [ENTER] or [SPACE] to advance...", True, (160, 160, 160))
        dialogue_surface.blit(prompt_surf, (1080 - prompt_surf.get_width() - 20, 140 - 25))
        
        # Position centered horizontally at the bottom of the screen
        surface.blit(dialogue_surface, (100, 720 - 180))

    def on_collect(self, collectible):
        if collectible is self.shard:
            self.finished = True

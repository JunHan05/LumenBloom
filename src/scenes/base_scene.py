"""
base_scene.py

Shared lifecycle every scene follows: handle_event(), update(), draw().
Owns the common systems (tilemap, camera, HUD, particles, projectiles,
screen shake, scene-complete wipe) so each scene file only has to
describe its own layout, enemies, hazards, and events.

Subclass this for every scene (scene1_grotto.py etc.):
    - build entities/hazards/platforms/collectibles in __init__
    - override update_scene(dt) / draw_scene(surface, offset) for
      anything specific to that scene
    - override on_collect(collectible) to react to pickups (e.g. ending
      the scene when the Lumen Shard is collected)
"""

import pygame

from config.settings import SCREEN_W, SCREEN_H, TILE_SIZE, FALL_DEATH_MARGIN
from src.entities.player import TENDRIL_ENEMY_PULL_SPEED, TENDRIL_ENEMY_PULL_DURATION
from src.core.camera import Camera
from src.world.tilemap import TileMap
from src.ui.hud import HUD
from src.effects.particles import ParticleSystem
from src.effects.transitions import ScreenShake, WipeTransition


class BaseScene:
    def __init__(self, player, background_layers, tilemap_grid, tileset_filename, level_width,
                 level_height=None):
        self.player = player
        self.background_layers = background_layers  # list of (image, scroll_factor)
        self.tilemap = TileMap(tilemap_grid, tileset_filename)
        # level_height defaults to a single screen (no vertical scroll) —
        # Scenes 1/2 are purely horizontal. Scene 3's vertical shaft
        # passes a taller value so Camera.update() also tracks Iris's Y.
        self.camera = Camera(level_width, level_height or SCREEN_H)
        self.hud = HUD()
        self.particles = ParticleSystem()
        self.screen_shake = ScreenShake()
        self.camera.shake = self.screen_shake
        self.transition = WipeTransition(duration=0.6)

        # A generic "fell off the map" line, well below the level grid's
        # own bottom row — so a missed jump into a bottomless gap costs a
        # life instead of leaving Iris falling forever (PROJECT_BRIEF.md
        # section 4). Every scene gets this for free; no per-scene setup.
        self.fall_death_y = len(tilemap_grid) * TILE_SIZE + FALL_DEATH_MARGIN

        self.platforms = []
        self.hazards = []
        self.enemies = []
        self.collectibles = []
        self.projectiles = []

        self.finished = False  # set True once the scene's goal is complete

    # --- Input -----------------------------------------------------------

    def handle_event(self, event):
        """Event-based actions (single key-press abilities). Continuous
        movement/crouch is read directly from key state inside
        Player.update(), so it doesn't need an event here."""
        if event.type == pygame.KEYDOWN and not self.player.is_dead and not self.player.hurt:
            if event.key == pygame.K_SPACE:
                self._on_glow_slash()
            elif event.key == pygame.K_z:
                self._on_pollen_burst()
            elif event.key == pygame.K_x:
                self._on_tendril_whip()
            elif event.key in (pygame.K_w, pygame.K_UP):
                self.player.jump()
        self.handle_scene_event(event)

    def handle_scene_event(self, event):
        """Override for scene-specific input. Most scenes won't need this."""
        pass

    def _on_glow_slash(self):
        hitbox, damage = self.player.glow_slash()
        for enemy in self.enemies:
            if not enemy.is_dead and hitbox.colliderect(enemy.rect):
                enemy.take_damage(damage)
        self.on_glow_slash_hit(hitbox, damage)

    def _on_pollen_burst(self):
        result = self.player.pollen_burst()
        if result is None:
            return
        center, radius, damage = result
        self.particles.emit_pollen_burst(center)
        for enemy in self.enemies:
            if enemy.is_dead:
                continue
            dx = enemy.rect.centerx - center[0]
            dy = enemy.rect.centery - center[1]
            if (dx * dx + dy * dy) ** 0.5 <= radius:
                enemy.take_damage(damage)
        self.on_pollen_burst_hit(center, radius, damage)

    def on_glow_slash_hit(self, hitbox, damage):
        """Override to react to a Glow Slash hit against something that
        isn't a regular enemy (e.g. Scene 3's vine switches and Murk
        Spore clusters)."""
        pass

    def on_pollen_burst_hit(self, center, radius, damage):
        """Override to react to a Pollen Burst hit against something
        that isn't a regular enemy."""
        pass

    def _on_tendril_whip(self):
        """Resolve a Tendril Whip probe: an enemy in the way gets pulled
        toward Iris; otherwise the nearest solid surface along the line
        becomes a swing anchor (PROJECT_BRIEF.md section 4)."""
        result = self.player.tendril_whip()
        if result is None:
            return
        start, end = result

        for enemy in self.enemies:
            if not enemy.is_dead and enemy.rect.clipline(start, end):
                enemy.apply_pull(self.player.rect.center, TENDRIL_ENEMY_PULL_SPEED,
                                  TENDRIL_ENEMY_PULL_DURATION)
                return

        solid_rects = self.tilemap.get_solid_rects() + [p.rect for p in self.platforms]
        closest_point = None
        closest_distance = None
        for rect in solid_rects:
            clipped = rect.clipline(start, end)
            if not clipped:
                continue
            for point in clipped:
                distance = (point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2
                if closest_distance is None or distance < closest_distance:
                    closest_distance = distance
                    closest_point = point

        if closest_point is not None:
            self.player.start_tendril_swing(closest_point)

    # --- Update ------------------------------------------------------------

    def update(self, dt, keys):
        """keys: the result of pygame.key.get_pressed(), read once by the
        game loop and passed in here — kept as a parameter (rather than
        read internally) so scenes are as easy to drive with simulated
        input in tests as Player.update() already is."""
        # 1. Update platforms first and track how much they shifted
        platform_deltas = {}
        for platform in self.platforms:
            old_x, old_y = platform.rect.x, platform.rect.y
            platform.update(dt, self.player.rect)
            platform_deltas[platform] = (platform.rect.x - old_x, platform.rect.y - old_y)

        # 2. Shift player horizontally/vertically if standing on a moving platform.
        # Requires the player's *center* over the platform (not just any
        # edge overlap) and an almost-exact vertical match — a loose edge
        # check here false-triggers the instant Iris merely grazes a
        # platform's corner while she's actually still resting on
        # adjacent solid ground at the same height (e.g. the floor tile
        # right next to a sinking platform). That falsely nudges her by
        # the platform's tiny per-frame delta, which is just enough to
        # push her into the floor tile she's already standing on —
        # Player._move_and_collide() then reads that as a horizontal wall
        # bump and snaps her all the way back to that tile's far edge.
        for platform, (dx, dy) in platform_deltas.items():
            standing_on = (
                self.player.on_ground
                and abs(self.player.rect.bottom - platform.rect.top) <= 1
                and platform.rect.left <= self.player.rect.centerx <= platform.rect.right
            )
            if standing_on:
                self.player.rect.x += dx
                self.player.rect.y += dy
                break

        # 3. Now compile the updated solid rects and update the player
        solid_rects = self.tilemap.get_solid_rects() + [p.rect for p in self.platforms]
        self.player.update(dt, keys, solid_rects)
        self._check_fall_death()
        self.tilemap.update(dt)

        for hazard in self.hazards:
            hazard.update(dt)
            hazard.apply_damage(self.player, dt)
            if hasattr(hazard, "take_pending_projectile"):
                projectile = hazard.take_pending_projectile()
                if projectile is not None:
                    self.projectiles.append(projectile)

        self._update_enemies(dt, solid_rects)
        self._update_projectiles(dt, solid_rects)

        for collectible in self.collectibles:
            collectible.update(dt)
        self._check_pickups()

        self.particles.update(dt)
        self.screen_shake.update(dt)
        self.camera.update(self.player.rect)

        if self.finished:
            self.transition.update(dt)

        self.update_scene(dt)

    def _check_fall_death(self):
        if not self.player.is_dead and self.player.rect.top > self.fall_death_y:
            self.player.hp = 0
            self.player.is_dead = True

    def _update_enemies(self, dt, solid_rects):
        for enemy in self.enemies:
            enemy.update(dt, self.player)
            enemy.check_contact_damage(self.player)

            if hasattr(enemy, "take_pending_projectile"):
                projectile = enemy.take_pending_projectile()
                if projectile is not None:
                    self.projectiles.append(projectile)
                    if hasattr(self.particles, "emit_thorn_launch") and hasattr(enemy, "facing_right"):
                        self.particles.emit_thorn_launch(projectile.rect.center, enemy.facing_right)

        # Remove enemies once dead AND their death animation has finished
        # (enemies without a death_anim_done flag are removed immediately).
        self.enemies = [e for e in self.enemies if not (e.is_dead and getattr(e, "death_anim_done", True))]

    def _update_projectiles(self, dt, solid_rects):
        for projectile in self.projectiles:
            projectile.update(dt, solid_rects)
            projectile.check_hit_player(self.player)
        self.projectiles = [p for p in self.projectiles if not p.spent]

    def _check_pickups(self):
        for collectible in self.collectibles:
            if collectible.check_pickup(self.player):
                if hasattr(collectible, "apply"):
                    collectible.apply(self.player)
                self.on_collect(collectible)

    def on_collect(self, collectible):
        """Override for scene-specific reactions to a pickup."""
        pass

    def update_scene(self, dt):
        """Override for anything specific to a scene."""
        pass

    # --- Draw --------------------------------------------------------------

    def draw(self, surface):
        offset = self.camera.get_offset()

        self._draw_background(surface, offset)
        self.tilemap.draw(surface, offset)
        for hazard in self.hazards:
            hazard.draw(surface, offset)
        for platform in self.platforms:
            platform.draw(surface, offset)
        for collectible in self.collectibles:
            collectible.draw(surface, offset)
        for enemy in self.enemies:
            enemy.draw(surface, offset)
        for projectile in self.projectiles:
            projectile.draw(surface, offset)
        self.player.draw(surface, offset)
        self.particles.draw(surface, offset)

        self.draw_scene(surface, offset)

        # murk_meter is only set by scenes that need it (Scene 3 sets
        # self.murk_meter in __init__; Scenes 1/2 leave it unset).
        # cutscene_active is only set by Scene 4 — hides the HP bar/lives/
        # cooldowns/Murk Meter from drawing on top of its opening comet-
        # strike flashback, which otherwise has nothing else on screen.
        if not getattr(self, "cutscene_active", False):
            self.hud.draw(surface, self.player, murk_meter=getattr(self, "murk_meter", None))

        if self.finished:
            self.transition.draw(surface)

    def _draw_background(self, surface, offset):
        """Tile each parallax layer however many times are needed to
        cover the screen width — real art may be wide, but a missing-
        asset placeholder is small, so a fixed two-copy blit wouldn't
        reliably cover the screen."""
        for image, scroll_factor in self.background_layers:
            layer_width = image.get_width()
            scroll_x = int(offset[0] * scroll_factor) % layer_width
            x = -scroll_x
            while x < SCREEN_W:
                surface.blit(image, (x, 0))
                x += layer_width

    def draw_scene(self, surface, camera_offset):
        """Override for anything drawn specific to a scene (e.g. a boss
        health bar, the Murk Meter)."""
        pass

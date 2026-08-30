"""
tilemap.py

Builds a level's solid geometry from a simple text grid of characters,
exposes collision rects, and implements the floor-fracture tile state
machine (Section 6: a boss ground-slam cracks nearby tiles, which break
after a delay and drop Iris through).

Grid legend (one character per tile):
    '.'  empty space (no tile)
    '#'  solid ground/wall tile
    'X'  fracturable solid tile — solid until cracked, then breaks away
"""

from pathlib import Path

import pygame

from config.settings import TILE_SIZE, FLOOR_FRACTURE_DELAY, TILES_IMG_DIR
from src.core.asset_loader import load_animation_frames

EMPTY = "."
SOLID = "#"
FRACTURABLE = "X"


class FracturableTile:
    """A single fracturable tile's state machine: solid -> cracked -> broken."""

    def __init__(self, grid_x, grid_y):
        self.rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.cracked = False
        self.broken = False
        self.crack_timer = 0.0

    def crack(self):
        """Start the fracture countdown (called when a boss slam lands nearby)."""
        if not self.broken:
            self.cracked = True
            self.crack_timer = 0.0

    def update(self, dt):
        if self.cracked and not self.broken:
            self.crack_timer += dt
            if self.crack_timer >= FLOOR_FRACTURE_DELAY:
                self.broken = True


class TileMap:
    """Loads a tileset image and builds a level's collision geometry from a
    list of equal-length strings (the level grid)."""

    def __init__(self, grid, tileset_filename):
        self.grid = grid
        self.solid_tiles = []        # plain "#" tiles: rects that never change
        self.fracturable_tiles = {}  # (grid_x, grid_y) -> FracturableTile
        # Cosmetic-only override: solid tiles at these (grid_x, grid_y)
        # draw with the cracked tile art this frame, no collision or
        # durability change — see set_temp_cracked_positions().
        self.temp_cracked_positions = set()

        # A scene whose land is painted into its background art (e.g.
        # Scene 4) passes a grid with no '#'/'X' at all — nothing would
        # ever be drawn from a tileset, so skip loading one entirely
        # rather than requiring an unused tileset image file to exist.
        has_tiles = any(SOLID in row or FRACTURABLE in row for row in grid)
        if not has_tiles:
            self.solid_image = None
            self.cracked_image = None
            return

        # Each tileset is [solid_tile, cracked_tile] (PROJECT_BRIEF.md
        # section 9). Prefers separate tile files (grotto_tileset_1.png =
        # solid, _2.png = cracked) over a single sliced sheet — see
        # asset_loader.load_animation_frames().
        tileset_base_name = Path(tileset_filename).stem
        self.solid_image, self.cracked_image = load_animation_frames(
            TILES_IMG_DIR, tileset_base_name, 2, size=(TILE_SIZE, TILE_SIZE)
        )

        for row_index, row in enumerate(grid):
            for col_index, symbol in enumerate(row):
                if symbol == SOLID:
                    rect = pygame.Rect(
                        col_index * TILE_SIZE, row_index * TILE_SIZE, TILE_SIZE, TILE_SIZE
                    )
                    self.solid_tiles.append(rect)
                elif symbol == FRACTURABLE:
                    self.fracturable_tiles[(col_index, row_index)] = FracturableTile(
                        col_index, row_index
                    )

    def crack_tiles_near(self, grid_x, grid_y, radius=1):
        """Start the fracture countdown on fracturable tiles within
        `radius` tiles of (grid_x, grid_y) — called by a boss ground-slam."""
        for (tx, ty), tile in self.fracturable_tiles.items():
            if abs(tx - grid_x) <= radius and abs(ty - grid_y) <= radius:
                tile.crack()

    def set_temp_cracked_positions(self, positions):
        """Replace the set of solid tiles drawn with the cracked art this
        frame. Wholesale replacement rather than merging, so a tile reverts
        to its normal look on the very next frame it's no longer included —
        used by Bug Boss's ground shockwave (Stomp) to make the floor look
        like it's cracking under the wave's own path as it travels, with
        no lasting effect once it's passed (unlike 'X' tiles, which crack
        permanently and eventually break)."""
        self.temp_cracked_positions = positions

    def open_gate_at(self, grid_x, grid_y):
        """Remove a plain solid tile from collision — used for sealed
        gates that open once a mini-boss/boss guarding them is defeated."""
        rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        if rect in self.solid_tiles:
            self.solid_tiles.remove(rect)

    def close_gate_at(self, grid_x, grid_y):
        """Inverse of open_gate_at() — adds a solid tile back. Used to
        seal an arena entrance behind Iris once a boss wakes up, so a
        fight already in progress can't just be walked away from."""
        rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        if rect not in self.solid_tiles:
            self.solid_tiles.append(rect)

    def update(self, dt):
        for tile in self.fracturable_tiles.values():
            tile.update(dt)

    def get_solid_rects(self):
        """All rects Iris/enemies currently collide with: permanent solid
        tiles plus any fracturable tiles that haven't broken yet."""
        rects = list(self.solid_tiles)
        for tile in self.fracturable_tiles.values():
            if not tile.broken:
                rects.append(tile.rect)
        return rects

    def draw(self, surface, camera_offset=(0, 0)):
        for rect in self.solid_tiles:
            grid_pos = (rect.x // TILE_SIZE, rect.y // TILE_SIZE)
            image = self.cracked_image if grid_pos in self.temp_cracked_positions else self.solid_image
            surface.blit(image, (rect.x - camera_offset[0], rect.y - camera_offset[1]))

        for tile in self.fracturable_tiles.values():
            if tile.broken:
                continue
            image = self.cracked_image if tile.cracked else self.solid_image
            surface.blit(image, (tile.rect.x - camera_offset[0], tile.rect.y - camera_offset[1]))

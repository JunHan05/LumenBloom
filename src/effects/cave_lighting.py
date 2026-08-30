"""
cave_lighting.py

A Hollow Knight-style darkness vignette with a soft light halo that
follows Iris — Scene 1's "cave lit by glowing fungi" setting
(PROJECT_BRIEF.md section 5). Its overall darkness reacts to how
enclosed the space around her currently is: tight tunnels read darker
(a small pool of light in near-total black), open rooms read lighter
(still moody, but with more of the surroundings visible), matching a
low-ceilinged corridor vs. a tall cavern. Generated directly with
pygame/numpy at runtime, no image asset — same "no external art"
approach as Shockwave.
"""

import numpy as np
import pygame

from config.settings import SCREEN_W, SCREEN_H, TILE_SIZE

LIGHT_DIAMETER = 560
LIGHT_RADIUS = LIGHT_DIAMETER // 2

# Open space around Iris (up/left/right, in tiles — see _openness()),
# capped at MAX so a tall shaft doesn't read as "open" the instant her
# head clears the one tile directly overhead.
MIN_CLEARANCE_TILES = 2   # at/below this: fully enclosed, darkest
MAX_CLEARANCE_TILES = 7   # at/above this: fully open, lightest

DARKEST_ALPHA = 230   # enclosed spaces — a small pool of light in near-total black
LIGHTEST_ALPHA = 120  # open spaces — still dim/moody, just far more visible
SMOOTH_SPEED = 2.5     # how fast darkness eases toward its target, per second


def _build_keep_mask():
    """A soft radial mask: fully transparent (alpha 0) at the center,
    smoothstep-rising to fully opaque (alpha 255) at the edge —
    multiplied into the darkness overlay's alpha channel each frame
    (BLEND_RGBA_MULT) to punch a glowing hole around Iris.

    This replaces an earlier BLEND_RGBA_SUB approach that had a real
    bug: SUB subtracts R, G, B, and A as four independent channels
    without weighting RGB by the source's own alpha first. Since the
    darkness fill's blue channel is 10 (not 0) and this gradient's RGB
    was uniformly white, every pixel inside the gradient's square
    canvas — not just the visible circle — got its blue channel forced
    toward 0, while pixels just *outside* that square kept the true
    value of 10. That mismatch showed up as a real, visible rectangular
    seam at the edge of the gradient's own canvas. MULT avoids this
    entirely: multiplying the darkness's blue value by this mask's
    alpha only ever *scales* it smoothly toward 0, so there's no
    channel that can end up inconsistent at the canvas edge."""
    yy, xx = np.mgrid[0:LIGHT_DIAMETER, 0:LIGHT_DIAMETER]
    dist = np.sqrt((xx - LIGHT_RADIUS) ** 2 + (yy - LIGHT_RADIUS) ** 2) / LIGHT_RADIUS
    dist = np.clip(dist, 0.0, 1.0)
    t = dist  # 0 at center, 1 at edge
    alpha = (t * t * (3 - 2 * t) * 255).astype(np.uint8)  # smoothstep

    arr = np.full((LIGHT_DIAMETER, LIGHT_DIAMETER, 4), 255, dtype=np.uint8)
    arr[..., 3] = alpha
    return pygame.image.frombuffer(arr.tobytes(), (LIGHT_DIAMETER, LIGHT_DIAMETER), "RGBA").convert_alpha()


class CaveLighting:
    """Owns the darkness overlay + light halo. One instance per scene —
    call update() each frame with Iris's rect and the scene's TileMap,
    then draw() last (after everything else, before the HUD)."""

    def __init__(self):
        self._mask = _build_keep_mask()
        self._overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self.current_alpha = DARKEST_ALPHA

    def update(self, dt, player_rect, tilemap):
        openness = self._openness(player_rect, tilemap)
        span = MAX_CLEARANCE_TILES - MIN_CLEARANCE_TILES
        fraction = max(0.0, min(1.0, (openness - MIN_CLEARANCE_TILES) / span))
        target_alpha = DARKEST_ALPHA + (LIGHTEST_ALPHA - DARKEST_ALPHA) * fraction
        self.current_alpha += (target_alpha - self.current_alpha) * min(1.0, dt * SMOOTH_SPEED)

    @staticmethod
    def _openness(player_rect, tilemap):
        """How much breathing room Iris has where she's standing: the
        *smallest* of her clearance upward, leftward, and rightward
        (each capped at MAX_CLEARANCE_TILES). Just checking overhead
        isn't enough — Scene 1's collision grid has almost no actual
        ceiling tiles (the cave-roof look is background art, not
        collision), so a tight corridor boxed in by walls on either
        side would otherwise read as fully "open." Taking the minimum
        across all three directions means being hemmed in from *any*
        side reads as enclosed, the same way it would look to the eye."""
        grid = tilemap.grid
        if not grid:
            return MAX_CLEARANCE_TILES
        row = int(player_rect.centery // TILE_SIZE)
        col = int(player_rect.centerx // TILE_SIZE)
        if row < 0 or row >= len(grid) or col < 0 or col >= len(grid[0]):
            return MAX_CLEARANCE_TILES

        def clearance(drow, dcol):
            r, c = row, col
            n = 0
            while n < MAX_CLEARANCE_TILES:
                r += drow
                c += dcol
                if r < 0 or r >= len(grid) or c < 0 or c >= len(grid[0]):
                    break
                if grid[r][c] in ('#', 'X'):
                    break
                n += 1
            return n

        return min(clearance(-1, 0), clearance(0, -1), clearance(0, 1))

    def draw(self, surface, camera_offset, player_center):
        self._overlay.fill((0, 0, 10, int(self.current_alpha)))
        light_pos = (
            player_center[0] - camera_offset[0] - LIGHT_RADIUS,
            player_center[1] - camera_offset[1] - LIGHT_RADIUS,
        )
        self._overlay.blit(self._mask, light_pos, special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(self._overlay, (0, 0))

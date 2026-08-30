"""
Central settings for Lumen Bloom.

Every path, screen constant, colour, key binding, and gameplay number lives
here so the rest of the code never hard-codes a value or a file path.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# BASE PATHS
# ---------------------------------------------------------------------------
# BASE_DIR = the LumenBloom/ project root (this file lives in config/, so go
# up one level).
BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR = ASSETS_DIR / "audio"

# Image subfolders
PLAYER_IMG_DIR = IMAGES_DIR / "player"
ENEMIES_IMG_DIR = IMAGES_DIR / "enemies"
BOSSES_IMG_DIR = IMAGES_DIR / "bosses"
BACKGROUNDS_IMG_DIR = IMAGES_DIR / "backgrounds"
TILES_IMG_DIR = IMAGES_DIR / "tiles"
HAZARDS_IMG_DIR = IMAGES_DIR / "hazards"
OBJECTS_IMG_DIR = IMAGES_DIR / "objects"
EFFECTS_IMG_DIR = IMAGES_DIR / "effects"
UI_IMG_DIR = IMAGES_DIR / "ui"
OPENING_STORY_IMG_DIR = IMAGES_DIR / "opening_story"

# Audio subfolders
MUSIC_DIR = AUDIO_DIR / "music"
SFX_DIR = AUDIO_DIR / "sfx"

# ---------------------------------------------------------------------------
# SCREEN / TIMING
# ---------------------------------------------------------------------------
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
GAME_TITLE = "Lumen Bloom"

# ---------------------------------------------------------------------------
# COLOURS (used for placeholder rectangles, UI, debug drawing)
# ---------------------------------------------------------------------------
COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "sky": (135, 206, 235),
    "placeholder_pink": (255, 0, 200),   # missing-asset placeholder colour
    "placeholder_border": (0, 0, 0),
    "hp_green": (80, 200, 100),
    "hp_red": (200, 60, 60),
    "warn_orange": (230, 130, 40),
    "murk_purple": (120, 60, 160),
    "glow_gold": (255, 215, 100),
    "ui_bg": (20, 20, 30),
    "ui_border": (240, 240, 240),
}

# ---------------------------------------------------------------------------
# KEY BINDINGS (pygame key constants are looked up at import time inside
# game code that imports pygame; here we just describe the mapping in plain
# words so this file has zero pygame dependency).
# ---------------------------------------------------------------------------
# Movement:      LEFT / RIGHT arrows
# Jump:          W or UP arrow (press again mid-air = double jump)
# Crouch:        S or DOWN arrow
# Glow Slash:    SPACE
# Pollen Burst:  Z
# Tendril Whip:  X
# Lumen Bloom:   C

# ---------------------------------------------------------------------------
# GAMEPLAY CONSTANTS
# ---------------------------------------------------------------------------
GRAVITY = 0.9
MOVE_SPEED = 5
JUMP_STRENGTH = -16
DOUBLE_JUMP_STRENGTH = -12
MAX_FALL_SPEED = 20

TILE_SIZE = 64
FLOOR_FRACTURE_DELAY = 2.0  # seconds a cracked tile holds before it breaks

# How far below a level's grid a scene must fall before it counts as
# "off the map" and costs a life — enough margin that legitimate catch
# rows/pits within the grid never false-trigger it.
FALL_DEATH_MARGIN = 250

PLAYER_MAX_HP = 100
PLAYER_START_LIVES = 3

DEFAULT_MUSIC_VOLUME = 0.2   # Lowered background music volume (0.0 to 1.0)

POLLEN_BURST_COOLDOWN = 3.0   # seconds

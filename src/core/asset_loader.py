"""
asset_loader.py

Single place that loads every image and sound in the game. Scenes should
call these functions once when they start (never inside the game loop).

If a file is missing, we DO NOT crash. We print a clear console warning and
hand back a placeholder so development can continue before all art/audio is
finished (see PROJECT_BRIEF.md section 9).
"""

import pygame
from pathlib import Path

from config.settings import COLORS, DEFAULT_MUSIC_VOLUME

# Cache so the same file is never loaded twice from disk.
_image_cache = {}
_sound_cache = {}


def load_image(path: Path, size=None, colorkey=None):
    """
    Load a single image from disk.

    path:     full Path to the image file.
    size:     optional (width, height) to scale to.
    colorkey: optional (r, g, b) colour to treat as transparent, for sprite
              sheets that were exported with a solid background instead of
              real alpha transparency.

    Returns a pygame.Surface. If the file is missing, returns a labelled
    placeholder rectangle instead of crashing.
    """
    cache_key = (str(path), size, colorkey)
    if cache_key in _image_cache:
        return _image_cache[cache_key]

    if not path.exists():
        print(f"MISSING: {path}")
        surface = _make_placeholder_surface(size or (64, 64), path.stem)
        _image_cache[cache_key] = surface
        return surface

    try:
        image = pygame.image.load(str(path))
        if colorkey is not None:
            image = image.convert()
            image.set_colorkey(colorkey)
        else:
            image = image.convert_alpha()

        if size is not None:
            image = pygame.transform.scale(image, size)

        _image_cache[cache_key] = image
        return image

    except pygame.error as e:
        print(f"FAILED TO LOAD: {path} ({e})")
        surface = _make_placeholder_surface(size or (64, 64), path.stem)
        _image_cache[cache_key] = surface
        return surface


def load_spritesheet(path: Path, frame_count: int, size=None, colorkey=None):
    """
    Load a sprite sheet that is a single horizontal row of equally-sized
    frames, and slice it into a list of frame surfaces.

    path:         full Path to the sheet image.
    frame_count:  number of frames in the row.
    size:         optional (width, height) to scale every sliced frame to.
    colorkey:     optional (r, g, b) transparency colour key.

    Returns a list[pygame.Surface] of length frame_count. If the sheet is
    missing, returns frame_count placeholder rectangles instead.
    """
    if not path.exists():
        print(f"MISSING: {path}")
        return [_make_placeholder_surface(size or (64, 64), path.stem) for _ in range(frame_count)]

    try:
        sheet = pygame.image.load(str(path))
        if colorkey is not None:
            sheet = sheet.convert()
            sheet.set_colorkey(colorkey)
        else:
            sheet = sheet.convert_alpha()

        sheet_w, sheet_h = sheet.get_size()
        frame_w = sheet_w // frame_count
        frames = []
        for i in range(frame_count):
            rect = pygame.Rect(i * frame_w, 0, frame_w, sheet_h)
            frame = pygame.Surface((frame_w, sheet_h), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            if size is not None:
                frame = pygame.transform.scale(frame, size)
            frames.append(frame)
        return frames

    except pygame.error as e:
        print(f"FAILED TO LOAD: {path} ({e})")
        return [_make_placeholder_surface(size or (64, 64), path.stem) for _ in range(frame_count)]


def load_animation_frames(directory: Path, base_name: str, frame_count: int, size=None, colorkey=None):
    """
    Load one animation's frames, preferring separate numbered image files
    — base_name_1.png, base_name_2.png, ... base_name_{frame_count}.png —
    over a single combined sprite sheet.

    This matters for AI-generated art: an image generator produces one
    consistent illustration per request, but can't reliably lay multiple
    aligned poses into one horizontal strip. So each pose becomes its own
    file instead, each scaled to `size` independently.

    If none of the numbered files exist, falls back to slicing a single
    base_name.png sprite sheet (load_spritesheet) — for hand-made or
    purchased sheets that already come as one horizontal strip.

    Any numbered file that's missing still falls back to a labelled
    placeholder (via load_image), so an animation can be filled in one
    pose at a time.
    """
    numbered_paths = [directory / f"{base_name}_{i + 1}.png" for i in range(frame_count)]

    if any(p.exists() for p in numbered_paths):
        return [load_image(p, size=size, colorkey=colorkey) for p in numbered_paths]

    return load_spritesheet(directory / f"{base_name}.png", frame_count, size=size, colorkey=colorkey)


def load_sound(path: Path):
    """
    Load a sound effect. Returns a pygame.mixer.Sound, or None if the file
    is missing (callers should check for None before calling .play()).
    """
    cache_key = str(path)
    if cache_key in _sound_cache:
        return _sound_cache[cache_key]

    if not path.exists():
        print(f"MISSING: {path}")
        _sound_cache[cache_key] = None
        return None

    try:
        sound = pygame.mixer.Sound(str(path))
        _sound_cache[cache_key] = sound
        return sound
    except pygame.error as e:
        print(f"FAILED TO LOAD: {path} ({e})")
        _sound_cache[cache_key] = None
        return None


def play_sound(sound, volume=1.0, layers=1):
    """Play a Sound returned by load_sound() — a no-op if it's None (file
    missing/failed to load), so call sites never need their own `if
    sound:` guard. `volume` is 0.0-1.0, applied to this one playback.

    `layers` plays the same Sound on that many channels at once instead
    of one — pygame.mixer.Sound.set_volume() is already capped at 1.0,
    so once a clip is maxed out there's no more software gain to give it;
    stacking identical playbacks sums their amplitude in the mixer
    instead, which is the only way left to make an already-max-volume
    clip read as louder without re-exporting the file itself."""
    if sound is not None:
        sound.set_volume(volume)
        for _ in range(layers):
            sound.play()


def play_music(path: Path, loops=-1, volume=DEFAULT_MUSIC_VOLUME):
    """
    Load and play a looping (by default) background music track via
    pygame.mixer.music — a separate API from load_sound()/Sound objects,
    since pygame only streams one music track at a time rather than
    mixing many short Sounds. A no-op (with the same MISSING console
    warning as every other asset loader here) if the file doesn't exist,
    so scenes can call this unconditionally before any music has been
    sourced yet.
    """
    if not path.exists():
        print(f"MISSING: {path}")
        return

    try:
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loops)
    except pygame.error as e:
        print(f"FAILED TO LOAD: {path} ({e})")


def stop_music():
    """Stop whatever background music track is currently playing (safe
    to call even if none is playing)."""
    pygame.mixer.music.stop()


def _make_placeholder_surface(size, label):
    """Create a bright pink rectangle with a black border and a text label,
    so a missing asset is obvious on screen instead of invisible or crashing."""
    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(COLORS["placeholder_pink"])
    pygame.draw.rect(surface, COLORS["placeholder_border"], surface.get_rect(), 2)

    try:
        font = pygame.font.Font(None, 16)
        text = font.render(label[:10], True, COLORS["placeholder_border"])
        text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
        surface.blit(text, text_rect)
    except pygame.error:
        # Font module may not be initialised yet; the coloured rectangle
        # alone is still a fine fallback.
        pass

    return surface

"""
collectibles.py

Pickups and progress markers: Glow Orb, Lumen Shard, Lumen Token, and
the checkpoint gate (PROJECT_BRIEF.md section 7).
"""

import pygame

from config.settings import OBJECTS_IMG_DIR, SFX_DIR
from src.core.asset_loader import load_image, load_animation_frames, load_sound, play_sound

OBJECT_SIZE = (50, 32)
GATE_SIZE = (64, 64)


class Collectible(pygame.sprite.Sprite):
    """Base pickup: sits at a fixed spot, disappears once Iris touches it."""

    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))
        self.collected = False
        self._pickup_sound = load_sound(SFX_DIR / "pickup.wav")

    def check_pickup(self, player):
        if not self.collected and self.rect.colliderect(player.rect):
            self.collected = True
            play_sound(self._pickup_sound)
            return True
        return False

    def draw(self, surface, camera_offset=(0, 0)):
        if not self.collected:
            surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class AnimatedCollectible(Collectible):
    """A collectible that simply loops through its animation frames until
    picked up — Glow Orb, Lumen Token, and Lumen Shard all behave
    identically, only the art differs. Prefers separate numbered pose
    files (glow_orb_1.png, _2.png, ...) over a single sliced sheet — see
    asset_loader.load_animation_frames()."""

    FRAME_DURATION = 0.15

    def __init__(self, x, y, base_name, frame_count=4, size=OBJECT_SIZE):
        frames = load_animation_frames(OBJECTS_IMG_DIR, base_name, frame_count, size=size)
        super().__init__(x, y, frames[0])
        self.frames = frames
        self.frame_index = 0
        self.frame_timer = 0.0

    def update(self, dt):
        if self.collected:
            return
        self.frame_timer += dt
        if self.frame_timer >= self.FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]


class GlowOrb(AnimatedCollectible):
    """Restores HP and triggers Radiant Aura on pickup."""

    HEAL_AMOUNT = 25

    def __init__(self, x, y):
        super().__init__(x, y, "glow_orb")

    def apply(self, player):
        player.hp = min(player.max_hp, player.hp + self.HEAL_AMOUNT)


class LumenToken(AnimatedCollectible):
    """Hidden collectible for exploration — counted on the victory
    screen (PROJECT_BRIEF.md section 7 & "victory screen with
    completion time + token count")."""

    def __init__(self, x, y):
        super().__init__(x, y, "lumen_token")

    def apply(self, player):
        player.token_count += 1


class LumenShard(AnimatedCollectible):
    """One per scene, behind the boss/puzzle. Collecting it saves
    progress and unlocks the next scene."""

    SHARD_SIZE = (32, 52)

    def __init__(self, x, y):
        super().__init__(x, y, "lumen_shard", size=self.SHARD_SIZE)


class CheckpointGate(pygame.sprite.Sprite):
    """Glowing flower gate — walking through activates it and marks this
    spot as Iris's respawn point (PROJECT_BRIEF.md section 4). Section 9
    lists 4 frames covering an inactive pair and an active pair."""

    FRAME_DURATION = 0.2

    def __init__(self, x, y):
        super().__init__()
        frames = load_animation_frames(OBJECTS_IMG_DIR, "checkpoint_gate", 3, size=GATE_SIZE)
        self.inactive_frames = [frames[2]]
        self.active_frames = [frames[0], frames[2]]

        self.image = self.inactive_frames[0]
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.active = False
        self.frame_index = 0
        self.frame_timer = 0.0
        self._activate_sound = load_sound(SFX_DIR / "checkpoint.wav")

    def check_activate(self, player):
        """Returns True the moment it first activates (so the scene can
        record the respawn point) — False every frame after."""
        if not self.active and self.rect.colliderect(player.rect):
            self.active = True
            self.frame_index = 0
            self.frame_timer = 0.0
            play_sound(self._activate_sound)
            return True
        return False

    def update(self, dt):
        frames = self.active_frames if self.active else self.inactive_frames
        self.frame_timer += dt
        if self.frame_timer >= self.FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(frames)
        self.image = frames[self.frame_index]

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class VineSwitch(pygame.sprite.Sprite):
    """One of Scene 3's three hidden puzzle switches (PROJECT_BRIEF.md
    section 5) — hit with Glow Slash or Pollen Burst to flip it on
    permanently. Doesn't disappear like a Collectible; it stays visible
    showing its "on" frame, so it's handled the same way as
    CheckpointGate rather than subclassing Collectible."""

    SWITCH_SIZE = (32, 32)

    def __init__(self, x, y):
        super().__init__()
        frames = load_animation_frames(OBJECTS_IMG_DIR, "vine_switch", 2, size=self.SWITCH_SIZE)
        self.off_image, self.on_image = frames
        self.image = self.off_image
        self.rect = self.image.get_rect(center=(x, y))
        self.active = False

    def hit(self):
        """Idempotent — flips on the first hit, no-ops after."""
        if not self.active:
            self.active = True
            self.image = self.on_image

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class Chest(pygame.sprite.Sprite):
    """Treasure chest in Scene 2 that unlocks the Tendril Whip on collection."""

    def __init__(self, x, y):
        super().__init__()
        # Load from assets/images/collectibles/
        self.closed_image = load_image(OBJECTS_IMG_DIR.parent / "collectibles" / "chest_closed.png")
        self.open_image = load_image(OBJECTS_IMG_DIR.parent / "collectibles" / "chest_open.png")
        
        self.image = self.closed_image
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.opened = False
        self._open_sound = load_sound(SFX_DIR / "checkpoint.wav")  # reuse checkpoint sound as chest open chime!

    def check_open(self, player):
        if not self.opened and self.rect.colliderect(player.rect):
            self.opened = True
            self.image = self.open_image
            player.tendril_whip_unlocked = True
            play_sound(self._open_sound)
            return True
        return False

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))

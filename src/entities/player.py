"""
player.py

Iris, the only playable character. Handles keyboard input, movement,
jump / double-jump, crouch, the animation state machine, Glow Slash /
Pollen Burst / Tendril Whip, and taking damage.
"""

import pygame

from config.settings import (
    PLAYER_IMG_DIR,
    SFX_DIR,
    GRAVITY,
    MOVE_SPEED,
    JUMP_STRENGTH,
    DOUBLE_JUMP_STRENGTH,
    MAX_FALL_SPEED,
    PLAYER_MAX_HP,
    PLAYER_START_LIVES,
    POLLEN_BURST_COOLDOWN,
)
from src.core.asset_loader import load_animation_frames, load_sound, play_sound

# How many frames each animation sheet contains (see PROJECT_BRIEF.md section 9).
FRAME_COUNTS = {
    "idle": 4,
    "run": 10,
    "jump": 3,
    "fall": 2,
    "double_jump": 3,
    "crouch": 2,
    "attack": 7,
    "pollen_burst": 4,
    "tendril_whip": 4,
    "hurt": 2,
    "death": 4,
}

# Every animation's source art paints Iris's silhouette at a different
# fraction of its own canvas (measured via alpha-channel bounding box —
# e.g. idle paints ~85% of its canvas height, jump/fall only ~71-72%,
# attack ~88%), so scaling every state to one flat box makes her
# visibly shrink or balloon between poses. Each state's box size below
# is back-solved from that measured ratio so the *painted* content comes
# out the same ~108px apparent height in every one — a square box per
# state (matching this project's existing scale-both-axes-equally
# approach), not a per-axis fit, so horizontal silhouette differences
# between poses (e.g. attack's arm swing) still read naturally.
#
# Crouch is the deliberate exception: she's physically shorter while
# crouching, so its target (~61px) preserves the same ~57% ratio to
# standing height that the source art already draws it at, rather than
# being forced to match everyone else.
ANIMATION_DRAW_SIZE = {
    "idle": (127, 127),
    "run": (130, 130),
    "jump": (151, 151),
    "fall": (152, 152),
    "double_jump": (131, 131),
    "crouch": (76, 76),
    "attack": (123, 123),
    "pollen_burst": (129, 129),
    "tendril_whip": (142, 142),
    "hurt": (129, 129),
    "death": (194, 194),
}

# How far below the collision box's bottom edge the drawn sprite's feet
# sit, in pixels — a fixed visual grounding choice independent of
# animation art scale, so it applies the same to every pose/size.
FOOT_GROUND_OFFSET = 12

# Seconds each animation frame is shown before advancing to the next one.
FRAME_DURATION = 0.1

# --- Glow Slash (SPACE): melee arc in front of Iris, no cooldown ---
GLOW_SLASH_DURATION = 0.25   # how long the swing animation plays
GLOW_SLASH_RANGE = 50        # hitbox width, extending out from Iris
GLOW_SLASH_HEIGHT = 50
GLOW_SLASH_DAMAGE = 20

# --- Pollen Burst (Z): circular AoE around Iris, short cooldown.
# Locked until Scene 3 — see pollen_burst_unlocked below.
POLLEN_BURST_RADIUS = 90
POLLEN_BURST_DAMAGE = 15
POLLEN_BURST_ANIM_DURATION = 0.3

# --- Tendril Whip (X): fires a vine forward, introduced in Scene 2 ---
TENDRIL_RANGE = 320          # how far the probe line reaches
TENDRIL_ANIM_DURATION = 0.3
TENDRIL_PULL_SPEED = 14      # pixels/frame Iris is pulled toward a surface anchor
TENDRIL_RELEASE_DISTANCE = 40  # how close to the anchor before the swing ends
TENDRIL_ENEMY_PULL_SPEED = 300  # pixels/second an enemy is pulled toward Iris
TENDRIL_ENEMY_PULL_DURATION = 0.35

# --- Taking damage ---
HURT_ANIM_DURATION = 0.4
INVULNERABLE_DURATION = 1.0


class Player(pygame.sprite.Sprite):
    """Iris, the only playable character."""

    def __init__(self, x, y):
        super().__init__()

        # Standing/crouch hitbox dimensions live on the instance (not just
        # literals in update()'s crouch logic) so a scene can rescale Iris
        # — see Scene4Radiance._shrink_iris() — without her snapping back
        # to full size the next time she stands up or crouches. Set before
        # _load_animations() so it can size the crouch frames to match
        # (see the crouch_height/standing_height ratio there).
        self.standing_width = 40
        self.standing_height = 96
        self.crouch_height = 48

        self.animations = self._load_animations()
        self.sounds = self._load_sounds()
        self.state = "idle"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.facing_right = True

        self.image = self.animations["idle"][0]
        self.rect = pygame.Rect(0, 0, self.standing_width, self.standing_height)
        self.rect.midbottom = (x, y)

        # Movement state
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.can_double_jump = False
        self.used_double_jump = False
        self.crouching = False

        # Health / lives (Section 4 of the brief)
        self.max_hp = PLAYER_MAX_HP
        self.hp = PLAYER_MAX_HP
        self.lives = PLAYER_START_LIVES
        self.is_dead = False

        # Glow Slash
        self.attacking = False
        self.attack_timer = 0.0

        # Pollen Burst — locked until Scene 3 (see scene3_spire.py)
        self.pollen_burst_unlocked = False
        self.bursting = False
        self.burst_timer = 0.0
        self.pollen_cooldown_timer = 0.0

        # Lumen Tokens collected across the whole playthrough (Section 7:
        # "hidden collectible for exploration"), shown on the victory screen.
        self.token_count = 0

        # Tendril Whip — locked until Scene 2's chest (see scene2_skybloom.py)
        self.tendril_whip_unlocked = False
        self.whipping = False
        self.whip_timer = 0.0
        self.tendril_swinging = False
        self.tendril_anchor = None

        # Hurt / invulnerability
        self.hurt = False
        self.hurt_timer = 0.0
        self.invulnerable = False
        self.invulnerable_timer = 0.0

    def _load_animations(self):
        """Load every Iris animation once. Prefers separate numbered pose
        files (iris_idle_1.png, iris_idle_2.png, ...) over a single sliced
        sheet — see asset_loader.load_animation_frames().

        Each state loads at its own ANIMATION_DRAW_SIZE box — sizes
        measured from each pose's actual painted proportions rather than
        one flat size for all of them, so every pose (except the
        deliberately-shorter crouch) reads as the same apparent height
        instead of visibly shrinking or growing as she animates."""
        animations = {}
        for state, frame_count in FRAME_COUNTS.items():
            animations[state] = load_animation_frames(
                PLAYER_IMG_DIR, f"iris_{state}", frame_count, size=ANIMATION_DRAW_SIZE[state]
            )
        return animations

    def _load_sounds(self):
        """Load every Iris SFX once. load_sound() already returns None
        (silently) for a missing file, and play_sound() no-ops on None —
        so this works whether or not a given sound has been sourced yet."""
        names = ["jump", "glow_slash", "pollen_burst", "hurt", "death"]
        return {name: load_sound(SFX_DIR / f"{name}.wav") for name in names}

    def handle_input(self, keys):
        """Read keyboard state and set horizontal velocity / crouch."""
        moving = False

        if keys[pygame.K_LEFT]:
            self.velocity_x = -MOVE_SPEED
            self.facing_right = False
            moving = True
        elif keys[pygame.K_RIGHT]:
            self.velocity_x = MOVE_SPEED
            self.facing_right = True
            moving = True
        else:
            self.velocity_x = 0

        # Crouching state is handled directly in update() to allow ceiling checks.
        return moving

    def jump(self):
        """Trigger a jump or, if already airborne, a double jump.

        Scenes should call this once per key-press event (pygame.KEYDOWN),
        not every frame the key is held, otherwise Iris would jump
        continuously.
        """
        if self.tendril_swinging:
            self.tendril_swinging = False
            self.velocity_y = JUMP_STRENGTH
            play_sound(self.sounds["jump"])
            return

        if self.on_ground:
            self.velocity_y = JUMP_STRENGTH
            self.on_ground = False
            self.can_double_jump = True
            self.used_double_jump = False
            play_sound(self.sounds["jump"])
        elif self.can_double_jump:
            self.velocity_y = DOUBLE_JUMP_STRENGTH
            self.can_double_jump = False
            self.used_double_jump = True
            play_sound(self.sounds["jump"])

    def glow_slash(self):
        """Trigger a Glow Slash swing (SPACE).

        Returns (hitbox_rect, damage) so the scene can check it against
        enemies right away — the hit is resolved instantly, the swing
        animation is just the visual follow-through. Call once per
        KEYDOWN event.
        """
        self.attacking = True
        self.attack_timer = 0.0
        play_sound(self.sounds["glow_slash"])

        if self.facing_right:
            hitbox = pygame.Rect(
                self.rect.right, self.rect.centery - GLOW_SLASH_HEIGHT // 2,
                GLOW_SLASH_RANGE, GLOW_SLASH_HEIGHT,
            )
        else:
            hitbox = pygame.Rect(
                self.rect.left - GLOW_SLASH_RANGE, self.rect.centery - GLOW_SLASH_HEIGHT // 2,
                GLOW_SLASH_RANGE, GLOW_SLASH_HEIGHT,
            )
        return hitbox, GLOW_SLASH_DAMAGE

    def pollen_burst(self):
        """Trigger a Pollen Burst (Z).

        Returns (center, radius, damage) for the scene to check against
        nearby enemies, or None if it's still locked (not yet Scene 3)
        or on cooldown. Call once per KEYDOWN event.
        """
        if not self.pollen_burst_unlocked or self.pollen_cooldown_timer > 0:
            return None

        self.bursting = True
        self.burst_timer = 0.0
        self.pollen_cooldown_timer = POLLEN_BURST_COOLDOWN
        play_sound(self.sounds["pollen_burst"])
        return self.rect.center, POLLEN_BURST_RADIUS, POLLEN_BURST_DAMAGE

    def tendril_whip(self):
        """Trigger a Tendril Whip (X): fires a vine forward.

        Returns the probe line's (start, end) points in the facing
        direction. The scene resolves what it actually hits — a solid
        surface or an enemy — since only the scene has the tilemap and
        enemy list, then calls back into start_tendril_swing() or pulls
        the enemy via Enemy.apply_pull(). Call once per KEYDOWN event.
        """
        if not self.tendril_whip_unlocked:
            return None

        self.whipping = True
        self.whip_timer = 0.0

        direction = 1 if self.facing_right else -1
        start = self.rect.center
        end = (start[0] + TENDRIL_RANGE * direction, start[1])
        return start, end

    def start_tendril_swing(self, anchor_point):
        """Begin pulling Iris toward a surface anchor point so she can
        cross a gap she couldn't otherwise reach."""
        self.tendril_anchor = anchor_point
        self.tendril_swinging = True

    def _update_tendril_swing(self, dt):
        anchor_x, anchor_y = self.tendril_anchor
        dx = anchor_x - self.rect.centerx
        dy = anchor_y - self.rect.centery
        distance = (dx * dx + dy * dy) ** 0.5

        if distance <= TENDRIL_RELEASE_DISTANCE:
            self.tendril_swinging = False
            return

        self.velocity_x = TENDRIL_PULL_SPEED * (dx / distance)
        self.velocity_y = TENDRIL_PULL_SPEED * (dy / distance)

    def take_damage(self, amount):
        """Apply damage from an enemy hit. Ignored while already
        invulnerable (post-hit grace period) or dead."""
        if self.invulnerable or self.is_dead:
            return

        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True
            play_sound(self.sounds["death"])
        else:
            play_sound(self.sounds["hurt"])

        self.hurt = True
        self.hurt_timer = 0.0
        self.invulnerable = True
        self.invulnerable_timer = 0.0

    def respawn(self, position):
        """Revive at a checkpoint with full HP after losing a life
        (PROJECT_BRIEF.md section 4). `position` is a scene's
        respawn_point — the last checkpoint touched, or the scene start
        if none has been reached yet."""
        self.hp = self.max_hp
        self.is_dead = False
        self.hurt = False
        self.invulnerable = False
        self.velocity_x = 0
        self.velocity_y = 0
        self.rect.midbottom = position

    def _apply_gravity(self):
        self.velocity_y += GRAVITY
        if self.velocity_y > MAX_FALL_SPEED:
            self.velocity_y = MAX_FALL_SPEED

    def update(self, dt, keys, solid_rects):
        """
        Update Iris for one frame.

        solid_rects: list of pygame.Rect Iris can stand on / bump into —
        the combined solid tiles from the tilemap plus any platforms'
        current rects, supplied fresh by the scene each frame (platforms
        move, so their rects change frame to frame).
        """
        if self.is_dead:
            # Frozen except for gravity, so a body that died mid-air
            # still settles instead of endlessly drifting on whatever
            # input was held at the moment of death.
            self.tendril_swinging = False
            self.velocity_x = 0
            self._apply_gravity()
            self._move_and_collide(solid_rects)
            self._update_state(moving=False)
            self._animate(dt)
            return

        # 1. Crouching logic and hitbox adjustment
        wants_to_crouch = self.on_ground and (keys[pygame.K_s] or keys[pygame.K_DOWN])
        if self.crouching and not wants_to_crouch:
            # Test if standing up is blocked by a ceiling
            test_rect = pygame.Rect(self.rect.x, self.rect.bottom - self.standing_height,
                                     self.standing_width, self.standing_height)
            blocked = False
            for solid in solid_rects:
                if test_rect.colliderect(solid):
                    blocked = True
                    break
            if blocked:
                wants_to_crouch = True

        if wants_to_crouch and not self.crouching:
            # Start crouch: shrink hitbox to crouch_height, keep bottom aligned with floor
            old_bottom = self.rect.bottom
            self.rect.height = self.crouch_height
            self.rect.bottom = old_bottom
            self.crouching = True
        elif not wants_to_crouch and self.crouching:
            # Stand up: restore hitbox to standing_height, grow upwards
            self.rect.height = self.standing_height
            self.rect.top = self.rect.bottom - self.standing_height
            self.crouching = False

        if self.hurt:
            moving = False
            self.velocity_x = 0
            self.tendril_swinging = False  # cancel swing if hurt
        else:
            moving = self.handle_input(keys)
        if self.tendril_swinging:
            self._update_tendril_swing(dt)
        else:
            self._apply_gravity()
        self._move_and_collide(solid_rects)
        self._update_timers(dt)

        self._update_state(moving)
        self._animate(dt)

    def _move_and_collide(self, solid_rects):
        """Move on one axis at a time and resolve collisions on that axis
        before moving on the next. Doing X and Y separately (instead of
        moving diagonally then fixing up) is what keeps platformer
        collision simple to reason about."""
        # --- Horizontal ---
        self.rect.x += self.velocity_x
        for solid in solid_rects:
            if self.rect.colliderect(solid):
                if self.velocity_x > 0:
                    self.rect.right = solid.left
                elif self.velocity_x < 0:
                    self.rect.left = solid.right
                # Release tendril swing if player collides with a wall horizontally
                if self.tendril_swinging:
                    self.tendril_swinging = False

        # --- Vertical ---
        self.rect.y += self.velocity_y
        self.on_ground = False
        for solid in solid_rects:
            if self.rect.colliderect(solid):
                if self.velocity_y > 0:
                    self.rect.bottom = solid.top
                    self.velocity_y = 0
                    self.on_ground = True
                    self.can_double_jump = False
                    self.used_double_jump = False
                elif self.velocity_y < 0:
                    self.rect.top = solid.bottom
                    self.velocity_y = 0
                # Release tendril swing if player collides vertically
                if self.tendril_swinging:
                    self.tendril_swinging = False

    def _update_timers(self, dt):
        if self.attacking:
            self.attack_timer += dt
            if self.attack_timer >= GLOW_SLASH_DURATION:
                self.attacking = False

        if self.bursting:
            self.burst_timer += dt
            if self.burst_timer >= POLLEN_BURST_ANIM_DURATION:
                self.bursting = False

        if self.whipping:
            self.whip_timer += dt
            if self.whip_timer >= TENDRIL_ANIM_DURATION:
                self.whipping = False

        if self.pollen_cooldown_timer > 0:
            self.pollen_cooldown_timer = max(0.0, self.pollen_cooldown_timer - dt)

        if self.hurt:
            self.hurt_timer += dt
            if self.hurt_timer >= HURT_ANIM_DURATION:
                self.hurt = False

        if self.invulnerable:
            self.invulnerable_timer += dt
            if self.invulnerable_timer >= INVULNERABLE_DURATION:
                self.invulnerable = False

    def _update_state(self, moving):
        previous_state = self.state

        # Priority: dying > hurt > attack/pollen burst > airborne > crouch
        # > run > idle. Higher-priority states interrupt lower ones so a
        # hit or a swing always shows, even mid-jump.
        if self.is_dead:
            self.state = "death"
        elif self.hurt:
            self.state = "hurt"
        elif self.attacking:
            self.state = "attack"
        elif self.bursting:
            self.state = "pollen_burst"
        elif self.whipping:
            self.state = "tendril_whip"
        elif not self.on_ground:
            if self.used_double_jump:
                self.state = "double_jump"
            elif self.velocity_y < 0:
                self.state = "jump"
            else:
                self.state = "fall"
        elif self.crouching:
            self.state = "crouch"
        elif moving:
            self.state = "run"
        else:
            self.state = "idle"

        # A different animation has its own frame list, so restart from
        # frame 0 instead of carrying over an index that may not exist in
        # the new animation (e.g. going from a 6-frame run to a 2-frame
        # crouch).
        if self.state != previous_state:
            self.frame_index = 0
            self.frame_timer = 0.0

    def _animate(self, dt):
        frames = self.animations[self.state]

        self.frame_timer += dt
        if self.frame_timer >= FRAME_DURATION:
            self.frame_timer = 0.0
            # Death/hurt/attack/burst animations hold their last frame
            # instead of looping back to the start.
            if self.frame_index < len(frames) - 1:
                self.frame_index += 1
            elif self.state in ("idle", "run", "jump", "fall", "double_jump", "crouch"):
                self.frame_index = 0

        frame = frames[self.frame_index]
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def draw(self, surface, camera_offset=(0, 0)):
        # Draw tendril whip line/rope if swinging
        if self.tendril_swinging and self.tendril_anchor is not None:
            start_pos = (self.rect.centerx - camera_offset[0], self.rect.centery - camera_offset[1])
            end_pos = (self.tendril_anchor[0] - camera_offset[0], self.tendril_anchor[1] - camera_offset[1])
            pygame.draw.line(surface, (80, 160, 80), start_pos, end_pos, 4) # green vine line

        # Computed from the current frame's actual surface size rather
        # than a fixed constant, since every pose has its own box size
        # (see ANIMATION_DRAW_SIZE) — this keeps every pose horizontally
        # centred on the hitbox and
        # grounded FOOT_GROUND_OFFSET px below its bottom regardless of
        # which size the current frame happens to be (including a scene
        # that rescales her cached frames, e.g. Scene4Radiance._shrink_iris()).
        img_width, img_height = self.image.get_size()
        draw_x = self.rect.centerx - img_width // 2
        draw_y = self.rect.bottom - (img_height - FOOT_GROUND_OFFSET)
        draw_pos = (draw_x - camera_offset[0], draw_y - camera_offset[1])
        surface.blit(self.image, draw_pos)

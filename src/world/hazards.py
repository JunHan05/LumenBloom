"""
hazards.py

Environmental hazards. Scene 1 needs the acid pool (constant damage
while standing in it). Scene 3 adds the Murk pool (instant damage on
contact), the Murk Spore cluster (a destructible growth that reduces
the Murk Meter), and the Murk Meter itself. Scene 4 adds the burning
crater (a temporary patch left by a comet impact).
"""

import pygame

from config.settings import HAZARDS_IMG_DIR, TILE_SIZE, COLORS
from src.core.asset_loader import load_animation_frames, load_image
from src.entities.projectile import Projectile


class Hazard(pygame.sprite.Sprite):
    """Base class for a hazard that damages Iris while she's touching it.
    The art is tileable (PROJECT_BRIEF.md section 9), so the current
    frame is repeated across the hazard's full rect rather than drawn
    once at native size."""

    FRAME_DURATION = 0.2

    def __init__(self, x, y, width, height, base_name, frame_count, damage_per_second):
        super().__init__()
        # Prefers separate numbered tile files (acid_pool_1.png, _2.png,
        # ...) over a single sliced sheet — see
        # asset_loader.load_animation_frames().
        self.frames = load_animation_frames(HAZARDS_IMG_DIR, base_name, frame_count,
                                             size=(TILE_SIZE, TILE_SIZE))
        self.rect = pygame.Rect(x, y, width, height)
        self.image = self.frames[0]
        self.frame_index = 0
        self.frame_timer = 0.0
        self.damage_per_second = damage_per_second

    def update(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= self.FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]

    def apply_damage(self, player, dt):
        """Deal continuous damage while Iris overlaps this hazard.
        Applied directly to hp (not via player.take_damage()) so the
        post-hit invulnerability window from an enemy attack doesn't
        block ongoing environmental damage, and so it scales smoothly
        with dt instead of being an all-or-nothing single hit."""
        if self.rect.colliderect(player.rect) and not player.is_dead:
            player.hp = max(0, player.hp - self.damage_per_second * dt)
            if player.hp <= 0:
                player.is_dead = True

    def draw(self, surface, camera_offset=(0, 0)):
        tile_w, tile_h = self.image.get_size()
        y = self.rect.y
        while y < self.rect.bottom:
            x = self.rect.x
            while x < self.rect.right:
                surface.blit(self.image, (x - camera_offset[0], y - camera_offset[1]))
                x += tile_w
            y += tile_h


class AcidPool(Hazard):
    """Constant damage while Iris stands in it (Scene 1). Unlike the base
    Hazard class, this doesn't tile — the acid_pool art is one wide
    panorama of the whole pool (cave walls and vines framing both
    edges), not a small repeatable square, so tiling it across the
    hazard's width would squash each copy into a tile and repeat the
    edge decorations several times. Loads its frames at the hazard's
    actual (width, height) and blits a single stretched copy instead."""

    DAMAGE_PER_SECOND = 20

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "acid_pool", 4, self.DAMAGE_PER_SECOND)
        self.frames = load_animation_frames(HAZARDS_IMG_DIR, "acid_pool", 4, size=(width, height))
        self.image = self.frames[0]

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class BurningCrater(Hazard):
    """A temporary scorched patch left behind by a comet impact (Scene
    4, PROJECT_BRIEF.md section 5). Unlike the other hazards, this one
    doesn't last the whole scene — it burns out after LIFETIME seconds,
    so the scene should drop it from self.hazards once `expired` is
    True (same pattern as a spent Projectile or Shockwave).

    Like AcidPool above, the burning_crater art is one full frame (a
    scene-sized canvas with the crater rendered in place and transparent
    everywhere else), not a small repeatable square — the base Hazard
    class assumes the latter and would squash each frame down to
    (TILE_SIZE, TILE_SIZE) then tile that tiny thumbnail across the
    rect, which shrinks the actual crater graphic down to a barely
    visible speck. Reloads at the hazard's real (width, height) and
    blits a single copy instead."""

    DAMAGE_PER_SECOND = 25
    LIFETIME = 4.0
    FRAME_COUNT = 11

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "burning_crater", self.FRAME_COUNT, self.DAMAGE_PER_SECOND)
        self.frames = load_animation_frames(HAZARDS_IMG_DIR, "burning_crater", self.FRAME_COUNT, size=(width, height))
        self.image = self.frames[0]
        # Spread the 11 frames across the full LIFETIME so the burn
        # animation plays through exactly once and ends right as the
        # crater expires, instead of finishing early and either looping
        # or freezing on the last frame.
        self.FRAME_DURATION = self.LIFETIME / self.FRAME_COUNT
        self.age = 0.0

    @property
    def expired(self):
        return self.age >= self.LIFETIME

    def update(self, dt):
        self.age += dt
        # Deliberately doesn't call Hazard.update() — that wraps frame_index
        # with modulo, replaying the burn animation on a loop for the whole
        # LIFETIME (11 frames * 0.08s = 0.88s per cycle, against a 4s
        # lifetime, so it'd visibly repeat several times). This instead
        # advances once through the frames and then holds on the last one
        # (a settled, charred crater) for the rest of its lifetime.
        self.frame_timer += dt
        if self.frame_timer >= self.FRAME_DURATION and self.frame_index < len(self.frames) - 1:
            self.frame_timer = 0.0
            self.frame_index += 1
            self.image = self.frames[self.frame_index]

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class MurkPool(Hazard):
    """Instant damage on contact (Scene 3, PROJECT_BRIEF.md section 5) —
    a single hit through player.take_damage() (which respects her
    invulnerability window) rather than the Acid Pool's continuous
    per-second chip. Standing in it still hurts repeatedly, just once
    per invulnerability window instead of every frame."""

    DAMAGE = 35

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "murk_pool", 4, damage_per_second=0)

    def apply_damage(self, player, dt):
        if self.rect.colliderect(player.rect) and not player.is_dead:
            player.take_damage(self.DAMAGE)


class MyceliumTendril:
    """A wall-mounted tendril that periodically shoots across the corridor
    (Scene 3, PROJECT_BRIEF.md section 5). Cycles through three states:
    retracted (safe — frame 1), warning (glowing tip telegraph — frame 2),
    and extended (a full-reach barrier, dangerous — frame 3). Damages Iris
    only while extended. Not a Hazard subclass — its damage is not
    continuous; the scene calls apply_damage() manually each frame."""

    RETRACT_DURATION = 2.5   # idle between strikes (seconds)
    WARNING_DURATION = 0.6   # glowing telegraph before it shoots
    EXTEND_DURATION  = 1.0   # fully extended, dangerous

    DAMAGE = 20              # single hit through player.take_damage()

    STATE_RETRACTED = "retracted"
    STATE_WARNING   = "warning"
    STATE_EXTENDED  = "extended"

    def __init__(self, x, y, direction=1, reach=TILE_SIZE * 4):
        """
        x, y      — wall anchor point (midbottom of the tendril base)
        direction — 1 shoots right, -1 shoots left
        reach     — how far the tendril extends in pixels
        """
        self.frames = load_animation_frames(HAZARDS_IMG_DIR, "mycelium_tendril", 3,
                                             size=None)
        self.direction = direction
        self.reach     = reach

        # Anchor the base flush against the wall it grows from:
        #   direction= 1 (shoots right) → left  edge sits on the wall face
        #   direction=-1 (shoots left)  → right edge sits on the wall face
        self.base_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        if direction > 0:
            self.base_rect.left   = x
        else:
            self.base_rect.right  = x
        self.base_rect.bottom = y
        self.rect = self.base_rect.copy()   # expands when extended

        self.state  = self.STATE_RETRACTED
        self.timer  = 0.0
        self.image  = self.frames[0]

    def start_offset(self, offset_seconds):
        """Stagger this tendril's timer so multiple tendrils in one
        corridor don't all extend at the same moment."""
        self.timer = offset_seconds % self.RETRACT_DURATION

    def update(self, dt):
        self.timer += dt
        if self.state == self.STATE_RETRACTED and self.timer >= self.RETRACT_DURATION:
            self.state, self.timer = self.STATE_WARNING, 0.0
            self.image = self.frames[1]

        elif self.state == self.STATE_WARNING and self.timer >= self.WARNING_DURATION:
            self.state, self.timer = self.STATE_EXTENDED, 0.0
            self.image = self.frames[2]
            # Expand the collision rect to cover the full corridor reach
            if self.direction > 0:
                self.rect = pygame.Rect(self.base_rect.x, self.base_rect.y,
                                         self.reach, self.base_rect.height)
            else:
                self.rect = pygame.Rect(
                    self.base_rect.right - self.reach, self.base_rect.y,
                    self.reach, self.base_rect.height,
                )

        elif self.state == self.STATE_EXTENDED and self.timer >= self.EXTEND_DURATION:
            self.state, self.timer = self.STATE_RETRACTED, 0.0
            self.image = self.frames[0]
            self.rect  = self.base_rect.copy()

    def apply_damage(self, player, dt):
        """Only dangerous while extended."""
        if self.state == self.STATE_EXTENDED and not player.is_dead:
            if self.rect.colliderect(player.rect):
                player.take_damage(self.DAMAGE)

    def draw(self, surface, camera_offset=(0, 0)):
        bx = self.base_rect.x - camera_offset[0]
        by = self.base_rect.y - camera_offset[1]
        
        img_w, img_h = self.image.get_size()
        scale_y = self.base_rect.height / img_h
        
        if self.state == self.STATE_EXTENDED:
            # Scale the extended frame across the full reach
            scaled = pygame.transform.scale(self.image, (self.reach, self.base_rect.height))
            if self.direction > 0:
                surface.blit(scaled, (bx, by))
            else:
                flipped = pygame.transform.flip(scaled, True, False)
                surface.blit(flipped, (bx - self.reach + self.base_rect.width, by))
        else:
            # Retracted or warning: scale maintaining aspect ratio
            scaled_w = int(img_w * scale_y)
            scaled = pygame.transform.scale(self.image, (scaled_w, self.base_rect.height))
            if self.direction > 0:
                surface.blit(scaled, (bx, by))
            else:
                flipped = pygame.transform.flip(scaled, True, False)
                surface.blit(flipped, (bx - scaled_w + self.base_rect.width, by))


class FallingSpeleothem:

    """A rock formation that cracks loose from a cave ceiling, falls,
    and impacts the floor (Scene 1, PROJECT_BRIEF.md section 5 — cave
    hazard variant of the brief's "acid drips from stalactites" beat,
    reskinned as rockfall to fit the Glowcap Grotto setting). Cycles
    forming (safe, telegraphs the drop) -> falling (safe, visual only)
    -> impact (damages on contact at the floor) -> back to forming.
    Same duck-typed update/apply_damage/draw shape as every other
    hazard so it drops into BaseScene's hazard loop unchanged, but the
    *damage rect* stays fixed at the floor landing spot throughout —
    only the drawn position moves."""

    FORMING_DURATION = 1.8   # visibly cracking loose at the ceiling
    FALLING_DURATION = 0.4   # falling — visual only, not yet dangerous
    SPLASH_DURATION = 0.4    # brief damaging impact at the floor
    DAMAGE = 10              # a clean 10 hits from full HP (100) to death

    STATE_FORMING = "forming"
    STATE_FALLING = "falling"
    STATE_SPLASH = "splash"

    def __init__(self, x, ceiling_y, floor_y, size=TILE_SIZE):
        # frame 0 = forming/cracking loose, 1 = falling, 2 = impact
        # (speleothem_1/2/3.png).
        self.frames = load_animation_frames(HAZARDS_IMG_DIR, "speleothem", 3, size=(size, size))
        self.image = self.frames[0]

        self.x = x
        self.ceiling_y = ceiling_y
        # Damage detection always uses this rect — fixed at the floor
        # landing spot — regardless of where the drop is drawn.
        self.rect = pygame.Rect(x, floor_y - size, size, size)

        self.state = self.STATE_FORMING
        self.timer = 0.0

    def start_offset(self, offset_seconds):
        """Stagger this drip's cycle so multiple drips in one corridor
        don't fall in lockstep — call once, right after construction."""
        self.timer = offset_seconds

    def update(self, dt):
        self.timer += dt
        if self.state == self.STATE_FORMING and self.timer >= self.FORMING_DURATION:
            self.state, self.timer = self.STATE_FALLING, 0.0
        elif self.state == self.STATE_FALLING and self.timer >= self.FALLING_DURATION:
            self.state, self.timer = self.STATE_SPLASH, 0.0
        elif self.state == self.STATE_SPLASH and self.timer >= self.SPLASH_DURATION:
            self.state, self.timer = self.STATE_FORMING, 0.0

        frame_index = {self.STATE_FORMING: 0, self.STATE_FALLING: 1, self.STATE_SPLASH: 2}[self.state]
        self.image = self.frames[frame_index]

    def apply_damage(self, player, dt):
        if self.state == self.STATE_SPLASH and self.rect.colliderect(player.rect) and not player.is_dead:
            player.take_damage(self.DAMAGE)

    def draw(self, surface, camera_offset=(0, 0)):
        if self.state == self.STATE_FALLING:
            progress = self.timer / self.FALLING_DURATION
            y = self.ceiling_y + progress * (self.rect.y - self.ceiling_y)
        elif self.state == self.STATE_SPLASH:
            y = self.rect.y
        else:
            y = self.ceiling_y
        surface.blit(self.image, (self.x - camera_offset[0], y - camera_offset[1]))


class SawTrap(Hazard):
    """A rotating saw blade that shuttles back and forth between two
    fixed points forever and can't be destroyed. Art is a 6-frame spin
    cycle (`saw_trap_1.png`..`saw_trap_6.png`, cropped from a CraftPix
    trap sheet — the standalone circular blade icon, not the sheet's
    rail-mounted "rises from the ground" animation, since this trap
    stays visible and travels continuously). Unlike the tileable Hazard
    subclasses above, a single solid object brushing past Iris is a
    one-hit-then-invulnerable-window hit, not a continuous per-second
    chip — so this reuses Player.take_damage() the same way MurkPool
    does, rather than Hazard.apply_damage()'s per-frame hp subtraction."""

    FRAME_COUNT = 6
    DAMAGE = 25
    SPEED = 80  # pixels/second

    def __init__(self, start_pos, end_pos, size=TILE_SIZE, speed=SPEED,
                 damage=DAMAGE, pause_time=0.0):
        x, y = start_pos
        super().__init__(x, y, size, size, "saw_trap", self.FRAME_COUNT, damage_per_second=0)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.speed = speed
        self.damage = damage
        self.pause_time = pause_time
        self.pause_timer = 0.0
        self.moving_to_end = True

    def update(self, dt):
        super().update(dt)  # keeps the blade-spin animation going even while paused

        if self.pause_timer > 0:
            self.pause_timer = max(0.0, self.pause_timer - dt)
            return

        target = self.end_pos if self.moving_to_end else self.start_pos
        dx = target[0] - self.rect.x
        dy = target[1] - self.rect.y
        distance = (dx * dx + dy * dy) ** 0.5

        if distance <= self.speed * dt:
            self.rect.x, self.rect.y = target
            self.moving_to_end = not self.moving_to_end
            self.pause_timer = self.pause_time
        else:
            self.rect.x += self.speed * dt * (dx / distance)
            self.rect.y += self.speed * dt * (dy / distance)

    def apply_damage(self, player, dt):
        if self.rect.colliderect(player.rect) and not player.is_dead:
            player.take_damage(self.damage)


class ArrowTrap:
    """A stationary wall-mounted trap that fires an arrow at a steady
    interval. The trap body's 2 frames (`arrow_trap_1.png`/`_2.png`)
    are the mount/spike graphic mid-extend, cropped from a CraftPix
    trap sheet — small (idle) and fully extended (fire). The arrow
    itself (`arrow.png`) is a single static horizontal frame, cropped
    from one of the sheet's straight-flight positions rather than one
    of its mid-arc rotated ones, since this trap fires in a flat line,
    not an arc. The trap itself is inert on contact; each fired arrow
    is a plain Projectile (the same class every boss's ranged attack
    already uses) carrying its own damage, so it travels in a straight
    line until it hits Iris, collides with terrain, or reaches
    max_distance — no bespoke arrow logic needed. Not a Hazard subclass
    since it doesn't tile or damage on overlap itself; matches
    FallingSpeleothem's duck-typed update/apply_damage/draw shape plus
    the enemy-style take_pending_projectile() BaseScene already knows
    how to collect."""

    FRAME_COUNT = 2
    ARROW_SIZE = (28, 10)

    def __init__(self, x, y, direction=1, fire_interval=2.0, arrow_speed=300,
                 damage=15, max_distance=500):
        self.rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        self.rect.midbottom = (x, y)

        self.direction = direction  # 1 = fires right, -1 = fires left
        self.fire_interval = fire_interval
        self.arrow_speed = arrow_speed
        self.damage = damage
        self.max_distance = max_distance

        # Source art (arrow_trap_1.png/_2.png) is the sheet's left-wall
        # mount, which opens toward the right (it's built to shoot a
        # right-facing arrow) — flip every frame once, at load time,
        # when firing left, so the mount visibly faces the direction it
        # actually shoots instead of opening the wrong way.
        loaded_frames = load_animation_frames(HAZARDS_IMG_DIR, "arrow_trap", self.FRAME_COUNT, size=(TILE_SIZE, TILE_SIZE))
        if direction < 0:
            self.frames = [pygame.transform.flip(frame, True, False) for frame in loaded_frames]
        else:
            self.frames = loaded_frames

        # Source art (arrow_1.png) points left (arrowhead on the left) —
        # flip it once, at load time, when firing right, so the sprite
        # always faces the way it's actually travelling instead of
        # flying backwards.
        arrow_image = load_animation_frames(HAZARDS_IMG_DIR, "arrow", 1, size=self.ARROW_SIZE)[0]
        self.arrow_image = pygame.transform.flip(arrow_image, True, False) if direction > 0 else arrow_image
        self.image = self.frames[0]
        self.frame_index = 0
        self.frame_timer = 0.0

        self.timer = 0.0
        self.pending_arrow = None  # scene collects this once per frame, same as an enemy's shot

    def update(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= Hazard.FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]

        self.timer += dt
        if self.timer >= self.fire_interval:
            self.timer = 0.0
            self._fire()

    def _fire(self):
        velocity = (self.arrow_speed * self.direction, 0)
        self.pending_arrow = Projectile(
            self.rect.centerx, self.rect.centery, velocity,
            self.arrow_image, self.damage, max_range=self.max_distance,
        )

    def take_pending_projectile(self):
        """Scene calls this once per frame to collect a freshly-fired
        arrow (or None), same pattern as JinnMonster's magic-orb shot."""
        arrow = self.pending_arrow
        self.pending_arrow = None
        return arrow

    def apply_damage(self, player, dt):
        """The trap body is inert — only its fired arrows carry damage —
        but BaseScene's hazard loop calls this on every hazard, so it
        needs to exist as a no-op."""
        pass

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class GroundSpikeWave:
    """A jagged wall of white spikes that bursts from the ground and
    races along the floor — Bug Boss's ranged Stomp attack (Scene 1,
    scenes/scene1_grotto.py). Drawn entirely in code as a row of
    triangles, no image asset, per the team's storyboard reference for
    this attack. Only reaches SPIKE_HEIGHT above the floor, so jumping
    clears it — the sole way to dodge it, same as the attack it was
    designed to evoke (Hollow Knight's Husk Guard ground slam)."""

    SPEED = 260                    # pixels/second, travels away from the boss
    MAX_DISTANCE = TILE_SIZE * 8   # ~8 tiles before fizzling out, not indefinite
    SPIKE_HEIGHT = 80
    WIDTH = 48
    SPIKE_COUNT = 6

    def __init__(self, x, floor_y, direction, damage):
        self.start_x = x
        self.x = x
        self.floor_y = floor_y
        self.direction = direction  # 1 = travels right, -1 = travels left
        self.damage = damage
        self.hit_player = False     # a single hit per wave, like a solid trap

    @property
    def expired(self):
        return abs(self.x - self.start_x) >= self.MAX_DISTANCE

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.WIDTH / 2), self.floor_y - self.SPIKE_HEIGHT,
                            self.WIDTH, self.SPIKE_HEIGHT)

    def update(self, dt):
        self.x += self.SPEED * dt * self.direction

    def apply_damage(self, player, dt):
        if self.hit_player or self.expired or player.is_dead:
            return
        if self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.hit_player = True

    def draw(self, surface, camera_offset=(0, 0)):
        rect = self.rect
        base_y = rect.bottom - camera_offset[1]
        left = rect.left - camera_offset[0]
        spike_width = rect.width / self.SPIKE_COUNT
        for i in range(self.SPIKE_COUNT):
            spike_x = left + i * spike_width
            # Alternating tall/short spikes for a jagged silhouette.
            height = rect.height if i % 2 == 0 else rect.height * 0.55
            pygame.draw.polygon(surface, COLORS["white"], [
                (spike_x, base_y),
                (spike_x + spike_width / 2, base_y - height),
                (spike_x + spike_width, base_y),
            ])


class MurkSporeCluster:
    """A glowing growth on a wall (Scene 3, PROJECT_BRIEF.md sections 5
    & 6). Destroying it with Glow Slash or Pollen Burst reduces the
    Murk Meter — a single hit destroys it, no HP pool needed. Not a
    Hazard subclass: it doesn't damage Iris itself, it's a destructible
    target, closer in shape to a Collectible than a damage source.

    Regrows after REGROW_DELAY rather than staying destroyed forever —
    without that, a level's fixed handful of clusters is a one-time
    resource, and the Murk Meter refills endlessly for the rest of the
    scene (e.g. through a long boss fight) with nothing left able to
    reduce it, turning "manage the meter" into "eventually take
    unavoidable passive damage" once every cluster is spent."""

    PULSE_FRAME_DURATION = 0.25   # faster pulse so the glow feels alive
    REGROW_DELAY = 25.0
    HIT_FLASH_DURATION = 0.3      # how long the bright burst frame shows after a hit
    GLOW_COLOR = (160, 60, 220)    # purple glow ring drawn behind the sprite

    def __init__(self, x, y, width=TILE_SIZE, height=TILE_SIZE):
        # 2 frames (PROJECT_BRIEF.md section 9) used as a slow glow pulse
        # while intact.
        self.frames = load_animation_frames(HAZARDS_IMG_DIR, "murk_spore_cluster", 2, size=(width, height))
        # A one-off burst frame shown right when the cluster is hit, and a
        # dark husk frame shown for the rest of the regrow delay — replaces
        # the old "just disappear" behavior with visible feedback.
        self.hit_frame = load_image(HAZARDS_IMG_DIR / "murk_spore_cluster_hit.png", size=(width, height))
        # Loaded at its native aspect ratio (a short, flattened husk) rather
        # than stretched to fill the square tile, then scaled to the tile's
        # width so it can be bottom-aligned in draw() and visually rest on
        # the ground instead of floating with empty space beneath it.
        destroyed_raw = load_image(HAZARDS_IMG_DIR / "murk_spore_cluster_destroyed.png")
        raw_w, raw_h = destroyed_raw.get_size()
        self.destroyed_frame = pygame.transform.scale(destroyed_raw, (width, round(raw_h * width / raw_w)))
        self.rect = pygame.Rect(x, y, width, height)
        self.image = self.frames[0]
        self.frame_index = 0
        self.frame_timer = 0.0
        self.destroyed = False
        self.regrow_timer = 0.0

    def hit(self):
        self.destroyed = True
        self.regrow_timer = 0.0

    def update(self, dt):
        if self.destroyed:
            # Advance the timer so hit-flash → husk transition still works,
            # but never reset destroyed — cluster stays gone permanently.
            self.regrow_timer += dt
            return
        self.frame_timer += dt
        if self.frame_timer >= self.PULSE_FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]

    def draw(self, surface, camera_offset=(0, 0)):
        if self.destroyed:
            x = self.rect.x - camera_offset[0]
            if self.regrow_timer < self.HIT_FLASH_DURATION:
                surface.blit(self.hit_frame, (x, self.rect.y - camera_offset[1]))
            else:
                # Bottom-align the flattened husk so it rests on the ground
                # instead of being stretched to fill the whole tile height.
                y = self.rect.bottom - self.destroyed_frame.get_height() - camera_offset[1]
                surface.blit(self.destroyed_frame, (x, y))
            return

        cx = self.rect.centerx - camera_offset[0]
        cy = self.rect.centery - camera_offset[1]

        # Outer glow ring — drawn behind sprite, pulses between dim and bright
        glow_radius = self.rect.width // 2 + 16
        pulse_alpha = 70 if self.frame_index == 0 else 130
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.GLOW_COLOR, pulse_alpha),
                           (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surf, (cx - glow_radius, cy - glow_radius))

        # Draw the sprite on top of the glow
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class MurkMeter:
    """Fills over time; once full, drains Iris's HP passively until a
    Murk Spore cluster is destroyed to reduce it (Scenes 3 & 4,
    PROJECT_BRIEF.md section 6: "Murk Meter full -> passive damage +
    dark vignette + ambient hum until a Murk Spore cluster is
    destroyed"). ui/hud.py owns drawing the bar; this class just owns
    the value and the passive-damage rule."""

    MAX_VALUE = 100.0
    FILL_RATE = 5.0                  # points per second — full in 20s of neglect
    PASSIVE_DAMAGE_PER_SECOND = 4    # a nagging pressure, not a hard timer to the boss fight
    REDUCTION_PER_CLUSTER = 40.0
    VIGNETTE_START_FRACTION = 0.5    # vignette starts fading in from here

    def __init__(self):
        self.value = 0.0

    @property
    def is_full(self):
        return self.value >= self.MAX_VALUE

    def fraction(self):
        return self.value / self.MAX_VALUE

    def update(self, dt, player):
        self.value = min(self.MAX_VALUE, self.value + self.FILL_RATE * dt)
        if self.is_full and not player.is_dead:
            player.hp = max(0, player.hp - self.PASSIVE_DAMAGE_PER_SECOND * dt)
            if player.hp <= 0:
                player.is_dead = True

    def reduce(self):
        self.value = max(0.0, self.value - self.REDUCTION_PER_CLUSTER)

    def draw_vignette(self, surface):
        """A dark overlay that deepens as the meter climbs (from
        VIGNETTE_START_FRACTION up to fully full), warning Iris before
        the passive damage actually kicks in."""
        fraction = self.fraction()
        if fraction <= self.VIGNETTE_START_FRACTION:
            return
        progress = (fraction - self.VIGNETTE_START_FRACTION) / (1 - self.VIGNETTE_START_FRACTION)
        alpha = int(140 * progress)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*COLORS["murk_purple"], alpha))
        surface.blit(overlay, (0, 0))

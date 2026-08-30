"""
particles.py

Generic particle system used for every particle-based effect in the
game: Pollen Burst clouds, spore rain, wind-blown leaves, soil bursts,
petal barrages, and feather rain (PROJECT_BRIEF.md section 8). A single
Particle class covers all of these — each effect is just a different
spawn pattern via the emit_* helper methods below.
"""

import math
import random

import pygame


class Particle:
    def __init__(self, x, y, velocity, color=None, image=None, radius=4,
                 lifetime=1.0, gravity=0.0, fade=True):
        self.x = x
        self.y = y
        self.vx, self.vy = velocity
        self.color = color
        self.image = image
        self.radius = radius
        self.lifetime = lifetime
        self.age = 0.0
        self.gravity = gravity
        self.fade = fade

    @property
    def alive(self):
        return self.age < self.lifetime

    def update(self, dt):
        self.age += dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    _SURFACE_CACHE = {}  # Cache pre-rendered circle surfaces to prevent lag

    def draw(self, surface, camera_offset=(0, 0)):
        if not self.alive:
            return

        pos = (int(self.x - camera_offset[0]), int(self.y - camera_offset[1]))
        alpha = max(0, int(255 * (1 - self.age / self.lifetime))) if self.fade else 255

        if self.image is not None:
            frame = self.image.copy()
            frame.set_alpha(alpha)
            surface.blit(frame, (pos[0] - frame.get_width() // 2, pos[1] - frame.get_height() // 2))
        else:
            # Round alpha to nearest 16 to keep the cache size extremely small
            alpha_cached = (alpha // 16) * 16
            if alpha_cached == 0:
                return  # fully transparent, skip drawing

            cache_key = (self.radius, self.color, alpha_cached)
            if cache_key not in Particle._SURFACE_CACHE:
                surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*self.color, alpha_cached), (self.radius, self.radius), self.radius)
                Particle._SURFACE_CACHE[cache_key] = surf

            cached_surf = Particle._SURFACE_CACHE[cache_key]
            surface.blit(cached_surf, (pos[0] - self.radius, pos[1] - self.radius))


class ParticleSystem:
    """Owns every live particle for a scene. Call update()/draw() once per
    frame, and spawn particles through the emit_* methods."""

    def __init__(self):
        self.particles = []

    def update(self, dt):
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface, camera_offset=(0, 0)):
        for particle in self.particles:
            particle.draw(surface, camera_offset)

    def emit_pollen_burst(self, center, count=20, color=(200, 255, 120)):
        """Circular outward burst — Iris's Pollen Burst ability."""
        cx, cy = center
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 160)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            self.particles.append(Particle(
                cx, cy, velocity, color=color,
                radius=random.randint(2, 4), lifetime=random.uniform(0.4, 0.7),
            ))

    def emit_spore_rain(self, x_range, y, count=10, color=(180, 120, 200)):
        """Spores falling from above — Fungal Warden's spore rain (Scene 3)."""
        for _ in range(count):
            x = random.uniform(*x_range)
            velocity = (random.uniform(-10, 10), random.uniform(40, 80))
            self.particles.append(Particle(
                x, y, velocity, color=color, radius=3, lifetime=2.0, gravity=20,
            ))

    def emit_wind_leaves(self, x, y_range, count=5):
        """Leaves streaming sideways — Scene 2 wind gust event."""
        for _ in range(count):
            y = random.uniform(*y_range)
            # Blow left (negative vx) to match the push direction
            velocity = (random.uniform(-300, -150), random.uniform(-20, 20))
            # Mix two shades of green for green forest canopy
            color = (80, 150, 40) if random.random() < 0.6 else (120, 180, 60)
            self.particles.append(Particle(
                x, y, velocity, color=color, radius=3, lifetime=1.5,
            ))

    def emit_soil_burst(self, center, count=12, color=(110, 80, 50)):
        """Dirt kicked up — Stalker Root emerging from the ground (Scene 2)."""
        cx, cy = center
        for _ in range(count):
            angle = random.uniform(math.pi, math.tau)  # upward half only
            speed = random.uniform(40, 120)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            self.particles.append(Particle(
                cx, cy, velocity, color=color, radius=3, lifetime=0.6, gravity=200,
            ))

    def emit_petals(self, center, count=16, color=(255, 220, 150)):
        """Radial ring of petals — Lumen Bloom ultimate."""
        cx, cy = center
        for i in range(count):
            angle = (math.tau / count) * i
            velocity = (math.cos(angle) * 200, math.sin(angle) * 200)
            self.particles.append(Particle(
                cx, cy, velocity, color=color, radius=4, lifetime=0.8,
            ))

    def emit_feathers(self, center, count=14, color=(200, 160, 220)):
        """Feather rain — Sky Wisp's death (Scene 2 boss)."""
        cx, cy = center
        for _ in range(count):
            velocity = (random.uniform(-30, 30), random.uniform(-60, -20))
            self.particles.append(Particle(
                cx, cy, velocity, color=color, radius=3, lifetime=1.5, gravity=60,
            ))

    def emit_explosion(self, center, count=24):
        """Comet impact burst — Scene 4's comet drops and opening
        flashback cutscene. Two colors mixed (bright flash + ember
        afterglow) for a rounder fireball look than a single-color burst."""
        cx, cy = center
        for i in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(100, 260)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = (255, 220, 120) if i % 2 == 0 else (220, 90, 40)
            self.particles.append(Particle(
                cx, cy, velocity, color=color,
                radius=random.randint(3, 6), lifetime=random.uniform(0.4, 0.9),
            ))

    def emit_ambient_leaves(self, x_range, y, count=1):
        """Gentle falling leaves drifting down."""
        for _ in range(count):
            x = random.uniform(*x_range)
            # Gentle drift: slow vertical fall (50-90), slight left sway (-50 to 0)
            velocity = (random.uniform(-50, 0), random.uniform(50, 90))
            # Mix two shades of green for green forest canopy
            color = (80, 150, 40) if random.random() < 0.65 else (120, 180, 60)
            self.particles.append(Particle(
                x, y, velocity, color=color, radius=random.randint(2, 3),
                lifetime=random.uniform(7.0, 11.0), gravity=10,
            ))

    def emit_debris(self, x, y_range, count=3):
        """Wood/bark debris blown sideways — Scene 2 storm wind gust."""
        for _ in range(count):
            y = random.uniform(*y_range)
            velocity = (random.uniform(-350, -180), random.uniform(-30, 30))
            color = random.choice([
                (120, 80, 40),   # wood brown
                (90, 60, 30),    # dark bark
                (150, 120, 80),  # light wood
            ])
            self.particles.append(Particle(
                x, y, velocity, color=color,
                radius=random.randint(3, 6), lifetime=random.uniform(0.5, 1.0),
            ))

    def emit_dust_impact(self, center, count=18, color=(150, 130, 100)):
        """Ground-hugging dust cloud kicked outward to both sides — Bug
        Boss's stick-slam impact (Scene 1)."""
        cx, cy = center
        for _ in range(count):
            direction = random.choice((-1, 1))
            angle = random.uniform(-0.3, 0.3)
            speed = random.uniform(60, 160)
            velocity = (
                math.cos(angle) * speed * direction,
                -abs(math.sin(angle) * speed) - random.uniform(10, 40),
            )
            self.particles.append(Particle(
                cx, cy, velocity, color=color,
                radius=random.randint(3, 6), lifetime=random.uniform(0.4, 0.8), gravity=220,
            ))

    def emit_embers(self, center, count=3, color=(255, 160, 60)):
        """Small upward-drifting embers — Scene 4's falling comet trail
        and the Aurelian Titan's idle ambient glow. Negative gravity
        keeps them rising and cooling rather than falling like debris."""
        cx, cy = center
        for _ in range(count):
            velocity = (random.uniform(-15, 15), random.uniform(-40, -10))
            self.particles.append(Particle(
                cx, cy, velocity, color=color, radius=random.randint(1, 3),
                lifetime=random.uniform(0.5, 1.0), gravity=-10,
            ))

    def emit_thorn_launch(self, center, facing_right):
        """Directional burst of green and grey particles when a thorn is launched."""
        cx, cy = center
        direction = 1 if facing_right else -1
        # Launch 8 particles in a cone in the firing direction
        for _ in range(8):
            angle = random.uniform(-0.3, 0.3)  # narrow cone
            speed = random.uniform(80, 180)
            velocity = (math.cos(angle) * speed * direction, math.sin(angle) * speed + random.uniform(-20, 20))
            # Briarling thorn colors (browns, dark greens, and greys)
            color = random.choice([
                (140, 150, 120),  # olive green
                (110, 120, 100),  # dark grey-green
                (160, 110, 60),   # wood brown
            ])
            self.particles.append(Particle(
                cx, cy, velocity, color=color, radius=random.randint(2, 3),
                lifetime=random.uniform(0.3, 0.6), gravity=15
            ))

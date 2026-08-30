"""
intro_scene.py

Opening story cutscene: an 8-panel illustrated slideshow that tells the
Aurelia / Murk Comet backstory (PROJECT_BRIEF.md section 3) before the
player reaches the main menu. Played once when the game starts.

Not a BaseScene subclass — there's no player, tilemap, or gameplay here,
just panels, captions, and timed fades — so it implements the same small
handle_event()/update()/draw() shape that scene_manager.py already talks
to everywhere else (see menus.py's TextCard for the same idea).
"""

import pygame

from config.settings import SCREEN_W, SCREEN_H, COLORS, OPENING_STORY_IMG_DIR, SFX_DIR
from src.core.asset_loader import load_image, load_sound, play_sound


class IntroScene:
    """Plays panel_1.png..panel_8.png in order, each with a slow Ken Burns
    zoom, crossfading into the next, with a captioned caption band and
    cinematic letterbox bars. Skippable at any time (ENTER/SPACE/click)."""

    # How long each panel is "on screen" for, including the crossfade time
    # it shares with its neighbours. Consecutive panels overlap for exactly
    # one CROSSFADE_DURATION, so a panel's unique (non-overlapping) hold
    # time is PANEL_DURATION - CROSSFADE_DURATION.
    PANEL_DURATION = 5.5
    CROSSFADE_DURATION = 1.0

    # Ken Burns zoom: each panel scales from 100% to 108% over its own
    # PANEL_DURATION, giving a slow drift/zoom on an otherwise still image.
    ZOOM_START = 1.0
    ZOOM_END = 1.08

    # Caption fade timing, measured from the moment its panel becomes the
    # active one (local_t = 0). CAPTION_FADE_OUT_START is computed (see
    # _caption_fade_out_start()) so it always finishes right as the
    # crossfade to the next panel begins — that way a longer
    # PANEL_DURATION gives the caption more time on screen instead of
    # just adding a silent gap before the crossfade.
    CAPTION_FADE_IN_DELAY = 0.3
    CAPTION_FADE_IN_DURATION = 0.5
    CAPTION_FADE_OUT_DURATION = 0.5

    # Cinematic black bars, present for the whole intro only.
    LETTERBOX_HEIGHT = 80

    # "Press SPACE to skip" hint: hidden for the first couple of seconds
    # so it doesn't clutter the very first moment, then fades in.
    SKIP_HINT_DELAY = 2.0
    SKIP_HINT_FADE_DURATION = 1.0

    # Fade-to-black at the very end (or immediately, if skipped).
    END_FADE_DURATION = 1.0

    # (filename in assets/images/opening_story/, caption text)
    PANELS = [
        ("panel_1.png", "In the world of Aurelia, life flourished for a thousand years."),
        ("panel_2.png", "At its heart lay the Lumen Core, the source of all growth and light."),
        ("panel_3.png", "Then, without warning, a dark comet fell from the sky."),
        ("panel_4.png", "The Murk Comet struck the heart of Aurelia."),
        ("panel_5.png", "The Lumen Core shattered into four scattered shards."),
        ("panel_6.png", "A corrupting force known as the Murk began to spread across the land."),
        ("panel_7.png", "Iris's father, the last Keeper of the Core, was gravely wounded."),
        ("panel_8.png", "Now, Iris must find the four Lumen Shards and restore what was lost."),
    ]

    def __init__(self):
        self.images = [load_image(OPENING_STORY_IMG_DIR / filename) for filename, _ in self.PANELS]
        self.captions = [caption for _, caption in self.PANELS]

        self.caption_font = pygame.font.Font(None, 40)
        self.hint_font = pygame.font.Font(None, 24)

        # Panel i starts (PANEL_DURATION - CROSSFADE_DURATION) after panel
        # i - 1, so each pair overlaps for one crossfade window.
        step = self.PANEL_DURATION - self.CROSSFADE_DURATION
        self.start_times = [i * step for i in range(len(self.PANELS))]
        self.total_show_duration = self.start_times[-1] + self.PANEL_DURATION

        self.time = 0.0          # seconds since the intro began (frozen once ending starts)
        self.ending = False      # True while fading out to black, for real or via skip
        self.end_fade_time = 0.0
        self.finished = False    # scene_manager swaps to the main menu once this is True

        # One-shot SFX tied to specific panels' arrival (index -> (sound,
        # layers)), reusing the same clips scene4_radiance.py/
        # aurelian_titan.py play for the same story beats. Each fires
        # once, the moment self.time reaches that panel's
        # start_times[index]; skipping the intro before then just means
        # it never plays. `layers` stacks identical playback since
        # set_volume() is already capped at 1.0 (see play_sound()) —
        # burning_crater.wav is doubled here per request, and
        # titan_attack.wav needs layers=5 just to be audible at all: its
        # source clip peaks ~4-5x quieter than comet.wav/burning_crater.wav
        # (same layers=5 used for it in aurelian_titan.py).
        self._panel_sounds = {
            2: (load_sound(SFX_DIR / "comet.wav"), 1),           # panel 3: comet falls
            3: (load_sound(SFX_DIR / "burning_crater.wav"), 2),  # panel 4: comet strikes
            5: (load_sound(SFX_DIR / "titan_attack.wav"), 5),    # panel 6: Murk/Titan unleashed
        }
        self._played_panel_sounds = set()

    # --- Input -----------------------------------------------------------------

    def handle_event(self, event):
        """ENTER, SPACE, or any mouse click skips straight to the closing
        fade-to-black — same visual exit as reaching panel 8 naturally."""
        skip_key = event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)
        skip_click = event.type == pygame.MOUSEBUTTONDOWN
        if (skip_key or skip_click) and not self.ending:
            self.ending = True

    # --- Update ------------------------------------------------------------------

    def update(self, dt):
        if not self.ending:
            self.time += dt
            for index, (sound, layers) in self._panel_sounds.items():
                if index not in self._played_panel_sounds and self.time >= self.start_times[index]:
                    self._played_panel_sounds.add(index)
                    play_sound(sound, layers=layers)
            if self.time >= self.total_show_duration:
                # Clamp rather than overshoot, so the last panel's local
                # time lands exactly on PANEL_DURATION instead of past it
                # (past it would make the draw loop skip drawing it).
                self.time = self.total_show_duration
                self.ending = True
        else:
            self.end_fade_time += dt
            if self.end_fade_time >= self.END_FADE_DURATION:
                self.finished = True

    # --- Draw ----------------------------------------------------------------

    def draw(self, surface):
        surface.fill(COLORS["black"])

        for index, image in enumerate(self.images):
            local_t = self.time - self.start_times[index]
            if local_t < 0 or local_t > self.PANEL_DURATION:
                continue  # this panel hasn't started yet, or has already fully ended

            scale = self._panel_scale(local_t)
            alpha = self._panel_alpha(index, local_t)
            self._draw_panel(surface, image, scale, alpha)

            if not self.ending:
                caption_alpha = self._caption_alpha(local_t)
                if caption_alpha > 0:
                    self._draw_caption(surface, self.captions[index], caption_alpha)

        self._draw_letterbox(surface)

        if not self.ending:
            self._draw_skip_hint(surface)
        else:
            self._draw_end_fade(surface)

    # --- Per-panel envelopes -----------------------------------------------------

    def _panel_alpha(self, index, local_t):
        """0..1 opacity envelope: fades in over the first CROSSFADE_DURATION
        and (except for the very last panel) fades back out over the last
        CROSSFADE_DURATION, so it hands off smoothly to the next panel."""
        fade_in = min(1.0, local_t / self.CROSSFADE_DURATION)
        if index == len(self.PANELS) - 1:
            return fade_in
        fade_out = min(1.0, (self.PANEL_DURATION - local_t) / self.CROSSFADE_DURATION)
        return min(fade_in, fade_out)

    def _panel_scale(self, local_t):
        """Ken Burns zoom: creeps from ZOOM_START to ZOOM_END across the
        panel's full time on screen, independent of the fade envelope."""
        progress = max(0.0, min(1.0, local_t / self.PANEL_DURATION))
        return self.ZOOM_START + (self.ZOOM_END - self.ZOOM_START) * progress

    def _caption_fade_out_start(self):
        """Caption starts fading out early enough to fully disappear
        right as this panel's crossfade-out begins (or, for the last
        panel, right as PANEL_DURATION ends)."""
        return self.PANEL_DURATION - self.CROSSFADE_DURATION - self.CAPTION_FADE_OUT_DURATION

    def _caption_alpha(self, local_t):
        fade_out_start = self._caption_fade_out_start()
        if local_t < self.CAPTION_FADE_IN_DELAY:
            return 0.0
        if local_t < self.CAPTION_FADE_IN_DELAY + self.CAPTION_FADE_IN_DURATION:
            return (local_t - self.CAPTION_FADE_IN_DELAY) / self.CAPTION_FADE_IN_DURATION
        if local_t < fade_out_start:
            return 1.0
        if local_t < fade_out_start + self.CAPTION_FADE_OUT_DURATION:
            return 1.0 - (local_t - fade_out_start) / self.CAPTION_FADE_OUT_DURATION
        return 0.0

    # --- Drawing helpers -----------------------------------------------------

    def _draw_panel(self, surface, image, scale, alpha):
        if alpha <= 0:
            return
        src_w, src_h = image.get_size()
        # Panel art isn't necessarily rendered at exactly SCREEN_W x
        # SCREEN_H (e.g. these came in at 1024x572), so first scale up
        # to "cover" the screen with no gaps (like CSS background-size:
        # cover), THEN apply the Ken Burns zoom on top of that.
        cover_scale = max(SCREEN_W / src_w, SCREEN_H / src_h)
        total_scale = cover_scale * scale
        scaled_w, scaled_h = int(src_w * total_scale), int(src_h * total_scale)
        # smoothscale (not scale) so the slow zoom doesn't look pixelated.
        scaled = pygame.transform.smoothscale(image, (scaled_w, scaled_h))
        scaled.set_alpha(int(255 * alpha))
        # Zoomed image is bigger than the screen; centering it and letting
        # blit() clip the overflow is what makes it "zoom in" on the middle.
        x = (SCREEN_W - scaled_w) // 2
        y = (SCREEN_H - scaled_h) // 2
        surface.blit(scaled, (x, y))

    def _draw_letterbox(self, surface):
        pygame.draw.rect(surface, COLORS["black"], (0, 0, SCREEN_W, self.LETTERBOX_HEIGHT))
        pygame.draw.rect(surface, COLORS["black"],
                          (0, SCREEN_H - self.LETTERBOX_HEIGHT, SCREEN_W, self.LETTERBOX_HEIGHT))

    def _draw_caption(self, surface, text, alpha):
        """White caption text on a semi-transparent dark band, so it reads
        clearly over any panel artwork, sitting just above the bottom
        letterbox bar."""
        lines = self._wrap_text(text, self.caption_font, SCREEN_W - 160)
        line_surfaces = [self.caption_font.render(line, True, COLORS["white"]) for line in lines]

        padding = 16
        line_spacing = 4
        band_width = max(s.get_width() for s in line_surfaces) + padding * 2
        band_height = (sum(s.get_height() for s in line_surfaces)
                       + line_spacing * (len(lines) - 1) + padding * 2)

        band = pygame.Surface((band_width, band_height), pygame.SRCALPHA)
        band.fill((0, 0, 0, 150))

        y = padding
        for line_surface in line_surfaces:
            rect = line_surface.get_rect(centerx=band_width // 2, y=y)
            band.blit(line_surface, rect)
            y += line_surface.get_height() + line_spacing

        band.set_alpha(int(255 * alpha))
        band_x = (SCREEN_W - band_width) // 2
        band_y = SCREEN_H - self.LETTERBOX_HEIGHT - band_height - 24
        surface.blit(band, (band_x, band_y))

    def _draw_skip_hint(self, surface):
        alpha = max(0.0, min(1.0, (self.time - self.SKIP_HINT_DELAY) / self.SKIP_HINT_FADE_DURATION))
        if alpha <= 0:
            return
        hint = self.hint_font.render("Press SPACE to skip", True, COLORS["white"])
        hint.set_alpha(int(200 * alpha))
        rect = hint.get_rect(bottomright=(SCREEN_W - 20, SCREEN_H - 20))
        surface.blit(hint, rect)

    def _draw_end_fade(self, surface):
        fade = min(1.0, self.end_fade_time / self.END_FADE_DURATION)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(255 * fade)))
        surface.blit(overlay, (0, 0))

    @staticmethod
    def _wrap_text(text, font, max_width):
        """Greedy word-wrap: keeps adding words to the current line while
        it still fits max_width, else starts a new line."""
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

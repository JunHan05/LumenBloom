"""
menus.py

Main menu, pause menu, Game Over screen, Victory screen, and the
narrative text card shown between scenes (PROJECT_BRIEF.md section 8).
Kept intentionally simple — plain text over a background — since the
point of this file is the states and transitions, not visual polish.
"""

import pygame

from config.settings import SCREEN_W, SCREEN_H, COLORS, UI_IMG_DIR, SFX_DIR
from src.core.asset_loader import load_image, load_sound, play_sound


class Menu:
    """Shared helpers for the text-based menu screens below."""

    def __init__(self):
        self.title_font = pygame.font.Font(None, 64)
        self.body_font = pygame.font.Font(None, 32)
        # Shared by every menu screen (navigable or not) so a subclass
        # never has to load its own copy — load_sound()/play_sound()
        # already no-op safely if these haven't been sourced yet.
        self._navigate_sound = load_sound(SFX_DIR / "menu_navigate.wav")
        self._confirm_sound = load_sound(SFX_DIR / "menu_confirm.wav")

    def _play_navigate(self):
        play_sound(self._navigate_sound)

    def _play_confirm(self):
        play_sound(self._confirm_sound)

    def _draw_centered_text(self, surface, text, font, color, y):
        rendered = font.render(text, True, color)
        rect = rendered.get_rect(center=(SCREEN_W // 2, y))
        surface.blit(rendered, rect)


class MainMenu(Menu):
    """Title screen with a navigable options list (UP/DOWN to move,
    ENTER/SPACE to confirm). "Start" plays the opening story cutscene
    then begins a fresh playthrough from Scene 1 (returns the string
    "start"); below it, one entry per scene doubles as a scene select
    that skips straight to gameplay with no cutscene (returns its
    SCENE_SEQUENCE index as an int); "Quit" returns the string "quit"."""

    SCENE_LABELS = [
        "The Glowcap Grotto",
        "The Skybloom Reach",
        "The Hollow Spire",
        "The Last Radiance",
    ]
    OPTIONS = [("Start", "start")] + [(label, i) for i, label in enumerate(SCENE_LABELS)] + [("Quit", "quit")]
    OPTION_SPACING = 40

    def __init__(self):
        super().__init__()
        self.logo = load_image(UI_IMG_DIR / "title_logo.png", size=(500, 142))
        self.selected_index = 0

    def handle_event(self, event):
        """Returns a scene index (int) or "quit" once the player confirms
        a choice, else None."""
        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected_index = (self.selected_index - 1) % len(self.OPTIONS)
            self._play_navigate()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected_index = (self.selected_index + 1) % len(self.OPTIONS)
            self._play_navigate()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._play_confirm()
            return self.OPTIONS[self.selected_index][1]
        return None

    def draw(self, surface):
        surface.fill(COLORS["ui_bg"])
        logo_rect = self.logo.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 110))
        surface.blit(self.logo, logo_rect)

        first_option_y = SCREEN_H // 2
        for i, (label, _action) in enumerate(self.OPTIONS):
            selected = i == self.selected_index
            color = COLORS["glow_gold"] if selected else COLORS["white"]
            text = f"> {label} <" if selected else label
            self._draw_centered_text(surface, text, self.body_font, color,
                                      first_option_y + i * self.OPTION_SPACING)


class PauseMenu(Menu):
    """Navigable pause overlay (UP/DOWN to move, ENTER/SPACE to confirm).
    ESC is also a quick-resume shortcut, matching the pre-existing
    "press ESC to pause / press ESC to resume" muscle memory."""

    OPTIONS = [("Resume", "resume"), ("Exit to Main Menu", "exit")]
    OPTION_SPACING = 40

    def __init__(self):
        super().__init__()
        self.selected_index = 0

    def handle_event(self, event):
        """Returns "resume"/"exit" once the player confirms a choice, else None."""
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            self._play_confirm()
            return "resume"
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected_index = (self.selected_index - 1) % len(self.OPTIONS)
            self._play_navigate()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected_index = (self.selected_index + 1) % len(self.OPTIONS)
            self._play_navigate()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._play_confirm()
            return self.OPTIONS[self.selected_index][1]
        return None

    def draw(self, surface):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        self._draw_centered_text(surface, "PAUSED", self.title_font, COLORS["white"], SCREEN_H // 2 - 40)

        first_option_y = SCREEN_H // 2 + 30
        for i, (label, _action) in enumerate(self.OPTIONS):
            selected = i == self.selected_index
            color = COLORS["glow_gold"] if selected else COLORS["white"]
            text = f"> {label} <" if selected else label
            self._draw_centered_text(surface, text, self.body_font, color,
                                      first_option_y + i * self.OPTION_SPACING)


class GameOverMenu(Menu):
    def handle_event(self, event):
        """Returns True once the player chooses to restart."""
        confirmed = event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)
        if confirmed:
            self._play_confirm()
        return confirmed

    def draw(self, surface):
        surface.fill(COLORS["black"])
        self._draw_centered_text(surface, "GAME OVER", self.title_font, COLORS["hp_red"], SCREEN_H // 2 - 20)
        self._draw_centered_text(surface, "Press ENTER to restart the scene", self.body_font,
                                  COLORS["white"], SCREEN_H // 2 + 40)


class VictoryMenu(Menu):
    """Shown after the Aurelian Titan falls (Scene 4) — completion time
    and token count are passed in once that scene exists."""

    def handle_event(self, event):
        """Returns True once the player chooses to return to the menu."""
        confirmed = event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)
        if confirmed:
            self._play_confirm()
        return confirmed

    def draw(self, surface, completion_time=0.0, token_count=0):
        surface.fill(COLORS["ui_bg"])
        self._draw_centered_text(surface, "AURELIA IS SAVED", self.title_font,
                                  COLORS["glow_gold"], SCREEN_H // 2 - 60)
        minutes, seconds = divmod(int(completion_time), 60)
        self._draw_centered_text(surface, f"Time: {minutes:02d}:{seconds:02d}    Lumen Tokens: {token_count}",
                                  self.body_font, COLORS["white"], SCREEN_H // 2)
        self._draw_centered_text(surface, "Press ENTER to return to the menu", self.body_font,
                                  COLORS["white"], SCREEN_H // 2 + 60)


class TextCard(Menu):
    """Narrative text card shown between scenes: 'Scene complete -> wipe
    transition + narrative text card -> next scene unlocked' (section 6)."""

    def __init__(self, text, duration=2.5):
        super().__init__()
        self.text = text
        self.duration = duration
        self.time = 0.0

    @property
    def done(self):
        return self.time >= self.duration

    def update(self, dt):
        self.time += dt

    def handle_event(self, event):
        """Returns True to skip early on any key press."""
        return event.type == pygame.KEYDOWN

    def draw(self, surface):
        surface.fill(COLORS["black"])
        self._draw_centered_text(surface, self.text, self.body_font, COLORS["white"], SCREEN_H // 2)

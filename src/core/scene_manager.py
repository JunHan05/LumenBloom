"""
scene_manager.py

Owns the current game state (main menu, playing, paused, narrative text
card, game over, victory) and the current scene. This is the one place
that knows how menu <-> Scenes 1-4 fit together; Game (game.py)
delegates handle_event()/update()/draw() straight to it.
"""

import pygame

from config.settings import PLAYER_START_LIVES, MUSIC_DIR
from src.core.asset_loader import play_music, stop_music
from src.entities.player import Player
from src.scenes.scene1_grotto import Scene1Grotto
from src.scenes.scene2_skybloom import Scene2Skybloom
from src.scenes.scene3_spire import Scene3Spire
from src.scenes.scene4_radiance import Scene4Radiance
from src.scenes.intro_scene import IntroScene
from src.ui.menus import MainMenu, PauseMenu, GameOverMenu, VictoryMenu, TextCard

STATE_INTRO = "intro"
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_TEXT_CARD = "text_card"
STATE_GAME_OVER = "game_over"
STATE_VICTORY = "victory"

SCENE_SEQUENCE = [
    (Scene1Grotto, "Scene 1 complete! The Skybloom Reach awaits..."),
    (Scene2Skybloom, "Scene 2 complete! The Hollow Spire awaits..."),
    (Scene3Spire, "Scene 3 complete! Only The Last Radiance remains..."),
    (Scene4Radiance, None),  # last scene — completing it goes to STATE_VICTORY, not a text card
]


class SceneManager:
    def __init__(self):
        self.state = STATE_MENU
        self.intro_scene = None  # created fresh each time "Start" is pressed, see _start_intro()
        self.main_menu = MainMenu()
        self.pause_menu = PauseMenu()
        self.game_over_menu = GameOverMenu()
        self.victory_menu = VictoryMenu()
        self.text_card = None

        self.player = None
        self.current_scene = None
        self.scene_index = 0
        self.elapsed_time = 0.0  # gameplay seconds, shown on the victory screen
        self.should_quit = False  # Game.run() checks this to end the main loop

        self._play_menu_music()

    # --- Music -----------------------------------------------------------------
    # Every track is looked up by a fixed filename in MUSIC_DIR — none of
    # these exist yet (Step 10 of the brief), so play_music() just prints
    # its usual one-time MISSING warning and no-ops until real tracks are
    # dropped in, same as every other not-yet-sourced asset in this project.

    def _play_menu_music(self):
        play_music(MUSIC_DIR / "menu_theme.mp3")

    def _play_intro_music(self):
        play_music(MUSIC_DIR / "intro_theme.mp3")

    def _play_scene_music(self, index):
        play_music(MUSIC_DIR / f"scene{index + 1}_theme.mp3")

    def _play_victory_music(self):
        play_music(MUSIC_DIR / "victory_theme.mp3")

    def _play_game_over_music(self):
        play_music(MUSIC_DIR / "game_over_theme.mp3", loops=0)

    # --- Starting / restarting ---------------------------------------------

    def _start_intro(self):
        """Main menu's "Start" button -> play the opening story cutscene,
        then continue straight into Scene 1 (see update()'s STATE_INTRO
        branch) once it finishes or is skipped. A fresh IntroScene each
        time so its internal timers/fades always start from zero."""
        self._play_intro_music()
        self.intro_scene = IntroScene()
        self.state = STATE_INTRO

    def _start_scene(self, index):
        self.scene_index = index
        scene_class, _ = SCENE_SEQUENCE[index]
        self.current_scene = scene_class(self.player)
        self._play_scene_music(index)

    def _start_new_game(self, scene_index=0):
        """scene_index lets the main menu act as a scene select — a
        fresh player always starts at PLAYER_START_LIVES/max HP, but
        abilities unlocked by earlier scenes (e.g. Lumen Bloom, which
        Scene 1's shard pickup grants) won't be present if a later
        scene is picked directly. That's an accepted tradeoff of direct
        scene select, not a bug."""
        self.player = Player(x=0, y=0)
        self.player.lives = PLAYER_START_LIVES
        self.elapsed_time = 0.0
        self._start_scene(scene_index)
        self.state = STATE_PLAYING

    def _restart_current_scene(self):
        """Game Over -> restart the scene Iris died in, with fresh lives
        and HP (PROJECT_BRIEF.md section 4)."""
        self.player.lives = PLAYER_START_LIVES
        self.player.hp = self.player.max_hp
        self.player.is_dead = False
        self._start_scene(self.scene_index)
        self.state = STATE_PLAYING

    def _exit_to_menu(self):
        """Pause menu -> abandon the current run and return to the main
        menu's scene select, same as closing and reopening the game."""
        self.current_scene = None
        self.player = None
        self.main_menu.selected_index = 0
        self.state = STATE_MENU
        self._play_menu_music()

    # --- Input ---------------------------------------------------------------

    def handle_event(self, event):
        if self.state == STATE_INTRO:
            self.intro_scene.handle_event(event)
        elif self.state == STATE_MENU:
            action = self.main_menu.handle_event(event)
            if action == "quit":
                self.should_quit = True
            elif action == "start":
                self._start_intro()
            elif isinstance(action, int):
                self._start_new_game(scene_index=action)
        elif self.state == STATE_PLAYING:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.pause_menu.selected_index = 0
                self.state = STATE_PAUSED
            else:
                self.current_scene.handle_event(event)
        elif self.state == STATE_PAUSED:
            action = self.pause_menu.handle_event(event)
            if action == "resume":
                self.state = STATE_PLAYING
            elif action == "exit":
                self._exit_to_menu()
        elif self.state == STATE_TEXT_CARD:
            if self.text_card.handle_event(event):
                self._advance_to_next_scene()
        elif self.state == STATE_GAME_OVER:
            if self.game_over_menu.handle_event(event):
                self._restart_current_scene()
        elif self.state == STATE_VICTORY:
            if self.victory_menu.handle_event(event):
                self.state = STATE_MENU
                self._play_menu_music()

    # --- Update ----------------------------------------------------------------

    def update(self, dt):
        if self.state == STATE_INTRO:
            self.intro_scene.update(dt)
            if self.intro_scene.finished:
                # Intro is only ever reached via "Start" -> continue
                # straight into a fresh playthrough from Scene 1.
                self._start_new_game(scene_index=0)
        elif self.state == STATE_PLAYING:
            self.elapsed_time += dt
            keys = pygame.key.get_pressed()
            self.current_scene.update(dt, keys)
            self._check_scene_events()
        elif self.state == STATE_TEXT_CARD:
            self.text_card.update(dt)
            if self.text_card.done:
                self._advance_to_next_scene()

    def _check_scene_events(self):
        if self.player.is_dead:
            self._on_player_death()
        elif self.current_scene.finished and self.current_scene.transition.covered:
            # The wipe holds fully covered here rather than auto-revealing
            # (see effects/transitions.py) — that hold is exactly the
            # moment to swap to the text card, which also draws a full
            # black screen, so the cut is seamless.
            self._on_scene_complete()

    def _on_player_death(self):
        self.player.lives -= 1
        if self.player.lives > 0:
            self.player.respawn(self.current_scene.respawn_point)
        else:
            self.state = STATE_GAME_OVER
            self._play_game_over_music()

    def _on_scene_complete(self):
        _, narrative_text = SCENE_SEQUENCE[self.scene_index]
        if narrative_text is None:
            # The last scene (Scene 4) has no "next scene" text card —
            # completing it goes straight to the victory screen.
            self.state = STATE_VICTORY
            self._play_victory_music()
        else:
            # Silence during the narrative beat rather than letting the
            # finished scene's track keep playing under it — the next
            # scene's music picks up once _advance_to_next_scene() starts it.
            stop_music()
            self.text_card = TextCard(narrative_text)
            self.state = STATE_TEXT_CARD

    def _advance_to_next_scene(self):
        next_index = self.scene_index + 1
        if next_index < len(SCENE_SEQUENCE):
            self._start_scene(next_index)
            self.state = STATE_PLAYING
        else:
            # Unreachable in normal play (the last scene routes straight
            # to STATE_VICTORY above, never through a text card) — kept
            # as a safe fallback rather than assuming that can't change.
            self.state = STATE_MENU
            self._play_menu_music()

    # --- Draw --------------------------------------------------------------------

    def draw(self, surface):
        if self.state == STATE_INTRO:
            self.intro_scene.draw(surface)
        elif self.state == STATE_MENU:
            self.main_menu.draw(surface)
        elif self.state == STATE_PLAYING:
            self.current_scene.draw(surface)
        elif self.state == STATE_PAUSED:
            self.current_scene.draw(surface)
            self.pause_menu.draw(surface)
        elif self.state == STATE_TEXT_CARD:
            self.text_card.draw(surface)
        elif self.state == STATE_GAME_OVER:
            self.game_over_menu.draw(surface)
        elif self.state == STATE_VICTORY:
            self.victory_menu.draw(surface, completion_time=self.elapsed_time, token_count=self.player.token_count)

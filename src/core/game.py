"""
game.py

The Game class owns the window, the clock, and the main loop. It is the
one place that calls pygame.init()/pygame.quit() and drives everything
else (menus, scenes, input, drawing) frame by frame.
"""

import pygame

from config.settings import SCREEN_W, SCREEN_H, FPS, GAME_TITLE
from src.core.scene_manager import SceneManager


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(GAME_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True

        self.scene_manager = SceneManager()

    def run(self):
        """Main game loop: handle input, update game state, draw, repeat."""
        while self.running:
            # dt = seconds since last frame, so cooldowns/animations/hazard
            # damage stay paced to real time regardless of frame rate.
            dt = self.clock.tick(FPS) / 1000.0

            self._handle_events()
            if self.scene_manager.should_quit:
                self.running = False
                continue
            self.scene_manager.update(dt)
            self.scene_manager.draw(self.screen)
            pygame.display.flip()

        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            else:
                self.scene_manager.handle_event(event)

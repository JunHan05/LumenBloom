"""
camera.py

Horizontal scroll camera: keeps Iris roughly centred on screen while
clamping to the level's edges, and layers in screen-shake offset from
effects/transitions.py's ScreenShake.
"""

from config.settings import SCREEN_W, SCREEN_H


class Camera:
    def __init__(self, level_width, level_height=SCREEN_H):
        self.level_width = level_width
        self.level_height = level_height
        self.offset_x = 0
        self.offset_y = 0
        self.shake = None  # optional ScreenShake instance, set by the scene

    def update(self, target_rect):
        max_offset_x = max(0, self.level_width - SCREEN_W)
        self.offset_x = max(0, min(target_rect.centerx - SCREEN_W // 2, max_offset_x))

        max_offset_y = max(0, self.level_height - SCREEN_H)
        self.offset_y = max(0, min(target_rect.centery - SCREEN_H // 2, max_offset_y))

    def get_offset(self):
        shake_x, shake_y = self.shake.get_offset() if self.shake else (0, 0)
        return (self.offset_x + shake_x, self.offset_y + shake_y)

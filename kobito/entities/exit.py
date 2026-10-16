"""The way back up from a hidden underground stage.

Like the castle Goal it isn't solid: the player walks into it and Game
sends them back to the surface, just past the gap they fell through.
One look per stage:
  * subway -- a station staircase with green globe lamps and an EXIT sign
  * sewer  -- a ladder up to an open manhole, street light pouring down
  * mine   -- a timber-framed lift cage on a rope
Every one carries the word 出口 (でぐち, "exit").
"""

import pygame

from kobito.fonts import pixel_font

WIDTH, HEIGHT = 120, 200
INK = (24, 18, 20)


class Exit(pygame.sprite.Sprite):
    def __init__(self, x, ground_y, style):
        super().__init__()
        self.style = style
        self.image = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        getattr(self, f"_draw_{style}")()
        self.rect = self.image.get_rect(bottomleft=(x, ground_y))

    def _sign(self, center, bg=(0, 110, 60)):
        rect = pygame.Rect(0, 0, 76, 36)
        rect.center = center
        pygame.draw.rect(self.image, INK, rect.inflate(4, 4), border_radius=5)
        pygame.draw.rect(self.image, bg, rect, border_radius=4)
        font = pixel_font(16)
        for text, dy in (("出口", -8), ("EXIT", 8)):
            label = font.render(text, True, (255, 255, 255))
            self.image.blit(label, label.get_rect(center=(rect.centerx, rect.centery + dy)))

    def _draw_subway(self):
        s = self.image
        # Stairwell: dark opening with steps climbing to the right.
        well = pygame.Rect(10, 70, 100, 130)
        pygame.draw.rect(s, (30, 28, 34), well)
        for i in range(8):
            y = well.bottom - 14 - i * 14
            pygame.draw.rect(s, (150, 150, 160), (well.x + i * 12, y, well.right - well.x - i * 12, 5))
        pygame.draw.rect(s, (226, 222, 206), (well.x - 6, 64, well.width + 12, 10))
        # Green railings and globe lamps on posts.
        for px in (8, 112):
            pygame.draw.rect(s, (30, 90, 60), (px - 3, 30, 6, 170))
            pygame.draw.circle(s, INK, (px, 26), 13)
            pygame.draw.circle(s, (90, 210, 120), (px, 26), 11)
            pygame.draw.circle(s, (210, 255, 220), (px - 3, 22), 4)
        self._sign((WIDTH // 2, 44))

    def _draw_sewer(self):
        s = self.image
        light = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(light, (255, 250, 200, 70), [(38, 0), (82, 0), (100, HEIGHT), (20, HEIGHT)])
        s.blit(light, (0, 0))
        pygame.draw.ellipse(s, INK, (30, 0, 60, 16))
        pygame.draw.ellipse(s, (250, 246, 210), (34, 2, 52, 12))
        for rx in (42, 78):                                              # ladder rails
            pygame.draw.rect(s, (140, 140, 150), (rx - 3, 8, 6, HEIGHT - 8))
            pygame.draw.rect(s, INK, (rx - 3, 8, 6, HEIGHT - 8), width=1)
        for y in range(24, HEIGHT, 20):
            pygame.draw.rect(s, (170, 170, 180), (42, y, 36, 4))
        self._sign((WIDTH // 2, 120), bg=(40, 120, 80))

    def _draw_mine(self):
        s = self.image
        pygame.draw.line(s, (180, 150, 100), (WIDTH // 2, 0), (WIDTH // 2, 70), 3)     # rope
        for px in (12, 108):                                                       # timber frame
            pygame.draw.rect(s, (104, 70, 40), (px - 8, 20, 16, HEIGHT - 20))
            pygame.draw.rect(s, (134, 94, 56), (px - 8, 20, 5, HEIGHT - 20))
        pygame.draw.rect(s, (104, 70, 40), (0, 14, WIDTH, 14))
        cage = pygame.Rect(26, 70, 68, 130)
        pygame.draw.rect(s, (40, 34, 30), cage)
        for x in range(cage.x, cage.right + 1, 11):
            pygame.draw.line(s, (150, 150, 160), (x, cage.y), (x, cage.bottom), 2)
        for y in (cage.y, cage.y + 64, cage.bottom - 3):
            pygame.draw.rect(s, (170, 170, 180), (cage.x - 2, y, cage.width + 4, 4))
        self._sign((WIDTH // 2, 48), bg=(150, 90, 30))

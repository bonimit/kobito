"""The way out of an underground room: the rope (or ladder) hanging down
through the hole the player fell in by.

It isn't solid. Walk up to it and hold up / jump to climb (kobito/entities/
player.py, Player.rope); climb out of the top and Game brings the player
back up at the pit they dropped into. One look per style:
  * subway -- a steel maintenance ladder, yellow-and-black at the foot
  * sewer  -- a rusty rung ladder up to the manhole
  * mine   -- a knotted hemp rope
A little plate on it says 出口 ↑ (でぐち, "exit") and のぼる ("climb").
"""

import pygame

from kobito.fonts import pixel_font

WIDTH = 96
INK = (24, 18, 20)


class ClimbRope(pygame.sprite.Sprite):
    def __init__(self, center_x, ground_y, style):
        super().__init__()
        self.style = style
        self.image = pygame.Surface((WIDTH, ground_y), pygame.SRCALPHA)
        getattr(self, f"_draw_{style}")(ground_y)
        self._plate(ground_y - 132)
        self.rect = self.image.get_rect(midtop=(center_x, 0))

    def _ladder(self, height, rail, rung, spacing=18):
        s, cx = self.image, WIDTH // 2
        for rx in (cx - 16, cx + 16):
            pygame.draw.rect(s, INK, (rx - 4, 0, 8, height))
            pygame.draw.rect(s, rail, (rx - 3, 0, 6, height))
        for y in range(10, height, spacing):
            pygame.draw.rect(s, INK, (cx - 16, y - 1, 32, 6))
            pygame.draw.rect(s, rung, (cx - 15, y, 30, 4))

    def _draw_subway(self, height):
        self._ladder(height, (150, 156, 166), (190, 194, 204))
        cx = WIDTH // 2
        for i, y in enumerate(range(height - 60, height, 12)):     # hazard stripes at the foot
            for rx in (cx - 16, cx + 16):
                pygame.draw.rect(self.image, (240, 200, 60) if i % 2 else (30, 30, 34), (rx - 3, y, 6, 12))

    def _draw_sewer(self, height):
        self._ladder(height, (120, 104, 84), (156, 128, 96), spacing=20)

    def _draw_mine(self, height):
        s, cx = self.image, WIDTH // 2
        pygame.draw.rect(s, INK, (cx - 5, 0, 10, height))
        pygame.draw.rect(s, (196, 160, 104), (cx - 4, 0, 8, height))
        for y in range(0, height, 8):                                  # twist of the strands
            pygame.draw.line(s, (150, 116, 70), (cx - 4, y), (cx + 3, y + 6), 2)
        for y in range(40, height - 10, 44):                           # knots to hold on to
            pygame.draw.ellipse(s, INK, (cx - 9, y - 7, 18, 16))
            pygame.draw.ellipse(s, (210, 176, 118), (cx - 7, y - 5, 14, 12))

    def _plate(self, y):
        rect = pygame.Rect(0, 0, 72, 40)
        rect.midtop = (WIDTH // 2, y)
        pygame.draw.rect(self.image, INK, rect.inflate(4, 4), border_radius=6)
        pygame.draw.rect(self.image, (0, 110, 60), rect, border_radius=5)
        font = pixel_font(16)
        for text, dy in (("出口 ↑", -9), ("のぼる", 9)):
            label = font.render(text, True, (255, 255, 255))
            self.image.blit(label, label.get_rect(center=(rect.centerx, rect.centery + dy)))

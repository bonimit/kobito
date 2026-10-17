"""The way out of a hidden stage -- back up from underground, or back
down from the sky.

Like the castle Goal it isn't solid: the player walks into it and Game
sends them back to the surface, just past the gap they fell through.
One look per stage:
  * subway -- a station staircase with green globe lamps and an EXIT sign
  * sewer  -- a ladder up to an open manhole, street light pouring down
  * mine   -- a timber-framed lift cage on a rope
The hidden sky stages have their own ways back down:
  * rainbow -- a rainbow slide
  * thunder -- a giant lightning bolt to ride
  * moon    -- a vermilion torii gate in the moonlight
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

    # -- Sky stages: the way back down ------------------------------------------

    def _draw_rainbow(self):
        """A rainbow arch standing on the cloud -- step through it to slide down."""
        s = self.image
        colors = [(232, 72, 72), (246, 150, 60), (250, 220, 80), (110, 200, 100), (80, 160, 230), (140, 110, 210)]
        center = (WIDTH // 2, HEIGHT)
        pygame.draw.circle(s, INK, center, 60, width=46)
        for i, color in enumerate(colors):
            pygame.draw.circle(s, color, center, 58 - i * 7, width=7)
        pygame.draw.rect(s, (0, 0, 0, 0), (0, HEIGHT - 1, WIDTH, 1))
        self._sign((WIDTH // 2, HEIGHT - 86), bg=(200, 90, 150))

    def _draw_thunder(self):
        """A giant golden lightning bolt stuck into the cloud -- ride it down."""
        s = self.image
        bolt = [(70, 0), (34, 92), (60, 92), (40, HEIGHT), (96, 76), (68, 76), (92, 0)]
        pygame.draw.polygon(s, INK, bolt)
        inner = [(x + (2 if x < 60 else -2), y + (3 if y == 0 else 0)) for x, y in bolt]
        pygame.draw.polygon(s, (255, 214, 60), inner)
        pygame.draw.line(s, (255, 248, 190), (78, 6), (50, 84), 3)
        self._sign((WIDTH // 2, 132), bg=(90, 90, 140))

    def _draw_moon(self):
        """A vermilion torii on the cloud, glowing in the moonlight."""
        s = self.image
        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 240, 190, 60), (6, 40, WIDTH - 12, HEIGHT - 30))
        s.blit(glow, (0, 0))
        red, dark = (214, 64, 50), (150, 40, 34)
        pygame.draw.rect(s, red, (24, 60, 12, HEIGHT - 60))
        pygame.draw.rect(s, red, (84, 60, 12, HEIGHT - 60))
        pygame.draw.polygon(s, INK, [(4, 40), (116, 40), (110, 54), (10, 54)])         # kasagi
        pygame.draw.polygon(s, (40, 34, 40), [(6, 42), (114, 42), (109, 52), (11, 52)])
        pygame.draw.rect(s, red, (14, 64, 92, 9))                                        # nuki
        pygame.draw.rect(s, dark, (24, 60, 12, 6))
        pygame.draw.rect(s, dark, (84, 60, 12, 6))
        self._sign((WIDTH // 2, 112), bg=(110, 80, 160))

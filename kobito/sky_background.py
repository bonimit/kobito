"""Backdrops for the hidden sky stages (kobito/levels/sky.py).

  * rainbow -- a bright pastel sky with giant rainbows and puffy cloud banks
  * thunder -- a dark storm: rolling grey cloud banks, slanting rain,
               lightning that flashes the whole sky, and the thunder god
               Raijin's ring of taiko drums floating in the distance
  * moon    -- a night sky full of twinkling stars and a huge full moon with
               the moon rabbit pounding mochi, lavender clouds lit from above

Each also has a "sea of clouds" far below -- the way back down if you fall.
Purely decorative: update(dt), then draw().
"""

import math
import random

import pygame

from kobito.constants import SCREEN_HEIGHT, SCREEN_WIDTH

GRADIENTS = {
    "rainbow": ((118, 194, 255), (255, 228, 242)),
    "thunder": ((44, 48, 78), (112, 118, 152)),
    "moon": ((10, 14, 44), (62, 46, 104)),
}
BANK_COLORS = {
    "rainbow": [(196, 222, 252), (222, 236, 255)],
    "thunder": [(80, 84, 112), (104, 108, 136)],
    "moon": [(70, 62, 120), (104, 92, 160)],
}
RAINBOW = [(232, 72, 72), (246, 150, 60), (250, 220, 80), (110, 200, 100), (80, 160, 230), (110, 100, 210),
           (170, 110, 210)]


def _gradient(top, bottom):
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        t = y / (SCREEN_HEIGHT - 1)
        pygame.draw.line(surface, [round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)], (0, y), (SCREEN_WIDTH, y))
    return surface


class SkyBackground:
    def __init__(self, level_width, style, seed=5):
        self.level_width = level_width
        self.style = style
        self.time = 0.0
        rng = random.Random(seed)
        self.sky = _gradient(*GRADIENTS[style])
        # Two parallax banks of clouds: (parallax, y, [(x, radius)]).
        self.banks = []
        for depth, (parallax, base_y) in enumerate(((0.2, 330), (0.45, 420))):
            puffs, x = [], -100
            while x < level_width + SCREEN_WIDTH:
                puffs.append((x, rng.randint(40, 80)))
                x += rng.randint(50, 90)
            self.banks.append((parallax, base_y, BANK_COLORS[style][depth], puffs))
        self.sea = [(x, rng.randint(26, 44)) for x in range(-60, SCREEN_WIDTH + 120, 46)]
        getattr(self, f"_init_{style}")(rng)

    def update(self, dt):
        self.time += dt

    def draw(self, screen, camera_x):
        screen.blit(self.sky, (0, 0))
        getattr(self, f"_draw_far_{self.style}")(screen, camera_x)
        for parallax, base_y, color, puffs in self.banks:
            span = self.level_width + SCREEN_WIDTH
            for x, r in puffs:
                sx = (x - camera_x * parallax) % span - 100
                if -r < sx < SCREEN_WIDTH + r:
                    pygame.draw.circle(screen, color, (sx, base_y), r)
            pygame.draw.rect(screen, color, (0, base_y, SCREEN_WIDTH, SCREEN_HEIGHT - base_y))
        getattr(self, f"_draw_near_{self.style}")(screen, camera_x)
        self._draw_sea(screen, camera_x)

    def _draw_sea(self, screen, camera_x):
        """The sea of clouds far below -- drifting slowly, the way down."""
        color = {"rainbow": (255, 255, 255), "thunder": (130, 134, 160), "moon": (130, 118, 186)}[self.style]
        drift = (self.time * 12 + camera_x * 0.7) % 46
        for x, r in self.sea:
            pygame.draw.circle(screen, color, (x - drift, SCREEN_HEIGHT + 4), r)

    # -- Rainbow ------------------------------------------------------------------

    def _init_rainbow(self, rng):
        self.sparkles = [(rng.randrange(self.level_width), rng.randrange(60, 320), rng.uniform(0, 6.3))
                         for _ in range(40)]

    def _draw_far_rainbow(self, screen, camera_x):
        # Giant rainbows, one every 1100 px of the far layer.
        span = 1100
        offset = -(camera_x * 0.15) % span
        for k in range(-1, 3):
            cx = offset + k * span + 300
            for i, color in enumerate(RAINBOW):
                r = 330 - i * 16
                pygame.draw.circle(screen, color, (cx, 470), r, width=16)
            pygame.draw.circle(screen, GRADIENTS["rainbow"][1], (cx, 470), 330 - len(RAINBOW) * 16)

    def _draw_near_rainbow(self, screen, camera_x):
        for x, y, phase in self.sparkles:
            sx = x - camera_x * 0.6
            if -10 < sx < SCREEN_WIDTH + 10:
                a = 0.5 + 0.5 * math.sin(self.time * 3 + phase)
                size = 2 + round(3 * a)
                pygame.draw.line(screen, (255, 255, 255), (sx - size, y), (sx + size, y), 2)
                pygame.draw.line(screen, (255, 255, 255), (sx, y - size), (sx, y + size), 2)

    # -- Thunder ------------------------------------------------------------------

    def _init_thunder(self, rng):
        self.rain = [(rng.randrange(SCREEN_WIDTH), rng.randrange(SCREEN_HEIGHT), rng.uniform(0.8, 1.2))
                     for _ in range(90)]
        self.flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.flash.fill((236, 236, 255))
        self.bolt_seed = 0

    def _draw_far_thunder(self, screen, camera_x):
        # Raijin's ring of drums, far away.
        cx = SCREEN_WIDTH * 1.1 - (camera_x * 0.08) % (SCREEN_WIDTH * 1.4)
        cy = 250
        pygame.draw.circle(screen, (66, 70, 100), (cx, cy), 92, width=6)
        for i in range(8):
            a = i * math.pi / 4 + self.time * 0.15
            dx, dy = cx + math.cos(a) * 92, cy + math.sin(a) * 92
            pygame.draw.circle(screen, (96, 70, 70), (dx, dy), 17)
            pygame.draw.circle(screen, (150, 120, 90), (dx, dy), 12)
            pygame.draw.circle(screen, (200, 60, 50), (dx, dy), 5)       # a little tomoe mark
        # Lightning: every few seconds a bolt and a flash.
        cycle = self.time % 4.2
        if cycle < 0.22:
            rng = random.Random(int(self.time // 4.2))
            x = rng.randrange(120, SCREEN_WIDTH - 120)
            points, y = [(x, 0)], 0
            while y < 380:
                y += rng.randint(30, 60)
                x += rng.randint(-40, 40)
                points.append((x, y))
            pygame.draw.lines(screen, (255, 250, 200), False, points, 5)
            pygame.draw.lines(screen, (255, 255, 255), False, points, 2)
            self.flash.set_alpha(round(110 * (1 - cycle / 0.22)))
            screen.blit(self.flash, (0, 0))

    def _draw_near_thunder(self, screen, camera_x):
        for x, y, speed in self.rain:
            sx = (x - camera_x * 0.9 - self.time * 120) % SCREEN_WIDTH
            sy = (y + self.time * 620 * speed) % SCREEN_HEIGHT
            pygame.draw.line(screen, (170, 180, 220), (sx, sy), (sx - 6, sy + 16), 1)

    # -- Moon ---------------------------------------------------------------------

    def _init_moon(self, rng):
        self.stars = [(rng.randrange(self.level_width + SCREEN_WIDTH), rng.randrange(10, 330), rng.uniform(0, 6.3),
                       rng.choice((1, 1, 2))) for _ in range(150)]
        self.moon = self._build_moon()

    @staticmethod
    def _build_moon():
        size = 220
        moon = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        for r in range(c, 70, -6):                                          # halo
            pygame.draw.circle(moon, (255, 246, 200, round(40 * (1 - (r - 70) / (c - 70)))), (c, c), r)
        pygame.draw.circle(moon, (255, 244, 196), (c, c), 70)
        for dx, dy, r in ((-24, -20, 12), (18, 22, 9), (26, -14, 7), (-8, 30, 6)):
            pygame.draw.circle(moon, (236, 222, 168), (c + dx, c + dy), r)
        # The moon rabbit pounding mochi (a silhouette, as seen in Japan).
        ink = (214, 198, 140)
        pygame.draw.ellipse(moon, ink, (c - 30, c - 4, 26, 22))              # body
        pygame.draw.circle(moon, ink, (c - 22, c - 10), 8)                   # head
        pygame.draw.ellipse(moon, ink, (c - 28, c - 34, 6, 22))              # ears
        pygame.draw.ellipse(moon, ink, (c - 20, c - 34, 6, 22))
        pygame.draw.line(moon, ink, (c - 6, c + 2), (c + 16, c - 18), 4)     # mallet
        pygame.draw.rect(moon, ink, (c + 12, c - 24, 14, 10), border_radius=3)
        pygame.draw.ellipse(moon, ink, (c + 4, c + 10, 30, 16))              # mortar
        return moon

    def _draw_far_moon(self, screen, camera_x):
        span = self.level_width + SCREEN_WIDTH
        for x, y, phase, size in self.stars:
            sx = (x - camera_x * 0.1) % span
            if sx < SCREEN_WIDTH:
                a = 0.55 + 0.45 * math.sin(self.time * 2.2 + phase)
                shade = round(150 + 105 * a)
                pygame.draw.circle(screen, (shade, shade, min(255, shade + 20)), (sx, y), size)
        # Hung in the open middle of the sky, clear of the HUD cards.
        screen.blit(self.moon, (SCREEN_WIDTH // 2 - 40 - (camera_x * 0.03) % 60, 48))

    def _draw_near_moon(self, screen, camera_x):
        pass

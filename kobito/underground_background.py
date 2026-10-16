"""Backdrops for the hidden underground stages.

Three styles, each built from a pre-rendered far wall (scrolls at half
speed, so the room has depth) plus a near layer drawn every frame:

  * subway -- an NYC station: white subway tile, a maroon mosaic name band,
              steel columns, coloured line signs, fluorescent tubes, and a
              silver train rattling past on the far track now and then.
  * sewer  -- a turtle-hideout style sewer: wet green brick, arched
              tunnels with murky water, big pipes with valve wheels, light
              falling through street grates, dripping water.
  * mine   -- an old mine: rough rock with glittering crystals and gold
              veins, timber support frames, flickering lanterns, a cart
              track along the back wall.

All of them have a ceiling with a hole where the player drops in.
Purely decorative, like kobito/background.py: update(dt), then draw().
"""

import math
import random

import pygame

from kobito.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import pixel_font

FAR_TILE_W = 480
FAR_PARALLAX = 0.5
CEILING_H = 44


def _glow(radius, color, strength=150):
    """A soft round light: stacked circles, brightest in the middle."""
    surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -2):
        alpha = round(strength * (1 - i / radius) ** 1.6)
        pygame.draw.circle(surface, (*color, alpha), (radius, radius), i)
    return surface


class UndergroundBackground:
    def __init__(self, level_width, ground_y, style, entry_x, seed=3):
        self.level_width = level_width
        self.ground_y = ground_y
        self.style = style
        self.entry_x = entry_x
        self.time = 0.0
        self.rng = random.Random(seed)
        self.far = getattr(self, f"_build_far_{style}")()
        getattr(self, f"_init_{style}")()
        self.beam = self._build_beam()

    def update(self, dt):
        self.time += dt

    def draw(self, screen, camera_x):
        offset = -((camera_x * FAR_PARALLAX) % FAR_TILE_W)
        x = offset
        while x < SCREEN_WIDTH:
            screen.blit(self.far, (x, 0))
            x += FAR_TILE_W
        getattr(self, f"_draw_{self.style}")(screen, camera_x)
        self._draw_ceiling(screen, camera_x)

    # -- Shared ---------------------------------------------------------------

    def _visible(self, spacing, camera_x, margin=120, start=0):
        """World x positions every `spacing` px that are on screen."""
        first = int((camera_x - margin - start) // spacing)
        x = start + first * spacing
        while x - camera_x < SCREEN_WIDTH + margin:
            if x >= start - margin:
                yield x
            x += spacing

    def _build_beam(self):
        """The shaft of light under the hole the player fell through."""
        w, h = 120, self.ground_y - CEILING_H
        beam = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            half = 26 + y * 0.09
            alpha = round(70 * (1 - y / h))
            pygame.draw.line(beam, (255, 246, 200, alpha), (w / 2 - half, y), (w / 2 + half, y))
        return beam

    def _draw_ceiling(self, screen, camera_x):
        colors = {"subway": ((44, 46, 52), (70, 72, 80)), "sewer": ((40, 50, 44), (62, 76, 66)),
                  "mine": ((40, 30, 26), (66, 50, 40))}[self.style]
        pygame.draw.rect(screen, colors[0], (0, 0, SCREEN_WIDTH, CEILING_H))
        pygame.draw.rect(screen, colors[1], (0, CEILING_H - 6, SCREEN_WIDTH, 6))
        if self.style == "mine":   # stalactites
            for x in self._visible(70, camera_x, start=17):
                sx = x - camera_x
                length = 10 + (x * 7) % 18
                pygame.draw.polygon(screen, colors[0], [(sx - 9, CEILING_H - 2), (sx + 9, CEILING_H - 2), (sx, CEILING_H + length)])
        # The hole the player came through, with daylight pouring in.
        hx = self.entry_x - camera_x
        if -100 < hx < SCREEN_WIDTH + 100:
            pygame.draw.rect(screen, (250, 240, 200), (hx - 28, 0, 56, CEILING_H))
            pygame.draw.rect(screen, (20, 16, 20), (hx - 32, CEILING_H - 6, 64, 6))
            screen.blit(self.beam, (hx - self.beam.get_width() / 2, CEILING_H))

    # -- NYC subway -----------------------------------------------------------

    LINES = [("1", (238, 53, 46)), ("A", (0, 57, 166)), ("N", (252, 204, 10)), ("4", (0, 147, 60)),
             ("7", (185, 51, 173)), ("L", (167, 169, 172))]

    def _build_far_subway(self):
        s = pygame.Surface((FAR_TILE_W, SCREEN_HEIGHT))
        s.fill((34, 32, 36))
        wall = pygame.Rect(0, CEILING_H, FAR_TILE_W, 352 - CEILING_H)
        s.fill((226, 222, 206), wall)
        for row, y in enumerate(range(wall.y, wall.bottom, 12)):          # running-bond tile
            pygame.draw.line(s, (196, 192, 176), (0, y), (FAR_TILE_W, y))
            for x in range(-24 + (row % 2) * 12, FAR_TILE_W, 24):
                pygame.draw.line(s, (196, 192, 176), (x, y), (x, y + 12))
        # Mosaic name band with a gold border, as in the old IRT stations.
        band = pygame.Rect(0, 128, FAR_TILE_W, 50)
        s.fill((128, 40, 50), band)
        for y in (band.y, band.bottom - 4):
            s.fill((206, 170, 90), (0, y, FAR_TILE_W, 4))
        for x in range(0, FAR_TILE_W, 8):
            s.fill((150, 56, 62) if (x // 8) % 2 else (116, 34, 44), (x, band.y + 4, 8, 4))
        font = pixel_font(32)
        name = font.render("TIMES SQ - 42 ST", True, (250, 246, 230))
        s.blit(name, name.get_rect(center=(FAR_TILE_W // 2, band.centery + 2)))
        # Dado: a strip of darker tile above the far track.
        s.fill((150, 92, 70), (0, 300, FAR_TILE_W, 52))
        for x in range(0, FAR_TILE_W, 24):
            pygame.draw.line(s, (124, 74, 56), (x, 300), (x, 352))
        # The far track bed.
        s.fill((26, 24, 28), (0, 352, FAR_TILE_W, self.ground_y - 352))
        for x in range(0, FAR_TILE_W, 26):
            s.fill((60, 46, 36), (x, 456, 16, 6))
        for y in (452, 466):
            s.fill((140, 140, 150), (0, y, FAR_TILE_W, 3))
        return s

    def _init_subway(self):
        self.train_period = 7.5
        self.train_cars = 4
        self.fluorescent = _glow(46, (230, 245, 255), 90)

    def _draw_train(self, screen):
        cycle = self.time % self.train_period
        run_time = 2.6
        if cycle > run_time:
            return
        car_w, gap = 300, 10
        total = self.train_cars * (car_w + gap)
        rightward = int(self.time // self.train_period) % 2 == 0
        progress = cycle / run_time
        x0 = -total + progress * (SCREEN_WIDTH + total) if rightward else SCREEN_WIDTH - progress * (SCREEN_WIDTH + total)
        top = 318
        for car in range(self.train_cars):
            x = x0 + car * (car_w + gap)
            body = pygame.Rect(round(x), top, car_w, 132)
            pygame.draw.rect(screen, (174, 180, 190), body, border_radius=10)
            for rib in range(body.x + 8, body.right - 8, 6):
                pygame.draw.line(screen, (150, 156, 166), (rib, body.y + 88), (rib, body.bottom - 8))
            for wx in range(body.x + 22, body.right - 40, 46):
                pygame.draw.rect(screen, (250, 232, 160), (wx, body.y + 22, 32, 40), border_radius=4)
                pygame.draw.rect(screen, (60, 62, 70), (wx, body.y + 22, 32, 40), width=3, border_radius=4)
            pygame.draw.rect(screen, (0, 147, 60), (body.x, body.y + 74, car_w, 6))
            pygame.draw.circle(screen, (0, 147, 60), (body.right - 26, body.y + 40), 13)
            label = pixel_font(16).render("4", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=(body.right - 26, body.y + 41)))
            pygame.draw.rect(screen, (90, 92, 100), body, width=3, border_radius=10)

    def _draw_subway(self, screen, camera_x):
        self._draw_train(screen)
        # Fluorescent tubes along the ceiling.
        for x in self._visible(192, camera_x, start=60):
            sx = x - camera_x
            screen.blit(self.fluorescent, (sx - 46, CEILING_H - 30))
            pygame.draw.rect(screen, (240, 250, 255), (sx - 30, CEILING_H, 60, 5), border_radius=2)
        # Steel columns with rivets.
        for x in self._visible(256, camera_x, start=128):
            sx = x - camera_x
            pygame.draw.rect(screen, (34, 64, 74), (sx - 10, CEILING_H, 20, self.ground_y - CEILING_H))
            pygame.draw.rect(screen, (60, 98, 110), (sx - 10, CEILING_H, 5, self.ground_y - CEILING_H))
            pygame.draw.rect(screen, (24, 46, 54), (sx - 16, CEILING_H, 32, 10))
            for y in range(CEILING_H + 30, self.ground_y, 40):
                pygame.draw.circle(screen, (90, 130, 140), (sx, y), 2)
        # Hanging line signs.
        for i, x in enumerate(self._visible(512, camera_x, start=256)):
            sx = x - camera_x
            pygame.draw.line(screen, (30, 30, 34), (sx - 30, CEILING_H), (sx - 30, 200), 2)
            pygame.draw.line(screen, (30, 30, 34), (sx + 30, CEILING_H), (sx + 30, 200), 2)
            sign = pygame.Rect(0, 0, 112, 38)
            sign.midtop = (sx, 198)
            pygame.draw.rect(screen, (20, 20, 22), sign, border_radius=4)
            lines = self.LINES[(int(x) // 512 + i) % len(self.LINES):] + self.LINES
            for j, (label, color) in enumerate(lines[:3]):
                cx = sign.x + 22 + j * 34
                pygame.draw.circle(screen, color, (cx, sign.centery), 14)
                text = pixel_font(16).render(label, True, (20, 20, 20) if color == (252, 204, 10) else (255, 255, 255))
                screen.blit(text, text.get_rect(center=(cx, sign.centery + 1)))

    # -- Sewer ----------------------------------------------------------------

    def _build_far_sewer(self):
        s = pygame.Surface((FAR_TILE_W, SCREEN_HEIGHT))
        s.fill((56, 68, 58))
        for row, y in enumerate(range(CEILING_H, self.ground_y, 16)):    # brick
            pygame.draw.line(s, (42, 52, 44), (0, y), (FAR_TILE_W, y), 2)
            for x in range((row % 2) * 16, FAR_TILE_W, 32):
                pygame.draw.line(s, (42, 52, 44), (x, y), (x, y + 16), 2)
        for x, w in ((60, 150), (300, 120)):                               # arched tunnels
            rect = pygame.Rect(x, 250, w, 260)
            pygame.draw.ellipse(s, (30, 36, 32), rect.inflate(16, 16))
            pygame.draw.ellipse(s, (16, 20, 18), rect)
            pygame.draw.rect(s, (16, 20, 18), (x, 380, w, 120))
            pygame.draw.rect(s, (46, 92, 66), (x, 420, w, 80))              # murky water
        # Big pipe along the top and a thinner one under it.
        for y, h, color, flange in ((64, 30, (66, 124, 104), (48, 96, 80)), (112, 16, (120, 112, 96), (90, 84, 72))):
            s.fill(color, (0, y, FAR_TILE_W, h))
            s.fill(tuple(min(255, c + 30) for c in color), (0, y + 3, FAR_TILE_W, 4))
            for x in range(40, FAR_TILE_W, 120):
                s.fill(flange, (x, y - 4, 10, h + 8))
        return s

    def _init_sewer(self):
        self.grate_glow = _glow(70, (200, 255, 190), 70)
        # A slanted shaft of street light under each grate.
        h = self.ground_y - CEILING_H
        self.grate_shaft = pygame.Surface((110, h), pygame.SRCALPHA)
        for y in range(h):
            left = 6 + y * 0.012
            right = 54 + y * 0.09
            pygame.draw.line(self.grate_shaft, (210, 255, 200, round(46 * (1 - y / h))), (left, y), (right, y))
        self.drips = [(self.rng.randrange(self.level_width), self.rng.uniform(0, 2)) for _ in range(28)]

    def _draw_sewer(self, screen, camera_x):
        # Water ripples in the far arches.
        for i in range(0, SCREEN_WIDTH, 40):
            y = 430 + 3 * math.sin(self.time * 2 + i * 0.07)
            pygame.draw.line(screen, (90, 150, 110), (i, y), (i + 18, y), 2)
        # Light falling through street grates in the ceiling.
        for x in self._visible(420, camera_x, start=250):
            sx = x - camera_x
            screen.blit(self.grate_glow, (sx - 70, CEILING_H - 40))
            screen.blit(self.grate_shaft, (sx - 30, CEILING_H))
            for gx in range(-20, 24, 8):
                pygame.draw.line(screen, (20, 24, 20), (sx + gx, CEILING_H - 8), (sx + gx, CEILING_H), 3)
        # Vertical pipes with red valve wheels.
        for x in self._visible(300, camera_x, start=160):
            sx = x - camera_x
            pygame.draw.rect(screen, (60, 112, 94), (sx - 12, CEILING_H, 24, self.ground_y - CEILING_H))
            pygame.draw.rect(screen, (96, 160, 132), (sx - 8, CEILING_H, 5, self.ground_y - CEILING_H))
            for y in (CEILING_H + 40, self.ground_y - 40):
                pygame.draw.rect(screen, (40, 84, 70), (sx - 16, y, 32, 10))
            wy = 300
            pygame.draw.circle(screen, (180, 40, 40), (sx, wy), 16, width=4)
            for a in range(4):
                ang = a * math.pi / 2 + self.time * 0.3
                pygame.draw.line(screen, (180, 40, 40), (sx, wy), (sx + math.cos(ang) * 14, wy + math.sin(ang) * 14), 3)
            pygame.draw.circle(screen, (120, 20, 20), (sx, wy), 4)
        # Drips.
        for x, phase in self.drips:
            sx = x - camera_x
            if -10 < sx < SCREEN_WIDTH + 10:
                t = (self.time * 0.6 + phase) % 2.0
                if t < 1.0:
                    y = CEILING_H + t * t * (self.ground_y - CEILING_H)
                    pygame.draw.ellipse(screen, (150, 220, 180), (sx - 2, y, 4, 7))

    # -- Mine -----------------------------------------------------------------

    def _build_far_mine(self):
        s = pygame.Surface((FAR_TILE_W, SCREEN_HEIGHT))
        s.fill((50, 38, 32))
        rng = random.Random(11)
        for _ in range(140):                                               # rough rock
            x, y = rng.randrange(-20, FAR_TILE_W + 20), rng.randrange(CEILING_H, self.ground_y)
            r = rng.randint(8, 30)
            shade = rng.choice([(58, 44, 36), (44, 33, 28), (64, 50, 40)])
            pygame.draw.circle(s, shade, (x, y), r)
            for wrap in (-FAR_TILE_W, FAR_TILE_W):
                pygame.draw.circle(s, shade, (x + wrap, y), r)
        for _ in range(26):                                                # gold specks
            x, y = rng.randrange(FAR_TILE_W), rng.randrange(80, 400)
            pygame.draw.circle(s, (220, 180, 70), (x, y), rng.randint(1, 3))
        # Cart track along the back wall.
        for x in range(0, FAR_TILE_W, 24):
            s.fill((80, 56, 36), (x, 440, 14, 8))
        for y in (436, 446):
            s.fill((120, 120, 128), (0, y, FAR_TILE_W, 3))
        return s

    def _init_mine(self):
        self.lantern_glow = _glow(80, (255, 190, 90), 110)
        self.crystals = [(self.rng.randrange(self.level_width), self.rng.randrange(90, 400),
                          self.rng.choice([(110, 220, 240), (240, 130, 200), (170, 240, 140)]),
                          self.rng.uniform(0, 6.28)) for _ in range(30)]

    def _draw_mine(self, screen, camera_x):
        # A mine cart parked on the back track, every so often.
        for x in self._visible(900, camera_x, start=520):
            sx = (x - camera_x) * 0.5 + SCREEN_WIDTH * 0.25
            pygame.draw.polygon(screen, (90, 92, 100), [(sx - 40, 400), (sx + 40, 400), (sx + 32, 434), (sx - 32, 434)])
            pygame.draw.rect(screen, (60, 62, 70), (sx - 40, 400, 80, 6))
            for wx in (-22, 22):
                pygame.draw.circle(screen, (40, 40, 44), (sx + wx, 438), 8)
            for gx, gy, c in ((-18, 396, (200, 170, 60)), (0, 392, (110, 220, 240)), (16, 396, (200, 170, 60))):
                pygame.draw.circle(screen, c, (sx + gx, gy), 8)
        # Twinkling crystals in the walls.
        for x, y, color, phase in self.crystals:
            sx = x - camera_x * 0.8
            if -20 < sx < SCREEN_WIDTH + 20:
                sparkle = 0.5 + 0.5 * math.sin(self.time * 3 + phase)
                pts = [(sx, y - 9), (sx + 6, y), (sx, y + 9), (sx - 6, y)]
                pygame.draw.polygon(screen, color, pts)
                pygame.draw.polygon(screen, (30, 22, 20), pts, width=1)
                if sparkle > 0.8:
                    pygame.draw.line(screen, (255, 255, 255), (sx - 8, y - 10), (sx - 2, y - 10), 1)
                    pygame.draw.line(screen, (255, 255, 255), (sx - 5, y - 13), (sx - 5, y - 7), 1)
        # Timber frames with lanterns.
        for x in self._visible(288, camera_x, start=150):
            sx = x - camera_x
            for px in (sx - 70, sx + 70):
                pygame.draw.rect(screen, (104, 70, 40), (px - 9, CEILING_H, 18, self.ground_y - CEILING_H))
                pygame.draw.rect(screen, (134, 94, 56), (px - 9, CEILING_H, 5, self.ground_y - CEILING_H))
            pygame.draw.rect(screen, (104, 70, 40), (sx - 86, CEILING_H + 6, 172, 18))
            pygame.draw.rect(screen, (134, 94, 56), (sx - 86, CEILING_H + 6, 172, 5))
            flicker = 0.85 + 0.15 * math.sin(self.time * 11 + x)
            glow = self.lantern_glow
            glow.set_alpha(round(255 * flicker))
            screen.blit(glow, (sx - 80, CEILING_H + 50 - 80))
            pygame.draw.line(screen, (40, 30, 24), (sx, CEILING_H + 24), (sx, CEILING_H + 38), 2)
            pygame.draw.rect(screen, (60, 46, 36), (sx - 8, CEILING_H + 38, 16, 22), border_radius=3)
            pygame.draw.rect(screen, (255, 210, 120), (sx - 5, CEILING_H + 42, 10, 14), border_radius=2)

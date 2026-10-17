import pygame

from kobito.constants import GROUND_BROWN, TILE_SIZE


class Platform(pygame.sprite.Sprite):
    """A static solid block the player can stand on.

    A pygame.sprite.Sprite just needs two attributes to work with the
    rest of pygame's sprite tooling: `image` (what to draw) and `rect`
    (where it is, used for both drawing position and collision checks).
    """

    def __init__(self, x, y, width, height, color=GROUND_BROWN, cap_color=None, shade_color=None):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)

        # A lit top band, a shaded underside and faint vertical seams are
        # what make solid tiles read as chunky terrain instead of flat
        # rectangles. All optional -- a theme that sets no cap/shade
        # still gets the plain fill above.
        if cap_color:
            cap_height = min(6, max(3, height // 5))
            self.image.fill(cap_color, (0, 0, width, cap_height))
            # One darker pixel row under the cap reads as the lit surface
            # casting a shadow onto the dirt beneath it.
            if shade_color and height > cap_height + 1:
                self.image.fill(shade_color, (0, cap_height, width, 1))

        if shade_color:
            if height >= 6:
                self.image.fill(shade_color, (0, height - 2, width, 2))
            for seam_x in range(TILE_SIZE, width, TILE_SIZE):
                self.image.fill(shade_color, (seam_x, 0, 1, height))

        self.rect = self.image.get_rect(topleft=(x, y))
        # One-way platforms (clouds) can be jumped up through from below and
        # only hold you up when you land on them from above.
        self.one_way = False


class CloudPlatform(pygame.sprite.Sprite):
    """A fluffy one-way cloud for the sky stages: jump up through it from
    below, land on it from above. Drawn as a row of overlapping puffs with
    a lit top and a shaded belly."""

    def __init__(self, x, y, width, color=(250, 250, 255), shade=(214, 220, 240), height=TILE_SIZE):
        super().__init__()
        self.one_way = True
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        r = height // 2
        edge = tuple(max(0, c - 70) for c in shade)   # a soft outline so clouds read on any sky
        bumps = [(cx, r - 1 if i % 2 else r - 4) for i, cx in enumerate(range(r, width - r + 1, max(1, r)))]
        pygame.draw.rect(self.image, edge, (0, r - 4, width, height - r + 4), border_radius=r)
        for cx, bump in bumps:
            pygame.draw.circle(self.image, edge, (cx, r + 2), bump + 2)
        belly = pygame.Rect(2, r - 2, width - 4, height - r)
        pygame.draw.rect(self.image, shade, belly, border_radius=r)
        for cx, bump in bumps:
            pygame.draw.circle(self.image, color, (cx, r + 2), bump)
        pygame.draw.rect(self.image, color, (0, r, width, height - r - 6), border_radius=r)
        light = tuple(min(255, c + 12) for c in color)
        for cx in range(r, width - r + 1, max(1, r * 2)):
            pygame.draw.circle(self.image, light, (cx - 3, r - 1), max(2, r // 3))
        self.rect = self.image.get_rect(topleft=(x, y))

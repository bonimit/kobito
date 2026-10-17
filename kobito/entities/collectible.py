import math

import pygame

from kobito.item_art import get_icon
from kobito.items import ITEMS

COIN_COLOR = (255, 205, 60)
COIN_EDGE = (200, 150, 30)
COIN_INK = (90, 56, 10)
COIN_SHINE = (255, 246, 190)
COIN_SPIN = (1.0, 0.75, 0.4, 0.15, 0.4, 0.75)   # widths through one turn
COIN_SPIN_SECONDS = 0.9
BOB_PIXELS = 3

# The halo behind each kind of pickup: what it is, at a glance.
HALO_COLORS = {"konbini": (120, 200, 255), "favorite": (255, 140, 200), "rare": (255, 214, 90),
               "treasure": (255, 226, 120), "shiitake": (255, 150, 150)}

SHIITAKE_CAP = (121, 74, 45)
SHIITAKE_CAP_EDGE = (95, 56, 33)
SHIITAKE_STEM = (230, 214, 180)
SHIITAKE_SPOT = (196, 168, 140)

VALUES = {"coin": 5, "shiitake": 15}
SIZE = 22
ITEM_SIZE = 26


class Collectible(pygame.sprite.Sprite):
    """A pickup. Not solid -- the player passes through freely, and
    touching one removes it (Game does a spritecollide with dokill=True).

    `kind` is "coin", "shiitake" (an extra life), or any item id from
    kobito/items.py -- a konbini snack that refills power, a rare find, or
    a character's favourite. Game reads `kind` to decide what it does.
    """

    def __init__(self, x, y, kind="coin"):
        super().__init__()
        if kind not in VALUES and kind not in ITEMS:
            raise ValueError(f"Unknown collectible kind: {kind!r}")

        self.kind = kind
        self.item = ITEMS.get(kind)
        self.value = VALUES.get(kind, self.item.score if self.item else 0)
        size = SIZE if self.item is None else ITEM_SIZE
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        if self.item is not None:
            self.image.blit(get_icon(kind, ITEM_SIZE), (0, 0))
        else:
            getattr(self, f"_draw_{kind}")()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.phase = ((x * 7 + y * 3) % 100) / 100   # neighbours don't spin/bob in sync
        self._spin = [self._squash(w) for w in COIN_SPIN] if kind == "coin" else None

    @property
    def halo_color(self):
        if self.item is not None:
            return HALO_COLORS.get(self.item.group)
        return HALO_COLORS.get(self.kind)

    def frame(self, t):
        """The image to draw at game time t: coins spin, everything else is
        its still image."""
        if self._spin is None:
            return self.image
        i = int(((t / COIN_SPIN_SECONDS) + self.phase) * len(self._spin)) % len(self._spin)
        return self._spin[i]

    def bob(self, t):
        """Vertical draw offset: items float gently (coins stay put and spin)."""
        if self._spin is not None:
            return 0
        return round(BOB_PIXELS * math.sin(t * 3.2 + self.phase * 6.28))

    def _squash(self, width_scale):
        w = max(2, round(SIZE * width_scale))
        frame = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
        squashed = pygame.transform.smoothscale(self.image, (w, SIZE)) if w != SIZE else self.image
        frame.blit(squashed, squashed.get_rect(center=(SIZE // 2, SIZE // 2)))
        return frame

    def _draw_coin(self):
        center, radius = SIZE // 2, SIZE // 2 - 1
        pygame.draw.circle(self.image, COIN_INK, (center, center), radius)
        pygame.draw.circle(self.image, COIN_EDGE, (center, center), radius - 2)
        pygame.draw.circle(self.image, COIN_COLOR, (center, center), radius - 4)
        pygame.draw.rect(self.image, COIN_EDGE, (center - 1, center - 5, 3, 10))          # stamped slot
        pygame.draw.circle(self.image, COIN_SHINE, (center - 3, center - 4), 2)

    def _draw_shiitake(self):
        stem_w = SIZE // 3
        stem_rect = pygame.Rect(0, 0, stem_w, SIZE // 2)
        stem_rect.midtop = (SIZE // 2, SIZE // 2 - 2)
        pygame.draw.rect(self.image, SHIITAKE_STEM, stem_rect)

        cap_rect = pygame.Rect(1, 1, SIZE - 2, int(SIZE * 0.62))
        pygame.draw.ellipse(self.image, SHIITAKE_CAP, cap_rect)
        pygame.draw.ellipse(self.image, SHIITAKE_CAP_EDGE, cap_rect, width=2)
        for dx, dy in ((0.32, 0.22), (0.62, 0.3), (0.47, 0.12)):
            pygame.draw.circle(self.image, SHIITAKE_SPOT, (int(SIZE * dx), int(SIZE * dy)), 1)

import pygame

from kobito.item_art import get_icon
from kobito.items import ITEMS

COIN_COLOR = (255, 205, 60)
COIN_EDGE = (200, 150, 30)

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

    def _draw_coin(self):
        center, radius = SIZE // 2, SIZE // 2 - 2
        pygame.draw.circle(self.image, COIN_COLOR, (center, center), radius)
        pygame.draw.circle(self.image, COIN_EDGE, (center, center), radius, width=2)

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

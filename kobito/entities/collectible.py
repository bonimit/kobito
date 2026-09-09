import pygame

COIN_COLOR = (255, 205, 60)
COIN_EDGE = (200, 150, 30)

SHIITAKE_CAP = (121, 74, 45)
SHIITAKE_CAP_EDGE = (95, 56, 33)
SHIITAKE_STEM = (230, 214, 180)
SHIITAKE_SPOT = (196, 168, 140)

ONIGIRI_BODY = (255, 255, 250)
ONIGIRI_EDGE = (70, 70, 70)
ONIGIRI_NORI = (35, 45, 35)

VALUES = {"coin": 5, "shiitake": 15, "onigiri": 10}
SIZE = 22


class Collectible(pygame.sprite.Sprite):
    """A pickup: coin, shiitake mushroom, or onigiri. Not solid -- the
    player passes through freely, and touching one removes it and adds
    its value to the score (handled in Game, via spritecollide with
    dokill=True).
    """

    def __init__(self, x, y, kind="coin"):
        super().__init__()
        if kind not in VALUES:
            raise ValueError(f"Unknown collectible kind: {kind!r}")

        self.kind = kind
        self.value = VALUES[kind]
        self.image = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
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

    def _draw_onigiri(self):
        points = [(SIZE // 2, 1), (1, SIZE - 1), (SIZE - 1, SIZE - 1)]
        pygame.draw.polygon(self.image, ONIGIRI_BODY, points)
        pygame.draw.polygon(self.image, ONIGIRI_EDGE, points, width=2)

        band_w = SIZE * 0.24
        band_rect = pygame.Rect(0, 0, band_w, SIZE * 0.58)
        band_rect.center = (SIZE // 2, SIZE * 0.68)
        pygame.draw.rect(self.image, ONIGIRI_NORI, band_rect)

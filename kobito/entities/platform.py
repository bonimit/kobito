import pygame

from kobito.constants import GROUND_BROWN


class Platform(pygame.sprite.Sprite):
    """A static solid block the player can stand on.

    A pygame.sprite.Sprite just needs two attributes to work with the
    rest of pygame's sprite tooling: `image` (what to draw) and `rect`
    (where it is, used for both drawing position and collision checks).
    """

    def __init__(self, x, y, width, height, color=GROUND_BROWN):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

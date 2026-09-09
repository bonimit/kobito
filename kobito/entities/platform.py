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

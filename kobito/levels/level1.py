import pygame

from kobito.constants import TILE_SIZE
from kobito.entities.platform import Platform


def build_level1():
    """Returns (platforms_group, player_start_pos) for the first level.

    Positions are specified in tile coordinates (col, row) and converted
    to pixels here, so the layout below is easy to read/edit as a grid.
    """
    platforms = pygame.sprite.Group()

    def add_platform(col, row, width_in_tiles=1, height_in_tiles=1):
        platforms.add(
            Platform(
                col * TILE_SIZE,
                row * TILE_SIZE,
                width_in_tiles * TILE_SIZE,
                height_in_tiles * TILE_SIZE,
            )
        )

    # Ground strip along the bottom of the level, split into two segments
    # with a gap between tiles 10-13 to force a jump.
    ground_row = 15
    add_platform(0, ground_row, width_in_tiles=10, height_in_tiles=2)
    add_platform(14, ground_row, width_in_tiles=26, height_in_tiles=2)

    # Floating platforms to practice jumping between.
    add_platform(6, 11, width_in_tiles=3)
    add_platform(11, 8, width_in_tiles=3)
    add_platform(16, 11, width_in_tiles=4)

    player_start = (2 * TILE_SIZE, (ground_row - 3) * TILE_SIZE)
    return platforms, player_start

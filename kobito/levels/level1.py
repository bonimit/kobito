import pygame

from kobito.constants import TILE_SIZE
from kobito.entities.platform import Platform
from kobito.entities.question_block import QuestionBlock


def build_level1():
    """Returns (platforms_group, question_blocks_group, player_start_pos).

    Positions are specified in tile coordinates (col, row) and converted
    to pixels here, so the layout below is easy to read/edit as a grid.

    Question blocks are added to `platforms` too (so the player collides
    with them like any solid tile) as well as their own group (so Game
    can tell which touched solid was a question block).
    """
    platforms = pygame.sprite.Group()
    question_blocks = pygame.sprite.Group()

    def add_platform(col, row, width_in_tiles=1, height_in_tiles=1):
        platforms.add(
            Platform(
                col * TILE_SIZE,
                row * TILE_SIZE,
                width_in_tiles * TILE_SIZE,
                height_in_tiles * TILE_SIZE,
            )
        )

    def add_question_block(col, row):
        block = QuestionBlock(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE)
        platforms.add(block)
        question_blocks.add(block)

    # Ground strip along the bottom of the level, split into two segments
    # with a gap between tiles 10-13 to force a jump.
    ground_row = 15
    add_platform(0, ground_row, width_in_tiles=10, height_in_tiles=2)
    add_platform(14, ground_row, width_in_tiles=26, height_in_tiles=2)

    # Floating platforms to practice jumping between.
    add_platform(6, 11, width_in_tiles=3)
    add_platform(11, 8, width_in_tiles=3)
    add_platform(16, 11, width_in_tiles=4)

    # Question blocks, each placed ~3 tiles above a reachable surface
    # (about the height of this game's jump arc).
    add_question_block(4, 12)
    add_question_block(7, 8)
    add_question_block(17, 8)

    player_start = (2 * TILE_SIZE, (ground_row - 3) * TILE_SIZE)
    return platforms, question_blocks, player_start

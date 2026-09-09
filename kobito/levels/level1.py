from dataclasses import dataclass, field

import pygame

from kobito.constants import TILE_SIZE
from kobito.entities.collectible import Collectible
from kobito.entities.enemy import Enemy
from kobito.entities.platform import Platform
from kobito.entities.question_block import QuestionBlock

LEVEL_WIDTH_TILES = 40


@dataclass
class Level:
    platforms: pygame.sprite.Group
    question_blocks: pygame.sprite.Group
    enemies: pygame.sprite.Group
    collectibles: pygame.sprite.Group
    player_start: tuple
    width_px: int
    ground_y: int
    ground_segments_px: list = field(default_factory=list)


def build_level1():
    """Builds and returns the first level.

    Positions are specified in tile coordinates (col, row) and converted
    to pixels here, so the layout below is easy to read/edit as a grid.

    Question blocks and enemies are added to `platforms` too (so the
    player collides with them like any solid tile) as well as their own
    groups (so Game can tell what kind of solid it touched).
    """
    platforms = pygame.sprite.Group()
    question_blocks = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    collectibles = pygame.sprite.Group()
    ground_segments_px = []

    def add_platform(col, row, width_in_tiles=1, height_in_tiles=1):
        platforms.add(
            Platform(
                col * TILE_SIZE,
                row * TILE_SIZE,
                width_in_tiles * TILE_SIZE,
                height_in_tiles * TILE_SIZE,
            )
        )

    def add_ground(col, row, width_in_tiles):
        add_platform(col, row, width_in_tiles=width_in_tiles, height_in_tiles=2)
        ground_segments_px.append((col * TILE_SIZE, (col + width_in_tiles) * TILE_SIZE))

    def add_question_block(col, row):
        block = QuestionBlock(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE)
        platforms.add(block)
        question_blocks.add(block)

    def add_enemy(spawn_col, row, patrol_start_col, patrol_end_col):
        enemy = Enemy(
            spawn_col * TILE_SIZE,
            row * TILE_SIZE,
            patrol_min_x=patrol_start_col * TILE_SIZE,
            patrol_max_x=patrol_end_col * TILE_SIZE,
        )
        enemies.add(enemy)

    def add_collectible(col, row, kind="coin"):
        collectibles.add(Collectible(col * TILE_SIZE, row * TILE_SIZE, kind=kind))

    # Ground strip along the bottom of the level, split into two segments
    # with a gap between tiles 10-13 to force a jump. Recorded in
    # ground_segments_px so decorative trees (see kobito/background.py)
    # only get placed on solid ground, never floating over the gap.
    ground_row = 15
    add_ground(0, ground_row, width_in_tiles=10)
    add_ground(14, ground_row, width_in_tiles=26)

    # Floating platforms to practice jumping between.
    add_platform(6, 11, width_in_tiles=3)
    add_platform(11, 8, width_in_tiles=3)
    add_platform(16, 11, width_in_tiles=4)

    # Question blocks, each placed ~3 tiles above a reachable surface
    # (about the height of this game's jump arc).
    add_question_block(4, 12)
    add_question_block(7, 8)
    add_question_block(17, 8)

    # Patrol enemies: one on the ground, one on the row-11 platform, one
    # further along the ground past the gap.
    add_enemy(spawn_col=5, row=ground_row - 1, patrol_start_col=3, patrol_end_col=9)
    add_enemy(spawn_col=7, row=10, patrol_start_col=6, patrol_end_col=9)
    add_enemy(spawn_col=20, row=ground_row - 1, patrol_start_col=15, patrol_end_col=25)

    # Collectibles: mostly coins tracing the path a player would
    # naturally run/jump through, with rarer, higher-value shiitake and
    # onigiri tucked in trickier or out-of-the-way spots.
    for col in (2, 3, 8):
        add_collectible(col, 13, kind="coin")
    add_collectible(7, 7, kind="shiitake")
    for col in (17, 18, 19):
        add_collectible(col, 7, kind="coin")
    for col in (22, 23):
        add_collectible(col, 13, kind="coin")
    add_collectible(35, 13, kind="onigiri")

    player_start = (2 * TILE_SIZE, (ground_row - 3) * TILE_SIZE)
    return Level(
        platforms=platforms,
        question_blocks=question_blocks,
        enemies=enemies,
        collectibles=collectibles,
        player_start=player_start,
        width_px=LEVEL_WIDTH_TILES * TILE_SIZE,
        ground_y=ground_row * TILE_SIZE,
        ground_segments_px=ground_segments_px,
    )

from dataclasses import dataclass, field

import pygame

from kobito.constants import TILE_SIZE
from kobito.entities.collectible import Collectible
from kobito.entities.enemy import Enemy
from kobito.entities.goal import Goal
from kobito.entities.platform import Platform
from kobito.entities.question_block import QuestionBlock
from kobito.themes import get_theme

LEVEL_WIDTH_TILES = 120


@dataclass
class Level:
    platforms: pygame.sprite.Group
    question_blocks: pygame.sprite.Group
    enemies: pygame.sprite.Group
    collectibles: pygame.sprite.Group
    goal: pygame.sprite.Sprite
    player_start: tuple
    width_px: int
    ground_y: int
    theme: object
    ground_segments_px: list = field(default_factory=list)


def build_level1(theme_id="forest"):
    """Builds and returns the first level, skinned with the given world
    theme (see kobito/themes.py).

    Positions are specified in tile coordinates (col, row) and converted
    to pixels here, so the layout below is easy to read/edit as a grid.
    The layout itself (platforms, blocks, enemies, collectibles) is the
    same regardless of theme -- only the colors and background scenery
    change.

    Question blocks and enemies are added to `platforms` too (so the
    player collides with them like any solid tile) as well as their own
    groups (so Game can tell what kind of solid it touched).
    """
    theme = get_theme(theme_id)
    platforms = pygame.sprite.Group()
    question_blocks = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    collectibles = pygame.sprite.Group()
    ground_segments_px = []

    def add_platform(col, row, width_in_tiles=1, height_in_tiles=1, color=None):
        platforms.add(
            Platform(
                col * TILE_SIZE,
                row * TILE_SIZE,
                width_in_tiles * TILE_SIZE,
                height_in_tiles * TILE_SIZE,
                color=color or theme.platform_color,
                cap_color=theme.cap_color,
                shade_color=theme.shade_color,
            )
        )

    def add_ground(col, row, width_in_tiles):
        add_platform(col, row, width_in_tiles=width_in_tiles, height_in_tiles=2, color=theme.ground_color)
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

    # Ground strip along the bottom, split into segments with 4-tile
    # gaps between them. A 4-tile gap is comfortably clearable: the jump
    # arc lasts ~0.7s at this gravity, which carries the player ~5.5
    # tiles at run speed. Recorded in ground_segments_px so decorative
    # props (see kobito/background.py) only get placed on solid ground,
    # never floating over a gap.
    ground_row = 15
    for start_col, width in ((0, 10), (14, 12), (30, 14), (48, 14), (66, 14), (84, 14), (102, 18)):
        add_ground(start_col, ground_row, width_in_tiles=width)

    # Floating platforms: the wider ones carry a question block three
    # tiles above them, the 2-tile ones are stepping stones over gaps.
    for col, row, width in (
        (19, 11, 3), (36, 11, 3), (57, 9, 3), (69, 11, 3), (90, 10, 3), (110, 11, 3),
        (11, 12, 2), (45, 12, 2), (81, 12, 2),
    ):
        add_platform(col, row, width_in_tiles=width)

    # Twelve question blocks spread across the level -- enough that a
    # player can miss a few and still clear the badge's 70% bar (see
    # BADGE_MIN_QUESTIONS in kobito/constants.py). Each sits ~3 tiles
    # above a reachable surface, which is about this game's jump height.
    for col, row in (
        (5, 12), (8, 12), (17, 12), (20, 8), (33, 12), (37, 8),
        (51, 12), (55, 12), (70, 8), (73, 12), (88, 12), (105, 12),
    ):
        add_question_block(col, row)

    # Patrol enemies along the ground segments and on a couple of the
    # platforms, so neither route through the level is a free run.
    for spawn, row, patrol_start, patrol_end in (
        (6, ground_row - 1, 3, 9),
        (20, 10, 19, 21),
        (34, ground_row - 1, 31, 43),
        (52, ground_row - 1, 49, 61),
        (58, 8, 57, 59),
        (70, 10, 69, 71),
        (74, ground_row - 1, 67, 79),
        (90, ground_row - 1, 85, 97),
        (108, ground_row - 1, 103, 113),
    ):
        add_enemy(spawn_col=spawn, row=row, patrol_start_col=patrol_start, patrol_end_col=patrol_end)

    # Collectibles: coins tracing the route a player naturally runs and
    # jumps through, with rarer shiitake (an extra life) and onigiri
    # tucked into the trickier, out-of-the-way spots.
    for col in (2, 3, 9, 16, 18, 32, 34, 50, 54, 68, 72, 86, 89, 104, 106, 113):
        add_collectible(col, 13, kind="coin")
    for col in (19, 20, 21, 57, 58, 59):
        add_collectible(col, 7, kind="coin")
    add_collectible(37, 7, kind="shiitake")
    add_collectible(70, 7, kind="shiitake")
    add_collectible(45, 11, kind="onigiri")
    add_collectible(81, 11, kind="onigiri")

    # The castle the player runs into to finish the level, near the
    # right-hand end of the final ground segment.
    goal = Goal(116 * TILE_SIZE, ground_row * TILE_SIZE)

    player_start = (2 * TILE_SIZE, (ground_row - 3) * TILE_SIZE)
    return Level(
        platforms=platforms,
        question_blocks=question_blocks,
        enemies=enemies,
        collectibles=collectibles,
        goal=goal,
        player_start=player_start,
        width_px=LEVEL_WIDTH_TILES * TILE_SIZE,
        ground_y=ground_row * TILE_SIZE,
        theme=theme,
        ground_segments_px=ground_segments_px,
    )

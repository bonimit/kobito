import random
from dataclasses import dataclass, field

import pygame

from kobito.constants import LEVEL_BLOCK_BUFFER, TILE_SIZE, required_question_count
from kobito.entities.collectible import Collectible
from kobito.entities.enemy import Enemy, FlyingEnemy
from kobito.entities.gift_box import GiftBox
from kobito.entities.goal import Goal
from kobito.entities.platform import Platform
from kobito.entities.question_block import QuestionBlock
from kobito.items import KONBINI_IDS
from kobito.themes import ENEMY_PALETTES, FLYING_ENEMY_PALETTES, get_theme

# Ground enemies walk a little faster in later levels -- caps out so it
# never outruns what the player can react to.
ENEMY_SPEED_BASE = 70.0
ENEMY_SPEED_STEP = 2.5
ENEMY_SPEED_MAX = 110.0

# A segment is a long stretch of ground (see build_segment) with room to
# actually play -- run, jump, stomp enemies, grab snacks -- between
# question boxes, instead of a quiz every few steps. The gap that ends
# each segment is comfortably clearable: the jump arc lasts ~0.7s at this
# gravity, which carries the player ~5.5 tiles at run speed.
SEGMENT_WIDTH_TILES = 22
GAP_WIDTH_TILES = 4
FINAL_SEGMENT_WIDTH_TILES = 18
GROUND_ROW = 15

# Question boxes are the interruptions, so they're kept well apart: never
# closer than this many tiles to each other. (Gift boxes don't pause the
# game, so they can sit nearer.)
MIN_QUESTION_SPACING_TILES = 8


@dataclass
class Level:
    platforms: pygame.sprite.Group
    question_blocks: pygame.sprite.Group
    gift_boxes: pygame.sprite.Group
    enemies: pygame.sprite.Group
    collectibles: pygame.sprite.Group
    goal: pygame.sprite.Sprite
    player_start: tuple
    width_px: int
    ground_y: int
    theme: object
    ground_segments_px: list = field(default_factory=list)


def build_level1(theme_id="forest", level_number=1, favorites=()):
    """Builds and returns the first level, skinned with the given world
    theme (see kobito/themes.py) and sized to the given level_number.

    The level is a chain of identical-shaped "segments" (see
    build_segment) so it can grow with level_number: required_question_
    count() climbs as level_number climbs, and this function keeps adding
    segments until there are enough question blocks to comfortably clear
    that requirement (plus a small buffer so a player can skip a couple).

    `favorites` are the chosen mascot's two favourite item ids (see
    kobito/characters.py); they're scattered through the level as
    bonus pickups.

    Positions are specified in tile coordinates (col, row) and converted
    to pixels here. Question blocks, gift boxes and enemies are added to
    `platforms` too (so the player collides with them like any solid
    tile) as well as their own groups (so Game can tell what it touched).
    """
    theme = get_theme(theme_id)
    builder = _LevelBuilder(theme, level_number, favorites)

    target_blocks = min(32, required_question_count(level_number) + LEVEL_BLOCK_BUFFER)
    segment_index = 0
    while builder.blocks_placed < target_blocks:
        builder.build_segment(segment_index)
        segment_index += 1

    builder.build_final_segment()

    return builder.finish()


class _LevelBuilder:
    def __init__(self, theme, level_number=1, favorites=()):
        self.theme = theme
        self.favorites = list(favorites)
        # Seeded per level so a level's layout is the same every time it's
        # built (and testable), but differs from level to level.
        self.rng = random.Random(1000 + level_number)
        self.enemy_speed = min(ENEMY_SPEED_MAX, ENEMY_SPEED_BASE + (level_number - 1) * ENEMY_SPEED_STEP)
        self.enemy_body_color, self.enemy_foot_color = ENEMY_PALETTES.get(theme.id, (None, None))
        self.flying_palette = FLYING_ENEMY_PALETTES.get(theme.id)
        self.platforms = pygame.sprite.Group()
        self.question_blocks = pygame.sprite.Group()
        self.gift_boxes = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.collectibles = pygame.sprite.Group()
        self.ground_segments_px = []
        self.blocks_placed = 0
        self.col = 0

    def _add_platform(self, col, row, width_in_tiles=1, height_in_tiles=1, color=None):
        self.platforms.add(
            Platform(
                col * TILE_SIZE,
                row * TILE_SIZE,
                width_in_tiles * TILE_SIZE,
                height_in_tiles * TILE_SIZE,
                color=color or self.theme.platform_color,
                cap_color=self.theme.cap_color,
                shade_color=self.theme.shade_color,
            )
        )

    def _add_ground(self, col, width_in_tiles):
        self._add_platform(col, GROUND_ROW, width_in_tiles=width_in_tiles, height_in_tiles=2,
                            color=self.theme.ground_color)
        self.ground_segments_px.append((col * TILE_SIZE, (col + width_in_tiles) * TILE_SIZE))

    def _add_question_block(self, col, row):
        block = QuestionBlock(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE)
        self.platforms.add(block)
        self.question_blocks.add(block)
        self.blocks_placed += 1

    def _add_gift_box(self, col, row):
        box = GiftBox(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE)
        self.platforms.add(box)
        self.gift_boxes.add(box)

    def _add_enemy(self, spawn_col, row, patrol_start_col, patrol_end_col):
        enemy = Enemy(
            spawn_col * TILE_SIZE,
            row * TILE_SIZE,
            patrol_min_x=patrol_start_col * TILE_SIZE,
            patrol_max_x=patrol_end_col * TILE_SIZE,
            speed=self.enemy_speed,
            body_color=self.enemy_body_color,
            foot_color=self.enemy_foot_color,
        )
        self.enemies.add(enemy)

    def _add_flying_enemy(self, col, top_row, bottom_row):
        body_color, wing_color = self.flying_palette or (None, None)
        enemy = FlyingEnemy(
            col * TILE_SIZE,
            top_row * TILE_SIZE,
            patrol_min_y=top_row * TILE_SIZE,
            patrol_max_y=bottom_row * TILE_SIZE,
            body_color=body_color,
            wing_color=wing_color,
        )
        self.enemies.add(enemy)

    def _add_collectible(self, col, row, kind="coin"):
        self.collectibles.add(Collectible(col * TILE_SIZE, row * TILE_SIZE, kind=kind))

    def build_segment(self, segment_index):
        """One long ground segment (22 tiles), laid out left to right:

            col  5   gift box  (a low hop from the ground)
            col 10-12 a stepping-stone platform, with a QUESTION block
                      above it (col 11, row 8) -- the platform is what
                      makes the high block reachable
            col 16   a second gift box (even segments)
            col 19   a second QUESTION block (odd segments)

        so consecutive question blocks are always at least
        MIN_QUESTION_SPACING_TILES apart -- the player gets real
        stretches of platforming, stomping and snack-hunting in between.
        """
        s = self.col
        W = SEGMENT_WIDTH_TILES
        self._add_ground(s, W)

        # --- Boxes ------------------------------------------------------
        self._add_gift_box(s + (7 if segment_index == 0 else 5), 12)

        support_col = s + 10
        self._add_platform(support_col, 12, width_in_tiles=3)
        high_col = support_col + 1
        self._add_question_block(high_col, 8)

        if segment_index % 2 == 0:
            self._add_gift_box(s + 16, 12)
        else:
            self._add_question_block(s + 19, 12)

        # --- Enemies: two ground patrols, one on the stepping stone ---
        self._add_enemy(spawn_col=s + 1, row=GROUND_ROW - 1, patrol_start_col=s, patrol_end_col=s + 9)
        self._add_enemy(spawn_col=support_col, row=11, patrol_start_col=support_col, patrol_end_col=support_col + 2)
        self._add_enemy(spawn_col=s + 14, row=GROUND_ROW - 1, patrol_start_col=s + 13, patrol_end_col=s + W - 1)
        # A bat guarding the jump across the gap, every third segment.
        if segment_index % 3 == 2:
            self._add_flying_enemy(s + W + 1, top_row=6, bottom_row=13)

        # --- Pickups ----------------------------------------------------
        for col in (s + 3, s + 8, s + 15, s + W - 2):
            self._add_collectible(col, 13, kind="coin")
        self._add_collectible(high_col, 7, kind="coin")
        if segment_index % 4 == 3:
            self._add_collectible(support_col + 1, 11, kind="shiitake")

        # One konbini snack per segment (power), alternating sides of the
        # question boxes so there's always one to find; and one of the
        # mascot's favourites every other segment.
        snack = KONBINI_IDS[(segment_index * 3 + self.rng.randrange(len(KONBINI_IDS))) % len(KONBINI_IDS)]
        self._add_collectible(s + (12 if segment_index % 2 else 17), 13, kind=snack)
        if self.favorites and segment_index % 2 == 1:
            self._add_collectible(s + 7, 13, kind=self.favorites[(segment_index // 2) % len(self.favorites)])
        elif self.favorites:
            self._add_collectible(s + 20, 13, kind=self.favorites[(segment_index // 2) % len(self.favorites)])

        # A risk/reward bonus every 5th segment: a small coin cluster
        # above the high block, reached by jumping again from on top of it.
        if segment_index % 5 == 4:
            for i, dy in enumerate((0, 1, 2)):
                self._add_collectible(high_col + i - 1, 8 - 3 - dy, kind="coin")

        self.col = s + W + GAP_WIDTH_TILES

    def build_final_segment(self):
        """A calmer approach segment with no boxes -- a breather before the
        castle, with a snack to top up on, guarded by one last patrol.
        """
        seg_start = self.col
        self._add_ground(seg_start, FINAL_SEGMENT_WIDTH_TILES)

        self._add_collectible(seg_start + 2, 13, kind="coin")
        self._add_collectible(seg_start + 5, 13, kind="coin")
        self._add_collectible(seg_start + 9, 13, kind="onigiri")
        self._add_enemy(
            spawn_col=seg_start + 3, row=GROUND_ROW - 1,
            patrol_start_col=seg_start + 1, patrol_end_col=seg_start + 8,
        )

        goal_col = seg_start + FINAL_SEGMENT_WIDTH_TILES - 4
        self.goal = Goal(goal_col * TILE_SIZE, GROUND_ROW * TILE_SIZE)
        self.col = seg_start + FINAL_SEGMENT_WIDTH_TILES

    def finish(self):
        player_start = (2 * TILE_SIZE, (GROUND_ROW - 3) * TILE_SIZE)
        return Level(
            platforms=self.platforms,
            question_blocks=self.question_blocks,
            gift_boxes=self.gift_boxes,
            enemies=self.enemies,
            collectibles=self.collectibles,
            goal=self.goal,
            player_start=player_start,
            width_px=self.col * TILE_SIZE,
            ground_y=GROUND_ROW * TILE_SIZE,
            theme=self.theme,
            ground_segments_px=self.ground_segments_px,
        )

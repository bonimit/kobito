from dataclasses import dataclass, field

import pygame

from kobito.constants import LEVEL_BLOCK_BUFFER, TILE_SIZE, required_question_count
from kobito.entities.collectible import Collectible
from kobito.entities.enemy import Enemy, FlyingEnemy
from kobito.entities.goal import Goal
from kobito.entities.platform import Platform
from kobito.entities.question_block import QuestionBlock
from kobito.themes import ENEMY_PALETTES, FLYING_ENEMY_PALETTES, get_theme

# Ground enemies walk a little faster in later levels -- caps out so it
# never outruns what the player can react to.
ENEMY_SPEED_BASE = 70.0
ENEMY_SPEED_STEP = 2.5
ENEMY_SPEED_MAX = 110.0

# One repeating "segment" of ground carries up to 3 question blocks (see
# _build_segment) before a gap forces a jump into the next one. A 4-tile
# gap is comfortably clearable: the jump arc lasts ~0.7s at this
# gravity, which carries the player ~5.5 tiles at run speed.
SEGMENT_WIDTH_TILES = 14
GAP_WIDTH_TILES = 4
FINAL_SEGMENT_WIDTH_TILES = 18
GROUND_ROW = 15


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


def build_level1(theme_id="forest", level_number=1):
    """Builds and returns the first level, skinned with the given world
    theme (see kobito/themes.py) and sized to the given level_number.

    The level is generated as a chain of identical-shaped "segments"
    (see _build_segment) rather than a fixed hand-authored layout, so it
    can grow with level_number: required_question_count() (in
    kobito/constants.py) climbs as level_number climbs, and this
    function keeps adding segments -- each with its own question
    blocks, enemies, and collectibles -- until there are enough blocks
    to comfortably clear that requirement (plus a small buffer so a
    player can skip a couple).

    Positions are specified in tile coordinates (col, row) and converted
    to pixels here. Question blocks and enemies are added to `platforms`
    too (so the player collides with them like any solid tile) as well
    as their own groups (so Game can tell what kind of solid it touched).
    """
    theme = get_theme(theme_id)
    builder = _LevelBuilder(theme, level_number)

    target_blocks = min(32, required_question_count(level_number) + LEVEL_BLOCK_BUFFER)
    segment_index = 0
    while builder.blocks_placed < target_blocks:
        builder.build_segment(segment_index)
        segment_index += 1

    builder.build_final_segment()

    return builder.finish()


class _LevelBuilder:
    def __init__(self, theme, level_number=1):
        self.theme = theme
        self.enemy_speed = min(ENEMY_SPEED_MAX, ENEMY_SPEED_BASE + (level_number - 1) * ENEMY_SPEED_STEP)
        self.enemy_body_color, self.enemy_foot_color = ENEMY_PALETTES.get(theme.id, (None, None))
        self.flying_palette = FLYING_ENEMY_PALETTES.get(theme.id)
        self.platforms = pygame.sprite.Group()
        self.question_blocks = pygame.sprite.Group()
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
        """One ground segment, chained ground(15) -> platform/block(12)
        -> block(8) so every tier sits within a 3-tile jump of the one
        below it: block/platform on the ground segment top is 3 tiles
        up, and a row-8 block's bottom is exactly 3 tiles above a row-12
        surface's top.
        """
        seg_start = self.col
        self._add_ground(seg_start, SEGMENT_WIDTH_TILES)

        # A low block directly on the ground -- reachable with a single
        # jump from the segment itself. First segment leaves the player
        # a little room to get moving before the first obstacle.
        low_col = seg_start + (5 if segment_index == 0 else 3)
        self._add_question_block(low_col, 12)

        # A support platform plus a high block sitting right above it --
        # the platform is the stepping stone that makes the high block
        # (otherwise too far above the ground to reach directly) jumpable.
        support_col = seg_start + 7
        self._add_platform(support_col, 12, width_in_tiles=3)
        high_col = support_col + 1
        self._add_question_block(high_col, 8)

        # A third, ground-level bonus block on alternating segments --
        # more density without needing another support platform.
        if segment_index % 2 == 1:
            self._add_question_block(seg_start + SEGMENT_WIDTH_TILES - 3, 12)

        # Two ground patrols plus one on the elevated platform -- denser
        # than a single patrol per segment, so neither the ground route
        # nor the platform route through a segment is ever a free run.
        self._add_enemy(
            spawn_col=seg_start + 1, row=GROUND_ROW - 1,
            patrol_start_col=seg_start, patrol_end_col=seg_start + SEGMENT_WIDTH_TILES - 1,
        )
        self._add_enemy(
            spawn_col=support_col, row=11,
            patrol_start_col=support_col, patrol_end_col=support_col + 2,
        )
        if segment_index % 2 == 0:
            self._add_enemy(
                spawn_col=seg_start + SEGMENT_WIDTH_TILES - 4, row=GROUND_ROW - 1,
                patrol_start_col=seg_start + SEGMENT_WIDTH_TILES - 6, patrol_end_col=seg_start + SEGMENT_WIDTH_TILES - 1,
            )

        # A vertically-patrolling flying hazard guarding the jump across
        # the gap into the next segment -- a new kind of threat a ground
        # Enemy never poses, so clearing a gap isn't always a free jump.
        if segment_index % 3 == 2:
            self._add_flying_enemy(seg_start + SEGMENT_WIDTH_TILES + 1, top_row=6, bottom_row=13)

        self._add_collectible(seg_start + 2, 13, kind="coin")
        self._add_collectible(seg_start + SEGMENT_WIDTH_TILES - 2, 13, kind="coin")
        self._add_collectible(high_col, 7, kind="coin")
        if segment_index % 4 == 3:
            self._add_collectible(support_col + 1, 11, kind="shiitake")
        if segment_index % 6 == 5:
            self._add_collectible(seg_start + 8, 13, kind="onigiri")

        # A risk/reward bonus event every 5th segment: a small coin
        # cluster floating above the high block, only reachable by
        # jumping again from on top of it -- a skill-rewarding detour
        # rather than something free on the main path through.
        if segment_index % 5 == 4:
            for i, dy in enumerate((0, 1, 2)):
                self._add_collectible(high_col + i - 1, 8 - 3 - dy, kind="coin")

        self.col = seg_start + SEGMENT_WIDTH_TILES + GAP_WIDTH_TILES

    def build_final_segment(self):
        """A calmer approach segment with no question blocks -- a
        breather before the castle, guarded by one last patrol.
        """
        seg_start = self.col
        self._add_ground(seg_start, FINAL_SEGMENT_WIDTH_TILES)

        self._add_collectible(seg_start + 2, 13, kind="coin")
        self._add_collectible(seg_start + 5, 13, kind="coin")
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
            enemies=self.enemies,
            collectibles=self.collectibles,
            goal=self.goal,
            player_start=player_start,
            width_px=self.col * TILE_SIZE,
            ground_y=GROUND_ROW * TILE_SIZE,
            theme=self.theme,
            ground_segments_px=self.ground_segments_px,
        )

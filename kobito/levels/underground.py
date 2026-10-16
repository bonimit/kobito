"""The three hidden underground stages.

Three of each level's gaps are secret (kobito/levels/level1.py,
SECRET_GAP_SEGMENTS): drop into one and you land in one of these instead of
losing a life. They're bonus rooms -- no quiz boxes, lots of coins and gift
boxes, a few enemies, and one treasure you can only find down here -- with
an exit at the far end that brings you back up just past the gap.

  * subway -- an NYC subway station (treasure: 駅弁 ekiben)
  * sewer  -- sewer tunnels and water pipes, turtle-hideout style
              (treasure: ピザまん pizza bun)
  * mine   -- an old mine with timber frames and lanterns (treasure: 宝石 gem)

Every room shares one layout (so it's tested once) but each style skins
it differently: platforms, enemies, backdrop (kobito/underground_background.py)
and exit (kobito/entities/exit.py). Entering also teaches the place's
Japanese word (地下鉄 / 下水道 / 鉱山).
"""

import random
from types import SimpleNamespace

from kobito.constants import TILE_SIZE
from kobito.entities.exit import Exit
from kobito.items import KONBINI_IDS
from kobito.levels.level1 import GROUND_ROW, Level, _LevelBuilder

ROOM_WIDTH_TILES = 64
ENTRY_COL = 3
EXIT_COL = 59

STYLES = {
    "subway": {
        "name": "NYC Subway", "jp": "地下鉄", "reading": "chikatetsu", "meaning": "subway",
        "example": "地下鉄で行きます。", "example_en": "I'll go by subway.",
        "ground": (118, 118, 126), "cap": (240, 200, 60), "shade": (84, 84, 94),   # yellow platform edge
        "ledge": (150, 150, 160), "pillar": (60, 92, 104),
        "enemy": ((136, 130, 134), (226, 150, 164)),                              # rats
        "flying": None, "treasure": "ekiben", "hint": "steam",
    },
    "sewer": {
        "name": "Sewer Pipes", "jp": "下水道", "reading": "gesuidou", "meaning": "sewer",
        "example": "下水道は暗いです。", "example_en": "The sewer is dark.",
        "ground": (78, 94, 82), "cap": (112, 156, 92), "shade": (50, 62, 54),       # slimy stone
        "ledge": (68, 140, 112), "pillar": (60, 128, 100),                         # green pipes
        "enemy": ((84, 146, 72), (52, 96, 44)),                                    # little gators
        "flying": None, "treasure": "pizza_bun", "hint": "glow",
    },
    "mine": {
        "name": "Old Mine", "jp": "鉱山", "reading": "kouzan", "meaning": "mine (where ore is dug)",
        "example": "鉱山で宝石をさがします。", "example_en": "I look for gems in the mine.",
        "ground": (96, 72, 54), "cap": (156, 112, 70), "shade": (62, 46, 36),
        "ledge": (140, 96, 56), "pillar": (110, 84, 64),                           # timber and rock
        "enemy": ((116, 88, 72), (72, 52, 42)),                                    # moles
        "flying": ((92, 70, 112), (62, 42, 82)),                                   # bats
        "treasure": "gem", "hint": "sparkle",
    },
}


def place_lesson(style):
    s = STYLES[style]
    return f"{s['jp']} ({s['reading']}) = {s['meaning']}.  {s['example']}  ({s['example_en']})"


def build_underground(style, level_number=1, pit_index=0, favorites=()):
    """Builds one hidden room. Returns (level, entry_x): a Level whose
    `goal` is the Exit, and the x where the player drops in."""
    spec = STYLES[style]
    theme = SimpleNamespace(
        id=f"underground_{style}", name=spec["name"],
        ground_color=spec["ground"], platform_color=spec["ledge"],
        cap_color=spec["cap"], shade_color=spec["shade"],
    )
    b = _LevelBuilder(theme, level_number, favorites)
    b.rng = random.Random(5000 + level_number * 10 + pit_index)
    b.enemy_body_color, b.enemy_foot_color = spec["enemy"]
    b.flying_palette = spec["flying"]
    W = ROOM_WIDTH_TILES

    b._add_ground(0, W)
    for col in (-2, W):                       # walls at both ends of the room
        b._add_platform(col, 0, width_in_tiles=2, height_in_tiles=GROUND_ROW + 2, color=spec["shade"])

    def coins(cols, row):
        for col in cols:
            b._add_collectible(col, row, kind="coin")

    # A: a staircase of ledges, a coin row over each.
    b._add_collectible(6, 13, kind=KONBINI_IDS[b.rng.randrange(len(KONBINI_IDS))])
    for col, row in ((6, 12), (10, 10), (14, 8)):
        b._add_platform(col, row, width_in_tiles=3)
        coins(range(col, col + 3), row - 1)
    b._add_platform(19, 12, width_in_tiles=2)  # step up to the long ledge

    # B: a long high ledge with a coin line, a gift box above it and the
    # treasure at the top of a jump. Enemies patrol the floor beneath.
    b._add_platform(22, 9, width_in_tiles=10)
    coins(range(22, 32), 8)
    b._add_gift_box(29, 6)
    b._add_collectible(25, 5, kind=spec["treasure"])
    coins((24, 27, 30), 13)
    b._add_enemy(spawn_col=23, row=GROUND_ROW - 1, patrol_start_col=21, patrol_end_col=35)
    b._add_enemy(spawn_col=31, row=GROUND_ROW - 1, patrol_start_col=21, patrol_end_col=35)

    # C: pillars (columns / pipes / timber) of rising height, coins on top.
    # The tallest is 3 tiles -- a jump from the floor clears it, so nobody
    # gets trapped in the gaps between them.
    for col, row in ((37, 14), (41, 13), (45, 12)):
        b._add_platform(col, row, width_in_tiles=2, height_in_tiles=GROUND_ROW - row, color=spec["pillar"])
        coins((col, col + 1), row - 1)
    b._add_gift_box(49, 12)
    b._add_enemy(spawn_col=39, row=GROUND_ROW - 1, patrol_start_col=39, patrol_end_col=41)
    if spec["flying"]:
        b._add_flying_enemy(43, top_row=5, bottom_row=10)
        b._add_flying_enemy(52, top_row=6, bottom_row=11)

    # D: a last arc of coins, a snack and a favourite before the exit.
    for col, row in ((51, 12), (52, 11), (53, 10), (54, 10), (55, 11), (56, 12)):
        b._add_collectible(col, row, kind="coin")
    b._add_collectible(53, 13, kind=KONBINI_IDS[b.rng.randrange(len(KONBINI_IDS))])
    if b.favorites:
        b._add_collectible(55, 13, kind=b.favorites[pit_index % len(b.favorites)])
    b._add_enemy(spawn_col=50, row=GROUND_ROW - 1, patrol_start_col=50, patrol_end_col=57)

    exit_sprite = Exit(EXIT_COL * TILE_SIZE, GROUND_ROW * TILE_SIZE, style)
    level = Level(
        platforms=b.platforms, question_blocks=b.question_blocks, gift_boxes=b.gift_boxes,
        enemies=b.enemies, collectibles=b.collectibles, goal=exit_sprite,
        player_start=(ENTRY_COL * TILE_SIZE, 0), width_px=W * TILE_SIZE,
        ground_y=GROUND_ROW * TILE_SIZE, theme=theme, ground_segments_px=b.ground_segments_px,
    )
    return level, ENTRY_COL * TILE_SIZE + TILE_SIZE // 2

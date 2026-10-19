"""The three hidden sky stages -- the way UP, mirroring the underground
stages' way down (kobito/levels/underground.py).

Every level hides three cloud springs in the grass (level1.py,
SECRET_SPRING_SEGMENTS). Land on one and it launches you off the top of
the screen into one of these:

  * rainbow -- Rainbow Bridge (虹 niji): bright pastel sky, giant rainbows,
               white clouds (treasure: 綿あめ cotton candy)
  * thunder -- Thunder Clouds (雷 kaminari): a storm with lightning, rain and
               the thunder god Raijin's ring of drums
               (treasure: 雷おこし kaminari okoshi)
  * moon    -- Moonlit Clouds (月 tsuki): night sky, a huge full moon with
               the moon rabbit, twinkling stars (treasure: 月見団子 dango)

The rooms are built from one-way clouds (jump up through them, land on
top). There is no floor: fall through a gap and you simply drift back
down to the surface -- no life lost. The 出口 at the far end also takes
you back down. Entering teaches the sky word (虹 / 雷 / 月).
"""

import random
from types import SimpleNamespace

import pygame

from kobito.constants import TILE_SIZE
from kobito.entities.exit import Exit
from kobito.entities.platform import CloudPlatform
from kobito.items import KONBINI_IDS
from kobito.levels.level1 import GROUND_ROW, Level, _LevelBuilder

ROOM_WIDTH_TILES = 64
ENTRY_COL = 4
EXIT_COL = 58
CLOUD_ROW = 12      # the start and end clouds; the exit stands on the last one

STYLES = {
    "rainbow": {
        "name": "Rainbow Bridge", "jp": "虹", "reading": "niji", "meaning": "rainbow",
        "example": "虹がきれいです。", "example_en": "The rainbow is beautiful.",
        "cloud": (252, 252, 255), "cloud_shade": (222, 214, 242),
        "enemy": ((255, 255, 255), (190, 186, 210)),
        "flying": ((250, 150, 176), (255, 222, 120)),
        "species": ((("sheep", {"body": (255, 255, 255)}),),                    # cloud sheep, pink birds
                    (("seagull", {"body": (250, 150, 176), "wing": (255, 222, 120)}),)),
        "treasure": "wataame", "hint": "rainbow",
    },
    "thunder": {
        "name": "Thunder Clouds", "jp": "雷", "reading": "kaminari", "meaning": "thunder",
        "example": "雷が鳴っています。", "example_en": "Thunder is rumbling.",
        "cloud": (178, 184, 206), "cloud_shade": (120, 124, 150),
        "enemy": ((250, 206, 70), (210, 60, 50)),
        "flying": ((86, 90, 118), (250, 230, 90)),
        "species": ((("oni", {"body": (250, 206, 70)}),), ("thundercloud",)),     # thunder imps, storm clouds
        "treasure": "kaminari_okoshi", "hint": "spark",
    },
    "moon": {
        "name": "Moonlit Clouds", "jp": "月", "reading": "tsuki", "meaning": "moon",
        "example": "月が明るいです。", "example_en": "The moon is bright.",
        "cloud": (212, 204, 246), "cloud_shade": (150, 138, 204),
        "enemy": ((246, 246, 252), (240, 170, 190)),
        "flying": ((74, 62, 116), (44, 34, 84)),
        "species": (("rabbit",), (("bat", {"body": (74, 62, 116), "wing": (44, 34, 84)}),)),   # moon rabbits, night bats
        "treasure": "tsukimi_dango", "hint": "star",
    },
}


def place_lesson(style):
    s = STYLES[style]
    return f"{s['jp']} ({s['reading']}) = {s['meaning']}.  {s['example']}  ({s['example_en']})"


def build_sky(style, level_number=1, index=0, favorites=()):
    """Builds one hidden sky room. Returns (level, entry_x): a Level whose
    `goal` is the Exit and whose platforms are one-way clouds, and the x
    where the player shoots up into the room."""
    spec = STYLES[style]
    theme = SimpleNamespace(
        id=f"sky_{style}", name=spec["name"], ground_color=spec["cloud"], platform_color=spec["cloud"],
        cap_color=None, shade_color=spec["cloud_shade"],
    )
    b = _LevelBuilder(theme, level_number, favorites)
    b.rng = random.Random(7000 + level_number * 10 + index)
    b.enemy_body_color, b.enemy_foot_color = spec["enemy"]
    b.flying_palette = spec["flying"]
    # This room's own creatures: cloud sheep, thunder imps, moon rabbits, ...
    b.ground_species, b.flying_species = list(spec["species"][0]), list(spec["species"][1])
    W = ROOM_WIDTH_TILES

    def cloud(col, row, width):
        b.platforms.add(CloudPlatform(col * TILE_SIZE, row * TILE_SIZE, width * TILE_SIZE,
                                      color=spec["cloud"], shade=spec["cloud_shade"]))

    def coins(cols, row):
        for col in cols:
            b._add_collectible(col, row, kind="coin")

    def snack(col, row):
        b._add_collectible(col, row, kind=KONBINI_IDS[b.rng.randrange(len(KONBINI_IDS))])

    for col in (-2, W):    # off-screen walls so nobody walks out of the room
        b._add_platform(col, 0, width_in_tiles=2, height_in_tiles=GROUND_ROW + 2, color=spec["cloud_shade"])

    # The start cloud, wide enough to land on after the launch.
    cloud(1, CLOUD_ROW, 9)
    snack(7, CLOUD_ROW - 1)

    # A higher cloud with coins, then a walker on a low one under a gift box.
    cloud(11, 10, 5)
    coins(range(11, 16), 9)
    cloud(17, CLOUD_ROW, 6)
    b._add_gift_box(19, 8)
    b._add_enemy(spawn_col=20, row=CLOUD_ROW - 1, patrol_start_col=17, patrol_end_col=23)

    # The long high cloud: a coin line, a second gift box, and the treasure
    # at the top of a jump.
    cloud(24, 9, 10)
    coins(range(24, 34), 8)
    b._add_collectible(27, 5, kind=spec["treasure"])
    b._add_gift_box(31, 6)

    cloud(35, CLOUD_ROW, 5)
    coins(range(35, 40), CLOUD_ROW - 1)
    b._add_enemy(spawn_col=37, row=CLOUD_ROW - 1, patrol_start_col=35, patrol_end_col=40)

    # Stepping-stone puffs, guarded from the air.
    for col, row in ((41, 10), (45, 8), (49, 10)):
        cloud(col, row, 2)
        coins((col, col + 1), row - 1)
    b._add_flying_enemy(44, top_row=3, bottom_row=8)
    b._add_flying_enemy(48, top_row=4, bottom_row=9)

    # The last cloud: a coin arc, a snack, a favourite, and the way down.
    cloud(52, CLOUD_ROW, W - 52)
    for col, row in ((53, 10), (54, 9), (55, 9), (56, 10)):
        b._add_collectible(col, row, kind="coin")
    snack(53, CLOUD_ROW - 1)
    if b.favorites:
        b._add_collectible(56, CLOUD_ROW - 1, kind=b.favorites[index % len(b.favorites)])

    exit_sprite = Exit(EXIT_COL * TILE_SIZE, CLOUD_ROW * TILE_SIZE, style)
    level = Level(
        platforms=b.platforms, question_blocks=b.question_blocks, gift_boxes=b.gift_boxes,
        enemies=b.enemies, collectibles=b.collectibles, goal=exit_sprite,
        player_start=(ENTRY_COL * TILE_SIZE, 0), width_px=W * TILE_SIZE,
        ground_y=CLOUD_ROW * TILE_SIZE, theme=theme, ground_segments_px=[],
        springs=pygame.sprite.Group(),
    )
    return level, ENTRY_COL * TILE_SIZE + TILE_SIZE // 2

"""Level prizes: a hexagonal badge per level, grouped by JLPT level.

Twenty badges, four per JLPT level from N5 up to N1, so the prize tracks
proficiency rather than just how many levels you've played: clearing a
level at N5 hands you an N5-tier badge (hiragana, first kanji, polite
form), while an N1 clear hands you an N1-tier one. Within a tier the
four cycle by level number, so a long run at one level still keeps
handing out fresh prizes.

Art comes from assets/sprites/badges/<badge id>.png when present (the
hexagonal artwork sheet, sliced one file per badge). Any badge without
art falls back to a drawn hexagon in that badge's colors with its kanji
emblem -- same silhouette as the real art, so a part-finished set still
reads as one collection.

A badge is earned, not given -- see BADGE_PASS_ACCURACY in
kobito/constants.py. The player doesn't need every question right, just
most of them, so a level ends either with the badge earned or with it
shown locked and greyed out.
"""

import math
from dataclasses import dataclass
from pathlib import Path

import pygame

from kobito.fonts import get_font

ART_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "badges"

OUTLINE_RATIO = 1.13  # how far the dark outline extends past the body
FACE_COLOR = (255, 250, 236)
SPARKLE_COLOR = (255, 255, 255)

LOCKED_COLOR = (150, 150, 158)
LOCKED_OUTLINE = (86, 86, 94)
LOCKED_FACE = (206, 206, 212)


@dataclass
class Badge:
    id: str  # also the art filename stem under assets/sprites/badges/
    name: str
    emblem: str  # a single kanji, drawn big in the fallback badge's face
    color: tuple
    outline: tuple
    caption: str
    jlpt: str


# Ordered easiest theme first within each tier, so the prize reads as a
# progression: kana and first kanji at N5, everyday life at N4, then
# steadily more expressive motifs up to N1.
BADGES = [
    # --- N5: kana, first kanji, basic politeness --------------------
    Badge("hiragana_start", "Hiragana Start", "あ", (232, 74, 124), (140, 30, 72),
          "Your very first letter!", "N5"),
    Badge("first_sprout", "First Sprout", "芽", (82, 170, 230), (24, 84, 140),
          "Up through the soil!", "N5"),
    Badge("first_kanji", "First Kanji", "木", (240, 190, 62), (142, 100, 8),
          "One tree, one kanji!", "N5"),
    Badge("polite_form", "Polite Form", "礼", (162, 92, 212), (82, 34, 122),
          "Desu, masu, perfect!", "N5"),

    # --- N4: everyday life and travel -------------------------------
    Badge("milk_run", "Milk Run", "牛", (92, 176, 226), (30, 88, 142),
          "One bottle, one errand!", "N4"),
    Badge("travel_talk", "Travel Talk", "旅", (236, 122, 60), (138, 58, 10),
          "Map read, train caught!", "N4"),
    Badge("blossom_words", "Blossom Words", "花", (240, 112, 162), (144, 34, 88),
          "In full bloom!", "N4"),
    Badge("onsen_break", "Onsen Break", "湯", (62, 172, 172), (14, 88, 92),
          "Soak and study!", "N4"),

    # --- N3: expression, sound, reading -----------------------------
    Badge("rest_day", "Rest Day", "眠", (92, 190, 112), (28, 100, 50),
          "Even kobito nap!", "N3"),
    Badge("sound_pitch", "Sound and Pitch", "音", (246, 152, 62), (146, 76, 8),
          "Every note in tune!", "N3"),
    Badge("water_song", "Water Song", "水", (152, 92, 216), (72, 32, 126),
          "A splash of melody!", "N3"),
    Badge("bookworm", "Bookworm", "本", (238, 186, 56), (140, 96, 6),
          "Read right through!", "N3"),

    # --- N2: nuance and connection ----------------------------------
    Badge("meadow_walk", "Meadow Walk", "草", (122, 196, 112), (44, 104, 48),
          "Out in the open!", "N2"),
    Badge("sharp_eye", "Sharp Eye", "実", (156, 86, 206), (76, 30, 118),
          "You spotted it!", "N2"),
    Badge("sunflower_sun", "Sunflower Sun", "陽", (86, 176, 236), (26, 90, 146),
          "Facing the light!", "N2"),
    Badge("friendship", "Friendship", "友", (246, 152, 132), (150, 66, 52),
          "Better together!", "N2"),

    # --- N1: mastery ------------------------------------------------
    Badge("rain_shelter", "Rain Shelter", "雨", (100, 190, 116), (32, 100, 52),
          "Dry under one leaf!", "N1"),
    Badge("crab_claws", "Crab Claws", "蟹", (240, 122, 166), (144, 40, 90),
          "Nothing slips past!", "N1"),
    Badge("space_walk", "Space Walk", "宙", (58, 74, 126), (20, 28, 62),
          "All the way out here!", "N1"),
    Badge("fish_rider", "Fish Rider", "魚", (240, 190, 70), (142, 100, 12),
          "Riding the current!", "N1"),
]

BADGES_BY_JLPT = {}
for _badge in BADGES:
    BADGES_BY_JLPT.setdefault(_badge.jlpt, []).append(_badge)

_art_cache = {}


def badge_for_level(jlpt_level, level_number):
    """The badge for finishing `level_number` played at `jlpt_level`.

    Falls back to the N5 tier for an unrecognized JLPT level rather than
    raising -- a missing prize should never be what ends a run.
    """
    tier = BADGES_BY_JLPT.get(jlpt_level) or BADGES_BY_JLPT["N5"]
    return tier[(level_number - 1) % len(tier)]


def _load_art(badge_id):
    if badge_id not in _art_cache:
        path = ART_DIR / f"{badge_id}.png"
        _art_cache[badge_id] = pygame.image.load(str(path)).convert_alpha() if path.is_file() else None
    return _art_cache[badge_id]


def _shade(color, factor):
    return tuple(max(0, min(255, round(channel * factor))) for channel in color)


def _hex_points(cx, cy, radius):
    return [
        (cx + radius * math.cos(math.pi / 6 + i * math.pi / 3),
         cy + radius * math.sin(math.pi / 6 + i * math.pi / 3))
        for i in range(6)
    ]


def draw_badge(surface, center_x, center_y, size, badge, earned=True):
    """Draws one badge centered on (center_x, center_y).

    `size` is the badge's overall height. When `earned` is False it's
    drawn greyed out -- the player can see exactly which prize they just
    missed, which nudges a retry far better than hiding it.
    """
    art = _load_art(badge.id)
    if art is not None:
        scale = size / art.get_height()
        scaled = pygame.transform.smoothscale(art, (max(1, round(art.get_width() * scale)), size))
        if not earned:
            scaled = pygame.transform.grayscale(scaled)
        surface.blit(scaled, scaled.get_rect(center=(center_x, center_y)))
        return

    _draw_fallback(surface, center_x, center_y, size, badge, earned)


def _draw_fallback(surface, center_x, center_y, size, badge, earned):
    """A drawn hexagon in the badge's colors -- same silhouette as the
    real artwork, so a badge still reads as part of the set before its
    art has been dropped in.
    """
    if earned:
        color, outline, face = badge.color, badge.outline, FACE_COLOR
    else:
        color, outline, face = LOCKED_COLOR, LOCKED_OUTLINE, LOCKED_FACE

    radius = size / 2 / OUTLINE_RATIO

    # Composited on its own surface so the shadow and gloss can be
    # translucent without smearing whatever is behind the badge.
    pad = round(size * 0.9)
    layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    cx = cy = pad

    pygame.draw.polygon(layer, (0, 0, 0, 60), _hex_points(cx, cy + radius * 0.10, radius * OUTLINE_RATIO))
    pygame.draw.polygon(layer, outline, _hex_points(cx, cy, radius * OUTLINE_RATIO))
    pygame.draw.polygon(layer, color, _hex_points(cx, cy, radius))

    # Gloss: a soft translucent highlight across the upper-left, masked
    # to the silhouette -- an unclipped ellipse spills past the hex
    # corners, which shows as a pale smear on a dark background.
    gloss = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    gloss_rect = pygame.Rect(0, 0, radius * 1.15, radius * 0.72)
    gloss_rect.center = (cx - radius * 0.20, cy - radius * 0.44)
    pygame.draw.ellipse(gloss, (255, 255, 255, 64), gloss_rect)

    mask = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), _hex_points(cx, cy, radius))
    gloss.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    layer.blit(gloss, (0, 0))

    pygame.draw.circle(layer, outline, (cx, cy), radius * 0.60)
    pygame.draw.circle(layer, face, (cx, cy), radius * 0.52)

    emblem_font = get_font(max(12, round(radius * 0.86)))
    emblem_color = outline if earned else (120, 120, 128)
    emblem = emblem_font.render(badge.emblem, True, emblem_color)
    layer.blit(emblem, emblem.get_rect(center=(cx, cy)))

    if earned:
        for dx, dy, scale in ((-0.92, -0.74, 0.20), (0.86, -0.86, 0.15), (0.98, 0.30, 0.11)):
            _draw_sparkle(layer, cx + radius * dx, cy + radius * dy, radius * scale)

    surface.blit(layer, (center_x - pad, center_y - pad))


def _draw_sparkle(surface, x, y, size):
    pygame.draw.polygon(surface, SPARKLE_COLOR, [
        (x, y - size), (x + size * 0.30, y - size * 0.30),
        (x + size, y), (x + size * 0.30, y + size * 0.30),
        (x, y + size), (x - size * 0.30, y + size * 0.30),
        (x - size, y), (x - size * 0.30, y - size * 0.30),
    ])

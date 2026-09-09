"""Level prizes: one cute badge per level, drawn with pygame
primitives so there's no art dependency.

Deliberately cartoon/arcade styled rather than a formal award rosette:
chunky silhouette, thick dark outline, a glossy shine and sparkles --
the look of a mobile-game achievement sticker. Shape varies per badge
as well as color, so a collection of them reads as a set of distinct
prizes rather than one medal in eight palettes.

A badge is earned, not given -- see BADGE_PASS_ACCURACY in
kobito/constants.py. The player doesn't need every question right, just
most of them, so a level ends either with the badge earned or with it
shown locked and greyed out.
"""

import math
from dataclasses import dataclass

import pygame

from kobito.fonts import get_font

STAR = "star"
SHIELD = "shield"
FLOWER = "flower"
HEX = "hex"

OUTLINE_RATIO = 1.13  # how far the dark outline extends past the body
FACE_COLOR = (255, 250, 236)
SPARKLE_COLOR = (255, 255, 255)


@dataclass
class Badge:
    name: str
    emblem: str  # a single kanji, drawn big in the badge's face
    color: tuple
    outline: tuple
    shape: str
    caption: str


# Cycled by level number, so a long run keeps handing out fresh prizes
# instead of repeating one. Each is a real Japanese motif with a
# beginner-friendly kanji, so even the reward teaches a character.
BADGES = [
    Badge("Sakura Seedling", "桜", (247, 126, 168), (146, 44, 84), FLOWER, "Your first bloom!"),
    Badge("Koi Courage", "鯉", (250, 142, 64), (140, 60, 12), STAR, "Swimming upstream!"),
    Badge("Bamboo Focus", "竹", (86, 190, 108), (24, 92, 46), SHIELD, "Straight and steady!"),
    Badge("Crane Grace", "鶴", (94, 162, 240), (26, 72, 138), HEX, "A thousand paper wings!"),
    Badge("Fuji Summit", "山", (126, 118, 232), (52, 44, 128), STAR, "You climbed it!"),
    Badge("Lantern Light", "灯", (255, 196, 62), (146, 96, 8), FLOWER, "Lighting the way!"),
    Badge("Tiger Spirit", "虎", (255, 166, 48), (138, 74, 6), SHIELD, "Fierce and fearless!"),
    Badge("Dragon Mastery", "龍", (170, 112, 240), (78, 34, 136), HEX, "Master of the skies!"),
]

LOCKED_COLOR = (150, 150, 158)
LOCKED_OUTLINE = (86, 86, 94)
LOCKED_FACE = (206, 206, 212)


def badge_for_level(level_number):
    """Badges cycle, so level 9 gets the first badge again."""
    return BADGES[(level_number - 1) % len(BADGES)]


def _shade(color, factor):
    return tuple(max(0, min(255, round(channel * factor))) for channel in color)


def _star_points(cx, cy, radius, tips=5, inner_ratio=0.52):
    points = []
    for i in range(tips * 2):
        angle = -math.pi / 2 + i * math.pi / tips
        r = radius if i % 2 == 0 else radius * inner_ratio
        points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    return points


def _hex_points(cx, cy, radius):
    return [
        (cx + radius * math.cos(math.pi / 6 + i * math.pi / 3),
         cy + radius * math.sin(math.pi / 6 + i * math.pi / 3))
        for i in range(6)
    ]


def _shield_points(cx, cy, radius):
    # Flat shoulders, straight sides, then a point at the bottom -- the
    # classic game-shield silhouette.
    half = radius * 0.88
    return [
        (cx - half, cy - radius * 0.80),
        (cx + half, cy - radius * 0.80),
        (cx + half, cy + radius * 0.12),
        (cx + half * 0.52, cy + radius * 0.72),
        (cx, cy + radius),
        (cx - half * 0.52, cy + radius * 0.72),
        (cx - half, cy + radius * 0.12),
    ]


def _draw_body(surface, shape, cx, cy, radius, color):
    """Draws one badge silhouette. Flower is petal circles rather than a
    polygon, so it gets its own branch.
    """
    if shape == FLOWER:
        petals = 8
        for i in range(petals):
            angle = i * 2 * math.pi / petals
            pygame.draw.circle(
                surface, color,
                (cx + math.cos(angle) * radius * 0.62, cy + math.sin(angle) * radius * 0.62),
                radius * 0.46,
            )
        pygame.draw.circle(surface, color, (cx, cy), radius * 0.66)
        return

    points = {
        STAR: _star_points,
        HEX: _hex_points,
        SHIELD: _shield_points,
    }[shape](cx, cy, radius)
    pygame.draw.polygon(surface, color, points)


def draw_badge(surface, center_x, center_y, size, badge, earned=True):
    """Draws one badge centered on (center_x, center_y).

    `size` is the badge's overall diameter. When `earned` is False it's
    drawn greyed out -- the player can see exactly which prize they just
    missed, which nudges a retry far better than hiding it.
    """
    if earned:
        color, outline, face = badge.color, badge.outline, FACE_COLOR
    else:
        color, outline, face = LOCKED_COLOR, LOCKED_OUTLINE, LOCKED_FACE

    radius = size / 2 / OUTLINE_RATIO
    shape = badge.shape

    # Composited on its own surface so the shadow and gloss can be
    # translucent without smearing whatever is behind the badge.
    pad = round(size * 0.9)
    layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    cx = cy = pad

    _draw_body(layer, shape, cx, cy + radius * 0.10, radius * OUTLINE_RATIO, (0, 0, 0, 60))
    _draw_body(layer, shape, cx, cy, radius * OUTLINE_RATIO, outline)
    _draw_body(layer, shape, cx, cy, radius, color)

    # Gloss: a soft translucent highlight across the upper-left, the
    # cue that makes a flat shape read as a shiny cartoon object. It has
    # to be masked to the silhouette first -- an unclipped ellipse spills
    # into the transparent gaps between a star's arms, which is invisible
    # on a pale background but shows as a pale smear on a dark one.
    gloss = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    gloss_rect = pygame.Rect(0, 0, radius * 1.15, radius * 0.72)
    gloss_rect.center = (cx - radius * 0.20, cy - radius * 0.44)
    pygame.draw.ellipse(gloss, (255, 255, 255, 64), gloss_rect)

    mask = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    _draw_body(mask, shape, cx, cy, radius, (255, 255, 255, 255))
    gloss.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    layer.blit(gloss, (0, 0))

    # Face disc the emblem sits on, with its own dark rim.
    pygame.draw.circle(layer, outline, (cx, cy), radius * 0.60)
    pygame.draw.circle(layer, face, (cx, cy), radius * 0.52)

    emblem_font = get_font(max(12, round(radius * 0.86)))
    emblem_color = _shade(outline, 1.0) if earned else (120, 120, 128)
    emblem = emblem_font.render(badge.emblem, True, emblem_color)
    layer.blit(emblem, emblem.get_rect(center=(cx, cy)))

    if earned:
        # Chunky four-point sparkles rather than dots -- reads as
        # "shiny prize" instead of stray pixels.
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

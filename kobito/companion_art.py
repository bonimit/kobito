"""AI hint companion art. Loads real sprite frames from
assets/sprites/<companion_id>/<expression>.png when present, falling
back to a simple placeholder shape (same idea as kobito/assets.py's
fallback for mascot animations) shaded with that companion's `color`
for any expression that isn't there yet.

Generalizes what was originally kobito-only art (kobito_companion.py)
to any companion in kobito/companions.py, since the player now picks
one of several companions rather than always getting Kobito.
"""

from pathlib import Path

import pygame

from kobito.companions import get_companion

SPRITES_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites"
EXPRESSIONS = ("idle", "thinking", "talking", "happy", "sympathetic")

CAP_COLOR = (92, 64, 40)
EYE_COLOR = (40, 32, 24)

_image_cache = {}


def _load_image(companion_id, expression):
    key = (companion_id, expression)
    if key not in _image_cache:
        path = SPRITES_DIR / companion_id / f"{expression}.png"
        _image_cache[key] = pygame.image.load(str(path)).convert_alpha() if path.is_file() else None
    return _image_cache[key]


def draw_companion(screen, companion_id, x, y, size, expression="idle"):
    if expression not in EXPRESSIONS:
        expression = "idle"

    image = _load_image(companion_id, expression)
    if image is not None:
        scale = size / image.get_height()
        scaled = pygame.transform.smoothscale(image, (max(1, round(image.get_width() * scale)), size))
        screen.blit(scaled, scaled.get_rect(center=(x, y)))
        return

    _draw_placeholder(screen, companion_id, x, y, size, expression)


def _draw_placeholder(screen, companion_id, x, y, size, expression):
    """Flat-shape fallback for any companion/expression without a real
    frame yet -- same leaf-cap forest-spirit silhouette as Kobito's
    original design, recolored per companion.
    """
    body_color = get_companion(companion_id)["color"]
    body_shade = tuple(max(0, round(channel * 0.78)) for channel in body_color)

    body_rect = pygame.Rect(0, 0, size, size)
    body_rect.center = (x, y)
    pygame.draw.ellipse(screen, body_color, body_rect)
    pygame.draw.ellipse(screen, body_shade, body_rect, width=max(1, round(size * 0.06)))

    cap_points = [
        (x, y - size * 0.75),
        (x - size * 0.42, y - size * 0.22),
        (x + size * 0.42, y - size * 0.22),
    ]
    pygame.draw.polygon(screen, CAP_COLOR, cap_points)

    eye_y = y - size * 0.04
    eye_offset = size * 0.18
    if expression == "thinking":
        for ex in (x - eye_offset, x + eye_offset):
            pygame.draw.line(screen, EYE_COLOR, (ex - 3, eye_y), (ex + 3, eye_y), 2)
        pygame.draw.line(screen, EYE_COLOR, (x - size * 0.08, y + size * 0.18), (x + size * 0.08, y + size * 0.18), 2)
    elif expression in ("happy", "talking"):
        for ex in (x - eye_offset, x + eye_offset):
            pygame.draw.circle(screen, EYE_COLOR, (int(ex), int(eye_y)), max(1, round(size * 0.06)))
        pygame.draw.arc(
            screen, EYE_COLOR,
            (x - size * 0.2, y + size * 0.02, size * 0.4, size * 0.25),
            3.4, 6.0, 2,
        )
    else:  # idle / sympathetic
        for ex in (x - eye_offset, x + eye_offset):
            pygame.draw.circle(screen, EYE_COLOR, (int(ex), int(eye_y)), max(1, round(size * 0.06)))
        pygame.draw.line(screen, EYE_COLOR, (x - size * 0.09, y + size * 0.16), (x + size * 0.09, y + size * 0.16), 2)

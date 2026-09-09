"""Kobito, the AI hint companion's art. Loads real sprite frames from
assets/sprites/kobito/<expression>.png when present, falling back to a
simple placeholder shape (same idea as kobito/assets.py's fallback for
mascot animations) for any expression that isn't there yet.
"""

from pathlib import Path

import pygame

SPRITES_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites" / "kobito"
EXPRESSIONS = ("idle", "thinking", "talking", "happy", "sympathetic")

BODY_COLOR = (139, 195, 116)
BODY_SHADE = (108, 165, 90)
CAP_COLOR = (92, 64, 40)
EYE_COLOR = (40, 32, 24)

_image_cache = {}


def _load_image(expression):
    if expression not in _image_cache:
        path = SPRITES_DIR / f"{expression}.png"
        _image_cache[expression] = pygame.image.load(str(path)).convert_alpha() if path.is_file() else None
    return _image_cache[expression]


def draw_kobito(screen, x, y, size, expression="idle"):
    if expression not in EXPRESSIONS:
        expression = "idle"

    image = _load_image(expression)
    if image is not None:
        scale = size / image.get_height()
        scaled = pygame.transform.smoothscale(image, (max(1, round(image.get_width() * scale)), size))
        screen.blit(scaled, scaled.get_rect(center=(x, y)))
        return

    _draw_placeholder(screen, x, y, size, expression)


def _draw_placeholder(screen, x, y, size, expression):
    """Flat-shape fallback for any expression without a real frame yet
    -- same green/leaf-cap forest-spirit design brief as the real art.
    """
    body_rect = pygame.Rect(0, 0, size, size)
    body_rect.center = (x, y)
    pygame.draw.ellipse(screen, BODY_COLOR, body_rect)
    pygame.draw.ellipse(screen, BODY_SHADE, body_rect, width=max(1, round(size * 0.06)))

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

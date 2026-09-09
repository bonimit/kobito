"""Placeholder art for Kobito, the AI hint companion, until real sprite
frames exist (they'd slot in the same way character frames do -- see
kobito/assets.py -- once available). A small round forest-spirit body
with a leaf-cap: green/brown palette, no legs (floats), matching the
design brief used to generate real art later.
"""

import pygame

BODY_COLOR = (139, 195, 116)
BODY_SHADE = (108, 165, 90)
CAP_COLOR = (92, 64, 40)
EYE_COLOR = (40, 32, 24)


def draw_kobito(screen, x, y, size, expression="idle"):
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
    elif expression == "happy":
        for ex in (x - eye_offset, x + eye_offset):
            pygame.draw.circle(screen, EYE_COLOR, (int(ex), int(eye_y)), max(1, round(size * 0.06)))
        pygame.draw.arc(
            screen, EYE_COLOR,
            (x - size * 0.2, y + size * 0.02, size * 0.4, size * 0.25),
            3.4, 6.0, 2,
        )
    else:  # idle / talking
        for ex in (x - eye_offset, x + eye_offset):
            pygame.draw.circle(screen, EYE_COLOR, (int(ex), int(eye_y)), max(1, round(size * 0.06)))
        pygame.draw.line(screen, EYE_COLOR, (x - size * 0.09, y + size * 0.16), (x + size * 0.09, y + size * 0.16), 2)

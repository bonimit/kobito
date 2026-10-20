"""Shared look for in-game UI: panels, outlined text and small icons, so the
HUD, the companion's box, the settings screen and the end-of-level card all
read as one game.

Type hierarchy (see kobito/fonts.py):
  * TITLE  -- pixel 32: screen titles, the big numbers (score, quiz count)
  * LABEL  -- pixel 16: small caps labels ("SCORE", "POWER"), hints
  * BODY   -- rounded 18-20: sentences (companion lines, menu items)
"""

import pygame

from kobito.fonts import pixel_font, rounded_font

PANEL_BG = (16, 13, 28, 178)
PANEL_EDGE = (255, 214, 150, 120)
GOLD = (255, 210, 110)
CREAM = (255, 246, 226)
MUTED = (190, 182, 205)
OUTLINE = (20, 14, 26)
RED = (240, 86, 96)
GREEN = (110, 220, 130)
SKY = (150, 205, 255)


def title_font(size=32):
    return pixel_font(size)


def label_font(size=16):
    return pixel_font(size)


def body_font(size=18):
    return rounded_font(size)


def fit(string, make_font, max_width, sizes):
    """The largest font in `sizes` (biggest first) whose rendering of `string` fits `max_width`
    (the smallest if none does): ui.fit(name, ui.body_font, 90, (16, 14, 12))."""
    for size in sizes:
        font = make_font(size)
        if font.size(string)[0] <= max_width:
            return font
    return make_font(sizes[-1])


def ellipsize(string, font, max_width):
    """`string` cut with "…" so it fits `max_width` pixels in `font`."""
    if font.size(string)[0] <= max_width:
        return string
    while len(string) > 1 and font.size(string + "…")[0] > max_width:
        string = string[:-1]
    return string.rstrip() + "…"


def panel(surface, rect, bg=PANEL_BG, edge=PANEL_EDGE, radius=12, alpha=1.0):
    """A translucent rounded card -- the one container style for all UI."""
    rect = pygame.Rect(rect)
    card = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(card, (*bg[:3], round(bg[3] * alpha)), card.get_rect(), border_radius=radius)
    if edge:
        pygame.draw.rect(card, (*edge[:3], round(edge[3] * alpha)), card.get_rect(), width=2, border_radius=radius)
    surface.blit(card, rect.topleft)
    return rect


def text(surface, string, font, pos, color=CREAM, outline=OUTLINE, anchor="topleft", thickness=2):
    """Text with a crisp dark outline, so it stays readable over any world.
    `anchor` is any pygame.Rect attribute ("topleft", "center", "midtop",
    "topright", ...). Returns the text's rect."""
    face = font.render(string, True, color)
    rect = face.get_rect(**{anchor: pos})
    if outline:
        edge = font.render(string, True, outline)
        for dx in range(-thickness, thickness + 1):
            for dy in range(-thickness, thickness + 1):
                if dx or dy:
                    surface.blit(edge, (rect.x + dx, rect.y + dy))
    surface.blit(face, rect)
    return rect


def heart(surface, center, size, color=RED, empty=False):
    x, y = center
    r = size // 4
    shape = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)
    cx, cy = size // 2 + 2, size // 2 + 2
    pts = [(cx - size // 2 + 1, cy - r // 2), (cx, cy + size // 2 - 1), (cx + size // 2 - 1, cy - r // 2)]
    for fill, grow in ((OUTLINE, 2), ((70, 60, 80) if empty else color, 0)):
        pygame.draw.circle(shape, fill, (cx - r, cy - r // 2), r + grow)
        pygame.draw.circle(shape, fill, (cx + r, cy - r // 2), r + grow)
        pygame.draw.polygon(shape, fill, [(px, py + (grow if py > cy else -grow)) for px, py in pts])
    if not empty:
        pygame.draw.circle(shape, (255, 190, 196), (cx - r - 1, cy - r), max(1, r // 3))
    surface.blit(shape, shape.get_rect(center=(x, y)))


def gear(surface, center, size, color=CREAM):
    import math
    x, y = center
    r = size // 2
    for i in range(8):
        a = i * math.pi / 4
        pygame.draw.line(surface, OUTLINE, (x, y), (x + math.cos(a) * r, y + math.sin(a) * r), 7)
    for i in range(8):
        a = i * math.pi / 4
        pygame.draw.line(surface, color, (x, y), (x + math.cos(a) * (r - 1), y + math.sin(a) * (r - 1)), 4)
    pygame.draw.circle(surface, OUTLINE, (x, y), r - 3)
    pygame.draw.circle(surface, color, (x, y), r - 5)
    pygame.draw.circle(surface, OUTLINE, (x, y), max(2, r // 3))


def item_box_icon(surface, center, size):
    """A little wooden crate with a lid -- 'everything you've picked up'."""
    rect = pygame.Rect(0, 0, size, round(size * 0.8))
    rect.center = center
    pygame.draw.rect(surface, OUTLINE, rect.inflate(4, 4), border_radius=4)
    pygame.draw.rect(surface, (196, 140, 80), rect, border_radius=3)
    lid = pygame.Rect(rect.x - 2, rect.y - 2, rect.width + 4, max(4, size // 4))
    pygame.draw.rect(surface, OUTLINE, lid.inflate(2, 2), border_radius=3)
    pygame.draw.rect(surface, (226, 172, 104), lid, border_radius=3)
    pygame.draw.line(surface, (150, 100, 56), (rect.x + 3, rect.centery + 2), (rect.right - 4, rect.centery + 2), 2)
    pygame.draw.rect(surface, GOLD, (rect.centerx - 3, lid.bottom - 1, 6, 5))


def count_badge(surface, center, value):
    """A small round counter (like an app-icon badge) for icons."""
    font = label_font(16)
    label = font.render(str(value), True, CREAM)
    w = max(18, label.get_width() + 8)
    rect = pygame.Rect(0, 0, w, 18)
    rect.center = center
    pygame.draw.rect(surface, OUTLINE, rect.inflate(2, 2), border_radius=9)
    pygame.draw.rect(surface, (210, 60, 80), rect, border_radius=9)
    surface.blit(label, label.get_rect(center=(rect.centerx, rect.centery)))


def bar(surface, rect, fraction, fill, bg=(50, 44, 64), radius=4):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, OUTLINE, rect.inflate(4, 4), border_radius=radius + 1)
    pygame.draw.rect(surface, bg, rect, border_radius=radius)
    w = round(rect.width * max(0.0, min(1.0, fraction)))
    if w > 0:
        pygame.draw.rect(surface, fill, (rect.x, rect.y, w, rect.height), border_radius=radius)

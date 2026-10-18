"""Shared look for the new-game setup screens (mascot, companion, world,
difficulty): an animated city backdrop under a dark veil, the step bar
(HERO › COMPANION › WORLD › LEVEL), titles, a roster strip, arrow and
confirm buttons, and the keycap hints row.

The backdrop is one shared, slowly scrolling scene, so moving from one
setup screen to the next feels like the same place.
"""

import math

import pygame

from kobito import ui
from kobito.constants import IS_WEB, SCREEN_HEIGHT, SCREEN_WIDTH

STEPS = ("HERO", "COMPANION", "WORLD", "LEVEL")
STAGE = pygame.Rect(36, 110, 424, 292)      # left: the big animated pick
CARD = pygame.Rect(476, 110, 448, 292)      # right: what the pick is about
ROSTER_Y = 414
ROSTER_H = 72
CONFIRM = pygame.Rect(0, 0, 196, 58)
CONFIRM.topright = (SCREEN_WIDTH - 36, ROSTER_Y + (ROSTER_H - 58) // 2)
STAGE_BG = (20, 16, 36, 225)
CARD_BG = (18, 14, 32, 235)
SCROLL_SPEED = 22.0       # backdrop drift, px/s


class Backdrop:
    def __init__(self, theme_id="tokyo"):
        from kobito.background import Background
        from kobito.levels.level1 import build_level1
        level = build_level1(theme_id)
        self.background = Background(level.width_px, level.ground_y, level.ground_segments_px, level.theme)
        self.span = max(1, level.width_px - SCREEN_WIDTH)
        self.camera_x = 0.0
        self.veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(SCREEN_HEIGHT):
            alpha = round(150 + 70 * (y / SCREEN_HEIGHT))
            pygame.draw.line(self.veil, (10, 7, 20, alpha), (0, y), (SCREEN_WIDTH, y))

    def update(self, dt):
        self.background.update(dt)
        self.camera_x = (self.camera_x + SCROLL_SPEED * dt) % self.span

    def draw(self, screen):
        self.background.draw(screen, self.camera_x)
        screen.blit(self.veil, (0, 0))


_backdrop = None


def backdrop():
    global _backdrop
    if _backdrop is None:
        _backdrop = Backdrop()
    return _backdrop


def draw_steps(screen, current):
    """① HERO › ② COMPANION › ③ WORLD › ④ LEVEL, with the current step lit."""
    font = ui.label_font(16)
    parts = []
    for i, name in enumerate(STEPS):
        label = font.render(name, True, ui.CREAM)
        parts.append((i, name, 26 + 8 + label.get_width()))
    gap = 34
    total = sum(w for *_, w in parts) + gap * (len(parts) - 1)
    x = SCREEN_WIDTH // 2 - total // 2
    y = 24
    for i, name, width in parts:
        done, here = i < current, i == current
        color = ui.GOLD if here else (ui.GREEN if done else (120, 112, 140))
        pygame.draw.circle(screen, ui.OUTLINE, (x + 13, y), 14)
        pygame.draw.circle(screen, color, (x + 13, y), 12, width=0 if here or done else 2)
        if done:
            check(screen, (x + 13, y), ui.OUTLINE)
        else:
            ui.text(screen, str(i + 1), font, (x + 13, y), color=ui.OUTLINE if here else color, outline=None,
                    anchor="center")
        ui.text(screen, name, font, (x + 34, y), color=ui.CREAM if here else color, anchor="midleft", thickness=1)
        x += width
        if i < len(parts) - 1:
            pygame.draw.line(screen, (90, 84, 112), (x + 8, y), (x + gap - 8, y), 2)
            x += gap


def draw_title(screen, title, jp):
    ui.text(screen, title, ui.title_font(36), (SCREEN_WIDTH // 2, 64), anchor="center", thickness=3)
    ui.text(screen, jp, ui.body_font(15), (SCREEN_WIDTH // 2, 86), color=ui.GOLD, anchor="midtop", thickness=1)


# Symbols are drawn as shapes: the bundled pixel fonts have no glyphs for
# arrows, check marks or stars.

def triangle(screen, center, size, direction, color):
    """A filled ◀ (direction -1) or ▶ (+1)."""
    x, y = center
    pygame.draw.polygon(screen, color, [(x + size * direction, y), (x - size * direction, y - size),
                                        (x - size * direction, y + size)])


def check(screen, center, color, size=6):
    x, y = center
    pygame.draw.lines(screen, color, False, [(x - size, y), (x - size // 3, y + size * 2 // 3),
                                             (x + size, y - size * 2 // 3)], 3)


def star(screen, center, r, color):
    """A five-pointed star."""
    x, y = center
    points = []
    for k in range(10):
        radius = r if k % 2 == 0 else r * 0.45
        a = -math.pi / 2 + k * math.pi / 5
        points.append((x + radius * math.cos(a), y + radius * math.sin(a)))
    pygame.draw.polygon(screen, color, points)


def sparkle(screen, center, r, color):
    """A four-pointed twinkle."""
    x, y = center
    pygame.draw.polygon(screen, color, [(x, y - r), (x + r * 0.28, y - r * 0.28), (x + r, y),
                                        (x + r * 0.28, y + r * 0.28), (x, y + r), (x - r * 0.28, y + r * 0.28),
                                        (x - r, y), (x - r * 0.28, y - r * 0.28)])


def spotlight(screen, rect, color, t):
    """A soft pulsing glow on the stage, and a pedestal to stand on."""
    cx, floor = rect.centerx, rect.bottom - 52
    glow = pygame.Surface(rect.size, pygame.SRCALPHA)
    pulse = 0.85 + 0.15 * math.sin(t * 2.0)
    for radius, alpha in ((150, 26), (112, 36), (78, 46)):
        pygame.draw.circle(glow, (*color, round(alpha * pulse)), (rect.width // 2, floor - rect.y - 70), radius)
    screen.blit(glow, rect.topleft)
    pedestal = pygame.Rect(0, 0, 190, 34)
    pedestal.center = (cx, floor)
    pygame.draw.ellipse(screen, (12, 8, 22), pedestal.move(0, 6))
    pygame.draw.ellipse(screen, (64, 52, 92), pedestal)
    pygame.draw.ellipse(screen, (*color,), pedestal, width=3)
    return floor


def arrow_button(screen, center, direction, active=True):
    """A round ‹ or › button; returns its rect for clicks."""
    rect = pygame.Rect(0, 0, 44, 44)
    rect.center = center
    pygame.draw.circle(screen, ui.OUTLINE, center, 23)
    pygame.draw.circle(screen, (60, 50, 88) if active else (40, 34, 58), center, 21)
    pygame.draw.circle(screen, ui.GOLD, center, 21, width=2)
    triangle(screen, (center[0] + 2 * direction, center[1]), 8, direction, ui.CREAM)
    return rect


def roster(screen, count, index, card_w, draw_item, t):
    """A row of cards along the bottom-left; the selected one is lifted and
    ringed in gold. `draw_item(i, rect, selected)` fills each card.
    Returns the card rects (for clicks / taps)."""
    gap = 10
    rects = []
    x = 36
    for i in range(count):
        selected = i == index
        rect = pygame.Rect(x, ROSTER_Y + (0 if selected else 6), card_w, ROSTER_H - 6)
        if selected:
            rect.y -= round(2 * math.sin(t * 5))
        ui.panel(screen, rect, bg=(44, 36, 70, 240) if selected else (24, 20, 40, 220),
                 edge=(*ui.GOLD, 255) if selected else (120, 110, 150, 140), radius=10)
        if selected:
            pygame.draw.rect(screen, ui.GOLD, rect.inflate(4, 4), width=2, border_radius=12)
        draw_item(i, rect, selected)
        rects.append(rect)
        x += card_w + gap
    return rects


def confirm_button(screen, label, t, flash=0.0):
    rect = CONFIRM
    lift = round(2 * math.sin(t * 4))
    face = rect.move(0, -lift)
    pygame.draw.rect(screen, ui.OUTLINE, face.move(0, 4).inflate(4, 4), border_radius=14)
    color = tuple(min(255, round(c + (255 - c) * flash)) for c in (255, 196, 70))
    pygame.draw.rect(screen, color, face, border_radius=12)
    pygame.draw.rect(screen, (255, 236, 170), face.inflate(-8, -8), width=2, border_radius=10)
    font = ui.label_font(16)
    width = font.size(label)[0] + 22
    left = face.centerx - width // 2
    ui.text(screen, label, font, (left, face.centery), color=ui.OUTLINE, outline=None, anchor="midleft")
    triangle(screen, (left + width - 7, face.centery), 7, 1, ui.OUTLINE)
    return rect


ARROWS = "<>"     # keycap label drawn as ◀ ▶


def _key_width(font, key):
    return 44 if key == ARROWS else max(26, font.size(key)[0] + 14)


def keycap(screen, key, x, y):
    font = ui.label_font(16)
    rect = pygame.Rect(x, y - 13, _key_width(font, key), 26)
    pygame.draw.rect(screen, (12, 8, 20), rect.move(0, 3), border_radius=6)
    pygame.draw.rect(screen, (70, 62, 96), rect, border_radius=6)
    pygame.draw.rect(screen, (130, 120, 160), rect, width=1, border_radius=6)
    if key == ARROWS:
        triangle(screen, (rect.centerx - 9, rect.centery), 5, -1, ui.CREAM)
        triangle(screen, (rect.centerx + 9, rect.centery), 5, 1, ui.CREAM)
    else:
        label = font.render(key, True, ui.CREAM)
        screen.blit(label, label.get_rect(center=rect.center))
    return rect.right


def hints(screen, items):
    """Keycap hints centred at the bottom: [(key, what it does), ...]."""
    if IS_WEB:
        items = [("Tap", "a card to look"), ("Tap again", "to choose")]
    font = ui.label_font(16)
    widths = []
    for key, words in items:
        widths.append(_key_width(font, key) + 8 + font.size(words)[0])
    gap = 26
    x = SCREEN_WIDTH // 2 - (sum(widths) + gap * (len(items) - 1)) // 2
    y = SCREEN_HEIGHT - 26
    for (key, words), width in zip(items, widths):
        right = keycap(screen, key, x, y)
        ui.text(screen, words, font, (right + 8, y), color=ui.MUTED, anchor="midleft", thickness=1)
        x += width + gap


def wrap(text, font, width):
    from kobito.stage_end_screens import wrap as _wrap
    return _wrap(text, font, width)

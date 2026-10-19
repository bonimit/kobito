"""Pop-ups for things worth celebrating -- a trophy, a finished daily
mission -- shown one at a time at the top of whatever screen is up (a
stage, the town, the notice board). They come from profile.events (see
kobito/progress.py): call update(dt) and draw(screen) each frame.
"""

import pygame

from kobito import audio, ui

SHOW_SECONDS = 3.4
SLIDE_SECONDS = 0.25
CARD = pygame.Rect(0, 0, 440, 54)
CARD_Y = 166       # under the HUD cards


def draw_trophy(surface, center, size, color):
    """A little trophy cup (or, for missions, the same cup in green)."""
    x, y = center
    s = size
    dark = tuple(max(0, c - 70) for c in color)
    cup = [(x - s * 0.42, y - s * 0.45), (x + s * 0.42, y - s * 0.45), (x + s * 0.3, y + s * 0.05),
           (x - s * 0.3, y + s * 0.05)]
    for side in (-1, 1):                                                   # handles
        pygame.draw.circle(surface, ui.OUTLINE, (x + side * s * 0.42, y - s * 0.25), s * 0.18, 3)
    pygame.draw.polygon(surface, ui.OUTLINE, [(px + (2 if px > x else -2), py) for px, py in cup])
    pygame.draw.polygon(surface, color, cup)
    pygame.draw.rect(surface, ui.OUTLINE, (x - s * 0.08, y, s * 0.16, s * 0.3))
    pygame.draw.rect(surface, ui.OUTLINE, (x - s * 0.32, y + s * 0.28, s * 0.64, s * 0.18), border_radius=2)
    pygame.draw.rect(surface, dark, (x - s * 0.28, y + s * 0.3, s * 0.56, s * 0.12), border_radius=2)
    pygame.draw.line(surface, tuple(min(255, c + 60) for c in color), (x - s * 0.22, y - s * 0.38),
                     (x - s * 0.16, y - s * 0.08), 2)


class Toasts:
    def __init__(self, profile):
        self.profile = profile
        self.current = None      # (event, seconds shown)

    def update(self, dt):
        if self.current is None and self.profile.events:
            event = self.profile.events.pop(0)
            self.current = [event, 0.0]
            audio.play("levelup" if event["kind"] == "trophy" else "gift")
        elif self.current is not None:
            self.current[1] += dt
            if self.current[1] >= SHOW_SECONDS:
                self.current = None

    def draw(self, screen):
        if self.current is None:
            return
        event, t = self.current
        slide = min(1.0, t / SLIDE_SECONDS, (SHOW_SECONDS - t) / SLIDE_SECONDS)
        card = CARD.copy()
        card.midtop = (screen.get_width() // 2, round(CARD_Y - (1 - slide) * 90))
        trophy = event["kind"] == "trophy"
        edge = ui.GOLD if trophy else ui.GREEN
        ui.panel(screen, card, bg=(22, 16, 36, 240), edge=(*edge, 230), radius=14)
        draw_trophy(screen, (card.x + 30, card.centery - 2), 30, ui.GOLD if trophy else ui.GREEN)
        ui.text(screen, event["title"], ui.label_font(16), (card.x + 56, card.y + 9), color=edge)
        sub = event["sub"]
        font = ui.body_font(14)
        while font.size(sub)[0] > card.width - 70 and len(sub) > 8:
            sub = sub[:-2] + "…"
        ui.text(screen, sub, font, (card.x + 56, card.y + 30), color=ui.CREAM, thickness=1)

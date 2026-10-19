import math

import pygame

from kobito.entities.platform import Platform
from kobito.fonts import pixel_font

SIZE_RATIO = 1.15  # fraction of a full tile cell the block occupies -- a bit bigger than the grid cell
INK = (30, 20, 26)

# Each world gets a block colour picked to stand out from its scenery
# (turquoise in the desert, coral under the sea, jade in Korea, ...), so a
# quiz box never melts into the background.
THEME_COLORS = {
    "forest": (255, 186, 30),
    "desert": (40, 196, 214),
    "arabian_night": (255, 196, 50),
    "underwater": (255, 112, 86),
    "sky": (255, 120, 190),
    "tokyo": (255, 70, 160),
    "nagano": (255, 160, 30),
    "okinawa": (255, 96, 70),
    "hokkaido": (236, 70, 86),
    "kyoto": (255, 190, 40),
    "island": (255, 100, 170),
    "fairy_tale": (150, 110, 255),
    "london": (255, 196, 30),
    "new_york": (40, 200, 255),
    "korea": (60, 196, 140),
    "okinawa_drive": (255, 96, 140),
    "aomori": (255, 196, 40),
    "shizuoka": (255, 120, 60),
    "hokkaido_farm": (255, 150, 30),
}
DEFAULT_COLOR = (255, 186, 30)
USED_FACE = (96, 88, 100)
USED_LIGHT = (128, 120, 132)
USED_DARK = (64, 58, 70)

FACES = ("classic", "medallion", "kanji")   # rotated through a level's blocks
GLINT_PERIOD = 2.6   # seconds between shine sweeps
GLINT_TIME = 0.45


def _mix(color, other, t):
    return tuple(round(c + (o - c) * t) for c, o in zip(color, other))


class QuestionBlock(Platform):
    """A solid block that triggers a Japanese question the first time
    the player touches it.

    Subclassing Platform means it's automatically solid -- the player
    collides with it exactly like any other tile, with zero extra
    physics code. `used` just tracks whether this particular block has
    already been answered, so it doesn't fire again.

    Drawn slightly larger than a full tile cell (see SIZE_RATIO) and
    centered on it, as a chunky bevelled block with a dark outline, in a
    colour chosen per world (THEME_COLORS) so it pops off the scenery.
    Its face varies through a level -- a classic "?", a "?" medallion with
    stars, or 問 (mon, "question") -- and a shine sweeps
    across it every few seconds (see animate). Once answered it turns to
    dull stone with a green check (right) or a red cross (wrong).
    """

    def __init__(self, cell_x, cell_y, cell_size, theme_id="forest", variant=0):
        block_size = round(cell_size * SIZE_RATIO)
        offset = (cell_size - block_size) // 2
        self.base_color = THEME_COLORS.get(theme_id, DEFAULT_COLOR)
        super().__init__(cell_x + offset, cell_y + offset, block_size, block_size, color=self.base_color)
        self.image = pygame.Surface((block_size, block_size), pygame.SRCALPHA)
        self.face = FACES[variant % len(FACES)]
        self.phase = (variant * 0.37) % 1.0   # so neighbouring blocks don't shine in sync
        self.used = False
        self.pending_question = None   # a skipped question waits here for the player to return
        self.resting = False           # just skipped: don't reopen until the player steps away
        self._active_frame = self._render(active=True)
        self._used_frame = self._render(active=False)
        self._wrong_frame = self._render(active=False, wrong=True)
        self.answered_wrong = False
        self.image = self._active_frame.copy()

    @property
    def glow_color(self):
        return _mix(self.base_color, (255, 255, 255), 0.35)

    # -- Drawing ---------------------------------------------------------------

    def _render(self, active, wrong=False):
        size = self.rect.width
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        face = self.base_color if active else USED_FACE
        light = _mix(face, (255, 255, 255), 0.45) if active else USED_LIGHT
        dark = _mix(face, (0, 0, 0), 0.4) if active else USED_DARK
        outer = image.get_rect()
        pygame.draw.rect(image, INK, outer, border_radius=6)
        inner = outer.inflate(-4, -4)
        pygame.draw.rect(image, dark, inner, border_radius=5)          # bevel shadow (bottom/right)
        pygame.draw.rect(image, light, inner.move(0, 0).inflate(-3, -3).move(-1, -1), border_radius=5)
        top = inner.inflate(-7, -7)
        pygame.draw.rect(image, face, top, border_radius=4)
        for cx, cy in ((top.left + 2, top.top + 2), (top.right - 3, top.top + 2),
                       (top.left + 2, top.bottom - 3), (top.right - 3, top.bottom - 3)):
            pygame.draw.circle(image, dark, (cx, cy), 2)              # rivets
        if not active:
            c = outer.center
            if wrong:
                # Answered wrong: a red cross.
                for (x1, y1), (x2, y2) in (((-7, -7), (7, 7)), ((7, -7), (-7, 7))):
                    pygame.draw.line(image, INK, (c[0] + x1, c[1] + y1), (c[0] + x2, c[1] + y2), 6)
                    pygame.draw.line(image, (240, 96, 96), (c[0] + x1, c[1] + y1), (c[0] + x2, c[1] + y2), 4)
            else:
                # Answered right: a green check.
                pts = [(c[0] - 7, c[1]), (c[0] - 2, c[1] + 6), (c[0] + 8, c[1] - 6)]
                pygame.draw.lines(image, INK, False, pts, 6)
                pygame.draw.lines(image, (150, 230, 150), False, pts, 4)
            return image

        mark_color = _mix(face, INK, 0.75)
        if self.face == "medallion":
            pygame.draw.circle(image, light, outer.center, size // 3 + 2)
            pygame.draw.circle(image, mark_color, outer.center, size // 3 + 2, width=2)
            for dx, dy in ((-11, -11), (11, -11)):
                self._star(image, (outer.centerx + dx, outer.centery + dy), 3, (255, 255, 255))
        # "kanji" blocks show 問 (mon, "question") instead of "?" -- same
        # job, a little Japanese on the block itself.
        glyph = "問" if self.face == "kanji" else "?"
        font = pixel_font(32)
        text = font.render(glyph, True, (255, 255, 255) if self.face == "kanji" else mark_color)
        if self.face == "kanji":
            text = pygame.transform.smoothscale(text, (round(text.get_width() * 0.8), round(text.get_height() * 0.8)))
        edge = font.render(glyph, True, INK if self.face == "kanji" else dark)
        if self.face == "kanji":
            edge = pygame.transform.smoothscale(edge, text.get_size())
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                image.blit(edge, text.get_rect(center=(outer.centerx + dx, outer.centery + dy)))
        else:
            image.blit(edge, edge.get_rect(center=(outer.centerx + 2, outer.centery + 2)))
        image.blit(text, text.get_rect(center=outer.center))
        return image

    @staticmethod
    def _star(surface, center, r, color):
        x, y = center
        pygame.draw.polygon(surface, color, [(x, y - r - 1), (x + 1, y - 1), (x + r + 1, y), (x + 1, y + 1),
                                             (x, y + r + 1), (x - 1, y + 1), (x - r - 1, y), (x - 1, y - 1)])

    def animate(self, t):
        """A diagonal shine sweeps across an unanswered block every few
        seconds. Call once per frame with the game clock."""
        if self.used:
            return
        cycle = (t / GLINT_PERIOD + self.phase) % 1.0
        sweep = cycle * GLINT_PERIOD / GLINT_TIME
        self.image = self._active_frame.copy()
        if sweep < 1.0:
            size = self.rect.width
            x = -size + sweep * size * 2.2
            shine = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.polygon(shine, (255, 255, 255, 120), [(x, size), (x + 8, size), (x + 8 + size, 0), (x + size, 0)])
            mask = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect().inflate(-6, -6), border_radius=4)
            shine.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self.image.blit(shine, (0, 0))

    def mark_used(self):
        self.used = True
        self.image = self._used_frame.copy()

    def mark_answered(self, correct):
        """Shows how the question went: a green check, or a red cross."""
        self.used = True
        self.answered_wrong = not correct
        self.image = (self._used_frame if correct else self._wrong_frame).copy()

    def reopen(self):
        """Back to a fresh "?" box -- after the player skipped its question,
        so they can come back and answer it later."""
        self.used = False
        self.image = self._active_frame.copy()

    def glow_strength(self, t):
        """0..1 pulse for the halo Game draws behind an unanswered block."""
        return 0.55 + 0.45 * math.sin(t * 3.0 + self.phase * 6.28)

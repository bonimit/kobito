import pygame

from kobito.entities.platform import Platform
from kobito.fonts import get_font

ACTIVE_COLOR = (255, 193, 7)
USED_COLOR = (120, 108, 90)
MARK_COLOR = (90, 60, 0)


class QuestionBlock(Platform):
    """A solid block that triggers a Japanese question the first time
    the player touches it.

    Subclassing Platform means it's automatically solid -- the player
    collides with it exactly like any other tile, with zero extra
    physics code. `used` just tracks whether this particular block has
    already been answered, so it doesn't fire again.
    """

    def __init__(self, x, y, size):
        super().__init__(x, y, size, size, color=ACTIVE_COLOR)
        self.used = False
        self._draw_question_mark()

    def _draw_question_mark(self):
        font = get_font(int(self.rect.height * 0.7))
        text = font.render("?", True, MARK_COLOR)
        self.image.blit(text, text.get_rect(center=(self.rect.width // 2, self.rect.height // 2)))

    def mark_used(self):
        self.used = True
        self.image.fill(USED_COLOR)

import pygame

from kobito.entities.platform import Platform
from kobito.fonts import get_font

ACTIVE_COLOR = (255, 193, 7)
USED_COLOR = (120, 108, 90)
MARK_COLOR = (90, 60, 0)


SIZE_RATIO = 1.15  # fraction of a full tile cell the block occupies -- a bit bigger than the grid cell


class QuestionBlock(Platform):
    """A solid block that triggers a Japanese question the first time
    the player touches it.

    Subclassing Platform means it's automatically solid -- the player
    collides with it exactly like any other tile, with zero extra
    physics code. `used` just tracks whether this particular block has
    already been answered, so it doesn't fire again.

    Drawn slightly larger than a full tile cell (see SIZE_RATIO) and
    centered on it, rather than filling the cell exactly like a
    platform tile -- reads as a distinct, chunky "hit this" object,
    Mario block-style, and its hitbox grows to match.
    """

    def __init__(self, cell_x, cell_y, cell_size):
        block_size = round(cell_size * SIZE_RATIO)
        offset = (cell_size - block_size) // 2
        super().__init__(cell_x + offset, cell_y + offset, block_size, block_size, color=ACTIVE_COLOR)
        self.used = False
        self._draw_question_mark()

    def _draw_question_mark(self):
        font = get_font(int(self.rect.height * 0.7))
        text = font.render("?", True, MARK_COLOR)
        self.image.blit(text, text.get_rect(center=(self.rect.width // 2, self.rect.height // 2)))

    def mark_used(self):
        self.used = True
        self.image.fill(USED_COLOR)

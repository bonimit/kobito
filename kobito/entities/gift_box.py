import pygame

from kobito.entities.platform import Platform

RED = (214, 52, 70)
RED_DARK = (140, 28, 44)
RIBBON = (255, 214, 80)
RIBBON_DARK = (200, 150, 30)
USED = (120, 108, 100)
USED_DARK = (84, 74, 70)

SIZE_RATIO = 1.15  # same chunky size as a question block


class GiftBox(Platform):
    """A solid present-box. Unlike a QuestionBlock it never asks a
    question: bumping it pops open a random reward (coins, a konbini
    snack, an extra life, now and then something rare -- see
    kobito/items.py roll_gift). Wrapped in red with a gold ribbon so it
    can't be mistaken for a yellow "?" quiz block.
    """

    def __init__(self, cell_x, cell_y, cell_size):
        size = round(cell_size * SIZE_RATIO)
        offset = (cell_size - size) // 2
        super().__init__(cell_x + offset, cell_y + offset, size, size, color=RED)
        self.used = False
        self._draw(opened=False)

    def _draw(self, opened):
        w, h = self.rect.size
        body, dark, ribbon, ribbon_dark = (USED, USED_DARK, USED_DARK, USED_DARK) if opened else (RED, RED_DARK, RIBBON, RIBBON_DARK)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (30, 18, 24), (0, 0, w, h), border_radius=5)       # dark outline
        pygame.draw.rect(self.image, dark, (2, 2, w - 4, h - 4), border_radius=4)
        pygame.draw.rect(self.image, body, (2, 2, w - 6, h - 7), border_radius=4)
        if not opened:
            pygame.draw.line(self.image, (255, 150, 160), (5, 4), (w // 2 - 6, 4), 2)    # shine
        pygame.draw.rect(self.image, ribbon, (w // 2 - 3, 0, 6, h))
        pygame.draw.rect(self.image, ribbon, (0, h // 2 - 3, w, 6))
        pygame.draw.rect(self.image, ribbon_dark, (w // 2 - 3, 0, 6, h), width=1)
        pygame.draw.rect(self.image, ribbon_dark, (0, h // 2 - 3, w, 6), width=1)
        if not opened:  # a little bow on top
            for dx in (-6, 6):
                pygame.draw.ellipse(self.image, ribbon, (w // 2 + dx - 4, 2, 8, 6))
                pygame.draw.ellipse(self.image, ribbon_dark, (w // 2 + dx - 4, 2, 8, 6), width=1)

    def mark_used(self):
        self.used = True
        self._draw(opened=True)

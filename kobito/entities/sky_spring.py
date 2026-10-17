"""A secret way up: a little cloud tuft sitting on the ground, with a
coiled spring hidden underneath.

It looks like scenery, but land on it and it launches you straight up off
the top of the screen into a hidden sky stage (kobito/levels/sky.py).
Not solid -- Game checks for the player landing on it each frame.
"""

import pygame

WIDTH, HEIGHT = 56, 26
COLORS = {
    "thunder": ((176, 182, 204), (126, 130, 156)),
    "rainbow": ((252, 252, 255), (226, 214, 240)),
    "moon": ((210, 202, 244), (156, 144, 206)),
}


class SkySpring(pygame.sprite.Sprite):
    def __init__(self, x, ground_y, style, link):
        super().__init__()
        self.style = style
        self.link = link            # {"index", "style", "x", "return_x"}
        self.squash = 0.0           # seconds of "boing" left after a bounce
        self._frames = {False: self._render(False), True: self._render(True)}
        self.image = self._frames[False]
        self.rect = self.image.get_rect(midbottom=(x, ground_y))

    def _render(self, squashed):
        image = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        puff, shade = COLORS[self.style]
        top = 10 if squashed else 2
        # The spring peeking out under the cloud.
        for i, y in enumerate(range(HEIGHT - 3, top + 8, -4)):
            pygame.draw.line(image, (120, 120, 132), (WIDTH // 2 - 9, y), (WIDTH // 2 + 9, y - 2), 2)
        pygame.draw.ellipse(image, shade, (4, top + 6, WIDTH - 8, HEIGHT - top - 8))
        for cx, r in ((15, 10), (28, 12), (41, 10)):
            pygame.draw.circle(image, puff, (cx, top + 10), r)
        pygame.draw.circle(image, (255, 255, 255), (24, top + 6), 3)
        return image

    def boing(self):
        self.squash = 0.18

    def update_squash(self, dt):
        self.squash = max(0.0, self.squash - dt)
        self.image = self._frames[self.squash > 0]

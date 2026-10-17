"""A sunball -- what the player throws with sun power (from eating a
sunflower), like Mario's fireball.

It flies forward, bounces along floors and platform tops, and defeats the
first enemy it touches. It fizzles when it hits a wall or after a short
while. Game keeps at most MAX_SHOTS on screen.
"""

import math

import pygame

SPEED_X = 430.0
BOUNCE_SPEED = 300.0
GRAVITY = 1500.0
LIFETIME = 1.6
MAX_SHOTS = 2
SIZE = 16
INK = (60, 30, 10)


def _render(spin):
    s = pygame.Surface((SIZE + 8, SIZE + 8), pygame.SRCALPHA)
    c = (SIZE + 8) // 2
    for i in range(8):                                    # rays, turning as it flies
        a = spin + i * math.pi / 4
        pygame.draw.line(s, (255, 160, 40), (c + math.cos(a) * 6, c + math.sin(a) * 6),
                         (c + math.cos(a) * 11, c + math.sin(a) * 11), 3)
    pygame.draw.circle(s, INK, (c, c), SIZE // 2)
    pygame.draw.circle(s, (255, 196, 40), (c, c), SIZE // 2 - 2)
    pygame.draw.circle(s, (255, 244, 170), (c - 2, c - 2), 3)
    return s


FRAMES = None


class SunShot(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        global FRAMES
        if FRAMES is None:
            FRAMES = [_render(i * math.pi / 16) for i in range(4)]
        self.rect = pygame.Rect(0, 0, SIZE, SIZE)
        self.rect.center = (round(x), round(y))
        self.vx = SPEED_X * direction
        self.vy = 60.0
        self.age = 0.0
        self.image = FRAMES[0]

    def draw_rect(self):
        return self.image.get_rect(center=self.rect.center)

    def update(self, dt, platforms):
        self.age += dt
        if self.age >= LIFETIME:
            self.kill()
            return
        self.image = FRAMES[int(self.age * 20) % len(FRAMES)]
        self.rect.x += round(self.vx * dt)
        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if not getattr(platform, "one_way", False):
                self.kill()          # hit a wall: fizzle
                return
        self.vy += GRAVITY * dt
        previous_bottom = self.rect.bottom
        self.rect.y += round(self.vy * dt)
        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if self.vy > 0 and previous_bottom <= platform.rect.top + 6:
                self.rect.bottom = platform.rect.top
                self.vy = -BOUNCE_SPEED     # bounce along the ground
            elif not getattr(platform, "one_way", False):
                self.kill()
                return

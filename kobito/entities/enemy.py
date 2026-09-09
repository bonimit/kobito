import pygame

from kobito.constants import GRAVITY, MAX_FALL_SPEED, TILE_SIZE

BODY_COLOR = (150, 60, 50)
FOOT_COLOR = (90, 40, 35)
EYE_COLOR = (255, 255, 255)
PUPIL_COLOR = (20, 20, 20)


class Enemy(pygame.sprite.Sprite):
    """A simple Goomba-style patrol enemy.

    Physics-wise this is a stripped-down Player: it falls under gravity
    and stands on platforms the same way, but instead of reading input
    it just walks back and forth, turning around at its patrol bounds
    or whenever it bumps into something solid.
    """

    def __init__(self, x, y, patrol_min_x, patrol_max_x, speed=70.0):
        super().__init__()

        width, height = TILE_SIZE - 6, TILE_SIZE - 6
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self._draw_body()
        self.rect = self.image.get_rect(topleft=(x, y))

        self.patrol_min_x = patrol_min_x
        self.patrol_max_x = patrol_max_x
        self.velocity_x = speed
        self.velocity_y = 0.0

    def _draw_body(self):
        w, h = self.image.get_size()
        pygame.draw.ellipse(self.image, BODY_COLOR, (0, 0, w, h))

        foot_w = w // 3
        pygame.draw.ellipse(self.image, FOOT_COLOR, (2, h - 6, foot_w, 6))
        pygame.draw.ellipse(self.image, FOOT_COLOR, (w - foot_w - 2, h - 6, foot_w, 6))

        eye_y = h // 3
        for eye_x in (w // 3, w - w // 3):
            pygame.draw.circle(self.image, EYE_COLOR, (eye_x, eye_y), 4)
            pygame.draw.circle(self.image, PUPIL_COLOR, (eye_x, eye_y), 2)

    def update(self, dt, platforms):
        self.velocity_y = min(self.velocity_y + GRAVITY * dt, MAX_FALL_SPEED)

        self._move_and_collide_x(dt, platforms)
        self._move_and_collide_y(dt, platforms)
        self._enforce_patrol_bounds()

    def _move_and_collide_x(self, dt, platforms):
        self.rect.x += round(self.velocity_x * dt)
        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if self.velocity_x > 0:
                self.rect.right = platform.rect.left
            elif self.velocity_x < 0:
                self.rect.left = platform.rect.right
            self.velocity_x *= -1

    def _move_and_collide_y(self, dt, platforms):
        self.rect.y += round(self.velocity_y * dt)
        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if self.velocity_y > 0:
                self.rect.bottom = platform.rect.top
            elif self.velocity_y < 0:
                self.rect.top = platform.rect.bottom
            self.velocity_y = 0

    def _enforce_patrol_bounds(self):
        if self.rect.left <= self.patrol_min_x:
            self.rect.left = self.patrol_min_x
            self.velocity_x = abs(self.velocity_x)
        elif self.rect.right >= self.patrol_max_x:
            self.rect.right = self.patrol_max_x
            self.velocity_x = -abs(self.velocity_x)

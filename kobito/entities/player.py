import pygame

from kobito.constants import (
    GRAVITY,
    JUMP_SPEED,
    MAX_FALL_SPEED,
    PLAYER_PLACEHOLDER,
    RUN_SPEED,
    TILE_SIZE,
)


class Player(pygame.sprite.Sprite):
    """The mascot character.

    Phase 1 uses a flat-color rectangle as a stand-in for real sprite
    sheets, which get added in Phase 2. Everything about the movement
    and collision logic below stays the same once real art is swapped in.
    """

    def __init__(self, x, y):
        super().__init__()

        # Placeholder art: a rectangle a bit smaller than one tile, so
        # the player has visible clearance from tile edges.
        width, height = TILE_SIZE - 4, TILE_SIZE * 1.5
        self.image = pygame.Surface((width, height))
        self.image.fill(PLAYER_PLACEHOLDER)
        self.rect = self.image.get_rect(topleft=(x, y))

        # Velocity in pixels/second. x is set directly from input each
        # frame; y accumulates gravity and gets reset by jumps/landing.
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        # Whether the player is currently resting on top of a platform.
        # Needed so jumping is only allowed from the ground (no
        # double/air jumps), and to know when to stop applying gravity's
        # downward push.
        self.on_ground = False

    def handle_input(self):
        keys = pygame.key.get_pressed()

        self.velocity_x = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.velocity_x = -RUN_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity_x = RUN_SPEED

        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.velocity_y = -JUMP_SPEED
            self.on_ground = False

    def apply_gravity(self, dt):
        # Gravity is acceleration: it increases downward speed every
        # frame rather than being an instant snap, which is what makes
        # jump arcs feel natural instead of teleport-y.
        self.velocity_y += GRAVITY * dt
        if self.velocity_y > MAX_FALL_SPEED:
            self.velocity_y = MAX_FALL_SPEED

    def update(self, dt, platforms):
        self.handle_input()
        self.apply_gravity(dt)

        # Move and resolve collisions on one axis at a time. Doing X and
        # Y together makes it ambiguous which side of a block you hit;
        # separating them means "did I hit something moving sideways?"
        # and "did I hit something moving up/down?" are two simple,
        # independent questions.
        self._move_and_collide_x(dt, platforms)
        self._move_and_collide_y(dt, platforms)

    def _move_and_collide_x(self, dt, platforms):
        self.rect.x += round(self.velocity_x * dt)

        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if self.velocity_x > 0:
                # Moving right: our right edge is inside the platform,
                # so snap it back to the platform's left edge.
                self.rect.right = platform.rect.left
            elif self.velocity_x < 0:
                self.rect.left = platform.rect.right
            self.velocity_x = 0

    def _move_and_collide_y(self, dt, platforms):
        self.rect.y += round(self.velocity_y * dt)
        self.on_ground = False

        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if self.velocity_y > 0:
                # Falling: land on top of the platform.
                self.rect.bottom = platform.rect.top
                self.on_ground = True
            elif self.velocity_y < 0:
                # Jumping: bonked our head on a platform above us.
                self.rect.top = platform.rect.bottom
            self.velocity_y = 0

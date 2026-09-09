import pygame

from kobito.assets import load_character_animations
from kobito.constants import (
    GRAVITY,
    JUMP_SPEED,
    MAX_FALL_SPEED,
    RUN_SPEED,
    TILE_SIZE,
)


class Player(pygame.sprite.Sprite):
    """The mascot character: physics/collision plus animation state."""

    def __init__(self, x, y, character_id="capybara", color=(200, 200, 200)):
        super().__init__()

        self.animations = load_character_animations(character_id, color)
        self.state = "idle"
        self.facing_right = True
        self.image = self.animations[self.state].current_frame

        # The hitbox used for movement/collision is a fixed size,
        # independent of whatever the current animation frame's pixel
        # dimensions happen to be (a run frame might be a different
        # width than an idle frame). Keeping physics on a stable rect
        # avoids jittery collisions as frames change; `draw_rect()`
        # below positions the (possibly different-sized) visual frame
        # relative to this hitbox purely for drawing.
        self.rect = pygame.Rect(0, 0, TILE_SIZE - 4, round(TILE_SIZE * 1.5))
        self.rect.topleft = (x, y)

        self.velocity_x = 0.0
        self.velocity_y = 0.0
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
        self.velocity_y += GRAVITY * dt
        if self.velocity_y > MAX_FALL_SPEED:
            self.velocity_y = MAX_FALL_SPEED

    def update(self, dt, platforms):
        self.handle_input()
        self.apply_gravity(dt)
        self._move_and_collide_x(dt, platforms)
        self._move_and_collide_y(dt, platforms)
        self._update_animation(dt)

    def _move_and_collide_x(self, dt, platforms):
        self.rect.x += round(self.velocity_x * dt)

        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if self.velocity_x > 0:
                self.rect.right = platform.rect.left
            elif self.velocity_x < 0:
                self.rect.left = platform.rect.right
            self.velocity_x = 0

    def _move_and_collide_y(self, dt, platforms):
        self.rect.y += round(self.velocity_y * dt)
        self.on_ground = False

        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if self.velocity_y > 0:
                self.rect.bottom = platform.rect.top
                self.on_ground = True
            elif self.velocity_y < 0:
                self.rect.top = platform.rect.bottom
            self.velocity_y = 0

    def _update_animation(self, dt):
        if not self.on_ground:
            new_state = "jump"
        elif self.velocity_x != 0:
            new_state = "run"
        else:
            new_state = "idle"

        if new_state != self.state:
            self.state = new_state
            self.animations[self.state].reset()

        if self.velocity_x > 0:
            self.facing_right = True
        elif self.velocity_x < 0:
            self.facing_right = False

        animation = self.animations[self.state]
        animation.update(dt)
        frame = animation.current_frame
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def draw_rect(self):
        """Where to blit `self.image`, in world space.

        Frames can vary in size between animations/states, so this
        anchors the *bottom-center* of whatever frame is current to the
        bottom-center of the fixed hitbox — feet stay planted on the
        ground regardless of frame size.
        """
        return self.image.get_rect(midbottom=self.rect.midbottom)

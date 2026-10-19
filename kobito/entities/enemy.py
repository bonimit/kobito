import pygame

from kobito import enemy_art
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

    def __init__(self, x, y, patrol_min_x, patrol_max_x, speed=70.0, body_color=None, foot_color=None,
                 species=None):
        super().__init__()

        self.body_color = body_color or BODY_COLOR
        self.foot_color = foot_color or FOOT_COLOR
        # The look (kobito/enemy_art.py): a named species (slime, oni, crab,
        # squid, bull, ... -- each world has its own, see WORLD_ENEMIES), or -- when only colours are given, as in the hidden rooms --
        # a round "critter" in those colours. The hitbox stays one size.
        self.species = species or ("critter" if body_color else "slime")
        colors = {"body": body_color, "foot": foot_color} if body_color else {}
        self._frames = enemy_art.frames_for(enemy_art.render_ground, self.species, colors)
        self._anim = (x % 7) * 0.1

        width, height = TILE_SIZE - 6, TILE_SIZE - 6
        self.rect = pygame.Rect(x, y, width, height)
        self.image = self._frames[0][0]

        self.patrol_min_x = patrol_min_x
        self.patrol_max_x = patrol_max_x
        self.velocity_x = speed
        self.velocity_y = 0.0

    def draw_rect(self):
        """The (bigger) artwork stands on the hitbox's feet."""
        return self.image.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + 3))

    def _animate(self, dt):
        self._anim += dt
        right, left = self._frames[enemy_art.flap(self._anim, 5.0)]
        self.image = right if self.velocity_x >= 0 else left

    def update(self, dt, platforms):
        self.velocity_y = min(self.velocity_y + GRAVITY * dt, MAX_FALL_SPEED)

        self._move_and_collide_x(dt, platforms)
        self._move_and_collide_y(dt, platforms)
        self._enforce_patrol_bounds()
        self._animate(dt)

    def _move_and_collide_x(self, dt, platforms):
        self.rect.x += round(self.velocity_x * dt)
        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if getattr(platform, "one_way", False):
                continue
            if self.velocity_x > 0:
                self.rect.right = platform.rect.left
            elif self.velocity_x < 0:
                self.rect.left = platform.rect.right
            self.velocity_x *= -1

    def _move_and_collide_y(self, dt, platforms):
        previous_bottom = self.rect.bottom
        self.rect.y += round(self.velocity_y * dt)
        for platform in pygame.sprite.spritecollide(self, platforms, dokill=False):
            if getattr(platform, "one_way", False) and (self.velocity_y <= 0 or previous_bottom > platform.rect.top):
                continue
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


# Wingbeats per second: buzzing bees, flapping birds, slow-bobbing ghosts.
FLAP_SPEEDS = {"bat": 7.0, "bee": 14.0, "crow": 6.0, "seagull": 5.0, "flying_fish": 6.0, "jellyfish": 2.5,
               "pufferfish": 2.0}


class FlyingEnemy(pygame.sprite.Sprite):
    """A bat-like hazard that patrols up and down through the air rather
    than walking the ground -- ignores gravity entirely, so it threatens
    the jump arcs and platform tops that a ground Enemy never reaches,
    forcing the player to time a jump rather than just walk around it.
    """

    def __init__(self, x, y, patrol_min_y, patrol_max_y, speed=55.0, body_color=None, wing_color=None,
                 species=None):
        super().__init__()

        self.body_color = body_color or (70, 55, 90)
        self.wing_color = wing_color or (100, 80, 120)
        # bat, crow, seagull, bee, flying fish, lantern / umbrella ghost, ...;
        # a bat in the given colours when only colours are given (hidden rooms).
        self.species = species or "bat"
        colors = {"body": body_color, "wing": wing_color} if body_color else {}
        self._frames = enemy_art.frames_for(enemy_art.render_flying, self.species, colors)
        self._anim = (y % 5) * 0.1

        width, height = TILE_SIZE - 8, TILE_SIZE - 10
        self.rect = pygame.Rect(x, y, width, height)
        self.image = self._frames[0][0]
        self.facing_left = (x // TILE_SIZE) % 2 == 1

        self.patrol_min_y = patrol_min_y
        self.patrol_max_y = patrol_max_y
        self.velocity_y = speed

    def draw_rect(self):
        return self.image.get_rect(center=self.rect.center)

    def update(self, dt, platforms):
        self._anim += dt
        right, left = self._frames[enemy_art.flap(self._anim, FLAP_SPEEDS.get(self.species, 3.0))]
        self.image = left if self.facing_left else right
        self.rect.y += round(self.velocity_y * dt)
        if self.rect.top <= self.patrol_min_y:
            self.rect.top = self.patrol_min_y
            self.velocity_y = abs(self.velocity_y)
        elif self.rect.bottom >= self.patrol_max_y:
            self.rect.bottom = self.patrol_max_y
            self.velocity_y = -abs(self.velocity_y)

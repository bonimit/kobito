import pygame

from kobito import input as game_input
from kobito.assets import load_character_animations
from kobito.constants import (
    GRAVITY,
    JUMP_SPEED,
    MAX_FALL_SPEED,
    RUN_SPEED,
    TILE_SIZE,
)

# Moves (all tunable here):
RUN_BOOST = 1.6            # hold run: this much faster (jumps carry further too)
FLAPS_PER_JUMP = 2         # press jump again in mid-air to flap up, this many times
FLAP_SPEED = 430.0
GLIDE_FALL_SPEED = 130.0   # hold jump while falling to glide down slowly
CLIMB_SPEED = 150.0        # hold toward a wall in mid-air to climb it...
CLIMB_SECONDS = 1.2        # ...for this long per wall, then you slide
WALL_SLIDE_SPEED = 90.0
WALL_JUMP_PUSH = 1.3       # jump off a wall: kick away at this x RUN_SPEED
WALL_KICK_SECONDS = 0.18   # steering is ignored briefly so the kick carries
RUN_KEYS = (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_x, pygame.K_j)
FIRE_ONLY_KEYS = (pygame.K_f,)   # throw without running


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

        # Moves: run, flap/glide ("fly"), wall climb / wall jump. Game reads
        # fire_requested (a fresh press of the run button) to throw sunballs.
        self.running = False
        self.flaps_left = FLAPS_PER_JUMP
        self.gliding = False
        self.climbing = False
        self.wall_sliding = False
        self.climb_time = 0.0
        self.wall_dir = 0          # -1 / +1: pushing into a wall on that side this frame
        self.wall_kick = 0.0
        self.fire_requested = False
        self._jump_was_held = False
        self._run_was_held = False
        self._fire_sources = set()

        # Game sets these every frame: below 1.0 when the player is
        # drowsy (low power), above 1.0 during a golden-can speed boost.
        self.run_scale = 1.0
        self.jump_scale = 1.0

        # Every solid the player overlapped *during* collision
        # resolution this frame (before rects get snapped apart so they
        # no longer overlap). Game reads this after update() to detect
        # things like "did I just bump a question block" -- checking
        # for overlap *after* resolution wouldn't work, since by then
        # the rects are touching but not overlapping.
        self.touched = set()

    def handle_input(self, dt=1 / 60):
        keys = pygame.key.get_pressed()

        # Left/right from keyboard, gamepad and (web) touch -- whichever the
        # player is actually using just works.
        direction = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction = 1
        for axis in (game_input.move_axis(), game_input.touch_move_axis()):
            if axis < 0:
                direction = -1
            elif axis > 0:
                direction = 1

        jump_held = (
            keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
            or game_input.jump_held() or game_input.touch_jump_held()
        )
        run_held = any(keys[k] for k in RUN_KEYS) or game_input.run_held() or game_input.touch_run_held()
        jump_pressed = jump_held and not self._jump_was_held
        # Throwing fires on a fresh press of ANY run/throw input -- so you can
        # hold Shift to run and still tap X (or F) to throw.
        sources = {k for k in RUN_KEYS + FIRE_ONLY_KEYS if keys[k]} | game_input.run_buttons_down()
        if game_input.touch_run_held():
            sources.add("touch")
        self.fire_requested = bool(sources - self._fire_sources)
        self._fire_sources = sources
        self._jump_was_held, self._run_was_held = jump_held, run_held
        self.running = run_held

        if self.on_ground:
            self.flaps_left = FLAPS_PER_JUMP
            self.climb_time = 0.0

        # Horizontal: walk / run (a wall kick briefly overrides steering).
        if self.wall_kick > 0:
            self.wall_kick = max(0.0, self.wall_kick - dt)
        else:
            speed = RUN_SPEED * self.run_scale * (RUN_BOOST if run_held else 1.0)
            self.velocity_x = direction * speed

        # Wall climb: in the air, pushing into a wall -> climb it (for a
        # while), then slide. Jump while on the wall -> kick off it.
        on_wall = not self.on_ground and self.wall_dir != 0 and direction == self.wall_dir
        self.climbing = False
        self.wall_sliding = False
        if on_wall and jump_pressed:
            self.velocity_y = -JUMP_SPEED * self.jump_scale
            self.velocity_x = -self.wall_dir * RUN_SPEED * WALL_JUMP_PUSH
            self.wall_kick = WALL_KICK_SECONDS
            self.climb_time = 0.0
            self.flaps_left = FLAPS_PER_JUMP
            return
        if on_wall:
            if self.climb_time < CLIMB_SECONDS:
                self.climbing = True
                self.climb_time += dt
                self.velocity_y = -CLIMB_SPEED
            else:
                self.wall_sliding = True

        # Jumping, flapping and gliding ("fly").
        if jump_held and self.on_ground:
            self.velocity_y = -JUMP_SPEED * self.jump_scale
            self.on_ground = False
        elif jump_pressed and not self.on_ground and not on_wall and self.flaps_left > 0:
            self.flaps_left -= 1
            self.velocity_y = min(self.velocity_y, -FLAP_SPEED * self.jump_scale)
        self.gliding = jump_held and not self.on_ground and not self.climbing and self.velocity_y > 0

    def apply_gravity(self, dt):
        if self.climbing:
            return  # climbing holds its own steady speed up the wall
        self.velocity_y += GRAVITY * dt
        if self.gliding:
            self.velocity_y = min(self.velocity_y, GLIDE_FALL_SPEED)
        if self.wall_sliding:
            self.velocity_y = min(self.velocity_y, WALL_SLIDE_SPEED)
        if self.velocity_y > MAX_FALL_SPEED:
            self.velocity_y = MAX_FALL_SPEED

    def update(self, dt, platforms):
        self.touched = set()
        self.handle_input(dt)
        self.apply_gravity(dt)
        self._move_and_collide_x(dt, platforms)
        self._move_and_collide_y(dt, platforms)
        self._update_animation(dt)

    def _move_and_collide_x(self, dt, platforms):
        self.rect.x += round(self.velocity_x * dt)
        self.wall_dir = 0

        colliding = pygame.sprite.spritecollide(self, platforms, dokill=False)
        self.touched.update(colliding)
        for platform in colliding:
            if getattr(platform, "one_way", False):
                continue  # clouds never block sideways
            if self.velocity_x > 0:
                self.rect.right = platform.rect.left
                self.wall_dir = 1
            elif self.velocity_x < 0:
                self.rect.left = platform.rect.right
                self.wall_dir = -1
            self.velocity_x = 0

    def _move_and_collide_y(self, dt, platforms):
        previous_bottom = self.rect.bottom
        self.rect.y += round(self.velocity_y * dt)
        self.on_ground = False

        colliding = pygame.sprite.spritecollide(self, platforms, dokill=False)
        self.touched.update(colliding)
        for platform in colliding:
            # A one-way cloud only catches a player coming down onto it from
            # above -- jumping up from underneath passes straight through.
            if getattr(platform, "one_way", False) and (
                self.velocity_y <= 0 or previous_bottom > platform.rect.top
            ):
                continue
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

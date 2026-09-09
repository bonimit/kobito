import pygame

from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, SKY_BLUE
from kobito.entities.player import Player
from kobito.levels.level1 import build_level1


class Game:
    """Owns the window, the main loop, and the current level's state.

    The "game loop" is the heartbeat of any real-time game: over and
    over, as fast as the frame rate allows, it (1) reads input/events,
    (2) advances the simulation by one time step, and (3) draws the
    result. Nothing moves or gets checked outside of this loop.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito")
        self.clock = pygame.time.Clock()
        self.running = True

        self.platforms, player_start = build_level1()
        self.player = Player(*player_start)

        # A "sprite group" is pygame's container for a batch of sprites.
        # It gives us group.draw(screen) and group.update(...) instead of
        # hand-rolled loops, and spritecollide() below checks one sprite
        # against every sprite in a group in one call.
        self.all_sprites = pygame.sprite.Group(self.player, *self.platforms)

        # How far the world has scrolled left, in pixels, so the camera
        # can follow the player through a level wider than the screen.
        self.camera_x = 0.0

    def run(self):
        while self.running:
            # dt = seconds since last frame. Using it to scale movement
            # (instead of moving a fixed number of pixels/frame) keeps
            # speeds consistent even if the frame rate dips.
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()

        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

    def _update(self, dt):
        self.player.update(dt, self.platforms)

        # Keep the player roughly centered horizontally by shifting the
        # camera, but never scroll past the left edge of the level.
        target_camera_x = self.player.rect.centerx - SCREEN_WIDTH / 2
        self.camera_x = max(0.0, target_camera_x)

    def _draw(self):
        self.screen.fill(SKY_BLUE)

        for sprite in self.all_sprites:
            draw_pos = (sprite.rect.x - self.camera_x, sprite.rect.y)
            self.screen.blit(sprite.image, draw_pos)

        pygame.display.flip()

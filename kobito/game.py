import pygame

from kobito.characters import get_character
from kobito.constants import (
    CORRECT_ANSWER_SCORE,
    FPS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SKY_BLUE,
    STARTING_LIVES,
)
from kobito.entities.player import Player
from kobito.entities.question_block import QuestionBlock
from kobito.fonts import get_font
from kobito.levels.level1 import build_level1
from kobito.questions import QuestionBank
from kobito.quiz_screen import QuizScreen

HUD_TEXT_COLOR = (30, 30, 30)
GAME_OVER_OVERLAY = (0, 0, 0, 160)


class Game:
    """Owns the window, the main loop, and the current level's state.

    The "game loop" is the heartbeat of any real-time game: over and
    over, as fast as the frame rate allows, it (1) reads input/events,
    (2) advances the simulation by one time step, and (3) draws the
    result. Nothing moves or gets checked outside of this loop.
    """

    def __init__(self, character_id="capybara"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False

        self.platforms, self.question_blocks, player_start = build_level1()
        character = get_character(character_id)
        self.player = Player(*player_start, character_id=character["id"], color=character["color"])

        # A "sprite group" is pygame's container for a batch of sprites.
        # It gives us group.draw(screen) and group.update(...) instead of
        # hand-rolled loops, and spritecollide() below checks one sprite
        # against every sprite in a group in one call.
        self.all_sprites = pygame.sprite.Group(self.player, *self.platforms)

        # How far the world has scrolled left, in pixels, so the camera
        # can follow the player through a level wider than the screen.
        self.camera_x = 0.0

        self.question_bank = QuestionBank()
        self.score = 0
        self.lives = STARTING_LIVES
        self.hud_font = get_font(22)
        self.game_over_font = get_font(36)

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
        if self.game_over:
            return

        self.player.update(dt, self.platforms)

        # Keep the player roughly centered horizontally by shifting the
        # camera, but never scroll past the left edge of the level.
        target_camera_x = self.player.rect.centerx - SCREEN_WIDTH / 2
        self.camera_x = max(0.0, target_camera_x)

        self._check_question_blocks()

    def _check_question_blocks(self):
        # player.touched is whatever solids collision resolution found
        # this frame (see Player.update) -- filter down to the one kind
        # we care about here, and only the ones not already answered.
        for solid in self.player.touched:
            if isinstance(solid, QuestionBlock) and not solid.used:
                self._trigger_question(solid)
                break  # handle at most one block per frame

    def _trigger_question(self, block):
        block.mark_used()
        question = self.question_bank.random_question()
        correct = QuizScreen(self.screen, question).run()

        if correct:
            self.score += CORRECT_ANSWER_SCORE
        else:
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True

        # QuizScreen ran its own loop with its own clock, so the main
        # loop's clock has an artificially large elapsed time queued up
        # for its next tick. Draining it here stops that showing up as
        # one huge dt (e.g. a sudden gravity jump) on the next frame.
        self.clock.tick(FPS)

    def _draw(self):
        self.screen.fill(SKY_BLUE)

        for sprite in self.all_sprites:
            # Most sprites (platforms) are drawn at their own rect.
            # The player overrides this with draw_rect() because its
            # visual frame size can differ from its fixed collision
            # hitbox (see Player.draw_rect).
            rect = sprite.draw_rect() if hasattr(sprite, "draw_rect") else sprite.rect
            draw_pos = (rect.x - self.camera_x, rect.y)
            self.screen.blit(sprite.image, draw_pos)

        self._draw_hud()
        if self.game_over:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_hud(self):
        score_label = self.hud_font.render(f"Score: {self.score}", True, HUD_TEXT_COLOR)
        lives_label = self.hud_font.render(f"Lives: {self.lives}", True, HUD_TEXT_COLOR)
        self.screen.blit(score_label, (12, 10))
        self.screen.blit(lives_label, (12, 36))

    def _draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(GAME_OVER_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        text = self.game_over_font.render(f"Game Over - Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

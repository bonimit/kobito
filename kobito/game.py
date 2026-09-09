import pygame

from kobito.background import Background
from kobito.characters import get_character
from kobito.constants import (
    CORRECT_ANSWER_SCORE,
    FPS,
    GAUGE_DAMAGE,
    GAUGE_MAX,
    INVULNERABILITY_SECONDS,
    KNOCKBACK_SPEED_X,
    KNOCKBACK_SPEED_Y,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STARTING_LIVES,
)
from kobito.difficulty import JLPT_DESCRIPTIONS, next_jlpt_level
from kobito.entities.player import Player
from kobito.entities.question_block import QuestionBlock
from kobito.fonts import get_font
from kobito.hint_service import HintService
from kobito.levels.level1 import build_level1
from kobito.questions import QuestionBank
from kobito.quiz_screen import QuizScreen

HUD_TEXT_COLOR = (255, 255, 255)
HUD_BACKING_COLOR = (20, 20, 25, 130)
HUD_BACKING_RECT = pygame.Rect(4, 4, 210, 100)
GAME_OVER_OVERLAY = (0, 0, 0, 160)
LEVEL_COMPLETE_OVERLAY = (0, 0, 0, 170)
BLINK_INTERVAL_SECONDS = 0.1
CONTINUE_KEYS = (pygame.K_RETURN, pygame.K_SPACE)

GAUGE_BAR_SIZE = (140, 14)
GAUGE_BAR_POS = (12, 62)
GAUGE_BAR_BG = (210, 205, 195)
GAUGE_BAR_FILL = (90, 190, 110)
GAUGE_BAR_BORDER = (60, 50, 40)

# Outcomes Game.run() can return, telling main.py what to do next.
OUTCOME_QUIT = "quit"
OUTCOME_ADVANCE = "advance"


class Game:
    """Owns the window, the main loop, and the current level's state.

    The "game loop" is the heartbeat of any real-time game: over and
    over, as fast as the frame rate allows, it (1) reads input/events,
    (2) advances the simulation by one time step, and (3) draws the
    result. Nothing moves or gets checked outside of this loop.

    One Game instance is one level. Reaching the goal flagpole ends it
    with outcome OUTCOME_ADVANCE, score, and an adaptively-computed
    JLPT level for the *next* level (based on this level's answer
    accuracy); main.py uses that to construct the next Game. Quitting
    (Esc/window close) or running out of lives instead ends with
    OUTCOME_QUIT.
    """

    def __init__(self, character_id="capybara", theme_id="forest", jlpt_level="N5", level_number=1, starting_score=0):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito")
        self.clock = pygame.time.Clock()
        self.running = True
        self.outcome = OUTCOME_QUIT
        self.game_over = False
        self.level_complete = False
        self.next_jlpt_level = None
        self.level_accuracy = None

        self.jlpt_level = jlpt_level
        self.level_number = level_number

        level = build_level1(theme_id)
        self.platforms = level.platforms
        self.question_blocks = level.question_blocks
        self.enemies = level.enemies
        self.collectibles = level.collectibles
        self.goal = level.goal
        self.background = Background(level.width_px, level.ground_y, level.ground_segments_px, level.theme)

        character = get_character(character_id)
        self.player = Player(*level.player_start, character_id=character["id"], color=character["color"])

        # A "sprite group" is pygame's container for a batch of sprites.
        # It gives us group.draw(screen) and group.update(...) instead of
        # hand-rolled loops, and spritecollide() below checks one sprite
        # against every sprite in a group in one call. The goal is drawn
        # like everything else here but deliberately isn't in
        # `platforms`, so it's visible without being solid.
        self.all_sprites = pygame.sprite.Group(
            self.player, *self.platforms, *self.enemies, *self.collectibles, self.goal
        )

        # How far the world has scrolled left, in pixels, so the camera
        # can follow the player through a level wider than the screen.
        self.camera_x = 0.0

        self.question_bank = QuestionBank()
        self.hint_service = HintService()
        self.score = starting_score
        self.correct_count = 0
        self.wrong_count = 0
        self.lives = STARTING_LIVES
        self.gauge = 0
        self.invulnerable_timer = 0.0
        self.hud_font = get_font(22)
        self.hud_font_small = get_font(16)
        self.game_over_font = get_font(36)
        self.level_complete_font = get_font(32)

    def run(self):
        while self.running:
            # dt = seconds since last frame. Using it to scale movement
            # (instead of moving a fixed number of pixels/frame) keeps
            # speeds consistent even if the frame rate dips.
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()

        # Only tear down pygame when the player is truly done (quit or
        # ran out of lives) -- advancing to the next level reuses the
        # same window, so main.py can build a fresh Game right after.
        if self.outcome != OUTCOME_ADVANCE:
            pygame.quit()

        return self.outcome, self.score, self.next_jlpt_level

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.level_complete and event.key in CONTINUE_KEYS:
                    self.outcome = OUTCOME_ADVANCE
                    self.running = False

    def _update(self, dt):
        if self.game_over or self.level_complete:
            return

        self.player.update(dt, self.platforms)
        self.enemies.update(dt, self.platforms)
        self.background.update(dt)

        # Keep the player roughly centered horizontally by shifting the
        # camera, but never scroll past the left edge of the level.
        target_camera_x = self.player.rect.centerx - SCREEN_WIDTH / 2
        self.camera_x = max(0.0, target_camera_x)

        self._check_question_blocks()
        self._check_collectibles()
        self._check_goal()

        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        else:
            self._check_enemy_contact()

    def _check_goal(self):
        if self.level_complete or not self.player.rect.colliderect(self.goal.rect):
            return

        self.level_complete = True
        self.next_jlpt_level, self.level_accuracy = next_jlpt_level(
            self.jlpt_level, self.correct_count, self.wrong_count
        )

    def _check_collectibles(self):
        # dokill=True removes each collected sprite from every group it
        # belongs to (collectibles *and* all_sprites), so there's no
        # separate cleanup needed once it's picked up.
        for item in pygame.sprite.spritecollide(self.player, self.collectibles, dokill=True):
            if item.kind == "shiitake":
                self.lives += 1
            else:
                self.score += item.value
                self._add_gauge(item.value)

    def _add_gauge(self, amount):
        self.gauge += amount
        while self.gauge >= GAUGE_MAX:
            self.gauge -= GAUGE_MAX
            self.lives += 1

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
        question = self.question_bank.random_question(jlpt=self.jlpt_level)

        # Snapshot the level as it looks right now (block already
        # marked used) so the quiz box shows over the actual scene
        # instead of a plain color, and anchor the box to the block's
        # current on-screen position so it appears right next to it.
        self._draw()
        background = self.screen.copy()
        anchor_rect = block.rect.move(-self.camera_x, 0)

        correct = QuizScreen(
            self.screen, question, background=background, anchor_rect=anchor_rect, hint_service=self.hint_service
        ).run()

        if correct:
            self.score += CORRECT_ANSWER_SCORE
            self.correct_count += 1
        else:
            self._take_damage()
            self.wrong_count += 1

        # QuizScreen ran its own loop with its own clock, so the main
        # loop's clock has an artificially large elapsed time queued up
        # for its next tick. Draining it here stops that showing up as
        # one huge dt (e.g. a sudden gravity jump) on the next frame.
        self.clock.tick(FPS)

    def _check_enemy_contact(self):
        hit_enemies = pygame.sprite.spritecollide(self.player, self.enemies, dokill=False)
        if not hit_enemies:
            return

        self._take_damage()
        self.invulnerable_timer = INVULNERABILITY_SECONDS

        # Knock the player up and away from whichever enemy they hit,
        # so they don't just immediately re-collide once invulnerability
        # ends, and so the hit reads clearly (same idea as classic
        # platformers bouncing you back on damage).
        enemy = hit_enemies[0]
        direction = -1 if self.player.rect.centerx < enemy.rect.centerx else 1
        self.player.velocity_x = direction * KNOCKBACK_SPEED_X
        self.player.velocity_y = KNOCKBACK_SPEED_Y

    def _take_damage(self):
        # A wrong quiz answer or an enemy hit costs a life outright,
        # *and* sets the gauge back -- mistakes also cost progress
        # toward the next bonus life, not just the life you just lost.
        self.lives -= 1
        self.gauge = max(0, self.gauge - GAUGE_DAMAGE)
        if self.lives <= 0:
            self.game_over = True

    def _draw(self):
        self.background.draw(self.screen, self.camera_x)

        for sprite in self.all_sprites:
            if sprite is self.player and self._player_should_blink_off():
                continue

            # Most sprites (platforms, enemies) are drawn at their own
            # rect. The player overrides this with draw_rect() because
            # its visual frame size can differ from its fixed collision
            # hitbox (see Player.draw_rect).
            rect = sprite.draw_rect() if hasattr(sprite, "draw_rect") else sprite.rect
            draw_pos = (rect.x - self.camera_x, rect.y)
            self.screen.blit(sprite.image, draw_pos)

        self._draw_hud()
        if self.game_over:
            self._draw_game_over()
        elif self.level_complete:
            self._draw_level_complete()

        pygame.display.flip()

    def _player_should_blink_off(self):
        # While invulnerable, skip drawing the player on alternating
        # short intervals -- a blinking sprite is the classic signal
        # that you're briefly safe after taking a hit.
        if self.invulnerable_timer <= 0:
            return False
        return int(self.invulnerable_timer / BLINK_INTERVAL_SECONDS) % 2 == 0

    def _draw_hud(self):
        # A semi-transparent dark backing keeps the HUD readable
        # regardless of how bright or dark the current world's sky is
        # (a plain dark text color would vanish against a night sky).
        backing = pygame.Surface(HUD_BACKING_RECT.size, pygame.SRCALPHA)
        backing.fill(HUD_BACKING_COLOR)
        self.screen.blit(backing, HUD_BACKING_RECT.topleft)

        level_label = self.hud_font.render(f"Level {self.level_number} - {self.jlpt_level}", True, HUD_TEXT_COLOR)
        score_label = self.hud_font.render(f"Score: {self.score}", True, HUD_TEXT_COLOR)
        lives_label = self.hud_font.render(f"Lives: {self.lives}", True, HUD_TEXT_COLOR)
        self.screen.blit(level_label, (12, 10))
        self.screen.blit(score_label, (12, 36))
        self.screen.blit(lives_label, (12, 62))
        self._draw_gauge_bar()

    def _draw_gauge_bar(self):
        width, height = GAUGE_BAR_SIZE
        bar_rect = pygame.Rect(GAUGE_BAR_POS[0], GAUGE_BAR_POS[1] + 26, *GAUGE_BAR_SIZE)
        pygame.draw.rect(self.screen, GAUGE_BAR_BG, bar_rect)

        fill_width = round(width * (self.gauge / GAUGE_MAX))
        if fill_width > 0:
            pygame.draw.rect(self.screen, GAUGE_BAR_FILL, (*bar_rect.topleft, fill_width, height))
        pygame.draw.rect(self.screen, GAUGE_BAR_BORDER, bar_rect, width=2)

        label = self.hud_font_small.render("Gauge", True, HUD_TEXT_COLOR)
        self.screen.blit(label, (bar_rect.right + 8, bar_rect.centery - label.get_height() // 2))

    def _draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(GAME_OVER_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        text = self.game_over_font.render(f"Game Over - Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    def _draw_level_complete(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(LEVEL_COMPLETE_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        center_x = SCREEN_WIDTH // 2
        lines = [
            (self.level_complete_font, f"Level {self.level_number} Complete!"),
            (self.hud_font, f"Score: {self.score}    Accuracy: {round(self.level_accuracy * 100)}%"),
            (self.hud_font, f"Next up: {self.next_jlpt_level} - {JLPT_DESCRIPTIONS[self.next_jlpt_level]}"),
            (self.hud_font_small, "Press Enter to continue"),
        ]
        y = SCREEN_HEIGHT // 2 - 70
        for font, text in lines:
            surface = font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, surface.get_rect(centerx=center_x, y=y))
            y += surface.get_height() + 12

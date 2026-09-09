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
from kobito.entities.player import Player
from kobito.entities.question_block import QuestionBlock
from kobito.fonts import get_font
from kobito.levels.level1 import build_level1
from kobito.questions import QuestionBank
from kobito.quiz_screen import QuizScreen

HUD_TEXT_COLOR = (255, 255, 255)
HUD_BACKING_COLOR = (20, 20, 25, 130)
HUD_BACKING_RECT = pygame.Rect(4, 4, 210, 82)
GAME_OVER_OVERLAY = (0, 0, 0, 160)
BLINK_INTERVAL_SECONDS = 0.1

GAUGE_BAR_SIZE = (140, 14)
GAUGE_BAR_POS = (12, 62)
GAUGE_BAR_BG = (210, 205, 195)
GAUGE_BAR_FILL = (90, 190, 110)
GAUGE_BAR_BORDER = (60, 50, 40)


class Game:
    """Owns the window, the main loop, and the current level's state.

    The "game loop" is the heartbeat of any real-time game: over and
    over, as fast as the frame rate allows, it (1) reads input/events,
    (2) advances the simulation by one time step, and (3) draws the
    result. Nothing moves or gets checked outside of this loop.
    """

    def __init__(self, character_id="capybara", theme_id="forest"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False

        level = build_level1(theme_id)
        self.platforms = level.platforms
        self.question_blocks = level.question_blocks
        self.enemies = level.enemies
        self.collectibles = level.collectibles
        self.background = Background(level.width_px, level.ground_y, level.ground_segments_px, level.theme)

        character = get_character(character_id)
        self.player = Player(*level.player_start, character_id=character["id"], color=character["color"])

        # A "sprite group" is pygame's container for a batch of sprites.
        # It gives us group.draw(screen) and group.update(...) instead of
        # hand-rolled loops, and spritecollide() below checks one sprite
        # against every sprite in a group in one call.
        self.all_sprites = pygame.sprite.Group(
            self.player, *self.platforms, *self.enemies, *self.collectibles
        )

        # How far the world has scrolled left, in pixels, so the camera
        # can follow the player through a level wider than the screen.
        self.camera_x = 0.0

        self.question_bank = QuestionBank()
        self.score = 0
        self.lives = STARTING_LIVES
        self.gauge = 0
        self.invulnerable_timer = 0.0
        self.hud_font = get_font(22)
        self.hud_font_small = get_font(16)
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
        self.enemies.update(dt, self.platforms)
        self.background.update(dt)

        # Keep the player roughly centered horizontally by shifting the
        # camera, but never scroll past the left edge of the level.
        target_camera_x = self.player.rect.centerx - SCREEN_WIDTH / 2
        self.camera_x = max(0.0, target_camera_x)

        self._check_question_blocks()
        self._check_collectibles()

        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        else:
            self._check_enemy_contact()

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
        question = self.question_bank.random_question()

        # Snapshot the level as it looks right now (block already
        # marked used) so the quiz box shows over the actual scene
        # instead of a plain color, and anchor the box to the block's
        # current on-screen position so it appears right next to it.
        self._draw()
        background = self.screen.copy()
        anchor_rect = block.rect.move(-self.camera_x, 0)

        correct = QuizScreen(self.screen, question, background=background, anchor_rect=anchor_rect).run()

        if correct:
            self.score += CORRECT_ANSWER_SCORE
        else:
            self._take_damage()

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

        score_label = self.hud_font.render(f"Score: {self.score}", True, HUD_TEXT_COLOR)
        lives_label = self.hud_font.render(f"Lives: {self.lives}", True, HUD_TEXT_COLOR)
        self.screen.blit(score_label, (12, 10))
        self.screen.blit(lives_label, (12, 36))
        self._draw_gauge_bar()

    def _draw_gauge_bar(self):
        width, height = GAUGE_BAR_SIZE
        bar_rect = pygame.Rect(GAUGE_BAR_POS, GAUGE_BAR_SIZE)
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

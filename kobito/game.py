import pygame

from kobito import input as game_input
from kobito.background import Background
from kobito.characters import get_character
from kobito.badges import badge_for_level, draw_badge
from kobito.constants import (
    BADGE_PASS_ACCURACY,
    CORRECT_ANSWER_SCORE,
    FPS,
    GAUGE_DAMAGE,
    GAUGE_MAX,
    INVULNERABILITY_SECONDS,
    JLPT_GAUGE_PENALTY,
    JLPT_QUESTION_POINTS,
    KNOCKBACK_SPEED_X,
    KNOCKBACK_SPEED_Y,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STARTING_LIVES,
    required_question_count,
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
HUD_TEXT_OUTLINE = (20, 20, 20)
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

    def __init__(
        self,
        character_id="capybara",
        theme_id="forest",
        companion_id="kobito",
        jlpt_level="N5",
        level_number=1,
        starting_score=0,
    ):
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
        self.badge = badge_for_level(jlpt_level, level_number)
        self.badge_earned = False

        self.jlpt_level = jlpt_level
        self.level_number = level_number
        game_input.get_joysticks()

        level = build_level1(theme_id, level_number=level_number)
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
        self.hint_service = HintService(companion_id=companion_id)
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

            game_input.handle_hotplug(event)

            if event.type == pygame.JOYBUTTONDOWN:
                if self.level_complete and event.button in game_input.CONFIRM_BUTTONS:
                    self.outcome = OUTCOME_ADVANCE
                    self.running = False
                elif event.button in game_input.CANCEL_BUTTONS:
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
        self.badge_earned = self._badge_earned()

    def _badge_earned(self):
        """The level's badge needs a decent sample answered *and* most of
        it right -- 7 of 10 at level 1, climbing with level_number (see
        required_question_count). Requiring the minimum count too stops
        a player claiming the badge off a single lucky answer.
        """
        answered = self.correct_count + self.wrong_count
        if answered < required_question_count(self.level_number):
            return False
        return self.correct_count / answered >= BADGE_PASS_ACCURACY

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
        companion = self.hint_service.companion
        base_points = JLPT_QUESTION_POINTS.get(question["jlpt"], CORRECT_ANSWER_SCORE)
        # Companion abilities scale the base numbers (see
        # kobito/companions.py) -- Hana's Bright Spark bumps XP gain,
        # Kinoko's Playful Streak adds a flat score bonus, Ushi's Steady
        # Heart softens the penalty. Kobito's multipliers are all 1.0 /
        # 0, so it's a no-op for the baseline companion.
        points = round(base_points * companion["xp_gain_multiplier"]) + companion["bonus_score"]
        penalty = round(JLPT_GAUGE_PENALTY.get(question["jlpt"], GAUGE_DAMAGE) * companion["xp_penalty_multiplier"])

        # Snapshot the level as it looks right now (block already
        # marked used) so the quiz box shows over the actual scene
        # instead of a plain color, and anchor the box to the block's
        # current on-screen position so it appears right next to it.
        self._draw()
        background = self.screen.copy()
        anchor_rect = block.rect.move(-self.camera_x, 0)

        correct = QuizScreen(
            self.screen,
            question,
            background=background,
            anchor_rect=anchor_rect,
            hint_service=self.hint_service,
            points=points,
            penalty=penalty,
        ).run()

        if correct:
            # Quiz blocks are the main XP source: a right answer both
            # scores and fills the gauge, so studying -- not just coin
            # collecting -- is what earns bonus lives.
            self.score += points
            self._add_gauge(points)
            self.correct_count += 1
        else:
            # Costs XP but not a life -- the badge only asks for 70%
            # accuracy, so getting a few wrong has to be survivable.
            self.gauge = max(0, self.gauge - penalty)
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

    def _take_damage(self, gauge_cost=GAUGE_DAMAGE):
        # A wrong quiz answer or an enemy hit costs a life outright,
        # *and* sets the gauge back -- mistakes also cost progress
        # toward the next bonus life, not just the life you just lost.
        # Quiz misses pass a gauge_cost scaled to the question's JLPT
        # level; enemy contact uses the flat default.
        self.lives -= 1
        self.gauge = max(0, self.gauge - gauge_cost)
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
        # No background panel -- an outline around each glyph (instead
        # of a solid color) is what keeps the HUD readable against any
        # world's sky, bright or dark, without covering the scene.
        self._draw_outlined_text(f"Level {self.level_number} - {self.jlpt_level}", self.hud_font, (12, 10))
        self._draw_outlined_text(f"Score: {self.score}", self.hud_font, (12, 36))
        self._draw_outlined_text(f"Lives: {self.lives}", self.hud_font, (12, 62))
        self._draw_gauge_bar()
        self._draw_quiz_progress()

    def _draw_quiz_progress(self):
        """Shows progress toward the badge (e.g. "Quiz 6/8  -  badge at
        7/10"), so the 70% bar is something the player can actually aim
        at mid-level rather than a surprise at the castle.
        """
        answered = self.correct_count + self.wrong_count
        min_questions = required_question_count(self.level_number)
        needed = round(min_questions * BADGE_PASS_ACCURACY)
        text = f"Quiz {self.correct_count}/{answered}"
        if not self._badge_earned():
            text += f"    badge at {needed}/{min_questions}"
        else:
            text += "    badge ready!"
        self._draw_outlined_text(text, self.hud_font_small, (12, 104))

    def _draw_outlined_text(self, text, font, pos, color=HUD_TEXT_COLOR, outline_color=HUD_TEXT_OUTLINE):
        outline = font.render(text, True, outline_color)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            self.screen.blit(outline, (pos[0] + dx, pos[1] + dy))
        self.screen.blit(font.render(text, True, color), pos)

    def _draw_gauge_bar(self):
        width, height = GAUGE_BAR_SIZE
        bar_rect = pygame.Rect(GAUGE_BAR_POS[0], GAUGE_BAR_POS[1] + 26, *GAUGE_BAR_SIZE)
        pygame.draw.rect(self.screen, GAUGE_BAR_BG, bar_rect)

        fill_width = round(width * (self.gauge / GAUGE_MAX))
        if fill_width > 0:
            pygame.draw.rect(self.screen, GAUGE_BAR_FILL, (*bar_rect.topleft, fill_width, height))
        pygame.draw.rect(self.screen, GAUGE_BAR_BORDER, bar_rect, width=2)

        label_height = self.hud_font_small.get_height()
        self._draw_outlined_text(
            f"XP {self.gauge}/{GAUGE_MAX}",
            self.hud_font_small,
            (bar_rect.right + 8, bar_rect.centery - label_height // 2),
        )

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
        answered = self.correct_count + self.wrong_count
        min_questions = required_question_count(self.level_number)
        needed = round(min_questions * BADGE_PASS_ACCURACY)

        title = self.level_complete_font.render(f"Level {self.level_number} Complete!", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(centerx=center_x, y=42))

        # The badge is the prize, so it gets the visual center of the
        # screen -- shown greyed out when it wasn't earned, so the player
        # can see exactly what they just missed.
        draw_badge(self.screen, center_x, 190, 128, self.badge, earned=self.badge_earned)

        if self.badge_earned:
            headline = f"Badge earned:  {self.badge.name}"
            sub = self.badge.caption
            headline_color = (255, 226, 140)
        else:
            headline = f"Badge locked:  {self.badge.name}"
            sub = f"Answer {needed} of {min_questions} correctly to claim it -- so close!"
            headline_color = (215, 215, 220)

        lines = [
            (self.hud_font, headline, headline_color),
            (self.hud_font_small, sub, (225, 225, 230)),
            (self.hud_font, f"Score: {self.score}    Quiz: {self.correct_count}/{answered}"
                            f"    Accuracy: {round(self.level_accuracy * 100)}%", (255, 255, 255)),
            (self.hud_font, f"Next up: {self.next_jlpt_level} - {JLPT_DESCRIPTIONS[self.next_jlpt_level]}",
             (255, 255, 255)),
            (self.hud_font_small, "Press Enter to continue", (215, 215, 220)),
        ]
        y = 288
        for font, text, color in lines:
            surface = font.render(text, True, color)
            self.screen.blit(surface, surface.get_rect(centerx=center_x, y=y))
            y += surface.get_height() + 10

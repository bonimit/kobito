import asyncio
import math
import random

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
    DROWSY_JUMP_SCALE,
    DROWSY_RUN_SCALE,
    MAX_LIVES,
    POWER_DROWSY,
    POWER_MAX,
    POWER_WAKE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STARTING_LIVES,
    STOMP_BOUNCE_SPEED,
    STOMP_DROP_CHANCE,
    STOMP_GAUGE,
    STOMP_SCORE,
    WAKE_INVULNERABILITY_SECONDS,
    required_question_count,
)
from kobito.difficulty import JLPT_DESCRIPTIONS, next_jlpt_level
from kobito.companion_art import draw_companion
from kobito.entities.collectible import Collectible
from kobito.entities.enemy import FlyingEnemy
from kobito.entities.gift_box import GiftBox
from kobito.entities.player import Player
from kobito.entities.question_block import QuestionBlock
from kobito.fonts import get_font
from kobito.hint_service import HintService
from kobito.item_art import get_icon
from kobito.item_coach import ItemCoach
from kobito.items import BIG_DRINKS, SMALL_SNACKS, get_item, roll_gift
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
GAUGE_BAR_POS = (12, 90)
GAUGE_BAR_BG = (210, 205, 195)
GAUGE_BAR_FILL = (90, 190, 110)
GAUGE_BAR_BORDER = (60, 50, 40)

POWER_PIP = (15, 14)   # width, height of one power pip
POWER_OK = (96, 214, 120)
POWER_LOW = (240, 86, 86)
POWER_EMPTY = (60, 60, 70)
BOOST_SPEED_SCALE = 1.25
SPEECH_BOX = pygame.Rect(318, 8, SCREEN_WIDTH - 318 - 14, 0)

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
        # None on desktop (see kobito.input.IS_WEB) -- a phone has no
        # keyboard/joystick, so this on-screen d-pad + jump button is
        # its only way to play.
        self.touch_controls = game_input.get_gameplay_touch_controls(self.screen)

        character = get_character(character_id)
        self.character = character
        level = build_level1(theme_id, level_number=level_number, favorites=character["favorites"])
        self.platforms = level.platforms
        self.question_blocks = level.question_blocks
        self.gift_boxes = level.gift_boxes
        self.enemies = level.enemies
        self.collectibles = level.collectibles
        self.goal = level.goal
        self.background = Background(level.width_px, level.ground_y, level.ground_segments_px, level.theme)

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

        # Power: stamina out of POWER_MAX. Enemy hits drain it; konbini
        # snacks and gift-box prizes refill it. See kobito/constants.py.
        self.power = POWER_MAX
        self.boost_timer = 0.0
        self.drowsy_warned = False
        self.fell_asleep_flag = False
        self.rng = random.Random()
        self.coach = ItemCoach(self.hint_service, character["name"])
        self.effects = []          # floating text / icons / puffs, see _add_effect
        self.stomps = 0
        self.snacks_eaten = 0
        self.favorites_found = 0
        self.gifts_opened = 0
        self.clock_time = 0.0
        self._vignette = self._build_vignette()
        self.hud_font = get_font(22)
        self.speech_font = get_font(15)
        self.hud_font_small = get_font(16)
        self.game_over_font = get_font(36)
        self.level_complete_font = get_font(32)

    async def run(self):
        while self.running:
            # dt = seconds since last frame. Using it to scale movement
            # (instead of moving a fixed number of pixels/frame) keeps
            # speeds consistent even if the frame rate dips.
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            await self._update(dt)
            self._draw()
            # Yields to the browser's event loop every frame -- required
            # by Pygbag's Emscripten build (a plain blocking loop would
            # freeze the tab); a harmless no-op in the desktop build.
            await asyncio.sleep(0)

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

            if self.touch_controls:
                jump_tapped = self.touch_controls.handle_event(event)
                if jump_tapped and self.level_complete:
                    self.outcome = OUTCOME_ADVANCE
                    self.running = False

    async def _update(self, dt):
        if self.game_over or self.level_complete:
            return

        self.clock_time += dt
        self._apply_power_effects(dt)
        self.player.update(dt, self.platforms)
        self.enemies.update(dt, self.platforms)
        self.background.update(dt)
        self.coach.update(dt)
        self._update_effects(dt)

        # Keep the player roughly centered horizontally by shifting the
        # camera, but never scroll past the left edge of the level.
        target_camera_x = self.player.rect.centerx - SCREEN_WIDTH / 2
        self.camera_x = max(0.0, target_camera_x)

        await self._check_question_blocks()
        self._check_gift_boxes()
        self._check_collectibles()
        self._check_goal()

        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self._check_enemy_contact(dt)

    @property
    def drowsy(self):
        return self.power <= POWER_DROWSY

    def _apply_power_effects(self, dt):
        """Sleepy players are slower; a golden-can boost makes them faster."""
        run, jump = 1.0, 1.0
        if self.drowsy:
            run, jump = DROWSY_RUN_SCALE, DROWSY_JUMP_SCALE
        if self.boost_timer > 0:
            self.boost_timer = max(0.0, self.boost_timer - dt)
            run = max(run, BOOST_SPEED_SCALE)
        self.player.run_scale, self.player.jump_scale = run, jump

    def _set_power(self, value):
        """Changes power, and has the companion warn the player the first
        time they slip into drowsy territory (and again after they've
        recovered and slipped back)."""
        self.power = max(0, min(POWER_MAX, value))
        if self.drowsy and self.power > 0 and not self.drowsy_warned:
            self.drowsy_warned = True
            self.coach.warn_drowsy(self.power)
        elif not self.drowsy:
            self.drowsy_warned = False

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
        for pickup in pygame.sprite.spritecollide(self.player, self.collectibles, dokill=True):
            where = (pickup.rect.centerx, pickup.rect.top)
            if pickup.item is not None:
                self._collect_item(pickup.item, where)
            elif pickup.kind == "shiitake":
                self.lives = min(MAX_LIVES, self.lives + 1)
                self._add_effect_text("+1 Life", where, (255, 150, 150))
            else:
                self.score += pickup.value
                self._add_gauge(pickup.value)

    def _collect_item(self, item, where, from_gift=False):
        """Applies one item: score, power, life, speed boost -- then has the
        companion react and teach the word."""
        was_sleepy = self.drowsy
        self.score += item.score
        self._add_gauge(item.score)

        before = self.power
        self._set_power(POWER_MAX if item.full_power else self.power + item.power)
        gained = self.power - before
        if item.life:
            self.lives = min(MAX_LIVES, self.lives + item.life)
        if item.boost_seconds:
            self.boost_timer = item.boost_seconds

        if item.group == "favorite":
            situation, color = "favorite", (255, 170, 210)
            self.favorites_found += 1
        elif item.group == "rare":
            situation, color = "rare", (255, 226, 120)
        elif was_sleepy and not self.drowsy:
            situation, color = "rescue", (150, 255, 170)
        else:
            situation, color = "snack", (170, 235, 255)
        if item.group == "konbini":
            self.snacks_eaten += 1

        label = item.name + (f"  +{gained} Power" if gained else "")
        if item.life:
            label += "  +1 Life"
        self._add_effect_text(label, where, color)
        if from_gift:
            self._add_effect_icon(item.id, where)
        self.coach.react(situation, item, self.power)

    def _check_gift_boxes(self):
        # Same trick as the question blocks: player.touched is whatever the
        # player overlapped during collision resolution this frame.
        for solid in self.player.touched:
            if isinstance(solid, GiftBox) and not solid.used:
                self._open_gift(solid)
                break

    def _open_gift(self, box):
        box.mark_used()
        self.gifts_opened += 1
        top = (box.rect.centerx, box.rect.top)
        gift = roll_gift(self.rng, self.character["favorites"], sleepy=self.drowsy)
        if gift["kind"] == "coins":
            earned = gift["coins"] * 5
            self.score += earned
            self._add_gauge(earned)
            self._add_effect_text(f"+{gift['coins']} coins!", top, (255, 226, 120))
            self.coach.react("coins", None, self.power)
        elif gift["kind"] == "life":
            self.lives = min(MAX_LIVES, self.lives + 1)
            self._add_effect_text("+1 Life!", top, (255, 150, 150))
            self.coach.react("life", None, self.power)
        else:
            self._collect_item(gift["item"], top, from_gift=True)

    def _add_gauge(self, amount):
        self.gauge += amount
        while self.gauge >= GAUGE_MAX:
            self.gauge -= GAUGE_MAX
            self.lives += 1

    async def _check_question_blocks(self):
        # player.touched is whatever solids collision resolution found
        # this frame (see Player.update) -- filter down to the one kind
        # we care about here, and only the ones not already answered.
        for solid in self.player.touched:
            if isinstance(solid, QuestionBlock) and not solid.used:
                await self._trigger_question(solid)
                break  # handle at most one block per frame

    async def _trigger_question(self, block):
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

        correct = await QuizScreen(
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

    def _check_enemy_contact(self, dt):
        hit_enemies = pygame.sprite.spritecollide(self.player, self.enemies, dokill=False)
        if not hit_enemies:
            return

        # Jumping on an enemy's head defeats it: the player has to be
        # falling, with their feet near the enemy's top. Checked even while
        # invulnerable, so a post-hit blink is a chance to hit back.
        slack = 18 + max(0.0, self.player.velocity_y) * dt
        for enemy in hit_enemies:
            if self.player.velocity_y > 0 and self.player.rect.bottom - enemy.rect.top <= slack:
                self._stomp(enemy)
                return

        if self.invulnerable_timer > 0:
            return

        self._take_hit()
        self.invulnerable_timer = INVULNERABILITY_SECONDS

        # Knock the player up and away from whichever enemy they hit,
        # so they don't just immediately re-collide once invulnerability
        # ends, and so the hit reads clearly (same idea as classic
        # platformers bouncing you back on damage).
        enemy = hit_enemies[0]
        direction = -1 if self.player.rect.centerx < enemy.rect.centerx else 1
        self.player.velocity_x = direction * KNOCKBACK_SPEED_X
        self.player.velocity_y = KNOCKBACK_SPEED_Y

    def _stomp(self, enemy):
        where = (enemy.rect.centerx, enemy.rect.top)
        ground_enemy = not isinstance(enemy, FlyingEnemy)
        enemy.kill()
        self.stomps += 1
        self.score += STOMP_SCORE
        self._add_gauge(STOMP_GAUGE)
        self.player.velocity_y = -STOMP_BOUNCE_SPEED
        self.player.on_ground = False
        self._add_effect_text(f"+{STOMP_SCORE}", where, (255, 255, 255))
        self._add_effect_puff(where)

        # Ground enemies sometimes drop a snack where they stood.
        if ground_enemy and self.rng.random() < STOMP_DROP_CHANCE:
            snack = get_item(self.rng.choice(SMALL_SNACKS + BIG_DRINKS))
            drop = Collectible(enemy.rect.centerx - 13, enemy.rect.bottom - 28, kind=snack.id)
            self.collectibles.add(drop)
            self.all_sprites.add(drop)

    def _take_hit(self):
        """An enemy hit costs 1 power (ten hits drain a full gauge) and
        sets the XP gauge back. Running out of power means falling
        asleep: that costs a life, and the player wakes up groggy."""
        self.gauge = max(0, self.gauge - GAUGE_DAMAGE)
        self._set_power(self.power - 1)
        if self.power > 0:
            return

        self.lives -= 1
        self.coach.fell_asleep(self.power)
        self._add_effect_text("Zzz...", (self.player.rect.centerx, self.player.rect.top), (190, 200, 255))
        if self.lives <= 0:
            self.fell_asleep_flag = True
            self.game_over = True
            return
        self._set_power(POWER_WAKE)
        self.drowsy_warned = False
        self.invulnerable_timer = WAKE_INVULNERABILITY_SECONDS

    # -- Floating effects (world-space text, icons, puffs) -------------------

    def _add_effect_text(self, text, where, color):
        self.effects.append({"kind": "text", "text": text, "x": where[0], "y": where[1] - 6,
                             "t": 0.0, "life": 1.5, "color": color})

    def _add_effect_icon(self, item_id, where):
        self.effects.append({"kind": "icon", "item": item_id, "x": where[0], "y": where[1] - 20,
                             "t": 0.0, "life": 1.0})

    def _add_effect_puff(self, where):
        self.effects.append({"kind": "puff", "x": where[0], "y": where[1] + 8, "t": 0.0, "life": 0.45})

    def _update_effects(self, dt):
        for effect in self.effects:
            effect["t"] += dt
        self.effects = [e for e in self.effects if e["t"] < e["life"]]

    def _draw_effects(self):
        for e in self.effects:
            progress = e["t"] / e["life"]
            x = e["x"] - self.camera_x
            if e["kind"] == "text":
                self._draw_outlined_text(e["text"], self.hud_font_small,
                                         (x - self.hud_font_small.size(e["text"])[0] // 2, e["y"] - 46 * progress),
                                         color=e["color"])
            elif e["kind"] == "icon":
                icon = get_icon(e["item"], 40)
                self.screen.blit(icon, icon.get_rect(center=(x, e["y"] - 70 * progress)))
            else:
                for i in range(6):
                    angle = i * math.pi / 3
                    r = 6 + 26 * progress
                    pygame.draw.circle(self.screen, (250, 250, 240),
                                       (x + math.cos(angle) * r, e["y"] + math.sin(angle) * r * 0.7),
                                       max(1, round(5 * (1 - progress))))

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

        self._draw_effects()
        if self.drowsy and not self.game_over:
            self._draw_drowsy()
        self._draw_hud()
        self._draw_speech()
        if self.game_over:
            self._draw_game_over()
        elif self.level_complete:
            self._draw_level_complete()

        if self.touch_controls:
            self.touch_controls.draw(self.screen)

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
        self._draw_outlined_text(f"Level {self.level_number} - {self.jlpt_level}", self.hud_font, (12, 8))
        self._draw_outlined_text(f"Score: {self.score}", self.hud_font, (12, 32))
        self._draw_outlined_text(f"Lives: {self.lives}", self.hud_font, (12, 56))
        self._draw_favorites()
        self._draw_power()
        self._draw_gauge_bar()
        self._draw_quiz_progress()

    def _draw_favorites(self):
        """The mascot's two favourite items, with how many have been found
        this level -- a small reminder of what to hunt for."""
        x = 112
        for item_id in self.character["favorites"]:
            self.screen.blit(get_icon(item_id, 22), (x, 58))
            x += 26
        self._draw_outlined_text(f"x{self.favorites_found}", self.hud_font_small, (x + 2, 62))

    def _draw_power(self):
        """Ten pips: green when healthy, flashing red when drowsy."""
        x0, y0 = 12, 84 - 0
        pip_w, pip_h = POWER_PIP
        flash = self.drowsy and int(self.clock_time * 4) % 2 == 0
        for i in range(POWER_MAX):
            rect = pygame.Rect(x0 + i * (pip_w + 3), y0, pip_w, pip_h)
            filled = i < self.power
            color = POWER_EMPTY if not filled else (POWER_LOW if self.drowsy else POWER_OK)
            if filled and flash:
                color = (255, 170, 170)
            pygame.draw.rect(self.screen, color, rect, border_radius=3)
            pygame.draw.rect(self.screen, GAUGE_BAR_BORDER, rect, width=2, border_radius=3)
        label = f"POWER {self.power}/{POWER_MAX}"
        if self.drowsy:
            label += "  sleepy..."
        elif self.boost_timer > 0:
            label += f"  BOOST {math.ceil(self.boost_timer)}s"
        self._draw_outlined_text(label, self.hud_font_small, (x0 + POWER_MAX * (pip_w + 3) + 6, y0 - 1),
                                 color=(255, 190, 190) if self.drowsy else HUD_TEXT_COLOR)

    # -- Drowsiness -----------------------------------------------------------

    @staticmethod
    def _build_vignette():
        """Dark blue edges (built from stacked frames, no per-pixel work)
        that fade in when the player is about to fall asleep."""
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        surface.fill((14, 20, 70, 40))  # a faint all-over blue tint, like heavy eyelids
        steps = 60
        for i in range(steps):
            alpha = max(40, round(235 * (1 - i / steps) ** 1.6))
            pygame.draw.rect(surface, (10, 14, 64, alpha),
                             (i * 4, i * 3, SCREEN_WIDTH - i * 8, SCREEN_HEIGHT - i * 6), width=4)
        return surface

    def _draw_drowsy(self):
        pulse = 0.75 + 0.25 * math.sin(self.clock_time * 2.4)
        self._vignette.set_alpha(round(255 * pulse))
        self.screen.blit(self._vignette, (0, 0))
        # Z's drifting up from the player's head.
        head = self.player.rect.midtop
        for i in range(3):
            t = (self.clock_time * 0.7 + i / 3) % 1.0
            letter = self.hud_font.render("Z", True, (200, 210, 255))
            letter.set_alpha(round(255 * (1 - t)))
            self.screen.blit(letter, (head[0] - self.camera_x + 8 + i * 6 + t * 14, head[1] - 10 - t * 46))

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
        self._draw_outlined_text(text, self.hud_font_small, (12, 134))

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

    def _wrap(self, text, font, width):
        lines, current = [], ""
        for word in text.replace("  ", " ").split(" "):
            trial = f"{current} {word}".strip()
            if current and font.size(trial)[0] > width:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        return lines

    def _draw_speech(self):
        """The companion's reaction to what just happened -- a small box
        at the top, never blocking play, that fades out by itself."""
        speech = self.coach.speech
        if speech is None:
            return
        text_x = SPEECH_BOX.x + 64
        width = SPEECH_BOX.width - 64 - 12
        rows = []
        for index, line in enumerate(speech.lines):
            color = (255, 244, 214) if index == 0 else (180, 215, 255)
            for wrapped in self._wrap(line, self.speech_font, width):
                rows.append((wrapped, color))
        rows = rows[:5]
        height = max(60, 38 + len(rows) * (self.speech_font.get_height() + 3))
        box = pygame.Rect(SPEECH_BOX.x, SPEECH_BOX.y, SPEECH_BOX.width, height)

        fade = min(1.0, speech.seconds_left / 0.6)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 12, 24, round(190 * fade)), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, (255, 214, 150, round(220 * fade)), panel.get_rect(), width=2, border_radius=10)
        self.screen.blit(panel, box.topleft)

        draw_companion(self.screen, self.coach.companion["id"], box.x + 32, box.centery, 44,
                       expression=speech.expression)
        name = self.speech_font.render(self.coach.companion["name"], True, (255, 210, 110))
        self.screen.blit(name, (text_x, box.y + 6))
        y = box.y + 8 + name.get_height()
        for text, color in rows:
            surface = self.speech_font.render(text, True, color)
            self.screen.blit(surface, (text_x, y))
            y += surface.get_height() + 3

    def _draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(GAME_OVER_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        text = self.game_over_font.render(f"Game Over - Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        if self.fell_asleep_flag:
            note = self.hud_font.render("You fell asleep... grab a snack next time!", True, (190, 200, 255))
            self.screen.blit(note, note.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 44)))

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
            (self.hud_font_small, f"Stomped {self.stomps}   Snacks {self.snacks_eaten}   "
                                  f"Favorites {self.favorites_found}   Gifts {self.gifts_opened}", (200, 225, 255)),
            (self.hud_font_small, "Press Enter to continue", (215, 215, 220)),
        ]
        y = 288
        for font, text, color in lines:
            surface = font.render(text, True, color)
            self.screen.blit(surface, surface.get_rect(centerx=center_x, y=y))
            y += surface.get_height() + 10

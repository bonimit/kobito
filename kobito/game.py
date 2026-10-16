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
    XP_PER_LIFE,
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
from kobito import ui
from kobito.hint_service import HintService
from kobito.item_art import get_icon
from kobito.item_coach import ItemCoach
from kobito.items import BIG_DRINKS, SMALL_SNACKS, get_item, roll_gift
from kobito.levels.level1 import build_level1
from kobito.questions import QuestionBank
from kobito.quiz_screen import QuizScreen
from kobito.settings_screen import PAGE_ITEMS, PAGE_MENU, RESULT_QUIT, SettingsScreen

OVERLAY = (8, 6, 16, 175)
BLINK_INTERVAL_SECONDS = 0.1
CONTINUE_KEYS = (pygame.K_RETURN, pygame.K_SPACE)
SETTINGS_KEYS = (pygame.K_ESCAPE, pygame.K_p)
SETTINGS_BUTTONS = (6, 7)  # gamepad Back / Start

# HUD layout (see _draw_hud). Two cards in the top corners -- the left one
# is "you" (score, lives, power, XP), the right one is "the lesson" (quiz
# progress toward the badge) -- with a small tray of icons under it.
HUD_LEFT_CARD = pygame.Rect(10, 10, 286, 118)
HUD_RIGHT_CARD = pygame.Rect(SCREEN_WIDTH - 10 - 262, 10, 262, 104)
HUD_TRAY_HEIGHT = 40

POWER_PIP = (13, 14)   # width, height of one power pip
POWER_OK = (96, 214, 120)
POWER_LOW = (240, 86, 86)
POWER_EMPTY = (60, 56, 76)
XP_FILL = (150, 205, 255)
BOOST_SPEED_SCALE = 1.25
# Docked at the bottom, in the strip below the ground line (y=480): nothing
# is played down there, so the box never covers the player. Its sides stop
# short of the on-screen touch buttons in the web build.
SPEECH_BOX = pygame.Rect(196, SCREEN_HEIGHT - 66, SCREEN_WIDTH - 196 - 104, 62)
SPEECH_FONT_SIZES = (19, 17, 15)   # largest that fits in two lines wins

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
        starting_xp=0,
        item_box=None,
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
        self.skipped_count = 0
        self.lives = STARTING_LIVES
        # XP is a running total that carries from level to level; each time
        # it passes another multiple of XP_PER_LIFE the player earns a life.
        self.xp = starting_xp
        self.next_life_xp = (starting_xp // XP_PER_LIFE + 1) * XP_PER_LIFE
        self.asked_ids = set()  # questions already asked this level (no repeats)
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
        # Every item picked up this run, id -> count. main.py passes the same
        # dict to each level so the box carries over; it's opened from the
        # settings screen (the HUD just shows a crate icon and a count).
        self.item_box = item_box if item_box is not None else {}
        self.pending_settings = None   # page to open at the end of this frame
        self._box_rect = None          # HUD icons, clickable / tappable
        self._gear_rect = None

    async def run(self):
        while self.running:
            # dt = seconds since last frame. Using it to scale movement
            # (instead of moving a fixed number of pixels/frame) keeps
            # speeds consistent even if the frame rate dips.
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            if self.pending_settings:
                await self._open_settings(self.pending_settings)
                continue
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

        return self.outcome, self.score, self.next_jlpt_level, self.xp

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.game_over and event.key in CONTINUE_KEYS + SETTINGS_KEYS:
                    self.running = False
                elif event.key in SETTINGS_KEYS:
                    self.pending_settings = PAGE_MENU
                elif self.level_complete and event.key in CONTINUE_KEYS:
                    self.outcome = OUTCOME_ADVANCE
                    self.running = False

            game_input.handle_hotplug(event)

            if event.type == pygame.JOYBUTTONDOWN:
                if self.game_over and event.button in game_input.CONFIRM_BUTTONS + SETTINGS_BUTTONS:
                    self.running = False
                elif self.level_complete and event.button in game_input.CONFIRM_BUTTONS:
                    self.outcome = OUTCOME_ADVANCE
                    self.running = False
                elif event.button in SETTINGS_BUTTONS:
                    self.pending_settings = PAGE_MENU

            tap = game_input.touch_tap_pos(event)
            if tap is not None and not self.game_over:
                if self._gear_rect and self._gear_rect.collidepoint(tap):
                    self.pending_settings = PAGE_MENU
                    continue
                if self._box_rect and self._box_rect.collidepoint(tap):
                    self.pending_settings = PAGE_ITEMS
                    continue

            if self.touch_controls:
                jump_tapped = self.touch_controls.handle_event(event)
                if jump_tapped and self.level_complete:
                    self.outcome = OUTCOME_ADVANCE
                    self.running = False

    async def _open_settings(self, page):
        """Pauses the level under the settings menu. Quit there ends the
        run; otherwise play picks up exactly where it stopped."""
        self.pending_settings = None
        self._draw()
        result = await SettingsScreen(self.screen, self.screen.copy(), self.item_box, start_page=page).run()
        if result == RESULT_QUIT:
            self.running = False
        # Same reason as after a quiz: the menu's time shouldn't arrive as
        # one huge dt on the next frame.
        self.clock.tick(FPS)

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
                self._add_xp(pickup.value)

    def _collect_item(self, item, where, from_gift=False):
        """Applies one item: score, power, life, speed boost -- then has the
        companion react and teach the word."""
        was_sleepy = self.drowsy
        self.item_box[item.id] = self.item_box.get(item.id, 0) + 1
        self.score += item.score
        self._add_xp(item.score)

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
            self._add_xp(earned)
            self._add_effect_text(f"+{gift['coins']} coins!", top, (255, 226, 120))
            self.coach.react("coins", None, self.power)
        elif gift["kind"] == "life":
            self.lives = min(MAX_LIVES, self.lives + 1)
            self._add_effect_text("+1 Life!", top, (255, 150, 150))
            self.coach.react("life", None, self.power)
        else:
            self._collect_item(gift["item"], top, from_gift=True)

    def _add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.next_life_xp:
            self.next_life_xp += XP_PER_LIFE
            self.lives = min(MAX_LIVES, self.lives + 1)
            self._add_effect_text("1UP!", (self.player.rect.centerx, self.player.rect.top), (255, 150, 150))

    def _lose_xp(self, amount):
        # Never below zero. A bonus life already earned is kept, and
        # next_life_xp doesn't move back, so the lost XP has to be won again.
        self.xp = max(0, self.xp - amount)

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
        question = self.question_bank.random_question(jlpt=self.jlpt_level, exclude=self.asked_ids)
        self.asked_ids.add(question["id"])
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

        if correct is None:
            # Passed: nothing answered, nothing lost -- the badge only needs
            # 20 of the level's 30 questions answered.
            self.skipped_count += 1
            self._add_effect_text("Skipped", (block.rect.centerx, block.rect.top), (210, 210, 225))
        elif correct:
            # Quiz blocks are the main XP source: a right answer both
            # scores and adds XP, so studying -- not just coin
            # collecting -- is what earns bonus lives.
            self.score += points
            self._add_xp(points)
            self.correct_count += 1
        else:
            # Costs XP but not a life -- the badge only asks for 70%
            # accuracy, so getting a few wrong has to be survivable.
            self._lose_xp(penalty)
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
        self._add_xp(STOMP_GAUGE)
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
        takes a little XP off. Running out of power means falling
        asleep: that costs a life, and the player wakes up groggy."""
        self._lose_xp(GAUGE_DAMAGE)
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
                ui.text(self.screen, e["text"], ui.label_font(16), (x, e["y"] - 46 * progress),
                        color=e["color"], anchor="midbottom")
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
        if not (self.game_over or self.level_complete):
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

    # -- HUD -------------------------------------------------------------------
    #
    # One type scale everywhere (kobito/ui.py): gold pixel LABELS name a
    # thing, big pixel NUMBERS are the thing, rounded BODY text is for
    # sentences. Each card reads top-down as label -> number -> detail.

    def _draw_hud(self):
        self._draw_player_card()
        self._draw_level_pill()
        self._draw_quiz_card()
        self._draw_tray()

    def _draw_player_card(self):
        card = ui.panel(self.screen, HUD_LEFT_CARD)
        x, right = card.x + 14, card.right - 14
        label, big = ui.label_font(16), ui.title_font(32)

        ui.text(self.screen, "SCORE", label, (x, card.y + 8), color=ui.GOLD)
        ui.text(self.screen, str(self.score), big, (x, card.y + 24))
        ui.text(self.screen, "LIVES", label, (right, card.y + 8), color=ui.GOLD, anchor="topright")
        lives = ui.text(self.screen, f"×{self.lives}", big, (right, card.y + 24), anchor="topright")
        ui.heart(self.screen, (lives.x - 16, lives.centery + 1), 22)

        # Power: ten pips -- green when fine, flashing red when sleepy.
        row = card.y + 70
        ui.text(self.screen, "POWER", label, (x, row), color=ui.GOLD)
        pip_w, pip_h = POWER_PIP
        px = x + 66
        flash = self.drowsy and int(self.clock_time * 4) % 2 == 0
        for i in range(POWER_MAX):
            rect = pygame.Rect(px + i * (pip_w + 3), row + 1, pip_w, pip_h)
            filled = i < self.power
            color = POWER_EMPTY if not filled else (POWER_LOW if self.drowsy else POWER_OK)
            if filled and flash:
                color = (255, 170, 170)
            pygame.draw.rect(self.screen, ui.OUTLINE, rect.inflate(4, 4), border_radius=4)
            pygame.draw.rect(self.screen, color, rect, border_radius=3)
        ui.text(self.screen, str(self.power), label, (right, row), anchor="topright",
                color=ui.RED if self.drowsy else ui.CREAM)

        # XP: a running total, and a slim bar toward the next bonus life.
        row = card.y + 94
        ui.text(self.screen, "XP", label, (x, row), color=ui.GOLD)
        value = ui.text(self.screen, str(self.xp), label, (x + 66, row))
        next_up = ui.text(self.screen, f"1UP {self.next_life_xp}", label, (right, row), color=ui.MUTED,
                          anchor="topright", thickness=1)
        bar_x = max(value.right + 10, x + 120)
        into_life = self.xp - (self.next_life_xp - XP_PER_LIFE)
        ui.bar(self.screen, (bar_x, row + 5, next_up.x - 10 - bar_x, 7), into_life / XP_PER_LIFE, XP_FILL, radius=3)

        # Temporary states get their own tag under the card, so they're
        # noticed without crowding the numbers above.
        tag = None
        if self.drowsy:
            tag = ("SLEEPY... FIND A SNACK!", (120, 30, 44, 220), (255, 190, 190))
        elif self.boost_timer > 0:
            tag = (f"BOOST  {math.ceil(self.boost_timer)}s", (24, 70, 44, 220), (170, 255, 190))
        if tag:
            words, bg, color = tag
            width = label.size(words)[0] + 24
            pill = ui.panel(self.screen, (card.x, card.bottom + 6, width, 26), bg=bg, edge=(*color, 160), radius=13)
            ui.text(self.screen, words, label, pill.center, color=color, anchor="center", thickness=1)

    def _draw_level_pill(self):
        label = ui.label_font(16)
        words = f"LEVEL {self.level_number}  ·  {self.jlpt_level}"
        pill = pygame.Rect(0, 0, label.size(words)[0] + 32, 28)
        pill.midtop = (SCREEN_WIDTH // 2, 12)
        ui.panel(self.screen, pill, radius=14)
        ui.text(self.screen, words, label, pill.center, color=ui.GOLD, anchor="center")

    def _draw_quiz_card(self):
        """Progress toward the badge -- at least N questions answered, 70%
        of them right -- so it's something to aim at mid-level rather than
        a surprise at the castle."""
        card = ui.panel(self.screen, HUD_RIGHT_CARD)
        x, right = card.x + 14, card.right - 14
        label, big = ui.label_font(16), ui.title_font(32)
        answered = self.correct_count + self.wrong_count
        min_questions = required_question_count(self.level_number)
        ready = self._badge_earned()

        ui.text(self.screen, "QUIZ", label, (x, card.y + 8), color=ui.GOLD)
        goal = "BADGE READY!" if ready else f"BADGE: {round(BADGE_PASS_ACCURACY * 100)}% RIGHT"
        ui.text(self.screen, goal, label, (right, card.y + 8), color=ui.GREEN if ready else ui.MUTED,
                anchor="topright", thickness=1)
        count = ui.text(self.screen, str(answered), big, (x, card.y + 24))
        ui.text(self.screen, f"/{min_questions} answered", label, (count.right + 4, count.bottom - 6),
                color=ui.CREAM, anchor="bottomleft")

        ui.bar(self.screen, (x, card.y + 66, card.width - 28, 7), answered / min_questions,
               ui.GREEN if ready else ui.GOLD, radius=3)

        row = card.y + 80
        accuracy = round(100 * self.correct_count / answered) if answered else None
        right_text = ui.text(self.screen, f"{self.correct_count} right", label, (x, row))
        if accuracy is not None:
            ok = accuracy >= BADGE_PASS_ACCURACY * 100
            ui.text(self.screen, f"{accuracy}%", label, (right_text.right + 10, row),
                    color=ui.GREEN if ok else (255, 150, 150))
        if self.skipped_count:
            ui.text(self.screen, f"{self.skipped_count} skipped", label, (right, row), color=ui.MUTED,
                    anchor="topright", thickness=1)

    def _draw_tray(self):
        """Icons under the quiz card: the mascot's favourite foods (with how
        many were found), the item box, and the settings gear. The box and
        the gear are buttons -- click or tap to open the settings screen."""
        label = ui.label_font(16)
        favorites = self.character["favorites"]
        fav_w = 26 * len(favorites) + label.size(f"×{self.favorites_found}")[0] + 8
        width = 12 + fav_w + 16 + 40 + 8 + 36 + 8
        tray = pygame.Rect(HUD_RIGHT_CARD.right - width, HUD_RIGHT_CARD.bottom + 6, width, HUD_TRAY_HEIGHT)
        ui.panel(self.screen, tray, radius=12)

        x = tray.x + 12
        for item_id in favorites:
            icon = get_icon(item_id, 24)
            self.screen.blit(icon, icon.get_rect(midleft=(x, tray.centery)))
            x += 26
        ui.text(self.screen, f"×{self.favorites_found}", label, (x + 2, tray.centery), anchor="midleft",
                color=(255, 170, 210))
        x += fav_w - 26 * len(favorites) + 6
        pygame.draw.line(self.screen, (*ui.PANEL_EDGE[:3],), (x, tray.y + 9), (x, tray.bottom - 9), 1)

        self._box_rect = pygame.Rect(x + 8, tray.y + 2, 40, tray.height - 4)
        ui.item_box_icon(self.screen, (self._box_rect.centerx - 2, self._box_rect.centery + 2), 24)
        held = sum(self.item_box.values())
        if held:
            ui.count_badge(self.screen, (self._box_rect.right - 6, self._box_rect.y + 7), held)

        self._gear_rect = pygame.Rect(self._box_rect.right + 6, tray.y + 2, 36, tray.height - 4)
        ui.gear(self.screen, self._gear_rect.center, 22)

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
            letter = ui.title_font(32).render("z", True, (200, 210, 255))
            letter.set_alpha(round(255 * (1 - t)))
            self.screen.blit(letter, (head[0] - self.camera_x + 8 + i * 6 + t * 14, head[1] - 10 - t * 46))

    # -- Companion box -----------------------------------------------------------

    @staticmethod
    def _wrap(text, font, width):
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

    def _fit_speech(self, text, width):
        """Wraps `text` at the largest companion font size that fits in two
        lines; anything still too long is trimmed with an ellipsis."""
        for size in SPEECH_FONT_SIZES:
            font = ui.body_font(size)
            lines = self._wrap(text, font, width)
            if len(lines) <= 2:
                return font, lines
        lines = lines[:2]
        while font.size(lines[1] + "…")[0] > width and len(lines[1]) > 1:
            lines[1] = lines[1][:-1]
        lines[1] = lines[1].rstrip() + "…"
        return font, lines

    def _draw_speech(self):
        """The companion's reaction to what just happened -- a box docked at
        the bottom that never blocks play and fades out by itself. A reaction
        with a vocabulary lesson shows as two pages."""
        speech = self.coach.speech
        if speech is None:
            return
        box = SPEECH_BOX
        fade = min(1.0, speech.seconds_left / 0.6)
        ui.panel(self.screen, box, bg=(16, 12, 28, 242), edge=(255, 214, 150, 220), radius=12, alpha=fade)

        # Portrait in its own little frame on the left.
        frame = pygame.Rect(box.x + 7, box.y + 7, box.height - 14, box.height - 14)
        pygame.draw.rect(self.screen, (44, 36, 66), frame, border_radius=9)
        draw_companion(self.screen, self.coach.companion["id"], frame.centerx, frame.centery, 46,
                       expression=speech.expression)

        # Name plate sitting on the box's top edge, RPG style.
        name = self.coach.companion["name"].upper()
        label = ui.label_font(16)
        plate = pygame.Rect(frame.right + 12, box.y - 11, label.size(name)[0] + 20, 20)
        ui.panel(self.screen, plate, bg=(255, 210, 110, 255), edge=(20, 14, 26, 255), radius=6)
        ui.text(self.screen, name, label, plate.center, color=ui.OUTLINE, outline=None, anchor="center")

        page = speech.page
        lesson = page == 1
        text_x, right = frame.right + 14, box.right - 22
        font, lines = self._fit_speech(speech.lines[page], right - text_x)
        color = ui.SKY if lesson else ui.CREAM
        line_h = font.get_height() - 2
        top = box.y + 12 + (box.height - 18 - line_h * len(lines)) // 2
        for i, line in enumerate(lines):
            ui.text(self.screen, line, font, (text_x, top + i * line_h), color=color, thickness=1)

        if len(speech.lines) > 1:  # page dots
            for i in range(2):
                pygame.draw.circle(self.screen, ui.GOLD if i == page else (110, 100, 120),
                                   (box.right - 12, box.y + 22 + i * 12), 3)

    # -- End-of-level screens ----------------------------------------------------

    def _dim(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        self.screen.blit(overlay, (0, 0))

    def _prompt(self, words, y):
        """A blinking "press a button" line at the bottom of a card."""
        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            ui.text(self.screen, words, ui.label_font(16), (SCREEN_WIDTH // 2, y), color=ui.CREAM, anchor="center")

    def _draw_game_over(self):
        self._dim()
        card = pygame.Rect(0, 0, 520, 250)
        card.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        ui.panel(self.screen, card, bg=(18, 14, 32, 235), radius=16)
        cx = card.centerx
        ui.text(self.screen, "GAME OVER", ui.title_font(48), (cx, card.y + 54), color=ui.RED, anchor="center",
                thickness=3)
        ui.text(self.screen, "FINAL SCORE", ui.label_font(16), (cx, card.y + 100), color=ui.GOLD, anchor="center")
        ui.text(self.screen, str(self.score), ui.title_font(32), (cx, card.y + 128), anchor="center")
        note = ("You fell asleep... grab a konbini snack next time!" if self.fell_asleep_flag
                else "Good try! Every question makes you stronger.")
        ui.text(self.screen, note, ui.body_font(18), (cx, card.y + 172), color=(190, 200, 255), anchor="center",
                thickness=1)
        self._prompt("PRESS ENTER", card.bottom - 26)

    def _draw_level_complete(self):
        self._dim()
        cx = SCREEN_WIDTH // 2
        answered = self.correct_count + self.wrong_count
        min_questions = required_question_count(self.level_number)
        needed = round(min_questions * BADGE_PASS_ACCURACY)

        ui.text(self.screen, f"LEVEL {self.level_number}", ui.label_font(16), (cx, 30), color=ui.GOLD,
                anchor="center")
        ui.text(self.screen, "STAGE CLEAR!", ui.title_font(48), (cx, 64), anchor="center", thickness=3)

        # The badge is the prize, so it gets the visual center -- greyed out
        # when it wasn't earned, so the player sees what they just missed.
        draw_badge(self.screen, cx, 172, 112, self.badge, earned=self.badge_earned)

        if self.badge_earned:
            headline, sub, color = f"Badge earned: {self.badge.name}", self.badge.caption, ui.GOLD
        else:
            headline = f"Badge locked: {self.badge.name}"
            sub = f"Answer at least {min_questions} with {needed} right to claim it -- so close!"
            color = ui.MUTED
        ui.text(self.screen, headline, ui.body_font(22), (cx, 252), color=color, anchor="center")
        ui.text(self.screen, sub, ui.body_font(16), (cx, 280), color=ui.CREAM, anchor="center", thickness=1)

        # Four stat tiles: label on top, number below.
        accuracy = f"{round(self.level_accuracy * 100)}%" if self.level_accuracy is not None else "-"
        tiles = [("SCORE", str(self.score)), ("QUIZ", f"{self.correct_count}/{answered}"),
                 ("ACCURACY", accuracy), ("NEXT", self.next_jlpt_level)]
        tile_w, gap = 168, 12
        x0 = cx - (len(tiles) * tile_w + (len(tiles) - 1) * gap) // 2
        for i, (name, value) in enumerate(tiles):
            tile = ui.panel(self.screen, (x0 + i * (tile_w + gap), 306, tile_w, 70), radius=10)
            ui.text(self.screen, name, ui.label_font(16), (tile.centerx, tile.y + 18), color=ui.GOLD, anchor="center")
            ui.text(self.screen, value, ui.title_font(32), (tile.centerx, tile.y + 46), anchor="center")

        ui.text(self.screen, f"Next up: {JLPT_DESCRIPTIONS[self.next_jlpt_level]}", ui.body_font(16),
                (cx, 394), color=ui.CREAM, anchor="center", thickness=1)
        extras = (f"STOMPED {self.stomps}     SNACKS {self.snacks_eaten}     FAVORITES {self.favorites_found}"
                  f"     GIFTS {self.gifts_opened}     SKIPPED {self.skipped_count}")
        ui.text(self.screen, extras, ui.label_font(16), (cx, 422), color=ui.SKY, anchor="center", thickness=1)
        self._prompt("PRESS ENTER TO CONTINUE", 456)

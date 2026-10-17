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
from kobito.adaptive import AdaptiveTutor
from kobito.difficulty import JLPT_DESCRIPTIONS, JLPT_LEVELS, MODE_ADAPTIVE, MODE_CHOOSE, MODE_RANDOM, next_jlpt_level
from kobito.companion_art import draw_companion
from kobito.entities.collectible import Collectible
from kobito.entities.enemy import FlyingEnemy
from kobito.entities.gift_box import GiftBox
from kobito.entities.player import Player
from kobito.entities.question_block import QuestionBlock
from kobito import save_game, ui
from kobito.hint_service import HintService
from kobito.item_art import get_icon
from kobito.item_coach import ItemCoach
from kobito.items import BIG_DRINKS, SMALL_SNACKS, get_item, roll_gift
from kobito.levels.level1 import build_level1
from kobito.levels import sky as sky_levels
from kobito.levels import underground as underground_levels
from kobito.levels.sky import build_sky
from kobito.levels.underground import build_underground
from kobito.questions import QuestionBank
from kobito.quiz_screen import QuizScreen
from kobito.settings_screen import PAGE_ITEMS, PAGE_MENU, RESULT_QUIT, SettingsScreen
from kobito.sky_background import SkyBackground
from kobito.underground_background import UndergroundBackground
from kobito.world import World

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

FADE_SECONDS = 0.35        # each half of a room change / respawn fade
BANNER_SECONDS = 3.0       # "SECRET AREA!" title when entering one
FALL_LIMIT_Y = SCREEN_HEIGHT + 24   # below this, the player has fallen out of the world
SPRING_SPEED = 1450.0      # a cloud spring's launch -- well off the top of the screen
SKY_ENTRY_SPEED = 950.0    # shooting up into a sky room from below
LAUNCH_SECONDS = 1.6       # how long a launch can take to clear the top before it fizzles

SPRING_RAINBOW = [(232, 72, 72), (250, 200, 60), (110, 200, 100), (80, 160, 230), (170, 110, 210), (255, 150, 200)]

# Every hidden room's look and words, underground and sky alike.
HIDDEN_STYLES = {**underground_levels.STYLES, **sky_levels.STYLES}

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
        badges=None,
        resume_state=None,
        difficulty_mode=MODE_CHOOSE,
        tutor=None,
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
        # How questions are picked: the chosen JLPT level ("choose"), the
        # AI tutor adapting to every answer ("adaptive", see
        # kobito/adaptive.py), or any level at random ("random"). The tutor
        # is shared by every level of the run, like the item box.
        self.difficulty_mode = difficulty_mode
        self.tutor = tutor if tutor is not None else (
            AdaptiveTutor(jlpt_level) if difficulty_mode == MODE_ADAPTIVE else None)
        game_input.get_joysticks()
        # None on desktop (see kobito.input.IS_WEB) -- a phone has no
        # keyboard/joystick, so this on-screen d-pad + jump button is
        # its only way to play.
        self.touch_controls = game_input.get_gameplay_touch_controls(self.screen)

        character = get_character(character_id)
        self.character = character
        self.theme_id = theme_id
        self.companion_id = companion_id
        level = build_level1(theme_id, level_number=level_number, favorites=character["favorites"])
        # The level's surface, plus any hidden underground rooms the player
        # has dropped into (built on first visit, keyed by pit index). Game's
        # platforms / enemies / collectibles / ... always mean the room the
        # player is in right now -- see the properties below.
        self.surface = World(level, Background(level.width_px, level.ground_y, level.ground_segments_px, level.theme))
        self.world = self.surface
        self.underground_worlds = {}
        self._underground_states = {}   # saved coins/enemies for rooms not yet rebuilt
        self.secrets_found = set()      # pit indices visited this level
        self.sky_worlds = {}            # ...and the same for the sky rooms, keyed by spring index
        self._sky_states = {}
        self.sky_found = set()
        self.launch = None              # (spring link, seconds left) while flying up off a spring

        self.player = Player(*level.player_start, character_id=character["id"], color=character["color"])
        # A "sprite group" is pygame's container for a batch of sprites; the
        # world's group holds everything drawn in that room (the goal is in
        # it but deliberately not in `platforms`, so it's visible without
        # being solid). The player joins whichever room it's in.
        self.all_sprites.add(self.player)

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
        self.fell_in_pit_flag = False
        self.pits_fallen = 0
        self.transition = None   # an in-progress fade, see _start_transition
        self.banner = None       # (title, subtitle, seconds left)
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
        self.badges = badges if badges is not None else []   # badge ids earned this run
        self.pending_settings = None   # page to open at the end of this frame
        self._box_rect = None          # HUD icons, clickable / tappable
        self._gear_rect = None
        if resume_state:
            self._restore(resume_state)

    # The room the player is in right now. Everything that handles
    # collisions, pickups and drawing goes through these.
    platforms = property(lambda self: self.world.platforms)
    question_blocks = property(lambda self: self.world.question_blocks)
    gift_boxes = property(lambda self: self.world.gift_boxes)
    enemies = property(lambda self: self.world.enemies)
    collectibles = property(lambda self: self.world.collectibles)
    goal = property(lambda self: self.world.goal)
    background = property(lambda self: self.world.background)
    all_sprites = property(lambda self: self.world.all_sprites)

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
                if not (self.game_over or self.level_complete):
                    self.save_progress()
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
        result = await SettingsScreen(self.screen, self.screen.copy(), self.item_box, start_page=page,
                                      on_save=self.save_progress).run()
        if result == RESULT_QUIT:
            self.running = False
        # Same reason as after a quiz: the menu's time shouldn't arrive as
        # one huge dt on the next frame.
        self.clock.tick(FPS)

    # -- Saving ----------------------------------------------------------------

    def _run_record(self, level_number=None, jlpt_level=None):
        return {
            "character_id": self.character["id"], "companion_id": self.companion_id, "theme_id": self.theme_id,
            "jlpt_level": jlpt_level or self.jlpt_level, "level_number": level_number or self.level_number,
            "score": self.score, "xp": self.xp,
            "item_box": dict(self.item_box), "badges": list(self.badges),
            "difficulty_mode": self.difficulty_mode,
            "tutor": self.tutor.to_state() if self.tutor is not None else None,
        }

    def snapshot(self):
        """Everything needed to drop the player back exactly here: where they
        stand, their power/lives/quiz counters, and which blocks, boxes,
        coins and enemies are already gone -- on the surface and in every
        hidden room visited. (Enemies still around restart from their spawn
        spot.) Saved while underground, the spot is just past the pit they
        dropped into: they continue on the surface and can drop in again."""
        if self.world.hidden:
            link = self.world.link
            spot = [link["return_x"] - self.player.rect.width // 2, self.surface.ground_y - self.player.rect.height]
        else:
            spot = [self.player.rect.x, self.player.rect.y]
        state = {
            "player": spot,
            "power": self.power, "lives": self.lives, "next_life_xp": self.next_life_xp,
            "correct": self.correct_count, "wrong": self.wrong_count, "skipped": self.skipped_count,
            "stomps": self.stomps, "snacks": self.snacks_eaten, "favorites": self.favorites_found,
            "gifts": self.gifts_opened, "asked_ids": sorted(self.asked_ids, key=str),
            "pits_fallen": self.pits_fallen, "secrets_found": sorted(self.secrets_found),
            "underground": {str(i): w.objects_state() for i, w in self.underground_worlds.items()},
            "sky_found": sorted(self.sky_found),
            "sky": {str(i): w.objects_state() for i, w in self.sky_worlds.items()},
        }
        state.update(self.surface.objects_state())
        return state

    def _restore(self, state):
        try:
            self.surface.restore_objects(state)
            self.player.rect.topleft = tuple(int(v) for v in state["player"])
            self.power = max(1, min(POWER_MAX, int(state.get("power", POWER_MAX))))
            self.lives = max(1, min(MAX_LIVES, int(state.get("lives", STARTING_LIVES))))
            self.next_life_xp = max(self.next_life_xp, int(state.get("next_life_xp", 0)))
            self.correct_count = int(state.get("correct", 0))
            self.wrong_count = int(state.get("wrong", 0))
            self.skipped_count = int(state.get("skipped", 0))
            self.stomps = int(state.get("stomps", 0))
            self.snacks_eaten = int(state.get("snacks", 0))
            self.favorites_found = int(state.get("favorites", 0))
            self.gifts_opened = int(state.get("gifts", 0))
            self.asked_ids = set(state.get("asked_ids", []))
            self.pits_fallen = int(state.get("pits_fallen", 0))
            self.secrets_found = {int(i) for i in state.get("secrets_found", [])}
            rooms = state.get("underground", {})
            self._underground_states = {int(k): v for k, v in rooms.items() if isinstance(v, dict)}
            self.sky_found = {int(i) for i in state.get("sky_found", [])}
            rooms = state.get("sky", {})
            self._sky_states = {int(k): v for k, v in rooms.items() if isinstance(v, dict)}
        except (KeyError, TypeError, ValueError):
            return  # a damaged spot just means starting the level fresh
        self.drowsy_warned = self.drowsy
        self.camera_x = max(0.0, self.player.rect.centerx - SCREEN_WIDTH / 2)
        # A moment of safety, in case an enemy is standing on the spot.
        self.invulnerable_timer = WAKE_INVULNERABILITY_SECONDS

    def save_progress(self):
        """Saves the run with the player's exact spot in this level. Returns
        True if it was written."""
        if self.game_over or self.level_complete:
            return False
        return save_game.save_run(self._run_record(), level=self.snapshot())

    async def _update(self, dt):
        if self.game_over or self.level_complete:
            return
        if self.transition:
            self._update_transition(dt)
            return

        self.clock_time += dt
        if self.banner:
            title, sub, left = self.banner
            self.banner = (title, sub, left - dt) if left > dt else None
        self._apply_power_effects(dt)
        self.player.update(dt, self.platforms)
        self.enemies.update(dt, self.platforms)
        for spring in self.world.springs:
            spring.update_squash(dt)
        self.background.update(dt)
        self.coach.update(dt)
        self._update_effects(dt)

        self._follow_camera()

        await self._check_question_blocks()
        self._check_gift_boxes()
        self._check_collectibles()
        if self.world.hidden:
            self._check_exit()
        else:
            self._check_goal()
            self._check_springs(dt)
            if self.transition:
                return
        if self.player.rect.top > FALL_LIMIT_Y:
            self._fell_out()
            return

        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self._check_enemy_contact(dt)

    def _follow_camera(self):
        # Keep the player roughly centered horizontally by shifting the
        # camera, but never scroll past either end of the room.
        target = self.player.rect.centerx - SCREEN_WIDTH / 2
        self.camera_x = max(0.0, min(target, self.world.width_px - SCREEN_WIDTH))

    # -- Pits, secret rooms and the way back up ---------------------------------

    def _fell_out(self):
        """The player dropped below the screen. Over a secret pit that's the
        way into a hidden room; anywhere else it's a fall -- one life."""
        if self.world.kind == "sky":
            # No floor up there: falling through the clouds just drifts you
            # back down to the surface -- the sky's own way down.
            self._start_transition(self._leave_hidden)
            return
        pit = None if self.world.hidden else self.world.secret_pit_at(self.player.rect.centerx)
        if pit is not None:
            self._start_transition(lambda: self._enter_underground(pit))
            return
        if self.world.underground:      # no holes down there, but never get stuck
            self._start_transition(lambda: self._place_player(self.world.entry_x, -self.player.rect.height))
            return

        self.pits_fallen += 1
        self.lives -= 1
        if self.lives <= 0:
            self.fell_in_pit_flag = True
            self.game_over = True
            return
        self._start_transition(self._respawn_after_fall)

    def _respawn_after_fall(self):
        x = self.world.ledge_before(self.player.rect.centerx)
        self._place_player(x, self.world.ground_y)
        self.invulnerable_timer = WAKE_INVULNERABILITY_SECONDS
        self._add_effect_text("-1 Life", (x, self.world.ground_y - 60), (255, 150, 150))
        self.coach.fell(self.power)

    def _place_player(self, x, bottom):
        self.player.rect.midbottom = (round(x), round(bottom))
        self.player.velocity_x = self.player.velocity_y = 0.0
        self._follow_camera()

    def _switch_world(self, world):
        self.all_sprites.remove(self.player)
        self.world = world
        self.all_sprites.add(self.player)
        self.effects = []

    def _underground_world(self, pit):
        index = pit["index"]
        if index not in self.underground_worlds:
            level, entry_x = build_underground(pit["style"], self.level_number, index, self.character["favorites"])
            background = UndergroundBackground(level.width_px, level.ground_y, pit["style"], entry_x, seed=index)
            world = World(level, background, kind="underground", style=pit["style"], entry_x=entry_x, link=pit)
            if index in self._underground_states:
                world.restore_objects(self._underground_states.pop(index))
            self.underground_worlds[index] = world
        return self.underground_worlds[index]

    def _enter_underground(self, pit):
        world = self._underground_world(pit)
        self._switch_world(world)
        # Drop in through the hole in the ceiling.
        self._place_player(world.entry_x, 0)
        spec = HIDDEN_STYLES[pit["style"]]
        self.banner = ("SECRET AREA!", f"{spec['jp']}  ·  {spec['name'].upper()}", BANNER_SECONDS)
        first_visit = pit["index"] not in self.secrets_found
        self.secrets_found.add(pit["index"])
        if first_visit:
            self.coach.secret(spec["name"], underground_levels.place_lesson(pit["style"]))

    # -- The way up: cloud springs and sky rooms --------------------------------

    def _check_springs(self, dt):
        """Landing on a cloud spring launches the player straight up; once
        they're off the top of the screen, the sky room fades in."""
        player = self.player
        for spring in self.world.springs:
            # Only a landing with the player's middle over the spring counts,
            # so the launch path straight up is always clear.
            if (player.velocity_y >= 0 and player.rect.colliderect(spring.rect)
                    and spring.rect.left <= player.rect.centerx <= spring.rect.right
                    and player.rect.bottom <= spring.rect.top + 18):
                player.velocity_y = -SPRING_SPEED
                player.on_ground = False
                spring.boing()
                self.launch = (spring.link, LAUNCH_SECONDS)
                self._add_effect_puff((spring.rect.centerx, spring.rect.top))
                break
        if self.launch:
            link, left = self.launch
            if player.rect.bottom < -30:
                self.launch = None
                self._start_transition(lambda: self._enter_sky(link))
            else:
                self.launch = (link, left - dt) if left > dt else None

    def _sky_world(self, link):
        index = link["index"]
        if index not in self.sky_worlds:
            level, entry_x = build_sky(link["style"], self.level_number, index, self.character["favorites"])
            world = World(level, SkyBackground(level.width_px, link["style"], seed=index), kind="sky",
                          style=link["style"], entry_x=entry_x, link=link)
            if index in self._sky_states:
                world.restore_objects(self._sky_states.pop(index))
            self.sky_worlds[index] = world
        return self.sky_worlds[index]

    def _enter_sky(self, link):
        world = self._sky_world(link)
        self._switch_world(world)
        # Shoot up from below the screen, through the first (one-way) cloud,
        # and land on it.
        self._place_player(world.entry_x, SCREEN_HEIGHT + 40)
        self.player.velocity_y = -SKY_ENTRY_SPEED
        spec = HIDDEN_STYLES[link["style"]]
        self.banner = ("SECRET SKY!", f"{spec['jp']}  ·  {spec['name'].upper()}", BANNER_SECONDS)
        first_visit = link["index"] not in self.sky_found
        self.sky_found.add(link["index"])
        if first_visit:
            self.coach.secret(spec["name"], sky_levels.place_lesson(link["style"]))

    # -- Leaving a hidden room ---------------------------------------------------

    def _check_exit(self):
        if self.player.rect.colliderect(self.goal.rect.inflate(-60, 0)):
            self._start_transition(self._leave_hidden)

    def _leave_hidden(self):
        """Back to the surface, just past the pit or spring that led in."""
        came_from_sky = self.world.kind == "sky"
        link = self.world.link
        self._switch_world(self.surface)
        self._place_player(link["return_x"], self.surface.ground_y)
        self.invulnerable_timer = 1.0
        if came_from_sky:
            self.coach.landed()
        else:
            self.coach.surface()

    def _start_transition(self, action):
        """Fades to black, runs `action` (move rooms / respawn) while the
        screen is dark, then fades back in. Play is paused meanwhile."""
        if self.transition is None:
            self.transition = {"t": 0.0, "phase": "out", "action": action}

    def _update_transition(self, dt):
        tr = self.transition
        tr["t"] += dt
        if tr["t"] < FADE_SECONDS:
            return
        if tr["phase"] == "out":
            tr["action"]()
            tr.update(phase="in", t=0.0)
        else:
            self.transition = None

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
        if self.tutor is not None:
            self.next_jlpt_level = self.tutor.estimated_level()
        self.badge_earned = self._badge_earned()
        if self.badge_earned and self.badge.id not in self.badges:
            self.badges.append(self.badge.id)
        # Autosave: a checkpoint at the start of the next level, so closing
        # the game on the "stage clear" card loses nothing.
        save_game.save_run(self._run_record(level_number=self.level_number + 1, jlpt_level=self.next_jlpt_level))

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
        elif item.group in ("rare", "treasure"):
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
        touched = self.player.touched
        for block in self.question_blocks:
            # A block whose question was just skipped waits until the player
            # has stepped away before it can be bumped again.
            if block.resting and block not in touched:
                block.resting = False
        for solid in touched:
            if isinstance(solid, QuestionBlock) and not solid.used and not solid.resting:
                await self._trigger_question(solid)
                break  # handle at most one block per frame

    def _next_question(self):
        bank = self.question_bank
        if self.tutor is not None:
            return self.tutor.pick(bank.questions, exclude=self.asked_ids)
        if self.difficulty_mode == MODE_RANDOM:
            return bank.random_question(jlpt=self.rng.choice(JLPT_LEVELS), exclude=self.asked_ids)
        return bank.random_question(jlpt=self.jlpt_level, exclude=self.asked_ids)

    async def _trigger_question(self, block):
        block.mark_used()
        # A box that was skipped earlier asks the same question again.
        question = block.pending_question or self._next_question()
        block.pending_question = None
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
            # Passed: nothing answered, nothing lost. The box stays a "?" box
            # holding the same question, so the player can come back to it.
            self.skipped_count += 1
            block.reopen()
            block.pending_question = question
            block.resting = True
            self._add_effect_text("Skipped -- come back later", (block.rect.centerx, block.rect.top), (210, 210, 225))
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
        if correct is not None and self.tutor is not None:
            # The tutor learns from every answer; the HUD shows the level it
            # now thinks suits the player.
            self.tutor.record(question, correct)
            self.jlpt_level = self.tutor.estimated_level()

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
        if not self.world.hidden:
            self._draw_pit_hints()
            self._draw_spring_hints()

        # Treasures pulse with a soft halo, so they stand out from the scenery.
        for pickup in self.collectibles:
            if pickup.item is not None and pickup.item.group == "treasure":
                pulse = 0.6 + 0.4 * math.sin(self.clock_time * 4)
                center = (pickup.rect.centerx - self.camera_x, pickup.rect.centery)
                halo = pygame.Surface((64, 64), pygame.SRCALPHA)
                for r in range(30, 6, -4):
                    pygame.draw.circle(halo, (255, 236, 150, round(70 * pulse * (1 - r / 32))), (32, 32), r)
                self.screen.blit(halo, (center[0] - 32, center[1] - 32))

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
            self._draw_banner()
            self._draw_hud()
            self._draw_speech()
        if self.transition:
            tr = self.transition
            amount = tr["t"] / FADE_SECONDS if tr["phase"] == "out" else 1 - tr["t"] / FADE_SECONDS
            fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade.fill((6, 4, 10))
            fade.set_alpha(round(255 * max(0.0, min(1.0, amount))))
            self.screen.blit(fade, (0, 0))
        if self.game_over:
            self._draw_game_over()
        elif self.level_complete:
            self._draw_level_complete()

        if self.touch_controls:
            self.touch_controls.draw(self.screen)

        pygame.display.flip()

    def _draw_pit_hints(self):
        """A secret pit gives itself away, if you look: NYC-manhole steam,
        a green sewer glow, or gold sparkles from the mine rise out of it."""
        for pit in self.surface.secret_pits:
            x0, x1 = pit["x0"] - self.camera_x, pit["x1"] - self.camera_x
            if x1 < -40 or x0 > SCREEN_WIDTH + 40:
                continue
            hint = HIDDEN_STYLES[pit["style"]]["hint"]
            width = x1 - x0
            # The pit looks deeper than an ordinary one: a dark, tinted shaft
            # fading in towards the bottom of the screen.
            ground = self.surface.ground_y
            depth = SCREEN_HEIGHT - ground
            shade = {"steam": (40, 40, 50), "glow": (20, 60, 36), "sparkle": (60, 40, 24)}[hint]
            hole = pygame.Surface((width, depth), pygame.SRCALPHA)
            for y in range(depth):
                pygame.draw.line(hole, (*shade, round(230 * (y / depth) ** 0.7)), (0, y), (width, y))
            self.screen.blit(hole, (x0, ground))
            layer = pygame.Surface((width + 80, 240), pygame.SRCALPHA)
            base = layer.get_height()
            for i in range(7):
                phase = (self.clock_time * 0.32 + i / 7) % 1.0
                px = 40 + 12 + (i * 37) % max(1, width - 24) + math.sin(phase * 6 + i) * 7
                py = base - phase * 190
                if hint == "steam":
                    r = round(8 + phase * 18)
                    pygame.draw.circle(layer, (226, 228, 236, round(190 * (1 - phase))), (px, py), r)
                elif hint == "glow":
                    pygame.draw.circle(layer, (90, 230, 120, round(220 * (1 - phase))), (px, py), 5)
                    pygame.draw.circle(layer, (220, 255, 220, round(200 * (1 - phase))), (px - 1, py - 1), 1)
                else:
                    a = round(255 * (1 - phase) * (0.6 + 0.4 * math.sin(self.clock_time * 9 + i)))
                    for dx, dy in ((6, 0), (0, 6)):
                        pygame.draw.line(layer, (240, 180, 40, a), (px - dx, py - dy), (px + dx, py + dy), 3)
            if hint == "glow":
                pygame.draw.ellipse(layer, (120, 255, 150, 50), (30, base - 40, width + 20, 60))
            self.screen.blit(layer, (x0 - 40, self.surface.ground_y + 70 - base))

    def _draw_spring_hints(self):
        """A cloud spring gives itself away with a little updraft rising off
        it: rainbow sparkles, crackling sparks, or twinkling stars."""
        for spring in self.surface.springs:
            sx = spring.rect.centerx - self.camera_x
            if not -60 < sx < SCREEN_WIDTH + 60:
                continue
            hint = HIDDEN_STYLES[spring.style]["hint"]
            for i in range(6):
                phase = (self.clock_time * 0.45 + i / 6) % 1.0
                px = sx - 22 + (i * 17) % 44 + math.sin(phase * 7 + i) * 4
                py = spring.rect.top - 4 - phase * 120
                fade = 1 - phase
                if hint == "rainbow":
                    color = SPRING_RAINBOW[i % len(SPRING_RAINBOW)]
                    pygame.draw.circle(self.screen, color, (px, py), max(1, round(3 * fade)))
                elif hint == "spark":
                    if int(self.clock_time * 12 + i) % 3:
                        pygame.draw.lines(self.screen, (255, 230, 90), False,
                                          [(px, py), (px + 3, py + 4), (px - 1, py + 6), (px + 2, py + 10)], 2)
                else:
                    size = max(1, round(4 * fade))
                    pygame.draw.line(self.screen, (255, 250, 200), (px - size, py), (px + size, py), 2)
                    pygame.draw.line(self.screen, (255, 250, 200), (px, py - size), (px, py + size), 2)
            # Wind streaks rushing upward.
            for i in range(3):
                phase = (self.clock_time * 1.2 + i / 3) % 1.0
                y = spring.rect.top - 10 - phase * 90
                pygame.draw.line(self.screen, (255, 255, 255), (sx - 18 + i * 18, y), (sx - 18 + i * 18, y - 14), 1)

    @property
    def secrets_total(self):
        return len(self.surface.secret_pits) + len(self.surface.springs)

    @property
    def secrets_total_found(self):
        return len(self.secrets_found) + len(self.sky_found)

    def _draw_banner(self):
        if not self.banner:
            return
        title, sub, left = self.banner
        card = pygame.Surface((620, 110), pygame.SRCALPHA)
        ui.text(card, title, ui.title_font(48), (310, 36), color=ui.GOLD, anchor="center", thickness=3)
        ui.text(card, sub, ui.label_font(16), (310, 84), anchor="center")
        card.set_alpha(round(255 * min(1.0, left / 0.6)))
        self.screen.blit(card, card.get_rect(center=(SCREEN_WIDTH // 2, 200)))

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
        mode = {MODE_ADAPTIVE: f"AI {self.jlpt_level}", MODE_RANDOM: "RANDOM"}.get(self.difficulty_mode, self.jlpt_level)
        words = f"LEVEL {self.level_number}  ·  {mode}"
        if self.world.hidden:
            words = f"SECRET  ·  {HIDDEN_STYLES[self.world.style]['name'].upper()}"
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
        if self.fell_asleep_flag:
            note = "You fell asleep... grab a konbini snack next time!"
        elif self.fell_in_pit_flag:
            note = "You fell into a pit... some pits hide a secret, though!"
        else:
            note = "Good try! Every question makes you stronger."
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
                 ("ACCURACY", accuracy),
                 ("NEXT", "MIX" if self.difficulty_mode == MODE_RANDOM else self.next_jlpt_level)]
        tile_w, gap = 168, 12
        x0 = cx - (len(tiles) * tile_w + (len(tiles) - 1) * gap) // 2
        for i, (name, value) in enumerate(tiles):
            tile = ui.panel(self.screen, (x0 + i * (tile_w + gap), 306, tile_w, 70), radius=10)
            ui.text(self.screen, name, ui.label_font(16), (tile.centerx, tile.y + 18), color=ui.GOLD, anchor="center")
            ui.text(self.screen, value, ui.title_font(32), (tile.centerx, tile.y + 46), anchor="center")

        next_up = {
            MODE_ADAPTIVE: f"Next up: the AI keeps adapting -- you're around {self.next_jlpt_level} "
                           f"({JLPT_DESCRIPTIONS[self.next_jlpt_level]})",
            MODE_RANDOM: "Next up: a random mix of N5-N1",
        }.get(self.difficulty_mode, f"Next up: {JLPT_DESCRIPTIONS[self.next_jlpt_level]}")
        ui.text(self.screen, next_up, ui.body_font(16),
                (cx, 394), color=ui.CREAM, anchor="center", thickness=1)
        extras = (f"STOMPED {self.stomps}     SNACKS {self.snacks_eaten}     FAVORITES {self.favorites_found}"
                  f"     GIFTS {self.gifts_opened}     SECRETS {self.secrets_total_found}/{self.secrets_total}")
        ui.text(self.screen, extras, ui.label_font(16), (cx, 422), color=ui.SKY, anchor="center", thickness=1)
        self._prompt("PRESS ENTER TO CONTINUE", 456)

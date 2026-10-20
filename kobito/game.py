import asyncio
import math
import random

import pygame

from kobito import audio, display, progress
from kobito import input as game_input
from kobito.background import Background
from kobito.characters import get_character
from kobito.badges import badge_for_level, draw_badge
from kobito.constants import (
    BADGE_PASS_ACCURACY,
    CORRECT_ANSWER_SCORE,
    FPS,
    IS_WEB,
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
    TILE_SIZE,
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
from kobito.entities.sun_shot import MAX_SHOTS, SunShot

SUN_POWER_SECONDS = 20.0   # how long a sunflower's power lasts (a new one refills it)
SUN_FLICKER_SECONDS = 3.0  # the glow flickers this long before it fades
from kobito import save_game, ui
from kobito.hint_service import HintService
from kobito.item_art import get_icon
from kobito.item_coach import ItemCoach
from kobito.items import BIG_DRINKS, ITEMS, ROLES, SMALL_SNACKS, benefits, get_item, roll_gift
from kobito.levels.level1 import build_level1
from kobito.levels import sky as sky_levels
from kobito.levels import underground as underground_levels
from kobito.levels.sky import build_sky
from kobito.levels.underground import build_underground
from kobito.profile import (EXP_BADGE, EXP_CLEAR, EXP_CORRECT, EXP_ITEM, EXP_TEST, YEN_BADGE, YEN_CLEAR,
                            YEN_COIN, YEN_CORRECT)
from kobito.questions import QuestionBank, shuffled
from kobito.quiz_screen import QuizScreen
from kobito.settings_screen import PAGE_ITEMS, PAGE_MENU, RESULT_QUIT, SettingsScreen
from kobito.sky_background import SkyBackground
from kobito.stage_end_screens import LuckyDrawScreen, ResultsScreen, ReviewScreen, TileScreen, roll_prize
from kobito.stage_test import build_test, learned_words, word_from_item, word_from_place
from kobito.underground_background import UndergroundBackground
from kobito.toasts import Toasts
from kobito.wardrobe import GEAR, HEAD
from kobito.world import World

OVERLAY = (8, 6, 16, 175)
BLINK_INTERVAL_SECONDS = 0.1
CONTINUE_KEYS = (pygame.K_RETURN, pygame.K_SPACE)
SETTINGS_KEYS = (pygame.K_ESCAPE, pygame.K_p)
SETTINGS_BUTTONS = (game_input.BACK, game_input.START)

# HUD layout (see _draw_hud). Two cards in the top corners -- the left one
# is "you" (score, lives, power, XP), the right one is "the lesson" (quiz
# progress toward the badge) -- with a small tray of icons under it.
HUD_LEFT_CARD = pygame.Rect(10, 10, 286, 142)
EXP_FILL = (255, 196, 110)
EIYO_BOOST_SECONDS = 15.0     # the konbini's energy drink
COMBO_FROM = 3                # right answers in a row before the combo bonus kicks in...
COMBO_BONUS = 10              # ...worth this many points per step (capped)
COMBO_BONUS_MAX = 60
HUD_RIGHT_CARD = pygame.Rect(SCREEN_WIDTH - 10 - 262, 10, 262, 104)
HUD_TRAY_HEIGHT = 40

POWER_PIP = (13, 14)   # width, height of one power pip
POWER_OK = (96, 214, 120)
POWER_LOW = (240, 86, 86)
POWER_EMPTY = (60, 56, 76)
XP_FILL = (150, 205, 255)
BOOST_SPEED_SCALE = 1.25
# Bottom-LEFT corner, in the strip under the ground line, so it never covers
# the player (who's usually mid-screen) or the play area. In the web build it
# starts just right of the on-screen left/right buttons.
SPEECH_BOX = pygame.Rect(196 if IS_WEB else 10, SCREEN_HEIGHT - 60, 420, 56)
SPEECH_FONT_SIZES = (19, 17, 15)   # largest that fits in two lines wins

MAX_GUARD = 5              # STRENGTH items stack up to this many blocked hits
STAGE_TUNES = 3            # each world's music comes in this many versions, one per stage
FADE_SECONDS = 0.35        # each half of a room change / respawn fade
BANNER_SECONDS = 3.0       # "SECRET AREA!" title when entering one
FALL_LIMIT_Y = SCREEN_HEIGHT + 24   # below this, the player has fallen out of the world
SPRING_SPEED = 1450.0      # a cloud spring's launch -- well off the top of the screen
SKY_ENTRY_SPEED = 950.0    # shooting up into a sky room from below
LAUNCH_SECONDS = 1.6       # how long a launch can take to clear the top before it fizzles
PARACHUTE_START_Y = -10    # down from the sky: the chute opens just above the screen (feet y)
ROPE_TOP_EXIT = 40         # underground: climb the rope until your feet are this high -- out!
CLIMB_OUT_SECONDS = 0.7    # back on the surface: the hop up out of the pit...
CLIMB_OUT_DEPTH = 70       # ...from this far down in it...
CLIMB_OUT_HOP = 90         # ...arcing this high over the edge

SPRING_RAINBOW = [(232, 72, 72), (250, 200, 60), (110, 200, 100), (80, 160, 230), (170, 110, 210), (255, 150, 200)]

# Passing a stage takes required_question_count() answers (right or wrong).
# This far before the finish the companion reminds the player if they're
# short, and the progress line marks the ? boxes still open.
FINISH_WARN_DISTANCE = 30 * TILE_SIZE
FINISH_PUSHBACK = 3 * TILE_SIZE

# The mini-map under the level pill: a thin line from start to finish.
MINIMAP_W = 200
MINIMAP_X = SCREEN_WIDTH // 2 - MINIMAP_W // 2
MINIMAP_Y = 50

# Every hidden room's look and words, underground and sky alike.
HIDDEN_STYLES = {**underground_levels.STYLES, **sky_levels.STYLES}

# Outcomes Game.run() can return, telling main.py what to do next.
OUTCOME_QUIT = "quit"
OUTCOME_ADVANCE = "advance"

# The Stage Test after the castle: XP per right answer, and the XP a
# multiple-choice question shows (and pays) during the test.
TEST_BONUS_XP = 10

# Question variety: the next question is never the same kind as the last
# RECENT_CATEGORIES asked, and the run remembers up to HISTORY_SIZE
# question ids so each level favours ones you haven't met yet.
RECENT_CATEGORIES = 2
HISTORY_SIZE = 600


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
        question_history=None,
        profile=None,
    ):
        pygame.init()
        self.screen = display.screen()
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
        self.climb_out = None           # the hop up out of a pit after climbing a rope, see _leave_hidden
        self._finish_warned = None      # the shortfall last reminded about near the finish
        self._gate_said_at = -10.0      # when the castle last turned the player back
        # For the end-of-stage review: every question asked this level, in
        # order (id -> {"question", "chosen", "result"}), and the items picked up.
        self.quiz_log = {}
        self.level_items = []
        self.pending_stage_end = False   # set when the player continues past the clear card

        # Ability level, 円 and wardrobe -- kept across runs (kobito/profile.py).
        self.profile = profile if profile is not None else save_game.load_profile()
        self.player = Player(*level.player_start, character_id=character["id"], color=character["color"],
                             worn=self.profile.worn(),
                             perks={GEAR[g].perk for g in self.profile.worn() if GEAR[g].perk})
        self.guard_left = 1 if self.profile.perk("guard") else 0   # kabuto: one blocked hit per stage
        self.toasts = Toasts(self.profile)   # trophies and missions pop up here (kobito/progress.py)
        self.combo = 0                       # right answers in a row
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
        # Every question asked this run, oldest first -- shared with main.py
        # (like the item box) so later levels favour questions not seen yet.
        self.question_history = question_history if question_history is not None else []
        self.recent_categories = []
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
        # Sun power (from eating a sunflower): the run button throws sunballs.
        self.sun_power = False
        self.sun_time_left = 0.0
        self.shots = pygame.sprite.Group()
        self.sun_throws = 0   # the "X THROW" prompt shows until the first throw
        self.sun_gained_at = -10.0
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
        else:
            self._use_boosts()

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

    def _track(self):
        """The music for the room the player is in: each secret-room style
        has its own tune, and each world three -- stage 1 plays the first,
        stage 2 the second, stage 3 the third, then round again
        (tools/make_audio.py, stage_variants)."""
        if self.world.hidden:
            return self.world.style
        variant = (self.level_number - 1) % STAGE_TUNES
        return self.theme_id if variant == 0 else audio.pick(f"{self.theme_id}_{variant + 1}", self.theme_id)

    async def run(self):
        audio.music(self._track())
        while self.running:
            # dt = seconds since last frame. Using it to scale movement
            # (instead of moving a fixed number of pixels/frame) keeps
            # speeds consistent even if the frame rate dips.
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            if self.pending_settings:
                await self._open_settings(self.pending_settings)
                continue
            if self.pending_stage_end:
                await self._stage_end()
                break
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
        for event in game_input.events():
            if event.type == pygame.QUIT:
                if not (self.game_over or self.level_complete):
                    self.save_progress()
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.game_over and event.key in CONTINUE_KEYS + SETTINGS_KEYS:
                    self.running = False
                elif event.key in SETTINGS_KEYS and not self.pending_settings:
                    audio.play("pause")
                    self.pending_settings = PAGE_MENU
                elif self.level_complete and event.key in CONTINUE_KEYS:
                    self.pending_stage_end = True

            game_input.handle_hotplug(event)

            if event.type == pygame.JOYBUTTONDOWN:
                if self.game_over and event.button in game_input.CONFIRM_BUTTONS + SETTINGS_BUTTONS:
                    self.running = False
                elif self.level_complete and event.button in game_input.CONFIRM_BUTTONS:
                    self.pending_stage_end = True
                elif event.button in SETTINGS_BUTTONS and not self.pending_settings:
                    audio.play("pause")
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
                    self.pending_stage_end = True

    async def _open_settings(self, page):
        """Pauses the level under the settings menu. Quit there ends the
        run; otherwise play picks up exactly where it stopped."""
        self.pending_settings = None
        self._draw()
        result = await SettingsScreen(self.screen, self.screen.copy(), self.item_box, start_page=page,
                                      on_save=self.save_progress, lesson_log=self._lesson_log).run()
        if result == RESULT_QUIT:
            self.running = False
        # Same reason as after a quiz: the menu's time shouldn't arrive as
        # one huge dt on the next frame.
        self.clock.tick(FPS)

    # -- Ability level, 円 and konbini boosts ------------------------------------

    def _gain_exp(self, amount):
        """Study EXP toward the ability level; a level-up gets a banner and
        names whatever costume it unlocked."""
        before = self.profile.level
        unlocked = self.profile.add_exp(amount)
        level = self.profile.level
        if level == before:
            return
        progress.check_trophies(self.profile)
        audio.play("levelup")
        if unlocked:
            gear = unlocked[-1]
            sub = f"NEW {('COSTUME' if gear.slot == HEAD else 'ACCESSORY')}: {gear.name.upper()} ({gear.jp})"
            self.coach.say(f"Level {level}! New: {gear.name} -- {gear.jp} ({gear.reading}). "
                           f"Try it on at home!", "happy", seconds=6.0)
        else:
            sub = "YOUR STUDY IS PAYING OFF"
        self.banner = (f"LEVEL UP!  Lv {level}", sub, BANNER_SECONDS)

    def _use_boosts(self):
        """Konbini boosts bought before this stage kick in now."""
        boosts = self.profile.take_boosts()
        where = (self.player.rect.centerx, self.player.rect.top)
        if "omamori" in boosts:
            self.lives = min(MAX_LIVES, self.lives + 1)
            self._add_effect_text("お守り +1 Life", where, (255, 150, 150))
        if "sun_seeds" in boosts:
            self._gain_sun_power(where)
        if "eiyo_drink" in boosts:
            self.boost_timer = EIYO_BOOST_SECONDS
            self._add_effect_text("SPEED!", (where[0], where[1] - 24), (170, 255, 190))
        if "protein_bar" in boosts:
            self.guard_left = min(MAX_GUARD, self.guard_left + 2)
            self._add_effect_text("GUARD ×2", (where[0], where[1] - 48), (255, 190, 130))

    def _lesson_log(self):
        """What the pause menu's lesson log shows: this level's questions so
        far and the words met (items picked up, secret places found)."""
        entries = list(self.quiz_log.values())
        items = [get_item(item_id) for item_id in dict.fromkeys(self.level_items)]
        return self.level_number, entries, learned_words(entries, items, self._places_found())

    # -- Saving ----------------------------------------------------------------

    def _run_record(self, level_number=None, jlpt_level=None):
        return {
            "character_id": self.character["id"], "companion_id": self.companion_id, "theme_id": self.theme_id,
            "jlpt_level": jlpt_level or self.jlpt_level, "level_number": level_number or self.level_number,
            "score": self.score, "xp": self.xp,
            "item_box": dict(self.item_box), "badges": list(self.badges),
            "difficulty_mode": self.difficulty_mode,
            "tutor": self.tutor.to_state() if self.tutor is not None else None,
            "question_history": list(self.question_history),
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
        elif self.climb_out:
            spot = [self.climb_out["to"] - self.player.rect.width // 2, self.surface.ground_y - self.player.rect.height]
        else:
            spot = [self.player.rect.x, self.player.rect.y]
        state = {
            "player": spot,
            "power": self.power, "lives": self.lives, "next_life_xp": self.next_life_xp,
            "correct": self.correct_count, "wrong": self.wrong_count, "skipped": self.skipped_count,
            "stomps": self.stomps, "snacks": self.snacks_eaten, "favorites": self.favorites_found,
            "gifts": self.gifts_opened, "asked_ids": sorted(self.asked_ids, key=str),
            "pits_fallen": self.pits_fallen, "secrets_found": sorted(self.secrets_found),
            "sun_power": self.sun_power, "sun_time_left": round(self.sun_time_left, 2),
            "underground": {str(i): w.objects_state() for i, w in self.underground_worlds.items()},
            "sky_found": sorted(self.sky_found),
            "sky": {str(i): w.objects_state() for i, w in self.sky_worlds.items()},
            "quiz_log": [{"id": e["question"]["id"], "result": e["result"],
                          "chosen": None if e["chosen"] is None else e["question"]["choices"][e["chosen"]]}
                         for e in self.quiz_log.values()],
            "level_items": list(self.level_items),
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
            self.sun_power = bool(state.get("sun_power", False))
            self.sun_time_left = float(state.get("sun_time_left", SUN_POWER_SECONDS)) if self.sun_power else 0.0
            self.secrets_found = {int(i) for i in state.get("secrets_found", [])}
            rooms = state.get("underground", {})
            self._underground_states = {int(k): v for k, v in rooms.items() if isinstance(v, dict)}
            self.sky_found = {int(i) for i in state.get("sky_found", [])}
            rooms = state.get("sky", {})
            self._sky_states = {int(k): v for k, v in rooms.items() if isinstance(v, dict)}
            self.level_items = [i for i in state.get("level_items", []) if i in ITEMS]
            self._restore_quiz_log(state.get("quiz_log", []))
        except (KeyError, TypeError, ValueError):
            return  # a damaged spot just means starting the level fresh
        self.drowsy_warned = self.drowsy
        self.camera_x = max(0.0, self.player.rect.centerx - SCREEN_WIDTH / 2)
        # A moment of safety, in case an enemy is standing on the spot.
        self.invulnerable_timer = WAKE_INVULNERABILITY_SECONDS

    def _restore_quiz_log(self, rows):
        by_id = {q["id"]: q for q in self.question_bank.questions}
        for row in rows:
            question = by_id.get(row.get("id"))
            if question is None or row.get("result") not in ("right", "wrong", "skipped"):
                continue
            chosen = row.get("chosen")
            chosen = question["choices"].index(chosen) if chosen in question["choices"] else None
            self.quiz_log[question["id"]] = {"question": question, "chosen": chosen, "result": row["result"]}

    def save_progress(self):
        """Saves the run with the player's exact spot in this level. Returns
        True if it was written."""
        if self.game_over or self.level_complete:
            return False
        return save_game.save_run(self._run_record(), level=self.snapshot(), profile=self.profile)

    async def _update(self, dt):
        if self.game_over or self.level_complete:
            return
        if self.transition:
            self._update_transition(dt)
            return

        self.clock_time += dt
        if self.climb_out:
            self._update_climb_out(dt)
            self.background.update(dt)
            self.coach.update(dt)
            self._update_effects(dt)
            return
        if self.banner:
            title, sub, left = self.banner
            self.banner = (title, sub, left - dt) if left > dt else None
        self._apply_power_effects(dt)
        self.player.update(dt, self.platforms)
        if self.player.chute_landed:
            self._chute_landed()
        self.enemies.update(dt, self.platforms)
        self._update_sun(dt)
        for spring in self.world.springs:
            spring.update_squash(dt)
        for block in self.question_blocks:
            if abs(block.rect.centerx - self.player.rect.centerx) < SCREEN_WIDTH:
                block.animate(self.clock_time)
        self.background.update(dt)
        self.coach.update(dt)
        self.toasts.update(dt)
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

    # -- Sun power ---------------------------------------------------------------

    def _update_sun(self, dt):
        """With sun power, a fresh press of the run button throws a sunball
        (at most MAX_SHOTS at once); sunballs defeat the enemies they hit."""
        player = self.player
        if self.sun_power:
            self.sun_time_left -= dt
            if self.sun_time_left <= 0:
                self.sun_power = False
                self._add_effect_text("Sun power faded", (player.rect.centerx, player.rect.top), (255, 200, 120))
        if player.fire_requested and self.sun_power and len(self.shots) < MAX_SHOTS:
            direction = 1 if player.facing_right else -1
            self.shots.add(SunShot(player.rect.centerx + direction * 18, player.rect.centery - 4, direction))
            audio.play("throw")
            self.sun_throws += 1
        self.shots.update(dt, self.platforms)
        for shot in list(self.shots):
            enemy = pygame.sprite.spritecollideany(shot, self.enemies)
            if enemy is not None:
                shot.kill()
                self._zap(enemy)
            elif not -60 < shot.rect.centerx - self.camera_x < SCREEN_WIDTH + 60:
                shot.kill()

    def _zap(self, enemy):
        where = (enemy.rect.centerx, enemy.rect.top)
        enemy.kill()
        audio.play("zap")
        progress.record(self.profile, "stomps")
        self.stomps += 1
        self.score += STOMP_SCORE
        self._add_xp(STOMP_GAUGE)
        self._add_effect_text(f"+{STOMP_SCORE}", where, (255, 210, 110))
        self._add_effect_puff(where)

    def _gain_sun_power(self, where):
        first_time = not self.sun_power
        self.sun_power = True
        self.sun_time_left = SUN_POWER_SECONDS
        self.sun_gained_at = self.clock_time
        self._add_effect_text("SUN POWER!", where, (255, 190, 60))
        return first_time

    def _follow_camera(self):
        # Keep the player roughly centered horizontally by shifting the
        # camera, but never scroll past either end of the room.
        target = self.player.rect.centerx - SCREEN_WIDTH / 2
        self.camera_x = max(0.0, min(target, self.world.width_px - SCREEN_WIDTH))

    # -- Pits, secret rooms and the way back up ---------------------------------

    def _fell_out(self):
        """The player dropped below the screen. Over a secret pit that's the
        way into a hidden room; anywhere else it's a fall -- one life."""
        if self.world.hidden:
            # Secret stages are a bonus, never a trap: falling through the
            # clouds or off a ledge underground just takes you back up to
            # the main stage, no life lost.
            self._start_transition(self._leave_hidden)
            return
        pit = self.world.secret_pit_at(self.player.rect.centerx)
        if pit is not None:
            self._start_transition(lambda: self._enter_underground(pit))
            return

        self.pits_fallen += 1
        self.lives -= 1
        audio.play("fall")
        if self.lives <= 0:
            self.fell_in_pit_flag = True
            self._game_over()
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
        self.shots.empty()
        self.all_sprites.remove(self.player)
        self.world = world
        self.all_sprites.add(self.player)
        # Underground, the room's goal is the rope back up (kobito/entities/rope.py).
        self.player.rope = world.goal.rect if world.underground else None
        self.player.on_rope = self.player.parachute = False
        self.climb_out = None
        self.effects = []
        audio.play("warp")
        audio.music(self._track())

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
            self.coach.secret(spec["name"], underground_levels.place_lesson(pit["style"]),
                              tip="The way out is the way in: climb the rope back up! のぼる (noboru) = to climb.")
            progress.record(self.profile, "secrets")

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
                audio.play("spring")
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
            self.coach.secret(spec["name"], sky_levels.place_lesson(link["style"]),
                              tip="Fall off a cloud or take the 出口 sign -- a パラシュート (parachute) brings you down.")
            progress.record(self.profile, "secrets")

    # -- Leaving a hidden room ---------------------------------------------------

    def _check_exit(self):
        """Sky: walk into the way-down sign. Underground: climb the rope you
        fell in by, right up through the hole in the ceiling."""
        if self.world.underground:
            if self.player.on_rope and self.player.rect.bottom < ROPE_TOP_EXIT:
                self._start_transition(self._leave_hidden)
        elif self.player.rect.colliderect(self.goal.rect.inflate(-60, 0)):
            self._start_transition(self._leave_hidden)

    def _leave_hidden(self):
        """Back to the main stage. From the sky you float down under a
        parachute just before the spring; from underground you climb up out
        of the pit you fell into and hop onto the far edge."""
        came_from_sky = self.world.kind == "sky"
        link = self.world.link
        self._switch_world(self.surface)
        if came_from_sky:
            self._place_player(link["return_x"], PARACHUTE_START_Y)
            self.player.parachute = True
            self.invulnerable_timer = 1.0
            audio.play("flap")
        else:
            pit_x = (link["x0"] + link["x1"]) / 2
            self._place_player(pit_x, self.surface.ground_y + CLIMB_OUT_DEPTH)
            self.climb_out = {"t": 0.0, "from": pit_x, "to": link["return_x"]}
            self.invulnerable_timer = CLIMB_OUT_SECONDS + 1.0
            self.coach.surface()

    def _update_climb_out(self, dt):
        """Scripted hop up out of the pit onto the ground past it."""
        c = self.climb_out
        c["t"] += dt
        k = min(1.0, c["t"] / CLIMB_OUT_SECONDS)
        ground = self.surface.ground_y
        x = c["from"] + (c["to"] - c["from"]) * k
        # Straight up out of the hole first, then an arc over the edge.
        bottom = ground + CLIMB_OUT_DEPTH * (1 - k) - CLIMB_OUT_HOP * 4 * k * (1 - k)
        self._place_player(x, bottom)
        self.player.on_ground = False
        self.player.velocity_x = 1 if c["to"] >= c["from"] else -1   # faces the way it hops
        self.player._update_animation(dt)
        if k >= 1.0:
            self.climb_out = None
            self._add_effect_puff((round(x), ground))
            audio.play("stomp", 0.6)

    def _chute_landed(self):
        player = self.player
        player.chute_landed = False
        self.invulnerable_timer = max(self.invulnerable_timer, 1.0)
        self._add_effect_puff(player.rect.midbottom)
        audio.play("stomp", 0.6)
        self.coach.say("パラシュート (parachute)... 着地 (ちゃくち, chakuchi) = landing!", "happy", seconds=4.0)

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

    @property
    def answered(self):
        return self.correct_count + self.wrong_count

    @property
    def answers_needed(self):
        """How many more questions must be answered to pass the stage."""
        return max(0, required_question_count(self.level_number) - self.answered)

    def _open_blocks_behind(self):
        return sum(1 for b in self.surface.question_blocks if not b.used and b.rect.centerx < self.player.rect.centerx)

    def _finish_line(self, need, at_gate=False):
        """What the companion says when the player nears (or reaches) the
        finish without enough answers -- short enough for the two-line
        bubble."""
        plural = "s" if need > 1 else ""
        where = "Head back to the ? boxes!" if self._open_blocks_behind() else "Find a ? box!"
        if at_gate:
            return f"Not yet! {need} more answer{plural} to pass. {where}"
        return f"Finish ahead! You need {need} more answer{plural} to pass. {where}"

    def _check_finish_reminder(self):
        """Near the finish without enough answers: say so, once per shortfall."""
        need = self.answers_needed
        near = self.goal.rect.left - self.player.rect.centerx < FINISH_WARN_DISTANCE
        if need and near and self._finish_warned != need:
            self._finish_warned = need
            self.coach.say(self._finish_line(need), "talking", seconds=6.0)

    def _check_goal(self):
        self._check_finish_reminder()
        if self.level_complete or not self.player.rect.colliderect(self.goal.rect):
            return
        need = self.answers_needed
        if need:
            # The castle won't let them in yet: a step back, and a reminder.
            self._place_player(self.goal.rect.left - FINISH_PUSHBACK, self.surface.ground_y)
            self._finish_warned = need     # and the map marks the open ? boxes
            if self.clock_time - self._gate_said_at > 2.0:
                self._gate_said_at = self.clock_time
                audio.play("gate")
                self.coach.say(self._finish_line(need, at_gate=True), "sympathetic", seconds=6.0)
                self._add_effect_text(f"{need} more to answer!", (self.goal.rect.left, self.goal.rect.top - 10),
                                      (255, 206, 70))
            return

        self.level_complete = True
        audio.stop_music()
        audio.play("clear")
        self.next_jlpt_level, self.level_accuracy = next_jlpt_level(
            self.jlpt_level, self.correct_count, self.wrong_count
        )
        if self.tutor is not None:
            self.next_jlpt_level = self.tutor.estimated_level()
        self.badge_earned = self._badge_earned()
        if self.badge_earned and self.badge.id not in self.badges:
            self.badges.append(self.badge.id)
        self.profile.add_yen(YEN_CLEAR + (YEN_BADGE if self.badge_earned else 0))
        self._gain_exp(EXP_CLEAR + (EXP_BADGE if self.badge_earned else 0))
        progress.record(self.profile, "stages")
        if self.badge_earned:
            progress.record(self.profile, "badges")
        progress.record_best(self.profile, "best_score", self.score)
        # Autosave: a checkpoint at the start of the next level, so closing
        # the game on the "stage clear" card loses nothing.
        save_game.save_run(self._run_record(level_number=self.level_number + 1, jlpt_level=self.next_jlpt_level),
                           profile=self.profile)

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
                audio.play("oneup")
                self.lives = min(MAX_LIVES, self.lives + 1)
                self._add_effect_text("+1 Life", where, (255, 150, 150))
            else:
                audio.play("coin")
                self.score += pickup.value
                self._add_xp(pickup.value)
                self.profile.add_yen(YEN_COIN)
                progress.record(self.profile, "coins")

    def _collect_item(self, item, where, from_gift=False):
        """Applies one item -- score, power, and its role: SKILL (study EXP),
        STRENGTH (guard against hits), SPEED, LIFE, LUCKY (円) or SUN (see
        kobito/items.py) -- then has the companion react and teach the word."""
        was_sleepy = self.drowsy
        self.item_box[item.id] = self.item_box.get(item.id, 0) + 1
        self.level_items.append(item.id)
        self._gain_exp(EXP_ITEM)
        progress.record(self.profile, "sunflowers" if item.group == "power" else "items")
        self.score += item.score
        self._add_xp(item.score)

        before = self.power
        self._set_power(POWER_MAX if item.full_power else self.power + item.power)
        gained = self.power - before
        if item.life:
            self.lives = min(MAX_LIVES, self.lives + item.life)
        if item.boost_seconds:
            self.boost_timer = max(self.boost_timer, item.boost_seconds)
        if item.guard:
            self.guard_left = min(MAX_GUARD, self.guard_left + item.guard)
        if item.yen:
            self.profile.add_yen(item.yen)
        if item.exp:
            self._gain_exp(item.exp)

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

        self._add_effect_text(item.name, where, color)
        # What it did for you, in the colour of its role, just under the name.
        tags = [t for t in benefits(item) if not t.endswith("POWER") or t == "SUN POWER"]
        if gained:
            tags.insert(0, f"+{gained} POWER")
        if tags:
            self._add_effect_text("  ".join(tags), (where[0], where[1] + 22), ROLES[item.role][1])
        if from_gift:
            self._add_effect_icon(item.id, where)
        audio.play("powerup" if item.group == "power" else "item")
        if item.group == "power":
            self.coach.power_up(item, first_time=self._gain_sun_power(where))
        else:
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
        audio.play("gift")
        progress.record(self.profile, "gifts")
        self.gifts_opened += 1
        top = (box.rect.centerx, box.rect.top)
        gift = roll_gift(self.rng, self.character["favorites"], sleepy=self.drowsy)
        if gift["kind"] == "coins":
            earned = gift["coins"] * 5
            self.profile.add_yen(gift["coins"] * YEN_COIN)
            progress.record(self.profile, "coins", gift["coins"])
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
            audio.play("oneup")
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
            return self.tutor.pick(bank.questions, exclude=self.asked_ids, avoid_categories=self.recent_categories)
        jlpt = self.rng.choice(JLPT_LEVELS) if self.difficulty_mode == MODE_RANDOM else self.jlpt_level
        return bank.pick(jlpt, exclude=self.asked_ids, history=self.question_history,
                         recent_categories=self.recent_categories, rng=self.rng)

    def _remember_question(self, question):
        history = self.question_history
        if question["id"] in history:
            history.remove(question["id"])
        history.append(question["id"])
        del history[:-HISTORY_SIZE]
        self.recent_categories = (self.recent_categories + [question["category"]])[-RECENT_CATEGORIES:]

    async def _trigger_question(self, block):
        block.mark_used()
        audio.play("block")
        # A box that was skipped earlier asks the same question again.
        # Choices are shuffled every time a question is asked, so the right
        # answer isn't always in the same slot.
        question = block.pending_question or shuffled(self._next_question(), self.rng)
        block.pending_question = None
        self.asked_ids.add(question["id"])
        self._remember_question(question)
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
        # The quiz's own companion box takes over from any item chatter.
        self.coach.speech = None
        self._draw()
        background = self.screen.copy()
        anchor_rect = block.rect.move(-self.camera_x, 0)

        quiz = QuizScreen(
            self.screen,
            question,
            background=background,
            anchor_rect=anchor_rect,
            hint_service=self.hint_service,
            points=points,
            penalty=penalty,
        )
        audio.duck(True)
        correct = await quiz.run()
        audio.duck(False)
        self._log_answer(question, quiz.selected, correct)

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
            self.profile.add_yen(YEN_CORRECT)
            self._gain_exp(EXP_CORRECT)
            self.combo += 1
            if self.combo >= COMBO_FROM:
                # A streak of right answers is worth a growing bonus.
                bonus = min(COMBO_BONUS_MAX, COMBO_BONUS * (self.combo - COMBO_FROM + 1))
                self.score += bonus
                self._add_effect_text(f"COMBO x{self.combo}!  +{bonus}", (block.rect.centerx, block.rect.top - 22),
                                      (255, 150, 60))
            progress.record(self.profile, "answered")
            progress.record(self.profile, "correct")
            progress.record_best(self.profile, "best_combo", self.combo)
        else:
            # Costs XP but not a life -- the badge only asks for 70%
            # accuracy, so getting a few wrong has to be survivable.
            self._lose_xp(penalty)
            self.wrong_count += 1
            self.combo = 0
            progress.record(self.profile, "answered")
        if correct is not None:
            block.mark_answered(correct)
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

    def _log_answer(self, question, chosen, correct):
        """Remembers how a question went, for the end-of-stage review. A
        skip never overwrites an answer given since (or before)."""
        result = "skipped" if correct is None else "right" if correct else "wrong"
        previous = self.quiz_log.get(question["id"])
        if result == "skipped" and previous and previous["result"] != "skipped":
            return
        self.quiz_log[question["id"]] = {"question": question, "chosen": chosen, "result": result}

    # -- After the castle: review, Stage Test, lucky draw -------------------------

    def _places_found(self):
        """The secret places found this level, as their HIDDEN_STYLES specs."""
        pits = {pit["index"]: pit["style"] for pit in self.surface.secret_pits}
        springs = {spring.link["index"]: spring.style for spring in self.surface.springs}
        styles = [pits[i] for i in sorted(self.secrets_found) if i in pits]
        styles += [springs[i] for i in sorted(self.sky_found) if i in springs]
        return [HIDDEN_STYLES[style] for style in styles]

    async def _stage_end(self):
        """Runs once the player continues past the stage-clear card: a
        review of every question (with explanations) and the words met,
        an optional Stage Test built from them, then a lucky draw. Ends
        the level with OUTCOME_ADVANCE."""
        self.pending_stage_end = False
        # The stage itself, without the clear card, behind every screen.
        self.level_complete = False
        self._draw()
        self.level_complete = True
        background = self.screen.copy()
        audio.music(audio.STAGE_END_TRACK)

        entries = list(self.quiz_log.values())
        items = [get_item(item_id) for item_id in dict.fromkeys(self.level_items)]
        words = learned_words(entries, items, self._places_found())
        extra = [word_from_item(item) for item in ITEMS.values()]
        extra += [word_from_place(spec) for spec in HIDDEN_STYLES.values()]
        test = build_test(entries, words, self.question_bank.questions, self.jlpt_level, self.rng, extra_words=extra)

        results = []
        if await ReviewScreen(self.screen, background, self.level_number, entries, words, len(test)).run() == "test":
            for number, item in enumerate(test, 1):
                if item["kind"] == "mc":
                    question = item["question"]
                    correct = await QuizScreen(
                        self.screen, question, background=background,
                        anchor_rect=pygame.Rect(SCREEN_WIDTH // 2, 40, 1, 1), hint_service=self.hint_service,
                        points=TEST_BONUS_XP, title=f"TEST {number}/{len(test)}",
                    ).run()
                    if correct is not None and self.tutor is not None:
                        self.tutor.record(question, correct)
                else:
                    correct = await TileScreen(self.screen, background, item, number, len(test)).run()
                    if correct == "skip":
                        correct = None
                results.append((item["kind"], correct))
            bonus = TEST_BONUS_XP * sum(1 for _, correct in results if correct)
            if results and all(correct for _, correct in results):
                progress.record(self.profile, "perfect_tests")
            self.profile.add_exp(EXP_TEST * sum(1 for _, correct in results if correct))
            self.score += bonus
            self._add_xp(bonus)
            if self.tutor is not None:
                self.next_jlpt_level = self.tutor.estimated_level()
            await ResultsScreen(self.screen, background, results, bonus).run()

        # Lucky draw: one box, the prizes flashing through it until the
        # player jumps into it.
        prize = roll_prize(self.rng, self.character["favorites"])
        prize = await LuckyDrawScreen(self.screen, background, self.character, prize, self.rng).run()
        if prize["kind"] == "coins":
            self.score += prize["amount"]
            self.profile.add_yen(prize["amount"])
        elif prize["kind"] == "xp":
            self._add_xp(prize["amount"])
        else:
            self.item_box[prize["item"].id] = self.item_box.get(prize["item"].id, 0) + 1

        # The checkpoint saved at the castle didn't have the test's XP or the
        # prizes yet.
        save_game.save_run(self._run_record(level_number=self.level_number + 1, jlpt_level=self.next_jlpt_level),
                           profile=self.profile)
        self.outcome = OUTCOME_ADVANCE
        self.running = False
        self.clock.tick(FPS)

    def _check_enemy_contact(self, dt):
        hit_enemies = pygame.sprite.spritecollide(self.player, self.enemies, dokill=False)
        if not hit_enemies:
            return

        # Sun power makes the mascot invincible: anything it touches is
        # defeated, and nothing costs power or XP.
        if self.sun_power:
            for enemy in hit_enemies:
                self._zap(enemy)
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

        if self.guard_left:
            # A guard (the kabuto, or a STRENGTH item) takes this one: no power
            # or XP lost.
            self.guard_left -= 1
            audio.play("block")
            self._add_effect_text("GUARD! Blocked it", (self.player.rect.centerx, self.player.rect.top), (255, 190, 130))
        else:
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
        audio.play("stomp")
        progress.record(self.profile, "stomps")
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
        asleep: that costs a life, and the player wakes up groggy.
        (Never called with sun power -- see _check_enemy_contact.)"""
        audio.play("hit")
        self._lose_xp(GAUGE_DAMAGE)
        self._set_power(self.power - 1)
        if self.power > 0:
            return

        self.lives -= 1
        self.coach.fell_asleep(self.power)
        self._add_effect_text("Zzz...", (self.player.rect.centerx, self.player.rect.top), (190, 200, 255))
        if self.lives <= 0:
            self.fell_asleep_flag = True
            self._game_over()
            return
        self._set_power(POWER_WAKE)
        self.drowsy_warned = False
        self.invulnerable_timer = WAKE_INVULNERABILITY_SECONDS

    def _game_over(self):
        self.game_over = True
        audio.stop_music()
        audio.play("gameover")

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

        self._draw_glows()

        t = self.clock_time
        for sprite in self.all_sprites:
            if sprite is self.player and self._player_should_blink_off():
                continue

            # Most sprites (platforms, enemies) are drawn at their own
            # rect. The player overrides this with draw_rect() because
            # its visual frame size can differ from its fixed collision
            # hitbox (see Player.draw_rect). Pickups spin (coins) or bob.
            rect = sprite.draw_rect() if hasattr(sprite, "draw_rect") else sprite.rect
            if isinstance(sprite, Collectible):
                self.screen.blit(sprite.frame(t), (rect.x - self.camera_x, rect.y + sprite.bob(t)))
            elif sprite is self.player and self.sun_power and not self._sun_flicker_off():
                # Powered up: the mascot itself glows gold, pulsing.
                lit = sprite.image.copy()
                k = 0.5 + 0.5 * math.sin(t * 6)
                lit.fill((round(70 + 50 * k), round(50 + 30 * k), 0), special_flags=pygame.BLEND_RGB_ADD)
                self.screen.blit(lit, (rect.x - self.camera_x, rect.y))
            else:
                self.screen.blit(sprite.image, (rect.x - self.camera_x, rect.y))
        for shot in self.shots:
            rect = shot.draw_rect()
            self.screen.blit(shot.image, (rect.x - self.camera_x, rect.y))
        if self.sun_power:
            self._draw_sun_aura()
        if self.player.parachute:
            self._draw_parachute()

        self._draw_effects()
        if self.drowsy and not self.game_over:
            self._draw_drowsy()
        if not (self.game_over or self.level_complete):
            self._draw_banner()
            self._draw_hud()
            self._draw_speech()
            self.toasts.draw(self.screen)
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

    def _draw_parachute(self):
        """A red-and-white canopy over the player, swaying as it drifts."""
        player = self.player
        cx = player.rect.centerx - self.camera_x + math.sin(self.clock_time * 2.2) * 4
        top = player.rect.top - 78
        half, height = 54, 40
        ink = (24, 18, 20)
        # Strings from the canopy's rim to the shoulders.
        shoulders = [(player.rect.left + 6 - self.camera_x, player.rect.top + 14),
                     (player.rect.right - 6 - self.camera_x, player.rect.top + 14)]
        rim = [(cx - half + 2, top + height), (cx - half / 3, top + height), (cx + half / 3, top + height),
               (cx + half - 2, top + height)]
        for i, point in enumerate(rim):
            pygame.draw.line(self.screen, (60, 50, 50), point, shoulders[0 if i < 2 else 1], 2)
        # The dome, as six panels.
        panels = 6
        dome = [(cx - math.cos(math.pi * k / 24) * (half + 3), top + height + 1 - math.sin(math.pi * k / 24) * (height + 3))
                for k in range(25)]
        pygame.draw.polygon(self.screen, ink, dome)
        for i in range(panels):
            a0, a1 = math.pi * i / panels, math.pi * (i + 1) / panels
            points = [(cx, top + height)]
            for k in range(7):
                a = a0 + (a1 - a0) * k / 6
                points.append((cx - math.cos(a) * half, top + height - math.sin(a) * height))
            pygame.draw.polygon(self.screen, (226, 64, 64) if i % 2 == 0 else (250, 244, 232), points)
        # A scalloped hem.
        for i in range(panels):
            x = cx - half + (i + 0.5) * half * 2 / panels
            pygame.draw.circle(self.screen, ink, (x, top + height), half / panels + 1, width=2,
                               draw_bottom_left=True, draw_bottom_right=True)
        pygame.draw.line(self.screen, ink, (cx - half, top + height), (cx + half, top + height), 2)

    def _glow_surface(self, color, radius, strength):
        """A cached soft round glow (concentric circles, brightest inside)."""
        key = (color, radius, strength)
        cache = self.__dict__.setdefault("_glow_cache", {})
        if key not in cache:
            glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for r in range(radius, 2, -2):
                glow_alpha = round(strength * (1 - r / radius) ** 1.3)
                pygame.draw.circle(glow, (*color, glow_alpha), (radius, radius), r)
            cache[key] = glow
        return cache[key]

    def _sun_flicker_off(self):
        """True on the 'off' beats of the flicker in sun power's last seconds."""
        return self.sun_time_left < SUN_FLICKER_SECONDS and int(self.clock_time * 8) % 2 == 0

    def _draw_sun_aura(self):
        """Little suns circling the powered-up player -- one fewer as each
        third of the time runs out -- and, until they've thrown one, a keycap
        prompt over their head saying how."""
        t = self.clock_time
        cx, cy = self.player.rect.centerx - self.camera_x, self.player.rect.centery
        suns = max(1, math.ceil(3 * self.sun_time_left / SUN_POWER_SECONDS))
        for i in range(suns if not self._sun_flicker_off() else 0):
            a = t * 3.2 + i * 2 * math.pi / 3
            x, y = cx + math.cos(a) * 26, cy + math.sin(a) * 14
            pygame.draw.circle(self.screen, (120, 60, 0), (x, y), 5)
            pygame.draw.circle(self.screen, (255, 210, 60), (x, y), 4)
        self._draw_sun_timer(cx, t)
        # (after the "SUN POWER!" pop-up has floated away, so they don't overlap)
        if self.sun_throws == 0 and t - self.sun_gained_at > 1.4:
            key = "X" if game_input.using_gamepad() or not IS_WEB else "B"
            label = ui.label_font(16)
            bob = round(2 * math.sin(t * 4))
            words = label.render("THROW", True, ui.CREAM)
            cap = pygame.Rect(0, 0, 24, 24)
            total = cap.width + 6 + words.get_width()
            cap.midleft = (cx - total // 2, self.player.rect.top - 30 + bob)
            pygame.draw.rect(self.screen, ui.OUTLINE, cap.inflate(4, 4), border_radius=6)
            pygame.draw.rect(self.screen, (255, 210, 90), cap, border_radius=5)
            pygame.draw.rect(self.screen, (200, 140, 40), (cap.x, cap.bottom - 5, cap.width, 5),
                             border_bottom_left_radius=5, border_bottom_right_radius=5)
            ui.text(self.screen, key, label, (cap.centerx, cap.centery - 1), color=ui.OUTLINE, outline=None,
                    anchor="center")
            ui.text(self.screen, "THROW", label, (cap.right + 6, cap.centery), anchor="midleft")

    def _draw_sun_timer(self, cx, t):
        """A little countdown dial by the player's head: a gold ring that
        empties over the 20 seconds, with the seconds left inside -- red
        for the last few."""
        left = max(0.0, self.sun_time_left)
        center = (round(cx + 30), self.player.rect.top - 14)
        low = left < 5
        color = (255, 110, 90) if low else (255, 206, 70)
        if low and self._sun_flicker_off():
            return
        pygame.draw.circle(self.screen, ui.OUTLINE, center, 15)
        pygame.draw.circle(self.screen, (40, 28, 30), center, 13)
        fraction = left / SUN_POWER_SECONDS
        if fraction > 0:
            rect = pygame.Rect(0, 0, 26, 26)
            rect.center = center
            start = math.pi / 2
            pygame.draw.arc(self.screen, color, rect, start, start + 2 * math.pi * fraction, 4)
        ui.text(self.screen, str(math.ceil(left)), ui.label_font(16), center, color=ui.CREAM, anchor="center",
                thickness=1)

    def _draw_glows(self):
        """Soft halos behind the things worth touching -- unanswered "?"
        blocks and every pickup (coloured by what it is) -- so they stand out
        from any world's scenery."""
        t = self.clock_time
        left, right = self.camera_x - 60, self.camera_x + SCREEN_WIDTH + 60
        for block in self.question_blocks:
            if not block.used and left < block.rect.centerx < right:
                glow = self._glow_surface(block.glow_color, 40, 150)
                glow.set_alpha(round(255 * block.glow_strength(t)))
                self.screen.blit(glow, glow.get_rect(center=(block.rect.centerx - self.camera_x, block.rect.centery)))
        if self.sun_power and not self._sun_flicker_off():   # a bright halo while powered up
            glow = self._glow_surface((255, 200, 60), 60, 230)
            glow.set_alpha(round(255 * (0.75 + 0.25 * math.sin(t * 5))))
            self.screen.blit(glow, glow.get_rect(center=(self.player.rect.centerx - self.camera_x,
                                                       self.player.rect.centery)))
        for pickup in self.collectibles:
            color = pickup.halo_color
            if color is None or not left < pickup.rect.centerx < right:
                continue
            big = pickup.item is not None and pickup.item.group in ("rare", "treasure")
            glow = self._glow_surface(color, 30 if big else 22, 170 if big else 120)
            if big:
                glow.set_alpha(round(255 * (0.6 + 0.4 * math.sin(t * 4))))
            else:
                glow.set_alpha(255)
            center = (pickup.rect.centerx - self.camera_x, pickup.rect.centery + pickup.bob(t))
            self.screen.blit(glow, glow.get_rect(center=center))

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
            if pit["index"] in self.secrets_found:
                # The rope you climbed out on, tied to a stake at the far edge.
                stake = (round(x1) - 6, ground)
                pygame.draw.rect(self.screen, (24, 18, 20), (stake[0] - 4, ground - 18, 8, 20))
                pygame.draw.rect(self.screen, (150, 104, 60), (stake[0] - 3, ground - 17, 6, 18))
                sway = math.sin(self.clock_time * 1.4 + pit["index"]) * 6
                end = (round(x1 - 22 + sway), SCREEN_HEIGHT)
                pygame.draw.line(self.screen, (24, 18, 20), (stake[0], ground - 12), end, 5)
                pygame.draw.line(self.screen, (206, 170, 112), (stake[0], ground - 12), end, 3)

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
    # sentences. Each corner reads top-down as label -> number -> detail.
    # No backing cards -- every glyph, bar and pip has a dark outline, which
    # keeps it readable over any world without covering the scene.

    def _draw_hud(self):
        self._draw_player_card()
        self._draw_level_pill()
        self._draw_minimap()
        self._draw_quiz_card()
        self._draw_tray()

    def _draw_player_card(self):
        card = HUD_LEFT_CARD   # no backing card: outlined text reads on any sky
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

        # Ability level: Lv, a bar to the next level, and the 円 to spend.
        row = card.y + 118
        ui.text(self.screen, "LV", label, (x, row), color=ui.GOLD)
        value = ui.text(self.screen, str(self.profile.level), label, (x + 66, row))
        yen = ui.text(self.screen, f"{self.profile.yen:,}円", ui.body_font(15), (right, row + 8), color=ui.CREAM,
                      anchor="midright", thickness=1)
        bar_x = max(value.right + 10, x + 120)
        into, needed = self.profile.level_progress()
        ui.bar(self.screen, (bar_x, row + 5, yen.x - 10 - bar_x, 7), into / needed, EXP_FILL, radius=3)

        # Temporary states get their own tag under the card, so they're
        # noticed without crowding the numbers above.
        tags = []
        if self.drowsy:
            tags.append(("SLEEPY... FIND A SNACK!", (120, 30, 44, 220), (255, 190, 190)))
        elif self.boost_timer > 0:
            tags.append((f"SPEED  {math.ceil(self.boost_timer)}s", (24, 70, 44, 220), (170, 255, 190)))
        if self.guard_left:
            tags.append((f"GUARD ×{self.guard_left}", (80, 44, 20, 220), (255, 190, 130)))
        for i, (words, bg, color) in enumerate(tags):
            width = label.size(words)[0] + 24
            pill = ui.panel(self.screen, (card.x, card.bottom + 6 + i * 30, width, 26), bg=bg, edge=(*color, 160),
                            radius=13)
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

    def _draw_minimap(self):
        """A thin line under the level pill: it fills in gold as the hero
        heads for the finish (the ゴール flag -- or a secret room's exit),
        with a dot for where they are now. Underground the line is the whole
        room, and the flag is the rope back up, at the start."""
        y, left, right = MINIMAP_Y, MINIMAP_X, MINIMAP_X + MINIMAP_W
        end = self.world.width_px if self.world.underground else self.goal.rect.centerx
        progress = max(0.0, min(1.0, self.player.rect.centerx / max(1, end)))
        x = left + round(progress * MINIMAP_W)
        pygame.draw.line(self.screen, (0, 0, 0), (left, y + 1), (right, y + 1), 3)      # shadow
        pygame.draw.line(self.screen, (110, 100, 135), (left, y), (right, y), 3)
        pygame.draw.line(self.screen, ui.GOLD, (left, y), (x, y), 3)
        if not self.world.hidden and self._finish_warned and self.answers_needed:
            # Short of answers near the end: mark the ? boxes still open.
            scale = MINIMAP_W / max(1, self.goal.rect.centerx)
            for block in self.surface.question_blocks:
                if not block.used:
                    bx = left + round(min(block.rect.centerx, self.goal.rect.centerx) * scale)
                    pygame.draw.line(self.screen, ui.OUTLINE, (bx, y - 7), (bx, y - 2), 4)
                    pygame.draw.line(self.screen, (255, 206, 70), (bx, y - 6), (bx, y - 3), 2)
        # The finish: a tiny flag (green for a secret room's exit).
        fx = left + round(self.goal.rect.centerx / end * MINIMAP_W) if self.world.underground else right
        pygame.draw.line(self.screen, ui.CREAM, (fx, y - 8), (fx, y + 1), 2)
        flag = ui.GREEN if self.world.hidden else (240, 96, 96)
        pygame.draw.polygon(self.screen, flag, [(fx + 1, y - 8), (fx + 7, y - 6), (fx + 1, y - 4)])
        # The hero.
        pygame.draw.circle(self.screen, ui.OUTLINE, (x, y), 6)
        pygame.draw.circle(self.screen, ui.CREAM, (x, y), 4)

    def _draw_quiz_card(self):
        """Progress toward the badge -- at least N questions answered, 70%
        of them right -- so it's something to aim at mid-level rather than
        a surprise at the castle."""
        card = HUD_RIGHT_CARD
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
        passed = answered >= min_questions     # enough answers to pass the stage
        ui.text(self.screen, f"/{min_questions} " + ("answered" if passed else "to pass"), label,
                (count.right + 4, count.bottom - 6), color=ui.GREEN if passed else ui.CREAM, anchor="bottomleft")

        ui.bar(self.screen, (x, card.y + 66, card.width - 28, 7), min(1.0, answered / min_questions),
               ui.GREEN if passed else ui.GOLD, radius=3)

        row = card.y + 80
        accuracy = round(100 * self.correct_count / answered) if answered else None
        right_text = ui.text(self.screen, f"{self.correct_count} right", label, (x, row))
        if accuracy is not None:
            ok = accuracy >= BADGE_PASS_ACCURACY * 100
            ui.text(self.screen, f"{accuracy}%", label, (right_text.right + 10, row),
                    color=ui.GREEN if ok else (255, 150, 150))
        if self.combo >= 2:
            ui.text(self.screen, f"COMBO x{self.combo}", label, (right, row), color=(255, 150, 60),
                    anchor="topright")
        elif self.skipped_count:
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
        # Left-aligned with the quiz lines above it (they start 14px in); the
        # icons have ~3px of transparent padding, so start that much earlier.
        tray = pygame.Rect(HUD_RIGHT_CARD.x - 1, HUD_RIGHT_CARD.bottom + 6, width, HUD_TRAY_HEIGHT)

        x = tray.x + 12
        for item_id in favorites:
            icon = get_icon(item_id, 24)
            self.screen.blit(icon, icon.get_rect(midleft=(x, tray.centery)))
            x += 26
        ui.text(self.screen, f"×{self.favorites_found}", label, (x + 2, tray.centery), anchor="midleft",
                color=(255, 170, 210))
        x += fav_w - 26 * len(favorites) + 6

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
        self._prompt(game_input.prompt("PRESS ENTER", "PRESS A", "TAP TO CONTINUE"), card.bottom - 26)

    def _draw_level_complete(self):
        self._dim()
        cx = SCREEN_WIDTH // 2
        answered = self.correct_count + self.wrong_count
        min_questions = required_question_count(self.level_number)

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
            pct = round(100 * self.correct_count / answered) if answered else 0
            sub = f"Get {round(BADGE_PASS_ACCURACY * 100)}% right to claim it -- you got {pct}%. So close!"
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
        self._prompt(game_input.prompt("PRESS ENTER FOR THE LESSON REVIEW", "PRESS A FOR THE LESSON REVIEW",
                                       "TAP JUMP FOR THE LESSON REVIEW"), 456)

import sys

# Window / rendering
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

# True only in the Pygbag/Emscripten (browser) build -- used to gate the
# on-screen touch controls (kobito/input.py) so the desktop build never
# shows them, since a mouse/keyboard/joystick player has no use for them.
IS_WEB = sys.platform == "emscripten"

# Tile size in pixels. Everything in the level (platforms, player size)
# is a multiple of this so levels can be laid out on a grid.
TILE_SIZE = 32

# Physics (pixels per second, and pixels per second^2 for gravity)
GRAVITY = 1800.0
MAX_FALL_SPEED = 1200.0
RUN_SPEED = 260.0
JUMP_SPEED = 620.0

# Colors (placeholder art uses flat colors until real sprites exist)
SKY_BLUE = (135, 206, 235)
GROUND_BROWN = (139, 90, 43)

# Question blocks / scoring
STARTING_LIVES = 3
CORRECT_ANSWER_SCORE = 10

# A question's worth scales with its JLPT level: clearing an N1 block is
# worth four N5 blocks, and missing one costs proportionally more of the
# XP gauge. Same numbers drive the score, the gauge gain on a correct
# answer, and the gauge penalty on a wrong one, so the risk/reward of
# playing at a harder level is legible to the player.
JLPT_QUESTION_POINTS = {"N5": 10, "N4": 15, "N3": 20, "N2": 30, "N1": 40}
JLPT_GAUGE_PENALTY = {"N5": 4, "N4": 6, "N3": 8, "N2": 11, "N1": 15}

# Every level holds QUESTION_BLOCKS_PER_LEVEL yellow "?" quiz blocks, but
# the player doesn't have to hit them all: earning the level's badge needs
# at least MIN_QUESTIONS_ANSWERED questions answered, with
# BADGE_PASS_ACCURACY of the answered ones correct (14 of 20 at 70%). A
# wrong answer costs XP but deliberately NOT a life, otherwise a few
# mistakes would end the run before a player could reach that bar.
QUESTION_BLOCKS_PER_LEVEL = 30
MIN_QUESTIONS_ANSWERED = 20
BADGE_PASS_ACCURACY = 0.7


def required_question_count(level_number=None):
    """How many questions must be answered (not necessarily correctly --
    see BADGE_PASS_ACCURACY) to be eligible for the level's badge. The
    same for every level; the parameter is kept so callers needn't care.
    """
    return MIN_QUESTIONS_ANSWERED


# XP: a running total that only ever counts up (minus penalties) --
# there is no 0-100 bar to refill. Every XP_PER_LIFE earned, though, is
# a bonus life, like the classic "100 coins = 1UP". A wrong quiz answer
# or an enemy hit takes XP off the total (GAUGE_DAMAGE for a hit), which
# delays the next bonus life.
XP_PER_LIFE = 100
GAUGE_DAMAGE = 5

# Enemy contact: a brief invulnerability window (with knockback) after
# getting hit, so touching an enemy costs exactly one power instead of
# draining several in the few frames it takes to separate.
INVULNERABILITY_SECONDS = 1.2
KNOCKBACK_SPEED_X = 220.0
KNOCKBACK_SPEED_Y = -300.0

# Power gauge: the player's stamina, separate from lives. Each enemy hit
# costs 1 power (so ten hits drain a full gauge). At POWER_DROWSY or below
# the player is about to doze off -- slower and sluggish -- until they
# find something from the konbini to perk them up. Hitting 0 means
# falling asleep: that costs a life, and they wake with POWER_WAKE.
POWER_MAX = 10
POWER_DROWSY = 3
POWER_WAKE = 5
DROWSY_RUN_SCALE = 0.72
DROWSY_JUMP_SCALE = 0.9
WAKE_INVULNERABILITY_SECONDS = 2.0
MAX_LIVES = 9

# Jumping on an enemy's head defeats it and bounces the player up.
STOMP_BOUNCE_SPEED = 470.0
STOMP_SCORE = 10
STOMP_GAUGE = 5
STOMP_DROP_CHANCE = 0.22  # a defeated ground enemy sometimes drops a snack

# Favourite items (see characters.py): a character's own favourite food
# or toy is worth more than a plain snack.
FAVORITE_SCORE = 25
FAVORITE_POWER = 1

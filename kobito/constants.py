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

# Earning a level's badge means answering most questions right, not all
# of them: at least the level's required question count (see
# required_question_count() below), with BADGE_PASS_ACCURACY of those
# correct -- i.e. 7 out of 10 at level 1. A wrong answer therefore costs
# XP but deliberately NOT a life, otherwise a few mistakes would end the
# run before the player could ever reach a 70% bar.
BADGE_PASS_ACCURACY = 0.7

# How many questions a level requires climbs as level_number climbs, so
# later levels demand more practice, not just harder JLPT content.
# Starts at 10 (level 1) and climbs by 2 per level, capped at 30 -- the
# size of each JLPT level's question pool (see assets/data/questions.json),
# so the bar never asks for more distinct questions than actually exist.
QUESTIONS_PER_LEVEL_START = 10
QUESTIONS_PER_LEVEL_STEP = 2
QUESTIONS_PER_LEVEL_MAX = 30

# A level places a couple more question blocks than it strictly
# requires, so a player can skip one or two (or get unlucky with a
# tricky one) and still reach the bar rather than needing a clean sweep
# of every block in the level.
LEVEL_BLOCK_BUFFER = 2


def required_question_count(level_number):
    """How many questions must be answered (not necessarily correctly --
    see BADGE_PASS_ACCURACY) to be eligible for the level's badge.
    """
    raw = QUESTIONS_PER_LEVEL_START + (level_number - 1) * QUESTIONS_PER_LEVEL_STEP
    return min(QUESTIONS_PER_LEVEL_MAX, raw)

# Life gauge: fills from coin/onigiri pickups (by their value), same
# idea as classic "100 coins = 1UP" -- reaching/exceeding GAUGE_MAX
# grants a bonus life and the gauge carries over its remainder. A wrong
# quiz answer or an enemy hit sets the gauge back by GAUGE_DAMAGE, on
# top of costing a life outright, so mistakes also cost progress toward
# the next bonus life.
GAUGE_MAX = 100
GAUGE_DAMAGE = 5

# Enemy contact: a brief invulnerability window (with knockback) after
# getting hit, so touching an enemy costs exactly one life instead of
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

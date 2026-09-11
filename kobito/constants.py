# Window / rendering
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

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

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
# of them: at least BADGE_MIN_QUESTIONS answered, with BADGE_PASS_ACCURACY
# of those correct -- i.e. 7 out of 10. A wrong answer therefore costs XP
# but deliberately NOT a life, otherwise three mistakes would end the run
# before the player could ever reach a 70% bar.
BADGE_MIN_QUESTIONS = 10
BADGE_PASS_ACCURACY = 0.7

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

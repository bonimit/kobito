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

# Enemy contact: a brief invulnerability window (with knockback) after
# getting hit, so touching an enemy costs exactly one life instead of
# draining several in the few frames it takes to separate.
INVULNERABILITY_SECONDS = 1.2
KNOCKBACK_SPEED_X = 220.0
KNOCKBACK_SPEED_Y = -300.0

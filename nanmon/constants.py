import pygame

# Window (vertical orientation)
WIDTH, HEIGHT = 600, 900
FPS = 60
RNG_SEED = 42

# Colors
BG_COLOR = pygame.Color("#1E1E1E")
WHITE = pygame.Color(255, 255, 255)
SALTY_COLOR = pygame.Color("#A7D3FF")
SWEET_COLOR = pygame.Color("#FF9ECF")

# Gameplay
LEVEL_TARGET_SCORE = 20
SPAWN_INTERVAL_MIN = 0.25
SPAWN_INTERVAL_MAX = 0.55
MAX_ONSCREEN_FOOD = 30
HOMING_FRACTION = 0.35
HOMING_STRENGTH_WEAK = 0.6
HOMING_STRENGTH_STRONG = 1.2
HOMING_RANGE_SCALE = 900.0
HOMING_MAX_VX = 260

# Nausea
NAUSEA_MAX = 100
NAUSEA_WRONG_EAT = 20
NAUSEA_DECAY_PER_SEC = 2.0

# Player
# Horizontal is snappy; vertical uses a spring toward a target moved by keys
MOUTH_SPEED = 700      # vertical target speed
MOUTH_SPEED_X = 450    # horizontal direct speed
MOUTH_SIZE = (64, 36)
NECK_SWISH_AMPLITUDE = 6
NECK_SWISH_SPEED = 3.0
MOUTH_SPRING_K = 64.0  # stronger spring = snappier vertical response
MOUTH_DAMPING = 18.0   # higher damping = less bounce/overshoot
MOUTH_MAX_SPEED = 1400 # allow faster catch-up without jitter

# Foods
# Make foods move much faster
FOOD_FALL_SPEED_RANGE = (320, 500)

# Flash feedback
FLASH_DURATION = 0.15

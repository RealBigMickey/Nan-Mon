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
NAUSEA_MAX = 260
NAUSEA_WRONG_EAT = 20
NAUSEA_DECAY_PER_SEC = 2.0

# Player
# Horizontal is snappy; vertical uses a spring toward a target moved by keys
MOUTH_SPEED = 700      # vertical target speed
MOUTH_SPEED_X = 450    # horizontal direct speed
MOUTH_SIZE = (40, 40)
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

# ---Teddy add---
ASSET_BG_PATH = "nanmon/assets/bg"
ASSET_FOOD_DIR = "nanmon/assets/food"
FOOD_SIZE = (40, 40)
# ---Teddy add---

# --- Boss & Target additions ---
# Boss asset and behavior
ASSET_BOSS_IMAGE = "nanmon/assets/boss/boss.png"
# Much bigger boss, slow movement
BOSS_SIZE = (500, 320)
BOSS_Y = 70  # mid-top y
BOSS_Y_TOP = 50
BOSS_Y_BOTTOM = 360
BOSS_SPEED_X = 65.0
BOSS_SPEED_Y = 34.0
# Attacks
BOSS_SHOT_INTERVAL = 2.2
BOSS_RING_INTERVAL = 3.6
BOSS_RING_PROJECTILES = 28
BOSS_RING_PAIR_GAP = 0.35
BOSS_FOOD_SPEED = 300.0
BOSS_HIT_DAMAGE = 22.0  # nausea added when hit by boss projectile
# Appear/Hide cycle
BOSS_APPEAR_DURATION = 6.0
BOSS_HIDE_DURATION = 3.0
# Bite-to-kill
BOSS_HIT_FLASH_TIME = 0.18
BOSS_BITES_TO_KILL = 3

# When to spawn the boss (seconds); used by Progress bar
BOSS_SPAWN_TIME = 5.0

# Target visuals that may appear on boss (optional for now)
TARGET_SIZE = (44, 44)
TARGET_LIFETIME = 4.0
TARGET_RESPAWN_BASE = 1.2         # delay before a new target appears normally
TARGET_RESPAWN_AFTER_BITE = 0.6   # shorter delay after a successful bite
TARGET_IMG_PATHS = {
	"BLUE": "nanmon/assets/char/target_blue.png",
	"PINK": "nanmon/assets/char/target_pink.png",
}
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

# Font
FONT_PATH = "nanmon/assets/Pixel Emulator.otf"

# Gameplay
SPAWN_INTERVAL_MIN = 0.25
SPAWN_INTERVAL_MAX = 0.55
MAX_ONSCREEN_FOOD = 30
HOMING_FRACTION = 0.35
HOMING_STRENGTH_WEAK = 0.7
HOMING_STRENGTH_STRONG = 1.35
HOMING_RANGE_SCALE = 900.0
HOMING_MAX_VX = 260

# Nausea
NAUSEA_MAX = 160
NAUSEA_WRONG_EAT = 20
NAUSEA_DECAY_PER_SEC = 3.0

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
MOUTH_BITE_DURATION = 0.12  # how long the mouth shows the bite sprite after eating

# Foods
# Make foods move much faster
FOOD_FALL_SPEED_RANGE = (320, 500)

# Flash feedback
FLASH_DURATION = 0.15

# ---Teddy add---
ASSET_BG_PATH = "nanmon/assets/bg"
ASSET_FOOD_DIR = "nanmon/assets/food"
FOOD_SIZE = (40, 40)
# Default shrunken hitbox for foods (1.0 = full sprite rect)
FOOD_HITBOX_SCALE = 0.8
# Hats directory
ASSET_HAT_DIR = "nanmon/assets/hats"
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
# Per-kind nausea tiers (used instead of flat damage)
BOSS_HIT_DAMAGE_WEAK = 8.0     # e.g., Doritos, Soda
BOSS_HIT_DAMAGE_NORMAL = 16.0  # e.g., Fries, Icecream
BOSS_HIT_DAMAGE_STRONG = 30.0  # e.g., Burgers, Cake
BOSS_HIT_DAMAGE_BY_KIND = {
	"DORITOS": BOSS_HIT_DAMAGE_WEAK,
	"SODA": BOSS_HIT_DAMAGE_WEAK,
	"FRIES": BOSS_HIT_DAMAGE_NORMAL,
	"ICECREAM": BOSS_HIT_DAMAGE_NORMAL,
	"BURGERS": BOSS_HIT_DAMAGE_STRONG,
	"CAKE": BOSS_HIT_DAMAGE_STRONG,
}
# Appear/Hide cycle
BOSS_APPEAR_DURATION = 9.0
BOSS_HIDE_DURATION = 3.0
# Spawn animation duration (seconds)
BOSS_SPAWN_DURATION = 1.2
# Bite-to-kill
BOSS_HIT_FLASH_TIME = 0.18
BOSS_BITES_TO_KILL = 4

# When to spawn the boss (seconds); used by Progress bar
BOSS_SPAWN_TIME = 3.0

# Target visuals that may appear on boss (optional for now)
TARGET_SIZE = (44, 44)
TARGET_LIFETIME = 4.0
TARGET_RESPAWN_BASE = 1.2         # delay before a new target appears normally
TARGET_RESPAWN_AFTER_BITE = 2.0   # longer delay after a successful bite
TARGET_IMG_PATHS = {
	"BLUE": "nanmon/assets/char/target_blue.png",
	"PINK": "nanmon/assets/char/target_pink.png",
}

# Beam attack
BOSS_BEAM_INTERVAL = 6.0      # base interval between beams (will shorten with damage)
BOSS_BEAM_DURATION = 1.6      # how long a beam fires
BOSS_BEAM_RATE = 18.0         # foods per second during beam
BOSS_BEAM_SPEED = 420.0       # projectile speed for beam
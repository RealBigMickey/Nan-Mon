from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Import defaults to fall back on project-wide tuning
from .constants import (
    ASSET_BG_PATH,
    BOSS_BEAM_DURATION,
    BOSS_BEAM_INTERVAL,
    BOSS_BEAM_RATE,
    BOSS_BEAM_SPEED,
    BOSS_BITES_TO_KILL,
    BOSS_FOOD_SPEED,
    BOSS_RING_INTERVAL,
    BOSS_RING_PAIR_GAP,
    BOSS_RING_PROJECTILES,
    BOSS_SHOT_INTERVAL,
    BOSS_SIZE,
    BOSS_SPEED_X,
    BOSS_SPEED_Y,
    BOSS_SPAWN_DURATION,
    BOSS_Y,
    BOSS_Y_BOTTOM,
    BOSS_Y_TOP,
    FOOD_FALL_SPEED_RANGE,
    HOMING_FRACTION,
    MAX_ONSCREEN_FOOD,
    NAUSEA_WRONG_EAT,
    BOSS_SPAWN_TIME,
    SPAWN_INTERVAL_MIN,
    SPAWN_INTERVAL_MAX,
)


@dataclass
class LevelBossConfig:
    # Visual/placement
    image_path: Optional[str] = None  # keep default in constants if None
    size: tuple[int, int] = BOSS_SIZE
    y_target: int = BOSS_Y
    y_top: int = BOSS_Y_TOP
    y_bottom: int = BOSS_Y_BOTTOM

    # Movement
    speed_x: float = BOSS_SPEED_X
    speed_y: float = BOSS_SPEED_Y

    # Attacks
    shot_interval: float = BOSS_SHOT_INTERVAL
    ring_interval: float = BOSS_RING_INTERVAL
    ring_projectiles: int = BOSS_RING_PROJECTILES
    ring_pair_gap: float = BOSS_RING_PAIR_GAP
    beam_interval: float = BOSS_BEAM_INTERVAL
    beam_duration: float = BOSS_BEAM_DURATION
    beam_rate: float = BOSS_BEAM_RATE
    beam_speed: float = BOSS_BEAM_SPEED
    food_speed: float = BOSS_FOOD_SPEED

    # Health / lifecycle
    bites_to_kill: int = BOSS_BITES_TO_KILL
    spawn_duration: float = BOSS_SPAWN_DURATION

    # Content
    ring_foods_salty: List[str] = field(default_factory=lambda: ["DORITOS", "FRIES", "BURGERS"])
    ring_foods_sweet: List[str] = field(default_factory=lambda: ["ICECREAM", "SODA", "CAKE"])
    burst_foods: List[str] = field(default_factory=lambda: ["DORITOS", "FRIES", "SODA", "ICECREAM"])
    beam_kinds: List[str] = field(default_factory=lambda: ["DORITOS", "SODA"])  # single-kind sustained


@dataclass
class LevelConfig:
    level: int
    name: str

    # Visual/audio
    bg_images: List[str]
    bg_scroll_speed: float = 40.0
    music_path: Optional[str] = None

    # Spawning
    spawn_interval_min: float = SPAWN_INTERVAL_MIN
    spawn_interval_max: float = SPAWN_INTERVAL_MAX
    food_fall_speed_range: tuple[float, float] = FOOD_FALL_SPEED_RANGE
    homing_fraction: float = HOMING_FRACTION
    max_onscreen_food: int = MAX_ONSCREEN_FOOD

    # Boss timing
    boss_spawn_time: float = BOSS_SPAWN_TIME

    # Mechanics/modifiers
    nausea_wrong_eat: float = NAUSEA_WRONG_EAT
    nausea_damage_multiplier: float = 1.0
    invert_modes: bool = False  # if True, SALTY vs SWEET match logic is inverted

    # Food pools for normal spawns
    foods_light: List[str] = field(default_factory=lambda: ["DORITOS", "FRIES", "ICECREAM", "SODA"])
    foods_homing: List[str] = field(default_factory=lambda: ["BURGERS", "CAKE"])  # chosen when homing

    # Boss config
    boss: LevelBossConfig = field(default_factory=LevelBossConfig)


def _bg(path: str) -> str:
    return f"{ASSET_BG_PATH}/{path}"


def get_level(n: int) -> LevelConfig:
    # Level 1: baseline
    if n == 1:
        return LevelConfig(
            level=1,
            name="Tasty Tutorial",
            bg_images=[_bg("game_bg1.png"), _bg("game_bg1.png")],
            bg_scroll_speed=40.0,
            music_path="assets/sounds/level1_backgrounds_sounds.wav",  # 修正: 指定正確音樂路徑
            food_fall_speed_range=FOOD_FALL_SPEED_RANGE,
            homing_fraction=HOMING_FRACTION,
            max_onscreen_food=MAX_ONSCREEN_FOOD,
            spawn_interval_min=SPAWN_INTERVAL_MIN,
            spawn_interval_max=SPAWN_INTERVAL_MAX,
            boss_spawn_time=BOSS_SPAWN_TIME,
            nausea_wrong_eat=NAUSEA_WRONG_EAT,
            boss=LevelBossConfig(),
        )

    # Level 2: faster, denser, stronger boss
    if n == 2:
        sweet_foods = ["BUBBLETEA", "MANGOICE", "TOFUPUDDING"]
        salty_foods = ["FRIEDCHICKEN", "TAIWANBURGER", "STINKYTOFU"]
        all_foods = sweet_foods + salty_foods
        return LevelConfig(
            level=2,
            name="Snack Storm",
            bg_images=[_bg("game_bg2.jpg"), _bg("game_bg2.jpg")],
            bg_scroll_speed=55.0,
            music_path="assets/sounds/level2_backgrounds_sounds.wav",
            food_fall_speed_range=(360, 520),
            homing_fraction=min(1.0, HOMING_FRACTION + 0.12),
            max_onscreen_food=MAX_ONSCREEN_FOOD + 8,
            spawn_interval_min=max(0.18, SPAWN_INTERVAL_MIN - 0.05),
            spawn_interval_max=max(0.35, SPAWN_INTERVAL_MAX - 0.1),
            boss_spawn_time=max(6.0, BOSS_SPAWN_TIME - 3.0),
            nausea_wrong_eat=NAUSEA_WRONG_EAT,
            foods_light=all_foods,
            foods_homing=all_foods,
                boss=LevelBossConfig(
                    speed_x=BOSS_SPEED_X * 1.1,
                    speed_y=BOSS_SPEED_Y * 1.1,
                    ring_projectiles=BOSS_RING_PROJECTILES + 4,
                    beam_rate=BOSS_BEAM_RATE + 4,
                    bites_to_kill=BOSS_BITES_TO_KILL + 1,
                    ring_foods_salty=salty_foods,
                    ring_foods_sweet=sweet_foods,
                    burst_foods=all_foods,
                    beam_kinds=all_foods,
                ),
        )

    # Level 3: challenging, inverted modes, aggressive boss
    if n == 3:
        # 指定第三關食物
        salty_foods = ["BEEFSOUP", "RICEBOWLCAKE", "TAINANPORRIDGE"]
        sweet_foods = ["TAINANPUDDING", "TAINANICECREAM", "TAINANTOFUICE"]
        all_foods = salty_foods + sweet_foods
        return LevelConfig(
            level=3,
            name="Spice & Sugar Mayhem",
            bg_images=[_bg("game_bg3.jpg"), _bg("game_bg3.jpg")],
            bg_scroll_speed=72.0,
            music_path="assets/sounds/level3_backgrounds_sounds.wav",
            food_fall_speed_range=(380, 560),
            homing_fraction=min(1.0, HOMING_FRACTION + 0.2),
            max_onscreen_food=MAX_ONSCREEN_FOOD + 12,
            spawn_interval_min=max(0.16, SPAWN_INTERVAL_MIN - 0.08),
            spawn_interval_max=max(0.3, SPAWN_INTERVAL_MAX - 0.15),
            boss_spawn_time=max(5.0, BOSS_SPAWN_TIME - 5.0),
            nausea_wrong_eat=NAUSEA_WRONG_EAT,
            nausea_damage_multiplier=1.2,
            invert_modes=True,
            foods_light=all_foods,
            foods_homing=all_foods,
                boss=LevelBossConfig(
                    speed_x=BOSS_SPEED_X * 1.25,
                    speed_y=BOSS_SPEED_Y * 1.2,
                    ring_projectiles=BOSS_RING_PROJECTILES + 8,
                    ring_pair_gap=max(0.2, BOSS_RING_PAIR_GAP - 0.05),
                    beam_rate=BOSS_BEAM_RATE + 8,
                    beam_speed=BOSS_BEAM_SPEED * 1.1,
                    bites_to_kill=BOSS_BITES_TO_KILL + 2,
                    ring_foods_salty=salty_foods,
                    ring_foods_sweet=sweet_foods,
                    burst_foods=all_foods,
                    beam_kinds=all_foods,
                ),
        )

    # Fallback to level 1 config for unknown inputs
    return get_level(1)

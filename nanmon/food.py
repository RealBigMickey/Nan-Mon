from __future__ import annotations
import os
import random
from typing import Tuple
import pygame
from .constants import (
    SALTY_COLOR, SWEET_COLOR,
    FOOD_FALL_SPEED_RANGE, WIDTH, HEIGHT,
    HOMING_STRENGTH_WEAK, HOMING_STRENGTH_STRONG,
    HOMING_RANGE_SCALE, HOMING_MAX_VX,
    ASSET_FOOD_DIR, FOOD_SIZE,   # 👈 新增
    FOOD_HITBOX_SCALE,
)
from .levels import LevelConfig


KINDS = [
    # Level 1
    "DORITOS", "BURGERS", "FRIES", "ICECREAM", "SODA", "CAKE",
    # Level 2
    "SHAVEDICE", "DONUT", "CUPCAKE", "RIBS", "HOTDOG", "FRIEDCHICKEN",
    # Level 3
    "BEEFSOUP", "RICEBOWLCAKE", "TAINANPORRIDGE", "TAINANPUDDING", "TAINANICECREAM", "TAINANTOFUICE",
]

FOOD_IMAGE_FILES = {
    # Base
    "DORITOS": "DORITOS.png",
    "BURGERS": "BURGERS.png",
    "FRIES": "FRIES.png",
    "ICECREAM": "ICECREAM.png",
    "SODA": "SODA.png",
    "CAKE": "CAKE.png",
    "BUBBLETEA": "BUBBLETEA.png",
    "MANGOICE": "MANGOICE.png",
    "TOFUPUDDING": "TOFUPUDDING.png",
    "FRIEDCHICKEN": "FRIEDCHICKEN.png",
    "TAIWANBURGER": "TAIWANBURGER.png",
    "STINKYTOFU": "STINKYTOFU.png",
    # Level 2
    "SHAVEDICE": "SHAVEDICE.png",
    "DONUT": "DONUT.png",
    "CUPCAKE": "CUPCAKE.png",
    "RIBS": "RIBS.png",
    "HOTDOG": "HOTDOG.png",
    # Level 3
    "BEEFSOUP": "BEEFSOUP.png",
    "RICEBOWLCAKE": "RICEBOWLCAKE.png",
    "TAINANPORRIDGE": "TAINANPORRIDGE.png",
    "TAINANPUDDING": "TAINANPUDDING.png",
    "TAINANICECREAM": "TAINANICECREAM.png",
    "TAINANTOFUICE": "TAINANTOFUICE.png",
}

def _load_food_image(kind: str) -> pygame.Surface | None:
    """嘗試載入並縮放食物 PNG，找不到時回傳 None 讓程式走幾何後援。"""
    filename = FOOD_IMAGE_FILES.get(kind)
    if not filename:
        return None
    path = os.path.join(ASSET_FOOD_DIR, filename)
    if not os.path.exists(path):
        return None
    # Cache loaded/scaled images to avoid disk I/O and rescale cost during bursts
    if not hasattr(_load_food_image, "_cache"):
        _load_food_image._cache = {}
    cache = _load_food_image._cache  # type: ignore[attr-defined]
    key = (path, FOOD_SIZE)
    if key in cache:
        return cache[key]
    img = pygame.image.load(path).convert_alpha()
    img = pygame.transform.scale(img, FOOD_SIZE)
    cache[key] = img
    return img

class Food(pygame.sprite.Sprite):
    def __init__(self, kind: str, category: str, x: int, speed_y: float, homing: bool, *, spawn_center_y: int | None = None, scale: float = 1.0, hitbox_scale: float | None = None):
        super().__init__()
        self.kind = kind
        self.category = category
        self.homing = homing
        self.vx = 0.0
        self.vy = speed_y
        # Hitbox scale (relative to current sprite size); defaults to constant
        self.hitbox_scale = float(FOOD_HITBOX_SCALE if hitbox_scale is None else hitbox_scale)

        # 先嘗試用圖片；失敗則用原本的幾何畫法
        image = _load_food_image(kind)
        if image is not None:
            # Apply optional scale
            if abs(scale - 1.0) > 1e-3:
                w, h = image.get_size()
                sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
                image = pygame.transform.scale(image, (sw, sh))
            self.base_image = image
            self.image = self.base_image.copy()
        else:
            base_w, base_h = FOOD_SIZE
            if abs(scale - 1.0) > 1e-3:
                base_w = max(1, int(base_w * scale))
                base_h = max(1, int(base_h * scale))
            self.base_image = pygame.Surface((base_w, base_h), pygame.SRCALPHA)
            self.image = self.base_image.copy()
            self._draw_shape()  # ← 你的原本幾何造型保留當備援

        # Spawn from top by default, or from a provided center Y (e.g., boss center)
        if spawn_center_y is None:
            self.rect = self.image.get_rect(midtop=(x, -FOOD_SIZE[1]))
        else:
            self.rect = self.image.get_rect(center=(x, spawn_center_y))
        self.fx = float(self.rect.x)
        self.fy = float(self.rect.y)

    @property
    def hitbox(self) -> pygame.Rect:
        """Return a shrunken collision rect centered within sprite rect."""
        if self.hitbox_scale >= 0.999:
            return self.rect
        w = int(self.rect.width * self.hitbox_scale)
        h = int(self.rect.height * self.hitbox_scale)
        if w <= 0 or h <= 0:
            return pygame.Rect(self.rect.centerx, self.rect.centery, 1, 1)
        r = pygame.Rect(0, 0, w, h)
        r.center = self.rect.center
        return r

    def _draw_shape(self):
        # 這段沿用你既有的幾何圖形繪製（略）。保留可防缺圖。
        s = self.base_image
        s.fill((0, 0, 0, 0))
        salty = (self.category == "SALTY")
        color = SALTY_COLOR if salty else SWEET_COLOR
        w, h = s.get_size()
        cx, cy = w//2, h//2
        # ...（你的原本繪製分支）...

    def update(self, dt: float, mouth_pos: Tuple[int, int]):
        # 你的原有追蹤/整體運動邏輯完全保留
        # Homing only if enabled
        if self.homing and mouth_pos is not None:
            target_x = mouth_pos[0]
            dx = target_x - (self.fx + self.rect.width/2)
            base = HOMING_STRENGTH_STRONG if self.kind in ("BURGERS", "CAKE") else HOMING_STRENGTH_WEAK
            scale = min(1.0, abs(dx) / HOMING_RANGE_SCALE)
            strength = base * (0.3 + 0.7 * scale)
            steer = max(-1.0, min(1.0, dx / 90.0))
            self.vx += strength * steer * 60 * dt
        if self.vx > HOMING_MAX_VX: self.vx = HOMING_MAX_VX
        elif self.vx < -HOMING_MAX_VX: self.vx = -HOMING_MAX_VX
        self.fx += self.vx * dt
        self.fy += self.vy * dt
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

def make_food(rng: random.Random, level_cfg: LevelConfig | None = None) -> Food:
    if level_cfg is None:
        from .constants import HOMING_FRACTION
        homing_choice = rng.random() < HOMING_FRACTION
        if homing_choice:
            kind = rng.choice(["BURGERS", "CAKE"])  # defaults for level-less spawn
        else:
            kind = rng.choice(["DORITOS", "FRIES", "ICECREAM", "SODA"])
        category = "SALTY" if kind in ("DORITOS", "BURGERS", "FRIES") else "SWEET"
        speed_y = rng.uniform(*FOOD_FALL_SPEED_RANGE)
        x = rng.randint(20, WIDTH-20)
        homing = (kind in ("BURGERS", "CAKE"))
        return Food(kind, category, x, speed_y, homing)
    else:
        homing_choice = rng.random() < level_cfg.homing_fraction
        if homing_choice and level_cfg.foods_homing:
            kind = rng.choice(level_cfg.foods_homing)
        else:
            pool = level_cfg.foods_light or ["DORITOS", "FRIES", "ICECREAM", "SODA"]
            kind = rng.choice(pool)
        # Derive category for broader set of foods
        salty_set = {"DORITOS", "BURGERS", "FRIES", "FRIEDCHICKEN", "RIBS", "HOTDOG", "TAIWANBURGER", "STINKYTOFU"}
        category = "SALTY" if kind in salty_set else "SWEET"
        speed_y = rng.uniform(*level_cfg.food_fall_speed_range)
        x = rng.randint(20, WIDTH-20)
        homing = (kind in tuple(level_cfg.foods_homing))
        scale = getattr(level_cfg, "food_scale", 1.0)
        hitbox_scale = getattr(level_cfg, "food_hitbox_scale", None)
        return Food(kind, category, x, speed_y, homing, scale=scale, hitbox_scale=hitbox_scale)

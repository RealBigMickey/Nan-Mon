# nanmon/food.py
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
)

FOOD_IMAGE_FILES = {
    "DORITOS":   "DORITOS.png",
    "BURGERS":   "BURGERS.png",
    "FRIES":     "FRIES.png",
    "ICECREAM":  "ICECREAM.png",
    "SODA":      "SODA.png",
    "CAKE":      "CAKE.png",
}

def _load_food_image(kind: str) -> pygame.Surface | None:
    """嘗試載入並縮放食物 PNG，找不到時回傳 None 讓程式走幾何後援。"""
    filename = FOOD_IMAGE_FILES.get(kind)
    if not filename:
        return None
    path = os.path.join(ASSET_FOOD_DIR, filename)
    if not os.path.exists(path):
        return None
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(img, FOOD_SIZE)

class Food(pygame.sprite.Sprite):
    def __init__(self, kind: str, category: str, x: int, speed_y: float, homing: bool):
        super().__init__()
        self.kind = kind
        self.category = category
        self.homing = homing
        self.vx = 0.0
        self.vy = speed_y

        # 先嘗試用圖片；失敗則用原本的幾何畫法
        image = _load_food_image(kind)
        if image is not None:
            self.base_image = image
            self.image = self.base_image.copy()
        else:
            self.base_image = pygame.Surface(FOOD_SIZE, pygame.SRCALPHA)
            self.image = self.base_image.copy()
            self._draw_shape()  # ← 你的原本幾何造型保留當備援

        self.rect = self.image.get_rect(midtop=(x, -FOOD_SIZE[1]))
        self.fx = float(self.rect.x)
        self.fy = float(self.rect.y)

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

def make_food(rng: random.Random) -> Food:
    from .constants import HOMING_FRACTION
    homing_choice = rng.random() < HOMING_FRACTION
    if homing_choice:
        kind = rng.choice(["BURGERS", "CAKE"])
    else:
        kind = rng.choice(["DORITOS", "FRIES", "ICECREAM", "SODA"])
    category = "SALTY" if kind in ("DORITOS", "BURGERS", "FRIES") else "SWEET"
    speed_y = rng.uniform(*FOOD_FALL_SPEED_RANGE)
    x = rng.randint(20, WIDTH-20)
    homing = (kind in ("BURGERS", "CAKE"))
    return Food(kind, category, x, speed_y, homing)

from __future__ import annotations
import math
import random
from typing import Tuple
import pygame
from .constants import (
    SALTY_COLOR, SWEET_COLOR,
    FOOD_FALL_SPEED_RANGE,
    WIDTH, HEIGHT,
    HOMING_STRENGTH_WEAK, HOMING_STRENGTH_STRONG,
    HOMING_RANGE_SCALE, HOMING_MAX_VX,
)

class Food(pygame.sprite.Sprite):
    def __init__(self, kind: str, category: str, x: int, speed_y: float, homing: bool):
        super().__init__()
        self.kind = kind
        self.category = category
        self.homing = homing
        self.vx = 0.0
        self.vy = speed_y
        self.base_image = pygame.Surface((40, 40), pygame.SRCALPHA)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(midtop=(x, -40))
        # subpixel position buffers
        self.fx = float(self.rect.x)
        self.fy = float(self.rect.y)
        self._draw_shape()

    def _draw_shape(self):
        s = self.base_image
        s.fill((0, 0, 0, 0))
        salty = (self.category == "SALTY")
        color = SALTY_COLOR if salty else SWEET_COLOR
        w, h = s.get_size()
        cx, cy = w//2, h//2

        if self.kind == "DORITOS":
            pts = [(cx, 4), (w-6, h-6), (6, h-6)]
            pygame.draw.polygon(s, color, pts)
        elif self.kind == "BURGERS":
            pygame.draw.rect(s, color, pygame.Rect(6, 10, w-12, h-20), border_radius=8)
            pygame.draw.rect(s, pygame.Color(255,255,255), pygame.Rect(6, 10, w-12, h-20), 2, border_radius=8)
        elif self.kind == "FRIES":
            for i in range(5):
                rx = 6 + i*6
                pygame.draw.rect(s, color, pygame.Rect(rx, 6, 4, h-12))
        elif self.kind == "ICECREAM":
            pygame.draw.circle(s, color, (cx, cy), min(cx, cy)-4)
        elif self.kind == "SODA":
            pygame.draw.rect(s, color, pygame.Rect(cx-8, 4, 16, h-8))
            pygame.draw.rect(s, pygame.Color(255,255,255), pygame.Rect(cx-8, 4, 16, h-8), 2)
        elif self.kind == "CAKE":
            top_w = w - 20
            bottom_w = w - 8
            top_x = (w - top_w)//2
            bottom_x = (w - bottom_w)//2
            pts = [ (top_x, 8), (top_x+top_w, 8), (bottom_x+bottom_w, h-8), (bottom_x, h-8) ]
            pygame.draw.polygon(s, color, pts)
            pygame.draw.rect(s, pygame.Color(255,255,255), pygame.Rect(top_x+6, 12, top_w-12, 6))
        else:
            pygame.draw.rect(s, color, s.get_rect())
        self.image = s
        self.rect = self.image.get_rect(topleft=self.rect.topleft)

    def update(self, dt: float, mouth_pos: Tuple[int, int]):
        # Always-on gentle homing; burgers/cake stronger
        target_x = mouth_pos[0]
        dx = target_x - (self.fx + self.rect.width/2)
        base = HOMING_STRENGTH_STRONG if self.kind in ("BURGERS", "CAKE") else HOMING_STRENGTH_WEAK
        scale = min(1.0, abs(dx) / HOMING_RANGE_SCALE)
        strength = base * (0.3 + 0.7 * scale)
        steer = max(-1.0, min(1.0, dx / 90.0))
        self.vx += strength * steer * 60 * dt
        # cap vx
        if self.vx > HOMING_MAX_VX:
            self.vx = HOMING_MAX_VX
        elif self.vx < -HOMING_MAX_VX:
            self.vx = -HOMING_MAX_VX

        # Integrate subpixel pos
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

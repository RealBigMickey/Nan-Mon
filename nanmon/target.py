"""Weak-point target that spawns on the boss's lower-front outer rim and follows it."""

from __future__ import annotations

import math
import os
import random
import pygame

from .constants import TARGET_IMG_PATHS, TARGET_SIZE, TARGET_LIFETIME


class Target:
    """固定顏色，生成在 Boss 身上，存在一段時間並跟隨 Boss 移動。"""

    def __init__(self, boss_rect: pygame.Rect):
        # 固定顏色（一次抽籤）
        self.color_key = random.choice(["BLUE", "PINK"])

        # 放在 boss 外圍：下半部外緣（避免跑到上半或背面）
        bw, bh = boss_rect.width, boss_rect.height
        # 範圍約 36°..144°（0.20π..0.80π），偏向畫面下方
        ang = random.uniform(math.pi * 0.20, math.pi * 0.80)
        rx = (bw * 0.42) * math.cos(ang)
        ry = (bh * 0.42) * math.sin(ang)
        ox, oy = int(rx), int(ry)
        self.offset = (ox, oy)

        # 載入圖像（或簡易圈圈）
        path = TARGET_IMG_PATHS.get(self.color_key, "")
        if path and os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, TARGET_SIZE)
        else:
            img = pygame.Surface(TARGET_SIZE, pygame.SRCALPHA)
            color = (80, 80, 255) if self.color_key == "BLUE" else (255, 80, 180)
            pygame.draw.circle(
                img,
                color,
                (TARGET_SIZE[0] // 2, TARGET_SIZE[1] // 2),
                TARGET_SIZE[0] // 2,
                2,
            )

        self.image = img
        self.rect = self.image.get_rect(
            center=(boss_rect.centerx + ox, boss_rect.centery + oy)
        )
        self.timer = TARGET_LIFETIME
        self.alive = True

    def update(self, dt: float, boss_rect: pygame.Rect | None = None):
        self.timer -= dt
        if self.timer <= 0:
            self.alive = False
            return

        # 跟隨 Boss（用 offset 重新定位）
        if boss_rect is not None:
            self.rect.center = (
                boss_rect.centerx + self.offset[0],
                boss_rect.centery + self.offset[1],
            )

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

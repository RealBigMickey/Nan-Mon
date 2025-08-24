# nanmon/progress.py
from __future__ import annotations
import pygame
from .constants import WIDTH, WHITE, FONT_PATH

class Progress:
    """
    垂直進度條（貼右側），底部往上填滿；旁邊顯示文字 'progrss'。
    - boss_time: 幾秒後達成 (可用於觸發 Boss)
    - size: (bar_width, bar_height)
    - margin: 與右邊框的內距
    - top: 與視窗頂端的距離 (避免蓋到 HUD)
    """
    def __init__(self, boss_time: float, size=(12, 160), margin: int = 16, top: int = 80):
        self.boss_time = float(boss_time)
        self.elapsed = 0.0

        self.w, self.h = size
        self.x = WIDTH - margin - self.w  # 靠右
        self.y = top

        # 小字體；改用專案字體 Munro TTF
        try:
            self.font = pygame.font.Font(FONT_PATH, 18)
        except Exception:
            self.font = pygame.font.Font(None, 18)
        self.label = self.font.render("progrss", True, WHITE)
        # 轉成垂直擺放
        self.label_rot = pygame.transform.rotate(self.label, 90)

    def update(self, dt: float):
        self.elapsed = min(self.boss_time, self.elapsed + dt)

    @property
    def ready(self) -> bool:
        return self.elapsed >= self.boss_time

    def draw(self, surface: pygame.Surface):
        # 外框
        border_rect = pygame.Rect(self.x - 2, self.y - 2, self.w + 4, self.h + 4)
        pygame.draw.rect(surface, WHITE, border_rect, 1)

        # 由下往上填滿
        ratio = (self.elapsed / self.boss_time) if self.boss_time > 0 else 1.0
        fill_h = int(self.h * max(0.0, min(1.0, ratio)))
        if fill_h > 0:
            fill_rect = pygame.Rect(self.x, self.y + (self.h - fill_h), self.w, fill_h)
            pygame.draw.rect(surface, WHITE, fill_rect)

        # 文字：貼在進度條左側置中（垂直字）
        label_rect = self.label_rot.get_rect()
        label_rect.centery = self.y + self.h // 2
        label_rect.right = self.x - 6  # 與條之間留點距離
        surface.blit(self.label_rot, label_rect)
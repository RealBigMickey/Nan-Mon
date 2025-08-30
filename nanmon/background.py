# nanmon/background.py
#Teddy add
from __future__ import annotations
import pygame
from typing import Sequence, Tuple

class ScrollingBackground:
    """
    兩張（或多張）圖輪流作為滾動背景。
    - 垂直向下滾動；滾完一個畫面高度後切換下一張。
    - 缺圖時不會崩潰（畫純色備援交給呼叫端）。
    """
    def __init__(
        self,
        image_paths: Sequence[str],
        canvas_size: Tuple[int, int],
        speed_y: float = 40.0,
    ):
        self.w, self.h = canvas_size
        self.speed_y = float(speed_y)
        self.image_paths = list(image_paths)
        self.images: list[pygame.Surface | None] = [None] * len(image_paths)

        if not self.image_paths:
            self.image_paths = [""]
            self.images = [None]

        self.index = 0
        self.offset = 0.0

    def _load_image(self, index: int) -> pygame.Surface | None:
        """Lazily load an image at the given index."""
        if self.images[index] is not None:
            return self.images[index]
        
        path = self.image_paths[index]
        if not path:
            return None
            
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (self.w, self.h))
            self.images[index] = img
            return img
        except Exception:
            self.images[index] = None
            return None

    def update(self, dt: float):
        self.offset += self.speed_y * dt
        if self.offset >= self.h:
            self.offset = 0.0
            self.index = (self.index + 1) % len(self.images)

    def draw(self, surface: pygame.Surface, fallback_color: pygame.Color | Tuple[int,int,int]):
        img = self._load_image(self.index)
        if img is None:
            surface.fill(fallback_color)
            return
        # 當前圖貼兩次，形成無縫垂直捲動
        y = int(self.offset)
        surface.blit(img, (0, y))
        surface.blit(img, (0, y - self.h))

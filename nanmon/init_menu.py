#init_menu.py
#Teddy add
from __future__ import annotations
import os
import pygame
from .constants import WIDTH, HEIGHT, BG_COLOR, WHITE, FPS

class InitMenu:
    """
    兩張圖交替顯示的開始畫面。
    - 按 P 開始遊戲
    - 按 ESC 離開
    - 會自動調整圖片尺寸以符合 WIDTH x HEIGHT
    """
    def __init__(self,
                 image_path_1: str = "nanmon/assets/init_menu_1.jpg",
                 image_path_2: str = "nanmon/assets/init_menu_2.jpg",
                 anim_fps: float = 2.0):
        self.images = []
        for path in (image_path_1, image_path_2):
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
            self.images.append(img)

        self.anim_fps = anim_fps
        self.timer = 0.0
        self.index = 0
        self.running = True
        self.start_game = False

        # 用與遊戲一致的字型風格（目前 game.py 以 Font(None, 18) 為主）
        self.font_title = pygame.font.Font(None, 48)
        self.font_hint  = pygame.font.Font(None, 28)

    def update(self, dt: float):
        self.timer += dt
        if self.timer >= (1.0 / max(0.001, self.anim_fps)):
            self.timer = 0.0
            self.index = (self.index + 1) % len(self.images)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_p:
                self.start_game = True
                self.running = False

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        surface.blit(self.images[self.index], (0, 0))

        # 標題與提示
        title_s = self.font_title.render("Salty/Sweet", True, WHITE)
        hint_s  = self.font_hint.render("Press P to start the game  •  ESC to quit", True, WHITE)

        surface.blit(title_s, (WIDTH//2 - title_s.get_width()//2, HEIGHT//2 - 60))
        surface.blit(hint_s,  (WIDTH//2 - hint_s.get_width()//2,  HEIGHT//2 + 12))

    def loop(self, screen: pygame.Surface, clock: pygame.time.Clock) -> bool:
        """顯示開始畫面，回傳 True 表示開始遊戲，False 表示離開。"""
        while self.running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw(screen)
            pygame.display.flip()
        return self.start_game

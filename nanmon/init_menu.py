#init_menu.py
#Teddy add
from __future__ import annotations
import os
import pygame
from .constants import WIDTH, HEIGHT, BG_COLOR, WHITE, FPS, FONT_PATH

class InitMenu:
    """
    兩張圖交替顯示的開始畫面。
    - 按 Space 開始遊戲
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

        # 使用 Pixel Emulator 字型
        pixel_font_path = os.path.join("nanmon", "assets", "Pixel Emulator.otf")
        # 字體大小縮小，標題 32，提示 18
        self.font_title = pygame.font.Font(pixel_font_path, 32)
        self.font_hint  = pygame.font.Font(pixel_font_path, 18)

        # 初始化選單音效
        sound_path = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
        self.menu_sound = None
        if os.path.exists(sound_path):
            try:
                self.menu_sound = pygame.mixer.Sound(sound_path)
            except Exception:
                self.menu_sound = None

        # 初始化並播放背景音樂
        self.bg_music_playing = False
        bg_music_path = os.path.join("nanmon", "assets", "sounds", "init_menu_background_sounds.wav")
        if os.path.exists(bg_music_path):
            try:
                pygame.mixer.music.load(bg_music_path)
                pygame.mixer.music.play(-1)
                self.bg_music_playing = True
            except Exception:
                self.bg_music_playing = False

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
                if self.menu_sound:
                    self.menu_sound.play()
                self.running = False
            elif event.key == pygame.K_SPACE:
                if self.menu_sound:
                    self.menu_sound.play()
                self.start_game = True
                self.running = False

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        surface.blit(self.images[self.index], (0, 0))

        # 標題與提示
        title_s = self.font_title.render("Salty/Sweet", True, WHITE)
        hint_s  = self.font_hint.render("Press SPACE to start  •  ESC to quit", True, WHITE)

        surface.blit(title_s, (WIDTH//2 - title_s.get_width()//2, HEIGHT//2 - 60))
        surface.blit(hint_s,  (WIDTH//2 - hint_s.get_width()//2,  HEIGHT//2 + 12))

    def loop(self, screen_or_dm, clock: pygame.time.Clock) -> bool:
        """顯示開始畫面，回傳 True 表示開始遊戲，False 表示離開。
        接受 DisplayManager 或 pygame.Surface：若為前者，會使用邏輯畫面+letterboxing 呈現。
        """
        while self.running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            # 支援 DisplayManager（有 get_logical_surface/present 方法）
            if hasattr(screen_or_dm, "get_logical_surface") and hasattr(screen_or_dm, "present"):
                frame = screen_or_dm.get_logical_surface()
                frame.fill(BG_COLOR)
                self.draw(frame)
                screen_or_dm.present()
            else:
                screen = screen_or_dm  # 假設為 pygame.Surface
                self.draw(screen)
                pygame.display.flip()
        # 停止背景音樂
        if self.bg_music_playing:
            pygame.mixer.music.stop()
        return self.start_game

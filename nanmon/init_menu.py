from __future__ import annotations
import os
import pygame
from .constants import WIDTH, HEIGHT, BG_COLOR, WHITE, FPS, FONT_PATH

class InitMenu:
    """
    Start menu with alternating images and simple level selection.
    Returns (start_game: bool, selected_level: int) from loop().
    """
    def __init__(self,
                 image_path_1: str = "nanmon/assets/init_menu_1.jpg",
                 image_path_2: str = "nanmon/assets/init_menu_2.jpg",
                 anim_fps: float = 2.0) -> None:
        # Images
        self.images = []
        for path in (image_path_1, image_path_2):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
            except Exception:
                img = pygame.Surface((WIDTH, HEIGHT))
                img.fill((20, 20, 20))
            self.images.append(img)

        # State
        self.anim_fps = float(anim_fps)
        self.timer = 0.0
        self.index = 0
        self.running = True
        self.start_game = False
        # Level selection
        self.selected_level = 1
        self.max_level = 3
        # Transition (wipe left→right)
        self._fade_out = False
        self._fade_time = 0.0
        self._fade_duration = 0.6

        # Fonts
        self.font_title = pygame.font.Font(FONT_PATH, 32)
        self.font_hint = pygame.font.Font(FONT_PATH, 18)

        # Sounds
        self.menu_sound = None
        try:
            sp = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
            if os.path.exists(sp):
                self.menu_sound = pygame.mixer.Sound(sp)
        except Exception:
            self.menu_sound = None
        self.turn_sound = None
        try:
            pt = os.path.join("nanmon", "assets", "sounds", "page_turn.mp3")
            if os.path.exists(pt):
                self.turn_sound = pygame.mixer.Sound(pt)
        except Exception:
            self.turn_sound = None

        # Music
        self.bg_music_playing = False
        try:
            mp = os.path.join("nanmon", "assets", "sounds", "init_menu_background_sounds.wav")
            if os.path.exists(mp):
                pygame.mixer.music.load(mp)
                pygame.mixer.music.play(-1)
                self.bg_music_playing = True
        except Exception:
            self.bg_music_playing = False

    def update(self, dt: float) -> None:
        self.timer += dt
        if self.timer >= max(0.001, 1.0 / max(0.001, self.anim_fps)):
            self.timer = 0.0
            self.index = (self.index + 1) % len(self.images)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                try:
                    s = self.turn_sound or self.menu_sound
                    if s:
                        s.play()
                except Exception:
                    pass
                self.running = False
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected_level = max(1, self.selected_level - 1)
                try:
                    if self.menu_sound:
                        self.menu_sound.play()
                except Exception:
                    pass
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected_level = min(self.max_level, self.selected_level + 1)
                try:
                    if self.menu_sound:
                        self.menu_sound.play()
                except Exception:
                    pass
            elif event.key == pygame.K_SPACE:
                try:
                    s = self.turn_sound or self.menu_sound
                    if s:
                        s.play()
                except Exception:
                    pass
                self.start_game = True
                self._fade_out = True
                self._fade_time = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        surface.blit(self.images[self.index], (0, 0))
        # Title and hint
        title_s = self.font_title.render("Salty/Sweet", True, WHITE)
        hint_s = self.font_hint.render("Press SPACE to start, ESC to quit", True, WHITE)
        surface.blit(title_s, (WIDTH//2 - title_s.get_width()//2, HEIGHT//2 - 60))
        surface.blit(hint_s, (WIDTH//2 - hint_s.get_width()//2, HEIGHT//2 + 12))
        # Level selector
        level_s = self.font_title.render(f"Level: {self.selected_level}", True, WHITE)
        surface.blit(level_s, (WIDTH//2 - level_s.get_width()//2, HEIGHT//2 + 60))
        hint2 = self.font_hint.render("Use <- / -> (or A/D) to change levels", True, WHITE)
        surface.blit(hint2, (WIDTH//2 - hint2.get_width()//2, HEIGHT//2 + 90))

    def loop(self, screen_or_dm, clock: pygame.time.Clock):
        """Return (start: bool, level: int). Supports DisplayManager or raw Surface."""
        import pygame
        # 強制停止所有音效（包含BOSS音樂）
        try:
            pygame.mixer.stop()
        except Exception:
            pass
        while self.running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            if hasattr(screen_or_dm, "get_logical_surface") and hasattr(screen_or_dm, "present"):
                frame = screen_or_dm.get_logical_surface()
                frame.fill(BG_COLOR)
                self.draw(frame)
                if self._fade_out:
                    self._fade_time += dt
                    t = min(1.0, self._fade_time / max(0.001, self._fade_duration))
                    wipe_w = int(WIDTH * t)
                    if wipe_w > 0:
                        pygame.draw.rect(frame, (0, 0, 0), pygame.Rect(0, 0, wipe_w, HEIGHT))
                    if t >= 1.0:
                        self.running = False
                screen_or_dm.present()
            else:
                screen = screen_or_dm
                self.draw(screen)
                if self._fade_out:
                    self._fade_time += dt
                    t = min(1.0, self._fade_time / max(0.001, self._fade_duration))
                    wipe_w = int(WIDTH * t)
                    if wipe_w > 0:
                        pygame.draw.rect(screen, (0, 0, 0), pygame.Rect(0, 0, wipe_w, HEIGHT))
                    if t >= 1.0:
                        self.running = False
                pygame.display.flip()
        if self.bg_music_playing:
            pygame.mixer.music.stop()
        return (self.start_game, self.selected_level)

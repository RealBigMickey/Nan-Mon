from __future__ import annotations
import os
import pygame
from .constants import WIDTH, HEIGHT, BG_COLOR, WHITE, FPS, FONT_PATH, ASSET_HAT_DIR
from .mouth import Mouth


class InitMenu:
    """Start menu with level and hat selection, plus a frozen live preview."""

    def __init__(self, image_path_1: str = "nanmon/assets/init_menu_1.jpg",
                 image_path_2: str = "nanmon/assets/init_menu_2.jpg",
                 anim_fps: float = 2.0) -> None:
        # Background images
        self.images = []
        for path in (image_path_1, image_path_2):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (WIDTH, HEIGHT))
            except Exception:
                img = pygame.Surface((WIDTH, HEIGHT))
                img.fill((20, 20, 20))
            self.images.append(img)

        # Animation state
        self.anim_fps = float(anim_fps)
        self.timer = 0.0
        self.index = 0
        self.running = True
        self.start_game = False

        # Selectors
        self.selected_level = 1
        self.max_level = 3
        self.hats = self._discover_hats()
        self.hat_index = 0 if self.hats else -1
        self.selected_hat = (self.hats[self.hat_index] if self.hat_index >= 0 else None)
        # Focus: 0=Level 1=Hat
        self.focus = 0

        # Transition (wipe L->R)
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

        # Preview
        self.preview_mouth = None
        self._preview_pos = (WIDTH // 2, HEIGHT // 2 + 190)
        self._preview_bite_t = 0.0

    @staticmethod
    def _hat_display_name(hat: str | None) -> str:
        if not hat:
            return "None"
        base = os.path.splitext(os.path.basename(hat))[0]
        base = base.replace("_", " ").strip()
        return base.title() if base else "None"

    def update(self, dt: float) -> None:
        # animate background
        self.timer += dt
        if self.timer >= max(0.001, 1.0 / max(0.001, self.anim_fps)):
            self.timer = 0.0
            self.index = (self.index + 1) % len(self.images)

        # preview idle bite, no movement
        if self.preview_mouth is not None:
            self._preview_bite_t += dt
            if self._preview_bite_t >= 1.4:
                self.preview_mouth.bite()
                self._preview_bite_t = 0.0
            # zeroed key-state
            class _Zero:
                def __getitem__(self, _):
                    return 0
            self.preview_mouth.rect.center = self._preview_pos
            self.preview_mouth.target.update(0, 0)
            self.preview_mouth.vel.update(0, 0)
            self.preview_mouth.update(dt, _Zero())
            self.preview_mouth.rect.center = self._preview_pos

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
                return
            if event.key in (pygame.K_UP, pygame.K_w):
                self.focus = (self.focus - 1) % 2
                try:
                    if self.menu_sound:
                        self.menu_sound.play()
                except Exception:
                    pass
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.focus = (self.focus + 1) % 2
                try:
                    if self.menu_sound:
                        self.menu_sound.play()
                except Exception:
                    pass
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                if self.focus == 0:
                    self.selected_level = max(1, self.selected_level - 1)
                else:
                    if self.hats:
                        self.hat_index = (self.hat_index - 1) % len(self.hats)
                        self.selected_hat = self.hats[self.hat_index]
                try:
                    if self.menu_sound:
                        self.menu_sound.play()
                except Exception:
                    pass
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if self.focus == 0:
                    self.selected_level = min(self.max_level, self.selected_level + 1)
                else:
                    if self.hats:
                        self.hat_index = (self.hat_index + 1) % len(self.hats)
                        self.selected_hat = self.hats[self.hat_index]
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

        title_s = self.font_title.render("Salty/Sweet", True, WHITE)
        hint_s = self.font_hint.render("Press SPACE to start, ESC to quit", True, WHITE)
        surface.blit(title_s, (WIDTH//2 - title_s.get_width()//2, HEIGHT//2 - 60))
        surface.blit(hint_s, (WIDTH//2 - hint_s.get_width()//2, HEIGHT//2 + 12))

        # Level selector
        level_label = f"Level: {self.selected_level}"
        level_s = self.font_title.render(level_label, True, (255, 255, 0) if self.focus == 0 else WHITE)
        surface.blit(level_s, (WIDTH//2 - level_s.get_width()//2, HEIGHT//2 + 40))

        # Hat selector (pretty name)
        hat_label = f"Hat: {self._hat_display_name(self.selected_hat)}"
        hat_s = self.font_title.render(hat_label, True, (255, 255, 0) if self.focus == 1 else WHITE)
        surface.blit(hat_s, (WIDTH//2 - hat_s.get_width()//2, HEIGHT//2 + 90))

        hint2 = self.font_hint.render("Use Up/Down to switch, Left/Right to change", True, WHITE)
        surface.blit(hint2, (WIDTH//2 - hint2.get_width()//2, HEIGHT//2 + 126))

        # Preview
        if self.preview_mouth is None:
            self.preview_mouth = Mouth(self._preview_pos)
            self.preview_mouth.facing = "RIGHT"
        self.preview_mouth.set_hat(self.selected_hat)
        self.preview_mouth.rect.center = self._preview_pos
        # Draw 1.5x bigger on the start menu
        try:
            self.preview_mouth.draw_scaled(surface, self._preview_pos, scale=1.5)
        except Exception:
            # Fallback if draw_scaled unavailable
            self.preview_mouth.draw(surface)

    def loop(self, screen_or_dm, clock: pygame.time.Clock):
        # stop sounds
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
        return (self.start_game, self.selected_level, self.selected_hat)

    def _discover_hats(self):
        items = []
        try:
            for fname in os.listdir(ASSET_HAT_DIR):
                if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                    items.append(fname)
        except Exception:
            return [None]
        items.sort()
        return [None] + items

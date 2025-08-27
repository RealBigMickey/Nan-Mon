from __future__ import annotations
import os
import math
import pygame
from .constants import WIDTH, HEIGHT, BG_COLOR, WHITE, FPS, FONT_PATH, ASSET_HAT_DIR
from .unlocks import load_unlocked_hats, is_debug_unlock_all, list_all_hats
from .mouth import Mouth


class InitMenu:
    """Start menu with level/hat select. Focus = row; Left/Right change; SPACE start; ESC quit."""

    def __init__(self,
                 image_path_1: str = "nanmon/assets/init_menu_1.jpg",
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
        self.t = 0.0  # UI animation clock

        # --- Required art ---
        # Border 330x220; level previews 300x200
        try:
            self.border_img = pygame.image.load("nanmon/assets/preview_boarder.png").convert_alpha()
        except Exception:
            self.border_img = pygame.Surface((330, 220), pygame.SRCALPHA)
            pygame.draw.rect(self.border_img, (60, 60, 60), self.border_img.get_rect(), border_radius=12)
            pygame.draw.rect(self.border_img, (180, 180, 180), self.border_img.get_rect(), 3, border_radius=12)

        def _load_level_preview(path: str) -> pygame.Surface:
            try:
                img = pygame.image.load(path).convert_alpha()
            except Exception:
                img = pygame.Surface((300, 200), pygame.SRCALPHA)
                img.fill((40, 40, 40, 255))
            if img.get_size() != (300, 200):
                img = pygame.transform.smoothscale(img, (300, 200))
            return img

        self.level_previews = {
            1: _load_level_preview("nanmon/assets/level1_preview.png"),
            2: _load_level_preview("nanmon/assets/level2_preview.png"),
            3: _load_level_preview("nanmon/assets/level3_preview.png"),
        }
        self.max_level = 3
        self.selected_level = 1

        # Hats
        self.hats = self._discover_hats()
        self.hat_index = 0 if self.hats else -1
        self.selected_hat = (self.hats[self.hat_index] if self.hat_index >= 0 else None)

        # Focus: 0=Level, 1=Hat
        self.focus = 0

        # Fade transition
        self._fade_out = False
        self._fade_time = 0.0
        self._fade_duration = 0.6

        # Fonts (smaller title per request)
        self.font_title = pygame.font.Font(FONT_PATH, 30)
        self.font_hint = pygame.font.Font(FONT_PATH, 16)
        self.font_label = pygame.font.Font(FONT_PATH, 26)

        # Sounds (only use menu_select_sounds)
        self.menu_sound = None
        try:
            sp = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
            if os.path.exists(sp):
                self.menu_sound = pygame.mixer.Sound(sp)
        except Exception:
            self.menu_sound = None

        # Music (optional – leave if present)
        self.bg_music_playing = False
        try:
            mp = os.path.join("nanmon", "assets", "sounds", "init_menu_background_sounds.wav")
            if os.path.exists(mp):
                pygame.mixer.music.load(mp)
                pygame.mixer.music.play(-1)
                self.bg_music_playing = True
        except Exception:
            self.bg_music_playing = False

        # Mouth preview (shown only when Hat row focused)
        self._preview_pos = (WIDTH // 2, HEIGHT // 2 + 170)
        self.preview_mouth = Mouth(self._preview_pos)
        self._preview_bite_t = 0.0
        if self.selected_hat:
            try:
                self.preview_mouth.set_hat(self.selected_hat)
            except Exception:
                pass

        # Selection flash for level tile
        self._level_flash_t = 0.0
        self._level_flash_dur = 0.35

    # ---------- Discovery ----------
    def _discover_hats(self):
        try:
            if is_debug_unlock_all():
                items = list_all_hats()
            else:
                unlocked = load_unlocked_hats()
                items = [fn for fn in unlocked if isinstance(fn, str) and os.path.exists(os.path.join(ASSET_HAT_DIR, fn))]
            items.sort()
            return [None] + items
        except Exception:
            return [None]

    # ---------- Helpers ----------
    @staticmethod
    def _hat_display_name(hat: str | None) -> str:
        if not hat:
            return "None"
        base = os.path.splitext(os.path.basename(hat))[0]
        base = base.replace("_", " ").strip()
        return base.title() if base else "None"

    def _play(self, snd):
        try:
            if snd:
                snd.play()
        except Exception:
            pass

    # ---------- Update / Input ----------
    def update(self, dt: float) -> None:
        self.t += dt
        self.timer += dt
        if self.timer >= max(0.001, 1.0 / max(0.001, self.anim_fps)):
            self.timer = 0.0
            self.index = (self.index + 1) % len(self.images)

        self._level_flash_t = max(0.0, self._level_flash_t - dt)

        # idle bite for mouth when hat row focused
        if self.focus == 1 and self.preview_mouth is not None:
            self._preview_bite_t += dt
            if self._preview_bite_t >= 1.4:
                self.preview_mouth.bite()
                self._preview_bite_t = 0.0
            class _Zero:
                def __getitem__(self, _): return 0
            self.preview_mouth.rect.center = self._preview_pos
            self.preview_mouth.target.update(0, 0)
            self.preview_mouth.vel.update(0, 0)
            self.preview_mouth.update(dt, _Zero())
            self.preview_mouth.rect.center = self._preview_pos

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type != pygame.KEYDOWN:
            return

        k = event.key
        if k == pygame.K_ESCAPE:
            self._play(self.menu_sound)
            self.running = False
            return

        if k in (pygame.K_UP, pygame.K_w):
            self.focus = (self.focus - 1) % 2
            self._play(self.menu_sound)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.focus = (self.focus + 1) % 2
            self._play(self.menu_sound)
        elif k in (pygame.K_LEFT, pygame.K_a):
            if self.focus == 0:
                prev = self.selected_level
                self.selected_level = max(1, self.selected_level - 1)
                if self.selected_level != prev:
                    self._level_flash_t = self._level_flash_dur
                self._play(self.menu_sound)
            else:
                if self.hats:
                    self.hat_index = (self.hat_index - 1) % len(self.hats)
                    self.selected_hat = self.hats[self.hat_index]
                    self._play(self.menu_sound)
        elif k in (pygame.K_RIGHT, pygame.K_d):
            if self.focus == 0:
                prev = self.selected_level
                self.selected_level = min(self.max_level, self.selected_level + 1)
                if self.selected_level != prev:
                    self._level_flash_t = self._level_flash_dur
                self._play(self.menu_sound)
            else:
                if self.hats:
                    self.hat_index = (self.hat_index + 1) % len(self.hats)
                    self.selected_hat = self.hats[self.hat_index]
                    self._play(self.menu_sound)
        elif k == pygame.K_SPACE:
            self._play(self.menu_sound)
            self.start_game = True
            self._fade_out = True
            self._fade_time = 0.0

    # ---------- Drawing ----------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        surface.blit(self.images[self.index], (0, 0))

        # Smaller title, moved down; subtle pulse only
        scale = 1.0 + 0.02 * math.sin(self.t * 2.6)
        title_text = "Salty / Sweet"
        title_s = self.font_title.render(title_text, True, WHITE)
        tw, th = title_s.get_width(), title_s.get_height()
        title_scaled = pygame.transform.smoothscale(title_s, (int(tw * scale), int(th * scale)))
        tx = WIDTH // 2 - title_scaled.get_width() // 2
        ty = HEIGHT // 2 - 60  # moved down
        surface.blit(title_scaled, (tx, ty))

        # Minimal hint (no ENTER)
        hint_s = self.font_hint.render("Arrows/WASD to navigate • SPACE start", True, WHITE)
        surface.blit(hint_s, (WIDTH//2 - hint_s.get_width()//2, ty + title_scaled.get_height() + 6))

        # Selector rows
        y0 = HEIGHT//2 - 6 + 36  # slightly lower than title
        self._draw_selector_row(surface, "LEVEL", str(self.selected_level), y0, active=(self.focus == 0))
        self._draw_selector_row(surface, "HAT", self._hat_display_name(self.selected_hat), y0 + 48, active=(self.focus == 1))

        # Preview section (only one shown depending on focus)
        self._draw_preview(surface)

    def _draw_selector_row(self, surface: pygame.Surface, label: str, value: str, y: int, active: bool):
        color = (255, 255, 0) if active else WHITE
        pulse = 1.0 + (0.035 * math.sin(self.t * 6.0)) if active else 1.0
        label_s = self.font_label.render(f"{label}:", True, color)
        value_s = self.font_label.render(value, True, color)
        if pulse != 1.0:
            label_s = pygame.transform.smoothscale(label_s, (int(label_s.get_width()*pulse), int(label_s.get_height()*pulse)))
            value_s = pygame.transform.smoothscale(value_s, (int(value_s.get_width()*pulse), int(value_s.get_height()*pulse)))
        x_center = WIDTH // 2
        gap = 10
        x = x_center - (label_s.get_width() + gap + value_s.get_width()) // 2
        surface.blit(label_s, (x, y))
        surface.blit(value_s, (x + label_s.get_width() + gap, y))

        if active:
            wig = int(2 * math.sin(self.t * 8.0))
            left = self.font_label.render("<", True, color)
            right = self.font_label.render(">", True, color)
            surface.blit(left, (x - 24 + wig, y))
            surface.blit(right, (x + label_s.get_width() + gap + value_s.get_width() + 8 - wig, y))

    def _draw_preview(self, surface: pygame.Surface):
        # Compute a working region but don't draw any background/card.
        top = HEIGHT // 2 + 64
        area = pygame.Rect(40, top, WIDTH - 80, HEIGHT - top - 24)

        if self.focus == 0:
            # LEVEL: single centered border, preview at (+15,+10)
            tile_w, tile_h = self.border_img.get_size()  # 330x220
            tile = pygame.Rect(0, 0, tile_w, tile_h)
            tile.center = area.center

            pv = self.level_previews.get(self.selected_level)
            if pv:
                surface.blit(pv, (tile.x + 15, tile.y + 10))
            surface.blit(self.border_img, tile.topleft)

            # Label (small shadow for legibility over any bg)
            lab_text = f"Level {self.selected_level}"
            lab = self.font_hint.render(lab_text, True, (240, 240, 240))
            lab_sh = self.font_hint.render(lab_text, True, (0, 0, 0))
            lx = tile.centerx - lab.get_width() // 2
            ly = tile.bottom + 6
            surface.blit(lab_sh, (lx + 1, ly + 1))
            surface.blit(lab, (lx, ly))

        else:
            # HAT: live mouth only (no border, no box)
            if self.preview_mouth is None:
                self.preview_mouth = Mouth(self._preview_pos)
                self.preview_mouth.facing = "RIGHT"
            self.preview_mouth.set_hat(self.selected_hat)
            self.preview_mouth._ribbon_left = None
            self.preview_mouth._ribbon_right = None
            pos = (area.centerx, area.centery + 10)
            self.preview_mouth.rect.center = pos
            try:
                self.preview_mouth.draw_scaled(surface, pos, scale=2.25)
            except Exception:
                self.preview_mouth.draw(surface)


    # ---------- Main loop ----------
    def loop(self, screen_or_dm, clock: pygame.time.Clock):
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

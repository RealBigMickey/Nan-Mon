from __future__ import annotations
import os
import random
import math
import pygame
from .constants import WIDTH, HEIGHT, ASSET_FOOD_DIR, FOOD_SIZE, FONT_PATH, ASSET_HAT_DIR
from .unlocks import (
    load_unlocked_hats,
    unlock_hat,
    is_debug_unlock_all,
    list_all_hats,
)
from .effects import Smoke
from .models import KINDS, EatenCounters
from .mouth import Mouth

FINISH_BG = pygame.Color(245, 245, 245)
# Faster finish-screen physics
GRAVITY = 2400.0
AIR_DRAG = 0.995
GROUND_FRICTION = 0.88
SLEEP_SPEED = 12.0
HITBOX_SCALE = 0.86
SLIDE_SCALE = 0.22


class SpewItem:
    def __init__(self, kind: str, img: pygame.Surface, cx: float, cy: float, vx: float, vy: float):
        self.kind = kind
        self.img = img
        self.cx = cx
        self.cy = cy
        self.vx = vx
        self.vy = vy
        r = min(img.get_width(), img.get_height()) * 0.5 * HITBOX_SCALE
        self.r = float(r)
        self.rect = img.get_rect(center=(int(cx), int(cy)))
        self.asleep = False
        self._final_grade: str | None = None

    def update_rect(self) -> None:
        self.rect = self.img.get_rect(center=(int(self.cx), int(self.cy)))


class FinishScreen:
    def __init__(self, eaten: EatenCounters, level: int, score: int, hat: str | None = None):
        # Sound placeholders
        self._drum_snd = None
        self._spit_out_snd = None
        self._bgm_snd = None
        self._cymbal_snd = None
        self._applause_snd = None

        # Store level, score, and eaten stats (including correct count)
        self.level = level
        self.eaten = eaten
        self.score = score
        self._y_offset = 60
        self._final_grade: str | None = None

        # Scrolling background setup
        self._bg_img = None
        self._bg_h = 0
        self._bg_y = 0.0
        self._bg_speed = 60.0

        # Counts and ordering
        self.counts = {k: int(eaten.per_type.get(k, 0)) for k in KINDS}
        self.order = [k for k in KINDS if self.counts[k] > 0]
        self.shown = {k: 0 for k in KINDS}
        self.current_idx = 0
        self.done = (sum(self.counts.values()) == 0)

        # Load food images (nearest-neighbor)
        self.food_imgs = {}
        for k in KINDS:
            path = os.path.join(ASSET_FOOD_DIR, f"{k}.png")
            try:
                img = pygame.image.load(path).convert_alpha()
            except Exception:
                img = pygame.Surface(FOOD_SIZE, pygame.SRCALPHA)
                pygame.draw.rect(img, pygame.Color(200, 200, 200), img.get_rect(), 2)
            self.food_imgs[k] = pygame.transform.scale(img, FOOD_SIZE)

        # Big mouth on right (moved upward)
        self.mouth = Mouth((int(WIDTH * 0.82), int(HEIGHT * 0.72) - self._y_offset))
        if hat:
            try:
                self.mouth.set_hat(hat)
            except Exception:
                pass
        self.mouth.facing = "LEFT"
        self.mouth_scale = 3.5

        # Collections
        self.flying = []
        self.settled = []

        # Pile region and cadence
        self.pile_left = 20
        self.pile_right = int(WIDTH * 0.74)
        self.ground_y = int(HEIGHT * 0.9) - self._y_offset
        self.spew_timer = 0.0
        self.spew_start_interval = 0.30
        self.spew_end_interval = max(0.001, 0.25 / 3.0)
        self.spew_accel_count = 10
        self.spew_count = 0
        self._bite_delay_timer = -1.0
        self._bite_duration = 0.06
        # Initial delay before any spew begins
        self._spew_delay = 1.0

        # Fonts
        self.font = pygame.font.Font(FONT_PATH, 28)
        self.font_small = pygame.font.Font(FONT_PATH, 22)
        self.font_big = pygame.font.Font(FONT_PATH, 96)
        self.font_title = pygame.font.Font(FONT_PATH, 48)
        self.font_list = pygame.font.Font(FONT_PATH, 34)

        # Grade reveal state and optional sounds
        self.show_grade = False
        self.grade_reveal_started = False
        self.grade_reveal_timer = 0.0

        # Result sounds and channels
        self._drum_chan = None
        self._pop_snd = None
        self._cheer_snd = None
        self._cheer_chan = None
        self._spray_snd = None

        # Celebration state
        self._reveal_time = 0.0
        self._confetti = []
        self._confetti_trickle = 0.0
        self._confetti_accum = 0.0
        self._smoke = []
        self._flash_time = 0.0
        self._impact_jitter_time = 0.0
        self._impact_jitter_mag = 0.0

        # Unlock animation assets
        self._mystery_img = None
        self._lighting_img = None
        self._unlock_hat_img = None
        self._unlock_hat_name = None
        self._unlock_hat_file = None

        # Rank images (S, A, B, C, D, F)
        self._rank_imgs = {}
        self._rank_base_h = int(HEIGHT * 0.24)

        # Clapping sprite (shown for ranks A and S)
        self._clap_img = None
        self._clap_phase = 0.0
        self._need_smoke_spawn = False

        # Optional images (scoreboard, plate)
        self._scoreboard_img = None
        self._scoreboard_h = 0
        self._plate_img = None
        self._plate_h = 0

        # Optional container hitbox (not drawn)
        self._container_mask = None
        self._container_rect = None
        self._container_img = None  # original image
        self._walls_mask = None   # outline/solid pixels from image
        self._interior_mask = None  # filled interior computed
        self._active_mask = None   # mask used for collisions
        try:
            spit_path = os.path.join("nanmon", "assets", "sounds", "spit_out.wav")
            if os.path.exists(spit_path):
                self._spit_out_snd = pygame.mixer.Sound(spit_path)
            bgm_path = os.path.join("nanmon", "assets", "sounds", "final_screen_bg_sounds.wav")
            if os.path.exists(bgm_path):
                self._bgm_snd = pygame.mixer.Sound(bgm_path)

            cymbal_path = os.path.join("nanmon", "assets", "sounds", "cymbal_sounds.wav")
            if os.path.exists(cymbal_path):
                self._cymbal_snd = pygame.mixer.Sound(cymbal_path)
                self._cymbal_snd.set_volume(1.0)
            applause_path = os.path.join("nanmon", "assets", "sounds", "applause_sounds.wav")
            if os.path.exists(applause_path):
                self._applause_snd = pygame.mixer.Sound(applause_path)
                self._applause_snd.set_volume(1.0)
            drum_path = os.path.join("nanmon", "assets", "sounds", "drum_sounds.wav")
            if os.path.exists(drum_path):
                self._drum_snd = pygame.mixer.Sound(drum_path)
                self._drum_snd.set_volume(1.0)
        except Exception:
            pass
        # Sounds
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            for name, attr in (("drumroll.ogg", "_drum_snd"), ("cheer.ogg", "_cheer_snd"), ("spray.ogg", "_spray_snd"), ("pop.ogg", "_pop_snd"), ("pop.wav", "_pop_snd")):
                p = os.path.join("nanmon", "assets", name)
                if os.path.exists(p):
                    setattr(self, attr, pygame.mixer.Sound(p))
        except Exception:
            self._drum_snd = None

        # Rank images
        for letter in ["S", "A", "B", "C", "D", "F"]:
            try:
                p = os.path.join("nanmon", "assets", "clear_screen", f"{letter}.png")
                img = pygame.image.load(p).convert_alpha()
                h = max(1, img.get_height())
                scale_h = max(24, self._rank_base_h)
                scale_w = int(img.get_width() * (scale_h / h))
                img = pygame.transform.scale(img, (scale_w, scale_h))
                self._rank_imgs[letter] = img
            except Exception:
                pass

        # Scoreboard
        for fname in ("score_board.png", "scoreboard.png"):
            p = os.path.join("nanmon", "assets", "clear_screen", fname)
            if os.path.exists(p):
                try:
                    sb = pygame.image.load(p).convert_alpha()
                    self._scoreboard_img = sb
                    self._scoreboard_h = sb.get_height() or 0
                    break
                except Exception:
                    pass

        # Plate (bottom)
        p = os.path.join("nanmon", "assets", "clear_screen", "plate.png")
        if os.path.exists(p):
            try:
                pl = pygame.image.load(p).convert_alpha()
                if pl.get_width() != WIDTH:
                    new_w = WIDTH
                    new_h = int(pl.get_height() * (new_w / max(1, pl.get_width())))
                    pl = pygame.transform.scale(pl, (new_w, new_h))
                self._plate_img = pl
                self._plate_h = pl.get_height() or 0
            except Exception:
                self._plate_img = None
                self._plate_h = 0

        # Container hitbox (mask) - not drawn; use as-is, no scaling
        p = os.path.join("nanmon", "assets", "clear_screen", "container_hitbox.png")
        if os.path.exists(p):
            try:
                cont = pygame.image.load(p).convert_alpha()
                # Use original size directly (expected WIDTH x HEIGHT)
                self._container_img = cont
                w, h = cont.get_size()

                # Raw mask from alpha (opaque=solid)
                self._walls_mask = pygame.mask.from_surface(cont)

                # Compute interior mask via flood-fill of outside
                full = pygame.mask.Mask((w, h), fill=True)
                outside = full.copy()
                outside.erase(self._walls_mask, (0, 0))
                seed = None
                for pt in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)):
                    if outside.get_at(pt):
                        seed = pt
                        break
                interior = None
                if seed is not None:
                    try:
                        outside_cc = outside.connected_component(seed)
                        interior = full.copy()
                        if outside_cc is not None:
                            interior.erase(outside_cc, (0, 0))
                        interior.erase(self._walls_mask, (0, 0))
                    except Exception:
                        interior = None
                self._interior_mask = interior

                # FIX: choose walls by default; toggle with 'm' if you want to inspect interior
                self._active_mask = self._walls_mask

                self._container_rect = cont.get_rect()
                # FIX: make alignment unambiguous — image top-left at screen (0,0)
                self._container_rect.topleft = (0, 0)
            except Exception:
                self._container_mask = None
                self._container_rect = None
                self._container_img = None
                self._walls_mask = None
                self._interior_mask = None
                self._active_mask = None

        # Background
        p = os.path.join("nanmon", "assets", "clear_screen", "background.png")
        if os.path.exists(p):
            try:
                bg = pygame.image.load(p).convert()
                if bg.get_width() != WIDTH:
                    new_w = WIDTH
                    new_h = int(bg.get_height() * (new_w / max(1, bg.get_width())))
                    bg = pygame.transform.scale(bg, (new_w, new_h))
                self._bg_img = bg
                self._bg_h = bg.get_height()
                self._bg_y = 0.0
            except Exception:
                self._bg_img = None
                self._bg_h = 0

        # Clapping image
        p = os.path.join("nanmon", "assets", "clapping.png")
        if not os.path.exists(p):
            p = os.path.join("nanmon", "assets", "clear_screen", "clapping.png")
        if os.path.exists(p):
            try:
                cim = pygame.image.load(p).convert_alpha()
                cw = max(1, cim.get_width())
                scale_w = WIDTH
                scale_h = int(cim.get_height() * (scale_w / cw))
                self._clap_img = pygame.transform.scale(cim, (scale_w, scale_h))
            except Exception:
                self._clap_img = None

        # Mystery box and lighting assets (optional)
        try:
            p_box = os.path.join("nanmon", "assets", "clear_screen", "mystery_box.png")
            if os.path.exists(p_box):
                box = pygame.image.load(p_box).convert_alpha()
                # scale box to ~30% width
                target_w = int(WIDTH * 0.3)
                scale = target_w / max(1, box.get_width())
                target_h = max(1, int(box.get_height() * scale))
                self._mystery_img = pygame.transform.scale(box, (target_w, target_h))
        except Exception:
            self._mystery_img = None
        try:
            p_lt = os.path.join("nanmon", "assets", "clear_screen", "Lighting.png")
            if os.path.exists(p_lt):
                lt = pygame.image.load(p_lt).convert_alpha()
                # Keep original size; will draw at (0,0) without scaling
                self._lighting_img = lt
        except Exception:
            self._lighting_img = None

    @staticmethod
    def _hat_display_name(hat: str | None) -> str:
        if not hat:
            return "Unknown"
        base = os.path.splitext(os.path.basename(hat))[0]
        base = base.replace("_", " ").strip()
        return base.title() if base else "Unknown"

    def _choose_random_hat(self) -> tuple[str | None, pygame.Surface | None]:
        """Pick a random hat image, preferring hats not yet unlocked.
        Returns (file_name, scaled_surface)."""
        all_hats = list_all_hats()
        if not all_hats:
            return (None, None)
        unlocked = load_unlocked_hats()
        if not is_debug_unlock_all():
            candidates = [h for h in all_hats if h not in unlocked]
        else:
            candidates = list(all_hats)
        if not candidates:
            candidates = list(all_hats)
        pick = random.choice(candidates)
        try:
            path = os.path.join(ASSET_HAT_DIR, pick)
            img = pygame.image.load(path).convert_alpha()
            # scale hat to a nice showcase size
            max_w = int(WIDTH * 0.28)
            max_h = int(HEIGHT * 0.18)
            w, h = img.get_size()
            scale = min(max_w / max(1, w), max_h / max(1, h), 1.5)
            sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
            simg = pygame.transform.scale(img, (sw, sh))
            return (pick, simg)
        except Exception:
            return (pick, None)

    def _play_hat_unlock(self, dm, clock) -> None:
        """Show a short unlock animation with a mystery box, lightning, and a random hat reveal."""
        # Prepare hat choice
        hat_file, hat_img = self._choose_random_hat()
        self._unlock_hat_file = hat_file
        self._unlock_hat_name = self._hat_display_name(hat_file)
        self._unlock_hat_img = hat_img

        # Fresh confetti for unlock sequence
        self._confetti = []

        t = 0.0                 # staged timing for reveal beats (can clamp)
        dur = 2.6               # staging window length
        elapsed = 0.0           # unbounded timer for continuous effects (blink/rotation)
        stage_pop = False
        pop_time: float | None = None
        stage_cheer = False

        # Start a drum roll if available
        try:
            if self._drum_snd is not None:
                self._drum_snd.play()
        except Exception:
            pass

        # Snapshot the current clear-screen frame to keep as the background
        base_bg = dm.get_logical_surface().copy()

        while True:
            dt = clock.tick(60) / 1000.0
            elapsed += dt
            if t < dur:
                t += dt

            surf = dm.get_logical_surface()
            # Draw the captured background first
            surf.blit(base_bg, (0, 0))
            # Dim the background
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            surf.blit(overlay, (0, 0))

            # Box position and subtle animation (hide once the hat appears)
            if t < 1.55:
                bx = WIDTH // 2
                box_img = self._mystery_img
                if box_img is not None:
                    bw, bh = box_img.get_size()
                    # bounce in first 0.6s
                    scale = 1.0
                    if t < 0.6:
                        phase = t / 0.6
                        scale = 0.9 + 0.1 * (1 - math.cos(phase * math.pi))
                    # slight shake 0.6-1.6s
                    jitter_x = 0
                    if 0.6 <= t <= 1.6:
                        jitter_x = random.randint(-3, 3)
                    # strong rapid rotation while unlocking 0.6-1.6s
                    angle = 0.0
                    if 0.6 <= t <= 1.6:
                        phase = (t - 0.6)
                        angle = 28.0 * math.sin(phase * 2 * math.pi * 8.0)
                    sbw, sbh = int(bw * scale), int(bh * scale)
                    sbw = max(1, sbw); sbh = max(1, sbh)
                    scaled_box = pygame.transform.scale(box_img, (sbw, sbh))
                    # rotate after scaling for crisper result
                    if angle != 0.0:
                        scaled_box = pygame.transform.rotate(scaled_box, angle)
                    by = int(HEIGHT * 0.60)
                    rect = scaled_box.get_rect(center=(bx + jitter_x, by))
                    surf.blit(scaled_box, rect)
                else:
                    # fallback placeholder
                    rect = pygame.Rect(WIDTH//2 - 120, int(HEIGHT*0.60) - 80, 240, 160)
                    pygame.draw.rect(surf, (120, 120, 140), rect)
                    pygame.draw.rect(surf, (40, 40, 60), rect, 4)

            # At 1.6s, POP + lightning + reveal
            if t >= 1.6 and not stage_pop:
                stage_pop = True
                pop_time = elapsed
                try:
                    if self._pop_snd is not None:
                        self._pop_snd.play()
                    elif self._spray_snd is not None:
                        self._spray_snd.play()
                except Exception:
                    pass
                # stop drum if rolling
                try:
                    if self._drum_chan is not None:
                        self._drum_chan.stop()
                except Exception:
                    pass
                # Confetti burst when popping
                self._spawn_confetti(burst=220)
                # Persist unlock
                try:
                    if self._unlock_hat_file:
                        unlock_hat(self._unlock_hat_file)
                except Exception:
                    pass

            # Lightning flash window 1.6-1.9
            if self._lighting_img is not None and 1.6 <= t <= 1.9:
                alpha = int(255 * max(0.0, 1.0 - (t - 1.6) / 0.3))
                lt = self._lighting_img.copy()
                # apply overall alpha via multiply (no scaling, placed at (0,0))
                if alpha < 255:
                    aoverlay = pygame.Surface(lt.get_size(), pygame.SRCALPHA)
                    aoverlay.fill((255, 255, 255, alpha))
                    lt.blit(aoverlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(lt, (0, 0))

            # Hat reveal rising from the box after 1.55s (draw at 1.5x scale)
            if self._unlock_hat_img is not None and t >= 1.55:
                hi = self._unlock_hat_img
                hw, hh = hi.get_size()
                sw = max(1, int(hw * 1.5))
                sh = max(1, int(hh * 1.5))
                scaled_hi = pygame.transform.scale(hi, (sw, sh))
                # slow continuous rotation after reveal using unbounded elapsed
                angle = max(0.0, (elapsed - 1.55)) * 60.0  # deg/sec
                rotated_hi = pygame.transform.rotate(scaled_hi, angle)
                hr = rotated_hi.get_rect()
                rise = min(1.0, (t - 1.55) / 0.7)
                y = int(HEIGHT * 0.62) - int(160 * rise) + 130
                hr.midbottom = (WIDTH // 2, y)
                surf.blit(rotated_hi, hr)
                if not stage_cheer and t >= 1.8:
                    stage_cheer = True
                    try:
                        if self._cheer_snd is not None:
                            self._cheer_snd.play()
                    except Exception:
                        pass

            # Texts (only after the hat starts to emerge), smaller and clamped to width
            if t >= 1.55:
                # Title smaller
                title_surf = self.font_list.render("New Hat Unlocked!", True, pygame.Color(255, 255, 0))
                tx = (WIDTH - title_surf.get_width()) // 2
                ty = int(HEIGHT * 0.16)
                surf.blit(title_surf, (tx, ty))

                if self._unlock_hat_name:
                    name_surf = self.font.render(self._unlock_hat_name, True, pygame.Color(255, 255, 255))
                    # Clamp to 90% screen width if needed
                    max_w = int(WIDTH * 0.9)
                    if name_surf.get_width() > max_w:
                        scale = max_w / name_surf.get_width()
                        new_w = max(1, int(name_surf.get_width() * scale))
                        new_h = max(1, int(name_surf.get_height() * scale))
                        name_surf = pygame.transform.scale(name_surf, (new_w, new_h))
                    nx = (WIDTH - name_surf.get_width()) // 2
                    ny = ty + title_surf.get_height() + 6
                    surf.blit(name_surf, (nx, ny))

            # Update and draw confetti using finish screen effect
            self._update_confetti(dt)
            self._draw_confetti(surf)

            # After POP, show continue prompt centered near bottom with real blinking
            if stage_pop and pop_time is not None:
                since_pop = max(0.0, elapsed - pop_time)
                if since_pop >= 0.15:
                    # blink at ~2Hz based on unbounded elapsed time
                    if (int(since_pop * 2) % 2) == 0:
                        prompt = "Press space to continue"
                        pr = self.font_small.render(prompt, True, pygame.Color(255, 255, 255))
                        px = (WIDTH - pr.get_width()) // 2
                        py = HEIGHT - max(28, int(self.font_small.get_linesize() * 1.6)) - 200
                        self._draw_text_outlined(surf, self.font_small, prompt, (px, py))

            dm.present()

            # Only exit when SPACE/ENTER is pressed after the box has opened (pop)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if stage_pop:
                        return
                    # ignore presses before the box opens

    # --- Celebration helpers ---
    def _spawn_confetti(self, burst: int = 80):
        for _ in range(burst):
            x = random.uniform(0, WIDTH)
            y = random.uniform(0, HEIGHT)
            vx = random.uniform(-160, 160)
            vy = random.uniform(-120, 220)
            size = random.randint(3, 6)
            color = random.choice([
                (255, 80, 80), (255, 200, 60), (120, 255, 120), (120, 180, 255), (220, 120, 255)
            ])
            life = random.uniform(0.8, 1.8)
            self._confetti.append({
                "x": x, "y": y, "vx": vx, "vy": vy, "size": size, "color": color,
                "life": life, "age": 0.0, "spin": random.uniform(-6, 6)
            })

    def _update_confetti(self, dt: float):
        alive = []
        for p in self._confetti:
            p["age"] += dt
            if p["age"] > p["life"]:
                continue
            p["vy"] += GRAVITY * 0.4 * dt
            p["vx"] *= 0.995
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            alive.append(p)
        self._confetti = alive

    def _draw_confetti(self, surf: pygame.Surface):
        for p in self._confetti:
            t = max(0.0, min(1.0, p["age"] / p["life"]))
            alpha = int(255 * (1.0 - t))
            s = max(1, int(p["size"]))
            rect = pygame.Rect(int(p["x"]), int(p["y"]), s, s)
            col = (*p["color"], alpha)
            tile = pygame.Surface((s, s), pygame.SRCALPHA)
            tile.fill(col)
            surf.blit(tile, rect)

    # --- Text helper: white text with black outline ---
    def _draw_text_outlined(self, surf: pygame.Surface, font: pygame.font.Font, text: str, pos: tuple[int, int]):
        white = font.render(text, True, pygame.Color(255, 255, 255))
        black = font.render(text, True, pygame.Color(0, 0, 0))
        x, y = pos
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
            surf.blit(black, (x + dx, y + dy))
        surf.blit(white, pos)

    # --- Mask helper: sample mask using screen coordinates ---
    def _mask_solid_at_screen(self, sx: float, sy: float) -> bool:
        if self._active_mask is None or self._container_rect is None:
            return False
        mx = int(sx) - self._container_rect.left
        my = int(sy) - self._container_rect.top
        if mx < 0 or my < 0 or mx >= self._active_mask.get_size()[0] or my >= self._active_mask.get_size()[1]:
            return False
        return bool(self._active_mask.get_at((mx, my)))

    # --- Physics helpers ---
    def _resolve_ground(self, it: SpewItem) -> None:
        if it.cy + it.r >= self.ground_y:
            it.cy = self.ground_y - it.r
            if it.vy > 0:
                it.vy = 0.0
            it.vx *= GROUND_FRICTION
            if abs(it.vx) < SLEEP_SPEED:
                it.vx = 0.0
                it.asleep = True

    def _resolve_container(self, it: SpewItem) -> None:
        if self._active_mask is None or self._container_rect is None:
            self._resolve_ground(it)
            return

        # 只有往下掉落時才受遮罩限制，往上拋不做遮罩碰撞
        if it.vy < 0:
            # 食物往上拋時不做任何遮罩碰撞
            return

        # FIX: do NOT clamp to screen bottom when a container mask exists
        # (We still keep a small safety if something escapes entirely)
        if self._active_mask is None and it.cy + it.r >= HEIGHT:
            it.cy = HEIGHT - it.r
            it.vy = 0.0

        # Only resolve contact when moving downward and touching SOLID below
        # 只有往下掉落才判斷遮罩
        # Sample directly below the circle
        cx = float(min(WIDTH - 1, max(0, it.cx)))
        bottom = float(min(HEIGHT - 1, max(0, it.cy + it.r + 1)))
        if self._mask_solid_at_screen(cx, bottom):
            # Step upward to the first non-solid pixel to sit on the surface
            max_probe = 12
            y = bottom
            for _ in range(max_probe):
                if not self._mask_solid_at_screen(cx, y):
                    break
                y -= 1
                if y < 0:
                    break
            # Position so the circle just touches the surface
            it.cy = float(y) - it.r
            it.vy = 0.0
            # Apply ground friction and sleep when slow
            it.vx *= GROUND_FRICTION
            if abs(it.vx) < SLEEP_SPEED:
                it.vx = 0.0
                it.asleep = True

        # Optional: simple side push-out to avoid sticking into walls
        # Left sample
        cx_left = float(max(0, it.cx - it.r - 1))
        cy_mid = float(it.cy)
        if self._mask_solid_at_screen(cx_left, cy_mid):
            it.cx = float(int(it.cx) + 1)
            it.vx = max(0.0, it.vx)
        # Right sample
        cx_right = float(min(WIDTH - 1, it.cx + it.r + 1))
        if self._mask_solid_at_screen(cx_right, cy_mid):
            it.cx = float(int(it.cx) - 1)
            it.vx = min(0.0, it.vx)

    def _circle_collide(self, a: SpewItem, b: SpewItem) -> bool:
        dx = a.cx - b.cx
        dy = a.cy - b.cy
        rs = a.r + b.r
        return (dx * dx + dy * dy) < (rs * rs)

    def _resolve_circle(self, a: SpewItem, b: SpewItem) -> None:
        dx = a.cx - b.cx
        dy = a.cy - b.cy
        dist2 = dx * dx + dy * dy
        if dist2 == 0:
            dx, dy = 0.01, -0.01
            dist2 = dx * dx + dy * dy
        dist = dist2 ** 0.5
        overlap = a.r + b.r - dist
        if overlap <= 0:
            return
        nx = dx / dist
        ny = dy / dist
        a.cx += nx * overlap
        a.cy += ny * overlap
        vn = a.vx * nx + a.vy * ny
        if vn < 0:
            a.vx -= vn * nx
            a.vy -= vn * ny
        tx, ty = -ny, nx
        at = SLIDE_SCALE * GRAVITY * ty
        a.vx += tx * at * (1.0 / 60.0)
        a.vy += ty * at * (1.0 / 60.0)
        a.vx *= 0.995
        a.vy *= 0.995

    # --- Spawning ---
    def _spawn_spew(self, kind: str) -> None:
        img = self.food_imgs[kind]
        x0 = self.mouth.rect.centerx - 20
        y0 = self.mouth.rect.centery - 20
        margin = img.get_width() * 0.5
        a = self.pile_left + margin
        b = min(self.pile_right - margin, self.mouth.rect.centerx - margin - 140)
        if b <= a:
            b = a + 1
        tx = int(random.triangular(a, b, a))
        ty = self.ground_y - img.get_height()
        T = random.uniform(0.7, 1.1)  # 增加拋物線時間範圍
        vx = (tx - x0) / T + random.uniform(-16, 16)  # 增加橫向隨機性
        vy = (ty - y0 - 0.5 * GRAVITY * T * T) / T + random.uniform(-18, 6)  # 增加拋物線高度
        self.flying.append(SpewItem(kind, img, x0, y0, vx, vy))
        # Play spit_out sound on spawn (if available)
        if self._spit_out_snd is not None:
            try:
                self._spit_out_snd.play()
            except Exception:
                pass

    def _spawn_settled(self, kind: str) -> None:
        """Instantly place a food item onto the pile as if it has finished falling."""
        img = self.food_imgs[kind]
        margin = img.get_width() * 0.5
        a = self.pile_left + margin
        b = min(self.pile_right - margin, self.mouth.rect.centerx - margin - 140)
        if b <= a:
            b = a + 1
        tx = int(random.triangular(a, b, a))
        ty = self.ground_y - img.get_height()
        it = SpewItem(kind, img, float(tx), float(ty), 0.0, 0.0)
        it.asleep = True
        it.update_rect()
        self.settled.append(it)

    def _skip_to_end(self) -> None:
        """Skip animations: place all remaining items, reveal grade and scores immediately."""
        # Place all remaining food immediately
        for k in self.order:
            remaining = max(0, int(self.counts.get(k, 0)))
            if remaining:
                for _ in range(remaining):
                    self._spawn_settled(k)
                self.shown[k] += remaining
                self.counts[k] = 0
        self.flying.clear()
        self.done = True

        # Stop any drum roll
        try:
            if self._drum_chan is not None:
                self._drum_chan.stop()
        except Exception:
            pass

        # Reveal grade now
        self.grade_reveal_started = True
        self.grade_reveal_timer = 0.0
        self.show_grade = True
        self._reveal_time = 0.0
        self._final_grade = self._grade_letter()

        # Celebrate like normal reveal
        if self._final_grade != 'F':
            self._spawn_confetti(burst=400)
            self._confetti_trickle = 1.2
        else:
            self._confetti_trickle = 0.0
        self._confetti_accum = 0.0
        self._flash_time = 0.14
        self._impact_jitter_time = 0.32
        self._impact_jitter_mag = 8.0
        self._need_smoke_spawn = (self._final_grade != 'F')

        # Play cymbal/applause once
        try:
            if self._cymbal_snd is not None:
                self._cymbal_snd.play()
            if self._final_grade in ("S", "A", "B", "C", "D") and self._applause_snd is not None:
                self._applause_snd.play()
        except Exception:
            pass

    def _next_spew(self) -> None:
        while not self.done:
            if self.current_idx >= len(self.order):
                self.done = True
                return
            kind = self.order[self.current_idx]
            if self.counts[kind] <= 0:
                self.current_idx += 1
                continue
            self.counts[kind] -= 1
            self.shown[kind] += 1
            self._spawn_spew(kind)
            self.mouth.bite_timer = 0.045
            break

    def _grade_letter(self) -> str:
        base = 100
        level = self.level
        # different levels have different requirements for ranks
        if level == 1:
            base = 23
        elif level == 2:
            base = 30
        elif level == 3:
            base = 40
        if self.eaten.total == 0:
            final_score = 0
        else:
            final_score = self.score * math.sqrt(self.eaten.correct / self.eaten.total)
    # ...existing code...

        if final_score >= 2.0 * base:
            return "S"
        if final_score >= 1.5 * base:
            return "A"
        if final_score >= 1.2 * base:
            return "B"
        if final_score >= 1.0 * base:
            return "C"
        if final_score >= 0.8 * base:
            return "D"
        return "F"

    def loop(self, dm, clock):
        # 結算畫面開始時強制停止boss音樂（避免殘留）
        try:
            import pygame
            pygame.mixer.stop()
            # ...existing code...
        except Exception as e:
            pass
        # 播放結尾畫面背景音樂
        bgm_played = False
        drum_played = False
        cymbal_played = False
        self._applause_played = False
        running = True
        # Fade-in from white for the result screen
        fade_in_t = 0.0
        fade_in_dur = 0.5
        # Transition sound
        turn_snd = None
        letter = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pt_path = os.path.join("nanmon", "assets", "sounds", "page_turn.mp3")
            if os.path.exists(pt_path):
                turn_snd = pygame.mixer.Sound(pt_path)
        except Exception:
            turn_snd = None
        fixed_mouth_pos = (int(WIDTH * 0.82), int(HEIGHT * 0.72) - self._y_offset)
        while running:
            # 背景音樂只播放一次
            if not bgm_played and self._bgm_snd is not None:
                try:
                    self._bgm_snd.play()
                    bgm_played = True
                except Exception:
                    pass
            dt = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # 播放選單音效
                        try:
                            if turn_snd:
                                turn_snd.play()
                            else:
                                if not pygame.mixer.get_init():
                                    pygame.mixer.init()
                                sound_path = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
                                if os.path.exists(sound_path):
                                    pygame.mixer.Sound(sound_path).play()
                        except Exception:
                            pass
                        return
                    if event.key == pygame.K_SPACE:
                        # If not revealed yet, skip to final state (place all items, show grade now)
                        if not self.show_grade:
                            self._skip_to_end()
                            continue
                        # Already showing grade: proceed to next screen
                        # 播放選單音效
                        try:
                            if turn_snd:
                                turn_snd.play()
                            else:
                                if not pygame.mixer.get_init():
                                    pygame.mixer.init()
                                sound_path = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
                                if os.path.exists(sound_path):
                                    pygame.mixer.Sound(sound_path).play()
                        except Exception:
                            pass
                        # If grade is A/S, play unlock sequence before exit
                        try:
                            letter = self._final_grade or self._grade_letter()
                        except Exception:
                            letter = None
                        # 強制 S 級分數顯示神秘箱動畫
                        if letter == "S":
                            self._play_hat_unlock(dm, clock)
                        # All ranks continue to next level
                        return ("NEXT_LEVEL", int(self.level) + 1)

            keys = pygame.key.get_pressed()
            self.mouth.update(dt, keys)
            self.mouth.rect.center = fixed_mouth_pos
            self.mouth.facing = "LEFT"

            if self._bite_delay_timer >= 0.0:
                self._bite_delay_timer -= dt
                if self._bite_delay_timer <= 0.0:
                    self.mouth.bite()
                    self.mouth.bite_timer = float(self._bite_duration)
                    self._bite_delay_timer = -1.0

            if not self.done:
                # Respect initial delay before starting spew cadence
                if self._spew_delay > 0.0:
                    self._spew_delay = max(0.0, self._spew_delay - dt)
                else:
                    self.spew_timer += dt
                    while True:
                        progress = min(1.0, self.spew_count / float(max(1, self.spew_accel_count)))
                        current_interval = self.spew_start_interval + (self.spew_end_interval - self.spew_start_interval) * progress
                        if self.spew_timer < current_interval:
                            break
                        self.spew_timer -= current_interval
                        self._next_spew()
                        self.spew_count += 1
            else:
                # 吐完食物後才播放鼓聲，並延長分數揭曉等待
                if not self.grade_reveal_started:
                    self.grade_reveal_started = True
                    self.grade_reveal_timer = 2.2  # 可調整延長時間
                    if not drum_played and self._drum_snd is not None:
                        try:
                            self._drum_chan = self._drum_snd.play()
                            drum_played = True
                        except Exception as e:
                            self._drum_chan = None
                elif not self.show_grade:
                    self.grade_reveal_timer = max(0.0, self.grade_reveal_timer - dt)
                    if self.grade_reveal_timer <= 0.0:
                        self.show_grade = True
                        self._reveal_time = 0.0

                        # decide and cache final grade exactly once
                        self._final_grade = self._grade_letter()

                        # graffiti/confetti only if not F
                        if self._final_grade != 'F':
                            self._spawn_confetti(burst=500)
                            self._confetti_trickle = 1.6
                        else:
                            self._confetti_trickle = 0.0
                        self._confetti_accum = 0.0

                        # impact effects (keep or gate as you like)
                        self._flash_time = 0.16
                        self._impact_jitter_time = 0.42
                        self._impact_jitter_mag = 9.0

                        # smoke burst only for non-F
                        self._need_smoke_spawn = (self._final_grade != 'F')

                        # 分數揭曉後播放cymbal音效（只執行一次）
                        if self._cymbal_snd is not None:
                            try:
                                self._cymbal_snd.play()
                                 # S,A,B,C,D級才播放applause音效（只執行一次）
                                if self._final_grade in ("S", "A", "B", "C", "D") and self._applause_snd is not None:
                                    self._applause_snd.play()
                            except Exception as e:
                                pass
                        try:
                            if self._drum_chan is not None:
                                self._drum_chan.stop()
                        except Exception:
                            pass


            if self.show_grade:
                self._reveal_time += dt
                self._update_confetti(dt)
                if self._confetti_trickle > 0.0:
                    self._confetti_trickle = max(0.0, self._confetti_trickle - dt)
                    self._confetti_accum += 36.0 * dt
                    n = int(self._confetti_accum)
                    if n > 0:
                        self._confetti_accum -= n
                        self._spawn_confetti(burst=n)

            for it in list(self.flying):
                if it.asleep:
                    self.flying.remove(it)
                    self.settled.append(it)
                    continue
                it.vy += GRAVITY * dt
                it.vx *= AIR_DRAG
                it.cx += it.vx * dt
                it.cy += it.vy * dt

                # FIX: only clamp to screen edges if we have NO container mask
                if self._active_mask is None:
                    min_cx = float(it.r)
                    max_cx = float(WIDTH) - it.r
                    if it.cx < min_cx:
                        it.cx = min_cx
                        it.vx *= -0.2
                    elif it.cx > max_cx:
                        it.cx = max_cx
                        it.vx *= -0.2

                for other in self.settled:
                    if self._circle_collide(it, other):
                        self._resolve_circle(it, other)

                for other in self.flying:
                    if other is it:
                        continue
                    dx = it.cx - other.cx
                    if abs(dx) > (it.r + other.r):
                        continue
                    dy = it.cy - other.cy
                    if abs(dy) > (it.r + other.r):
                        continue
                    if self._circle_collide(it, other):
                        self._resolve_circle(it, other)

                # Use container mask for collisions if available; else use flat ground
                if self._active_mask is not None and self._container_rect is not None:
                    # 允許食物從遮罩正上方掉落，不做反彈
                    mask = self._active_mask
                    rect = self._container_rect
                    mx = int(it.cx - rect.left)
                    my = int(it.cy - rect.top)
                    # 如果食物在遮罩外，且在遮罩最上方區域，則不做反彈
                    if my < rect.height * 0.08 and not mask.get_at((mx, my)):
                        # 直接略過碰撞，讓食物掉下來
                        pass
                    else:
                        self._resolve_container(it)
                else:
                    self._resolve_ground(it)
                it.update_rect()

                if it.asleep:
                    self.flying.remove(it)
                    self.settled.append(it)

            surf = dm.get_logical_surface()
            # Draw scrolling background (stacked tiles moving upward)
            if self._bg_img is not None and self._bg_h > 0:
                self._bg_y -= self._bg_speed * dt
                if self._bg_y <= -self._bg_h:
                    self._bg_y += self._bg_h
                start_y = int(self._bg_y) % self._bg_h - self._bg_h
                y = start_y
                while y < HEIGHT:
                    surf.blit(self._bg_img, (0, y))
                    y += self._bg_h
            else:
                surf.fill(FINISH_BG)

            # Draw plate above background but before anything else
            if self._plate_img is not None and self._plate_h > 0:
                plate_y = HEIGHT - self._plate_h
                surf.blit(self._plate_img, (0, plate_y))


            # Draw scoreboard at the very top
            content_y0 = 50
            if self._scoreboard_img is not None:
                surf.blit(self._scoreboard_img, (0, 0))
                content_y0 = 50

            self._draw_text_outlined(surf, self.font_title, "Result: ", (65, content_y0))

            if self.show_grade:
                letter = self._final_grade or self._grade_letter()
                base = self._rank_imgs.get(letter)

                if base is not None:
                    pop = 1.0 + max(0.0, 0.28 - self._reveal_time) * 3.2
                    if pop != 1.0:
                        w = max(1, int(base.get_width() * pop))
                        h = max(1, int(base.get_height() * pop))
                        img = pygame.transform.scale(base, (w, h))
                    else:
                        img = base
                    rect = img.get_rect()
                    rect.topright = (WIDTH - 10, 80)
                    jx = jy = 0
                    if self._impact_jitter_time > 0.0:
                        self._impact_jitter_time = max(0.0, self._impact_jitter_time - (1/60))
                        mag = self._impact_jitter_mag * (self._impact_jitter_time / 0.42)
                        jx = int(random.uniform(-mag, mag))
                        jy = int(random.uniform(-mag, mag))
                    jittered = rect.move(jx, jy)

                    if self._need_smoke_spawn:
                        cx, cy = jittered.center
                        for _ in range(10):
                            px = cx + random.randint(-30, 30)
                            py = cy + random.randint(-20, 20)
                            self._smoke.append(Smoke((px, py)))
                        self._need_smoke_spawn = False

                    if self._smoke:
                        alive_smoke = []
                        for s in self._smoke:
                            s.update(1/60)
                            if s.alive:
                                alive_smoke.append(s)
                                s.draw(surf)
                        self._smoke = alive_smoke

                    surf.blit(img, jittered)
                self._draw_confetti(surf)
                if self._flash_time > 0.0:
                    self._flash_time = max(0.0, self._flash_time - (1/60))
                    alpha = int(200 * (self._flash_time / 0.16))
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    overlay.fill((255, 255, 255, alpha))
                    surf.blit(overlay, (0, 0))

            start_y = content_y0 + 50
            y = start_y
            x = 50
            col_wrapped = False
            bottom_left = start_y
            bottom_right = start_y
            for k in KINDS:
                if self.eaten.per_type.get(k, 0) <= 0:
                    continue
                line = f"{k}: {self.shown[k]}"
                if (y > 360) and (not col_wrapped):
                    col_wrapped = True
                    x = 330
                    y = start_y
                self._draw_text_outlined(surf, self.font_list, line, (x, y))
                y += max(28, self.font_list.get_linesize())
                if not col_wrapped:
                    bottom_left = y
                else:
                    bottom_right = y

            # Blink the continue prompt every second, placed just below the food list
            if self.show_grade:
                blink_on = (int(self._reveal_time) % 2) == 0
                if blink_on:
                    prompt_y = max(bottom_left, bottom_right) + 12
                    self._draw_text_outlined(surf, self.font_small, "Press space to continue", (50, prompt_y))

            for it in self.settled:
                surf.blit(it.img, it.rect)
            for it in self.flying:
                surf.blit(it.img, it.rect)

            # Draw the mouth (with hat) at larger scale on the right
            try:
                self.mouth.draw_scaled(surf, fixed_mouth_pos, scale=self.mouth_scale)
            except Exception:
                # Fallback to previous behavior if draw_scaled is unavailable
                base_img = self.mouth.image
                mw = int(base_img.get_width() * self.mouth_scale)
                mh = int(base_img.get_height() * self.mouth_scale)
                large = pygame.transform.scale(base_img, (mw, mh))
                mouth_draw_rect = large.get_rect(center=fixed_mouth_pos)
                surf.blit(large, mouth_draw_rect)

            if self.show_grade:
                letter = self._final_grade or self._grade_letter()
                if (letter in ("A", "S")) and (self._clap_img is not None):
                    self._clap_phase += dt
                    freq = 2.6
                    s = math.sin(self._clap_phase * 2 * math.pi * freq)
                    up_gap = 18
                    down_depth = 26
                    if s >= 0:
                        bottom_y = HEIGHT - int(s * up_gap) + 18
                    else:
                        bottom_y = HEIGHT + int((-s) * down_depth) + 18
                    clap_rect = self._clap_img.get_rect()
                    clap_rect.midbottom = (WIDTH // 2, bottom_y)
                    surf.blit(self._clap_img, clap_rect)

            # Fade-in overlay
            if fade_in_t < fade_in_dur:
                fade_in_t = min(fade_in_dur, fade_in_t + dt)
                t = fade_in_t / max(0.001, fade_in_dur)
                alpha = int(255 * (1.0 - t))
                if alpha > 0:
                    white = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    white.fill((255, 255, 255, alpha))
                    surf.blit(white, (0, 0))

            dm.present()
            # end of frame

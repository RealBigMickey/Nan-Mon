from __future__ import annotations
import os
import random
import math
import pygame
from .constants import WIDTH, HEIGHT, ASSET_FOOD_DIR, FOOD_SIZE, LEVEL_TARGET_SCORE
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

    def update_rect(self) -> None:
        self.rect = self.img.get_rect(center=(int(self.cx), int(self.cy)))


class FinishScreen:
    def __init__(self, eaten: EatenCounters):
        self.eaten = eaten
        # Vertical offset to move finish-screen mouth and food animations upward
        self._y_offset = 60

        # Scrolling background setup
        self._bg_img: pygame.Surface | None = None
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
        self.food_imgs: dict[str, pygame.Surface] = {}
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
        self.mouth.facing = "LEFT"
        self.mouth_scale = 3.5

        # Collections
        self.flying: list[SpewItem] = []
        self.settled: list[SpewItem] = []

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

        # Fonts
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
        self.font_big = pygame.font.Font(None, 96)
        self.font_title = pygame.font.Font(None, 48)
        self.font_list = pygame.font.Font(None, 34)

        # Grade reveal state and optional sounds
        self.show_grade = False
        self.grade_reveal_started = False
        self.grade_reveal_timer = 0.0
        self._drum_snd: pygame.mixer.Sound | None = None
        self._drum_chan = None
        # Celebration state
        self._reveal_time = 0.0
        self._confetti: list[dict] = []
        self._confetti_trickle = 0.0
        self._confetti_accum = 0.0
        self._cheer_snd: pygame.mixer.Sound | None = None
        self._cheer_chan = None
        self._spray_snd: pygame.mixer.Sound | None = None
        self._smoke: list[Smoke] = []
        self._flash_time = 0.0
        self._impact_jitter_time = 0.0
        self._impact_jitter_mag = 0.0

        # Rank images (S, A, B, C, D, F)
        self._rank_imgs: dict[str, pygame.Surface] = {}
        self._rank_base_h = int(HEIGHT * 0.24)

        # Clapping sprite (shown for ranks A and S)
        self._clap_img: pygame.Surface | None = None
        self._clap_phase = 0.0
        self._need_smoke_spawn = False

        # Optional images (scoreboard, plate)
        self._scoreboard_img: pygame.Surface | None = None
        self._scoreboard_h = 0
        self._plate_img: pygame.Surface | None = None
        self._plate_h = 0

        # Optional container hitbox (not drawn)
        self._container_mask: pygame.mask.Mask | None = None
        self._container_rect: pygame.Rect | None = None
        self._container_img: pygame.Surface | None = None  # original image
        self._walls_mask: pygame.mask.Mask | None = None   # outline/solid pixels from image
        self._interior_mask: pygame.mask.Mask | None = None  # filled interior computed
        self._active_mask: pygame.mask.Mask | None = None   # mask used for collisions

        # FIX: use walls by default (solid = black opaque pixels)
        self._mask_mode: str = "walls"  # 'interior' or 'walls'
        self._show_hitbox_overlay: bool = False            # press 'H' to toggle

        # Load media/assets
        self._load_media()

    # --- media loading helpers ---
    def _load_media(self) -> None:
        # Sounds
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            for name, attr in (("drumroll.ogg", "_drum_snd"), ("cheer.ogg", "_cheer_snd"), ("spray.ogg", "_spray_snd")):
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

        # FIX: do NOT clamp to screen bottom when a container mask exists
        # (We still keep a small safety if something escapes entirely)
        if self._active_mask is None and it.cy + it.r >= HEIGHT:
            it.cy = HEIGHT - it.r
            it.vy = 0.0

        # Only resolve contact when moving downward and touching SOLID below
        if it.vy >= 0:
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
        T = random.uniform(0.62, 0.9)
        vx = (tx - x0) / T + random.uniform(-12, 10)
        vy = (ty - y0 - 0.5 * GRAVITY * T * T) / T + random.uniform(-10, 2)
        self.flying.append(SpewItem(kind, img, x0, y0, vx, vy))

    def _next_spew(self) -> None:
        if self.done:
            return
        if self.current_idx >= len(self.order):
            self.done = True
            return
        kind = self.order[self.current_idx]
        if self.counts[kind] <= 0:
            self.current_idx += 1
            self._next_spew()
            return
        self.counts[kind] -= 1
        self.shown[kind] += 1
        self._spawn_spew(kind)
        self.mouth.bite_timer = 0.0
        self._bite_delay_timer = 0.045
        if self.counts[kind] <= 0:
            self.current_idx += 1

    def _grade_letter(self) -> str:
        total = max(0, int(self.eaten.total))
        target = max(1, int(LEVEL_TARGET_SCORE))
        ratio = total / target
        if ratio >= 2.0:
            return "S"
        if ratio >= 1.5:
            return "A"
        if ratio >= 1.2:
            return "B"
        if ratio >= 1.0:
            return "C"
        if ratio >= 0.8:
            return "D"
        return "F"

    def loop(self, dm, clock) -> None:
        running = True
        fixed_mouth_pos = (int(WIDTH * 0.82), int(HEIGHT * 0.72) - self._y_offset)
        while running:
            dt = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_SPACE and self.done:
                        return
                    if event.key == pygame.K_h:
                        # Toggle debug overlay for container hitbox image
                        self._show_hitbox_overlay = not self._show_hitbox_overlay
                    if event.key == pygame.K_m:
                        # Toggle mask mode between interior and walls (for debugging)
                        if self._mask_mode == "interior":
                            self._mask_mode = "walls"
                            self._active_mask = self._walls_mask
                        else:
                            self._mask_mode = "interior"
                            self._active_mask = self._interior_mask or self._walls_mask

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
                if not self.grade_reveal_started:
                    self.grade_reveal_started = True
                    self.grade_reveal_timer = 1.0
                    if self._drum_snd is not None:
                        try:
                            self._drum_chan = self._drum_snd.play()
                        except Exception:
                            self._drum_chan = None
                elif not self.show_grade:
                    self.grade_reveal_timer = max(0.0, self.grade_reveal_timer - dt)
                    if self.grade_reveal_timer <= 0.0:
                        self.show_grade = True
                        self._reveal_time = 0.0
                        self._spawn_confetti(burst=360)
                        self._confetti_trickle = 1.6
                        self._confetti_accum = 0.0
                        self._flash_time = 0.16
                        self._impact_jitter_time = 0.42
                        self._impact_jitter_mag = 9.0
                        self._need_smoke_spawn = True
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

            # Debug: draw semi-transparent container hitbox overlay if toggled
            if self._show_hitbox_overlay and self._container_img is not None and self._container_rect is not None:
                overlay = self._container_img.copy()
                overlay.set_alpha(110)
                surf.blit(overlay, self._container_rect)
                # Also draw active mask visualization (green tint) to show what physics sees
                if self._active_mask is not None:
                    mw, mh = self._active_mask.get_size()
                    try:
                        viz = self._active_mask.to_surface(setcolor=(0, 255, 0, 120), unsetcolor=(0, 0, 0, 0))
                        surf.blit(viz, self._container_rect)
                    except Exception:
                        pass

            # Draw scoreboard at the very top
            content_y0 = 50
            if self._scoreboard_img is not None:
                surf.blit(self._scoreboard_img, (0, 0))
                content_y0 = 50

            self._draw_text_outlined(surf, self.font_title, "Result: ", (65, content_y0))

            if self.show_grade:
                letter = self._grade_letter()
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
                    rect.topright = (WIDTH, 50)
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

            if self.show_grade:
                self._draw_text_outlined(surf, self.font_small, "Press SPACE to continue", (20, HEIGHT - 28))

            for it in self.settled:
                surf.blit(it.img, it.rect)
            for it in self.flying:
                surf.blit(it.img, it.rect)

            base_img = self.mouth.image
            mw = int(base_img.get_width() * self.mouth_scale)
            mh = int(base_img.get_height() * self.mouth_scale)
            large = pygame.transform.scale(base_img, (mw, mh))
            mouth_draw_rect = large.get_rect(center=fixed_mouth_pos)
            surf.blit(large, mouth_draw_rect)

            if self.show_grade:
                letter = self._grade_letter()
                if (letter in ('A', 'S')) and (self._clap_img is not None):
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

            dm.present()
            # end of frame

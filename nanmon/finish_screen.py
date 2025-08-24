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
        self.mouth.facing = "LEFT"
        self.mouth_scale = 3.5

        # Collections
        self.flying = []
        self.settled = []

        # Pile region and cadence
        self.pile_left = 20
        self.pile_right = int(WIDTH * 0.74)
        # Ground for the pile, moved upward
        self.ground_y = int(HEIGHT * 0.9) - self._y_offset
        self.spew_timer = 0.0
        # Dynamic spew cadence: start slightly slower, ramp to 3x faster by 10 foods
        self.spew_start_interval = 0.30
        self.spew_end_interval = max(0.001, 0.25 / 3.0)
        self.spew_accel_count = 10
        self.spew_count = 0
        # Mouth close timing during spew (open at spawn, then close briefly)
        self._bite_delay_timer = -1.0
        self._bite_duration = 0.06

        pixel_font_path = os.path.join("nanmon", "assets", "Pixel Emulator.otf")
        self.font = pygame.font.Font(pixel_font_path, 32)
        self.font_small = pygame.font.Font(pixel_font_path, 22)
        self.font_big = pygame.font.Font(pixel_font_path, 96)

        # Grade reveal state and optional drum roll sound
        self.show_grade = False
        self.grade_reveal_started = False
        self.grade_reveal_timer = 0.0
        self._drum_snd = None
        self._drum_chan = None
        # Celebration state
        self._reveal_time = 0.0
        self._confetti = []
        self._confetti_trickle = 0.0
        self._confetti_accum = 0.0
        self._cheer_snd = None
        self._cheer_chan = None
        self._spray_snd = None
        self._smoke = []
        self._flash_time = 0.0
        self._impact_jitter_time = 0.0
        self._impact_jitter_mag = 0.0

        # Rank images (S, A, B, C, D, F)
        self._rank_imgs = {}
        # Base size 25% smaller, then reduce by 5% more
        self._rank_base_h = int(HEIGHT * 0.33)

        # Clapping sprite (shown for ranks A and S)
        self._clap_img = None
        self._clap_phase = 0.0
        # One-shot: spawn smoke at rank center when revealed
        self._need_smoke_spawn = False
    # No static graffiti blobs; graffiti is represented by flying confetti particles

        # Sounds (optional)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            drum_path = os.path.join("nanmon", "assets", "drumroll.ogg")
            if os.path.exists(drum_path):
                self._drum_snd = pygame.mixer.Sound(drum_path)
            cheer_path = os.path.join("nanmon", "assets", "cheer.ogg")
            if os.path.exists(cheer_path):
                self._cheer_snd = pygame.mixer.Sound(cheer_path)
            spray_path = os.path.join("nanmon", "assets", "spray.ogg")
            if os.path.exists(spray_path):
                self._spray_snd = pygame.mixer.Sound(spray_path)
        except Exception:
            self._drum_snd = None

        # Load rank images at base height with nearest-neighbor (transform.scale)
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

        # Load clapping image
        try:
            clap_path = os.path.join("nanmon", "assets", "clapping.png")
            if not os.path.exists(clap_path):
                clap_path = os.path.join("nanmon", "assets", "clear_screen", "clapping.png")
            if os.path.exists(clap_path):
                cim = pygame.image.load(clap_path).convert_alpha()
                # Scale to exactly the window width, keep aspect ratio (nearest-neighbor)
                cw = max(1, cim.get_width())
                scale_w = WIDTH
                scale_h = int(cim.get_height() * (scale_w / cw))
                self._clap_img = pygame.transform.scale(cim, (scale_w, scale_h))
        except Exception:
            self._clap_img = None

    # --- Celebration helpers ---
    def _spawn_confetti(self, burst: int = 80):
        for _ in range(burst):
            # Spawn across the entire screen area for wide coverage
            x = random.uniform(0, WIDTH)
            y = random.uniform(0, HEIGHT)
            vx = random.uniform(-160, 160)
            # Allow some particles to launch upward briefly, gravity will pull them down
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
        dist = (dx * dx + dy * dy) ** 0.5
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
        # Spawn offset up/left of mouth center
        x0 = self.mouth.rect.centerx - 20
        y0 = self.mouth.rect.centery - 20
        # Strong left bias for target x within pile
        margin = img.get_width() * 0.5
        a = self.pile_left + margin
        b = min(self.pile_right - margin, self.mouth.rect.centerx - margin - 140)
        if b <= a:
            b = a + 1
        tx = int(random.triangular(a, b, a))
        ty = self.ground_y - img.get_height()
        # Faster ballistic arc
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
        # Spawn while mouth is open
        self._spawn_spew(kind)
        # Force open now, then schedule a brief close animation
        self.mouth.bite_timer = 0.0
        self._bite_delay_timer = 0.045
        if self.counts[kind] <= 0:
            self.current_idx += 1

    def _grade_letter(self) -> str:
        total = max(0, int(self.eaten.total))
        target = max(1, int(LEVEL_TARGET_SCORE))
        ratio = total / target
        # Stricter grading thresholds
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
                        # 播放選單音效
                        try:
                            if not pygame.mixer.get_init():
                                pygame.mixer.init()
                            sound_path = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
                            if os.path.exists(sound_path):
                                pygame.mixer.Sound(sound_path).play()
                        except Exception:
                            pass
                        return
                    if event.key == pygame.K_SPACE and self.done:
                        # 播放選單音效
                        try:
                            if not pygame.mixer.get_init():
                                pygame.mixer.init()
                            sound_path = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
                            if os.path.exists(sound_path):
                                pygame.mixer.Sound(sound_path).play()
                        except Exception:
                            pass
                        return

            keys = pygame.key.get_pressed()
            self.mouth.update(dt, keys)
            self.mouth.rect.center = fixed_mouth_pos
            self.mouth.facing = "LEFT"

            # Trigger delayed bite (close mouth) shortly after a spew
            if self._bite_delay_timer >= 0.0:
                self._bite_delay_timer -= dt
                if self._bite_delay_timer <= 0.0:
                    self.mouth.bite()
                    self.mouth.bite_timer = float(self._bite_duration)
                    self._bite_delay_timer = -1.0

            # Variable cadence: start slower, ramp to 3x speed by 10 spews
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
                # Start grade reveal countdown once spew is done
                if not self.grade_reveal_started:
                    self.grade_reveal_started = True
                    self.grade_reveal_timer = 1.0
                    # Play drum roll if available
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
                        # Spawn a bigger burst of confetti and trickle
                        # Much bigger burst and trickle
                        self._spawn_confetti(burst=360)
                        self._confetti_trickle = 1.6
                        self._confetti_accum = 0.0
                        # Harder impact: flash and jitter
                        self._flash_time = 0.16
                        self._impact_jitter_time = 0.42
                        self._impact_jitter_mag = 9.0
                        # Defer smoke spawn so we can anchor to the rank center in draw
                        self._need_smoke_spawn = True
                        # Reset graffiti so it regenerates on reveal
                        self._graffiti_generated = False
                        # Play cheer sound if available
                        if self._cheer_snd is not None:
                            try:
                                self._cheer_chan = self._cheer_snd.play()
                            except Exception:
                                self._cheer_chan = None
                        # No spray sfx for image-based rank
                        # Stop drum on reveal if it is still playing
                        try:
                            if self._drum_chan is not None:
                                self._drum_chan.stop()
                        except Exception:
                            pass

            # Update confetti particles
            if self.show_grade:
                self._reveal_time += dt
                self._update_confetti(dt)
                # confetti trickle
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

                # Clamp to screen width only
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

                self._resolve_ground(it)
                it.update_rect()

                if it.asleep:
                    self.flying.remove(it)
                    self.settled.append(it)

            surf = dm.get_logical_surface()
            surf.fill(FINISH_BG)
            top_h = int(HEIGHT * 0.4)
            title = self.font.render("Results", True, pygame.Color(40, 40, 40))
            surf.blit(title, (20, 14))

            if self.show_grade:
                letter = self._grade_letter()
                base = self._rank_imgs.get(letter)
                if base is not None:
                    # Stronger pop on reveal
                    pop = 1.0 + max(0.0, 0.28 - self._reveal_time) * 3.2
                    if pop != 1.0:
                        w = max(1, int(base.get_width() * pop))
                        h = max(1, int(base.get_height() * pop))
                        img = pygame.transform.scale(base, (w, h))
                    else:
                        img = base
                    rect = img.get_rect()
                    # Rank sprite position: change these numbers to move it manually.
                    rect.topright = (WIDTH, 50)
                    # Impact jitter right after reveal
                    jx = jy = 0
                    if self._impact_jitter_time > 0.0:
                        self._impact_jitter_time = max(0.0, self._impact_jitter_time - (1/60))
                        mag = self._impact_jitter_mag * (self._impact_jitter_time / 0.42)
                        jx = int(random.uniform(-mag, mag))
                        jy = int(random.uniform(-mag, mag))

                    jittered = rect.move(jx, jy)

                    # Spawn smoke at the center of the rank once, then render smoke behind the rank
                    if self._need_smoke_spawn:
                        cx, cy = jittered.center
                        for _ in range(10):
                            px = cx + random.randint(-30, 30)
                            py = cy + random.randint(-20, 20)
                            self._smoke.append(Smoke((px, py)))
                        self._need_smoke_spawn = False

                    # Update and draw smoke behind the rank
                    if self._smoke:
                        alive_smoke = []
                        for s in self._smoke:
                            s.update(1/60)
                            if s.alive:
                                alive_smoke.append(s)
                                s.draw(surf)
                        self._smoke = alive_smoke

                    # Draw rank image (no paint/graffiti effects)
                    surf.blit(img, jittered)

                # Smoke is handled before drawing the rank to keep it behind

                # Confetti on top
                self._draw_confetti(surf)
                # Flash overlay for impact
                if self._flash_time > 0.0:
                    self._flash_time = max(0.0, self._flash_time - (1/60))
                    alpha = int(200 * (self._flash_time / 0.16))
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    overlay.fill((255, 255, 255, alpha))
                    surf.blit(overlay, (0, 0))

            y = 56
            for k in KINDS:
                if self.eaten.per_type.get(k, 0) <= 0:
                    continue
                # Show simple eaten count instead of shown/total
                line = f"{k}: {self.shown[k]}"
                img = self.font.render(line, True, pygame.Color(40, 40, 40))
                surf.blit(img, (30, y))
                y += 26
                if y > top_h - 20:
                    break

            if self.show_grade:
                hint = self.font_small.render("Press SPACE to continue", True, pygame.Color(40, 40, 40))
                surf.blit(hint, (20, top_h - 24))

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

            # Top layer: clapping banner (A/S ranks only), bottom-anchored bounce and shifted down by 50px
            if self.show_grade:
                letter = self._grade_letter()
                if letter in ("A", "S") and self._clap_img is not None:
                    self._clap_phase += dt
                    freq = 2.6  # Hz
                    s = math.sin(self._clap_phase * 2 * math.pi * freq)
                    up_gap = 18      # keep a small gap at the top of the bounce
                    down_depth = 26  # allow dipping under bottom
                    if s >= 0:
                        bottom_y = HEIGHT - int(s * up_gap) + 18
                    else:
                        bottom_y = HEIGHT + int((-s) * down_depth) + 18
                    clap_rect = self._clap_img.get_rect()
                    clap_rect.midbottom = (WIDTH // 2, bottom_y)
                    surf.blit(self._clap_img, clap_rect)

            dm.present()
            # end of frame


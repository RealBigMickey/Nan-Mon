from __future__ import annotations
import os
import random
import pygame
from .constants import WIDTH, HEIGHT, ASSET_FOOD_DIR, FOOD_SIZE, LEVEL_TARGET_SCORE
from .models import KINDS, EatenCounters
from .mouth import Mouth

FINISH_BG = pygame.Color(245, 245, 245)
GRAVITY = 1400.0
AIR_DRAG = 0.995
GROUND_FRICTION = 0.88
SLEEP_SPEED = 12.0   # speed below which an item may fall asleep when grounded
HITBOX_SCALE = 0.86  # circle slightly smaller than sprite to promote rolling
SLIDE_SCALE = 0.22   # fraction of gravity applied along slope tangent


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
        self.counts = {k: int(eaten.per_type.get(k, 0)) for k in KINDS}
        self.order = [k for k in KINDS if self.counts[k] > 0]
        self.shown = {k: 0 for k in KINDS}
        self.current_idx = 0
        self.done = (sum(self.counts.values()) == 0)

        # Load food images (use nearest neighbor for upscaling)
        self.food_imgs: dict[str, pygame.Surface] = {}
        for k in KINDS:
            path = os.path.join(ASSET_FOOD_DIR, f"{k}.png")
            try:
                img = pygame.image.load(path).convert_alpha()
            except Exception:
                img = pygame.Surface(FOOD_SIZE, pygame.SRCALPHA)
                pygame.draw.rect(img, pygame.Color(200, 200, 200), img.get_rect(), 2)
            self.food_imgs[k] = pygame.transform.scale(img, FOOD_SIZE)  # nearest neighbor

        # Big mouth on right
        self.mouth = Mouth((int(WIDTH * 0.82), int(HEIGHT * 0.72)))
        self.mouth.facing = "LEFT"
        self.mouth_scale = 3.5

        # Collections
        self.flying = []
        self.settled = []

        # Pile region spans most of the screen width (leave room near mouth on the right)
        self.pile_left = 20
        self.pile_right = int(WIDTH * 0.74)
        self.ground_y = int(HEIGHT * 0.9)
        self.spew_timer = 0.0
        self.spew_interval = 0.25  # slower spew cadence

        # Fonts
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
        self.font_big = pygame.font.Font(None, 96)

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

    def _spawn_spew(self, kind: str) -> None:
        img = self.food_imgs[kind]
        # Spawn from mouth center
        x0 = self.mouth.rect.centerx - 20
        y0 = self.mouth.rect.centery - 20
        # Arc to pile: bias target very strongly toward the left side
        margin = img.get_width() * 0.5
        a = self.pile_left + margin
        # Pull the right bound much further left of the mouth
        b = min(self.pile_right - margin, self.mouth.rect.centerx - margin - 140)
        if b <= a:
            b = a + 1
        # Strong left skew: mode fixed at left bound
        tx = int(random.triangular(a, b, a))
        ty = self.ground_y - img.get_height()
        # Ballistic arc: solve for vx, vy to reach (tx, ty) from (x0, y0) in T seconds
        T = random.uniform(1.0, 1.3)
        vx = (tx - x0) / T + random.uniform(-6, 6)
        vy = (ty - y0 - 0.5 * GRAVITY * T * T) / T + random.uniform(-6, 5)
        item = SpewItem(kind, img, x0, y0, vx, vy)
        self.flying.append(item)

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
        self.mouth.bite()
        self._spawn_spew(kind)
        if self.counts[kind] <= 0:
            self.current_idx += 1

    def _grade_letter(self) -> str:
        total = max(0, int(self.eaten.total))
        target = max(1, int(LEVEL_TARGET_SCORE))
        ratio = total / target
        if ratio >= 1.5: return "S"
        if ratio >= 1.0: return "A"
        if ratio >= 0.8: return "B"
        if ratio >= 0.6: return "C"
        if ratio >= 0.4: return "D"
        return "F"

    def loop(self, dm, clock) -> None:
        running = True
        fixed_mouth_pos = (int(WIDTH * 0.82), int(HEIGHT * 0.72))
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

            keys = pygame.key.get_pressed()
            self.mouth.update(dt, keys)
            self.mouth.rect.center = fixed_mouth_pos
            self.mouth.facing = "LEFT"

            if not self.done:
                self.spew_timer += dt
                while self.spew_timer >= self.spew_interval:
                    self.spew_timer -= self.spew_interval
                    self._next_spew()

            for it in list(self.flying):
                if it.asleep:
                    self.flying.remove(it)
                    self.settled.append(it)
                    continue
                it.vy += GRAVITY * dt
                it.vx *= AIR_DRAG
                it.cx += it.vx * dt
                it.cy += it.vy * dt

                # Clamp to screen width only (allow arc from mouth to pile)
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

            grade = self._grade_letter()
            grade_img = self.font_big.render(grade, True, pygame.Color(30, 30, 30))
            surf.blit(grade_img, (WIDTH - grade_img.get_width() - 24, 8))

            y = 56
            for k in KINDS:
                if self.eaten.per_type.get(k, 0) <= 0:
                    continue
                line = f"{k}: {self.shown[k]}/{self.eaten.per_type[k]}"
                img = self.font.render(line, True, pygame.Color(40, 40, 40))
                surf.blit(img, (30, y))
                y += 26
                if y > top_h - 20:
                    break

            if self.done:
                hint = self.font_small.render("Press SPACE to continue", True, pygame.Color(40, 40, 40))
                surf.blit(hint, (20, top_h - 24))

            for it in self.settled:
                surf.blit(it.img, it.rect)
            for it in self.flying:
                surf.blit(it.img, it.rect)

            base_img = self.mouth.image
            mw = int(base_img.get_width() * self.mouth_scale)
            mh = int(base_img.get_height() * self.mouth_scale)
            # Nearest-neighbor upscaling for crisp pixels
            large = pygame.transform.scale(base_img, (mw, mh))
            mouth_draw_rect = large.get_rect(center=fixed_mouth_pos)
            surf.blit(large, mouth_draw_rect)

            dm.present()

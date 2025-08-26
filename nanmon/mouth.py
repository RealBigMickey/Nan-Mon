from __future__ import annotations
import os
import random
import pygame
from typing import Tuple
from .effects import Smoke
from .constants import (
    MOUTH_SIZE,
    SALTY_COLOR,
    SWEET_COLOR,
    WIDTH,
    HEIGHT,
    FLASH_DURATION,
    MOUTH_SPEED,
    MOUTH_SPRING_K,
    MOUTH_DAMPING,
    MOUTH_MAX_SPEED,
    MOUTH_SPEED_X,
    MOUTH_BITE_DURATION,
    ASSET_HAT_DIR,
)

HAT_SCALE = 1.509  # 1.0 = same as mouth; tweak to taste (slightly bigger)

class Mouth(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int, int]):
        super().__init__()
        # Facing offsets for hats
        self._hat_offset_left = (-30, -31)
        self._hat_offset_right = (-30, -31)
        self._scarf_offset_left = (-5, 40)
        self._scarf_offset_right = (-10, 40)

        # Basic state
        self.mode = "SALTY"  # SALTY -> blue sprites, SWEET -> pink sprites
        self.facing = "RIGHT"  # LEFT/RIGHT
        self._sprites = self._load_sprites()
        self.image = self._sprites[("SALTY", "RIGHT", "OPEN")].copy()
        self.rect = self.image.get_rect(center=pos)
        self.flash_timer = 0.0
        self.bite_timer = 0.0
        self.bite_total = MOUTH_BITE_DURATION

        # Hybrid movement target + velocity
        self.target = pygame.Vector2(self.rect.center)
        self.vel = pygame.Vector2(0, 0)

        # Death/FX
        self.dying = False
        self.death_timer = 0.0
        self._smoke_cd = 0.0
        self._smoke: list[Smoke] = []
        self.stagger_timer = 0.0

        # Status effects
        self.cold_timer = 0.0
        self.cold_speed_scale = 1.0

        # Hat state
        self._hat_name: str | None = None
        self._hat_img_left: pygame.Surface | None = None
        self._hat_img_right: pygame.Surface | None = None
        self._hat_src_left: pygame.Surface | None = None
        self._hat_src_right: pygame.Surface | None = None

    def toggle_mode(self):
        self.mode = "SWEET" if self.mode == "SALTY" else "SALTY"
        self._update_image()

    # --- sprite loading ---
    def _load_sprites(self):
        base = os.path.join("nanmon", "assets", "char")
        mapping = {
            ("SALTY", "LEFT",  "OPEN"): "head_blue_left.png",
            ("SALTY", "LEFT",  "BITE1"): "head_blue_left_bite_1.png",
            ("SALTY", "LEFT",  "BITE2"): "head_blue_left_bite_2.png",
            ("SALTY", "LEFT",  "BITE3"): "head_blue_left_bite_3.png",
            ("SALTY", "RIGHT", "OPEN"): "head_blue_left.png",
            ("SALTY", "RIGHT", "BITE1"): "head_blue_left_bite_1.png",
            ("SALTY", "RIGHT", "BITE2"): "head_blue_left_bite_2.png",
            ("SALTY", "RIGHT", "BITE3"): "head_blue_left_bite_3.png",
            ("SWEET", "LEFT",  "OPEN"): "head_pink_left.png",
            ("SWEET", "LEFT",  "BITE1"): "head_pink_left_bite_1.png",
            ("SWEET", "LEFT",  "BITE2"): "head_pink_left_bite_2.png",
            ("SWEET", "LEFT",  "BITE3"): "head_pink_left_bite_3.png",
            ("SWEET", "RIGHT", "OPEN"): "head_pink_left.png",
            ("SWEET", "RIGHT", "BITE1"): "head_pink_left_bite_1.png",
            ("SWEET", "RIGHT", "BITE2"): "head_pink_left_bite_2.png",
            ("SWEET", "RIGHT", "BITE3"): "head_pink_left_bite_3.png",
        }
        sprites: dict[tuple[str, str, str], pygame.Surface] = {}
        for key, fname in mapping.items():
            path = os.path.join(base, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
            except Exception:
                img = pygame.Surface(MOUTH_SIZE, pygame.SRCALPHA)
                color = SALTY_COLOR if key[0] == "SALTY" else SWEET_COLOR
                pygame.draw.circle(img, color, (MOUTH_SIZE[0]//2, MOUTH_SIZE[1]//2), min(MOUTH_SIZE)//2)
            img = pygame.transform.scale(img, MOUTH_SIZE)
            if key[1] == "RIGHT":
                img = pygame.transform.flip(img, True, False)
            sprites[key] = img
        return sprites

    def update(self, dt: float, keys):
        if self.dying:
            self.update_dying(dt)
            if self.flash_timer > 0:
                self.flash_timer -= dt
            if self.bite_timer > 0:
                self.bite_timer -= dt
            self._update_image()
            return

        # Timers
        if self.stagger_timer > 0:
            self.stagger_timer = max(0.0, self.stagger_timer - dt)
        if self.cold_timer > 0.0:
            self.cold_timer = max(0.0, self.cold_timer - dt)
            if self.cold_timer <= 0.0:
                self.cold_speed_scale = 1.0

        # Horizontal: direct control
        pos = pygame.Vector2(self.rect.center)
        right = 1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0
        left = 1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0
        ctrl_scale_x = 0.35 if self.stagger_timer > 0 else 1.0
        vx = (right - left) * MOUTH_SPEED_X * ctrl_scale_x * self.cold_speed_scale
        if vx < 0:
            self.facing = "LEFT"
        elif vx > 0:
            self.facing = "RIGHT"
        pos.x += vx * dt
        pos.x = max(self.rect.width//2, min(WIDTH - self.rect.width//2, pos.x))

        # Vertical: spring to target
        down = 1 if (keys[pygame.K_DOWN] or keys[pygame.K_s]) else 0
        up = 1 if (keys[pygame.K_UP] or keys[pygame.K_w]) else 0
        tdy = 0.0 if self.stagger_timer > 0 else (down - up) * MOUTH_SPEED * dt * self.cold_speed_scale
        self.target.y = max(self.rect.height//2, min(HEIGHT - self.rect.height//2, self.target.y + tdy))
        self.target.x = pos.x

        to_y = self.target.y - pos.y
        k_scale = 0.35 if self.stagger_timer > 0 else 1.0
        d_scale = 0.65 if self.stagger_timer > 0 else 1.0
        ay = to_y * (MOUTH_SPRING_K * k_scale) - self.vel.y * (MOUTH_DAMPING * d_scale)
        self.vel.x = 0
        self.vel.y += ay * dt
        if abs(self.vel.y) > MOUTH_MAX_SPEED:
            self.vel.y = MOUTH_MAX_SPEED if self.vel.y > 0 else -MOUTH_MAX_SPEED
        pos.y += self.vel.y * dt
        pos.y = max(self.rect.height//2, min(HEIGHT - self.rect.height//2, pos.y))

        self.rect.center = (int(pos.x), int(pos.y))

        # Timers
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.bite_timer > 0:
            self.bite_timer -= dt
        self._update_image()

    def flash(self, good: bool):
        self.flash_timer = FLASH_DURATION
        self._flash_good = good

    def bite(self):
        self.bite_timer = MOUTH_BITE_DURATION
        self._update_image()

    def die(self):
        if not self.dying:
            self.dying = True
            self.death_timer = 1.6
            self._smoke_cd = 0.0

    def knockback(self, strength: float = 1800.0):
        self.vel.y += strength
        self.rect.y += int(strength * 0.015)
        self.stagger(0.28)

    def stagger(self, duration: float):
        self.stagger_timer = max(self.stagger_timer, duration)

    def _update_image(self):
        # Bite animation state
        if self.bite_timer > 0:
            bite_frame = int((self.bite_timer / self.bite_total) * 4)
            if bite_frame < 1:
                bite_state = "BITE1"
            elif bite_frame < 2:
                bite_state = "BITE2"
            elif bite_frame < 3:
                bite_state = "BITE3"
            else:
                bite_state = "OPEN"
        else:
            bite_state = "OPEN"

        key = (self.mode, self.facing, bite_state)
        base_img = self._sprites.get(key)
        if base_img is None:
            base_img = next(iter(self._sprites.values()))
        img = base_img.copy()

        if bite_state.startswith("BITE"):
            scale = 1.22
            w, h = img.get_width(), img.get_height()
            img = pygame.transform.scale(img, (int(w*scale), int(h*scale)))
            jitter_y = random.randint(-12, 12)
            pad = abs(jitter_y)
            surf_h = img.get_height() + pad
            img_jitter = pygame.Surface((img.get_width(), surf_h), pygame.SRCALPHA)
            base_y = (surf_h - img.get_height()) // 2 + jitter_y
            img_jitter.blit(img, (0, base_y))
            img = img_jitter

        # Flash overlay
        if self.flash_timer > 0 and bite_state == "OPEN":
            good = getattr(self, "_flash_good", None)
            if good is True:
                tint = pygame.Color(180, 255, 180, 90)
            elif good is False:
                tint = pygame.Color(255, 120, 120, 105)
            else:
                tint = pygame.Color(255, 255, 255, 0)
            if tint.a > 0:
                overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                overlay.fill((tint.r, tint.g, tint.b, tint.a))
                img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # Cold status overlay (always visible while cold)
        if self.cold_timer > 0.0:
            overlay2 = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            overlay2.fill((120, 180, 255, 140))
            img.blit(overlay2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        self.image = img

    def draw(self, surface: pygame.Surface):
        for s in list(self._smoke):
            s.draw(surface)
            if not s.alive:
                self._smoke.remove(s)

        draw_rect = self.rect.copy()
        if self.dying:
            jitter = 6
            draw_rect.x += random.randint(-jitter, jitter)
            draw_rect.y += random.randint(-jitter, jitter)

        surface.blit(self.image, draw_rect)

        if self.dying:
            overlay = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 60, 60, 120))
            tinted = self.image.copy()
            tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(tinted, draw_rect)

        # Hat
        hat_img = self._hat_img_right if self.facing == "RIGHT" else self._hat_img_left
        ox, oy = (self._hat_offset_right if self.facing == "RIGHT" else self._hat_offset_left)
        jitter_y = random.randint(-12, 12) if self.bite_timer > 0 else 0
        if hat_img is not None:
            hx = draw_rect.centerx + int(ox)
            hy = draw_rect.centery + int(oy) + jitter_y
            surface.blit(hat_img, (hx, hy))

    def draw_scaled(self, surface: pygame.Surface, center: Tuple[int, int], scale: float = 1.0):
        base_img = self.image
        bw, bh = base_img.get_size()
        sw = max(1, int(bw * scale))
        sh = max(1, int(bh * scale))
        scaled_mouth = pygame.transform.scale(base_img, (sw, sh))
        mouth_rect = scaled_mouth.get_rect(center=center)
        surface.blit(scaled_mouth, mouth_rect)

        hat_img = self._hat_img_right if self.facing == "RIGHT" else self._hat_img_left
        if hat_img is not None:
            hw, hh = hat_img.get_size()
            hsw = max(1, int(hw * scale))
            hsh = max(1, int(hh * scale))
            scaled_hat = pygame.transform.scale(hat_img, (hsw, hsh))
            ox, oy = self._hat_offset_right if self.facing == "RIGHT" else self._hat_offset_left
            sox = int(ox * scale)
            soy = int(oy * scale)
            jitter_y = random.randint(-12, 12) if self.bite_timer > 0 else 0
            hx = mouth_rect.centerx + sox
            hy = mouth_rect.centery + soy + jitter_y
            surface.blit(scaled_hat, (hx, hy))

    def circle_hit(self, point: tuple[int, int], radius: int = 0) -> bool:
        cx, cy = self.rect.center
        cr = min(self.rect.width, self.rect.height) // 2
        dx = point[0] - cx
        dy = point[1] - cy
        rr = (cr + radius)
        return (dx * dx + dy * dy) <= (rr * rr)

    def update_dying(self, dt: float):
        if not self.dying:
            return
        self.rect.y += int(420 * dt)
        self.death_timer -= dt
        self._smoke_cd -= dt
        if self._smoke_cd <= 0.0:
            self._smoke.append(Smoke(self.rect.center))
            self._smoke_cd = 0.07
        for s in list(self._smoke):
            s.update(dt)
            if not s.alive:
                self._smoke.remove(s)

    # --- Hats API ---
    def set_hat(self, hat_name: str | None):
        if hat_name == getattr(self, "_hat_name", None) and getattr(self, "_hat_src_left", None) is not None:
            return

        self._hat_name = hat_name
        self._hat_src_left = None
        self._hat_src_right = None
        self._hat_img_left = None
        self._hat_img_right = None

        if not hat_name:
            return

        path = os.path.join(ASSET_HAT_DIR, hat_name)
        try:
            img = pygame.image.load(path).convert_alpha()
            bw, bh = MOUTH_SIZE
            target_w = max(1, int(round(bw * HAT_SCALE)))
            target_h = max(1, int(round(bh * HAT_SCALE)))
            hat_base = pygame.transform.scale(img, (target_w, target_h))
            self._hat_src_left = hat_base
            self._hat_src_right = pygame.transform.flip(hat_base, True, False)
            self._hat_img_left = self._hat_src_left
            self._hat_img_right = self._hat_src_right
        except Exception:
            self._hat_src_left = None
            self._hat_src_right = None
            self._hat_img_left = None
            self._hat_img_right = None

    # --- Status API ---
    def apply_cold(self, duration: float, speed_scale: float = 0.7):
        try:
            dur = float(duration)
        except Exception:
            dur = 0.0
        self.cold_timer = max(self.cold_timer, dur)
        try:
            sc = float(speed_scale)
        except Exception:
            sc = 0.7
        sc = max(0.1, min(1.0, sc))
        self.cold_speed_scale = min(self.cold_speed_scale, sc)

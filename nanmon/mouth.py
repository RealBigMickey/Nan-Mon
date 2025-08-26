from __future__ import annotations
import os
import math
import pygame
from typing import Tuple
import random
from .effects import Smoke
from .constants import (
    MOUTH_SIZE,
    SALTY_COLOR,
    SWEET_COLOR,
    WHITE,
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

class Mouth(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int, int]):
        super().__init__()
        self.mode = "SALTY"  # SALTY -> blue sprites, SWEET -> pink sprites
        self.facing = "RIGHT"  # LEFT/RIGHT
        self._sprites = self._load_sprites()
        # start with blue open right
        self.image = self._sprites[("SALTY", "RIGHT", "OPEN")].copy()
        self.rect = self.image.get_rect(center=pos)
        self.flash_timer = 0.0
        self.bite_timer = 0.0
        self.bite_total = 0.18  # 4格咬合動畫總時長（秒），可依需求調整
        # Hybrid movement: a target point moved by keys; mouth eases toward it
        self.target = pygame.Vector2(self.rect.center)
        self.vel = pygame.Vector2(0, 0)
        # death animation state
        self.dying = False
        self.death_timer = 0.0
        self._smoke_cd = 0.0
        self._smoke = []  # list[Smoke]
        # brief control dampening after big impacts to preserve momentum
        self.stagger_timer = 0.0
        # Hat state
        self._hat_name = None
        self._hat_img_left = None
        self._hat_img_right = None
        # Hat offsets (relative to mouth center) — tweak these to align manually
        self._hat_offset_left = (1, -38)   # when facing LEFT
        self._hat_offset_right = (-38, -38) # when facing RIGHT

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
            ("SALTY", "RIGHT", "OPEN"): "head_blue_left.png",  # 右邊 mirror 左邊
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
                # fallback: colored circle placeholder
                img = pygame.Surface(MOUTH_SIZE, pygame.SRCALPHA)
                color = SALTY_COLOR if key[0] == "SALTY" else SWEET_COLOR
                pygame.draw.circle(img, color, (MOUTH_SIZE[0]//2, MOUTH_SIZE[1]//2), min(MOUTH_SIZE)//2)
            # scale to desired mouth size with nearest-neighbor for crisp pixels
            img = pygame.transform.scale(img, MOUTH_SIZE)
            # 右邊自動 mirror
            if key[1] == "RIGHT":
                img = pygame.transform.flip(img, True, False)
            sprites[key] = img
        return sprites

    def update(self, dt: float, keys):
        if self.dying:
            # continue death physics and effects only
            self.update_dying(dt)
            # still tick timers for flashes/bites to update image/overlay
            if self.flash_timer > 0:
                self.flash_timer -= dt
            if self.bite_timer > 0:
                self.bite_timer -= dt
            self._update_image()
            return
        # Tick stagger timer
        if self.stagger_timer > 0:
            self.stagger_timer = max(0.0, self.stagger_timer - dt)

        # Horizontal: snappy, direct ship-like movement on X
        pos = pygame.Vector2(self.rect.center)
        # Allow both Arrow keys and WASD
        right = 1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0
        left = 1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0
        # Reduce horizontal control while staggered so momentum isn't killed instantly
        ctrl_scale_x = 0.35 if self.stagger_timer > 0 else 1.0
        vx = (right - left) * MOUTH_SPEED_X * ctrl_scale_x
        if vx < 0:
            self.facing = "LEFT"
        elif vx > 0:
            self.facing = "RIGHT"
        pos.x += vx * dt
        pos.x = max(self.rect.width//2, min(WIDTH - self.rect.width//2, pos.x))

        # Vertical: target Y moves by keys, mouth springs toward it
        down = 1 if (keys[pygame.K_DOWN] or keys[pygame.K_s]) else 0
        up = 1 if (keys[pygame.K_UP] or keys[pygame.K_w]) else 0
        # Ignore vertical input briefly during stagger to maintain knockback
        tdy = 0.0 if self.stagger_timer > 0 else (down - up) * MOUTH_SPEED * dt
        self.target.y = max(self.rect.height//2, min(HEIGHT - self.rect.height//2, self.target.y + tdy))
        self.target.x = pos.x  # spring acts only on Y

        # Spring toward target only on Y axis
        to_y = self.target.y - pos.y
        # During stagger, reduce spring pull and damping so the impulse carries farther
        k_scale = 0.35 if self.stagger_timer > 0 else 1.0
        d_scale = 0.65 if self.stagger_timer > 0 else 1.0
        ay = to_y * (MOUTH_SPRING_K * k_scale) - self.vel.y * (MOUTH_DAMPING * d_scale)
        self.vel.x = 0  # prevent horizontal spring
        self.vel.y += ay * dt
        if abs(self.vel.y) > MOUTH_MAX_SPEED:
            self.vel.y = MOUTH_MAX_SPEED if self.vel.y > 0 else -MOUTH_MAX_SPEED
        pos.y += self.vel.y * dt

        # Bounds and update rect
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
        # When flashing we also trigger a quick bite animation (used on eat outside to be explicit)
        # Image will get updated in update()

    def bite(self):
        # Public hook: call when an eat occurs (food or weak-point)
        self.bite_timer = MOUTH_BITE_DURATION
        self._update_image()

    def die(self):
        if not self.dying:
            self.dying = True
            self.death_timer = 1.6
            self._smoke_cd = 0.0

    def knockback(self, strength: float = 1800.0):
        """Apply a downward impulse to the mouth (force-like push)."""
        # Positive Y is downward in screen coords
        self.vel.y += strength
        # Also apply a small immediate displacement so the effect is visible even with damping
        self.rect.y += int(strength * 0.015)
        # Briefly dampen controls so the knockback isn't cancelled by input
        self.stagger(0.28)

    def stagger(self, duration: float):
        """Temporarily reduce control influence to preserve momentum."""
        self.stagger_timer = max(self.stagger_timer, duration)

    def _update_image(self):
        # 4連續咬合動畫
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
        # 咬合時放大+抖動
        if bite_state.startswith("BITE"):
            scale = 1.22
            w, h = img.get_width(), img.get_height()
            img = pygame.transform.scale(img, (int(w*scale), int(h*scale)))
            # 咬合時上下jitter（不裁切底部）
            jitter_y = random.randint(-12, 12)
            pad = abs(jitter_y)
            surf_h = img.get_height() + pad
            img_jitter = pygame.Surface((img.get_width(), surf_h), pygame.SRCALPHA)
            base_y = (surf_h - img.get_height()) // 2 + jitter_y
            img_jitter.blit(img, (0, base_y))
            # 不加閃光
            img = img_jitter
        # Only apply flash overlay if not biting; whiten only visible pixels
        if self.flash_timer > 0 and bite_state == "OPEN":
            good = getattr(self, "_flash_good", None)
            if good is True:
                tint = pygame.Color(180, 255, 180, 90)
            elif good is False:
                tint = pygame.Color(255, 120, 120, 105)
            else:
                tint = pygame.Color(255, 255, 255, 0)
            if tint.a > 0:
                # Build an overlay and use additive blend; alpha remains from base,
                # so fully transparent pixels stay invisible.
                overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                overlay.fill((tint.r, tint.g, tint.b, tint.a))
                img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.image = img

    def draw(self, surface: pygame.Surface):
        # smoke
        for s in list(self._smoke):
            s.draw(surface)
            if not s.alive:
                self._smoke.remove(s)

        draw_rect = self.rect.copy()
        if self.dying:
            jitter = 6
            draw_rect.x += random.randint(-jitter, jitter)
            draw_rect.y += random.randint(-jitter, jitter)

        # base mouth first
        surface.blit(self.image, draw_rect)

        if self.dying:
            overlay = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 60, 60, 120))
            tinted = self.image.copy()
            tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(tinted, draw_rect)

        # hat on top, facing-aware
        hat_img = None
        ox = oy = 0
        if self.facing == "RIGHT":
            hat_img = self._hat_img_right
            ox, oy = self._hat_offset_right
        else:
            hat_img = self._hat_img_left
            ox, oy = self._hat_offset_left

        # 帽子跟著嘴巴動畫一起動（放大/抖動）
        if hat_img is not None:
            # 嘴巴咬合時帽子也放大
            scale = 1.0
            if hasattr(self, 'bite_timer') and self.bite_timer > 0:
                scale = 1.22
            hat_w, hat_h = hat_img.get_width(), hat_img.get_height()
            if scale != 1.0:
                hat_img_scaled = pygame.transform.scale(hat_img, (int(hat_w*scale), int(hat_h*scale)))
            else:
                hat_img_scaled = hat_img
            hx = draw_rect.centerx + int(ox * scale)
            hy = draw_rect.centery + int(oy * scale)
            surface.blit(hat_img_scaled, (hx, hy))

    def draw_scaled(self, surface: pygame.Surface, center: Tuple[int, int], scale: float = 1.0):
        """Draw the mouth (and hat) at an arbitrary scale centered at `center`.
        - Scales the current mouth image and hat sprites.
        - Offsets are scaled so hats stay aligned.
        """
        # Base (mouth)
        # 咬合動畫放大/抖動
        anim_scale = scale
        jitter_y = 0
        if hasattr(self, 'bite_timer') and self.bite_timer > 0:
            anim_scale = scale * 1.22
            jitter_y = random.randint(-12, 12)
        base_img = self.image
        bw, bh = base_img.get_size()
        sw = max(1, int(bw * anim_scale))
        sh = max(1, int(bh * anim_scale))
        scaled_mouth = pygame.transform.scale(base_img, (sw, sh))
        mouth_rect = scaled_mouth.get_rect(center=(center[0], center[1] + jitter_y))
        surface.blit(scaled_mouth, mouth_rect)

        # Hat on top (if any), scaled with同樣factor並加jitter
        hat_img = self._hat_img_right if self.facing == "RIGHT" else self._hat_img_left
        if hat_img is not None:
            hw, hh = hat_img.get_size()
            hsw = max(1, int(hw * anim_scale))
            hsh = max(1, int(hh * anim_scale))
            scaled_hat = pygame.transform.scale(hat_img, (hsw, hsh))
            ox, oy = self._hat_offset_right if self.facing == "RIGHT" else self._hat_offset_left
            sox = int(ox * anim_scale)
            soy = int(oy * anim_scale)
            hx = mouth_rect.centerx + sox
            hy = mouth_rect.centery + soy
            surface.blit(scaled_hat, (hx, hy))

    # Precise circle hit-test
    def circle_hit(self, point: tuple[int, int], radius: int = 0) -> bool:
        cx, cy = self.rect.center
        cr = min(self.rect.width, self.rect.height) // 2
        # if a target radius is provided, inflate the check by that radius
        dx = point[0] - cx
        dy = point[1] - cy
        rr = (cr + radius)
        return (dx * dx + dy * dy) <= (rr * rr)

    def update_dying(self, dt: float):
        if not self.dying:
            return
        # crash downwards
        self.rect.y += int(420 * dt)
        self.death_timer -= dt
        # spawn smoke puffs
        self._smoke_cd -= dt
        if self._smoke_cd <= 0.0:
            self._smoke.append(Smoke(self.rect.center))
            self._smoke_cd = 0.07
        # update smoke
        for s in list(self._smoke):
            s.update(dt)
            if not s.alive:
                self._smoke.remove(s)

    # --- Hats API ---
    def set_hat(self, hat_name: str | None):
        if hat_name == getattr(self, "_hat_name", None) and self._hat_img_left is not None:
            return
        self._hat_name = hat_name
        self._hat_img_left = None
        self._hat_img_right = None
        if not hat_name:
            return

        path = os.path.join(ASSET_HAT_DIR, hat_name)
        try:
            img = pygame.image.load(path).convert_alpha()
            # scale to mouth width so size stays consistent across frames
            target_w = max(1, self.image.get_width())
            scale = target_w / max(1, img.get_width())
            new_w = max(1, int(img.get_width() * scale))
            new_h = max(1, int(img.get_height() * scale))
            left = pygame.transform.scale(img, (new_w, new_h))
            right = pygame.transform.flip(left, True, False)

            self._hat_img_left = left
            self._hat_img_right = right
        except Exception:
            self._hat_img_left = None
            self._hat_img_right = None


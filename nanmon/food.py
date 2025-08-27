from __future__ import annotations
import os
import random
from typing import Tuple
import math
import pygame
from .constants import (
    SALTY_COLOR, SWEET_COLOR,
    FOOD_FALL_SPEED_RANGE, WIDTH, HEIGHT,
    HOMING_STRENGTH_WEAK, HOMING_STRENGTH_STRONG,
    HOMING_RANGE_SCALE, HOMING_MAX_VX,
    ASSET_FOOD_DIR, FOOD_SIZE,
    FOOD_HITBOX_SCALE,
)
from .levels import LevelConfig


KINDS = [
    # Level 1
    "DORITOS", "BURGERS", "FRIES", "ICECREAM", "SODA", "CAKE",
    # Level 2
    "SHAVEDICE", "DONUT", "CUPCAKE", "RIBS", "HOTDOG", "FRIEDCHICKEN",
        # HOTDOG splits into these
        "DOG", "BREAD",
    # Level 3
    "BEEFSOUP", "RICEBOWLCAKE", "TAINANPORRIDGE", "TAINANPUDDING", "TAINANICECREAM", "TAINANTOFUICE",
]

FOOD_IMAGE_FILES = {
    # Base
    "DORITOS": "DORITOS.png",
    "BURGERS": "BURGERS.png",
    "FRIES": "FRIES.png",
    "ICECREAM": "ICECREAM.png",
    "SODA": "SODA.png",
    "CAKE": "CAKE.png",
    "BUBBLETEA": "BUBBLETEA.png",
    "MANGOICE": "MANGOICE.png",
    "TOFUPUDDING": "TOFUPUDDING.png",
    "FRIEDCHICKEN": "FRIEDCHICKEN.png",
    "TAIWANBURGER": "TAIWANBURGER.png",
    "STINKYTOFU": "STINKYTOFU.png",
    # Level 2
    "SHAVEDICE": "SHAVEDICE.png",
    "DONUT": "DONUT.png",
    "CUPCAKE": "CUPCAKE.png",
    "RIBS": "RIBS.png",
        "HOTDOG": "HOTDOG.png",
        # HOTDOG split parts
        "DOG": "DOG.png",
        "BREAD": "BREAD.png",
    # Level 3
    "BEEFSOUP": "BEEFSOUP.png",
    "RICEBOWLCAKE": "RICEBOWLCAKE.png",
    "TAINANPORRIDGE": "TAINANPORRIDGE.png",
    "TAINANPUDDING": "TAINANPUDDING.png",
    "TAINANICECREAM": "TAINANICECREAM.png",
    "TAINANTOFUICE": "TAINANTOFUICE.png",
}

def _load_food_image(kind: str) -> pygame.Surface | None:
    """Try to load and scale the PNG; return None to fall back to geometry."""
    filename = FOOD_IMAGE_FILES.get(kind)
    if not filename:
        return None
    path = os.path.join(ASSET_FOOD_DIR, filename)
    if not os.path.exists(path):
        return None
    # Cache loaded/scaled images to avoid disk I/O and rescale cost during bursts
    if not hasattr(_load_food_image, "_cache"):
        _load_food_image._cache = {}
    cache = _load_food_image._cache  # type: ignore[attr-defined]
    key = (path, FOOD_SIZE)
    if key in cache:
        return cache[key]
    img = pygame.image.load(path).convert_alpha()
    img = pygame.transform.scale(img, FOOD_SIZE)
    cache[key] = img
    return img

class Food(pygame.sprite.Sprite):
    def __init__(
        self,
        kind: str,
        category: str,
        x: int,
        speed_y: float,
        homing: bool,
        *,
        spawn_center_y: int | None = None,
        scale: float = 1.0,
        hitbox_scale: float | None = None
    ):
        super().__init__()
        self.kind = kind
        self.category = category
        self.homing = homing
        self.vx = 0.0
        self.vy = speed_y
        # When neutralized (e.g., defused soup), skip collisions and let it fly away
        self.neutralized = False
        # Hitbox scale (relative to current sprite size); defaults to constant
        self.hitbox_scale = float(FOOD_HITBOX_SCALE if hitbox_scale is None else hitbox_scale)

        # try image first; fallback to geometry
        image = _load_food_image(kind)
        if image is not None:
            # Apply optional scale
            if abs(scale - 1.0) > 1e-3:
                w, h = image.get_size()
                sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
                image = pygame.transform.scale(image, (sw, sh))
            self.base_image = image
            self.image = self.base_image.copy()
        else:
            base_w, base_h = FOOD_SIZE
            if abs(scale - 1.0) > 1e-3:
                base_w = max(1, int(base_w * scale))
                base_h = max(1, int(base_h * scale))
            self.base_image = pygame.Surface((base_w, base_h), pygame.SRCALPHA)
            self.image = self.base_image.copy()
            self._draw_shape()

        # Mark if this food originated from a boss emission (spawn_center_y provided)
        self.from_boss = (spawn_center_y is not None)

        # SHAVEDICE/TAINANICECREAM: very slow fall for world foods; keep boss foods at normal boss speed
        if self.kind in ("SHAVEDICE", "TAINANICECREAM") and not self.from_boss:
            self.vy = min(self.vy, 140.0)

        # HOTDOG: will split into DOG + BREAD after a short delay
        self._split_timer = (random.uniform(0.4, 0.8) if self.kind == "HOTDOG" else None)
        self.spawn_children = None
        self.remove_me = False

        # Spawn from top by default, or from a provided center Y (e.g., boss center)
        if spawn_center_y is None:
            self.rect = self.image.get_rect(midtop=(x, -FOOD_SIZE[1]))
        else:
            self.rect = self.image.get_rect(center=(x, spawn_center_y))
        self.fx = float(self.rect.x)
        self.fy = float(self.rect.y)
        # Optional wobble state for S-shape trajectories
        self._wobble_t = 0.0
        self._wobble_prev = 0.0

    @property
    def hitbox(self) -> pygame.Rect:
        """Return a shrunken collision rect centered within sprite rect."""
        if self.hitbox_scale >= 0.999:
            return self.rect
        w = int(self.rect.width * self.hitbox_scale)
        h = int(self.rect.height * self.hitbox_scale)
        if w <= 0 or h <= 0:
            return pygame.Rect(self.rect.centerx, self.rect.centery, 1, 1)
        r = pygame.Rect(0, 0, w, h)
        r.center = self.rect.center
        return r

    def _draw_shape(self):
        # Simple geometric fallback if an image is missing
        s = self.base_image
        s.fill((0, 0, 0, 0))
        salty = (self.category == "SALTY")
        color = SALTY_COLOR if salty else SWEET_COLOR
        w, h = s.get_size()
        cx, cy = w // 2, h // 2
        # ellipse + border
        pygame.draw.ellipse(s, (*color[:3], 200), (2, 2, w - 4, h - 4))
        pygame.draw.ellipse(s, (0, 0, 0, 180), (2, 2, w - 4, h - 4), 2)
        # little highlight
        pygame.draw.circle(s, (255, 255, 255, 120), (int(cx * 0.65), int(cy * 0.55)), max(2, w // 10))

    def update(self, dt: float, mouth_pos: Tuple[int, int]):
        # Homing only if enabled
        if self.homing and mouth_pos is not None:
            target_x = mouth_pos[0]
            dx = target_x - (self.fx + self.rect.width / 2)

            # Strong baseline for certain kinds; RICEBOWLCAKE is strongest by far
            strong_set = {"BURGERS", "CAKE", "DONUT", "RICEBOWLCAKE"}
            base = HOMING_STRENGTH_STRONG if self.kind in strong_set else HOMING_STRENGTH_WEAK

            # DONUT: very strong tracking
            if self.kind == "DONUT":
                base *= 2.2

            # RICEBOWLCAKE: strongest tracking
            if self.kind == "RICEBOWLCAKE":
                base *= 3.4  # beef this up hard
                steer = max(-1.0, min(1.0, dx / 70.0))  # tighter steer
            else:
                steer = max(-1.0, min(1.0, dx / 90.0))

            scale = min(1.0, abs(dx) / HOMING_RANGE_SCALE)
            strength = base * (0.3 + 0.7 * scale)
            self.vx += strength * steer * 60 * dt

        # clamp horizontal speed
        if self.vx > HOMING_MAX_VX:
            self.vx = HOMING_MAX_VX
        elif self.vx < -HOMING_MAX_VX:
            self.vx = -HOMING_MAX_VX

        # integrate
        self.fx += self.vx * dt
        self.fy += self.vy * dt

        # Optional horizontal wobble (S-shape)
        if hasattr(self, 'wobble_amp') and getattr(self, 'wobble_amp'):
            self._wobble_t += dt
            freq = float(getattr(self, 'wobble_freq', 4.0))
            phase = float(getattr(self, 'wobble_phase', 0.0))
            amp = float(getattr(self, 'wobble_amp', 0.0))
            off = amp * math.sin(self._wobble_t * freq + phase)
            self.fx += (off - self._wobble_prev)
            self._wobble_prev = off

        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)

        # HOTDOG split behavior: replace self with DOG and BREAD
        if self._split_timer is not None and not self.remove_me:
            self._split_timer -= dt
            # If we're getting close to the bottom, force an early split so it's visible
            if (self.rect.top >= HEIGHT - 220) and self.spawn_children is None:
                self._split_timer = 0.0
            if self._split_timer <= 0 and self.spawn_children is None:
                cx, cy = self.rect.center

                # Horizontal speed based on fall speed (or a floor)
                hspeed = max(260.0, abs(self.vy))

                # Both parts are SALTY, inherit 0 vertical speed and opposite horizontal speeds
                dog = Food("DOG", "SALTY", cx - 10, 0.0, False, spawn_center_y=cy)
                bread = Food("BREAD", "SALTY", cx + 10, 0.0, False, spawn_center_y=cy)

                # Move purely horizontally in opposite directions
                dog.vx = -hspeed
                bread.vx = +hspeed

                # No vertical drift
                dog.vy = 0.0
                bread.vy = 0.0

                self.spawn_children = [dog, bread]
                self.remove_me = True

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

def make_food(rng: random.Random, level_cfg: LevelConfig | None = None) -> Food:
    if level_cfg is None:
        from .constants import HOMING_FRACTION
        homing_choice = rng.random() < HOMING_FRACTION
        if homing_choice:
            kind = rng.choice(["BURGERS", "CAKE"])  # defaults for level-less spawn
        else:
            kind = rng.choice(["DORITOS", "FRIES", "ICECREAM", "SODA"])
        category = "SALTY" if kind in ("DORITOS", "BURGERS", "FRIES") else "SWEET"
        speed_y = rng.uniform(*FOOD_FALL_SPEED_RANGE)
        x = rng.randint(20, WIDTH - 20)
        homing = (kind in ("BURGERS", "CAKE"))
        return Food(kind, category, x, speed_y, homing)
    else:
        homing_choice = rng.random() < level_cfg.homing_fraction
        if homing_choice and level_cfg.foods_homing:
            kind = rng.choice(level_cfg.foods_homing)
        else:
            pool = level_cfg.foods_light or ["DORITOS", "FRIES", "ICECREAM", "SODA"]
            kind = rng.choice(pool)

        salty_set = {
            # base salty
            "DORITOS", "BURGERS", "FRIES", "FRIEDCHICKEN", "RIBS",
            "HOTDOG", "TAIWANBURGER", "STINKYTOFU",
            # level 3 salty
            "BEEFSOUP", "RICEBOWLCAKE", "TAINANPORRIDGE",
        }
        # everything not in salty_set is SWEET, including:
        # TAINANPUDDING, TAINANICECREAM, TAINANTOFUICE

        category = "SALTY" if kind in salty_set else "SWEET"

        speed_y = rng.uniform(*level_cfg.food_fall_speed_range)
        x = rng.randint(20, WIDTH - 20)
        homing = (kind in tuple(level_cfg.foods_homing))
        scale = getattr(level_cfg, "food_scale", 1.0)
        hitbox_scale = getattr(level_cfg, "food_hitbox_scale", None)
        return Food(kind, category, x, speed_y, homing, scale=scale, hitbox_scale=hitbox_scale)

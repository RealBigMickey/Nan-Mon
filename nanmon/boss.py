"""Boss entity: always visible, emits sequential double rings, has a weak point target."""

from __future__ import annotations

import math
import random
import pygame

from .constants import (
    WIDTH,
    HEIGHT,
    WHITE,
    BOSS_Y,
    BOSS_SPEED_X,
    BOSS_SPEED_Y,
    BOSS_SHOT_INTERVAL,
    BOSS_FOOD_SPEED,
    BOSS_SIZE,
    BOSS_Y_TOP,
    BOSS_Y_BOTTOM,
    ASSET_BOSS_IMAGE,
    BOSS_RING_INTERVAL,
    BOSS_RING_PROJECTILES,
    BOSS_RING_PAIR_GAP,
    BOSS_HIT_FLASH_TIME,
    BOSS_BITES_TO_KILL,
    TARGET_RESPAWN_BASE,
    TARGET_RESPAWN_AFTER_BITE,
    BOSS_SPAWN_DURATION,
)
from .food import Food
from .target import Target
from .effects import Smoke


class Boss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        try:
            raw = pygame.image.load(ASSET_BOSS_IMAGE).convert_alpha()
            self.image = pygame.transform.smoothscale(raw, BOSS_SIZE)
        except Exception:
            self.image = pygame.Surface(BOSS_SIZE, pygame.SRCALPHA)
            pygame.draw.rect(self.image, WHITE, self.image.get_rect(), 2)

        # Start off-screen for spawn animation
        self.rect = self.image.get_rect(midtop=(WIDTH // 2, -BOSS_SIZE[1]))
        self.vx = BOSS_SPEED_X
        self.vy = BOSS_SPEED_Y
        self.left_bound = 40
        self.right_bound = WIDTH - 40
        self.shoot_cd = 0.0
        self.projectiles = pygame.sprite.Group()

        # Spawn state then active
        self.spawning = True
        self.spawn_timer = BOSS_SPAWN_DURATION
        self.spawn_total = BOSS_SPAWN_DURATION
        self.target_y = BOSS_Y
        self.active = False

        # Ring attack cadence
        self.ring_cd = BOSS_RING_INTERVAL * 0.5
        self._second_ring_pending = None

        # Weak point and state
        self.target = None
        self.target_cd = 0.4
        self.bites = 0
        self.dead = False
        self.hit_flash = 0.0
        self.pause_timer = 0.0
        # death animation
        self.dying = False
        self.death_timer = 0.0
        self._smoke_cd = 0.0
        self._smoke = []

    def update(self, dt: float):
        # Handle spawn animation: slide in from top and fade in
        if self.spawning:
            self.spawn_timer -= dt
            t = max(0.0, min(1.0, 1.0 - (self.spawn_timer / max(0.0001, self.spawn_total))))
            # Ease-out cubic for smooth landing
            ease = 1 - pow(1 - t, 3)
            # interpolate Y
            start_y = -self.rect.height
            end_y = self.target_y
            self.rect.top = int(start_y + (end_y - start_y) * ease)
            if self.spawn_timer <= 0.0:
                self.spawning = False
                self.active = True
                self.rect.top = end_y
            return
        if self.dead:
            return
        if self.dying:
            # death sequence: vibrate, spawn smoke, fall down
            self.death_timer -= dt
            # accelerate downward more strongly
            self.rect.y += int(220 * dt)
            self._smoke_cd -= dt
            if self._smoke_cd <= 0.0:
                self._smoke.append(Smoke(self.rect.center))
                self._smoke_cd = 0.06
            for s in list(self._smoke):
                s.update(dt)
                if not s.alive:
                    self._smoke.remove(s)
            if self.death_timer <= 0.0:
                self.dead = True
            return
        # Pause attacks after weak point hit
        if self.pause_timer > 0.0:
            self.pause_timer -= dt
            # Still update projectiles and weak point
            for f in list(self.projectiles):
                f.update(dt, (self.rect.centerx, self.rect.bottom))
                if (
                    f.rect.top > HEIGHT + 40
                    or f.rect.right < -80
                    or f.rect.left > WIDTH + 80
                ):
                    self.projectiles.remove(f)
            if self.target is None:
                self.target_cd -= dt
                if self.target_cd <= 0.0:
                    self.target = Target(self.rect)
                    self.target_cd = TARGET_RESPAWN_BASE
            else:
                self.target.update(dt, self.rect)
                if not self.target.alive:
                    self.target = None
                    self.target_cd = TARGET_RESPAWN_BASE
            return
        # Hit flash
        if self.hit_flash > 0:
            self.hit_flash -= dt
        # Movement
        self.rect.x += int(self.vx * dt)
        if self.rect.left < self.left_bound:
            self.rect.left = self.left_bound
            self.vx = abs(self.vx)
        elif self.rect.right > self.right_bound:
            self.rect.right = self.right_bound
            self.vx = -abs(self.vx)
        self.rect.y += int(self.vy * dt)
        if self.rect.top < BOSS_Y_TOP:
            self.rect.top = BOSS_Y_TOP
            self.vy = abs(self.vy)
        elif self.rect.bottom > BOSS_Y_BOTTOM:
            self.rect.bottom = BOSS_Y_BOTTOM
            self.vy = -abs(self.vy)
        # Rings: sequential pair
        self.ring_cd -= dt
        if self._second_ring_pending is not None:
            cat, t = self._second_ring_pending
            t -= dt
            if t <= 0.0:
                self.spawn_ring(cat)
                self._second_ring_pending = None
            else:
                self._second_ring_pending = (cat, t)
        if self.ring_cd <= 0.0 and self._second_ring_pending is None:
            first = random.choice(["SALTY", "SWEET"])
            second = "SWEET" if first == "SALTY" else "SALTY"
            self.spawn_ring(first)
            self._second_ring_pending = (second, BOSS_RING_PAIR_GAP)
            self.ring_cd = BOSS_RING_INTERVAL
        # Downward burst
        self.shoot_cd -= dt
        if self.shoot_cd <= 0.0:
            self.shoot_food_burst()
            self.shoot_cd = BOSS_SHOT_INTERVAL
        # Update projectiles
        for f in list(self.projectiles):
            f.update(dt, (self.rect.centerx, self.rect.bottom))
            if (
                f.rect.top > HEIGHT + 40
                or f.rect.right < -80
                or f.rect.left > WIDTH + 80
            ):
                self.projectiles.remove(f)
        # Manage weak point target
        if self.target is None:
            self.target_cd -= dt
            if self.target_cd <= 0.0:
                self.target = Target(self.rect)
                self.target_cd = TARGET_RESPAWN_BASE
        else:
            self.target.update(dt, self.rect)
            if not self.target.alive:
                self.target = None
                self.target_cd = TARGET_RESPAWN_BASE

    def shoot_food_burst(self):
        for _ in range(2):
            kind = random.choice(["DORITOS", "FRIES", "SODA", "ICECREAM"])  # light burst
            category = "SALTY" if kind in ("DORITOS", "BURGERS", "FRIES") else "SWEET"
            f = Food(
                kind,
                category,
                self.rect.centerx + random.randint(-40, 40),
                speed_y=BOSS_FOOD_SPEED,
                homing=False,
                spawn_center_y=self.rect.centery,
            )
            f.vx = random.uniform(-90, 90)
            self.projectiles.add(f)

    def spawn_ring(self, category: str):
        cx, cy = self.rect.center
        n = BOSS_RING_PROJECTILES
        speed = 260.0
        kinds = (
            "DORITOS",
            "FRIES",
            "BURGERS",
        ) if category == "SALTY" else (
            "ICECREAM",
            "SODA",
            "CAKE",
        )
        for i in range(n):
            ang = 2 * math.pi * (i / n)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            kind = random.choice(kinds)
            f = Food(kind, category, cx, speed_y=vy, homing=False, spawn_center_y=cy)
            f.vx = vx
            self.projectiles.add(f)

    def register_bite(self):
        self.bites += 1
        self.hit_flash = BOSS_HIT_FLASH_TIME
        self.pause_timer = 1.0  # Pause attacks for 1 second
        # Clear current target and use a shorter respawn
        if self.target is not None:
            self.target.alive = False
            self.target = None
            self.target_cd = TARGET_RESPAWN_AFTER_BITE
        if self.bites >= BOSS_BITES_TO_KILL:
            # start death animation instead of instant death
            self.dying = True
            self.death_timer = 2.2
            self._smoke_cd = 0.0

    def draw(self, surface: pygame.Surface):
        if self.dead:
            return
        draw_rect = self.rect.copy()
        if self.hit_flash > 0:
            jitter = 3
            draw_rect.x += random.randint(-jitter, jitter)
            draw_rect.y += random.randint(-jitter, jitter)
        if self.dying:
            jitter = 8
            draw_rect.x += random.randint(-jitter, jitter)
            draw_rect.y += random.randint(-jitter, jitter)
        # Base sprite (fade-in during spawn)
        if getattr(self, 'spawning', False):
            # Compute alpha based on progress
            t = 1.0
            if getattr(self, 'spawn_total', 0) > 0:
                t = max(0.0, min(1.0, 1.0 - (self.spawn_timer / self.spawn_total)))
            img = self.image.copy()
            img.set_alpha(int(255 * t))
            surface.blit(img, draw_rect)
        else:
            surface.blit(self.image, draw_rect)
        if self.hit_flash > 0 or self.dying:
            overlay = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            # while dying, blend to white as timer runs out
            if self.dying:
                t = max(0.0, min(1.0, 1.0 - (self.death_timer / 2.2)))
                red = 60 + int(195 * t)
                g = 60 + int(195 * t)
                b = 60 + int(195 * t)
                a = 120
                overlay.fill((red, g, b, a))
            else:
                overlay.fill((255, 60, 60, 120))
            surface.blit(overlay, draw_rect)
        # smoke on top of boss sprite
        for s in self._smoke:
            s.draw(surface)
        if self.target is not None and self.target.alive:
            self.target.draw(surface)
        for f in self.projectiles:
            f.draw(surface)

from __future__ import annotations
import math
import pygame
from typing import Tuple
from .constants import MOUTH_SIZE, SALTY_COLOR, SWEET_COLOR, WHITE, WIDTH, HEIGHT, FLASH_DURATION, MOUTH_SPEED, MOUTH_SPRING_K, MOUTH_DAMPING, MOUTH_MAX_SPEED, MOUTH_SPEED_X

class Mouth(pygame.sprite.Sprite):
    def __init__(self, pos: Tuple[int, int]):
        super().__init__()
        self.mode = "SALTY"
        self.color = SALTY_COLOR
        self.base_image = pygame.Surface(MOUTH_SIZE, pygame.SRCALPHA)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=pos)
        self.flash_timer = 0.0
        self._redraw()
        # Hybrid movement: a target point moved by keys; mouth eases toward it
        self.target = pygame.Vector2(self.rect.center)
        self.vel = pygame.Vector2(0, 0)

    def toggle_mode(self):
        self.mode = "SWEET" if self.mode == "SALTY" else "SALTY"
        self.color = SWEET_COLOR if self.mode == "SWEET" else SALTY_COLOR
        self._redraw()

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper):
        # Horizontal: snappy, direct ship-like movement on X
        pos = pygame.Vector2(self.rect.center)
        # Allow both Arrow keys and WASD
        right = 1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0
        left = 1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0
        vx = (right - left) * MOUTH_SPEED_X
        pos.x += vx * dt
        pos.x = max(self.rect.width//2, min(WIDTH - self.rect.width//2, pos.x))

        # Vertical: target Y moves by keys, mouth springs toward it
        down = 1 if (keys[pygame.K_DOWN] or keys[pygame.K_s]) else 0
        up = 1 if (keys[pygame.K_UP] or keys[pygame.K_w]) else 0
        tdy = (down - up) * MOUTH_SPEED * dt
        self.target.y = max(self.rect.height//2, min(HEIGHT - self.rect.height//2, self.target.y + tdy))
        self.target.x = pos.x  # spring acts only on Y

        # Spring toward target only on Y axis
        to_y = self.target.y - pos.y
        ay = to_y * MOUTH_SPRING_K - self.vel.y * MOUTH_DAMPING
        self.vel.x = 0  # prevent horizontal spring
        self.vel.y += ay * dt
        if abs(self.vel.y) > MOUTH_MAX_SPEED:
            self.vel.y = MOUTH_MAX_SPEED if self.vel.y > 0 else -MOUTH_MAX_SPEED
        pos.y += self.vel.y * dt

        # Bounds and update rect
        pos.y = max(self.rect.height//2, min(HEIGHT - self.rect.height//2, pos.y))
        self.rect.center = (int(pos.x), int(pos.y))
        if self.flash_timer > 0:
            self.flash_timer -= dt
            self._redraw()

    def flash(self, good: bool):
        self.flash_timer = FLASH_DURATION
        self._redraw(flash_good=good)

    def _redraw(self, flash_good: bool | None = None):
        self.image = self.base_image.copy()
        self.image.fill((0, 0, 0, 0))
        w, h = self.image.get_size()
        col = self.color
        if flash_good is True:
            col = pygame.Color(180, 255, 180)
        elif flash_good is False:
            col = pygame.Color(255, 120, 120)
        # Draw a circle for a clear circular visual and hitbox
        center = (w // 2, h // 2)
        radius = min(w, h) // 2
        pygame.draw.circle(self.image, col, center, radius)

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

    # Precise circle hit-test
    def circle_hit(self, point: tuple[int, int], radius: int = 0) -> bool:
        cx, cy = self.rect.center
        cr = min(self.rect.width, self.rect.height) // 2
        # if a target radius is provided, inflate the check by that radius
        dx = point[0] - cx
        dy = point[1] - cy
        rr = (cr + radius)
        return (dx * dx + dy * dy) <= (rr * rr)

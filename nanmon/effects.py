from __future__ import annotations
import random
import pygame


class Smoke:
    """Simple expanding, fading smoke puff."""
    def __init__(self, pos: tuple[int, int]):
        self.x, self.y = pos
        self.vx = random.uniform(-40, 40)
        self.vy = random.uniform(-20, -60)
        self.life = random.uniform(0.6, 1.2)
        self.age = 0.0
        self.base_r = random.randint(6, 12)
        self.color = (200, 200, 200)

    @property
    def alive(self) -> bool:
        return self.age < self.life

    def update(self, dt: float):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # gentle gravity
        self.vy += 30.0 * dt

    def draw(self, surface: pygame.Surface):
        if not self.alive:
            return
        t = max(0.0, min(1.0, self.age / self.life))
        alpha = int(180 * (1.0 - t))
        radius = int(self.base_r * (1.0 + 1.8 * t))
        if radius <= 0 or alpha <= 0:
            return
        puff = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(puff, (*self.color, alpha), (radius + 1, radius + 1), radius)
        surface.blit(puff, (int(self.x - radius), int(self.y - radius)))


class ScreenShake:
    """Simple screen shake: decays over time, provides an offset."""
    def __init__(self):
        self.time = 0.0
        self.duration = 0.0
        self.magnitude = 0.0

    def shake(self, duration: float = 0.4, magnitude: float = 8.0):
        self.duration = max(self.duration, duration)
        self.magnitude = max(self.magnitude, magnitude)
        self.time = self.duration

    def update(self, dt: float):
        if self.time > 0.0:
            self.time = max(0.0, self.time - dt)

    def offset(self) -> tuple[float, float]:
        if self.time <= 0.0:
            return (0.0, 0.0)
        # decay factor
        t = self.time / self.duration if self.duration > 0 else 0.0
        mag = self.magnitude * t
        return (
            random.uniform(-mag, mag),
            random.uniform(-mag, mag),
        )

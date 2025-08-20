from __future__ import annotations
import math
import pygame
from .constants import WIDTH, HEIGHT, WHITE, NECK_SWISH_AMPLITUDE, NECK_SWISH_SPEED

def draw_neck(surface: pygame.Surface, mouth_rect: pygame.Rect, t: float):
    start = (WIDTH//2, HEIGHT)
    base_y = HEIGHT - 120
    swish = int(NECK_SWISH_AMPLITUDE * math.sin(2 * math.pi * NECK_SWISH_SPEED * t))
    y = base_y + swish
    p1 = (start[0], y)
    p2 = (mouth_rect.centerx, y)
    p3 = (mouth_rect.centerx, mouth_rect.centery)
    pygame.draw.lines(surface, WHITE, False, [start, p1, p2, p3], 2)

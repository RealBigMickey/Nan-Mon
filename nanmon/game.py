from __future__ import annotations
import os
import random
import math
import pygame
from .constants import WIDTH, HEIGHT, FPS, RNG_SEED, BG_COLOR, WHITE, LEVEL_TARGET_SCORE, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX, MAX_ONSCREEN_FOOD, NAUSEA_MAX, NAUSEA_WRONG_EAT, NAUSEA_DECAY_PER_SEC
from .mouth import Mouth
from .food import Food, make_food
from .models import EatenCounters
from .neck import draw_neck
from .hud import draw_hud


def run_game(headless_seconds: float | None = None):
    rng = random.Random(RNG_SEED)

    if headless_seconds is not None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    except pygame.error as e:
        print("Pygame video init failed:", e)
        return
    pygame.display.set_caption("道地南蠻 — Salty/Sweet")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    mouth = Mouth((WIDTH//2, HEIGHT - 140))
    foods = pygame.sprite.Group()

    eaten = EatenCounters()
    score = 0
    nausea = 0.0

    spawn_timer = 0.0
    next_spawn = rng.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)

    level_cleared = False
    game_over = False

    legend_timer = 3.0

    running = True
    elapsed = 0.0
    while running:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE and not (level_cleared or game_over):
                    mouth.toggle_mode()
                if event.key == pygame.K_r and (level_cleared or game_over):
                    return "RESTART"

        keys = pygame.key.get_pressed()

        if not (level_cleared or game_over):
            mouth.update(dt, keys)

            if nausea > 0:
                nausea = max(0.0, nausea - NAUSEA_DECAY_PER_SEC * dt)

            spawn_timer += dt
            if spawn_timer >= next_spawn and len(foods) < MAX_ONSCREEN_FOOD:
                foods.add(make_food(rng))
                spawn_timer = 0.0
                next_spawn = rng.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)

            for f in list(foods):
                f.update(dt, mouth.rect.center)
                if f.rect.top > HEIGHT + 10 or f.rect.right < -50 or f.rect.left > WIDTH + 50:
                    foods.remove(f)

            for f in list(foods):
                if mouth.rect.colliderect(f.rect):
                    match = (mouth.mode == f.category)
                    mouth.flash(match)
                    if match:
                        score += 1
                        eaten.total += 1
                        eaten.per_type[f.kind] += 1
                    else:
                        nausea = min(NAUSEA_MAX, nausea + NAUSEA_WRONG_EAT)
                    foods.remove(f)

            if score >= LEVEL_TARGET_SCORE:
                level_cleared = True
            if nausea >= NAUSEA_MAX:
                game_over = True

        screen.fill(BG_COLOR)
        draw_neck(screen, mouth.rect, elapsed)
        for f in foods:
            f.draw(screen)
        mouth.draw(screen)

        legend_timer = max(0.0, legend_timer - dt)
        legend_alpha = int(255 * (legend_timer / 3.0)) if legend_timer > 0 else 0

        draw_hud(screen, font, mouth, nausea, eaten, score, legend_alpha, level_cleared, game_over)

        pygame.display.flip()

        if headless_seconds is not None and elapsed >= headless_seconds:
            running = False

    pygame.quit()

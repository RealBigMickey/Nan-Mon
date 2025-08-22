from __future__ import annotations
import os
import random
import math
import pygame
from .constants import (
    WIDTH, HEIGHT, FPS, RNG_SEED, BG_COLOR, WHITE,
    LEVEL_TARGET_SCORE, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    MAX_ONSCREEN_FOOD, NAUSEA_MAX, NAUSEA_WRONG_EAT, NAUSEA_DECAY_PER_SEC,
    BOSS_SPAWN_TIME, BOSS_HIT_DAMAGE,
)
from .mouth import Mouth
from .food import Food, make_food
from .models import EatenCounters
from .neck import draw_neck
from .hud import draw_hud
from .progress import Progress
from .boss import Boss
from .effects import Smoke, ScreenShake
#--Teddy add start--
from .init_menu import InitMenu 
from .background import ScrollingBackground 
from .constants import ASSET_FOOD_DIR,ASSET_BG_PATH 
#--Teddy add end--

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
# --- Teddy add start---
     # --- 開始畫面（headless 模式會略過） ---
    if headless_seconds is None:  # CI/無視窗測試不顯示開始畫面:contentReference[oaicite:3]{index=3}
        init_menu = InitMenu(
            image_path_1="nanmon/assets/init_menu_1.jpg",
            image_path_2="nanmon/assets/init_menu_2.jpg",
            anim_fps=2.0,  # 每秒 2 張
        )
        start = init_menu.loop(screen, clock)
        if not start:
            pygame.quit()
            return  # 使用者按 ESC 或關閉視窗
        
    # ---- 背景：兩張圖上下滾動並交替 ----
    bg = ScrollingBackground(
        image_paths=[
            os.path.join(ASSET_BG_PATH, "game_bg1.png"),
        os.path.join(ASSET_BG_PATH, "game_bg2.png"),
        ],
        canvas_size=(WIDTH, HEIGHT),
        speed_y=40.0,   # 想更快/更慢可調整
    )
# --- Teddy add end ---

    mouth = Mouth((WIDTH//2, HEIGHT - 140))
    foods = pygame.sprite.Group()
    boss: Boss | None = None
    progress = Progress(BOSS_SPAWN_TIME)
    # effects
    shake = ScreenShake()
    world_smoke: list[Smoke] = []
    world = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

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
        bg.update(dt) #Teddy add
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

            # Standard spawns nearly zero during boss
            if boss is None:
                spawn_timer += dt
                if spawn_timer >= next_spawn and len(foods) < MAX_ONSCREEN_FOOD:
                    foods.add(make_food(rng))
                    spawn_timer = 0.0
                    next_spawn = rng.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)

            # Spawn boss when progress ready
            progress.update(dt)
            if boss is None and progress.ready:
                boss = Boss()

            # Update foods
            for f in list(foods):
                f.update(dt, mouth.rect.center)
                if f.rect.top > HEIGHT + 10 or f.rect.right < -50 or f.rect.left > WIDTH + 50:
                    foods.remove(f)

            # Update boss and its projectiles
            if boss is not None:
                was_dead = boss.dead
                boss.update(dt)
                # Boss projectiles collision with mouth
                for proj in list(boss.projectiles):
                    if mouth.rect.colliderect(proj.rect):
                        match = (mouth.mode == proj.category)
                        mouth.flash(match)
                        if match:
                            mouth.bite()  # Show bite animation for boss foods
                        nausea = min(NAUSEA_MAX, nausea + BOSS_HIT_DAMAGE)
                        boss.projectiles.remove(proj)
                # Impact when boss just finished dying
                if (not was_dead) and boss.dead:
                    shake.shake(duration=0.6, magnitude=16)
                    # spawn a burst of smoke at impact
                    cx, by = boss.rect.centerx, min(HEIGHT - 20, boss.rect.bottom)
                    for _ in range(22):
                        s = Smoke((cx + random.randint(-60, 60), by - random.randint(0, 20)))
                        world_smoke.append(s)
                # Weak point: if target alive and bite flavor matches, register bite on eat below
                # Also allow direct circular contact with the weak point (no food required)
                if boss.active and boss.target is not None and boss.target.alive:
                    target_mode = "SALTY" if boss.target.color_key == "BLUE" else "SWEET"
                    if mouth.mode == target_mode:
                        t_center = boss.target.rect.center
                        t_radius = max(boss.target.rect.width, boss.target.rect.height) // 2
                        if mouth.circle_hit(t_center, radius=int(t_radius * 0.35)):
                            mouth.bite()
                            boss.register_bite()
                            # Apply strong force-based knockback to player instead of teleport
                            mouth.knockback(strength=3200.0)

            for f in list(foods):
                if mouth.rect.colliderect(f.rect):
                    match = (mouth.mode == f.category)
                    mouth.flash(match)
                    if match:
                        score += 1
                        eaten.total += 1
                        eaten.per_type[f.kind] += 1
                        mouth.bite()
                        # Boss weak point damage via correct-eat while target alive and matching mode
                        if boss is not None and boss.active and boss.target is not None and boss.target.alive:
                            target_mode = "SALTY" if boss.target.color_key == "BLUE" else "SWEET"
                            if mouth.mode == target_mode:
                                # Use circle hit instead of rect overlap for reliability
                                t_center = boss.target.rect.center
                                t_radius = max(boss.target.rect.width, boss.target.rect.height) // 2
                                if mouth.circle_hit(t_center, radius=int(t_radius * 0.4)):
                                    mouth.bite()
                                    boss.register_bite()
                    else:
                        nausea = min(NAUSEA_MAX, nausea + NAUSEA_WRONG_EAT)
                    foods.remove(f)

            # Boss death ends level
            if boss is not None and boss.dead:
                level_cleared = True

            if score >= LEVEL_TARGET_SCORE:
                level_cleared = True
            if nausea >= NAUSEA_MAX:
                if not game_over:
                    # trigger player death animation and shake once
                    mouth.die()
                    shake.shake(duration=0.45, magnitude=12)
                game_over = True

        # --- draw order --- (draw world to buffer first for camera shake)
        world.fill((0, 0, 0, 0))
        bg.draw(world, BG_COLOR)
        # Boss behind HUD but above background/neck; draw its projectiles with it
        if boss is not None:
            boss.draw(world)

        draw_neck(world, mouth.rect, elapsed)
        for f in foods:
            f.draw(world)
        mouth.draw(world)
        # draw world-level smoke (impacts)
        for s in list(world_smoke):
            s.update(dt)
            s.draw(world)
            if not s.alive:
                world_smoke.remove(s)

        # apply shake offset
        shake.update(dt)
        dx, dy = shake.offset()
        screen.blit(world, (int(dx), int(dy)))

        legend_timer = max(0.0, legend_timer - dt)
        legend_alpha = int(255 * (legend_timer / 3.0)) if legend_timer > 0 else 0

        draw_hud(screen, font, mouth, nausea, eaten, score, legend_alpha, level_cleared, game_over)
        # progress bar
        if not (level_cleared or game_over) and boss is None:
            progress.draw(screen)

        pygame.display.flip()

        if headless_seconds is not None and elapsed >= headless_seconds:
            running = False

    pygame.quit()

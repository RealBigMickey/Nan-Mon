from __future__ import annotations
import os
import random
import math
import pygame
from .constants import (
    WIDTH, HEIGHT, FPS, RNG_SEED, BG_COLOR, WHITE,
    SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    MAX_ONSCREEN_FOOD, NAUSEA_MAX, NAUSEA_WRONG_EAT, NAUSEA_DECAY_PER_SEC,
    BOSS_SPAWN_TIME, BOSS_HIT_DAMAGE,
    BOSS_HIT_DAMAGE_BY_KIND,
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
from .display_manager import DisplayManager
from .constants import FONT_PATH
from .clear_screen import FinishScreen
from .earth_bg_anim import draw_earth_bg_anim
import os
from .levels import get_level
from .level2_clear_anim import draw_level2_clear_anim #level2

def run_game(headless_seconds: float | None = None, smooth_scale: bool = False, margin: float = 0.95, start_level: int | None = None):
    rng = random.Random(RNG_SEED)

    if headless_seconds is not None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    # Create DPI-safe, resizable window with logical scaling
    try:
        dm = DisplayManager(
            margin=margin,
            use_integer_scale=not smooth_scale,
            caption="道地南蠻 — Salty/Sweet",
            bg_color=(BG_COLOR.r, BG_COLOR.g, BG_COLOR.b),
        )
    except pygame.error as e:
        return
    clock = pygame.time.Clock()
    font = pygame.font.Font(FONT_PATH, 16)
    # --- Teddy add start---
    # --- 開始畫面（headless 模式會略過） ---
    selected_level = start_level or 1  # default level or provided
    if headless_seconds is None and start_level is None:  # CI/無視窗測試與連續關卡時略過開始畫面
        init_menu = InitMenu(
            image_path_1="nanmon/assets/init_menu_1.jpg",
            image_path_2="nanmon/assets/init_menu_2.jpg",
            anim_fps=2.0,  # 每秒 2 張
        )
        _menu_res = init_menu.loop(dm, clock)
        selected_hat = None
        if isinstance(_menu_res, tuple):
            if len(_menu_res) >= 2:
                start = bool(_menu_res[0])
                selected_level = int(_menu_res[1])
                if len(_menu_res) >= 3:
                    selected_hat = _menu_res[2]
            elif len(_menu_res) == 1:
                start = bool(_menu_res[0])
            else:
                start = False
        else:
            start = bool(_menu_res)
        if not start:
            pygame.quit()
            return  # 使用者按 ESC 或關閉視窗

    # ---- Level setup ----
    level_cfg = get_level(selected_level)

    # Optional per-level music
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        music_path = level_cfg.music_path
        if music_path:
            abs_music_path = music_path
            if not os.path.isabs(music_path):
                abs_music_path = os.path.join(os.path.dirname(__file__), music_path)
            if os.path.exists(abs_music_path):
                pygame.mixer.music.load(abs_music_path)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(1.0)
    except Exception as e:
        pass

    # ---- 背景：兩張圖上下滾動並交替 ----
    bg = ScrollingBackground(
        image_paths=level_cfg.bg_images,
        canvas_size=(WIDTH, HEIGHT),
        speed_y=level_cfg.bg_scroll_speed,
    )
# --- Teddy add end ---

    mouth = Mouth((WIDTH//2, HEIGHT - 140))
    try:
        if 'selected_hat' in locals() and selected_hat:
            mouth.set_hat(selected_hat)
    except Exception:
        pass
    foods = pygame.sprite.Group()
    boss: Boss | None = None
    progress = Progress(level_cfg.boss_spawn_time)
    # effects
    shake = ScreenShake()
    world_smoke: list[Smoke] = []
    world = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    eaten = EatenCounters()
    score: float = 0.0
    nausea = 0.0

    spawn_timer = 0.0
    next_spawn = rng.uniform(level_cfg.spawn_interval_min, level_cfg.spawn_interval_max)

    level_cleared = False
    game_over = False

    legend_timer = 3.0

    running = True
    player_invincible = False
    elapsed = 0.0
    contact_push_cd = 0.0  # cooldown to avoid continuous boss-contact pushback
    boss_contact_prev = False  # track edge of collision with boss body
    # 加入選單音效
    menu_sound = None
    eat_sound = None
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        sound_path = os.path.join("nanmon", "assets", "sounds", "menu_select_sounds.ogg")
        eat_sound_path = os.path.join("nanmon", "assets", "sounds", "eat_sounds.wav")
        if os.path.exists(sound_path):
            menu_sound = pygame.mixer.Sound(sound_path)
        if os.path.exists(eat_sound_path):
            eat_sound = pygame.mixer.Sound(eat_sound_path)
    except Exception:
        menu_sound = None
    # Fade-in from black at gameplay start
    fade_in_time = 0.0
    fade_in_duration = 0.3
    fade_to_finish = False
    fade_finish_time = 0.0
    fade_finish_duration = 0.6
    waiting_clear_space = False
    # Page turn SFX for transitions
    page_turn_snd = None
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pt_path = os.path.join("nanmon", "assets", "sounds", "page_turn.mp3")
        if os.path.exists(pt_path):
            page_turn_snd = pygame.mixer.Sound(pt_path)
    except Exception:
        page_turn_snd = None

    earth_anim_state = {}  # 狀態保存於主循環外
    earth_anim_done = False
    l2_done = False
    while running:
        dt = clock.tick(FPS) / 1000.0
        bg.update(dt) #Teddy add
        elapsed += dt
        # cooldowns
        if contact_push_cd > 0.0:
            contact_push_cd = max(0.0, contact_push_cd - dt)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                dm.handle_resize(event)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if menu_sound:
                        menu_sound.play()
                    running = False
                if event.key == pygame.K_SPACE and not (level_cleared or game_over):
                    mouth.toggle_mode()
                if event.key == pygame.K_SPACE and game_over:
                    if menu_sound:
                        menu_sound.play()
                    return "RESTART"
                if event.key == pygame.K_SPACE and level_cleared:
                    # proceed to finish screen on space
                    if page_turn_snd:
                        try:
                            page_turn_snd.play()
                        except Exception:
                            pass
                    waiting_clear_space = False
                    fade_to_finish = True
                    fade_finish_time = 0.0
                if event.key == pygame.K_F6:
                    # Debug: force S-rank by boosting score and eaten count
                    level_cleared = True
                    # Ensure rank S (>= 2x target) and instant clear
                    score = 2000
                    eaten.total = 1
                    eaten.correct = 1
                    level_cleared = True
                if event.key == pygame.K_F7:
                    # Debug: instantly clear the level to test finish screen
                    level_cleared = True

        keys = pygame.key.get_pressed()

        if not (level_cleared or game_over):
            mouth.update(dt, keys)

            if nausea > 0:
                nausea = max(0.0, nausea - NAUSEA_DECAY_PER_SEC * dt)

            # Standard spawns nearly zero during boss
            if boss is None:
                spawn_timer += dt
                if spawn_timer >= next_spawn and len(foods) < level_cfg.max_onscreen_food:
                    foods.add(make_food(rng, level_cfg))
                    spawn_timer = 0.0
                    next_spawn = rng.uniform(level_cfg.spawn_interval_min, level_cfg.spawn_interval_max)

            # Spawn boss when progress ready
            progress.update(dt)
            if boss is None and progress.ready:
                boss = Boss()  # instantiate; Boss supports level config via attribute if available
                # Attach level config if Boss supports it
                try:
                    setattr(boss, "_lvl", level_cfg)
                except Exception:
                    pass
                # 播放boss音樂（背景音樂不停止）
                # 音效檔案：boss1_sounds.wav
                # 不在boss出現時自動播放音效

            # Update foods
            for f in list(foods):
                f.update(dt, mouth.rect.center)
                if f.rect.top > HEIGHT + 10 or f.rect.right < -50 or f.rect.left > WIDTH + 50:
                    foods.remove(f)

            # Update boss and its projectiles
            if boss is not None:
                was_dead = boss.dead
                boss.update(dt, player_pos=mouth.rect.center)
                # Become invincible once boss starts dying
                if getattr(boss, 'dying', False):
                    player_invincible = True
                # Boss projectiles collision with mouth
                for proj in list(boss.projectiles):
                    if mouth.rect.colliderect(proj.rect):
                        match = (mouth.mode == proj.category)
                        if getattr(level_cfg, 'invert_modes', False):
                            match = not match
                        mouth.flash(match)
                        if eat_sound:
                            eat_sound.play()
                        if match:
                            # Count boss foods toward eaten totals when correctly matched
                            mouth.bite()  # Show bite animation for boss foods
                            try:
                                eaten.total += 1
                                eaten.correct += 1
                                eaten.per_type[proj.kind] += 1
                            except Exception:
                                # Be robust if a projectile lacks kind or mapping
                                pass
                            # Boss foods contribute only a quarter score
                            score += 0.25
                        if not player_invincible and not match:
                            dmg = BOSS_HIT_DAMAGE_BY_KIND.get(getattr(proj, "kind", ""), BOSS_HIT_DAMAGE)
                            # Apply per-level multiplier
                            nausea = min(NAUSEA_MAX, nausea + dmg * getattr(level_cfg, 'nausea_damage_multiplier', 1.0))
                        boss.projectiles.remove(proj)
                # Impact when boss just finished dying
                if (not was_dead) and boss.dead:
                    shake.shake(duration=0.6, magnitude=16)
                    # 停止boss音樂
                    try:
                        boss.stop_boss_music()
                    except Exception:
                        pass
                    # spawn a burst of smoke at impact
                    cx, by = boss.rect.centerx, min(HEIGHT - 20, boss.rect.bottom)
                    for _ in range(22):
                        s = Smoke((cx + random.randint(-60, 60), by - random.randint(0, 20)))
                        world_smoke.append(s)
                # Weak point: if target alive and bite flavor matches, register bite on eat below
                # Also allow direct circular contact with the weak point (no food required)
                if boss.active and boss.target is not None and boss.target.alive:
                    target_mode = "SALTY" if boss.target.color_key == "BLUE" else "SWEET"
                    if getattr(level_cfg, 'invert_modes', False):
                        target_mode = "SWEET" if target_mode == "SALTY" else "SALTY"
                    if mouth.mode == target_mode:
                        t_center = boss.target.rect.center
                        t_radius = max(boss.target.rect.width, boss.target.rect.height) // 2
                        if mouth.circle_hit(t_center, radius=int(t_radius * 0.35)):
                            mouth.bite()
                            boss.register_bite()
                            # Apply strong force-based knockback to player instead of teleport
                            mouth.knockback(strength=12000.0)

                # Light pushback when touching the boss body (makes reaching target trickier)
                boss_contact_now = (
                    boss is not None
                    and boss.active
                    and not getattr(boss, 'spawning', False)
                    and not getattr(boss, 'dying', False)
                    and not boss.dead
                    and mouth.rect.colliderect(boss.rect)
                )
                if boss_contact_now and not boss_contact_prev and contact_push_cd <= 0.0 and not player_invincible:
                    # Light pushback on first contact with a long cooldown
                    mouth.knockback(strength=1200.0)
                    contact_push_cd = 2.0

            for f in list(foods):
                if mouth.rect.colliderect(f.rect):
                    # Optional inverted mode mechanic per-level
                    match = (mouth.mode == f.category)
                    if getattr(level_cfg, 'invert_modes', False):
                        match = not match
                    mouth.flash(match)
                    if eat_sound:
                        eat_sound.play()
                    if match:
                        score += 1.0
                        eaten.total += 1
                        eaten.correct += 1
                        eaten.per_type[f.kind] += 1
                        mouth.bite()
                        # Boss weak point damage via correct-eat while target alive and matching mode
                        if boss is not None and boss.active and boss.target is not None and boss.target.alive:
                            target_mode = "SALTY" if boss.target.color_key == "BLUE" else "SWEET"
                            if getattr(level_cfg, 'invert_modes', False):
                                target_mode = "SWEET" if target_mode == "SALTY" else "SALTY"
                            if mouth.mode == target_mode:
                                # Use circle hit instead of rect overlap for reliability
                                t_center = boss.target.rect.center
                                t_radius = max(boss.target.rect.width, boss.target.rect.height) // 2
                                if mouth.circle_hit(t_center, radius=int(t_radius * 0.4)):
                                    mouth.bite()
                                    boss.register_bite()
                                    mouth.knockback(strength=9000.0)
                    else:
                        # Count as eaten (wrong) and apply nausea if not invincible
                        eaten.total += 1
                        if not player_invincible:
                            nausea_add = getattr(level_cfg, 'nausea_wrong_eat', NAUSEA_WRONG_EAT)
                            nausea = min(NAUSEA_MAX, nausea + nausea_add)
                    foods.remove(f)

            # Boss death ends level
            if boss is not None and boss.dead:
                # 播放level clear音效（只播放一次）
                # 音效檔案：level_clear_sounds.wav
                if not level_cleared:
                    if boss and hasattr(boss, '_level_clear_snd') and boss._level_clear_snd:
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        pygame.mixer.stop()
                        boss._level_clear_snd.play()

                level_cleared = True

            if nausea >= NAUSEA_MAX and not player_invincible:
                if not game_over:
                    # trigger player death animation and shake once
                    mouth.die()
                    shake.shake(duration=0.45, magnitude=12)
                    # 播放game over音效（只播放一次）
                    # 音效檔案：game_over_sounds.wav
                    try:
                        if boss and hasattr(boss, '_game_over_snd') and boss._game_over_snd:
                            if not pygame.mixer.get_init():
                                pygame.mixer.init()
                            pygame.mixer.stop()
                            boss._game_over_snd.play()
                    except Exception:
                        pass
                game_over = True

        # --- draw order --- draw to world buffer then to logical frame with shake
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

        # apply shake offset into logical frame and present with letterboxing
        shake.update(dt)
        dx, dy = shake.offset()
        frame = dm.get_logical_surface()
        frame.fill((0, 0, 0, 0))
        frame.blit(world, (int(dx), int(dy)))

        legend_timer = max(0.0, legend_timer - dt)
        legend_alpha = int(255 * (legend_timer / 3.0)) if legend_timer > 0 else 0

        draw_hud(frame, font, mouth, nausea, eaten, int(score), legend_alpha, level_cleared, game_over)
        # If cleared, show continue prompt
        if level_cleared:
            if selected_level == 2:
                # ← 只有第二關用新的台灣+火球動畫
                if 'l2_anim_state' not in locals():
                    l2_anim_state = {}
                l2_anim_state['mouth_pos'] = mouth.rect.center  # (x, y)
                l2_anim_state['dt'] = dt
                l2_done = draw_level2_clear_anim(frame, l2_anim_state)
                # 動畫結束後，才允許 SPACE 進到結算畫面
                if l2_done:
                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                            if page_turn_snd:
                                try:
                                    page_turn_snd.play()
                                except Exception:
                                    pass
                            waiting_clear_space = False
                            fade_to_finish = True
                            fade_finish_time = 0.0
            else:
                # 其它關卡，沿用你原本的 earth 動畫
                earth_anim_state['dt'] = dt
                earth_anim_done = draw_earth_bg_anim(frame, earth_anim_state)
                if earth_anim_done:
                    # ...（保留你原本的 SPACE 進結算流程）
                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                            if page_turn_snd:
                                try:
                                    page_turn_snd.play()
                                except Exception:
                                    pass
                            waiting_clear_space = False
                            fade_to_finish = True
                            fade_finish_time = 0.0
                    
        # progress bar
        if not (level_cleared or game_over) and boss is None:
            progress.draw(frame)

        # Optional fades
        if fade_in_time < fade_in_duration:
            fade_in_time = min(fade_in_duration, fade_in_time + dt)
            t = fade_in_time / max(0.001, fade_in_duration)
            # Left-to-right wipe: start fully covered, reveal to the right quickly
            cover_x = int(WIDTH * t)
            cover_w = max(0, WIDTH - cover_x)
            if cover_w > 0:
                pygame.draw.rect(frame, (0, 0, 0), pygame.Rect(cover_x, 0, cover_w, HEIGHT))
        if fade_to_finish:
            fade_finish_time = min(fade_finish_duration, fade_finish_time + dt)
            t2 = fade_finish_time / max(0.001, fade_finish_duration)
            alpha2 = int(255 * t2)
            if alpha2 > 0:
                overlay2 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                # white flash to finish
                overlay2.fill((255, 255, 255, alpha2))
                frame.blit(overlay2, (0, 0))

        dm.present()

        # When level is cleared, break to the finish screen
        if level_cleared:
            # Wait for SPACE to begin transition
            if fade_to_finish and fade_finish_time >= fade_finish_duration:
                # 停止背景音樂
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                # 不再播放level clear音效
                fs = FinishScreen(eaten, level=selected_level, score=int(score), hat=(selected_hat if 'selected_hat' in locals() else None))
                res = fs.loop(dm, clock)
                # Handle next-level progression (wins) or restart (menu)
                if isinstance(res, tuple) and len(res) == 2 and res[0] == "NEXT_LEVEL":
                    next_level = int(res[1])
                    return ("NEXT_LEVEL", next_level)
                return "RESTART"

        # Track boss contact edge for next frame
        boss_contact_prev = boss_contact_now if 'boss_contact_now' in locals() else False

        if headless_seconds is not None and elapsed >= headless_seconds:
            running = False

    pygame.quit()
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
from .boss import Boss, DandanBurger, OrangePork, Coffin
from .effects import Smoke, ScreenShake
#--Teddy add start--
from .init_menu import InitMenu
from .background import ScrollingBackground
from .constants import ASSET_FOOD_DIR, ASSET_BG_PATH
#--Teddy add end--
from .display_manager import DisplayManager
from .constants import FONT_PATH
from .clear_screen import FinishScreen
from .earth_bg_anim import draw_earth_bg_anim
from .levels import get_level
from .level2_clear_anim import draw_level2_clear_anim  # level2
from .level3_clear_anim import draw_level3_clear_anim  # level3


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
    except pygame.error:
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
    except Exception:
        pass

    # ---- 背景：兩張圖上下滾動並交替 ----
    bg = ScrollingBackground(
        image_paths=level_cfg.bg_images,
        canvas_size=(WIDTH, HEIGHT),
        speed_y=level_cfg.bg_scroll_speed,
    )
    # --- Teddy add end ---

    mouth = Mouth((WIDTH // 2, HEIGHT - 140))
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
    l3_done = False
    # Level 3: parry gate state (spawn single beef soup until parried)
    l3_parry_gate = (selected_level == 3)
    l3_parry_done = False
    l3_parry_soup: Food | None = None

    # Helper: detect a truly parried soup striking the Coffin boss
    def _parried_soup_hits_boss(obj, _boss):
        return (
            _boss is not None and isinstance(_boss, Coffin) and
            getattr(obj, "kind", "") == "BEEFSOUP" and
            bool(getattr(obj, "neutralized", False)) and
            bool(getattr(obj, "parried_by_player", False)) and
            float(getattr(obj, "vy", 0.0)) < 0.0 and
            obj.rect.colliderect(_boss.rect)
        )

    while running:
        dt = clock.tick(FPS) / 1000.0
        # Stop background scrolling once Level 3 is cleared
        if not (level_cleared and selected_level == 3):
            bg.update(dt)  # Teddy add
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

            # Standard spawns nearly zero during boss; blocked during L3 parry gate
            if boss is None and not (l3_parry_gate and not l3_parry_done):
                spawn_timer += dt
                if spawn_timer >= next_spawn and len(foods) < level_cfg.max_onscreen_food:
                    foods.add(make_food(rng, level_cfg))
                    spawn_timer = 0.0
                    next_spawn = rng.uniform(level_cfg.spawn_interval_min, level_cfg.spawn_interval_max)

            # Spawn boss when progress ready
            # Block boss countdown until L3 parry completed
            if not (l3_parry_gate and not l3_parry_done):
                progress.update(dt)
            if boss is None and progress.ready and not (l3_parry_gate and not l3_parry_done):
                # Instantiate boss per level
                try:
                    from .boss import DandanBurger, OrangePork, Coffin
                except Exception:
                    DandanBurger = Boss  # fallback
                    OrangePork = Boss
                    Coffin = Boss
                if level_cfg and getattr(level_cfg, 'level', 1) == 1:
                    boss = DandanBurger(level_cfg)
                elif level_cfg and getattr(level_cfg, 'level', 1) == 2:
                    boss = OrangePork(level_cfg)
                elif level_cfg and getattr(level_cfg, 'level', 1) == 3:
                    boss = Coffin(level_cfg)
                else:
                    boss = Boss(level_cfg)
                # Attach level config if Boss supports it
                try:
                    setattr(boss, "_lvl", level_cfg)
                except Exception:
                    pass
                # 播放boss音樂（背景音樂不停止）
                # 音效檔案：boss1_sounds.wav
                # 不在boss出現時自動播放音效

            # Level 3 parry gate: ensure a single center BEEFSOUP is present until parried
            if l3_parry_gate and not l3_parry_done and l3_parry_soup is None:
                # Singular gate soup falls much slower to be readable
                speed_y = 220.0
                # BEEFSOUP is SALTY by design
                gate = Food("BEEFSOUP", "SALTY", WIDTH // 2, speed_y, False,
                            scale=getattr(level_cfg, "food_scale", 1.0),
                            hitbox_scale=getattr(level_cfg, "food_hitbox_scale", None))
                foods.add(gate)
                l3_parry_soup = gate

            # Update foods
            for f in list(foods):
                f.update(dt, mouth.rect.center)
                # If HOTDOG split produced children, add them and remove the parent
                spawn_kids = getattr(f, 'spawn_children', None)
                if spawn_kids:
                    for ch in spawn_kids:
                        foods.add(ch)
                    # clear to avoid duplicating next frame
                    f.spawn_children = None
                if getattr(f, 'remove_me', False):
                    foods.remove(f)
                    continue
                # Remove offscreen in any direction, including above when defused flies up
                if f.rect.top > HEIGHT + 10 or f.rect.right < -50 or f.rect.left > WIDTH + 50 or f.rect.bottom < -50:
                    foods.remove(f)

            # Update boss and its projectiles
            if boss is not None:
                was_dead = boss.dead
                boss.update(dt, player_pos=mouth.rect.center)
                # Become invincible once boss starts dying
                if getattr(boss, 'dying', False):
                    player_invincible = True
                # Boss projectiles: parry hits on boss, then collisions with player
                for proj in list(boss.projectiles):
                    # If a parried soup from boss pool hits the boss, score the hit and remove it
                    if _parried_soup_hits_boss(proj, boss):
                        try:
                            boss.register_parry_hit()
                        except Exception:
                            pass
                        try:
                            boss.projectiles.remove(proj)
                        except Exception:
                            pass
                        for _ in range(6):
                            world_smoke.append(Smoke((proj.rect.centerx + random.randint(-8, 8),
                                                      proj.rect.centery + random.randint(-8, 8))))
                        continue

                    # Use shrunken hitboxes for projectiles
                    hitbox = getattr(proj, 'hitbox', None)
                    proj_rect = hitbox if hitbox is not None else proj.rect

                    # Player collision with projectiles
                    if mouth.rect.colliderect(proj_rect):
                        # --- PARRY HAS PRIORITY (boss projectiles) ---
                        if getattr(proj, "kind", "") == "BEEFSOUP" and getattr(mouth, "switch_grace_timer", 0.0) > 0.0:
                            proj.neutralized = True
                            proj.parried_by_player = True
                            proj.vy = -520.0
                            proj.vx = random.uniform(-120.0, 120.0)
                            # Skip damage/removal so it can travel upward and potentially hit the boss
                            continue
                        # If already neutralized (parried), ignore collisions with the player
                        if getattr(proj, 'neutralized', False):
                            continue

                        match = (mouth.mode == proj.category)
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
                                pass
                            # Boss foods contribute only a quarter score
                            score += 0.25
                        # Wrong-eat boss projectile: apply penalty only if not currently invincible
                        if not player_invincible and not match and not mouth.is_invincible:
                            dmg = BOSS_HIT_DAMAGE_BY_KIND.get(getattr(proj, "kind", ""), BOSS_HIT_DAMAGE)
                            nausea = min(NAUSEA_MAX, nausea + dmg * getattr(level_cfg, 'nausea_damage_multiplier', 1.0))
                            # Knockback and grant brief i-frames
                            mouth.knockback(1800.0)
                            mouth.set_invincible(0.5)
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
                    if mouth.mode == target_mode:
                        t_center = boss.target.rect.center
                        t_radius = max(boss.target.rect.width, boss.target.height) // 2 if hasattr(boss.target, 'height') else max(boss.target.rect.width, boss.target.rect.height) // 2
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

            # Handle world foods (player collisions and parry)
            for f in list(foods):
                # Use shrunken hitbox for food collisions
                f_rect = getattr(f, 'hitbox', None)
                f_rect = f_rect if f_rect is not None else f.rect

                # If a parried soup (world pool) hits the boss, score the hit and remove it
                if _parried_soup_hits_boss(f, boss):
                    try:
                        boss.register_parry_hit()
                    except Exception:
                        pass
                    foods.remove(f)
                    for _ in range(6):
                        world_smoke.append(Smoke((f.rect.centerx + random.randint(-8, 8),
                                                  f.rect.centery + random.randint(-8, 8))))
                    continue

                # Skip player collision if already neutralized (parried)
                if getattr(f, 'neutralized', False):
                    continue

                if mouth.rect.colliderect(f_rect):
                    # --- PARRY HAS PRIORITY (works for sweet->salty and salty->sweet) ---
                    if f.kind == "BEEFSOUP" and getattr(mouth, "switch_grace_timer", 0.0) > 0.0:
                        if not getattr(f, "neutralized", False):
                            f.neutralized = True
                            f.parried_by_player = True
                            f.vy = -520.0
                            f.vx = random.uniform(-120.0, 120.0)
                            for _ in range(8):
                                world_smoke.append(Smoke((mouth.rect.centerx + random.randint(-12, 12),
                                                          mouth.rect.centery + random.randint(-12, 12))))
                            # L3 gate opens on first successful parry
                            if l3_parry_gate and not l3_parry_done:
                                l3_parry_done = True
                                if menu_sound:
                                    try:
                                        menu_sound.play()
                                    except Exception:
                                        pass
                        # IMPORTANT: skip eat/damage logic; let it fly upward to maybe hit boss
                        continue
                    # --- END: parry-priority ---

                    # Match mechanic
                    match = (mouth.mode == f.category)
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
                            if mouth.mode == target_mode:
                                # Use circle hit instead of rect overlap for reliability
                                t_center = boss.target.rect.center
                                t_radius = max(boss.target.rect.width, boss.target.rect.height) // 2
                                if mouth.circle_hit(t_center, radius=int(t_radius * 0.4)):
                                    mouth.bite()
                                    boss.register_bite()
                                    mouth.knockback(strength=9000.0)
                    else:
                        # Count as eaten (wrong) and apply penalty only if not invincible
                        eaten.total += 1
                        if not player_invincible and not mouth.is_invincible:
                            nausea_add = getattr(level_cfg, 'nausea_wrong_eat', NAUSEA_WRONG_EAT)
                            nausea = min(NAUSEA_MAX, nausea + nausea_add)
                            # SHAVEDICE wrong eat: apply cold status (slow + blue tint)
                            if f.kind == "SHAVEDICE":
                                mouth.apply_cold(duration=2.0, speed_scale=0.7)
                            # Knockback and grant brief i-frames
                            mouth.knockback(1800.0)
                            mouth.set_invincible(0.5)
                    foods.remove(f)

            # If the gate soup disappeared without a parry (ate or fell), respawn another
            if l3_parry_gate and not l3_parry_done and l3_parry_soup is not None and l3_parry_soup not in foods:
                l3_parry_soup = None

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
        # Freeze background when level 3 is cleared (stop scrolling)
        if level_cleared and selected_level == 3:
            # Draw current snapshot without further update; bg.update(dt) still ran, but that's OK visually
            bg.draw(world, BG_COLOR)
        else:
            bg.draw(world, BG_COLOR)
        # Boss behind HUD but above background/neck; draw its projectiles with it
        if boss is not None:
            boss.draw(world)

        draw_neck(world, mouth.rect, elapsed)
        # During Level 3 clear animation, skip drawing gameplay entities to avoid overlap
        if not (level_cleared and selected_level == 3):
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
            elif selected_level == 3:
                # Level 3: SCHOOL drop + walk-in animation
                if 'l3_anim_state' not in locals():
                    l3_anim_state = {}
                l3_anim_state['mouth_pos'] = mouth.rect.center
                l3_anim_state['dt'] = dt
                l3_done = draw_level3_clear_anim(frame, l3_anim_state)
                if l3_done:
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
                # On Level 3, return to main menu instead of next level
                if selected_level == 3:
                    return "RESTART"
                # Handle next-level progression (wins) or restart (menu) for other levels
                if isinstance(res, tuple) and len(res) == 2 and res[0] == "NEXT_LEVEL":
                    next_level = int(res[1])
                    return ("NEXT_LEVEL", next_level)
                return "RESTART"

        # Track boss contact edge for next frame
        boss_contact_prev = boss_contact_now if 'boss_contact_now' in locals() else False

        if headless_seconds is not None and elapsed >= headless_seconds:
            running = False

    pygame.quit()

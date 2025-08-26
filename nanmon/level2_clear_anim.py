# nanmon/level2_clear_anim.py
from __future__ import annotations
import os, math, pygame
from .constants import WIDTH, HEIGHT

# ===== Helpers =====
def _load_img(path: str, fallback_color=(255, 0, 255, 180)) -> pygame.Surface:
    try:
        if path and os.path.exists(path):
            return pygame.image.load(path).convert_alpha()
    except Exception:
        pass
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    s.fill(fallback_color)
    return s

def _fit_scale(img: pygame.Surface, max_w: int, max_h: int) -> float:
    iw, ih = img.get_width(), img.get_height()
    if iw == 0 or ih == 0:
        return 1.0
    return max(max_w / iw, max_h / ih)  # cover

def _lerp(a: float, b: float, t: float) -> float:
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t

def _blit_center(surface: pygame.Surface, img: pygame.Surface, center: tuple[int, int]):
    surface.blit(img, img.get_rect(center=center))

def _draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, line: int = 0):
    txt = font.render(text, True, (255, 255, 255))
    x = WIDTH // 2 - txt.get_width() // 2
    y = int(HEIGHT * 0.08) + line * (txt.get_height() + 8)
    shadow = font.render(text, True, (50, 50, 50))
    surface.blit(shadow, (x + 2, y + 2))
    surface.blit(txt, (x, y))

def rotate_about_anchor(img: pygame.Surface, angle_deg: float, anchor_offset: tuple[float, float]):
    rot_img = pygame.transform.rotozoom(img, angle_deg, 1.0)
    ox, oy = anchor_offset[0] - img.get_width() / 2, anchor_offset[1] - img.get_height() / 2
    rad = math.radians(-angle_deg)
    rx = ox * math.cos(rad) - oy * math.sin(rad)
    ry = ox * math.sin(rad) + oy * math.cos(rad)
    anchor_rot_x = rot_img.get_width() / 2 + rx
    anchor_rot_y = rot_img.get_height() / 2 + ry
    return rot_img, (anchor_rot_x, anchor_rot_y)

# ===== Main =====
def draw_level2_clear_anim(surface: pygame.Surface, state: dict) -> bool:
    """Level 2 Clear 動畫（含音效邏輯）：
       Phase 1: Taiwan 放大淡入 2s (無文字)
       Phase 2: Fireball 三段軌跡 4s (顯示「南蠻郎: 福爾摩沙!!」；Wind 迴圈中)
       Phase 3: 完成 (顯示結束兩行字；Wind 停止，Fireball 音效已播放一次)
    """
    if "init" not in state:
        state["init"] = True
        state["phase"] = 1
        state["timer"] = 0.0
        state["dt"] = state.get("dt", 1/60)

        # 圖片路徑（bg）
        state["taiwan_img"]  = _load_img(os.path.join("nanmon", "assets", "bg", "TAIWAN.png"))
        state["fire_img"]    = _load_img(os.path.join("nanmon", "assets", "bg", "FIRE.png"))

        # 時長
        state["dur_grow"] = 2.0
        state["fire_duration"] = 4.0

        # Taiwan scale & alpha（放大淡入到 0.7× cover）
        cover = _fit_scale(state["taiwan_img"], WIDTH, HEIGHT)
        state["taiwan_scale_start"]  = 0.08 * cover
        state["taiwan_scale_end"]    = 0.7  * cover
        state["taiwan_alpha_start"]  = 70
        state["taiwan_alpha_end"]    = 255

        # Fireball
        state["fire_time"] = 0.0
        state["fire_end_pos"]  = (WIDTH // 2, HEIGHT // 2)
        state["fire_start_pos"] = (int(-0.15 * WIDTH), int(HEIGHT * 1.15))
        state["fire_scale_start"] = 0.28
        state["fire_scale_end"]   = 0.0

        # 字型：Pixel Emulator
        pixel_font_path = os.path.join("nanmon", "assets", "Pixel Emulator.otf")
        try:
            state["font"] = pygame.font.Font(pixel_font_path, 28)
        except Exception:
            state["font"] = pygame.font.SysFont("arial", 24)

        # ===== 音效：安全載入 + 背景音樂播放 =====
        def _safe_init_mixer():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except Exception:
                pass
        def _load_snd(p):
            try:
                _safe_init_mixer()
                if os.path.exists(p):
                    return pygame.mixer.Sound(p)
            except Exception:
                pass
            return None
        snd_base = os.path.join("nanmon", "assets", "sounds")
        state["snd_level_clear"] = _load_snd(os.path.join(snd_base, "level_clear_sounds.wav"))
        state["snd_wind"]        = _load_snd(os.path.join(snd_base, "wind_sounds.wav"))
        state["snd_fireball"]    = _load_snd(os.path.join(snd_base, "fireball_sounds.wav"))
        state["wind_playing"]    = False
        state["fireball_played"] = False

        # 規格：關卡結束即播放 level_clear_sounds 當 BGM
        if state["snd_level_clear"]:
            try:
                # 當背景音樂：你可改成 play(-1) 讓它整段循環
                state["snd_level_clear"].play()
            except Exception:
                pass

    dt, phase, timer = state.get("dt", 1/60), state["phase"], state["timer"]

    # Phase 1: Taiwan 放大淡入（無文字）
    if phase == 1:
        timer += dt
        t = min(1.0, timer / state["dur_grow"])
        s = _lerp(state["taiwan_scale_start"], state["taiwan_scale_end"], t)
        a = int(_lerp(state["taiwan_alpha_start"], state["taiwan_alpha_end"], t))
        w0, h0 = state["taiwan_img"].get_width(), state["taiwan_img"].get_height()
        img = pygame.transform.scale(state["taiwan_img"], (int(w0*s), int(h0*s))).copy()
        img.fill((255, 255, 255, a), special_flags=pygame.BLEND_RGBA_MULT)
        _blit_center(surface, img, (WIDTH//2, HEIGHT//2))

        if t >= 1.0:
            # 進入火球階段：TAIWAN 已「凍結」於畫面
            phase, timer = 2, 0.0
            state["fire_time"] = 0.0
            state["shot_pos"] = tuple(state.get("mouth_pos", state["fire_start_pos"]))
            # 規格：此刻開始播放 WIND 迴圈
            if state["snd_wind"] and not state["wind_playing"]:
                try:
                    state["snd_wind"].play(-1)
                    state["wind_playing"] = True
                except Exception:
                    pass

    # Phase 2: Fireball 三段軌跡 4s（顯示「Formosa!!」；WIND 迴圈中）
    elif phase == 2:
        # 背景：Taiwan 以 0.7× cover 固定顯示（全彩、不透明）
        s = state["taiwan_scale_end"]
        w0, h0 = state["taiwan_img"].get_width(), state["taiwan_img"].get_height()
        _blit_center(surface, pygame.transform.scale(state["taiwan_img"], (int(w0*s), int(h0*s))),
                     (WIDTH//2, HEIGHT//2))

        # 火球狀態
        if "fire" not in state:
            state["fire"] = {
                "img": state["fire_img"].convert_alpha(),
                "pos": list(state["shot_pos"]),
                "fs": state["fire_scale_start"],
            }
        fire_state = state["fire"]

        # 進度
        state["fire_time"] += dt
        ft = min(1.0, state["fire_time"]/state["fire_duration"])

        # 3 段關鍵點（mouth -> 右中 -> 左中略上 -> 中央）
        p0 = state["shot_pos"]
        p1 = (int(WIDTH*0.82), int(HEIGHT*0.50))
        p2 = (int(WIDTH*0.18), int(HEIGHT*0.38))
        p3 = state["fire_end_pos"]

        # 輕位移的二次貝茲
        def quad(pa, pb, c, t_):
            omt=1-t_
            return (omt*omt*pa[0]+2*omt*t_*c[0]+t_*t_*pb[0],
                    omt*omt*pa[1]+2*omt*t_*c[1]+t_*t_*pb[1])
        if ft<1/3:
            seg_t=ft/(1/3); c=((p0[0]+p1[0])//2,(p0[1]+p1[1])//2+35); target=quad(p0,p1,c,seg_t)
        elif ft<2/3:
            seg_t=(ft-1/3)/(1/3); c=((p1[0]+p2[0])//2,(p1[1]+p2[1])//2-30); target=quad(p1,p2,c,seg_t)
        else:
            seg_t=(ft-2/3)/(1/3); c=((p2[0]+p3[0])//2,(p2[1]+p3[1])//2+45); target=quad(p2,p3,c,seg_t)

        # 更新位置與尺寸
        fire_state["pos"] = [target[0], target[1]]
        fs = max(0.0, _lerp(state["fire_scale_start"], state["fire_scale_end"], ft))
        fire_state["fs"] = fs
        if fs>0:
            fw, fh = int(state["fire_img"].get_width()*fs), int(state["fire_img"].get_height()*fs)
            _blit_center(surface, pygame.transform.scale(fire_state["img"], (fw, fh)),
                         (int(fire_state["pos"][0]), int(fire_state["pos"][1])))

        # 只有火球飛行時顯示文字
        _draw_text(surface, state["font"], "Formosa!!")

        # 結束：火球抵達中心並消失
        if ft >= 1.0:
            phase = 3
            try: del state["fire"]
            except Exception: pass
            # 規格：停止 WIND 迴圈、播放 FIREBALL 一次
            if state["wind_playing"] and state["snd_wind"]:
                try:
                    state["snd_wind"].stop()
                except Exception:
                    pass
                state["wind_playing"] = False
            if (not state["fireball_played"]) and state["snd_fireball"]:
                try:
                    state["snd_fireball"].play()
                except Exception:
                    pass
                state["fireball_played"] = True

    # Phase 3: 完成（顯示兩行白字）
    else:
        s = state["taiwan_scale_end"]
        w0, h0 = state["taiwan_img"].get_width(), state["taiwan_img"].get_height()
        _blit_center(surface, pygame.transform.scale(state["taiwan_img"], (int(w0*s), int(h0*s))),
                     (WIDTH//2, HEIGHT//2))
        _draw_text(surface, state["font"], "We have arrived in Taiwan!", line=0)
        _draw_text(surface, state["font"], "Press space to continue.", line=1)

    state["phase"], state["timer"] = phase, timer
    return phase >= 3

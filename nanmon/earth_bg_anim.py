import pygame
import os
import math
from .constants import WIDTH, HEIGHT

def draw_earth_bg_anim(surface, anim_state):
    """
    Draw earth_bg.png animation: from above screen, slowly moves down to center, width=WIDTH, height scaled.
    anim_state: dict with keys 'y', 'speed', 'img', 'done'
    """
    if anim_state.get('img_raw') is None:
        try:
            img_path = os.path.join(os.path.dirname(__file__), 'assets', 'bg', 'earth_bg1.png')
            img_raw = pygame.image.load(img_path).convert_alpha()
            anim_state['img_raw'] = img_raw
            # 固定大小，目標高度為畫面高度的2/3
            target_h = int(HEIGHT * (2/3))
            scale = target_h / img_raw.get_height()
            anim_state['scale'] = scale
            anim_state['done'] = False
            # 初始y在畫面頂端外面
            anim_state['y'] = -target_h
            anim_state['target_y'] = (HEIGHT - target_h) // 2
            anim_state['speed'] = 120  # 速度提升為原本的1.5倍 (pixels/sec)
        except Exception:
            anim_state['img_raw'] = None
            anim_state['done'] = True
    img_raw = anim_state.get('img_raw')
    scale = anim_state.get('scale', 1.0)
    dt = anim_state.get('dt', 1/60)
    y = anim_state.get('y', 0)
    target_y = anim_state.get('target_y', HEIGHT//2)
    speed = anim_state.get('speed', 80)
    if img_raw is not None:
        orig_w, orig_h = img_raw.get_width(), img_raw.get_height()
        cur_h = int(orig_h * scale)
        cur_w = int(orig_w * scale)
        img = pygame.transform.scale(img_raw, (cur_w, cur_h))
        # 飄動參數
        float_amplitude = 12  # 飄動幅度（像素）
        float_period = 2.5    # 完整上下週期（秒）
        # 記錄飄動時間
        if 'float_time' not in anim_state:
            anim_state['float_time'] = 0.0
        anim_state['float_time'] += dt
        if not anim_state.get('done'):
            if y < target_y:
                y = min(target_y, y + speed * dt)
                anim_state['y'] = y
            else:
                anim_state['y'] = target_y
                anim_state['done'] = True
                anim_state['float_time'] = 0.0  # 飄動從0開始
        rect = img.get_rect()
        rect.centerx = WIDTH // 2
        # 飄動效果：done時上下微幅擺動
        if anim_state.get('done'):
            float_offset = float_amplitude * math.sin(2 * math.pi * anim_state['float_time'] / float_period)
            rect.top = int(anim_state['y'] + float_offset)
        else:
            rect.top = int(anim_state['y'])
        surface.blit(img, rect)
    return anim_state.get('done', False)

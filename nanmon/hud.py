from __future__ import annotations
import pygame
from .constants import WIDTH, HEIGHT, WHITE, BG_COLOR, NAUSEA_MAX, SALTY_COLOR, SWEET_COLOR, FONT_PATH
from .mouth import Mouth
from .models import EatenCounters


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, mouth: Mouth, nausea: float, eaten: EatenCounters, score: int, legend_alpha: int, level_cleared: bool, game_over: bool):
    mode_text = f"Mode: {mouth.mode}"
    txt = font.render(mode_text, True, WHITE)
    surface.blit(txt, (12, 10))
    swatch_col = SWEET_COLOR if mouth.mode == "SWEET" else SALTY_COLOR
    pygame.draw.rect(surface, swatch_col, pygame.Rect(12 + txt.get_width() + 8, 14, 20, 12))

    bar_w, bar_h = 220, 16
    bar_x = WIDTH - bar_w - 12
    bar_y = 12
    pygame.draw.rect(surface, WHITE, pygame.Rect(bar_x-2, bar_y-2, bar_w+4, bar_h+4), 2)
    fill_w = int(bar_w * max(0, min(1, nausea / NAUSEA_MAX)))
    fill_col = pygame.Color(255, 120, 120) if nausea >= NAUSEA_MAX else pygame.Color(200, 200, 50)
    pygame.draw.rect(surface, fill_col, pygame.Rect(bar_x, bar_y, fill_w, bar_h))

    count_text = f"Eaten total: {eaten.total}  Score: {score}"
    txt2 = font.render(count_text, True, WHITE)
    surface.blit(txt2, (12, HEIGHT - 26))

    # 每種食物換行顯示且靠左
    food_types = ["DORITOS","BURGERS","FRIES","ICECREAM","SODA","CAKE"]
    # 預先計算高度，讓整體往上移動
    sample_txt = font.render("SAMPLE", True, WHITE)
    block_height = len(food_types) * (sample_txt.get_height() + 2)
    y = HEIGHT - 26 - 20 - block_height
    for k in food_types:
        line = f"{k}: {eaten.per_type[k]}"
        txt = font.render(line, True, WHITE)
        surface.blit(txt, (12, y))
        y += txt.get_height() + 2

    if legend_alpha > 0:
        legend = "Salty: triangle/burger/fries | Sweet: circle/soda/cake"
        # 自動縮小字型直到不超出螢幕
        font_size = font.get_height()
        legend_font = font
        legend_surf = legend_font.render(legend, True, WHITE)
        while legend_surf.get_width() > WIDTH - 40 and font_size > 8:
            font_size -= 2
            legend_font = pygame.font.Font(FONT_PATH, font_size)
            legend_surf = legend_font.render(legend, True, WHITE)
        legend_surf.set_alpha(legend_alpha)
        surface.blit(legend_surf, (WIDTH//2 - legend_surf.get_width()//2, 10 + txt.get_height() + 4))

    if level_cleared:
        msg = font.render("LEVEL CLEARED!", True, WHITE)
        surface.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 30))
    elif game_over:
        msg = font.render("GAME OVER!", True, WHITE)
        surface.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 30))

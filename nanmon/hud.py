from __future__ import annotations
import pygame
from .constants import WIDTH, HEIGHT, WHITE, BG_COLOR, NAUSEA_MAX, SALTY_COLOR, SWEET_COLOR
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

    types_line = " ".join(f"{k}:{eaten.per_type[k]}" for k in ["DORITOS","BURGERS","FRIES","ICECREAM","SODA","CAKE"]) 
    txt3 = font.render(types_line, True, WHITE)
    surface.blit(txt3, (12, HEIGHT - 26 - 20))

    if legend_alpha > 0:
        legend = "Salty: triangle/burger/fries | Sweet: circle/soda/cake"
        legend_surf = font.render(legend, True, WHITE)
        legend_surf.set_alpha(legend_alpha)
        surface.blit(legend_surf, (WIDTH//2 - legend_surf.get_width()//2, 10 + txt.get_height() + 4))

    if level_cleared:
        msg = font.render("LEVEL CLEARED – Press SPACE to restart", True, WHITE)
        surface.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 30))
    elif game_over:
        msg = font.render("GAME OVER – Press SPACE to restart", True, WHITE)
        surface.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 30))

from __future__ import annotations
import sys
import pygame
from typing import Tuple
from .constants import WIDTH as LOGICAL_W, HEIGHT as LOGICAL_H


class DisplayManager:
    """
    DPI-aware logical-to-window scaler with letterboxing.
    - Draw everything to the logical surface (LOGICAL_W x LOGICAL_H).
    - Call present() to scale and blit to a resizable window with aspect preserved.
    - Integer scaling by default for crisp pixel art; optional smooth scaling.
    """

    def __init__(
        self,
        margin: float = 0.95,
        use_integer_scale: bool = True,
        caption: str = "Game",
        bg_color: Tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        self.margin = float(max(0.1, min(1.0, margin)))
        self.use_integer_scale = bool(use_integer_scale)
        self.bg_color = bg_color

        # Logical surface the game renders into. Use SRCALPHA so it doesn't
        # depend on a display mode being set (convert_alpha requires that).
        self.logical = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)

        # Detect display size; provide sane fallback for dummy/headless
        info = pygame.display.Info()
        sw = info.current_w or (LOGICAL_W * 2)
        sh = info.current_h or (LOGICAL_H * 2)

        # Initial window size that fits within the screen (with margin)
        scale = min((sw * self.margin) / LOGICAL_W, (sh * self.margin) / LOGICAL_H)
        if self.use_integer_scale:
            scale = max(1, int(scale))
        else:
            scale = max(1.0, scale)
        win_w = int(LOGICAL_W * scale)
        win_h = int(LOGICAL_H * scale)

        # Create resizable window
        self.window = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
        pygame.display.set_caption(caption)

        # Derived state
        self.dest_rect = pygame.Rect(0, 0, win_w, win_h)
        self._recompute_letterbox()

    def _compute_scale(self, w: int, h: int) -> float:
        sx = w / LOGICAL_W
        sy = h / LOGICAL_H
        s = min(sx, sy)
        if self.use_integer_scale:
            s = max(1, int(s))
        else:
            s = max(1.0, s)
        return s

    def _recompute_letterbox(self) -> None:
        w, h = self.window.get_size()
        # Avoid zero sizes
        w = max(1, int(w))
        h = max(1, int(h))
        s = self._compute_scale(w, h)
        out_w, out_h = int(LOGICAL_W * s), int(LOGICAL_H * s)
        # Clamp to window
        out_w = min(out_w, w)
        out_h = min(out_h, h)
        x = (w - out_w) // 2
        y = (h - out_h) // 2
        self.dest_rect = pygame.Rect(x, y, out_w, out_h)

    def handle_resize(self, event: pygame.event.Event) -> None:
        # Enforce minimum size big enough for 1x logical rendering
        new_w = max(event.w, LOGICAL_W)
        new_h = max(event.h, LOGICAL_H)
        self.window = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
        self._recompute_letterbox()

    def get_logical_surface(self) -> pygame.Surface:
        return self.logical

    def present(self) -> None:
        # Fill letterbox bars
        self.window.fill(self.bg_color)
        # Choose scaling method
        if self.use_integer_scale:
            scaled = pygame.transform.scale(self.logical, self.dest_rect.size)
        else:
            scaled = pygame.transform.smoothscale(self.logical, self.dest_rect.size)
        self.window.blit(scaled, self.dest_rect.topleft)
        pygame.display.flip()

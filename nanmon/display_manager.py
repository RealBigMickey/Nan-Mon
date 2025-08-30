from __future__ import annotations
import sys
import pygame
from typing import Tuple
from .constants import WIDTH as LOGICAL_W, HEIGHT as LOGICAL_H, LETTERBOX_COLOR


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
        bg_color: Tuple[int, int, int] = (LETTERBOX_COLOR.r, LETTERBOX_COLOR.g, LETTERBOX_COLOR.b),  # Light grey for letterbox
        initial_size: Tuple[int, int] | None = None,
    ) -> None:
        self.margin = float(max(0.1, min(1.0, margin)))
        self.use_integer_scale = bool(use_integer_scale)
        self.bg_color = bg_color

        # Logical surface the game renders into. Use SRCALPHA so it doesn't
        # depend on a display mode being set (convert_alpha requires that).
        self.logical = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)

        # Create a resizable window
        if initial_size is None:
            # Default to logical size but allow resizing
            initial_size = (LOGICAL_W, LOGICAL_H)
        
        self.window = pygame.display.set_mode(initial_size, pygame.RESIZABLE)
        pygame.display.set_caption(caption)

        # Derived state
        self.dest_rect = pygame.Rect(0, 0, initial_size[0], initial_size[1])
        self._recompute_letterbox()

    def _compute_scale(self, w: int, h: int) -> float:
        # Compute scale to fill as much space as possible while preserving 2:3 aspect ratio
        # and ensuring content fits entirely within the window
        sx = w / LOGICAL_W
        sy = h / LOGICAL_H
        
        # Use minimum scale to ensure content fits (can be < 1 for scaling down)
        s = min(sx, sy)
        
        if self.use_integer_scale:
            # Only use integer scaling when scaling up significantly
            if s >= 2.0:
                s = int(s)
            # For scaling down or small scaling up, use exact scaling
            # Don't force minimum of 1.0 - allow scaling down
        
        return s

    def _recompute_letterbox(self) -> None:
        w, h = self.window.get_size()
        # Avoid zero sizes
        w = max(1, int(w))
        h = max(1, int(h))
        
        s = self._compute_scale(w, h)
        out_w, out_h = int(LOGICAL_W * s), int(LOGICAL_H * s)
        
        # Center the scaled content in the window
        x = (w - out_w) // 2
        y = (h - out_h) // 2
        self.dest_rect = pygame.Rect(x, y, out_w, out_h)

    def handle_resize(self, event: pygame.event.Event) -> None:
        # Handle window resize by recomputing letterbox
        if hasattr(event, 'size'):
            # Update window surface size
            self.window = pygame.display.set_mode(event.size, pygame.RESIZABLE)
        self._recompute_letterbox()

    def get_logical_surface(self) -> pygame.Surface:
        return self.logical

    def present(self) -> None:
        # Fill letterbox bars
        self.window.fill(self.bg_color)
        # Scale logical surface to fit destination rectangle
        scaled = pygame.transform.scale(self.logical, self.dest_rect.size)
        self.window.blit(scaled, self.dest_rect.topleft)
        pygame.display.flip()

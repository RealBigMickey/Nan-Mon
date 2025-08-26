import argparse
import os
import sys
import platform 
from nanmon.game import run_game

def _maybe_set_windows_dpi_aware():
    """Optionally set process DPI awareness on Windows to avoid OS upscaling.
    Safe no-op on non-Windows or if the API is unavailable.
    Must be called BEFORE pygame.init().
    """
    if platform.system() != "Windows":
        return
    try:
        import ctypes  # type: ignore
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        # Ignore failures; game still runs
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", type=float, default=None, nargs="?", help="Run headless for N seconds")
    parser.add_argument("--smooth-scale", action="store_true", help="Use non-integer smooth scaling (anti-aliased)")
    parser.add_argument("--margin", type=float, default=0.95, help="Initial window margin relative to display size (0..1)")
    args = parser.parse_args()

    # Optional Windows DPI awareness before pygame.init()
    _maybe_set_windows_dpi_aware()

    while True:
        res = run_game(headless_seconds=args.headless, smooth_scale=args.smooth_scale, margin=args.margin)
        if res == "RESTART":
            continue
        if isinstance(res, tuple) and len(res) == 2 and res[0] == "NEXT_LEVEL":
            # Start next level directly, skipping the menu
            _, lvl = res
            res = run_game(headless_seconds=args.headless, smooth_scale=args.smooth_scale, margin=args.margin, start_level=int(lvl))
            if res == "RESTART":
                continue
            if isinstance(res, tuple) and len(res) == 2 and res[0] == "NEXT_LEVEL":
                # loop to support multiple consecutive NEXT_LEVEL signals
                continue
            break
        break


if __name__ == "__main__":
    main()

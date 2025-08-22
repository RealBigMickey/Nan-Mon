# 道地南蠻 — Pixel-art Shoot-'em-up (Pygame)

A tiny pixel-art styled arcade game where you control a mouth that toggles between Salty and Sweet to eat matching foods. Mismatches build nausea.

Controls

- Arrows or WASD: Move
- Space: Toggle mode (Salty/Sweet). Also used to Start/Restart on the end screen
- Esc: Quit

Rules

- Eat foods that match your current mode color:
  - Salty (Pale Blue #A7D3FF): Doritos (triangle), Burgers (rounded rect, mild homing), Fries (thin rects)
  - Sweet (Pink #FF9ECF): Ice cream (circle), Soda (tall rect), Cake (trapezoid, mild homing)
- Wrong eat: Nausea +20
- Nausea decays at 2 per second
- Nausea reaching 100 ends the game
- Score +1 per correct eat; Level clears at 20 correct eats

Tech

- Python 3.10+
- pygame (latest stable)
- Window 600x900 (vertical), 60 FPS
- Deterministic RNG seed 42 per run

Run

1) Install deps
   pip install -r requirements.txt
2) Start the game
   python main.py

Dev/CI (headless)
You can run a headless smoke test (no window) for a couple seconds:
   On Windows PowerShell: set SDL_VIDEODRIVER=dummy; python main.py --headless 2

Notes

- All sprites use simple shapes for a placeholder pixel-art vibe.
- Neck is a cosmetic polyline from bottom-center to the mouth with two right-angle turns and a sinusoidal swish.

## Display scaling, DPI, and letterboxing

- The game renders to a logical surface of 600x900, then scales to the window while preserving aspect ratio with letterboxing.
- By default, scaling is integer-only for crisp pixel art. You can enable smooth non-integer scaling with:

   python main.py --smooth-scale

- Initial window size is chosen to fit within your display bounds using a margin (default 0.95). You can tweak it:

   python main.py --margin 0.9

- The window is resizable. On resize, the game recomputes scale and centers the content with black bars.
- On Windows, the app attempts to opt into DPI awareness to avoid OS upscaling; it still works if that call is not available.

Minimal usage example (for reference):

```python
from nanmon.display_manager import DisplayManager

dm = DisplayManager(margin=0.95, use_integer_scale=True, caption="Game")
frame = dm.get_logical_surface()

# your game draw:
frame.fill((0,0,0,0))
# ... draw sprites and HUD onto 'frame' ...

dm.present()  # scales to the window with letterboxing
```

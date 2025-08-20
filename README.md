# 道地南蠻 — Pixel-art Shoot-'em-up (Pygame)

A tiny pixel-art styled arcade game where you control a mouth that toggles between Salty and Sweet to eat matching foods. Mismatches build nausea.

Controls

- Arrows: Move
- Space: Toggle mode (Salty/Sweet)
- R: Restart when cleared or game over
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
- Window 800x600, 60 FPS
- Deterministic RNG seed 42 per run

Run

1) Install deps
   pip install -r requirements.txt
2) Start the game
   python main.py

Dev/CI (headless)
You can run a headless smoke test (no window) for a couple seconds:
   SDL_VIDEODRIVER=dummy python main.py --headless 2

Notes

- All sprites use simple shapes for a placeholder pixel-art vibe.
- Neck is a cosmetic polyline from bottom-center to the mouth with two right-angle turns and a sinusoidal swish.

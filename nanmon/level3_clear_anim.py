from __future__ import annotations
import os
import math
import random
import pygame
from .constants import WIDTH, HEIGHT

# ----------------------------- Helpers & Particles -----------------------------

class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "color", "size", "kind")
    def __init__(self, x, y, vx, vy, life, color, size, kind="dust"):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.life = float(life)
        self.color = color
        self.size = int(size)
        self.kind = kind

    def update(self, dt: float):
        self.life = max(0.0, self.life - dt)
        if self.kind == "dust":
            self.vx *= 0.98
            self.vy += 850.0 * dt
        elif self.kind == "confetti":
            self.vy += 400.0 * dt
            self.vx += math.sin(self.y * 0.05) * 12.0 * dt
        elif self.kind == "spark":
            self.vx *= 0.99
            self.vy *= 0.99
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def alive(self):
        return self.life > 0.0


def _load_img(path: str, fallback_size=(64, 64), color=(200, 60, 200, 200)) -> pygame.Surface:
    try:
        if path and os.path.exists(path):
            return pygame.image.load(path).convert_alpha()
    except Exception:
        pass
    s = pygame.Surface(fallback_size, pygame.SRCALPHA)
    s.fill(color)
    pygame.draw.rect(s, (0, 0, 0, 80), s.get_rect(), 2)
    return s


def _fit_scale_cover(img: pygame.Surface, max_w: int, max_h: int) -> float:
    iw, ih = img.get_width(), img.get_height()
    if iw == 0 or ih == 0:
        return 1.0
    return min(max_w / iw, max_h / ih)


def _blit_center(surface: pygame.Surface, img: pygame.Surface, center: tuple[int, int]):
    surface.blit(img, img.get_rect(center=center))


def _draw_circle_alpha(surf: pygame.Surface, color, center, radius: int, alpha: int):
    if radius <= 0 or alpha <= 0:
        return
    tmp = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(tmp, (*color[:3], alpha), (radius + 1, radius + 1), radius)
    surf.blit(tmp, (center[0] - radius - 1, center[1] - radius - 1))


def draw_level3_clear_anim(surface: pygame.Surface, state: dict) -> bool:
    """
    Level 3 clear animation (fixed):
      - School drops and settles.
      - Character starts at top, transforms while falling, LANDS (clamped).
      - After a brief beat, it drops "into" the doorway; we STOP drawing it the
        moment its top crosses the occlusion line so it never looks like it fell
        through the floor. Light pulse + dust. Then finish.
    """
    # ------------------------------ Init --------------------------------------
    if "init" not in state:
        state["init"] = True
        state["dt"] = float(state.get("dt", 1/60))
        state["timer"] = 0.0
        state["phase"] = 1

        # Load assets
        bg_dir = os.path.join("nanmon", "assets", "bg")
        char_dir = os.path.join("nanmon", "assets", "char")

        school_img = _load_img(os.path.join(bg_dir, "SCHOOL.png"), (360, 240))
        scale = _fit_scale_cover(school_img, int(WIDTH * 0.7), int(HEIGHT * 0.55))
        if scale != 1.0:
            school_img = pygame.transform.smoothscale(
                school_img,
                (int(school_img.get_width() * scale), int(school_img.get_height() * scale))
            )
        state["school_img"] = school_img

        # Standing mouth (quarter size)
        mouth_standing_full = _load_img(os.path.join(bg_dir, "MOUTH_STANDING.png"), (160, 160), (70, 180, 255, 220))
        mw, mh = mouth_standing_full.get_width(), mouth_standing_full.get_height()
        mouth_standing = pygame.transform.smoothscale(mouth_standing_full, (max(1, mw // 4), max(1, mh // 4)))
        state["mouth_img"] = mouth_standing

        # Blue-open (start of crossfade)
        blue_open = _load_img(os.path.join(char_dir, "head_blue_left.png"), (120, 120), (120, 200, 255, 220))
        bw, bh = blue_open.get_width(), blue_open.get_height()
        state["blue_open_img"] = pygame.transform.smoothscale(blue_open, (max(1, bw // 4), max(1, bh // 4)))

        # Ground reference
        state["ground_y"] = int(HEIGHT - 78)  # top-left y where the mouth stands on ground
        state["occlusion_y"] = state["ground_y"] - 2  # doorway line to hide the sprite on enter

        # School physics
        sch = state["school_img"]
        state["school_rect"] = sch.get_rect(midtop=(WIDTH // 2, -sch.get_height()))
        state["school_vy"] = 0.0
        state["gravity"] = 3400.0
        state["bounce"] = 0.10
        state["settled"] = False

        # Player starts above screen at doorway x
        door_x = state["school_rect"].centerx
        m_h = state["mouth_img"].get_height()
        state["player_pos"] = [float(door_x), float(-m_h)]  # we treat this as the TOP-LEFT y of the sprite
        state["fall_vy"] = 0.0
        state["fall_gravity"] = 2000.0

        # Transform while falling
        state["transform_time"] = 0.75
        state["transform_progress"] = 0.0

        # Enter drop (behind doorway)
        state["enter_vy"] = 0.0
        state["enter_gravity"] = 1700.0

        # FX
        state["particles"] = []
        state["light_pulse_t"] = 0.0
        state["light_pulse_on"] = False

        # Optional SFX
        def _safe_init_mixer():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except Exception:
                pass
        def _load_snd(path: str):
            try:
                _safe_init_mixer()
                if os.path.exists(path):
                    return pygame.mixer.Sound(path)
            except Exception:
                return None
            return None

        sdir = os.path.join("nanmon", "assets", "sounds")
        land_snd = None
        for candidate in ("thump.wav", "land.wav", "hit_wood.wav", "thud.wav"):
            s = _load_snd(os.path.join(sdir, candidate))
            if s:
                land_snd = s
                break
        enter_snd = None
        for candidate in ("whoosh.wav", "pop.wav", "door.wav", "enter.wav"):
            s = _load_snd(os.path.join(sdir, candidate))
            if s:
                enter_snd = s
                break
        state["land_snd"] = land_snd
        state["enter_snd"] = enter_snd

    # ------------------------------ Step ---------------------------------------
    dt = float(state.get("dt", 1/60))
    state["timer"] = float(state.get("timer", 0.0)) + dt
    phase = int(state.get("phase", 1))

    # Update particles
    particles: list[_Particle] = state["particles"]
    for p in list(particles):
        p.update(dt)
        if not p.alive:
            particles.remove(p)

    # Ground line
    pygame.draw.line(surface, (255, 255, 255, 80), (0, state["ground_y"]), (WIDTH, state["ground_y"]))

    # ------------------------------ Phases -------------------------------------

    # Phase 1: School drops in and settles
    if phase == 1:
        rect = state["school_rect"]
        if not state["settled"]:
            state["school_vy"] += state["gravity"] * dt
            rect.y += int(state["school_vy"] * dt)
            ground_top = state["ground_y"] - rect.height
            if rect.y >= ground_top:
                rect.y = ground_top
                if abs(state["school_vy"]) > 80.0:
                    state["school_vy"] = -abs(state["school_vy"]) * state["bounce"]
                    # Dust burst
                    left = rect.left + 16; right = rect.right - 16
                    for _ in range(12):
                        x = random.uniform(left, right)
                        vx = random.uniform(-240, 240)
                        vy = random.uniform(-520, -240)
                        size = random.randint(6, 11)
                        life = random.uniform(0.35, 0.7)
                        particles.append(_Particle(x, state["ground_y"] - 6, vx, vy, life, (210, 200, 190, 200), size, "dust"))
                else:
                    state["settled"] = True
                    for _ in range(8):
                        x = random.uniform(rect.left + 18, rect.right - 18)
                        vx = random.uniform(-120, 120)
                        vy = random.uniform(-260, -140)
                        size = random.randint(5, 9)
                        life = random.uniform(0.35, 0.6)
                        particles.append(_Particle(x, state["ground_y"] - 6, vx, vy, life, (220, 210, 200, 200), size, "dust"))

        surface.blit(state["school_img"], rect)

        for p in particles:
            if p.kind == "dust":
                alpha = max(0, min(255, int(255 * min(1.0, p.life / 0.7))))
                c = (*p.color[:3], alpha)
                pygame.draw.circle(surface, c, (int(p.x), int(p.y)), max(1, p.size))

        if state["settled"] and state["timer"] >= 0.50:
            state["phase"] = 2
            state["timer"] = 0.0

    # Phase 2: Transform WHILE falling, then LAND (clamped; no pass-through)
    elif phase == 2:
        surface.blit(state["school_img"], state["school_rect"])

        px, py = state["player_pos"]
        mimg = state["mouth_img"]
        mh = mimg.get_height()
        ground_y = float(state["ground_y"] - mh + 6)  # top-left y when standing on ground

        # Fall update
        state["fall_vy"] += state["fall_gravity"] * dt
        py += state["fall_vy"] * dt

        # Crossfade
        state["transform_progress"] = min(1.0, state["transform_progress"] + dt / max(0.001, state["transform_time"]))
        t = state["transform_progress"]

        bo = state["blue_open_img"]
        if t < 1.0:
            bo_sfc = bo.copy()
            bo_sfc.fill((255, 255, 255, int(255 * (1.0 - t))), special_flags=pygame.BLEND_RGBA_MULT)
            _blit_center(surface, bo_sfc, (int(px), int(py + bo.get_height() // 2)))
        ms_sfc = mimg.copy()
        ms_sfc.fill((255, 255, 255, int(255 * t)), special_flags=pygame.BLEND_RGBA_MULT)
        _blit_center(surface, ms_sfc, (int(px), int(py + mh // 2)))

        # LANDING CLAMP
        if py >= ground_y:
            py = ground_y
            state["fall_vy"] = 0.0  # important: kill velocity so we don't "tunnel"
            state["player_pos"] = [px, py]

            # FX
            door_left = state["school_rect"].centerx - mimg.get_width() // 2
            door_right = state["school_rect"].centerx + mimg.get_width() // 2
            for _ in range(10):
                x = random.uniform(door_left, door_right)
                vx = random.uniform(-180, 180)
                vy = random.uniform(-380, -180)
                size = random.randint(4, 8)
                life = random.uniform(0.3, 0.6)
                particles.append(_Particle(x, state["ground_y"] - 6, vx, vy, life, (220, 210, 200, 200), size, "dust"))
            s = state.get("land_snd")
            if s:
                try: s.play()
                except Exception: pass

            state["phase"] = 3
            state["timer"] = 0.0
        else:
            state["player_pos"] = [px, py]

    # Phase 3: Brief beat on the ground, then start the occluded enter-drop
    elif phase == 3:
        px, py = state["player_pos"]
        _blit_center(surface, state["mouth_img"], (int(px), int(py + state["mouth_img"].get_height() // 2)))
        surface.blit(state["school_img"], state["school_rect"])

        if state["timer"] >= 0.20:
            state["phase"] = 4
            state["timer"] = 0.0
            state["enter_vy"] = 0.0
            state["light_pulse_on"] = True
            state["light_pulse_t"] = 0.0
            s = state.get("enter_snd")
            if s:
                try: s.play()
                except Exception: pass

    # Phase 4: Enter drop. IMPORTANT: stop drawing once top crosses occlusion line.
    elif phase == 4:
        px, py = state["player_pos"]
        mh = state["mouth_img"].get_height()

        # Update enter fall first
        state["enter_vy"] += state["enter_gravity"] * dt
        py += state["enter_vy"] * dt
        state["player_pos"] = [px, py]

        # If still above the doorway line, draw it (under the school). Otherwise, hide.
        if py < state["occlusion_y"]:
            _blit_center(surface, state["mouth_img"], (int(px), int(py + mh // 2)))

        # School on top for occlusion
        surface.blit(state["school_img"], state["school_rect"])

        # Doorway light pulse
        if state["light_pulse_on"]:
            state["light_pulse_t"] += dt
            t = state["light_pulse_t"]
            if t <= 0.35:
                c = state["school_rect"].midbottom[0], state["ground_y"] - 6
                radius = int(20 + 280 * (t / 0.35))
                alpha = int(180 * (1.0 - (t / 0.35)))
                _draw_circle_alpha(surface, (255, 255, 220), c, radius, alpha)
            else:
                state["light_pulse_on"] = False

        # As soon as the sprite top is below floor by ~half-height, trigger finish FX and end
        if py >= state["ground_y"] + mh * 0.55:
            center_x = state["school_rect"].centerx
            base_y = state["ground_y"] - 6
            for _ in range(12):
                ang = random.uniform(-math.pi, 0.0)
                spd = random.uniform(220, 420)
                vx = math.cos(ang) * spd
                vy = math.sin(ang) * spd
                color = random.choice([(255, 240, 120, 240), (160, 240, 255, 240), (255, 140, 220, 240)])
                particles.append(_Particle(center_x, base_y, vx, vy, random.uniform(0.25, 0.45), color, random.randint(3, 5), "spark"))
            state["phase"] = 5
            state["timer"] = 0.0

    # Phase 5: Hold static scene briefly, then done
    else:
        surface.blit(state["school_img"], state["school_rect"])
        for p in particles:
            if p.kind == "dust":
                alpha = max(0, min(255, int(255 * min(1.0, p.life / 0.7))))
                c = (*p.color[:3], alpha)
                pygame.draw.circle(surface, c, (int(p.x), int(p.y)), max(1, p.size))
            else:
                alpha = max(0, min(255, int(255 * min(1.0, p.life / 0.6))))
                sfc = pygame.Surface((p.size, p.size), pygame.SRCALPHA)
                sfc.fill((*p.color[:3], alpha))
                surface.blit(sfc, (int(p.x), int(p.y)))
        if state["timer"] >= 0.45:
            return True

    return False

"""Boss entity: always visible, emits sequential double rings, has a weak point target.
Level-aware: accepts an optional LevelConfig to tweak visuals, movement, attacks, and health.
"""

from __future__ import annotations

import math
import random
import pygame

from .constants import (
    WIDTH,
    HEIGHT,
    WHITE,
    BOSS_Y,
    BOSS_SPEED_X,
    BOSS_SPEED_Y,
    BOSS_SHOT_INTERVAL,
    BOSS_FOOD_SPEED,
    BOSS_SIZE,
    BOSS_Y_TOP,
    BOSS_Y_BOTTOM,
    ASSET_BOSS_IMAGE,
    BOSS_RING_INTERVAL,
    BOSS_RING_PROJECTILES,
    BOSS_RING_PAIR_GAP,
    BOSS_HIT_FLASH_TIME,
    BOSS_BITES_TO_KILL,
    TARGET_RESPAWN_BASE,
    TARGET_RESPAWN_AFTER_BITE,
    BOSS_SPAWN_DURATION,
    BOSS_BEAM_INTERVAL,
    BOSS_BEAM_DURATION,
    BOSS_BEAM_RATE,
    BOSS_BEAM_SPEED,
)
from .food import Food
from .target import Target
from .effects import Smoke
from .levels import LevelConfig


class Boss(pygame.sprite.Sprite):
    def play_boss_music(self):
        if self._boss_snd:
            self._boss_snd.play(-1)

    def stop_boss_music(self):
        if self._boss_snd:
            self._boss_snd.stop()
    def __init__(self, level_cfg: LevelConfig | None = None):
        super().__init__()
        self._boss_shoot_played = False  # boss1_sounds.wav只播放一次
        self._lvl = level_cfg

        # Visuals
        img_path = ASSET_BOSS_IMAGE
        size = BOSS_SIZE
        if self._lvl:
            b = self._lvl.boss
            if b.image_path:
                img_path = b.image_path
            size = b.size
        try:
            raw = pygame.image.load(img_path).convert_alpha()
            self.image = pygame.transform.scale(raw, size)
        except Exception:
            self.image = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(self.image, WHITE, self.image.get_rect(), 2)

        # Start off-screen for spawn animation
        self.rect = self.image.get_rect(midtop=(WIDTH // 2, -size[1]))
        self.vx = (self._lvl.boss.speed_x if self._lvl else BOSS_SPEED_X)
        self.vy = (self._lvl.boss.speed_y if self._lvl else BOSS_SPEED_Y)
        self.left_bound = 40
        self.right_bound = WIDTH - 40
        self.shoot_cd = 0.0
        self.projectiles = pygame.sprite.Group()
        # 音效屬性
        import os
        boss_sound_path = os.path.join(os.path.dirname(__file__), 'assets', 'sounds', 'boss1_sounds.wav')
        hurt_sound_path = os.path.join(os.path.dirname(__file__), 'assets', 'sounds', 'boss1_hurt_sounds.wav')
        game_over_path = os.path.join(os.path.dirname(__file__), 'assets', 'sounds', 'game_over_sounds.wav')
        level_clear_path = os.path.join(os.path.dirname(__file__), 'assets', 'sounds', 'level_clear_sounds.wav')
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            if os.path.exists(boss_sound_path):
                self._boss_snd = pygame.mixer.Sound(boss_sound_path)
                self._boss_snd.set_volume(1.0)
            else:
                self._boss_snd = None
        except Exception as e:
            self._boss_snd = None
        try:
            if os.path.exists(hurt_sound_path):
                self._hurt_snd = pygame.mixer.Sound(hurt_sound_path)
                self._hurt_snd.set_volume(1.0)
            else:
                self._hurt_snd = None
        except Exception as e:
            self._hurt_snd = None
        try:
            if os.path.exists(game_over_path):
                self._game_over_snd = pygame.mixer.Sound(game_over_path)
            else:
                self._game_over_snd = None
        except Exception:
            self._game_over_snd = None
        try:
            if os.path.exists(level_clear_path):
                self._level_clear_snd = pygame.mixer.Sound(level_clear_path)
            else:
                self._level_clear_snd = None
        except Exception:
            self._level_clear_snd = None

        # Spawn state then active
        self.spawning = True
        self.spawn_timer = (self._lvl.boss.spawn_duration if self._lvl else BOSS_SPAWN_DURATION)
        self.spawn_total = self.spawn_timer
        self.target_y = (self._lvl.boss.y_target if self._lvl else BOSS_Y)
        self.active = False
        # Optional finite lifetime (no weak-point levels)
        self.lifetime = float(getattr(self._lvl.boss, 'lifetime_seconds', 0.0)) if self._lvl else 0.0

        # Ring attack cadence
        base_ring = (self._lvl.boss.ring_interval if self._lvl else BOSS_RING_INTERVAL)
        self.ring_cd = base_ring * 0.5
        self._second_ring_pending = None

        # Weak point and state
        self.target = None
        self.target_cd = 0.4
        self.bites = 0
        self.dead = False
        self.hit_flash = 0.0
        self.pause_timer = 0.0

        # Beam attack state
        self.beam_cd = 0.0
        self.beam_timer = 0.0
        self.beam_kind = None  # "DORITOS" or "SODA"
        self.beam_emit_accum = 0.0

        # death animation
        self.dying = False
        self.death_timer = 0.0
        self._smoke_cd = 0.0
        self._smoke = []
        # continuous fume while alive scales with damage
        self.fume_cd = 0.0

    def update(self, dt: float, player_pos: tuple[int, int] | None = None):
        # Handle spawn animation: slide in from top and fade in
        if self.spawning:
            self.spawn_timer -= dt
            t = max(0.0, min(1.0, 1.0 - (self.spawn_timer / max(0.0001, self.spawn_total))))
            # Ease-out cubic for smooth landing
            ease = 1 - pow(1 - t, 3)
            # interpolate Y
            start_y = -self.rect.height
            end_y = self.target_y
            # If smooth/center bounds are enabled, position using center to land precisely
            use_center = bool(getattr(self._lvl.boss, 'smooth_motion', False)) if self._lvl else False
            if use_center:
                start_cy = start_y + self.rect.height * 0.5
                end_cy = float(end_y + self.rect.height * 0.5)
                cy = start_cy + (end_cy - start_cy) * ease
                self.rect.centery = int(round(cy))
            else:
                self.rect.top = int(start_y + (end_y - start_y) * ease)
            if self.spawn_timer <= 0.0:
                self.spawning = False
                self.active = True
                if use_center:
                    self.rect.top = end_y
                else:
                    self.rect.top = end_y
            return
        if self.dead:
            return
        if self.dying:
            # death sequence: vibrate, spawn smoke, fall down
            self.death_timer -= dt
            # accelerate downward more strongly
            self.rect.y += int(220 * dt)
            self._smoke_cd -= dt
            if self._smoke_cd <= 0.0:
                self._smoke.append(Smoke(self.rect.center))
                self._smoke_cd = 0.06
            for s in list(self._smoke):
                s.update(dt)
                if not s.alive:
                    self._smoke.remove(s)
            if self.death_timer <= 0.0:
                self.dead = True
            return
        # Lifetime countdown for bosses that auto-end
        if self.active and self.lifetime and self.lifetime > 0.0:
            self.lifetime = max(0.0, self.lifetime - dt)
            if self.lifetime <= 0.0 and not self.dying:
                # Trigger death animation cleanly
                self.dying = True
                self.death_timer = 2.0
                self._smoke_cd = 0.0
                return
        # Pause attacks after weak point hit
        if self.pause_timer > 0.0:
            self.pause_timer -= dt
            # Still update projectiles and weak point
            for f in list(self.projectiles):
                f.update(dt, (self.rect.centerx, self.rect.bottom))
                if (
                    f.rect.top > HEIGHT + 40
                    or f.rect.right < -80
                    or f.rect.left > WIDTH + 80
                ):
                    self.projectiles.remove(f)
            if self.target is None:
                self.target_cd -= dt
                if self.target_cd <= 0.0:
                    self.target = Target(self.rect)
                    self.target_cd = TARGET_RESPAWN_BASE
            else:
                self.target.update(dt, self.rect)
                if not self.target.alive:
                    self.target = None
                    self.target_cd = TARGET_RESPAWN_BASE
            return
        # Hit flash
        if self.hit_flash > 0:
            self.hit_flash -= dt
        # Movement: support optional smooth float-centers and simple center-based bounds per level
        smooth = bool(getattr(self._lvl.boss, 'smooth_motion', False)) if self._lvl else False
        center_bounds = bool(getattr(self._lvl.boss, 'center_bounds', False)) if self._lvl else False
        # Define simple center-coordinate limits (independent of sprite size)
        min_cx = getattr(self, 'left_bound', 40)
        max_cx = getattr(self, 'right_bound', WIDTH - 40)
        y_top = (self._lvl.boss.y_top if self._lvl else BOSS_Y_TOP)
        y_bottom = (self._lvl.boss.y_bottom if self._lvl else BOSS_Y_BOTTOM)

        if smooth:
            # Initialize float centers if not present
            if not hasattr(self, '_fx') or not hasattr(self, '_fy'):
                self._fx = float(self.rect.centerx)
                self._fy = float(self.rect.centery)
            self._fx += self.vx * dt
            self._fy += self.vy * dt

            if center_bounds:
                # Bounce at simple center bounds
                if self._fx < min_cx:
                    self._fx = min_cx
                    self.vx = abs(self.vx)
                elif self._fx > max_cx:
                    self._fx = max_cx
                    self.vx = -abs(self.vx)
                if self._fy < y_top:
                    self._fy = y_top
                    self.vy = abs(self.vy)
                elif self._fy > y_bottom:
                    self._fy = y_bottom
                    self.vy = -abs(self.vy)
            else:
                # Legacy edge-based constraints
                if self._fx < self.left_bound + self.rect.width * 0.5:
                    self._fx = self.left_bound + self.rect.width * 0.5
                    self.vx = abs(self.vx)
                elif self._fx > self.right_bound - self.rect.width * 0.5:
                    self._fx = self.right_bound - self.rect.width * 0.5
                    self.vx = -abs(self.vx)
                if self._fy - self.rect.height * 0.5 < y_top:
                    self._fy = y_top + self.rect.height * 0.5
                    self.vy = abs(self.vy)
                elif self._fy + self.rect.height * 0.5 > y_bottom:
                    self._fy = y_bottom - self.rect.height * 0.5
                    self.vy = -abs(self.vy)

            # Write back
            self.rect.centerx = int(round(self._fx))
            self.rect.centery = int(round(self._fy))
        else:
            # Integer-based movement
            self.rect.x += int(self.vx * dt)
            self.rect.y += int(self.vy * dt)

            if center_bounds:
                # Bounce using center coords
                cx, cy = self.rect.center
                if cx < min_cx:
                    self.rect.centerx = min_cx
                    self.vx = abs(self.vx)
                elif cx > max_cx:
                    self.rect.centerx = max_cx
                    self.vx = -abs(self.vx)
                if cy < y_top:
                    self.rect.centery = y_top
                    self.vy = abs(self.vy)
                elif cy > y_bottom:
                    self.rect.centery = y_bottom
                    self.vy = -abs(self.vy)
            else:
                # Legacy edge-based constraints
                if self.rect.left < self.left_bound:
                    self.rect.left = self.left_bound
                    self.vx = abs(self.vx)
                elif self.rect.right > self.right_bound:
                    self.rect.right = self.right_bound
                    self.vx = -abs(self.vx)
                if self.rect.top < y_top:
                    self.rect.top = y_top
                    self.vy = abs(self.vy)
                elif self.rect.bottom > y_bottom:
                    self.rect.bottom = y_bottom
                    self.vy = -abs(self.vy)

        # Update existing smoke puffs even while alive
        for s in list(self._smoke):
            s.update(dt)
            if not s.alive:
                self._smoke.remove(s)

        # Emit fume that ramps up as boss takes hits
        bites_to_kill = (self._lvl.boss.bites_to_kill if self._lvl else BOSS_BITES_TO_KILL)
        damage_ratio = min(1.0, self.bites / max(1, bites_to_kill))
        fume_interval = max(0.18, 1.2 - 0.9 * damage_ratio)
        self.fume_cd -= dt
        if self.fume_cd <= 0.0 and not self.dying and self.active:
            # Spawn a small puff from the top area
            fx = self.rect.centerx + random.randint(-self.rect.width // 5, self.rect.width // 5)
            fy = self.rect.top + random.randint(0, 20)
            self._smoke.append(Smoke((fx, fy)))
            # Faster as damage increases
            self.fume_cd = fume_interval

        # Scale attack cadence based on remaining health:
        # start quite long at full health, shorten as damage accumulates
        health_ratio = max(0.0, 1.0 - (self.bites / max(1, bites_to_kill)))
        ring_base = (self._lvl.boss.ring_interval if self._lvl else BOSS_RING_INTERVAL)
        beam_base = (self._lvl.boss.beam_interval if self._lvl else BOSS_BEAM_INTERVAL)
        ring_interval = max(1.8, ring_base * (0.6 + 0.9 * health_ratio))
        beam_interval = max(2.5, beam_base * (0.7 + 1.0 * health_ratio))

        # Rings: sequential pair
        attacks_on = (self._lvl is None) or getattr(self._lvl.boss, 'attacks_enabled', True)
        if attacks_on:
            self.ring_cd -= dt
            if self._second_ring_pending is not None:
                cat, t = self._second_ring_pending
                t -= dt
                if t <= 0.0:
                    self.spawn_ring(cat)
                    self._second_ring_pending = None
                else:
                    self._second_ring_pending = (cat, t)
            if self.ring_cd <= 0.0 and self._second_ring_pending is None:
                first = random.choice(["SALTY", "SWEET"])
                second = "SWEET" if first == "SALTY" else "SALTY"
                self.spawn_ring(first)
                gap = (self._lvl.boss.ring_pair_gap if self._lvl else BOSS_RING_PAIR_GAP)
                self._second_ring_pending = (second, gap)
                self.ring_cd = ring_interval

        # Downward burst
        if attacks_on:
            self.shoot_cd -= dt
            if self.shoot_cd <= 0.0:
                self.shoot_food_burst()
                self.shoot_cd = (self._lvl.boss.shot_interval if self._lvl else BOSS_SHOT_INTERVAL)

        # Beam attack: sustained stream of one kind towards player (disabled if attacks_off)
        if attacks_on:
            self.beam_cd -= dt
            if self.beam_timer > 0.0:
                self.beam_timer = max(0.0, self.beam_timer - dt)
                # Emit foods at a steady rate
                rate = (self._lvl.boss.beam_rate if self._lvl else BOSS_BEAM_RATE)
                self.beam_emit_accum += rate * dt
                while self.beam_emit_accum >= 1.0:
                    self.beam_emit_accum -= 1.0
                    kinds = (self._lvl.boss.beam_kinds if self._lvl else ["DORITOS", "SODA"])
                    kind = self.beam_kind or random.choice(kinds)
                    salty_set = {"DORITOS", "BURGERS", "FRIES", "FRIEDCHICKEN", "RIBS", "HOTDOG", "TAIWANBURGER", "STINKYTOFU"}
                    category = "SALTY" if kind in salty_set else "SWEET"
                    # Aim horizontally at player if provided
                    px = player_pos[0] if player_pos is not None else self.rect.centerx
                    x = px
                    f = Food(
                        kind,
                        category,
                        x,
                        speed_y=(self._lvl.boss.beam_speed if self._lvl else BOSS_BEAM_SPEED),
                        homing=False,
                        spawn_center_y=self.rect.bottom,
                    )
                    # small spread
                    f.vx = random.uniform(-50, 50)
                    self.projectiles.add(f)
            elif self.beam_cd <= 0.0:
                # Start a new beam
                kinds = (self._lvl.boss.beam_kinds if self._lvl else ["DORITOS", "SODA"])  # all same kind
                self.beam_kind = random.choice(kinds)
                self.beam_timer = (self._lvl.boss.beam_duration if self._lvl else BOSS_BEAM_DURATION)
                self.beam_emit_accum = 0.0
                self.beam_cd = beam_interval

        # Update projectiles
        for f in list(self.projectiles):
            f.update(dt, (self.rect.centerx, self.rect.bottom))
            if (
                f.rect.top > HEIGHT + 40
                or f.rect.right < -80
                or f.rect.left > WIDTH + 80
            ):
                self.projectiles.remove(f)

        # Manage weak point target (optional per level)
        want_target = True
        if self._lvl is not None:
            want_target = bool(getattr(self._lvl.boss, 'has_weak_point', True))
        if want_target:
            if self.target is None:
                self.target_cd -= dt
                if self.target_cd <= 0.0:
                    self.target = Target(self.rect)
                    self.target_cd = TARGET_RESPAWN_BASE
            else:
                self.target.update(dt, self.rect)
                if not self.target.alive:
                    self.target = None
                    self.target_cd = TARGET_RESPAWN_BASE

    def shoot_food_burst(self):
        # If attacks are disabled for this boss (e.g., Level 2), do nothing
        if self._lvl is not None and not getattr(self._lvl.boss, 'attacks_enabled', True):
            return
        # Boss射食物時音效：boss1_sounds.wav，只播放一次
        if not self._boss_shoot_played and hasattr(self, '_boss_snd') and self._boss_snd:
            try:
                self._boss_snd.play()
                self._boss_shoot_played = True
            except Exception:
                pass
        foods = (self._lvl.boss.burst_foods if self._lvl else ["DORITOS", "FRIES", "SODA", "ICECREAM"])  # light burst
        for _ in range(2):
            kind = random.choice(foods)
            salty_set = {"DORITOS", "BURGERS", "FRIES", "FRIEDCHICKEN", "RIBS", "HOTDOG", "TAIWANBURGER", "STINKYTOFU"}
            category = "SALTY" if kind in salty_set else "SWEET"
            f = Food(
                kind,
                category,
                self.rect.centerx + random.randint(-40, 40),
                speed_y=(self._lvl.boss.food_speed if self._lvl else BOSS_FOOD_SPEED),
                homing=False,
                spawn_center_y=self.rect.centery,
            )
            f.vx = random.uniform(-90, 90)
            self.projectiles.add(f)

    def spawn_ring(self, category: str):
        cx, cy = self.rect.center
        n = (self._lvl.boss.ring_projectiles if self._lvl else BOSS_RING_PROJECTILES)
        speed = 260.0
        # Rings contain random foods of the same category
        if self._lvl:
            kinds = self._lvl.boss.ring_foods_salty if category == "SALTY" else self._lvl.boss.ring_foods_sweet
        else:
            kinds = (
                "DORITOS",
                "FRIES",
                "BURGERS",
            ) if category == "SALTY" else (
                "ICECREAM",
                "SODA",
                "CAKE",
            )
        for i in range(n):
            ang = 2 * math.pi * (i / n)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            kind = random.choice(kinds)
            f = Food(kind, category, cx, speed_y=vy, homing=False, spawn_center_y=cy)
            f.vx = vx
            self.projectiles.add(f)

    def register_bite(self):
        self.bites += 1
        self.hit_flash = BOSS_HIT_FLASH_TIME
        self.pause_timer = 1.8  # Pause attacks longer after a weak-point bite
        # Clear current target and use a longer respawn
        if self.target is not None:
            self.target.alive = False
            self.target = None
            self.target_cd = TARGET_RESPAWN_AFTER_BITE
            # 播放boss受傷音效
            if hasattr(self, '_hurt_snd') and self._hurt_snd:
                self._hurt_snd.play()
        thresh = (self._lvl.boss.bites_to_kill if self._lvl else BOSS_BITES_TO_KILL)
        if self.bites >= thresh:
            # start death animation instead of instant death
            self.dying = True
            self.death_timer = 2.2
            self._smoke_cd = 0.0

    def draw(self, surface: pygame.Surface):
        if self.dead:
            return
        draw_rect = self.rect.copy()
        # Progressive jitter/red tint as health drops
        thresh = (self._lvl.boss.bites_to_kill if self._lvl else BOSS_BITES_TO_KILL)
        bites = min(self.bites, thresh)
        health_ratio = max(0.0, 1.0 - (bites / max(1, thresh)))
        base_jitter = int((1.0 - health_ratio) * 3)
        if self.hit_flash > 0:
            jitter = base_jitter + 2
            draw_rect.x += random.randint(-jitter, jitter)
            draw_rect.y += random.randint(-jitter, jitter)
        if self.dying:
            jitter = 8
            draw_rect.x += random.randint(-jitter, jitter)
            draw_rect.y += random.randint(-jitter, jitter)

        # Base sprite (fade-in during spawn)
        if getattr(self, 'spawning', False):
            # Compute alpha based on progress
            t = 1.0
            if getattr(self, 'spawn_total', 0) > 0:
                t = max(0.0, min(1.0, 1.0 - (self.spawn_timer / self.spawn_total)))
            img = self.image.copy()
            img.set_alpha(int(255 * t))
            surface.blit(img, draw_rect)
        else:
            # Apply subtle baseline vibration that increases with damage
            if bites > 0 and not self.dying:
                vib = int((1.0 - health_ratio) * 2)
                if vib > 0:
                    draw_rect.x += random.randint(-vib, vib)
                    draw_rect.y += random.randint(-vib, vib)
            surface.blit(self.image, draw_rect)

        # Red tint overlay masked to non-transparent pixels only
        if self.hit_flash > 0 or self.dying or bites > 0:
            if self.dying:
                # While dying, intensify red instead of whitening
                t = max(0.0, min(1.0, 1.0 - (self.death_timer / 2.2)))
                tint = (150 + int(90 * t), 40, 40)
                alpha = 140
            else:
                t = 1.0 - health_ratio
                # Stronger red with more damage; slight boost during brief hit_flash
                r_boost = 30 if self.hit_flash > 0 else 0
                tint = (min(255, 80 + int(150 * t) + r_boost), 40, 40)
                alpha = 70 + int(90 * t)
            if alpha > 0:
                overlay = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
                overlay.fill((*tint, alpha))
                tinted = self.image.copy()
                tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(tinted, draw_rect)

        # smoke on top of boss sprite
        for s in self._smoke:
            s.draw(surface)
        if self.target is not None and self.target.alive:
            self.target.draw(surface)
        for f in self.projectiles:
            f.draw(surface)


class DandanBurger(Boss):
    """Level 1 boss: inherits full attack kit from base Boss."""
    def __init__(self, level_cfg: LevelConfig | None = None):
        super().__init__(level_cfg)
        # Ensure attacks remain enabled for Level 1
        if self._lvl is not None:
            try:
                self._lvl.boss.attacks_enabled = True
            except Exception:
                pass


class OrangePork(Boss):
    """Level 2 boss: unique sprite; attacks disabled for now, keep weak point and animations."""
    def __init__(self, level_cfg: LevelConfig | None = None):
        super().__init__(level_cfg)
        # Enforce attacks disabled
        if self._lvl is not None:
            try:
                self._lvl.boss.attacks_enabled = False
            except Exception:
                pass
        # Enforce sprite to orange_pork.png if not already applied
        img_path = "nanmon/assets/boss/orange_pork.png"
        try:
            raw = pygame.image.load(img_path).convert_alpha()
            size = self._lvl.boss.size if self._lvl else self.image.get_size()
            self.image = pygame.transform.scale(raw, size)
            # Keep current rect position and size
            prev = self.rect
            self.rect = self.image.get_rect(center=prev.center)
            # Keep float centers aligned with new rect
            self._fx = float(self.rect.centerx)
            self._fy = float(self.rect.centery)
            # Safety: ensure resized sprite remains fully on-screen horizontally
            left_bound = getattr(self, 'left_bound', 40)
            right_bound = getattr(self, 'right_bound', WIDTH - 40)
            min_cx = left_bound + (self.rect.width * 0.5)
            max_cx = right_bound - (self.rect.width * 0.5)
            if self._fx < min_cx:
                self._fx = min_cx
            elif self._fx > max_cx:
                self._fx = max_cx
            self.rect.centerx = int(round(self._fx))
        except Exception:
            # keep whatever base set
            pass


class Coffin(Boss):
    """Level 3 boss: coffin sprite, minimal movement, no weak point, passive."""
    def __init__(self, level_cfg: LevelConfig | None = None):
        super().__init__(level_cfg)
        # Enforce no attacks and no weak point regardless of config
        if self._lvl is not None:
            try:
                self._lvl.boss.attacks_enabled = False
                self._lvl.boss.has_weak_point = False
            except Exception:
                pass
        # Enforce sprite to coffin.png
        img_path = "nanmon/assets/boss/coffin.png"
        try:
            raw = pygame.image.load(img_path).convert_alpha()
            size = self._lvl.boss.size if self._lvl else self.image.get_size()
            self.image = pygame.transform.scale(raw, size)
            prev = self.rect
            self.rect = self.image.get_rect(center=prev.center)
            self._fx = float(self.rect.centerx)
            self._fy = float(self.rect.centery)
        except Exception:
            pass

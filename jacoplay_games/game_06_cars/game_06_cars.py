import os
import sys
import json
import math
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import pygame


# ==========================
# Config
# ==========================
LOGICAL_W, LOGICAL_H = 1920, 1080
TARGET_FPS = 60

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "game_06_data")
MEDIA_DIR = os.path.join(ROOT_DIR, "game_06_media")

CARS_JSON = os.path.join(DATA_DIR, "lista_auto.json")
TRACKS_JSON = os.path.join(DATA_DIR, "track_meta.json")

FONT_PATH = os.path.join(MEDIA_DIR, "A4SPEED-Bold.ttf")

MENU_BKG = os.path.join(MEDIA_DIR, "menu_bkg.png")
INSTR_BKG = os.path.join(MEDIA_DIR, "istruzioni_bkg.png")
MENU_MUSIC = os.path.join(MEDIA_DIR, "menu_music.mp3")
RACE_MUSIC_1 = os.path.join(MEDIA_DIR, "race_music1.mp3")
RACE_MUSIC_2 = os.path.join(MEDIA_DIR, "race_music2.mp3")
ENGINE_SOUNDS = [os.path.join(MEDIA_DIR, f"motore{i}.mp3") for i in range(1, 9)]
CRASH_SOUNDS = [os.path.join(MEDIA_DIR, f"crash{i}.mp3") for i in range(1, 6)]
BEEP_SOUND = os.path.join(MEDIA_DIR, "beep.mp3")

MUSIC_END_EVENT = pygame.USEREVENT + 1

TRACK1_RENDER = os.path.join(MEDIA_DIR, "track1_render.png")
TRACK1_SURFACE = os.path.join(MEDIA_DIR, "track1_surface.png")
TRACK2_RENDER = os.path.join(MEDIA_DIR, "track2_render.png")
TRACK2_SURFACE = os.path.join(MEDIA_DIR, "track2_surface.png")
TRACK3_RENDER = os.path.join(MEDIA_DIR, "track3_render.png")
TRACK3_SURFACE = os.path.join(MEDIA_DIR, "track3_surface.png")

TRACK_ASSETS = {
    "track01": (TRACK1_RENDER, TRACK1_SURFACE),
    "track02": (TRACK2_RENDER, TRACK2_SURFACE),
    "track03": (TRACK3_RENDER, TRACK3_SURFACE),
}

print("ROOT_DIR =", ROOT_DIR)
print("MEDIA_DIR =", MEDIA_DIR)
print("DATA_DIR  =", DATA_DIR)
print("MENU_BKG exists?", os.path.exists(MENU_BKG), MENU_BKG)
print("INSTR_BKG exists?", os.path.exists(INSTR_BKG), INSTR_BKG)

# Surface colors (RGB)
CLR_ROAD = (0, 0, 0)
CLR_GRASS = (0, 255, 0)
CLR_OIL = (255, 255, 0)
CLR_BOOST = (0, 0, 255)
CLR_REPAIR = (0, 255, 255)
CLR_WALL = (255, 0, 0)

VALID_SURFACE_COLORS = {CLR_ROAD, CLR_GRASS, CLR_OIL, CLR_BOOST, CLR_REPAIR, CLR_WALL}

# Lane system (virtual lanes)
LANE_HALF_WIDTH = 50  # pista ~ 200 px => come spec

# AI constants
AI_WP_REACH_DIST = 55
AI_OVERTAKE_DIST = 120
AI_LANE_COOLDOWN_MIN = 1.0
AI_LANE_COOLDOWN_MAX = 1.5

# Gameplay mapping (1..5 -> numeric)
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))

def map_1_5(val: int, out_min: float, out_max: float) -> float:
    # val: 1..5
    t = (val - 1) / 4.0
    return lerp(out_min, out_max, t)

def vec_length(v: pygame.Vector2) -> float:
    return math.hypot(v.x, v.y)

def safe_normalize(v: pygame.Vector2) -> pygame.Vector2:
    l = vec_length(v)
    if l < 1e-6:
        return pygame.Vector2(0, 0)
    return v / l

def angle_from_velocity(v: pygame.Vector2) -> float:
    # 0° = right, 90° = down, 180° = left, 270° = up
    if vec_length(v) < 1e-6:
        return 0.0
    return (math.degrees(math.atan2(v.y, v.x)) + 360.0) % 360.0


# ==========================
# Assets / helpers
# ==========================
def load_image(path: str, fallback_size=(64, 64), col=(200, 50, 50)) -> pygame.Surface:
    try:
        img = pygame.image.load(path).convert_alpha()
        return img
    except Exception:
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill(col)
        return surf

def load_font(size: int) -> pygame.font.Font:
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        return pygame.font.SysFont("arial", size)

def draw_text(surf: pygame.Surface, text: str, font: pygame.font.Font, x: int, y: int, color=(255, 255, 255)):
    img = font.render(text, True, color)
    surf.blit(img, (x, y))

def compute_letterbox(dst_w: int, dst_h: int) -> Tuple[pygame.Rect, float]:
    sx = dst_w / LOGICAL_W
    sy = dst_h / LOGICAL_H
    scale = min(sx, sy)
    w = int(LOGICAL_W * scale)
    h = int(LOGICAL_H * scale)
    x = (dst_w - w) // 2
    y = (dst_h - h) // 2
    return pygame.Rect(x, y, w, h), scale


# ==========================
# Data models
# ==========================
@dataclass
class CarModel:
    nome: str
    sprite: str  # filename or relative
    velocita_max: int
    ripresa: int
    controllo: int
    sterzo: int
    robustezza: int

    def sprite_path(self) -> str:
        # allow either "foo.png" in media dir or full path
        if os.path.isabs(self.sprite):
            return self.sprite
        return os.path.join(MEDIA_DIR, self.sprite)

@dataclass
class TrackInfo:
    name: str
    laps: int
    start_grid: List[Dict]
    finish_line: Dict
    waypoints: List[Dict]

def load_cars() -> List[CarModel]:
    if not os.path.exists(CARS_JSON):
        # fallback minimal list
        return [
            CarModel("Fallback Car", "fallback_car.png", 3, 3, 3, 3, 3)
        ]
    with open(CARS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    cars = []
    for c in data.get("cars", data.get("lista", data.get("auto", []))):
        cars.append(CarModel(
            nome=c["nome"],
            sprite=c.get("sprite", "fallback_car.png"),
            velocita_max=int(c["velocita_max"]),
            ripresa=int(c["ripresa"]),
            controllo=int(c["controllo"]),
            sterzo=int(c["sterzo"]),
            robustezza=int(c["robustezza"]),
        ))
    return cars

def load_tracks_meta() -> Dict[str, TrackInfo]:
    if not os.path.exists(TRACKS_JSON):
        # fallback one-track
        return {
            "track01": TrackInfo(
                name="track01",
                laps=3,
                start_grid=[{"x": 960, "y": 900, "angle": 270} for _ in range(8)],
                finish_line={"x": 900, "y": 880, "width": 200, "height": 20},
                waypoints=[{"x": 960, "y": 900}, {"x": 1400, "y": 700}, {"x": 960, "y": 400}, {"x": 500, "y": 700}],
            )
        }

    with open(TRACKS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    out: Dict[str, TrackInfo] = {}
    for t in data.get("tracks", []):
        ti = TrackInfo(
            name=t["name"],
            laps=int(t["laps"]),
            start_grid=t["start_grid"],
            finish_line=t["finish_line"],
            waypoints=t["waypoints"],
        )
        out[ti.name] = ti
    return out


def simulate_group_race(group_models: List[CarModel], rng: random.Random) -> List[Dict]:
    """Simulate one non-visible race group and return ranked rows."""
    # weighting aligned with arcade feel: speed/accel/control matter more
    w_speed = 1.00
    w_accel = 0.90
    w_ctrl = 0.85
    w_steer = 0.70
    w_rob = 0.55

    scored = []
    for m in group_models:
        base = (
            w_speed * m.velocita_max
            + w_accel * m.ripresa
            + w_ctrl * m.controllo
            + w_steer * m.sterzo
            + w_rob * m.robustezza
        )
        noise = rng.gauss(0.0, 0.9)

        # Small incident probability; robustness mitigates penalty chance/severity.
        incident_penalty = 0.0
        incident_p = 0.08 + 0.05 * ((6 - m.robustezza) / 5.0)
        if rng.random() < incident_p:
            incident_penalty = rng.uniform(0.6, 2.0) * (1.15 - 0.10 * m.robustezza)

        score = base + noise - incident_penalty
        scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    rows = []
    for rank, (score, m) in enumerate(scored, start=1):
        rows.append({
            "rank": rank,
            "model": m,
            "score": score,
            "qualified": rank <= 4,
        })
    return rows


def simulate_hidden_groups_from_groups(hidden_groups: List[List[CarModel]], rng: random.Random) -> List[Dict]:
    out = []
    for gi, gmodels in enumerate(hidden_groups, start=1):
        out.append({
            "group_name": f"Gruppo {gi}",
            "rows": simulate_group_race(gmodels, rng),
        })
    return out


# ==========================
# Track runtime
# ==========================
class Track:
    def __init__(self, info: TrackInfo, render_path: str, surface_path: str):
        self.info = info
        self.render_img = load_image(render_path, fallback_size=(LOGICAL_W, LOGICAL_H), col=(50, 50, 50))
        self.render_img = pygame.transform.smoothscale(self.render_img, (LOGICAL_W, LOGICAL_H))

        self.surface_img = load_image(surface_path, fallback_size=(LOGICAL_W, LOGICAL_H), col=(0, 0, 0))
        # surface map must be non-alpha and same size
        self.surface_img = pygame.transform.scale(self.surface_img.convert(), (LOGICAL_W, LOGICAL_H))

        self.finish_rect = pygame.Rect(
            int(self.info.finish_line["x"]),
            int(self.info.finish_line["y"]),
            int(self.info.finish_line["width"]),
            int(self.info.finish_line["height"]),
        )
        self.waypoints = [pygame.Vector2(w["x"], w["y"]) for w in self.info.waypoints]

    def surface_color_at(self, pos: pygame.Vector2) -> Tuple[int, int, int]:
        x = int(clamp(pos.x, 0, LOGICAL_W - 1))
        y = int(clamp(pos.y, 0, LOGICAL_H - 1))
        return self.surface_img.get_at((x, y))[:3]


# ==========================
# Car entity (player + AI)
# ==========================
class Car:
    def __init__(self, model: CarModel, is_player: bool, rng: random.Random):
        self.model = model
        self.is_player = is_player
        self.rng = rng

        self.sprite_base = load_image(model.sprite_path(), fallback_size=(64, 32), col=(200, 200, 200))
        self.sprite_base = pygame.transform.smoothscale(self.sprite_base, (64, 32))

        self.pos = pygame.Vector2(960, 540)
        self.vel = pygame.Vector2(0, 0)
        self.angle = 0.0

        # map stats to arcade physics
        self.max_speed = map_1_5(model.velocita_max, 260, 420)  # px/s
        self.accel = map_1_5(model.ripresa, 400, 800)           # px/s^2
        self.control = map_1_5(model.controllo, 0.70, 0.92)     # higher = more stable
        self.steering_deg = map_1_5(model.sterzo, 90, 180)      # deg/s
        # robustness used later for HP; for now affects how much wall slows you (simple)
        self.robust = map_1_5(model.robustezza, 0.7, 1.0)

        # status effects timers
        self.boost_timer = 0.0
        self.oil_timer = 0.0
        self.repair_timer = 0.0

        # lap tracking (simple)
        self.laps_done = 0
        self._was_on_finish = None
        self.race_done = False
        self.finish_order = 0
        self.just_hit_wall = False
        self.wall_hit_speed = 0.0

        # AI parameters
        self.ai_wp_index = 0
        self.ai_lane = 0
        self.ai_lane_pref = 0
        self.ai_lane_cooldown = 0.0
        self.ai_unstuck_reverse_timer = 0.0
        self.ai_overtake_boost_timer = 0.0
        self.ai_base_aggr = self.rng.uniform(0.88, 1.02)
        self.ai_error_target = pygame.Vector2(0, 0)
        self.ai_error_next = pygame.Vector2(0, 0)
        self.ai_error_t = 1.0
        self.ai_error_period = self.rng.uniform(0.25, 0.5)

        # give each AI a lane preference
        if not is_player:
            self.ai_lane_pref = self.rng.choices([-1, 0, 1], weights=[2, 6, 2])[0]
            self.ai_lane = self.ai_lane_pref
            self.ai_wp_index = self.rng.randrange(0, 3)  # small spread at start

    def align_ai_waypoint_to_track(self, track: Track):
        """Pick a coherent initial waypoint using spawn position and facing direction."""
        if self.is_player or not track.waypoints:
            return
        heading = pygame.Vector2(math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle)))
        best_i = 0
        best_score = float("inf")
        for i, wp in enumerate(track.waypoints):
            to_wp = wp - self.pos
            dist = to_wp.length()
            if dist < 1e-6:
                self.ai_wp_index = i
                return
            dot = safe_normalize(to_wp).dot(heading)
            # Penalize waypoints behind the spawn heading.
            score = dist * (1.0 if dot >= 0.0 else 1.35)
            if score < best_score:
                best_score = score
                best_i = i
        self.ai_wp_index = best_i

    def _maybe_advance_ai_waypoint(self, track: Track):
        """Advance target waypoint when reached or when geometrically passed."""
        if self.is_player or not track.waypoints:
            return
        n = len(track.waypoints)
        # Cap loop to avoid infinite cycling in degenerate cases.
        for _ in range(n):
            wp = track.waypoints[self.ai_wp_index]
            prev_wp = track.waypoints[(self.ai_wp_index - 1) % n]

            # Standard reach-radius rule.
            if (self.pos - wp).length() < AI_WP_REACH_DIST:
                self.ai_wp_index = (self.ai_wp_index + 1) % n
                continue

            # Segment-pass rule: if car has projected beyond current waypoint
            # along segment prev_wp -> wp, advance even if it missed the radius.
            seg = wp - prev_wp
            seg_len2 = seg.length_squared()
            if seg_len2 > 1e-6:
                rel = self.pos - prev_wp
                t = rel.dot(seg) / seg_len2
                closest = prev_wp + seg * t
                lateral = (self.pos - closest).length()
                if t > 1.02 and lateral < (LANE_HALF_WIDTH * 3.0):
                    self.ai_wp_index = (self.ai_wp_index + 1) % n
                    continue
            break

    def rect(self) -> pygame.Rect:
        # axis-aligned collider (per spec)
        return pygame.Rect(int(self.pos.x - 22), int(self.pos.y - 14), 44, 28)

    def _find_escape_from_wall(self, track: Track, max_radius: int = 40) -> Optional[pygame.Vector2]:
        # probe a small neighborhood to find first non-wall pixel
        dirs = (
            pygame.Vector2(1, 0), pygame.Vector2(-1, 0),
            pygame.Vector2(0, 1), pygame.Vector2(0, -1),
            pygame.Vector2(1, 1), pygame.Vector2(1, -1),
            pygame.Vector2(-1, 1), pygame.Vector2(-1, -1),
        )
        for r in range(2, max_radius + 1, 2):
            for d in dirs:
                p = self.pos + d * r
                if track.surface_color_at(p) != CLR_WALL:
                    return d * r
        return None

    def _apply_surface_effects(self, track: Track, dt: float):
        col = track.surface_color_at(self.pos)
        self.just_hit_wall = False

        # timers decay
        self.boost_timer = max(0.0, self.boost_timer - dt)
        self.oil_timer = max(0.0, self.oil_timer - dt)
        self.repair_timer = max(0.0, self.repair_timer - dt)

        # trigger zones by color
        if col == CLR_BOOST:
            self.boost_timer = 2.5
        elif col == CLR_OIL:
            self.oil_timer = 2.0
        elif col == CLR_REPAIR:
            self.repair_timer = 0.5  # placeholder (we'll heal HP later)

        # wall: simple stop (later we add damage)
        if col == CLR_WALL:
            self.just_hit_wall = True
            self.wall_hit_speed = vec_length(self.vel)
            # push back opposite to movement; if almost stopped use facing direction
            push_dir = safe_normalize(self.vel)
            if vec_length(self.vel) < 1.0:
                ang = math.radians(self.angle)
                push_dir = pygame.Vector2(math.cos(ang), math.sin(ang))
            self.pos -= push_dir * 8.0
            self.vel *= 0.10

            # anti-stuck fallback: relocate a few pixels to nearest non-wall area
            if track.surface_color_at(self.pos) == CLR_WALL:
                escape = self._find_escape_from_wall(track)
                if escape is not None:
                    self.pos += escape

    def _compute_speed_caps(self, track: Track) -> Tuple[float, float]:
        # base caps
        max_speed = self.max_speed
        accel = self.accel

        # boost
        if self.boost_timer > 0:
            max_speed *= 1.30

        # oil: reduce control & steering (handled elsewhere); also reduce max speed a bit
        if self.oil_timer > 0:
            max_speed *= 0.90

        # grass slowdown
        col = track.surface_color_at(self.pos)
        if col == CLR_GRASS:
            max_speed *= 0.75
            accel *= 0.80

        return max_speed, accel

    def update_player(self, track: Track, keys, dt: float):
        self._apply_surface_effects(track, dt)

        # direction vector (absolute)
        dx = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
        dy = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
        dir_des = pygame.Vector2(dx, dy)
        dir_des = safe_normalize(dir_des)

        accelerating = keys[pygame.K_UP]
        reversing = keys[pygame.K_DOWN]
        braking = keys[pygame.K_SPACE]
        ang_facing = math.radians(self.angle)
        facing_dir = pygame.Vector2(math.cos(ang_facing), math.sin(ang_facing))

        max_speed, accel = self._compute_speed_caps(track)

        # steering: rotate velocity direction towards desired direction (simple)
        if vec_length(dir_des) > 0.0 and vec_length(self.vel) > 2.0:
            vdir = safe_normalize(self.vel)
            # angle between
            ang_v = math.atan2(vdir.y, vdir.x)
            ang_d = math.atan2(dir_des.y, dir_des.x)
            # shortest angle diff
            diff = (ang_d - ang_v + math.pi) % (2 * math.pi) - math.pi
            max_turn = math.radians(self.steering_deg) * dt
            diff = clamp(diff, -max_turn, max_turn)
            new_ang = ang_v + diff
            # preserve speed magnitude, apply control to reduce lateral drift (arcade)
            speed = vec_length(self.vel)
            new_dir = pygame.Vector2(math.cos(new_ang), math.sin(new_ang))
            self.vel = new_dir * speed

        # accelerate in desired direction
        if accelerating and vec_length(dir_des) > 0.0:
            self.vel += dir_des * accel * dt
        elif accelerating and vec_length(dir_des) == 0.0:
            # if no direction pressed, accelerate along current facing direction
            self.vel += facing_dir * accel * dt

        # reverse (retromarcia): negative acceleration along facing/drive direction
        if reversing:
            if vec_length(dir_des) > 0.0:
                reverse_dir = dir_des
            else:
                reverse_dir = facing_dir
            self.vel -= reverse_dir * accel * 0.70 * dt

        # brake
        if braking:
            self.vel *= (1.0 - clamp(3.0 * dt, 0.0, 0.9))

        # control: dampen drift / stabilise
        self.vel *= (1.0 - (1.0 - self.control) * 1.8 * dt)

        # clamp speed
        spd = vec_length(self.vel)
        if spd > max_speed:
            self.vel = safe_normalize(self.vel) * max_speed

        # move
        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, 0, LOGICAL_W)
        self.pos.y = clamp(self.pos.y, 0, LOGICAL_H)

        # keep facing stable while moving backwards; avoid 180deg sprite flip
        if vec_length(self.vel) > 1.0:
            facing_now = pygame.Vector2(math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle)))
            moving_forward_vs_facing = self.vel.dot(facing_now) >= 0.0
            if moving_forward_vs_facing:
                self.angle = angle_from_velocity(self.vel)

    def update_ai(self, track: Track, all_cars: List["Car"], dt: float):
        self._apply_surface_effects(track, dt)

        # update lane cooldown/timers
        self.ai_lane_cooldown = max(0.0, self.ai_lane_cooldown - dt)
        self.ai_unstuck_reverse_timer = max(0.0, self.ai_unstuck_reverse_timer - dt)
        self.ai_overtake_boost_timer = max(0.0, self.ai_overtake_boost_timer - dt)

        # wall unstuck: short straight reverse, then resume waypoint logic
        if self.just_hit_wall and self.ai_unstuck_reverse_timer <= 0.0:
            self.ai_unstuck_reverse_timer = self.rng.uniform(0.40, 0.70)
            self.ai_lane_cooldown = max(self.ai_lane_cooldown, 0.6)

        if self.ai_unstuck_reverse_timer > 0.0:
            max_speed, accel = self._compute_speed_caps(track)
            facing = pygame.Vector2(math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle)))
            self.vel -= facing * accel * 0.90 * dt

            # cap reverse speed to keep maneuver controlled
            rev_cap = max_speed * 0.45
            spd = vec_length(self.vel)
            if spd > rev_cap:
                self.vel = safe_normalize(self.vel) * rev_cap

            # strong damping to avoid lateral zig-zag while reversing
            self.vel *= (1.0 - clamp(2.0 * dt, 0.0, 0.7))
            self.pos += self.vel * dt
            self.pos.x = clamp(self.pos.x, 0, LOGICAL_W)
            self.pos.y = clamp(self.pos.y, 0, LOGICAL_H)
            return

        self._maybe_advance_ai_waypoint(track)

        # smooth noise based on control (spec)
        # amplitude grows with (6 - control_int)
        control_int = int(self.model.controllo)
        amp_map = {5: 2, 4: 4, 3: 7, 2: 12, 1: 18}
        amp = amp_map.get(control_int, 7)

        self.ai_error_t += dt / self.ai_error_period
        if self.ai_error_t >= 1.0:
            self.ai_error_t = 0.0
            self.ai_error_target = self.ai_error_next
            self.ai_error_next = pygame.Vector2(
                self.rng.uniform(-amp, amp),
                self.rng.uniform(-amp, amp)
            )
            self.ai_error_period = self.rng.uniform(0.25, 0.5)

        error = self.ai_error_target.lerp(self.ai_error_next, self.ai_error_t)

        # waypoint targeting
        wp = track.waypoints[self.ai_wp_index]
        next_wp = track.waypoints[(self.ai_wp_index + 1) % len(track.waypoints)]
        seg = next_wp - wp
        seg_dir = safe_normalize(seg)
        normal = pygame.Vector2(-seg_dir.y, seg_dir.x)

        lane_offset_px = self.ai_lane * LANE_HALF_WIDTH
        target = wp + normal * lane_offset_px + error

        # curve vs straight estimation via angle between segments
        prev_wp = track.waypoints[(self.ai_wp_index - 1) % len(track.waypoints)]
        cur_wp = track.waypoints[self.ai_wp_index]
        nxt_wp = track.waypoints[(self.ai_wp_index + 1) % len(track.waypoints)]
        a = safe_normalize(cur_wp - prev_wp)
        b = safe_normalize(nxt_wp - cur_wp)
        dot = clamp(a.dot(b), -1.0, 1.0)
        turn_angle = math.degrees(math.acos(dot))  # 0..180

        # dynamic target speed (spec)
        base_aggr = self.ai_base_aggr
        if turn_angle < 12:
            delta = self.rng.uniform(0.00, 0.06)
        else:
            # stronger slowdown if low control
            low_control_factor = (6 - control_int) / 5.0
            delta = -self.rng.uniform(0.05, 0.18) * (1.0 + 0.6 * low_control_factor)

        overtake_boost = 0.0
        if self.ai_overtake_boost_timer > 0.0:
            overtake_boost = 0.06

        # surface caps
        max_speed, accel = self._compute_speed_caps(track)

        target_speed = max_speed * clamp(base_aggr + delta + overtake_boost, 0.75, 1.05)

        # simple traffic + overtake bias
        self._ai_traffic_and_overtake(track, all_cars, seg_dir, dt)

        # steering towards target
        dir_to_target = safe_normalize(target - self.pos)

        # rotate velocity direction toward desired direction with steering limit
        if vec_length(dir_to_target) > 0.0 and vec_length(self.vel) > 2.0:
            vdir = safe_normalize(self.vel)
            ang_v = math.atan2(vdir.y, vdir.x)
            ang_d = math.atan2(dir_to_target.y, dir_to_target.x)
            diff = (ang_d - ang_v + math.pi) % (2 * math.pi) - math.pi
            max_turn = math.radians(self.steering_deg) * dt

            # oil reduces steering effectiveness
            if self.oil_timer > 0.0:
                max_turn *= 0.65

            diff = clamp(diff, -max_turn, max_turn)
            new_ang = ang_v + diff
            speed = vec_length(self.vel)
            new_dir = pygame.Vector2(math.cos(new_ang), math.sin(new_ang))
            self.vel = new_dir * speed

        # accelerate along dir_to_target to reach target_speed
        spd = vec_length(self.vel)
        if spd < target_speed:
            self.vel += dir_to_target * accel * dt
        else:
            # mild damping if too fast
            self.vel *= (1.0 - clamp(1.2 * dt, 0.0, 0.5))

        # control stabilization
        self.vel *= (1.0 - (1.0 - self.control) * 1.6 * dt)

        # clamp
        spd = vec_length(self.vel)
        if spd > target_speed:
            self.vel = safe_normalize(self.vel) * target_speed

        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, 0, LOGICAL_W)
        self.pos.y = clamp(self.pos.y, 0, LOGICAL_H)
        self.angle = angle_from_velocity(self.vel)

    def _ai_traffic_and_overtake(self, track: Track, all_cars: List["Car"], seg_dir: pygame.Vector2, dt: float):
        # find nearest "ahead" car in a small cone
        my_pos = self.pos
        nearest = None
        nearest_dist = 1e9

        for c in all_cars:
            if c is self:
                continue
            if getattr(c, "race_done", False):
                continue
            offset = c.pos - my_pos
            dist = offset.length()
            if dist < 1e-6 or dist > AI_OVERTAKE_DIST:
                continue
            # ahead test: dot with segment direction
            if safe_normalize(offset).dot(seg_dir) > 0.35:
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = c

        if nearest is None:
            return

        # if close and cooldown ready, attempt lane change
        if self.ai_lane_cooldown <= 0.0 and nearest_dist < AI_OVERTAKE_DIST:
            # choose lane with less occupancy
            candidates = []
            if self.ai_lane == 0:
                candidates = [-1, 1]
            elif self.ai_lane == -1:
                candidates = [0]
            elif self.ai_lane == 1:
                candidates = [0]

            best_lane = self.ai_lane
            best_score = 1e9
            for ln in candidates:
                score = 0.0
                # penalize lanes with cars near target lane
                for c in all_cars:
                    if c is self:
                        continue
                    if abs(c.pos.y - self.pos.y) < 80 and abs(c.pos.x - self.pos.x) < 200:
                        # rough "near"
                        if ln != self.ai_lane:
                            score += 1.0
                # prefer lane preference slightly
                score += 0.3 * abs(ln - self.ai_lane_pref)
                if score < best_score:
                    best_score = score
                    best_lane = ln

            if best_lane != self.ai_lane:
                self.ai_lane = best_lane
                self.ai_lane_cooldown = self.rng.uniform(AI_LANE_COOLDOWN_MIN, AI_LANE_COOLDOWN_MAX)
                self.ai_overtake_boost_timer = self.rng.uniform(0.6, 1.2)

    def check_finish(self, track: Track):
        on_finish = track.finish_rect.collidepoint(int(self.pos.x), int(self.pos.y))
        # prime state on first frame to avoid counting the spawn position as a completed lap
        if self._was_on_finish is None:
            self._was_on_finish = on_finish
            return
        if on_finish and not self._was_on_finish:
            self.laps_done += 1
        self._was_on_finish = on_finish

    def draw(self, surf: pygame.Surface):
        spr = pygame.transform.rotozoom(self.sprite_base, -self.angle, 1.0)
        r = spr.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surf.blit(spr, r)


# ==========================
# Game states
# ==========================
class State:
    def handle_event(self, e: pygame.event.Event): ...
    def update(self, dt: float): ...
    def draw(self, surf: pygame.Surface): ...

class MenuState(State):
    def __init__(self, game: "Game"):
        self.game = game
        self.bkg = load_image(MENU_BKG, fallback_size=(LOGICAL_W, LOGICAL_H), col=(20, 20, 60))
        self.bkg = pygame.transform.smoothscale(self.bkg, (LOGICAL_W, LOGICAL_H))
        self.font_big = load_font(64)
        self.font = load_font(54)
        self.items = ["Avvia partita", "Istruzioni", "Esci"]
        self.sel = 0

    def _activate_selected(self):
        if self.sel == 0:
            self.game.push_state(CarSelectState(self.game))
        elif self.sel == 1:
            self.game.push_state(InstructionsState(self.game))
        else:
            self.game.running = False

    def _menu_item_rect(self, index: int) -> pygame.Rect:
        x = 90
        y0 = LOGICAL_H - 260
        line_h = 78
        txt = self.items[index]
        w, h = self.font.size(txt)
        return pygame.Rect(x - 8, y0 + index * line_h - 4, w + 16, h + 10)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.game.running = False
            if e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.items)
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.items)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_selected()
        elif e.type == pygame.MOUSEMOTION:
            mx, my = e.pos
            for i in range(len(self.items)):
                if self._menu_item_rect(i).collidepoint(mx, my):
                    self.sel = i
                    break
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            for i in range(len(self.items)):
                if self._menu_item_rect(i).collidepoint(mx, my):
                    self.sel = i
                    self._activate_selected()
                    break

    def update(self, dt): ...

    def draw(self, surf):
        surf.blit(self.bkg, (0, 0))
        draw_text(surf, "CARS", self.font_big, 70, 70)

        x = 90
        y = LOGICAL_H - 260  # posizione dentro riquadro basso-sinistra
        line_h = 78

        for i, it in enumerate(self.items):
            col = (255, 220, 80) if i == self.sel else (255, 255, 255)
            draw_text(surf, it, self.font, x, y, col)
            y += line_h       


class InstructionsState(State):
    def __init__(self, game: "Game"):
        self.game = game
        self.bkg = load_image(INSTR_BKG, fallback_size=(LOGICAL_W, LOGICAL_H), col=(60, 20, 20))
        self.bkg = pygame.transform.smoothscale(self.bkg, (LOGICAL_W, LOGICAL_H))
        self.font = load_font(34)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
            self.game.pop_state()

    def update(self, dt): ...

    def draw(self, surf):
        surf.blit(self.bkg, (0, 0))
        draw_text(surf, "Premi un tasto per tornare al menu", self.font, 60, 980, (255, 255, 255))


class CarSelectState(State):
    def __init__(self, game: "Game"):
        self.game = game
        # spec: 32 auto in ordine alfabetico
        self.cars = sorted(game.cars, key=lambda c: c.nome.lower())[:32]
        self.sel = 0
        self.font_big = load_font(46)
        self.font = load_font(18)
        self.font_small = load_font(22)
        self.preview_cache = {}
        self.cols = 8
        self.rows = 4

        # layout griglia 4x8 su 1920x1080
        self.grid_x = 24
        self.grid_y = 110
        self.card_w = 230
        self.card_h = 226
        self.gap_x = 8
        self.gap_y = 8

        self.bar_defs = [
            ("V", "velocita_max", (255, 110, 110)),
            ("R", "ripresa", (255, 190, 90)),
            ("C", "controllo", (100, 220, 255)),
            ("S", "sterzo", (130, 230, 130)),
            ("R", "robustezza", (200, 160, 255)),
        ]

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE,):
                self.game.pop_state()
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self.sel = (self.sel - 1) % len(self.cars)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self.sel = (self.sel + 1) % len(self.cars)
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - self.cols) % len(self.cars)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + self.cols) % len(self.cars)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.game.selected_car = self.cars[self.sel]
                self.game.start_tournament(self.game.selected_car)
                visible_idx, visible_group = self.game.get_visible_group()
                if visible_group is not None:
                    self.game.push_state(
                        PreRaceState(
                            self.game,
                            track_name=self.game.current_track_name(),
                            race_models=visible_group,
                            phase_label=self.game.current_phase_label(),
                            visible_group_index=visible_idx,
                        )
                    )

    def update(self, dt): ...

    def draw(self, surf):
        surf.fill((10, 10, 14))
        draw_text(surf, "Seleziona Auto - ENTER per confermare", self.font_big, 28, 24)
        draw_text(
            surf,
            "Legenda iniziali: V Velocita max, R Ripresa, C Controllo, S Sterzo, R Robustezza",
            self.font_small,
            28,
            72,
            (185, 185, 185),
        )

        for i, c in enumerate(self.cars):
            col = i % self.cols
            row = i // self.cols
            if row >= self.rows:
                break

            x = self.grid_x + col * (self.card_w + self.gap_x)
            y = self.grid_y + row * (self.card_h + self.gap_y)
            card = pygame.Rect(x, y, self.card_w, self.card_h)

            selected = (i == self.sel)
            pygame.draw.rect(surf, (26, 26, 34), card, border_radius=10)
            border_col = (255, 220, 80) if selected else (70, 70, 86)
            pygame.draw.rect(surf, border_col, card, width=3 if selected else 1, border_radius=10)

            preview = self.preview_cache.get(c.nome)
            if preview is None:
                # spec: sprite mostrato a dimensione originale
                preview = load_image(c.sprite_path(), fallback_size=(96, 48), col=(120, 120, 120))
                self.preview_cache[c.nome] = preview

            pr = preview.get_rect(center=(x + self.card_w // 2, y + 44))
            surf.blit(preview, pr)

            draw_text(surf, c.nome, self.font, x + 8, y + 80, (235, 235, 235))

            bar_x = x + 24
            bar_y = y + 112
            bar_h = 14
            bar_max_w = self.card_w - 40
            for short_label, attr_name, bar_col in self.bar_defs:
                val = int(getattr(c, attr_name))
                fill_w = int(bar_max_w * (clamp(val, 1, 5) / 5.0))
                draw_text(surf, short_label, self.font, x + 8, bar_y - 1, (220, 220, 220))
                pygame.draw.rect(surf, (46, 46, 56), (bar_x, bar_y, bar_max_w, bar_h), border_radius=4)
                pygame.draw.rect(surf, bar_col, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
                bar_y += 19

        draw_text(
            surf,
            "Frecce/WASD: selezione    ENTER: conferma    ESC: menu",
            self.font_small,
            28,
            1044,
            (180, 180, 180),
        )


class RaceState(State):
    def __init__(
        self,
        game: "Game",
        track_name: str,
        race_models: Optional[List[CarModel]] = None,
        start_grid: Optional[List[Dict]] = None,
        phase_label: str = "Gara",
        visible_group_index: int = 0,
    ):
        self.game = game
        self.phase_label = phase_label
        self.visible_group_index = visible_group_index
        self.font = load_font(28)
        self.font_big = load_font(44)
        self.rng = random.Random(12345)

        # pick track info + load images
        ti = self.game.tracks.get(track_name)
        if ti is None:
            # fallback to first
            ti = next(iter(self.game.tracks.values()))
        render_path, surface_path = TRACK_ASSETS.get(
            ti.name,
            (TRACK1_RENDER, TRACK1_SURFACE),
        )
        self.track = Track(ti, render_path, surface_path)

        # spawn cars (player + 7 AI)
        selected = game.selected_car or game.cars[0]
        self.cars: List[Car] = []

        if race_models and len(race_models) > 0:
            selected = race_models[0]

        self.player = Car(selected, is_player=True, rng=self.rng)
        self.cars.append(self.player)

        if race_models and len(race_models) > 1:
            for m in race_models[1:8]:
                self.cars.append(Car(m, is_player=False, rng=self.rng))
        else:
            # choose 7 random AI models distinct-ish
            pool = [c for c in game.cars if c.nome != selected.nome]
            self.rng.shuffle(pool)
            for i in range(7):
                m = pool[i % len(pool)]
                self.cars.append(Car(m, is_player=False, rng=self.rng))

        # assign start positions (random order per spec)
        if start_grid and len(start_grid) >= len(self.cars):
            grid = list(start_grid)
        else:
            grid = list(self.track.info.start_grid)
            self.rng.shuffle(grid)
        for car, g in zip(self.cars, grid):
            car.pos = pygame.Vector2(float(g["x"]), float(g["y"]))
            car.angle = float(g.get("angle", 0))
            # give small initial velocity along angle
            ang = math.radians(car.angle)
            car.vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * 5.0
            if not car.is_player:
                # requested: all cars start aiming at the first waypoint
                car.ai_wp_index = 0

        self.laps_target = int(self.track.info.laps)
        self.countdown = 3.0
        self.race_started = False
        self.finished = False
        self.results_pushed = False
        self.finish_counter = 0
        self.countdown_last_n = 4
        self.sfx_enabled = self.game.audio_enabled
        self.engine_channels: List[Optional[pygame.mixer.Channel]] = []
        self.engine_sounds: List[Optional[pygame.mixer.Sound]] = []
        self.crash_cooldown = 0.0

        if self.sfx_enabled:
            self._init_race_sfx()

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                # for now: exit race immediately (we'll add confirm dialog later)
                self._stop_engine_sfx()
                self.game.pop_state()

    def update(self, dt: float):
        keys = pygame.key.get_pressed()
        self.crash_cooldown = max(0.0, self.crash_cooldown - dt)

        # countdown
        if not self.race_started:
            self.countdown -= dt
            self._update_countdown_beep()
            if self.countdown <= 0:
                self.race_started = True

        # update cars
        if self.race_started and not self.finished:
            active_cars = [c for c in self.cars if not c.race_done]

            if not self.player.race_done:
                self.player.update_player(self.track, keys, dt)
            for c in self.cars[1:]:
                if not c.race_done:
                    c.update_ai(self.track, active_cars, dt)

            # laps
            for c in self.cars:
                if c.race_done:
                    continue
                c.check_finish(self.track)
                # lap counter starts at 0; a car finishes when lap x+1 begins
                if c.laps_done > self.laps_target:
                    c.race_done = True
                    self.finish_counter += 1
                    c.finish_order = self.finish_counter

            if self.player.race_done:
                self.finished = True

            self._update_engine_sfx()
            self._play_crash_sfx_if_needed()

        # when race ends, freeze standings and show results screen
        if self.finished and not self.results_pushed:
            self._stop_engine_sfx()
            final_standings = self._build_standings_snapshot()
            hidden_group_models = self.game.get_hidden_groups(self.visible_group_index)
            hidden_results = simulate_hidden_groups_from_groups(hidden_group_models, random.Random())
            tournament_info = self.game.advance_tournament(final_standings, hidden_results)
            self.results_pushed = True
            self.game.push_state(
                RaceResultsState(
                    self.game,
                    final_standings,
                    hidden_results,
                    phase_label=self.phase_label,
                    tournament_info=tournament_info,
                )
            )

        # keep them inside screen; walls already handled per pixel
        for c in self.cars:
            if c.race_done:
                continue
            c.pos.x = clamp(c.pos.x, 0, LOGICAL_W)
            c.pos.y = clamp(c.pos.y, 0, LOGICAL_H)

    def draw(self, surf: pygame.Surface):
        surf.blit(self.track.render_img, (0, 0))

        # (debug) finish line
        pygame.draw.rect(surf, (255, 255, 255), self.track.finish_rect, 2)

        for c in self.cars:
            if not c.race_done:
                c.draw(surf)

        # UI
        draw_text(surf, f"Giro: {min(self.player.laps_done, self.laps_target)}/{self.laps_target}", self.font, 20, 20)
        draw_text(surf, self.phase_label, self.font, 20, 118, (220, 220, 220))
        draw_text(surf, f"Boost: {self.player.boost_timer:0.1f}", self.font, 20, 55, (180, 220, 255))
        draw_text(surf, f"Olio:  {self.player.oil_timer:0.1f}", self.font, 20, 85, (255, 255, 160))

        if not self.race_started:
            n = max(1, int(math.ceil(self.countdown)))
            draw_text(surf, str(n), self.font_big, 950, 500, (255, 220, 80))

        if self.finished:
            draw_text(surf, "FINISH! Premi ESC", self.font_big, 700, 480, (255, 220, 80))

    def _build_standings_snapshot(self) -> List[Dict]:
        wps = self.track.waypoints

        def progress_key(c: Car):
            nearest_idx = 0
            nearest_d2 = float("inf")
            for i, wp in enumerate(wps):
                d2 = (wp.x - c.pos.x) ** 2 + (wp.y - c.pos.y) ** 2
                if d2 < nearest_d2:
                    nearest_d2 = d2
                    nearest_idx = i
            # completed laps first, then waypoint progress, then closeness
            return (c.laps_done, nearest_idx, -nearest_d2)

        finished = [c for c in self.cars if c.race_done]
        finished.sort(key=lambda c: c.finish_order)

        unfinished = [c for c in self.cars if not c.race_done]
        unfinished.sort(key=progress_key, reverse=True)

        ordered = finished + unfinished
        out = []
        for rank, c in enumerate(ordered, start=1):
            out.append({
                "rank": rank,
                "model": c.model,
                "is_player": c.is_player,
                "laps_done": c.laps_done,
            })
        return out

    def _init_race_sfx(self):
        # Reserve channels for 8 engine loops (one per car in visible race)
        try:
            pygame.mixer.set_num_channels(max(24, pygame.mixer.get_num_channels()))
            self.engine_channels = [pygame.mixer.Channel(8 + i) for i in range(len(self.cars))]
            self.engine_sounds = []
            for i in range(len(self.cars)):
                s = self.game.engine_sounds[i % len(self.game.engine_sounds)] if self.game.engine_sounds else None
                self.engine_sounds.append(s)
        except Exception:
            self.sfx_enabled = False

    def _update_engine_sfx(self):
        if not self.sfx_enabled:
            return
        for i, c in enumerate(self.cars):
            ch = self.engine_channels[i] if i < len(self.engine_channels) else None
            snd = self.engine_sounds[i] if i < len(self.engine_sounds) else None
            if ch is None or snd is None:
                continue
            if c.race_done:
                ch.stop()
                continue
            speed = vec_length(c.vel)
            if speed > 18.0:
                if not ch.get_busy():
                    ch.play(snd, loops=-1)
                # light pitch substitute via volume dynamics
                vol = clamp(0.20 + (speed / max(c.max_speed, 1.0)) * 0.55, 0.18, 0.85)
                ch.set_volume(vol)
            elif speed < 6.0:
                ch.stop()

    def _play_crash_sfx_if_needed(self):
        if not self.sfx_enabled:
            return
        if self.crash_cooldown > 0.0:
            return
        for c in self.cars:
            if c.race_done:
                continue
            if c.just_hit_wall and c.wall_hit_speed > 35.0 and self.game.crash_sounds:
                try:
                    random.choice(self.game.crash_sounds).play()
                    self.crash_cooldown = 0.15
                except Exception:
                    pass
                break

    def _update_countdown_beep(self):
        if not self.sfx_enabled or self.game.beep_sound is None:
            return
        if self.countdown <= 0:
            return
        n = int(math.ceil(self.countdown))
        if n in (1, 2, 3) and n < self.countdown_last_n:
            try:
                self.game.beep_sound.play()
            except Exception:
                pass
        self.countdown_last_n = n

    def _stop_engine_sfx(self):
        if not self.sfx_enabled:
            return
        for ch in self.engine_channels:
            if ch is not None:
                ch.stop()


class RaceResultsState(State):
    def __init__(
        self,
        game: "Game",
        standings: List[Dict],
        hidden_results: Optional[List[Dict]] = None,
        phase_label: str = "Gara",
        tournament_info: Optional[Dict] = None,
    ):
        self.game = game
        self.standings = standings
        self.hidden_results = hidden_results or []
        self.phase_label = phase_label
        self.tournament_info = tournament_info or {}
        self.font_big = load_font(54)
        self.font = load_font(30)
        self.font_small = load_font(24)
        self.preview_cache = {}
        self.qual_slots = 4

        self.player_rank = None
        for row in self.standings:
            if row["is_player"]:
                self.player_rank = row["rank"]
                break
        self.player_qualified = (self.player_rank is not None and self.player_rank <= self.qual_slots)
        self.tournament_over = bool(self.tournament_info.get("tournament_over", True))
        self.next_phase_label = self.tournament_info.get("next_phase_label")
        self.is_final_results = self.phase_label.strip().lower() == "finale"

    def _continue_flow(self):
        if not self.player_qualified or self.tournament_over:
            self.game.go_to_menu()
            return

        visible_idx, visible_group = self.game.get_visible_group()
        if visible_group is None:
            self.game.go_to_menu()
            return
        self.game.go_to_menu(reset_tournament=False)
        self.game.push_state(
            PreRaceState(
                self.game,
                track_name=self.game.current_track_name(),
                race_models=visible_group,
                phase_label=self.next_phase_label or self.game.current_phase_label(),
                visible_group_index=visible_idx,
            )
        )

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
            self._continue_flow()

    def update(self, dt): ...

    def draw(self, surf):
        surf.fill((12, 12, 16))
        draw_text(surf, f"Risultati - {self.phase_label}", self.font_big, 70, 40, (255, 220, 80))

        y = 150
        row_h = 74
        for row in self.standings:
            rank = row["rank"]
            model = row["model"]
            is_player = row["is_player"]
            qualified = rank <= self.qual_slots

            box = pygame.Rect(70, y, 1780, row_h - 10)
            if self.is_final_results:
                base_col = (34, 34, 42)
            else:
                base_col = (24, 44, 24) if qualified else (44, 24, 24)
            pygame.draw.rect(surf, base_col, box, border_radius=10)
            if self.is_final_results:
                pygame.draw.rect(surf, (90, 90, 90), box, width=1, border_radius=10)
            else:
                border_col = (255, 220, 80) if is_player else (90, 90, 90)
                pygame.draw.rect(surf, border_col, box, width=3 if is_player else 1, border_radius=10)

            draw_text(surf, f"{rank:02d}", self.font, 92, y + 14, (255, 255, 255))
            draw_text(surf, model.nome, self.font, 180, y + 14, (245, 245, 245))
            if self.is_final_results:
                draw_text(surf, f"POS {rank}", self.font, 1320, y + 14, (230, 230, 230))
            else:
                draw_text(
                    surf,
                    "QUALIFICATO" if qualified else "SQUALIFICATO",
                    self.font,
                    1320,
                    y + 14,
                    (120, 255, 140) if qualified else (255, 120, 120),
                )

            preview = self.preview_cache.get(model.nome)
            if preview is None:
                preview = load_image(model.sprite_path(), fallback_size=(96, 48), col=(120, 120, 120))
                self.preview_cache[model.nome] = preview
            pr = preview.get_rect(midleft=(900, y + 32))
            surf.blit(preview, pr)

            y += row_h

        # summary of non-visible simulated groups
        if self.hidden_results:
            sum_y = 760
            draw_text(surf, "Altre gare (simulate):", self.font_small, 70, sum_y, (210, 210, 210))
            sum_y += 36
            for g in self.hidden_results:
                qualified_names = [r["model"].nome for r in g["rows"] if r["qualified"]]
                names = ", ".join(qualified_names)
                draw_text(surf, f"{g['group_name']} qualificati: {names}", self.font_small, 70, sum_y, (170, 220, 255))
                sum_y += 30
                if sum_y > 900:
                    break

        if self.player_qualified and not self.tournament_over:
            draw_text(surf, "Hai passato il turno!", self.font, 70, 980, (120, 255, 140))
            draw_text(surf, "Premi un tasto per andare alla prossima gara", self.font_small, 70, 1014, (200, 200, 200))
        elif self.player_qualified and self.tournament_over:
            draw_text(surf, "Torneo concluso: sei arrivato alla fine!", self.font, 70, 980, (255, 220, 80))
            draw_text(surf, "Premi un tasto per tornare al menu", self.font_small, 70, 1014, (220, 220, 220))
        else:
            draw_text(surf, "Sei squalificato: torneo terminato.", self.font, 70, 980, (255, 120, 120))
            draw_text(surf, "Premi un tasto per tornare al menu", self.font_small, 70, 1014, (220, 220, 220))


class PreRaceState(State):
    def __init__(
        self,
        game: "Game",
        track_name: str,
        race_models: Optional[List[CarModel]] = None,
        phase_label: str = "Pre-gara",
        visible_group_index: int = 0,
    ):
        self.game = game
        self.track_name = track_name
        self.phase_label = phase_label
        self.visible_group_index = visible_group_index
        self.font_big = load_font(52)
        self.font = load_font(30)
        self.font_small = load_font(24)
        self.rng = random.Random()
        self.preview_cache = {}

        if race_models:
            self.race_models = list(race_models)[:8]
        else:
            selected = game.selected_car or game.cars[0]
            pool = [c for c in game.cars if c.nome != selected.nome]
            self.rng.shuffle(pool)
            self.race_models = [selected] + pool[:7]

        ti = self.game.tracks.get(track_name)
        if ti is None:
            ti = next(iter(self.game.tracks.values()))
        self.start_grid = list(ti.start_grid)
        self.rng.shuffle(self.start_grid)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.game.pop_state()
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                # replace pre-race with the actual race state
                self.game.pop_state()
                self.game.push_state(
                    RaceState(
                        self.game,
                        track_name=self.track_name,
                        race_models=self.race_models,
                        start_grid=self.start_grid,
                        phase_label=self.phase_label,
                        visible_group_index=self.visible_group_index,
                    )
                )

    def update(self, dt): ...

    def draw(self, surf):
        surf.fill((12, 14, 20))
        draw_text(surf, f"{self.phase_label} - Pre-gara", self.font_big, 70, 50, (255, 220, 80))
        draw_text(surf, "Griglia di partenza (casuale)", self.font, 70, 124, (220, 220, 220))

        y = 200
        for i, car_m in enumerate(self.race_models, start=1):
            col = (255, 255, 255) if i != 1 else (255, 220, 80)
            draw_text(surf, f"{i:02d}. {car_m.nome}", self.font, 90, y + 6, col)

            preview = self.preview_cache.get(car_m.nome)
            if preview is None:
                preview = load_image(car_m.sprite_path(), fallback_size=(96, 48), col=(120, 120, 120))
                self.preview_cache[car_m.nome] = preview

            pr = preview.get_rect(midleft=(760, y + 26))
            surf.blit(preview, pr)
            y += 58

        draw_text(
            surf,
            "ENTER: avvia gara    ESC: torna a selezione auto",
            self.font_small,
            70,
            1000,
            (180, 180, 180),
        )


# ==========================
# Game container
# ==========================
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Top-Down Racing (Spec v3)")

        info = pygame.display.Info()
        self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.logical = pygame.Surface((LOGICAL_W, LOGICAL_H)).convert_alpha()

        self.running = True
        self.states: List[State] = []
        self.audio_enabled = False
        self.music_mode = "none"   # "none" | "menu" | "race"
        self.race_music_idx = 0
        self.engine_sounds: List[pygame.mixer.Sound] = []
        self.crash_sounds: List[pygame.mixer.Sound] = []
        self.beep_sound: Optional[pygame.mixer.Sound] = None

        self.cars: List[CarModel] = load_cars()
        self.tracks: Dict[str, TrackInfo] = load_tracks_meta()
        self.selected_car: Optional[CarModel] = None
        self.tournament_active = False
        self.tournament_phase = 0  # 0=Quarti, 1=Semifinale, 2=Finale
        self.tournament_groups: List[List[CarModel]] = []
        self.tournament_rng = random.Random()

        self._init_audio()
        self.push_state(MenuState(self))
        self._sync_music_with_state()

    def _init_audio(self):
        try:
            pygame.mixer.init()
            self.audio_enabled = True
            self._load_sfx_assets()
        except Exception:
            self.audio_enabled = False

    def _load_sfx_assets(self):
        self.engine_sounds = []
        self.crash_sounds = []
        self.beep_sound = None
        if not self.audio_enabled:
            return
        for p in ENGINE_SOUNDS:
            if os.path.exists(p):
                try:
                    s = pygame.mixer.Sound(p)
                    s.set_volume(0.35)
                    self.engine_sounds.append(s)
                except Exception:
                    pass
        for p in CRASH_SOUNDS:
            if os.path.exists(p):
                try:
                    s = pygame.mixer.Sound(p)
                    s.set_volume(0.45)
                    self.crash_sounds.append(s)
                except Exception:
                    pass
        if os.path.exists(BEEP_SOUND):
            try:
                self.beep_sound = pygame.mixer.Sound(BEEP_SOUND)
                self.beep_sound.set_volume(0.55)
            except Exception:
                self.beep_sound = None

    def _start_menu_music(self):
        if not self.audio_enabled or self.music_mode == "menu":
            return
        if not os.path.exists(MENU_MUSIC):
            return
        try:
            pygame.mixer.music.set_endevent(0)
            pygame.mixer.music.load(MENU_MUSIC)
            pygame.mixer.music.play(-1)  # loop infinito
            self.music_mode = "menu"
        except Exception:
            pass

    def _play_race_track(self, idx: int):
        if not self.audio_enabled:
            return
        tracks = [RACE_MUSIC_1, RACE_MUSIC_2]
        path = tracks[idx % 2]
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.set_endevent(MUSIC_END_EVENT)
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(0)  # una volta, poi alterna a fine traccia
            self.race_music_idx = idx % 2
        except Exception:
            pass

    def _start_race_music(self):
        if not self.audio_enabled or self.music_mode == "race":
            return
        self.music_mode = "race"
        self._play_race_track(0)

    def _sync_music_with_state(self):
        if not self.states:
            return
        st = self.current_state()
        if isinstance(st, RaceState):
            self._start_race_music()
        else:
            self._start_menu_music()

    def _on_music_end(self):
        # alternanza solo durante la gara
        if self.music_mode != "race":
            return
        self._play_race_track((self.race_music_idx + 1) % 2)

    def push_state(self, st: State):
        self.states.append(st)
        self._sync_music_with_state()

    def pop_state(self):
        if self.states:
            self.states.pop()
        if not self.states:
            self.running = False
        else:
            self._sync_music_with_state()

    def current_state(self) -> State:
        return self.states[-1]

    def current_phase_label(self) -> str:
        labels = ["Quarti", "Semifinale", "Finale"]
        idx = int(clamp(self.tournament_phase, 0, len(labels) - 1))
        return labels[idx]

    def current_track_name(self) -> str:
        # One circuit per phase: Quarti->track01, Semifinale->track02, Finale->track03.
        order = ["track01", "track02", "track03"]
        idx = int(clamp(self.tournament_phase, 0, len(order) - 1))
        wanted = order[idx]
        if wanted in self.tracks:
            return wanted
        if self.tracks:
            return next(iter(self.tracks.keys()))
        return "track01"

    def start_tournament(self, selected: CarModel):
        self.selected_car = selected
        self.tournament_active = True
        self.tournament_phase = 0

        pool = [c for c in self.cars if c.nome != selected.nome]
        self.tournament_rng.shuffle(pool)
        # 32 auto -> 4 gruppi da 8, il giocatore sempre nel gruppo visibile
        g0 = [selected] + pool[:7]
        g1 = pool[7:15]
        g2 = pool[15:23]
        g3 = pool[23:31]
        self.tournament_groups = [g0, g1, g2, g3]

    def get_visible_group(self) -> Tuple[int, Optional[List[CarModel]]]:
        if not self.tournament_groups or self.selected_car is None:
            return 0, None
        for i, g in enumerate(self.tournament_groups):
            for m in g:
                if m.nome == self.selected_car.nome:
                    return i, g
        return 0, None

    def get_hidden_groups(self, visible_group_index: int) -> List[List[CarModel]]:
        out = []
        for i, g in enumerate(self.tournament_groups):
            if i != visible_group_index:
                out.append(g)
        return out

    def _build_next_groups(self, qualifiers: List[CarModel], next_phase: int):
        self.tournament_rng.shuffle(qualifiers)
        player = self.selected_car
        if player is not None:
            for i, m in enumerate(qualifiers):
                if m.nome == player.nome:
                    qualifiers.insert(0, qualifiers.pop(i))
                    break

        if next_phase == 1:
            # 16 -> 2 gruppi da 8
            self.tournament_groups = [qualifiers[:8], qualifiers[8:16]]
        elif next_phase == 2:
            # 8 -> 1 gruppo finale
            self.tournament_groups = [qualifiers[:8]]
        else:
            self.tournament_groups = []

    def advance_tournament(self, visible_standings: List[Dict], hidden_results: List[Dict]) -> Dict:
        # collect qualifiers for current phase (top 4 each group)
        qualifiers: List[CarModel] = []
        qualifiers.extend([row["model"] for row in visible_standings[:4]])
        for hg in hidden_results:
            qualifiers.extend([r["model"] for r in hg["rows"] if r["qualified"]])

        player_qualified = False
        if self.selected_car is not None:
            player_qualified = any(m.nome == self.selected_car.nome for m in qualifiers)

        # If player eliminated, tournament ends for this run.
        if not player_qualified:
            self.tournament_active = False
            self.tournament_groups = []
            return {
                "player_qualified": False,
                "tournament_over": True,
                "next_phase_label": None,
            }

        # Final already played: tournament complete.
        if self.tournament_phase >= 2:
            self.tournament_active = False
            self.tournament_groups = []
            return {
                "player_qualified": True,
                "tournament_over": True,
                "next_phase_label": None,
            }

        next_phase = self.tournament_phase + 1
        self._build_next_groups(qualifiers, next_phase)
        self.tournament_phase = next_phase
        return {
            "player_qualified": True,
            "tournament_over": False,
            "next_phase_label": self.current_phase_label(),
        }

    def go_to_menu(self, reset_tournament: bool = True):
        self.states = [MenuState(self)]
        if reset_tournament:
            self.selected_car = None
            self.tournament_active = False
            self.tournament_groups = []
            self.tournament_phase = 0
        self._sync_music_with_state()

    def run(self):
        while self.running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
                elif e.type == MUSIC_END_EVENT:
                    self._on_music_end()
                else:
                    if self.states:
                        self.current_state().handle_event(e)

            if self.states:
                self.current_state().update(dt)
                self.current_state().draw(self.logical)

            # scale with letterbox
            dst_rect, _scale = compute_letterbox(self.screen.get_width(), self.screen.get_height())
            scaled = pygame.transform.smoothscale(self.logical, (dst_rect.w, dst_rect.h))
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, dst_rect)
            pygame.display.flip()

        pygame.quit()


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

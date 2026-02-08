# game_15_duck.py
# Jacoplay - Game 15 Duck
# Implementati: AVVIO + INTRO + MENU + ISTRUZIONI + MUSICA LOOP + avvio PARTITA (WORLD+HUD+OSTACOLI+MOVIMENTO)
# Prossimi step: armi/slot, pooling proiettili, pooling nemici, wave spawn, griglia collisioni, danni, game over.

import os
import sys
import json
import math
import random
import argparse
from dataclasses import dataclass
import pygame


# -----------------------------
# Path helpers
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "game_15_data")
MEDIA_DIR = os.path.join(BASE_DIR, "game_15_media")

PROPS_PATH = os.path.join(DATA_DIR, "game_15.properties")

FONT_PATH = os.path.join(MEDIA_DIR, "DirtyWar.otf")
BKG_MENU_PATH = os.path.join(MEDIA_DIR, "bkg_menu.png")
BKG_ISTR_PATH = os.path.join(MEDIA_DIR, "bkg_istruzioni.png")
BKG_GAME_PATH = os.path.join(MEDIA_DIR, "bkg_game.png")

MUSIC_PATH = os.path.join(MEDIA_DIR, "music_game.mp3")
QUACK_PATHS = [os.path.join(MEDIA_DIR, f"quack{i}.mp3") for i in range(1, 7)]

# HUD assets
HEART_PATH = os.path.join(MEDIA_DIR, "heart.png")
ARMA1_PATH = os.path.join(MEDIA_DIR, "arma_01.png")
ARMA2_PATH = os.path.join(MEDIA_DIR, "arma_02.png")
COLPO1_PATH = os.path.join(MEDIA_DIR, "colpo_01.png")
COLPO2_PATH = os.path.join(MEDIA_DIR, "colpo_02.png")
SLOT_PATH = os.path.join(MEDIA_DIR, "slot.png")
PAPERA_DX_01 = os.path.join(MEDIA_DIR, "papera_dx_01.png")
PAPERA_DX_02 = os.path.join(MEDIA_DIR, "papera_dx_02.png")
PAPERA_SX_01 = os.path.join(MEDIA_DIR, "papera_sx_01.png")
PAPERA_SX_02 = os.path.join(MEDIA_DIR, "papera_sx_02.png")

PAPERA_ELITE_DX_01 = os.path.join(MEDIA_DIR, "papera_elite_dx_01.png")
PAPERA_ELITE_DX_02 = os.path.join(MEDIA_DIR, "papera_elite_dx_02.png")
PAPERA_ELITE_SX_01 = os.path.join(MEDIA_DIR, "papera_elite_sx_01.png")
PAPERA_ELITE_SX_02 = os.path.join(MEDIA_DIR, "papera_elite_sx_02.png")

# Enemy constants
DUCK_POOL_NORMAL = 200
DUCK_POOL_ELITE = 20

DUCK_SPEED_BASE = 40.0         # wave 1
DUCK_SPEED_INC_PER_WAVE = 20.0 # +20 ogni wave

DUCK_ANIM_MS = 500             # alterna frame ogni 0.5s

DUCK_HITBOX_W, DUCK_HITBOX_H = 80, 80
DUCK_HP_NORMAL = 1
DUCK_HP_ELITE = 2

WAVE_INTERVAL_MS = 30_000      # ogni mezzo minuto, a partire da 0
WAVE_SPAWN_MARGIN = 40         # “appena fuori” dallo schermo

# dimensione riferimento sprite nemico (coerente col fallback)
DUCK_SPRITE_W = 96
DUCK_SPRITE_H = 96

# hitbox nemico = SOLO quarto inferiore ("piedi")
DUCK_FOOT_W = 60
DUCK_FOOT_H = DUCK_SPRITE_H // 4  # 24


# energia a prossimità nemici
ENERGY_DRAIN_RADIUS = 120.0        # px (tweak)
ENERGY_DRAIN_RATE_PER_DUCK = 3.0   # 3 punti al secondo per nemico vicino


# DEBUG: spawn test
DEBUG_SPAWN_ENEMY_KEY = None

# Player sprites
JAC_FRONT = os.path.join(MEDIA_DIR, "jac_front.png")
JAC_BACK = os.path.join(MEDIA_DIR, "jac_back.png")
JAC_DX = os.path.join(MEDIA_DIR, "jac_dx.png")
JAC_SX = os.path.join(MEDIA_DIR, "jac_sx.png")

# Obstacles
OST_1 = os.path.join(MEDIA_DIR, "ostacolo_01.png")
OST_2 = os.path.join(MEDIA_DIR, "ostacolo_02.png")
OST_3 = os.path.join(MEDIA_DIR, "ostacolo_03.png")
OBSTACLE_PATHS = [OST_1, OST_2, OST_3]


# -----------------------------
# Spec constants
# -----------------------------
W, H = 1920, 1080
FPS = 60

BIANCO = (255, 255, 255)
VERDE_SCURO = (13, 53, 18)
ARANCIO = (192, 79, 21)

WORLD_W, WORLD_H = 5760, 3240           # 3x3 schermate 1920x1080
TILE_W, TILE_H = 1920, 1080
PLAYER_SPEED = 240.0                     # px/s (virtuali)

BULLET_POOL_SIZE = 20
BULLET_SPEED = 1400.0          # px/s virtuali
BULLET_LIFE_MS = 1400          # durata massima prima di tornare nel pool
BULLET2_ENERGY_COST = 0        # costo energia per colpo_02 (1 = “1 energia”)

SLOT_W, SLOT_H = 220, 120
WEAPON_W, WEAPON_H = 75, 75
WEAPON_RESPAWN_MS = 60_000

AMMO_PICKUP_AMOUNT = 25
ENERGY_PICKUP_FOR_WEAPON2 = 10

# Spatial grid
CELL = 40
GRID_COLS = W // CELL   # 1920/40 = 48
GRID_ROWS = H // CELL   # 1080/40 = 27

# -----------------------------
# Utilities
# -----------------------------
def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def safe_image(path: str, fallback_size=None) -> pygame.Surface:
    if not os.path.exists(path):
        if fallback_size is None:
            fallback_size = (W, H)
        surf = pygame.Surface(fallback_size)
        surf.fill((255, 0, 255))
        return surf.convert()
    img = pygame.image.load(path)
    return img.convert_alpha() if img.get_alpha() else img.convert()

def safe_font(path: str, size: int) -> pygame.font.Font:
    if os.path.exists(path):
        return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size)

def render_centered(font: pygame.font.Font, text: str, color, center_xy):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center_xy)
    return surf, rect

def wrap_pos(x: float, y: float) -> tuple[float, float]:
    """Toro: coordinate sempre in [0..WORLD_W), [0..WORLD_H)."""
    x %= WORLD_W
    y %= WORLD_H
    return x, y

def shortest_delta(a: float, b: float, period: float) -> float:
    """Delta b-a sulla circonferenza, scegliendo il cammino più corto ([-period/2, +period/2])."""
    d = b - a
    half = period / 2.0
    if d > half:
        d -= period
    elif d < -half:
        d += period
    return d

# -----------------------------
# class SpatialGrid
# -----------------------------
class SpatialGrid:
    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        self.cells = [[] for _ in range(cols * rows)]

    def clear(self):
        for lst in self.cells:
            lst.clear()

    def _idx(self, cx: int, cy: int) -> int:
        return cy * self.cols + cx

    def _clamp_cell(self, cx: int, cy: int) -> tuple[int, int]:
        cx = max(0, min(self.cols - 1, cx))
        cy = max(0, min(self.rows - 1, cy))
        return cx, cy

    def add_rect(self, rect: pygame.Rect, obj):
        # inserisci obj in tutte le celle toccate dal rect
        x0 = rect.left // CELL
        y0 = rect.top // CELL
        x1 = rect.right // CELL
        y1 = rect.bottom // CELL
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                cx, cy = self._clamp_cell(cx, cy)
                self.cells[self._idx(cx, cy)].append(obj)

    def query_rect(self, rect: pygame.Rect):
        # ritorna oggetti presenti nelle celle toccate dal rect
        seen = set()
        out = []
        x0 = rect.left // CELL
        y0 = rect.top // CELL
        x1 = rect.right // CELL
        y1 = rect.bottom // CELL
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                cx, cy = self._clamp_cell(cx, cy)
                for obj in self.cells[self._idx(cx, cy)]:
                    oid = id(obj)
                    if oid not in seen:
                        seen.add(oid)
                        out.append(obj)
        return out



# -----------------------------
# UI elements
# -----------------------------
@dataclass
class MenuItem:
    label: str
    y: int
    action: str  # "NEW", "HELP", "QUIT"
    rect: pygame.Rect | None = None
    hovered: bool = False

    def compute_rect(self, font: pygame.font.Font, x_center: int):
        surf = font.render(self.label, True, VERDE_SCURO)
        self.rect = surf.get_rect(center=(x_center, self.y))

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, x_center: int):
        color = ARANCIO if self.hovered else VERDE_SCURO
        surf = font.render(self.label, True, color)
        rect = surf.get_rect(center=(x_center, self.y))
        self.rect = rect
        screen.blit(surf, rect)


# -----------------------------
# Game session (world + HUD + obstacles + player movement)
# -----------------------------
@dataclass
# -----------------------------
# class OBSTACLES
# -----------------------------
class Obstacle:
    img: pygame.Surface
    x: float
    y: float
    w: int
    h: int

    def rect_local(self, player_x: float, player_y: float) -> pygame.Rect:
        """Rettangolo dell'ostacolo in coordinate SCHERMO, vicino al player (wrap-aware)."""
        dx = shortest_delta(player_x, self.x, WORLD_W)
        dy = shortest_delta(player_y, self.y, WORLD_H)
        sx = (W // 2) + dx - self.w // 2
        sy = (H // 2) + dy - self.h // 2
        return pygame.Rect(int(sx), int(sy), self.w, self.h)

@dataclass

# -----------------------------
# class SLOT
# -----------------------------
class Slot:
    x: float
    y: float
    w: int = SLOT_W
    h: int = SLOT_H
    weapon_kind: int = 1           # 1=arma_01, 2=arma_02
    weapon_active: bool = True
    respawn_at_ms: int = 0         # quando respawnare

    def rect_local(self, player_x: float, player_y: float) -> pygame.Rect:
        dx = shortest_delta(player_x, self.x, WORLD_W)
        dy = shortest_delta(player_y, self.y, WORLD_H)
        sx = (W // 2) + dx - self.w // 2
        sy = (H // 2) + dy - self.h // 2
        return pygame.Rect(int(sx), int(sy), self.w, self.h)

    def weapon_rect_local(self, player_x: float, player_y: float) -> pygame.Rect:
        dx = shortest_delta(player_x, self.x, WORLD_W)
        dy = shortest_delta(player_y, self.y, WORLD_H)
        sx = (W // 2) + dx - WEAPON_W // 2
        sy = (H // 2) + dy - WEAPON_H // 2
        return pygame.Rect(int(sx), int(sy), WEAPON_W, WEAPON_H)


# -----------------------------
# class BULLET
# -----------------------------
class Bullet:
    def __init__(self):
        self.active = False
        self.kind = 1  # 1=colpo_01, 2=colpo_02
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.spawn_ms = 0
        self.hits_left = 1

    def spawn(self, kind: int, x: float, y: float, vx: float, vy: float, now_ms: int):
        self.active = True
        self.kind = kind
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.spawn_ms = now_ms
        self.hits_left = 3 if kind == 2 else 1

    def deactivate(self):
        self.active = False

    def update(self, dt: float, now_ms: int):
        if not self.active:
            return
        # lifespan
        if now_ms - self.spawn_ms >= BULLET_LIFE_MS:
            self.active = False
            return

        self.x = (self.x + self.vx * dt) % WORLD_W
        self.y = (self.y + self.vy * dt) % WORLD_H

# -----------------------------
# class BULLET POOL
# -----------------------------
class BulletPool:
    def __init__(self, capacity: int):
        self.bullets = [Bullet() for _ in range(capacity)]
        self._cursor = 0  # round-robin

    def spawn(self, kind: int, x: float, y: float, vx: float, vy: float, now_ms: int) -> bool:
        """Ritorna True se ha spawnato, False se il pool è pieno (tutti attivi)."""
        # prova a trovare un proiettile libero partendo dal cursore
        n = len(self.bullets)
        for i in range(n):
            idx = (self._cursor + i) % n
            b = self.bullets[idx]
            if not b.active:
                b.spawn(kind, x, y, vx, vy, now_ms)
                self._cursor = (idx + 1) % n
                return True
        return False  # pool pieno

    def update(self, dt: float, now_ms: int):
        for b in self.bullets:
            if b.active:
                b.update(dt, now_ms)

# -----------------------------
# class ENEMY
# -----------------------------
# class ENEMY (papera normale/élite)
class Enemy:
    def __init__(self):
        self.active = False
        self.elite = False
        self.x = 0.0
        self.y = 0.0
        self.hp = 1

    def spawn(self, elite: bool, x: float, y: float):
        self.active = True
        self.elite = elite
        self.x = x
        self.y = y
        self.hp = DUCK_HP_ELITE if elite else DUCK_HP_NORMAL

    def deactivate(self):
        self.active = False

    def hit(self, dmg: int = 1):
        self.hp -= dmg
        if self.hp <= 0:
            self.deactivate()

    # rect_local = piedi (quarto inferiore)
    def rect_local(self, player_x: float, player_y: float) -> pygame.Rect:
        dx = shortest_delta(player_x, self.x, WORLD_W)
        dy = shortest_delta(player_y, self.y, WORLD_H)

        # posizione del centro sprite su schermo
        sx_center = (W // 2) + dx
        sy_center = (H // 2) + dy

        # piedi: rettangolo nel quarto inferiore dello sprite
        foot_left = sx_center - DUCK_FOOT_W // 2
        foot_top = sy_center + (DUCK_SPRITE_H // 2 - DUCK_FOOT_H)  # parte bassa

        return pygame.Rect(int(foot_left), int(foot_top), int(DUCK_FOOT_W), int(DUCK_FOOT_H))


    # body rect per collisioni coi colpi (intero sprite)
    def body_rect_local(self, player_x: float, player_y: float) -> pygame.Rect:
        dx = shortest_delta(player_x, self.x, WORLD_W)
        dy = shortest_delta(player_y, self.y, WORLD_H)

        sx_center = (W // 2) + dx
        sy_center = (H // 2) + dy

        left = sx_center - DUCK_SPRITE_W // 2
        top = sy_center - DUCK_SPRITE_H // 2

        return pygame.Rect(int(left), int(top), int(DUCK_SPRITE_W), int(DUCK_SPRITE_H))


    def update(self, dt: float, player_x: float, player_y: float, speed: float):
        if not self.active:
            return

        dx = shortest_delta(self.x, player_x, WORLD_W)
        dy = shortest_delta(self.y, player_y, WORLD_H)

        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return

        vx = (dx / dist) * speed
        vy = (dy / dist) * speed

        self.x = (self.x + vx * dt) % WORLD_W
        self.y = (self.y + vy * dt) % WORLD_H


# -----------------------------
# class ENEMYPOOL
# -----------------------------
# >>> MODIFICA QUI: due pool distinti (normali + élite)
class DuckPool:
    def __init__(self, capacity: int):
        self.enemies = [Enemy() for _ in range(capacity)]
        self._cursor = 0

    def spawn(self, elite: bool, x: float, y: float) -> bool:
        n = len(self.enemies)
        for i in range(n):
            idx = (self._cursor + i) % n
            e = self.enemies[idx]
            if not e.active:
                e.spawn(elite, x, y)
                self._cursor = (idx + 1) % n
                return True
        return False

    def active_list(self):
        return [e for e in self.enemies if e.active]


# -----------------------------
# class GAME SESSION
# -----------------------------
class GameSession:
    def __init__(self):
        # player
        self.px = WORLD_W / 2
        self.py = WORLD_H / 2
        self.facing = "front"

        # stats
        self.wave = 1
        self.lives = 3
        self.energy = 100  # 0..100
        self.ammo1 = 0
        self.ammo2 = 0

        self._blink_ms_left = 0

        # assets
        self.bkg_tile = safe_image(BKG_GAME_PATH, fallback_size=(TILE_W, TILE_H))
        self.jac_front = safe_image(JAC_FRONT, fallback_size=(120, 120))
        self.jac_back = safe_image(JAC_BACK, fallback_size=(120, 120))
        self.jac_dx = safe_image(JAC_DX, fallback_size=(120, 120))
        self.jac_sx = safe_image(JAC_SX, fallback_size=(120, 120))

        self.heart = safe_image(HEART_PATH, fallback_size=(64, 64))
        self.arma1 = safe_image(ARMA1_PATH, fallback_size=(96, 96))
        self.arma2 = safe_image(ARMA2_PATH, fallback_size=(96, 96))
        self.slot_img = safe_image(SLOT_PATH, fallback_size=(SLOT_W, SLOT_H))
        self.colpo1 = safe_image(COLPO1_PATH, fallback_size=(24, 24))
        self.colpo2 = safe_image(COLPO2_PATH, fallback_size=(24, 24))
        self.bullet_pool = BulletPool(BULLET_POOL_SIZE)

        # duck sprites (normali + élite)
        self.papera_dx_01 = safe_image(PAPERA_DX_01, fallback_size=(96, 96))
        self.papera_dx_02 = safe_image(PAPERA_DX_02, fallback_size=(96, 96))
        self.papera_sx_01 = safe_image(PAPERA_SX_01, fallback_size=(96, 96))
        self.papera_sx_02 = safe_image(PAPERA_SX_02, fallback_size=(96, 96))

        self.papera_elite_dx_01 = safe_image(PAPERA_ELITE_DX_01, fallback_size=(96, 96))
        self.papera_elite_dx_02 = safe_image(PAPERA_ELITE_DX_02, fallback_size=(96, 96))
        self.papera_elite_sx_01 = safe_image(PAPERA_ELITE_SX_01, fallback_size=(96, 96))
        self.papera_elite_sx_02 = safe_image(PAPERA_ELITE_SX_02, fallback_size=(96, 96))

        # precompute player rect (screen)
        self.player_img = self.jac_front
        self.player_rect = self.player_img.get_rect(center=(W // 2, H // 2))

        # obstacles
        self.obstacles: list[Obstacle] = []
        self._spawn_obstacles()

        self.slots: list[Slot] = []
        self._spawn_slots()

        # pool papere
        self.ducks_normal = DuckPool(DUCK_POOL_NORMAL)
        self.ducks_elite = DuckPool(DUCK_POOL_ELITE)

        # wave timer
        self.wave = 1
        self._next_wave_ms = 0  # wave 1 a t=0

        # accumulatore danno contatto
        self._energy_drain_accum = 0.0

        # flag game over sessione
        self._game_over = False

        # spatial grid
        self.grid = SpatialGrid(GRID_COLS, GRID_ROWS)

        # quack sounds + cooldown per papera (1 suono/sec per papera)
        self.quacks: list[pygame.mixer.Sound] = []
        for p in QUACK_PATHS:
            if os.path.exists(p):
                try:
                    s = pygame.mixer.Sound(p)
                    self.quacks.append(s)
                except pygame.error:
                    pass

        # key = id(enemy), value = last_play_ms
        self._last_quack_ms: dict[int, int] = {}
        


    def _spawn_obstacles(self):
        # specifiche: 40 ostacoli 249x159, random su 5760x3240, no overlap col punto di start (centro)
        target = 40
        ow, oh = 249, 159

        imgs = [safe_image(p, fallback_size=(ow, oh)) for p in OBSTACLE_PATHS]
        start_x, start_y = WORLD_W / 2, WORLD_H / 2

        # area di esclusione attorno allo start (un po' conservativa)
        avoid_r = 280

        placed = 0
        tries = 0
        max_tries = 15000

        while placed < target and tries < max_tries:
            tries += 1
            x = random.uniform(0, WORLD_W)
            y = random.uniform(0, WORLD_H)

            # evita start
            dx0 = shortest_delta(start_x, x, WORLD_W)
            dy0 = shortest_delta(start_y, y, WORLD_H)
            if (dx0 * dx0 + dy0 * dy0) ** 0.5 < avoid_r:
                continue

            # evita overlap tra ostacoli (in torus: usiamo delta corto rispetto al candidato)
            ok = True
            for ob in self.obstacles:
                dx = shortest_delta(x, ob.x, WORLD_W)
                dy = shortest_delta(y, ob.y, WORLD_H)
                if abs(dx) < (ow + ob.w) / 2 and abs(dy) < (oh + ob.h) / 2:
                    # rettangoli potenzialmente sovrapposti -> scartiamo
                    ok = False
                    break
            if not ok:
                continue

            img = random.choice(imgs)
            self.obstacles.append(Obstacle(img=img, x=x, y=y, w=ow, h=oh))
            placed += 1

    def _random_weapon_kind(self) -> int:
        # 75% arma_01, 25% arma_02
        return 1 if random.random() < 0.75 else 2

    def _spawn_slots(self):
        margin_x = 200
        margin_y = 200
        avoid_start_r = 260

        for ty in range(3):
            for tx in range(3):
                tile_x0 = tx * TILE_W
                tile_y0 = ty * TILE_H

                tries = 0
                while True:
                    tries += 1
                    sx = random.uniform(tile_x0 + margin_x, tile_x0 + TILE_W - margin_x)
                    sy = random.uniform(tile_y0 + margin_y, tile_y0 + TILE_H - margin_y)

                    # evita start (centro)
                    dx0 = shortest_delta(WORLD_W / 2, sx, WORLD_W)
                    dy0 = shortest_delta(WORLD_H / 2, sy, WORLD_H)
                    if (dx0 * dx0 + dy0 * dy0) ** 0.5 < avoid_start_r and tries < 200:
                        continue

                    # evita ostacoli (bbox approssimato)
                    ok = True
                    for ob in self.obstacles:
                        dx = shortest_delta(sx, ob.x, WORLD_W)
                        dy = shortest_delta(sy, ob.y, WORLD_H)
                        if abs(dx) < (SLOT_W + ob.w) / 2 and abs(dy) < (SLOT_H + ob.h) / 2:
                            ok = False
                            break

                    if ok or tries >= 400:
                        self.slots.append(
                            Slot(
                                x=sx,
                                y=sy,
                                weapon_kind=self._random_weapon_kind(),
                                weapon_active=True,
                                respawn_at_ms=0,
                            )
                        )
                        break

    # calcola speed wave
    def _duck_speed_for_wave(self, wave: int) -> float:
        return DUCK_SPEED_BASE + DUCK_SPEED_INC_PER_WAVE * (wave - 1)

    # spawn check coerente con hitbox "piedi" (quarto inferiore)
    def _world_pos_hits_obstacle(self, x: float, y: float) -> bool:
        # x,y sono il CENTRO sprite del nemico.
        # I "piedi" sono nel quarto inferiore -> centro piedi più in basso.
        foot_cx = x
        foot_cy = (y + (DUCK_SPRITE_H / 2 - DUCK_FOOT_H / 2)) % WORLD_H

        for ob in self.obstacles:
            dx = shortest_delta(foot_cx, ob.x, WORLD_W)
            dy = shortest_delta(foot_cy, ob.y, WORLD_H)

            if abs(dx) < (DUCK_FOOT_W + ob.w) / 2 and abs(dy) < (DUCK_FOOT_H + ob.h) / 2:
                return True
        return False


    # collisione nemico (piedi) con ostacoli in WORLD coords
    def _enemy_hits_obstacle_at(self, ex: float, ey: float) -> bool:
        # centro dei piedi in world coords (offset verso il basso rispetto al centro sprite)
        foot_cx = ex
        foot_cy = (ey + (DUCK_SPRITE_H / 2 - DUCK_FOOT_H / 2)) % WORLD_H

        for ob in self.obstacles:
            dx = shortest_delta(foot_cx, ob.x, WORLD_W)
            dy = shortest_delta(foot_cy, ob.y, WORLD_H)

            if abs(dx) < (DUCK_FOOT_W + ob.w) / 2 and abs(dy) < (DUCK_FOOT_H + ob.h) / 2:
                return True
        return False

    

    # push duck fuori dagli ostacoli (world coords)
    def _push_duck_out_of_obstacles(self, en: Enemy):
        # tentativi: spingi lungo X o Y in base a penetrazione minima
        for ob in self.obstacles:
            dx = shortest_delta(en.x, ob.x, WORLD_W)
            dy = shortest_delta(en.y, ob.y, WORLD_H)

            # overlap AABB in world coords
            ox = (DUCK_HITBOX_W + ob.w) / 2 - abs(dx)
            oy = (DUCK_HITBOX_H + ob.h) / 2 - abs(dy)
            if ox > 0 and oy > 0:
                # scegli asse con overlap minore
                if ox < oy:
                    en.x = (en.x + (ox if dx > 0 else -ox)) % WORLD_W
                else:
                    en.y = (en.y + (oy if dy > 0 else -oy)) % WORLD_H


    # spawn appena fuori schermo
    def _spawn_point_offscreen(self) -> tuple[float, float]:
        # scegli un lato e genera una coordinata “appena fuori” dal visibile, in world coords
        side = random.choice(["L", "R", "T", "B"])
        if side == "L":
            sx = -W / 2 - WAVE_SPAWN_MARGIN
            sy = random.uniform(-H / 2, H / 2)
        elif side == "R":
            sx = W / 2 + WAVE_SPAWN_MARGIN
            sy = random.uniform(-H / 2, H / 2)
        elif side == "T":
            sx = random.uniform(-W / 2, W / 2)
            sy = -H / 2 - WAVE_SPAWN_MARGIN
        else:  # "B"
            sx = random.uniform(-W / 2, W / 2)
            sy = H / 2 + WAVE_SPAWN_MARGIN

        wx = (self.px + sx) % WORLD_W
        wy = (self.py + sy) % WORLD_H
        return wx, wy

    # spawn wave (50 normali, oppure 40+10 élite ogni 3)
    def _spawn_wave(self):
        wave = self.wave
        if wave % 3 == 0:
            want_normal = 40
            want_elite = 10
        else:
            want_normal = 50
            want_elite = 0

        # spawn normali
        for _ in range(want_normal):
            for _try in range(50):
                x, y = self._spawn_point_offscreen()
                if self._world_pos_hits_obstacle(x, y):
                    continue
                if self.ducks_normal.spawn(False, x, y):
                    break
                else:
                    # pool pieno -> stop
                    break

        # spawn élite
        for _ in range(want_elite):
            for _try in range(50):
                x, y = self._spawn_point_offscreen()
                if self._world_pos_hits_obstacle(x, y):
                    continue
                if self.ducks_elite.spawn(True, x, y):
                    break
                else:
                    break


    def _check_weapon_pickups(self):
        now = pygame.time.get_ticks()

        # hitbox player: usa la stessa logica “solo terzo inferiore”
        p_img = self._current_player_image()
        p_rect = p_img.get_rect(center=(W // 2, H // 2))
        p_hit = p_rect.copy()
        cut = (p_hit.height * 2) // 3
        p_hit.y += cut
        p_hit.height = max(1, p_hit.height - cut)

        for sl in self.slots:
            # respawn
            if not sl.weapon_active:
                if now >= sl.respawn_at_ms:
                    sl.weapon_kind = self._random_weapon_kind()
                    sl.weapon_active = True
                continue

            # pickup
            wrect = sl.weapon_rect_local(self.px, self.py)
            if p_hit.colliderect(wrect):
                if sl.weapon_kind == 1:
                    self.ammo1 += AMMO_PICKUP_AMOUNT
                else:
                    self.ammo2 += AMMO_PICKUP_AMOUNT
                    self.energy = min(100, self.energy + ENERGY_PICKUP_FOR_WEAPON2)

                sl.weapon_active = False
                sl.respawn_at_ms = now + WEAPON_RESPAWN_MS



    def _update_facing(self, vx: float, vy: float):
        # segue le specifiche: W=back, S=front, D=dx, A=sx
        if vy > 0:
            self.facing = "front"
        elif vy < 0:
            self.facing = "back"
        elif vx > 0:
            self.facing = "dx"
        elif vx < 0:
            self.facing = "sx"

    def _current_player_image(self) -> pygame.Surface:
        if self.facing == "back":
            return self.jac_back
        if self.facing == "dx":
            return self.jac_dx
        if self.facing == "sx":
            return self.jac_sx
        return self.jac_front

    def _player_rect_screen(self) -> pygame.Rect:
        img = self._current_player_image()
        return img.get_rect(center=(W // 2, H // 2))

    def _facing_dir(self) -> tuple[float, float]:
        # coerente con facing: W=back, S=front, D=dx, A=sx
        if self.facing == "back":
            return (0.0, -1.0)
        if self.facing == "dx":
            return (1.0, 0.0)
        if self.facing == "sx":
            return (-1.0, 0.0)
        return (0.0, 1.0)  # front

    def _mouse_dir(self) -> tuple[float, float]:
        mx, my = pygame.mouse.get_pos()
        dx = mx - (W // 2)
        dy = my - (H // 2)

        # se il mouse è praticamente al centro, fallback su direzione del player
        if abs(dx) < 1 and abs(dy) < 1:
            return self._facing_dir()

        length = math.hypot(dx, dy)
        return (dx / length, dy / length)


    def handle_events(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                mods = pygame.key.get_mods()
                want_kind2 = bool(mods & pygame.KMOD_SHIFT)  # SHIFT+SPACE => colpo_02

                now_ms = pygame.time.get_ticks()
                dx, dy = self._mouse_dir()

                # punto di spawn: leggermente davanti al player
                spawn_x = (self.px + dx * 70) % WORLD_W
                spawn_y = (self.py + dy * 70) % WORLD_H

                vx = dx * BULLET_SPEED
                vy = dy * BULLET_SPEED

                if want_kind2:
                    # colpo_02: consuma ammo2 + energia
                    if self.ammo2 <= 0:
                        return
                    if self.energy < BULLET2_ENERGY_COST:
                        return
                    if self.bullet_pool.spawn(2, spawn_x, spawn_y, vx, vy, now_ms):
                        self.ammo2 -= 1
                        self.energy = max(0, self.energy - BULLET2_ENERGY_COST)
                else:
                    # colpo_01: consuma ammo1
                    if self.ammo1 <= 0:
                        return
                    if self.bullet_pool.spawn(1, spawn_x, spawn_y, vx, vy, now_ms):
                        self.ammo1 -= 1

            # ducks_normal / ducks_elite
            if False and e.type == pygame.KEYDOWN and e.key == DEBUG_SPAWN_ENEMY_KEY:
                # spawn a distanza casuale dal player (non troppo vicino)
                for _ in range(10):
                    ang = random.uniform(0, math.tau)
                    dist = random.uniform(500, 900)
                    ex = (self.px + math.cos(ang) * dist) % WORLD_W
                    ey = (self.py + math.sin(ang) * dist) % WORLD_H

                    elite = (random.random() < 0.2)  # 20% elite per test
                    if elite:
                        if self.ducks_elite.spawn(True, ex, ey):
                            break
                    else:
                        if self.ducks_normal.spawn(False, ex, ey):
                            break

    def _bullet_hits_obstacle(self, bx: float, by: float, bw: int, bh: int) -> bool:
        # rettangolo proiettile in coordinate schermo (wrap-aware)
        dx = shortest_delta(self.px, bx, WORLD_W)
        dy = shortest_delta(self.py, by, WORLD_H)
        br = pygame.Rect(int((W // 2) + dx - bw // 2), int((H // 2) + dy - bh // 2), bw, bh)

        for ob in self.obstacles:
            dxo = shortest_delta(self.px, ob.x, WORLD_W)
            dyo = shortest_delta(self.py, ob.y, WORLD_H)
            orc = pygame.Rect(
                int((W // 2) + dxo - ob.w // 2),
                int((H // 2) + dyo - ob.h // 2),
                ob.w,
                ob.h,
            )
            if br.colliderect(orc):
                return True
        return False
 

    def _collides_with_obstacles(self, test_px: float, test_py: float) -> bool:
        # collisione bbox (no alpha): player al centro, ostacoli in coordinate locali rispetto al player "test"
        # Prospettiva: il player può "sovrapporsi" agli ostacoli con la parte superiore.
        # La collisione avviene solo sul terzo inferiore dello sprite del player.
        p_img = self._current_player_image()
        p_rect = p_img.get_rect(center=(W // 2, H // 2))
        p_hit = p_rect.copy()

        cut = (p_hit.height * 2) // 3
        p_hit.y += cut
        p_hit.height = max(1, p_hit.height - cut)

        for ob in self.obstacles:
            dx = shortest_delta(test_px, ob.x, WORLD_W)
            dy = shortest_delta(test_py, ob.y, WORLD_H)
            ob_rect = pygame.Rect(
                int((W // 2) + dx - ob.w // 2),
                int((H // 2) + dy - ob.h // 2),
                ob.w,
                ob.h,
            )
            if p_hit.colliderect(ob_rect):
                return True
        return False

    # movimento nemico con prova diagonale + fallback direzioni
    def _move_enemy_towards_player(self, en: Enemy, dt: float, speed: float):
        # direzione verso player (wrap-aware)
        dx = shortest_delta(en.x, self.px, WORLD_W)
        dy = shortest_delta(en.y, self.py, WORLD_H)

        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return

        ux = dx / dist
        uy = dy / dist

        step = speed * dt

        def try_move_dir(dirx: float, diry: float) -> bool:
            """Prova prima movimento diagonale (x+y insieme), poi slide su assi.
            Ritorna True se si è mosso almeno un po'."""
            moved = False
            sx = dirx * step
            sy = diry * step

            # 1) prova movimento "full" (diagonale)
            nx = (en.x + sx) % WORLD_W
            ny = (en.y + sy) % WORLD_H
            if not self._enemy_hits_obstacle_at(nx, ny):
                en.x, en.y = nx, ny
                return True

            # 2) slide: prova asse dominante prima
            if abs(sx) >= abs(sy):
                # prova X
                nx = (en.x + sx) % WORLD_W
                if not self._enemy_hits_obstacle_at(nx, en.y):
                    en.x = nx
                    moved = True
                # prova Y
                ny = (en.y + sy) % WORLD_H
                if not self._enemy_hits_obstacle_at(en.x, ny):
                    en.y = ny
                    moved = True
            else:
                # prova Y
                ny = (en.y + sy) % WORLD_H
                if not self._enemy_hits_obstacle_at(en.x, ny):
                    en.y = ny
                    moved = True
                # prova X
                nx = (en.x + sx) % WORLD_W
                if not self._enemy_hits_obstacle_at(nx, en.y):
                    en.x = nx
                    moved = True

            return moved

        # Prova direzione verso player
        if try_move_dir(ux, uy):
            return

        # 3) Se bloccato: prova direzioni alternative attorno alla direzione desiderata
        # (rotazioni progressive: aiuta a "scivolare" intorno al bordo)
        angles_deg = [30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180]
        for a in angles_deg:
            rad = math.radians(a)
            ca = math.cos(rad)
            sa = math.sin(rad)
            rx = ux * ca - uy * sa
            ry = ux * sa + uy * ca

            # normalizza (per sicurezza)
            rlen = math.hypot(rx, ry)
            if rlen < 1e-6:
                continue
            rx /= rlen
            ry /= rlen

            if try_move_dir(rx, ry):
                return

        # se anche così è bloccato, resta fermo (raro: compresso da molte papere / corner strettissimo)




    def update(self, dt: float, keys):
        now_ms = pygame.time.get_ticks()
        # input -> velocità virtuale del personaggio
        vx = 0.0
        vy = 0.0
        if keys[pygame.K_a]:
            vx -= PLAYER_SPEED
        if keys[pygame.K_d]:
            vx += PLAYER_SPEED
        if keys[pygame.K_w]:
            vy -= PLAYER_SPEED
        if keys[pygame.K_s]:
            vy += PLAYER_SPEED

        if vx != 0.0 or vy != 0.0:
            self._update_facing(vx, vy)

        # movimento: axis-separated per bloccare bene sugli ostacoli
        dx = vx * dt
        dy = vy * dt

        # x
        if dx != 0:
            nx = (self.px + dx) % WORLD_W
            if not self._collides_with_obstacles(nx, self.py):
                self.px = nx
        # y
        if dy != 0:
            ny = (self.py + dy) % WORLD_H
            if not self._collides_with_obstacles(self.px, ny):
                self.py = ny

        if self._blink_ms_left > 0:
            self._blink_ms_left = max(0, self._blink_ms_left - int(dt * 1000))

        # wave timer
        if now_ms >= self._next_wave_ms:
            self._spawn_wave()
            self._next_wave_ms = now_ms + WAVE_INTERVAL_MS
            # wave incrementa dopo lo spawn (wave corrente visibile)
            # Se preferisci mostrare la wave “nuova” subito, inverti le 2 righe.
            self.wave += 1

        # update bullets
        self.bullet_pool.update(dt, now_ms)

        # bullet fuori schermo => deactivate
        margin = 30
        for b in self.bullet_pool.bullets:
            if not b.active:
                continue

            dx = shortest_delta(self.px, b.x, WORLD_W)
            dy = shortest_delta(self.py, b.y, WORLD_H)

            if abs(dx) > (W / 2 + margin) or abs(dy) > (H / 2 + margin):
                b.deactivate()


        # update papere (axis-separated vs ostacoli)
        speed = self._duck_speed_for_wave(max(1, self.wave - 1))

        for en in self.ducks_normal.enemies:
            if en.active:
                self._move_enemy_towards_player(en, dt, speed)

        for en in self.ducks_elite.enemies:
            if en.active:
                self._move_enemy_towards_player(en, dt, speed)

        # pulizia cooldown quack per papere non più attive
        if self._last_quack_ms:
            for en in (self.ducks_normal.enemies + self.ducks_elite.enemies):
                if (not en.active) and (id(en) in self._last_quack_ms):
                    del self._last_quack_ms[id(en)]


        # evita che le papere camminino sugli ostacoli
        #for en in self.ducks_normal.enemies:
        #    if en.active:
        #        self._push_duck_out_of_obstacles(en)
        #for en in self.ducks_elite.enemies:
        #    if en.active:
        #        self._push_duck_out_of_obstacles(en)
                

        # rebuild grid with enemies
        self.grid.clear()
        for en in self.ducks_normal.enemies:
            if en.active:
                self.grid.add_rect(en.body_rect_local(self.px, self.py), en)
        for en in self.ducks_elite.enemies:
            if en.active:
                self.grid.add_rect(en.body_rect_local(self.px, self.py), en)


        

        # push-apart enemies (no overlap)
        def push_apart(a: Enemy, b: Enemy):
            # lavora in WORLD coords usando delta corto
            dx = shortest_delta(a.x, b.x, WORLD_W)
            dy = shortest_delta(a.y, b.y, WORLD_H)

            # se sono nello stesso punto, dai una direzione casuale
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                ang = random.uniform(0, math.tau)
                dx, dy = math.cos(ang), math.sin(ang)
                dist = 1.0

            # raggio "fisico" (hitbox come cerchio)
            ra = DUCK_FOOT_W / 2
            rb = DUCK_FOOT_W / 2
            overlap = (ra + rb) - dist
            if overlap > 0:
                MAX_PUSH = 6.0
                overlap = min(overlap, MAX_PUSH)
                nx = dx / dist
                ny = dy / dist
                a.x = (a.x - nx * overlap * 0.5) % WORLD_W
                a.y = (a.y - ny * overlap * 0.5) % WORLD_H
                b.x = (b.x + nx * overlap * 0.5) % WORLD_W
                b.y = (b.y + ny * overlap * 0.5) % WORLD_H

        # esegui push-apart usando vicinato celle (query su rect nemico)
        for en in self.ducks_normal.enemies:
            if not en.active:
                continue
            r = en.rect_local(self.px, self.py)
            for other in self.grid.query_rect(r):
                if other is en or not other.active:
                    continue
                push_apart(en, other)

        for en in self.ducks_elite.enemies:
            if not en.active:
                continue
            r = en.rect_local(self.px, self.py)
            for other in self.grid.query_rect(r):
                if other is en or not other.active:
                    continue
                push_apart(en, other)

        # 2° pass anti-ostacoli (dopo push-apart) per evitare jitter
        #for en in self.ducks_normal.enemies:
        #    if en.active:
        #        self._push_duck_out_of_obstacles(en)
        #for en in self.ducks_elite.enemies:
        #    if en.active:
        #        self._push_duck_out_of_obstacles(en)

        # rebuild grid dopo push-apart (posizioni aggiornate)
        self.grid.clear()
        for en in self.ducks_normal.enemies:
            if en.active:
                self.grid.add_rect(en.body_rect_local(self.px, self.py), en)
        for en in self.ducks_elite.enemies:
            if en.active:
                self.grid.add_rect(en.body_rect_local(self.px, self.py), en)


        # drain energia per contatto con nemici
        p_img = self._current_player_image()
        p_rect = p_img.get_rect(center=(W // 2, H // 2))
        p_hit = p_rect.copy()
        cut = (p_hit.height * 2) // 3
        p_hit.y += cut
        p_hit.height = max(1, p_hit.height - cut)

        near = 0

        def is_near(en: Enemy) -> bool:
            dx = shortest_delta(self.px, en.x, WORLD_W)
            dy = shortest_delta(self.py, en.y, WORLD_H)
            return (dx*dx + dy*dy) <= (ENERGY_DRAIN_RADIUS * ENERGY_DRAIN_RADIUS)

        for en in self.ducks_normal.enemies:
            if en.active and is_near(en):
                near += 1
        for en in self.ducks_elite.enemies:
            if en.active and is_near(en):
                near += 1

        # drain energia + quack per papera (max 1/sec ciascuna)
        if near > 0 and self._blink_ms_left <= 0:
            # energia
            self._energy_drain_accum += dt * (ENERGY_DRAIN_RATE_PER_DUCK * near)

            # quack: uno per papera "vicina" con cooldown 1000ms
            if self.quacks:
                # raccogli tutte le papere vicine (normali + elite)
                near_enemies: list[Enemy] = []
                for en in self.ducks_normal.enemies:
                    if en.active and is_near(en):
                        near_enemies.append(en)
                for en in self.ducks_elite.enemies:
                    if en.active and is_near(en):
                        near_enemies.append(en)

                for en in near_enemies:
                    eid = id(en)
                    last = self._last_quack_ms.get(eid, -10_000)
                    if now_ms - last >= 1000:
                        self._last_quack_ms[eid] = now_ms
                        random.choice(self.quacks).play()

        # applica drain (float immediato)
        drain = self._energy_drain_accum
        if drain > 0:
            self.energy = max(0, self.energy - drain)
            self._energy_drain_accum = 0.0

            
        # perdita vita
        if self.energy <= 0:
            self.lives -= 1
            if self.lives <= 0:
                # segnala game over: lo gestiamo dal main
                self._game_over = True
            else:
                self.energy = 100
                self._blink_ms_left = 2000  # 2 secondi blink
                self._energy_drain_accum = 0.0


        # bullet vs enemy usando griglia
        bsize = 24

        for b in self.bullet_pool.bullets:
            if not b.active:
                continue

            dx = shortest_delta(self.px, b.x, WORLD_W)
            dy = shortest_delta(self.py, b.y, WORLD_H)
            br = pygame.Rect(int((W // 2) + dx - bsize // 2), int((H // 2) + dy - bsize // 2), bsize, bsize)

            candidates = self.grid.query_rect(br)
            for en in candidates:
                if not getattr(en, "active", False):
                    continue
                er = en.body_rect_local(self.px, self.py)
                if br.colliderect(er):
                    en.hit(1)
                    b.hits_left -= 1
                    if b.hits_left <= 0:
                        b.deactivate()
                    break


        # collisione contro ostacoli: se collide, sparisce
        bsize = 24  # coerente col fallback_size
        for b in self.bullet_pool.bullets:
            if not b.active:
                continue
            if self._bullet_hits_obstacle(b.x, b.y, bsize, bsize):
                b.deactivate()

        self._check_weapon_pickups()


    def draw_world(self, screen: pygame.Surface):
        """
        Disegno del mondo:
        - background tile 1920x1080 ripetuto su 3x3 e wrap
        - ostacoli fissi in coordinate virtuali, renderizzati relativi al player
        - player sempre al centro
        """
        # view top-left in world coords
        view_x = self.px - W / 2
        view_y = self.py - H / 2

        # tiles to cover the screen (+1 margin)
        start_tx = math.floor(view_x / TILE_W)
        start_ty = math.floor(view_y / TILE_H)
        end_tx = math.floor((view_x + W) / TILE_W)
        end_ty = math.floor((view_y + H) / TILE_H)

        for ty in range(start_ty, end_ty + 1):
            for tx in range(start_tx, end_tx + 1):
                # world tile coordinate wrapped in 0..2
                wtx = tx % 3
                wty = ty % 3

                # top-left of this tile in world coords (wrapped)
                tile_world_x = tx * TILE_W
                tile_world_y = ty * TILE_H

                # compute screen position (relative to view)
                sx = tile_world_x - view_x
                sy = tile_world_y - view_y

                screen.blit(self.bkg_tile, (int(sx), int(sy)))

        # obstacles (solo quelli "vicini" saranno visibili con rect_local)
        for ob in self.obstacles:
            r = ob.rect_local(self.px, self.py)
            # culling semplice
            if r.right < 0 or r.left > W or r.bottom < 0 or r.top > H:
                continue
            screen.blit(ob.img, r)


        #slot + armi
        for sl in self.slots:
            r = sl.rect_local(self.px, self.py)
            if not (r.right < 0 or r.left > W or r.bottom < 0 or r.top > H):
                screen.blit(self.slot_img, r)

            if sl.weapon_active:
                wr = sl.weapon_rect_local(self.px, self.py)
                if wr.right < 0 or wr.left > W or wr.bottom < 0 or wr.top > H:
                    continue
                screen.blit(self.arma1 if sl.weapon_kind == 1 else self.arma2, wr)

        # draw ducks (animazione + dx/sx + elite)

        frame2 = ((pygame.time.get_ticks() // DUCK_ANIM_MS) % 2) == 1

        def duck_image(en: Enemy) -> pygame.Surface:
            # se en.x < player.x → guarda verso destra (DX), altrimenti SX
            use_dx = en.x < self.px

            if en.elite:
                if use_dx:
                    return self.papera_elite_dx_02 if frame2 else self.papera_elite_dx_01
                else:
                    return self.papera_elite_sx_02 if frame2 else self.papera_elite_sx_01
            else:
                if use_dx:
                    return self.papera_dx_02 if frame2 else self.papera_dx_01
                else:
                    return self.papera_sx_02 if frame2 else self.papera_sx_01


        # normali
        for en in self.ducks_normal.enemies:
            if not en.active:
                continue

            dx = shortest_delta(self.px, en.x, WORLD_W)
            dy = shortest_delta(self.py, en.y, WORLD_H)
            sx = int((W // 2) + dx)
            sy = int((H // 2) + dy)

            img = duck_image(en)
            r = img.get_rect(center=(sx, sy))

            if r.right < 0 or r.left > W or r.bottom < 0 or r.top > H:
                continue

            screen.blit(img, r)


        # élite
        for en in self.ducks_elite.enemies:
            if not en.active:
                continue

            dx = shortest_delta(self.px, en.x, WORLD_W)
            dy = shortest_delta(self.py, en.y, WORLD_H)
            sx = int((W // 2) + dx)
            sy = int((H // 2) + dy)

            img = duck_image(en)
            r = img.get_rect(center=(sx, sy))

            if r.right < 0 or r.left > W or r.bottom < 0 or r.top > H:
                continue

            screen.blit(img, r)

        # draw bullets (sopra il mondo, sotto il player)
        for b in self.bullet_pool.bullets:
            if not b.active:
                continue

            dx = shortest_delta(self.px, b.x, WORLD_W)
            dy = shortest_delta(self.py, b.y, WORLD_H)
            sx = int((W // 2) + dx)
            sy = int((H // 2) + dy)

            img_b = self.colpo1 if b.kind == 1 else self.colpo2
            r = img_b.get_rect(center=(sx, sy))

            # culling semplice
            if r.right < 0 or r.left > W or r.bottom < 0 or r.top > H:
                continue

            screen.blit(img_b, r)



        # player (blink: lo facciamo lampeggiare più avanti quando implementiamo danni/vite)
        img = self._current_player_image()
        prect = img.get_rect(center=(W // 2, H // 2))
        if self._blink_ms_left > 0:
            # lampeggio (50% duty)
            if (pygame.time.get_ticks() // 120) % 2 == 0:
                screen.blit(img, prect)
        else:
            screen.blit(img, prect)

    def draw_hud(self, screen: pygame.Surface, font50: pygame.font.Font):
        # Labels
        screen.blit(font50.render("ENERGIA", True, VERDE_SCURO), (35, 42))
        screen.blit(font50.render("VITE", True, VERDE_SCURO), (35, 989))
        screen.blit(font50.render(f"WAVE {self.wave}", True, VERDE_SCURO), (1610, 42))

        # hearts (3 posizioni fisse; se vite < 3 non disegniamo quelli a destra)
        heart_positions = [(213, 987), (296, 987), (379, 987)]
        for i in range(min(self.lives, 3)):
            screen.blit(self.heart, heart_positions[i])

        # weapons icons + ammo counts
        screen.blit(self.arma1, (1328, 963))
        screen.blit(font50.render(str(self.ammo1), True, VERDE_SCURO), (1442, 986))

        screen.blit(self.arma2, (1617, 963))
        screen.blit(font50.render(str(self.ammo2), True, VERDE_SCURO), (1754, 986))

        # energy bar: 500px = 100 energia => 5px per punto
        bar_x, bar_y = 335, 36
        bar_w, bar_h = 500, 50
        # base (outline invisibile richiesto? no -> solo pieno verde)
        energy_w = max(0, min(bar_w, int(self.energy * 5)))
        pygame.draw.rect(screen, VERDE_SCURO, pygame.Rect(bar_x, bar_y, energy_w, bar_h))


# -----------------------------
# Main game class
# -----------------------------
class Game15Duck:
    def __init__(self, best_score: int):
        self.best_score = best_score

        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption("Game 15 - Duck")
        self.clock = pygame.time.Clock()

        self.font60 = safe_font(FONT_PATH, 60)
        self.font70 = safe_font(FONT_PATH, 70)
        self.font50 = safe_font(FONT_PATH, 50)

        self.bkg_menu = safe_image(BKG_MENU_PATH)
        self.bkg_istr = safe_image(BKG_ISTR_PATH)

        # Stato
        self.running = True
        self.state = "INTRO"  # INTRO -> MENU -> HELP -> GAME
        self.props = load_json(PROPS_PATH)
        self.primorun = bool(self.props.get("primorun", True))

        if not self.primorun:
            self.state = "MENU"

        # Musica: deve partire quando si entra nel menu e restare sempre in loop
        self.music_started = False

        # Se partiamo direttamente dal MENU (primorun già false), la musica deve partire subito
        if self.state == "MENU":
            self.ensure_music()

        # Sessione di gioco
        self.session: GameSession | None = None
        # memorizza wave raggiunta per schermata GAME OVER
        self.last_wave_reached = 1


        self.menu_items = [
            MenuItem("NUOVA PARTITA", 386, "NEW"),
            MenuItem("ISTRUZIONI", 651, "HELP"),
            MenuItem("ESCI", 921, "QUIT"),
        ]
        for it in self.menu_items:
            it.compute_rect(self.font60, W // 2)

        # Intro timeline (ms)
        self.intro_t0 = pygame.time.get_ticks()
        # NB: nel file caricato hai già adattato in più righe la frase lunga: la lasciamo così,
        # perché comunque rispetta la sequenza e mantiene font/posizioni e tempi.
        self.intro_lines = [
            (2000, "Normandia 1944", (W // 2, H * 1 // 8)),
            (5000, "Con un eroico sbarco", (W // 2, H * 2 // 8)),
            (5000, "comincia la riscossa alleata", (W // 2, H * 3 // 8)),
            (5000, "contro il regno del male", (W // 2, H * 4 // 8)),
            (9000, "Normandia 2022", (W // 2, H * 5 // 8)),
            (11000, "Questa volta ad attaccare", (W // 2, H * 6 // 8)),
            (11000, "non sono i buoni!", (W // 2, H * 7 // 8)),
        ]
        self.intro_end_ms = 16000  # 2s +3s +4s +2s +5s

    # -------------------------
    # Music control
    # -------------------------
    def ensure_music(self):
        if self.music_started:
            return
        if os.path.exists(MUSIC_PATH):
            try:
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play(-1)  # loop
            except pygame.error:
                pass
        self.music_started = True

    # -------------------------
    # State transitions
    # -------------------------
    def goto_menu(self):
        self.state = "MENU"
        self.ensure_music()
        self.session = None

    def goto_help(self):
        self.state = "HELP"
        self.ensure_music()

    def goto_game(self):
        self.ensure_music()
        self.session = GameSession()
        self.state = "GAME"

    def quit_to_jacoplay(self):
        pygame.quit()
        raise SystemExit(int(self.best_score))

    # -------------------------
    # Event handling
    # -------------------------
    def handle_common_events(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
            # ESC dipende dallo stato
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                if self.state == "MENU":
                    # da menu: esci dal gioco
                    self.running = False
                elif self.state == "GAME":
                    # in gioco: torna al menu
                    self.goto_menu()
                elif self.state in ("HELP", "GAMEOVER", "INTRO"):
                    # comportamento comodo: torna al menu
                    self.goto_menu()

    def handle_menu_events(self, events):
        mx, my = pygame.mouse.get_pos()
        for it in self.menu_items:
            it.hovered = bool(it.rect and it.rect.collidepoint(mx, my))

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for it in self.menu_items:
                    if it.rect and it.rect.collidepoint(e.pos):
                        if it.action == "NEW":
                            self.goto_game()
                        elif it.action == "HELP":
                            self.goto_help()
                        elif it.action == "QUIT":
                            self.quit_to_jacoplay()

    def handle_help_events(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN:
                self.goto_menu()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.goto_menu()

    def handle_game_events(self, events):
        # Per ora nessun input "di gameplay" (arriva con proiettili/armi).
        # Manteniamo solo eventuale ritorno al menu per debug (Tasto M).
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_m:
                self.goto_menu()

        if self.session is not None:
            self.session.handle_events(events)


    # -------------------------
    # Render
    # -------------------------
    def render_intro(self):
        self.screen.fill((0, 0, 0))
        now = pygame.time.get_ticks()
        dt = now - self.intro_t0

        for t_ms, line, pos in self.intro_lines:
            if dt >= t_ms:
                surf, rect = render_centered(self.font60, line, BIANCO, pos)
                self.screen.blit(surf, rect)

        if dt >= self.intro_end_ms:
            if self.primorun:
                self.primorun = False
                self.props["primorun"] = False
                try:
                    save_json(PROPS_PATH, self.props)
                except OSError:
                    pass
            self.goto_menu()

    def render_menu(self):
        self.screen.blit(self.bkg_menu, (0, 0))
        for it in self.menu_items:
            it.draw(self.screen, self.font60, W // 2)

    def render_help(self):
        self.screen.blit(self.bkg_istr, (0, 0))

    def render_game(self, dt: float):
        assert self.session is not None
        keys = pygame.key.get_pressed()
        self.session.update(dt, keys)
        # switch a GAMEOVER
        # salva wave raggiunta prima del GAMEOVER
        if getattr(self.session, "_game_over", False):
            # Nota: nel tuo codice la wave viene incrementata dopo lo spawn,
            # quindi la "wave corrente" è wave-1.
            self.last_wave_reached = max(1, self.session.wave - 1)
            self.state = "GAMEOVER"
            return

        # world
        self.session.draw_world(self.screen)

        # HUD sopra
        self.session.draw_hud(self.screen, self.font50)

    # render GAMEOVER (metodo di classe, NON annidato)
    def render_gameover(self):
        self.screen.blit(self.bkg_menu, (0, 0))
        surf, rect = render_centered(self.font70, "GAME OVER", VERDE_SCURO, (W // 2, H // 2))
        self.screen.blit(surf, rect)

        # testo wave affrontate
        surf2, rect2 = render_centered(
            self.font60,
            f"Hai affrontato {self.last_wave_reached} wave",
            VERDE_SCURO,
            (W // 2, H // 2 + 90),
        )
        self.screen.blit(surf2, rect2)
        

    # input GAMEOVER (metodo di classe, NON annidato)
    def handle_gameover_events(self, events):
        for e in events:
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.goto_menu()
                return

    # -------------------------
    # Main loop
    # -------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            events = pygame.event.get()

            self.handle_common_events(events)

            if self.state == "INTRO":
                self.render_intro()

            elif self.state == "MENU":
                self.handle_menu_events(events)
                self.render_menu()

            elif self.state == "HELP":
                self.handle_help_events(events)
                self.render_help()

            elif self.state == "GAME":
                self.handle_game_events(events)
                if self.session is None:
                    self.session = GameSession()
                self.render_game(dt)
            elif self.state == "GAMEOVER":
                self.handle_gameover_events(events)
                self.render_gameover()


            pygame.display.flip()

        self.quit_to_jacoplay()


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--score", type=int, default=0, help="Best score dalle sessioni precedenti")
    return p.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])
    game = Game15Duck(best_score=args.score)
    game.run()


if __name__ == "__main__":
    main()

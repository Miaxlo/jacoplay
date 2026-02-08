# game_02_roll.py
#
# Prima versione:
# - Menu principale (NUOVA PARTITA, ISTRUZIONI, ESCI)
# - Schermata istruzioni
# - Gioco base con solo movimento del personaggio (tasti A/D/W/S)
# - Nessun robot/oggetti/carta ancora (verranno aggiunti in step successivi)

import sys
import os
import math
import argparse
import random

import pygame

# ---------------------------------------------------------------------------
# COSTANTI E CONFIGURAZIONE
# ---------------------------------------------------------------------------

INTERNAL_WIDTH = 1920
INTERNAL_HEIGHT = 1080

BIANCO = (255, 255, 255)
VIOLA = (120, 32, 110)
NERO = (0, 0, 0)

# Stati di gioco
STATE_MENU = "MENU"
STATE_INSTRUCTIONS = "INSTRUCTIONS"
STATE_PLAYING = "PLAYING"
STATE_GAME_OVER = "GAME_OVER"

# Area di gioco del personaggio
PLAYER_AREA_X = 421
PLAYER_AREA_Y = 67
PLAYER_AREA_W = 970
PLAYER_AREA_H = 970

PLAYER_ANIM_INTERVAL = 100  # ms tra un frame e l'altro
PLAYER_STEP = 20            # pixel per step

# Area di gioco del robot
ROBOT_AREA_X = 354
ROBOT_AREA_Y = 22
ROBOT_AREA_W = 1116
ROBOT_AREA_H = 1058

# Posizione iniziale robot
ROBOT_START_X = 1370
ROBOT_START_Y = 980

# Velocità robot per stage (px/s)
ROBOT_SPEED_STAGE = {
    1: 80,
    2: 160,
    3: 240,
}

# Velocità di rotazione quando rimbalza su un bordo (gradi al secondo)
ROBOT_ROT_SPEED = 180

# (Per dopo, quando gestiremo la rotazione su carta)
ROBOT_SPIN_SPEED = 180  # gradi al secondo

# Durata dello spin del robot dopo aver toccato la carta (in secondi)
ROBOT_SPIN_DURATION = 3

# Velocità della pallina di carta (px/s)
PAPER_SHOT_SPEED = 600


# --- Parametri oggetti / carta per stage ---------------------------------

OBJECT_SPAWN_INTERVAL = {  # secondi
    1: 3.0,
    2: 5.0,
    3: 8.0,
}

OBJECT_SPAWN_PROB = {      # probabilità di far comparire qualcosa
    1: 0.90,
    2: 0.80,
    3: 0.70,
}

PAPER_SPAWN_PROB = {       # probabilità che sia carta (anziché oggetto)
    1: 0.30,
    2: 0.20,
    3: 0.10,
}

TARGET_OBJECTS_PER_STAGE = 10
MAX_PAPER_COUNT = 3        # max 3 pezzi di carta “in tasca”
MIN_DIST_ITEM_FROM_ACTORS = 40  # distanza minima da player/robot allo spawn
MAX_LIVES = 3


# ---------------------------------------------------------------------------
# FUNZIONI DI SUPPORTO
# ---------------------------------------------------------------------------

def compute_shot_target(start, mouse_pos):
    """
    Restituisce il punto finale del colpo:
    - se il mouse è dentro l'area del player -> il cursore
    - altrimenti l'intersezione del segmento start->mouse con il bordo dell'area
    """
    sx, sy = start
    mx, my = mouse_pos

    area = pygame.Rect(PLAYER_AREA_X, PLAYER_AREA_Y, PLAYER_AREA_W, PLAYER_AREA_H)

    # Mouse dentro l'area -> lo usiamo direttamente
    if area.collidepoint(mx, my):
        return float(mx), float(my)

    dx = mx - sx
    dy = my - sy
    if dx == 0 and dy == 0:
        # niente direzione, fallback: resta dov'è
        return float(sx), float(sy)

    candidates = []

    # Intersezione con i lati verticali
    if dx != 0:
        t = (area.left - sx) / dx
        if 0 <= t <= 1:
            y = sy + t * dy
            if area.top <= y <= area.bottom:
                candidates.append((t, area.left, y))

        t = (area.right - sx) / dx
        if 0 <= t <= 1:
            y = sy + t * dy
            if area.top <= y <= area.bottom:
                candidates.append((t, area.right, y))

    # Intersezione con i lati orizzontali
    if dy != 0:
        t = (area.top - sy) / dy
        if 0 <= t <= 1:
            x = sx + t * dx
            if area.left <= x <= area.right:
                candidates.append((t, x, area.top))

        t = (area.bottom - sy) / dy
        if 0 <= t <= 1:
            x = sx + t * dx
            if area.left <= x <= area.right:
                candidates.append((t, x, area.bottom))

    if not candidates:
        # caso limite: clamp del mouse all'interno dell'area
        cx = min(max(mx, area.left), area.right)
        cy = min(max(my, area.top), area.bottom)
        return float(cx), float(cy)

    # prendi l'intersezione "più vicina"
    t_min, px, py = min(candidates, key=lambda c: c[0])
    return float(px), float(py)


def resource_path(relative_path):
    """
    Restituisce il path assoluto a partire dalla posizione di questo file.
    Serve per funzionare sia da .py sia da eseguibile impacchettato.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def load_image(rel_path, use_alpha=True):
    full_path = resource_path(rel_path)
    img = pygame.image.load(full_path)
    if use_alpha:
        return img.convert_alpha()
    else:
        return img.convert()


def load_font(size):
    font_path = resource_path(os.path.join("game_02_media", "VaselineExtra.ttf"))
    return pygame.font.Font(font_path, size)


# ---------------------------------------------------------------------------
# CLASSE PLAYER
# ---------------------------------------------------------------------------

class Player:
    def __init__(self):
        # Carico i 24 frame del personaggio
        self.frames = []
        for i in range(1, 25):
            filename = f"frame_{i:02d}.png"
            self.frames.append(load_image(os.path.join("game_02_media", filename), use_alpha=True))

        # Carico solo i push per 01, 07, 13, 19
        self.push_frames = {}
        for i in (1, 7, 13, 19):
            filename = f"frame_{i:02d}_push.png"
            try:
                self.push_frames[i] = load_image(os.path.join("game_02_media", filename), use_alpha=True)
            except pygame.error:
                # Se per qualche motivo manca, uso il frame normale
                self.push_frames[i] = self.frames[i - 1]

        # Frame corrente (0-23), ma logicamente corrisponde a 1-24
        self.frame_index = 0
        self.image = self.frames[self.frame_index]

        # Posizionamento al centro dell'area di gioco del personaggio
        start_x = PLAYER_AREA_X + PLAYER_AREA_W // 2
        start_y = PLAYER_AREA_Y + PLAYER_AREA_H // 2
        self.rect = self.image.get_rect(center=(start_x, start_y))
        self.mask = pygame.mask.from_surface(self.image)

        # Movimento / animazione
        self.active_key = None           # 'A', 'D', 'W', 'S' oppure None
        self.anim_timer = 0              # per l'intervallo dei 100 ms
        self.finishing_rotation = False  # quando si rilascia A/D e si deve arrivare a 1,7,13,19
        self.rotation_direction = None   # +1 per D, -1 per A
        self.push_active = False         # se sta alternando push / non push
        self.push_base_frame = None      # 1,7,13,19 (numero human-based)
        self.push_axis = None            # 'x' o 'y'
        self.push_sign = 0               # +1 o -1
        self.current_image_is_push = False

    # ----------------------------- UTILITIES -----------------------------

    def _frame_number(self):
        """Restituisce il numero di frame 1..24 corrispondente a frame_index 0..23."""
        return self.frame_index + 1

    def _set_frame_number(self, n):
        """Imposta il frame corrente, n in 1..24."""
        self.frame_index = (n - 1) % 24
        old_center = self.rect.center
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=old_center)
        self.mask = pygame.mask.from_surface(self.image)
        self.current_image_is_push = False

    def _clamp_in_area(self):
        """Mantiene il player dentro l'area 970x970."""
        if self.rect.left < PLAYER_AREA_X:
            self.rect.left = PLAYER_AREA_X
        if self.rect.right > PLAYER_AREA_X + PLAYER_AREA_W:
            self.rect.right = PLAYER_AREA_X + PLAYER_AREA_W
        if self.rect.top < PLAYER_AREA_Y:
            self.rect.top = PLAYER_AREA_Y
        if self.rect.bottom > PLAYER_AREA_Y + PLAYER_AREA_H:
            self.rect.bottom = PLAYER_AREA_Y + PLAYER_AREA_H

    # -------------------------- MOVIMENTO A/D ----------------------------

    def start_move_rotation(self, key):
        """
        Inizio movimento rotazione (A o D).
        Se un altro movimento è attivo, non fa nulla
        (rispetta la regola: nessun tasto contemporaneo).
        """
        if self.active_key is not None:
            return
        if key not in ("A", "D"):
            return

        self.active_key = key
        self.finishing_rotation = False
        self.rotation_direction = 1 if key == "D" else -1
        self.anim_timer = 0

    def stop_move_rotation(self, key):
        """Viene chiamato su KEYUP di A o D."""
        if self.active_key == key:
            # dobbiamo arrivare a frame 1,7,13,19
            self.active_key = None
            self.finishing_rotation = True

    def _step_rotation(self, direction):
        """
        Esegue un singolo step di rotazione (frame successivo o precedente)
        e sposta il personaggio di 20px nelle direzioni definite.
        direction: +1 (D) o -1 (A)
        """
        old_frame_number = self._frame_number()

        # Avanzo/indietreggio il frame
        new_frame_number = ((old_frame_number - 1 + direction) % 24) + 1
        # mantieni il centro
        center = self.rect.center
        self._set_frame_number(new_frame_number)
        self.rect = self.image.get_rect(center=center)

        # Determino il quadrante del frame di partenza (0..3, ogni 6 frame)
        # frame 1-6 -> 0, 7-12 -> 1, 13-18 -> 2, 19-24 -> 3
        quadrant = (old_frame_number - 1) // 6

        if direction == 1:  # D (clockwise)
            # dalla 01 alla 07: +20,+20
            # dalla 07 alla 13: -20,+20
            # dalla 13 alla 19: -20,-20
            # dalla 19 alla 01: +20,-20
            moves = [
                (+PLAYER_STEP, +PLAYER_STEP),
                (-PLAYER_STEP, +PLAYER_STEP),
                (-PLAYER_STEP, -PLAYER_STEP),
                (+PLAYER_STEP, -PLAYER_STEP),
            ]
        else:  # A (counter-clockwise)
            # dalla 01 alla 19: -20,+20
            # dalla 19 alla 13: +20,+20
            # dalla 13 alla 07: +20,-20
            # dalla 07 alla 01: -20,-20
            moves = [
                (-PLAYER_STEP, -PLAYER_STEP),
                (+PLAYER_STEP, -PLAYER_STEP),
                (+PLAYER_STEP, +PLAYER_STEP),
                (-PLAYER_STEP, +PLAYER_STEP),
            ]

        dx, dy = moves[quadrant]

        # Applico lo spostamento, rispettando i bordi
        self.rect.x += dx
        self.rect.y += dy
        self._clamp_in_area()

    def _rotation_on_idle(self):
        """
        Dopo il rilascio di A/D, continuiamo a ruotare
        finché non arriviamo ai frame 1,7,13,19.
        """
        if not self.finishing_rotation or self.rotation_direction is None:
            return

        # se siamo già in 1,7,13,19, stop
        if (self._frame_number() - 1) % 6 == 0:
            self.finishing_rotation = False
            self.rotation_direction = None
            return

        # altrimenti facciamo un altro step
        self._step_rotation(self.rotation_direction)

        # ricontrollo se siamo arrivati
        if (self._frame_number() - 1) % 6 == 0:
            self.finishing_rotation = False
            self.rotation_direction = None

    # -------------------------- MOVIMENTO W/S (PUSH) ---------------------

    def start_push(self, key):
        """
        Inizio del movimento push con W o S.
        Usa solo i frame base 1,7,13,19 per le versioni _push.
        Se è attivo un altro movimento non fa nulla.
        """
        if self.active_key is not None or self.finishing_rotation:
            return
        if key not in ("W", "S"):
            return

        # Trovo il frame base più vicino tra 1,7,13,19
        current = self._frame_number()
        base_candidates = [1, 7, 13, 19]
        base = min(base_candidates, key=lambda b: min((current - b) % 24, (b - current) % 24))

        self.push_base_frame = base
        self._set_frame_number(base)
        self.active_key = key
        self.push_active = True
        self.anim_timer = 0
        self.current_image_is_push = False

        # Direzione a seconda del frame base e del tasto
        # W: "spinge"
        # S: "tira" (direzione invertita)
        if base == 1:
            axis = 'y'
            sign = -1  # immagine 01 --> -20px lungo l'asse y
        elif base == 7:
            axis = 'x'
            sign = +1  # immagine 07 --> +20px lungo l'asse X
        elif base == 13:
            axis = 'y'
            sign = +1  # immagine 13 --> +20px lungo l'asse y
        elif base == 19:
            axis = 'x'
            sign = -1  # immagine 19 --> -20px lungo l'asse X
        else:
            axis = 'y'
            sign = 0

        if key == "S":
            sign = -sign

        self.push_axis = axis
        self.push_sign = sign

    def stop_push(self, key):
        """
        KEYUP di W o S.
        L'animazione continua fino al frame senza push.
        """
        if self.active_key == key:
            # non disattiviamo subito: lasciamo che l'update
            # faccia ancora un toggle se serve per tornare all'immagine non push
            self.active_key = None
            # se stiamo su un frame push, lasciamo che il prossimo step
            # ci riporti alla versione senza push

    def _step_push(self):
        """
        Un singolo step di push: alterna tra frame normale e frame _push,
        e sposta il personaggio di 20px lungo l'asse definito.
        """
        # Toggle immagine
        frame_num = self.push_base_frame
        center = self.rect.center

        if self.current_image_is_push:
            # torna a immagine normale
            self.image = self.frames[frame_num - 1]
            self.current_image_is_push = False
        else:
            # passa alla versione push
            push_img = self.push_frames.get(frame_num, self.frames[frame_num - 1])
            self.image = push_img
            self.current_image_is_push = True

        self.rect = self.image.get_rect(center=center)
        self.mask = pygame.mask.from_surface(self.image)

        # Spostamento di 20px lungo l'asse definito
        if self.push_axis == 'x':
            self.rect.x += self.push_sign * PLAYER_STEP
        elif self.push_axis == 'y':
            self.rect.y += self.push_sign * PLAYER_STEP

        self._clamp_in_area()

        # Se non c'è più un tasto W/S attivo e abbiamo appena messo
        # l'immagine NON push, possiamo fermare l'animazione
        if self.active_key is None and not self.current_image_is_push:
            self.push_active = False
            self.push_base_frame = None
            self.push_axis = None
            self.push_sign = 0

    # -------------------------- UPDATE GENERALE --------------------------

    def update(self, dt):
        """
        dt in millisecondi.
        Gestisce il timing delle animazioni (A/D/W/S).
        """
        self.anim_timer += dt

        # -----------------------------------------------------------------
        # NESSUN TASTO ATTIVO
        # -----------------------------------------------------------------
        if self.active_key is None:
            # 1) Rotazione: dopo il rilascio di A/D dobbiamo arrivare a 1/7/13/19
            if self.finishing_rotation:
                if self.anim_timer >= PLAYER_ANIM_INTERVAL:
                    self.anim_timer -= PLAYER_ANIM_INTERVAL
                    self._rotation_on_idle()

            # 2) Push: tasto W/S rilasciato ma animazione push ancora "aperta"
            elif self.push_active:
                if not self.current_image_is_push:
                    # Siamo già sull'immagine base (non push):
                    # utente ha rilasciato troppo in fretta o abbiamo già chiuso.
                    # Spegniamo lo stato push.
                    self.push_active = False
                    self.push_base_frame = None
                    self.push_axis = None
                    self.push_sign = 0
                elif self.anim_timer >= PLAYER_ANIM_INTERVAL:
                    # Siamo rimasti bloccati su un frame push:
                    # facciamo un ultimo step per tornare all'immagine normale.
                    self.anim_timer -= PLAYER_ANIM_INTERVAL
                    self._step_push()
                    # Se dopo questo step siamo su immagine non push e active_key è None,
                    # _step_push() stessa azzera push_active / push_base_frame / push_axis / push_sign

            return

        # -----------------------------------------------------------------
        # C'È UN TASTO ATTIVO (A/D/W/S)
        # -----------------------------------------------------------------
        if self.anim_timer < PLAYER_ANIM_INTERVAL:
            return
        self.anim_timer -= PLAYER_ANIM_INTERVAL

        if self.active_key in ("A", "D"):
            direction = 1 if self.active_key == "D" else -1
            self._step_rotation(direction)
        elif self.active_key in ("W", "S"):
            self._step_push()

# ---------------------------------------------------------------------------
# CLASSE ROBOT
# ---------------------------------------------------------------------------

class Robot:
    """
    Robot aspirapolvere (roomba):
    - si muove nello spazio 1116x1058 a partire da (354,22)
    - parte da (1370,980) con rotazione 0° e direzione verso nord
    - velocità costante in modulo, dipende dallo stage
    - quando tocca un bordo si ferma e ruota di un angolo casuale [-135°, +135°]
      alla velocità di 45°/s, poi riprende a muoversi.
    """

    def __init__(self, stage, sound_spin, sound_wrong):

        self.sound_spin = sound_spin
        self.sound_wrong = sound_wrong

        # immagine di base (orientata "verso nord" nello sprite)
        self.base_image = load_image(os.path.join("game_02_media", "roomba.png"), use_alpha=True)
        self.image = self.base_image

        # posizione (usiamo float per la fisica)
        self.x = float(ROBOT_START_X)
        self.y = float(ROBOT_START_Y)
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.mask = pygame.mask.from_surface(self.image)

        # angolo in gradi: 0° = NORD (verso l'alto),
        # positivo = rotazione in senso orario (verso EST, SUD, OVEST)
        self.angle = 0.0

        # velocità
        self.speed = self._speed_for_stage(stage)
        self.vx, self.vy = self._compute_velocity()

        # modalità: 'move' (si sposta) oppure 'rotate' (ruota sul posto)
        self.mode = "move"
        self.rotation_dir = 0       # +1 o -1
        self.rotation_left = 0.0    # gradi ancora da ruotare

        # bordo su cui ha urtato (serve per evitare rotazioni che puntano ancora verso il bordo)
        self.last_hit_edges = {
            "left": False,
            "right": False,
            "top": False,
            "bottom": False,
        }
        # tempo residuo di spin (quando viene colpito dalla carta)
        self.spin_time_left = 0.0


    def start_spin(self):
        """Entra in modalità spin dopo aver toccato la carta."""
        # Se è già in spin, non riavviare il suono
        if self.mode == "spin":
            return

        self.mode = "spin"
        self.spin_time_left = ROBOT_SPIN_DURATION
        self.vx = 0.0
        self.vy = 0.0

        # Avvia suono spin in loop
        self.sound_spin.play(loops=-1)

    def _update_spin(self, dt_ms, stage):
        dt = dt_ms / 1000.0
        step = ROBOT_SPIN_SPEED * dt  # 180°/s come da specifiche
        self.angle = (self.angle + step) % 360.0
        self.spin_time_left -= dt
        self._update_rect_from_pos()

        if self.spin_time_left <= 0:
            self.spin_time_left = 0

            # Stop suono spin
            self.sound_spin.stop()

            # riprende a muoversi nella direzione dell'angolo attuale
            self.speed = self._speed_for_stage(stage)
            self.vx, self.vy = self._compute_velocity()
            self.mode = "move"


    # --------------------------- UTILITIES --------------------------------

    def _speed_for_stage(self, stage):
        return ROBOT_SPEED_STAGE.get(stage, ROBOT_SPEED_STAGE[1])

    def _compute_velocity(self):
        """
        Calcola le componenti vx, vy a partire da self.angle e self.speed.
        0° = nord (verso l'alto), asse Y cresce verso il basso.
        vx = speed * sin(angle)
        vy = -speed * cos(angle)
        """
        rad = math.radians(self.angle)
        vx = self.speed * math.sin(rad)
        vy = -self.speed * math.cos(rad)
        return vx, vy

    def _update_rect_from_pos(self):
        """Aggiorna image e rect in base a x, y e angle."""
        # pygame ruota in senso antiorario, noi abbiamo angolo orario -> usiamo -angle
        rotated = pygame.transform.rotate(self.base_image, -self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        self.image = rotated
        self.rect = rect
        self.mask = pygame.mask.from_surface(self.image)

    def ensure_speed_for_stage(self, stage):
        """Se cambia stage, adegua il modulo della velocità mantenendo la direzione."""
        new_speed = self._speed_for_stage(stage)
        if abs(new_speed - self.speed) < 1e-6:
            return

        if self.speed != 0:
            scale = new_speed / self.speed
            self.vx *= scale
            self.vy *= scale
        else:
            # se per qualche motivo speed era 0, ricalcolo da angolo
            self.vx, self.vy = self._compute_velocity()

        self.speed = new_speed

    def reset_for_stage(self, stage):
        """
        Per dopo: quando cambieremo stage o quando il giocatore perde una vita.
        (Non ancora usata in questo step, ma pronta.)
        """
        self.x = float(ROBOT_START_X)
        self.y = float(ROBOT_START_Y)
        self.angle = 0.0
        self.speed = self._speed_for_stage(stage)
        self.vx, self.vy = self._compute_velocity()
        self.mode = "move"
        self.rotation_dir = 0
        self.rotation_left = 0.0
        self.last_hit_edges = {"left": False, "right": False, "top": False, "bottom": False}
        self._update_rect_from_pos()

    # ------------------------ LOGICA DI MOVIMENTO -------------------------

    def _update_move(self, dt_ms):
        """Aggiorna la posizione quando il robot è in modalità 'move'."""
        dt = dt_ms / 1000.0

        # spostamento
        self.x += self.vx * dt
        self.y += self.vy * dt
        self._update_rect_from_pos()

        # controllo bordi dell'area del robot
        hit_left = self.rect.left <= ROBOT_AREA_X
        hit_right = self.rect.right >= ROBOT_AREA_X + ROBOT_AREA_W
        hit_top = self.rect.top <= ROBOT_AREA_Y
        hit_bottom = self.rect.bottom >= ROBOT_AREA_Y + ROBOT_AREA_H

        if hit_left or hit_right or hit_top or hit_bottom:
            # clamp alla zona
            if hit_left:
                self.rect.left = ROBOT_AREA_X
            if hit_right:
                self.rect.right = ROBOT_AREA_X + ROBOT_AREA_W
            if hit_top:
                self.rect.top = ROBOT_AREA_Y
            if hit_bottom:
                self.rect.bottom = ROBOT_AREA_Y + ROBOT_AREA_H

            # aggiorno x,y con il centro clampato
            self.x, self.y = self.rect.center

            # avvia logica di rotazione rispetto ai bordi
            self._start_border_rotation(hit_top, hit_right, hit_bottom, hit_left)

    def _angle_in_range_for_edge(self, deg, edge):
        """
        Ritorna True se l'angolo assoluto `deg` (0-359) è nel range ammesso
        per il bordo indicato, secondo le specifiche:
        - bordo superiore: 100°–260°
        - bordo destro:    190°–350°
        - bordo inferiore: 280°–80°  (wrap)
        - bordo sinistro:  10°–170°
        """
        if edge == "top":
            return 100 <= deg <= 260
        elif edge == "right":
            return 190 <= deg <= 350
        elif edge == "bottom":
            return deg >= 280 or deg <= 80
        elif edge == "left":
            return 10 <= deg <= 170
        return True

    def _start_border_rotation(self, hit_top, hit_right, hit_bottom, hit_left):
        """
        Gestisce l'innesco della rotazione quando il robot tocca un bordo.

        Logica:
        - per ogni bordo TOCCATO si guarda l'angolo relativo alla perpendicolare;
          se è già tra 100° e 260° NON si ruota rispetto a quel bordo
        - se per TUTTI i bordi toccati l'angolo relativo è 100°–260°, nessuna rotazione
        - altrimenti si sceglie un nuovo angolo assoluto:
            * sempre in senso orario
            * compreso nei range ammessi per tutti i bordi VICINI (toccati o entro 50px),
              usando l'intersezione dei range (gestisce correttamente gli angoli).
        """
        # bordi toccati
        touched_edges = []
        if hit_top:
            touched_edges.append("top")
        if hit_right:
            touched_edges.append("right")
        if hit_bottom:
            touched_edges.append("bottom")
        if hit_left:
            touched_edges.append("left")

        if not touched_edges:
            return

        # perpendicolari dei bordi
        perp_map = {
            "top": 0.0,
            "right": 90.0,
            "bottom": 180.0,
            "left": 270.0,
        }

        angle = self.angle % 360.0

        # angolo relativo 0-360 rispetto alla perpendicolare del bordo
        def rel_phi(a, perp):
            return (a - perp + 360.0) % 360.0

        # Verifica se è necessario ruotare:
        # se per TUTTI i bordi toccati l'angolo relativo è tra 100° e 260°
        # NON ruotiamo (il robot va già via dal bordo).
        need_rotation = False
        for edge in touched_edges:
            perp = perp_map[edge]
            phi = rel_phi(angle, perp)
            # "vicino" alla perpendicolare: fuori da (100,260)
            if not (100.0 < phi < 260.0):
                need_rotation = True
                break

        if not need_rotation:
            # Già orientato in modo divergente rispetto a tutti i bordi toccati.
            # Nessuna rotazione: continuiamo in movimento.
            return

        # Costruisco l'insieme dei bordi "vicini" (toccati o entro 50px)
        NEAR_TOL = 50
        near_edges = set(touched_edges)

        # distanza dai bordi
        dist_top = self.rect.top - ROBOT_AREA_Y
        dist_left = self.rect.left - ROBOT_AREA_X
        dist_bottom = (ROBOT_AREA_Y + ROBOT_AREA_H) - self.rect.bottom
        dist_right = (ROBOT_AREA_X + ROBOT_AREA_W) - self.rect.right

        if dist_top <= NEAR_TOL:
            near_edges.add("top")
        if dist_right <= NEAR_TOL:
            near_edges.add("right")
        if dist_bottom <= NEAR_TOL:
            near_edges.add("bottom")
        if dist_left <= NEAR_TOL:
            near_edges.add("left")

        # Maschera di angoli ammessi 0-359.
        # Per ogni bordo vicino, restringiamo il range (intersezione).
        allowed = [True] * 360
        for edge in near_edges:
            for deg in range(360):
                if not self._angle_in_range_for_edge(deg, edge):
                    allowed[deg] = False

        candidates = [deg for deg in range(360) if allowed[deg]]

        if not candidates:
            # In teoria non dovrebbe succedere, ma in caso limite
            # non facciamo ruotare il robot.
            return

        # scegliamo un angolo target casuale tra quelli ammessi
        target_angle = float(random.choice(candidates))

        # Rotazione sempre in senso orario: delta tra angolo corrente e target
        cw_delta = (target_angle - angle) % 360.0
        if cw_delta == 0.0:
            # se per qualche motivo è 0, non ha senso ruotare
            return

        self.rotation_dir = 1      # sempre orario
        self.rotation_left = cw_delta
        self.mode = "rotate"
        self.vx = 0.0
        self.vy = 0.0

    def _update_rotate(self, dt_ms, stage):
        """Aggiorna l'angolo quando il robot è in modalità 'rotate'."""
        dt = dt_ms / 1000.0
        step = ROBOT_ROT_SPEED * dt

        if step > self.rotation_left:
            step = self.rotation_left

        self.rotation_left -= step
        self.angle = (self.angle + self.rotation_dir * step) % 360.0

        # durante la rotazione il centro non cambia
        self._update_rect_from_pos()

        if self.rotation_left <= 0.0:
            # ho finito la rotazione: calcolo il nuovo vettore velocità
            self.rotation_left = 0.0
            self.angle = self.angle % 360.0
            self.speed = self._speed_for_stage(stage)
            self.vx, self.vy = self._compute_velocity()
            self.mode = "move"

    # ------------------------------ UPDATE / DRAW -------------------------

    def update(self, dt_ms, stage):
        """Update generale chiamato dal main."""
        # Se cambia stage, adeguo la velocità
        self.ensure_speed_for_stage(stage)

        if self.mode == "move":
            self._update_move(dt_ms)
        elif self.mode == "rotate":
            self._update_rotate(dt_ms, stage)
        elif self.mode == "spin":
            self._update_spin(dt_ms, stage)
        else:
            # fallback: trattalo come move
            self._update_move(dt_ms)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# ---------------------------------------------------------------------------
# CLASSE ITEM (oggetto o carta)
# ---------------------------------------------------------------------------

class Item:
    def __init__(self, image, kind, x, y):
        """
        kind: "object" oppure "paper"
        """
        self.image = image
        self.kind = kind
        self.rect = self.image.get_rect(topleft=(x, y))
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# ---------------------------------------------------------------------------
# CLASSE PAPERSHOT 
# ---------------------------------------------------------------------------

class PaperShot:
    def __init__(self, image, start_pos, target_pos, speed):
        self.image = image
        self.x, self.y = start_pos
        self.tx, self.ty = target_pos
        self.speed = speed

        dx = self.tx - self.x
        dy = self.ty - self.y
        length = math.hypot(dx, dy)
        if length == 0:
            dx, dy = 0, -1
            length = 1.0

        self.vx = self.speed * (dx / length)
        self.vy = self.speed * (dy / length)

        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt_ms):
        """
        Muove il colpo.
        Ritorna True se ha raggiunto (o superato) il target.
        """
        dt = dt_ms / 1000.0
        old_x, old_y = self.x, self.y

        self.x += self.vx * dt
        self.y += self.vy * dt

        self.rect.center = (int(self.x), int(self.y))

        # Controllo se abbiamo passato il target (prodotto scalare)
        ox, oy = old_x, old_y
        tx, ty = self.tx, self.ty
        nx, ny = self.x, self.y

        vx1, vy1 = tx - ox, ty - oy
        vx2, vy2 = tx - nx, ty - ny

        if vx1 * vx2 + vy1 * vy2 <= 0:
            # abbiamo raggiunto/superato il target: clamp e segnala "arrivato"
            self.x, self.y = tx, ty
            self.rect.center = (int(tx), int(ty))
            return True

        return False

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# ---------------------------------------------------------------------------
# CLASSE POPUP MESSAGGI
# ---------------------------------------------------------------------------

class PopupMessage:
    def __init__(self, text, font, color, center_x, base_y, delay=0.0):
        self.text = text
        self.font = font
        self.color = color

        # posizione finale e di partenza (parte più in basso e sale)
        self.center_x = center_x
        self.base_y = base_y           # y finale
        self.start_y = base_y + 80     # parte più giù di 80px

        # tempi (in secondi)
        self.total_time = 1.5          # durata animazione VISIBILE
        self.fade_in_time = 0.3
        self.fade_out_time = 0.5

        # delay iniziale prima di far partire il popup
        self.delay = delay

        self.elapsed = 0.0

        # surface del testo (VaselineExtra, colore passato)
        self.surface = self.font.render(self.text, True, self.color)
        self.rect = self.surface.get_rect(center=(self.center_x, self.start_y))
        self.alpha = 0

    def update(self, dt_ms):
        """Aggiorna posizione e alpha. Ritorna False quando è da rimuovere."""
        self.elapsed += dt_ms / 1000.0
        t = self.elapsed

        # Se siamo ancora nel delay iniziale, tienilo invisibile fermo in basso
        if t < self.delay:
            self.alpha = 0
            self.rect.center = (self.center_x, int(self.start_y))
            return True

        # tempo locale dell'animazione dopo il delay
        local_t = t - self.delay

        if local_t >= self.total_time:
            return False

        # movimento dal basso verso l'alto
        progress = min(1.0, local_t / self.total_time)
        y = self.start_y + (self.base_y - self.start_y) * progress
        self.rect.center = (self.center_x, int(y))

        # fade in / fade out
        if local_t < self.fade_in_time:
            # fade in
            self.alpha = int(255 * (local_t / self.fade_in_time))
        elif local_t > self.total_time - self.fade_out_time:
            # fade out
            remaining = self.total_time - local_t
            self.alpha = int(255 * max(0.0, remaining / self.fade_out_time))
        else:
            self.alpha = 255

        return True

    def draw(self, surface):
        surf = self.surface.copy()
        surf.set_alpha(self.alpha)
        surface.blit(surf, self.rect)


# ---------------------------------------------------------------------------
# FUNZIONE PRINCIPALE
# ---------------------------------------------------------------------------

def main():
    # ------------------ parsing argomenti (best_score) -------------------
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--score", type=int, default=0)
    args, unknown = parser.parse_known_args()
    best_score = args.score

    # ----------------------------- pygame init ---------------------------
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode(
        (INTERNAL_WIDTH, INTERNAL_HEIGHT),
        pygame.FULLSCREEN | pygame.SCALED
    )
    pygame.display.set_caption("Jac n Roll - game_02_roll")

    clock = pygame.time.Clock()


    # ---------------------------- CARICAMENTO ASSET ----------------------
    # Backgrounds
    bkg_menu = load_image(os.path.join("game_02_media", "bkg_menu.png"))
    bkg_istruzioni = load_image(os.path.join("game_02_media", "bkg_istruzioni.png"))
    bkg_gioco = load_image(os.path.join("game_02_media", "bkg_gioco.png"))

    # Backgrounds
    bkg_menu = load_image(os.path.join("game_02_media", "bkg_menu.png"))
    bkg_istruzioni = load_image(os.path.join("game_02_media", "bkg_istruzioni.png"))
    bkg_gioco = load_image(os.path.join("game_02_media", "bkg_gioco.png"))

    # Oggetti e carta
    object_images = [
        load_image(os.path.join("game_02_media", "oggetto_01.png")),
        load_image(os.path.join("game_02_media", "oggetto_02.png")),
        load_image(os.path.join("game_02_media", "oggetto_03.png")),
        load_image(os.path.join("game_02_media", "oggetto_04.png")),
    ]
    paper_image = load_image(os.path.join("game_02_media", "carta.png"))

    # Cuore vite
    heart_image = load_image(os.path.join("game_02_media", "heart.png"))

    # Fonts
    font_menu = load_font(70)
    font_stage = load_font(60)
    font_game_over = load_font(90)
    font_game_over_small = load_font(60)

    # Musiche
    music_menu_path = resource_path(os.path.join("game_02_media", "music_menu.mp3"))
    music_game_path = resource_path(os.path.join("game_02_media", "music_game.mp3"))

    # Suoni singoli
    sound_bell = pygame.mixer.Sound(resource_path(os.path.join("game_02_media", "sound_bell.mp3")))
    sound_spin = pygame.mixer.Sound(resource_path(os.path.join("game_02_media", "sound_spin.mp3")))
    sound_wrong = pygame.mixer.Sound(resource_path(os.path.join("game_02_media", "sound_wrong.mp3")))
    sound_stage = pygame.mixer.Sound(resource_path(os.path.join("game_02_media", "sound_stage.mp3")))

    # Volume (opzionale)
    sound_bell.set_volume(0.9)
    sound_spin.set_volume(0.9)
    sound_wrong.set_volume(0.9)
    sound_stage.set_volume(0.9)


    def play_menu_music():
        pygame.mixer.music.load(music_menu_path)
        pygame.mixer.music.set_volume(0.85)
        pygame.mixer.music.play(-1)

    def play_game_music():
        pygame.mixer.music.load(music_game_path)
        pygame.mixer.music.set_volume(0.85)
        pygame.mixer.music.play(-1)

    def stop_music():
        pygame.mixer.music.stop()

    # ---------------------------- MENU: setup testi ----------------------
    menu_items = ["NUOVA PARTITA", "ISTRUZIONI", "ESCI"]

    def build_menu_surfaces(mouse_pos):
        """Ritorna lista di (surface, rect, label) con hover gestito."""
        items = []
        mid_x = INTERNAL_WIDTH // 2
        # Partiamo da metà schermo in verticale
        start_y = INTERNAL_HEIGHT // 2
        spacing = 100

        for idx, label in enumerate(menu_items):
            y = start_y + idx * spacing
            # testo provvisorio per avere il rect al centro
            text_surface = font_menu.render(label, True, VIOLA)
            rect = text_surface.get_rect(center=(mid_x, y))

            if rect.collidepoint(mouse_pos):
                color = BIANCO
            else:
                color = VIOLA

            text_surface = font_menu.render(label, True, color)
            rect = text_surface.get_rect(center=(mid_x, y))
            items.append((text_surface, rect, label))

        return items

    # ---------------------------- STATO INIZIALE -------------------------
    state = STATE_MENU
    play_menu_music()

    # Oggetto player (solo durante il gioco)
    player = None

    # Stage corrente (solo struttura per ora)
    current_stage = 1

    # Oggetto robot
    robot = None

    # Lista degli item (oggetti + carta)
    items = []

    # Contatori
    objects_collected = 0
    paper_collected = 0

    # Vite
    lives = MAX_LIVES

    # colpi carta
    paper_shots = []

    # Lista popup messaggi
    popup_messages = []

    # Timer per spawn oggetti
    spawn_timer = 0.0  # in secondi

    # Per gestione game over (da completare negli step successivi)
    last_completed_stage = 0

    def spawn_random_item():
        """
        Gestisce la logica di:
        - timer basato su OBJECT_SPAWN_INTERVAL
        - probabilità di comparsa oggetto/carta
        - scelta posizione casuale nello spazio del player
        - distanza minima da player e robot
        Restituisce un Item o None.
        """
        nonlocal current_stage, player, robot

        interval = OBJECT_SPAWN_INTERVAL.get(current_stage, 5.0)
        prob_obj = OBJECT_SPAWN_PROB.get(current_stage, 0.8)
        prob_paper = PAPER_SPAWN_PROB.get(current_stage, 0.25)

        # Tiro: compare qualcosa?
        if random.random() > prob_obj:
            return None

        # È carta?
        is_paper = (random.random() < prob_paper)

        if is_paper:
            img = paper_image
            kind = "paper"
        else:
            img = random.choice(object_images)
            kind = "object"

        iw, ih = img.get_width(), img.get_height()

        # range coordinate dentro area player, tenendo conto delle dimensioni
        min_x = PLAYER_AREA_X
        max_x = PLAYER_AREA_X + PLAYER_AREA_W - iw
        min_y = PLAYER_AREA_Y
        max_y = PLAYER_AREA_Y + PLAYER_AREA_H - ih

        if max_x < min_x or max_y < min_y:
            return None  # area troppo piccola (non dovrebbe mai accadere)

        # fino a N tentativi per trovare una posizione valida
        for _ in range(50):
            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)

            # distanza minima da player e robot
            ok = True
            cx_item = x + iw / 2
            cy_item = y + ih / 2

            if player is not None:
                cx_p, cy_p = player.rect.center
                if math.hypot(cx_item - cx_p, cy_item - cy_p) < MIN_DIST_ITEM_FROM_ACTORS:
                    ok = False

            if ok and robot is not None:
                cx_r, cy_r = robot.rect.center
                if math.hypot(cx_item - cx_r, cy_item - cy_r) < MIN_DIST_ITEM_FROM_ACTORS:
                    ok = False

            if ok:
                return Item(img, kind, x, y)

        return None  # non trovata posizione valida

    def add_popup(text, delay=0.0):
        """Crea un popup centrale in basso, viola, con font Vaseline."""
        center_x = INTERNAL_WIDTH // 2
        base_y = INTERNAL_HEIGHT - 200   # posizione finale (un po' sopra il bordo basso)
        popup_messages.append(
            PopupMessage(text, font_stage, VIOLA, center_x, base_y, delay=delay)
        )


    # --------------------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------------------
    running = True
    while running:
        dt = clock.tick(60)  # ms
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # ---------------------- EVENTI MENU --------------------------
            if state == STATE_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # click sinistro
                    for surf, rect, label in build_menu_surfaces(mouse_pos):
                        if rect.collidepoint(event.pos):
                            if label == "NUOVA PARTITA":
                                # Avvia il gioco
                                stop_music()
                                play_game_music()
                                state = STATE_PLAYING
                                current_stage = 1
                                last_completed_stage = 0
                                player = Player()
                                robot = Robot(current_stage, sound_spin, sound_wrong)
                                sound_stage.play()
                                items.clear()
                                paper_shots.clear() 
                                objects_collected = 0
                                paper_collected = 0
                                spawn_timer = 0.0
                                lives = MAX_LIVES
                                popup_messages.clear()
                            elif label == "ISTRUZIONI":
                                state = STATE_INSTRUCTIONS
                            elif label == "ESCI":
                                running = False

            # ------------------- EVENTI ISTRUZIONI -----------------------
            elif state == STATE_INSTRUCTIONS:
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    # Ritorno al menu, la musica non cambia
                    state = STATE_MENU

            # ---------------------- EVENTI GIOCO -------------------------
            elif state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Torna al menu
                        stop_music()
                        play_menu_music()
                        state = STATE_MENU
                        player = None
                        robot = None
                        popup_messages.clear()
                    elif event.key == pygame.K_SPACE:
                         # Lancia una pallina di carta verso il mouse
                         if paper_collected > 0 and player is not None:
                             mx, my = pygame.mouse.get_pos()
                             cx, cy = player.rect.center
                             target_x, target_y = compute_shot_target((cx, cy), (mx, my))

                             shot = PaperShot(
                                 paper_image,
                                 (float(cx), float(cy)),
                                 (target_x, target_y),
                                 PAPER_SHOT_SPEED,
                             )
                             paper_shots.append(shot)
                             paper_collected = max(0, paper_collected - 1)  # scala contatore carta
                    elif event.key == pygame.K_a:
                        player.start_move_rotation("A")
                    elif event.key == pygame.K_d:
                        player.start_move_rotation("D")
                    elif event.key == pygame.K_w:
                        player.start_push("W")
                    elif event.key == pygame.K_s:
                        player.start_push("S")

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        player.stop_move_rotation("A")
                    elif event.key == pygame.K_d:
                        player.stop_move_rotation("D")
                    elif event.key == pygame.K_w:
                        player.stop_push("W")
                    elif event.key == pygame.K_s:
                        player.stop_push("S")

            # ------------------- EVENTI GAME OVER ------------------------
            elif state == STATE_GAME_OVER:
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    # Torna al menu, riparte musica menu
                    stop_music()
                    play_menu_music()
                    state = STATE_MENU

        # ----------------------------------------------------------------
        # UPDATE LOGICO
        # ----------------------------------------------------------------
        if state == STATE_PLAYING:
            if player is not None:
                player.update(dt)
            if robot is not None:
                robot.update(dt, current_stage)

            # Gestione timer di spawn oggetti / carta
            spawn_timer += dt / 1000.0
            interval = OBJECT_SPAWN_INTERVAL.get(current_stage, 5.0)
            if spawn_timer >= interval:
                spawn_timer -= interval
                new_item = spawn_random_item()
                if new_item is not None:
                    items.append(new_item)

            # Collisioni player con oggetti / carta (pixel-perfect)
            if player is not None and player.mask is not None:
                for item in items[:]:
                    offset = (item.rect.x - player.rect.x, item.rect.y - player.rect.y)
                    if player.mask.overlap(item.mask, offset):
                        if item.kind == "object":
                            objects_collected += 1
                            add_popup("+1 oggetto!")
                        elif item.kind == "paper":
                            # raccolta carta, massimo 3
                            if paper_collected < MAX_PAPER_COUNT:
                                paper_collected += 1
                                add_popup("Carta raccolta!")
                        # Suono raccolta
                        sound_bell.play()
                        items.remove(item)

            # Collisioni robot con oggetti e carta a terra
            if robot is not None and robot.mask is not None:
                for item in items[:]:
                    offset = (item.rect.x - robot.rect.x, item.rect.y - robot.rect.y)
                    if robot.mask.overlap(item.mask, offset):
                        if item.kind == "object":
                            # Suono "errore": il robot ha mangiato un oggetto
                            sound_wrong.play()
                            # Il robot aspira l'oggetto: sparisce
                            items.remove(item)
                        elif item.kind == "paper":
                            # Carta -> modalità spin
                            robot.start_spin()
                            items.remove(item)

            # Collisione player-robot (pixel-perfect) -> perdita vita / game over
            if player is not None and robot is not None:
                offset_pr = (robot.rect.x - player.rect.x, robot.rect.y - player.rect.y)
            if player is not None and robot is not None:
                offset_pr = (robot.rect.x - player.rect.x, robot.rect.y - player.rect.y)
                if player.mask.overlap(robot.mask, offset_pr):
                    lives -= 1
                    if lives <= 0:
                        # Game over per esaurimento vite
                        state = STATE_GAME_OVER
                        if last_completed_stage > best_score:
                            best_score = last_completed_stage
                    else:
                        # Se restiamo con 1 sola vita -> popup "Ultima vita!"
                        if lives == 1:
                            add_popup("Ultima vita!")

                        # Perdita vita: reset di player e robot, ma NON azzeriamo oggetti/carta
                        player = Player()
                        robot.reset_for_stage(current_stage)

            # Avanzamento stage quando raccolgo abbastanza oggetti
            if objects_collected >= TARGET_OBJECTS_PER_STAGE:
                # Stage completato
                last_completed_stage = current_stage

                if current_stage < 3:
                    # Passa allo stage successivo
                    current_stage += 1
                    objects_collected = 0
                    items.clear()
                    spawn_timer = 0.0

                    # Reset di player e robot per il nuovo stage
                    player = Player()
                    robot.reset_for_stage(current_stage)
                    sound_stage.play()

                    # Popup "Stage 2!" o "Stage 3!" dopo 1 secondo
                    add_popup(f"Stage {current_stage}!", delay=1.0)
                else:
                    # Hai completato lo stage 3: vittoria -> GAME OVER "positivo"
                    state = STATE_GAME_OVER
                    if last_completed_stage > best_score:
                        best_score = last_completed_stage

            # Aggiorna palline di carta
            for shot in paper_shots[:]:
                arrived = shot.update(dt)
                if arrived:
                    # Quando arriva al target, diventa un pezzo di carta per terra
                    items.append(Item(paper_image, "paper", shot.rect.x, shot.rect.y))
                    paper_shots.remove(shot)
                else:
                    # se per qualche motivo esce dall'area di gioco, la eliminiamo
                    if (shot.rect.right < PLAYER_AREA_X or
                        shot.rect.left > PLAYER_AREA_X + PLAYER_AREA_W or
                        shot.rect.bottom < PLAYER_AREA_Y or
                        shot.rect.top > PLAYER_AREA_Y + PLAYER_AREA_H):
                        paper_shots.remove(shot)

            # Aggiorna popup
            for msg in popup_messages[:]:
                if not msg.update(dt):
                    popup_messages.remove(msg)


        # ----------------------------------------------------------------
        # DISEGNO
        # ----------------------------------------------------------------
        if state == STATE_MENU:
            screen.blit(bkg_menu, (0, 0))
            for surf, rect, label in build_menu_surfaces(mouse_pos):
                screen.blit(surf, rect)

        elif state == STATE_INSTRUCTIONS:
            screen.blit(bkg_istruzioni, (0, 0))

        elif state == STATE_PLAYING:
            screen.blit(bkg_gioco, (0, 0))

            # Disegno item (oggetti + carta)
            for item in items:
                item.draw(screen)

            # Palline di carta in volo
            for shot in paper_shots:
                shot.draw(screen)

            # Robot
            if robot is not None:
                robot.draw(screen)

            # Personaggio
            if player is not None:
                screen.blit(player.image, player.rect)

            # Scritta "Stage n"
            text_stage = font_stage.render(f"Stage {current_stage}", True, BIANCO)
            screen.blit(text_stage, (46, 63))

            # Vite (3 cuori all'inizio)
            # coordinate indicative (adatta se hai segnaposto precisi nel bkg)
            if lives >= 1:
                screen.blit(heart_image, (15, 174))
            if lives >= 2:
                screen.blit(heart_image, (116, 174))
            if lives >= 3:
                screen.blit(heart_image, (217, 174))

            # Contatore oggetti "x/10" a (121,345)
            text_objs = font_stage.render(f"{objects_collected}/{TARGET_OBJECTS_PER_STAGE}", True, BIANCO)
            screen.blit(text_objs, (121, 345))

            # Contatore carta (0..3) a (1738,931)
            text_paper = font_stage.render(str(paper_collected), True, BIANCO)
            screen.blit(text_paper, (1738, 931))

            # Popup messaggi
            for msg in popup_messages:
                msg.draw(screen)

        elif state == STATE_GAME_OVER:
            screen.blit(bkg_menu, (0, 0))
            text_go = font_game_over.render("GAME OVER", True, VIOLA)
            rect_go = text_go.get_rect(center=(INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2 - 40))
            screen.blit(text_go, rect_go)

            if last_completed_stage > 0:
                msg = f"Complimenti, hai completato {last_completed_stage} stage"
            else:
                msg = "Non hai completato il primo stage, riprova!"

            text_msg = font_game_over_small.render(msg, True, VIOLA)
            rect_msg = text_msg.get_rect(center=(INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2 + 20))
            screen.blit(text_msg, rect_msg)

        pygame.display.flip()

    # Uscita: ritorno il best_score (per ora non lo modifichiamo in questa versione)
    pygame.quit()
    sys.exit(best_score)


if __name__ == "__main__":
    main()

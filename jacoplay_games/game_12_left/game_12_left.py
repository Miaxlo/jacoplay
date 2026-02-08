import os
import sys
import json
import argparse
import time
import math
import random

import pygame

# Tenta di importare python-vlc per il video intro
try:
    import vlc
except ImportError:
    vlc = None

# ----------------------------------------------------------------------
# COSTANTI GENERALI
# ----------------------------------------------------------------------

INTERNAL_RESOLUTION = (1920, 1080)

BIANCO = (255, 255, 255)
VIOLA = (216, 110, 204)
SPEED1 = (255, 0, 0)
SPEED2 = (255, 192, 0)
SPEED3 = (255, 255, 0)
SPEED4 = (204, 255, 102)
SPEED5 = (71, 212, 90)
BLU = (78, 149, 217)

# Velocità massima del personaggio (px/s)
MAX_SPEED_PX = 2000.0

# Fisica del salto
JUMP_VELOCITY = 3000.0 / 2.5   # 1666.666...
GRAVITY = 4000.0 / 2.5         # 3000.0

# Durata scivolata
SLIDE_DURATION = 1.0     # secondi

# Durata teorica di un salto completo (su e giù alla stessa quota)
JUMP_TOTAL_TIME = 2 * JUMP_VELOCITY / GRAVITY

# Fattori di velocità per i 6 livelli (0 non usato nel gioco)
SPEED_LEVEL_FACTORS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

# Posizione fissa del personaggio
CHAR_X = 1100
CHAR_Y = 464


# ----------------------------------------------------------------------
# PATH BASE (relativi al file corrente)
# ----------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "game_12_data")
MEDIA_DIR = os.path.join(BASE_DIR, "game_12_media")

PROPERTIES_PATH = os.path.join(DATA_DIR, "game_12.properties")
FONT_PATH = os.path.join(MEDIA_DIR, "Sadannes.ttf")

INTRO_VIDEO_PATH = os.path.join(MEDIA_DIR, "intro.mp4")

BKG_MENU_PATH = os.path.join(MEDIA_DIR, "bkg_menu.png")
BKG_ISTRUZIONI_PATH = os.path.join(MEDIA_DIR, "bkg_istruzioni.png")

# Sfondi di gioco
BKG0_1_PATH = os.path.join(MEDIA_DIR, "bkg_0_1.png")
BKG0_2_PATH = os.path.join(MEDIA_DIR, "bkg_0_2.png")
BKG1_PATH = os.path.join(MEDIA_DIR, "bkg_1.png")

TACHIMETRO_PATH = os.path.join(MEDIA_DIR, "tachimetro.png")

BARRA_PATH = os.path.join(MEDIA_DIR, "barra.png")
TESTA_PATH = os.path.join(MEDIA_DIR, "testa.png")
AUTO_PATH = os.path.join(MEDIA_DIR, "auto.png")  # serve per la distanza (anche se non la disegniamo ancora)

CAMION_PATH = os.path.join(MEDIA_DIR, "camion.png")
RUOTA_AUTO_PATH = os.path.join(MEDIA_DIR, "ruota_auto.png")
RUOTA_CAMION_PATH = os.path.join(MEDIA_DIR, "ruota_camion.png")

MOTORE_AUTO_PATH = os.path.join(MEDIA_DIR, "motore_auto.mp3")
MOTORE_CAMION_PATH = os.path.join(MEDIA_DIR, "motore_camion.mp3")
CLACSON_CAMION_PATH = os.path.join(MEDIA_DIR, "clacson_camion.mp3")

BKG_GAMEOVER_OK_PATH = os.path.join(MEDIA_DIR, "bkg_gameover_ok.png")
BKG_GAMEOVER_KO_PATH = os.path.join(MEDIA_DIR, "bkg_gameover_ko.png")


# Frame personaggio
CHAR_FRAMES_FILES = [
    "jac_00.png",  # 0
    "jac_01.png",  # 1
    "jac_02.png",  # 2
    "jac_03.png",  # 3
    "jac_04.png",  # 4 - scivolata
    "jac_05.png",  # 5 - salto
    "jac_06.png",  # 6 - caduto indietro
    "jac_07.png",  # 7 - caduto avanti
    "jac_08.png",  # 8 - fermo in piedi
]

MUSIC_MENU_PATH = os.path.join(MEDIA_DIR, "music_menu.mp3")
MUSIC_GAME_PATH = os.path.join(MEDIA_DIR, "music_game.mp3")

# Ostacoli da specifica
FOCA_PATH = os.path.join(MEDIA_DIR, "foca.png")
RENNA_PATH = os.path.join(MEDIA_DIR, "renna.png")
WOLPERTINGER_PATH = os.path.join(MEDIA_DIR, "wolpertinger.png")
AQUILA1_PATH = os.path.join(MEDIA_DIR, "aquila01.png")
AQUILA2_PATH = os.path.join(MEDIA_DIR, "aquila02.png")

# Spawn ostacoli: ogni X secondi con X casuale tra 3 e 5
OBST_MIN_GAP_TIME = 3.0
OBST_MAX_GAP_TIME = 5.0

# Quote Y fisse (top-left) da specifica
FOCA_Y = 575
RENNA_Y = 549
WOLPERTINGER_Y = 574
AQUILA_Y = 317

# Aquila: si muove verso destra rispetto allo sfondo a 100 px/s
AQUILA_EXTRA_SPEED = 100.0
AQUILA_ANIM_PERIOD = 0.18  # alternanza frame (puoi tarare)

# ----------------------------------------------------------------------
# UTILITÀ LETTURA/SCRITTURA PROPERTIES
# ----------------------------------------------------------------------

def load_properties():
    """Carica game_12.properties; se non esiste, crea default con primorun=True."""
    props = {"primorun": True}
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(PROPERTIES_PATH):
        try:
            with open(PROPERTIES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    props.update(data)
        except Exception as e:
            print(f"Impossibile leggere {PROPERTIES_PATH}: {e}", file=sys.stderr)

    return props


def save_properties(props):
    """Salva le properties sul disco."""
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(PROPERTIES_PATH, "w", encoding="utf-8") as f:
            json.dump(props, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Impossibile scrivere {PROPERTIES_PATH}: {e}", file=sys.stderr)


# ----------------------------------------------------------------------
# RIPRODUZIONE INTRO CON VLC
# ----------------------------------------------------------------------

def play_intro_video():
    """
    Riproduce il video di intro in fullscreen con python-vlc.
    Ritorna quando il video è terminato o quando l'utente chiude/ESC.
    Se vlc non è disponibile o il file manca, non fa nulla.
    """
    if vlc is None:
        print("python-vlc non disponibile: salto il video di intro.", file=sys.stderr)
        return

    if not os.path.exists(INTRO_VIDEO_PATH):
        print(f"Video intro non trovato: {INTRO_VIDEO_PATH}", file=sys.stderr)
        return

    # Istanza VLC
    instance = vlc.Instance()
    player = instance.media_player_new()

    media = instance.media_new(INTRO_VIDEO_PATH)
    player.set_media(media)

    # Fullscreen
    try:
        player.set_fullscreen(True)
    except Exception:
        pass

    # Avvia riproduzione
    player.play()
    time.sleep(0.2)  # piccolo delay per far partire il video

    # Loop finché il video è in riproduzione
    running = True
    while running:
        state = player.get_state()
        if state in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
            break

        # Gestione di ESC / chiusura finestra Pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        time.sleep(0.01)

    player.stop()
    # Esce da fullscreen se possibile
    try:
        player.set_fullscreen(False)
    except Exception:
        pass


# ----------------------------------------------------------------------
# SCHERMATA ISTRUZIONI
# ----------------------------------------------------------------------

def show_instructions_screen(screen, clock, font_menu):
    """
    Mostra la schermata ISTRUZIONI (bkg_istruzioni.png).
    La musica del menu NON viene interrotta.
    Si esce con un tasto qualunque o click.
    """
    try:
        bkg_instr = pygame.image.load(BKG_ISTRUZIONI_PATH).convert()
    except Exception as e:
        print(f"Errore caricando bkg_istruzioni: {e}", file=sys.stderr)
        bkg_instr = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                running = False

        if bkg_instr:
            screen.blit(bkg_instr, (0, 0))
        else:
            screen.fill((0, 0, 0))
            txt = font_menu.render("ISTRUZIONI non trovate (bkg_istruzioni.png)", True, BIANCO)
            rect = txt.get_rect(center=(INTERNAL_RESOLUTION[0] // 2,
                                        INTERNAL_RESOLUTION[1] // 2))
            screen.blit(txt, rect)

        pygame.display.flip()
        clock.tick(60)


# ----------------------------------------------------------------------
# GIOCO: SFONDO + PERSONAGGIO + OSTACOLI
# ----------------------------------------------------------------------

def load_character_frames():
    """Carica tutti i frame del personaggio."""
    frames = []
    for fname in CHAR_FRAMES_FILES:
        path = os.path.join(MEDIA_DIR, fname)
        try:
            img = pygame.image.load(path).convert_alpha()
        except Exception as e:
            print(f"Errore caricando frame personaggio {fname}: {e}", file=sys.stderr)
            # fallback: piccolo quadrato visibile
            img = pygame.Surface((50, 50), pygame.SRCALPHA)
            img.fill((255, 0, 255, 255))
        frames.append(img)
    return frames


def run_game(screen, clock, font_menu):
    """
    Loop di gioco:
    - sfondo a due livelli con parallasse
    - personaggio che corre / salta / scivola in posizione fissa
    - ostacoli che arrivano da sinistra
    - musica di gioco in loop
    ESC → ritorno al menu.
    """

    game_result = None  # None / "ok" / "ko"
    frozen = False
    freeze_timer = 0.0


    # Musica di gioco
    if os.path.exists(MUSIC_GAME_PATH):
        try:
            pygame.mixer.music.load(MUSIC_GAME_PATH)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Errore caricando music_game: {e}", file=sys.stderr)
    else:
        print(f"File musica gioco non trovato: {MUSIC_GAME_PATH}", file=sys.stderr)

    # Carica sfondi mantenendo l'alpha (PNG con trasparenza)
    try:
        bkg0_1 = pygame.image.load(BKG0_1_PATH).convert_alpha()
    except Exception as e:
        print(f"Errore caricando bkg_0_1: {e}", file=sys.stderr)
        bkg0_1 = pygame.Surface(INTERNAL_RESOLUTION, pygame.SRCALPHA)
        bkg0_1.fill((30, 30, 30, 255))

    try:
        bkg0_2 = pygame.image.load(BKG0_2_PATH).convert_alpha()
    except Exception as e:
        print(f"Errore caricando bkg_0_2: {e}", file=sys.stderr)
        bkg0_2 = bkg0_1.copy()

    try:
        bkg1 = pygame.image.load(BKG1_PATH).convert_alpha()
    except Exception as e:
        print(f"Errore caricando bkg_1: {e}", file=sys.stderr)
        bkg1 = pygame.Surface(INTERNAL_RESOLUTION, pygame.SRCALPHA)
        bkg1.fill((60, 60, 60, 255))

    bkg0_width = bkg0_1.get_width()
    bkg1_width = bkg1.get_width()

    # UI distanza (barra + testa)
    try:
        barra_img = pygame.image.load(BARRA_PATH).convert_alpha()
    except Exception as e:
        print(f"Errore caricando barra.png: {e}", file=sys.stderr)
        barra_img = None

    try:
        testa_img = pygame.image.load(TESTA_PATH).convert_alpha()
    except Exception as e:
        print(f"Errore caricando testa.png: {e}", file=sys.stderr)
        testa_img = None

    testa_w = testa_img.get_width() if testa_img else 78  # in specifica 78px
    testa_half = testa_w // 2  # centro orizzontale (39 se 78)


    # Tachimetro (UI)
    try:
        tachimetro_img = pygame.image.load(TACHIMETRO_PATH).convert_alpha()
    except Exception as e:
        print(f"Errore caricando tachimetro.png: {e}", file=sys.stderr)
        tachimetro_img = None

    # -------------------------
    # AUTO + CAMION (sprite + maschere + suoni)
    # -------------------------
    def _load_img(path, fallback_size=(100, 60)):
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception as e:
            print(f"Errore caricando {path}: {e}", file=sys.stderr)
            s = pygame.Surface(fallback_size, pygame.SRCALPHA)
            s.fill((255, 0, 255, 200))
            return s

    auto_img = _load_img(AUTO_PATH, (300, 150))
    camion_img = _load_img(CAMION_PATH, (500, 250))
    ruota_auto_img = _load_img(RUOTA_AUTO_PATH, (80, 80))
    ruota_camion_img = _load_img(RUOTA_CAMION_PATH, (120, 120))

    auto_mask = pygame.mask.from_surface(auto_img)
    camion_mask = pygame.mask.from_surface(camion_img)

    # Ruote: rotazione antioraria 360° ogni 0.5s => 720°/s
    wheel_angle = 0.0
    WHEEL_DEG_PER_SEC = 720.0

    # Distanze iniziali (metri)
    # auto: 50m a sinistra (già la usi come car_distance_m)
    # camion: ora lo hai portato a 150m a destra
    truck_distance_m = 150.0

    # Suoni su canali dedicati
    auto_motor_snd = None
    truck_motor_snd = None
    truck_horn_snd = None

    try:
        auto_motor_snd = pygame.mixer.Sound(MOTORE_AUTO_PATH)
    except Exception as e:
        print(f"Errore caricando {MOTORE_AUTO_PATH}: {e}", file=sys.stderr)

    try:
        truck_motor_snd = pygame.mixer.Sound(MOTORE_CAMION_PATH)
    except Exception as e:
        print(f"Errore caricando {MOTORE_CAMION_PATH}: {e}", file=sys.stderr)

    try:
        truck_horn_snd = pygame.mixer.Sound(CLACSON_CAMION_PATH)
    except Exception as e:
        print(f"Errore caricando {CLACSON_CAMION_PATH}: {e}", file=sys.stderr)

    ch_auto = pygame.mixer.Channel(1)
    ch_truck = pygame.mixer.Channel(2)
    ch_horn = pygame.mixer.Channel(3)

    def stop_vehicle_audio():
        try:
            ch_auto.stop()
            ch_truck.stop()
            ch_horn.stop()
        except Exception:
            pass
    

    auto_motor_on = False
    truck_motor_on = False
    truck_was_visible = False

    # Carica frame personaggio
    char_frames = load_character_frames()
    run_frames = char_frames[0:4]  # jac_00..jac_03

    # Stati/parametri legati al personaggio
    speed_level = 1  # 20% all'avvio
    speed_factor = SPEED_LEVEL_FACTORS[speed_level]
    current_speed = speed_factor * MAX_SPEED_PX  # px/s

    char_y = float(CHAR_Y)
    char_state = "run"     # "run", "jump", "slide"
    jump_vy = 0.0          # velocità verticale nel salto
    slide_timer = 0.0      # tempo residuo di scivolata
    jump_elapsed = 0.0     # tempo trascorso dall'inizio del salto
    # Salto dinamico (gravità e velocità iniziale scalate col livello)
    jump_g = GRAVITY
    jump_v0 = JUMP_VELOCITY

    # Frame base per la rotazione del salto
    jump_base_frame = char_frames[5]  # jac_05.png

    # Animazione corsa
    run_frame_index = 0
    run_frame_timer = 0.0
    TIME_PER_FRAME_AT_MAX_SPEED = 1.0 / 32.0  # 1/32 s per frame a 100% (molto veloce)

    # Punteggio e gestione impatti ostacoli
    points = 0
    # Progressione dentro al livello corrente (0,1,2) -> larghezze 15/30/45 solo per l'ULTIMO rettangolo
    level_progress = 0
    # Distanza tra auto e personaggio in metri (positiva se l'auto è più avanti a sinistra)
    # Inizio: 50m come da specifica
    car_distance_m = 50.0

    # Blink per urto <5%
    invuln_timer = 0.0
    blink_timer = 0.0
    blink_visible = True

    # Knockdown per urto >5%
    knock_timer = 0.0
    knock_frame = None  # 6 o 7

    # Scroll sfondi (offset iniziali)
    offset0 = 0.0  # livello 0
    offset1 = 0.0  # livello 1

    # -------------------------
    # Ostacoli (specifica)
    # -------------------------
    def _load_png_or_fallback(path, size, rgba):
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception:
            s = pygame.Surface(size, pygame.SRCALPHA)
            s.fill(rgba)
            return s

    foca_img = _load_png_or_fallback(FOCA_PATH, (140, 110), (200, 200, 255, 255))
    renna_img = _load_png_or_fallback(RENNA_PATH, (140, 140), (200, 255, 200, 255))
    wolp_img = _load_png_or_fallback(WOLPERTINGER_PATH, (150, 120), (255, 200, 200, 255))
    aquila1_img = _load_png_or_fallback(AQUILA1_PATH, (120, 80), (255, 255, 0, 255))
    aquila2_img = _load_png_or_fallback(AQUILA2_PATH, (120, 80), (255, 220, 0, 255))

    foca_mask = pygame.mask.from_surface(foca_img)
    renna_mask = pygame.mask.from_surface(renna_img)
    wolp_mask = pygame.mask.from_surface(wolp_img)
    aquila1_mask = pygame.mask.from_surface(aquila1_img)
    aquila2_mask = pygame.mask.from_surface(aquila2_img)

    # Stato animazione aquila
    aquila_anim_timer = 0.0
    aquila_anim_idx = 0  # 0 -> aquila01, 1 -> aquila02

    obstacles = []  # lista di dict: {"type": "low"/"high", "x": float, "y": float, "img": surf}
    spawn_timer = 0.0
    next_spawn_time = random.uniform(OBST_MIN_GAP_TIME, OBST_MAX_GAP_TIME)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # secondi
        if frozen:
            # Congela tutto: niente update logica/animazioni.
            freeze_timer -= dt
            if freeze_timer <= 0.0:
                running = False  # usciamo dal loop e andiamo alla schermata OK/KO
            dt_logic = 0.0
        else:
            dt_logic = dt
        

        # Aggiorna animazione aquila (alternanza aquila01/aquila02)
        aquila_anim_timer += dt_logic
        if aquila_anim_timer >= AQUILA_ANIM_PERIOD:
            aquila_anim_timer -= AQUILA_ANIM_PERIOD
            aquila_anim_idx = 1 - aquila_anim_idx
   
        # -------------------------
        # EVENTI
        # -------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            elif event.type == pygame.KEYDOWN:
                # ESC → esci dal gioco e torna al menu
                if event.key == pygame.K_ESCAPE:
                    running = False

                # SALTO: freccia su / W / SPAZIO
                elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                    if char_state == "run":
                        char_state = "jump"

                        duration_scale = 0.99 ** max(0, speed_level - 1)

                        # Per avere un salto PIÙ CORTO quando vai veloce,
                        # bisogna aumentare "k" (accelera la fisica):
                        # k = 1/duration_scale  -> livello 2: 1/0.9=1.111...  (salto -10%)
                        k = 1.0 / duration_scale

                        # Scaliamo insieme v0 e g con k: altezza invariata, tempo /k
                        jump_v0 = JUMP_VELOCITY * k
                        jump_g = GRAVITY * k

                        jump_vy = -jump_v0
                        jump_elapsed = 0.0

                # SCIVOLATA: freccia giù / S / CTRL
                elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_LCTRL, pygame.K_RCTRL):
                    if char_state == "run":
                        char_state = "slide"
                        duration_scale = 0.9 ** max(0, speed_level - 1)
                        slide_timer = SLIDE_DURATION * duration_scale

        # -------------------------
        # LOGICA GIOCO
        # -------------------------

        # Aggiorna velocità (per ora resta fissa al 20%)
        speed_factor = SPEED_LEVEL_FACTORS[speed_level]
        current_speed = speed_factor * MAX_SPEED_PX

        # Auto: velocità costante = 50% della velocità massima del personaggio (px/s)
        car_speed_px = 0.5 * MAX_SPEED_PX

        # Nel gioco 200px = 1m
        # Se il bambino è più veloce dell'auto, la distanza diminuisce (si avvicina).
        # Se è più lento, la distanza aumenta (si allontana).
        rel_speed_px = car_speed_px - current_speed  # + => auto scappa
        car_distance_m += (rel_speed_px * dt_logic) / 200.0

        # Camion: velocità costante = 50% MAX, ma sta dietro (a destra).
        truck_speed_px = 0.5 * MAX_SPEED_PX

        # Se il bambino è più veloce del camion, la distanza aumenta (si allontana).
        # Se è più lento, la distanza diminuisce (il camion si avvicina).
        truck_distance_m += ((current_speed - truck_speed_px) * dt_logic) / 200.0
     
        # Aggiorna scroll sfondi
        # Il personaggio corre verso sinistra → sfondi scorrono verso destra (x crescente)
        offset1 += current_speed * dt_logic
        offset0 += current_speed * 0.1 * dt_logic  # livello 0 al 10% della velocità del personaggio

        # Fisica salto / scivolata
        if char_state == "jump":
            jump_vy += jump_g * dt_logic
            char_y += jump_vy * dt_logic
            jump_elapsed += dt_logic

            if char_y >= CHAR_Y:
                char_y = float(CHAR_Y)
                char_state = "run"
                jump_vy = 0.0
                jump_elapsed = 0.0

        elif char_state == "slide":
            slide_timer -= dt_logic
            if slide_timer <= 0.0:
                char_state = "run"

        # Wrapping orizzontale per sfondi
        if bkg1_width > 0:
            while offset1 > bkg1_width:
                offset1 -= bkg1_width

        if bkg0_width > 0:
            while offset0 > bkg0_width:
                offset0 -= bkg0_width

        # Animazione corsa (solo quando corre)
        animation_speed_factor = max(speed_factor, 0.05)  # evita divisioni per 0
        time_per_frame = TIME_PER_FRAME_AT_MAX_SPEED / animation_speed_factor

        if char_state == "run" and current_speed > 0:
            run_frame_timer += dt_logic
            if run_frame_timer >= time_per_frame:
                run_frame_timer -= time_per_frame
                run_frame_index = (run_frame_index + 1) % len(run_frames)

        # -------------------------
        # OSTACOLI: spawn e movimento
        # -------------------------
        spawn_timer += dt_logic
        if spawn_timer >= next_spawn_time:
            spawn_timer -= next_spawn_time

            obst_type = random.choice(["foca", "renna", "wolpertinger", "aquila"])

            if obst_type == "foca":
                img = foca_img
                mask = foca_mask
                y = FOCA_Y
            elif obst_type == "renna":
                img = renna_img
                mask = renna_mask
                y = RENNA_Y
            elif obst_type == "wolpertinger":
                img = wolp_img
                mask = wolp_mask
                y = WOLPERTINGER_Y
            else:
                # aquila: animata (img/mask cambiano al volo)
                img = aquila1_img
                mask = aquila1_mask
                y = AQUILA_Y

            x = -img.get_width() - 50  # “compaiono a sinistra”
            obstacles.append({
                "type": obst_type,
                "x": float(x),
                "y": float(y),
                "img": img,
                "mask": mask,
                "hit_once": False,
                "scored": False,
            })

            next_spawn_time = random.uniform(OBST_MIN_GAP_TIME, OBST_MAX_GAP_TIME)


        # Muovi ostacoli con il mondo (verso destra)
        for obst in obstacles:
            extra = AQUILA_EXTRA_SPEED if obst["type"] == "aquila" else 0.0
            obst["x"] += (current_speed + extra) * dt_logic

        # Rimuovi ostacoli che sono usciti a destra
        obstacles = [
            o for o in obstacles
            if o["x"] < INTERNAL_RESOLUTION[0] + 200
        ]

        # AUTO/CAMION: posizione X (in px) riferita alla posizione del personaggio
        PX_PER_M = 200.0

        auto_x = CHAR_X - (car_distance_m * PX_PER_M)
        auto_y = 362

        truck_x = CHAR_X + (truck_distance_m * PX_PER_M)
        truck_y = 56


        # Ruote: aggiorna angolo
        wheel_angle = (wheel_angle + WHEEL_DEG_PER_SEC * dt_logic) % 360.0

        # Visibilità (parziale) a schermo
        auto_visible = (auto_x < INTERNAL_RESOLUTION[0]) and (auto_x + auto_img.get_width() > 0)
        truck_visible = (truck_x < INTERNAL_RESOLUTION[0]) and (truck_x + camion_img.get_width() > 0)

        # -------------------------
        # AUDIO AUTO (motore in loop con volume dinamico)
        # Soglie: start a X=-1525, volume 100% quando X>-1225, 0 quando X<-1525
        # -------------------------
        if auto_motor_snd is not None:
            if auto_x >= -1525 and not auto_motor_on:
                ch_auto.play(auto_motor_snd, loops=-1)
                auto_motor_on = True

            if auto_motor_on:
                if auto_x <= -1525:
                    vol = 0.0
                elif auto_x >= -1225:
                    vol = 1.0
                else:
                    vol = (auto_x + 1525.0) / 300.0  # 0..1 tra -1525 e -1225
                vol = max(0.0, min(1.0, vol))
                ch_auto.set_volume(vol)

                if vol <= 0.0 and auto_x < -1525:
                    ch_auto.stop()
                    auto_motor_on = False

        # -------------------------
        # AUDIO CAMION (motore in loop + clacson quando compare)
        # Soglie: start a X=2400, volume 100% quando X<1921, 0 quando X>2400
        # -------------------------
        if truck_motor_snd is not None:
            if truck_x <= 2400 and not truck_motor_on:
                ch_truck.play(truck_motor_snd, loops=-1)
                truck_motor_on = True

            if truck_motor_on:
                if truck_x >= 2400:
                    vol = 0.0
                elif truck_x <= 1921:
                    vol = 1.0
                else:
                    vol = (2400.0 - truck_x) / (2400.0 - 1921.0)  # 0..1 tra 2400 e 1921
                vol = max(0.0, min(1.0, vol))
                ch_truck.set_volume(vol)

                if vol <= 0.0 and truck_x > 2400:
                    ch_truck.stop()
                    truck_motor_on = False

        # Clacson: una volta quando compare a schermo, e di nuovo se scompare e ricompare
        if truck_visible and not truck_was_visible:
            if truck_horn_snd is not None:
                ch_horn.play(truck_horn_snd)
        truck_was_visible = truck_visible


        # -------------------------
        # DISEGNO
        # -------------------------
        # Livello 0 (più lontano)
        x0_1 = int(offset0)
        x0_2 = x0_1 - bkg0_width
        screen.blit(bkg0_1, (x0_1, 0))
        screen.blit(bkg0_2, (x0_2, 0))

        # Livello 1 (più vicino / strada)
        x1_1 = int(offset1)
        x1_2 = x1_1 - bkg1_width
        screen.blit(bkg1, (x1_1, 0))
        screen.blit(bkg1, (x1_2, 0))

        # Personaggio in primo piano
        # (se knockdown attivo, forza frame 6/7)
        if knock_timer > 0.0 and knock_frame is not None:
            current_frame = char_frames[knock_frame]  # 6 o 7
            rect = current_frame.get_rect(topleft=(CHAR_X, int(char_y)))

        else:
            if char_state == "run":
                current_frame = run_frames[run_frame_index]
                rect = current_frame.get_rect(topleft=(CHAR_X, int(char_y)))

            elif char_state == "jump":
                # Progresso del salto 0..1 (clippato per sicurezza)
                if JUMP_TOTAL_TIME > 0:
                    jump_total_time = (2.0 * jump_v0 / jump_g) if jump_g > 0 else 0.001
                    progress = max(0.0, min(jump_elapsed / jump_total_time, 1.0))
                else:
                    progress = 1.0

                angle = 360.0 * progress  # rotazione antioraria

                base_rect = jump_base_frame.get_rect(topleft=(CHAR_X, int(char_y)))
                rotated = pygame.transform.rotate(jump_base_frame, angle)
                rect = rotated.get_rect(center=base_rect.center)
                current_frame = rotated

            elif char_state == "slide":
                current_frame = char_frames[4]  # jac_04.png - scivolata
                rect = current_frame.get_rect(topleft=(CHAR_X, int(char_y)))

            else:
                current_frame = run_frames[run_frame_index]
                rect = current_frame.get_rect(topleft=(CHAR_X, int(char_y)))


        # Blink (urto <5%): alterna visibilità
        if invuln_timer > 0.0:
            blink_timer += dt_logic
            if blink_timer >= 0.10:
                blink_timer -= 0.10
                blink_visible = not blink_visible
        else:
            blink_visible = True

        if blink_visible:
            screen.blit(current_frame, rect.topleft)

        # Disegna ostacoli (davanti al personaggio come da specifica)
        obstacle_rects = []
        for obst in obstacles:
            # Aquila: scegli frame corrente
            if obst["type"] == "aquila":
                if aquila_anim_idx == 0:
                    obst["img"] = aquila1_img
                    obst["mask"] = aquila1_mask
                else:
                    obst["img"] = aquila2_img
                    obst["mask"] = aquila2_mask

            img = obst["img"]
            ox = int(obst["x"])
            oy = int(obst["y"])
            screen.blit(img, (ox, oy))
            obstacle_rects.append((obst, img.get_rect(topleft=(ox, oy))))

        # -------------------------
        # DISEGNO AUTO + CAMION (sopra ostacoli e personaggio)
        # -------------------------
        # Auto
        auto_rect = auto_img.get_rect(topleft=(int(auto_x), auto_y))
        if auto_visible:
            screen.blit(auto_img, auto_rect.topleft)

            wheel_rot = pygame.transform.rotate(ruota_auto_img, wheel_angle)

            # 1a ruota
            wrect = wheel_rot.get_rect()
            wrect.center = (auto_rect.left + 160 + ruota_auto_img.get_width() // 2,
                            auto_rect.top + 376 + ruota_auto_img.get_height() // 2)
            screen.blit(wheel_rot, wrect.topleft)

            # 2a ruota (X=945)
            wrect2 = wheel_rot.get_rect()
            wrect2.center = (auto_rect.left + 945 + ruota_auto_img.get_width() // 2,
                             auto_rect.top + 376 + ruota_auto_img.get_height() // 2)
            screen.blit(wheel_rot, wrect2.topleft)




        # Camion
        truck_rect = camion_img.get_rect(topleft=(int(truck_x), truck_y))
        if truck_visible:
            screen.blit(camion_img, truck_rect.topleft)

            # Ruota camion: 1 istanza offset (266,662) (spec)
            wheel_rot_t = pygame.transform.rotate(ruota_camion_img, wheel_angle)
            tw = wheel_rot_t.get_rect()
            tw.center = (truck_rect.left + 266 + ruota_camion_img.get_width() // 2,
                         truck_rect.top + 662 + ruota_camion_img.get_height() // 2)
            screen.blit(wheel_rot_t, tw.topleft)


        # Mask pixel-perfect del personaggio (frame corrente)
        char_mask = pygame.mask.from_surface(current_frame)
        char_pixels = char_mask.count() or 1


        # -------------------------
        # COLLISIONI + REGOLE SPECIFICA (PIXEL PERFECT)
        # -------------------------

        # Aggiorna timer invuln/knock
        if invuln_timer > 0.0:
            invuln_timer = max(0.0, invuln_timer - dt_logic)

        if knock_timer > 0.0:
            knock_timer = max(0.0, knock_timer - dt_logic)
            if knock_timer == 0.0:
                # Ripartenza dopo 2s: velocità minima 20% e torna a correre
                speed_level = 1
                level_progress = 0
                knock_frame = None

        # Se sei in knockdown o invulnerabile, ignora nuove collisioni (evita spam)
        can_collide = (knock_timer <= 0.0 and invuln_timer <= 0.0)

        collided_obstacle = None
        collided_rect = None
        collision_ratio = 0.0

        if can_collide:
            for obst in obstacles:
                if obst.get("hit_once", False):
                    continue

                o_rect = obst["img"].get_rect(topleft=(int(obst["x"]), int(obst["y"])))

                # Check veloce rect
                if not rect.colliderect(o_rect):
                    continue

                offset = (o_rect.left - rect.left, o_rect.top - rect.top)
                overlap = char_mask.overlap_area(obst["mask"], offset)

                if overlap > 0:
                    ratio = overlap / char_pixels
                    if ratio > collision_ratio:
                        collision_ratio = ratio
                        collided_obstacle = obst
                        collided_rect = o_rect

        if collided_obstacle is not None:
            collided_obstacle["hit_once"] = True

            if collision_ratio < 0.05:
                # <5%: blink 1s + -1 livello (min 20%)
                invuln_timer = 1.0
                blink_timer = 0.0
                blink_visible = True
                speed_level = max(1, speed_level - 1)
                level_progress = 0


            else:
                # >5%: velocità 0%, frame 6/7 per 2s, ostacolo scompare, poi riparte a 20%
                speed_level = 0
                level_progress = 0

                # Se personaggio a destra del centro orizzontale dell'ostacolo -> frame 6, altrimenti 7
                if rect.centerx > collided_rect.centerx:
                    knock_frame = 6
                else:
                    knock_frame = 7

                knock_timer = 2.0

                # Rimuovi ostacolo colpito
                collided_obstacle["remove"] = True

        # Punteggio: se l'ostacolo passa oltre il personaggio senza essere colpito
        for obst in obstacles:
            if obst.get("remove", False) or obst.get("hit_once", False) or obst.get("scored", False):
                continue
            # quando il suo lato sinistro supera il lato destro del personaggio -> “superato”
            if obst["x"] > rect.right:
                obst["scored"] = True
                points += 1

                # Avanza solo la progressione dell'ultimo livello
                if speed_level > 0 and speed_level < 5:
                    level_progress += 1

                    # al terzo punto: completa il livello, passa al livello successivo
                    if level_progress >= 3:
                        level_progress = 0
                        speed_level = min(5, speed_level + 1)

                # Se sei già al livello 5, i punti continuano ma non aumentano oltre

        # Ripulisci ostacoli rimossi
        obstacles = [o for o in obstacles if not o.get("remove", False)]

        # -------------------------
        # COLLISIONI con AUTO/CAMION (fine partita)
        # -------------------------
        def mask_overlap(a_mask, a_rect, b_mask, b_rect):
            if not a_rect.colliderect(b_rect):
                return False
            off = (b_rect.left - a_rect.left, b_rect.top - a_rect.top)
            return a_mask.overlap(b_mask, off) is not None

        # maschera personaggio (già calcolata: char_mask) e rect (rect)
        # AUTO: successo
        if auto_visible:
            auto_mask_now = auto_mask
            if mask_overlap(char_mask, rect, auto_mask_now, auto_rect):
                game_result = "ok"
                frozen = True
                freeze_timer = 0.0  # freeze immediato (puoi mettere 0.2 se vuoi "freeze frame")
                stop_vehicle_audio()
                running = False

        # CAMION: fallimento
        if truck_visible:
            camion_mask_now = camion_mask
            if mask_overlap(char_mask, rect, camion_mask_now, truck_rect):
                game_result = "ko"
                frozen = True
                freeze_timer = 0.0
                stop_vehicle_audio()
                running = False


        points_in_level = points % 3   # 0,1,2

        # -------------------------
        # UI VELOCITÀ (tachimetro.png + rettangoli)
        # -------------------------

        # 1) Tachimetro fisso
        if tachimetro_img is not None:
            screen.blit(tachimetro_img, (19, 15))

        # 2) Rettangoli velocità come da specifica
        # Rettangolo 1 (20%) a (193,27), h=72
        base_x = 193
        base_y = 27
        rect_h = 72

        # larghezza 15/30/45 in base a 0/1/2 punti nel livello
        rect_w = 15 * (points_in_level + 1)

        colors = [SPEED1, SPEED2, SPEED3, SPEED4, SPEED5]

        n = max(0, min(speed_level, 5))
        for i in range(n):
            rx = base_x + i * 51

            # Tutti i rettangoli precedenti sono pieni (45px)
            if i < n - 1:
                w = 45
            else:
                # Solo l'ultimo cresce: 15/30/45 in base a level_progress (0/1/2)
                w = 15 * (max(0, min(level_progress, 2)) + 1)

            r = pygame.Rect(rx, base_y, w, rect_h)
            pygame.draw.rect(screen, colors[i], r)

        # -------------------------
        # UI DISTANZA (barra + testa + "Xm") - come da specifica
        # -------------------------

        # Barra fissa a (0, 960)
        if barra_img is not None:
            screen.blit(barra_img, (0, 960))

        # Spazio barra: inizia da X=168, largo 1524px => 75m
        BAR_START_X = 168
        BAR_WIDTH_PX = 1524
        BAR_METERS = 200.0

        # Clamp distanza nel range 0..75m (la barra rappresenta 75m)
        if car_distance_m < 0.0:
            car_distance_m = 0.0
        elif car_distance_m > BAR_METERS:
            car_distance_m = BAR_METERS

        # La testa ha Y fissa 970 e si muove in X in base ai metri
        # La specifica parla del "centro orizzontale della testa"
        head_center_x = BAR_START_X + (car_distance_m / BAR_METERS) * BAR_WIDTH_PX

        # Convertiamo in top-left X
        head_x = int(head_center_x - testa_half)
        head_y = 970

        if testa_img is not None:
            screen.blit(testa_img, (head_x, head_y))

        # Testo "Xm" in viola a (25, 932)
        # Altezza 26px: usiamo un font da 26 (o vicino)
        try:
            font_26 = pygame.font.Font(FONT_PATH, 26)
        except Exception:
            font_26 = pygame.font.SysFont(None, 26)

        dist_txt = font_26.render(f"{int(round(car_distance_m))}m", True, VIOLA)
        screen.blit(dist_txt, (25, 932))



        pygame.display.flip()

    # Stop musica di gioco
    pygame.mixer.music.stop()
    stop_vehicle_audio()   

    # Se fine partita (ok/ko) mostra schermata e avvia music_menu.mp3 in loop
    if game_result in ("ok", "ko"):
        try:
            bkg = pygame.image.load(BKG_GAMEOVER_OK_PATH if game_result == "ok" else BKG_GAMEOVER_KO_PATH).convert()
        except Exception as e:
            print(f"Errore caricando bkg gameover: {e}", file=sys.stderr)
            bkg = None

        # Avvia music_menu.mp3 e LA LASCIA SUONARE anche quando torni al menu
        if os.path.exists(MUSIC_MENU_PATH):
            try:
                pygame.mixer.music.load(MUSIC_MENU_PATH)
                pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"Errore caricando music_menu (gameover): {e}", file=sys.stderr)

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    waiting = False

            if bkg:
                screen.blit(bkg, (0, 0))
            else:
                screen.fill((0, 0, 0))

            pygame.display.flip()
            clock.tick(60)

        # Ritorna un flag per dire al menu: "la music_menu sta già suonando, non riavviarla"
        return True

    return False


# ----------------------------------------------------------------------
# MENU PRINCIPALE
# ----------------------------------------------------------------------

def main_menu(screen, clock, font_menu, props, best_score):
    """
    Gestione del menu principale:
      - BKG: bkg_menu.png
      - Musica: music_menu.mp3 in loop (interrotta solo per video intro, gioco o uscita)
      - Voci: NUOVA PARTITA, ISTRUZIONI, RIVEDI INTRO, ESCI
    Ritorna il best_score aggiornato (anche se per ora non cambia).
    """
    # Carica background menu
    try:
        bkg_menu = pygame.image.load(BKG_MENU_PATH).convert()
    except Exception as e:
        print(f"Errore caricando bkg_menu: {e}", file=sys.stderr)
        bkg_menu = None

    # Avvia musica menu
    if os.path.exists(MUSIC_MENU_PATH):
        try:
            pygame.mixer.music.load(MUSIC_MENU_PATH)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Errore caricando music_menu: {e}", file=sys.stderr)
    else:
        print(f"File musica menu non trovato: {MUSIC_MENU_PATH}", file=sys.stderr)

    # Definizione voci menu
    labels = [
        "NUOVA PARTITA",
        "ISTRUZIONI",
        "RIVEDI INTRO",
        "ESCI",
    ]

    # Pre-calcolo delle rect di riferimento (allineamento a destra)
    menu_items = []
    # Modifica richiesta: +800px a destra e +20px di spaziatura
    start_x = 1856          # 1056 + 800
    start_y = 170
    step_y = 76             # 56 + 20

    for i, label in enumerate(labels):
        text_surface = font_menu.render(label, True, BIANCO)
        rect = text_surface.get_rect()
        rect.topright = (start_x, start_y + i * step_y)
        menu_items.append({
            "label": label,
            "rect": rect,
        })

    hovered_index = None

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        hovered_index = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, item in enumerate(menu_items):
                    if item["rect"].collidepoint(mouse_pos):
                        selection = item["label"]
                        if selection == "NUOVA PARTITA":
                            pygame.mixer.music.stop()
                            menu_music_already_playing = run_game(screen, clock, font_menu)

                            # Al ritorno dal gioco:
                            # - se run_game ha mostrato gameover, la music_menu sta già suonando e NON va riavviata
                            if not menu_music_already_playing:
                                if os.path.exists(MUSIC_MENU_PATH):
                                    try:
                                        pygame.mixer.music.load(MUSIC_MENU_PATH)
                                        pygame.mixer.music.play(-1)
                                    except Exception as e:
                                        print(f"Errore ricaricando music_menu: {e}", file=sys.stderr)

                        elif selection == "ISTRUZIONI":
                            show_instructions_screen(screen, clock, font_menu)

                        elif selection == "RIVEDI INTRO":
                            pygame.mixer.music.stop()
                            play_intro_video()
                            if os.path.exists(MUSIC_MENU_PATH):
                                try:
                                    pygame.mixer.music.load(MUSIC_MENU_PATH)
                                    pygame.mixer.music.play(-1)
                                except Exception as e:
                                    print(f"Errore ricaricando music_menu dopo intro: {e}", file=sys.stderr)

                        elif selection == "ESCI":
                            running = False
                        break

        # Ricalcola hover
        for i, item in enumerate(menu_items):
            if item["rect"].collidepoint(mouse_pos):
                hovered_index = i
                break

        # Disegno menu
        if bkg_menu:
            screen.blit(bkg_menu, (0, 0))
        else:
            screen.fill((0, 0, 0))

        for i, item in enumerate(menu_items):
            color = BLU if i == hovered_index else BIANCO
            surf = font_menu.render(item["label"], True, color)
            rect = surf.get_rect()
            rect.topright = item["rect"].topright
            item["rect"] = rect
            screen.blit(surf, rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.mixer.music.stop()
    return best_score


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(description="Game 12 Left")
    parser.add_argument("--score", type=int, default=0,
                        help="Miglior punteggio preesistente (best_score)")
    return parser.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])
    best_score = args.score

    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode(
        INTERNAL_RESOLUTION,
        pygame.FULLSCREEN | pygame.SCALED
    )
    pygame.display.set_caption("Game 12 Left")

    clock = pygame.time.Clock()

    try:
        font_menu = pygame.font.Font(FONT_PATH, 56)
    except Exception as e:
        print(f"Errore caricando il font Sadannes.ttf: {e}", file=sys.stderr)
        font_menu = pygame.font.SysFont(None, 56)

    props = load_properties()

    if props.get("primorun", True):
        play_intro_video()
        props["primorun"] = False
        save_properties(props)

    best_score = main_menu(screen, clock, font_menu, props, best_score)

    # Alla fine, stampa best_score così Jacoplay può leggerlo da stdout
    print(best_score)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

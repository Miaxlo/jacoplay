import os
import sys
import json
import argparse
import time
import math

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
JUMP_VELOCITY = 1600.0   # velocità iniziale verso l'alto (px/s)
GRAVITY = 4500.0          # gravità (px/s^2)

# Durata scivolata
SLIDE_DURATION = 1      # secondi

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
# GIOCO: SFONDO + PERSONAGGIO (CORSA)
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
    Loop di gioco: per ora implementa
    - sfondo a due livelli con parallasse
    - personaggio che corre in posizione fissa
    - musica di gioco in loop
    ESC → ritorno al menu.
    """

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

    # Carica frame personaggio
    char_frames = load_character_frames()
    run_frames = char_frames[0:4]  # jac_00..jac_03

    # Stato iniziale del personaggio
    speed_level = 1  # 20% all'avvio
    speed_factor = SPEED_LEVEL_FACTORS[speed_level]
    current_speed = speed_factor * MAX_SPEED_PX  # px/s

    # Stato del personaggio
    char_y = float(CHAR_Y)
    char_state = "run"     # "run", "jump", "slide"
    jump_vy = 0.0          # velocità verticale nel salto
    slide_timer = 0.0      # tempo residuo di scivolata
    jump_elapsed = 0.0     # tempo trascorso dall'inizio del salto

    # Frame base per la rotazione del salto
    jump_base_frame = char_frames[5]  # jac_05.png


    # Animazione corsa
    run_frame_index = 0
    run_frame_timer = 0.0
    TIME_PER_FRAME_AT_MAX_SPEED = 1.0 / 32.0  # 1/32 s per frame a 100% (frequenza raddoppiata)

    # Scroll sfondi (offset iniziali)
    offset0 = 0.0  # livello 0
    offset1 = 0.0  # livello 1

    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # secondi

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
                        jump_vy = -JUMP_VELOCITY
                        jump_elapsed = 0.0

                # SCIVOLATA: freccia giù / S / CTRL
                elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_LCTRL, pygame.K_RCTRL):
                    if char_state == "run":
                        char_state = "slide"
                        slide_timer = SLIDE_DURATION


        # Aggiorna velocità (per ora resta fissa al 20%)
        speed_factor = SPEED_LEVEL_FACTORS[speed_level]
        current_speed = speed_factor * MAX_SPEED_PX

        # Aggiorna scroll sfondi
        # Il personaggio corre verso sinistra → sfondi scorrono verso destra (x crescente)
        offset1 += current_speed * dt
        offset0 += current_speed * 0.1 * dt  # livello 0 al 10% della velocità del personaggio

        if char_state == "jump":
            # Fisica del salto: vy aumenta verso il basso per la gravità
            jump_vy += GRAVITY * dt
            char_y += jump_vy * dt

            # Tempo trascorso nel salto
            jump_elapsed += dt

            # Atterraggio
            if char_y >= CHAR_Y:
                char_y = float(CHAR_Y)
                char_state = "run"
                jump_vy = 0.0
                jump_elapsed = 0.0

        elif char_state == "slide":
            slide_timer -= dt
            if slide_timer <= 0.0:
                char_state = "run"

        # Wrapping orizzontale per sfondi
        if bkg1_width > 0:
            while offset1 > bkg1_width:
                offset1 -= bkg1_width

        if bkg0_width > 0:
            while offset0 > bkg0_width:
                offset0 -= bkg0_width

        # Aggiorna animazione corsa solo quando sta correndo
        animation_speed_factor = max(speed_factor, 0.05)  # evita divisioni per 0
        time_per_frame = TIME_PER_FRAME_AT_MAX_SPEED / animation_speed_factor

        if char_state == "run" and current_speed > 0:
            run_frame_timer += dt
            if run_frame_timer >= time_per_frame:
                run_frame_timer -= time_per_frame
                run_frame_index = (run_frame_index + 1) % len(run_frames)

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

        # Personaggio in primo piano rispetto allo sfondo
        if char_state == "run":
            current_frame = run_frames[run_frame_index]
            rect = current_frame.get_rect(topleft=(CHAR_X, int(char_y)))

        elif char_state == "jump":
            # Progresso del salto 0..1 (clippato per sicurezza)
            if JUMP_TOTAL_TIME > 0:
                progress = max(0.0, min(jump_elapsed / JUMP_TOTAL_TIME, 1.0))
            else:
                progress = 1.0

            angle = 360.0 * progress  # senso antiorario (pygame: positivo = antiorario)

            # Ruota il frame di salto intorno al suo centro
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

        screen.blit(current_frame, rect.topleft)

        pygame.display.flip()

    # Stop musica di gioco
    pygame.mixer.music.stop()


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
                            run_game(screen, clock, font_menu)
                            # Al ritorno dal gioco, riavvia musica menu
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

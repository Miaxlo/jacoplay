import sys
import os
import json
import math
import random
import pygame

# ============================================================
# COSTANTI GENERALI
# ============================================================

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# Colori RGB
BLU_SCURO       = (21, 96, 130)
AZZURRO_SCURO   = (0, 176, 240)
AZZURRO_CHIARO  = (220, 234, 247)
VERDE_SCURO     = (138, 232, 52)
VERDE_CHIARO    = (228, 247, 49)
GIALLO_CHIARO   = (255, 219, 40)
GIALLO_SCURO    = (233, 113, 50)
ROSSO_CHIARO    = (255, 0, 0)
ROSSO_SCURO     = (128, 53, 14)
NERO            = (0, 0, 0)
BIANCO          = (255, 255, 255)

FPS = 60

# Scene identifiers
SCENE_INTRO = "intro"
SCENE_MENU = "menu"
SCENE_GAME = "game"
SCENE_INSTRUCTIONS = "instructions"
SCENE_GAME_OVER = "game_over"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "game_01_data")
MEDIA_DIR = os.path.join(BASE_DIR, "game_01_media")

GAME_PROPERTIES_PATH = os.path.join(DATA_DIR, "game_01.properties")
INTRO_PROPERTIES_PATH = os.path.join(DATA_DIR, "game_01_intro.properties")

# Audio e immagini chiave
MUSIC_MENU = os.path.join(MEDIA_DIR, "music_menu.mp3")
MUSIC_INTRO = os.path.join(MEDIA_DIR, "music_intro.mp3")  # metti qui il tuo file intro
BKG_MENU = os.path.join(MEDIA_DIR, "bkg_menu.png")
BKG_BIANCO = os.path.join(MEDIA_DIR, "bkg_bianco.png")
BKG_GAME = os.path.join(MEDIA_DIR, "bkg_game.png")

FONT_PATH = os.path.join(MEDIA_DIR, "Starborn.ttf")


# ============================================================
# UTILITY
# ============================================================

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Errore salvataggio JSON {path}: {e}", file=sys.stderr)


def format_score(value: int) -> str:
    """Formatta il punteggio con punto separatore delle migliaia."""
    return f"{value:,}".replace(",", ".")


def get_arg_score(argv):
    """Legge il parametro --score dagli argomenti della riga di comando."""
    best_score = 0
    if "--score" in argv:
        idx = argv.index("--score")
        if idx + 1 < len(argv):
            try:
                best_score = int(argv[idx + 1])
            except ValueError:
                best_score = 0
    return best_score


def load_font(size: int) -> pygame.font.Font:
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        # Fallback in caso di problema
        return pygame.font.SysFont(None, size)


def blit_text_center(surface, text, font, color, y):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, y))
    surface.blit(rendered, rect)


def blit_text(surface, text, font, color, x, y, align="left"):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if align == "left":
        rect.topleft = (x, y)
    elif align == "right":
        rect.topright = (x, y)
    elif align == "center":
        rect.center = (x, y)
    surface.blit(rendered, rect)
    return rect


# ============================================================
# CLASSI DI SUPPORTO
# ============================================================

class GameConfig:
    def __init__(self):
        self.primorun = True
        self.load()

    def load(self):
        data = load_json(GAME_PROPERTIES_PATH, {})
        self.primorun = bool(data.get("primorun", True))

    def save_primorun_false(self):
        data = load_json(GAME_PROPERTIES_PATH, {})
        data["primorun"] = False
        save_json(GAME_PROPERTIES_PATH, data)


class IntroImage:
    def __init__(self, image_surface, duration_sec, fadein_sec):
        self.image = image_surface
        self.duration_ms = int(duration_sec * 1000)
        self.fadein_ms = int(fadein_sec * 1000)


class IntroManager:
    """
    Gestisce l'animazione iniziale:
    - sfondo nero
    - lista di immagini con Fadein + Durata
    - ESC apre il menu, CONTINUA riprende da dove era
    """
    def __init__(self, screen):
        self.screen = screen
        self.images = []
        self.current_index = 0
        self.current_time = 0  # ms dall'inizio dell'immagine corrente
        self.finished = False
        
       # musica intro (canale dedicato)
        self.music_sound = None
        self.music_channel = None
        self.music_started = False
        self._load_intro_music()
        
        self.load_intro_config()

    def load_intro_config(self):
        config = load_json(INTRO_PROPERTIES_PATH, [])
        self.images = []

        for entry in config:
            # gestione chiavi con nomi leggermente diversi
            img_name = (
                entry.get("Immagine")
                or entry.get("Imagine")
                or entry.get("image")
            )
            durata = entry.get("Durata") or entry.get("durata") or entry.get("duration", 0)
            fadein = entry.get("Fadein") or entry.get("fadein", 0)

            if not img_name:
                continue

            path = os.path.join(MEDIA_DIR, img_name)
            try:
                surf = pygame.image.load(path).convert_alpha()
                surf = pygame.transform.smoothscale(surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                self.images.append(IntroImage(surf, durata, fadein))
            except Exception as e:
                print(f"Errore caricamento immagine intro {path}: {e}", file=sys.stderr)

    def reset(self):
        self.current_index = 0
        self.current_time = 0
        self.finished = False

    def update(self, dt_ms):
        if self.finished or not self.images:
            self.finished = True
            return

        self.current_time += dt_ms
        current = self.images[self.current_index]

        total_time = current.fadein_ms + current.duration_ms
        if self.current_time >= total_time:
            # passiamo all'immagine successiva
            self.current_index += 1
            self.current_time = 0
            if self.current_index >= len(self.images):
                self.finished = True

    def draw(self):
        self.screen.fill(NERO)
        if not self.images or self.finished:
            return

        current = self.images[self.current_index]
        prev_image = None
        if self.current_index > 0:
            prev_image = self.images[self.current_index - 1].image

        t = self.current_time

        # Mostra immagine precedente (se esiste) pienamente visibile
        if prev_image is not None:
            self.screen.blit(prev_image, (0, 0))

        # Calcolo alpha per fade-in dell'immagine corrente
        if t < current.fadein_ms and current.fadein_ms > 0:
            alpha = int(255 * (t / current.fadein_ms))
        else:
            alpha = 255

        img = current.image.copy()
        img.set_alpha(alpha)
        self.screen.blit(img, (0, 0))

    def _load_intro_music(self):
        try:
            self.music_sound = pygame.mixer.Sound(MUSIC_INTRO)
        except Exception as e:
            print(f"Errore caricamento musica intro {MUSIC_INTRO}: {e}", file=sys.stderr)
            self.music_sound = None

    def start_music(self):
        """Avvia la musica dell'intro (loop infinito) se non è già partita."""
        if self.music_started:
            return
        if self.music_sound is None:
            return
        try:
            # usiamo un canale dedicato separato da pygame.mixer.music
            self.music_channel = self.music_sound.play(loops=-1)
            self.music_started = True
        except Exception as e:
            print(f"Errore avvio musica intro: {e}", file=sys.stderr)

    def stop_music(self, fade_ms=0):
        """Ferma la musica dell'intro, opzionalmente con fadeout."""
        if not self.music_started:
            return
        try:
            if self.music_channel is not None:
                if fade_ms > 0:
                    self.music_channel.fadeout(fade_ms)
                else:
                    self.music_channel.stop()
        except Exception as e:
            print(f"Errore stop musica intro: {e}", file=sys.stderr)
        self.music_channel = None
        self.music_started = False


class Menu:
    """
    Gestisce il menu principale:
    - bkg_menu.png in sottofondo in alcuni casi
    - bkg_bianco.png come overlay
    - voci:
        NUOVA PARTITA
        CONTINUA
        RIVEDI INTRO
        ISTRUZIONI
        ESCI
    """
    def __init__(self, screen):
        self.screen = screen
        self.font = load_font(40)
        # Carico immagini
        try:
            self.bkg_menu = pygame.image.load(BKG_MENU).convert()
            self.bkg_menu = pygame.transform.smoothscale(
                self.bkg_menu, (SCREEN_WIDTH, SCREEN_HEIGHT)
            )
        except Exception:
            self.bkg_menu = None

        try:
            self.bkg_bianco = pygame.image.load(BKG_BIANCO).convert_alpha()
            self.bkg_bianco = pygame.transform.smoothscale(
                self.bkg_bianco, (SCREEN_WIDTH, SCREEN_HEIGHT)
            )
        except Exception:
            self.bkg_bianco = None

        self.items = [
            "NUOVA PARTITA",
            "CONTINUA",
            "RIVEDI INTRO",
            "ISTRUZIONI",
            "ESCI",
        ]

        self.item_rects = []
        self.hover_index = None

        self.active = False
        self.can_continue = False
        self.continue_target = None  # "intro" o "game"
        self.menu_music_playing = False
        self.auto_background = False  # True se arriviamo a fine intro o fine gioco
        self.frozen_background = None  # Surface dello stato freeze di gioco/intro

    def open(self, can_continue, continue_target, auto_background, frozen_background):
        self.active = True
        self.can_continue = can_continue
        self.continue_target = continue_target
        self.auto_background = auto_background
        self.frozen_background = frozen_background
        self.hover_index = None
        # musica menu solo se arrivo da fine animazione o fine gioco
        if auto_background and not self.menu_music_playing:
            try:
                # la musica di menu NON deve generare USEREVENT
                pygame.mixer.music.set_endevent(0)
                pygame.mixer.music.load(MUSIC_MENU)
                pygame.mixer.music.play(-1)
                self.menu_music_playing = True
            except Exception as e:
                print(f"Errore avvio musica menu: {e}", file=sys.stderr)

    def close(self):
        self.active = False
        # se chiudo il menu, fermo la musica menu
        if self.menu_music_playing:
            pygame.mixer.music.stop()
            self.menu_music_playing = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover_index = None
            mx, my = event.pos
            for i, rect in enumerate(self.item_rects):
                if rect.collidepoint(mx, my):
                    # CONTINUA è cliccabile solo se can_continue
                    if self.items[i] == "CONTINUA" and not self.can_continue:
                        continue
                    self.hover_index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hover_index is not None:
                return self._activate_item(self.hover_index)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC nel menu: se posso continuare, continuo, altrimenti esco
                if self.can_continue:
                    return "continue"
                else:
                    return "exit"

        return None

    def _activate_item(self, index):
        label = self.items[index]
        if label == "NUOVA PARTITA":
            return "new_game"
        elif label == "CONTINUA":
            if self.can_continue:
                return "continue"
            else:
                return None
        elif label == "RIVEDI INTRO":
            return "replay_intro"
        elif label == "ISTRUZIONI":
            return "instructions"
        elif label == "ESCI":
            return "exit"
        return None

    def update(self, dt_ms):
        pass  # niente logica temporale particolare per ora

    def draw(self):
        # sfondo
        if self.auto_background and self.bkg_menu is not None:
            self.screen.blit(self.bkg_menu, (0, 0))
        elif self.frozen_background is not None:
            self.screen.blit(self.frozen_background, (0, 0))
        else:
            self.screen.fill(BIANCO)

        # overlay bianco trasparente
        if self.bkg_bianco is not None:
            self.screen.blit(self.bkg_bianco, (0, 0))

        # scritte menu centrate
        self.item_rects = []
        base_y = SCREEN_HEIGHT // 2 - 2 * 60
        for i, text in enumerate(self.items):
            y = base_y + i * 60
            color = BLU_SCURO
            if text == "CONTINUA" and not self.can_continue:
                color = (150, 150, 150)  # disabilitato
            index = i
            if self.hover_index == index and not (text == "CONTINUA" and not self.can_continue):
                color = AZZURRO_SCURO

            rendered = self.font.render(text, True, color)
            rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, y))
            self.screen.blit(rendered, rect)
            self.item_rects.append(rect)


class GameCore:
    """
    Gestisce la partita vera e propria.
    Per ora implementa:
    - carico sfondi e elementi base
    - mostra score, moltiplicatore stelle, vite
    - struttura per brani musicali e countdown
    - ESC richiama menu (gestito dal main loop)
    TODO:
    - logica completa di punteggio ritmo
    - stelle, moltiplicatore stelle
    - rage, barre rage
    - pulsazioni box_pulse
    - box messaggi
    """
    def __init__(self, screen, best_score):
        self.screen = screen
        self.best_score = best_score
        self.score = 0
        self.lives = 3
        self.star_multiplier = 1.0
        self.rage = 0
        
        # RAGE
        self.rage_change_beat = 0        # ultimo beat in cui il rage è cambiato
        self.rage_raged_active = False   # sabry_raged attiva?
        self.rage_raged_timer_ms = 0.0   # timer per i 2 secondi di sabry_raged

        # per evitare di incrementare rage più volte durante la stessa pressione
        # quando il personaggio è in posizione 3
        self.limb_rage_applied = {}
        # se hai già limb_state / limb_pressed, inizializza così:
        if hasattr(self, "limb_state"):
            self.limb_rage_applied = {name: False for name in self.limb_state}


        # stato arti / controlli (Q/A/O/K)
        self.limb_keys = {
            pygame.K_q: "braccio_sx",
            pygame.K_a: "gamba_sx",
            pygame.K_o: "braccio_dx",
            pygame.K_k: "gamba_dx",
        }
        self.limb_state = {
            "braccio_sx": 0,
            "gamba_sx": 0,
            "braccio_dx": 0,
            "gamba_dx": 0,
        }
        self.limb_pressed = {name: False for name in self.limb_state}
        self.limb_press_start_ms = {name: 0.0 for name in self.limb_state}

        # mappa inversa: arto -> tasto
        self.limb_to_key = {}
        for keycode, limb in self.limb_keys.items():
            self.limb_to_key[limb] = keycode

        # mappa posizioni stelle (8 posizioni da specifica)
        self.star_positions = [
            (647, 518),   # 1 - mano braccio_sx_1
            (1037, 518),  # 2 - mano braccio_dx_1
            (699, 722),   # 3 - piede gamba_sx_1
            (994, 715),   # 4 - piede gamba_dx_1
            (665, 385),   # 5 - mano braccio_sx_2
            (1039, 387),  # 6 - mano braccio_dx_2
            (644, 621),   # 7 - piede gamba_sx_2
            (1042, 598),  # 8 - piede gamba_dx_2
        ]

        # stelle attive
        # ogni stella: {"slot_index": int 0-7, "created_beat": int,
        #               "state": "normal"|"puf", "puf_timer_ms": float}
        self.stars = []
        self.star_last_spawn_beat = -1

        # posizioni "rapide" (al click) per ogni tasto
        self.star_quick_slots = {
            pygame.K_q: [0],  # posizione 1
            pygame.K_o: [1],  # posizione 2
            pygame.K_a: [2],  # posizione 3
            pygame.K_k: [3],  # posizione 4
        }

        # posizioni "hold" (> 1/16 di beat) per ogni tasto
        self.star_hold_slots = {
            pygame.K_q: [4],  # posizione 5
            pygame.K_o: [5],  # posizione 6
            pygame.K_a: [6],  # posizione 7
            pygame.K_k: [7],  # posizione 8
        }

        # buffer colpi ritmo (per mosse multiple)
        self.hit_events_frame = []

        # (in futuro useremo questa per il box messaggi)
        self.message_queue = []
        self.font_messages = load_font(70)
        self.message_last_shift_beat = -1  # ultimo beat gestito per lo shift ogni 4 beat

        self.font_score_label = load_font(70)
        self.font_score_value = load_font(70)
        self.font_star_mul_small = load_font(55)
        self.font_star_mul_big = load_font(82)
        self.font_game_over = load_font(90)
        self.font_game_over_small = load_font(60)

        # caricamento delle immagini di gioco
        self.images = {}
        self._load_images()

        # tre brani musicali
        self.tracks = [
            {"file": os.path.join(MEDIA_DIR, "music_01.mp3"), "bpm": 80},
            {"file": os.path.join(MEDIA_DIR, "music_02.mp3"), "bpm": 100},
            {"file": os.path.join(MEDIA_DIR, "music_03.mp3"), "bpm": 120},
        ]
        self.current_track_index = 0
        self.track_started = False
        self.game_finished = False
        self.countdown_active = True  # prime 4 battute
        self.enable_controls = False

        # tempo
        self.quarter_ms = 0
        self.sixteenth_ms = 0

        # BOX PULSE
        self.pulse_active = False
        self.pulse_alpha = 0
        self.pulse_timer_ms = 0.0
        self.pulse_fade_ms = 200.0  # durata della pulsazione in ms
        self.pulse_last_tick_index = -1  # IMPORTANTE: -1 per far scattare il primo tick

        # Game over
        self.game_over = False
        self.game_over_is_new_record = False

        self._start_track(0)

    def _load_images(self):
        def load_and_scale(name, key=None):
            if key is None:
                key = name
            path = os.path.join(MEDIA_DIR, name)
            try:
                img = pygame.image.load(path).convert_alpha()
                self.images[key] = img
            except Exception as e:
                print(f"Errore caricamento immagine {path}: {e}", file=sys.stderr)
                self.images[key] = None

        # sfondo e sabry
        load_and_scale("bkg_game.png", "bkg_game")
        load_and_scale("sabry_sleeping.png", "sabry_sleeping")
        load_and_scale("sabry_raged.png", "sabry_raged")
        load_and_scale("Bocca.png", "bocca")

        # arti - posizioni 0/1/2/3 come da specifiche
        for i in range(4):
            load_and_scale(f"gamba_dx_{i}.png", f"gamba_dx_{i}")
            load_and_scale(f"gamba_sx_{i}.png", f"gamba_sx_{i}")
            load_and_scale(f"braccio_dx_{i}.png", f"braccio_dx_{i}")
            load_and_scale(f"braccio_sx_{i}.png", f"braccio_sx_{i}")

        # box
        load_and_scale("box_stelle.png", "box_stelle")
        load_and_scale("box_punti.png", "box_punti")
        load_and_scale("box_rage.png", "box_rage")
        load_and_scale("barra_rage_0.png", "barra_rage_0")
        load_and_scale("barra_rage_1.png", "barra_rage_1")
        load_and_scale("barra_rage_2.png", "barra_rage_2")
        load_and_scale("barra_rage_3.png", "barra_rage_3")

        # cuore
        load_and_scale("heart.png", "heart")

        # box pulse
        load_and_scale("box_pulse.png", "box_pulse")
        
        # stelle
        load_and_scale("stella.png", "stella")
        load_and_scale("stella_puf.png", "stella_puf")


    # -------------------- musica e bpm --------------------

    def _start_track(self, index):
        print("=== _start_track chiamata con index:", index)
        if index >= len(self.tracks):
            self._finish_game()
            return

        # Pulisce eventuali USEREVENT rimasti in coda (es. da stop del menu in versioni precedenti)
        pygame.event.get(pygame.USEREVENT)
        # Attiva l'endevent SOLO per le musiche di gioco
        pygame.mixer.music.set_endevent(pygame.USEREVENT)
        
        self.current_track_index = index
        track = self.tracks[index]
        self.quarter_ms = 60000.0 / track["bpm"]
        self.sixteenth_ms = self.quarter_ms / 4.0
        
        # reset stelle a inizio brano
        self.stars = []
        self.star_last_spawn_beat = -1
        
        # reset BOX PULSE a inizio brano
        self.pulse_active = False
        self.pulse_alpha = 0
        self.pulse_timer_ms = 0.0
        self.pulse_last_tick_index = -1
        
        # avvio musica
        try:
            pygame.mixer.music.load(track["file"])
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Errore caricamento brano {track['file']}: {e}", file=sys.stderr)
        self.track_started = True
        self.countdown_active = True
        self.enable_controls = False

    def _on_track_finished(self):
        # chiamato quando finisce un brano
        next_index = self.current_track_index + 1
        if next_index < len(self.tracks):
            self._start_track(next_index)
        else:
            self._finish_game()

    def _finish_game(self):
        self.game_finished = True
        self.game_over = True
        if self.score > self.best_score:
            self.best_score = self.score
            self.game_over_is_new_record = True
        pygame.mixer.music.stop()

    # -------------------- RAGE --------------------

    def _set_rage(self, new_rage: int, increased: bool, current_beat: int | None):
        """
        Imposta il valore di rage, applica clamp 0..3 e aggiorna il beat
        dell'ultimo cambiamento. Se increased=True e new_rage == 3,
        scatena gli effetti di rage massimo.
        """
        new_rage = max(0, min(3, new_rage))
        if new_rage == self.rage:
            return

        old_rage = self.rage
        self.rage = new_rage

        # aggiorna il beat dell'ultimo cambiamento (serve per il decay ogni 4 battute)
        if current_beat is not None:
            self.rage_change_beat = current_beat

        # se siamo appena saliti a 3, applichiamo gli effetti speciali
        if increased and old_rage < 3 and new_rage == 3:
            self._on_rage_max_reached()

    def _on_rage_max_reached(self):
        """
        Effetti quando il rage arriva a 3:
        - sabry_raged + Bocca per 2 secondi
        - -1 vita (se arriva a 0, fine gioco)
        - -10.000 punti * moltiplicatore stelle (usato come intero, minimo 1)
        """
        self.rage_raged_active = True
        self.rage_raged_timer_ms = 0.0

        # penalità punti
        star_mul_int = max(1, int(self.star_multiplier))
        penalty = 10000 * star_mul_int
        new_score = self.score - penalty
        if new_score < 0:
            new_score = 0
        self.score = new_score

        # penalità vite
        if self.lives > 0:
            self.lives -= 1
            if self.lives <= 0:
                # nessuna vita -> fine partita
                self._finish_game()

    def _check_rage_decay(self, current_beat: int):
        """
        Se per 4 battute (16 beat) il rage non è cambiato e non siamo
        in stato sabry_raged, rage scende di 1 (fino a 0).
        """
        if self.rage_raged_active:
            return
        if self.rage <= 0:
            return
        # 4 battute = 16 quarti
        if current_beat - self.rage_change_beat >= 16:
            self._set_rage(self.rage - 1, increased=False, current_beat=current_beat)

    def _check_rage_from_limbs(self, pos_ms: float, current_beat: int):
        """
        Se qualunque tasto viene tenuto per più di mezzo beat e
        l'arto è in posizione 3, aumenta rage di 1 (max 3) una sola
        volta per ogni pressione (come da specifiche).
        """
        if self.quarter_ms <= 0:
            return

        half_beat_ms = self.quarter_ms / 2.0

        if not hasattr(self, "limb_state") or not hasattr(self, "limb_pressed"):
            return

        for limb, pressed in self.limb_pressed.items():
            if not pressed:
                continue

            start = self.limb_press_start_ms.get(limb, 0.0)
            held = max(0.0, pos_ms - start)

            # deve essere tenuto oltre il mezzo beat E in posizione 3
            if (held >= half_beat_ms and
                self.limb_state.get(limb, 0) == 3 and
                not self.limb_rage_applied.get(limb, False)):

                self.limb_rage_applied[limb] = True
                # aumento rage di 1 (max 3)
                self._set_rage(self.rage + 1, increased=True, current_beat=current_beat)

    # -------------------- STELLE --------------------

    def _trigger_star_hit(self, star):
        """
        Trasforma una stella in 'puf' e assegna i punti.
        """
        if star["state"] == "puf":
            return

        star["state"] = "puf"
        star["puf_timer_ms"] = 0.0

        # +100 punti per stella, moltiplicati per star_multiplier (intero)
        star_mul_int = max(1, int(self.star_multiplier))
        delta = 100 * star_mul_int
        new_score = self.score + delta
        if new_score < 0:
            new_score = 0
        self.score = new_score

        # aumento moltiplicatore stelle (+0.1)
        self._increase_star_multiplier(0.1)


    def _check_star_quick_hit(self, keycode, pos_ms: float):
        """
        Colpo 'rapido' alla pressione del tasto:
        Q -> pos 1, O -> pos 2, A -> pos 3, K -> pos 4.
        """
        if not self.stars:
            return

        slots = self.star_quick_slots.get(keycode)
        if not slots:
            return

        for slot_idx in slots:
            for star in self.stars:
                if star["slot_index"] == slot_idx and star["state"] == "normal":
                    self._trigger_star_hit(star)
                    return  # una stella per pressione è sufficiente

    def _check_star_hold_hits(self, pos_ms: float):
        """
        Colpo 'hold': se il tasto è tenuto per più di 1/16 di beat
        e c'è una stella nella posizione 5/6/7/8 corrispondente,
        la facciamo sparire.
        """
        if self.sixteenth_ms <= 0 or not self.stars:
            return

        threshold_ms = self.sixteenth_ms

        for limb, pressed in self.limb_pressed.items():
            if not pressed:
                continue

            start = self.limb_press_start_ms.get(limb, 0.0)
            held = max(0.0, pos_ms - start)
            if held < threshold_ms:
                continue

            keycode = self.limb_to_key.get(limb)
            if keycode is None:
                continue

            slots = self.star_hold_slots.get(keycode)
            if not slots:
                continue

            for slot_idx in slots:
                for star in self.stars:
                    if star["slot_index"] == slot_idx and star["state"] == "normal":
                        self._trigger_star_hit(star)
                        return  # una stella per pressione

    def _update_stars(self, pos_ms: float, current_beat: int, dt_ms: float):
        """
        - Spawna una stella all'inizio di ogni battuta (beat multiplo di 4)
          a partire dal 16° beat (quinta battuta).
        - Aggiorna durata stelle (4 battute) e durata animazione 'puf'
          (1/16 di beat).
        """
        # SPAWN
        if current_beat >= 16:
            if current_beat % 4 == 0 and current_beat != self.star_last_spawn_beat:
                # posizioni libere
                occupied = {s["slot_index"] for s in self.stars}
                free_slots = [
                    i for i in range(len(self.star_positions)) if i not in occupied
                ]
                if free_slots:
                    slot_idx = random.choice(free_slots)
                    self.stars.append(
                        {
                            "slot_index": slot_idx,
                            "created_beat": current_beat,
                            "state": "normal",
                            "puf_timer_ms": 0.0,
                        }
                    )
                    self.star_last_spawn_beat = current_beat

        # AGGIORNAMENTO VITA / PUF
        puf_duration_ms = self.sixteenth_ms if self.sixteenth_ms > 0 else 200.0
        new_stars = []
        for star in self.stars:
            if star["state"] == "normal":
                # 4 battute = 16 beat
                if current_beat - star["created_beat"] >= 16:
                    # stella scaduta → penalità moltiplicatore
                    self._decrease_star_multiplier(0.5)
                    continue
                else:
                    new_stars.append(star)
            elif star["state"] == "puf":
                star["puf_timer_ms"] += dt_ms
                if star["puf_timer_ms"] >= puf_duration_ms:
                    # fine animazione puf -> stella rimossa
                    continue
                else:
                    new_stars.append(star)

        self.stars = new_stars

    # -------------------- STAR MULTIPLIER --------------------

    def _increase_star_multiplier(self, amount):
        """Aumenta star_multiplier e controlla passaggi di livello intero."""
        old = self.star_multiplier
        self.star_multiplier = min(5.0, self.star_multiplier + amount)

        old_int = int(old)
        new_int = int(self.star_multiplier)

        # Se si supera un nuovo livello intero → messaggio "Xn"
        if new_int > old_int:
            self._add_message(f"X{new_int}", GIALLO_CHIARO)

    def _decrease_star_multiplier(self, amount):
        """Riduce star_multiplier (senza scendere sotto 1.0)."""
        old = self.star_multiplier
        self.star_multiplier = max(1.0, self.star_multiplier - amount)

        old_int = int(old)
        new_int = int(self.star_multiplier)

        # Se si supera verso il basso un nuovo livello intero → messaggio "Xn"
        if new_int < old_int:
            self._add_message(f"X{new_int}", GIALLO_CHIARO)


    # -------------------- BOX PULSE --------------------

    def _update_pulse(self, pos_ms: float, dt_ms: float):
        """
        Gestisce la comparsa e la dissolvenza del box_pulse.

        - Il tempo è diviso in 'tick' da 1/8 di beat (quarter_ms / 2).
        - Ogni battuta (4/4) ha 8 tick:
            tick 0 -> inizio 1° beat
            tick 3 -> 4° ottavo (fra 2° e 3° beat)
            tick 4 -> inizio 3° beat
            tick 7 -> 8° ottavo (fine battuta)
        - Ai tick 0, 3, 4, 7 facciamo comparire il box_pulse con alpha=255
          e poi lo facciamo svanire velocemente.
        """
        if self.quarter_ms <= 0:
            return

        tick_ms = self.quarter_ms / 2.0  # 1/8 di beat
        if tick_ms <= 0:
            return

        tick_index = int(pos_ms / tick_ms)

        # Triggeriamo una nuova pulsazione SOLO quando cambiamo tick
        if tick_index != self.pulse_last_tick_index:
            self.pulse_last_tick_index = tick_index
            step_in_bar = tick_index % 8  # 8 ottavi per battuta (4/4)

            # 1° beat, 4° ottavo, 3° beat, 8° ottavo
            if step_in_bar in (0, 3, 4, 7):
                self.pulse_active = True
                self.pulse_alpha = 255
                self.pulse_timer_ms = 0.0

        # Gestione fade-out
        if self.pulse_active:
            self.pulse_timer_ms += dt_ms
            fade_ms = self.pulse_fade_ms
            t = self.pulse_timer_ms / fade_ms
            if t >= 1.0:
                self.pulse_active = False
                self.pulse_alpha = 0
            else:
                self.pulse_alpha = int(255 * (1.0 - t))



    # -------------------- supporto ritmo / controlli --------------------

    def _compute_rhythm_hit(self, pos_ms: float):
        """
        Calcola la qualità del colpo (Perfect/Great/Good/Bad) in base
        alla distanza dal sedicesimo più vicino, come da specifiche.
        Ritorna (quality, base_points).
        """
        if self.sixteenth_ms <= 0:
            return None

        # indice del sedicesimo più vicino
        sixteenth_index = round(pos_ms / self.sixteenth_ms)
        sixteenth_time_ms = sixteenth_index * self.sixteenth_ms
        delta = abs(pos_ms - sixteenth_time_ms)

        # soglie da specifica
        # Perfect: ±25ms → +100
        # Great:  ±45ms → +50
        # Good:   ±75ms → +10
        # Bad:  > 75ms  → -5  (punteggio non sotto 0 dopo somma)
        if delta <= 25:
            return ("perfect", 100)
        elif delta <= 45:
            return ("great", 50)
        elif delta <= 75:
            return ("good", 10)
        else:
            return ("bad", -5)

    def _add_message(self, text, color):
        """
        Aggiunge un messaggio nel box:
        - max 5 righe
        - se arriva il 6° messaggio, il primo viene eliminato subito
        """
        if len(self.message_queue) >= 5:
            # elimina il messaggio più vecchio per fare spazio al nuovo
            self.message_queue.pop(0)

        self.message_queue.append({"text": text, "color": color})

    # -------------------- BOX MESSAGGI --------------------

    def _update_messages(self, current_beat: int):
        """
        Ogni 4 beat scompare il primo messaggio (se presente)
        e gli altri 'salgono' semplicemente restando nelle righe più alte.
        Usiamo il beat globale del brano, non il tempo di creazione.
        """
        if not self.message_queue:
            return
        if current_beat <= 0:
            return

        # ogni 4 beat (0–3, 4–7, 8–11, ...)
        if current_beat % 4 != 0:
            return

        # evita di processare più volte lo stesso beat
        if self.message_last_shift_beat == current_beat:
            return

        self.message_last_shift_beat = current_beat

        # rimuove la riga in alto (se c'è almeno un messaggio)
        if self.message_queue:
            self.message_queue.pop(0)

    def _process_hit_events(self):
        """
        Applica il punteggio per i colpi raccolti in questo frame,
        gestendo anche il moltiplicatore mosse multiple come da specifica.
        """
        if not self.hit_events_frame:
            return

        hits = self.hit_events_frame
        self.hit_events_frame = []

        # Se tutti hanno stessa qualità → moltiplicatore mosse multiple
        qualities = {h["quality"] for h in hits}
        total_base = 0
        msg_quality = None
        count = len(hits)

        if len(hits) == 1:
            # caso singolo colpo
            h = hits[0]
            total_base = h["base_points"]
            msg_quality = h["quality"]
        else:
            if len(qualities) == 1:
                # stessa qualità → (somma punti) * n
                msg_quality = hits[0]["quality"]
                base_sum = sum(h["base_points"] for h in hits)
                total_base = base_sum * count
            else:
                # qualità diverse → somma semplice
                total_base = sum(h["base_points"] for h in hits)
                # per i messaggi genereremo uno per colpo

        # Applica star multiplier (parte intera, minimo 1)
        star_mul_int = max(1, int(self.star_multiplier))
        delta = total_base * star_mul_int

        # aggiorna punteggio senza scendere sotto 0
        new_score = self.score + delta
        if new_score < 0:
            new_score = 0
        self.score = new_score

        # Messaggi nel box (per ora solo accodati)
        def quality_to_text_color(q):
            if q == "perfect":
                return "PERFECT!!!", VERDE_SCURO
            if q == "great":
                return "GREAT!", VERDE_CHIARO
            if q == "good":
                return "GOOD", GIALLO_CHIARO
            if q == "bad":
                return "BAD", ROSSO_CHIARO
            return None, None

        if len(hits) == 1:
            text, color = quality_to_text_color(msg_quality)
            if text:
                self._add_message(text, color)
        else:
            if len(qualities) == 1:
                # un solo messaggio con Xn (PERFECT!!! x3, ecc.)
                text, color = quality_to_text_color(msg_quality)
                if text:
                    if count > 1:
                        text = f"{text} x{count}"
                    self._add_message(text, color)
            else:
                # qualità diverse → un messaggio per colpo
                for h in hits:
                    text, color = quality_to_text_color(h["quality"])
                    if text:
                        self._add_message(text, color)

    def _update_limb_states(self, pos_ms: float):
        """
        Aggiorna l'immagine (0/1/2/3) in base alla durata di pressione:
        - subito: 1
        - > 1/16 di beat: 2
        - > 1/8 di beat:  3
        """
        sixteenth_ms = self.sixteenth_ms
        eighth_ms = self.quarter_ms / 2.0 if self.quarter_ms > 0 else 0

        for limb, pressed in self.limb_pressed.items():
            if not pressed:
                continue
            start = self.limb_press_start_ms[limb]
            held = max(0.0, pos_ms - start)

            if eighth_ms > 0 and held >= eighth_ms:
                self.limb_state[limb] = 3
            elif sixteenth_ms > 0 and held >= sixteenth_ms:
                self.limb_state[limb] = 2
            else:
                self.limb_state[limb] = 1

    def _on_rhythm_key_down(self, key_char):
        """
        Gestisce:
        - inizio animazione arto (stato=1)
        - calcolo punteggio ritmo (accodato a hit_events_frame)
        """
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return

        limb = self.limb_keys.get(key_char)
        if limb:
            if not self.limb_pressed[limb]:
                self.limb_pressed[limb] = True
                self.limb_press_start_ms[limb] = float(pos_ms)
                self.limb_state[limb] = 1
                self.limb_rage_applied[limb] = False  # nuova pressione -> Rage ancora non applicato

        hit = self._compute_rhythm_hit(float(pos_ms))
        if hit is not None:
            quality, base_points = hit
            self.hit_events_frame.append(
                {
                    "quality": quality,
                    "base_points": base_points,
                }
            )
            
        # colpo rapido sulle stelle (posizioni 1–4)
        self._check_star_quick_hit(key_char, pos_ms)
       

    def _on_rhythm_key_up(self, key_char):
        limb = self.limb_keys.get(key_char)
        if limb:
            self.limb_pressed[limb] = False
            self.limb_state[limb] = 0
            self.limb_rage_applied[limb] = False


    # -------------------- input e logica --------------------

    def handle_event(self, event):
        if self.game_over:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back_to_menu"
            return None

        if event.type == pygame.USEREVENT:
            # evento di fine musica
            self._on_track_finished()

        # Durante il countdown i controlli di gioco non funzionano
        if not self.enable_controls:
            return None

        # CONTROLLI RITMO Q/A/O/K
        if event.type == pygame.KEYDOWN:
            if event.key in self.limb_keys:
                self._on_rhythm_key_down(event.key)

        elif event.type == pygame.KEYUP:
            if event.key in self.limb_keys:
                self._on_rhythm_key_up(event.key)

        return None

    def _handle_rhythm_key(self, key):
        """
        TODO: logica completa del punteggio ritmo.
        Per ora aggiungiamo dei punti "finti" per avere un feedback.
        """
        # esempio provvisorio: +10 punti a ogni pressione
        # Sostituisci con la logica di beat / distance ms, ecc.
        base_points = 10
        self._add_points(base_points)

    def _add_points(self, base_points):
        # TODO: applicare moltiplicatore stelle, ecc.
        self.score = max(0, self.score + base_points)

    def update(self, dt_ms):
        if self.game_over:
            return

        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            self._on_track_finished()
            return

        current_beat = int(pos_ms / self.quarter_ms) if self.quarter_ms > 0 else 0

        # aggiornamento BOX PULSE a tempo
        self._update_pulse(pos_ms, dt_ms)

        # aggiornamento stelle (spawn + durata/puf)
        self._update_stars(pos_ms, current_beat, dt_ms)

        # aggiornamento BOX MESSAGGI (shift ogni 4 beat)
        self._update_messages(current_beat)

        # countdown sui primi 16 beat (4 battute)
        if self.countdown_active:
            if current_beat >= 16:
                self.countdown_active = False
                self.enable_controls = True

        # aggiornamento stato Rage "raged" (sabry_raged/Bocca per 2 secondi)
        if self.rage_raged_active:
            self.rage_raged_timer_ms += dt_ms
            if self.rage_raged_timer_ms >= 2000:
                # dopo 2 secondi torna sleeping e rage scende a 2 (se il gioco non è finito)
                self.rage_raged_active = False
                self.rage_raged_timer_ms = 0.0
                if not self.game_over:
                    self._set_rage(2, increased=False, current_beat=current_beat)

        # se i controlli sono abilitati, aggiornare arti, hit ritmo e Rage
        if self.enable_controls and not self.game_over:
            if hasattr(self, "_update_limb_states"):
                self._update_limb_states(pos_ms)
            if hasattr(self, "_process_hit_events"):
                self._process_hit_events()

            # check Rage da tasti tenuti troppo a lungo in posizione 3
            self._check_rage_from_limbs(pos_ms, current_beat)
            
            # check stelle 'hold' (posizioni 5–8)
            self._check_star_hold_hits(pos_ms)
            
        # decay Rage ogni 4 battute senza cambiamenti
        self._check_rage_decay(current_beat)

    # -------------------- disegno --------------------

    def _draw_countdown(self):
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return
        beat = int(pos_ms / self.quarter_ms)
        if beat >= 16:
            return
        # 0..15 -> 4 numeri, uno ogni 4 beat
        index = beat // 4  # 0..3
        number = 4 - index
        # leggero "pulse" sul carattere
        beat_in_group = beat % 4  # 0..3
        scale = 1.0 + 0.05 * math.sin(beat_in_group * math.pi / 2.0)
        font_size = int(100 * scale)
        font = load_font(font_size)
        blit_text_center(self.screen, str(number), font, GIALLO_CHIARO, SCREEN_HEIGHT // 2)

    def _draw_messages(self):
        """
        Disegna i messaggi nel box a sinistra.
        Coordinate da specifica: primo testo a (56, 204),
        font Starborn 70, max 5 righe.
        """
        if not self.message_queue:
            return

        if not hasattr(self, "font_messages"):
            return

        x = 56
        y = 204
        line_height = self.font_messages.get_linesize()

        for msg in self.message_queue:
            text = msg["text"]
            color = msg["color"]
            surf = self.font_messages.render(text, True, color)
            self.screen.blit(surf, (x, y))
            y += line_height

    def draw(self):
        if self.game_over:
            self._draw_game_over()
            return

        # sfondo e personaggio
        bkg = self.images.get("bkg_game")
        if bkg is not None:
            self.screen.blit(bkg, (0, 0))
        else:
            self.screen.fill(NERO)

        # sabry: sleeping di base, raged quando rage == 3 per 2 secondi
        if self.rage_raged_active:
            sabry = self.images.get("sabry_raged") or self.images.get("sabry_sleeping")
        else:
            sabry = self.images.get("sabry_sleeping")

        if sabry is not None:
            self.screen.blit(sabry, (0, 0))

        # Bocca compare solo durante sabry_raged
        if self.rage_raged_active:
            bocca = self.images.get("bocca")
            if bocca is not None:
                self.screen.blit(bocca, (872, 541))

        # arti (posizioni 0/1/2/3 in base a limb_state)
        def blit_limb(name_base, state, pos):
            key = f"{name_base}_{state}"
            img = self.images.get(key)
            if img is None:
                # fallback a _0 se manca l'immagine specifica
                img = self.images.get(f"{name_base}_0")
            if img is not None:
                self.screen.blit(img, pos)

        blit_limb("gamba_dx", self.limb_state["gamba_dx"], (892, 612))
        blit_limb("gamba_sx", self.limb_state["gamba_sx"], (600, 623))
        blit_limb("braccio_dx", self.limb_state["braccio_dx"], (935, 326))
        blit_limb("braccio_sx", self.limb_state["braccio_sx"], (564, 327))

        # STELLE
        if self.stars:
            img_star = self.images.get("stella")
            img_puf = self.images.get("stella_puf")
            for star in self.stars:
                if star["state"] == "puf":
                    img = img_puf
                else:
                    img = img_star
                if img is None:
                    continue
                x, y = self.star_positions[star["slot_index"]]
                self.screen.blit(img, (x, y))

        # box_stelle at (0,895)
        if self.images.get("box_stelle"):
            self.screen.blit(self.images["box_stelle"], (0, 895))
        # box_punti at (516,0)
        if self.images.get("box_punti"):
            self.screen.blit(self.images["box_punti"], (516, 0))
        # box_rage at (1382,880)
        if self.images.get("box_rage"):
            self.screen.blit(self.images["box_rage"], (1382, 880))
        # barra Rage in base al valore di self.rage (0..3)
        rage_key = f"barra_rage_{self.rage}"
        barra = self.images.get(rage_key)
        if barra is not None:
            self.screen.blit(barra, (1414, 975))

        # vite (3 cuori)
        heart = self.images.get("heart")
        if heart is not None:
            positions = [(36, 29), (166, 29), (296, 29)]
            for i in range(self.lives):
                self.screen.blit(heart, positions[i])

        # SCORE label con doppio contorno
        blit_text(self.screen, "SCORE", self.font_score_label, AZZURRO_CHIARO, 554, 47, align="left")
        blit_text(self.screen, "SCORE", self.font_score_label, AZZURRO_SCURO, 552, 45, align="left")

        # punteggio con doppio contorno
        score_str = format_score(self.score)
        blit_text(self.screen, score_str, self.font_score_value, AZZURRO_CHIARO, 1327, 47, align="right")
        blit_text(self.screen, score_str, self.font_score_value, AZZURRO_SCURO, 1325, 45, align="right")

        # moltiplicatore stelle piccolo (decimali)
        mul_dec = f"{self.star_multiplier:.1f}"
        blit_text(self.screen, mul_dec, self.font_star_mul_small, GIALLO_CHIARO, 166, 970, align="left")
        blit_text(self.screen, mul_dec, self.font_star_mul_small, GIALLO_SCURO, 164, 968, align="left")

        # moltiplicatore stelle intero
        mul_int = f"X{int(self.star_multiplier)}"
        blit_text(self.screen, mul_int, self.font_star_mul_big, GIALLO_CHIARO, 492, 938, align="right")
        blit_text(self.screen, mul_int, self.font_star_mul_big, GIALLO_SCURO, 490, 936, align="right")

        # BOX MESSAGGI
        self._draw_messages()

        # BOX PULSE a (1535, 0) con alpha variabile
        if self.pulse_active:
            pulse_img = self.images.get("box_pulse")
            if pulse_img is not None and self.pulse_alpha > 0:
                img = pulse_img.copy()
                img.set_alpha(self.pulse_alpha)
                self.screen.blit(img, (1535, 0))

        # countdown se attivo
        if self.countdown_active:
            self._draw_countdown()

    def _draw_game_over(self):
        # sfondo bianco + bkg_bianco se vuoi
        self.screen.fill(BIANCO)
        blit_text_center(self.screen, "GAME OVER", self.font_game_over, BLU_SCURO, SCREEN_HEIGHT // 2 - 60)

        txt = f"HAI OTTENUTO {format_score(self.score)} PUNTI"
        blit_text_center(self.screen, txt, self.font_game_over_small, BLU_SCURO, SCREEN_HEIGHT // 2 + 10)

        if self.game_over_is_new_record:
            blit_text_center(self.screen, "HAI SUPERATO IL RECORD", self.font_game_over_small, VERDE_SCURO,
                             SCREEN_HEIGHT // 2 + 80)


# ============================================================
# LOOP PRINCIPALE
# ============================================================

def main():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("game_01_dancing")

    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        pygame.FULLSCREEN | pygame.SCALED
    )
    clock = pygame.time.Clock()

    # Evento di fine musica
    #pygame.mixer.music.set_endevent(pygame.USEREVENT)

    # Lettura parametri e configurazione
    best_score = get_arg_score(sys.argv)
    config = GameConfig()

    intro_manager = IntroManager(screen)
    menu = Menu(screen)
    game_core = None  # creato quando serve

    # stato globale
    current_scene = None
    frozen_background = None  # snapshot per menu

    # Se primorun True: partenza con intro
    if config.primorun:
        current_scene = SCENE_INTRO
        intro_manager.start_music()
    else:
        current_scene = SCENE_MENU
        menu.open(
            can_continue=False,
            continue_target=None,
            auto_background=True,
            frozen_background=None
        )

    instructions_image = None
    try:
        instructions_image = pygame.image.load(os.path.join(MEDIA_DIR, "help.png")).convert_alpha()
        instructions_image = pygame.transform.smoothscale(instructions_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except Exception as e:
        print(f"Errore caricamento help.png: {e}", file=sys.stderr)

    running = True

    while running:
        dt_ms = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # ESC globale: apre menu (se non siamo già nel menu o game over instructions)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if current_scene == SCENE_INTRO:
                    # congelo lo sfondo corrente dell'intro
                    frozen_background = screen.copy()
                    menu.open(
                        can_continue=True,
                        continue_target=SCENE_INTRO,
                        auto_background=False,
                        frozen_background=frozen_background
                    )
                    current_scene = SCENE_MENU

                elif current_scene == SCENE_GAME:
                    frozen_background = screen.copy()
                    menu.open(
                        can_continue=True,
                        continue_target=SCENE_GAME,
                        auto_background=False,
                        frozen_background=frozen_background
                    )
                    current_scene = SCENE_MENU

                elif current_scene == SCENE_GAME_OVER:
                    # ESC da game over porta al menu con bkg_menu e musica
                    menu.open(
                        can_continue=False,
                        continue_target=None,
                        auto_background=True,
                        frozen_background=None
                    )
                    current_scene = SCENE_MENU

            # Gestione scene specifiche
            if current_scene == SCENE_MENU:
                action = menu.handle_event(event)
                if action == "new_game":
                    menu.close()
                    # creo una nuova partita
                    game_core = GameCore(screen, best_score)
                    current_scene = SCENE_GAME

                elif action == "continue":
                    menu.close()
                    if menu.continue_target == SCENE_INTRO:
                        current_scene = SCENE_INTRO
                    elif menu.continue_target == SCENE_GAME:
                        current_scene = SCENE_GAME

                elif action == "replay_intro":
                    menu.close()
                    intro_manager.reset()
                    intro_manager.start_music()
                    current_scene = SCENE_INTRO

                elif action == "instructions":
                    current_scene = SCENE_INSTRUCTIONS

                elif action == "exit":
                    running = False

            elif current_scene == SCENE_INTRO:
                # event gestiti solo per ESC (già sopra) – niente altro
                pass

            elif current_scene == SCENE_GAME:
                if game_core:
                    result = game_core.handle_event(event)
                    if result == "back_to_menu":
                        # fine gioco -> torna a menu
                        best_score = game_core.best_score
                        menu.open(
                            can_continue=False,
                            continue_target=None,
                            auto_background=True,
                            frozen_background=None
                        )
                        current_scene = SCENE_MENU

            elif current_scene == SCENE_INSTRUCTIONS:
                # qualsiasi tasto o click chiude le istruzioni e torna al menu
                if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN):
                    current_scene = SCENE_MENU

        # ----------------------------------------------------
        # UPDATE
        # ----------------------------------------------------
        if current_scene == SCENE_INTRO:
            intro_manager.update(dt_ms)
            if intro_manager.finished:
                # fine intro: musica intro sfuma e non riparte più
                intro_manager.stop_music(fade_ms=2000)  # fade di 2 secondi

                # primorun diventa False e si apre menu con musica propria
                config.save_primorun_false()
                menu.open(
                    can_continue=False,
                    continue_target=None,
                    auto_background=True,
                    frozen_background=None
                )
                current_scene = SCENE_MENU


        elif current_scene == SCENE_MENU:
            menu.update(dt_ms)

        elif current_scene == SCENE_GAME and game_core:
            game_core.update(dt_ms)
            if game_core.game_over and not game_core.game_finished:
                # se mai avessimo logica diversa, qui potremmo spostare
                pass
            if game_core.game_finished:
                # aggiornamento best_score globale
                best_score = game_core.best_score
                current_scene = SCENE_GAME_OVER

        elif current_scene == SCENE_INSTRUCTIONS:
            # nessun update particolare
            pass

        elif current_scene == SCENE_GAME_OVER:
            # nessun update particolare
            pass

        # ----------------------------------------------------
        # DRAW
        # ----------------------------------------------------
        if current_scene == SCENE_INTRO:
            intro_manager.draw()

        elif current_scene == SCENE_MENU:
            menu.draw()

        elif current_scene == SCENE_GAME and game_core:
            game_core.draw()

        elif current_scene == SCENE_INSTRUCTIONS:
            if instructions_image is not None:
                screen.blit(instructions_image, (0, 0))
            else:
                screen.fill(BIANCO)
                font = load_font(40)
                blit_text_center(screen, "ISTRUZIONI NON DISPONIBILI", font, BLU_SCURO, SCREEN_HEIGHT // 2)

        elif current_scene == SCENE_GAME_OVER and game_core:
            game_core.draw()

        pygame.display.flip()

    pygame.quit()
    # quando esco, torno a Jacoplay passando il best_score corrente
    sys.exit(best_score)


if __name__ == "__main__":
    main()

import os
import sys
import json
import time
import pygame
import subprocess

try:
    import vlc
except Exception:
    vlc = None

VERDE_SCURO = (150, 193, 29)
VERDE_CHIARO = (217, 242, 208)
GRIGIO = (127, 127, 127)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SEARCH_ROOTS = [os.getcwd(), BASE_DIR, os.path.dirname(BASE_DIR)]

def _first_existing_path(*parts):
    for root in _SEARCH_ROOTS:
        p = os.path.join(root, *parts)
        if os.path.exists(p):
            return p
    return os.path.join(os.getcwd(), *parts)

DATA_DIR = _first_existing_path("jacoplay_data")
MEDIA_DIR = _first_existing_path("jacoplay_media")
GAMES_FILE = _first_existing_path("jacoplay_data", "games.properties")
MENU_FILE = _first_existing_path("jacoplay_data", "jacoplay.properties")
THUMBS_DIR = _first_existing_path("jacoplay_media", "thumbs")
FONT_PATH = _first_existing_path("jacoplay_media", "Ov3Read.ttf")

def resolve_media_path(filename):
    return _first_existing_path("jacoplay_media", filename)

def safe_image_load(path, size=(1, 1), alpha=True, fill_color=(0, 0, 0, 0)):
    try:
        if os.path.exists(path):
            img = pygame.image.load(path)
            return img.convert_alpha() if alpha else img.convert()
    except Exception:
        pass
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill(fill_color)
    return surf

pygame.init()
pygame.mixer.quit()
screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("Jacoplay")
clock = pygame.time.Clock()

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_font(size: int) -> pygame.font.Font:
    if os.path.exists(FONT_PATH):
        try:
            return pygame.font.Font(FONT_PATH, size)
        except Exception:
            pass
    return pygame.font.SysFont("Arial", size)

FONT_40 = load_font(40)
FONT_36 = load_font(36)
FONT_18 = load_font(30)

# ----------------------------
# Musica di sottofondo menu
# ----------------------------
MUSIC_PATH = resolve_media_path("jacoplay_ost_main.mp3")

def start_menu_music():
    """Avvia la musica di sottofondo in loop (-1) se il file esiste."""
    if not os.path.exists(MUSIC_PATH):
        return
    try:
        # Inizializza mixer se necessario
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.set_volume(1.0)
        # loop=-1 per riproduzione continua
        pygame.mixer.music.play(-1)
    except Exception:
        # In caso di problemi con l'audio, semplicemente ignora
        pass

def fadeout_menu_music_and_wait(ms=2000):
    """Fa il fadeout della musica in ms millisecondi e aspetta la fine del fade."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.fadeout(ms)
            pygame.time.delay(ms)
        else:
            # Se non c'è musica, aspetta comunque per mantenere la tempistica
            pygame.time.delay(ms)
    except Exception:
        pygame.time.delay(ms)

def stop_menu_music():
    """Ferma immediatamente la musica di sottofondo."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass

def render_text_box(text: str, font: pygame.font.Font, color, box_rect: pygame.Rect, line_spacing=4, align="center"):
    """Rende un testo con word-wrap nel box, supportando '\n' come a capo esplicito.

    - '\n' nel testo forza un nuovo paragrafo.
    - L'allineamento può essere 'center' o 'left'.
    """
    if not text:
        return []

    # Rimuove CR ed esplode in paragrafi sui newline reali
    text = text.replace("\r", "")
    paragraphs = text.split("\n")  # '\n' nel JSON diventa davvero a capo qui

    lines = []
    for para in paragraphs:
        # Se il paragrafo è vuoto, aggiunge una riga vuota (riga bianca)
        if para == "":
            lines.append("")
            continue

        words = para.split(" ")
        cur = ""
        for w in words:
            test = (cur + (" " if cur else "") + w)
            if font.size(test)[0] <= box_rect.width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                # Gestione parola più lunga del box
                if font.size(w)[0] > box_rect.width:
                    slice_w = ""
                    for ch in w:
                        if font.size(slice_w + ch)[0] <= box_rect.width:
                            slice_w += ch
                        else:
                            lines.append(slice_w)
                            slice_w = ch
                    cur = slice_w
                else:
                    cur = w
        if cur != "":
            lines.append(cur)

    surfaces = []
    y = box_rect.top
    for line in lines:
        surf = font.render(line, True, color)
        if align == "center":
            x = box_rect.left + (box_rect.width - surf.get_width()) // 2
        else:  # align == "left"
            x = box_rect.left
        surfaces.append((surf, (x, y)))
        y += surf.get_height() + line_spacing
        if y > box_rect.bottom:
            break
    return surfaces


class ImageButton:
    def __init__(self, off_path, on_path, pos, fallback_size=(180, 64)):
        self.off_img = safe_image_load(off_path, size=fallback_size)
        self.on_img = safe_image_load(on_path, size=fallback_size)
        self.image = self.off_img
        self.rect = self.image.get_rect(topleft=pos)
        self.hover = False

    def update(self, mouse_pos):
        hovering = self.rect.collidepoint(mouse_pos)
        if hovering != self.hover:
            self.hover = hovering
            self.image = self.on_img if self.hover else self.off_img

    def draw(self, target):
        target.blit(self.image, self.rect.topleft)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

def modal_popup(message: str, tipo: int) -> bool:
    background_snapshot = screen.copy()
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 100))
    bkg_box = safe_image_load(resolve_media_path("bkg_box.png"), size=(800, 500))

    btn_ok = ImageButton(
        resolve_media_path("btn_ok_off.png"),
        resolve_media_path("btn_ok_on.png"),
        (849, 660) if tipo == 1 else (680, 660),
    )
    btn_cancel = None
    if tipo == 2:
        btn_cancel = ImageButton(
            resolve_media_path("btn_annulla_off.png"),
            resolve_media_path("btn_annulla_on.png"),
            (1018, 660),
        )

    box_pos = (560, 290)
    text_rect = pygame.Rect(590, 320, 740, 300)

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if btn_ok.handle_event(event):
                return True
            if btn_cancel and btn_cancel.handle_event(event):
                return False

        btn_ok.update(mouse_pos)
        if btn_cancel:
            btn_cancel.update(mouse_pos)

        screen.blit(background_snapshot, (0, 0))
        screen.blit(overlay, (0, 0))
        screen.blit(bkg_box, box_pos)

        for surf, pos in render_text_box(message, FONT_40, VERDE_SCURO, text_rect):
            screen.blit(surf, pos)

        btn_ok.draw(screen)
        if btn_cancel:
            btn_cancel.draw(screen)

        pygame.display.flip()
        clock.tick(60)




# ----------------------------
# VLC video intro
# ----------------------------

def play_intro_video():
    intro_path = resolve_media_path("intro.mp4")
    if not os.path.exists(intro_path):
        return
    if vlc is None:
        return
    try:
        instance = vlc.Instance()
        player = instance.media_player_new()
        media = instance.media_new(intro_path)
        player.set_media(media)
        player.set_fullscreen(True)
        player.play()

        # Attendi avvio
        time.sleep(0.3)
        # Attendi fine
        while True:
            state = player.get_state()
            if state in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
                break
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    player.stop()
                    pygame.quit()
                    sys.exit(0)
            clock.tick(60)
        player.stop()
    except Exception:
        pass


# ----------------------------
# Caricamento proprietà e giochi
# ----------------------------

def load_menu_properties():
    data = load_json(MENU_FILE, {"primorun": True})
    # Normalizza booleano
    primorun = bool(data.get("primorun", True))
    return {"primorun": primorun}


def set_menu_primorun(value: bool):
    data = load_menu_properties()
    data["primorun"] = bool(value)
    save_json(MENU_FILE, data)


def load_games():
    """
    Carica i giochi da `games.properties` rendendosi tollerante a vari formati:
    - lista di dict
    - dict con chiave "games"
    - dict mappando nome->dict
    - lista con elementi stringa JSON (NDJSON)
    - stringa intera con più righe JSON
    - **formato .properties / INI-like**: blocchi di chiavi `chiave=valore` separati da righe vuote
    Gli attributi supportati: Titolo/Nome/Stato/Posizione/Descrizione/Punteggio.
    """
    raw = load_json(GAMES_FILE, None)

    def as_list_from_properties(text: str):
        records = []
        cur = {}
        last_key = None
        for line in text.splitlines():
            s = line.strip()
            if not s:
                if cur:
                    records.append(cur)
                    cur = {}
                continue
            if s.startswith("#") or s.startswith(";"):
                continue
            if "=" in s:
                k, v = s.split("=", 1)
                cur[k.strip()] = v.strip()
                last_key = k.strip()
            else:
                # Supporto multilinea: righe senza '=' vengono aggiunte alla descrizione (con vero newline)
                if last_key == "Descrizione":
                    cur["Descrizione"] = cur.get("Descrizione", "")
                    if cur["Descrizione"]:
                        cur["Descrizione"] += "\n" + s
                    else:
                        cur["Descrizione"] = s
        if cur:
            records.append(cur)
        return records

    # Normalizza in una lista di record grezzi
    items = []
    if isinstance(raw, dict) and "games" in raw:
        items = raw.get("games", [])
    elif isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = [v for v in raw.values()]
    elif isinstance(raw, str):
        # prova JSON intero
        try:
            val = json.loads(raw)
            if isinstance(val, list):
                items = val
            elif isinstance(val, dict) and "games" in val:
                items = val["games"]
            elif isinstance(val, dict):
                items = [v for v in val.values()]
            else:
                items = []
        except Exception:
            # tenta NDJSON
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    items.append(obj)
                except Exception:
                    pass
            # se ancora vuoto, prova formato properties
            if not items:
                items = as_list_from_properties(raw)
    else:
        # se non è leggibile come JSON, prova a caricare il file come testo e interpretarlo come .properties
        try:
            with open(GAMES_FILE, "r", encoding="utf-8") as f:
                txt = f.read()
            items = as_list_from_properties(txt)
        except Exception:
            items = []

    games = []
    for i, g in enumerate(items):
        # Se l'elemento è una stringa, prova a interpretarla come JSON
        if isinstance(g, str):
            try:
                g = json.loads(g)
            except Exception:
                # potrebbe essere una riga di tipo properties singola: la ignoriamo qui
                continue
        if not isinstance(g, dict):
            continue

        def _to_int(v, default=0):
            try:
                return int(v)
            except Exception:
                return default

        def _to_bool(v, default=False):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                s = v.strip().lower()
                if s in {"true", "1", "si", "sì", "yes", "y"}:
                    return True
                if s in {"false", "0", "no", "n"}:
                    return False
            if isinstance(v, (int, float)):
                return bool(v)
            return default

        games.append({
            "Titolo": g.get("Titolo", g.get("titolo", g.get("title", ""))),
            "Nome": g.get("Nome", g.get("nome", g.get("name", ""))),
            "Stato": _to_bool(g.get("Stato", g.get("stato", g.get("enabled", False)))),
            "Posizione": _to_int(g.get("Posizione", g.get("posizione", g.get("position", i + 1)))),
            "Descrizione": g.get("Descrizione", g.get("descrizione", g.get("description", ""))),
            "Punteggio": _to_int(g.get("Punteggio", g.get("punteggio", g.get("score", 0)))),
        })

    # Se ancora vuoto, crea un placeholder per evitare UI "vuota"
    if not games:
        games = [{
            "Titolo": "Nessun gioco trovato",
            "Nome": "",
            "Stato": False,
            "Posizione": 1,
            "Descrizione": "Assicurati che 'jacoplay_data/games.properties' contenga giochi in formato JSON o properties.",
            "Punteggio": 0,
        }]

    games.sort(key=lambda x: x["Posizione"])
    return games


def save_games(games):
    # Manteniamo struttura semplice come lista
    save_json(GAMES_FILE, games)


# ----------------------------
# Helpers per path gioco
# ----------------------------

def resolve_game_script(name: str):
    # Esistono due convenzioni possibili: jacoplay_game_ [singolare] o jacoplay_games [plurale]
    # 1) jacoplay_game_[nome]/game_[nome].py
    p1 = os.path.join(f"jacoplay_game_{name}", f"game_{name}.py")
    if os.path.exists(p1):
        return p1
    # 2) jacoplay_games/game_[name]/game_[name].py
    p2 = os.path.join("jacoplay_games", f"game_{name}", f"game_{name}.py")
    if os.path.exists(p2):
        return p2
    return p1  # fallback default


# ----------------------------
# Disegno elementi del menu
# ----------------------------
class MenuUI:
    def __init__(self, games):
        self.games = games
        # Gioco corrente: posizione == 1
        self.index_by_pos = {g["Posizione"]: i for i, g in enumerate(self.games)}
        self.current_pos = 1 if 1 in self.index_by_pos else (self.games[0]["Posizione"] if self.games else 1)

        # Assets base
        self.bkg = safe_image_load(resolve_media_path("bkg.png"), size=(1920, 1080), alpha=False)
        # Pulsanti principali
        self.btn_quit = ImageButton(
            resolve_media_path("btn_quit_off.png"),
            resolve_media_path("btn_quit_on.png"),
            (29, 975),
        )
        self.btn_intro = ImageButton(
            resolve_media_path("btn_intro_off.png"),
            resolve_media_path("btn_intro_on.png"),
            (264, 975),
        )
        self.btn_reset = ImageButton(
            resolve_media_path("btn_reset_off.png"),
            resolve_media_path("btn_reset_on.png"),
            (499, 975),
        )
        # Frecce
        self.btn_sx = ImageButton(
            resolve_media_path("btn_freccia_sx_off.png"),
            resolve_media_path("btn_freccia_sx_on.png"),
            (167, 721),
        )
        self.btn_dx = ImageButton(
            resolve_media_path("btn_freccia_dx_off.png"),
            resolve_media_path("btn_freccia_dx_on.png"),
            (434, 721),
        )
        # Play (verrà deciso dinamicamente se lock o no)
        self.play_off = safe_image_load(resolve_media_path("btn_play_off.png"), size=(300, 100))
        self.play_on = safe_image_load(resolve_media_path("btn_play_on.png"), size=(300, 100))
        self.play_lock = safe_image_load(resolve_media_path("btn_play_lock.png"), size=(300, 100))
        self.play_rect = self.play_off.get_rect(topleft=(677, 743))
        self.play_hover = False

    def current_index(self):
        return self.index_by_pos.get(self.current_pos, 0)

    def current_game(self):
        if not self.games:
            return None
        return self.games[self.current_index()]

    def next_game(self):
        if not self.games:
            return
        # posizione successiva, con wrap
        positions = [g["Posizione"] for g in self.games]
        positions.sort()
        try:
            idx = positions.index(self.current_pos)
        except ValueError:
            idx = 0
        idx = (idx + 1) % len(positions)
        self.current_pos = positions[idx]

    def prev_game(self):
        if not self.games:
            return
        positions = [g["Posizione"] for g in self.games]
        positions.sort()
        try:
            idx = positions.index(self.current_pos)
        except ValueError:
            idx = 0
        idx = (idx - 1) % len(positions)
        self.current_pos = positions[idx]

    def update_buttons(self, mouse_pos):
        self.btn_quit.update(mouse_pos)
        self.btn_intro.update(mouse_pos)
        self.btn_reset.update(mouse_pos)
        self.btn_sx.update(mouse_pos)
        self.btn_dx.update(mouse_pos)
        # Play hover (solo se attivo)
        g = self.current_game()
        if g and g.get("Stato", False):
            self.play_hover = self.play_rect.collidepoint(mouse_pos)
        else:
            self.play_hover = False

    def handle_events(self, event):
        # Quit
        if self.btn_quit.handle_event(event):
            if modal_popup("Sei sicuro che vuoi uscire?", 2):
                pygame.quit()
                sys.exit(0)

        # Intro
        if self.btn_intro.handle_event(event):
            # Fadeout di 2 secondi, poi video, poi musica da capo
            fadeout_menu_music_and_wait(2000)
            play_intro_video()
            start_menu_music()

        # Reset
        if self.btn_reset.handle_event(event):
            if modal_popup("Sei sicuro che vuoi resettare tutti i risultati?", 2):
                self.reset_progress()

        # Frecce
        if self.btn_sx.handle_event(event):
            self.prev_game()
        if self.btn_dx.handle_event(event):
            self.next_game()

        # Play
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            g = self.current_game()
            if g and g.get("Stato", False) and self.play_rect.collidepoint(event.pos):
                self.launch_current_game()

    def reset_progress(self):
        if not self.games:
            return
        # Tutti punti=0 e Stato=False, tranne Posizione=1 -> Stato=True
        for g in self.games:
            g["Punteggio"] = 0
            g["Stato"] = False
        # abilitare pos=1 se esiste
        if 1 in self.index_by_pos:
            self.games[self.index_by_pos[1]]["Stato"] = True
        save_games(self.games)

    def launch_current_game(self):
        g = self.current_game()
        if not g:
            return
        name = g.get("Nome", "")
        cur_score = g.get("Punteggio", 0)
        script = resolve_game_script(name)
        stop_menu_music()

        # Esegue lo script del gioco passandogli il punteggio corrente come input
        # Il gioco deve stampare su stdout la nuova cifra punteggio come numero intero.
        try:
            # Tenta di usare lo stesso eseguibile python
            python_exec = sys.executable or "python"
            proc = subprocess.run(
                [python_exec, script, "--score", str(cur_score)],
                capture_output=True,
                text=True,
                check=False,
            )
            new_score = None
            # Cerca un intero nell'output (ultima riga utile)
            out = (proc.stdout or "").strip().splitlines()
            for line in reversed(out):
                line = line.strip()
                if line.isdigit():
                    new_score = int(line)
                    break
                # Pattern: SCORE: <num>
                if line.upper().startswith("SCORE"):
                    try:
                        new_score = int(''.join(ch for ch in line if ch.isdigit()))
                        break
                    except Exception:
                        pass
            if new_score is not None:
                g["Punteggio"] = new_score
                # Facoltativo: sblocca gioco successivo se esiste
                # (non specificato ma spesso utile)
                # Manteniamo comunque lo stato attuale
                save_games(self.games)
        except Exception:
            # In caso di errore si ignora
            pass
        start_menu_music()

    def draw(self, target):
        # Sfondo
        target.blit(self.bkg, (0, 0))

        # Dati gioco corrente
        g = self.current_game()
        if g:
            titolo = g.get("Titolo", "")
            nome = g.get("Nome", "")
            stato = bool(g.get("Stato", False))
            descr = g.get("Descrizione", "")

            # Titolo box (75,303) 573x65 centrato, font 28pt; colore in base a Stato
            title_rect = pygame.Rect(75, 303, 573, 65)
            title_color = VERDE_SCURO if stato else GRIGIO
            # Centra verticalmente e orizzontalmente
            title_surf = FONT_40.render(titolo, True, title_color)
            title_pos = (
                title_rect.left + (title_rect.width - title_surf.get_width()) // 2,
                title_rect.top + (title_rect.height - title_surf.get_height()) // 2,
            )
            target.blit(title_surf, title_pos)

            # Immagine 573x322 pos (75,381), normale o lock
            thumb_name = f"thumbs_{nome}_lock.png" if not stato else f"thumbs_{nome}.png"
            thumb_path = _first_existing_path("jacoplay_media", "thumbs", thumb_name)
            thumb = safe_image_load(thumb_path, size=(573, 322))
            target.blit(thumb, (75, 381))

            # Descrizione se stato True, box (677,322) 475x321, font 20pt, colore VERDE_SCURO, wrap
            desc_rect = pygame.Rect(677, 322, 475, 321)
            if stato:
                full_descr = f"{descr or ''} (ultimo punteggio: {g.get('Punteggio', 0)})"
                descr_color = VERDE_SCURO
            else:
                full_descr = f"Sblocca i giochi precedenti per accedere a questo gioco"
                descr_color = GRIGIO
            for surf, pos in render_text_box(full_descr, FONT_18, descr_color, desc_rect, line_spacing=2, align="left"):
                target.blit(surf, pos)
                    
        # Pulsanti
        self.btn_quit.draw(target)
        self.btn_intro.draw(target)
        self.btn_reset.draw(target)
        self.btn_sx.draw(target)
        self.btn_dx.draw(target)

        # Play (on/off/lock) alle coord (677,743)
        if g and g.get("Stato", False):
            img = self.play_on if self.play_hover else self.play_off
        else:
            img = self.play_lock
        target.blit(img, self.play_rect.topleft)


# ----------------------------
# Main
# ----------------------------

def main():
    props = load_menu_properties()
    games = load_games()

    # All'avvio, se primorun True, riproduci video e poi imposta False
    # e SOLO dopo fai partire la musica di sottofondo.
    if props.get("primorun", True):
        play_intro_video()
        set_menu_primorun(False)
        start_menu_music()
    else:
        # Esecuzioni successive: salta il video e parti direttamente con l'audio
        start_menu_music()

    ui = MenuUI(games)

    # Loop principale
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # ESC fa la stessa cosa del pulsante Quit (conferma)
                if modal_popup("Sei sicuro che vuoi uscire?", 2):
                    running = False
            ui.handle_events(event)

        ui.update_buttons(mouse_pos)
        ui.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

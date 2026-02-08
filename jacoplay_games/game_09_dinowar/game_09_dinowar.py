# game_09_dinowar.py
# DinoWar (game_09_dinowar) - Menu + Avvio Partita (leader selection + setup)
# Specifiche: DinoWar_Specifiche_Funzionali_game_09_dinowar.docx

from __future__ import annotations

import json
import math
import os
import random
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame


# =========================
# Costanti (da specifica)
# =========================
LOGICAL_W, LOGICAL_H = 1920, 1080

BIANCO = (255, 255, 255)
GIALLO = (255, 234, 0)
VERDE = (132, 226, 145)
NERO = (0, 0, 0)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "game_09_media")
DATA_DIR = os.path.join(BASE_DIR, "game_09_data")
JSON_PATH = os.path.join(DATA_DIR, "game_09.properties")

FONT_PATH = os.path.join(MEDIA_DIR, "LuckiestGuy-Regular.ttf")

# Menu assets/coords
MENU_BG = "bg_menu.png"
MENU_ITEMS = [
    # name, off, on, pos(x,y)
    ("menu1", "menu1_off.png", "menu1_on.png", (304, 136)),
    ("menu2", "menu2_off.png", "menu2_on.png", (263, 368)),
    ("menu3", "menu3_off.png", "menu3_on.png", (809, 806)),
    ("menu4", "menu4_off.png", "menu4_on.png", (635, 593)),
]
MUSIC_MENU = "music_menu.mp3"
SFX_CARN_DOWN = "carnivoro_down.mp3"
SFX_HERB_DOWN = "erbivoro_down.mp3"
ICON_HIT = "colpo.png"
ICON_HEAL = "cura.png"
ICON_PROTECT = "scudo.png"
SFX_CARN_ATTACK = "carnivoro_attack.mp3"
SFX_HERB_ATTACK = "erbivoro_attack.mp3"
SFX_DEAD = "dead.mp3"



# Game assets/coords
BATTLE_BG = "bg_battlefield.png"
MUSIC_GAME = "music_game.mp3"

ICON_LEAVES = "icon_leaves.png"
ICON_MEAT = "icon_meat.png"

DECK_IMG = "mazzo.png"

BTN_ABB_OFF, BTN_ABB_ON = "btn_abbandona_off.png", "btn_abbandona_on.png"
BTN_COMP_OFF, BTN_COMP_ON = "btn_completa_off.png", "btn_completa_on.png"
#btn_skill_OFF, btn_skill_ON = "btn_skill_off.png", "btn_skill_on.png"

SFX_FLIP = "giracarta.mp3"

# Posizioni aree (da specifica)
POS_ENERGY_USER = (23, 966)
POS_ENERGY_AI = (23, 21)

POS_DECK_AI = (1746, 20)
POS_DECK_USER = (1746, 860)

POS_HAND_AI = (574, -50)     # area mano AI (y fuori schermo, come da specifica)
POS_HAND_USER = (574, 930)

HAND_W, HAND_H = (771, 200)
HAND_CARD_W, HAND_CARD_H = (153, 200)
HAND_STEP_X = 103  # overlap 50 px (153-103)

POS_FIELD_AI = (270, 220)
POS_FIELD_USER = (270, 560)

FIELD_CARD_W, FIELD_CARD_H = (230, 300)
FIELD_MAX = 6

# Testi
TITLE_LEADER = "SCEGLI IL TUO LEADER"

# Fazioni / energie (da JSON)
FACTION_HERB = "ERBIVORE"
FACTION_CARN = "CARNIVORE"
ENERGY_LEAVES = "LEAVES"
ENERGY_MEAT = "MEAT"


# =========================
# Utility di scaling
# =========================
class Scaler:
    """Gestisce rendering su surface logica 1920x1080 e scaling a schermo."""
    def __init__(self, window: pygame.Surface):
        self.window = window
        self.logical = pygame.Surface((LOGICAL_W, LOGICAL_H)).convert_alpha()
        self.logical_rect = self.logical.get_rect()
        self.window_rect = self.window.get_rect()

    def begin(self) -> pygame.Surface:
        self.logical.fill((0, 0, 0, 0))
        return self.logical

    def present(self) -> None:
        ww, wh = self.window_rect.size
        lw, lh = self.logical_rect.size

        scale = min(ww / lw, wh / lh)
        sw, sh = int(lw * scale), int(lh * scale)

        scaled = pygame.transform.smoothscale(self.logical, (sw, sh))
        x = (ww - sw) // 2
        y = (wh - sh) // 2

        self.window.fill((0, 0, 0))
        self.window.blit(scaled, (x, y))
        pygame.display.flip()

    def to_logical_pos(self, window_pos: Tuple[int, int]) -> Tuple[int, int]:
        """Converte coordinate mouse da window -> logical (considerando letterbox)."""
        ww, wh = self.window_rect.size
        lw, lh = self.logical_rect.size

        scale = min(ww / lw, wh / lh)
        sw, sh = int(lw * scale), int(lh * scale)
        offset_x = (ww - sw) // 2
        offset_y = (wh - sh) // 2

        mx, my = window_pos
        mx -= offset_x
        my -= offset_y

        if scale <= 0:
            return 0, 0

        lx = int(mx / scale)
        ly = int(my / scale)
        return lx, ly


# =========================
# Cache immagini / audio
# =========================
class AssetCache:
    def __init__(self):
        self._images: Dict[str, pygame.Surface] = {}
        self._sounds: Dict[str, pygame.mixer.Sound] = {}

    def image(self, filename: str, alpha: bool = True) -> pygame.Surface:
        if filename not in self._images:
            path = os.path.join(MEDIA_DIR, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Immagine mancante: {path}")
            img = pygame.image.load(path)
            img = img.convert_alpha() if alpha else img.convert()
            self._images[filename] = img
        return self._images[filename]

    def sound(self, filename: str) -> pygame.mixer.Sound:
        if filename not in self._sounds:
            path = os.path.join(MEDIA_DIR, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Suono mancante: {path}")
            self._sounds[filename] = pygame.mixer.Sound(path)
        return self._sounds[filename]


class Audio:
    """Gestione musica/effetti. Importante: stop totale quando si torna al menu."""
    def __init__(self, cache: AssetCache):
        self.cache = cache

    def stop_all(self) -> None:
        pygame.mixer.stop()
        pygame.mixer.music.stop()

    def play_music_loop(self, filename: str, volume: float = 0.8) -> None:
        path = os.path.join(MEDIA_DIR, filename)
        pygame.mixer.music.stop()
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)

    def stop_music(self) -> None:
        pygame.mixer.music.stop()

    def play_sfx(self, filename: str, volume: float = 1.0) -> None:
        s = self.cache.sound(filename)
        s.set_volume(volume)
        s.play()


# =========================
# Dati carte
# =========================
@dataclass(frozen=True)
class AbilityDef:
    name: str
    type: str       # NONE/ATTACK/HEAL/SHIELD/PROTECT/SPEED
    targets: str    # NONE/ONE/ALL/SELF
    point_per_target: int
    notes: str


@dataclass(frozen=True)
class CardDef:
    id: int
    name: str
    species: str
    faction: str        # ERBIVORE/CARNIVORE
    energy_type: str    # LEAVES/MEAT
    hp: int
    atk: int
    image: str
    ability: AbilityDef


@dataclass
class CardInstance:
    base: CardDef
    current_hp: int
    is_leader: bool = False
    speed_icon: bool = False
    protect_active: bool = False

    # stato turno
    summoned_this_turn: bool = False
    attacks_left: int = 1
    ability_used_this_turn: bool = False

    # buff (per step successivi)
    shield_points: int = 0      # riduce danno, consumabile

    # stato UI
    selected: bool = False
    atk: bool = False

    def reset_hp(self) -> None:
        self.current_hp = self.base.hp




def load_cards_from_json(path: str) -> List[CardDef]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    #  Supporto entrambi i formati:
    # 1) lista diretta di carte: [ {...}, {...} ]
    # 2) oggetto con chiave "cards": { "version": 1, "cards": [ {...}, ... ] }
    if isinstance(raw, dict):
        raw_cards = raw.get("cards", [])
    else:
        raw_cards = raw

    if not isinstance(raw_cards, list):
        raise ValueError(f"Formato JSON non valido: 'cards' non è una lista. Trovato: {type(raw_cards)}")

    cards: List[CardDef] = []
    for obj in raw_cards:
        if not isinstance(obj, dict):
            raise ValueError(f"Elemento carta non valido (atteso dict, trovato {type(obj)}): {obj}")

        ab = obj.get("ability") or {}
        if not isinstance(ab, dict):
            raise ValueError(f"Campo 'ability' non valido per carta id={obj.get('id')}: {type(ab)}")

        ability = AbilityDef(
            name=str(ab.get("name", "")),
            type=str(ab.get("type", "NONE")),
            targets=str(ab.get("targets", "NONE")),
            point_per_target=int(ab.get("point_per_target", 0)),
            notes=str(ab.get("notes", "")),
        )

        cards.append(
            CardDef(
                id=int(obj["id"]),
                name=str(obj.get("name", "")),
                species=str(obj.get("species", "")),
                faction=str(obj.get("faction", "")),
                energy_type=str(obj.get("energy_type", "")),
                hp=int(obj.get("hp", 1)),
                atk=int(obj.get("atk", 0)),
                image=str(obj.get("image", "")),
                ability=ability,
            )
        )

    cards.sort(key=lambda c: c.id)
    return cards



# =========================
# UI: pulsanti rollover
# =========================
class HoverButton:
    def __init__(self, cache: AssetCache, img_off: str, img_on: str, pos: Tuple[int, int]):
        self.cache = cache
        self.img_off_name = img_off
        self.img_on_name = img_on
        self.pos = pos

        self.img_off = cache.image(img_off)
        self.img_on = cache.image(img_on)

        self.rect = self.img_off.get_rect(topleft=pos)
        self.hovered = False
        self.enabled = True

        # When True, the button stays visually "ON" even if mouse leaves.
        self.forced_on = False

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.hovered = False
            self.forced_on = False

    def set_forced(self, on: bool) -> None:
        """Force the visual ON/OFF state (latched buttons)."""
        self.forced_on = bool(on)

    def update(self, mouse_pos: Tuple[int, int]) -> None:
        if not self.enabled:
            self.hovered = False
            return
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surf: pygame.Surface) -> None:
        img = self.img_on if ((self.hovered or self.forced_on) and self.enabled) else self.img_off
        surf.blit(img, self.pos)

    def is_clicked(self, mouse_pos: Tuple[int, int], mouse_up: bool) -> bool:
        if not self.enabled:
            return False
        return mouse_up and self.rect.collidepoint(mouse_pos)

@dataclass
class Toast:
    text: str
    ms_left: int

def draw_toast(surf: pygame.Surface, toast: Optional[Toast], font: pygame.font.Font) -> None:
    if not toast or toast.ms_left <= 0:
        return
    txt = font.render(toast.text, True, BIANCO)
    r = txt.get_rect(center=(LOGICAL_W // 2, LOGICAL_H // 2))
    # contorno semplice
    shadow = font.render(toast.text, True, NERO)
    surf.blit(shadow, (r.x + 3, r.y + 3))
    surf.blit(txt, r.topleft)

def hand_card_rects(hand: List[str], origin: Tuple[int, int]) -> List[pygame.Rect]:
    x0, y0 = origin
    rects = []
    for i in range(len(hand)):
        x = x0 + i * HAND_STEP_X
        y = y0
        rects.append(pygame.Rect(x, y, HAND_CARD_W, HAND_CARD_H))
    return rects

def field_card_rects(field: List[CardInstance], origin: Tuple[int, int]) -> List[pygame.Rect]:
    ox, oy = origin
    rects = []
    for i in range(min(len(field), FIELD_MAX)):
        rects.append(pygame.Rect(ox + i * FIELD_CARD_W, oy, FIELD_CARD_W, FIELD_CARD_H))
    return rects

def hovered_field_index(mouse_pos: Tuple[int, int], rects: List[pygame.Rect]) -> Optional[int]:
    for i, r in enumerate(rects):
        if r.collidepoint(mouse_pos):
            return i
    return None

def protected_indices(field: List[CardInstance]) -> List[int]:
    return [i for i, inst in enumerate(field) if getattr(inst, "protect_active", False)]

def is_attack_target_allowed(defender_field: List[CardInstance], target_idx: int) -> bool:
    prot = protected_indices(defender_field)
    if not prot:
        return True  # nessun protect attivo -> si può colpire chiunque
    return target_idx in prot


def should_atk_for_attack(inst: CardInstance) -> bool:
    return inst.attacks_left > 0 and (not inst.summoned_this_turn)

def can_use_ability_now(inst: CardInstance) -> bool:
    ab = inst.base.ability
    if ab is None:
        return False
    if ab.type == "NONE" or ab.targets == "NONE":
        return False
    if inst.summoned_this_turn:
        return False
    if inst.ability_used_this_turn:
        return False
    return True


def field_image_name(inst: CardInstance) -> str:
    cid = inst.base.id
    if inst.selected:
        return f"{cid}_selected.png"
    if inst.atk:
        return f"{cid}_atk.png"
    return f"{cid}.png"

def field_image_name(inst: CardInstance) -> str:
    cid = inst.base.id

    if inst.selected:
        return f"{cid}_selected.png"

    can_attack = inst.atk
    can_use_ability = can_use_ability_now(inst)

    # può ancora attaccare (abilità sì o no è irrilevante)
    if can_attack:
        return f"{cid}_atk.png"

    # non può più attaccare ma può ancora usare abilità
    if can_use_ability:
        return f"{cid}_glow.png"

    # né attacco né abilità
    return f"{cid}.png"



def hovered_hand_index(mouse_pos: Tuple[int, int], rects: List[pygame.Rect]) -> Optional[int]:
    # con overlap conviene prendere la carta "più a destra" tra quelle che collidono
    hit = None
    for i, r in enumerate(rects):
        if r.collidepoint(mouse_pos):
            hit = i
    return hit

def draw_one_card_with_animation(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    player: PlayerState,
    is_user: bool,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    #btns: Tuple[HoverButton, HoverButton, HoverButton],
    btns: Tuple[HoverButton, HoverButton],
    other_player: PlayerState,
    clock: pygame.time.Clock,
) -> None:
    if not player.deck or len(player.hand) >= 7:
        return

    #btn_abbandona, btn_completa, btn_skill = btns
    btn_abbandona, btn_completa = btns
    font_energy = fonts["energy"]
    font_hp = fonts["hp"]
    

    token = player.deck.pop(0)
    audio.play_sfx(SFX_FLIP, volume=0.9)

    if is_user:
        start = POS_DECK_USER
        end = (LOGICAL_W // 2 - deck_img.get_width() // 2, LOGICAL_H // 2 - deck_img.get_height() // 2)
    else:
        start = POS_DECK_AI
        slot_idx = len(player.hand)
        end = (POS_HAND_AI[0] + slot_idx * HAND_STEP_X, POS_HAND_AI[1])

    mover = MovingSprite(deck_img, start, end, 300)

    def render_base() -> pygame.Surface:
        surf = scaler.begin()
        surf.blit(bg, (0, 0))

        # deck visibili se ancora carte
        if other_player.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_USER if is_user else POS_DECK_AI)
        if player.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_AI if is_user else POS_DECK_USER)

        # icone
        surf.blit(icon_ai, POS_ENERGY_AI)
        surf.blit(icon_user, POS_ENERGY_USER)

        # energia
        ai_energy_txt = font_energy.render(str(other_player.energy if is_user else player.energy), True, BIANCO)
        user_energy_txt = font_energy.render(str(player.energy if is_user else other_player.energy), True, BIANCO)
        surf.blit(ai_energy_txt, (133, 42))
        surf.blit(user_energy_txt, (133, 987))

        # bottoni
        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        btn_abbandona.update(mouse_logical)
        btn_completa.update(mouse_logical)
        #btn_skill.update(mouse_logical)
        btn_abbandona.draw(surf)
        btn_completa.draw(surf)
        #btn_skill.draw(surf)

        # campo
        draw_field_row(surf, cache, other_player.field if is_user else player.field, POS_FIELD_AI, font_hp, use_states=False)
        draw_field_row(surf, cache, player.field if is_user else other_player.field, POS_FIELD_USER, font_hp, use_states=True)

        # mani
        draw_hand_row(surf, cache, player.hand if is_user else other_player.hand, POS_HAND_USER, show_faces=True)
        draw_hand_row(surf, cache, other_player.hand if is_user else player.hand, POS_HAND_AI, show_faces=False)
        return surf

    # movimento
    while not mover.done:
        dt = clock.tick(60)
        _consume_quit_events()
        mover.update(dt)
        surf = render_base()
        surf.blit(mover.image, mover.pos())
        scaler.present()

    # reveal solo per utente
    if is_user:
        reveal_img = token_to_big_image(cache, token)
        reveal_pos = (LOGICAL_W // 2 - reveal_img.get_width() // 2, LOGICAL_H // 2 - reveal_img.get_height() // 2)
        elapsed = 0
        while elapsed < 2000:
            dt = clock.tick(60)
            _consume_quit_events()
            elapsed += dt
            surf = render_base()
            surf.blit(reveal_img, reveal_pos)
            scaler.present()

    player.hand.append(token)



# =========================
# Animazioni (minimo indispensabile)
# =========================
def ease_out_cubic(t: float) -> float:
    # t in [0..1]
    return 1 - (1 - t) ** 3


@dataclass
class MovingSprite:
    image: pygame.Surface
    start: Tuple[int, int]
    end: Tuple[int, int]
    duration_ms: int
    elapsed_ms: int = 0
    done: bool = False

    def update(self, dt_ms: int) -> None:
        if self.done:
            return
        self.elapsed_ms += dt_ms
        if self.elapsed_ms >= self.duration_ms:
            self.elapsed_ms = self.duration_ms
            self.done = True

    def pos(self) -> Tuple[int, int]:
        if self.duration_ms <= 0:
            return self.end
        t = self.elapsed_ms / self.duration_ms
        e = ease_out_cubic(max(0.0, min(1.0, t)))
        x = int(self.start[0] + (self.end[0] - self.start[0]) * e)
        y = int(self.start[1] + (self.end[1] - self.start[1]) * e)
        return x, y


def animate_normal_attack(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    #btns: Tuple[HoverButton, HoverButton, HoverButton],
    btns: Tuple[HoverButton, HoverButton],
    user_state: PlayerState,
    ai_state: PlayerState,
    attacker_idx: int,
    target_idx: int,
    clock: pygame.time.Clock,
) -> None:
    """
    Animazione max ~1s:
      - attacker va verso target (300ms)
      - mostra colpo + suono (200ms)
      - torna indietro (300ms)
    """
    #btn_abbandona, btn_completa, btn_skill = btns
    btn_abbandona, btn_completa = btns

    font_energy = fonts["energy"]
    font_hp = fonts["hp"]

    hit_img = cache.image(ICON_HIT)

    # posizioni origine/bersaglio (topleft delle carte)
    a0 = (POS_FIELD_USER[0] + attacker_idx * FIELD_CARD_W, POS_FIELD_USER[1])
    t0 = (POS_FIELD_AI[0] + target_idx * FIELD_CARD_W, POS_FIELD_AI[1])

    # sovrapposizione "circa metà": ci avviciniamo a metà della distanza
    ax, ay = a0
    tx, ty = t0
    mid = (ax + int((tx - ax) * 0.5), ay + int((ty - ay) * 0.5))

    attacker = user_state.field[attacker_idx]
    attacker_img = cache.image(field_image_name(attacker))

    # suono attacco in base alla fazione di chi attacca
    if attacker.base.faction == FACTION_CARN:
        audio.play_sfx(SFX_CARN_ATTACK, volume=0.9)
    else:
        audio.play_sfx(SFX_HERB_ATTACK, volume=0.9)

    def render_base() -> pygame.Surface:
        surf = scaler.begin()
        surf.blit(bg, (0, 0))

        if ai_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_AI)
        if user_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_USER)

        surf.blit(icon_ai, POS_ENERGY_AI)
        surf.blit(icon_user, POS_ENERGY_USER)

        ai_energy_txt = font_energy.render(str(ai_state.energy), True, BIANCO)
        user_energy_txt = font_energy.render(str(user_state.energy), True, BIANCO)
        surf.blit(ai_energy_txt, (133, 42))
        surf.blit(user_energy_txt, (133, 987))

        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        btn_abbandona.update(mouse_logical)
        btn_completa.update(mouse_logical)
        #btn_skill.update(mouse_logical)

        btn_abbandona.draw(surf)
        btn_completa.draw(surf)
        #btn_skill.draw(surf)

        draw_field_row(surf, cache, ai_state.field, POS_FIELD_AI, font_hp, use_states=False)
        draw_field_row(surf, cache, user_state.field, POS_FIELD_USER, font_hp, use_states=True)

        draw_hand_row(surf, cache, user_state.hand, POS_HAND_USER, show_faces=True)
        draw_hand_row(surf, cache, ai_state.hand, POS_HAND_AI, show_faces=False)

        return surf

    # 1) avanti
    mover1 = MovingSprite(attacker_img, a0, mid, 300)
    while not mover1.done:
        dt = clock.tick(60)
        _consume_quit_events()
        mover1.update(dt)
        surf = render_base()
        surf.blit(attacker_img, mover1.pos())
        scaler.present()

    # 2) colpo (icona al centro del target)
    elapsed = 0
    hit_ms = 200
    hit_center = (t0[0] + FIELD_CARD_W // 2 - hit_img.get_width() // 2,
                  t0[1] + FIELD_CARD_H // 2 - hit_img.get_height() // 2)
    while elapsed < hit_ms:
        dt = clock.tick(60)
        _consume_quit_events()
        elapsed += dt
        surf = render_base()
        surf.blit(attacker_img, mid)
        surf.blit(hit_img, hit_center)
        scaler.present()

    # 3) indietro
    mover2 = MovingSprite(attacker_img, mid, a0, 300)
    while not mover2.done:
        dt = clock.tick(60)
        _consume_quit_events()
        mover2.update(dt)
        surf = render_base()
        surf.blit(attacker_img, mover2.pos())
        scaler.present()

def animate_normal_attack_ai(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    #btns: Tuple[HoverButton, HoverButton, HoverButton],
    btns: Tuple[HoverButton, HoverButton],
    user_state: PlayerState,
    ai_state: PlayerState,
    attacker_idx: int,
    target_idx: int,
    clock: pygame.time.Clock,
) -> None:
    """
    Animazione max ~1s: AI (alto) -> Utente (basso)
      - attacker va verso target (300ms)
      - mostra colpo + suono (200ms)
      - torna indietro (300ms)
    """
    #btn_abbandona, btn_completa, btn_skill = btns
    btn_abbandona, btn_completa = btns
    font_energy = fonts["energy"]
    font_hp = fonts["hp"]

    hit_img = cache.image(ICON_HIT)

    a0 = (POS_FIELD_AI[0] + attacker_idx * FIELD_CARD_W, POS_FIELD_AI[1])
    t0 = (POS_FIELD_USER[0] + target_idx * FIELD_CARD_W, POS_FIELD_USER[1])

    ax, ay = a0
    tx, ty = t0
    mid = (ax + int((tx - ax) * 0.5), ay + int((ty - ay) * 0.5))

    attacker = ai_state.field[attacker_idx]
    attacker_img = cache.image(field_image_name(attacker))

    # suono attacco in base alla fazione
    if attacker.base.faction == FACTION_CARN:
        audio.play_sfx(SFX_CARN_ATTACK, volume=0.9)
    else:
        audio.play_sfx(SFX_HERB_ATTACK, volume=0.9)

    def render_base() -> pygame.Surface:
        surf = scaler.begin()
        surf.blit(bg, (0, 0))

        if ai_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_AI)
        if user_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_USER)

        surf.blit(icon_ai, POS_ENERGY_AI)
        surf.blit(icon_user, POS_ENERGY_USER)

        ai_energy_txt = font_energy.render(str(ai_state.energy), True, BIANCO)
        user_energy_txt = font_energy.render(str(user_state.energy), True, BIANCO)
        surf.blit(ai_energy_txt, (133, 42))
        surf.blit(user_energy_txt, (133, 987))

        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        btn_abbandona.update(mouse_logical)
        btn_completa.update(mouse_logical)
        #btn_skill.update(mouse_logical)

        btn_abbandona.draw(surf)
        btn_completa.draw(surf)
        #btn_skill.draw(surf)

        draw_field_row(surf, cache, ai_state.field, POS_FIELD_AI, font_hp, use_states=False)
        draw_field_row(surf, cache, user_state.field, POS_FIELD_USER, font_hp, use_states=True)

        draw_hand_row(surf, cache, user_state.hand, POS_HAND_USER, show_faces=True)
        draw_hand_row(surf, cache, ai_state.hand, POS_HAND_AI, show_faces=False)

        return surf

    # avanti
    mover1 = MovingSprite(attacker_img, a0, mid, 300)
    while not mover1.done:
        dt = clock.tick(60)
        _consume_quit_events()
        mover1.update(dt)
        surf = render_base()
        surf.blit(attacker_img, mover1.pos())
        scaler.present()

    # colpo
    elapsed = 0
    hit_ms = 200
    hit_center = (
        t0[0] + FIELD_CARD_W // 2 - hit_img.get_width() // 2,
        t0[1] + FIELD_CARD_H // 2 - hit_img.get_height() // 2,
    )
    while elapsed < hit_ms:
        dt = clock.tick(60)
        _consume_quit_events()
        elapsed += dt
        surf = render_base()
        surf.blit(attacker_img, mid)
        surf.blit(hit_img, hit_center)
        scaler.present()

    # indietro
    mover2 = MovingSprite(attacker_img, mid, a0, 300)
    while not mover2.done:
        dt = clock.tick(60)
        _consume_quit_events()
        mover2.update(dt)
        surf = render_base()
        surf.blit(attacker_img, mover2.pos())
        scaler.present()






def animate_skill_hit(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    #btns: Tuple[HoverButton, HoverButton, HoverButton],
    btns: Tuple[HoverButton, HoverButton],
    user_state: PlayerState,
    ai_state: PlayerState,
    target_is_ai: bool,
    target_idx: int,
    clock: pygame.time.Clock,
    ms: int = 200,
) -> None:
    """Animazione semplice per abilità ATTACK: icona colpo sul bersaglio + render per ms."""
    #btn_abbandona, btn_completa, btn_skill = btns
    btn_abbandona, btn_completa = btns
    font_energy = fonts["energy"]
    font_hp = fonts["hp"]
    hit_img = cache.image(ICON_HIT)

    origin = POS_FIELD_AI if target_is_ai else POS_FIELD_USER
    t0 = (origin[0] + target_idx * FIELD_CARD_W, origin[1])

    hit_pos = (
        t0[0] + FIELD_CARD_W // 2 - hit_img.get_width() // 2,
        t0[1] + FIELD_CARD_H // 2 - hit_img.get_height() // 2,
    )

    def render_base() -> pygame.Surface:
        surf = scaler.begin()
        surf.blit(bg, (0, 0))

        if ai_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_AI)
        if user_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_USER)

        surf.blit(icon_ai, POS_ENERGY_AI)
        surf.blit(icon_user, POS_ENERGY_USER)

        ai_energy_txt = font_energy.render(str(ai_state.energy), True, BIANCO)
        user_energy_txt = font_energy.render(str(user_state.energy), True, BIANCO)
        surf.blit(ai_energy_txt, (133, 42))
        surf.blit(user_energy_txt, (133, 987))

        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        btn_abbandona.update(mouse_logical)
        btn_completa.update(mouse_logical)
        #btn_skill.update(mouse_logical)

        btn_abbandona.draw(surf)
        btn_completa.draw(surf)
        #btn_skill.draw(surf)

        draw_field_row(surf, cache, ai_state.field, POS_FIELD_AI, font_hp, use_states=False)
        draw_field_row(surf, cache, user_state.field, POS_FIELD_USER, font_hp, use_states=True)

        draw_hand_row(surf, cache, user_state.hand, POS_HAND_USER, show_faces=True)
        draw_hand_row(surf, cache, ai_state.hand, POS_HAND_AI, show_faces=False)
        return surf

    elapsed = 0
    while elapsed < ms:
        dt = clock.tick(60)
        _consume_quit_events()
        elapsed += dt
        surf = render_base()
        surf.blit(hit_img, hit_pos)
        scaler.present()

def animate_heal_icon(
    scaler: Scaler,
    cache: AssetCache,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    btns: Tuple[HoverButton, HoverButton],  # (btn_abbandona, btn_completa) oppure includi altri se li disegni
    user_state: PlayerState,
    ai_state: PlayerState,
    target_is_ai: bool,
    target_idx: int,
    clock: pygame.time.Clock,
    ms: int = 200,
) -> None:
    """
    Mostra l'icona cura (cura.png) sulla carta target.

    - cura.png è 100x100
    - coordinate relative alla carta: (75,158)
    - durata: ms millisecondi
    """

    def render_base() -> pygame.Surface:
        btn_abbandona, btn_completa = btns
        font_energy = fonts["energy"]
        font_hp = fonts["hp"]

        surf = scaler.begin()
        surf.blit(bg, (0, 0))

        if ai_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_AI)
        if user_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_USER)

        surf.blit(icon_ai, POS_ENERGY_AI)
        surf.blit(icon_user, POS_ENERGY_USER)

        ai_energy_txt = font_energy.render(str(ai_state.energy), True, BIANCO)
        user_energy_txt = font_energy.render(str(user_state.energy), True, BIANCO)
        surf.blit(ai_energy_txt, (133, 42))
        surf.blit(user_energy_txt, (133, 987))

        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        btn_abbandona.update(mouse_logical)
        btn_completa.update(mouse_logical)

        btn_abbandona.draw(surf)
        btn_completa.draw(surf)

        draw_field_row(surf, cache, ai_state.field, POS_FIELD_AI, font_hp, use_states=False)
        draw_field_row(surf, cache, user_state.field, POS_FIELD_USER, font_hp, use_states=True)

        draw_hand_row(surf, cache, user_state.hand, POS_HAND_USER, show_faces=True)
        draw_hand_row(surf, cache, ai_state.hand, POS_HAND_AI, show_faces=False)

        return surf

    
    # Disegna base
    elapsed = 0
    while elapsed < ms:
        surf = render_base()

        if target_is_ai:
            rects = field_card_rects(ai_state.field, POS_FIELD_AI)
        else:
            rects = field_card_rects(user_state.field, POS_FIELD_USER)

        if 0 <= target_idx < len(rects):
            r = rects[target_idx]
            heal_img = cache.image(ICON_HEAL)
            surf.blit(heal_img, (r.x + 75, r.y + 158))

        scaler.present()
        dt = clock.tick(90)
        elapsed += dt



def apply_normal_attack_damage(attacker: CardInstance, target: CardInstance) -> bool:
    """
    Ritorna True se il target muore (HP < 1).
    Danno base = attacker.atk, ridotto da shield_points (consumandolo).
    """
    dmg = max(0, int(attacker.base.atk))

    if target.shield_points > 0 and dmg > 0:
        used = min(dmg, target.shield_points)
        target.shield_points -= used
        dmg -= used

    if dmg > 0:
        target.current_hp -= dmg

    return target.current_hp < 1


def ability_cost(ability: AbilityDef, n_targets: int) -> int:
    """Costo energia abilità (regola aggiornata):
    - targets == ALL  -> 2 energie (costo fisso)
    - tutti gli altri targets validi -> 1 energia (costo fisso)
    - type/targets NONE -> 0
    NB: point_per_target NON è il costo: è il valore dell'effetto per bersaglio.
    """
    a_type = str(getattr(ability, "type", "NONE")).upper()
    a_tgt = str(getattr(ability, "targets", "NONE")).upper()

    if a_type == "NONE" or a_tgt == "NONE":
        return 0
    return 2 if a_tgt == "ALL" else 1


def can_cast_ability(caster: CardInstance) -> Tuple[bool, str]:
    """Checks basic constraints for casting an ability."""
    if caster.summoned_this_turn:
        return False, "Non puoi usare abilità nel turno in cui la carta è stata messa in campo"
    if caster.ability_used_this_turn:
        return False, "Abilità già usata in questo turno"
    if caster.base.ability.type in ("", "NONE"):
        return False, "Questa carta non ha un'abilità"
    return True, ""


def apply_heal(targets: List[CardInstance], points: int) -> None:
    for t in targets:
        t.current_hp = min(t.base.hp, t.current_hp + max(0, points))


def apply_speed(targets: List[CardInstance], points: int) -> None:
    # Interpretazione: aggiunge attacchi extra nel turno corrente.
    for t in targets:
        t.attacks_left += max(0, points)
        t.speed_icon = True


def apply_shield(targets: List[CardInstance], points: int) -> None:
    """Aggiunge punti scudo consumabili (riduzione danno) ai target."""
    add = max(0, int(points))
    if add <= 0:
        return
    for t in targets:
        t.shield_points += add


def apply_ability_attack_damage(points: int, target: CardInstance) -> bool:
    """Return True if target dies."""
    dmg = max(0, int(points))
    if target.shield_points > 0 and dmg > 0:
        used = min(dmg, target.shield_points)
        target.shield_points -= used
        dmg -= used
    if dmg > 0:
        target.current_hp -= dmg
    return target.current_hp < 1


def resolve_ability(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    #btns: Tuple[HoverButton, HoverButton, HoverButton],
    btns: Tuple[HoverButton, HoverButton],
    caster_state: PlayerState,
    other_state: PlayerState,
    caster_idx: int,
    targets_idx: Optional[List[int]],
    caster_is_user: bool,
    clock: pygame.time.Clock,
) -> Tuple[bool, Optional[str]]:
    """
    Applica l'abilità del caster.

    Regole:
      - point_per_target è l'effetto per bersaglio (danno/cura/scudo/attacchi extra)
      - costo energia: ALL=2, altri=1
      - ATTACK colpisce sempre avversario; HEAL/SPEED/SHIELD colpiscono sempre alleati
    Ritorna (applied, toast_msg_or_None). Se applied=False e msg!=None, mostra toast.
    """
    caster = caster_state.field[caster_idx]
    ok, msg = can_cast_ability(caster)
    if not ok:
        return False, msg

    ability = caster.base.ability
    a_type = ability.type.upper()
    a_targets = ability.targets.upper()

    # --- risoluzione target ---
    target_state: PlayerState
    idxs: List[int]

    if a_type == "ATTACK":
        target_state = other_state
    else:
        target_state = caster_state

    if a_targets == "SELF":
        target_state = caster_state
        idxs = [caster_idx]
    elif a_targets == "ALL":
        idxs = list(range(len(target_state.field)))
    elif a_targets == "ONE":
        if not targets_idx or len(targets_idx) != 1:
            return False, "Seleziona un bersaglio"
        idxs = targets_idx
        if idxs[0] < 0 or idxs[0] >= len(target_state.field):
            return False, "Bersaglio non valido"
    else:
        return False, "Abilità non valida"

    target_cards = [target_state.field[i] for i in idxs if 0 <= i < len(target_state.field)]

    # --- costo energia ---
    cost = ability_cost(ability, len(target_cards))
    if caster_state.energy < cost:
        return False, "Energia insufficiente"

    caster_state.energy -= cost
    caster.ability_used_this_turn = True

    points = int(ability.point_per_target)

    # --- applica effetto ---
    if a_type == "HEAL":
        # salva HP prima
        before_hps = [t.current_hp for t in target_cards]

        # applica cura
        apply_heal(target_cards, points)

        # mostra icona cura SOLO dove gli HP sono aumentati
        for i, t in enumerate(target_cards):
            if t.current_hp > before_hps[i]:
                # idxs è la lista degli indici di campo corrispondenti a target_cards
                animate_heal_icon(
                    scaler=scaler,
                    cache=cache,
                    bg=bg,
                    deck_img=deck_img,
                    fonts=fonts,
                    icon_user=icon_user,
                    icon_ai=icon_ai,
                    btns=btns,  # oppure la tua tupla reale
                    user_state=caster_state,
                    ai_state=other_state,
                    target_is_ai=False,     # HEAL cura sempre alleati (campo caster)
                    target_idx=idxs[i],     # IMPORTANTISSIMO: indice nel field
                    clock=clock,
                    ms=200,
                )

    elif a_type == "SPEED":
        apply_speed(target_cards, points)
        # aggiorna atk del giocatore che sta lanciando, se è l'utente
        if caster_is_user:
            for inst in caster_state.field:
                if not inst.selected:
                    inst.atk = should_atk_for_attack(inst)

    elif a_type == "SHIELD":
        apply_shield(target_cards, points)

    elif a_type == "PROTECT":
        # applica protect ai target (di norma SELF o ALL, ma lo gestiamo genericamente)
        for t in target_cards:
            t.protect_active = True
        

    elif a_type == "ATTACK":

        # ===== ENFORCE PROTECT (QUI!) =====
        prot = [i for i, inst in enumerate(target_state.field) if getattr(inst, "protect_active", False)]
        if prot:
            if a_targets == "ONE":
                # idxs deve contenere esattamente 1 indice (già garantito sopra)
                if idxs[0] not in prot:
                    return False, "Devi attaccare un dinosauro protetto"
            elif a_targets == "ALL":
                # con ALL colpisci solo i protetti
                idxs = [i for i in idxs if i in prot]
                target_cards = [target_state.field[i] for i in idxs]

        # Animazione semplice: icona colpo + suono.
        # Se targets=ALL: sequenza una dopo l'altra (non insieme).
        render_user_state = caster_state if caster_is_user else other_state
        render_ai_state = other_state if caster_is_user else caster_state

        # se caster è utente, i target sono AI (alto); altrimenti target sono USER (basso)
        target_is_ai = caster_is_user

        # snapshot per iterare in sicurezza anche se si rimuovono carte
        targets_snapshot = list(target_cards)

        for target_obj in targets_snapshot:
            # trova indice corrente (può cambiare per rimozioni)
            current_idx = None
            for j, inst in enumerate(target_state.field):
                if inst is target_obj:
                    current_idx = j
                    break
            if current_idx is None:
                continue

            # suono colpo
            if caster.base.faction == FACTION_CARN:
                audio.play_sfx(SFX_CARN_ATTACK, volume=0.9)
            else:
                audio.play_sfx(SFX_HERB_ATTACK, volume=0.9)

            # animazione icona colpo sul bersaglio
            animate_skill_hit(
                scaler=scaler,
                cache=cache,
                audio=audio,
                bg=bg,
                deck_img=deck_img,
                fonts=fonts,
                icon_user=icon_user,
                icon_ai=icon_ai,
                btns=btns,
                user_state=render_user_state,
                ai_state=render_ai_state,
                target_is_ai=target_is_ai,
                target_idx=current_idx,
                clock=clock,
                ms=200,
            )

            # applica danno (con consumo shield se presente)
            died = apply_ability_attack_damage(points, target_state.field[current_idx])

            if died:
                audio.play_sfx(SFX_DEAD, volume=0.9)
                pygame.time.delay(120)
                target_state.field.pop(current_idx)

                # game over check (energie non contano)
                res = check_and_handle_game_over(
                    scaler=scaler, cache=cache, audio=audio, fonts=fonts,
                    user_state=render_user_state, ai_state=render_ai_state, clock=clock
                )
                if res is not None:
                    return True, "MENU"

    else:
        return False, "Abilità non supportata"

    return True, None


def is_energy_token(token: str) -> bool:
    return token.startswith("E:")

def is_dino_token(token: str) -> bool:
    return token.startswith("DINO:")

def token_dino_id(token: str) -> int:
    return int(token.split(":")[1])

def is_player_out_of_moves(p: PlayerState) -> bool:
    if len(p.field) > 0:
        return False
    has_dino_in_hand = any(t.startswith("DINO:") for t in p.hand)
    has_dino_in_deck = any(t.startswith("DINO:") for t in p.deck)
    return not (has_dino_in_hand or has_dino_in_deck)

def check_and_handle_game_over(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    fonts: Dict[str, pygame.font.Font],
    user_state: PlayerState,
    ai_state: PlayerState,
    clock: pygame.time.Clock,
) -> Optional[str]:
    """
    Ritorna:
      - "USER_WON" se AI out-of-moves
      - "USER_LOST" se USER out-of-moves
      - None se si continua
    """
    if is_player_out_of_moves(ai_state):
        end_screen(scaler, cache, audio, fonts, won=True, clock=clock)
        return "USER_WON"
    if is_player_out_of_moves(user_state):
        end_screen(scaler, cache, audio, fonts, won=False, clock=clock)
        return "USER_LOST"
    return None

def ai_play_cards(
    audio: Audio,
    ai_state: PlayerState,
    def_by_id: Dict[int, CardDef],
) -> None:
    """
    Strategia semplice (coerente con la tua logica attuale):
      1) gioca fino a 2 energie (se in mano) -> aumenta ai_state.energy
      2) evoca dinosauri finché:
            - campo < 6
            - ha dinos in mano
    NOTA: evocare dinosauri NON consuma energia (energia serve solo per abilità).
    """
    # 1) energie max 2
    while ai_state.energy_played_this_turn < 2:
        idx = next((i for i, t in enumerate(ai_state.hand) if t.startswith("E:")), None)
        if idx is None:
            break
        ai_state.hand.pop(idx)
        ai_state.energy += 1
        ai_state.energy_played_this_turn += 1

    # 2) evoca AL MASSIMO 1 dinosauro per turno
    if ai_state.dinos_played_this_turn >= 1:
        return

    if len(ai_state.field) >= 6:
        return

    dino_idx = next((i for i, t in enumerate(ai_state.hand) if t.startswith("DINO:")), None)
    if dino_idx is None:
        return

    token = ai_state.hand.pop(dino_idx)
    cid = int(token.split(":")[1])

    inst = CardInstance(base=def_by_id[cid], current_hp=def_by_id[cid].hp)
    inst.summoned_this_turn = True
    inst.attacks_left = 0
    inst.ability_used_this_turn = True
    ai_state.field.append(inst)

    ai_state.dinos_played_this_turn += 1  # ✅ conta il dinos giocato

    # suono down coerente con fazione
    if inst.base.faction == FACTION_CARN:
        audio.play_sfx(SFX_CARN_DOWN, volume=0.9)
    else:
        audio.play_sfx(SFX_HERB_DOWN, volume=0.9)

def ai_take_turn_normal_attack(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    btns: Tuple[HoverButton, HoverButton],
    user_state: PlayerState,
    ai_state: PlayerState,
    clock: pygame.time.Clock,
) -> bool:
    """
    Turno AI: esegue tutti gli attacchi normali possibili (uno per ogni dinosauro con attacks_left>0
    e non evocato in questo turno). Ritorna True se la partita termina.
    """

    # Helper: indici protetti nel campo difensore
    def protected_indices(field):
        return [i for i, inst in enumerate(field) if getattr(inst, "protect_active", False)]

    def pick_target_index() -> Optional[int]:
        # Se ci sono protetti, target SOLO tra i protetti
        prot = protected_indices(user_state.field)
        candidate_idxs = prot if prot else list(range(len(user_state.field)))

        # Filtra target validi (es. se vuoi evitare leader finché ci sono altri)
        # Se non ti serve la regola sul leader, puoi togliere il filtro.
        non_leader = [idx for idx in candidate_idxs if not getattr(user_state.field[idx], "is_leader", False)]
        if non_leader:
            return non_leader[0]  # semplice: primo valido
        if candidate_idxs:
            return candidate_idxs[0]
        return None

    # Attaccanti AI in ordine (per tutti quelli che possono ancora attaccare)
    for attacker_idx, attacker in list(enumerate(ai_state.field)):
        if attacker_idx >= len(ai_state.field):
            break  # campo modificato (morti) -> safety

        attacker = ai_state.field[attacker_idx]
        can_attack = (attacker.attacks_left > 0 and not attacker.summoned_this_turn)
        if not can_attack:
            continue

        # Se non ci sono target, termina (utente "annientato" lato campo)
        if not user_state.field:
            return True

        # scegli bersaglio rispettando PROTECT
        target_idx = pick_target_index()
        if target_idx is None or target_idx >= len(user_state.field):
            return True

        # animazione attacco AI (se la tua firma differisce, adatta parametri)
        animate_normal_attack_ai(
            scaler=scaler,
            cache=cache,
            audio=audio,
            bg=bg,
            deck_img=deck_img,
            fonts=fonts,
            icon_user=icon_user,
            icon_ai=icon_ai,
            btns=btns,
            user_state=user_state,
            ai_state=ai_state,
            attacker_idx=attacker_idx,
            target_idx=target_idx,
            clock=clock,
        )

        target = user_state.field[target_idx]
        died = apply_normal_attack_damage(attacker, target)

        if died:
            audio.play_sfx(SFX_DEAD, volume=0.9)
            pygame.time.delay(120)
            user_state.field.pop(target_idx)

            res = check_and_handle_game_over(
                scaler=scaler, cache=cache, audio=audio, fonts=fonts,
                user_state=user_state, ai_state=ai_state, clock=clock
            )
            if res is not None:
                return True

        attacker.attacks_left = max(0, attacker.attacks_left - 1)

        # Se hai un flag visivo tipo atk/glow per l'AI, in genere non serve, ma se lo usi:
        if hasattr(attacker, "atk"):
            attacker.atk = should_atk_for_attack(attacker)

        # micro pausa tra attacchi (opzionale)
        pygame.time.delay(120)

    return False



##def ai_take_turn_normal_attack(
##    scaler: Scaler,
##    cache: AssetCache,
##    audio: Audio,
##    bg: pygame.Surface,
##    deck_img: pygame.Surface,
##    fonts: Dict[str, pygame.font.Font],
##    icon_user: pygame.Surface,
##    icon_ai: pygame.Surface,
##    #btns: Tuple[HoverButton, HoverButton, HoverButton],
##    btns: Tuple[HoverButton, HoverButton],
##    user_state: PlayerState,
##    ai_state: PlayerState,
##    clock: pygame.time.Clock,
##) -> bool:
##    """Ritorna True se la partita termina durante gli attacchi."""
##    """
##    AI: attacca con TUTTI gli attaccanti validi (in ordine da sinistra a destra).
##    Target: preferisce non-leader con HP più bassi, altrimenti leader.
##    """
##    while True:
##        # trova prossimo attaccante valido
##        attacker_idx = None
##        for i, inst in enumerate(ai_state.field):
##            if inst.attacks_left > 0 and not inst.summoned_this_turn:
##                attacker_idx = i
##                break
##        if attacker_idx is None:
##            return  # nessun altro attacco
##
##        if not user_state.field:
##            return
##
##        prot = protected_indices(user_state.field)
##        candidate_targets = prot if prot else list(range(len(user_state.field)))
##        # poi scegli da candidate_targets (la tua logica attuale)
##
##        # scegli target
##        candidates = [(i, c) for i, c in enumerate(candidate_targets) if not c.is_leader]
##        if candidates:
##            target_idx = min(candidates, key=lambda x: x[1].current_hp)[0]
##        else:
##            target_idx = 0
##
##        attacker = ai_state.field[attacker_idx]
##        target = user_state.field[target_idx]
##
##        # animazione
##        animate_normal_attack_ai(
##            scaler=scaler,
##            cache=cache,
##            audio=audio,
##            bg=bg,
##            deck_img=deck_img,
##            fonts=fonts,
##            icon_user=icon_user,
##            icon_ai=icon_ai,
##            btns=btns,
##            user_state=user_state,
##            ai_state=ai_state,
##            attacker_idx=attacker_idx,
##            target_idx=target_idx,
##            clock=clock,
##        )
##
##        # danno
##        died = apply_normal_attack_damage(attacker, target)
##
##        if died:
##            audio.play_sfx(SFX_DEAD, volume=0.9)
##            pygame.time.delay(120)
##            user_state.field.pop(target_idx)
##            # game over check
##            if is_player_out_of_moves(user_state):
##                end_screen(scaler, cache, audio, fonts, won=False, clock=clock)
##                return True
##
##
##        attacker.attacks_left = max(0, attacker.attacks_left - 1)
##        attacker.selected = False
##        attacker.atk = (attacker.attacks_left > 0 and not attacker.summoned_this_turn)
##        return False




# =========================
# Rendering HP sulle carte in campo
# =========================
def draw_card_hp_on_field(
    card_img: pygame.Surface,
    hp_current: int,
    hp_max: int,
    font: pygame.font.Font
) -> pygame.Surface:
    surf = card_img.copy()

    color = BIANCO if hp_current == hp_max else GIALLO
    txt = font.render(str(hp_current), True, color)
    shadow = font.render(str(hp_current), True, NERO)

    # 🎯 coordinate RELATIVE ALLA CARTA
    x, y = 179, 22

    # ombra per leggibilità
    surf.blit(shadow, (x + 2, y + 2))
    surf.blit(txt, (x, y))

    return surf


# =========================
# Stato partita (solo setup iniziale per ora)
# =========================
@dataclass
class PlayerState:
    faction: str
    energy_type: str
    leader: CardInstance
    deck: List[str]          # "DINO:<id>" oppure "E:LEAVES"/"E:MEAT"
    hand: List[str]          # stesso encoding del deck
    field: List[CardInstance]
    energy: int = 0
    energy_played_this_turn: int = 0
    dinos_played_this_turn: int = 0


    def deck_count(self) -> int:
        return len(self.deck)

    def hand_count(self) -> int:
        return len(self.hand)


def build_deck_for_faction(
    all_cards: List[CardDef],
    faction: str,
    leader_id: int,
) -> List[str]:
    dinos = [c for c in all_cards if c.faction == faction and c.id != leader_id]
    if not dinos:
        raise ValueError(f"Nessun dinosauro disponibile per fazione {faction}")

    picked = [random.choice(dinos).id for _ in range(10)]  # 10 dinos (anche duplicati)
    energy_type = dinos[0].energy_type  # coerente con fazione (da JSON)
    energy_token = f"E:{energy_type}"

    deck = [f"DINO:{cid}" for cid in picked] + [energy_token] * 10  # +10 energia
    random.shuffle(deck)
    return deck


def faction_to_icon(faction: str) -> str:
    return ICON_LEAVES if faction == FACTION_HERB else ICON_MEAT


def other_faction(faction: str) -> str:
    return FACTION_CARN if faction == FACTION_HERB else FACTION_HERB

def end_screen(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    fonts: Dict[str, pygame.font.Font],
    won: bool,
    clock: pygame.time.Clock,
) -> None:
    """
    Schermata finale minimale:
      - sfondo battlefield
      - scritta centrale OK/KO
      - click o invio per uscire (torna al menu)
    """
    # stop audio di gioco (musica+effetti) come per abbandona
    audio.stop_all()

    bg = cache.image(BATTLE_BG)


    msg = "Vittoria! La tua squadra ha sconfitto tutti gli avversari" if won else \
          "Sconfitta! sei stato annientato dalla squadra avversaria"

    font_end = fonts["end"]  # nuovo font più grande

    # Spezza su due righe per stare comodo a schermo
    lines = [
        "Vittoria!" if won else "Sconfitta!",
        "La tua squadra ha sconfitto tutti gli avversari" if won else "sei stato annientato dalla squadra avversaria",
    ]

    # Pre-render linee con ombra
    renders = []
    for line in lines:
        t = font_end.render(line, True, BIANCO)
        s = font_end.render(line, True, NERO)
        renders.append((t, s))
    
    #msg = "OK" if won else "KO"
    #txt = fonts["title"].render(msg, True, BIANCO)
    #shadow = fonts["title"].render(msg, True, NERO)
    #rect = txt.get_rect(center=(LOGICAL_W // 2, LOGICAL_H // 2))



    while True:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                return
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                return

        surf = scaler.begin()
        # centro verticale con due righe
        total_h = sum(t.get_height() for t, _ in renders) + 20  # 20px di spacing
        y = (LOGICAL_H - total_h) // 2

        for t, s in renders:
            rect = t.get_rect(center=(LOGICAL_W // 2, y + t.get_height() // 2))
            surf.blit(s, (rect.x + 4, rect.y + 4))
            surf.blit(t, rect.topleft)
            y += t.get_height() + 20

        scaler.present()

        #surf = scaler.begin()
        #surf.blit(bg, (0, 0))
        #surf.blit(shadow, (rect.x + 4, rect.y + 4))
        #surf.blit(txt, rect.topleft)
        #scaler.present()



# =========================
# Menu
# =========================
def menu_loop(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    font_big: pygame.font.Font,
    best_score: int,
    all_cards: List[CardDef],
    clock: pygame.time.Clock,
) -> Tuple[str, Optional[str], int]:
    """
    Ritorna:
      ("START", "ERBIVORE"/"CARNIVORE", best_score) oppure ("QUIT", None, best_score)
    """
    # Stop completo se si arriva qui da una partita (specifica: interrompere tutti gli audio)
    audio.stop_all()

    bg = cache.image(MENU_BG)
    help_img = cache.image("help.png")
    show_help = False

    buttons = []
    for name, off, on, pos in MENU_ITEMS:
        buttons.append((name, HoverButton(cache, off, on, pos)))

    audio.play_music_loop(MUSIC_MENU, volume=0.7)

    running = True
    while running:
        dt_ms = clock.tick(60)
        _ = dt_ms  # attualmente non usato qui

        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        left_up = False
        right_up = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT", None, best_score
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "QUIT", None, best_score

            if show_help:
                # qualsiasi tasto o click torna al menu
                if event.type == pygame.KEYDOWN:
                    show_help = False
                elif event.type == pygame.MOUSEBUTTONUP:
                    show_help = False
                continue

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    left_up = True
                elif event.button == 3:
                    right_up = True
        for _, btn in buttons:
            btn.update(mouse_logical)

        # click handling
        if left_up:
            for name, btn in buttons:
                if btn.is_clicked(mouse_logical, mouse_up=True):
                    if name == "menu1":
                        audio.stop_music()
                        return "START", FACTION_HERB, best_score
                    if name == "menu2":
                        audio.stop_music()
                        return "START", FACTION_CARN, best_score
                    if name == "menu3":
                        audio.stop_music()
                        return "QUIT", None, best_score
                    if name == "menu4":
                        show_help = True
                        break


        surf = scaler.begin()
        if show_help:
            surf.blit(help_img, (0, 0))
        else:
            surf.blit(bg, (0, 0))
            for _, btn in buttons:
                btn.draw(surf)
        scaler.present()

    return "QUIT", None, best_score


# =========================
# Avvio partita
# =========================
def select_leader_screen(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    font_title: pygame.font.Font,
    faction_user: str,
    all_cards: List[CardDef],
    clock: pygame.time.Clock,
) -> Tuple[int, int]:
    """
    Mostra le carte della fazione scelta dall’utente, su due file, in ordine ID,
    e fa scegliere il leader con click. Seleziona leader AI random tra fazione opposta.
    Ritorna: (leader_user_id, leader_ai_id)
    """
    bg = cache.image(BATTLE_BG)

    # Carica set carte di fazione
    user_cards = [c for c in all_cards if c.faction == faction_user]
    ai_cards = [c for c in all_cards if c.faction == other_faction(faction_user)]
    if not user_cards or not ai_cards:
        raise ValueError("Carte insufficienti per una o entrambe le fazioni.")

    # Disposizione su due righe "semplice": 5 sopra, resto sotto (coerente con 1..9 o 10..15)
    # (La specifica non dà coordinate esatte; manteniamo un layout stabile.)
    start_x = 270
    row1_y = 280
    row2_y = 620
    gap_x = 10

    cards_rects: List[Tuple[int, pygame.Rect]] = []
    for i, c in enumerate(user_cards):
        row = 0 if i < 5 else 1
        col = i if i < 5 else (i - 5)
        x = start_x + col * (FIELD_CARD_W + gap_x)
        y = row1_y if row == 0 else row2_y
        img = cache.image(f"{c.id}.png")
        rect = img.get_rect(topleft=(x, y))
        cards_rects.append((c.id, rect))

    title_surf = font_title.render(TITLE_LEADER, True, BIANCO)
    title_rect = title_surf.get_rect(center=(LOGICAL_W // 2, 120))

    leader_user_id: Optional[int] = None
    while leader_user_id is None:
        clock.tick(60)

        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        right_up = False
        left_up = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    left_up = True
                elif event.button == 3:
                    right_up = True

        if left_up:
            for cid, rect in cards_rects:
                if rect.collidepoint(mouse_logical):
                    leader_user_id = cid
                    break

        surf = scaler.begin()
        surf.blit(bg, (0, 0))
        surf.blit(title_surf, title_rect)

        # draw cards
        for cid, rect in cards_rects:
            img = cache.image(f"{cid}.png")
            surf.blit(img, rect.topleft)

        scaler.present()

    leader_ai_id = random.choice(ai_cards).id
    return leader_user_id, leader_ai_id


def protected_indices(field):
    return [i for i, inst in enumerate(field) if getattr(inst, "protect_active", False)]

def candidate_target_indices(defender_field):
    prot = protected_indices(defender_field)
    return prot if prot else list(range(len(defender_field)))

def pick_best_enemy_target(user_field):
    # Sceglie il target "migliore" tra quelli consentiti (rispetta PROTECT)
    idxs = candidate_target_indices(user_field)
    if not idxs:
        return None
    # euristica semplice: più basso HP prima (finish), altrimenti leader alla fine
    def score(i):
        inst = user_field[i]
        return (inst.current_hp, 1 if getattr(inst, "is_leader", False) else 0)
    return sorted(idxs, key=score)[0]

def pick_best_ally_target(ai_field):
    if not ai_field:
        return None
    # euristica: cura/proteggi chi ha meno hp%, o leader se rischia
    def score(i):
        inst = ai_field[i]
        frac = inst.current_hp / max(1, inst.base.hp)
        return (frac, 0 if getattr(inst, "is_leader", False) else 1)
    return sorted(range(len(ai_field)), key=score)[0]

def ai_take_turn_use_abilities(
    scaler, cache, audio, bg, deck_img, fonts, icon_user, icon_ai, btns,
    user_state, ai_state, clock
) -> None:
    # costo: 2 per ALL, 1 per altri (come hai stabilito)
    def ability_cost(ab):
        return 2 if ab.targets.upper() == "ALL" else 1

    for caster_idx, caster in enumerate(list(ai_state.field)):
        # può essere cambiato se muore qualcosa, ma lato AI va bene
        ok, msg = can_cast_ability(caster)
        if not ok:
            continue

        ab = caster.base.ability
        if ab is None:
            continue
        a_type = ab.type.upper()
        a_tgt = ab.targets.upper()
        if a_type == "NONE" or a_tgt == "NONE":
            continue

        cost = ability_cost(ab)
        if ai_state.energy < cost:
            continue

        targets_idx = None

        if a_tgt == "ONE":
            if a_type == "ATTACK":
                t = pick_best_enemy_target(user_state.field)
                if t is None:
                    continue
                targets_idx = [t]
            elif a_type in ("HEAL", "SPEED", "SHIELD", "PROTECT"):
                t = pick_best_ally_target(ai_state.field)
                if t is None:
                    continue
                targets_idx = [t]
            else:
                continue

        elif a_tgt in ("SELF", "ALL"):
            # per SELF/ALL non serve targets_idx
            targets_idx = None

        else:
            continue

        # lancia abilità
        applied, result = resolve_ability(
            scaler=scaler, cache=cache, audio=audio, bg=bg, deck_img=deck_img,
            fonts=fonts, icon_user=icon_user, icon_ai=icon_ai,
            btns=btns,
            caster_state=ai_state, other_state=user_state,
            caster_idx=caster_idx,
            targets_idx=targets_idx,
            caster_is_user=False,
            clock=clock,
        )

        # se result porta al menu o gameover lo gestisci dove già lo gestisci nel tuo flusso.
        # qui basta uscire se serve:
        if result == "MENU":
            return

def ai_take_turn_play_cards(ai_state, max_field_size=5) -> None:
    # 1) gioca 1 dinosauro se possibile e non già fatto
    if not getattr(ai_state, "played_dino_this_turn", False):
        if len(ai_state.field) < max_field_size:
            # trova dinosauri in mano
            dinos = [(i, c) for i, c in enumerate(ai_state.hand) if c.base.type.upper() == "DINO"]
            if dinos:
                # euristica: più hp base
                dinos.sort(key=lambda x: x[1].base.hp, reverse=True)
                hand_idx, inst = dinos[0]
                ai_state.hand.pop(hand_idx)
                inst.summoned_this_turn = True
                inst.attacks_left = inst.base.speed  # o come fai per user
                inst.ability_used_this_turn = False
                ai_state.field.append(inst)
                ai_state.played_dino_this_turn = True

    # 2) (opzionale) gioca energie dalla mano
    # se le energie aumentano ai_state.energy nel tuo codice, qui le puoi “consumare”
    # e.g. mentre esistono carte ENERGY in mano, le giochi:
    i = 0
    while i < len(ai_state.hand):
        c = ai_state.hand[i]
        if c.base.type.upper() == "ENERGY":
            ai_state.hand.pop(i)
            ai_state.energy += 1
            continue
        i += 1


def start_match(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    fonts: Dict[str, pygame.font.Font],
    faction_user: str,
    all_cards: List[CardDef],
    clock: pygame.time.Clock,
) -> str:
    """
    Setup partita:
    - ferma menu, bg battlefield, musica game loop
    - schermata scelta leader
    - costruzione mazzi, shuffle
    - setup aree + bottoni (abbandona/completa/skill) con rollover
    - pesca iniziale (struttura base)
    Ritorna "MENU" quando l'utente abbandona (per ora).
    """
    # Nasconde elementi menu (qui implicito) e ferma musica menu
    audio.stop_music()

    # Avvia musica di gioco
    audio.play_music_loop(MUSIC_GAME, volume=0.75)

    # BG
    bg = cache.image(BATTLE_BG)

    # Scelta leader
    leader_user_id, leader_ai_id = select_leader_screen(
        scaler=scaler,
        cache=cache,
        audio=audio,
        font_title=fonts["title"],
        faction_user=faction_user,
        all_cards=all_cards,
        clock=clock,
    )

    # Crea istanze leader
    def_by_id = {c.id: c for c in all_cards}
    user_leader = CardInstance(base=def_by_id[leader_user_id], current_hp=def_by_id[leader_user_id].hp, is_leader=True)
    ai_leader = CardInstance(base=def_by_id[leader_ai_id], current_hp=def_by_id[leader_ai_id].hp, is_leader=True)

    # Mazzi
    user_deck = build_deck_for_faction(all_cards, faction_user, leader_user_id)
    ai_deck = build_deck_for_faction(all_cards, other_faction(faction_user), leader_ai_id)

    user_state = PlayerState(
        faction=faction_user,
        energy_type=user_leader.base.energy_type,
        leader=user_leader,
        deck=user_deck,
        hand=[],
        field=[user_leader],
        energy=0,
    )
    ai_state = PlayerState(
        faction=other_faction(faction_user),
        energy_type=ai_leader.base.energy_type,
        leader=ai_leader,
        deck=ai_deck,
        hand=[],
        field=[ai_leader],
        energy=0,
    )

    # Bottoni
    btn_abbandona = HoverButton(cache, BTN_ABB_OFF, BTN_ABB_ON, (14, 488))
    btn_completa = HoverButton(cache, BTN_COMP_OFF, BTN_COMP_ON, (1654, 488))
    #btn_skill = HoverButton(cache, btn_skill_OFF, btn_skill_ON, (1736, 668))

    # Icone energia
    icon_user = cache.image(faction_to_icon(user_state.faction))
    icon_ai = cache.image(faction_to_icon(ai_state.faction))

    # Deck backs
    deck_img = cache.image(DECK_IMG)

    # Font HP + energia
    font_energy = fonts["energy"]
    font_hp = fonts["hp"]

    # Pesca iniziale: 7 carte ciascuno
    # Implementazione minimale: animazione base con easing per utente e AI come struttura.
    # Nei prossimi step: big reveal (utente) e spostamento in mano con slot liberi.
    run_initial_draw_animations(
        scaler=scaler,
        cache=cache,
        audio=audio,
        bg=bg,
        deck_img=deck_img,
        user_state=user_state,
        ai_state=ai_state,
        fonts=fonts,
        icon_user=icon_user,
        icon_ai=icon_ai,
        #btns=(btn_abbandona, btn_completa, btn_skill),
        btns=(btn_abbandona, btn_completa),
        clock=clock,
    )

    # Turno utente (per ora: solo gestione abbandona + hover bottoni)
    user_turn = True  # inizio con utente come da specifica

    user_turn = True
    turn_started = True
    toast: Optional[Toast] = None
    hover_big_token: Optional[str] = None

    selected_attacker_idx: Optional[int] = None

    # Skill system (latched btn_skill)
    #skill_active: bool = False
    #skill_waiting_target: bool = False

    while True:
        dt = clock.tick(60)
        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())

        if toast and toast.ms_left > 0:
            toast.ms_left -= dt
            if toast.ms_left <= 0:
                toast = None

        # btn_completa interattivo solo su turno utente
        btn_completa.set_enabled(user_turn)
        # btn_skill utilizzabile solo nel turno utente
        #btn_skill.set_enabled(user_turn)

        btn_abbandona.update(mouse_logical)
        btn_completa.update(mouse_logical)
        #btn_skill.update(mouse_logical)

        left_up = False
        right_up = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "MENU"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "MENU"
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    left_up = True
                elif event.button == 3:
                    right_up = True

        # Abbandona sempre attivo
        if left_up and btn_abbandona.is_clicked(mouse_logical, True):
            audio.stop_all()
            return "MENU"

        # Cambio turno (utente -> AI)
        if left_up and user_turn and btn_completa.is_clicked(mouse_logical, True):
            user_turn = False
            turn_started = True

        def_by_id = {c.id: c for c in all_cards}

        # ===== Inizio turno: reset contatori + pesca automatica (1 carta se <7) =====
        if turn_started:
            current = user_state if user_turn else ai_state
            current.energy_played_this_turn = 0
            current.dinos_played_this_turn = 0


            # reset minimi (per step futuri)
            for inst in current.field:
                inst.attacks_left = 1
                inst.atk = False
                inst.selected = False
                inst.ability_used_this_turn = False
                inst.summoned_this_turn = False  # dopo il cambio turno, tutte diventano "vecchie"

            for inst in user_state.field:
                inst.speed_icon = False
            for inst in ai_state.field:
                inst.speed_icon = False

            #resetta scudo di shield
            if user_turn:
                # Inizia TURNO UTENTE: scadono gli shield dell'UTENTE (messi nel suo turno precedente)
                for inst in user_state.field:
                    inst.shield_points = 0
            else:
                # Inizia TURNO AI: scadono gli shield dell'AI (messi nel suo turno precedente)
                for inst in ai_state.field:
                    inst.shield_points = 0

            #resettta scudo di protect
            if user_turn:
                # inizia turno utente -> scadono i protect dell'utente
                for inst in user_state.field:
                    inst.protect_active = False
            else:
                # inizia turno AI -> scadono i protect dell'AI
                for inst in ai_state.field:
                    inst.protect_active = False



            # aggiorna atk per il turno utente
            if user_turn:
                for inst in user_state.field:
                    inst.atk = (inst.attacks_left > 0 and not inst.summoned_this_turn)


            # pesca automatica
            draw_one_card_with_animation(
                scaler=scaler,
                cache=cache,
                audio=audio,
                bg=bg,
                deck_img=deck_img,
                player=current,
                is_user=user_turn,          # reveal solo se utente
                fonts=fonts,
                icon_user=icon_user,
                icon_ai=icon_ai,
                #btns=(btn_abbandona, btn_completa, btn_skill),
                btns=(btn_abbandona, btn_completa),
                other_player=ai_state if user_turn else user_state,
                clock=clock,
            )

            # ----- Se è iniziato il turno AI, esegui l'intero turno AI in una volta sola -----
            if not user_turn:
                # 1) AI gioca carte (energie + max 1 dinosauro/turno) - usa la tua funzione già presente
                ai_play_cards(audio=audio, ai_state=ai_state, def_by_id=def_by_id)

                # 2) AI usa abilità (se può)
                ai_take_turn_use_abilities(
                    scaler=scaler, cache=cache, audio=audio, bg=bg, deck_img=deck_img,
                    fonts=fonts, icon_user=icon_user, icon_ai=icon_ai,
                    btns=(btn_abbandona, btn_completa),
                    user_state=user_state, ai_state=ai_state,
                    clock=clock,
                )

                # 3) AI attacca con tutti i dinosauri che possono (già rispetta PROTECT)
                ended = ai_take_turn_normal_attack(
                    scaler=scaler,
                    cache=cache,
                    audio=audio,
                    bg=bg,
                    deck_img=deck_img,
                    fonts=fonts,
                    icon_user=icon_user,
                    icon_ai=icon_ai,
                    btns=(btn_abbandona, btn_completa),
                    user_state=user_state,
                    ai_state=ai_state,
                    clock=clock,
                )
                if ended:
                    return "MENU"

                # 4) fine turno AI -> passa a utente
                user_turn = True
                turn_started = True
                toast = Toast("Tocca a te", 1500)
                continue  # IMPORTANTISSIMO: evita di settare turn_started=False qui sotto

            # fine "inizio turno" normale
            turn_started = False

        # ===== Hover big sulla mano utente (sempre, anche fuori turno) =====
        hover_big_token = None
        user_hand_rects = hand_card_rects(user_state.hand, POS_HAND_USER)
        idx_hover = hovered_hand_index(mouse_logical, user_hand_rects)
        if idx_hover is not None and 0 <= idx_hover < len(user_state.hand):
            hover_big_token = user_state.hand[idx_hover]

        # ===== Click su carta mano: solo se turno utente =====
        if left_up and user_turn:
            idx_click = hovered_hand_index(mouse_logical, user_hand_rects)
            if idx_click is not None and 0 <= idx_click < len(user_state.hand):
                token = user_state.hand[idx_click]

                # Energia
                if token.startswith("E:"):
                    if user_state.energy_played_this_turn >= 2:
                        toast = Toast("Non si possono giocare più di due carte energia per turno", 2000)
                    else:
                        user_state.energy += 1
                        user_state.energy_played_this_turn += 1
                        # rimuovi carta e shift a sinistra
                        user_state.hand.pop(idx_click)

                # Dinosauro
                elif token.startswith("DINO:"):
                    if user_state.dinos_played_this_turn >= 1:
                        toast = Toast("Non puoi giocare più di 1 dinosauro per turno", 2000)
                    elif len(user_state.field) >= 6:
                        toast = Toast("Non è possibile avere più di 6 carte in campo", 2000)
                    else:
                        cid = int(token.split(":")[1])
                        inst = CardInstance(base=def_by_id[cid], current_hp=def_by_id[cid].hp)
                        inst.summoned_this_turn = True
                        inst.attacks_left = 0               # non può attaccare nel turno in cui entra :contentReference[oaicite:6]{index=6}
                        inst.ability_used_this_turn = True  # non può usare abilità nello stesso turno :contentReference[oaicite:7]{index=7}
                        user_state.field.append(inst)

                        # suono down coerente con fazione della carta
                        if inst.base.faction == FACTION_CARN:
                            audio.play_sfx(SFX_CARN_DOWN, volume=0.9)
                        else:
                            audio.play_sfx(SFX_HERB_DOWN, volume=0.9)

                        user_state.hand.pop(idx_click)
                        user_state.dinos_played_this_turn += 1 

        # ===== ATTACCO NORMALE (solo turno utente) =====
        if user_turn:
            user_field_rects = field_card_rects(user_state.field, POS_FIELD_USER)
            ai_field_rects = field_card_rects(ai_state.field, POS_FIELD_AI)


            if left_up or right_up:
                idx_u = hovered_field_index(mouse_logical, user_field_rects)
                idx_a = hovered_field_index(mouse_logical, ai_field_rects)

                # ===== ABILITA' (tasto destro) =====
                if right_up and selected_attacker_idx is not None:
                    caster = user_state.field[selected_attacker_idx]
                    ab = caster.base.ability
                    a_type = ab.type.upper()
                    a_tgt = ab.targets.upper()

                    ok, msg = can_cast_ability(caster)
                    if not ok:
                        toast = Toast(msg, 2000)
                        continue

                    # SELF/ALL: solo right-click sul caster stesso
                    if a_tgt in ("SELF", "ALL"):
                        if idx_u is not None and idx_u == selected_attacker_idx:
                            applied, result = resolve_ability(
                                scaler=scaler, cache=cache, audio=audio, bg=bg, deck_img=deck_img,
                                fonts=fonts, icon_user=icon_user, icon_ai=icon_ai,
                                btns=(btn_abbandona, btn_completa),  # o lascia la tua tupla attuale
                                caster_state=user_state, other_state=ai_state,
                                caster_idx=selected_attacker_idx,
                                targets_idx=None,
                                caster_is_user=True,
                                clock=clock,
                            )
                            if result == "MENU":
                                return "MENU"
                            if isinstance(result, str):
                                toast = Toast(result, 2000)

                            caster.selected = False
                            caster.atk = should_atk_for_attack(caster)
                            selected_attacker_idx = None
                        continue

                    # ONE: dipende dal tipo
                    if a_tgt == "ONE":
                        target_idxs = None

                        if a_type == "ATTACK":
                            if idx_a is not None:
                                target_idxs = [idx_a]
                        elif a_type in ("HEAL", "SPEED", "SHIELD"):
                            if idx_u is not None:
                                target_idxs = [idx_u]

                        if target_idxs is not None:
                            applied, result = resolve_ability(
                                scaler=scaler, cache=cache, audio=audio, bg=bg, deck_img=deck_img,
                                fonts=fonts, icon_user=icon_user, icon_ai=icon_ai,
                                btns=(btn_abbandona, btn_completa),
                                caster_state=user_state, other_state=ai_state,
                                caster_idx=selected_attacker_idx,
                                targets_idx=target_idxs,
                                caster_is_user=True,
                                clock=clock,
                            )
                            if result == "MENU":
                                return "MENU"
                            if isinstance(result, str):
                                toast = Toast(result, 2000)

                            caster.selected = False
                            caster.atk = should_atk_for_attack(caster)
                            selected_attacker_idx = None

                        continue


                # 1) CLICK SU CAMPO UTENTE: toggle / cambio selezione
                if idx_u is not None:
                    inst = user_state.field[idx_u]

                    # click sulla stessa carta selezionata => toggle OFF
                    if selected_attacker_idx is not None and idx_u == selected_attacker_idx:
                        inst.selected = False
                        inst.atk = should_atk_for_attack(inst)
                        selected_attacker_idx = None
                        continue

                    # click su un'altra carta => sposta selezione SEMPRE (nessun toast qui)
                    if selected_attacker_idx is not None and idx_u != selected_attacker_idx:
                        prev = user_state.field[selected_attacker_idx]
                        prev.selected = False
                        prev.atk = should_atk_for_attack(prev)

                    # seleziona la nuova
                    for c in user_state.field:
                        if c is not inst:
                            c.selected = False
                            c.atk = should_atk_for_attack(c)

                    inst.selected = True
                    inst.atk = False
                    selected_attacker_idx = idx_u
                    continue

                # 2) CLICK SU CAMPO AI: esegui attacco se ho un attaccante selezionato
                elif selected_attacker_idx is not None and idx_a is not None:
                    attacker = user_state.field[selected_attacker_idx]

                    can_attack = (attacker.attacks_left > 0 and not attacker.summoned_this_turn)
                    if not can_attack:
                        toast = Toast("Questa carta non può attaccare in questo turno", 1500)
                        # NON deselezionare: resta selezionata (utile per skill)
                        continue

                    target = ai_state.field[idx_a]

                    if not is_attack_target_allowed(ai_state.field, idx_a):
                        toast = Toast("Devi attaccare un dinosauro protetto", 1500)
                        continue


                    animate_normal_attack(
                        scaler=scaler,
                        cache=cache,
                        audio=audio,
                        bg=bg,
                        deck_img=deck_img,
                        fonts=fonts,
                        icon_user=icon_user,
                        icon_ai=icon_ai,
                        #btns=(btn_abbandona, btn_completa, btn_skill),
                        btns=(btn_abbandona, btn_completa),
                        user_state=user_state,
                        ai_state=ai_state,
                        attacker_idx=selected_attacker_idx,
                        target_idx=idx_a,
                        clock=clock,
                    )

                    died = apply_normal_attack_damage(attacker, target)

                    if died:
                        audio.play_sfx(SFX_DEAD, volume=0.9)
                        pygame.time.delay(120)
                        ai_state.field.pop(idx_a)

                        res = check_and_handle_game_over(
                            scaler=scaler, cache=cache, audio=audio, fonts=fonts,
                            user_state=user_state, ai_state=ai_state, clock=clock
                        )
                        if res is not None:
                            return "MENU"

                    attacker.attacks_left = max(0, attacker.attacks_left - 1)
                    attacker.selected = False
                    attacker.atk = should_atk_for_attack(attacker)
                    selected_attacker_idx = None

                # 3) CLICK A VUOTO: deseleziona (se c'era selezione)
                elif selected_attacker_idx is not None and idx_u is None and idx_a is None:
                    inst = user_state.field[selected_attacker_idx]
                    inst.selected = False
                    inst.atk = should_atk_for_attack(inst)
                    selected_attacker_idx = None




        # ===== Render =====
        surf = scaler.begin()
        surf.blit(bg, (0, 0))

        if ai_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_AI)
        if user_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_USER)

        surf.blit(icon_ai, POS_ENERGY_AI)
        surf.blit(icon_user, POS_ENERGY_USER)

        ai_energy_txt = font_energy.render(str(ai_state.energy), True, BIANCO)
        user_energy_txt = font_energy.render(str(user_state.energy), True, BIANCO)
        surf.blit(ai_energy_txt, (133, 42))
        surf.blit(user_energy_txt, (133, 987))

        btn_abbandona.draw(surf)
        btn_completa.draw(surf)
        #btn_skill.draw(surf)

        draw_field_row(surf, cache, ai_state.field, POS_FIELD_AI, font_hp, use_states=False)
        draw_field_row(surf, cache, user_state.field, POS_FIELD_USER, font_hp, use_states=True)

        draw_hand_row(surf, cache, user_state.hand, POS_HAND_USER, show_faces=True)
        draw_hand_row(surf, cache, ai_state.hand, POS_HAND_AI, show_faces=False)

        # hover big carta mano (utente)
        if hover_big_token:
            big = token_to_big_image(cache, hover_big_token)
            big_pos = (LOGICAL_W // 2 - big.get_width() // 2, LOGICAL_H // 2 - big.get_height() // 2)
            surf.blit(big, big_pos)

        draw_toast(surf, toast, fonts["title"])

        scaler.present()

        # ===== Turno AI: per ora solo "passa" (poi nel prossimo step faremo la sequenza AI) =====
        if not user_turn:
            # 1) AI gioca carte
            ai_play_cards(audio=audio, ai_state=ai_state, def_by_id=def_by_id)

            # 2) AI attacca (ora potenzialmente più attacchi)
            ended = ai_take_turn_normal_attack(
                scaler=scaler,
                cache=cache,
                audio=audio,
                bg=bg,
                deck_img=deck_img,
                fonts=fonts,
                icon_user=icon_user,
                icon_ai=icon_ai,
                #btns=(btn_abbandona, btn_completa, btn_skill),
                btns=(btn_abbandona, btn_completa),
                user_state=user_state,
                ai_state=ai_state,
                clock=clock,
            )
            if ended:
                return "MENU"

            # 3) Frame finale "stabile" prima del toast (così non appare durante animazioni)
            # (render “normale” senza hover big)
            surf = scaler.begin()
            surf.blit(bg, (0, 0))

            if ai_state.deck_count() > 0:
                surf.blit(deck_img, POS_DECK_AI)
            if user_state.deck_count() > 0:
                surf.blit(deck_img, POS_DECK_USER)

            surf.blit(icon_ai, POS_ENERGY_AI)
            surf.blit(icon_user, POS_ENERGY_USER)

            ai_energy_txt = font_energy.render(str(ai_state.energy), True, BIANCO)
            user_energy_txt = font_energy.render(str(user_state.energy), True, BIANCO)
            surf.blit(ai_energy_txt, (133, 42))
            surf.blit(user_energy_txt, (133, 987))

            btn_abbandona.draw(surf)
            btn_completa.draw(surf)
            #btn_skill.draw(surf)

            draw_field_row(surf, cache, ai_state.field, POS_FIELD_AI, font_hp, use_states=False)
            draw_field_row(surf, cache, user_state.field, POS_FIELD_USER, font_hp, use_states=True)

            draw_hand_row(surf, cache, user_state.hand, POS_HAND_USER, show_faces=True)
            draw_hand_row(surf, cache, ai_state.hand, POS_HAND_AI, show_faces=False)

            scaler.present()
            pygame.time.delay(150)  # piccolo respiro

            toast = Toast("Tocca a te", 1500)

            user_turn = True
            turn_started = True



def draw_hand_row(
    surf: pygame.Surface,
    cache: AssetCache,
    hand: List[str],
    origin: Tuple[int, int],
    show_faces: bool,
) -> None:
    x0, y0 = origin
    for i, token in enumerate(hand):
        x = x0 + i * HAND_STEP_X
        y = y0
        if show_faces:
            img = token_to_hand_image(cache, token)
        else:
            img = cache.image(DECK_IMG)
        surf.blit(img, (x, y))


def token_to_hand_image(cache: AssetCache, token: str) -> pygame.Surface:
    # token: "DINO:<id>" o "E:LEAVES"/"E:MEAT"
    if token.startswith("DINO:"):
        cid = int(token.split(":")[1])
        return cache.image(f"{cid}_small.png")

    if token == "E:LEAVES":
        return cache.image("e_leaves_small.png")

    if token == "E:MEAT":
        return cache.image("e_meat_small.png")

    return cache.image(DECK_IMG)



def draw_field_row(
    surf: pygame.Surface,
    cache: AssetCache,
    player_field: List[CardInstance],
    origin: Tuple[int, int],
    font_hp: pygame.font.Font,
    use_states: bool
) -> None:
    ICON_SPEED = "speed.png"
    ICON_SHIELD = "shield.png"
    ox, oy = origin
    for idx, inst in enumerate(player_field[:FIELD_MAX]):
        x = ox + idx * FIELD_CARD_W
        y = oy
        if use_states:
            base_img = cache.image(field_image_name(inst))  # usa atk/glow/selected
        else:
            cid = inst.base.id
            base_img = cache.image(f"{cid}.png")
        img = draw_card_hp_on_field(base_img, inst.current_hp, inst.base.hp, font_hp)
        surf.blit(img, (x, y))
        if inst.speed_icon:
            sp = cache.image(ICON_SPEED)
            surf.blit(sp, (x + 24, y + 185))
        if inst.shield_points > 0:
            font_shield = pygame.font.Font(None, 60)
            sh = cache.image(ICON_SHIELD)
            surf.blit(sh, (x + 92, y + 70))

            # testo punti scudo sopra l'icona
            shield_txt = font_shield.render(str(inst.shield_points), True, BIANCO)
            surf.blit(shield_txt, (x + 92 + 34, y + 70 + 19))
        if inst.protect_active:
            ico = cache.image(ICON_PROTECT)
            surf.blit(ico, (x + 10, y + 70))





def run_initial_draw_animations(
    scaler: Scaler,
    cache: AssetCache,
    audio: Audio,
    bg: pygame.Surface,
    deck_img: pygame.Surface,
    user_state: PlayerState,
    ai_state: PlayerState,
    fonts: Dict[str, pygame.font.Font],
    icon_user: pygame.Surface,
    icon_ai: pygame.Surface,
    #btns: Tuple[HoverButton, HoverButton, HoverButton],
    btns: Tuple[HoverButton, HoverButton],
    clock: pygame.time.Clock,
) -> None:
    """
    Pesca iniziale:
      - 7 volte utente: deck->centro (300ms), reveal big 2s, poi in mano (slot)
      - 7 volte AI: deck->mano AI (300ms), sempre retro
    Qui: implementazione compatta ma fedele a tempi/easing.
    """
    #btn_abbandona, btn_completa, btn_skill = btns
    btn_abbandona, btn_completa = btns
    font_energy = fonts["energy"]
    font_hp = fonts["hp"]

    center_pos = (LOGICAL_W // 2 - deck_img.get_width() // 2, LOGICAL_H // 2 - deck_img.get_height() // 2)

    # helper render static UI
    def render_base() -> pygame.Surface:
        surf = scaler.begin()
        surf.blit(bg, (0, 0))

        # Deck backs (sotto l'animazione)
        if ai_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_AI)
        if user_state.deck_count() > 0:
            surf.blit(deck_img, POS_DECK_USER)

        # Icone energia
        surf.blit(icon_ai, POS_ENERGY_AI)
        surf.blit(icon_user, POS_ENERGY_USER)

        # Energia
        ai_energy_txt = font_energy.render(str(ai_state.energy), True, BIANCO)
        user_energy_txt = font_energy.render(str(user_state.energy), True, BIANCO)
        surf.blit(ai_energy_txt, (133, 42))
        surf.blit(user_energy_txt, (133, 987))

        # Bottoni (in avvio partita sono già presenti)
        mouse_logical = scaler.to_logical_pos(pygame.mouse.get_pos())
        btn_abbandona.update(mouse_logical)
        btn_completa.update(mouse_logical)
        #btn_skill.update(mouse_logical)

        btn_abbandona.draw(surf)
        btn_completa.draw(surf)
        #btn_skill.draw(surf)

        # Leader in campo
        draw_field_row(surf, cache, ai_state.field, POS_FIELD_AI, font_hp, use_states=False)
        draw_field_row(surf, cache, user_state.field, POS_FIELD_USER, font_hp, use_states=True)

        # Mano (già parzialmente riempita durante anim)
        draw_hand_row(surf, cache, user_state.hand, POS_HAND_USER, show_faces=True)
        draw_hand_row(surf, cache, ai_state.hand, POS_HAND_AI, show_faces=False)

        return surf

    # 7 carte utente con reveal
    for _ in range(7):
        if not user_state.deck:
            break

        token = user_state.deck.pop(0)
        audio.play_sfx(SFX_FLIP, volume=0.9)

        mover = MovingSprite(
            image=deck_img,
            start=POS_DECK_USER,
            end=center_pos,
            duration_ms=300,
        )

        # fase movimento
        while not mover.done:
            dt = clock.tick(60)
            _consume_quit_events()
            mover.update(dt)

            surf = render_base()
            surf.blit(mover.image, mover.pos())
            scaler.present()

        # reveal big per 2s al centro
        reveal_img = token_to_big_image(cache, token)
        reveal_pos = (LOGICAL_W // 2 - reveal_img.get_width() // 2, LOGICAL_H // 2 - reveal_img.get_height() // 2)

        reveal_time = 500 #2000
        elapsed = 0
        while elapsed < reveal_time:
            dt = clock.tick(60)
            _consume_quit_events()
            elapsed += dt

            surf = render_base()
            surf.blit(reveal_img, reveal_pos)
            scaler.present()

        # aggiungi in mano nel primo slot libero (fine animazione)
        if len(user_state.hand) < 7:
            user_state.hand.append(token)

        # se era l'ultima carta, l'immagine mazzo sparirà nel render_base (perché deck_count() == 0)

    # 7 carte AI (retro che vola verso mano AI)
    for _ in range(7):
        if not ai_state.deck:
            break

        token = ai_state.deck.pop(0)
        audio.play_sfx(SFX_FLIP, volume=0.9)

        # prossima posizione in mano AI
        slot_idx = len(ai_state.hand)
        target_x = POS_HAND_AI[0] + slot_idx * HAND_STEP_X
        target_y = POS_HAND_AI[1]

        mover = MovingSprite(
            image=deck_img,
            start=POS_DECK_AI,
            end=(target_x, target_y),
            duration_ms=300,
        )

        while not mover.done:
            dt = clock.tick(60)
            _consume_quit_events()
            mover.update(dt)

            surf = render_base()
            surf.blit(mover.image, mover.pos())
            scaler.present()

        if len(ai_state.hand) < 7:
            ai_state.hand.append(token)


def token_to_big_image(cache: AssetCache, token: str) -> pygame.Surface:
    # token: "DINO:<id>" o "E:LEAVES"/"E:MEAT"
    if token.startswith("DINO:"):
        cid = int(token.split(":")[1])
        return cache.image(f"{cid}_big.png")
    if token == "E:LEAVES":
        return cache.image("e_leaves_big.png")
    if token == "E:MEAT":
        return cache.image("e_meat_big.png")
    return cache.image(DECK_IMG)


def _consume_quit_events() -> None:
    # durante animazioni: consumiamo quit/escape in modo semplice
    for e in pygame.event.get([pygame.QUIT, pygame.KEYDOWN]):
        if e.type == pygame.QUIT:
            raise SystemExit
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            raise SystemExit


# =========================
# Main / integrazione Jacoplay
# =========================
def run_game(best_score: int = 0) -> int:
    pygame.init()
    pygame.mixer.init()

    # window (ridimensionabile). Rendering scalato su logica fissa 1920x1080.
    window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("DinoWar (game_09_dinowar)")

    scaler = Scaler(window)
    cache = AssetCache()
    audio = Audio(cache)

    # Font (unico font, varie dimensioni)
    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError(f"Font mancante: {FONT_PATH}")

    fonts = {
        "title": pygame.font.Font(FONT_PATH, 40),   # “SCEGLI IL TUO LEADER”
        "energy": pygame.font.Font(FONT_PATH, 50),  # numeri energia
        "hp": pygame.font.Font(FONT_PATH, 18),      # HP sulle carte
        "shield": pygame.font.Font(FONT_PATH, 45),      # HP sugli shield
        "end": pygame.font.Font(FONT_PATH, 70),
    }

    clock = pygame.time.Clock()

    # Carica carte dal JSON
    all_cards = load_cards_from_json(JSON_PATH)

    # Loop principale: menu -> partita -> menu ...
    while True:
        action, faction_user, best_score = menu_loop(
            scaler=scaler,
            cache=cache,
            audio=audio,
            font_big=fonts["title"],
            best_score=best_score,
            all_cards=all_cards,
            clock=clock,
        )

        if action == "QUIT":
            audio.stop_all()
            pygame.quit()
            return best_score

        if action == "START" and faction_user in (FACTION_HERB, FACTION_CARN):
            # partita
            try:
                result = start_match(
                    scaler=scaler,
                    cache=cache,
                    audio=audio,
                    fonts=fonts,
                    faction_user=faction_user,
                    all_cards=all_cards,
                    clock=clock,
                )
            except SystemExit:
                audio.stop_all()
                pygame.quit()
                return best_score

            # quando si esce da start_match torniamo al menu
            if result == "MENU":
                continue


def main(best_score: int = 0) -> int:
    """
    Entry point chiamabile da Jacoplay: deve ricevere best_score e restituirlo.
    """
    return run_game(best_score)


if __name__ == "__main__":
    # esecuzione standalone
    bs = 0
    if len(sys.argv) > 1:
        try:
            bs = int(sys.argv[1])
        except ValueError:
            bs = 0
    out = main(bs)
    print(out)

"""Who's playing? -- player accounts on a shared computer or browser.

The first screen of the game. Every player has a card: their mascot in its
costume, name, Lv and rank title, study streak, and a padlock if they set
a PIN. Pick a card to play (entering the PIN if there is one), "+ NEW
PLAYER" to make an account -- type a name, then choose a 4-digit PIN or
skip it -- or GUEST to play without one. Each account keeps its own save,
level, 円, costumes, trophies and missions (kobito/save_game.py), and shows
up on the leaderboard (kobito/board_screen.py).

Name and PIN entry work with a keyboard (just type) and with a gamepad or
touch through the on-screen keys.

choose_player() runs the whole flow and returns the signed-in account
(a dict from save_game.list_accounts()), or None for guest.
"""

import asyncio
import math

import pygame

from kobito import audio, gear_art, progress, save_game, setup_ui, town_ui, ui
from kobito import input as game_input
from kobito.assets import load_character_animations
from kobito.characters import get_character
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH

CARD = (176, 236)
CARD_GAP = 16
CARDS_VISIBLE = 4
NAME_ROWS = ("ABCDEFGHIJ", "KLMNOPQRST", "UVWXYZ0123", "456789-._ ")
PIN_KEYS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "DEL", "0", "OK")
PIN_LENGTH = 4
MAX_PIN_TRIES = 3
FLAME = (255, 140, 50)


def draw_flame(surface, center, size, color=FLAME):
    """The study-streak flame."""
    x, y = center
    s = size
    outer = [(x, y - s), (x + s * 0.55, y - s * 0.1), (x + s * 0.45, y + s * 0.5), (x, y + s * 0.7),
             (x - s * 0.45, y + s * 0.5), (x - s * 0.55, y - s * 0.1), (x - s * 0.15, y - s * 0.35)]
    pygame.draw.polygon(surface, ui.OUTLINE, [(px + (1 if px > x else -1), py + 1) for px, py in outer])
    pygame.draw.polygon(surface, color, outer)
    inner = [(x, y - s * 0.25), (x + s * 0.25, y + s * 0.2), (x, y + s * 0.5), (x - s * 0.25, y + s * 0.2)]
    pygame.draw.polygon(surface, (255, 230, 120), inner)


def draw_padlock(surface, center, size=12, color=ui.GOLD):
    x, y = center
    body = pygame.Rect(0, 0, size, size * 0.8)
    body.midtop = (x, y)
    pygame.draw.circle(surface, ui.OUTLINE, (x, y), size * 0.45, 4)
    pygame.draw.circle(surface, color, (x, y), size * 0.45 - 1, 2)
    pygame.draw.rect(surface, ui.OUTLINE, body.inflate(4, 4), border_radius=3)
    pygame.draw.rect(surface, color, body, border_radius=3)


class _Base:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito")
        self.clock = pygame.time.Clock()
        self.nav = town_ui.Nav()
        self.backdrop = setup_ui.backdrop()
        self.time = 0.0
        self.message = None      # (words, color, seconds left)
        game_input.get_joysticks()

    def _say(self, words, color=ui.RED, seconds=2.4):
        self.message = (words, color, seconds)

    def _tick(self):
        dt = self.clock.tick(FPS) / 1000.0
        self.time += dt
        self.backdrop.update(dt)
        if self.message:
            words, color, left = self.message
            self.message = (words, color, left - dt) if left > dt else None
        return dt

    def _quit_check(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)

    def _draw_message(self, y):
        if self.message:
            words, color, _ = self.message
            town_ui.toast(self.screen, words, color, (SCREEN_WIDTH // 2, y))


# -- Who's playing? -------------------------------------------------------------------

class AccountScreen(_Base):
    """The player cards. run() returns ("play", account), ("new", None),
    ("guest", None)."""

    def __init__(self):
        super().__init__()
        self.accounts = save_game.list_accounts()
        self.profiles = {a["id"]: save_game.load_profile_of(a["id"]) for a in self.accounts}
        self.portraits = {}
        self.index = 0
        self.first = 0               # first visible card
        self.confirm_delete = None   # account id asked about once
        self.cards = []
        self.guest_rect = pygame.Rect(0, 0, 0, 0)

    @property
    def choices(self):
        return self.accounts + ["new"]

    def _portrait(self, account):
        """The mascot this player last played, wearing their costume."""
        cid = account.get("character_id")
        if not cid:
            return None
        worn = self.profiles[account["id"]].worn()
        key = (cid, tuple(worn))
        if key not in self.portraits:
            character = get_character(cid)
            frame = load_character_animations(cid, character["color"])["idle"].frames[0]
            dressed = gear_art.dress(frame, cid, worn)
            self.portraits[key] = pygame.transform.scale(dressed, (dressed.get_width() * 2, dressed.get_height() * 2))
        return self.portraits[key]

    async def run(self):
        while True:
            self._tick()
            for event in game_input.events():
                result = self._handle(event)
                if result:
                    return result
            self._draw()
            await asyncio.sleep(0)

    def _move(self, step):
        self.index = (self.index + step) % len(self.choices)
        self.first = min(max(self.first, self.index - CARDS_VISIBLE + 1), self.index)
        self.confirm_delete = None
        audio.play("select")

    def _pick(self):
        choice = self.choices[self.index]
        audio.play("confirm")
        return ("new", None) if choice == "new" else ("play", choice)

    def _delete(self):
        choice = self.choices[self.index]
        if choice == "new":
            return
        if self.confirm_delete != choice["id"]:
            self.confirm_delete = choice["id"]
            self._say(f"Delete {choice['name']}? Press Del (or X) again", ui.RED, 3.0)
            return
        save_game.delete_account(choice["id"])
        audio.play("back")
        self.accounts = save_game.list_accounts()
        self.index = min(self.index, len(self.choices) - 1)
        self.first = 0
        self.confirm_delete = None
        self._say(f"{choice['name']} was deleted", ui.MUTED)

    def _handle(self, event):
        self._quit_check(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_g:
            return ("guest", None)
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_DELETE) or \
                (event.type == pygame.JOYBUTTONDOWN and event.button == game_input.X):
            self._delete()
            return None
        if event.type == pygame.JOYBUTTONDOWN and event.button == game_input.Y:
            return ("guest", None)
        action = self.nav.handle(event)
        if action in ("left", "right", "up", "down"):
            self._move(1 if action in ("right", "down") else -1)
        elif action == "confirm":
            return self._pick()
        elif action == "back" and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            raise SystemExit
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            if self.guest_rect.collidepoint(pos):
                return ("guest", None)
            for i, rect in self.cards:
                if rect.collidepoint(pos):
                    if i == self.index:
                        return self._pick()
                    self.index = i
                    audio.play("select")
        return None

    def _draw(self):
        screen = self.screen
        self.backdrop.draw(screen)
        setup_ui.draw_title(screen, "WHO'S PLAYING?", "だれが あそぶ？")
        ui.text(screen, "KOBITO", ui.title_font(32), (SCREEN_WIDTH // 2, 24), anchor="center", color=ui.GOLD,
                thickness=3)
        shown = self.choices[self.first:self.first + CARDS_VISIBLE]
        total = len(shown) * CARD[0] + (len(shown) - 1) * CARD_GAP
        x = SCREEN_WIDTH // 2 - total // 2
        self.cards = []
        for k, choice in enumerate(shown):
            i = self.first + k
            rect = pygame.Rect(x + k * (CARD[0] + CARD_GAP), 132, *CARD)
            if i == self.index:
                rect.y -= 6 + town_ui.bob(self.time, 4, 2)
            self.cards.append((i, rect))
            if choice == "new":
                self._draw_new_card(rect, i == self.index)
            else:
                self._draw_card(rect, choice, i == self.index)
        if self.first > 0:
            setup_ui.arrow_button(screen, (40, 250), -1)
        if self.first + CARDS_VISIBLE < len(self.choices):
            setup_ui.arrow_button(screen, (SCREEN_WIDTH - 40, 250), 1)

        font = ui.label_font(16)
        words = game_input.prompt("G  PLAY AS GUEST", "Y  PLAY AS GUEST", "PLAY AS GUEST")
        self.guest_rect = pygame.Rect(0, 0, font.size(words)[0] + 36, 34)
        self.guest_rect.center = (SCREEN_WIDTH // 2, 410)
        ui.panel(screen, self.guest_rect, bg=(30, 24, 46, 230), radius=16)
        ui.text(screen, words, font, self.guest_rect.center, color=ui.MUTED, anchor="center", thickness=1)
        self._draw_message(452)
        setup_ui.hints(screen, [(setup_ui.ARROWS, "choose"), ("Enter", "play"), ("Del", "delete"), ("Esc", "quit")],
                       [(setup_ui.DPAD, "choose"), ("pad-a", "play"), ("pad-x", "delete"), ("pad-y", "guest")])
        pygame.display.flip()

    def _card_frame(self, rect, selected):
        ui.panel(self.screen, rect, bg=(44, 36, 70, 245) if selected else (22, 18, 38, 235),
                 edge=(*ui.GOLD, 255) if selected else (120, 110, 150, 150), radius=14)
        if selected:
            pygame.draw.rect(self.screen, ui.GOLD, rect.inflate(6, 6), width=2, border_radius=16)

    def _draw_card(self, rect, account, selected):
        screen = self.screen
        profile = self.profiles.get(account["id"])
        self._card_frame(rect, selected)
        well = pygame.Rect(rect.x + 14, rect.y + 14, rect.width - 28, 112)
        pygame.draw.rect(screen, (60, 50, 92), well, border_radius=10)
        portrait = self._portrait(account)
        if portrait:
            screen.blit(portrait, portrait.get_rect(midbottom=(well.centerx, well.bottom - 4)))
        else:
            ui.text(screen, "?", ui.title_font(48), well.center, color=ui.MUTED, anchor="center")
        if save_game.has_pin(account):
            draw_padlock(screen, (rect.right - 24, rect.y + 22), 12)
        ui.text(screen, account["name"], ui.title_font(32) if len(account["name"]) <= 7 else ui.body_font(20),
                (rect.centerx, rect.y + 146), anchor="center", thickness=2)
        level = profile.level if profile else 1
        kanji, _, english = progress.rank_for(level)
        ui.text(screen, f"Lv {level}  ·  {english}", ui.label_font(16), (rect.centerx, rect.y + 176),
                color=ui.GOLD, anchor="center")
        ui.text(screen, kanji, ui.body_font(15), (rect.centerx, rect.y + 196), color=ui.SKY, anchor="center",
                thickness=1)
        days = profile.streak.get("days", 0) if profile else 0
        draw_flame(screen, (rect.x + 28, rect.bottom - 18), 9, FLAME if days else (110, 100, 120))
        ui.text(screen, f"{days}", ui.label_font(16), (rect.x + 42, rect.bottom - 18), anchor="midleft",
                color=ui.CREAM if days else ui.MUTED)
        trophies = len(profile.trophies) if profile else 0
        ui.text(screen, f"{trophies} trophies", ui.label_font(16), (rect.right - 14, rect.bottom - 18),
                anchor="midright", color=ui.MUTED, thickness=1)

    def _draw_new_card(self, rect, selected):
        screen = self.screen
        self._card_frame(rect, selected)
        c = (rect.centerx, rect.y + 90)
        pygame.draw.circle(screen, (60, 50, 92), c, 44)
        pygame.draw.rect(screen, ui.GOLD, (c[0] - 22, c[1] - 5, 44, 10), border_radius=4)
        pygame.draw.rect(screen, ui.GOLD, (c[0] - 5, c[1] - 22, 10, 44), border_radius=4)
        ui.text(screen, "NEW PLAYER", ui.label_font(16), (rect.centerx, rect.y + 160), anchor="center",
                color=ui.GOLD if selected else ui.CREAM)
        ui.text(screen, "あたらしく はじめる", ui.body_font(14), (rect.centerx, rect.y + 184), anchor="center",
                color=ui.MUTED, thickness=1)


# -- Name entry -----------------------------------------------------------------------

class NameEntryScreen(_Base):
    """Type a name (keyboard), or pick letters on the on-screen keys.
    run() returns the name, or None if cancelled."""

    def __init__(self, taken=()):
        super().__init__()
        self.name = ""
        self.taken = {t.lower() for t in taken}
        self.row, self.col = 0, 0
        self.keys = []
        pygame.key.start_text_input()

    @property
    def grid(self):
        return [list(r) for r in NAME_ROWS] + [["DEL", "OK"]]

    async def run(self):
        try:
            while True:
                self._tick()
                for event in game_input.events():
                    result = self._handle(event)
                    if result is not None:
                        return result or None
                self._draw()
                await asyncio.sleep(0)
        finally:
            pygame.key.stop_text_input()

    def _type(self, ch):
        if len(self.name) < save_game.MAX_NAME_LENGTH and (ch.isalnum() or ch in "-._ ") and ch.isascii():
            if not (ch == " " and (not self.name or self.name.endswith(" "))):
                self.name += ch
                audio.play("select")

    def _done(self):
        name = save_game.clean_name(self.name)
        if not name:
            audio.play("denied")
            self._say("Type a name first")
            return None
        if name.lower() in self.taken:
            audio.play("denied")
            self._say("That name is taken -- try another")
            return None
        audio.play("confirm")
        return name

    def _press(self, key):
        if key == "DEL":
            self.name = self.name[:-1]
            audio.play("back")
            return None
        if key == "OK":
            return self._done()
        self._type(key)
        return None

    def _handle(self, event):
        self._quit_check(event)
        if event.type == pygame.TEXTINPUT:
            for ch in event.text:
                self._type(ch.upper() if len(self.name) == 0 else ch)
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                return self._press("DEL")
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._done()
            if event.key == pygame.K_ESCAPE:
                return ""
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                pass   # arrows move the on-screen cursor below
            else:
                return None
        action = self.nav.handle(event)
        grid = self.grid
        if action in ("left", "right"):
            self.col = (self.col + (1 if action == "right" else -1)) % len(grid[self.row])
        elif action in ("up", "down"):
            self.row = (self.row + (1 if action == "down" else -1)) % len(grid)
            self.col = min(self.col, len(grid[self.row]) - 1)
        elif action == "confirm" and event.type == pygame.JOYBUTTONDOWN:
            return self._press(grid[self.row][self.col])
        elif action == "back" and event.type == pygame.JOYBUTTONDOWN:
            if event.button in game_input.CANCEL_BUTTONS:
                return self._press("DEL")
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            for (r, c), rect in self.keys:
                if rect.collidepoint(pos):
                    self.row, self.col = r, c
                    return self._press(grid[r][c])
        return None

    def _draw(self):
        screen = self.screen
        self.backdrop.draw(screen)
        setup_ui.draw_title(screen, "WHAT'S YOUR NAME?", "なまえを いれてね")
        box = pygame.Rect(0, 0, 380, 56)
        box.center = (SCREEN_WIDTH // 2, 140)
        ui.panel(screen, box, bg=(20, 16, 36, 240), edge=(*ui.GOLD, 220), radius=12)
        shown = self.name + ("_" if int(self.time * 2) % 2 == 0 else " ")
        ui.text(screen, shown, ui.title_font(36), box.center, anchor="center", thickness=2)
        ui.text(screen, f"{len(self.name)}/{save_game.MAX_NAME_LENGTH}", ui.label_font(16),
                (box.right - 10, box.bottom - 6), color=ui.MUTED, anchor="bottomright", thickness=1)
        self.keys = []
        grid = self.grid
        for r, row in enumerate(grid):
            wide = r == len(grid) - 1
            kw = 112 if wide else 52
            total = len(row) * kw + (len(row) - 1) * 6
            x0 = SCREEN_WIDTH // 2 - total // 2
            for c, key in enumerate(row):
                rect = pygame.Rect(x0 + c * (kw + 6), 190 + r * 50, kw, 44)
                self.keys.append(((r, c), rect))
                here = (r, c) == (self.row, self.col)
                special = key in ("DEL", "OK")
                bg = (255, 210, 110, 240) if here else ((60, 50, 92, 235) if special else (34, 28, 54, 235))
                ui.panel(screen, rect, bg=bg, edge=(*ui.GOLD, 200) if here else (110, 100, 140, 150), radius=8)
                label = "SPACE" if key == " " else key
                ui.text(screen, label, ui.label_font(16) if len(label) > 1 else ui.title_font(32), rect.center,
                        color=ui.OUTLINE if here else ui.CREAM, outline=None if here else ui.OUTLINE, anchor="center")
        self._draw_message(468)
        setup_ui.hints(screen, [("Type", "your name"), ("Enter", "done"), ("Backspace", "delete"), ("Esc", "back")],
                       [(setup_ui.DPAD, "choose"), ("pad-a", "press"), ("pad-b", "delete")])
        pygame.display.flip()


# -- PIN pad --------------------------------------------------------------------------

class PinScreen(_Base):
    """A 4-digit PIN. mode="create": set one (or skip -- run() returns
    None); mode="check": enter `account`'s PIN -- run() returns True, or
    False after too many wrong tries or Esc."""

    def __init__(self, mode, account=None):
        super().__init__()
        self.mode = mode
        self.account = account
        self.pin = ""
        self.tries = 0
        self.shake = 0.0
        self.index = 0
        self.keys = []
        self.skip_rect = pygame.Rect(0, 0, 0, 0)

    async def run(self):
        while True:
            dt = self._tick()
            self.shake = max(0.0, self.shake - dt)
            for event in game_input.events():
                result = self._handle(event)
                if result is not None:
                    return result[0]
            self._draw()
            await asyncio.sleep(0)

    def _press(self, key):
        if key == "DEL":
            self.pin = self.pin[:-1]
            audio.play("back")
            return None
        if key == "OK":
            return self._submit()
        if len(self.pin) < PIN_LENGTH:
            self.pin += key
            audio.play("select")
            if len(self.pin) == PIN_LENGTH and self.mode == "check":
                return self._submit()
        return None

    def _submit(self):
        if len(self.pin) < PIN_LENGTH:
            audio.play("denied")
            self._say(f"The PIN has {PIN_LENGTH} numbers")
            return None
        if self.mode == "create":
            audio.play("confirm")
            return (self.pin,)
        if save_game.check_pin(self.account, self.pin):
            audio.play("confirm")
            return (True,)
        self.tries += 1
        self.pin = ""
        self.shake = 0.4
        audio.play("denied")
        if self.tries >= MAX_PIN_TRIES:
            return (False,)
        self._say(f"Wrong PIN -- {MAX_PIN_TRIES - self.tries} tries left")
        return None

    def _cancel(self):
        audio.play("back")
        return (None,) if self.mode == "create" else (False,)

    def _handle(self, event):
        self._quit_check(event)
        if event.type == pygame.KEYDOWN:
            if event.unicode and event.unicode.isdigit():
                return self._press(event.unicode)
            if event.key == pygame.K_BACKSPACE:
                return self._press("DEL")
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._submit()
            if event.key == pygame.K_ESCAPE:
                return self._cancel()
            if event.key == pygame.K_s and self.mode == "create":
                return self._cancel()
        action = self.nav.handle(event)
        if action in ("left", "right"):
            self.index = (self.index + (1 if action == "right" else -1)) % len(PIN_KEYS)
        elif action in ("up", "down"):
            self.index = (self.index + (3 if action == "down" else -3)) % len(PIN_KEYS)
        elif action == "confirm" and event.type == pygame.JOYBUTTONDOWN:
            return self._press(PIN_KEYS[self.index])
        elif action == "back" and event.type == pygame.JOYBUTTONDOWN:
            return self._cancel() if not self.pin else self._press("DEL")
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            if self.skip_rect.collidepoint(pos):
                return self._cancel()
            for i, rect in self.keys:
                if rect.collidepoint(pos):
                    self.index = i
                    return self._press(PIN_KEYS[i])
        return None

    def _draw(self):
        screen = self.screen
        self.backdrop.draw(screen)
        if self.mode == "create":
            setup_ui.draw_title(screen, "SET A PIN?", "4けたの ばんごう (なくても OK)")
        else:
            setup_ui.draw_title(screen, f"HI, {self.account['name'].upper()}!", "ばんごうを いれてね")
        dx = round(8 * math.sin(self.shake * 50)) if self.shake else 0
        for k in range(PIN_LENGTH):
            c = (SCREEN_WIDTH // 2 - 66 + k * 44 + dx, 134)
            pygame.draw.circle(screen, ui.OUTLINE, c, 15)
            pygame.draw.circle(screen, ui.GOLD if k < len(self.pin) else (60, 50, 92), c, 13)
        self.keys = []
        for i, key in enumerate(PIN_KEYS):
            r, c = divmod(i, 3)
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 120 + c * 82, 170 + r * 62, 74, 54)
            self.keys.append((i, rect))
            here = i == self.index
            bg = (255, 210, 110, 240) if here else (34, 28, 54, 235)
            ui.panel(screen, rect, bg=bg, edge=(*ui.GOLD, 200) if here else (110, 100, 140, 150), radius=10)
            ui.text(screen, key, ui.title_font(32) if key.isdigit() else ui.label_font(16), rect.center,
                    color=ui.OUTLINE if here else ui.CREAM, outline=None if here else ui.OUTLINE, anchor="center")
        font = ui.label_font(16)
        words = ("S  NO PIN, THANKS" if self.mode == "create" else "Esc  BACK")
        words = game_input.prompt(words, "B  " + ("NO PIN" if self.mode == "create" else "BACK"),
                                  "NO PIN" if self.mode == "create" else "BACK")
        self.skip_rect = pygame.Rect(0, 0, font.size(words)[0] + 36, 32)
        self.skip_rect.center = (SCREEN_WIDTH // 2, 438)
        ui.panel(screen, self.skip_rect, bg=(30, 24, 46, 230), radius=16)
        ui.text(screen, words, font, self.skip_rect.center, color=ui.MUTED, anchor="center", thickness=1)
        self._draw_message(476)
        setup_ui.hints(screen, [("0-9", "type"), ("Backspace", "delete"), ("Enter", "OK")],
                       [(setup_ui.DPAD, "choose"), ("pad-a", "press"), ("pad-b", "delete / back")])
        pygame.display.flip()


# -- The whole flow ---------------------------------------------------------------------

async def choose_player():
    """Who's playing -> (new: name -> PIN) or (PIN check) -> signed in.
    Returns the account, or None for guest."""
    while True:
        audio.music(audio.MENU_TRACK)
        kind, account = await AccountScreen().run()
        if kind == "guest":
            save_game.sign_in(None)
            return None
        if kind == "new":
            name = await NameEntryScreen(taken=[a["name"] for a in save_game.list_accounts()]).run()
            if not name:
                continue
            pin = await PinScreen("create").run()
            account = save_game.create_account(name, pin)
            save_game.sign_in(account)
            return account
        if save_game.has_pin(account) and not await PinScreen("check", account).run():
            continue
        save_game.sign_in(account)
        return account

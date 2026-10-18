"""The pause / settings menu, opened mid-level with Esc, P, a gamepad's
Start button, or a tap on the HUD's gear or item-box icon.

Two pages:
  * MENU  -- Resume, Save game, Item Box, Furigana ON/OFF, Translation
             ON/OFF, Save & quit.
  * ITEMS -- the item box: every item picked up this run, with its
             Japanese word, reading and how many were found.

The HUD only shows a small crate icon with a count; this is where the
player comes to actually look inside it. Furigana / translation live here
too (instead of a tab on the quiz screen) so all player options are in one
place. The two toggles are remembered between sessions (kobito/save_game.py).

Works with keyboard, mouse, touch and gamepad. run() returns "resume" or
"quit".
"""

import asyncio

import pygame

from kobito import furigana, save_game
from kobito import input as game_input
from kobito import ui
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.item_art import get_icon
from kobito.items import get_item

RESULT_RESUME = "resume"
RESULT_QUIT = "quit"

PAGE_MENU = "menu"
PAGE_ITEMS = "items"

BACK_KEYS = (pygame.K_ESCAPE, pygame.K_p, pygame.K_BACKSPACE)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)
UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
LEFT_KEYS = (pygame.K_LEFT, pygame.K_a)
RIGHT_KEYS = (pygame.K_RIGHT, pygame.K_d)
START_BUTTONS = (game_input.BACK, game_input.START)
STICK_Y_AXIS = 1

MENU_PANEL = pygame.Rect(0, 0, 460, 444)
MENU_PANEL.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
ROW_HEIGHT = 50
TOAST_SECONDS = 2.2
ITEMS_PANEL = pygame.Rect(0, 0, 860, 470)
ITEMS_PANEL.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
GRID_COLS = 3
CARD_SIZE = (264, 78)
CARD_GAP = 10
GRID_ROWS_VISIBLE = 4

ITEM_GROUP_COLORS = {"konbini": ui.SKY, "favorite": (255, 170, 210), "rare": ui.GOLD,
                     "treasure": (150, 235, 250)}


class SettingsScreen:
    def __init__(self, screen, background, item_box, start_page=PAGE_MENU, on_save=None):
        self.screen = screen
        self.background = background.copy()
        self.dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.dim.fill((8, 6, 16, 170))
        self.item_box = item_box
        self.page = start_page
        self.came_from_icon = start_page == PAGE_ITEMS
        self.clock = pygame.time.Clock()
        self.selected = 0
        self.scroll = 0         # first visible row on the items page
        self.result = None
        # on_save() writes the game and returns True on success; without it
        # (e.g. nothing to save yet) the save rows simply aren't offered.
        self.on_save = on_save
        self.toast = None       # (message, color, seconds left)
        self._stick_y = 0       # last stick direction, so a held stick moves once
        self._row_rects = []
        self._back_rect = None

    # -- Menu model -----------------------------------------------------------

    def _rows(self):
        rows = [("resume", "Resume", None)]
        if self.on_save:
            rows.append(("save", "Save game", None))
        rows += [
            ("items", "Item Box", f"{sum(self.item_box.values())}"),
            ("furigana", "Furigana", furigana.is_enabled()),
            ("translation", "Translation", furigana.is_translation_visible()),
            ("quit", "Save & quit" if self.on_save else "Quit game", None),
        ]
        return rows

    def _activate(self, key):
        if key == "resume":
            self.result = RESULT_RESUME
        elif key == "items":
            self.page, self.scroll = PAGE_ITEMS, 0
        elif key == "save":
            if self.on_save():
                self.toast = ("Game saved!", ui.GREEN, TOAST_SECONDS)
            else:
                self.toast = ("Couldn't save the game", ui.RED, TOAST_SECONDS)
        elif key == "furigana":
            furigana.toggle()
            save_game.save_settings()
        elif key == "translation":
            furigana.toggle_translation()
            save_game.save_settings()
        elif key == "quit":
            if self.on_save:
                self.on_save()
            self.result = RESULT_QUIT

    def _back(self):
        if self.page == PAGE_ITEMS and not self.came_from_icon:
            self.page = PAGE_MENU
        else:
            self.result = RESULT_RESUME

    def _move(self, step):
        if self.page == PAGE_MENU:
            self.selected = (self.selected + step) % len(self._rows())
        else:
            self._scroll_by(step)

    def _scroll_by(self, step):
        rows = -(-len(self.item_box) // GRID_COLS)
        self.scroll = max(0, min(max(0, rows - GRID_ROWS_VISIBLE), self.scroll + step))

    # -- Loop -----------------------------------------------------------------

    async def run(self):
        game_input.get_joysticks()
        while self.result is None:
            dt = self.clock.tick(FPS) / 1000.0
            if self.toast:
                message, color, left = self.toast
                self.toast = (message, color, left - dt) if left > dt else None
            for event in game_input.events():
                self._handle(event)
            self._draw()
            await asyncio.sleep(0)
        return self.result

    def _handle(self, event):
        if event.type == pygame.QUIT:
            self.result = RESULT_QUIT
            return
        game_input.handle_hotplug(event)

        if event.type == pygame.KEYDOWN:
            if event.key in BACK_KEYS:
                self._back()
            elif event.key in UP_KEYS:
                self._move(-1)
            elif event.key in DOWN_KEYS:
                self._move(1)
            elif self.page == PAGE_MENU and event.key in CONFIRM_KEYS:
                self._activate(self._rows()[self.selected][0])
            elif self.page == PAGE_MENU and event.key in LEFT_KEYS + RIGHT_KEYS:
                key = self._rows()[self.selected][0]
                if key in ("furigana", "translation"):
                    self._activate(key)
            elif self.page == PAGE_ITEMS and event.key in CONFIRM_KEYS:
                self._back()

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button in START_BUTTONS:
                self.result = RESULT_RESUME
            elif event.button in game_input.CANCEL_BUTTONS:
                self._back()
            elif event.button in game_input.CONFIRM_BUTTONS:
                if self.page == PAGE_MENU:
                    self._activate(self._rows()[self.selected][0])
                else:
                    self._back()
        elif event.type == pygame.JOYHATMOTION and event.value[1]:
            self._move(-event.value[1])
        elif event.type == pygame.JOYAXISMOTION and event.axis == STICK_Y_AXIS:
            direction = 0 if abs(event.value) < game_input.AXIS_DEADZONE else (1 if event.value > 0 else -1)
            if direction and direction != self._stick_y:
                self._move(direction)
            self._stick_y = direction

        elif event.type == pygame.MOUSEMOTION and self.page == PAGE_MENU:
            for i, rect in enumerate(self._row_rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
        elif event.type == pygame.MOUSEWHEEL and self.page == PAGE_ITEMS:
            self._scroll_by(-event.y)

        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            if self._back_rect and self._back_rect.collidepoint(pos):
                self._back()
            elif self.page == PAGE_MENU:
                for i, rect in enumerate(self._row_rects):
                    if rect.collidepoint(pos):
                        self.selected = i
                        self._activate(self._rows()[i][0])
            elif self.page == PAGE_ITEMS:
                # Tap the top/bottom half of the grid to scroll.
                self._scroll_by(-1 if pos[1] < ITEMS_PANEL.centery else 1)

    # -- Drawing --------------------------------------------------------------

    def _draw(self):
        self.screen.blit(self.background, (0, 0))
        self.screen.blit(self.dim, (0, 0))
        if self.page == PAGE_MENU:
            self._draw_menu()
        else:
            self._draw_items()
        pygame.display.flip()

    def _header(self, rect, title, subtitle):
        ui.text(self.screen, subtitle, ui.label_font(16), (rect.x + 28, rect.y + 20), color=ui.GOLD)
        ui.text(self.screen, title, ui.title_font(32), (rect.x + 26, rect.y + 38))
        y = rect.y + 84
        pygame.draw.line(self.screen, (*ui.PANEL_EDGE[:3],), (rect.x + 24, y), (rect.right - 24, y), 2)
        return y

    def _back_button(self, rect, label="BACK"):
        font = ui.label_font(16)
        width = font.size(label)[0] + 52
        self._back_rect = pygame.Rect(rect.right - width - 20, rect.y + 24, width, 30)
        ui.panel(self.screen, self._back_rect, bg=(40, 32, 58, 230), edge=ui.PANEL_EDGE, radius=15)
        ui.text(self.screen, "Esc", ui.label_font(16), (self._back_rect.x + 12, self._back_rect.centery),
                color=ui.MUTED, anchor="midleft", thickness=1)
        ui.text(self.screen, label, font, (self._back_rect.right - 12, self._back_rect.centery),
                anchor="midright", thickness=1)

    def _draw_menu(self):
        rect = ui.panel(self.screen, MENU_PANEL, bg=(18, 14, 32, 240), radius=16)
        y = self._header(rect, "SETTINGS", "PAUSED")
        self._back_button(rect, "RESUME")

        self._row_rects = []
        y += 14
        body = ui.body_font(20)
        for i, (key, label, value) in enumerate(self._rows()):
            row = pygame.Rect(rect.x + 20, y, rect.width - 40, ROW_HEIGHT - 8)
            self._row_rects.append(row)
            active = i == self.selected
            if active:
                ui.panel(self.screen, row, bg=(255, 210, 110, 46), edge=(255, 210, 110, 200), radius=10)
                cx, cy = row.x + 16, row.centery
                pygame.draw.polygon(self.screen, ui.GOLD, [(cx - 4, cy - 7), (cx + 5, cy), (cx - 4, cy + 7)])
            color = ui.RED if key == "quit" else (ui.CREAM if active else ui.MUTED)
            ui.text(self.screen, label, body, (row.x + 36, row.centery), color=color, anchor="midleft")

            if key == "save":
                ui.text(self.screen, "keeps your exact spot", ui.label_font(16), (row.right - 14, row.centery),
                        color=ui.MUTED, anchor="midright", thickness=1)
            elif key == "items":
                ui.item_box_icon(self.screen, (row.right - 58, row.centery + 1), 26)
                if value != "0":
                    ui.count_badge(self.screen, (row.right - 40, row.centery - 10), value)
                ui.text(self.screen, "›", body, (row.right - 14, row.centery), color=ui.MUTED,
                        anchor="midright", thickness=1)
            elif isinstance(value, bool):
                self._switch(pygame.Rect(row.right - 84, row.centery - 13, 70, 26), value)
            y += ROW_HEIGHT

        if self.toast:
            message, color, _ = self.toast
            ui.text(self.screen, message, ui.label_font(16), (rect.centerx, rect.bottom - 22), color=color,
                    anchor="center")
        else:
            hint = "↑↓ choose    Enter select    Esc resume"
            ui.text(self.screen, hint, ui.label_font(16), (rect.centerx, rect.bottom - 22), color=ui.MUTED,
                    anchor="center", thickness=1)

    def _switch(self, rect, on):
        """An ON/OFF pill, like a phone settings toggle."""
        pygame.draw.rect(self.screen, ui.OUTLINE, rect.inflate(4, 4), border_radius=rect.height // 2 + 2)
        pygame.draw.rect(self.screen, ui.GREEN if on else (70, 62, 84), rect, border_radius=rect.height // 2)
        knob_x = rect.right - rect.height // 2 if on else rect.x + rect.height // 2
        pygame.draw.circle(self.screen, ui.CREAM, (knob_x, rect.centery), rect.height // 2 - 3)
        label = "ON" if on else "OFF"
        lx = rect.x + 10 if on else rect.right - 10
        ui.text(self.screen, label, ui.label_font(16), (lx, rect.centery),
                color=ui.OUTLINE if on else ui.CREAM, outline=None, anchor="midleft" if on else "midright")

    def _draw_items(self):
        rect = ui.panel(self.screen, ITEMS_PANEL, bg=(18, 14, 32, 240), radius=16)
        total = sum(self.item_box.values())
        y = self._header(rect, "ITEM BOX", f"{len(self.item_box)} KINDS  ·  {total} PICKED UP")
        self._back_button(rect)
        ui.item_box_icon(self.screen, (self._back_rect.x - 34, self._back_rect.centery), 28)

        entries = sorted(self.item_box.items(), key=lambda kv: (-kv[1], kv[0]))
        if not entries:
            ui.text(self.screen, "The box is empty.", ui.body_font(22), (rect.centerx, rect.centery - 6),
                    anchor="center")
            ui.text(self.screen, "Snacks, drinks and gift-box prizes you pick up are kept here.",
                    ui.body_font(16), (rect.centerx, rect.centery + 26), color=ui.MUTED, anchor="center",
                    thickness=1)
            return

        grid_w = GRID_COLS * CARD_SIZE[0] + (GRID_COLS - 1) * CARD_GAP
        x0 = rect.centerx - grid_w // 2
        y0 = y + 16
        first = self.scroll * GRID_COLS
        for n, (item_id, count) in enumerate(entries[first:first + GRID_COLS * GRID_ROWS_VISIBLE]):
            col, row = n % GRID_COLS, n // GRID_COLS
            card = pygame.Rect(x0 + col * (CARD_SIZE[0] + CARD_GAP), y0 + row * (CARD_SIZE[1] + CARD_GAP),
                               *CARD_SIZE)
            self._item_card(card, get_item(item_id), count)

        rows = -(-len(entries) // GRID_COLS)
        if rows > GRID_ROWS_VISIBLE:
            more = f"↑↓ scroll   {self.scroll + 1}-{min(rows, self.scroll + GRID_ROWS_VISIBLE)} of {rows} rows"
            ui.text(self.screen, more, ui.label_font(16), (rect.centerx, rect.bottom - 18), color=ui.MUTED,
                    anchor="center", thickness=1)

    def _item_card(self, card, item, count):
        accent = ITEM_GROUP_COLORS.get(item.group, ui.SKY)
        ui.panel(self.screen, card, bg=(34, 28, 52, 235), edge=(*accent, 150), radius=10)
        well = pygame.Rect(card.x + 8, card.y + 8, card.height - 16, card.height - 16)
        pygame.draw.rect(self.screen, (52, 44, 74), well, border_radius=8)
        icon = get_icon(item.id, well.width - 8)
        self.screen.blit(icon, icon.get_rect(center=well.center))

        tx = well.right + 10
        name_font = ui.body_font(17)
        name = item.name
        while name_font.size(name)[0] > card.right - tx - 44 and len(name) > 4:
            name = name[:-2] + "…"
        ui.text(self.screen, name, name_font, (tx, card.y + 9), thickness=1)
        ui.text(self.screen, item.jp, ui.body_font(16), (tx, card.y + 31), color=accent, thickness=1)
        ui.text(self.screen, item.reading, ui.label_font(16), (tx, card.y + 52), color=ui.MUTED, thickness=1)
        ui.text(self.screen, f"×{count}", ui.title_font(16) if count < 100 else ui.label_font(16),
                (card.right - 10, card.y + 10), color=ui.GOLD, anchor="topright")

"""My House (いえ): where every costume and accessory is kept, and where the
mascot changes into them.

A tatami room with the mascot standing by the shoji window, wearing what's
equipped; beside it, the wardrobe: a row of head items and a row of back
items (kobito/wardrobe.py). Unlocked pieces can be worn -- one of each --
and the info card says what the piece is in Japanese, what it does, and,
for a locked one, how to get it (the ability level it needs, or the
konbini's price). Newly unlocked pieces carry a NEW! tag until looked at.

Arrows / d-pad move, Enter / A puts it on (or takes it off), Esc / B goes
back out. Mouse, touch: tap a piece to pick it, tap again to wear it.
"""

import asyncio

import pygame

from kobito import audio, gear_art, setup_ui, town_ui, ui
from kobito import input as game_input
from kobito.constants import FPS, SCREEN_WIDTH
from kobito.wardrobe import BACK, GEAR, HEAD

ROOM = pygame.Rect(24, 92, 352, 372)
CLOSET = pygame.Rect(392, 92, 544, 372)
CELL = 64
GAP = 9
TOAST_SECONDS = 2.0

TATAMI = (196, 196, 120)
TATAMI_DARK = (150, 152, 86)
WALL = (232, 214, 178)
WOOD = (150, 98, 58)


class HouseScreen:
    def __init__(self, screen, profile, character_id):
        self.screen = screen
        self.profile = profile
        self.mascot = town_ui.Mascot(character_id)
        self.rows = [[g for g in GEAR.values() if g.slot == HEAD], [g for g in GEAR.values() if g.slot == BACK]]
        self.row, self.col = 0, 0
        self.clock = pygame.time.Clock()
        self.nav = town_ui.Nav()
        self.time = 0.0
        self.toast = None
        self.cells = []
        self.back_rect = pygame.Rect(0, 0, 0, 0)
        self._look()

    @property
    def selected(self):
        return self.rows[self.row][self.col]

    def _look(self):
        """Looking at an unlocked piece clears its NEW! tag."""
        if self.profile.has(self.selected.id):
            self.profile.mark_seen(self.selected.id)

    async def run(self):
        game_input.get_joysticks()
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            if self.toast:
                message, color, left = self.toast
                self.toast = (message, color, left - dt) if left > dt else None
            for event in game_input.events():
                if self._handle(event) == "back":
                    audio.play("back")
                    return
            self.mascot.update(dt)
            self._draw()
            await asyncio.sleep(0)

    # -- Input -----------------------------------------------------------------

    def _move(self, drow, dcol):
        row = (self.row + drow) % len(self.rows)
        col = min(self.col + dcol, len(self.rows[row]) - 1) % len(self.rows[row])
        if (row, col) != (self.row, self.col):
            self.row, self.col = row, col
            audio.play("select")
            self._look()

    def _wear(self):
        gear = self.selected
        if not self.profile.has(gear.id):
            audio.play("denied")
            how = (f"Reach Lv {gear.unlock_level} to unlock it" if gear.unlock_level
                   else f"Buy it at the konbini ({gear.price:,}円)")
            self.toast = (how, ui.RED, TOAST_SECONDS)
            return
        on = self.profile.equip(gear.id)
        audio.play("equip" if on else "back")
        self.toast = ((f"Wearing the {gear.name}!" if on else f"Took off the {gear.name}"),
                      ui.GREEN if on else ui.MUTED, TOAST_SECONDS)

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        action = self.nav.handle(event)
        if action == "back":
            return "back"
        if action == "confirm":
            self._wear()
        elif action in ("left", "right"):
            self._move(0, -1 if action == "left" else 1)
        elif action in ("up", "down"):
            self._move(-1 if action == "up" else 1, 0)
        if event.type == pygame.MOUSEMOTION:
            for (row, col), rect in self.cells:
                if rect.collidepoint(event.pos) and (row, col) != (self.row, self.col):
                    self.row, self.col = row, col
                    self._look()
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            if self.back_rect.collidepoint(pos):
                return "back"
            for (row, col), rect in self.cells:
                if rect.collidepoint(pos):
                    if (row, col) == (self.row, self.col):
                        self._wear()
                    else:
                        self.row, self.col = row, col
                        audio.play("select")
                        self._look()
        return None

    # -- Drawing ---------------------------------------------------------------

    def _draw(self):
        screen = self.screen
        screen.fill((40, 30, 36))
        self._draw_header()
        self._draw_room()
        self._draw_closet()
        if self.toast:
            message, color, _ = self.toast
            town_ui.toast(screen, message, color, (CLOSET.centerx, CLOSET.bottom - 2))
        setup_ui.hints(screen, [(setup_ui.ARROWS, "choose"), ("Enter", "wear / take off"), ("Esc", "back")],
                       [(setup_ui.DPAD, "choose"), ("pad-a", "wear / take off"), ("pad-b", "back")])
        pygame.display.flip()

    def _draw_header(self):
        screen = self.screen
        name = self.mascot.character["jp"]
        ui.text(screen, "MY HOUSE", ui.title_font(36), (28, 20), thickness=3)
        ui.text(screen, f"{name}のいえ  ·  costumes & accessories", ui.body_font(15), (30, 64), color=ui.GOLD,
                thickness=1)
        town_ui.wallet(screen, self.profile, (SCREEN_WIDTH - 24, 22))
        font = ui.label_font(16)
        self.back_rect = pygame.Rect(0, 0, font.size("BACK")[0] + 40, 30)
        self.back_rect.topright = (SCREEN_WIDTH - 334, 29)
        ui.panel(screen, self.back_rect, bg=(40, 32, 58, 230), radius=15)
        setup_ui.triangle(screen, (self.back_rect.x + 14, self.back_rect.centery), 6, -1, ui.MUTED)
        ui.text(screen, "BACK", font, (self.back_rect.right - 12, self.back_rect.centery), anchor="midright",
                thickness=1)

    def _draw_room(self):
        screen, room = self.screen, ROOM
        pygame.draw.rect(screen, ui.OUTLINE, room.inflate(6, 6), border_radius=14)
        clip = screen.get_clip()
        screen.set_clip(room)
        pygame.draw.rect(screen, WALL, room)
        # Shoji window: a paper screen in a wooden lattice, with sky behind.
        window = pygame.Rect(room.x + 40, room.y + 26, room.width - 80, 128)
        pygame.draw.rect(screen, WOOD, window.inflate(10, 10))
        pygame.draw.rect(screen, (250, 244, 226), window)
        for k in range(1, 4):
            x = window.x + k * window.width // 4
            pygame.draw.line(screen, WOOD, (x, window.y), (x, window.bottom), 3)
        for k in range(1, 3):
            y = window.y + k * window.height // 3
            pygame.draw.line(screen, WOOD, (window.x, y), (window.right, y), 3)
        # Wooden beam, then the tatami floor.
        floor_y = room.bottom - 120
        pygame.draw.rect(screen, WOOD, (room.x, floor_y - 10, room.width, 10))
        pygame.draw.rect(screen, TATAMI, (room.x, floor_y, room.width, room.bottom - floor_y))
        for k in range(0, room.width, 88):
            pygame.draw.rect(screen, TATAMI_DARK, (room.x + k, floor_y, 88, room.bottom - floor_y), 2)
        for k in range(floor_y + 6, room.bottom, 6):
            pygame.draw.line(screen, (182, 182, 108), (room.x, k), (room.right, k))
        # A zabuton cushion to stand on.
        cushion = pygame.Rect(0, 0, 170, 34)
        cushion.center = (room.centerx, room.bottom - 52)
        pygame.draw.ellipse(screen, (60, 40, 50), cushion.move(0, 5))
        pygame.draw.ellipse(screen, (180, 60, 90), cushion)
        pygame.draw.ellipse(screen, (220, 110, 140), cushion.inflate(-30, -14))
        frame = self.mascot.frame(self.profile.worn(), scale=3)
        screen.blit(frame, frame.get_rect(midbottom=(room.centerx, cushion.centery + 6)))
        screen.set_clip(clip)
        worn = self.profile.worn()
        caption = " + ".join(GEAR[g].jp for g in worn) if worn else "いつものすがた (usual look)"
        ui.text(screen, caption, ui.body_font(16), (room.centerx, room.bottom - 16), anchor="center", thickness=2)

    def _draw_closet(self):
        screen, panel = self.screen, CLOSET
        ui.panel(screen, panel, bg=(20, 16, 36, 240), radius=16)
        self.cells = []
        label = ui.label_font(16)
        y = panel.y + 14
        for r, (title, gears) in enumerate((("HEAD  ·  あたま", self.rows[0]), ("BACK  ·  せなか", self.rows[1]))):
            ui.text(screen, title, label, (panel.x + 18, y), color=ui.GOLD)
            worn = self.profile.equipped[HEAD if r == 0 else BACK]
            for c, gear in enumerate(gears):
                rect = pygame.Rect(panel.x + 18 + c * (CELL + GAP), y + 22, CELL, CELL)
                self.cells.append(((r, c), rect))
                self._draw_cell(rect, gear, selected=(r, c) == (self.row, self.col), worn=gear.id == worn)
            y += CELL + 40
        self._draw_info(pygame.Rect(panel.x + 14, y - 4, panel.width - 28, panel.bottom - y - 30))

    def _draw_cell(self, rect, gear, selected, worn):
        screen = self.screen
        have = self.profile.has(gear.id)
        if selected:
            rect = rect.move(0, -town_ui.bob(self.time, 5, 2) - 2)
        bg = (54, 46, 82) if have else (30, 26, 44)
        edge = ui.GREEN if worn else (ui.GOLD if selected else (90, 82, 120))
        pygame.draw.rect(screen, ui.OUTLINE, rect.inflate(4, 4), border_radius=12)
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, edge, rect, width=3 if (selected or worn) else 1, border_radius=10)
        icon = gear_art.gear_icon(gear.id, CELL - 10, t=self.time if selected else 0.0)
        if not have:
            icon = icon.copy()
            icon.fill((60, 56, 76, 255), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(icon, icon.get_rect(center=rect.center))
        if not have:
            self._lock(rect)
        elif worn:
            pygame.draw.circle(screen, ui.OUTLINE, (rect.right - 6, rect.y + 6), 10)
            pygame.draw.circle(screen, ui.GREEN, (rect.right - 6, rect.y + 6), 8)
            setup_ui.check(screen, (rect.right - 6, rect.y + 6), ui.OUTLINE, size=4)
        elif self.profile.is_new(gear.id):
            tag = pygame.Rect(0, 0, 40, 18)
            tag.midbottom = (rect.centerx, rect.bottom + 9)
            pygame.draw.rect(screen, ui.RED, tag, border_radius=9)
            ui.text(screen, "NEW!", ui.label_font(16), tag.center, color=ui.CREAM, outline=None, anchor="center")

    def _lock(self, rect):
        screen = self.screen
        body = pygame.Rect(0, 0, 18, 14)
        body.center = (rect.centerx, rect.centery + 4)
        pygame.draw.rect(screen, ui.OUTLINE, body.inflate(4, 4), border_radius=4)
        pygame.draw.circle(screen, ui.OUTLINE, (body.centerx, body.y), 9, width=5)
        pygame.draw.circle(screen, ui.MUTED, (body.centerx, body.y), 7, width=3)
        pygame.draw.rect(screen, ui.MUTED, body, border_radius=3)
        pygame.draw.circle(screen, ui.OUTLINE, body.center, 2)

    def _draw_info(self, rect):
        screen, gear = self.screen, self.selected
        ui.panel(screen, rect, bg=(34, 28, 54, 230), edge=None, radius=12)
        x = rect.x + 14
        ui.text(screen, gear.name, ui.body_font(20), (x, rect.y + 8))
        name_w = ui.body_font(20).size(gear.name)[0]
        ui.text(screen, f"{gear.jp}  ({gear.reading})", ui.body_font(17), (x + name_w + 14, rect.y + 10),
                color=ui.SKY, thickness=1)
        ui.text(screen, gear.blurb, ui.body_font(15), (x, rect.y + 38), color=ui.CREAM, thickness=1)
        if gear.perk_text:
            ui.text(screen, "PERK", ui.label_font(16), (x, rect.y + 64), color=ui.GOLD)
            ui.text(screen, gear.perk_text, ui.body_font(15), (x + 52, rect.y + 63), color=ui.GREEN, thickness=1)
        if self.profile.has(gear.id):
            worn = self.profile.equipped[gear.slot] == gear.id
            status = (game_input.prompt("WORN  ·  Enter to take off", "WORN  ·  A to take off", "WORN  ·  tap to take off")
                      if worn else game_input.prompt("Enter to wear it", "A to wear it", "Tap again to wear it"))
            color = ui.GREEN if worn else ui.CREAM
        elif gear.unlock_level:
            status, color = f"LOCKED  ·  unlocks at Lv {gear.unlock_level}", ui.MUTED
        else:
            status, color = f"SOLD AT THE KONBINI  ·  {gear.price:,}円", ui.GOLD
        ui.text(screen, status, ui.label_font(16), (x, rect.bottom - 22), color=color, thickness=1)

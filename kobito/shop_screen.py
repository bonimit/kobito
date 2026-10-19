"""The konbini (コンビニ): spend 円 on things that make you stronger.

Inside a little convenience store: three shelves -- study books (study
EXP, which raises your ability level), gear (the propeller cap that flies,
and two accessories), and boosts that kick in at the start of the next
stage (kobito/wardrobe.py PRODUCTS). The clerk behind the counter greets
you with いらっしゃいませ and thanks you in Japanese, and every product
shows its Japanese name and reading -- shopping is reading practice too.

Arrows / d-pad pick a product, Enter / A buys it, Esc / B leaves. Mouse,
touch: tap a product to look, tap again to buy.
"""

import asyncio

import pygame

from kobito import audio, gear_art, progress, setup_ui, town_ui, ui
from kobito.toasts import Toasts
from kobito import input as game_input
from kobito.companion_art import draw_companion
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.wardrobe import GEAR, PRODUCT_BY_ID, PRODUCTS

SHELF = pygame.Rect(296, 92, 640, 300)
COUNTER = pygame.Rect(24, 92, 256, 300)
INFO = pygame.Rect(24, 404, 912, 82)
CARD = (142, 68)
CARD_GAP = 10
ROW_STEP = 98
SHELF_ROWS = (("STUDY  ·  べんきょう", "study"), ("GEAR  ·  どうぐ", "gear"), ("NEXT STAGE  ·  つぎのステージ", "boost"))
CLERK = "ushi"
SAY_SECONDS = 2.6

GREETING = ("いらっしゃいませ！", "irasshaimase -- welcome!")
THANKS = ("ありがとうございます！", "arigatō gozaimasu -- thank you!")
SHORT = ("おかねが たりません…", "okane ga tarimasen -- not enough money")
SOLD = ("もう もっています！", "mō motte imasu -- you already have it")


class ShopScreen:
    def __init__(self, screen, profile):
        self.screen = screen
        self.profile = profile
        self.rows = [[p for p in PRODUCTS if p.kind == kind] for _, kind in SHELF_ROWS]
        self.row, self.col = 0, 0
        self.clock = pygame.time.Clock()
        self.nav = town_ui.Nav()
        self.time = 0.0
        self.said = GREETING
        self.said_left = SAY_SECONDS * 2
        self.flash = None          # (product id, seconds left) after a purchase
        self.unlocked = []         # gear a study book's level-up unlocked, for the toast
        self.cards = []
        self.back_rect = pygame.Rect(0, 0, 0, 0)
        self.toasts = Toasts(profile)
        audio.play("chime")

    @property
    def selected(self):
        return self.rows[self.row][self.col]

    async def run(self):
        game_input.get_joysticks()
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            self.said_left = max(0.0, self.said_left - dt)
            if self.flash:
                pid, left = self.flash
                self.flash = (pid, left - dt) if left > dt else None
            for event in game_input.events():
                if self._handle(event) == "back":
                    audio.play("chime")
                    return
            self.toasts.update(dt)
            self._draw()
            await asyncio.sleep(0)

    # -- Input -----------------------------------------------------------------

    def _say(self, line):
        self.said, self.said_left = line, SAY_SECONDS

    def _move(self, drow, dcol):
        row = (self.row + drow) % len(self.rows)
        col = min(self.col + dcol, len(self.rows[row]) - 1) % len(self.rows[row])
        if (row, col) != (self.row, self.col):
            self.row, self.col = row, col
            audio.play("select")

    def _status(self, product):
        """"owned" / "ready" (a boost waiting for the next stage) / "short" / "ok"."""
        if product.kind == "gear" and product.id in self.profile.owned:
            return "owned"
        if product.kind == "boost" and product.id in self.profile.boosts:
            return "ready"
        return "ok" if self.profile.yen >= product.price else "short"

    def _buy(self):
        product = self.selected
        status = self._status(product)
        if status in ("owned", "ready"):
            audio.play("denied")
            self._say(SOLD)
            return
        level = self.profile.level
        unlocked = self.profile.buy(product)
        if unlocked is None:
            audio.play("denied")
            self._say(SHORT)
            return
        audio.play("buy")
        progress.record(self.profile, "buys")
        if self.profile.level > level:
            audio.play("levelup")
        self.unlocked = unlocked
        self.flash = (product.id, 1.2)
        self._say(THANKS)

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        action = self.nav.handle(event)
        if action == "back":
            return "back"
        if action == "confirm":
            self._buy()
        elif action in ("left", "right"):
            self._move(0, -1 if action == "left" else 1)
        elif action in ("up", "down"):
            self._move(-1 if action == "up" else 1, 0)
        if event.type == pygame.MOUSEMOTION:
            for (row, col), rect in self.cards:
                if rect.collidepoint(event.pos):
                    self.row, self.col = row, col
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            if self.back_rect.collidepoint(pos):
                return "back"
            for (row, col), rect in self.cards:
                if rect.collidepoint(pos):
                    if (row, col) == (self.row, self.col):
                        self._buy()
                    else:
                        self.row, self.col = row, col
                        audio.play("select")
        return None

    # -- Drawing ---------------------------------------------------------------

    def _draw(self):
        screen = self.screen
        self._draw_store()
        self._draw_header()
        self._draw_counter()
        self._draw_shelves()
        self._draw_info()
        setup_ui.hints(screen, [(setup_ui.ARROWS, "choose"), ("Enter", "buy"), ("Esc", "leave")],
                       [(setup_ui.DPAD, "choose"), ("pad-a", "buy"), ("pad-b", "leave")])
        self.toasts.draw(screen)
        pygame.display.flip()

    def _draw_store(self):
        screen = self.screen
        screen.fill((236, 240, 236))
        # Floor tiles and the bright ceiling lights of a konbini.
        for y in range(300, SCREEN_HEIGHT, 30):
            pygame.draw.line(screen, (214, 220, 214), (0, y), (SCREEN_WIDTH, y))
        for x in range(0, SCREEN_WIDTH, 60):
            pygame.draw.line(screen, (214, 220, 214), (x, 300), (x, SCREEN_HEIGHT))
        for x in range(60, SCREEN_WIDTH, 220):
            pygame.draw.rect(screen, (255, 255, 250), (x, 0, 140, 8))
        # The store's stripes along the top wall.
        for k, color in enumerate(((240, 120, 160), (255, 214, 90), (110, 190, 230))):
            pygame.draw.rect(screen, color, (0, 8 + k * 6, SCREEN_WIDTH, 6))
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((20, 14, 30, 70))
        screen.blit(veil, (0, 0))

    def _draw_header(self):
        screen = self.screen
        ui.text(screen, "KONBINI", ui.title_font(36), (28, 30), thickness=3)
        ui.text(screen, "コンビニ  ·  こびとマート", ui.body_font(15), (178, 40), color=ui.GOLD, thickness=1)
        town_ui.wallet(screen, self.profile, (SCREEN_WIDTH - 24, 30))
        font = ui.label_font(16)
        self.back_rect = pygame.Rect(0, 0, font.size("LEAVE")[0] + 40, 30)
        self.back_rect.topright = (SCREEN_WIDTH - 334, 37)
        ui.panel(screen, self.back_rect, bg=(40, 32, 58, 230), radius=15)
        setup_ui.triangle(screen, (self.back_rect.x + 14, self.back_rect.centery), 6, -1, ui.MUTED)
        ui.text(screen, "LEAVE", font, (self.back_rect.right - 12, self.back_rect.centery), anchor="midright",
                thickness=1)

    def _draw_counter(self):
        screen, box = self.screen, COUNTER
        ui.panel(screen, box, bg=(20, 16, 36, 220), radius=16)
        # The clerk behind the counter, with a register.
        talking = self.said_left > 0
        draw_companion(screen, CLERK, box.centerx, box.y + 196 + town_ui.bob(self.time, 2.5, 2), 104,
                       expression="talking" if talking and int(self.time * 6) % 2 else "happy")
        counter = pygame.Rect(box.x + 14, box.y + 222, box.width - 28, 64)
        pygame.draw.rect(screen, ui.OUTLINE, counter.inflate(4, 4), border_radius=6)
        pygame.draw.rect(screen, (190, 140, 90), counter, border_radius=6)
        pygame.draw.rect(screen, (220, 176, 120), (counter.x, counter.y, counter.width, 10), border_radius=6)
        register = pygame.Rect(counter.right - 66, counter.y - 30, 52, 32)
        pygame.draw.rect(screen, ui.OUTLINE, register.inflate(4, 4), border_radius=4)
        pygame.draw.rect(screen, (70, 76, 96), register, border_radius=4)
        pygame.draw.rect(screen, (130, 230, 160), (register.x + 6, register.y + 5, 40, 10))
        ui.text(screen, "レジ", ui.body_font(14), (counter.x + 34, counter.centery + 4), color=ui.OUTLINE,
                outline=None, anchor="center")
        # Speech bubble.
        jp, en = self.said
        bubble = pygame.Rect(box.x + 12, box.y + 14, box.width - 24, 72)
        pygame.draw.rect(screen, ui.OUTLINE, bubble.inflate(4, 4), border_radius=14)
        pygame.draw.rect(screen, (252, 246, 232), bubble, border_radius=12)
        tail = [(box.centerx - 8, bubble.bottom - 1), (box.centerx + 8, bubble.bottom - 1),
                (box.centerx, bubble.bottom + 12)]
        pygame.draw.polygon(screen, (252, 246, 232), tail)
        pygame.draw.lines(screen, ui.OUTLINE, False, [tail[0], tail[2], tail[1]], 2)
        screen.blit(ui.body_font(19).render(jp, True, (40, 30, 46)), (bubble.x + 12, bubble.y + 10))
        for i, line in enumerate(setup_ui.wrap(en, ui.body_font(13), bubble.width - 24)[:2]):
            screen.blit(ui.body_font(13).render(line, True, (110, 96, 120)), (bubble.x + 12, bubble.y + 38 + i * 15))

    def _draw_shelves(self):
        screen, shelf = self.screen, SHELF
        ui.panel(screen, shelf, bg=(20, 16, 36, 220), radius=16)
        self.cards = []
        label = ui.label_font(16)
        for r, ((title, _), products) in enumerate(zip(SHELF_ROWS, self.rows)):
            y = shelf.y + 10 + r * ROW_STEP
            ui.text(screen, title, label, (shelf.x + 16, y), color=ui.GOLD)
            plank = pygame.Rect(shelf.x + 12, y + 20 + CARD[1] + 1, shelf.width - 24, 5)
            pygame.draw.rect(screen, (150, 104, 66), plank, border_radius=2)
            for c, product in enumerate(products):
                rect = pygame.Rect(shelf.x + 16 + c * (CARD[0] + CARD_GAP), y + 20, *CARD)
                self.cards.append(((r, c), rect))
                self._draw_card(rect, product, (r, c) == (self.row, self.col))

    def _draw_card(self, rect, product, selected):
        screen = self.screen
        status = self._status(product)
        if selected:
            rect = rect.move(0, -town_ui.bob(self.time, 5, 2) - 2)
        flash = self.flash and self.flash[0] == product.id
        bg = (70, 62, 100) if flash else ((52, 44, 78) if selected else (34, 28, 52))
        pygame.draw.rect(screen, ui.OUTLINE, rect.inflate(4, 4), border_radius=12)
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        if selected:
            pygame.draw.rect(screen, ui.GOLD, rect, width=3, border_radius=10)
        icon = gear_art.product_icon(product.id, 50)
        screen.blit(icon, icon.get_rect(center=(rect.x + 34, rect.centery)))
        ui.text(screen, product.jp, ui.body_font(14 if len(product.jp) > 5 else 16),
                (rect.x + 66, rect.y + 10), color=ui.CREAM, thickness=1)
        price = {"owned": "OWNED", "ready": "READY"}.get(status, f"{product.price:,}円")
        color = {"owned": ui.GREEN, "ready": ui.GREEN, "short": (200, 120, 130)}.get(status, ui.GOLD)
        ui.text(screen, price, ui.label_font(16), (rect.right - 10, rect.bottom - 10), color=color,
                anchor="bottomright", thickness=1)
        if status in ("owned", "ready"):
            setup_ui.check(screen, (rect.x + 14, rect.bottom - 16), ui.GREEN, size=5)

    def _draw_info(self):
        screen, box, product = self.screen, INFO, self.selected
        ui.panel(screen, box, bg=(20, 16, 36, 235), radius=14)
        x = box.x + 18
        name_font = ui.body_font(20)
        ui.text(screen, product.name, name_font, (x, box.y + 10))
        ui.text(screen, f"{product.jp}  ({product.reading})", ui.body_font(17),
                (x + name_font.size(product.name)[0] + 14, box.y + 12), color=ui.SKY, thickness=1)
        detail = product.text
        if product.kind == "gear" and product.id in GEAR and GEAR[product.id].perk_text:
            detail = GEAR[product.id].perk_text + "  Wear it at your house."
        ui.text(screen, detail, ui.body_font(15), (x, box.y + 44), color=ui.CREAM, thickness=1)
        status = self._status(product)
        words, color = {
            "owned": ("OWNED -- wear it at your house", ui.GREEN),
            "ready": ("READY -- it'll kick in at the start of the next stage", ui.GREEN),
            "short": (f"NEED {product.price - self.profile.yen:,}円 MORE", (230, 130, 140)),
            "ok": (game_input.prompt(f"ENTER: BUY FOR {product.price:,}円", f"A: BUY FOR {product.price:,}円",
                                     f"TAP AGAIN: BUY FOR {product.price:,}円"), ui.GOLD),
        }[status]
        ui.text(screen, words, ui.label_font(16), (box.right - 18, box.y + 14), color=color, anchor="topright",
                thickness=1)
        if self.unlocked and self.flash:
            gear = self.unlocked[-1]
            town_ui.toast(screen, f"LEVEL UP! New: {gear.name} ({gear.jp})", ui.GOLD,
                          (SHELF.centerx, SHELF.bottom - 4))
        elif self.flash:
            bought = PRODUCT_BY_ID[self.flash[0]]
            town_ui.toast(screen, f"Bought: {bought.name}!", ui.GREEN, (SHELF.centerx, SHELF.bottom - 4))

"""The end-of-stage screens: Stage Review, the tile questions of the Stage
Test (reading / writing), and the test results.

  * ReviewScreen     -- every question from the stage with the player's
                        answer, the right one and the explanation, then
                        "What you learned" (the stage's words). Scrolls.
                        run() -> "test" or "skip".
  * TileScreen       -- a reading (読み) or writing (書き) question answered by
                        placing tiles into slots -- keyboard, gamepad, mouse
                        or touch, no Japanese keyboard needed.
                        run() -> True / False / None (skipped).
  * ResultsScreen    -- score, stars and bonus XP. run() -> None.
  * LuckyDrawScreen  -- one big box with the prizes flashing through it;
                        jump into it to stop the shuffle. run() -> the prize.

Data comes from kobito/stage_test.py.
"""

import asyncio
import math

import pygame

from kobito import input as game_input
from kobito import ui
from kobito.constants import FPS, IS_WEB, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import get_font

GREEN = (110, 220, 130)
RED = (240, 100, 100)
MUTED = (175, 170, 190)
CARD_BG = (22, 20, 36, 240)
READING_ACCENT = (70, 200, 210)
WRITING_ACCENT = (255, 150, 70)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)
SKIP_KEYS = (pygame.K_s,)
GRACE_SECONDS = 0.3


def _dim(screen, background, alpha=190):
    screen.blit(background, (0, 0))
    shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    shade.fill((8, 6, 16, alpha))
    screen.blit(shade, (0, 0))


def wrap(text, font, width):
    """Wraps on spaces, and inside long runs with no spaces (Japanese)."""
    lines, current = [], ""
    for word in text.split(" "):
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = ""
        for ch in word:
            if font.size(current + ch)[0] > width and current:
                lines.append(current)
                current = ch
            else:
                current += ch
    if current:
        lines.append(current)
    return lines


def draw_mark(surface, center, kind, size=10):
    """A green check, a red cross, or a grey dash (skipped)."""
    x, y = center
    if kind == "right":
        pts = [(x - size, y), (x - size // 3, y + size * 2 // 3), (x + size, y - size * 2 // 3)]
        pygame.draw.lines(surface, ui.OUTLINE, False, pts, 6)
        pygame.draw.lines(surface, GREEN, False, pts, 4)
    elif kind == "wrong":
        for a, b in (((-1, -1), (1, 1)), ((1, -1), (-1, 1))):
            p1, p2 = (x + a[0] * size * 0.8, y + a[1] * size * 0.8), (x + b[0] * size * 0.8, y + b[1] * size * 0.8)
            pygame.draw.line(surface, ui.OUTLINE, p1, p2, 6)
            pygame.draw.line(surface, RED, p1, p2, 4)
    else:
        pygame.draw.line(surface, ui.OUTLINE, (x - size, y), (x + size, y), 6)
        pygame.draw.line(surface, MUTED, (x - size, y), (x + size, y), 4)


class _Screen:
    def __init__(self, screen, background):
        self.screen = screen
        self.background = background
        self.clock = pygame.time.Clock()
        self.age = 0.0
        self._stick = 0
        game_input.get_joysticks()

    def _stick_step(self, event, axis):
        if event.type != pygame.JOYAXISMOTION or event.axis != axis:
            return 0
        direction = 0 if abs(event.value) < game_input.AXIS_DEADZONE else (1 if event.value > 0 else -1)
        step = direction if direction and direction != self._stick else 0
        self._stick = direction
        return step


# -- Review --------------------------------------------------------------------

class ReviewScreen(_Screen):
    PANEL = pygame.Rect(36, 20, SCREEN_WIDTH - 72, SCREEN_HEIGHT - 40)

    def __init__(self, screen, background, level_number, entries, words, test_size):
        super().__init__(screen, background)
        self.level_number = level_number
        self.entries = entries
        self.words = words
        self.test_size = test_size
        self.view = pygame.Rect(self.PANEL.x + 20, self.PANEL.y + 92, self.PANEL.width - 40, self.PANEL.height - 146)
        self.content = self._build_content()
        self.scroll = 0

    @property
    def max_scroll(self):
        return max(0, self.content.get_height() - self.view.height)

    def _build_content(self):
        width = self.view.width
        body, small = get_font(16), get_font(14)
        label = ui.label_font(16)
        blocks = []   # (height, draw function)

        def add(height, fn):
            blocks.append((height, fn))

        if not self.entries:
            add(40, lambda s, y: ui.text(s, "No questions this stage -- the test will use fresh ones.", body,
                                          (0, y + 8), color=MUTED, thickness=1))
        for n, e in enumerate(self.entries, 1):
            q, kind = e["question"], e["result"]
            prompt = wrap(f"{n}. {q['prompt']}", body, width - 60)
            right = q["choices"][q["answer"]]
            lines = [(body, line, ui.CREAM) for line in prompt]
            if kind == "wrong" and e.get("chosen") is not None:
                lines.append((small, f"Your answer: {q['choices'][e['chosen']]}", RED))
            elif kind == "skipped":
                lines.append((small, "Skipped", MUTED))
            lines.append((small, f"Answer: {right}", GREEN))
            for line in wrap(q.get("explanation", ""), small, width - 60):
                lines.append((small, line, MUTED))
            height = sum(f.get_height() + 3 for f, _, _ in lines) + 18

            def draw_card(s, y, lines=lines, kind=kind, height=height, q=q):
                ui.panel(s, (0, y, width, height - 8), bg=(40, 34, 60, 200), edge=None, radius=8)
                draw_mark(s, (22, y + 18), kind)
                tag = f"{q['jlpt']} · {q['category'].upper().replace('_', ' ')}"
                ui.text(s, tag, label, (width - 12, y + 8), color=ui.GOLD, anchor="topright", thickness=1)
                yy = y + 6
                for font, text, color in lines:
                    s.blit(font.render(text, True, color), (44, yy))
                    yy += font.get_height() + 3
            add(height, draw_card)

        add(62, lambda s, y: ui.text(s, "WHAT YOU LEARNED", ui.title_font(32), (0, y + 10), color=ui.GOLD))
        if not self.words:
            add(30, lambda s, y: ui.text(s, "Pick up snacks and answer questions to collect words!", body,
                                          (0, y + 4), color=MUTED, thickness=1))
        col_w = width // 2
        for i in range(0, len(self.words), 2):
            pair = self.words[i:i + 2]

            def draw_row(s, y, pair=pair):
                for j, w in enumerate(pair):
                    x = j * col_w
                    jp = get_font(24).render(w["jp"], True, ui.CREAM)
                    s.blit(jp, (x, y + 2))
                    reading = w["kana"] if w["kana"] and w["kana"] != w["jp"] else ""
                    detail = f"{reading}  {w['romaji']}".strip()
                    s.blit(small.render(detail, True, ui.SKY), (x + jp.get_width() + 10, y + 2))
                    meaning = w["meaning"] or ""
                    s.blit(small.render(meaning[:42], True, MUTED), (x + jp.get_width() + 10, y + 20))
            add(44, draw_row)

        total = sum(h for h, _ in blocks) + 8
        content = pygame.Surface((width, total), pygame.SRCALPHA)
        y = 0
        for h, fn in blocks:
            fn(content, y)
            y += h
        return content

    async def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.age += dt
            for event in game_input.events():
                result = self._handle(event)
                if result:
                    return result
            self._draw()
            await asyncio.sleep(0)

    def _scroll_by(self, amount):
        self.scroll = max(0, min(self.max_scroll, self.scroll + amount))

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        ready = self.age >= GRACE_SECONDS
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self._scroll_by(40)
            elif event.key == pygame.K_UP:
                self._scroll_by(-40)
            elif event.key == pygame.K_PAGEDOWN:
                self._scroll_by(self.view.height - 40)
            elif event.key == pygame.K_PAGEUP:
                self._scroll_by(-(self.view.height - 40))
            elif event.key in CONFIRM_KEYS and ready:
                return "test"
            elif event.key in SKIP_KEYS + (pygame.K_ESCAPE,):
                return "skip"
        elif event.type == pygame.MOUSEWHEEL:
            self._scroll_by(-event.y * 40)
        elif event.type == pygame.JOYHATMOTION and event.value[1]:
            self._scroll_by(-event.value[1] * 40)
        elif event.type == pygame.JOYBUTTONDOWN and ready:
            if event.button in game_input.CONFIRM_BUTTONS:
                return "test"
            if event.button in game_input.CANCEL_BUTTONS:
                return "skip"
        step = self._stick_step(event, 1)
        if step:
            self._scroll_by(step * 40)
        tap = game_input.touch_tap_pos(event)
        if tap is not None and ready:
            if self._start_rect.collidepoint(tap):
                return "test"
            if self._skip_rect.collidepoint(tap):
                return "skip"
            self._scroll_by(60 if tap[1] > self.view.centery else -60)
        return None

    def _draw(self):
        _dim(self.screen, self.background)
        panel = ui.panel(self.screen, self.PANEL, bg=(18, 14, 32, 240), radius=16)
        right = sum(1 for e in self.entries if e["result"] == "right")
        wrong = sum(1 for e in self.entries if e["result"] == "wrong")
        skipped = sum(1 for e in self.entries if e["result"] == "skipped")
        ui.text(self.screen, f"LEVEL {self.level_number}  ·  STAGE REVIEW", ui.label_font(16),
                (panel.x + 22, panel.y + 16), color=ui.GOLD)
        ui.text(self.screen, "What you studied", ui.title_font(32), (panel.x + 20, panel.y + 34))
        summary = f"{right} right   {wrong} wrong   {skipped} skipped   ·   {len(self.words)} words"
        ui.text(self.screen, summary, ui.label_font(16), (panel.right - 22, panel.y + 48), color=ui.SKY,
                anchor="topright", thickness=1)

        self.screen.set_clip(self.view)
        self.screen.blit(self.content, (self.view.x, self.view.y - self.scroll))
        self.screen.set_clip(None)
        if self.max_scroll:   # a slim scrollbar
            track = pygame.Rect(self.view.right + 6, self.view.y, 4, self.view.height)
            pygame.draw.rect(self.screen, (60, 54, 80), track, border_radius=2)
            h = max(30, track.height * self.view.height // self.content.get_height())
            y = track.y + (track.height - h) * self.scroll // self.max_scroll
            pygame.draw.rect(self.screen, ui.GOLD, (track.x, y, 4, h), border_radius=2)

        label = ui.label_font(16)
        self._start_rect = pygame.Rect(0, 0, 300, 34)
        self._start_rect.bottomright = (panel.right - 20, panel.bottom - 14)
        ui.panel(self.screen, self._start_rect, bg=(255, 210, 110, 240), edge=(20, 14, 26, 255), radius=12)
        ui.text(self.screen, f"START STAGE TEST ({self.test_size})", label, self._start_rect.center,
                color=ui.OUTLINE, outline=None, anchor="center")
        self._skip_rect = pygame.Rect(0, 0, 120, 34)
        self._skip_rect.bottomright = (self._start_rect.x - 12, self._start_rect.bottom)
        ui.panel(self.screen, self._skip_rect, bg=(40, 34, 60, 230), radius=12)
        ui.text(self.screen, "SKIP TEST", label, self._skip_rect.center, color=MUTED, anchor="center", thickness=1)
        hint = "Tap to scroll" if IS_WEB else "↑↓ scroll    Enter start test    S skip"
        ui.text(self.screen, hint, label, (panel.x + 22, panel.bottom - 30), color=MUTED, anchor="midleft",
                thickness=1)
        pygame.display.flip()


# -- Reading / writing tile question --------------------------------------------

class TileScreen(_Screen):
    CARD = pygame.Rect(110, 60, SCREEN_WIDTH - 220, 400)
    TILE = 52
    GAP = 10

    def __init__(self, screen, background, item, index, total):
        super().__init__(screen, background)
        self.item = item
        self.kind = item["kind"]
        self.word = item["word"]
        self.answer = item["answer"]
        self.tiles = item["tiles"]
        self.title = f"TEST {index}/{total}"
        self.accent = READING_ACCENT if self.kind == "reading" else WRITING_ACCENT
        self.cursor = 0
        self.placed = []          # tile indexes, in order
        self.result = None        # None while answering, then True / False
        self.result_time = 0.0
        self._tile_rects = []

    @property
    def guess(self):
        return [self.tiles[i] for i in self.placed]

    def _move(self, step):
        free = [i for i in range(len(self.tiles)) if i not in self.placed]
        if not free:
            return
        i = self.cursor
        for _ in range(len(self.tiles)):
            i = (i + step) % len(self.tiles)
            if i not in self.placed:
                self.cursor = i
                return

    def _place(self, i=None):
        i = self.cursor if i is None else i
        if self.result is not None or i in self.placed or len(self.placed) >= len(self.answer):
            return
        self.placed.append(i)
        if len(self.placed) == len(self.answer):
            self.result = self.guess == self.answer
            self.result_time = 0.0
        else:
            self._move(1)

    def _undo(self):
        if self.result is None and self.placed:
            self.cursor = self.placed.pop()

    async def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.age += dt
            if self.result is not None:
                self.result_time += dt
                if self.result and self.result_time > 1.1:
                    return True
            for event in game_input.events():
                outcome = self._handle(event)
                if outcome is not None:
                    return outcome
            self._draw()
            await asyncio.sleep(0)

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        ready = self.age >= GRACE_SECONDS
        if self.result is False:   # wrong: wait for a press to move on
            confirm = (event.type == pygame.KEYDOWN and event.key in CONFIRM_KEYS) or \
                      (event.type == pygame.JOYBUTTONDOWN and event.button in game_input.FACE_BUTTONS) or \
                      game_input.touch_tap_pos(event) is not None
            return False if confirm and self.result_time > 0.4 else None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
                self._move(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d):
                self._move(1)
            elif event.key in CONFIRM_KEYS and ready:
                self._place()
            elif event.key == pygame.K_BACKSPACE:
                self._undo()
            elif event.key in SKIP_KEYS and self.result is None:
                return "skip"
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button in game_input.CONFIRM_BUTTONS and ready:
                self._place()
            elif event.button in game_input.CANCEL_BUTTONS:
                self._undo()
            elif event.button in game_input.SKIP_BUTTONS and self.result is None:
                return "skip"
        elif event.type == pygame.JOYHATMOTION and (event.value[0] or event.value[1]):
            self._move(event.value[0] or -event.value[1])
        step = self._stick_step(event, 0)
        if step:
            self._move(step)
        tap = game_input.touch_tap_pos(event)
        if tap is not None and ready:
            for i, rect in enumerate(self._tile_rects):
                if rect.collidepoint(tap):
                    self.cursor = i
                    self._place(i)
                    return None
            if self._slots_rect.collidepoint(tap):
                self._undo()
            elif self._skip_rect.collidepoint(tap) and self.result is None:
                return "skip"
        return None

    def _draw(self):
        _dim(self.screen, self.background, 150)
        card = self.CARD
        accent = self.accent
        shadow = pygame.Surface(card.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=12)
        self.screen.blit(shadow, (card.x + 5, card.y + 6))
        ui.panel(self.screen, card, bg=CARD_BG, edge=(*accent, 255), radius=12)
        band = pygame.Rect(card.x + 2, card.y + 2, card.width - 4, 30)
        pygame.draw.rect(self.screen, [round(c * 0.38) for c in accent], band, border_top_left_radius=11,
                         border_top_right_radius=11)
        kind = "READING  読み" if self.kind == "reading" else "WRITING  書き"
        ui.text(self.screen, f"{self.title}  ·  {kind}", get_font(15), (card.x + 16, band.centery), color=accent,
                anchor="midleft", outline=None)

        w = self.word
        cx = card.centerx
        if self.kind == "reading":
            ui.text(self.screen, "How do you read this word?", ui.body_font(20), (cx, card.y + 58), anchor="center")
            ui.text(self.screen, w["jp"], get_font(54), (cx, card.y + 116), anchor="center", thickness=3)
            ui.text(self.screen, f"({w['meaning']})" if w["meaning"] else "", get_font(16), (cx, card.y + 158),
                    color=MUTED, anchor="center", thickness=1)
        else:
            ui.text(self.screen, "Write this word in Japanese:", ui.body_font(20), (cx, card.y + 58), anchor="center")
            ui.text(self.screen, w["meaning"], ui.body_font(32), (cx, card.y + 110), anchor="center", thickness=3)
            ui.text(self.screen, f"({w['romaji']})", get_font(16), (cx, card.y + 150), color=MUTED, anchor="center",
                    thickness=1)

        # Answer slots.
        slot, gap = 46, 8
        n = len(self.answer)
        x0 = cx - (n * slot + (n - 1) * gap) // 2
        y = card.y + 184
        self._slots_rect = pygame.Rect(x0, y, n * slot + (n - 1) * gap, slot)
        guess = self.guess
        for i in range(n):
            r = pygame.Rect(x0 + i * (slot + gap), y, slot, slot)
            color = (60, 54, 84)
            if self.result is not None:
                color = (40, 110, 60) if self.result else (120, 40, 50)
            pygame.draw.rect(self.screen, ui.OUTLINE, r.inflate(4, 4), border_radius=8)
            pygame.draw.rect(self.screen, color, r, border_radius=7)
            if i < len(guess):
                ui.text(self.screen, guess[i], get_font(30), r.center, anchor="center")
        if self.result is False:
            ui.text(self.screen, "Answer:  " + "".join(self.answer), get_font(22), (cx, y + slot + 22), color=GREEN,
                    anchor="center")
        elif self.result:
            ui.text(self.screen, "Correct!", ui.body_font(22), (cx, y + slot + 22), color=GREEN, anchor="center")

        # Tiles.
        t, g = self.TILE, self.GAP
        per_row = min(len(self.tiles), 8)
        rows = (len(self.tiles) + per_row - 1) // per_row
        tx0 = cx - (per_row * t + (per_row - 1) * g) // 2
        ty0 = card.y + 272 - (rows - 1) * (t + g) // 2
        self._tile_rects = []
        for i, ch in enumerate(self.tiles):
            r = pygame.Rect(tx0 + (i % per_row) * (t + g), ty0 + (i // per_row) * (t + g), t, t)
            self._tile_rects.append(r)
            used = i in self.placed
            pygame.draw.rect(self.screen, ui.OUTLINE, r.inflate(4, 4), border_radius=10)
            pygame.draw.rect(self.screen, (44, 40, 60) if used else (248, 240, 220), r, border_radius=9)
            if not used:
                pygame.draw.rect(self.screen, (210, 196, 170), (r.x, r.bottom - 6, r.width, 6),
                                 border_bottom_left_radius=9, border_bottom_right_radius=9)
                ui.text(self.screen, ch, get_font(30), (r.centerx, r.centery - 2), color=(40, 30, 40), outline=None,
                        anchor="center")
            if i == self.cursor and self.result is None:
                pygame.draw.rect(self.screen, accent, r.inflate(10, 10), width=3, border_radius=12)

        hint = ("Tap tiles in order · tap the slots to undo" if IS_WEB
                else "Arrows choose   Enter place   Backspace undo   S skip")
        if self.result is False:
            hint = "Enter to continue"
        ui.text(self.screen, hint, ui.label_font(16), (card.x + 18, card.bottom - 22), color=MUTED, anchor="midleft",
                thickness=1)
        self._skip_rect = pygame.Rect(0, 0, 96, 26)
        self._skip_rect.bottomright = (card.right - 14, card.bottom - 10)
        if self.result is None:
            ui.panel(self.screen, self._skip_rect, bg=(40, 34, 60, 230), radius=10)
            ui.text(self.screen, "SKIP (S)", ui.label_font(16), self._skip_rect.center, color=MUTED, anchor="center",
                    thickness=1)
        pygame.display.flip()


# -- Results --------------------------------------------------------------------

def _star(surface, center, r, filled):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((center[0] + math.cos(a) * rr, center[1] + math.sin(a) * rr))
    pygame.draw.polygon(surface, ui.OUTLINE, [(x, y + 2) for x, y in pts])
    pygame.draw.polygon(surface, ui.GOLD if filled else (70, 64, 90), pts)


def stars_for(correct, total):
    ratio = correct / total if total else 0
    return 3 if ratio >= 0.9 else 2 if ratio >= 0.7 else 1 if ratio >= 0.4 else 0


class ResultsScreen(_Screen):
    def __init__(self, screen, background, results, bonus_xp):
        super().__init__(screen, background)
        self.results = results     # [(kind, True/False/None)]
        self.bonus_xp = bonus_xp

    async def run(self):
        while True:
            self.clock.tick(FPS)
            self.age += 1 / FPS
            for event in game_input.events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                game_input.handle_hotplug(event)
                go = (event.type == pygame.KEYDOWN and event.key in CONFIRM_KEYS + (pygame.K_ESCAPE,)) or \
                     (event.type == pygame.JOYBUTTONDOWN and event.button in game_input.FACE_BUTTONS) or \
                     game_input.touch_tap_pos(event) is not None
                if go and self.age > 0.5:
                    return None
            self._draw()
            await asyncio.sleep(0)

    def _draw(self):
        _dim(self.screen, self.background)
        card = pygame.Rect(0, 0, 560, 340)
        card.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        ui.panel(self.screen, card, bg=(18, 14, 32, 245), radius=16)
        total = len(self.results)
        correct = sum(1 for _, r in self.results if r)
        cx = card.centerx
        ui.text(self.screen, "STAGE TEST", ui.label_font(16), (cx, card.y + 28), color=ui.GOLD, anchor="center")
        ui.text(self.screen, f"{correct} / {total}", ui.title_font(48), (cx, card.y + 76), anchor="center",
                thickness=3)
        n = stars_for(correct, total)
        for i in range(3):
            _star(self.screen, (cx - 60 + i * 60, card.y + 136), 22, i < n)
        rows = []
        for kind, name in (("mc", "Multiple choice"), ("reading", "Reading 読み"), ("writing", "Writing 書き")):
            got = [r for k, r in self.results if k == kind]
            if got:
                rows.append(f"{name}:  {sum(1 for r in got if r)} / {len(got)}")
        y = card.y + 178
        for row in rows:
            ui.text(self.screen, row, get_font(17), (cx, y), anchor="center", thickness=1)
            y += 26
        ui.text(self.screen, f"+{self.bonus_xp} XP", ui.title_font(32), (cx, card.bottom - 62), color=GREEN,
                anchor="center")
        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            ui.text(self.screen, "PRESS ENTER TO CONTINUE", ui.label_font(16), (cx, card.bottom - 24),
                    anchor="center")
        pygame.display.flip()


# -- Lucky draw -----------------------------------------------------------------

def roll_prize(rng, favorites):
    """One lucky-draw box's prize. Items go to the item box."""
    from kobito.items import BIG_DRINKS, RARE_IDS, SMALL_SNACKS, TREASURE_IDS, get_item
    table = [("coins", 24), ("xp", 18), ("snack", 18), ("favorite", 12), ("rare", 12), ("treasure", 8),
             ("sunflower", 8)]
    roll = rng.uniform(0, sum(w for _, w in table))
    kind = table[-1][0]
    for name, weight in table:
        roll -= weight
        if roll <= 0:
            kind = name
            break
    if kind == "coins":
        return {"kind": "coins", "amount": rng.choice((50, 80, 100)), "item": None}
    if kind == "xp":
        return {"kind": "xp", "amount": rng.choice((30, 50)), "item": None}
    pool = {"snack": SMALL_SNACKS + BIG_DRINKS, "favorite": list(favorites) or SMALL_SNACKS, "rare": RARE_IDS,
            "treasure": TREASURE_IDS, "sunflower": ["sunflower"]}[kind]
    return {"kind": "item", "amount": 0, "item": get_item(rng.choice(pool))}


def prize_label(prize):
    if prize["kind"] == "coins":
        return f"+{prize['amount']} points"
    if prize["kind"] == "xp":
        return f"+{prize['amount']} XP"
    item = prize["item"]
    return f"{item.name}  {item.jp}"


def build_reel(rng, favorites, prize, size=12):
    """The items flashing through the lucky box: a varied mix of possible
    prizes (each shown once) plus the real one."""
    reel, seen = [prize], {prize_label(prize)}
    for _ in range(200):
        if len(reel) >= size:
            break
        other = roll_prize(rng, favorites)
        if prize_label(other) not in seen:
            seen.add(prize_label(other))
            reel.append(other)
    rng.shuffle(reel)
    return reel


class LuckyDrawScreen(_Screen):
    """One big lucky box over the player's mascot, with the possible prizes
    flashing through its window. Jump into it from below and the shuffle
    slows down -- tick, tick... tick -- and stops on the prize.
    run() -> the prize won."""

    GROUND_Y = 450
    BOX = pygame.Rect(0, 0, 196, 178)
    BOX_TOP = 134
    SPEED, JUMP, GRAVITY = 260.0, 620.0, 1800.0
    ICON = 78                   # 3x the 26 px item art: big and crisp
    SPIN_STEP = 0.11            # seconds per item while spinning
    SLOW_STEPS, SLOW_GROWTH = 11, 1.17   # after the hit: 11 more items, each shown a bit longer

    def __init__(self, screen, background, character, prize, rng):
        super().__init__(screen, background)
        from kobito.assets import load_character_animations
        self.animations = load_character_animations(character["id"], character["color"])
        self.prize = prize
        self.reel = build_reel(rng, character["favorites"], prize)
        self.index = 0
        self.step_time = 0.0
        self.step_length = self.SPIN_STEP
        self.slow_left = None       # items still to show after the hit; None = still spinning
        self.pop = 0.0              # the box's bump, and each new item's little pop
        self.item_pop = 0.0
        self.reveal_time = 0.0
        self.box = self.BOX.copy()
        self.box.midtop = (SCREEN_WIDTH // 2, self.BOX_TOP)
        self.player = pygame.Rect(0, 0, 28, 48)
        self.player.midbottom = (SCREEN_WIDTH // 2, self.GROUND_Y)
        self.vx = self.vy = 0.0
        self.on_ground = True
        self.facing_right = True
        self._jump_was_down = False

    @property
    def hit(self):
        return self.slow_left is not None

    @property
    def finished(self):
        return self.slow_left == 0

    @property
    def current(self):
        return self.reel[self.index]

    async def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.age += dt
            for event in game_input.events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                game_input.handle_hotplug(event)
                if self.finished and self.reveal_time > 0.9:
                    go = (event.type == pygame.KEYDOWN and event.key in CONFIRM_KEYS + (pygame.K_ESCAPE,)) or \
                         (event.type == pygame.JOYBUTTONDOWN and event.button in game_input.FACE_BUTTONS) or \
                         game_input.touch_tap_pos(event) is not None
                    if go:
                        return self.prize
            self._physics(dt)
            self._spin(dt)
            self._draw()
            await asyncio.sleep(0)

    def _open(self):
        """The player bumped the box: from here the shuffle slows down and
        lands exactly on the prize."""
        self.pop = 0.25
        if self.hit:
            return
        self.slow_left = self.SLOW_STEPS
        # Put the prize where the reel will stop (a slot not on show now).
        self.reel[(self.index + self.SLOW_STEPS) % len(self.reel)] = self.prize

    def _spin(self, dt):
        self.pop = max(0.0, self.pop - dt)
        self.item_pop = max(0.0, self.item_pop - dt)
        if self.finished:
            self.reveal_time += dt
            return
        self.step_time += dt
        while self.step_time >= self.step_length and not self.finished:
            self.step_time -= self.step_length
            self.index = (self.index + 1) % len(self.reel)
            self.item_pop = 0.08
            if self.hit:
                self.slow_left -= 1
                self.step_length *= self.SLOW_GROWTH
                if self.finished:
                    self.item_pop = 0.3

    def _physics(self, dt):
        keys = pygame.key.get_pressed()
        direction = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction = 1
        for axis in (game_input.move_axis(), game_input.touch_move_axis()):
            if axis:
                direction = -1 if axis < 0 else 1
        jump = (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_RETURN]
                or game_input.jump_held() or game_input.touch_jump_held())
        if self.hit:
            direction, jump = 0, False
        self.vx = direction * self.SPEED
        if direction:
            self.facing_right = direction > 0
        if jump and not self._jump_was_down and self.on_ground and self.age > GRACE_SECONDS:
            self.vy = -self.JUMP
            self.on_ground = False
        self._jump_was_down = jump
        self.player.x = max(60, min(SCREEN_WIDTH - 88, self.player.x + round(self.vx * dt)))
        self.vy += self.GRAVITY * dt
        self.player.y += round(self.vy * dt)
        if self.vy < 0 and self.player.colliderect(self.box):
            self.player.top = self.box.bottom
            self.vy = 0
            self._open()
        if self.player.bottom >= self.GROUND_Y:
            self.player.bottom = self.GROUND_Y
            self.vy = 0
            self.on_ground = True

    def _frame(self):
        name = "jump" if not self.on_ground else ("run" if self.vx else "idle")
        animation = self.animations[name]
        animation.update(1 / FPS)
        frame = animation.current_frame
        return frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def _prize_icon(self, prize, size):
        from kobito.item_art import get_icon
        if prize["item"] is not None:
            return get_icon(prize["item"].id, size)
        icon = pygame.Surface((size, size), pygame.SRCALPHA)
        c, r = size // 2, size // 2 - 2
        if prize["kind"] == "coins":
            pygame.draw.circle(icon, (90, 56, 10), (c, c), r)
            pygame.draw.circle(icon, (255, 205, 60), (c, c), r - 4)
            pygame.draw.circle(icon, (255, 236, 150), (c, c), r - 4, width=3)
            pygame.draw.rect(icon, (200, 150, 30), (c - 4, c - r // 2, 8, r))
        else:
            pygame.draw.circle(icon, (30, 60, 100), (c, c), r)
            pygame.draw.circle(icon, (90, 170, 240), (c, c), r - 4)
            ui.text(icon, "XP", ui.title_font(32), (c, c), anchor="center")
        return icon

    def _draw(self):
        _dim(self.screen, self.background, 215)
        cx = SCREEN_WIDTH // 2
        ui.text(self.screen, "LUCKY DRAW", ui.title_font(48), (cx, 52), color=ui.GOLD, anchor="center", thickness=3)
        if not self.hit:
            sub = "Jump into the box to stop it!"
        elif not self.finished:
            sub = "..."
        else:
            sub = ""
        ui.text(self.screen, sub, ui.body_font(20), (cx, 100), anchor="center")
        floor = pygame.Rect(40, self.GROUND_Y, SCREEN_WIDTH - 80, 26)
        pygame.draw.rect(self.screen, (70, 50, 36), floor, border_radius=6)
        pygame.draw.rect(self.screen, (150, 110, 70), (floor.x, floor.y, floor.width, 5), border_radius=3)

        box = self.box.move(0, -round(40 * self.pop))
        if self.finished:
            glow = pygame.Surface((420, 420), pygame.SRCALPHA)
            pulse = 0.85 + 0.15 * math.sin(self.reveal_time * 6)
            for radius, alpha in ((200, 26), (160, 40), (124, 60)):
                pygame.draw.circle(glow, (255, 220, 120, round(alpha * pulse)), (210, 210), radius)
            self.screen.blit(glow, glow.get_rect(center=box.center))
        # The box: red with gold ribbon, a dark window showing the reel, and
        # a name plate under it.
        pygame.draw.rect(self.screen, ui.OUTLINE, box.inflate(6, 6), border_radius=14)
        pygame.draw.rect(self.screen, (214, 52, 70), box, border_radius=12)
        pygame.draw.rect(self.screen, (170, 36, 54), box.inflate(-10, -10), width=4, border_radius=10)
        for x in (box.x + 14, box.right - 22):
            pygame.draw.rect(self.screen, ui.GOLD, (x, box.y, 8, box.height))
        window = pygame.Rect(0, 0, 124, 112)
        window.midtop = (box.centerx, box.y + 14)
        edge = ui.GOLD if self.finished and int(self.reveal_time * 4) % 2 == 0 else ui.OUTLINE
        pygame.draw.rect(self.screen, edge, window.inflate(8, 8), border_radius=10)
        pygame.draw.rect(self.screen, (250, 244, 226), window, border_radius=8)
        scale = 1.0 + 1.2 * self.item_pop
        icon = self._prize_icon(self.current, self.ICON)
        if scale != 1.0:
            size = round(self.ICON * scale)
            icon = pygame.transform.scale(icon, (size, size))
        self.screen.blit(icon, icon.get_rect(center=window.center))
        plate = pygame.Rect(0, 0, box.width - 16, 34)
        plate.midbottom = (box.centerx, box.bottom - 8)
        pygame.draw.rect(self.screen, (30, 22, 40), plate, border_radius=8)
        label = prize_label(self.current)
        size = 15
        while size > 11 and get_font(size).size(label)[0] > plate.width - 14:
            size -= 1        # long names ("Genki Can  エナジードリンク") shrink to fit the plate
        if get_font(size).size(label)[0] > plate.width - 14 and self.current["item"] is not None:
            label = self.current["item"].name
        ui.text(self.screen, label, get_font(size), plate.center,
                color=ui.GOLD if self.finished else ui.CREAM, anchor="center", thickness=1)

        frame = self._frame()
        self.screen.blit(frame, frame.get_rect(midbottom=self.player.midbottom))

        if self.finished and self.reveal_time > 0.4:
            ui.text(self.screen, f"You got: {prize_label(self.prize)}!", ui.body_font(24), (cx, 498),
                    color=ui.GOLD, anchor="center")
            if int(pygame.time.get_ticks() / 500) % 2 == 0:
                ui.text(self.screen, "PRESS ENTER TO CONTINUE", ui.label_font(16), (cx, 528), anchor="center")
        pygame.display.flip()

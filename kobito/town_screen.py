"""Kobito Town (こびとまち): the street between stages.

Four stops along one street -- the player's house (costumes and
accessories, kobito/house_screen.py), the konbini (spend 円,
kobito/shop_screen.py), the notice board (daily missions, trophies,
leaderboards and stats, kobito/board_screen.py), and a signpost onward to
the next stage (or back to the title, when visited from there). The mascot, in whatever it's
wearing, walks to the stop you pick; Enter / A goes in. The Lv / 円 chip
sits top right, and a NEW! bubble over the house flags unlocked gear not
yet looked at.

Every change is saved as you leave a shop or the house.
"""

import asyncio
import math

import pygame

from kobito import audio, display, progress, save_game, setup_ui, town_ui, ui
from kobito import input as game_input
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.board_screen import BoardScreen
from kobito.house_screen import HouseScreen
from kobito.shop_screen import ShopScreen
from kobito.toasts import Toasts, draw_trophy
from kobito.wardrobe import next_unlock

GROUND_Y = 420
WALK_SPEED = 330.0
STOPS = (("house", 140, "MY HOUSE", "いえ"), ("konbini", 400, "KONBINI", "コンビニ"),
         ("board", 640, "NOTICE BOARD", "けいじばん"), ("go", 850, None, None))

SKY_TOP, SKY_BOTTOM = (70, 92, 170), (250, 170, 140)


class TownScreen:
    def __init__(self, profile, character_id, leave_label="NEXT STAGE", leave_jp="つぎへ"):
        pygame.init()
        self.screen = display.screen()
        pygame.display.set_caption("Kobito - Town")
        self.profile = profile
        self.character_id = character_id
        self.leave_label, self.leave_jp = leave_label, leave_jp
        self.mascot = town_ui.Mascot(character_id)
        self.index = 1
        self.x = float(STOPS[1][1])
        self.facing_right = True
        self.clock = pygame.time.Clock()
        self.nav = town_ui.Nav()
        self.time = 0.0
        self.going_in = None        # the stop being entered once the walk arrives
        self.stop_rects = []
        self.toasts = Toasts(profile)
        self._sky = self._build_sky()

    @staticmethod
    def _build_sky():
        sky = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            k = min(1.0, y / GROUND_Y)
            color = tuple(round(a + (b - a) * k) for a, b in zip(SKY_TOP, SKY_BOTTOM))
            pygame.draw.line(sky, color, (0, y), (SCREEN_WIDTH, y))
        # Far-off city: a row of dusky towers with lit windows.
        for i, (x, w, h) in enumerate(((0, 70, 120), (80, 50, 170), (140, 90, 100), (250, 60, 190), (330, 80, 130),
                                       (430, 50, 210), (500, 100, 120), (620, 60, 160), (700, 90, 110),
                                       (810, 50, 180), (870, 90, 130))):
            rect = pygame.Rect(x, GROUND_Y - 40 - h, w, h + 40)
            pygame.draw.rect(sky, (96, 86, 140), rect)
            for wy in range(rect.y + 10, GROUND_Y - 50, 16):
                for wx in range(rect.x + 8, rect.right - 8, 14):
                    if (wx * 7 + wy * 3 + i) % 5 < 2:
                        pygame.draw.rect(sky, (255, 220, 150), (wx, wy, 5, 7))
        return sky

    async def run(self):
        """Blocks until the player takes the signpost onward."""
        game_input.get_joysticks()
        audio.music("town")
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in game_input.events():
                self._handle(event)
            target = STOPS[self.index][1]
            moving = abs(target - self.x) > 2
            if moving:
                step = WALK_SPEED * dt
                self.facing_right = target > self.x
                self.x = target if abs(target - self.x) <= step else self.x + step * (1 if self.facing_right else -1)
            elif self.going_in is not None:
                stop, self.going_in = self.going_in, None
                if await self._enter(stop) == "leave":
                    return
            self.mascot.update(dt, moving)
            self.toasts.update(dt)
            self._draw(moving)
            await asyncio.sleep(0)

    async def _enter(self, stop):
        if stop == "go":
            audio.play("confirm")
            save_game.save_profile(self.profile)
            return "leave"
        audio.play("confirm")
        if stop == "board":
            await BoardScreen(self.screen, self.profile).run()
            save_game.save_profile(self.profile)
            self.clock.tick(FPS)
            return None
        screen_class = HouseScreen(self.screen, self.profile, self.character_id) if stop == "house" \
            else ShopScreen(self.screen, self.profile)
        audio.music("house" if stop == "house" else "konbini")
        await screen_class.run()
        save_game.save_profile(self.profile)
        audio.music("town")
        self.clock.tick(FPS)
        return None

    def _pick(self, index):
        index = max(0, min(len(STOPS) - 1, index))
        if index != self.index:
            self.index = index
            self.going_in = None
            audio.play("select")

    def _handle(self, event):
        if event.type == pygame.QUIT:
            save_game.save_profile(self.profile)
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        action = self.nav.handle(event)
        if action in ("left", "right"):
            self._pick(self.index + (1 if action == "right" else -1))
        elif action == "confirm":
            self.going_in = STOPS[self.index][0]
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            for i, rect in enumerate(self.stop_rects):
                if rect.collidepoint(pos):
                    if i == self.index:
                        self.going_in = STOPS[i][0]
                    else:
                        self._pick(i)

    # -- Drawing ---------------------------------------------------------------

    def _draw(self, moving):
        screen = self.screen
        screen.blit(self._sky, (0, 0))
        pygame.draw.rect(screen, (120, 116, 130), (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
        pygame.draw.rect(screen, (170, 166, 178), (0, GROUND_Y, SCREEN_WIDTH, 10))
        for x in range(0, SCREEN_WIDTH, 48):
            pygame.draw.line(screen, (140, 136, 150), (x, GROUND_Y + 10), (x - 20, SCREEN_HEIGHT))
        self.stop_rects = [self._draw_house(), self._draw_konbini(), self._draw_board(), self._draw_sign()]
        for i, (stop, x, title, jp) in enumerate(STOPS):
            self._draw_label(i, x, title or self.leave_label, jp or self.leave_jp)
        frame = self.mascot.frame(self.profile.worn(), scale=2, moving=moving, facing_right=self.facing_right)
        shadow = pygame.Rect(0, 0, 70, 12)
        shadow.center = (round(self.x), GROUND_Y + 4)
        pygame.draw.ellipse(screen, (60, 56, 70), shadow)
        screen.blit(frame, frame.get_rect(midbottom=(round(self.x), GROUND_Y + 6)))

        ui.text(screen, "KOBITO TOWN", ui.title_font(36), (28, 18), thickness=3)
        ui.text(screen, "こびとまち  ·  between stages", ui.body_font(15), (30, 64), color=ui.GOLD, thickness=1)
        town_ui.wallet(screen, self.profile, (SCREEN_WIDTH - 24, 20))
        upcoming = next_unlock(self.profile.level)
        if upcoming:
            words = f"Next unlock: {upcoming.name} ({upcoming.jp}) at Lv {upcoming.unlock_level}"
            ui.text(screen, words, ui.label_font(16), (SCREEN_WIDTH - 24, 72), color=ui.CREAM, anchor="topright",
                    thickness=1)
        setup_ui.hints(screen, [(setup_ui.ARROWS, "walk"), ("Enter", "go in")],
                       [(setup_ui.DPAD, "walk"), ("pad-a", "go in")])
        self.toasts.draw(screen)
        pygame.display.flip()

    def _draw_label(self, i, x, title, jp):
        screen = self.screen
        here = i == self.index
        font = ui.label_font(16)
        width = max(font.size(title)[0], ui.body_font(14).size(jp)[0]) + 30
        rect = pygame.Rect(0, 0, width, 44)
        rect.midtop = (x, GROUND_Y + 22)
        ui.panel(screen, rect, bg=(44, 36, 70, 240) if here else (24, 20, 40, 210),
                 edge=(*ui.GOLD, 255) if here else (120, 110, 150, 140), radius=10)
        ui.text(screen, title, font, (rect.centerx, rect.y + 13), color=ui.GOLD if here else ui.CREAM,
                anchor="center")
        ui.text(screen, jp, ui.body_font(14), (rect.centerx, rect.y + 31), color=ui.MUTED, anchor="center",
                thickness=1)
        if here:
            y = GROUND_Y - 236 + town_ui.bob(self.time, 5, 5)
            pygame.draw.polygon(screen, ui.OUTLINE, [(x - 14, y - 10), (x + 14, y - 10), (x, y + 9)])
            pygame.draw.polygon(screen, ui.GOLD, [(x - 11, y - 8), (x + 11, y - 8), (x, y + 6)])

    def _draw_house(self):
        screen, cx = self.screen, STOPS[0][1]
        body = pygame.Rect(0, 0, 196, 150)
        body.midbottom = (cx, GROUND_Y)
        pygame.draw.rect(screen, (60, 40, 40), body.inflate(6, 6))
        pygame.draw.rect(screen, (238, 222, 190), body)
        for y in range(body.y + 12, body.bottom, 14):
            pygame.draw.line(screen, (220, 200, 166), (body.x, y), (body.right, y))
        # A tiled roof (kawara) with upturned eaves.
        roof = [(body.x - 26, body.y + 6), (body.x + 30, body.y - 58), (body.right - 30, body.y - 58),
                (body.right + 26, body.y + 6)]
        pygame.draw.polygon(screen, (40, 50, 80), roof)
        pygame.draw.polygon(screen, (20, 24, 40), roof, 3)
        for k in range(1, 6):
            y = body.y - 58 + k * 11
            inset = 30 - k * 9
            pygame.draw.line(screen, (70, 84, 120), (body.x + inset - 4, y), (body.right - inset + 4, y), 2)
        # Sliding door, a lit window, and the name plate.
        door = pygame.Rect(body.x + 22, body.bottom - 92, 62, 92)
        pygame.draw.rect(screen, (130, 84, 50), door)
        pygame.draw.rect(screen, (250, 240, 210), door.inflate(-14, -16))
        pygame.draw.line(screen, (130, 84, 50), (door.centerx, door.y), (door.centerx, door.bottom), 3)
        for y in range(door.y + 22, door.bottom - 8, 18):
            pygame.draw.line(screen, (130, 84, 50), (door.x + 7, y), (door.right - 7, y), 2)
        window = pygame.Rect(body.right - 82, body.y + 26, 60, 46)
        pygame.draw.rect(screen, (110, 70, 44), window.inflate(8, 8))
        pygame.draw.rect(screen, (255, 222, 140), window)
        pygame.draw.line(screen, (110, 70, 44), (window.centerx, window.y), (window.centerx, window.bottom), 3)
        plate = pygame.Rect(0, 0, 70, 22)
        plate.midtop = (body.right - 52, body.bottom - 54)
        pygame.draw.rect(screen, (90, 60, 36), plate.inflate(4, 4))
        pygame.draw.rect(screen, (240, 220, 180), plate)
        name = self.mascot.character["jp"]
        font = ui.body_font(13 if len(name) > 4 else 15)
        ui.text(screen, name, font, plate.center, color=(60, 40, 30), outline=None, anchor="center")
        if any(self.profile.is_new(g.id) for g in self.profile.available()):
            tag = pygame.Rect(0, 0, 58, 24)
            tag.midbottom = (cx + 70, body.y - 62 + town_ui.bob(self.time, 4, 3))
            pygame.draw.rect(screen, ui.OUTLINE, tag.inflate(4, 4), border_radius=12)
            pygame.draw.rect(screen, ui.RED, tag, border_radius=10)
            ui.text(screen, "NEW!", ui.label_font(16), tag.center, color=ui.CREAM, outline=None, anchor="center")
        return pygame.Rect(body.x - 26, body.y - 58, body.width + 52, body.height + 58)

    def _draw_konbini(self):
        screen, cx = self.screen, STOPS[1][1]
        body = pygame.Rect(0, 0, 250, 160)
        body.midbottom = (cx, GROUND_Y)
        pygame.draw.rect(screen, (50, 46, 60), body.inflate(6, 6))
        pygame.draw.rect(screen, (246, 246, 242), body)
        for k, color in enumerate(((240, 120, 160), (255, 214, 90), (110, 190, 230))):
            pygame.draw.rect(screen, color, (body.x, body.y + 34 + k * 7, body.width, 7))
        sign = pygame.Rect(body.x + 20, body.y + 6, body.width - 40, 24)
        ui.text(screen, "こびとマート", ui.body_font(19), sign.center, color=(220, 70, 110), outline=None,
                anchor="center")
        # Glass front: the bright inside, shelves, and the sliding doors.
        glass = pygame.Rect(body.x + 14, body.y + 62, body.width - 28, body.height - 62)
        pygame.draw.rect(screen, (200, 236, 250), glass)
        for k in range(3):
            y = glass.y + 18 + k * 26
            pygame.draw.rect(screen, (150, 160, 180), (glass.x + 8, y, 74, 4))
            for j in range(5):
                color = ((240, 120, 120), (250, 210, 90), (120, 200, 140), (130, 170, 240), (250, 160, 90))[(j + k) % 5]
                pygame.draw.rect(screen, color, (glass.x + 10 + j * 14, y - 9, 10, 9))
        doors = pygame.Rect(glass.right - 110, glass.y, 100, glass.height)
        pygame.draw.rect(screen, (230, 248, 255), doors)
        pygame.draw.rect(screen, (120, 130, 150), doors, 3)
        pygame.draw.line(screen, (120, 130, 150), (doors.centerx, doors.y), (doors.centerx, doors.bottom), 3)
        ui.text(screen, "OPEN 24h", ui.label_font(16), (doors.centerx, doors.y + 14), color=(220, 70, 110),
                outline=None, anchor="center")
        glow = 0.5 + 0.5 * math.sin(self.time * 3)
        pygame.draw.rect(screen, tuple(round(150 + 100 * glow) for _ in range(3)), glass, 2)
        return body

    def _draw_board(self):
        """The town notice board: a little roofed cork board with notes
        pinned to it, and today's mission count."""
        screen, cx = self.screen, STOPS[2][1]
        post = (96, 64, 40)
        for px in (cx - 56, cx + 52):
            pygame.draw.rect(screen, post, (px, GROUND_Y - 130, 8, 130))
        board = pygame.Rect(0, 0, 124, 82)
        board.midbottom = (cx, GROUND_Y - 36)
        pygame.draw.rect(screen, post, board.inflate(12, 12), border_radius=4)
        pygame.draw.rect(screen, (196, 150, 100), board)
        roof = [(board.x - 16, board.y - 6), (cx, board.y - 34), (board.right + 16, board.y - 6)]
        pygame.draw.polygon(screen, (60, 56, 80), roof)
        pygame.draw.polygon(screen, (30, 28, 44), roof, 3)
        for k, (dx, dy, color) in enumerate(((-44, 10, (250, 246, 230)), (-6, 6, (255, 226, 140)),
                                             (30, 14, (190, 230, 250)), (-30, 44, (250, 200, 210)),
                                             (16, 46, (250, 246, 230)))):
            note = pygame.Rect(board.x + 62 + dx - 14, board.y + dy, 30, 24)
            pygame.draw.rect(screen, color, note)
            pygame.draw.line(screen, (150, 140, 130), (note.x + 4, note.y + 9), (note.right - 4, note.y + 9))
            pygame.draw.line(screen, (150, 140, 130), (note.x + 4, note.y + 15), (note.right - 8, note.y + 15))
            pygame.draw.circle(screen, (220, 60, 60), (note.centerx, note.y + 2), 3)
        draw_trophy(screen, (board.right - 10, board.bottom - 4), 22, (255, 206, 70))
        missions = progress.today_missions(self.profile)
        done = sum(m["done"] for m in missions)
        tag = pygame.Rect(0, 0, 66, 24)
        tag.midbottom = (cx, board.y - 38 + town_ui.bob(self.time, 4, 3))
        pygame.draw.rect(screen, ui.OUTLINE, tag.inflate(4, 4), border_radius=12)
        pygame.draw.rect(screen, ui.GREEN if done == len(missions) else ui.GOLD, tag, border_radius=10)
        ui.text(screen, f"{done}/{len(missions)}", ui.label_font(16), tag.center, color=ui.OUTLINE, outline=None,
                anchor="center")
        return pygame.Rect(board.x - 16, board.y - 34, board.width + 32, 150)

    def _draw_sign(self):
        screen, cx = self.screen, STOPS[3][1]
        pygame.draw.rect(screen, (90, 60, 36), (cx - 5, GROUND_Y - 150, 10, 150))
        board = pygame.Rect(0, 0, 150, 48)
        board.midtop = (cx + 16, GROUND_Y - 150)
        points = [board.topleft, (board.right - 18, board.y), (board.right, board.centery),
                  (board.right - 18, board.bottom), board.bottomleft]
        pygame.draw.polygon(screen, (200, 150, 90), points)
        pygame.draw.polygon(screen, (90, 60, 36), points, 3)
        ui.text(screen, self.leave_label, ui.label_font(16), (board.centerx - 8, board.centery), color=ui.OUTLINE,
                outline=None, anchor="center")
        lower = pygame.Rect(0, 0, 100, 34)
        lower.midtop = (cx - 14, GROUND_Y - 92)
        pygame.draw.rect(screen, (200, 150, 90), lower)
        pygame.draw.rect(screen, (90, 60, 36), lower, 3)
        ui.text(screen, self.leave_jp, ui.body_font(15), lower.center, color=ui.OUTLINE, outline=None,
                anchor="center")
        return pygame.Rect(cx - 70, GROUND_Y - 160, 170, 160)

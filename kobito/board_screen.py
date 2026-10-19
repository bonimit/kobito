"""The notice board (掲示板) in Kobito Town: four tabs.

  * MISSIONS -- today's three missions with progress, the bonus for doing
    all three, and the study streak (kobito/progress.py).
  * TROPHIES -- the trophy case: every trophy, bronze / silver / gold, lit
    once earned; pick one to see what it takes and how close you are.
  * RANKING  -- leaderboards (Ability, Best score, Right answers, Study
    streak, Trophies) for everyone who plays on this device, or -- when a
    Kobito server is set up (kobito/online.py) -- the whole world.
  * STATS    -- your lifetime numbers and rank title.

Tabs: Tab / Q / E, the gamepad's shoulder buttons, or a tap. Arrows move
inside a tab; on RANKING ←→ switch boards and Space / Y switches between
this device and the world. Esc / B leaves.
"""

import asyncio

import pygame

from kobito import audio, online, progress, save_game, setup_ui, town_ui, ui
from kobito import input as game_input
from kobito.account_screen import draw_flame
from kobito.assets import load_character_animations
from kobito.characters import get_character
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.daily_screen import draw_mission
from kobito.toasts import draw_trophy

TABS = (("missions", "MISSIONS", "ミッション"), ("trophies", "TROPHIES", "トロフィー"),
        ("ranking", "RANKING", "ランキング"), ("stats", "STATS", "きろく"))
PANEL = pygame.Rect(24, 122, SCREEN_WIDTH - 48, 370)
TROPHY_COLS = 9
TROPHY_CELL = (92, 82)
RANK_ROWS = 7
STAT_LINES = [
    ("correct", "Right answers"), ("answered", "Questions answered"), ("best_combo", "Best combo"),
    ("stages", "Stages cleared"), ("badges", "Badges earned"), ("perfect_tests", "Perfect Stage Tests"),
    ("best_score", "Best score"), ("coins", "Coins collected"), ("stomps", "Enemies defeated"),
    ("items", "Items picked up"), ("gifts", "Gift boxes opened"), ("secrets", "Secret rooms found"),
    ("sunflowers", "Sunflowers eaten"), ("buys", "Konbini purchases"), ("days", "Days played"),
]
TAB_KEYS = (pygame.K_TAB, pygame.K_e)
TAB_BACK_KEYS = (pygame.K_q,)


class BoardScreen:
    def __init__(self, screen, profile, start_tab="missions"):
        self.screen = screen
        self.profile = profile
        self.tab = [t[0] for t in TABS].index(start_tab)
        self.trophy = 0
        self.board = 0
        self.world = online.enabled()
        self.clock = pygame.time.Clock()
        self.nav = town_ui.Nav()
        self.time = 0.0
        self.tab_rects = []
        self.back_rect = pygame.Rect(0, 0, 0, 0)
        self.scope_rect = pygame.Rect(0, 0, 0, 0)
        self.icons = {}
        self._fetch()

    # -- Data --------------------------------------------------------------------

    def _fetch(self):
        if self.world:
            online.refresh(progress.BOARDS[self.board][0])

    def local_rows(self, board):
        """Everyone on this device, best first: [(name, character_id, value, label, is_me)]."""
        me = save_game.current_account()
        rows = []
        for account in save_game.list_accounts():
            mine = me is not None and account["id"] == me["id"]
            profile = self.profile if mine else save_game.load_profile_of(account["id"])
            value, label = progress.board_entry(profile)[board]
            rows.append((account["name"], account.get("character_id"), value, label, mine))
        if me is None:
            value, label = progress.board_entry(self.profile)[board]
            rows.append(("Guest", None, value, label, True))
        return sorted(rows, key=lambda r: -r[2])

    def _icon(self, character_id):
        if not character_id:
            return None
        if character_id not in self.icons:
            frame = load_character_animations(character_id, get_character(character_id)["color"])["idle"].frames[0]
            scale = 30 / frame.get_height()
            self.icons[character_id] = pygame.transform.smoothscale(
                frame, (round(frame.get_width() * scale), 30))
        return self.icons[character_id]

    # -- Loop --------------------------------------------------------------------

    async def run(self):
        game_input.get_joysticks()
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in game_input.events():
                if self._handle(event) == "back":
                    audio.play("back")
                    return
            self._draw()
            await asyncio.sleep(0)

    def _switch_tab(self, step):
        self.tab = (self.tab + step) % len(TABS)
        audio.play("select")

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        if event.type == pygame.KEYDOWN:
            if event.key in TAB_KEYS:
                self._switch_tab(1)
                return None
            if event.key in TAB_BACK_KEYS:
                self._switch_tab(-1)
                return None
            if pygame.K_1 <= event.key <= pygame.K_4:
                self.tab = event.key - pygame.K_1
                return None
            if event.key == pygame.K_SPACE and TABS[self.tab][0] == "ranking":
                self._toggle_world()
                return None
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button in (game_input.LB, game_input.RB):
                self._switch_tab(1 if event.button == game_input.RB else -1)
                return None
            if event.button == game_input.Y and TABS[self.tab][0] == "ranking":
                self._toggle_world()
                return None
        action = self.nav.handle(event)
        if action == "back":
            return "back"
        tab = TABS[self.tab][0]
        if action in ("left", "right", "up", "down"):
            step = 1 if action in ("right", "down") else -1
            if tab == "trophies":
                move = step * (TROPHY_COLS if action in ("up", "down") else 1)
                self.trophy = (self.trophy + move) % len(progress.TROPHIES)
                audio.play("select")
            elif tab == "ranking":
                self.board = (self.board + step) % len(progress.BOARDS)
                audio.play("select")
                self._fetch()
            elif action in ("left", "right"):
                self._switch_tab(step)
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            if self.back_rect.collidepoint(pos):
                return "back"
            if self.scope_rect.collidepoint(pos):
                self._toggle_world()
            for i, rect in enumerate(self.tab_rects):
                if rect.collidepoint(pos):
                    self.tab = i
        return None

    def _toggle_world(self):
        if not online.enabled():
            audio.play("denied")
            return
        self.world = not self.world
        audio.play("select")
        self._fetch()

    # -- Drawing -------------------------------------------------------------------

    def _draw(self):
        screen = self.screen
        screen.fill((58, 40, 32))
        for y in range(0, SCREEN_HEIGHT, 24):                              # a cork-board texture
            pygame.draw.line(screen, (66, 46, 36), (0, y), (SCREEN_WIDTH, y + 8))
        ui.text(screen, "NOTICE BOARD", ui.title_font(36), (28, 16), thickness=3)
        ui.text(screen, "けいじばん", ui.body_font(15), (300, 30), color=ui.GOLD, thickness=1)
        town_ui.wallet(screen, self.profile, (SCREEN_WIDTH - 24, 18))
        self._draw_tabs()
        ui.panel(screen, PANEL, bg=(20, 16, 36, 240), radius=16)
        getattr(self, "_draw_" + TABS[self.tab][0])(PANEL)
        setup_ui.hints(screen, [("Tab", "next tab"), (setup_ui.ARROWS, "move"), ("Esc", "back")],
                       [("LB/RB", "tabs"), (setup_ui.DPAD, "move"), ("pad-b", "back")])
        pygame.display.flip()

    def _draw_tabs(self):
        font = ui.label_font(16)
        x = 24
        self.tab_rects = []
        for i, (_, name, jp) in enumerate(TABS):
            rect = pygame.Rect(x, 76, font.size(name)[0] + 30, 40)
            here = i == self.tab
            ui.panel(self.screen, rect, bg=(255, 210, 110, 240) if here else (30, 24, 46, 230),
                     edge=(*ui.GOLD, 200) if here else (110, 100, 140, 150), radius=10)
            ui.text(self.screen, name, font, (rect.centerx, rect.y + 13), color=ui.OUTLINE if here else ui.CREAM,
                    outline=None if here else ui.OUTLINE, anchor="center")
            ui.text(self.screen, jp, ui.body_font(12), (rect.centerx, rect.y + 30),
                    color=ui.OUTLINE if here else ui.MUTED, outline=None, anchor="center", thickness=1)
            self.tab_rects.append(rect)
            x = rect.right + 8

    def _draw_missions(self, panel):
        screen = self.screen
        missions = progress.today_missions(self.profile)
        ui.text(screen, "TODAY'S MISSIONS", ui.label_font(16), (panel.x + 24, panel.y + 18), color=ui.GOLD)
        ui.text(screen, "new ones every day", ui.label_font(16), (panel.right - 24, panel.y + 18), color=ui.MUTED,
                anchor="topright", thickness=1)
        for i, mission in enumerate(missions):
            draw_mission(screen, pygame.Rect(panel.x + 24, panel.y + 48 + i * 44, panel.width - 48, 36), mission)
        done = sum(m["done"] for m in missions)
        y = panel.y + 196
        all_done = self.profile.missions.get("all_done")
        ui.text(screen, ("ALL DONE -- bonus collected!" if all_done else
                         f"Finish all {len(missions)} for a {progress.ALL_MISSIONS_BONUS}円 bonus  ({done}/{len(missions)})"),
                ui.body_font(17), (panel.x + 24, y), color=ui.GREEN if all_done else ui.CREAM, thickness=1)
        streak = self.profile.streak
        draw_flame(screen, (panel.x + 42, y + 78), 20)
        ui.text(screen, f"{streak.get('days', 0)}-DAY STUDY STREAK", ui.title_font(32), (panel.x + 72, y + 58),
                color=(255, 170, 80))
        ui.text(screen, f"best {streak.get('best', 0)} days  ·  play every day: the daily bonus grows for a week "
                        f"(up to {progress.daily_bonus_for(7)}円)", ui.body_font(15), (panel.x + 72, y + 96),
                color=ui.MUTED, thickness=1)

    def _draw_trophies(self, panel):
        screen = self.screen
        earned = set(self.profile.trophies)
        ui.text(screen, f"{len(earned)} / {len(progress.TROPHIES)} EARNED", ui.label_font(16),
                (panel.x + 24, panel.y + 14), color=ui.GOLD)
        x0 = panel.x + (panel.width - TROPHY_COLS * TROPHY_CELL[0]) // 2
        for i, trophy in enumerate(progress.TROPHIES):
            r, c = divmod(i, TROPHY_COLS)
            cell = pygame.Rect(x0 + c * TROPHY_CELL[0], panel.y + 38 + r * TROPHY_CELL[1], TROPHY_CELL[0] - 8,
                               TROPHY_CELL[1] - 8)
            here = i == self.trophy
            have = trophy.id in earned
            ui.panel(screen, cell, bg=(54, 46, 82, 240) if have else (28, 24, 42, 230),
                     edge=(*ui.GOLD, 230) if here else None, radius=10)
            color = progress.TIER_COLORS[trophy.tier] if have else (70, 66, 86)
            draw_trophy(screen, (cell.centerx, cell.centery - 4), 34, color)
            if not have:
                ui.text(screen, "?", ui.label_font(16), (cell.centerx, cell.centery - 8), color=ui.MUTED, anchor="center")
        trophy = progress.TROPHIES[self.trophy]
        info = pygame.Rect(panel.x + 20, panel.bottom - 80, panel.width - 40, 66)
        ui.panel(screen, info, bg=(34, 28, 54, 230), edge=None, radius=12)
        have = trophy.id in earned
        tier_color = progress.TIER_COLORS[trophy.tier]
        ui.text(screen, f"{trophy.name}  ·  {trophy.jp}", ui.body_font(19), (info.x + 16, info.y + 8),
                color=ui.CREAM if have else ui.MUTED)
        ui.text(screen, progress.TIER_NAMES[trophy.tier], ui.label_font(16), (info.right - 16, info.y + 10),
                color=tier_color, anchor="topright")
        current = progress.stat_value(self.profile, trophy.stat)
        status = "EARNED" if have else f"{min(current, trophy.goal):,} / {trophy.goal:,}"
        ui.text(screen, f"{trophy.text}  ·  reward {trophy.reward}円", ui.body_font(15), (info.x + 16, info.y + 38),
                color=ui.MUTED, thickness=1)
        ui.text(screen, status, ui.label_font(16), (info.right - 16, info.y + 40), color=ui.GREEN if have else ui.GOLD,
                anchor="topright")

    def _draw_ranking(self, panel):
        screen = self.screen
        key, title, about = progress.BOARDS[self.board]
        setup_ui.triangle(screen, (panel.x + 30, panel.y + 27), 8, -1, ui.GOLD)
        ui.text(screen, title, ui.title_font(32), (panel.x + 50, panel.y + 10))
        width = ui.title_font(32).size(title)[0]
        setup_ui.triangle(screen, (panel.x + 66 + width, panel.y + 27), 8, 1, ui.GOLD)
        ui.text(screen, about, ui.body_font(15), (panel.x + 88 + width, panel.y + 18), color=ui.MUTED, thickness=1)
        # This device / the world.
        font = ui.label_font(16)
        scope = "WORLD" if self.world else "THIS DEVICE"
        self.scope_rect = pygame.Rect(0, 0, 220, 30)
        self.scope_rect.topright = (panel.right - 18, panel.y + 12)
        ui.panel(screen, self.scope_rect, bg=(40, 32, 58, 230), radius=15)
        ui.text(screen, (game_input.prompt("Space", "Y", "Tap") + "  " + scope), font, self.scope_rect.center,
                color=ui.SKY if self.world else ui.CREAM, anchor="center", thickness=1)

        if self.world:
            fetched, status = online.rows(key)
            rows = [(r["name"], r.get("character_id"), r["value"], r["label"],
                     r["name"] == (save_game.current_account() or {}).get("name")) for r in (fetched or [])]
            if status != "ok" and not rows:
                words = "Loading the world leaderboard…" if status == "loading" else "Couldn't reach the server."
                ui.text(screen, words, ui.body_font(18), (panel.centerx, panel.centery), color=ui.MUTED, anchor="center")
                return
        else:
            rows = self.local_rows(key)
        if not rows:
            ui.text(screen, "No scores yet -- play a stage!", ui.body_font(18), panel.center, color=ui.MUTED,
                    anchor="center")
            return
        mine = next((i for i, r in enumerate(rows) if r[4]), None)
        shown = rows[:RANK_ROWS]
        for i, (name, character_id, value, label, is_me) in enumerate(shown):
            self._rank_row(pygame.Rect(panel.x + 24, panel.y + 54 + i * 38, panel.width - 48, 32), i + 1, name,
                           character_id, label, is_me)
        if mine is not None and mine >= RANK_ROWS:
            name, character_id, value, label, _ = rows[mine]
            self._rank_row(pygame.Rect(panel.x + 24, panel.y + 54 + RANK_ROWS * 38 - 4, panel.width - 48, 32),
                           mine + 1, name, character_id, label, True)
        if not online.enabled():
            ui.text(screen, "World ranking: start a Kobito server and set KOBITO_SERVER (see README)", ui.body_font(13),
                    (panel.centerx, panel.bottom - 12), color=ui.MUTED, anchor="center", thickness=1)

    def _rank_row(self, rect, rank, name, character_id, label, is_me):
        screen = self.screen
        ui.panel(screen, rect, bg=(70, 56, 30, 235) if is_me else (34, 28, 54, 225),
                 edge=(*ui.GOLD, 220) if is_me else None, radius=8)
        medal = {1: progress.TIER_COLORS[2], 2: progress.TIER_COLORS[1], 3: progress.TIER_COLORS[0]}.get(rank)
        if medal:
            pygame.draw.circle(screen, ui.OUTLINE, (rect.x + 22, rect.centery), 13)
            pygame.draw.circle(screen, medal, (rect.x + 22, rect.centery), 11)
        ui.text(screen, str(rank), ui.label_font(16), (rect.x + 22, rect.centery),
                color=ui.OUTLINE if medal else ui.CREAM, outline=None if medal else ui.OUTLINE, anchor="center")
        icon = self._icon(character_id)
        if icon:
            screen.blit(icon, icon.get_rect(midleft=(rect.x + 46, rect.centery)))
        ui.text(screen, name + ("  (you)" if is_me else ""), ui.body_font(18), (rect.x + 96, rect.centery),
                color=ui.GOLD if is_me else ui.CREAM, anchor="midleft", thickness=1)
        ui.text(screen, label, ui.label_font(16), (rect.right - 16, rect.centery), anchor="midright")

    def _draw_stats(self, panel):
        screen = self.screen
        kanji, reading, english = progress.rank_for(self.profile.level)
        account = save_game.current_account()
        ui.text(screen, (account["name"] if account else "Guest"), ui.title_font(32), (panel.x + 24, panel.y + 12))
        ui.text(screen, f"Lv {self.profile.level}  ·  {english}  {kanji} ({reading})", ui.body_font(17),
                (panel.x + 26, panel.y + 52), color=ui.GOLD, thickness=1)
        col_w = (panel.width - 48) // 3
        for i, (key, words) in enumerate(STAT_LINES):
            c, r = divmod(i, 5)
            x = panel.x + 24 + c * col_w
            y = panel.y + 92 + r * 52
            ui.panel(screen, (x, y, col_w - 12, 44), bg=(34, 28, 54, 225), edge=None, radius=8)
            ui.text(screen, words, ui.body_font(14), (x + 12, y + 6), color=ui.MUTED, thickness=1)
            ui.text(screen, f"{self.profile.stats.get(key, 0):,}", ui.label_font(16), (x + 12, y + 24))

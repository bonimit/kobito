"""The daily welcome: shown on a player's first visit of the day.

A stamp card for the week (one stamp per day of the study streak, the
bonus growing each day up to a week -- kobito/progress.py), the 円 just
added, and today's three missions. Any key / button / tap continues.
"""

import asyncio

import pygame

from kobito import audio, progress, setup_ui, ui
from kobito import input as game_input
from kobito.account_screen import draw_flame
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH

PANEL = pygame.Rect(0, 0, 700, 430)
PANEL.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 6)
GRACE = 0.6


class DailyBonusScreen:
    def __init__(self, profile, bonus, name=None):
        self.screen = pygame.display.get_surface()
        self.profile = profile
        self.bonus = bonus            # from progress.daily_login
        self.name = name
        self.clock = pygame.time.Clock()
        self.backdrop = setup_ui.backdrop()
        self.time = 0.0
        audio.play("levelup")

    async def run(self):
        game_input.get_joysticks()
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            self.backdrop.update(dt)
            for event in game_input.events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                game_input.handle_hotplug(event)
                go = event.type in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN) or game_input.touch_tap_pos(event)
                if go and self.time > GRACE:
                    audio.play("confirm")
                    return
            self._draw()
            await asyncio.sleep(0)

    def _draw(self):
        screen = self.screen
        self.backdrop.draw(screen)
        panel = ui.panel(screen, PANEL, bg=(20, 16, 36, 245), radius=18)
        hello = f"WELCOME BACK, {self.name.upper()}!" if self.name else "WELCOME BACK!"
        ui.text(screen, hello, ui.label_font(16), (panel.centerx, panel.y + 22), color=ui.GOLD, anchor="center")
        ui.text(screen, "DAILY BONUS", ui.title_font(36), (panel.centerx, panel.y + 52), anchor="center", thickness=3)
        ui.text(screen, "まいにち ボーナス", ui.body_font(15), (panel.centerx, panel.y + 80), color=ui.SKY,
                anchor="center", thickness=1)

        # The week's stamp card: today's stamp pops in.
        days = self.bonus["days"]
        in_week = (days - 1) % 7 + 1
        for k in range(7):
            cell = pygame.Rect(panel.x + 40 + k * 90, panel.y + 104, 80, 92)
            stamped = k < in_week
            today = k == in_week - 1
            ui.panel(screen, cell, bg=(255, 236, 190, 240) if stamped else (40, 34, 60, 230),
                     edge=(*ui.GOLD, 255) if today else (110, 100, 140, 150), radius=10)
            ui.text(screen, f"DAY {k + 1}", ui.label_font(16), (cell.centerx, cell.y + 14),
                    color=ui.OUTLINE if stamped else ui.MUTED, outline=None if stamped else ui.OUTLINE, anchor="center")
            reward = progress.daily_bonus_for(days - in_week + k + 1)
            ui.text(screen, f"{reward}円", ui.body_font(15), (cell.centerx, cell.bottom - 14),
                    color=ui.OUTLINE if stamped else ui.CREAM, outline=None if stamped else ui.OUTLINE,
                    anchor="center", thickness=1)
            if stamped:
                pop = min(1.0, self.time / 0.4) if today else 1.0
                r = round(20 * (1.6 - 0.6 * pop) if today else 20)
                pygame.draw.circle(screen, (220, 50, 60), (cell.centerx, cell.centery), r, 4)
                ui.text(screen, "済", ui.body_font(20), (cell.centerx, cell.centery), color=(220, 50, 60), outline=None,
                        anchor="center", thickness=1)

        y = panel.y + 222
        draw_flame(screen, (panel.x + 64, y + 4), 18)
        ui.text(screen, f"{days}-DAY STREAK", ui.title_font(32), (panel.x + 92, y - 14), color=(255, 170, 80))
        ui.text(screen, f"best {self.bonus['best']} days  ·  come back tomorrow for more!", ui.body_font(15),
                (panel.x + 92, y + 25), color=ui.MUTED, thickness=1)
        ui.text(screen, f"+{self.bonus['bonus']}円", ui.title_font(36), (panel.right - 40, y - 2), color=ui.GOLD,
                anchor="midright", thickness=3)

        ui.text(screen, "TODAY'S MISSIONS  ·  きょうの ミッション", ui.label_font(16), (panel.x + 40, y + 52),
                color=ui.GOLD)
        for i, mission in enumerate(progress.today_missions(self.profile)):
            row = pygame.Rect(panel.x + 40, y + 76 + i * 34, panel.width - 80, 28)
            draw_mission(screen, row, mission)
        if self.time > GRACE:
            words = game_input.prompt("PRESS ANY KEY", "PRESS A", "TAP TO CONTINUE")
            ui.text(screen, words, ui.label_font(16), (panel.centerx, panel.bottom + 18), color=ui.CREAM,
                    anchor="center")
        pygame.display.flip()


def draw_mission(screen, row, mission):
    """One mission: words, a progress bar, the reward (or a tick when done)."""
    done = mission["done"]
    ui.panel(screen, row, bg=(30, 60, 44, 230) if done else (34, 28, 54, 230), edge=None, radius=8)
    ui.text(screen, mission["words"], ui.body_font(15), (row.x + 12, row.centery), color=ui.CREAM,
            anchor="midleft", thickness=1)
    bar = pygame.Rect(row.right - 260, row.centery - 4, 140, 8)
    ui.bar(screen, bar, mission["progress"] / mission["goal"], ui.GREEN if done else ui.GOLD, radius=4)
    ui.text(screen, f"{mission['progress']}/{mission['goal']}", ui.label_font(16), (bar.right + 8, row.centery),
            color=ui.MUTED, anchor="midleft", thickness=1)
    if done:
        setup_ui.check(screen, (row.right - 22, row.centery), ui.GREEN)
    else:
        ui.text(screen, f"{mission['reward']}円", ui.label_font(16), (row.right - 10, row.centery), color=ui.GOLD,
                anchor="midright")

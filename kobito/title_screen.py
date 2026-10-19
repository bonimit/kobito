"""The first screen when a saved game exists: Continue or New Game.

Shown over the saved world itself (the level's backdrop, scrolled to where
the player saved), with a card summarising the save -- mascot, companion,
level, score, badges, items. Starting a New Game replaces the save, so it
asks once more before going ahead.

run() returns "continue" or "new".
"""

import asyncio
import math

import pygame

from kobito import input as game_input
from kobito import ui
from kobito.assets import load_character_animations
from kobito.background import Background
from kobito.characters import get_character
from kobito.companion_art import draw_companion
from kobito.companions import get_companion
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.levels.level1 import build_level1
from kobito.themes import get_theme

RESULT_CONTINUE = "continue"
RESULT_NEW = "new"

CARD = pygame.Rect(0, 0, 560, 236)
CARD.midtop = (SCREEN_WIDTH // 2, 132)
BUTTON_SIZE = (230, 52)


class TitleScreen:
    def __init__(self, saved):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito")
        self.clock = pygame.time.Clock()
        self.saved = saved
        run = saved["run"]
        self.character = get_character(run["character_id"])
        self.companion = get_companion(run["companion_id"])
        self.theme = get_theme(run["theme_id"])
        self.selected = 0            # 0 = Continue, 1 = New Game
        self.confirm_new = False     # New Game pressed once: ask again
        self.time = 0.0
        self._stick = 0
        game_input.get_joysticks()

        level = build_level1(run["theme_id"], level_number=run["level_number"],
                             favorites=self.character["favorites"])
        self.background = Background(level.width_px, level.ground_y, level.ground_segments_px, level.theme)
        spot = (saved.get("level") or {}).get("player")
        self.camera_x = max(0.0, (spot[0] if spot else 0) - SCREEN_WIDTH / 2)
        self.idle = load_character_animations(self.character["id"], self.character["color"],
                                              width=64, height=96)["idle"]
        self.dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.dim.fill((8, 6, 16, 150))
        self.buttons = []

    async def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in game_input.events():
                result = self._handle(event)
                if result:
                    return result
            self.idle.update(dt)
            self.background.update(dt)
            self._draw()
            await asyncio.sleep(0)

    # -- Input ----------------------------------------------------------------

    def _choose(self, index):
        if index == 0:
            return RESULT_CONTINUE
        if self.confirm_new:
            return RESULT_NEW
        self.confirm_new = True
        return None

    def _move(self, step):
        self.selected = (self.selected + step) % 2
        self.confirm_new = False

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                self._move(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                self._move(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return self._choose(self.selected)
            elif event.key == pygame.K_ESCAPE:
                if self.confirm_new:
                    self.confirm_new = False
                else:
                    pygame.quit()
                    raise SystemExit
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button in game_input.CONFIRM_BUTTONS:
                return self._choose(self.selected)
            if event.button in game_input.CANCEL_BUTTONS:
                self.confirm_new = False
        elif event.type == pygame.JOYHATMOTION and (event.value[0] or event.value[1]):
            self._move(event.value[0] or -event.value[1])
        elif event.type == pygame.JOYAXISMOTION and event.axis in (0, 1):
            direction = 0 if abs(event.value) < game_input.AXIS_DEADZONE else (1 if event.value > 0 else -1)
            if direction and direction != self._stick:
                self._move(direction)
            self._stick = direction
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos) and i != self.selected:
                    self._move(i - self.selected)

        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(pos):
                    if i != self.selected:
                        self.selected, self.confirm_new = i, False
                    return self._choose(i)
        return None

    # -- Drawing --------------------------------------------------------------

    def _draw(self):
        self.background.draw(self.screen, self.camera_x)
        self.screen.blit(self.dim, (0, 0))
        cx = SCREEN_WIDTH // 2

        ui.text(self.screen, "こびと", ui.label_font(16), (cx, 40), color=ui.GOLD, anchor="center")
        ui.text(self.screen, "KOBITO", ui.title_font(48), (cx, 80), anchor="center", thickness=3)

        self._draw_save_card()
        self._draw_buttons()

        if self.confirm_new:
            note, color = "Your saved game will be replaced. Press again to start over.", (255, 170, 170)
        else:
            note, color = game_input.prompt("↑↓ choose    Enter select    Esc quit", "D-pad choose    A select"), ui.MUTED
        ui.text(self.screen, note, ui.label_font(16), (cx, SCREEN_HEIGHT - 26), color=color, anchor="center",
                thickness=1)
        pygame.display.flip()

    def _draw_save_card(self):
        run, level = self.saved["run"], self.saved.get("level")
        card = ui.panel(self.screen, CARD, bg=(18, 14, 32, 235), radius=16)
        label, big, body = ui.label_font(16), ui.title_font(32), ui.body_font(18)

        # Portraits: the mascot, with the companion at its shoulder.
        well = pygame.Rect(card.x + 18, card.y + 18, 132, card.height - 36)
        pygame.draw.rect(self.screen, (44, 36, 66), well, border_radius=12)
        frame = self.idle.current_frame
        self.screen.blit(frame, frame.get_rect(midbottom=(well.centerx - 8, well.bottom - 26)))
        bob = round(3 * math.sin(self.time * 2.5))
        draw_companion(self.screen, self.companion["id"], well.right - 26, well.y + 34 + bob, 40)
        ui.text(self.screen, self.character["name"].upper(), label, (well.centerx, well.bottom - 14),
                anchor="center", thickness=1)

        x = well.right + 22
        ui.text(self.screen, "SAVED GAME", label, (x, card.y + 20), color=ui.GOLD)
        ui.text(self.screen, self.saved.get("saved_at", ""), label, (card.right - 20, card.y + 20), color=ui.MUTED,
                anchor="topright", thickness=1)
        mode = {"adaptive": f"AI {run['jlpt_level']}", "random": "RANDOM"}.get(run.get("difficulty_mode"), run["jlpt_level"])
        ui.text(self.screen, f"LEVEL {run['level_number']}  ·  {mode}", big, (x, card.y + 40))
        ui.text(self.screen, self.theme.name, body, (x, card.y + 82), color=ui.SKY, thickness=1)

        stats = [("SCORE", str(run["score"])), ("XP", str(run["xp"])),
                 ("BADGES", str(len(run["badges"]))), ("ITEMS", str(sum(run["item_box"].values())))]
        tile_w = (card.right - 20 - x - 3 * 8) // 4
        for i, (name, value) in enumerate(stats):
            tile = ui.panel(self.screen, (x + i * (tile_w + 8), card.y + 120, tile_w, 62), radius=10)
            ui.text(self.screen, name, label, (tile.centerx, tile.y + 16), color=ui.GOLD, anchor="center")
            ui.text(self.screen, value, label if len(value) > 6 else big, (tile.centerx, tile.y + 42),
                    anchor="center")
        where = "right where you left off" if level else f"from the start of level {run['level_number']}"
        ui.text(self.screen, f"with {self.companion['name']}  ·  {where}", ui.body_font(16), (x, card.y + 192),
                color=ui.MUTED, thickness=1)

    def _draw_buttons(self):
        labels = ["CONTINUE", "NEW GAME"]
        gap = 24
        total = 2 * BUTTON_SIZE[0] + gap
        x0 = SCREEN_WIDTH // 2 - total // 2
        y = CARD.bottom + 34
        self.buttons = []
        for i, words in enumerate(labels):
            rect = pygame.Rect(x0 + i * (BUTTON_SIZE[0] + gap), y, *BUTTON_SIZE)
            self.buttons.append(rect)
            active = i == self.selected
            danger = i == 1 and self.confirm_new
            if active:
                bg = (240, 86, 96, 235) if danger else (255, 210, 110, 240)
                ui.panel(self.screen, rect, bg=bg, edge=(20, 14, 26, 255), radius=14)
                color, outline = ui.OUTLINE, None
            else:
                ui.panel(self.screen, rect, bg=(30, 24, 46, 220), radius=14)
                color, outline = ui.MUTED, ui.OUTLINE
            text = "REALLY START OVER?" if danger else words
            ui.text(self.screen, text, ui.label_font(16) if danger else ui.title_font(32), rect.center,
                    color=ui.CREAM if danger else color, outline=outline, anchor="center")

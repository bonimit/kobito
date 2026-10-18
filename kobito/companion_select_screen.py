import asyncio
import math

import pygame

from kobito import input as game_input
from kobito import setup_ui, ui
from kobito.companion_art import draw_companion
from kobito.companions import COMPANIONS
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH

TYPE_SPEED = 42.0        # greeting characters per second
HAPPY_PERIOD = 2.6       # a quick happy face every so often once it's done talking
CONFIRM_SECONDS = 0.45
# What every companion does in the game, whichever you pick.
DUTIES = (
    ("!", "Explains it when you answer wrong"),
    ("?", "Nudges you if you're stuck for ~10 seconds"),
    ("*", "Teaches the word for each item you collect"),
)


class CompanionSelectScreen:
    """Step 2 of a new game: pick the AI companion that gives hints.

    The highlighted companion floats on a lit stage and greets you in
    its own voice (typed out in a speech bubble). The card beside it
    shows its name, personality and ability (kobito/companions.py -- a
    real gameplay difference, not just a skin), what any companion does
    for you during play, and whether hints are live from Claude or the
    built-in ones (no API key / web build). All five sit in a roster
    strip; controls are the same as the mascot screen.

    The chosen companion_id flows into Game -> HintService, so its
    Claude-generated hints come back in that companion's voice and its
    ability applies for the whole run, and into every screen after this
    one that shows the companion's portrait.

    run() returns the chosen companion's id.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your companion")
        self.clock = pygame.time.Clock()
        self.index = 0
        self.time = 0.0
        self.typed = 0.0          # characters of the greeting shown so far
        self.confirming = None
        self.backdrop = setup_ui.backdrop()
        game_input.get_joysticks()
        self.joy_nav = game_input.MenuNav()
        self._arrows = {}
        self._cards = []
        self._confirm = setup_ui.CONFIRM
        self.live_ai = self._live_ai()

    @staticmethod
    def _live_ai():
        """True when Claude can write the hints (an API key is set up)."""
        from kobito.hint_service import HintService
        return HintService()._client is not None

    async def run(self):
        """Blocks until the player confirms a companion, then returns its id."""
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in pygame.event.get():
                self._handle(event)
            if self.confirming is not None:
                self.confirming += dt
                if self.confirming >= CONFIRM_SECONDS:
                    return COMPANIONS[self.index]["id"]
            self.backdrop.update(dt)
            self.typed += TYPE_SPEED * dt
            self._draw()
            await asyncio.sleep(0)  # yields to the browser event loop; a no-op on desktop

    # -- Input -------------------------------------------------------------------

    def _select(self, index):
        index %= len(COMPANIONS)
        if index != self.index:
            self.index = index
            self.typed = 0.0

    def _confirm_pick(self):
        if self.confirming is None:
            self.confirming = 0.0

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        if self.confirming is not None:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                self._select(self.index - 1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                self._select(self.index + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._confirm_pick()
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit

        action = self.joy_nav.handle_event(event)
        if action in ("left", "right"):
            self._select(self.index + (1 if action == "right" else -1))
        elif action == "confirm":
            self._confirm_pick()
        elif action == "cancel":
            pygame.quit()
            raise SystemExit

        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            for direction, rect in self._arrows.items():
                if rect.collidepoint(pos):
                    self._select(self.index + direction)
                    return
            for i, rect in enumerate(self._cards):
                if rect.collidepoint(pos):
                    if i == self.index:
                        self._confirm_pick()
                    else:
                        self._select(i)
                    return
            if self._confirm.collidepoint(pos):
                self._confirm_pick()

    # -- Drawing -----------------------------------------------------------------

    def _draw(self):
        screen = self.screen
        self.backdrop.draw(screen)
        setup_ui.draw_steps(screen, 1)
        setup_ui.draw_title(screen, "CHOOSE YOUR AI COMPANION", "ヒントを くれる なかまを えらぼう")
        companion = COMPANIONS[self.index]
        self._draw_stage(companion)
        self._draw_card(companion)
        self._cards = setup_ui.roster(screen, len(COMPANIONS), self.index, 96, self._draw_roster_item, self.time)
        flash = max(0.0, 1 - self.confirming / CONFIRM_SECONDS) if self.confirming is not None else 0.0
        self._confirm = setup_ui.confirm_button(screen, "CHOOSE", self.time, flash)
        setup_ui.hints(screen, [(setup_ui.ARROWS, "browse"), ("Enter", "choose"), ("Esc", "quit")])
        pygame.display.flip()

    def _expression(self, companion):
        if self.confirming is not None:
            return "happy"
        if self.typed < len(companion["greeting"]):
            return "talking"
        return "happy" if (self.time % HAPPY_PERIOD) < 0.35 else "idle"

    def _draw_stage(self, companion):
        screen, stage = self.screen, setup_ui.STAGE
        ui.panel(screen, stage, bg=setup_ui.STAGE_BG, radius=16)
        floor = setup_ui.spotlight(screen, stage, companion["color"], self.time)
        bob = round(6 * math.sin(self.time * 2.2))
        size = 132 + (round(18 * math.sin(self.confirming * 9)) if self.confirming is not None else 0)
        shadow = pygame.Rect(0, 0, 86 - bob * 2, 14)
        shadow.center = (stage.centerx, floor - 2)
        pygame.draw.ellipse(screen, (10, 6, 18), shadow)
        draw_companion(screen, companion["id"], stage.centerx, floor - 82 + bob, size,
                       expression=self._expression(companion))
        self._draw_bubble(companion, stage)
        self._arrows = {
            -1: setup_ui.arrow_button(screen, (stage.x + 34, stage.centery + 20), -1),
            1: setup_ui.arrow_button(screen, (stage.right - 34, stage.centery + 20), 1),
        }
        ui.text(screen, f"{self.index + 1} / {len(COMPANIONS)}", ui.label_font(16), (stage.centerx, stage.bottom - 18),
                color=ui.MUTED, anchor="center", thickness=1)

    def _draw_bubble(self, companion, stage):
        """The greeting, typed out, in a speech bubble at the top of the stage."""
        font = ui.body_font(16)
        bubble = pygame.Rect(stage.x + 16, stage.y + 14, stage.width - 32, 74)
        shown = companion["greeting"][:int(self.typed)]
        pygame.draw.rect(self.screen, ui.OUTLINE, bubble.inflate(4, 4), border_radius=14)
        pygame.draw.rect(self.screen, (252, 246, 232), bubble, border_radius=12)
        tail = [(stage.centerx - 10, bubble.bottom - 1), (stage.centerx + 10, bubble.bottom - 1),
                (stage.centerx, bubble.bottom + 12)]
        pygame.draw.polygon(self.screen, (252, 246, 232), tail)
        pygame.draw.lines(self.screen, ui.OUTLINE, False, [tail[0], tail[2], tail[1]], 2)
        y = bubble.y + 10
        for line in setup_ui.wrap(shown, font, bubble.width - 28)[:3]:
            self.screen.blit(font.render(line, True, (40, 30, 46)), (bubble.x + 14, y))
            y += 21

    def _draw_card(self, companion):
        screen, card = self.screen, setup_ui.CARD
        ui.panel(screen, card, bg=setup_ui.CARD_BG, radius=16)
        x = card.x + 24
        ui.text(screen, companion["name"].upper(), ui.title_font(36), (x, card.y + 14), thickness=3)
        ui.text(screen, companion["jp"], ui.body_font(20), (x, card.y + 58), color=ui.GOLD, thickness=1)
        self._draw_ai_chip(card)
        ui.text(screen, companion["tagline"], ui.body_font(17), (x, card.y + 88), color=ui.SKY, thickness=1)

        ability = ui.panel(screen, (x, card.y + 116, card.width - 48, 76), bg=(44, 34, 66, 235),
                           edge=(255, 196, 90, 170), radius=10)
        ui.text(screen, "ABILITY", ui.label_font(16), (ability.x + 12, ability.y + 8), color=ui.GOLD)
        ui.text(screen, companion["ability_name"], ui.body_font(17), (ability.x + 86, ability.y + 6), thickness=1)
        lines = setup_ui.wrap(companion["ability_description"], ui.body_font(15), ability.width - 24)
        for i, line in enumerate(lines[:2]):
            ui.text(screen, line, ui.body_font(15), (ability.x + 12, ability.y + 30 + i * 18), color=ui.CREAM,
                    thickness=1)

        ui.text(screen, "EVERY COMPANION", ui.label_font(16), (x, card.y + 202), color=ui.GOLD)
        for i, (mark, words) in enumerate(DUTIES):
            y = card.y + 230 + i * 23
            pygame.draw.circle(screen, (60, 50, 88), (x + 10, y), 10)
            if mark == "*":
                setup_ui.star(screen, (x + 10, y), 7, ui.GOLD)
            else:
                ui.text(screen, mark, ui.label_font(16), (x + 10, y), color=ui.GOLD, anchor="center", thickness=1)
            ui.text(screen, words, ui.body_font(15), (x + 28, y), anchor="midleft", thickness=1)

    def _draw_ai_chip(self, card):
        if self.live_ai:
            words, color = "LIVE AI HINTS · CLAUDE", ui.GREEN
        else:
            words, color = "BUILT-IN HINTS", ui.MUTED
        font = ui.label_font(16)
        chip = pygame.Rect(0, 0, font.size(words)[0] + 34, 26)
        chip.topright = (card.right - 18, card.y + 20)
        pygame.draw.rect(self.screen, (30, 24, 48), chip, border_radius=13)
        pygame.draw.rect(self.screen, color, chip, width=1, border_radius=13)
        pulse = 0.6 + 0.4 * math.sin(self.time * 4) if self.live_ai else 1.0
        dot = tuple(round(c * pulse) for c in color)
        pygame.draw.circle(self.screen, dot, (chip.x + 14, chip.centery), 5)
        ui.text(self.screen, words, font, (chip.x + 24, chip.centery), color=color, anchor="midleft", thickness=1)

    def _draw_roster_item(self, i, rect, selected):
        draw_companion(self.screen, COMPANIONS[i]["id"], rect.centerx, rect.centery + 2, 56 if selected else 48,
                       expression="happy" if selected else "idle")

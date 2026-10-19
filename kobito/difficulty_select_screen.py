import asyncio
import math

import pygame

from kobito import input as game_input
from kobito import setup_ui, ui
from kobito.companion_art import draw_companion
from kobito.companions import get_companion
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.difficulty import JLPT_DESCRIPTIONS, JLPT_LEVELS, MODE_ADAPTIVE, MODE_CHOOSE, MODE_RANDOM
from kobito.word_data import WORDS

OPTIONS = JLPT_LEVELS + [MODE_ADAPTIVE, MODE_RANDOM]
TYPE_SPEED = 48.0
CONFIRM_SECONDS = 0.45
ROW_H = 36
LEVEL_COLORS = {"N5": (110, 200, 120), "N4": (80, 180, 210), "N3": (240, 196, 70), "N2": (240, 140, 70),
                "N1": (225, 80, 90), MODE_ADAPTIVE: (170, 120, 250), MODE_RANDOM: (150, 150, 170)}
# What the companion says about each choice (shown in its speech bubble).
PITCH = {
    "N5": "A great place to start: kana, everyday words and simple sentences.",
    "N4": "Basic grammar and your first real kanji -- for when N5 feels easy.",
    "N3": "Everyday Japanese: longer sentences, more kanji, natural phrases.",
    "N2": "News, work and polite speech. A real challenge!",
    "N1": "Idioms, formal writing and the toughest kanji. Good luck!",
    MODE_ADAPTIVE: "I'll pick every question for you -- harder on a roll, easier when you're stuck.",
    MODE_RANDOM: "Anything from N5 to N1, every question a surprise!",
}
LABELS = {MODE_ADAPTIVE: ("AI", "AI Adaptive"), MODE_RANDOM: ("?", "Random mix")}


def _sample(option):
    """A few words from the level, so you can see what it means."""
    if option == MODE_ADAPTIVE:
        return "Starts at N5, then adapts to every answer -- missed ones come back."
    if option == MODE_RANDOM:
        return "A different level every question: " + "  ·  ".join(WORDS[lv][2][0] for lv in JLPT_LEVELS)
    return "e.g.  " + "  ·  ".join(f"{w[0]} {w[2].split(' / ')[0].lower()}" for w in WORDS[option][:4])


class DifficultySelectScreen:
    """Step 4 of a new game: how questions are picked --

      * a JLPT level, N5 (easiest) to N1 (hardest) -- questions from that
        level, stepping up or down between levels by how it went;
      * AI Adaptive -- the companion adjusts every single question to the
        player: harder when they're on a roll, easier when they're stuck,
        always kept in a comfortable range, with missed questions coming
        back for review (kobito/adaptive.py);
      * Random -- any question from any level, a surprise every time.

    Same look as the hero and companion screens (kobito/setup_ui.py): the
    chosen companion on the stage explains the highlighted option in a
    speech bubble; the card lists all seven, with sample words from the
    highlighted level underneath. Up/Down or Left/Right (keys, d-pad,
    stick) move, Enter / A / a second tap chooses.

    run() returns (mode, starting JLPT level).
    """

    def __init__(self, companion_id="kobito"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your level")
        self.clock = pygame.time.Clock()
        self.companion = get_companion(companion_id)
        self.index = 0
        self.time = 0.0
        self.typed = 0.0
        self.confirming = None
        self.backdrop = setup_ui.backdrop()
        self._stick = 0
        self._rows = []
        self._confirm = setup_ui.CONFIRM
        game_input.get_joysticks()

    async def run(self):
        """Blocks until the player confirms, then returns (mode, jlpt_level)."""
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in game_input.events():
                self._handle(event)
            if self.confirming is not None:
                self.confirming += dt
                if self.confirming >= CONFIRM_SECONDS:
                    return self.result_for(OPTIONS[self.index])
            self.backdrop.update(dt)
            self.typed += TYPE_SPEED * dt
            self._draw()
            await asyncio.sleep(0)  # yields to the browser event loop; a no-op on desktop

    @staticmethod
    def result_for(option):
        if option == MODE_ADAPTIVE:
            return MODE_ADAPTIVE, "N5"   # the tutor starts gentle and climbs fast if you're good
        if option == MODE_RANDOM:
            return MODE_RANDOM, "N5"
        return MODE_CHOOSE, option

    # -- Input -------------------------------------------------------------------

    def _select(self, index):
        index %= len(OPTIONS)
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
            if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                self._select(self.index - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                self._select(self.index + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._confirm_pick()
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit
        elif event.type == pygame.JOYBUTTONDOWN and event.button in game_input.CONFIRM_BUTTONS:
            self._confirm_pick()
        elif event.type == pygame.JOYHATMOTION and (event.value[0] or event.value[1]):
            self._select(self.index + (event.value[0] or -event.value[1]))
        elif event.type == pygame.JOYAXISMOTION and event.axis in (0, 1):
            direction = 0 if abs(event.value) < game_input.AXIS_DEADZONE else (1 if event.value > 0 else -1)
            if direction and direction != self._stick:
                self._select(self.index + direction)
            self._stick = direction
        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            for i, rect in enumerate(self._rows):
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
        setup_ui.draw_steps(screen, 3)
        setup_ui.draw_title(screen, "CHOOSE YOUR LEVEL", "レベルを えらぼう")
        option = OPTIONS[self.index]
        self._draw_stage(option)
        self._draw_list()
        self._draw_sample(option)
        flash = max(0.0, 1 - self.confirming / CONFIRM_SECONDS) if self.confirming is not None else 0.0
        self._confirm = setup_ui.confirm_button(screen, "START", self.time, flash)
        setup_ui.hints(screen, [("↑↓", "choose"), ("Enter", "start"), ("Esc", "quit")],
                       [(setup_ui.DPAD, "choose"), ("pad-a", "start")])
        pygame.display.flip()

    def _draw_stage(self, option):
        screen, stage = self.screen, setup_ui.STAGE
        ui.panel(screen, stage, bg=setup_ui.STAGE_BG, radius=16)
        color = LEVEL_COLORS[option]
        floor = setup_ui.spotlight(screen, stage, color, self.time)
        bob = round(5 * math.sin(self.time * 2.2))
        pitch = PITCH[option]
        if self.confirming is not None:
            expression = "happy"
        elif self.typed < len(pitch):
            expression = "talking"
        else:
            expression = "happy" if (self.time % 2.6) < 0.35 else "idle"
        draw_companion(screen, self.companion["id"], stage.centerx, floor - 80 + bob, 120, expression=expression)
        code, _ = LABELS.get(option, (option, None))
        ui.text(screen, code, ui.title_font(28), (stage.centerx, floor + 1), color=color, anchor="center", thickness=2)
        # The companion's take on the highlighted choice, typed out.
        font = ui.body_font(16)
        bubble = pygame.Rect(stage.x + 16, stage.y + 14, stage.width - 32, 74)
        pygame.draw.rect(screen, ui.OUTLINE, bubble.inflate(4, 4), border_radius=14)
        pygame.draw.rect(screen, (252, 246, 232), bubble, border_radius=12)
        tail = [(stage.centerx - 10, bubble.bottom - 1), (stage.centerx + 10, bubble.bottom - 1),
                (stage.centerx, bubble.bottom + 12)]
        pygame.draw.polygon(screen, (252, 246, 232), tail)
        pygame.draw.lines(screen, ui.OUTLINE, False, [tail[0], tail[2], tail[1]], 2)
        y = bubble.y + 10
        for line in setup_ui.wrap(pitch[:int(self.typed)], font, bubble.width - 28)[:3]:
            screen.blit(font.render(line, True, (40, 30, 46)), (bubble.x + 14, y))
            y += 21

    def _draw_list(self):
        screen, card = self.screen, setup_ui.CARD
        ui.panel(screen, card, bg=setup_ui.CARD_BG, radius=16)
        self._rows = []
        y = card.y + 12
        for i, opt in enumerate(OPTIONS):
            if opt == MODE_ADAPTIVE:     # a divider between the fixed levels and the two modes
                pygame.draw.line(screen, (80, 70, 110), (card.x + 20, y + 2), (card.right - 20, y + 2), 1)
                y += 6
            rect = pygame.Rect(card.x + 14, y, card.width - 28, ROW_H - 4)
            self._rows.append(rect)
            selected = i == self.index
            color = LEVEL_COLORS[opt]
            if selected:
                pygame.draw.rect(screen, (52, 42, 80), rect, border_radius=10)
                pygame.draw.rect(screen, ui.GOLD, rect, width=2, border_radius=10)
            code, name = LABELS.get(opt, (opt, JLPT_DESCRIPTIONS.get(opt)))
            chip = pygame.Rect(rect.x + 8, rect.y + 4, 46, rect.height - 8)
            pygame.draw.rect(screen, color if selected else tuple(round(c * 0.55) for c in color), chip,
                             border_radius=8)
            ui.text(screen, code, ui.label_font(16), chip.center, color=ui.OUTLINE, outline=None, anchor="center")
            ui.text(screen, name, ui.body_font(18), (chip.right + 14, rect.centery),
                    color=ui.CREAM if selected else ui.MUTED, anchor="midleft", thickness=1)
            if opt == MODE_ADAPTIVE:
                tag, font = "RECOMMENDED", ui.label_font(16)
                pill = pygame.Rect(0, 0, font.size(tag)[0] + 16, 20)
                pill.midright = (rect.right - 10, rect.centery)
                pygame.draw.rect(screen, (90, 60, 150), pill, border_radius=10)
                ui.text(screen, tag, font, pill.center, color=ui.CREAM, outline=None, anchor="center")
            elif opt in JLPT_LEVELS:     # difficulty, as 1-5 stars
                stars = JLPT_LEVELS.index(opt) + 1
                for k in range(5):
                    setup_ui.star(screen, (rect.right - 82 + k * 16, rect.centery), 6,
                                  color if k < stars else (70, 62, 92))
            y += ROW_H

    def _draw_sample(self, option):
        screen = self.screen
        strip = pygame.Rect(36, setup_ui.ROSTER_Y + 4, setup_ui.CONFIRM.x - 36 - 20, setup_ui.ROSTER_H - 8)
        ui.panel(screen, strip, bg=(24, 20, 40, 225), edge=(*LEVEL_COLORS[option], 200), radius=12)
        label = "HOW IT WORKS" if option in (MODE_ADAPTIVE, MODE_RANDOM) else "SAMPLE WORDS"
        ui.text(screen, label, ui.label_font(16), (strip.x + 14, strip.y + 9), color=LEVEL_COLORS[option])
        font = ui.body_font(17)
        lines = setup_ui.wrap(_sample(option), font, strip.width - 28)
        ui.text(screen, lines[0], font, (strip.x + 14, strip.y + 31), thickness=1)
        if len(lines) > 1:
            ui.text(screen, " ".join(lines[1:]), ui.body_font(14), (strip.x + 14, strip.y + 52), color=ui.MUTED,
                    thickness=1)

import asyncio

import pygame

from kobito import input as game_input
from kobito import setup_ui
from kobito.companion_art import draw_companion
from kobito.companions import get_companion
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, SKY_BLUE
from kobito.difficulty import JLPT_DESCRIPTIONS, JLPT_LEVELS, MODE_ADAPTIVE, MODE_CHOOSE, MODE_RANDOM
from kobito.fonts import get_font

TEXT_COLOR = (30, 30, 30)
HINT_COLOR = (70, 70, 70)
AI_COLOR = (40, 90, 160)

OPTIONS = JLPT_LEVELS + [MODE_ADAPTIVE, MODE_RANDOM]
COMPANION_SIZE = 120


class DifficultySelectScreen:
    """Lets the player choose how questions are picked:

      * a JLPT level, N5 (easiest) to N1 (hardest) -- questions from that
        level, stepping up or down between levels by how it went;
      * AI Adaptive -- the companion adjusts every single question to the
        player: harder when they're on a roll, easier when they're stuck,
        always kept in a comfortable range, with missed questions coming
        back for review (kobito/adaptive.py);
      * Random -- any question from any level, a surprise every time.

    run() returns (mode, starting JLPT level).
    """

    def __init__(self, companion_id="kobito"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your difficulty")
        self.clock = pygame.time.Clock()
        self.companion = get_companion(companion_id)

        self.index = 0
        self.font_title = get_font(40)
        self.font_level = get_font(32)
        self.font_hint = get_font(22)
        self.font_small = get_font(18)
        game_input.get_joysticks()
        self.joy_nav = game_input.MenuNav()
        self.menu_touch = game_input.get_menu_touch_controls(self.screen)

    async def run(self):
        """Blocks until the player confirms, then returns (mode, jlpt_level)."""
        while True:
            self.clock.tick(FPS)
            chosen = self._handle_events()
            if chosen is not None:
                return self.result_for(chosen)
            self._draw()
            await asyncio.sleep(0)  # yields to the browser event loop; a no-op on desktop

    @staticmethod
    def result_for(option):
        if option == MODE_ADAPTIVE:
            return MODE_ADAPTIVE, "N5"   # the tutor starts gentle and climbs fast if you're good
        if option == MODE_RANDOM:
            return MODE_RANDOM, "N5"
        return MODE_CHOOSE, option

    def _move(self, step):
        self.index = (self.index + step) % len(OPTIONS)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            game_input.handle_hotplug(event)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP):
                    self._move(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN):
                    self._move(1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return OPTIONS[self.index]
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit

            action = self.joy_nav.handle_event(event)
            if action == "left":
                self._move(-1)
            elif action == "right":
                self._move(1)
            elif action == "confirm":
                return OPTIONS[self.index]
            elif action == "cancel":
                pygame.quit()
                raise SystemExit

            if self.menu_touch:
                touch_action = self.menu_touch.handle_event(event)
                if touch_action == "left":
                    self._move(-1)
                elif touch_action == "right":
                    self._move(1)
                elif touch_action == "confirm":
                    return OPTIONS[self.index]
        return None

    def _draw(self):
        self.screen.fill(SKY_BLUE)
        option = OPTIONS[self.index]
        name = self.companion["name"]

        expression = "happy" if option in (MODE_ADAPTIVE, MODE_RANDOM) else "idle"
        draw_companion(self.screen, self.companion["id"], SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 70, COMPANION_SIZE,
                       expression=expression)

        title = self.font_title.render("Choose your difficulty", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=46))
        setup_ui.draw_steps(self.screen, 3)

        if option == MODE_ADAPTIVE:
            label, color = "AI Adaptive", AI_COLOR
            lines = [f"{name} adjusts every question to you:",
                     "harder when you're on a roll, easier when you're stuck,",
                     "kept in a comfortable range -- and missed ones come back to review."]
        elif option == MODE_RANDOM:
            label, color = "Random", TEXT_COLOR
            lines = ["Any question from N5 to N1 -- a surprise every time."]
        else:
            label, color = f"JLPT {option}", TEXT_COLOR
            lines = [f"{JLPT_DESCRIPTIONS[option]} -- questions from {option},",
                     "stepping up or down between levels by how you do."]

        label_surface = self.font_level.render(label, True, color)
        self.screen.blit(label_surface, label_surface.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 40))
        y = SCREEN_HEIGHT // 2 + 86
        for line in lines:
            surface = self.font_small.render(line, True, HINT_COLOR)
            self.screen.blit(surface, surface.get_rect(centerx=SCREEN_WIDTH // 2, y=y))
            y += 26

        # A row of dots showing every option, the current one filled.
        spacing = 30
        x0 = SCREEN_WIDTH // 2 - spacing * (len(OPTIONS) - 1) // 2
        for i, opt in enumerate(OPTIONS):
            center = (x0 + i * spacing, SCREEN_HEIGHT - 82)
            fill = AI_COLOR if opt == MODE_ADAPTIVE else TEXT_COLOR
            pygame.draw.circle(self.screen, fill, center, 8 if i == self.index else 5, 0 if i == self.index else 2)

        footer = self.font_hint.render("<- / -> to choose    Enter to confirm    Esc to quit", True, HINT_COLOR)
        self.screen.blit(footer, footer.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 55))

        if self.menu_touch:
            self.menu_touch.draw(self.screen)

        pygame.display.flip()

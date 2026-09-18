import asyncio

import pygame

from kobito import input as game_input
from kobito.companion_art import draw_companion
from kobito.companions import get_companion
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, SKY_BLUE
from kobito.difficulty import AI_RANDOM, JLPT_DESCRIPTIONS, JLPT_LEVELS, pick_ai_random_level
from kobito.fonts import get_font

TEXT_COLOR = (30, 30, 30)
HINT_COLOR = (70, 70, 70)

OPTIONS = JLPT_LEVELS + [AI_RANDOM]
COMPANION_SIZE = 120


class DifficultySelectScreen:
    """Lets the player pick a starting JLPT level (N5 easiest -> N1
    hardest), or "AI Random" to have their chosen companion pick one via
    the same Claude call used for hints (kobito/difficulty.py), falling
    back to a locally weighted random pick if no credentials/network.

    Always returns a concrete JLPT level string ("N5".."N1") -- the
    AI Random resolution happens here, not downstream.
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
        game_input.get_joysticks()
        self.joy_nav = game_input.MenuNav()
        self.menu_touch = game_input.get_menu_touch_controls(self.screen)

    async def run(self):
        """Blocks until the player confirms, then returns a concrete
        JLPT level string.
        """
        while True:
            self.clock.tick(FPS)
            chosen = self._handle_events()
            if chosen is not None:
                if chosen == AI_RANDOM:
                    self._draw(companion_state="thinking", status=f"{self.companion['name']} is choosing...")
                    return pick_ai_random_level()
                return chosen

            self._draw()
            await asyncio.sleep(0)  # yields to the browser event loop; a no-op on desktop

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            game_input.handle_hotplug(event)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.index = (self.index - 1) % len(OPTIONS)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.index = (self.index + 1) % len(OPTIONS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return OPTIONS[self.index]
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit

            action = self.joy_nav.handle_event(event)
            if action == "left":
                self.index = (self.index - 1) % len(OPTIONS)
            elif action == "right":
                self.index = (self.index + 1) % len(OPTIONS)
            elif action == "confirm":
                return OPTIONS[self.index]
            elif action == "cancel":
                pygame.quit()
                raise SystemExit

            if self.menu_touch:
                touch_action = self.menu_touch.handle_event(event)
                if touch_action == "left":
                    self.index = (self.index - 1) % len(OPTIONS)
                elif touch_action == "right":
                    self.index = (self.index + 1) % len(OPTIONS)
                elif touch_action == "confirm":
                    return OPTIONS[self.index]
        return None

    def _draw(self, companion_state="idle", status=None):
        self.screen.fill(SKY_BLUE)

        option = OPTIONS[self.index]
        is_ai_random = option == AI_RANDOM
        expression = "happy" if is_ai_random else companion_state
        draw_companion(
            self.screen, self.companion["id"], SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60, COMPANION_SIZE,
            expression=expression,
        )

        title = self.font_title.render("Choose your difficulty", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        if is_ai_random:
            name, description = "AI Random", f"Let {self.companion['name']} pick a level for you!"
        else:
            name, description = option, f"JLPT {option} - {JLPT_DESCRIPTIONS[option]}"

        name_label = self.font_level.render(name, True, TEXT_COLOR)
        self.screen.blit(name_label, name_label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 60))

        desc_label = self.font_hint.render(description, True, HINT_COLOR)
        self.screen.blit(desc_label, desc_label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 105))

        position = f"{self.index + 1} / {len(OPTIONS)}"
        position_label = self.font_hint.render(position, True, HINT_COLOR)
        self.screen.blit(position_label, position_label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 90))

        footer_text = status or "<- / -> to choose    Enter to confirm    Esc to quit"
        footer = self.font_hint.render(footer_text, True, HINT_COLOR)
        self.screen.blit(footer, footer.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 55))

        if self.menu_touch:
            self.menu_touch.draw(self.screen)

        pygame.display.flip()

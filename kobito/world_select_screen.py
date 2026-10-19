import asyncio

import pygame

from kobito import input as game_input
from kobito import setup_ui
from kobito.background import Background
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import get_font
from kobito.themes import THEMES

TEXT_COLOR = (255, 255, 255)
TEXT_SHADOW = (20, 20, 20)
HINT_COLOR = (235, 235, 235)

WORLD_ORDER = [
    "forest", "desert", "arabian_night", "underwater", "sky",
    "tokyo", "nagano", "okinawa", "hokkaido", "kyoto",
    "island", "fairy_tale", "london", "new_york", "korea",
]


class WorldSelectScreen:
    """Lets the player pick which themed world to play, showing a live
    preview of that world's actual background (same Background class
    Game uses, just with no camera movement) rather than a static
    thumbnail -- so what you see here is exactly what you'll get.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your world")
        self.clock = pygame.time.Clock()

        self.index = 0
        self.font_title = get_font(40)
        self.font_hint = get_font(22)
        game_input.get_joysticks()
        self.joy_nav = game_input.MenuNav()
        self.menu_touch = game_input.get_menu_touch_controls(self.screen)

        # One preview Background per world, built once up front (same
        # reasoning as SelectScreen preloading animations: switching
        # worlds with left/right should never stutter).
        preview_ground_segments = [(0, SCREEN_WIDTH)]
        self.previews = {
            world_id: Background(SCREEN_WIDTH, SCREEN_HEIGHT - 60, preview_ground_segments, THEMES[world_id])
            for world_id in WORLD_ORDER
        }

    async def run(self):
        """Blocks until the player confirms a world, then returns its id."""
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            chosen_id = self._handle_events()
            if chosen_id is not None:
                return chosen_id

            self.previews[WORLD_ORDER[self.index]].update(dt)
            self._draw()
            await asyncio.sleep(0)  # yields to the browser event loop; a no-op on desktop

    def _handle_events(self):
        for event in game_input.events():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            game_input.handle_hotplug(event)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.index = (self.index - 1) % len(WORLD_ORDER)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.index = (self.index + 1) % len(WORLD_ORDER)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return WORLD_ORDER[self.index]
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit

            action = self.joy_nav.handle_event(event)
            if action == "left":
                self.index = (self.index - 1) % len(WORLD_ORDER)
            elif action == "right":
                self.index = (self.index + 1) % len(WORLD_ORDER)
            elif action == "confirm":
                return WORLD_ORDER[self.index]

            if self.menu_touch:
                touch_action = self.menu_touch.handle_event(event)
                if touch_action == "left":
                    self.index = (self.index - 1) % len(WORLD_ORDER)
                elif touch_action == "right":
                    self.index = (self.index + 1) % len(WORLD_ORDER)
                elif touch_action == "confirm":
                    return WORLD_ORDER[self.index]
        return None

    def _draw(self):
        world_id = WORLD_ORDER[self.index]
        theme = THEMES[world_id]
        self.previews[world_id].draw(self.screen, camera_x=0)

        setup_ui.draw_steps(self.screen, 2)
        self._draw_shadowed_text(theme.name, self.font_title, centerx=SCREEN_WIDTH // 2, y=46)

        position = f"{self.index + 1} / {len(WORLD_ORDER)}"
        self._draw_shadowed_text(position, self.font_hint, centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 90)

        hint = game_input.prompt("<- / -> to choose    Enter to confirm    Esc to quit", "D-pad to choose    A to confirm")
        self._draw_shadowed_text(hint, self.font_hint, centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 55)

        if self.menu_touch:
            self.menu_touch.draw(self.screen)

        pygame.display.flip()

    def _draw_shadowed_text(self, text, font, centerx, y):
        # A drop shadow keeps the title/hint text readable regardless of
        # how bright or busy the world's own background is behind it.
        shadow = font.render(text, True, TEXT_SHADOW)
        self.screen.blit(shadow, shadow.get_rect(centerx=centerx + 2, y=y + 2))
        label = font.render(text, True, TEXT_COLOR)
        self.screen.blit(label, label.get_rect(centerx=centerx, y=y))

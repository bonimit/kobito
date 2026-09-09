import pygame

from kobito.assets import load_character_animations
from kobito.characters import CHARACTERS
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, SKY_BLUE

TEXT_COLOR = (30, 30, 30)
HINT_COLOR = (70, 70, 70)


class SelectScreen:
    """A small, self-contained loop the player sees before Game starts.

    It has its own game loop (events -> update -> draw) just like Game
    does, but its only job is: let the player cycle through mascots
    with left/right and confirm one with Enter. Once that happens it
    returns the chosen character's id and control passes to Game.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your mascot")
        self.clock = pygame.time.Clock()

        self.index = 0
        self.font_title = pygame.font.SysFont(None, 48)
        self.font_hint = pygame.font.SysFont(None, 26)

        # Preload one idle animation per character up front rather than
        # on-demand, so switching characters with left/right never
        # stutters loading a file mid-loop.
        self.idle_animations = {
            character["id"]: load_character_animations(
                character["id"], character["color"], width=64, height=96
            )["idle"]
            for character in CHARACTERS
        }

    def run(self):
        """Blocks until the player confirms a mascot, then returns its id."""
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            chosen_id = self._handle_events()
            if chosen_id is not None:
                return chosen_id

            character = CHARACTERS[self.index]
            animation = self.idle_animations[character["id"]]
            animation.update(dt)

            self._draw(character, animation.current_frame)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.index = (self.index - 1) % len(CHARACTERS)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.index = (self.index + 1) % len(CHARACTERS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return CHARACTERS[self.index]["id"]
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit
        return None

    def _draw(self, character, frame):
        self.screen.fill(SKY_BLUE)

        title = self.font_title.render("Choose your mascot", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=40))

        frame_rect = frame.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        self.screen.blit(frame, frame_rect)

        name = self.font_title.render(character["name"], True, TEXT_COLOR)
        self.screen.blit(name, name.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 90))

        position = f"{self.index + 1} / {len(CHARACTERS)}"
        position_label = self.font_hint.render(position, True, HINT_COLOR)
        self.screen.blit(
            position_label, position_label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 90)
        )

        hint = self.font_hint.render("<- / -> to choose    Enter to confirm    Esc to quit", True, HINT_COLOR)
        self.screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 55))

        pygame.display.flip()

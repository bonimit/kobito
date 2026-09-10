import pygame

from kobito import input as game_input
from kobito.companion_art import draw_companion
from kobito.companions import COMPANIONS
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, SKY_BLUE
from kobito.fonts import get_font

TEXT_COLOR = (30, 30, 30)
TAGLINE_COLOR = (90, 70, 40)
HINT_COLOR = (70, 70, 70)

COMPANION_SIZE = 160
IDLE_BLINK_PERIOD = 2.6  # seconds between a quick blink into "happy" and back


class CompanionSelectScreen:
    """Lets the player pick which AI hint companion accompanies them --
    Kobito or one of its friends (Ushi, Hana, Ume-shu, Kinoko), each
    with its own art and personality (see kobito/companions.py). Same
    self-contained loop shape as SelectScreen (mascot) and
    WorldSelectScreen.

    The chosen companion_id flows into Game -> HintService, so its
    Claude-generated hints come back in that companion's voice, and into
    every screen after this one that shows the companion's portrait
    (DifficultySelectScreen's AI Random pick, QuizScreen's dialogue box).
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your companion")
        self.clock = pygame.time.Clock()

        self.index = 0
        self.font_title = get_font(40)
        self.font_name = get_font(30)
        self.font_tagline = get_font(20)
        self.font_hint = get_font(22)
        game_input.get_joysticks()
        self.joy_nav = game_input.MenuNav()

        # A soft blink into "happy" every couple seconds is enough to
        # make the still portrait feel alive without needing a full
        # idle animation loop like the mascots have.
        self._blink_timer = 0.0

    def run(self):
        """Blocks until the player confirms a companion, then returns its id."""
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            chosen_id = self._handle_events()
            if chosen_id is not None:
                return chosen_id

            self._blink_timer = (self._blink_timer + dt) % IDLE_BLINK_PERIOD
            self._draw()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            game_input.handle_hotplug(event)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.index = (self.index - 1) % len(COMPANIONS)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.index = (self.index + 1) % len(COMPANIONS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return COMPANIONS[self.index]["id"]
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit

            action = self.joy_nav.handle_event(event)
            if action == "left":
                self.index = (self.index - 1) % len(COMPANIONS)
            elif action == "right":
                self.index = (self.index + 1) % len(COMPANIONS)
            elif action == "confirm":
                return COMPANIONS[self.index]["id"]
            elif action == "cancel":
                pygame.quit()
                raise SystemExit
        return None

    def _draw(self):
        self.screen.fill(SKY_BLUE)

        companion = COMPANIONS[self.index]
        expression = "happy" if self._blink_timer < 0.3 else "idle"
        draw_companion(
            self.screen, companion["id"], SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30, COMPANION_SIZE,
            expression=expression,
        )

        title = self.font_title.render("Choose your companion", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        name = self.font_name.render(companion["name"], True, TEXT_COLOR)
        self.screen.blit(name, name.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 90))

        tagline = self.font_tagline.render(companion["tagline"], True, TAGLINE_COLOR)
        self.screen.blit(tagline, tagline.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 130))

        position = f"{self.index + 1} / {len(COMPANIONS)}"
        position_label = self.font_hint.render(position, True, HINT_COLOR)
        self.screen.blit(
            position_label, position_label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 90)
        )

        hint = self.font_hint.render("<- / -> to choose    Enter to confirm    Esc to quit", True, HINT_COLOR)
        self.screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 55))

        pygame.display.flip()

import pygame

from kobito import input as game_input
from kobito.companion_art import draw_companion
from kobito.companions import COMPANIONS
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, SKY_BLUE
from kobito.fonts import get_font

TEXT_COLOR = (30, 30, 30)
TAGLINE_COLOR = (90, 70, 40)
HINT_COLOR = (70, 70, 70)
ABILITY_LABEL_COLOR = (30, 100, 60)
ABILITY_TEXT_COLOR = (50, 60, 50)
DIM_NAME_COLOR = (110, 110, 118)

CARD_BG = (255, 255, 255, 130)
CARD_BORDER = (255, 255, 255, 200)
SELECTED_BADGE_COLOR = (255, 240, 200, 210)
SELECTED_BORDER_COLOR = (255, 190, 60)

GALLERY_Y = 180
SELECTED_SIZE = 118
UNSELECTED_SIZE = 76
IDLE_BLINK_PERIOD = 2.6  # seconds between a quick blink into "happy" and back


class CompanionSelectScreen:
    """Lets the player pick which AI hint companion accompanies them --
    Kobito or one of its friends (Ushi, Hana, Ume-shu, Kinoko), each
    with its own art, personality, and a small gameplay ability (see
    kobito/companions.py). Same self-contained loop shape as
    SelectScreen (mascot) and WorldSelectScreen.

    Unlike the mascot select screen, all five companions are shown at
    once in a gallery row so the player can compare them side by side;
    left/right moves a highlight between them rather than swapping one
    portrait for another. The highlighted companion's name, tagline,
    and ability are shown in a detail card below the gallery.

    The chosen companion_id flows into Game -> HintService, so its
    Claude-generated hints come back in that companion's voice and its
    ability (see Game._trigger_question) applies for the whole run, and
    into every screen after this one that shows the companion's
    portrait (DifficultySelectScreen's AI Random pick, QuizScreen's
    dialogue box).
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your companion")
        self.clock = pygame.time.Clock()

        self.index = 0
        self.font_title = get_font(36)
        self.font_name = get_font(26)
        self.font_gallery_name = get_font(15)
        self.font_tagline = get_font(18)
        self.font_ability_label = get_font(15)
        self.font_ability_text = get_font(17)
        self.font_hint = get_font(20)
        game_input.get_joysticks()
        self.joy_nav = game_input.MenuNav()

        # A soft blink into "happy" every couple seconds on the
        # selected portrait -- enough to make the gallery feel alive
        # without a full idle animation loop like the mascots have.
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

        title = self.font_title.render("Choose your companion", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=20))

        self._draw_gallery()
        self._draw_detail_card(COMPANIONS[self.index])

        position = f"{self.index + 1} / {len(COMPANIONS)}"
        position_label = self.font_hint.render(position, True, HINT_COLOR)
        self.screen.blit(position_label, position_label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 60))

        hint = self.font_hint.render("<- / -> to compare    Enter to confirm    Esc to quit", True, HINT_COLOR)
        self.screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 32))

        pygame.display.flip()

    def _draw_gallery(self):
        """All five companions in one row, so the player can gauge and
        compare them at a glance rather than clicking through one at a
        time. The selected one is drawn larger, lifted, and ringed.
        """
        slot_width = SCREEN_WIDTH / len(COMPANIONS)
        for i, companion in enumerate(COMPANIONS):
            center_x = round(slot_width * (i + 0.5))
            selected = i == self.index

            if selected:
                size = SELECTED_SIZE
                center_y = GALLERY_Y - 12  # lifted, so it visibly stands out from the row
                expression = "happy" if self._blink_timer < 0.3 else "idle"

                badge_radius = size * 0.62
                badge = pygame.Surface((round(badge_radius * 2), round(badge_radius * 2)), pygame.SRCALPHA)
                pygame.draw.circle(badge, SELECTED_BADGE_COLOR, (badge_radius, badge_radius), badge_radius)
                self.screen.blit(badge, (center_x - badge_radius, center_y - badge_radius))
                pygame.draw.circle(self.screen, SELECTED_BORDER_COLOR, (center_x, center_y), badge_radius, width=3)
            else:
                size = UNSELECTED_SIZE
                center_y = GALLERY_Y
                expression = "idle"

            draw_companion(self.screen, companion["id"], center_x, center_y, size, expression=expression)

            name_color = TEXT_COLOR if selected else DIM_NAME_COLOR
            name_font = self.font_name if selected else self.font_gallery_name
            name_label = name_font.render(companion["name"], True, name_color)
            self.screen.blit(name_label, name_label.get_rect(centerx=center_x, y=GALLERY_Y + 70))

    def _draw_detail_card(self, companion):
        """Tagline and ability for the highlighted companion -- this is
        the "what does picking this one actually do" answer, shown as
        soon as it's highlighted rather than requiring a separate step.
        """
        card = pygame.Rect(0, 0, 560, 130)
        card.centerx = SCREEN_WIDTH // 2
        card.y = 330

        card_surface = pygame.Surface(card.size, pygame.SRCALPHA)
        card_surface.fill(CARD_BG)
        self.screen.blit(card_surface, card.topleft)
        pygame.draw.rect(self.screen, CARD_BORDER, card, width=2, border_radius=10)

        y = card.y + 14
        tagline = self.font_tagline.render(companion["tagline"], True, TAGLINE_COLOR)
        self.screen.blit(tagline, tagline.get_rect(centerx=card.centerx, y=y))
        y += tagline.get_height() + 12

        ability_label = self.font_ability_label.render("ABILITY", True, ABILITY_LABEL_COLOR)
        self.screen.blit(ability_label, ability_label.get_rect(centerx=card.centerx, y=y))
        y += ability_label.get_height() + 4

        ability_line = f"{companion['ability_name']} — {companion['ability_description']}"
        ability_text = self.font_ability_text.render(ability_line, True, ABILITY_TEXT_COLOR)
        if ability_text.get_width() > card.width - 30:
            # Fall back to two lines (name, then description) if the
            # combined line would run past the card's edges.
            name_text = self.font_ability_text.render(companion["ability_name"], True, ABILITY_TEXT_COLOR)
            self.screen.blit(name_text, name_text.get_rect(centerx=card.centerx, y=y))
            y += name_text.get_height() + 2
            desc_text = self.font_ability_text.render(companion["ability_description"], True, ABILITY_TEXT_COLOR)
            self.screen.blit(desc_text, desc_text.get_rect(centerx=card.centerx, y=y))
        else:
            self.screen.blit(ability_text, ability_text.get_rect(centerx=card.centerx, y=y))

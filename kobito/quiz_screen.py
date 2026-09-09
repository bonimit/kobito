import pygame

from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import get_font

DIM_OVERLAY_COLOR = (10, 15, 30, 130)

OUTLINE_COLOR = (46, 30, 15)
FRAME_COLOR = (139, 90, 43)  # matches the ground tiles, for continuity
PANEL_COLOR = (238, 224, 190)  # parchment, warmer than plain white
TEXT_COLOR = (40, 28, 16)
CATEGORY_COLOR = (150, 105, 40)
CHOICE_COLOR = (250, 241, 216)
CORRECT_COLOR = (150, 205, 120)
WRONG_COLOR = (215, 110, 95)
HINT_COLOR = (95, 75, 50)

RESULT_DISPLAY_SECONDS = 1.0
ANSWER_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}


class QuizScreen:
    """A question-block encounter: shows one question, waits for the
    player to press 1-4, briefly highlights right/wrong, then returns
    whether they got it correct.

    Self-contained loop, same shape as SelectScreen and Game: this is
    the pattern for any "pause the main game and show a full screen"
    moment (Kobito hints in Phase 4 will look similar).

    `background` is a snapshot of the level at the moment the question
    block was hit -- drawing that behind a dim overlay (rather than a
    flat color) keeps the quiz feeling like part of the same world
    instead of a separate app screen.
    """

    def __init__(self, screen, question, background=None):
        self.screen = screen
        self.question = question
        self.background = background
        self.clock = pygame.time.Clock()
        self.font_prompt = get_font(28)
        self.font_choice = get_font(24)
        self.font_hint = get_font(18)
        self.font_category = get_font(16)

    def run(self):
        selected = None
        result_timer = 0.0

        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and selected is None:
                    if event.key in ANSWER_KEYS:
                        selected = ANSWER_KEYS[event.key]

            self._draw(selected)

            if selected is not None:
                result_timer += dt
                if result_timer >= RESULT_DISPLAY_SECONDS:
                    return selected == self.question["answer"]

    def _draw(self, selected):
        if self.background is not None:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((25, 25, 40))

        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill(DIM_OVERLAY_COLOR)
        self.screen.blit(dim, (0, 0))

        panel = pygame.Rect(0, 0, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 120)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self._draw_signpost(panel)

        category = self.font_category.render(self.question["category"].upper(), True, CATEGORY_COLOR)
        self.screen.blit(category, (panel.x + 28, panel.y + 20))

        prompt = self.font_prompt.render(self.question["prompt"], True, TEXT_COLOR)
        self.screen.blit(prompt, prompt.get_rect(centerx=panel.centerx, y=panel.y + 56))

        choice_top = panel.y + 140
        choice_height = 52
        choice_gap = 12
        for index, choice_text in enumerate(self.question["choices"]):
            rect = pygame.Rect(
                panel.x + 36,
                choice_top + index * (choice_height + choice_gap),
                panel.width - 72,
                choice_height,
            )
            color = CHOICE_COLOR
            if selected is not None:
                if index == self.question["answer"]:
                    color = CORRECT_COLOR
                elif index == selected:
                    color = WRONG_COLOR

            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, FRAME_COLOR, rect, width=3)

            label = self.font_choice.render(f"{index + 1}. {choice_text}", True, TEXT_COLOR)
            self.screen.blit(label, label.get_rect(x=rect.x + 16, centery=rect.centery))

        if selected is None:
            hint = self.font_hint.render("Press 1-4 to answer", True, HINT_COLOR)
        elif selected == self.question["answer"]:
            hint = self.font_hint.render("Correct!", True, TEXT_COLOR)
        else:
            hint = self.font_hint.render(self.question.get("explanation", "Not quite."), True, TEXT_COLOR)
        self.screen.blit(hint, hint.get_rect(centerx=panel.centerx, y=panel.bottom - 34))

        pygame.display.flip()

    def _draw_signpost(self, panel):
        """A blocky, layered wood-and-parchment frame instead of a
        rounded UI card, to read as an in-world signpost rather than a
        generic app dialog.
        """
        pygame.draw.rect(self.screen, OUTLINE_COLOR, panel.inflate(16, 16))
        pygame.draw.rect(self.screen, FRAME_COLOR, panel.inflate(8, 8))
        pygame.draw.rect(self.screen, PANEL_COLOR, panel)

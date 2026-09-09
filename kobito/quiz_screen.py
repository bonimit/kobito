import pygame

from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import get_font

BG_COLOR = (25, 25, 40)
PANEL_COLOR = (245, 240, 225)
TEXT_COLOR = (30, 30, 30)
CATEGORY_COLOR = (150, 120, 60)
CHOICE_COLOR = (255, 255, 255)
CHOICE_BORDER = (90, 90, 90)
CORRECT_COLOR = (140, 210, 140)
WRONG_COLOR = (225, 120, 120)
HINT_COLOR = (100, 100, 100)

RESULT_DISPLAY_SECONDS = 1.0
ANSWER_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}


class QuizScreen:
    """A question-block encounter: shows one question, waits for the
    player to press 1-4, briefly highlights right/wrong, then returns
    whether they got it correct.

    Self-contained loop, same shape as SelectScreen and Game: this is
    the pattern for any "pause the main game and show a full screen"
    moment (Kobito hints in Phase 4 will look similar).
    """

    def __init__(self, screen, question):
        self.screen = screen
        self.question = question
        self.clock = pygame.time.Clock()
        self.font_prompt = get_font(30)
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
        self.screen.fill(BG_COLOR)

        panel = pygame.Rect(0, 0, SCREEN_WIDTH - 120, SCREEN_HEIGHT - 100)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel, border_radius=12)

        category = self.font_category.render(self.question["category"].upper(), True, CATEGORY_COLOR)
        self.screen.blit(category, (panel.x + 30, panel.y + 22))

        prompt = self.font_prompt.render(self.question["prompt"], True, TEXT_COLOR)
        self.screen.blit(prompt, prompt.get_rect(centerx=panel.centerx, y=panel.y + 60))

        choice_top = panel.y + 150
        choice_height = 54
        choice_gap = 14
        for index, choice_text in enumerate(self.question["choices"]):
            rect = pygame.Rect(
                panel.x + 40,
                choice_top + index * (choice_height + choice_gap),
                panel.width - 80,
                choice_height,
            )
            color = CHOICE_COLOR
            if selected is not None:
                if index == self.question["answer"]:
                    color = CORRECT_COLOR
                elif index == selected:
                    color = WRONG_COLOR

            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, CHOICE_BORDER, rect, width=2, border_radius=8)

            label = self.font_choice.render(f"{index + 1}. {choice_text}", True, TEXT_COLOR)
            self.screen.blit(label, label.get_rect(x=rect.x + 16, centery=rect.centery))

        if selected is None:
            hint = self.font_hint.render("Press 1-4 to answer", True, HINT_COLOR)
        elif selected == self.question["answer"]:
            hint = self.font_hint.render("Correct!", True, TEXT_COLOR)
        else:
            hint = self.font_hint.render(self.question.get("explanation", "Not quite."), True, TEXT_COLOR)
        self.screen.blit(hint, hint.get_rect(centerx=panel.centerx, y=panel.bottom - 36))

        pygame.display.flip()

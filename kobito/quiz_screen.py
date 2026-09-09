import pygame

from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import get_font

BOX_COLOR = (12, 12, 16, 220)
BOX_BORDER = (230, 230, 230)
TEXT_COLOR = (240, 240, 240)
CATEGORY_COLOR = (200, 175, 110)
CORRECT_COLOR = (140, 220, 140)
WRONG_COLOR = (235, 120, 110)
HINT_COLOR = (180, 180, 180)

BOX_WIDTH = 360
BOX_PADDING = 14
LINE_GAP = 4
CHOICE_HEIGHT = 24
GAP_TO_ANCHOR = 10
SCREEN_MARGIN = 10

RESULT_DISPLAY_SECONDS = 1.0
ANSWER_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}


class QuizScreen:
    """A question-block encounter: a small black box next to the block
    itself shows the question, waits for the player to press 1-4,
    briefly highlights right/wrong, then returns whether they got it
    correct.

    Self-contained loop, same shape as SelectScreen and Game. Unlike a
    full-screen dialog, the rest of the level stays fully visible and
    undimmed behind the box -- it's a callout next to the block, not a
    takeover.
    """

    def __init__(self, screen, question, background=None, anchor_rect=None):
        self.screen = screen
        self.question = question
        self.background = background
        self.anchor_rect = anchor_rect or pygame.Rect(SCREEN_WIDTH // 2, 80, 1, 1)
        self.clock = pygame.time.Clock()
        self.font_prompt = get_font(18)
        self.font_choice = get_font(16)
        self.font_hint = get_font(14)
        self.font_category = get_font(13)

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

        prompt_lines = self._wrap_text(self.question["prompt"], self.font_prompt, BOX_WIDTH - 2 * BOX_PADDING)
        hint_text = self._hint_text(selected)
        hint_lines = self._wrap_text(hint_text, self.font_hint, BOX_WIDTH - 2 * BOX_PADDING) if hint_text else []

        content_height = (
            self.font_category.get_height() + LINE_GAP
            + len(prompt_lines) * (self.font_prompt.get_height() + LINE_GAP)
            + len(self.question["choices"]) * (CHOICE_HEIGHT + LINE_GAP)
            + len(hint_lines) * (self.font_hint.get_height() + LINE_GAP)
        )
        box_height = content_height + 2 * BOX_PADDING
        box = self._position_box(BOX_WIDTH, box_height)

        box_surface = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        box_surface.fill(BOX_COLOR)
        self.screen.blit(box_surface, box.topleft)
        pygame.draw.rect(self.screen, BOX_BORDER, box, width=1)

        y = box.y + BOX_PADDING
        x = box.x + BOX_PADDING

        category = self.font_category.render(self.question["category"].upper(), True, CATEGORY_COLOR)
        self.screen.blit(category, (x, y))
        y += category.get_height() + LINE_GAP

        for line in prompt_lines:
            surface = self.font_prompt.render(line, True, TEXT_COLOR)
            self.screen.blit(surface, (x, y))
            y += surface.get_height() + LINE_GAP

        for index, choice_text in enumerate(self.question["choices"]):
            color = TEXT_COLOR
            if selected is not None:
                if index == self.question["answer"]:
                    color = CORRECT_COLOR
                elif index == selected:
                    color = WRONG_COLOR
            label = self.font_choice.render(f"{index + 1}. {choice_text}", True, color)
            self.screen.blit(label, (x, y))
            y += CHOICE_HEIGHT + LINE_GAP

        for line in hint_lines:
            surface = self.font_hint.render(line, True, HINT_COLOR)
            self.screen.blit(surface, (x, y))
            y += surface.get_height() + LINE_GAP

        pygame.display.flip()

    def _hint_text(self, selected):
        if selected is None:
            return "Press 1-4 to answer"
        if selected == self.question["answer"]:
            return "Correct!"
        return self.question.get("explanation", "Not quite.")

    def _position_box(self, width, height):
        box = pygame.Rect(0, 0, width, height)
        box.centerx = self.anchor_rect.centerx
        box.centerx = max(SCREEN_MARGIN + width // 2, min(box.centerx, SCREEN_WIDTH - SCREEN_MARGIN - width // 2))

        room_above = self.anchor_rect.top - GAP_TO_ANCHOR - SCREEN_MARGIN
        if room_above >= height:
            box.bottom = self.anchor_rect.top - GAP_TO_ANCHOR
        else:
            box.top = self.anchor_rect.bottom + GAP_TO_ANCHOR
        box.top = max(SCREEN_MARGIN, min(box.top, SCREEN_HEIGHT - SCREEN_MARGIN - height))
        return box

    def _wrap_text(self, text, font, max_width):
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

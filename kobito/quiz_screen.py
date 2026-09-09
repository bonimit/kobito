import pygame

from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import get_font

BOX_COLOR = (18, 18, 30, 175)  # translucent, not flat opaque -- lets the scene show through
BOX_BORDER = (230, 230, 230)
TEXT_COLOR = (240, 240, 240)
CATEGORY_COLOR = (200, 175, 110)
CORRECT_COLOR = (140, 220, 140)
WRONG_COLOR = (235, 120, 110)
HINT_COLOR = (180, 180, 180)

BOX_WIDTH = 340
BOX_PADDING = 14
LINE_GAP = 4
CHOICE_HEIGHT = 24
GAP_TO_ANCHOR = 12
SCREEN_MARGIN = 10
TAIL_SIZE = 9

RESULT_DISPLAY_SECONDS = 1.0
ANSWER_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}


class QuizScreen:
    """A question-block encounter: a small translucent tooltip box pops
    up from the block itself -- with a pointer tail toward it, like a
    speech bubble -- and shows the question. Waits for the player to
    press 1-4, briefly highlights right/wrong, then returns whether
    they got it correct.

    Self-contained loop, same shape as SelectScreen and Game. The rest
    of the level stays fully visible behind the (translucent) box, and
    the box is always positioned so it never covers the block that
    triggered it -- see _position_box.
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
        box, side = self._position_box(BOX_WIDTH, box_height)

        box_surface = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        box_surface.fill(BOX_COLOR)
        self.screen.blit(box_surface, box.topleft)
        pygame.draw.rect(self.screen, BOX_BORDER, box, width=1)
        self._draw_tail(box, side)

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
        """Picks whichever side (above/below/left/right of the block)
        has room for the box, and places it fully on that side --
        never overlapping the block itself. Falls back to whichever
        side has the *most* room if none fits perfectly (only possible
        in extremely cramped corners), still anchored outside the
        block first.
        """
        anchor = self.anchor_rect
        room = {
            "above": anchor.top - SCREEN_MARGIN - GAP_TO_ANCHOR,
            "below": SCREEN_HEIGHT - SCREEN_MARGIN - anchor.bottom - GAP_TO_ANCHOR,
            "left": anchor.left - SCREEN_MARGIN - GAP_TO_ANCHOR,
            "right": SCREEN_WIDTH - SCREEN_MARGIN - anchor.right - GAP_TO_ANCHOR,
        }

        if room["above"] >= height:
            side = "above"
        elif room["below"] >= height:
            side = "below"
        elif room["left"] >= width:
            side = "left"
        elif room["right"] >= width:
            side = "right"
        else:
            side = max(room, key=room.get)

        box = pygame.Rect(0, 0, width, height)
        if side == "above":
            box.midbottom = (anchor.centerx, anchor.top - GAP_TO_ANCHOR)
            box.centerx = self._clamp(box.centerx, SCREEN_MARGIN + width // 2, SCREEN_WIDTH - SCREEN_MARGIN - width // 2)
            box.top = max(box.top, SCREEN_MARGIN)
        elif side == "below":
            box.midtop = (anchor.centerx, anchor.bottom + GAP_TO_ANCHOR)
            box.centerx = self._clamp(box.centerx, SCREEN_MARGIN + width // 2, SCREEN_WIDTH - SCREEN_MARGIN - width // 2)
            box.bottom = min(box.bottom, SCREEN_HEIGHT - SCREEN_MARGIN)
        elif side == "left":
            box.midright = (anchor.left - GAP_TO_ANCHOR, anchor.centery)
            box.centery = self._clamp(box.centery, SCREEN_MARGIN + height // 2, SCREEN_HEIGHT - SCREEN_MARGIN - height // 2)
            box.left = max(box.left, SCREEN_MARGIN)
        else:
            box.midleft = (anchor.right + GAP_TO_ANCHOR, anchor.centery)
            box.centery = self._clamp(box.centery, SCREEN_MARGIN + height // 2, SCREEN_HEIGHT - SCREEN_MARGIN - height // 2)
            box.right = min(box.right, SCREEN_WIDTH - SCREEN_MARGIN)

        return box, side

    def _draw_tail(self, box, side):
        """A small triangle on the box's anchor-facing edge, pointing
        at the block -- the speech-bubble "tail" that makes the box
        read as popping up *from* the block rather than a separate,
        unrelated panel.
        """
        anchor = self.anchor_rect
        if side == "above":
            tip_x = self._clamp(anchor.centerx, box.left + TAIL_SIZE, box.right - TAIL_SIZE)
            points = [(tip_x, box.bottom + TAIL_SIZE), (tip_x - TAIL_SIZE, box.bottom), (tip_x + TAIL_SIZE, box.bottom)]
        elif side == "below":
            tip_x = self._clamp(anchor.centerx, box.left + TAIL_SIZE, box.right - TAIL_SIZE)
            points = [(tip_x, box.top - TAIL_SIZE), (tip_x - TAIL_SIZE, box.top), (tip_x + TAIL_SIZE, box.top)]
        elif side == "left":
            tip_y = self._clamp(anchor.centery, box.top + TAIL_SIZE, box.bottom - TAIL_SIZE)
            points = [(box.right + TAIL_SIZE, tip_y), (box.right, tip_y - TAIL_SIZE), (box.right, tip_y + TAIL_SIZE)]
        else:
            tip_y = self._clamp(anchor.centery, box.top + TAIL_SIZE, box.bottom - TAIL_SIZE)
            points = [(box.left - TAIL_SIZE, tip_y), (box.left, tip_y - TAIL_SIZE), (box.left, tip_y + TAIL_SIZE)]

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        bounds = pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        local_points = [(px - bounds.x, py - bounds.y) for px, py in points]

        tail_surface = pygame.Surface(bounds.size, pygame.SRCALPHA)
        pygame.draw.polygon(tail_surface, BOX_COLOR, local_points)
        self.screen.blit(tail_surface, bounds.topleft)

    def _clamp(self, value, low, high):
        return max(low, min(value, high))

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

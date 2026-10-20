import asyncio
import random
import re

import pygame

from kobito import audio
from kobito import furigana
from kobito import input as game_input
from kobito import ui
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.fonts import get_font
from kobito.companion_art import draw_companion
from kobito.hint_service import HINT_WAIT_SECONDS, HintService

# Matches a parenthetical translation trailing the whole string, e.g.
# "図書館で本を読みます。 (I read books at the library.)" -- but not a
# short reading gloss stuck mid-sentence right after a word, like
# "犬 (inu) means...", which has text following the parenthesis.
TRAILING_TRANSLATION = re.compile(r"^(.*\S)\s*\(([^()]+)\)\s*$")
DETAIL_TRANSLATION_COLOR = (175, 185, 200)

# Furigana / translation are set in the settings screen (Esc); F and T stay
# as quick shortcuts while a question is open.
FURIGANA_KEY = pygame.K_f
TRANSLATION_KEY = pygame.K_t

BOX_COLOR = (16, 18, 32, 238)  # nearly solid, so the question never blends into the scene
BOX_BORDER = (230, 230, 230)
TEXT_COLOR = (240, 240, 240)
CATEGORY_COLOR = (200, 175, 110)
# Each kind of question has its own accent -- the card's border and header
# band -- so vocabulary, kanji, grammar and verbs each look different.
CATEGORY_ACCENTS = {
    "vocabulary": (90, 170, 255),
    "kanji": (240, 96, 80),
    "grammar": (90, 205, 130),
    "verb_conjugation": (185, 125, 245),
    "expression": (250, 190, 70),
    "loanword": (60, 205, 200),
    "reading": (245, 130, 190),
}
HEADER_BAND = 24
CORRECT_COLOR = (140, 220, 140)
WRONG_COLOR = (235, 120, 110)
HINT_COLOR = (180, 180, 180)

BOX_WIDTH = 340
BOX_WIDTH_WIDE = 440    # reading passages, and choices too long for the normal box
BOX_PADDING = 14
FOOTER_H = 24           # the box's bottom row: controls hint + Skip, or "Read more" once answered
PASSAGE_BG = (34, 30, 52)
LINE_GAP = 4
CHOICE_HEIGHT = 24
# Tail and gap are equal on purpose: the tail's tip lands exactly on the
# anchor's edge, so the box reads as touching the block it popped up
# from -- a classic tooltip pointer, not a panel floating nearby.
GAP_TO_ANCHOR = 8
SCREEN_MARGIN = 10
TAIL_SIZE = 8

DETAIL_PANEL_WIDTH = 300
DETAIL_SLIDE_SPEED = 1600.0  # px/second
DETAIL_KEY = pygame.K_r
DETAIL_BG_COLOR = (16, 16, 26, 238)
DETAIL_LABEL_COLOR = (150, 200, 255)
DETAIL_TAB_BG = (30, 30, 44, 220)
DETAIL_TAB_BORDER = (150, 200, 255)

RESULT_DISPLAY_SECONDS = 1.0
REVEAL_BEFORE_HINT_SECONDS = 0.8  # let the wrong-answer highlight register before the companion shows up
ANSWER_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}
CONTINUE_KEYS = (pygame.K_RETURN, pygame.K_SPACE)
# Choosing with a cursor: Up/Down (keyboard, d-pad or stick) moves the
# highlight, Enter/Space or the gamepad's A button answers with it.
CURSOR_UP_KEYS = (pygame.K_UP,)
CURSOR_DOWN_KEYS = (pygame.K_DOWN,)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)
STICK_Y_AXIS = 1
# Ignore confirm presses for a moment after the box opens, so the jump
# that bumped the block can't also pick an answer by accident.
CONFIRM_GRACE_SECONDS = 0.3
# Once a question has been open this long without an answer, the player is
# clearly thinking hard: the companion speaks up with a hint (a nudge, never
# the answer). Claude's hint is requested a few seconds earlier, in the
# background, so it's usually ready right on time; until it arrives (or with
# no API key / offline) the question's own authored hint is shown.
THINKING_PROMPT_SECONDS = 10.0
NUDGE_PREFETCH_SECONDS = 6.0
PROMPT_FLASH_SECONDS = 1.6   # the box flashes gold and shows "!" when it speaks up
SKIP_KEYS = (pygame.K_s,)
SKIP_BUTTON_SIZE = (92, 22)

PHASE_ANSWERING = "answering"
PHASE_REVEAL = "reveal"
PHASE_HINT = "hint"

# The companion's box is a full-width bar that fits exactly in the strip
# under the ground line (y 480-540): nothing is played down there, so it
# never hides the player -- while answering or right after -- and nothing
# overlaps it. Up to 3 lines, shrinking the font a step for a long hint.
RPG_BOX = pygame.Rect(8, 480, SCREEN_WIDTH - 16, 58)
RPG_MAX_LINES = 3
RPG_BOX_COLOR = (15, 15, 15, 175)  # plain translucent black, no border -- classic JRPG textbox
RPG_NAME_COLOR = (255, 210, 110)
RPG_TEXT_COLOR = (245, 245, 245)
RPG_PORTRAIT_SIZE = 44
RPG_MARKER_SPACE = 80   # room on the right for the blinking "Enter ▼"
RPG_CONTINUE_BLINK_MS = 500

# After a wrong answer the companion's box grows into a hint panel: its
# reaction, the right answer, a tip (Claude's, or the question's own), and
# -- with Ume-shu -- why. Its top can reach HINT_TOP, so the question box
# always stays above that line (no jumping when the panel opens).
HINT_TOP = 378
HINT_TYPE_SPEED = 110.0      # characters per second
TIP_COLOR = (150, 205, 255)
WHY_COLOR = (245, 150, 200)

# Japanese has no spaces, so a run that doesn't fit is broken between
# characters -- but never before closing punctuation / small kana, after
# an opening bracket, or between two kanji (that would split a word, and
# its furigana).
NO_LINE_START = set("、。，．・：；？！?!ー」』）)]}ぁぃぅぇぉっゃゅょァィゥェォッャュョ…")
NO_LINE_END = set("「『（([{")


_last_line = {}     # (companion, pool) -> index of the line said last time


def companion_line(companion, pool, fallback):
    """One of the companion's lines from `pool` ("waiting", "cheers",
    "reactions"), never the same one twice in a row."""
    lines = companion.get(pool) or [fallback]
    key = (companion.get("id"), pool)
    choices = [i for i in range(len(lines)) if i != _last_line.get(key)] or [0]
    index = random.choice(choices)
    _last_line[key] = index
    return lines[index]


def _kanji(ch):
    return "一" <= ch <= "鿿" or ch == "々"


def _break_at(prefix, rest, font, max_width):
    """How many characters of `rest` to put on a line after `prefix`."""
    fit = 0
    while fit < len(rest) and font.size(prefix + rest[:fit + 1])[0] <= max_width:
        fit += 1
    for k in range(fit, 0, -1):
        if k == len(rest):
            return k
        if rest[k] in NO_LINE_START or rest[k - 1] in NO_LINE_END or (_kanji(rest[k - 1]) and _kanji(rest[k])):
            continue
        return k
    return fit


def wrap_text(text, font, max_width):
    """Word-wraps `text` to `max_width` pixels, breaking long Japanese runs
    between characters where Japanese allows it."""
    lines, current = [], ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue
        if current and font.size(word)[0] <= max_width:
            lines.append(current)
            current = word
            continue
        prefix, rest = (f"{current} " if current else ""), word
        while rest:
            if font.size(prefix + rest)[0] <= max_width:
                break
            k = _break_at(prefix, rest, font, max_width)
            if k == 0:
                if prefix:          # nothing more fits on this line: start the next
                    lines.append(prefix.rstrip())
                    prefix = ""
                    continue
                k = 1
            lines.append(prefix + rest[:k])
            prefix, rest = "", rest[k:]
        current = prefix + rest
    if current:
        lines.append(current)
    return lines or [""]


class QuizScreen:
    """A question-block encounter: a small translucent tooltip box pops
    up from the block itself -- with a pointer tail toward it, like a
    speech bubble -- and shows the question. The player picks a choice
    with the highlight (Up/Down + Enter, or d-pad/stick + A), with 1-4 as
    a quick pick, or by tapping/clicking it; then right/wrong is shown.

    On a wrong answer, the player's chosen AI companion (see
    kobito/companions.py) shows up next to the box with its own speech
    bubble holding a short, encouraging hint -- generated by Claude
    (kobito/hint_service.py), or a local fallback hint if no API
    credentials are configured or the request fails. The player presses
    Enter/Space to dismiss it.

    Once an answer is locked in (right or wrong), pressing R slides in a
    "Read more" detail panel from the right edge of the screen with the
    full explanation, the authored hint, and the correct choice spelled
    out -- for whenever the question itself or the companion's hint
    wasn't enough on its own. It never appears before an answer is
    picked, so it can't spoil the question.

    While answering, the player can also pass: S, a gamepad shoulder button
    or Start, or the on-screen Skip button ends the quiz with no answer --
    run() then returns None (True/False are right/wrong).

    Self-contained loop, same shape as SelectScreen and Game. The rest
    of the level stays fully visible behind the (translucent) box, and
    the box is always positioned so it never covers the block that
    triggered it -- see _position_box.
    """

    def __init__(
        self, screen, question, background=None, anchor_rect=None, hint_service=None, points=None, penalty=None,
        title=None,
    ):
        self.screen = screen
        self.question = question
        self.title = title        # e.g. "TEST 3/12", shown first in the header
        self.selected = None      # the choice the player picked (None if skipped)
        self.background = background
        self.anchor_rect = anchor_rect or pygame.Rect(SCREEN_WIDTH // 2, 80, 1, 1)
        self.hint_service = hint_service or HintService()
        # What this block is worth, and what missing it costs -- shown
        # up front so the player can see that a harder level pays more
        # and stings more, rather than having to infer it.
        self.points = points
        self.penalty = penalty
        self.clock = pygame.time.Clock()
        game_input.get_joysticks()
        self.font_prompt = get_font(18)
        self.font_choice = get_font(16)
        self.font_hint = get_font(14)
        self.font_category = get_font(13)
        self.font_companion = ui.body_font(16)
        self.font_dialogue_small = ui.body_font(14)
        self.font_hint_panel = ui.body_font(16)
        self.font_detail_title = get_font(20)
        self.font_detail_label = get_font(14)
        self.font_detail_body = get_font(15)
        self.font_ruby = get_font(10)

        # Furigana asks whether the current question's kanji is fair
        # game to annotate at all -- a "kanji" category question is
        # literally asking for the reading, so showing it would hand
        # over the answer regardless of the player's furigana setting.
        self.suppress_furigana = question.get("category") == "kanji"
        self._detail_rect = None
        self._hint_started = None   # when the hint panel opened (seconds since the box did)
        self._reaction = None       # picked when the answer turns out wrong
        self._cheer = None          # ...or right
        self._waiting = companion_line(self.hint_service.companion, "waiting", "Take your time!")
        widest = max(self.font_choice.size(f"4. {c}")[0] for c in question["choices"])
        self.box_width = (BOX_WIDTH_WIDE if question.get("category") == "reading"
                          or widest > BOX_WIDTH - 2 * BOX_PADDING else BOX_WIDTH)

        # Read-more panel state: starts fully off-screen (panel_x ==
        # SCREEN_WIDTH) and slides left/right toward whichever edge
        # show_details currently points at -- see _update_detail_panel.
        self.show_details = False
        self.panel_x = SCREEN_WIDTH

        # Screen-space rect for each choice line, refreshed every _draw
        # call -- lets a tap/click (web build only) select an answer by
        # hitting the line itself, since the box's position moves around
        # the anchor block and there's nowhere fixed to put buttons.
        self._choice_rects = []
        self._rpg_box_rect = None
        self._skip_rect = None  # the on-screen Skip button, set each _draw while answering
        self.cursor = 0           # highlighted choice while answering
        self._stick_y = 0         # last stick direction, so a held stick moves once
        self._age = 0.0           # seconds since the box opened
        self.prompted_at = None   # when the companion spoke up (seconds since opening)
        self._nudge_requested = False
        self._nudge_request = None  # the AI's answer, arriving in the background

    @property
    def prompted(self):
        return self.prompted_at is not None

    def _request_nudge(self):
        """Asks the AI for a hint in the background, so the quiz never waits on
        the network. No AI set up simply means the authored hint is used."""
        self._nudge_requested = True
        service = self.hint_service
        if not getattr(service, "available", False) or not hasattr(service, "start_nudge"):
            return
        self._nudge_request = service.start_nudge(self.question)

    def _nudge_text(self):
        request = self._nudge_request
        ai = request.text if request is not None and request.done else None
        return (ai or self.question.get("hint")
                or "Read it once more, slowly -- the answer is in the details.")

    def move_cursor(self, step):
        self.cursor = (self.cursor + step) % len(self.question["choices"])
        audio.play("select")

    async def run(self):
        phase = PHASE_ANSWERING
        selected = None
        reveal_timer = 0.0
        hint_text = None

        self.clock.tick()  # start timing now, not from when the screen was built
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._age += dt
            can_confirm = self._age >= CONFIRM_GRACE_SECONDS
            if phase == PHASE_ANSWERING:
                if self._age >= NUDGE_PREFETCH_SECONDS and not self._nudge_requested:
                    self._request_nudge()
                if self._age >= THINKING_PROMPT_SECONDS and self.prompted_at is None:
                    self.prompted_at = self._age

            for event in game_input.events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                game_input.handle_hotplug(event)

                if event.type == pygame.KEYDOWN:
                    if phase == PHASE_ANSWERING and event.key in ANSWER_KEYS:
                        selected = ANSWER_KEYS[event.key]
                        self.selected = selected
                        phase = PHASE_REVEAL
                    elif phase == PHASE_ANSWERING and event.key in CURSOR_UP_KEYS:
                        self.move_cursor(-1)
                    elif phase == PHASE_ANSWERING and event.key in CURSOR_DOWN_KEYS:
                        self.move_cursor(1)
                    elif phase == PHASE_ANSWERING and event.key in CONFIRM_KEYS:
                        if can_confirm:
                            selected = self.cursor
                            self.selected = selected
                            phase = PHASE_REVEAL
                    elif phase == PHASE_ANSWERING and event.key in SKIP_KEYS:
                        audio.play("skip")
                        return None  # passed: the question goes unanswered
                    elif phase == PHASE_HINT and event.key in CONTINUE_KEYS:
                        return False
                    elif event.key == DETAIL_KEY and selected is not None:
                        # Only available once an answer is locked in --
                        # the panel spells out the correct choice, so
                        # offering it earlier would spoil the question.
                        self.show_details = not self.show_details
                    elif event.key == FURIGANA_KEY:
                        furigana.toggle()
                    elif event.key == TRANSLATION_KEY:
                        furigana.toggle_translation()

                elif event.type == pygame.JOYBUTTONDOWN:
                    # While answering: d-pad/stick moves the highlight and
                    # A answers with it. Once the companion's hint is
                    # showing, any face button continues.
                    if phase == PHASE_ANSWERING and event.button in game_input.SKIP_BUTTONS:
                        audio.play("skip")
                        return None
                    if phase == PHASE_ANSWERING and event.button in game_input.CONFIRM_BUTTONS:
                        if can_confirm:
                            selected = self.cursor
                            self.selected = selected
                            phase = PHASE_REVEAL
                    elif selected is not None and event.button == game_input.Y:
                        self.show_details = not self.show_details
                    elif phase == PHASE_HINT and event.button in game_input.FACE_BUTTONS:
                        return False
                elif event.type == pygame.JOYHATMOTION and phase == PHASE_ANSWERING and event.value[1]:
                    self.move_cursor(-event.value[1])   # hat y is +1 for up
                elif event.type == pygame.JOYAXISMOTION and event.axis == STICK_Y_AXIS:
                    direction = 0 if abs(event.value) < game_input.AXIS_DEADZONE else (1 if event.value > 0 else -1)
                    if phase == PHASE_ANSWERING and direction and direction != self._stick_y:
                        self.move_cursor(direction)
                    self._stick_y = direction
                elif event.type == pygame.MOUSEMOTION and phase == PHASE_ANSWERING:
                    hovered = self._choice_at(event.pos)
                    if hovered is not None:
                        self.cursor = hovered

                tap_pos = game_input.touch_tap_pos(event)
                if tap_pos is not None and selected is not None and self._detail_rect \
                        and self._detail_rect.collidepoint(tap_pos):
                    self.show_details = not self.show_details
                elif tap_pos is not None:
                    if phase == PHASE_ANSWERING and self._skip_rect and self._skip_rect.collidepoint(tap_pos):
                        audio.play("skip")
                        return None
                    if phase == PHASE_ANSWERING:
                        tapped_choice = self._choice_at(tap_pos)
                        if tapped_choice is not None:
                            selected = tapped_choice
                            self.selected = selected
                            phase = PHASE_REVEAL
                    elif phase == PHASE_HINT and self._rpg_box_rect and self._rpg_box_rect.collidepoint(tap_pos):
                        return False

            if phase == PHASE_REVEAL:
                correct = selected == self.question["answer"]
                if reveal_timer == 0.0:
                    audio.play("correct" if correct else "wrong")
                reveal_timer += dt
                if correct and reveal_timer >= RESULT_DISPLAY_SECONDS:
                    return True
                if not correct and reveal_timer >= REVEAL_BEFORE_HINT_SECONDS:
                    # The companion "thinks" while the AI (if there is one)
                    # writes the hint; the screen keeps drawing, never frozen.
                    hint_text = await self._wait_for_hint(selected, phase)
                    self._open_hint()
                    phase = PHASE_HINT

            self._update_detail_panel(dt)
            self._draw(selected, phase, hint_text=hint_text)
            await asyncio.sleep(0)  # yields to the browser event loop; a no-op on desktop

    async def _wait_for_hint(self, selected, phase):
        service = self.hint_service
        request = service.start_hint(self.question, selected) if getattr(service, "available", False) else None
        waited = 0.0
        while request is not None and not request.done and waited < HINT_WAIT_SECONDS:
            waited += self.clock.tick(FPS) / 1000.0
            for event in game_input.events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
            self._draw(selected, phase, companion_state="thinking")
            await asyncio.sleep(0)
        if request is not None and request.done and request.text:
            return request.text
        if request is None:
            self._draw(selected, phase, companion_state="thinking")
        return service.fallback_hint(self.question) if hasattr(service, "fallback_hint") else service.get_hint(self.question)

    def _update_detail_panel(self, dt):
        target = SCREEN_WIDTH - DETAIL_PANEL_WIDTH if self.show_details else SCREEN_WIDTH
        step = DETAIL_SLIDE_SPEED * dt
        if self.panel_x < target:
            self.panel_x = min(target, self.panel_x + step)
        else:
            self.panel_x = max(target, self.panel_x - step)

    def _open_hint(self):
        self._hint_started = self._age
        if self._reaction is None:
            self._reaction = companion_line(self.hint_service.companion, "reactions", "Not quite!")

    def _split_passage(self, text):
        """A reading question's prompt -> (lead-in, 「passage」, question).
        Other questions -> (None, None, text)."""
        if self.question.get("category") == "reading":
            match = re.match(r"^(.*?)\s*(「.*」)\s*(.*)$", text)
            if match:
                return match.group(1) or None, match.group(2), match.group(3)
        return None, None, text

    def _layout(self, phase):
        """What goes in the box, top to bottom: [(kind, data, height)]."""
        width = self.box_width - 2 * BOX_PADDING
        items = []
        prompt_main, translation = self._split_translation(self.question["prompt"])
        lead, passage, question = self._split_passage(prompt_main)
        if lead:
            items.append(("lead", lead, self.font_hint.get_height() + LINE_GAP))
        if passage:
            lines = wrap_text(passage, self.font_prompt, width - 20)
            height = sum(self._line_height(line, self.font_prompt) + 2 for line in lines) + 14
            items.append(("passage", lines, height + LINE_GAP + 2))
        for line in wrap_text(question, self.font_prompt, width):
            items.append(("prompt", line, self._line_height(line, self.font_prompt) + LINE_GAP))
        if translation and furigana.is_translation_visible():
            for line in wrap_text(translation, self.font_hint, width):
                items.append(("translation", line, self.font_hint.get_height() + LINE_GAP))
        for index, choice in enumerate(self.question["choices"]):
            number = f"{index + 1}. "
            indent = self.font_choice.size(number)[0]
            lines = wrap_text(choice, self.font_choice, width - indent)
            heights = [self._line_height(line, self.font_choice) for line in lines]
            height = max(CHOICE_HEIGHT, sum(heights) + 2 * (len(lines) - 1))
            items.append(("choice", (index, number, indent, lines, heights), height + LINE_GAP))
        items.append(("footer", None, FOOTER_H))
        return items

    def _draw(self, selected, phase, hint_text=None, companion_state="idle"):
        if self.background is not None:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((25, 25, 40))

        items = self._layout(phase)
        box_height = HEADER_BAND + 8 + sum(h for *_, h in items) + BOX_PADDING - 4
        # The question box always stays above the tallest the companion's
        # hint panel can get, so it never moves when the hint opens.
        box, side = self._position_box(self.box_width, box_height, SCREEN_HEIGHT - HINT_TOP)
        self._question_rect = box

        accent = CATEGORY_ACCENTS.get(self.question.get("category"), CATEGORY_COLOR)
        shadow = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=8)
        self.screen.blit(shadow, (box.x + 4, box.y + 5))
        box_surface = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        pygame.draw.rect(box_surface, BOX_COLOR, box_surface.get_rect(), border_radius=8)
        band = pygame.Rect(0, 0, box.width, HEADER_BAND)
        pygame.draw.rect(box_surface, (*[round(c * 0.38) for c in accent], 255), band,
                         border_top_left_radius=8, border_top_right_radius=8)
        self.screen.blit(box_surface, box.topleft)
        pygame.draw.rect(self.screen, accent, box, width=2, border_radius=8)
        self._draw_tail(box, side, accent)

        x = box.x + BOX_PADDING
        category = self.font_category.render(self._header_text(), True, accent)
        self.screen.blit(category, category.get_rect(midleft=(x, box.y + HEADER_BAND // 2)))
        y = box.y + HEADER_BAND + 8

        self._choice_rects = []
        self._skip_rect = self._detail_rect = None
        for kind, data, height in items:
            if kind == "lead":
                self.screen.blit(self.font_hint.render(data, True, HINT_COLOR), (x, y))
            elif kind == "passage":
                block = pygame.Rect(x, y, box.width - 2 * BOX_PADDING, height - LINE_GAP - 2)
                pygame.draw.rect(self.screen, PASSAGE_BG, block, border_radius=6)
                pygame.draw.rect(self.screen, accent, (block.x, block.y, 4, block.height),
                                 border_top_left_radius=6, border_bottom_left_radius=6)
                ly = block.y + 7
                for line in data:
                    ly += self._draw_annotated_line(line, self.font_prompt, block.x + 12, ly, TEXT_COLOR) + 2
            elif kind == "prompt":
                self._draw_annotated_line(data, self.font_prompt, x, y, TEXT_COLOR)
            elif kind == "translation":
                self.screen.blit(self.font_hint.render(data, True, DETAIL_TRANSLATION_COLOR), (x, y))
            elif kind == "choice":
                self._draw_choice(data, x, y, phase, selected, accent, box)
            elif kind == "footer":
                self._draw_footer(box, phase, selected)
            y += height

        if phase == PHASE_ANSWERING:
            if self.prompted:
                self._draw_rpg_dialogue(self._nudge_text(), expression="talking", flash=self._age - self.prompted_at,
                                        chip="TIP")
            else:
                self._draw_rpg_dialogue(self._waiting, expression="happy")
        elif phase == PHASE_HINT:
            self._draw_hint_panel(hint_text)
        elif companion_state == "thinking":
            self._draw_rpg_dialogue("...", expression="thinking", show_continue=False)
        elif phase == PHASE_REVEAL and selected is not None:
            companion = self.hint_service.companion
            if selected == self.question["answer"]:
                if self._cheer is None:
                    self._cheer = companion_line(companion, "cheers", "Correct!")
                gain = f"  +{self.points} XP" if self.points is not None else ""
                self._draw_rpg_dialogue(f"{self._cheer}{gain}", expression="happy", show_continue=False)
            else:
                if self._reaction is None:
                    self._reaction = companion_line(companion, "reactions", "Not quite!")
                loss = f"  -{self.penalty} XP" if self.penalty is not None else ""
                self._draw_rpg_dialogue(f"{self._reaction}{loss}", expression="sympathetic", show_continue=False)

        if self.panel_x < SCREEN_WIDTH:
            self._draw_detail_panel()

        pygame.display.flip()

    def _draw_choice(self, data, x, y, phase, selected, accent, box):
        index, number, indent, lines, heights = data
        color = TEXT_COLOR
        if phase == PHASE_ANSWERING and index == self.cursor:
            # The highlighted choice: just its text, lit up in the question
            # type's colour (brightened so it reads on the card).
            color = tuple(min(255, round(c + (255 - c) * 0.35)) for c in accent)
        if selected is not None:
            if index == self.question["answer"]:
                color = CORRECT_COLOR
            elif index == selected:
                color = WRONG_COLOR
        # Level with the text, below any furigana row over the first line.
        ruby = self.font_ruby.get_height() if self._line_needs_ruby(lines[0]) else 0
        self.screen.blit(self.font_choice.render(number, True, color), (x, y + ruby))
        top = y
        for line, h in zip(lines, heights):
            self._draw_annotated_line(line, self.font_choice, x + indent, y, color)
            y += h + 2
        self._choice_rects.append(pygame.Rect(box.x, top, box.width, max(CHOICE_HEIGHT, y - top)))

    def _draw_footer(self, box, phase, selected):
        """The box's bottom row: how to answer and Skip while answering;
        a "Read more" button once an answer is in."""
        row_y = box.bottom - BOX_PADDING + 4 - FOOTER_H // 2
        x = box.x + BOX_PADDING
        if phase == PHASE_ANSWERING:
            text = self._footer_text(phase, selected)
            self.screen.blit(self.font_hint.render(text, True, HINT_COLOR),
                             self.font_hint.render(text, True, HINT_COLOR).get_rect(midleft=(x, row_y)))
            self._draw_skip_button(box)
        elif selected is not None:
            label = game_input.prompt("R  Read more", "Y  Read more", "Read more")
            if self.show_details:
                label = game_input.prompt("R  Close", "Y  Close", "Close")
            text = self.font_detail_label.render(label, True, DETAIL_LABEL_COLOR)
            rect = pygame.Rect(0, 0, text.get_width() + 18, SKIP_BUTTON_SIZE[1])
            rect.midright = (box.right - BOX_PADDING, row_y)
            pygame.draw.rect(self.screen, DETAIL_TAB_BG, rect, border_radius=6)
            pygame.draw.rect(self.screen, DETAIL_TAB_BORDER, rect, width=1, border_radius=6)
            self.screen.blit(text, text.get_rect(center=rect.center))
            self._detail_rect = rect

    def _draw_hint_panel(self, hint_text):
        """After a wrong answer: the companion's reaction, the right answer,
        a tip -- and for Ume-shu (Deep Insight) the full explanation too --
        typed out in a panel along the bottom."""
        companion = self.hint_service.companion
        font = self.font_hint_panel
        text_x = RPG_BOX.x + 96
        text_w = RPG_BOX.right - 100 - text_x
        answer = self.question["choices"][self.question["answer"]]
        rows = [("name", self._reaction or "Not quite!"), ("answer", f"Answer: {answer}")]
        tip = (hint_text or "").strip()
        explanation = (self.question.get("explanation") or "").strip()
        if tip:
            rows += [("tip" if i == 0 else "tip+", line) for i, line in enumerate(wrap_text(tip, font, text_w - 52)[:3])]
        if companion.get("always_show_explanation") and explanation and explanation != tip:
            rows += [("why" if i == 0 else "why+", line)
                     for i, line in enumerate(wrap_text(explanation, font, text_w - 52)[:2])]
        # Rows with kanji get a furigana line above them when furigana is on
        # (as in the question box); drop trailing tip/why lines that don't fit.
        base_h = font.get_height() + 3
        ruby_h = self.font_ruby.get_height()
        heights = [base_h + (ruby_h if self._line_needs_ruby(text) else 0) for _, text in rows]
        while len(rows) > 3 and 22 + sum(heights) > SCREEN_HEIGHT - 4 - HINT_TOP:
            rows, heights = rows[:-1], heights[:-1]
        row_h = base_h
        height = 22 + sum(heights)
        box = pygame.Rect(RPG_BOX.x, 0, RPG_BOX.width, height)
        box.bottom = SCREEN_HEIGHT - 4
        self._rpg_box_rect = box
        ui.panel(self.screen, box, bg=(14, 12, 26, 240), edge=(*RPG_NAME_COLOR, 200), radius=12)
        draw_companion(self.screen, companion["id"], box.x + 48, box.centery, 64,
                       expression="talking" if self._typing(rows) else "sympathetic")

        shown = int((self._age - (self._hint_started or self._age)) * HINT_TYPE_SPEED)
        y = box.y + 11
        for (kind, text), h in zip(rows, heights):
            ruby = h - base_h          # room for furigana above this row's text
            y += ruby
            x = text_x
            if kind == "name":
                chip = self.font_category.render(companion["name"].upper(), True, (30, 22, 10))
                rect = chip.get_rect(midleft=(x, y + row_h // 2)).inflate(14, 6)
                pygame.draw.rect(self.screen, RPG_NAME_COLOR, rect, border_radius=8)
                self.screen.blit(chip, chip.get_rect(center=rect.center))
                x = rect.right + 10
                color = RPG_TEXT_COLOR
            elif kind == "answer":
                c = (x + 8, y + row_h // 2)
                pygame.draw.lines(self.screen, CORRECT_COLOR, False,
                                  [(c[0] - 6, c[1]), (c[0] - 2, c[1] + 5), (c[0] + 7, c[1] - 5)], 3)
                x += 22
                color = CORRECT_COLOR
            elif kind in ("tip", "why"):
                label, color_ = ("TIP", TIP_COLOR) if kind == "tip" else ("WHY", WHY_COLOR)
                chip = self.font_category.render(label, True, (20, 16, 30))
                rect = pygame.Rect(x, y + 3, 42, row_h - 6)
                pygame.draw.rect(self.screen, color_, rect, border_radius=6)
                self.screen.blit(chip, chip.get_rect(center=rect.center))
                x += 52
                color = RPG_TEXT_COLOR
            else:   # continuation of a tip / why
                x += 52
                color = RPG_TEXT_COLOR
            visible = text[:max(0, shown)]
            shown -= len(text)
            if visible == text and ruby:
                self._draw_annotated_line(text, font, x, y - ruby, color)   # typed out: with furigana
            elif visible:
                self.screen.blit(font.render(visible, True, color), (x, y))
            y += row_h

        if not self._typing(rows) and (pygame.time.get_ticks() // RPG_CONTINUE_BLINK_MS) % 2 == 0:
            self._continue_marker(box.right - 14, box.bottom - 18)

    def _continue_marker(self, right, centery):
        """"Enter ▼" (or "A ▼" / "Tap ▼") -- the triangle drawn, since the
        fonts have no glyph for it."""
        words = self.font_hint_panel.render(game_input.prompt("Enter", "A", "Tap"), True, RPG_TEXT_COLOR)
        tri_x = right - 6
        pygame.draw.polygon(self.screen, RPG_TEXT_COLOR, [(tri_x - 6, centery - 3), (tri_x + 6, centery - 3),
                                                          (tri_x, centery + 5)])
        self.screen.blit(words, words.get_rect(midright=(tri_x - 12, centery)))

    def _typing(self, rows):
        if self._hint_started is None:
            return False
        return (self._age - self._hint_started) * HINT_TYPE_SPEED < sum(len(t) for _, t in rows)

    def _line_needs_ruby(self, text):
        if self.suppress_furigana or not furigana.is_enabled():
            return False
        for word in text.split(" "):
            for _, reading in furigana.annotate_word(word):
                if reading:
                    return True
        return False

    def _line_height(self, text, font, min_height=0):
        height = font.get_height()
        if self._line_needs_ruby(text):
            height += self.font_ruby.get_height()
        return max(height, min_height)

    def _draw_annotated_line(self, text, font, x, y, color):
        """Draws one already-wrapped line at (x, y), annotating kanji
        with furigana when enabled and not suppressed for this
        question's category. Returns the total height consumed
        (including the ruby row above the text, when present) so the
        caller can advance y to the next line.
        """
        if self.suppress_furigana or not furigana.is_enabled():
            surface = font.render(text, True, color)
            self.screen.blit(surface, (x, y))
            return surface.get_height()

        top_offset = self.font_ruby.get_height() if self._line_needs_ruby(text) else 0
        cursor_x = x
        words = text.split(" ")
        for i, word in enumerate(words):
            for chunk, reading in furigana.annotate_word(word):
                surface = font.render(chunk, True, color)
                self.screen.blit(surface, (cursor_x, y + top_offset))
                if reading:
                    ruby_surface = self.font_ruby.render(reading, True, color)
                    ruby_x = cursor_x + (surface.get_width() - ruby_surface.get_width()) // 2
                    self.screen.blit(ruby_surface, (ruby_x, y))
                cursor_x += surface.get_width()
            if i != len(words) - 1:
                space_surface = font.render(" ", True, color)
                self.screen.blit(space_surface, (cursor_x, y + top_offset))
                cursor_x += space_surface.get_width()
        return font.get_height() + top_offset

    def _draw_detail_panel(self):
        """The slide-in "Read more" panel: full explanation, the
        authored hint, and the correct choice spelled out plainly --
        for when the question or the companion's hint alone wasn't
        enough. Anchored to the right edge and only ever open once an
        answer is locked in, so it can never spoil the question.
        """
        panel = pygame.Rect(round(self.panel_x), 0, DETAIL_PANEL_WIDTH, SCREEN_HEIGHT)
        panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        panel_surface.fill(DETAIL_BG_COLOR)
        self.screen.blit(panel_surface, panel.topleft)
        pygame.draw.line(self.screen, DETAIL_TAB_BORDER, panel.topleft, panel.bottomleft, 2)

        x = panel.x + BOX_PADDING
        width = panel.width - 2 * BOX_PADDING
        y = 50

        title = self.font_detail_title.render("Read more", True, (255, 255, 255))
        self.screen.blit(title, (x, y))
        y += title.get_height() + LINE_GAP * 3

        rows = [
            ("QUESTION", self.question["prompt"]),
            ("CORRECT ANSWER", self.question["choices"][self.question["answer"]]),
            ("WHY", self.question.get("explanation") or "(no explanation given)"),
            ("HINT", self.question.get("hint") or "(no hint given)"),
        ]
        for label_text, body_text in rows:
            label_surface = self.font_detail_label.render(label_text, True, DETAIL_LABEL_COLOR)
            self.screen.blit(label_surface, (x, y))
            y += label_surface.get_height() + 2

            main_text, translation = self._split_translation(body_text)
            for line in self._wrap_text(main_text, self.font_detail_body, width):
                y += self._draw_annotated_line(line, self.font_detail_body, x, y, (235, 235, 240)) + 2

            if translation:
                y += 2  # a small gap marks it as a separate line, not a wrapped continuation
                for line in self._wrap_text(f"({translation})", self.font_detail_body, width):
                    surface = self.font_detail_body.render(line, True, DETAIL_TRANSLATION_COLOR)
                    self.screen.blit(surface, (x, y))
                    y += surface.get_height() + 2

            y += LINE_GAP * 3

    def _split_translation(self, text):
        """Splits a trailing "(English translation)" onto its own line
        rather than letting it wrap as a continuation of the Japanese
        sentence before it -- e.g. "図書館で本を読みます。 (I read
        books at the library.)" becomes two separate lines. A short
        mid-sentence reading gloss like "犬 (inu) means..." doesn't
        match (there's text after the parenthesis) and stays as one
        line, since that's a reading, not a translation.

        Returns (main_text, translation_or_None).
        """
        match = TRAILING_TRANSLATION.match(text)
        if match:
            return match.group(1), match.group(2)
        return text, None

    def _header_text(self):
        """e.g. "N3 · GRAMMAR · 20 XP" -- level, topic and stake in one
        line above the question.
        """
        parts = [self.question["jlpt"], self.question["category"].upper().replace("_", " ")]
        if self.title:
            parts.insert(0, self.title)
        if self.points is not None:
            parts.append(f"{self.points} XP")
        return "  ·  ".join(parts)

    def _choice_at(self, pos):
        for index, rect in enumerate(self._choice_rects):
            if rect.collidepoint(pos):
                return index
        return None

    def _draw_skip_button(self, box):
        """A small "Skip" button in the box's bottom-right corner. Passing
        leaves the question unanswered (no XP lost, no hint) -- a level
        holds 30 quiz boxes but the badge only needs 20 answered."""
        rect = pygame.Rect((0, 0), SKIP_BUTTON_SIZE)
        rect.midright = (box.right - BOX_PADDING, box.bottom - BOX_PADDING + 4 - FOOTER_H // 2)
        self._skip_rect = rect
        pygame.draw.rect(self.screen, (60, 60, 82), rect, border_radius=6)
        pygame.draw.rect(self.screen, (170, 170, 190), rect, width=1, border_radius=6)
        label = self.font_hint.render(game_input.prompt("Skip (S)", "Skip (LB)", "Skip"), True, (225, 225, 235))
        self.screen.blit(label, label.get_rect(center=rect.center))

    def _footer_text(self, phase, selected):
        if phase == PHASE_ANSWERING:
            return game_input.prompt("↑↓ choose · Enter answer", "D-pad choose · A answer", "Tap a choice to answer")
        return None  # once answered, the companion's dialogue box carries the message instead

    def _draw_rpg_dialogue(self, text, expression="talking", show_continue=False, flash=None, chip=None):
        """The companion speaking: a full-width bar in the strip under the
        ground line, portrait on the left and its name in gold leading the
        text -- the classic RPG dialogue box, kept slim so it never covers
        the level (or the player) behind the question.
        """
        box = RPG_BOX
        self._rpg_box_rect = box
        # Plain translucent black, no border -- a classic JRPG textbox.
        box_surface = pygame.Surface(box.size, pygame.SRCALPHA)
        box_surface.fill(RPG_BOX_COLOR)
        self.screen.blit(box_surface, box.topleft)
        speaking_up = flash is not None and flash < PROMPT_FLASH_SECONDS
        if speaking_up:
            # The companion just spoke up: the box (which never moves) pulses
            # gold for a moment so the player's eye goes to it.
            pulse = 0.5 + 0.5 * abs(((flash * 3) % 2) - 1)
            edge = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(edge, (*RPG_NAME_COLOR, round(255 * pulse)), edge.get_rect(), width=3)
            self.screen.blit(edge, box.topleft)

        portrait_center = (box.x + 8 + RPG_PORTRAIT_SIZE // 2, box.centery)
        companion = self.hint_service.companion
        draw_companion(
            self.screen, companion["id"], portrait_center[0], portrait_center[1], RPG_PORTRAIT_SIZE,
            expression=expression,
        )
        if speaking_up:
            # A little "!" bubble over the portrait.
            bubble = pygame.Rect(0, 0, 18, 18)
            bubble.center = (portrait_center[0] + RPG_PORTRAIT_SIZE // 2, box.y + 10)
            pygame.draw.ellipse(self.screen, RPG_NAME_COLOR, bubble)
            mark = self.font_category.render("!", True, (30, 22, 10))
            self.screen.blit(mark, mark.get_rect(center=bubble.center))

        text_x = box.x + 8 + RPG_PORTRAIT_SIZE + 12
        text_width = box.right - RPG_MARKER_SPACE - text_x
        chip_w = 50 if chip else 0
        font, lines, name_label = self._fit_dialogue(companion["name"], text or "...", text_width, chip_w)
        line_h = font.get_height() + 1
        # Furigana over kanji when it's on and the text fits in two lines.
        ruby = self.font_ruby.get_height() if len(lines) <= 2 and any(map(self._line_needs_ruby, lines)) else 0
        line_h += ruby
        y = box.y + (box.height - line_h * len(lines)) // 2 + ruby
        for i, line in enumerate(lines):
            x = text_x
            if i == 0:
                self.screen.blit(name_label, (x, y + (line_h - name_label.get_height()) // 2))
                x += name_label.get_width()
                if chip:
                    label = self.font_category.render(chip, True, (20, 16, 30))
                    rect = pygame.Rect(x, y + 2, chip_w - 8, line_h - 4)
                    pygame.draw.rect(self.screen, TIP_COLOR, rect, border_radius=6)
                    self.screen.blit(label, label.get_rect(center=rect.center))
                    x += chip_w
            if ruby and self._line_needs_ruby(line):
                self._draw_annotated_line(line, font, x, y - ruby, RPG_TEXT_COLOR)
            else:
                self.screen.blit(font.render(line, True, RPG_TEXT_COLOR), (x, y))
            y += line_h

        if show_continue and (pygame.time.get_ticks() // RPG_CONTINUE_BLINK_MS) % 2 == 0:
            self._continue_marker(box.right - 12, box.centery)

    def _fit_dialogue(self, name, text, width, first_line_extra=0):
        """Wraps the line -- its first row shortened to make room for the
        companion's name -- at the largest font that fits in
        RPG_MAX_LINES; trims with "..." if even the smallest doesn't."""
        name_label = self.font_category.render(f"{name}  ", True, RPG_NAME_COLOR)
        for font in (self.font_companion, self.font_dialogue_small):
            lines, current, limit = [], "", width - name_label.get_width() - first_line_extra
            for word in text.split(" "):
                candidate = f"{current} {word}".strip()
                if current and font.size(candidate)[0] > limit:
                    lines.append(current)
                    current, limit = word, width
                else:
                    current = candidate
            if current:
                lines.append(current)
            if len(lines) <= RPG_MAX_LINES:
                return font, lines, name_label
        lines = lines[:RPG_MAX_LINES]
        while font.size(lines[-1] + "...")[0] > width and len(lines[-1]) > 1:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "..."
        return font, lines, name_label

    def _position_box(self, width, height, bottom_reserve=0):
        """Picks whichever side (above/below/left/right of the block)
        has room for the box, and places it fully on that side --
        never overlapping the block itself. Falls back to whichever
        side has the *most* room if none fits perfectly (only possible
        in extremely cramped corners), still anchored outside the
        block first.

        `bottom_reserve` keeps the box clear of the companion's RPG dialogue
        box at the bottom of the screen when that's showing (or about
        to).
        """
        anchor = self.anchor_rect
        screen_bottom_limit = SCREEN_HEIGHT - SCREEN_MARGIN - bottom_reserve

        # "above" placement pins the box's *bottom* edge to a fixed point
        # (anchor.top - GAP_TO_ANCHOR) regardless of box height, so unlike
        # every other side it can't be made to fit just by having more
        # room -- if that fixed point already falls inside the reserved
        # area, "above" can never satisfy it and must be disqualified
        # outright (rather than merely deprioritized) so a shorter box
        # doesn't wrongly get placed there.
        above_bottom = anchor.top - GAP_TO_ANCHOR
        above_room = anchor.top - SCREEN_MARGIN - GAP_TO_ANCHOR if above_bottom <= screen_bottom_limit else -1

        room = {
            "above": above_room,
            "below": screen_bottom_limit - anchor.bottom - GAP_TO_ANCHOR,
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
            box.bottom = min(box.bottom, screen_bottom_limit)
        elif side == "left":
            box.midright = (anchor.left - GAP_TO_ANCHOR, anchor.centery)
            box.centery = self._clamp(box.centery, SCREEN_MARGIN + height // 2, screen_bottom_limit - height // 2)
            box.left = max(box.left, SCREEN_MARGIN)
        else:
            box.midleft = (anchor.right + GAP_TO_ANCHOR, anchor.centery)
            box.centery = self._clamp(box.centery, SCREEN_MARGIN + height // 2, screen_bottom_limit - height // 2)
            box.right = min(box.right, SCREEN_WIDTH - SCREEN_MARGIN)

        return box, side

    def _draw_tail(self, box, side, accent=BOX_BORDER):
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
        pygame.draw.polygon(tail_surface, accent, local_points)
        self.screen.blit(tail_surface, bounds.topleft)

    def _clamp(self, value, low, high):
        return max(low, min(value, high))

    def _wrap_text(self, text, font, max_width):
        return wrap_text(text, font, max_width)

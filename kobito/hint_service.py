"""The AI hint companion's brain: asks an AI -- Claude, Gemini or ChatGPT,
directly with the player's own key or through a Kobito AI proxy
(kobito/ai_client.py) -- for a short, encouraging nudge, after a missed
question or when the player has been thinking about one for a while, without
spelling out the answer. Falls back to the question's own authored hint (no
network needed) whenever no AI is set up or the request fails for any reason,
so a hint is always available -- the game must never hang or crash on a
network hiccup during a quiz.

Requests never block: start_hint() / start_nudge() / start() return an
AIRequest straight away and the answer arrives while the game keeps drawing.

The prompt is flavored with whichever companion the player picked (see
kobito/companions.py) so Ushi, Hana, Ume-shu, Kinoko and Kobito each
come back sounding like themselves, not interchangeable narrators.
"""

from kobito import ai_client
from kobito.companions import get_companion

# The hint itself is a sentence or two; leave room for models that think first.
MAX_HINT_TOKENS = 1024
HINT_WAIT_SECONDS = 6.0     # the quiz waits this long for a hint after a wrong answer

FALLBACK_HINTS = {
    "vocabulary": "Try sounding the word out loud -- does its reading remind you of a word you already know?",
    "kanji": "Look at the shape and any radicals in the kanji -- they often hint at the meaning.",
    "grammar": "Think about the job each word is doing in the sentence -- is it the subject, the object, or showing direction?",
    "verb_conjugation": "Check whether it's a ru-verb or an u-verb first -- they follow different conjugation patterns.",
    "expression": "Picture the moment -- who's speaking, and are they arriving, leaving, thanking or apologising?",
    "loanword": "Say the katakana out loud slowly -- it's borrowed from another language, often English.",
    "reading": "Find the key words first -- who, when, where -- then check each answer against the sentence.",
}
DEFAULT_FALLBACK_HINT = "Take another look at the sentence's structure -- you're closer than you think!"


_DEFAULT = object()


class HintService:
    """Safe to construct with nothing configured: every start_* returns None
    and get_hint() gives the local hint."""

    def __init__(self, companion_id="kobito", client=_DEFAULT):
        self.companion = get_companion(companion_id)
        self._client = ai_client.default_client() if client is _DEFAULT else client

    @property
    def available(self):
        return self._client is not None

    @property
    def label(self):
        """CLAUDE / GEMINI / CHATGPT / ONLINE (a proxy), or "" with no AI."""
        return getattr(self._client, "label", "") if self._client is not None else ""

    @property
    def status(self):
        """"none" (no AI set up), "unknown", "checking", "ok" or "down" -- see AIClient.check."""
        return getattr(self._client, "status", "unknown") if self._client is not None else "none"

    @property
    def problem(self):
        return getattr(self._client, "problem", "") if self._client is not None else ""

    def check(self):
        """Starts the background check that tells the truth about whether the AI is working."""
        if self._client is not None and hasattr(self._client, "check"):
            self._client.check()

    def start(self, prompt, max_tokens=MAX_HINT_TOKENS):
        """Sends `prompt`; returns an AIRequest (poll .done / .text), or None with no AI."""
        if self._client is None:
            return None
        return self._client.start(prompt, max_tokens)

    def complete(self, prompt, max_tokens=MAX_HINT_TOKENS):
        """Blocking version (desktop scripts and tests): the answer or None."""
        request = self.start(prompt, max_tokens)
        return request.wait() if request is not None else None

    def start_hint(self, question, chosen_index=None):
        return self.start(self.hint_prompt(question, chosen_index))

    def start_nudge(self, question):
        return self.start(self.nudge_prompt(question))

    def get_hint(self, question, chosen_index=None):
        hint = self.complete(self.hint_prompt(question, chosen_index)) if self._client is not None else None
        return hint or self.fallback_hint(question)

    def get_nudge(self, question):
        """A hint for a player who has been looking at a question for a while
        without answering. None when no AI is set up -- the quiz then shows the
        question's own authored hint."""
        if self._client is None:
            return None
        return self.complete(self.nudge_prompt(question))

    def nudge_prompt(self, question):
        """For a player who has been looking at a question for a while without
        answering: point at the useful clue, never at the answer."""
        correct_choice = question["choices"][question["answer"]]
        lines = [
            "A student learning Japanese has been looking at this quiz question for a while",
            "without answering -- they seem stuck.",
            "",
            f"JLPT level: {question['jlpt']}",
            f"Category: {question['category']}",
            f"Question: {question['prompt']}",
            f"Choices: {', '.join(question['choices'])}",
            f"CORRECT answer (secret -- never reveal it): {correct_choice}",
            f"Why it's correct: {question.get('explanation', '(none given)')}",
        ]
        if question.get("hint"):
            lines.append(f"Reference hint written by the course author: {question['hint']}")
        lines += [
            "",
            f"You are {self.companion['name']}, {self.companion['personality']}.",
            "Gently check in and give ONE short hint (at most 2 sentences) that helps",
            f"them reason it out themselves, pitched at {question['jlpt']} level.",
            "Rules:",
            "- NEVER state, translate, or spell out the correct choice, and never rule",
            "  choices in or out by number.",
            "- Be factually accurate: build only on the explanation above.",
            "- Point at the useful clue (a radical, a particle's role, a stem change, a nuance).",
            "- Start with the clue itself. No filler openers like 'Hmm', 'Tricky one',",
            "  'Looks like you're stuck' or 'Great question' -- the game already shows",
            "  that you're speaking up.",
        ]
        return "\n".join(lines)

    def hint_prompt(self, question, chosen_index=None):
        # The model is given the ground truth (correct choice, the
        # official explanation, and the author's own hint) rather than
        # left to work the answer out from the prompt alone. Without it
        # a hint can confidently point the student the wrong way --
        # accuracy here matters more than novelty, so the model's job is
        # to *reword* known-correct reasoning at the right level, not to
        # solve the question itself.
        correct_choice = question["choices"][question["answer"]]
        lines = [
            "A student learning Japanese just answered this quiz question wrong.",
            "",
            f"JLPT level: {question['jlpt']}",
            f"Category: {question['category']}",
            f"Question: {question['prompt']}",
            f"Choices: {', '.join(question['choices'])}",
            f"CORRECT answer: {correct_choice}",
            f"Why it's correct: {question.get('explanation', '(none given)')}",
        ]
        if question.get("hint"):
            lines.append(f"Reference hint written by the course author: {question['hint']}")
        if chosen_index is not None and 0 <= chosen_index < len(question["choices"]):
            lines.append(f"The student incorrectly chose: {question['choices'][chosen_index]}")
        lines += [
            "",
            f"You are {self.companion['name']}, {self.companion['personality']}.",
            "Give ONE short hint (at most 2 sentences) that guides the student to",
            f"reason out the answer themselves, pitched at {question['jlpt']} level.",
            "Rules:",
            "- NEVER state, translate, or spell out the correct choice.",
            "- Be factually accurate: build only on the explanation above.",
            "- Point at the useful clue (a radical, a particle's role, a stem",
            "  change, a nuance that separates the answer from the distractor).",
            "- If the student's wrong choice reveals a specific misunderstanding,",
            "  gently steer them off it without naming the right answer.",
            "- Start with the clue itself. The game already shows your reaction",
            "  (e.g. 'Ooh, so close!') and the right answer right above your hint, so",
            "  no filler openers like 'Hmm', 'Oops', 'Not quite' or 'Don't worry'.",
        ]
        return "\n".join(lines)

    def fallback_hint(self, question):
        # Every question in the bank ships with a hint written for that
        # exact question, so offline play gets a genuinely useful nudge
        # rather than the generic per-category line. The category and
        # default hints below only cover questions added without one.
        return (
            question.get("hint")
            or FALLBACK_HINTS.get(question["category"])
            or DEFAULT_FALLBACK_HINT
        )

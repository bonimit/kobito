"""The AI hint companion's brain: asks Claude for a short, encouraging
nudge after a missed question, without spelling out the answer. Falls
back to a canned, category-based hint (no network needed) whenever no
API credentials are configured or the request fails for any reason, so
a hint is always available -- the game must never hang or crash on a
network hiccup during a quiz.

The prompt is flavored with whichever companion the player picked (see
kobito/companions.py) so Ushi, Hana, Ume-shu, Kinoko and Kobito each
come back sounding like themselves, not interchangeable narrators.
"""

from kobito.companions import get_companion

MODEL = "claude-opus-5"
MAX_HINT_TOKENS = 200
REQUEST_TIMEOUT_SECONDS = 8.0

FALLBACK_HINTS = {
    "vocabulary": "Try sounding the word out loud -- does its reading remind you of a word you already know?",
    "kanji": "Look at the shape and any radicals in the kanji -- they often hint at the meaning.",
    "grammar": "Think about the job each word is doing in the sentence -- is it the subject, the object, or showing direction?",
    "verb_conjugation": "Check whether it's a ru-verb or an u-verb first -- they follow different conjugation patterns.",
}
DEFAULT_FALLBACK_HINT = "Take another look at the sentence's structure -- you're closer than you think!"


class HintService:
    """Call get_hint(question) any time after a wrong answer. Safe to
    construct even with no API key configured -- it just always falls
    back to a local hint in that case.
    """

    def __init__(self, companion_id="kobito", model=MODEL):
        self.companion = get_companion(companion_id)
        self.model = model
        self._client = self._build_client()

    def _build_client(self):
        try:
            import anthropic
        except ImportError:
            return None

        try:
            return anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SECONDS)
        except Exception:
            # No credentials configured (no ANTHROPIC_API_KEY, no `ant
            # auth login` profile, ...) -- fine, get_hint() just falls
            # back to a local hint below.
            return None

    def get_hint(self, question, chosen_index=None):
        if self._client is not None:
            hint = self._ask_claude(question, chosen_index)
            if hint:
                return hint
        return self._fallback_hint(question)

    def _ask_claude(self, question, chosen_index=None):
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
            "- Speak directly and warmly to the student. No preamble.",
        ]
        prompt = "\n".join(lines)
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=MAX_HINT_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            # Any failure (no network, invalid/expired key, rate limit,
            # timeout, ...) -- fall back rather than let a quiz hang or
            # crash on something outside the player's control.
            return None

        for block in response.content:
            if block.type == "text" and block.text.strip():
                return block.text.strip()
        return None

    def _fallback_hint(self, question):
        # Every question in the bank ships with a hint written for that
        # exact question, so offline play gets a genuinely useful nudge
        # rather than the generic per-category line. The category and
        # default hints below only cover questions added without one.
        return (
            question.get("hint")
            or FALLBACK_HINTS.get(question["category"])
            or DEFAULT_FALLBACK_HINT
        )

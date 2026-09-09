"""Kobito's hint brain: asks Claude for a short, encouraging nudge after
a missed question, without spelling out the answer. Falls back to a
canned, category-based hint (no network needed) whenever no API
credentials are configured or the request fails for any reason, so a
hint is always available -- the game must never hang or crash on a
network hiccup during a quiz.
"""

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

    def __init__(self, model=MODEL):
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

    def get_hint(self, question):
        if self._client is not None:
            hint = self._ask_claude(question)
            if hint:
                return hint
        return self._fallback_hint(question)

    def _ask_claude(self, question):
        prompt = (
            "A student learning Japanese just answered this quiz question wrong.\n"
            f"Category: {question['category']}\n"
            f"Question: {question['prompt']}\n"
            f"Choices: {', '.join(question['choices'])}\n\n"
            "You are Kobito, a small, warm, encouraging forest-spirit companion. "
            "Give ONE short hint (at most 2 sentences) that helps the student "
            "reason toward the answer themselves next time. Do NOT state or "
            "spell out the correct choice. Speak directly and warmly to the "
            "student."
        )
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
        return FALLBACK_HINTS.get(question["category"], DEFAULT_FALLBACK_HINT)

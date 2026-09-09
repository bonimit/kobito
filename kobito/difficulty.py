"""JLPT difficulty selection and progression.

JLPT_LEVELS is ordered easiest -> hardest (N5 is the beginner level,
N1 the most advanced), matching the real JLPT scale.
"""

import random

JLPT_LEVELS = ["N5", "N4", "N3", "N2", "N1"]
JLPT_DESCRIPTIONS = {
    "N5": "Beginner",
    "N4": "Basic",
    "N3": "Intermediate",
    "N2": "Upper Intermediate",
    "N1": "Advanced",
}
AI_RANDOM = "AI_RANDOM"

# Weighted toward beginner levels so a fresh, credential-less player
# doesn't get dropped into N1 by chance -- roughly mirrors what a
# reasonable "surprise me" pick would favor for someone just starting.
AI_RANDOM_FALLBACK_WEIGHTS = [40, 30, 15, 10, 5]

MODEL = "claude-opus-5"
REQUEST_TIMEOUT_SECONDS = 8.0

# Accuracy thresholds for adaptive difficulty between levels.
PROMOTE_ACCURACY = 0.8
DEMOTE_ACCURACY = 0.4


def next_jlpt_level(current_level, correct_count, wrong_count):
    """Given how a level went, returns (next_level, accuracy) for the
    level after it. Answering most questions right steps up to a
    harder JLPT level; answering most wrong steps down to an easier
    one; anything in between holds steady. Clamped to N5..N1.
    """
    total = correct_count + wrong_count
    accuracy = correct_count / total if total else 0.5

    index = JLPT_LEVELS.index(current_level)
    if accuracy >= PROMOTE_ACCURACY and index < len(JLPT_LEVELS) - 1:
        index += 1
    elif accuracy <= DEMOTE_ACCURACY and index > 0:
        index -= 1

    return JLPT_LEVELS[index], accuracy


def pick_ai_random_level():
    """Asks Claude to pick a starting JLPT level, for players who chose
    "AI Random" instead of picking a level themselves. Falls back to a
    locally weighted random pick (see AI_RANDOM_FALLBACK_WEIGHTS) if no
    API credentials are configured or the request fails for any reason
    -- a level is always returned, never blocks indefinitely or crashes.
    """
    try:
        import anthropic

        client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SECONDS)
        response = client.messages.create(
            model=MODEL,
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": (
                    "Pick ONE JLPT level (N5, N4, N3, N2, or N1) for a "
                    "brand-new player starting a Japanese-learning "
                    "platformer game. Reply with ONLY the level code, "
                    "nothing else."
                ),
            }],
        )
        for block in response.content:
            if block.type == "text":
                text = block.text.strip().upper()
                for level in JLPT_LEVELS:
                    if level in text:
                        return level
    except Exception:
        pass

    return random.choices(JLPT_LEVELS, weights=AI_RANDOM_FALLBACK_WEIGHTS)[0]

"""JLPT difficulty selection and progression.

JLPT_LEVELS is ordered easiest -> hardest (N5 is the beginner level,
N1 the most advanced), matching the real JLPT scale.
"""

JLPT_LEVELS = ["N5", "N4", "N3", "N2", "N1"]
JLPT_DESCRIPTIONS = {
    "N5": "Beginner",
    "N4": "Basic",
    "N3": "Intermediate",
    "N2": "Upper Intermediate",
    "N1": "Advanced",
}

# How questions are picked for a run (chosen on the difficulty screen):
MODE_CHOOSE = "choose"       # the player's chosen JLPT level, stepping up/down between levels
MODE_ADAPTIVE = "adaptive"   # the AI tutor adapts every question (kobito/adaptive.py)
MODE_RANDOM = "random"       # any level, at random, every question
MODES = (MODE_CHOOSE, MODE_ADAPTIVE, MODE_RANDOM)

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

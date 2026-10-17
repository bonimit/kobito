import json
import random
from pathlib import Path

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "assets" / "data" / "questions.json"


class QuestionBank:
    def __init__(self, path=QUESTIONS_PATH):
        with open(path, encoding="utf-8") as f:
            self.questions = json.load(f)

    def random_question(self, jlpt=None, exclude=None):
        """A random question at the given JLPT level. Ids in `exclude`
        (questions already asked this level) are skipped, so a level of 30
        quiz blocks never repeats a question; once every question at that
        level has been used, the exclusion is dropped rather than failing.
        """
        pool = self.questions
        if jlpt is not None:
            filtered = [q for q in pool if q["jlpt"] == jlpt]
            pool = filtered or pool  # fall back to the full bank if that level is empty
        if exclude:
            unseen = [q for q in pool if q["id"] not in exclude]
            pool = unseen or pool
        return random.choice(pool)


def shuffled(question, rng=random):
    """A copy of `question` with its choices in a random order (and
    `answer` pointing at the right one's new position) -- so the correct
    choice isn't always in the same slot. The bank itself is untouched."""
    order = list(range(len(question["choices"])))
    rng.shuffle(order)
    copy = dict(question)
    copy["choices"] = [question["choices"][i] for i in order]
    copy["answer"] = order.index(question["answer"])
    return copy

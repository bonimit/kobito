import json
import random
import re
from pathlib import Path

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "assets" / "data" / "questions.json"


_WORD_IN_PROMPT = re.compile(r"([぀-ヿ一-鿿々ー]+)\s*\(([a-z][a-z' ]*)\)")
_cache = {}


def _load(path):
    """The hand-written questions plus the generated ones (built once)."""
    if path not in _cache:
        from kobito import furigana
        from kobito.question_gen import furigana_readings, generate
        with open(path, encoding="utf-8") as f:
            written = json.load(f)
        taught = {m.group(1) for q in written if q["category"] == "vocabulary"
                  for m in [_WORD_IN_PROMPT.search(q["prompt"])] if m}
        for word, reading in furigana_readings().items():
            furigana.READINGS.setdefault(word, reading)
        _cache[path] = written + generate(skip_words=taught)
    return _cache[path]


class QuestionBank:
    """Every question: the hand-written ones in assets/data/questions.json
    and the ones generated from word and verb lists (kobito/question_gen.py)."""

    def __init__(self, path=QUESTIONS_PATH):
        self.questions = list(_load(path))

    def pick(self, jlpt=None, exclude=(), history=(), recent_categories=(), rng=random):
        """The next question to ask, chosen for variety:

          * questions at the given JLPT level, never one already asked this
            level (`exclude`) while others remain;
          * questions not met earlier in the run first (`history`: ids,
            oldest first); once all have been seen, one of the ones seen
            longest ago -- so a new level doesn't replay the last one;
          * a different kind of question from the last ones asked
            (`recent_categories`) -- no three kanji questions in a row --
            whenever an unseen question of another kind is left.
        The kind is picked first (evenly among the kinds that still have
        unseen questions), then a question of that kind -- so the hundreds of
        generated vocabulary questions don't crowd out the rest."""
        pool = self.questions
        if jlpt is not None:
            pool = [q for q in pool if q["jlpt"] == jlpt] or pool
        pool = [q for q in pool if q["id"] not in exclude] or pool
        varied = [q for q in pool if q["category"] not in recent_categories] or pool
        last_seen = {qid: i for i, qid in enumerate(history)}
        # Unseen and a new kind; else unseen (a new question beats a new
        # kind); else the questions seen longest ago.
        for candidates in (varied, pool):
            fresh = [q for q in candidates if q["id"] not in last_seen]
            if fresh:
                kind = rng.choice(sorted({q["category"] for q in fresh}))
                return rng.choice([q for q in fresh if q["category"] == kind])
        kind = rng.choice(sorted({q["category"] for q in varied}))
        oldest = sorted((q for q in varied if q["category"] == kind), key=lambda q: last_seen[q["id"]])
        return rng.choice(oldest[:max(1, len(oldest) // 3)])


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

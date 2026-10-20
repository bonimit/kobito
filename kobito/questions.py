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
        from kobito import jlpt_style
        from kobito.question_gen import generate, teach_furigana
        with open(path, encoding="utf-8") as f:
            written = json.load(f) + jlpt_style.build()
        taught = {m.group(1) for q in written if q["category"] == "vocabulary"
                  for m in [_WORD_IN_PROMPT.search(q["prompt"])] if m}
        _cache[path] = written + generate(skip_words=taught)
        teach_furigana(_cache[path])
    return _cache[path]


DYNAMIC_SHARE = 0.3     # how often the next question is one made up on the spot (kobito/question_dyn.py)


class QuestionBank:
    """Every question: the hand-written ones in assets/data/questions.json
    and the ones generated from word and verb lists (kobito/question_gen.py)."""

    def __init__(self, path=QUESTIONS_PATH):
        self.questions = list(_load(path))

    def get(self, qid, variant=None):
        """A question by id (a saved one coming back): from the bank, or rebuilt if it was made up
        on the spot; `variant` brings back the same fresh roll of its wrong choices."""
        from kobito import question_dyn, question_gen
        if not hasattr(self, "_by_id"):
            self._by_id = {q["id"]: q for q in self.questions}
        question = self._by_id.get(qid) or (question_dyn.rebuild(qid) if str(qid).startswith("dyn_") else None)
        if question is not None and variant is not None:
            question = question_gen.reroll(question, variant)
        return question

    def fresh(self, jlpt, rng=random, count=6, exclude=()):
        """Brand-new questions made up for this level (see kobito/question_dyn.py)."""
        from kobito import question_dyn
        return question_dyn.fresh(jlpt, rng, count, exclude)

    def prepare(self, question, rng=random):
        """The question as it will be asked: a generated one gets a new roll of its wrong choices
        every time, so the same question never shows the same options twice."""
        from kobito import question_gen
        return question_gen.reroll(question, rng.randrange(10 ** 6))

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
        if jlpt is not None and rng.random() < DYNAMIC_SHARE:
            made_up = [q for q in self.fresh(jlpt, rng, 4, exclude) if q["category"] not in recent_categories]
            if made_up:
                return rng.choice(made_up)
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

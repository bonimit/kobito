"""AI-adaptive question picking: harder when you're doing well, easier when
you're struggling, always kept in a comfortable "just challenging enough"
range.

Two well-known learning techniques, combined:

1. **Elo rating (learner model).** As in adaptive practice systems
   (Pelánek, "Applications of the Elo rating system in adaptive
   educational systems", Computers & Education 2016), every answer is a
   "match" between the player and the question. The player has an ability
   `theta`; each question a difficulty `d` (seeded from its JLPT level).
   The chance of answering correctly is predicted as

       P(correct) = 1 / (1 + exp(-(theta - d)))

   and after each answer both are nudged toward what happened:

       theta += K * (result - P)        d -= K_item * (result - P)

   with K shrinking as more answers come in (Pelánek's "uncertainty
   function" K = a / (1 + b * n)), so early answers move the estimate fast
   and later ones fine-tune it.

2. **The sweet spot.** Each next question is the one whose predicted
   success is closest to TARGET_SUCCESS (85%), and only questions whose
   prediction falls inside COMFORT_BAND (65-95%) are considered when
   possible. This follows "The Eighty Five Percent Rule for optimal
   learning" (Wilson et al., Nature Communications 2019): learning is
   fastest at roughly 85% accuracy -- mostly succeeding, with some errors
   to learn from. In simulation, players settle at ~80% real accuracy
   (Elo's estimates are noisy early on), comfortably above the badge's
   70% bar, and a strong player climbs from N5 to N2 in ~15 questions.

3. **Spaced repetition (Leitner boxes).** A question you miss goes into
   review box 1 and comes back after a few other questions; answer it
   right and it moves to box 2 (comes back later still); right again and
   it's learned. Spacing the reviews out like this is what makes words
   stick (the Leitner system, the classic "SRS").

Everything is local and instant -- no network needed.
"""

import math
import random

from kobito.difficulty import JLPT_LEVELS

TARGET_SUCCESS = 0.85
COMFORT_BAND = (0.65, 0.95)
# Where each JLPT level starts on the difficulty scale (in logits).
JLPT_DIFFICULTY = {"N5": -2.0, "N4": -1.0, "N3": 0.0, "N2": 1.0, "N1": 2.0}
CATEGORY_OFFSET = {"kanji": 0.15, "grammar": 0.1, "reading": 0.1, "verb_conjugation": 0.05, "expression": 0.05,
                   "vocabulary": 0.0, "loanword": -0.05}

# K = a / (1 + b * n): big steps while we know little, smaller later.
# Early on the tutor knows little, so it moves boldly (a strong player
# reaches their real level in a dozen questions); later it settles down.
PLAYER_K = (2.0, 0.10)
ITEM_K = (0.4, 0.5)
K_FLOOR = 0.25
# Ability is kept between "comfortable with N5" and "beyond N1" -- the
# good range the question bank can actually serve.
THETA_RANGE = (-2.0 - 1.0, 2.0 + 2.5)

# Leitner review: (questions to wait before it comes back) per box.
REVIEW_GAPS = {1: 4, 2: 9}
# Every question whose predicted success is within CLOSE_ENOUGH of the best
# fit is a candidate; the kind is picked at random among them, then the
# question -- so it never feels scripted, even when hundreds of questions
# share the same difficulty.
CLOSE_ENOUGH = 0.05


def logistic(x):
    return 1.0 / (1.0 + math.exp(-x))


def logit(p):
    return math.log(p / (1.0 - p))


class AdaptiveTutor:
    def __init__(self, start_level="N5", rng=None):
        self.rng = rng or random.Random()
        # Start where the starting level's questions are predicted at the
        # target success rate.
        self.theta = JLPT_DIFFICULTY.get(start_level, -2.0) + logit(TARGET_SUCCESS)
        self.answers = 0
        self.item_offsets = {}     # question id -> learned difficulty adjustment
        self.item_answers = {}     # question id -> times answered
        self.reviews = {}          # question id -> {"box": 1|2, "due": answer count}

    # -- Model ------------------------------------------------------------------

    def difficulty(self, question):
        base = JLPT_DIFFICULTY.get(question.get("jlpt"), 0.0) + CATEGORY_OFFSET.get(question.get("category"), 0.0)
        return base + self.item_offsets.get(question["id"], 0.0)

    def predict(self, question):
        return logistic(self.theta - self.difficulty(question))

    def record(self, question, correct):
        """Updates the player's ability, the question's difficulty and its
        review box from one answer."""
        p = self.predict(question)
        result = 1.0 if correct else 0.0
        k_player = max(K_FLOOR, PLAYER_K[0] / (1 + PLAYER_K[1] * self.answers))
        n_item = self.item_answers.get(question["id"], 0)
        k_item = ITEM_K[0] / (1 + ITEM_K[1] * n_item)
        self.theta = min(THETA_RANGE[1], max(THETA_RANGE[0], self.theta + k_player * (result - p)))
        self.item_offsets[question["id"]] = self.item_offsets.get(question["id"], 0.0) - k_item * (result - p)
        self.item_answers[question["id"]] = n_item + 1
        self.answers += 1

        qid = question["id"]
        if not correct:
            self.reviews[qid] = {"box": 1, "due": self.answers + REVIEW_GAPS[1]}
        elif qid in self.reviews:
            box = self.reviews[qid]["box"] + 1
            if box in REVIEW_GAPS:
                self.reviews[qid] = {"box": box, "due": self.answers + REVIEW_GAPS[box]}
            else:
                del self.reviews[qid]          # learned

    # -- Choosing the next question -------------------------------------------

    def pick(self, questions, exclude=(), avoid_categories=()):
        """The next question: a review that's due, or else the unseen
        question closest to the target success rate, inside the comfort band
        when possible -- of a different kind from the last few asked
        (`avoid_categories`) when there's one that fits."""
        by_id = {q["id"]: q for q in questions}
        due = [qid for qid, r in self.reviews.items() if r["due"] <= self.answers and qid in by_id]
        # A due review of the same kind as the last question waits one turn.
        due = [qid for qid in due if by_id[qid].get("category") not in avoid_categories] or \
            (due if not avoid_categories else [])
        if due:
            return by_id[min(due, key=lambda qid: self.reviews[qid]["due"])]

        pool = [q for q in questions if q["id"] not in exclude and q["id"] not in self.reviews] or \
            [q for q in questions if q["id"] not in exclude] or list(questions)
        pool = [q for q in pool if q.get("category") not in avoid_categories] or pool
        # Questions never answered before first (right answers don't become reviews).
        pool = [q for q in pool if q["id"] not in self.item_answers] or pool
        scored = [(abs(self.predict(q) - TARGET_SUCCESS), q) for q in pool]
        comfy = [sq for sq in scored if COMFORT_BAND[0] <= self.predict(sq[1]) <= COMFORT_BAND[1]]
        ranked = sorted(comfy or scored, key=lambda sq: sq[0])
        near = [q for d, q in ranked if d <= ranked[0][0] + CLOSE_ENOUGH]
        kind = self.rng.choice(sorted({q.get("category", "") for q in near}))
        return self.rng.choice([q for q in near if q.get("category", "") == kind])

    def estimated_level(self):
        """The JLPT level whose questions the player answers at about the
        target rate -- shown on the HUD and used for the next level."""
        comfortable = self.theta - logit(TARGET_SUCCESS)
        return min(JLPT_LEVELS, key=lambda lv: abs(JLPT_DIFFICULTY[lv] - comfortable))

    # -- Saving -----------------------------------------------------------------

    def to_state(self):
        return {"theta": round(self.theta, 4), "answers": self.answers,
                "item_offsets": {k: round(v, 4) for k, v in self.item_offsets.items()},
                "item_answers": self.item_answers, "reviews": self.reviews}

    @classmethod
    def from_state(cls, state, rng=None):
        tutor = cls(rng=rng)
        try:
            tutor.theta = float(state.get("theta", tutor.theta))
            tutor.answers = int(state.get("answers", 0))
            tutor.item_offsets = {str(k): float(v) for k, v in state.get("item_offsets", {}).items()}
            tutor.item_answers = {str(k): int(v) for k, v in state.get("item_answers", {}).items()}
            tutor.reviews = {str(k): {"box": int(v["box"]), "due": int(v["due"])}
                             for k, v in state.get("reviews", {}).items()}
        except (AttributeError, KeyError, TypeError, ValueError):
            return cls(rng=rng)
        return tutor

import json
import random
from pathlib import Path

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "assets" / "data" / "questions.json"


class QuestionBank:
    def __init__(self, path=QUESTIONS_PATH):
        with open(path, encoding="utf-8") as f:
            self.questions = json.load(f)

    def random_question(self, jlpt=None):
        pool = self.questions
        if jlpt is not None:
            filtered = [q for q in pool if q["jlpt"] == jlpt]
            pool = filtered or pool  # fall back to the full bank if that level is empty
        return random.choice(pool)

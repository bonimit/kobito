"""End-of-stage review data: what the player learned, and the Stage Test.

After the castle, the player sees every question from the stage (with
explanations) and the words they met, then takes a short test built from
that same stage:

  * MC_COUNT multiple-choice questions -- the ones they got wrong or
    skipped first, then others from the stage, topped up from the bank;
  * READING_COUNT reading questions (読み): a word with kanji, build its
    reading from hiragana tiles (魚 -> さかな);
  * WRITING_COUNT writing questions (書き): a meaning and its romaji,
    build the Japanese word from tiles ("fish (sakana)" -> 魚).

Words come from the stage itself: items picked up, vocabulary questions
asked, and secret places found -- topped up from all items if the stage
was short on them.
"""

import re

from kobito.kana import HIRAGANA, has_kanji, has_katakana, is_hiragana, romaji_to_hiragana
from kobito.questions import shuffled

MC_COUNT = 8
READING_COUNT = 2
WRITING_COUNT = 2
TILE_COUNT = 8           # tiles offered per reading/writing question (answer + decoys)
MAX_WORD_CHARS = 6

# "犬 (inu)" inside a vocabulary prompt: the word and its romaji.
_WORD_IN_PROMPT = re.compile(r"([぀-ヿ一-鿿々ー]+)\s*\(([a-z][a-z ]*)\)")


def make_word(jp, romaji, meaning, source):
    if is_hiragana(jp):
        kana = jp
    elif has_kanji(jp) and not has_katakana(jp):
        kana = romaji_to_hiragana(romaji)
    else:
        kana = None
    return {"jp": jp, "romaji": romaji, "kana": kana, "meaning": meaning, "source": source}


def word_from_question(question):
    if question.get("category") != "vocabulary":
        return None
    m = _WORD_IN_PROMPT.search(question.get("prompt", ""))
    if not m:
        return None
    meaning = question["choices"][question["answer"]]
    return make_word(m.group(1), m.group(2), meaning, "quiz")


def word_from_item(item):
    return make_word(item.jp, item.reading, item.meaning, "item")


def word_from_place(spec):
    return make_word(spec["jp"], spec["reading"], spec["meaning"], "place")


def learned_words(entries, items, places):
    """The stage's words, in the order met, without duplicates."""
    words, seen = [], set()
    candidates = [word_from_question(e["question"]) for e in entries]
    candidates += [word_from_item(item) for item in items]
    candidates += [word_from_place(spec) for spec in places]
    for word in candidates:
        if word and word["jp"] not in seen:
            seen.add(word["jp"])
            words.append(word)
    return words


def _decoys(answer, pool, count, rng):
    pool = [ch for ch in dict.fromkeys(pool) if ch not in answer]
    rng.shuffle(pool)
    return pool[:count]


def reading_tiles(word, rng, other_words=()):
    answer = list(word["kana"])
    decoys = _decoys(answer, HIRAGANA, max(3, TILE_COUNT - len(answer)), rng)
    tiles = answer + decoys
    rng.shuffle(tiles)
    return answer, tiles


def writing_tiles(word, rng, other_words=()):
    answer = list(word["jp"])
    pool = []
    if has_kanji(word["jp"]):
        pool += [ch for w in other_words for ch in w["jp"] if has_kanji(ch)]
    if has_katakana(word["jp"]):
        pool += [ch for w in other_words for ch in w["jp"] if has_katakana(ch)] + list("アイウカキクサシタナマラリルンー")
    pool += HIRAGANA
    decoys = _decoys(answer, pool, max(3, TILE_COUNT - len(answer)), rng)
    tiles = answer + decoys
    rng.shuffle(tiles)
    return answer, tiles


def build_test(entries, words, bank, jlpt, rng, extra_words=()):
    """The Stage Test as a list of {"kind": "mc"|"reading"|"writing", ...}."""
    # Multiple choice: misses and skips first -- that's what needs practice.
    order = {"wrong": 0, "skipped": 1, "right": 2}
    stage = sorted(entries, key=lambda e: order.get(e["result"], 3))
    picked, ids = [], set()
    for e in stage:
        if len(picked) < MC_COUNT and e["question"]["id"] not in ids:
            picked.append(e["question"])
            ids.add(e["question"]["id"])
    fresh = [q for q in bank if q["jlpt"] == jlpt and q["id"] not in ids] or [q for q in bank if q["id"] not in ids]
    rng.shuffle(fresh)
    picked += fresh[:MC_COUNT - len(picked)]
    mc = [{"kind": "mc", "question": shuffled(q, rng)} for q in picked]

    pool = list(words) + [w for w in extra_words if w["jp"] not in {x["jp"] for x in words}]
    readable = [w for w in pool if w["kana"] and has_kanji(w["jp"]) and len(w["kana"]) <= MAX_WORD_CHARS]
    writable = [w for w in pool if w["meaning"] and len(w["jp"]) <= MAX_WORD_CHARS]
    # Prefer this stage's words, then fill from the extras.
    readable.sort(key=lambda w: w not in words)
    reading = readable[:READING_COUNT]
    writable = [w for w in writable if w not in reading]
    writable.sort(key=lambda w: w not in words)
    writing = writable[:WRITING_COUNT]

    rw = []
    for w in reading:
        answer, tiles = reading_tiles(w, rng, pool)
        rw.append({"kind": "reading", "word": w, "answer": answer, "tiles": tiles})
    for w in writing:
        answer, tiles = writing_tiles(w, rng, pool)
        rw.append({"kind": "writing", "word": w, "answer": answer, "tiles": tiles})

    # Mix them in: a few multiple choice, then a reading/writing one, ...
    test, step = [], max(1, len(mc) // max(1, len(rw)))
    for i, q in enumerate(mc):
        test.append(q)
        if rw and (i + 1) % step == 0:
            test.append(rw.pop(0))
    return test + rw

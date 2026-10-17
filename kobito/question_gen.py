"""Questions generated from the word and verb lists in kobito/word_data.py,
so every JLPT level has a few hundred questions to draw on -- enough that
replaying the game keeps meeting new ones.

From each word:
  * meaning  -- "What does 天気 (tenki) mean?"             (vocabulary)
  * reverse  -- "Which word means "Weather"?"              (vocabulary)
  * reading  -- "How do you read 天気?" (kanji words only)  (kanji)
From each verb, one question per form taught at its level:
  * "飲む (to drink) → te-form?"                           (verb_conjugation)

Answers are right by construction: meanings and readings come straight
from the lists, conjugations from kobito/conjugation.py. Wrong choices
are other words of the same level and part of speech, near-miss readings
(a dropped long vowel, a missing dakuten, a stray っ), or the classic
conjugation mistakes. Everything is seeded from the question id, so the
bank is identical on every run and saves can refer to questions by id.
"""

import random
import zlib

from kobito.conjugation import _TE, _ROWS, FORMS, conjugate, mistakes
from kobito.kana import has_kanji, kana_to_romaji
from kobito.word_data import VERBS, WORDS

VERB_FORMS = {
    "N5": ["masu", "masen", "mashita", "te", "ta", "nai"],
    "N4": ["te", "ta", "nai", "potential", "volitional", "ba", "passive"],
    "N3": ["te", "nai", "potential", "volitional", "ba", "passive", "causative"],
}

MEANING_PROMPTS = (
    "What does {jp} ({romaji}) mean?",
    "You hear the word {jp} ({romaji}). What does it mean?",
    "{jp} ({romaji}) — what is it in English?",
)
REVERSE_PROMPTS = (
    "Which word means \"{meaning}\"?",
    "How do you say \"{meaning}\" in Japanese?",
)
READING_PROMPTS = (
    "How do you read {jp}?",
    "What is the reading of {jp}?",
)
POS_NAMES = {"n": "a noun", "i": "an i-adjective", "na": "a na-adjective", "adv": "an adverb"}

_VOICED = dict(zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
_VOICED.update({v: k for k, v in list(_VOICED.items())})
_SMALL = {"ゃ": "や", "ゅ": "ゆ", "ょ": "よ"}
_O_ROW = set("おこごそぞとどのほぼぽもよろ")
_GEMINATE_BEFORE = set("かきくけこさしすせそたちつてとぱぴぷぺぽ")


def _rng(qid):
    return random.Random(zlib.crc32(qid.encode("utf-8")))


def _question(qid, category, jlpt, prompt, choices, answer, explanation, hint, rng):
    """Shuffles the choices (seeded) and builds the question dict."""
    order = [answer] + [c for c in choices if c != answer]
    rng.shuffle(order)
    return {"id": qid, "category": category, "jlpt": jlpt, "prompt": prompt, "choices": order,
            "answer": order.index(answer), "explanation": explanation, "hint": hint, "generated": True}


# -- Words ------------------------------------------------------------------------

def _label(word):
    return f"{word[0]} ({kana_to_romaji(word[1])})"


def _meaning_question(word, group, jlpt):
    jp, kana, meaning, pos = word
    qid = f"gen_meaning_{jlpt.lower()}_{jp}"
    rng = _rng(qid)
    others = [w[2] for w in group if w[2] != meaning]
    choices = [meaning] + rng.sample(others, 3)
    prompt = rng.choice(MEANING_PROMPTS).format(jp=jp, romaji=kana_to_romaji(kana))
    explanation = f"{jp} ({kana}) is {POS_NAMES[pos]} meaning \"{meaning.lower()}\"."
    hint = f"Say it out loud -- {kana}. Where would you hear it?"
    return _question(qid, "vocabulary", jlpt, prompt, choices, meaning, explanation, hint, rng)


def _reverse_question(word, group, jlpt):
    jp, kana, meaning, pos = word
    qid = f"gen_reverse_{jlpt.lower()}_{jp}"
    rng = _rng(qid)
    others = [_label(w) for w in group if w[0] != jp]
    answer = _label(word)
    choices = [answer] + rng.sample(others, 3)
    prompt = rng.choice(REVERSE_PROMPTS).format(meaning=meaning)
    explanation = f"{jp} ({kana}) means \"{meaning.lower()}\"."
    hint = "Read each word's romaji aloud -- which one have you heard used that way?"
    return _question(qid, "vocabulary", jlpt, prompt, choices, answer, explanation, hint, rng)


def near_misses(kana):
    """Readings one slip away from `kana`: a long vowel dropped or added,
    a dakuten added or lost, a small っ / ゃゅょ / ん out of place."""
    out = set()
    for i, ch in enumerate(kana):
        rest = kana[i + 1:]
        if ch in _VOICED:
            out.add(kana[:i] + _VOICED[ch] + rest)
        if ch == "う" and i and (kana[i - 1] in _O_ROW or kana[i - 1] in "ゅょう"):
            out.add(kana[:i] + rest)                       # drop a long vowel
        if ch == "い" and i and kana[i - 1] in "えけげせぜてでねへべぺめれ":
            out.add(kana[:i] + rest)
        if ch in _O_ROW and not rest.startswith(("う", "っ")):
            out.add(kana[:i + 1] + "う" + rest)            # add one
        if ch == "っ":
            out.add(kana[:i] + rest)
        if ch in _GEMINATE_BEFORE and i and kana[i - 1] not in "っん":
            out.add(kana[:i] + "っ" + kana[i:])
        if ch in _SMALL:
            out.add(kana[:i] + _SMALL[ch] + rest)
        if ch == "ん":
            out.add(kana[:i] + rest)
    out.discard(kana)
    return sorted(w for w in out if w and w[0] not in "っんゃゅょ")


def _reading_question(word, group, jlpt):
    jp, kana, meaning, pos = word
    qid = f"gen_reading_{jlpt.lower()}_{jp}"
    rng = _rng(qid)
    readings = {w[1] for w in group}
    wrong = [w for w in near_misses(kana) if w not in readings]
    rng.shuffle(wrong)
    wrong = wrong[:3]
    if len(wrong) < 3:   # short words: borrow readings of similar words (same part of speech, length)
        same_pos = {w[1] for w in group if w[3] == pos}
        similar = sorted((w for w in readings if w != kana),
                         key=lambda w: (w not in same_pos, abs(len(w) - len(kana)), w))
        wrong += [w for w in similar if w not in wrong][:3 - len(wrong)]
    prompt = rng.choice(READING_PROMPTS).format(jp=jp)
    explanation = f"{jp} is read {kana} ({kana_to_romaji(kana)}) and means \"{meaning.lower()}\"."
    hint = "Watch the small details: long vowels (う / い), dakuten (゛) and small っ."
    return _question(qid, "kanji", jlpt, prompt, [kana] + wrong, kana, explanation, hint, rng)


# -- Verbs ------------------------------------------------------------------------

def _rule(verb, kind, form):
    """One line on how the form is built, for the explanation."""
    if kind == "ru":
        ending = conjugate(verb, kind, form)[len(verb) - 1:]
        return f"{verb} is a ru-verb: drop る and add {ending}"
    if kind == "irr":
        if verb.endswith("する"):
            return f"{verb} is a する verb: する changes irregularly"
        return "来る is irregular: its stem changes between き, こ and く"
    end = verb[-1]
    row = _ROWS[end]
    if form in ("te", "ta"):
        if verb in ("行く", "いく"):
            return "行く is the one exception: it takes って / った, not いて"
        te = _TE[end]
        return f"{verb} is an u-verb ending in {end}, and those take ～{te if form == 'te' else te[:-1] + ('た' if te.endswith('て') else 'だ')}"
    vowel = {"masu": "i", "masen": "i", "mashita": "i", "nai": "a", "passive": "a", "causative": "a",
             "potential": "e", "ba": "e", "volitional": "o"}[form]
    target = row["iaeo".index(vowel)]
    tail = conjugate(verb, kind, form)[len(verb):]
    return f"{verb} is an u-verb: change the final {end} to {target} and add {tail}"


FORM_HINTS = {
    "masu": "Polite forms are built on the verb's i-stem.",
    "masen": "Polite negative: the i-stem plus the polite 'not' ending.",
    "mashita": "Polite past: the i-stem plus the polite past ending.",
    "te": "The te-form depends on the verb's last sound -- and on whether it's a ru- or u-verb.",
    "ta": "The ta-form follows exactly the same sound changes as the te-form.",
    "nai": "For u-verbs, move the last sound to the a-row before ない.",
    "potential": "'Can do': u-verbs move to the e-row and add る; ru-verbs add られる.",
    "volitional": "'Let's ~': u-verbs move to the o-row and add う; ru-verbs add よう.",
    "ba": "'If ~': the e-row plus ば.",
    "passive": "Passive: u-verbs move to the a-row and add れる; ru-verbs add られる.",
    "causative": "Causative: u-verbs move to the a-row and add せる; ru-verbs add させる.",
}


def _verb_question(verb_entry, form, jlpt):
    verb, kana, meaning, kind = verb_entry
    qid = f"gen_verb_{jlpt.lower()}_{verb}_{form}"
    rng = _rng(qid)
    answer = conjugate(verb, kind, form)
    traps = [m for m in dict.fromkeys(mistakes(verb, kind, form)) if m != answer]
    rng.shuffle(traps)
    pool = [conjugate(verb, kind, f) for f in FORMS if f != form]
    pool = [p for p in dict.fromkeys(pool) if p != answer and p not in traps]
    rng.shuffle(pool)
    choices = [answer] + (traps[:2] + pool)[:3]
    label = FORMS[form][0]
    prompt = f"{verb} ({meaning}) → {label}?"
    explanation = f"{_rule(verb, kind, form)} → {answer}."
    return _question(qid, "verb_conjugation", jlpt, prompt, choices, answer, explanation, FORM_HINTS[form], rng)


# -- The whole set ------------------------------------------------------------------

def generate(skip_words=()):
    """Every generated question, in a fixed order. Words in `skip_words`
    (already taught by a hand-written question) are left out."""
    questions = []
    for jlpt, words in WORDS.items():
        words = [w for w in words if w[0] not in skip_words]
        by_pos = {}
        for w in words:
            by_pos.setdefault(w[3], []).append(w)
        for w in words:
            group = by_pos[w[3]]
            if len(group) < 4:
                group = words
            questions.append(_meaning_question(w, group, jlpt))
            questions.append(_reverse_question(w, group, jlpt))
            if has_kanji(w[0]):
                questions.append(_reading_question(w, words, jlpt))
    for jlpt, verbs in VERBS.items():
        for v in verbs:
            for form in VERB_FORMS[jlpt]:
                questions.append(_verb_question(v, form, jlpt))
    return questions


def furigana_readings():
    """Readings for the listed words that are written all in kanji (天気 →
    てんき), so generated prompts and choices get furigana."""
    return {w[0]: w[1] for words in WORDS.values() for w in words
            if len(w[0]) > 1 and all("一" <= ch <= "鿿" for ch in w[0])}

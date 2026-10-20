"""Questions made up on the spot, so there's no end to them.

The question bank (kobito/questions.py, question_gen.py) has about 1,400
questions. These are different: each one is built fresh from a random
seed -- a random number to read, a random time, a random sentence --
so a player who has "learned" the quiz by heart has learned nothing:
the next one is new. Families:

  numbers    -- read 306, 2,450 ...                       (N5-N3)
  time       -- read 3:40, 9:15                           (N5-N4)
  dates      -- 5月3日, 7月20日, days of the week          (N5-N4)
  counters   -- 3本 / 5匹 / 4人; which counter to use     (N5-N4)
  particles  -- 学校__行きます  (は が を に で と ...)      (N5-N3)
  adjectives -- 高い -> negative / past / te-form          (all levels)
  forms      -- "食べて is which form of 食べる?"          (N5-N3)
  sentences  -- "I ate bread." <-> パンを食べました        (N5-N4)
  opposites  -- the opposite of 大きい                     (N5-N3)
  loanwords  -- コーヒー = coffee, both ways               (N5-N3)
  context    -- the word that fits （　）を食べます         (N5-N4, a JLPT "contextual usage" question)

(The real-paper formats with fixed content -- the ★ puzzle, reading and writing the marked word,
closest meaning, usage, cloze and short passages -- are in kobito/jlpt_style.py.)

Every question is rebuilt exactly from its id (dyn_<family>_<level>_<seed>),
so a save can bring one back (rebuild(id)), and every answer is right by
construction: readings come from the rules below, which tests/QA check by
reading them back. Wrong choices are the classic slips (a missed sound
change, the wrong counter, a swapped particle).
"""

import random

from kobito.conjugation import FORMS, conjugate
from kobito.kana import kana_to_romaji
from kobito.word_data import VERBS, WORDS

LEVELS = ("N5", "N4", "N3", "N2", "N1")


def _question(qid, category, jlpt, prompt, answer, wrongs, explanation, hint, rng):
    """The question dict, with the choices shuffled -- or None unless there are 3 distinct wrong ones."""
    wrongs = [w for w in dict.fromkeys(wrongs) if w and w != answer]
    if len(wrongs) < 3:
        return None
    rng.shuffle(wrongs)
    order = [answer] + wrongs[:3]
    rng.shuffle(order)
    return {"id": qid, "category": category, "jlpt": jlpt, "prompt": prompt, "choices": order,
            "answer": order.index(answer), "explanation": explanation, "hint": hint, "generated": True,
            "dynamic": True}


# ---- numbers ------------------------------------------------------------------------

ONES = ["", "いち", "に", "さん", "よん", "ご", "ろく", "なな", "はち", "きゅう"]
HUNDREDS = ["", "ひゃく", "にひゃく", "さんびゃく", "よんひゃく", "ごひゃく", "ろっぴゃく", "ななひゃく", "はっぴゃく", "きゅうひゃく"]
THOUSANDS = ["", "せん", "にせん", "さんぜん", "よんせん", "ごせん", "ろくせん", "ななせん", "はっせん", "きゅうせん"]


def number_kana(n):
    """1-9999 in hiragana (ichi, ni, san, yon ...; 300 = sanbyaku, 600 = roppyaku, 3000 = sanzen ...)."""
    if not 1 <= n <= 9999:
        raise ValueError(n)
    th, rest = divmod(n, 1000)
    h, rest = divmod(rest, 100)
    t, o = divmod(rest, 10)
    tens = "" if t == 0 else ("じゅう" if t == 1 else ONES[t] + "じゅう")
    return THOUSANDS[th] + HUNDREDS[h] + tens + ONES[o]


def _number_slips(n, kana, rng):
    """Wrong readings: another digit, a missed sound change, a dropped place."""
    slips = []
    th, rest = divmod(n, 1000)
    h, rest = divmod(rest, 100)
    t, o = divmod(rest, 10)
    for pos, digit in ((1000, th), (100, h), (10, t), (1, o)):
        if digit or pos == 1:
            for d in rng.sample([d for d in range(1, 10) if d != digit], 2):
                m = n + (d - digit) * pos
                if 1 <= m <= 9999 and m != n:
                    slips.append(number_kana(m))
    if h:                                           # plain (no sound change) hundreds
        slips.append(kana.replace(HUNDREDS[h], ONES[h] + "ひゃく", 1))
    if th:
        slips.append(kana.replace(THOUSANDS[th], ONES[th] + "せん", 1))
    if t:                                           # 20 = nijuu, never "nijuuu"; swap tens with hundreds word
        slips.append(kana.replace("じゅう", "ひゃく", 1))
    return [s for s in slips if s != kana]


def make_numbers(rng, level, seed):
    top = {"N5": 99, "N4": 999}.get(level, 9999)
    n = rng.randint(11 if level == "N5" else 101 if level == "N4" else 1001, top)
    if n % 10 == 0 and rng.random() < 0.5:
        n += rng.randint(1, 9) if n + 9 <= top else 0
    kana = number_kana(n)
    prompt = rng.choice((f"How do you read {n:,}?", f"What is the reading of {n:,}?", f"Which is {n:,} in Japanese?"))
    rule = []
    if n % 1000 // 100 in (3, 6, 8):
        rule.append("300, 600 and 800 change the sound: さんびゃく, ろっぴゃく, はっぴゃく")
    if n // 1000 in (3, 8):
        rule.append("3,000 and 8,000 change too: さんぜん, はっせん")
    explanation = f"{n:,} is {kana}." + (" " + "; ".join(rule) + "." if rule else "")
    hint = ("Say it place by place: thousands, hundreds, tens, ones." +
            (" Watch the sound change on 3, 6 and 8 before ひゃく / せん." if n >= 100 else ""))
    return _question(f"dyn_numbers_{level}_{seed}", "numbers", level, prompt, kana, _number_slips(n, kana, rng),
                     explanation, hint, rng), {"words": []}


# ---- time -----------------------------------------------------------------------------

HOURS = ["", "いち", "に", "さん", "よ", "ご", "ろく", "しち", "はち", "く", "じゅう", "じゅういち", "じゅうに"]
MIN_ONES = ["", "いっぷん", "にふん", "さんぷん", "よんぷん", "ごふん", "ろっぷん", "ななふん", "はっぷん", "きゅうふん"]


def minute_kana(m):
    t, o = divmod(m, 10)
    if m < 10:
        return MIN_ONES[m]
    if o == 0:
        return ("" if t == 1 else ONES[t]) + "じゅっぷん"
    return ("じゅう" if t == 1 else ONES[t] + "じゅう") + MIN_ONES[o]


def time_kana(h, m):
    return HOURS[h] + "じ" + (minute_kana(m) if m else "")


def make_time(rng, level, seed):
    h = rng.randint(1, 12)
    m = rng.choice((0, 0, 30, 15, 45, 5, 10, 20, 40, 50)) if level == "N5" else rng.choice([0, 0] + list(range(1, 60)))
    kana = time_kana(h, m)
    text = f"{h}:{m:02d}"
    slips = []
    wrong_hour = {4: "よんじ", 7: "ななじ", 9: "きゅうじ", 1: "いっじ", 6: "ろっじ", 8: "はっじ"}
    for hh, bad in wrong_hour.items():
        if hh == h:
            slips.append(bad + (minute_kana(m) if m else ""))
    for other in rng.sample([x for x in range(1, 13) if x != h], 3):
        slips.append(time_kana(other, m))
    if m:
        flip = minute_kana(m).replace("ふん", "ぷん") if "ふん" in minute_kana(m) else minute_kana(m).replace("ぷん", "ふん")
        slips.append(HOURS[h] + "じ" + flip)
        for other in rng.sample([x for x in range(1, 60) if x != m], 3):
            slips.append(HOURS[h] + "じ" + minute_kana(other))
    else:
        slips += [HOURS[h] + "じはん", HOURS[h] + "じすぎ"]
    notes = []
    if h in (4, 7, 9):
        notes.append({4: "4 o'clock is よじ (not よんじ)", 7: "7 o'clock is しちじ", 9: "9 o'clock is くじ (not きゅうじ)"}[h])
    if m and ("ぷん" in minute_kana(m)):
        notes.append("minutes ending in 1, 3, 4, 6, 8 and 10 are ぷん; the rest are ふん")
    return _question(f"dyn_time_{level}_{seed}", "numbers", level,
                     rng.choice((f"How do you read {text}?", f"What time is {text} in Japanese?")), kana, slips,
                     f"{text} is {kana}." + (" Note: " + "; ".join(notes) + "." if notes else ""),
                     "Say the hour first (4 = よじ, 7 = しちじ, 9 = くじ), then the minutes (ふん or ぷん).", rng), {"words": []}


# ---- dates ----------------------------------------------------------------------------

MONTHS = ["", "いち", "に", "さん", "し", "ご", "ろく", "しち", "はち", "く", "じゅう", "じゅういち", "じゅうに"]
DAYS_1_10 = ["", "ついたち", "ふつか", "みっか", "よっか", "いつか", "むいか", "なのか", "ようか", "ここのか", "とおか"]
WEEKDAYS = [("月曜日", "げつようび", "Monday"), ("火曜日", "かようび", "Tuesday"), ("水曜日", "すいようび", "Wednesday"),
            ("木曜日", "もくようび", "Thursday"), ("金曜日", "きんようび", "Friday"), ("土曜日", "どようび", "Saturday"),
            ("日曜日", "にちようび", "Sunday")]


def day_kana(d):
    if d <= 10:
        return DAYS_1_10[d]
    if d == 14:
        return "じゅうよっか"
    if d == 20:
        return "はつか"
    if d == 24:
        return "にじゅうよっか"
    t, o = divmod(d, 10)
    tens = {1: "じゅう", 2: "にじゅう", 3: "さんじゅう"}[t]
    if o == 0:
        return tens + "にち"
    ones = {1: "いち", 2: "に", 3: "さん", 4: "よん", 5: "ご", 6: "ろく", 7: "しち", 8: "はち", 9: "く"}[o]
    return tens + ones + "にち"


def make_dates(rng, level, seed):
    qid = f"dyn_dates_{level}_{seed}"
    if rng.random() < 0.3:                                    # days of the week
        jp, kana, en = rng.choice(WEEKDAYS)
        if rng.random() < 0.5:
            return _question(qid, "vocabulary", level, f"What day is {jp} ({kana_to_romaji(kana)})?", en,
                             [w[2] for w in WEEKDAYS], f"{jp} ({kana}) is {en}.",
                             "The first kanji is the key: 月 moon, 火 fire, 水 water, 木 tree, 金 gold, 土 earth, 日 sun.", rng), \
                {"words": [(jp, kana)]}
        return _question(qid, "vocabulary", level, f"Which word is {en}?", f"{jp} ({kana_to_romaji(kana)})",
                         [f"{w[0]} ({kana_to_romaji(w[1])})" for w in WEEKDAYS], f"{en} is {jp} ({kana}).",
                         "Think of the element or body in the first kanji: 月 moon, 火 fire, 水 water, 木 tree, 金 gold, 土 earth, 日 sun.", rng), \
            {"words": [(w[0], w[1]) for w in WEEKDAYS]}
    month = rng.randint(1, 12)
    day = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 20, 24]) if level == "N5" else rng.randint(1, 31)
    month_kana = MONTHS[month] + "がつ"
    kana = month_kana + day_kana(day)
    slips = []
    for other in rng.sample([d for d in range(1, 32) if d != day], 3):
        slips.append(month_kana + day_kana(other))
    slips.append(month_kana + ONES_DAY(day))                                   # the plain "san-nichi" slip
    for other in rng.sample([m for m in range(1, 13) if m != month], 2):
        slips.append(MONTHS[other] + "がつ" + day_kana(day))
    if month in (4, 7, 9):
        slips.append({4: "よんがつ", 7: "ななかつ", 9: "きゅうがつ"}[month] + day_kana(day))
    notes = []
    if month in (4, 7, 9):
        notes.append({4: "April is しがつ", 7: "July is しちがつ", 9: "September is くがつ"}[month])
    if day <= 10 or day in (14, 20, 24):
        notes.append(f"the {day}th is {day_kana(day)}, an irregular day word")
    return _question(qid, "numbers", level, f"How do you read {month}月{day}日?", kana, slips,
                     f"{month}月{day}日 is {kana}." + (" " + "; ".join(notes) + "." if notes else ""),
                     "Month: number + がつ (4 = し, 7 = しち, 9 = く). Days 1-10, 14, 20 and 24 have their own words.", rng), \
        {"words": [(f"{month}月{day}日", kana)]}


def ONES_DAY(d):
    """The regular-but-wrong 'number + にち' reading of a day."""
    if d > 10:
        return day_kana(d)
    return ["", "いち", "に", "さん", "よん", "ご", "ろく", "なな", "はち", "きゅう", "じゅう"][d] + "にち"


# ---- counters -------------------------------------------------------------------------

def _regular(base):
    return {n: ONES[n] + base for n in range(1, 10)} | {10: "じゅう" + base}


def _table(base, **special):
    t = _regular(base)
    t.update({int(k[1:]): v for k, v in special.items()})
    return t


COUNTERS = {
    "人": ("ひと", "people", ("a person", "friends", "children"), {1: "ひとり", 2: "ふたり", 3: "さんにん", 4: "よにん", 5: "ごにん",
                                                              6: "ろくにん", 8: "はちにん", 9: "きゅうにん", 10: "じゅうにん"}),
    "本": ("ほん", "long thin things", ("a pen", "an umbrella", "a bottle", "a tree"),
          {1: "いっぽん", 2: "にほん", 3: "さんぼん", 4: "よんほん", 5: "ごほん", 6: "ろっぽん", 7: "ななほん", 8: "はっぽん",
           9: "きゅうほん", 10: "じゅっぽん"}),
    "枚": ("まい", "flat things", ("paper", "a shirt", "a plate", "a ticket"), _regular("まい")),
    "個": ("こ", "small round things", ("an apple", "an egg", "a candy"),
          {1: "いっこ", 2: "にこ", 3: "さんこ", 4: "よんこ", 5: "ごこ", 6: "ろっこ", 7: "ななこ", 8: "はっこ", 9: "きゅうこ", 10: "じゅっこ"}),
    "匹": ("ひき", "small animals", ("a cat", "a dog", "a fish"),
          {1: "いっぴき", 2: "にひき", 3: "さんびき", 4: "よんひき", 5: "ごひき", 6: "ろっぴき", 7: "ななひき", 8: "はっぴき",
           9: "きゅうひき", 10: "じゅっぴき"}),
    "冊": ("さつ", "books", ("a book", "a notebook", "a magazine"),
          {1: "いっさつ", 2: "にさつ", 3: "さんさつ", 4: "よんさつ", 5: "ごさつ", 6: "ろくさつ", 7: "ななさつ", 8: "はっさつ",
           9: "きゅうさつ", 10: "じゅっさつ"}),
    "台": ("だい", "machines and vehicles", ("a car", "a bicycle", "a computer"), _regular("だい")),
    "杯": ("はい", "cups and glasses", ("a cup of tea", "a glass of water", "a coffee"),
          {1: "いっぱい", 2: "にはい", 3: "さんばい", 4: "よんはい", 5: "ごはい", 6: "ろっぱい", 7: "ななはい", 8: "はっぱい",
           9: "きゅうはい", 10: "じゅっぱい"}),
}
COUNTER_LEVEL = {"N5": ("人", "本", "枚", "個"), "N4": tuple(COUNTERS), "N3": tuple(COUNTERS)}
OBJECTS = {  # object -> counter
    "猫 (neko)": "匹", "犬 (inu)": "匹", "魚 (sakana)": "匹", "ペン (pen)": "本", "傘 (kasa)": "本", "木 (ki)": "本",
    "紙 (kami)": "枚", "シャツ (shatsu)": "枚", "切符 (kippu)": "枚", "りんご (ringo)": "個", "卵 (tamago)": "個",
    "本 (hon)": "冊", "ノート (nōto)": "冊", "車 (kuruma)": "台", "自転車 (jitensha)": "台", "コーヒー (kōhī)": "杯",
    "お茶 (ocha)": "杯", "友達 (tomodachi)": "人", "学生 (gakusei)": "人",
}
OBJECT_KANA = {"猫": "ねこ", "犬": "いぬ", "魚": "さかな", "傘": "かさ", "木": "き", "紙": "かみ", "切符": "きっぷ", "卵": "たまご",
               "本": "ほん", "車": "くるま", "自転車": "じてんしゃ", "お茶": "おちゃ", "友達": "ともだち", "学生": "がくせい"}


def make_counters(rng, level, seed):
    qid = f"dyn_counters_{level}_{seed}"
    allowed = COUNTER_LEVEL.get(level, tuple(COUNTERS))
    if rng.random() < 0.4:                                     # which counter?
        choices = [o for o, c in OBJECTS.items() if c in allowed]
        obj = rng.choice(choices)
        right = OBJECTS[obj]
        label = lambda c: f"{c} ({COUNTERS[c][0]})"                      # noqa: E731
        reading = COUNTERS[right][0]
        slips = [label(c) for c in allowed if c != right]
        word = obj.split(" ")[0]
        return _question(qid, "counter", level, f"Which counter do you use for {obj}?", label(right), slips,
                         f"{right} ({reading}) counts {COUNTERS[right][1]}, like {obj}.",
                         f"Think about the shape or kind: {COUNTERS[right][1]}.", rng), \
            {"words": [(c, COUNTERS[c][0]) for c in COUNTERS] + [(word, OBJECT_KANA[word])] if word in OBJECT_KANA else
             [(c, COUNTERS[c][0]) for c in COUNTERS]}
    counter = rng.choice(allowed)
    table = COUNTERS[counter][3]
    n = rng.choice(sorted(table))
    right = table[n]
    base = COUNTERS[counter][0]
    plain = (ONES[n] if n < 10 else "じゅう") + base
    slips = [plain] + [table[m] for m in rng.sample([k for k in sorted(table) if k != n], 4)]
    for a, b in (("ぼん", "ほん"), ("ぽん", "ほん"), ("ぼん", "ぽん"), ("びき", "ひき"), ("ぴき", "ひき"), ("ぱい", "はい"), ("ばい", "はい")):
        if a in right:
            slips.append(right.replace(a, b))
        elif b in right:
            slips.append(right.replace(b, a))
    return _question(qid, "counter", level, f"How do you read {n}{counter} ({COUNTERS[counter][1]})?", right, slips,
                     f"{n}{counter} is {right}." + (" This counter changes its sound with the number." if right != plain else ""),
                     f"{counter} counts {COUNTERS[counter][1]}. Say the number, then listen for a sound change (ほん / ぼん / ぽん).", rng), \
        {"words": [(c, COUNTERS[c][0]) for c in COUNTERS]}


# ---- particles ------------------------------------------------------------------------

FOODS = [("パン", None), ("寿司", "すし"), ("ご飯", "ごはん"), ("魚", "さかな"), ("肉", "にく"), ("野菜", "やさい"), ("果物", "くだもの")]
DRINKS = [("水", "みず"), ("お茶", "おちゃ"), ("牛乳", "ぎゅうにゅう"), ("コーヒー", None)]
PLACES = [("学校", "がっこう"), ("駅", "えき"), ("公園", "こうえん"), ("病院", "びょういん"), ("図書館", "としょかん"), ("店", "みせ"), ("会社", "かいしゃ")]
PEOPLE = [("友達", "ともだち"), ("先生", "せんせい"), ("母", "はは"), ("父", "ちち"), ("兄", "あに"), ("姉", "あね")]
VEHICLES = [("電車", "でんしゃ"), ("バス", None), ("自転車", "じてんしゃ"), ("車", "くるま"), ("タクシー", None)]
LIKES = [("りんご", None), ("音楽", "おんがく"), ("猫", "ねこ"), ("犬", "いぬ"), ("花", "はな"), ("映画", "えいが"), ("日本語", "にほんご")]

# (sentence with {a} and the blank ___, correct, the particles that are definitely wrong, why, pool for {a}, level)
PARTICLE_TEMPLATES = [
    ("{a}___ 食べます。", "を", ["に", "で", "へ"], "を marks the thing you eat (the object).", FOODS, "N5"),
    ("{a}___ 飲みます。", "を", ["に", "で", "へ"], "を marks the thing you drink (the object).", DRINKS, "N5"),
    ("{a}___ 行きます。", "に", ["を", "で", "と"], "に marks where you go (the destination).", PLACES, "N5"),
    ("{a}___ 勉強します。", "で", ["を", "に", "へ"], "で marks the place where an action happens.", PLACES[:4] + PLACES[5:], "N5"),
    ("{a}___ 会います。", "に", ["を", "で", "へ"], "に marks the person you meet.", PEOPLE, "N5"),
    ("{a}___ 行きます。", "で", ["を", "に", "と"], "で marks how you travel (by train, by car ...).", VEHICLES, "N5"),
    ("{a}___ 話します。", "と", ["を", "へ", "で"], "と means 'with': the person you talk with.", PEOPLE, "N5"),
    ("{a}___ 好きです。", "が", ["を", "に", "で"], "好き takes が for the thing you like, not を.", LIKES, "N5"),
    ("{a}に 猫___ います。", "が", ["を", "で", "と"], "が marks what exists (います / あります).", PLACES[:4], "N4"),
    ("私は {a}___ 手紙を 書きます。", "に", ["を", "で", "が"], "に marks the person you do something for or to.", PEOPLE, "N4"),
    ("{a}の 前___ 待ちます。", "で", ["を", "に", "と"], "で marks where an action takes place.", PLACES, "N4"),
    ("{a}___ 勉強してから、 寝ます。", "を", ["に", "で", "と"], "を marks what you study.", [("日本語", "にほんご"), ("漢字", "かんじ")], "N4"),
    ("毎日 {a}___ 通います。", "に", ["を", "で", "と"], "に marks the place you go to regularly (通う).", PLACES, "N3"),
    ("{a}___ よると、 明日は 雨です。", "に", ["を", "で", "と"], "に よると means 'according to'.", [("天気予報", "てんきよほう"), ("先生", "せんせい")], "N3"),
    ("{a}___ 乗ります。", "に", ["を", "で", "と"], "乗る takes に for the vehicle you ride.", VEHICLES, "N4"),
]


def make_particles(rng, level, seed):
    order = ["N5", "N4", "N3"]
    pool = [t for t in PARTICLE_TEMPLATES if order.index(t[5]) <= order.index(level if level in order else "N3")]
    if level in order:
        mine = [t for t in pool if t[5] == level]
        pool = mine or pool
    sentence, right, wrong, why, nouns, _ = rng.choice(pool)
    noun, kana = rng.choice(nouns)
    text = sentence.replace("{a}", noun)
    others = [p for p in ("は", "を", "に", "で", "と", "へ", "も", "から") if p != right and p not in wrong]
    return _question(f"dyn_particles_{level}_{seed}", "particle", level, f"Which particle fills the blank?  {text}", right,
                     wrong + rng.sample(others, 1), f"{right}: {why}", "Ask what job the noun does in the sentence: place, object, person, tool?", rng), \
        {"words": [(noun, kana)] if kana else []}


# ---- adjectives -----------------------------------------------------------------------

ADJ_FORMS = {
    "neg": ("negative", lambda w, k, pos: (w[:-1] + "くない", k[:-1] + "くない") if pos == "i" else (w + "じゃない", k + "じゃない")),
    "past": ("past", lambda w, k, pos: (w[:-1] + "かった", k[:-1] + "かった") if pos == "i" else (w + "だった", k + "だった")),
    "te": ("te-form (and ~)", lambda w, k, pos: (w[:-1] + "くて", k[:-1] + "くて") if pos == "i" else (w + "で", k + "で")),
    "pastneg": ("past negative", lambda w, k, pos: (w[:-1] + "くなかった", k[:-1] + "くなかった") if pos == "i"
                else (w + "じゃなかった", k + "じゃなかった")),
}


def _adj_slips(w, pos, form):
    if pos == "i":
        stem, plain = w[:-1], w
        return {"neg": [plain + "くない", plain + "じゃない", stem + "かない", stem + "くだった"],
                "past": [plain + "かった", stem + "だった", plain + "だった", stem + "くった"],
                "te": [plain + "くて", stem + "で", plain + "で", stem + "いで"],
                "pastneg": [plain + "くなかった", stem + "じゃなかった", stem + "くないだった", stem + "かなかった"]}[form]
    return {"neg": [w + "くない", w + "ない", w + "かない", w + "じゃある"],
            "past": [w + "かった", w + "た", w + "くだった", w + "でした"][:3] + [w + "だった"[1:]],
            "te": [w + "くて", w + "て", w + "いで", w + "だって"],
            "pastneg": [w + "くなかった", w + "かなかった", w + "じゃなくて", w + "くないだった"]}[form]


def make_adjectives(rng, level, seed):
    words = [x for x in WORDS[level] if x[3] in ("i", "na") and x[1] not in ("いい", "よい") and x[0] not in ("いい", "良い")]
    if not words:
        return None, {}
    w, kana, meaning, pos = rng.choice(words)
    form = rng.choice(list(ADJ_FORMS))
    label, fn = ADJ_FORMS[form]
    answer, answer_kana = fn(w, kana, pos)
    slips = _adj_slips(w, pos, form)
    kind = "an い-adjective" if pos == "i" else "a な-adjective"
    rule = ({"neg": "drop い, add くない", "past": "drop い, add かった", "te": "drop い, add くて",
             "pastneg": "drop い, add くなかった"} if pos == "i" else
            {"neg": "add じゃない", "past": "add だった", "te": "add で", "pastneg": "add じゃなかった"})[form]
    hint = f"{w} is {kind}: " + ("い adjectives change their ending." if pos == "i" else "な adjectives stay the same and take じゃない / だった / で.")
    extra = []
    for f2 in ADJ_FORMS:
        j, jk = ADJ_FORMS[f2][1](w, kana, pos)
        extra.append((j, jk))
    return _question(f"dyn_adjectives_{level}_{seed}", "grammar", level, f"{w} ({meaning.lower()}) → {label}?", answer, slips,
                     f"{w} is {kind}: {rule} → {answer}.", hint, rng), {"words": [(w, kana)] + extra}


# ---- verb forms, the other way round ------------------------------------------------

def make_forms(rng, level, seed):
    verbs = VERBS.get(level) or VERBS["N3"]
    verb, kana, meaning, kind = rng.choice(verbs)
    allowed = [f for f, (_, lv) in FORMS.items() if f in ("masu", "masen", "mashita", "te", "ta", "nai", "potential", "volitional", "ba",
                                                      "passive", "causative")
               and ("N5", "N4", "N3").index(lv) <= ("N5", "N4", "N3").index(level if level in ("N5", "N4", "N3") else "N3")]
    results = {f: conjugate(verb, kind, f) for f in allowed}
    unique = [f for f in allowed if list(results.values()).count(results[f]) == 1]
    if len(unique) < 4:
        return None, {}
    form = rng.choice(unique)
    answer = FORMS[form][0]
    slips = [FORMS[f][0] for f in unique if f != form]
    shown = results[form]
    return _question(f"dyn_forms_{level}_{seed}", "verb_conjugation", level if level in ("N5", "N4", "N3") else "N3",
                     f"{shown} is which form of {verb} ({meaning})?", answer, slips,
                     f"{verb} → {shown} is the {answer}.",
                     "Look at how the ending changed: い/って/んで (te), た (past), ない (negative), える (potential), れる/られる (passive).", rng), \
        {"words": [(shown, conjugate(kana, kind, form)), (verb, kana)]}


# ---- sentences ------------------------------------------------------------------------

SENTENCE_VERBS = {
    "食べる": ("食べ", "たべ", "eat", "ate", "don't eat", [("パン", None, "bread"), ("寿司", "すし", "sushi"), ("ご飯", "ごはん", "rice"),
                                                       ("魚", "さかな", "fish"), ("肉", "にく", "meat"), ("野菜", "やさい", "vegetables")]),
    "飲む": ("飲み", "のみ", "drink", "drank", "don't drink", [("水", "みず", "water"), ("お茶", "おちゃ", "tea"), ("牛乳", "ぎゅうにゅう", "milk"),
                                                           ("コーヒー", None, "coffee")]),
    "読む": ("読み", "よみ", "read", "read", "don't read", [("本", "ほん", "a book"), ("新聞", "しんぶん", "the newspaper")]),
    "見る": ("見", "み", "watch", "watched", "don't watch", [("映画", "えいが", "a movie"), ("テレビ", None, "TV")]),
    "聞く": ("聞き", "きき", "listen to", "listened to", "don't listen to", [("音楽", "おんがく", "music")]),
    "買う": ("買い", "かい", "buy", "bought", "don't buy", [("りんご", None, "an apple"), ("本", "ほん", "a book"), ("パン", None, "bread"),
                                                      ("新聞", "しんぶん", "the newspaper")]),
}
ENDINGS = {"present": ("ます", "ます"), "past": ("ました", "ました"), "neg": ("ません", "ません")}


def _english(subject, verb, tense, obj):
    base = SENTENCE_VERBS[verb]
    return {"present": f"{subject} {base[2]} {obj}.", "past": f"{subject} {base[3]} {obj}.", "neg": f"{subject} {base[4]} {obj}."}[tense]


def make_sentences(rng, level, seed):
    verb = rng.choice(list(SENTENCE_VERBS))
    stem, stem_kana, _, _, _, objects = SENTENCE_VERBS[verb]
    obj, obj_kana, obj_en = rng.choice(objects)
    tense = rng.choice(list(ENDINGS))
    ja = lambda o, t, v=verb: f"{o}を{SENTENCE_VERBS[v][0]}{ENDINGS[t][0]}。"                       # noqa: E731
    subject = "I"
    right_en = _english(subject, verb, tense, obj_en)
    qid = f"dyn_sentences_{level}_{seed}"
    words = [(obj, obj_kana)] if obj_kana else []
    for v, (st, stk, *_rest) in SENTENCE_VERBS.items():
        for t, (suf, _) in ENDINGS.items():
            words.append((st + suf, stk + suf))
    for v in SENTENCE_VERBS.values():
        for o, ok, _ in v[5]:
            if ok:
                words.append((o, ok))
    if rng.random() < 0.5:                                           # Japanese -> English
        slips = [_english(subject, verb, t, obj_en) for t in ENDINGS if t != tense]
        other_objs = [o[2] for o in objects if o[2] != obj_en] or [o[2] for v in SENTENCE_VERBS.values() for o in v[5] if o[2] != obj_en]
        slips.append(_english(subject, verb, tense, rng.choice(other_objs)))
        slips.append(_english(subject, verb, rng.choice([t for t in ENDINGS if t != tense]), rng.choice(other_objs)))
        return _question(qid, "sentence", level, f"What does 「{ja(obj, tense)}」 mean?", right_en, slips,
                         f"{obj}を = the thing ({obj_en}); {stem}{ENDINGS[tense][0]} = {tense} ({verb}).",
                         "Find the verb ending first: ます (now), ました (past), ません (not).", rng), {"words": words}
    right = ja(obj, tense)
    slips = [ja(obj, t) for t in ENDINGS if t != tense]
    others = [o for v in SENTENCE_VERBS.values() for o in v[5] if o[0] != obj]
    slips.append(ja(rng.choice(others)[0], tense, verb))
    slips.append(ja(rng.choice(others)[0], rng.choice([t for t in ENDINGS if t != tense]), verb))
    return _question(qid, "sentence", level, f"Which sentence means 「{right_en}」?", right, slips,
                     f"{obj}を{stem}{ENDINGS[tense][0]}: {obj_en}, {tense} tense.",
                     "Match the thing first, then the verb ending (ます now / ました past / ません not).", rng), {"words": words}


# ---- opposites ------------------------------------------------------------------------

OPPOSITES = [
    ("大きい", "おおきい", "小さい", "ちいさい", "N5"), ("高い", "たかい", "安い", "やすい", "N5"), ("新しい", "あたらしい", "古い", "ふるい", "N5"),
    ("長い", "ながい", "短い", "みじかい", "N5"), ("暑い", "あつい", "寒い", "さむい", "N5"), ("多い", "おおい", "少ない", "すくない", "N5"),
    ("上", "うえ", "下", "した", "N5"), ("右", "みぎ", "左", "ひだり", "N5"), ("朝", "あさ", "夜", "よる", "N5"), ("男", "おとこ", "女", "おんな", "N5"),
    ("入る", "はいる", "出る", "でる", "N5"), ("行く", "いく", "来る", "くる", "N5"), ("買う", "かう", "売る", "うる", "N5"),
    ("強い", "つよい", "弱い", "よわい", "N4"), ("重い", "おもい", "軽い", "かるい", "N4"), ("近い", "ちかい", "遠い", "とおい", "N4"),
    ("明るい", "あかるい", "暗い", "くらい", "N4"), ("広い", "ひろい", "狭い", "せまい", "N4"), ("太い", "ふとい", "細い", "ほそい", "N4"),
    ("開ける", "あける", "閉める", "しめる", "N4"), ("始まる", "はじまる", "終わる", "おわる", "N4"), ("勝つ", "かつ", "負ける", "まける", "N4"),
    ("覚える", "おぼえる", "忘れる", "わすれる", "N4"), ("教える", "おしえる", "習う", "ならう", "N4"),
    ("上手", "じょうず", "下手", "へた", "N3"), ("便利", "べんり", "不便", "ふべん", "N3"), ("安全", "あんぜん", "危険", "きけん", "N3"),
    ("増える", "ふえる", "減る", "へる", "N3"), ("成功", "せいこう", "失敗", "しっぱい", "N3"), ("賛成", "さんせい", "反対", "はんたい", "N3"),
    ("得意", "とくい", "苦手", "にがて", "N3"), ("集める", "あつめる", "散らす", "ちらす", "N3"),
]


def make_opposites(rng, level, seed):
    rank = ("N5", "N4", "N3")
    pool = [p for p in OPPOSITES if p[4] == (level if level in rank else "N3")] or OPPOSITES
    a, ak, b, bk, _ = rng.choice(pool)
    if rng.random() < 0.5:
        a, ak, b, bk = b, bk, a, ak
    pos_group = [p for p in OPPOSITES if p[4] == _ and p[0] != a and p[2] != a] or OPPOSITES
    wrongs = []
    for p in pos_group:
        wrongs += [(p[0], p[1]), (p[2], p[3])]
    wrongs = [w for w in wrongs if w[0] not in (a, b)]
    label = lambda w, k: f"{w} ({kana_to_romaji(k)})"                                            # noqa: E731
    picks = rng.sample(wrongs, 3)
    return _question(f"dyn_opposites_{level}_{seed}", "vocabulary", level, f"What is the opposite of {label(a, ak)}?", label(b, bk),
                     [label(*p) for p in picks], f"{a} ({ak}) and {b} ({bk}) are opposites.",
                     "Picture the two ends of the same scale.", rng), {"words": [(a, ak), (b, bk)] + picks}


# ---- loanwords ------------------------------------------------------------------------

LOANWORDS = [
    ("コーヒー", "coffee"), ("パン", "bread"), ("ホテル", "hotel"), ("テレビ", "TV"), ("ラジオ", "radio"), ("カメラ", "camera"),
    ("スポーツ", "sports"), ("レストラン", "restaurant"), ("タクシー", "taxi"), ("バス", "bus"), ("ドア", "door"), ("ベッド", "bed"),
    ("ナイフ", "knife"), ("フォーク", "fork"), ("スプーン", "spoon"), ("ノート", "notebook"), ("ペン", "pen"), ("ケーキ", "cake"),
    ("ジュース", "juice"), ("ビール", "beer"), ("シャツ", "shirt"), ("スカート", "skirt"), ("ネクタイ", "necktie"), ("メール", "email"),
    ("プレゼント", "present"), ("ピアノ", "piano"), ("ギター", "guitar"), ("サッカー", "soccer"), ("テニス", "tennis"), ("トイレ", "toilet"),
    ("エレベーター", "elevator"), ("デパート", "department store"), ("スーパー", "supermarket"), ("コンビニ", "convenience store"),
    ("アルバイト", "part-time job"), ("ガソリン", "gasoline"), ("パソコン", "personal computer"), ("カレンダー", "calendar"),
    ("ポスト", "mailbox"), ("ハンバーガー", "hamburger"), ("アイスクリーム", "ice cream"), ("スマホ", "smartphone"),
]


def make_loanwords(rng, level, seed):
    word, en = rng.choice(LOANWORDS)
    others = [x for x in LOANWORDS if x[0] != word]
    qid = f"dyn_loanwords_{level}_{seed}"
    if rng.random() < 0.5:
        return _question(qid, "loanword", level, f"What does {word} mean?", en, [o[1] for o in rng.sample(others, 3)],
                         f"{word} comes from English: {en}.", "Say it aloud with Japanese sounds -- it's borrowed from another language.", rng), {"words": []}
    return _question(qid, "loanword", level, f"Which word means \"{en}\"?", word, [o[0] for o in rng.sample(others, 3)],
                     f"{en} in Japanese is {word}.", "It's a katakana word borrowed from English.", rng), {"words": []}


# ---- JLPT-style: the word that fits, and the ★ sentence puzzle ------------------------

def make_context(rng, level, seed):
    """JLPT 'contextual usage': the word that fits the blank (   )."""
    verb = rng.choice([v for v in SENTENCE_VERBS if v != "買う"])          # you can buy anything: no single answer
    stem, stem_kana, en, past, neg, objects = SENTENCE_VERBS[verb]
    obj, obj_kana, obj_en = rng.choice(objects)
    also_fine = {"見る": ("本", "新聞")}.get(verb, ())                       # 本を見ます is fine Japanese too
    pool = [o for v, d in SENTENCE_VERBS.items() if v != verb for o in d[5]
            if o[0] not in [x[0] for x in objects] and o[0] not in also_fine]
    wrongs = rng.sample(pool, 3)
    label = lambda o: f"{o[0]} ({kana_to_romaji(o[1])})" if o[1] else o[0]                        # noqa: E731
    tense = rng.choice(("ます", "ました", "ません"))
    words = [(o[0], o[1]) for o in [(obj, obj_kana)] + wrongs if o[1]] + [(stem + tense, stem_kana + tense)]
    return _question(f"dyn_context_{level}_{seed}", "vocabulary", level, f"Which word fits the blank?  （　　）を{stem}{tense}。",
                     label((obj, obj_kana)), [label(w) for w in wrongs],
                     f"You can {verb} ({en}) {obj_en}: （　　）を{stem}{tense} -> {obj}を{stem}{tense}.",
                     "Read the verb, then ask which thing you can actually do it to.", rng), {"words": words}


# ---- the registry ---------------------------------------------------------------------

FAMILIES = {
    "numbers": (make_numbers, ("N5", "N4", "N3")),
    "time": (make_time, ("N5", "N4")),
    "dates": (make_dates, ("N5", "N4")),
    "counters": (make_counters, ("N5", "N4", "N3")),
    "particles": (make_particles, ("N5", "N4", "N3")),
    "adjectives": (make_adjectives, LEVELS),
    "forms": (make_forms, ("N5", "N4", "N3")),
    "sentences": (make_sentences, ("N5", "N4")),
    "opposites": (make_opposites, ("N5", "N4", "N3")),
    "loanwords": (make_loanwords, ("N5", "N4", "N3")),
    "context": (make_context, ("N5", "N4")),
}


def make(family, level, seed):
    """(question, extras) for this exact id, or (None, {}) if that seed doesn't give a valid one.
    `extras["words"]` are (written, reading) pairs the furigana should know."""
    fn, levels = FAMILIES[family]
    if level not in levels:
        return None, {}
    rng = random.Random(f"{family}/{level}/{seed}")
    result = fn(rng, level, seed)
    return result if result[0] is not None else (None, {})


def rebuild(qid):
    """The dynamic question with this id (dyn_<family>_<level>_<seed>), or None."""
    try:
        _, family, level, seed = qid.split("_", 3)
        question, extras = make(family, level, int(seed))
        if question and question["id"] == qid:
            teach(extras)
            return question
        return None
    except (ValueError, KeyError):
        return None


def fresh(level, rng=random, count=8, exclude=()):
    """`count` brand-new questions at `level`, one family at a time in a random order."""
    families = [f for f, (_, levels) in FAMILIES.items() if level in levels]
    out = []
    tries = 0
    while len(out) < count and families and tries < count * 12:
        tries += 1
        family = families[tries % len(families)] if tries <= len(families) else rng.choice(families)
        question, extras = make(family, level, rng.randrange(1_000_000))
        if question and question["id"] not in exclude and all(q["id"] != question["id"] for q in out):
            teach(extras)
            out.append(question)
    return out


def teach(extras):
    from kobito import furigana
    for written, kana in extras.get("words", []):
        if written and kana:
            furigana.add_word(written, kana)

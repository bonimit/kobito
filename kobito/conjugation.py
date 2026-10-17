"""Japanese verb conjugation by rule, for the generated verb questions.

conjugate(verb, kind, form) works on the written form (食べる, 書く,
勉強する, 来る) and returns the conjugated written form. `kind` is "ru"
(ichidan), "u" (godan) or "irr" (する, 来る and ～する verbs).
"""

# Godan endings: the u-row character and its i / a / e / o row partners.
_ROWS = {
    "う": "いわえお", "く": "きかけこ", "ぐ": "ぎがげご", "す": "しさせそ", "つ": "ちたてと",
    "ぬ": "になねの", "ぶ": "びばべぼ", "む": "みまめも", "る": "りられろ",
}
_TE = {"う": "って", "つ": "って", "る": "って", "む": "んで", "ぶ": "んで", "ぬ": "んで",
       "く": "いて", "ぐ": "いで", "す": "して"}

# form id -> (English label used in prompts, JLPT level the form is taught at)
FORMS = {
    "masu": ("polite present (masu-form)", "N5"),
    "masen": ("polite negative", "N5"),
    "mashita": ("polite past", "N5"),
    "te": ("te-form", "N5"),
    "ta": ("plain past (ta-form)", "N5"),
    "nai": ("plain negative (nai-form)", "N5"),
    "potential": ("potential form (can ~)", "N4"),
    "volitional": ("volitional form (let's ~)", "N4"),
    "ba": ("conditional ba-form (if ~)", "N4"),
    "passive": ("passive form", "N4"),
    "causative": ("causative form (make / let ~)", "N3"),
}


def _godan(stem, end, row):
    return stem + _ROWS[end]["iaeo".index(row)]


def conjugate(verb, kind, form):
    if kind == "irr":
        if verb.endswith("する"):
            base = verb[:-2]
            return base + {
                "masu": "します", "masen": "しません", "mashita": "しました", "te": "して", "ta": "した",
                "nai": "しない", "potential": "できる", "volitional": "しよう", "ba": "すれば",
                "passive": "される", "causative": "させる",
            }[form]
        if verb in ("来る", "くる"):
            return _kuru("来" if verb == "来る" else "", form)
        raise ValueError(verb)
    stem, end = verb[:-1], verb[-1]
    if kind == "ru":
        return stem + {
            "masu": "ます", "masen": "ません", "mashita": "ました", "te": "て", "ta": "た", "nai": "ない",
            "potential": "られる", "volitional": "よう", "ba": "れば", "passive": "られる", "causative": "させる",
        }[form]
    if form in ("masu", "masen", "mashita"):
        return _godan(stem, end, "i") + {"masu": "ます", "masen": "ません", "mashita": "ました"}[form]
    if form in ("te", "ta"):
        te = "って" if verb in ("行く", "いく") else _TE[end]
        return stem + (te if form == "te" else te[:-1] + ("た" if te.endswith("て") else "だ"))
    if form == "nai":
        return _godan(stem, end, "a") + "ない"
    if form == "potential":
        return _godan(stem, end, "e") + "る"
    if form == "volitional":
        return _godan(stem, end, "o") + "う"
    if form == "ba":
        return _godan(stem, end, "e") + "ば"
    if form == "passive":
        return _godan(stem, end, "a") + "れる"
    if form == "causative":
        return _godan(stem, end, "a") + "せる"
    raise ValueError(form)


def _kuru(k, form):
    """来る: き- for the masu forms, te and ta; こ- for the rest; く- for ba."""
    reading = {"masu": "きます", "masen": "きません", "mashita": "きました", "te": "きて", "ta": "きた",
               "nai": "こない", "potential": "こられる", "volitional": "こよう", "ba": "くれば",
               "passive": "こられる", "causative": "こさせる"}[form]
    return (k + reading[1:]) if k else reading


def mistakes(verb, kind, form):
    """Common wrong answers for a form: the te/ta-form built like the masu
    stem (書きて), the wrong sound change (書って), a godan verb treated as
    ichidan (帰ます) and vice versa."""
    out = []
    if kind == "u":
        stem, end = verb[:-1], verb[-1]
        i_stem = _godan(stem, end, "i")
        if form == "te":
            out += [i_stem + "て", stem + ("って" if _TE[end] != "って" else "んで")]
        elif form == "ta":
            out += [i_stem + "た", stem + ("った" if _TE[end] != "って" else "んだ")]
        elif form == "nai":
            out += [i_stem + "ない", stem + "ない"]
        elif form == "masu" and end == "る":
            out += [stem + "ます"]
        elif form == "potential":
            out += [_godan(stem, end, "a") + "れる"]
    elif kind == "ru":
        stem = verb[:-1]
        if form == "nai":
            out += [stem + "らない"]
        elif form == "potential":
            out += [stem + "れる"]
        elif form == "volitional":
            out += [stem + "ろう"]
        elif form == "te":
            out += [stem + "って"]
    return out

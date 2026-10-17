"""Romaji -> hiragana, for the stage test's reading questions.

The game's word data carries readings in Hepburn romaji ("hoshi ume",
"gyuunyuu", "kin no kan"); to ask "how do you read 干し梅?" with hiragana
tiles we need ほしうめ. This is a small greedy converter for that data:
long vowels are written doubled (ou, uu, oo), a doubled consonant is a
small っ, and n before a consonant, an apostrophe or the end is ん
(kon'ya -> こんや). Spaces are dropped.
"""

import re

_SYLLABLES = {
    # three letters
    "kya": "きゃ", "kyu": "きゅ", "kyo": "きょ", "gya": "ぎゃ", "gyu": "ぎゅ", "gyo": "ぎょ",
    "sha": "しゃ", "shu": "しゅ", "sho": "しょ", "shi": "し", "chi": "ち", "cha": "ちゃ", "chu": "ちゅ",
    "cho": "ちょ", "tsu": "つ", "nya": "にゃ", "nyu": "にゅ", "nyo": "にょ", "hya": "ひゃ", "hyu": "ひゅ",
    "hyo": "ひょ", "bya": "びゃ", "byu": "びゅ", "byo": "びょ", "pya": "ぴゃ", "pyu": "ぴゅ", "pyo": "ぴょ",
    "mya": "みゃ", "myu": "みゅ", "myo": "みょ", "rya": "りゃ", "ryu": "りゅ", "ryo": "りょ",
    # two letters
    "ka": "か", "ki": "き", "ku": "く", "ke": "け", "ko": "こ", "ga": "が", "gi": "ぎ", "gu": "ぐ", "ge": "げ",
    "go": "ご", "sa": "さ", "su": "す", "se": "せ", "so": "そ", "za": "ざ", "ji": "じ", "zu": "ず", "ze": "ぜ",
    "zo": "ぞ", "ja": "じゃ", "ju": "じゅ", "jo": "じょ", "ta": "た", "te": "て", "to": "と", "da": "だ",
    "de": "で", "do": "ど", "na": "な", "ni": "に", "nu": "ぬ", "ne": "ね", "no": "の", "ha": "は", "hi": "ひ",
    "fu": "ふ", "he": "へ", "ho": "ほ", "ba": "ば", "bi": "び", "bu": "ぶ", "be": "べ", "bo": "ぼ", "pa": "ぱ",
    "pi": "ぴ", "pu": "ぷ", "pe": "ぺ", "po": "ぽ", "ma": "ま", "mi": "み", "mu": "む", "me": "め", "mo": "も",
    "ya": "や", "yu": "ゆ", "yo": "よ", "ra": "ら", "ri": "り", "ru": "る", "re": "れ", "ro": "ろ", "wa": "わ",
    "wo": "を",
    # vowels
    "a": "あ", "i": "い", "u": "う", "e": "え", "o": "お",
}
_VOWELS = set("aeiou")


def romaji_to_hiragana(romaji):
    """'hoshi ume' -> 'ほしうめ'; returns None if anything can't be converted."""
    text = re.sub(r"[\s\-]", "", romaji.lower())
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c == "'":   # kon'ya: the apostrophe only marks the ん
            i += 1
            continue
        if c == "n" and (i + 1 == len(text) or (text[i + 1] not in _VOWELS and text[i + 1] != "y")):
            out.append("ん")
            i += 1 + (i + 1 < len(text) and text[i + 1] == "n" and (i + 2 == len(text) or text[i + 2] not in _VOWELS))
            continue
        if c not in _VOWELS and i + 1 < len(text) and text[i + 1] == c:
            out.append("っ")   # doubled consonant: kk, tt, ss, pp ...
            i += 1
            continue
        for size in (3, 2, 1):
            chunk = text[i:i + size]
            if chunk in _SYLLABLES:
                out.append(_SYLLABLES[chunk])
                i += size
                break
        else:
            return None
    return "".join(out)


HIRAGANA = [chr(c) for c in range(ord("あ"), ord("ん") + 1)
            if chr(c) not in "ぁぃぅぇぉっゃゅょゎゐゑ"]


def has_kanji(text):
    return any("一" <= ch <= "鿿" or ch == "々" for ch in text)


def has_katakana(text):
    return any("゠" <= ch <= "ヿ" for ch in text)


def is_hiragana(text):
    return all("぀" <= ch <= "ゟ" for ch in text)

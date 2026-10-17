"""Furigana: small kana readings drawn above kanji, toggleable by the
player, plus a matching toggle for hiding/showing English translations.

READINGS maps a kanji substring to its reading for the *specific* way
that substring is used across assets/data/questions.json -- not a
general-purpose kanji dictionary. A few kanji are deliberately absent
(bare "一", "物", and all of "来" -- see the comments below) because
their correct reading depends on context this flat lookup can't
capture; showing no furigana is always safer than showing a wrong one.

Rendering (quiz_screen.py) tokenizes a line into words the same way it
already wraps text (splitting on spaces), then annotates each word by
greedily matching the longest known substring at each position within
its contiguous kanji runs -- so a compound like "何度見" resolves as
"何度" (registered whole) + "見" (single-kanji fallback) without
needing an entry for every possible concatenation.
"""

# Multi-kanji compounds and single-kanji stems, longest-match wins.
# Grouped roughly by where they came from for anyone auditing this list.
READINGS = {
    # --- compounds (glossed directly in explanations/hints) ---------
    "世界": "せかい", "価値": "かち", "便利": "べんり", "促進": "そくしん",
    "傾向": "けいこう", "先生": "せんせい", "効率": "こうりつ", "反対": "はんたい",
    "地図": "ちず", "妥協": "だきょう", "学校": "がっこう", "崩壊": "ほうかい",
    "巧妙": "こうみょう", "影響": "えいきょう", "循環": "じゅんかん", "心配": "しんぱい",
    "慎重": "しんちょう", "憂慮": "ゆうりょ", "憂鬱": "ゆううつ", "我慢": "がまん",
    "承認": "しょうにん", "把握": "はあく", "措置": "そち", "提案": "ていあん",
    "政治": "せいじ", "日本語": "にほんご", "曖昧": "あいまい", "期待": "きたい",
    "準備": "じゅんび", "特別": "とくべつ", "環境": "かんきょう", "病院": "びょういん",
    "矛盾": "むじゅん", "約束": "やくそく", "素直": "すなお", "経済": "けいざい",
    "経験": "けいけん", "苦手": "にがて", "説明": "せつめい", "象徴": "しょうちょう",
    "逸脱": "いつだつ", "遂行": "すいこう", "遠慮": "えんりょ", "陳列": "ちんれつ",
    "需要": "じゅよう", "顕著": "けんちょ", "買い物": "かいもの",
    "苦労": "くろう", "訪問": "ほうもん", "交通": "こうつう", "面倒": "めんどう",
    "工夫": "くふう", "状況": "じょうきょう", "割合": "わりあい", "潜在": "せんざい",
    "徹底": "てってい", "一致": "いっち", "展開": "てんかい", "円滑": "えんかつ",
    "愚痴": "ぐち", "余儀": "よぎ", "台風": "たいふう",

    # --- compounds identified from prompt/choice context ------------
    "一日": "いちにち", "一緒": "いっしょ", "一言": "ひとこと", "上司": "じょうし",
    "中止": "ちゅうし", "今年": "ことし", "仕事": "しごと", "余計": "よけい",
    "入院": "にゅういん", "全力": "ぜんりょく", "写真": "しゃしん", "努力": "どりょく",
    "勉強": "べんきょう", "去年": "きょねん", "友達": "ともだち", "合格": "ごうかく",
    "命令": "めいれい", "図書館": "としょかん", "土産": "みやげ", "失敗": "しっぱい",
    "学生": "がくせい", "実力": "じつりょく", "実行": "じっこう", "宿題": "しゅくだい",
    "富士山": "ふじさん", "寝坊": "ねぼう", "快方": "かいほう", "拝見": "はいけん",
    "教室": "きょうしつ", "文句": "もんく", "日本": "にほん", "早合点": "はやがてん",
    "明日": "あした", "映画": "えいが", "案内": "あんない", "毎日": "まいにち",
    "犯人": "はんにん", "理由": "りゆう", "生活習慣": "せいかつしゅうかん",
    "病気": "びょうき", "発言": "はつげん", "社長": "しゃちょう", "結果": "けっか",
    "練習": "れんしゅう", "職人": "しょくにん", "計画": "けいかく", "試合": "しあい",
    "試験": "しけん", "誤解": "ごかい", "説明書": "せつめいしょ", "資料": "しりょう",
    "逆": "ぎゃく", "遅刻": "ちこく", "野菜": "やさい", "電車": "でんしゃ",
    "音楽": "おんがく", "何度": "なんど", "際": "さい",

    # --- expression / loanword / reading questions --------------------
    # (whole idioms registered as one unit, so no single-kanji fallback
    # can mis-read them: 十人十色 is not ひと...)
    "七時": "しちじ", "百円": "ひゃくえん", "十五分": "じゅうごふん", "十時": "じゅうじ",
    "十一時": "じゅういちじ", "会社": "かいしゃ", "会議": "かいぎ", "金曜日": "きんようび",
    "日曜日": "にちようび", "元気": "げんき", "三回": "さんかい", "食事": "しょくじ",
    "部屋": "へや", "変更": "へんこう", "料理": "りょうり", "得意": "とくい",
    "全然": "ぜんぜん", "田中": "たなか", "山田": "やまだ", "問題": "もんだい",
    "一理": "いちり", "給料": "きゅうりょう", "天気予報": "てんきよほう", "素晴": "すば",
    "毎晩": "まいばん", "引": "ひ", "受": "う", "一石二鳥": "いっせきにちょう",
    "七転": "ななころ", "八起": "やお", "十人十色": "じゅうにんといろ", "団子": "だんご",
    "以心伝心": "いしんでんしん", "成功": "せいこう", "許可": "きょか", "責任": "せきにん",
    "彼女": "かのじょ", "笑顔": "えがお", "名作": "めいさく", "駅": "えき", "母": "はは",
    "兄": "あに", "持": "も", "薬": "くすり", "後": "あと", "店": "みせ", "寒": "さむ",
    "閉": "し", "猫": "ねこ", "借": "か", "広": "ひろ", "腕": "うで", "頭": "あたま",
    "軽": "かる", "忙": "いそが", "晴": "は", "猿": "さる", "落": "お", "花": "はな",
    "疲": "つか", "絶": "た", "知": "し", "休": "やす", "買": "か", "木": "き",

    # --- single kanji: verb/adjective stems (invariant across their
    #     regular conjugations -- 書く/書きます/書けば/書こう all use か) --
    "与": "あた", "会": "あ", "伺": "うかが", "加": "くわ", "参": "まい",
    "向": "む", "失": "うしな", "嫌": "きら", "尽": "つ", "帰": "かえ",
    "待": "ま", "得": "え", "忘": "わす", "応": "おう", "怒": "おこ",
    "承": "うけたまわ", "招": "まね", "撮": "と", "登": "のぼ", "立": "た",
    "組": "く", "沿": "そ", "泣": "な", "泳": "およ", "申": "もう",
    "痛": "いた", "行": "い", "見": "み", "直": "なお", "言": "い",
    "訳": "わけ", "話": "はな", "読": "よ", "謝": "あやま", "起": "お",
    "越": "こ", "遅": "おく", "違": "ちが", "開": "あ", "降": "ふ",
    "限": "かぎ", "聞": "き", "暑": "あつ", "暗": "くら", "書": "か",
    "比": "くら", "出": "だ", "多": "おお",

    # --- single kanji: nouns / kanji-quiz choices (given a reasonable
    #     default even where the question itself hides them -- see
    #     _suppress_furigana in quiz_screen.py for the kanji category) --
    "上": "うえ", "中": "なか", "人": "ひと", "低": "ひく", "何": "なに",
    "作": "つく", "使": "つか", "便": "べん", "働": "はたら", "口": "くち",
    "味": "あじ", "大": "おお", "学": "まな", "安": "やす", "小": "ちい",
    "少": "すく", "川": "かわ", "彼": "かれ", "悪": "わる", "手": "て",
    "技": "わざ", "教": "おし", "机": "つくえ", "校": "こう", "気": "き",
    "田": "た", "目": "め", "石": "いし", "私": "わたし", "空": "そら",
    "窓": "まど", "習": "なら", "耳": "みみ", "腹": "なか", "覧": "らん",
    "車": "くるま", "雨": "あめ", "顔": "かお", "飯": "はん", "飲": "の",
    "高": "たか", "昼": "ひる",

    # --- from earlier auto-extraction, single kanji -------------------
    "促": "うなが", "培": "つちか", "増": "ふ", "委": "ゆだ", "山": "やま",
    "巧": "たく", "急": "いそ", "新": "あたら", "水": "みず", "減": "へ",
    "潔": "いさぎよ", "珍": "めずら", "疎": "おろそ", "補": "おぎな",
    "覆": "くつがえ", "認": "みと", "調": "しら", "諦": "あきら", "貧": "まず",
    "迷": "まよ", "頼": "たよ", "食": "た", "本": "ほん", "犬": "いぬ",
    "遂": "つい",

    # NOTE: bare "一" (いち vs ひと-) and "物" (もの, not the trailing
    # "かいもの" one auto-extraction briefly mis-assigned it) are left
    # out deliberately -- ambiguous without more context than a flat
    # per-kanji lookup has. So is "来", whose reading genuinely changes
    # per conjugation (来い=こい but 来れば=くれば) in ways this lookup
    # can't distinguish -- showing no furigana beats showing a wrong one.
}

_enabled = True
_translation_visible = False


def is_enabled():
    return _enabled


def toggle():
    global _enabled
    _enabled = not _enabled
    return _enabled


def is_translation_visible():
    return _translation_visible


def toggle_translation():
    global _translation_visible
    _translation_visible = not _translation_visible
    return _translation_visible


def annotate_word(word):
    """Splits one space-delimited word into (text, reading_or_None)
    segments, by greedily matching the longest known substring at each
    position within the word's kanji runs. Non-kanji runs (kana, ASCII,
    punctuation) pass through as a single segment with reading None.
    """
    segments = []
    i = 0
    length = len(word)
    while i < length:
        char = word[i]
        if _is_kanji(char):
            match_len, reading = _longest_match(word, i)
            if reading:
                segments.append((word[i:i + match_len], reading))
                i += match_len
                continue
            # No reading known for this kanji -- emit it plain and move
            # on one character at a time so a later kanji in the same
            # run can still find its own match.
            segments.append((char, None))
            i += 1
        else:
            j = i
            while j < length and not _is_kanji(word[j]):
                j += 1
            segments.append((word[i:j], None))
            i = j
    return _merge_plain_runs(segments)


def _longest_match(word, start):
    """Longest READINGS key starting at `start` that stays within the
    contiguous kanji run beginning there. Returns (length, reading) or
    (0, None).
    """
    end = start
    while end < len(word) and _is_kanji(word[end]):
        end += 1
    for candidate_end in range(end, start, -1):
        candidate = word[start:candidate_end]
        reading = READINGS.get(candidate)
        if reading:
            return candidate_end - start, reading
    return 0, None


def _merge_plain_runs(segments):
    """Adjacent reading=None segments (e.g. a kanji with no known
    reading followed by trailing kana) collapse into one, so rendering
    doesn't insert phantom gaps between them.
    """
    merged = []
    for text, reading in segments:
        if reading is None and merged and merged[-1][1] is None:
            merged[-1] = (merged[-1][0] + text, None)
        else:
            merged.append((text, reading))
    return merged


def _is_kanji(char):
    return "一" <= char <= "鿿"

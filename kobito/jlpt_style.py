"""Questions in the shape of the real JLPT papers, written fresh for Kobito.

The Japan Foundation's sample papers use a handful of question types at every
level, and these follow them (the sentences and words are our own, not the
exam's). Each has an English instruction up front, then the Japanese:

  reading     -- how is the 【marked】 word read?               (category: kanji)
  writing     -- which kanji / katakana writes 【the kana】?     (kanji)
  fill        -- the word that fits （　　）                      (vocabulary)
  grammar     -- the form that fits （　　）                      (grammar)
  meaning     -- the sentence / word closest in meaning          (vocabulary)
  usage       -- which sentence uses the word correctly?         (vocabulary)
  ordering    -- the ★ puzzle: the piece in the third blank      (sentence)
  cloze       -- the connecting word that fits a short text      (grammar)
  passage     -- a short text and a question about it            (reading)

The furigana switch is off for reading / writing questions (a ruby over the
word would give the answer away). Wrong choices come in pools of three or
more: where an item has extra ones, every ask draws a different three
(question_gen.reroll), so the options can't be memorised either.
"""

# Each row: (level, ...)  -- see the builders at the bottom for the layout.

READING = [  # (level, sentence with 【word】, right, wrongs, explanation)
    ("N5", "毎朝、【新聞】を読みます。", "しんぶん", ["しんもん", "じんぶん", "しんふん", "しんぼん"], "新聞 (しんぶん) is a newspaper."),
    ("N5", "【友達】といっしょに昼ごはんを食べました。", "ともだち", ["ともたち", "ゆうたち", "ともだい", "ゆうだち"], "友達 (ともだち) is a friend."),
    ("N5", "わたしの【母】は病院で働いています。", "はは", ["ちち", "あに", "あね", "かか"], "母 (はは) is my mother; 父 is ちち."),
    ("N5", "【来週】、京都へ行きます。", "らいしゅう", ["らいしゅ", "くるしゅう", "らいじゅう", "らいしょう"], "来週 (らいしゅう) is next week."),
    ("N5", "【電話】で友達と話しました。", "でんわ", ["てんわ", "でんは", "でんぱ", "でんか"], "電話 (でんわ) is a telephone."),
    ("N5", "この本は【高い】です。", "たかい", ["こうい", "たけい", "ながい", "たがい"], "高い (たかい) means expensive or tall."),
    ("N4", "来週、会議が【開かれます】。", "ひらかれます", ["あかれます", "ひらけます", "かいかれます", "ひろかれます"], "開かれる (ひらかれる) is the passive of 開く: to be held."),
    ("N4", "この辞書を【貸して】ください。", "かして", ["かえして", "かりて", "かさして", "かせて"], "貸す (かす) is to lend; 借りる is to borrow."),
    ("N4", "旅行の【準備】はできましたか。", "じゅんび", ["しゅんび", "じゅうんび", "じゅんぴ", "じゅんひ"], "準備 (じゅんび) is preparation."),
    ("N4", "この町は【交通】が便利です。", "こうつう", ["こうとう", "きょうつう", "こうづう", "こうっつう"], "交通 (こうつう) is traffic or transport."),
    ("N4", "先生に【質問】しました。", "しつもん", ["しっもん", "しつぶん", "しちもん", "しつもう"], "質問 (しつもん) is a question."),
    ("N4", "彼は毎日【運動】しています。", "うんどう", ["うんとう", "うんどお", "ゆんどう", "うんろう"], "運動 (うんどう) is exercise."),
    ("N3", "彼の意見に【賛成】します。", "さんせい", ["さんぜい", "ざんせい", "さんしょう", "さんせ"], "賛成 (さんせい) means to agree."),
    ("N3", "台風で電車が【遅れて】いる。", "おくれて", ["おそれて", "のこれて", "おくれで", "おそくて"], "遅れる (おくれる) is to be late."),
    ("N3", "彼女の【努力】は認められた。", "どりょく", ["ぬりょく", "どうりょく", "どりき", "どりょうく"], "努力 (どりょく) is effort."),
    ("N3", "【経験】を積むことが大切だ。", "けいけん", ["けいげん", "きょうけん", "けいけい", "けいけ"], "経験 (けいけん) is experience."),
    ("N3", "【災害】に備えて、水を用意する。", "さいがい", ["ざいがい", "さいかい", "さいげ", "さいがえ"], "災害 (さいがい) is a disaster."),
    ("N3", "会議の【資料】を配る。", "しりょう", ["しりょ", "しろう", "じりょう", "しれう"], "資料 (しりょう) is materials or data."),
    ("N2", "彼は責任を【負う】覚悟を決めた。", "おう", ["ふう", "はう", "になう", "もう"], "負う (おう) is to bear (a responsibility)."),
    ("N2", "景気が【回復】する兆しが見える。", "かいふく", ["かいぷく", "かえふく", "かいひく", "かいふぐ"], "回復 (かいふく) is recovery."),
    ("N2", "病気で体力が【衰えた】。", "おとろえた", ["すいえた", "おとえた", "おとろいた", "おとろえだ"], "衰える (おとろえる) is to weaken."),
    ("N2", "工事の騒音が【著しい】。", "いちじるしい", ["ちょじるしい", "あきらしい", "いちしるしい", "いちじろしい"], "著しい (いちじるしい) is striking or marked."),
    ("N2", "国の【財政】は厳しい。", "ざいせい", ["さいせい", "ざいぜい", "ぞいせい", "ざいせ"], "財政 (ざいせい) is finances."),
    ("N2", "彼の発言は【誤解】を招いた。", "ごかい", ["ごがい", "ごかん", "ぐかい", "ごけ"], "誤解 (ごかい) is a misunderstanding."),
    ("N1", "彼は新しい制度に【抗議】した。", "こうぎ", ["こうき", "こうげ", "ごうぎ", "こうじ"], "抗議 (こうぎ) is a protest."),
    ("N1", "この計画は【概ね】順調だ。", "おおむね", ["おおね", "がいむね", "おおよね", "おおむめ"], "概ね (おおむね) means generally."),
    ("N1", "意見の【偏り】をなくす。", "かたより", ["かたぶり", "へんより", "かたまり", "かたよう"], "偏り (かたより) is a bias."),
    ("N1", "支払いが【滞る】。", "とどこおる", ["とどまる", "たいおる", "とどこる", "とどこうる"], "滞る (とどこおる) is to fall behind or stagnate."),
    ("N1", "彼に注意を【促す】。", "うながす", ["そくす", "たすがす", "うなかす", "うながる"], "促す (うながす) is to urge or prompt."),
    ("N1", "雨の日は【憂鬱】になる。", "ゆううつ", ["ゆうゆう", "ゆうつ", "ゆううっ", "ゆうゆつ"], "憂鬱 (ゆううつ) is gloom."),
]

WRITING = [  # (level, sentence with 【kana】, right, wrongs, explanation)
    ("N5", "【ともだち】と遊びます。", "友達", ["友連", "反達", "友違", "支達"], "友達 (ともだち): friend."),
    ("N5", "【でんしゃ】に乗ります。", "電車", ["雷車", "電東", "電軍", "電庫"], "電車 (でんしゃ): train."),
    ("N5", "【せんせい】はやさしいです。", "先生", ["失生", "先主", "光生", "先正"], "先生 (せんせい): teacher."),
    ("N5", "コップの【みず】を飲みます。", "水", ["氷", "永", "木", "冰"], "水 (みず): water."),
    ("N5", "【やすみ】の日に公園へ行きます。", "休み", ["体み", "伏み", "林み", "仕み"], "休み (やすみ): a day off."),
    ("N5", "【あたらしい】くつを買いました。", "新しい", ["親しい", "薪しい", "新らしい", "断しい"], "新しい (あたらしい): new."),
    ("N5", "これは【てれび】です。", "テレビ", ["テレピ", "チレビ", "テレヒ", "デレビ"], "テレビ: TV (watch ビ, not ピ)."),
    ("N5", "【すーぱー】で買い物をします。", "スーパー", ["ヌーパー", "スーバー", "スーハー", "ス一パー"], "スーパー: supermarket."),
    ("N5", "【くらす】のみんなと歌います。", "クラス", ["ケラス", "クラヌ", "タラス", "クラズ"], "クラス: class."),
    ("N4", "会社まで【ちかい】です。", "近い", ["折い", "沂い", "斤い", "辺い"], "近い (ちかい): near."),
    ("N4", "【びょういん】へ行きます。", "病院", ["痛院", "病完", "病陰", "疾院"], "病院 (びょういん): hospital."),
    ("N4", "【しゅくだい】を忘れました。", "宿題", ["宿類", "宿顕", "福題", "宿頭"], "宿題 (しゅくだい): homework."),
    ("N4", "先生に【おしえて】もらいました。", "教えて", ["数えて", "救えて", "叔えて", "孝えて"], "教える (おしえる): to teach."),
    ("N4", "【せいかつ】はたいへんです。", "生活", ["生話", "主活", "生括", "性活"], "生活 (せいかつ): life, living."),
    ("N4", "【ぱーてぃー】に行きます。", "パーティー", ["ハーテイー", "パーテイー", "バーティー", "パーデイー"], "パーティー: party (watch パ and ィ)."),
    ("N3", "【けんきゅう】を続ける。", "研究", ["研空", "研宄", "砂究", "研完"], "研究 (けんきゅう): research."),
    ("N3", "車が【とまる】。", "止まる", ["上まる", "正まる", "企まる", "歩まる"], "止まる (とまる): to stop."),
    ("N3", "駅の【ちかく】に住んでいる。", "近く", ["折く", "斤く", "辺く", "沂く"], "近く (ちかく): near."),
    ("N3", "計画を【へんこう】する。", "変更", ["変吏", "恋更", "変便", "変史"], "変更 (へんこう): change."),
    ("N3", "【こうつう】事故が増えた。", "交通", ["校通", "父通", "文通", "効通"], "交通 (こうつう): traffic."),
    ("N2", "【かんきょう】を守る。", "環境", ["還境", "環鏡", "環竟", "環意"], "環境 (かんきょう): environment."),
    ("N2", "事故の【げんいん】を調べる。", "原因", ["源因", "原困", "厡因", "原囚"], "原因 (げんいん): cause."),
    ("N2", "彼は【ほうこく】書を提出した。", "報告", ["報苦", "幸告", "報吉", "報古"], "報告 (ほうこく): report."),
    ("N2", "【ぎじゅつ】が進歩する。", "技術", ["枝術", "技述", "支術", "技衛"], "技術 (ぎじゅつ): technology."),
    ("N2", "物価が【じょうしょう】する。", "上昇", ["上昌", "工昇", "上斗", "上早"], "上昇 (じょうしょう): to rise."),
    ("N1", "【ぎせい】をはらう。", "犠牲", ["儀牲", "議牲", "義牲", "犠性"], "犠牲 (ぎせい): sacrifice."),
    ("N1", "【かんけつ】にまとめる。", "簡潔", ["簡結", "管潔", "間潔", "簡決"], "簡潔 (かんけつ): concise."),
    ("N1", "【ひょうばん】が高い。", "評判", ["平判", "評半", "評叛", "評料"], "評判 (ひょうばん): reputation."),
    ("N1", "【ほうしゅう】を受け取る。", "報酬", ["報州", "報洲", "幸酬", "報醜"], "報酬 (ほうしゅう): reward, pay."),
    ("N1", "【きぼ】を拡大する。", "規模", ["現模", "規摸", "視模", "規摸"][:3] + ["規糢"], "規模 (きぼ): scale."),
]

FILL = [  # vocabulary: (level, sentence with （　　）, right, wrongs, explanation, hint)
    ("N5", "朝ごはんにパンを（　　）。", "食べました", ["飲みました", "見ました", "聞きました", "買いました"], "You eat bread: 食べる.", "Which verb goes with bread?"),
    ("N5", "暑いので、窓を（　　）ください。", "あけて", ["しめて", "つけて", "けして", "おして"], "窓をあける: open the window.", "You want fresh air."),
    ("N5", "この本は三千円です。とても（　　）です。", "高い", ["低い", "長い", "重い", "近い"], "Three thousand yen for a book: expensive.", "Think about the price."),
    ("N5", "朝、6時に（　　）。", "起きます", ["寝ます", "休みます", "止まります", "終わります"], "朝 + 六時に: you get up.", "What do you do in the morning?"),
    ("N5", "雨ですから、かさを（　　）行きましょう。", "さして", ["かけて", "はいて", "きて", "もって"], "かさをさす: put up an umbrella.", "An umbrella is 'stabbed' up: さす."),
    ("N5", "駅まで歩いて十分（　　）。", "かかります", ["あります", "います", "なります", "できます"], "時間がかかる: it takes time.", "How long it takes: かかる."),
    ("N4", "駅で友達が来るのを（　　）います。", "待って", ["持って", "打って", "立って", "取って"], "待つ: to wait.", "A friend hasn't arrived yet."),
    ("N4", "本を図書館に（　　）に行きます。", "返し", ["貸し", "売り", "買い", "借り"], "返す: to return something.", "You are bringing it back."),
    ("N4", "ねつがあるので、今日は会社を（　　）。", "休みます", ["やめます", "すてます", "止めます", "切ります"], "会社を休む: take a day off.", "A fever means you stay home."),
    ("N4", "彼は英語がとても（　　）ので、通訳の仕事をしています。", "上手な", ["下手な", "苦手な", "きらいな", "不便な"], "上手: skilled.", "An interpreter must be good at it."),
    ("N4", "重い荷物を（　　）ので、手が痛くなりました。", "持った", ["打った", "切った", "見た", "思った"], "荷物を持つ: carry luggage.", "Heavy luggage hurts your hands."),
    ("N4", "雨が降っているので、試合は（　　）になりました。", "中止", ["中心", "注意", "中学", "宿題"], "中止: called off.", "The game won't happen."),
    ("N3", "テストが終わって、（　　）した。", "ほっと", ["ぴったり", "しっかり", "はっきり", "ゆっくり"], "ほっとする: to feel relieved.", "How you feel when it's over."),
    ("N3", "彼は自分の失敗を（　　）ようとしなかった。", "認め", ["決め", "守り", "止め", "守っ"], "失敗を認める: admit a failure.", "He wouldn't say it was his mistake."),
    ("N3", "山道は危ないので、（　　）に運転してください。", "慎重", ["乱暴", "簡単", "自由", "失礼"], "慎重に: carefully.", "A dangerous road needs care."),
    ("N3", "雨が続いて、野菜の値段が（　　）している。", "上昇", ["上達", "向上", "上品", "上手"], "値段が上昇する: prices rise.", "A price goes up."),
    ("N3", "この靴は足に（　　）合って、とても歩きやすい。", "ぴったり", ["すっかり", "ゆっくり", "しっかり", "はっきり"], "ぴったり合う: fit perfectly.", "Shoes that fit just right."),
    ("N3", "この問題は難しすぎて、（　　）が立たない。", "歯", ["手", "足", "目", "口"], "歯が立たない: can't make a dent in it.", "A set phrase about teeth."),
    ("N2", "景気の悪化で、会社の利益が（　　）した。", "減少", ["拡大", "増加", "成長", "上昇"], "利益が減少する: profit declines.", "Bad economy, so profit..."),
    ("N2", "彼は会議で自分の考えを（　　）に述べた。", "率直", ["勝手", "余計", "無理", "不満"], "率直に: frankly.", "Saying what you think, openly."),
    ("N2", "台風の影響で、飛行機の出発が（　　）された。", "延期", ["延長", "延命", "延滞", "延焼"], "延期: postponed.", "The date is pushed back."),
    ("N2", "彼女は優勝を逃して、（　　）涙を流した。", "悔し", ["苦し", "恐ろし", "厳し", "忙し"], "悔し涙: tears of frustration.", "Missing a win."),
    ("N2", "新しい制度について、国民の理解を（　　）必要がある。", "得る", ["守る", "保つ", "抑える", "止める"], "理解を得る: win understanding.", "A fixed pairing with 理解."),
    ("N2", "彼の話は説得力があって、（　　）聞き入ってしまった。", "つい", ["ざっと", "きっぱり", "せっかく", "せめて"], "つい: before I knew it.", "You listened without meaning to."),
    ("N1", "事件の（　　）が明らかになった。", "全容", ["全額", "全域", "全盛", "全員"], "全容: the whole picture.", "What came to light about the case."),
    ("N1", "彼は組織の腐敗を（　　）した。", "告発", ["告示", "通告", "警告", "広告"], "告発: to denounce, expose.", "Exposing wrongdoing."),
    ("N1", "長引く不況で、中小企業は（　　）に立たされている。", "窮地", ["境地", "窮屈", "境内", "苦地"], "窮地に立つ: be in a tight spot.", "A corner you can't get out of."),
    ("N1", "彼は周囲の反対を（　　）して、計画を実行した。", "押し切って", ["押し上げて", "押し込んで", "押し返して", "押し出して"], "反対を押し切る: override opposition.", "He pushed through."),
    ("N1", "この薬は副作用の（　　）がある。", "おそれ", ["こわれ", "あやうれ", "あぶれ", "うれい"], "～のおそれがある: there is a risk of.", "A formal word for 'risk'."),
    ("N1", "彼女は失敗を恐れず、果敢に（　　）に挑んだ。", "難題", ["難民", "難所", "難聴", "難色"], "難題に挑む: take on a hard problem.", "Something hard to solve."),
]

GRAMMAR = [  # (level, sentence with （　　）, right, wrongs, explanation, hint)
    ("N5", "わたしは毎日七時（　　）起きます。", "に", ["を", "で", "が", "と"], "に marks a point in time.", "A clock time takes に."),
    ("N5", "これはだれ（　　）かばんですか。", "の", ["を", "に", "で", "が"], "の links owner and thing.", "Whose bag?"),
    ("N5", "友達（　　）プレゼントをあげました。", "に", ["を", "で", "が", "の"], "に marks the person who receives.", "Who got the present?"),
    ("N5", "今日は寒い（　　）、セーターを着ます。", "ので", ["のに", "ても", "ながら", "けど"], "ので gives a reason.", "A reason for the sweater."),
    ("N5", "日本語を勉強して（　　）。", "います", ["あります", "なります", "できます", "いきます"], "～ています: ongoing.", "An action in progress."),
    ("N5", "この部屋に入っ（　　）いいですか。", "ても", ["ては", "でも", "ずに", "ながら"], "～てもいいですか: may I?", "Asking permission."),
    ("N4", "この本は友達（　　）借りました。", "から", ["まで", "を", "で", "へ"], "から marks the source.", "Where it came from."),
    ("N4", "先生にほめ（　　）、うれしかったです。", "られて", ["させて", "たがって", "ろうと", "ないで"], "ほめられる: be praised (passive).", "The teacher did it to me."),
    ("N4", "毎日練習した（　　）、上手になりました。", "おかげで", ["せいで", "くせに", "ばかりに", "あげく"], "おかげで: thanks to (good result).", "A good outcome."),
    ("N4", "もっと早く起きれば、電車に間に合った（　　）。", "のに", ["ても", "ながら", "ところ", "ように"], "～のに: regret about what didn't happen.", "If only I had..."),
    ("N4", "彼は日本に十年も住んでいる（　　）、日本語が下手です。", "のに", ["ので", "から", "ために", "ように"], "のに: although.", "A surprising contrast."),
    ("N4", "試験の前の日は早く寝る（　　）いいです。", "ほうが", ["ことが", "ところが", "ものが", "のが"], "～ほうがいい: had better.", "Giving advice."),
    ("N4", "A「この本、おもしろいですよ。」B「そうですか。わたしも（　　）たいです。」", "読み", ["読んで", "読む", "読んだ", "読め"], "～たい attaches to the ます-stem.", "want to read"),
    ("N4", "A「どこにかさをおきましたか。」B「げんかんに（　　）あります。」", "おいて", ["おく", "おき", "おかれ", "おけ"], "～てあります: placed on purpose.", "The state after placing."),
    ("N4", "A「ここでたばこをすってもいいですか。」B「いいえ、すっては（　　）。」", "いけません", ["いいです", "ありません", "できません", "なりたい"], "～てはいけません: must not.", "Refusing permission."),
    ("N3", "彼は学生（　　）、高い時計を持っている。", "なのに", ["だから", "ながら", "たびに", "として"], "なのに: even though.", "Surprising for a student."),
    ("N3", "この薬は食事の（　　）飲んでください。", "後で", ["前で", "中で", "横で", "上で"], "食事の後で: after the meal.", "When to take the medicine."),
    ("N3", "頑張った（　　）、試験に落ちてしまった。", "のに", ["ので", "ほど", "まで", "から"], "のに: despite.", "Trying hard but failing."),
    ("N3", "たとえ雨が降った（　　）、試合は行います。", "としても", ["ために", "ので", "ながら", "ように"], "たとえ～としても: even if.", "Rain won't stop it."),
    ("N3", "部長は会議中（　　）、電話に出られません。", "なので", ["だけど", "ように", "らしく", "ながら"], "なので: because.", "They are in a meeting."),
    ("N3", "来週日本へ行く（　　）、パスポートを取った。", "ために", ["ように", "ながら", "つもり", "あまり"], "ために: for the purpose of.", "Action toward a goal."),
    ("N2", "努力した（　　）、成功するとは限らない。", "からといって", ["ばかりか", "にしては", "どころか", "ものだから"], "～からといって～とは限らない.", "Because of X doesn't mean Y."),
    ("N2", "彼は日本語が上手だ（　　）、漢字はあまり読めない。", "とはいえ", ["ばかりに", "ほど", "に対して", "からには"], "とはいえ: even so.", "Granting something, then qualifying."),
    ("N2", "この仕事は経験者（　　）できない。", "でなければ", ["のみならず", "ともなると", "にあたって", "をはじめ"], "でなければ～ない: only if.", "Only experienced people."),
    ("N2", "試合に負けた（　　）、彼はさわやかな顔をしていた。", "にもかかわらず", ["ものだから", "ところで", "ことだし", "からには"], "にもかかわらず: despite.", "Losing but looking bright."),
    ("N2", "あの人はまるで先生である（　　）話す。", "かのように", ["わけに", "ものか", "ままに", "ところに"], "かのように: as if.", "Talking like a teacher."),
    ("N2", "雨が降ろう（　　）、必ず出発する。", "が", ["に", "を", "も", "へ"], "～ようが: no matter if.", "Come rain or shine."),
    ("N1", "医者（　　）者が、患者の命を軽く扱うとは許せない。", "ともあろう", ["たりとも", "ならでは", "ずくめの", "だらけの"], "～ともあろう者が: someone who should know better.", "A person with such a position."),
    ("N1", "一円（　　）無駄にできない。", "たりとも", ["ともなれば", "とあれば", "ながらも", "ならでは"], "～たりとも～ない: not even one.", "Not even one yen."),
    ("N1", "あの店の味は、店主の長年の経験（　　）。", "ならではだ", ["だらけだ", "めいている", "まみれだ", "ずくめだ"], "～ならでは: only possible with.", "Something unique to the owner."),
    ("N1", "彼の態度は謝罪する（　　）、開き直っている。", "どころか", ["ともなく", "ずにはおかない", "が早いか", "かたわら"], "～どころか: far from.", "The opposite of apologising."),
    ("N1", "彼女の話を聞く（　　）、涙が止まらなくなった。", "や否や", ["とはいえ", "ともなれば", "きらいがある", "ずじまい"], "～や否や: the moment.", "As soon as she began..."),
]

MEANING = [  # (level, instruction-kind, stem, right, wrongs, explanation)  stem has 【】 for a word, or is a sentence
    ("N5", "sentence", "このへやはせまいです。", "このへやは広くありません。", ["このへやは明るくありません。", "このへやはきれいではありません。", "このへやは古くありません。"], "せまい is the opposite of 広い."),
    ("N5", "sentence", "兄は昨日、学校を休みました。", "兄は昨日、学校へ行きませんでした。", ["兄は昨日、学校で勉強しました。", "兄は昨日、学校に来ました。", "兄は昨日、学校を出ました。"], "休む: to be absent."),
    ("N5", "sentence", "テストはむずかしくなかったです。", "テストはやさしかったです。", ["テストはむずかしかったです。", "テストは長かったです。", "テストは少なかったです。"], "むずかしくない ≈ やさしい."),
    ("N4", "word", "【けっこう】おいしいですね。", "かなり", ["ぜんぜん", "あまり", "ちっとも", "めったに"], "けっこう ≈ かなり: quite."),
    ("N4", "word", "宿題を【すぐ】出します。", "さっそく", ["ゆっくり", "たまに", "ときどき", "ずっと"], "すぐ ≈ さっそく: right away."),
    ("N4", "word", "今日は【とても】寒いです。", "ひじょうに", ["すこし", "あまり", "めったに", "ほとんど"], "とても ≈ ひじょうに: very."),
    ("N3", "word", "【ただちに】行ってください。", "すぐに", ["ゆっくり", "あとで", "ときどき", "ずっと"], "ただちに ≈ すぐに: immediately."),
    ("N3", "word", "この話は【だいたい】わかった。", "ほとんど", ["ぜんぜん", "きっと", "たいへん", "たまに"], "だいたい ≈ ほとんど: mostly."),
    ("N3", "word", "彼は【しばしば】遅刻する。", "よく", ["たまに", "まれに", "すぐに", "ずっと"], "しばしば ≈ よく: often."),
    ("N2", "word", "彼の話は【あいまい】だった。", "はっきりしなかった", ["面白くなかった", "長かった", "難しかった", "うれしかった"], "あいまい: vague."),
    ("N2", "word", "この仕事は【ひとまず】終わった。", "とりあえず", ["ようやく", "すっかり", "ちっとも", "ときどき"], "ひとまず ≈ とりあえず: for now."),
    ("N2", "word", "彼女は【あわてて】部屋を出た。", "急いで", ["静かに", "ゆっくり", "怒って", "笑って"], "あわてる: to hurry in a panic."),
    ("N1", "word", "彼は計画を【着々と】進めている。", "順調に少しずつ", ["ひそかに", "急いで", "勝手に", "いやいや"], "着々と: steadily."),
    ("N1", "word", "その発言は【軽率】だ。", "よく考えていない", ["礼儀正しい", "大げさだ", "正直だ", "冷たい"], "軽率: thoughtless, rash."),
    ("N1", "word", "彼女は周囲に【気兼ね】して何も言えなかった。", "遠慮", ["反対", "心配", "期待", "怒り"], "気兼ね ≈ 遠慮: hesitation out of consideration."),
]

USAGE = [  # (level, word, right sentence, three wrong sentences, explanation)
    ("N4", "ちょうど", "駅に着いたら、ちょうど電車が来た。", ["今日はちょうど暑すぎて外へ行かなかった。", "ちょうど友達と毎日会っている。", "この荷物はちょうど重くて持てない。"], "ちょうど: just at that moment / exactly."),
    ("N4", "すっかり", "雨がやんで、空がすっかり晴れた。", ["先生の質問はすっかりむずかしい。", "昨日の試合はすっかり負けるかもしれない。", "すっかり田中さんに電話してみよう。"], "すっかり: completely (a change finished)."),
    ("N4", "さっき", "さっき友達から電話がありました。", ["さっき来週の会議に出ます。", "明日はさっき雨が降るでしょう。", "さっき買うつもりです。"], "さっき: a little while ago (past)."),
    ("N3", "さっそく", "友達に教えてもらった店へさっそく行ってみた。", ["今日は朝からさっそく雨が降っている。", "先週さっそく引っ越しをした。", "彼はさっそく昼ごはんを食べるのが好きだ。"], "さっそく: right away, promptly."),
    ("N3", "うっかり", "うっかり財布を家に忘れてしまった。", ["うっかり勉強して合格した。", "試合にうっかり勝つために練習する。", "彼はうっかり約束を守る人だ。"], "うっかり: carelessly, by mistake."),
    ("N3", "めったに", "彼はめったに怒らない。", ["めったに毎日運動している。", "めったに雨が降っている。", "彼女はめったに優しい。"], "めったに + negative: rarely."),
    ("N2", "ひたすら", "彼はひたすら走り続けた。", ["今日はひたすら暑くて気温が高い。", "このケーキはひたすら甘い。", "彼女はひたすら若く見える。"], "ひたすら: single-mindedly (an action)."),
    ("N2", "かろうじて", "終電にかろうじて間に合った。", ["今日はかろうじて天気がよかった。", "かろうじて練習したので優勝した。", "彼はかろうじて毎日運動する。"], "かろうじて: barely, just managing."),
    ("N2", "あくまで", "これはあくまで私の個人的な意見です。", ["彼はあくまで速く走った。", "台風で、あくまで電車が止まった。", "あくまで今日は雨が降った。"], "あくまで: strictly, after all."),
    ("N1", "くまなく", "警察は現場をくまなく調べた。", ["今日はくまなく晴れている。", "彼はくまなく走っていった。", "彼女の話はくまなく面白かった。"], "くまなく: into every corner."),
    ("N1", "ことごとく", "彼の提案はことごとく反対された。", ["ことごとく一人だけ参加した。", "今日はことごとく疲れた。", "彼はことごとく会議に出た人だ。"], "ことごとく: every single one."),
    ("N1", "ねぎらう", "社長は社員の苦労をねぎらった。", ["先生は生徒の失敗をねぎらった。", "彼は道に迷った人をねぎらって警察に連れて行った。", "大雪で道路がねぎらわれた。"], "ねぎらう: to thank someone for their effort."),
]

# The ★ puzzle: (level, text before, four pieces in the right order, text after, English, why).
# The ★ is the third blank, as in the real paper: the answer is the third piece.
ORDERING = [
    ("N5", "あそこに", ["本を", "読んで", "いる", "人"], "は田中さんです。", "The person reading a book over there is Mr Tanaka.", "読んでいる makes 'is reading'; it describes 人."),
    ("N5", "これは", ["わたしの", "ともだちの", "おかあさんの", "くるま"], "です。", "This is my friend's mother's car.", "Each の hands over to the next owner."),
    ("N5", "あの", ["メガネを", "かけて", "いる", "人は"], "私の先生です。", "The person wearing glasses is my teacher.", "メガネをかけている describes 人."),
    ("N4", "あの", ["赤い", "セーターを", "着ている", "人は"], "山田さんです。", "The person in the red sweater is Ms Yamada.", "The describing phrase comes before 人."),
    ("N4", "この", ["本は", "漢字が", "多くて", "とても"], "むずかしいです。", "This book has many kanji and is very difficult.", "Topic, then reason (多くて), then とても + the adjective."),
    ("N4", "先生の", ["説明を", "聞いて", "やっと", "意味が"], "わかりました。", "After hearing the teacher's explanation I finally understood.", "やっと goes right before what finally happened."),
    ("N4", "雨が", ["降っている", "のに", "かさを", "持たずに"], "出かけました。", "I went out without an umbrella even though it was raining.", "のに follows 降っている."),
    ("N3", "この", ["歌を", "聞く", "たびに", "故郷を"], "思い出す。", "Every time I hear this song I think of home.", "～たびに follows the dictionary form."),
    ("N3", "あの", ["本を", "書いた", "人", "は"], "有名な作家だ。", "The person who wrote that book is a famous author.", "The clause 本を書いた describes 人."),
    ("N3", "彼の", ["話を", "聞いて", "いると", "不安で"], "ならない。", "Listening to him makes me anxious.", "～ていると: while doing; 不安でならない: can't help being anxious."),
    ("N2", "実際に", ["やってみない", "ことには", "うまくいくか", "どうか"], "わからない。", "Unless we actually try, we can't know if it will work.", "～ないことには～ない: unless."),
    ("N2", "あの人は", ["目上の人に", "対して", "さえ", "平気で"], "失礼なことを言う。", "He says rude things even to his seniors.", "に対して + さえ: even towards."),
    ("N1", "この問題は", ["個人の", "努力", "のみ", "では"], "解決できない。", "This problem can't be solved by individual effort alone.", "のみ + では: by ... alone."),
    ("N1", "締め切りが", ["迫って", "いるにも", "かかわらず", "仕事が"], "終わらない。", "The work isn't done even though the deadline is near.", "にもかかわらず: despite."),
]

CLOZE = [  # (level, text with （　　）, right, wrongs, explanation)
    ("N5", "きのうは雨でした。（　　）、どこへも行きませんでした。", "それで", ["でも", "しかし", "ところで"], "それで: so, as a result."),
    ("N5", "わたしは犬が好きです。（　　）、ねこも好きです。", "そして", ["でも", "しかし", "それで"], "そして: and."),
    ("N4", "弟は毎日ゲームをしています。（　　）、宿題はぜんぜんしません。", "でも", ["だから", "それで", "そして"], "でも: but."),
    ("N4", "雨が降ってきました。（　　）、かさを買いました。", "それで", ["でも", "しかし", "ところで"], "それで: so."),
    ("N4", "来週テストがあります。（　　）、毎日勉強しています。", "だから", ["でも", "しかし", "ところが"], "だから: therefore."),
    ("N3", "最近、一人暮らしの若者が増えている。（　　）、小さな部屋に住む人も多い。", "そのため", ["ところが", "ただし", "ところで"], "そのため: for that reason."),
    ("N3", "この店のパンは安くておいしい。（　　）、いつも客が多い。", "だから", ["しかし", "ところが", "ただし"], "だから: so."),
    ("N2", "この製品は品質がいい。（　　）、価格も手ごろだ。", "しかも", ["ただし", "ところが", "もっとも"], "しかも: moreover."),
    ("N2", "計画は順調に進んでいる。（　　）、油断はできない。", "とはいえ", ["そのうえ", "したがって", "つまり"], "とはいえ: even so."),
    ("N1", "この計画は確かに魅力的だ。（　　）、実現には多くの課題が残っている。", "とはいうものの", ["したがって", "なおかつ", "もしくは"], "とはいうものの: that said."),
    ("N1", "彼は経験も豊富で、（　　）、人柄も良い。", "なおかつ", ["ひいては", "あるいは", "とはいえ"], "なおかつ: and furthermore."),
]

PASSAGE = [  # (level, passage, question, right, wrongs, explanation)
    ("N5", "田中さんは毎朝、6時に起きます。それから、コーヒーを飲んで、7時に家を出ます。", "After getting up, what does Mr Tanaka do first?", "He drinks coffee.", ["He goes to work.", "He eats lunch.", "He goes back to sleep."], "起きます → それから コーヒーを飲んで."),
    ("N5", "あしたは友達のたんじょうびです。わたしは花を買って、友達の家へ行きます。", "What will the writer do tomorrow?", "Buy flowers and go to a friend's house.", ["Make a cake at home.", "Study at school.", "Go to the hospital."], "花を買って、友達の家へ行きます."),
    ("N4", "この店は月曜日が休みです。ほかの日は、朝10時から夜8時まで開いています。", "When is the shop open?", "Tuesday to Sunday, 10:00 to 20:00.", ["Every day, 10:00 to 20:00.", "Only on Mondays.", "Every evening only."], "月曜日が休み; other days 10-20."),
    ("N4", "山下さんへ。明日の会議は午後2時から3時に変わりました。場所は同じです。よろしく。", "What changed?", "The meeting time moved from 2:00 to 3:00.", ["The place of the meeting.", "The date of the meeting.", "The meeting was cancelled."], "二時から三時に変わりました: the time changed; 場所は同じ."),
    ("N3", "最近、駅の近くに新しい図書館ができました。本を借りることができるだけでなく、勉強する部屋もあります。夜九時まで開いているので、仕事の後でも使えます。", "What good point is mentioned?", "It is open until night, so people can use it after work.", ["It is free of charge.", "It has many foreign books.", "It is next to a school."], "夜九時まで開いているので、仕事の後でも使えます."),
    ("N3", "朝食べない人が多いと聞いた。でも、朝ごはんを食べると、午前中は頭がよく働くそうだ。だから私は毎朝何か食べている。", "Why does the writer eat something every morning?", "Because breakfast helps the head work well in the morning.", ["Because many people skip breakfast.", "Because it is cheap.", "Because the writer is always hungry."], "食べると頭がよく働くそうだ。だから食べる."),
    ("N2", "新聞を読む若者が減っていると言われる。しかし、ニュースをまったく見ないわけではない。スマートフォンで短い記事を読む人が増えているのだ。", "What does the writer say?", "Young people still read the news, but on smartphones.", ["Young people no longer care about news.", "Newspapers are selling more.", "Smartphones should be banned."], "見ないわけではない: it's not that they don't."),
    ("N2", "「忙しい」という言葉を口ぐせにしている人は多い。だが、本当に忙しいのか、それとも時間の使い方が下手なのか。一度考えてみる必要があるだろう。", "What does the writer want readers to do?", "Think about whether they are truly busy or just poor at using time.", ["Work harder.", "Stop saying anything about work.", "Take a long holiday."], "考えてみる必要がある."),
    ("N1", "伝統とは、過去をそのまま守ることではない。むしろ、時代に合わせて形を変えながら、核となる精神を受け継いでいくことだと思う。", "What does the writer say about tradition?", "It means keeping the core spirit while changing the form to suit the times.", ["It means keeping the past exactly as it was.", "It means abandoning old customs.", "It means copying foreign ideas."], "ではない。むしろ～: not X, rather Y."),
    ("N1", "便利さを追い求めるあまり、私たちは不便の中にある豊かさを見失ってきたのではないか。手間をかけて作る食事や、足で歩く道のりにこそ、人間らしい時間が流れている。", "What is the writer's main point?", "In seeking convenience we have lost the richness found in inconvenience.", ["Convenience makes life richer.", "People should stop cooking.", "Walking is faster than driving."], "不便の中にある豊かさを見失ってきた."),
]

# Readings for the words in the N5 / N4 questions, so the furigana switch has something to show
# (the N3-N1 questions go without, like the real papers).
READINGS = [
    ("三千円", "さんぜんえん"), ("重い", "おもい"), ("六時", "ろくじ"), ("止まります", "とまります"), ("十分", "じゅっぷん"),
    ("寒い", "さむい"), ("着ます", "きます"), ("入って", "はいって"), ("明るく", "あかるく"), ("古く", "ふるく"), ("昨日", "きのう"),
    ("長かった", "ながかった"), ("毎朝", "まいあさ"), ("家", "いえ"), ("打って", "うって"), ("打った", "うった"), ("返し", "かえし"),
    ("貸し", "かし"), ("売り", "うり"), ("止めます", "とめます"), ("通訳", "つうやく"), ("荷物", "にもつ"), ("切った", "きった"),
    ("中心", "ちゅうしん"), ("注意", "ちゅうい"), ("早く", "はやく"), ("間に合った", "まにあった"), ("十年", "じゅうねん"),
    ("着いたら", "ついたら"), ("外", "そと"), ("負ける", "まける"), ("着ている", "きている"), ("漢字", "かんじ"), ("意味", "いみ"),
    ("月曜日", "げつようび"), ("休み", "やすみ"), ("朝", "あさ"), ("夜", "よる"), ("八時", "はちじ"), ("山下", "やました"),
    ("午後", "ごご"), ("二時", "にじ"), ("三時", "さんじ"), ("場所", "ばしょ"), ("同じ", "おなじ"), ("日", "ひ"), ("田中", "たなか"),
    ("毎日", "まいにち"), ("手紙", "てがみ"), ("母", "はは"), ("花", "はな"), ("買って", "かって"), ("七時", "しちじ"), ("歩いて", "あるいて"), ("変わりました", "かわりました"), ("入っ", "はいっ"), ("英語", "えいご"), ("重くて", "おもくて"), ("時", "じ"),
]

GENERIC_HINTS = {
    "reading": "Think of the word as it's used in this sentence, then compare the readings sound by sound.",
    "writing": "Look closely at the kanji parts: the wrong ones differ by one stroke or one part.",
    "meaning": "Swap each choice into the sentence -- which one keeps the meaning?",
    "usage": "Only one sentence fits the word's real meaning; the others stretch it.",
    "ordering": "Build the sentence from its ends: what must come first, and what must come last?",
    "cloze": "Look at how the second sentence relates to the first: result, contrast or addition?",
    "passage": "Find the sentence in the text that answers the question.",
}


def _q(kind, level, n, category, prompt, right, wrongs, explanation, hint):
    wrongs = [w for w in dict.fromkeys(wrongs) if w != right]
    return {"id": f"jlpt_{kind}_{level.lower()}_{n:03d}", "category": category, "jlpt": level, "prompt": prompt,
            "choices": [right] + wrongs[:3], "answer": 0, "explanation": explanation, "hint": hint,
            "wrongs": wrongs, "style": "jlpt"}


def build():
    """Every JLPT-style question, as plain question dicts (the right answer first; Game shuffles)."""
    counts = {}
    out = []

    def add(kind, level, *args):
        counts[(kind, level)] = counts.get((kind, level), 0) + 1
        out.append(_q(kind, level, counts[(kind, level)], *args))

    for level, sentence, right, wrongs, why in READING:
        add("reading", level, "kanji", f"How is the marked word read?  {sentence}", right, wrongs, why, GENERIC_HINTS["reading"])
    for level, sentence, right, wrongs, why in WRITING:
        add("writing", level, "kanji", f"How is the marked word written?  {sentence}", right, wrongs, why, GENERIC_HINTS["writing"])
    for level, sentence, right, wrongs, why, hint in FILL:
        add("fill", level, "vocabulary", f"Which word fits the blank?  {sentence}", right, wrongs, why, hint)
    for level, sentence, right, wrongs, why, hint in GRAMMAR:
        add("grammar", level, "grammar", f"Which fits the blank?  {sentence}", right, wrongs, why, hint)
    for level, kind, stem, right, wrongs, why in MEANING:
        head = ("Which sentence means about the same?  " if kind == "sentence" else "Which is closest in meaning to the marked word?  ")
        add("meaning", level, "vocabulary", head + stem, right, wrongs, why, GENERIC_HINTS["meaning"])
    for level, word, right, wrongs, why in USAGE:
        add("usage", level, "vocabulary", f"Which sentence uses 「{word}」 correctly?", right, wrongs, why, GENERIC_HINTS["usage"])
    for level, before, pieces, after, english, why in ORDERING:
        frame = f"{before} ＿ ＿ ★ ＿ {after}".replace("  ", " ")
        add("ordering", level, "sentence", f"Put the four pieces in order. Which one goes on the ★?  {frame}", pieces[2],
            [p for i, p in enumerate(pieces) if i != 2], f"The sentence is 「{before}{''.join(pieces)}{after}」 ({english}) {why}", GENERIC_HINTS["ordering"])
    for level, text, right, wrongs, why in CLOZE:
        add("cloze", level, "grammar", f"Which word joins the sentences?  {text}", right, wrongs, why, GENERIC_HINTS["cloze"])
    for level, text, question, right, wrongs, why in PASSAGE:
        add("passage", level, "reading", f"「{text}」  {question}", right, wrongs, why, GENERIC_HINTS["passage"])
    return out

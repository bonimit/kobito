# Kobito

An 8-bit style Japanese-learning platformer built with Pygame.

## Setup

```
pip install -r requirements.txt
python main.py
```

To let Kobito (see below) generate real AI hints instead of using its
built-in fallback hints, set an API key before running:

```
export ANTHROPIC_API_KEY=your-key-here
```

The game works fine without one — Kobito just falls back to a
category-based canned hint instead of an AI-generated one.

## Controls

- **Left/Right arrows or A/D** — choose mascot/companion/world/difficulty (select screens) / run (in-level)
- **Space / W / Up** — jump; **Enter/Space** — confirm a selection
- **Up/Down + Enter (or Space)** — move the highlight through a quiz's
  choices and answer with it; **1-4** still picks a choice directly, and
  the mouse can hover/click a choice
- **S** — skip (pass on) the question instead of answering it
- **Enter/Space** — dismiss Kobito's hint after a wrong answer, or continue after completing a level
- **Esc / P** — pause and open **Settings** (save, item box, furigana, translation, save & quit)

A gamepad works everywhere alongside the keyboard — plug one in before or
during play, it's picked up automatically (hot-plug supported):

- **D-pad / left stick** — move / navigate menus
- **A** (button 0) — jump; confirm a selection; continue after Kobito's hint or a level
- **B** (button 1) — back (in Settings)
- **Start / Back** — open Settings
- **D-pad / stick up-down + A** — choose and answer in a quiz
- **LB / RB / Start** — skip the question

Button numbers follow the common Xbox-style layout most gamepads report.

On the web build (see below), on-screen touch buttons appear automatically
instead — a left/right/jump trio during gameplay, and prev/next/OK
arrows on every menu and quiz screen — since a phone has neither a
keyboard nor a gamepad. They're built entirely from the same input
handling as keyboard/joystick (see `kobito/input.py`); nothing about the
desktop build changes.

## Playing on the web or a phone

The exact same codebase also builds into a static, no-install web
version via [Pygbag](https://github.com/pygame-web/pygbag) (Pygame
compiled to WASM), playable in a desktop or mobile browser with the
on-screen touch controls above. Build it with:

```
pip install pygbag
./packaging/build_web.sh   # (on Windows: python -m pygbag --build .)
```

That leaves a static site in `build/web/` — open `build/web/index.html`
locally to try it, or deploy the folder as-is to any static host. For
Vercel specifically:

```
npx vercel deploy build/web --prod
```

(A `vercel.json` at the repo root also lets Vercel build it directly
from a git-connected project, running that same `pygbag --build` step.)

Two things behave differently in the web build:
- **AI hints** (`ANTHROPIC_API_KEY`) don't work in-browser — WASM can't
  make the same kind of network call the desktop build does, so it
  always uses Kobito's local fallback hints there. Gameplay is otherwise
  identical.
- The first load is slower than a native launch (the browser is
  downloading a WASM Python runtime), but it's cached after that.

## Standalone desktop builds

For a single executable that runs without installing Python or any
dependency (share it, or just avoid re-running `pip install` yourself):

```
pip install pyinstaller
python packaging/build_desktop.py
```

This produces `dist/Kobito` (`dist/Kobito.exe` on Windows). PyInstaller
bundles for whatever OS it runs *on* — it doesn't cross-compile — so
build a Windows .exe on Windows, a macOS .app on a Mac, and a Linux
binary on Linux; there's no way to produce all three from one machine.
See `packaging/build_desktop.py` for why `anthropic` is excluded from
the bundle (same local-hint fallback as the web build, for a different
reason — a PyInstaller/`cryptography` build issue on some platforms).

## Question blocks

**How they look.** Quiz blocks are chunky bevelled blocks with a dark
outline, a soft pulsing glow behind them and a shine that sweeps across every
few seconds, in a colour picked per world to stand out from its scenery
(gold in the forest, turquoise in the desert, coral underwater, jade in
Korea, …). Their faces vary through a level: a classic **?**, a **?**
medallion with stars, or **問** (*mon*, "question"). Answered blocks turn to
grey stone with a check mark (`kobito/entities/question_block.py`). The quiz
card that pops up is nearly solid, with a coloured header band and border per
question type — **vocabulary** blue, **kanji** vermilion, **grammar** green,
**verbs** purple — and the choice highlight takes the same colour.

Yellow "?" blocks (drawn slightly larger than a tile, Mario-block style)
pause gameplay and show a small black box — anchored right next to the
block, above it if there's room or below otherwise, rest of the level
still visible, with a tooltip-style tail that touches the block itself
(no floating gap) so the box clearly reads as popping up *from* it —
with a multiple-choice Japanese question (vocabulary,
kanji, grammar, or verb conjugation) drawn from
`assets/data/questions.json` (**190 questions** — 38 per JLPT level,
spread evenly across the four categories), filtered to the level's
current JLPT level (see Difficulty below).

Question blocks are kept well apart — **at least 8 tiles between any two**
(`MIN_QUESTION_SPACING_TILES` in `kobito/levels/level1.py`) — and levels
are long (about 400 tiles), so there are real stretches of running,
jumping, stomping and snack-hunting between quizzes, not a quiz every few
steps.

A question's worth scales with its level, shown up front in the quiz box
as e.g. `N3 · GRAMMAR · 20 XP`:

| Level | Correct | Wrong |
| --- | --- | --- |
| N5 | +10 | −4 XP |
| N4 | +15 | −6 XP |
| N3 | +20 | −8 XP |
| N2 | +30 | −11 XP |
| N1 | +40 | −15 XP |

Correct answers add to your **XP** as well as the score. XP is a plain
running total ("XP 1269"), not a bar that refills — it keeps counting up
across levels, and every 100 XP earns a bonus life (the HUD shows how far
you are from the next 1UP). Wrong answers and enemy hits take a little XP
off. Each block only
fires once. Add more questions by appending objects to that JSON file — each needs `category`,
`jlpt` (`N5`-`N1`), `prompt`, a `choices` list, an `answer` index, an
`explanation`, and a `hint` — a nudge pointing at the useful clue (a
radical, a particle's role, a stem change) without giving the answer
away. Both feed Kobito's hint below.

### Saving

Your run is saved automatically, and you can save any time yourself:

- **Stage clear** — autosaves a checkpoint at the start of the next level.
- **Settings → Save game** — saves your *exact spot*: where you're standing,
  power, lives, quiz progress, and which question boxes, gift boxes, coins
  and enemies are already gone.
- **Settings → Save & quit**, or just closing the window mid-level — the same.
- Your **item box**, **badges**, score and XP are part of the save, and the
  furigana / translation toggles are remembered between sessions.

When a save exists the game opens on a title screen showing it (mascot,
companion, level, world, score, badges, items) with **Continue** or **New
Game** — New Game asks once more before replacing the save. Running out of
lives leaves the save as it was, so Continue picks up from your last save.

Where it's stored (`kobito/save_game.py`): `%APPDATA%\Kobito\save.json` on
Windows, `~/Library/Application Support/Kobito/save.json` on macOS,
`~/.local/share/kobito/save.json` on Linux (override with `KOBITO_SAVE_PATH`),
and the browser's localStorage in the web build. Delete the file to start
completely fresh; a damaged or outdated save is simply ignored.

### HUD, settings and the item box

The HUD is plain outlined text and icons in the top corners — no backing
cards, so it covers as little of the world as possible — each read top-down as label →
big number → detail: the left one is you (score, lives, the 10-pip power
gauge, XP toward the next 1UP), the right one is the lesson (questions
answered toward the badge, how many right, your accuracy). Temporary states
(sleepy, boost) pop up as a tag under the left card. Under the quiz card is
a small tray: your mascot's favourite foods, the **item box** (a crate with
a count) and a **gear**.

The item box keeps every item you've picked up this run, across levels.
The HUD only shows the crate; click/tap it (or open Settings → Item Box) to
see each item with its Japanese word, reading and how many you've found.

Settings (`kobito/settings_screen.py`) pauses the level: Resume, Save game,
Item Box, Furigana ON/OFF, Translation ON/OFF, Save & quit. It works with arrow keys +
Enter, the mouse, touch and a gamepad (d-pad, A, B).

The companion's box (item comments and lessons) sits in the **bottom-left
corner**, in the strip under the ground line, so it never covers your
character; larger rounded type with a name plate, and a pickup's vocabulary
lesson is its second page. When a question opens, the quiz's own companion
box takes over.

Fonts (all bundled under `assets/fonts/`, see the licence files there):
**DotGothic16** for the pixel HUD labels, numbers and titles, **M PLUS
Rounded 1c** for sentences (the companion, menus), and **IPA Gothic** for
quiz text, which needs full kanji coverage. The shared panel/text/icon
helpers live in `kobito/ui.py`.

Japanese text renders with a bundled font (`assets/fonts/ipag.ttf`,
IPA Font License v1.0) since pygame's default font has no CJK glyphs.

### Furigana and translation

Two independent toggles, both in **Settings** (Esc / P / Start, or the
gear icon in the HUD). While a question is open, **F** and **T** still work
as shortcuts:

- **F** — furigana: small kana readings above kanji (`kobito/furigana.py`),
  on by default. Toggling it off drops back to plain kanji.
- **T** — translation: the English translation of the prompt, hidden by
  default so it can't hand you a grammar answer for free (a sentence
  like "...at the library" gives away that the blank wants a location
  particle). Off by default; press T to reveal it inline, right below
  the Japanese line.

Furigana is looked up from a hand-built reading dictionary covering
every kanji that appears in the question bank in the way it's actually
used there (not a general-purpose kanji dictionary) — a handful of
genuinely ambiguous readings (bare "一", "物", and the irregular verb
"来る", whose reading changes per conjugation: 来い is こい but 来れば
is くれば) are deliberately left unannotated rather than guessed wrong.
**Kanji-category questions never show furigana**, regardless of the
toggle — the question is literally "how do you read this kanji," so
annotating it would hand over the answer.

### Read more

If the question or the companion's hint isn't enough, press **R** once
an answer is locked in (right or wrong) to slide in a detail panel from
the right edge of the screen: the full question, the correct choice
spelled out, the complete explanation, and the authored hint, all in
one place. It's only available after answering, so it can never spoil
the question, and a small "R · Read more" tab stays visible the whole
time so it's discoverable without reading this README.

Wherever a Japanese sentence is followed by its English translation in
parentheses (e.g. `図書館で本を読みます。 (I read books at the
library.)`), the panel splits them onto separate lines instead of
letting them run together as one wrapped paragraph -- a short reading
gloss stuck mid-sentence right after a word (`犬 (inu) means...`) is
left alone, since that's a reading, not a translation.

## Your AI hint companion

While a question is open, your companion's dialogue box is a **slim,
full-width bar docked in the strip under the ground line** — always the same
place, never covering the level or your character (while you answer or right
after), and nothing overlaps it; the question box
always stays clear of it. If you've been **thinking about a question for
about 10 seconds** without answering (moving between choices doesn't
reset this), the companion **speaks up**: its box flashes gold, a "!" pops
over its portrait, and it offers a hint — a nudge toward the clue, never the
answer. With an API key, Claude writes that hint for the exact question in
your companion's voice; it's requested in the background a few seconds
early so it's ready on time, and the question's own authored hint shows
instantly whenever Claude isn't available (offline, no key, slow network).

Before a run starts, a companion-select screen shows **all five
companions at once** in a gallery (`kobito/companions.py`) so you can
compare them side by side — left/right moves the highlight, and the
highlighted one's tagline and ability show in a card below the row:

| Companion | Style | Ability |
| --- | --- | --- |
| **Kobito** | A gentle forest spirit — warm, soft-spoken | Balanced Guide — no bonus, no penalty |
| **Ushi** | A calm, motherly cow spirit | Steady Heart — wrong answers cost 25% less XP |
| **Hana** | A bright, bubbly flower spirit | Bright Spark — correct answers earn 10% more XP |
| **Ume-shu** | An elegant, quietly wise plum-blossom spirit | Deep Insight — hints always include the full explanation |
| **Kinoko** | A playful, quirky mushroom spirit who loves puns | Playful Streak — +2 flat bonus points per correct answer |

So picking a companion is a real choice, not just a skin: the ability
applies for the whole run via `Game._trigger_question`, scaling the
same JLPT-based XP numbers from the table above (Kobito's multipliers
are all neutral, so it's the baseline every other companion is judged
against).

Your companion is present for the whole answer -> reveal -> hint arc in
a slim JRPG-style textbox docked in the strip under the ground (a
translucent black bar, portrait and name on the left), switching
expression to match the moment (`assets/sprites/<companion_id>/`, five
real frames per companion — idle, thinking, talking, happy,
sympathetic; falls back to a flat-shape placeholder, tinted to that
companion, for any expression without art):

- Correct answer → **happy**, a quick "Correct! Nice work."
- Wrong answer → **sympathetic** ("Not quite... let me think."), then
  **thinking** while the hint request is in flight, then **talking**
  with the actual hint — generated by Claude (`kobito/hint_service.py`)
  in that companion's own voice, without spelling out the correct
  answer. Press Enter/Space to dismiss.

If no API key is configured, or the request fails for any reason (no
network, rate limit, timeout, ...), your companion falls back to that
question's own authored hint instead — a hint is always available, and
a network hiccup never hangs or crashes the game. The question box
above always repositions to stay clear of the companion's textbox.

Add a new companion by adding an entry to `kobito/companions.py` (id,
name, tagline, personality, placeholder color, and an ability —
`xp_gain_multiplier`, `xp_penalty_multiplier`, `bonus_score`, and/or
`always_show_explanation`) and dropping its five expression frames into
`assets/sprites/<id>/` — nothing else changes.

## Power, enemies and stomping

**Enemy designs** (`kobito/enemy_art.py`): every enemy has a bold silhouette,
a dark outline and a two-frame walk/flap, and faces the way it's going.
On the ground: a jelly **slime** (several colours), a horned **oni** with
fangs and a tiger-stripe belt, a wobbling **daruma** doll, and a beaked
**kappa** with a water dish on its head. In the air: a **bat**, the
one-eyed paper-lantern ghost **chōchin-obake**, and the umbrella ghost
**karakasa-obake** hopping on its handle. A level mixes them, and the
lineup rotates from level to level; the hidden rooms keep their own
critters (rats, gators, moles, cloud sheep, thunder imps, moon rabbits).

Every mascot has a **power gauge, 10 pips** (shown under the score). Each
enemy hit costs **1 power**, so ten hits drain a full gauge — hits no
longer cost a life directly.

- **3/10 or less: drowsy.** The pips flash red, the screen darkens at the
  edges, Z's float over the mascot, and it runs and jumps slower. The AI
  companion warns you once. Find something to perk you up!
- **0/10: you fall asleep.** That costs a **life** and you wake up with
  5/10 power and a couple of seconds of invulnerability. Out of lives is
  game over ("You fell asleep...").

**Jump on an enemy's head to defeat it** — you bounce up, score +10, and
ground enemies sometimes drop a snack. You must be falling onto it;
walking or jumping up into one still hurts (and a hit is followed by a
short blink of invulnerability, during which you can still stomp back).
Constants live in `kobito/constants.py` (`POWER_*`, `STOMP_*`).

Simple patrol enemies (walk back and forth, turn at their patrol bounds)
roam the ground and stepping stones; bats patrol up and down over the
gaps.

## Items: konbini snacks, favorites and rare finds

Pickups float gently with a coloured halo that says what they are at a
glance — **sky blue** for konbini snacks, **pink** for your favourites,
**gold** (bigger, pulsing) for rare finds and treasures. Coins are outlined
and spin. Gift boxes have a dark outline and a shine.

All items are data in `kobito/items.py` (icons are drawn in code in
`kobito/item_art.py`). They're picked up on touch, add to your score and
XP, and show up in three families:

- **Konbini snacks — refill power.** Things you'd grab at a Japanese
  convenience store: Genki Can (energy drink, +4), Mega Can (+5), Kan
  Coffee (+3), Ume Soda (+3, a nod to the Ume-shu companion), Onigiri (+2),
  Melon Pan (+2), Ocha (+2), Gummy (+2), Dried Ume (+2, the sour dried-plum
  snack), Nuts (+3), Candy (+1). The energy drinks are generic,
  not real brands.
- **Favorites — each mascot's own favourite things**, two per character
  (Capybara: yuzu, watermelon · Sloth: leaf, hibiscus · Kitsune: inari
  sushi, aburaage · Wombat: sweet potato, grass · Otter: clam, fish ·
  Scottish Fold: tuna, milk · Frenchie: bone, sausage). Scattered through
  every level (the HUD shows yours); each is worth +25 and +1 power.
- **Rare finds — mostly from gift boxes.** Golden Can (full power plus an
  8-second speed boost) and Lucky Bag / fukubukuro (full power and an extra
  life).
- **Treasures — only in the hidden underground stages** (see below), one
  per stage: 駅弁 ekiben in the subway (full power), ピザまん pizza bun in the
  sewer (power and a speed boost), 宝石 gem in the mine (big score and an
  extra life). They glow so you can't miss them.

Plus coins and shiitake (an extra life), as before. Every item also has its
Japanese word, reading, meaning and an example sentence — the companion
teaches it when you collect it.

## Pits and hidden underground stages

Falling into a gap is no longer endless:

- **An ordinary pit costs a life.** The screen fades and you're back on the
  ledge just before the gap, with a moment of safety (and a word from your
  companion). On your last life it's game over.
- **Three gaps per level are secret.** Look closely: a secret pit is darker
  than the others, with a clue rising out of it — subway steam, a green
  sewer glow, or gold sparkles from a mine. Drop in on purpose and you land
  in a **hidden underground stage** instead of losing a life:
  - **NYC Subway** (地下鉄 chikatetsu) — white tile walls, a TIMES SQ – 42 ST
    mosaic band, steel columns, coloured line signs, and a train rattling past.
    Rats patrol the platform. Treasure: 駅弁 ekiben.
  - **Sewer Pipes** (下水道 gesuidou) — turtle-hideout style tunnels: wet
    green brick, arched waterways, big pipes with red valve wheels, light
    through street grates, dripping water. Little gators. Treasure: ピザまん.
  - **Old Mine** (鉱山 kouzan) — rough rock with glittering crystals and gold
    veins, timber frames, flickering lanterns, mine carts. Moles and bats.
    Treasure: 宝石 gem.

  Each is a bonus room: no quiz boxes, lots of coins, two gift boxes, a
  snack, a favourite and the treasure. Your companion teaches the place's
  Japanese word when you arrive. Walk to the **出口 (EXIT)** at the far end —
  stairs, a manhole ladder or a mine lift — and you come back up just past
  the gap. Which room is behind which gap changes from level to level, and
  the stage-clear card shows how many secrets you found.

Saving underground keeps everything you picked up down there; you continue
on the surface just past that pit and can drop back in for the rest.
Code: `kobito/levels/underground.py` (layout + styles),
`kobito/underground_background.py` (backdrops), `kobito/entities/exit.py`,
`kobito/world.py` (switching between the surface and a room).

## Hidden sky stages (the way up)

Every level also hides **three secret ways up**: a small cloud tuft sitting
in the grass, with a spring underneath. It's given away by a little updraft
rising off it — rainbow sparkles, crackling sparks, or twinkling stars.
Walking over it does nothing; **jump and land on it** and it launches you
straight off the top of the screen into a hidden sky stage:

- **Rainbow Bridge** (虹 niji) — a bright pastel sky with giant rainbows.
  Cloud sheep and pink birds. Treasure: 綿あめ cotton candy. Exit: a rainbow arch.
- **Thunder Clouds** (雷 kaminari) — a storm with lightning flashes, slanting
  rain and the thunder god Raijin's ring of drums. Thunder imps and storm
  puffs. Treasure: 雷おこし kaminari okoshi. Exit: a giant lightning bolt.
- **Moonlit Clouds** (月 tsuki) — a starry night with a huge full moon and the
  moon rabbit pounding mochi. Moon rabbits and night bats. Treasure:
  月見団子 tsukimi dango. Exit: a vermilion torii gate.

Sky stages are built from **one-way clouds**: jump up through them from
below, land on top. There's no floor — **fall through a gap and you drift
back down to the surface, with no life lost** — so the way down is always
open, and the 出口 (EXIT) at the far end takes you down too. Like the
underground, each has coins, two gift boxes, a snack, a favourite and a
glowing treasure, and your companion teaches the sky word when you arrive.

So each level has six secrets: three pits down and three springs up. The
stage-clear card shows how many you found (SECRETS n/6).
Code: `kobito/levels/sky.py`, `kobito/sky_background.py`,
`kobito/entities/sky_spring.py`, `CloudPlatform` in `kobito/entities/platform.py`.

## Gift boxes

Not every box is a question. **Red boxes with a gold ribbon** are gifts:
bump one and it pops open with a random prize — coins, a snack, a big
drink, one of your favorites, an extra life, or (about 1 in 12) a rare
item. They never pause the game. When you're drowsy the odds improve
(more drinks and snacks, fewer coins), so a gift box can be a lifeline.
Yellow "?" blocks are still the quiz questions.

## AI companion reactions

The companion you chose comments on what you collect — in its own voice
(Kobito gentle, Ushi motherly, Hana bubbly, Ume-shu elegant, Kinoko
punny) — in a small box in the bottom-left corner (in the strip below the ground, so it never covers the player or blocks play). A reaction with a vocabulary lesson shows as two pages: the companion's line, then the word.
It warns you when you get sleepy, cheers when you find a favorite, and
celebrates rare finds. Each pickup also shows the **Japanese word for the
item with its reading and an example sentence**, e.g.
`おにぎり (onigiri) = rice ball. おにぎりを食べます。(I eat an onigiri.)`

The line you see first is instant and works offline
(`kobito/item_coach.py`). If an Anthropic key is set, a Claude-written
reaction is requested on a background thread and replaces it if it arrives
while the box is still showing — gameplay never waits on the network.

## Worlds

Before a level starts, a world-select screen (mirroring the mascot
select screen) lets you pick from 10 themed worlds — 5 fantasy and 5
built on real Japanese places:

| Fantasy | Real places |
| --- | --- |
| Whispering Forest — torii, sakura, stone lanterns, drifting petals | **Neon Tokyo** — lit skyline, Tokyo Tower, crows, night planes |
| Sunfall Desert — pyramids, cacti, camels, scorpions | **Nagano Snowfield** — snowy alps, falling snow, snow monkeys |
| Arabian Night — minarets, pagodas, bats under a hazy moon | **Okinawa Shore** — turquoise sea, palms, hibiscus, shisa, crabs |
| Coral Deep — reef, fish, jellyfish, turtles, a whale | **Hokkaido Lavender** — Furano rows, red-crowned cranes, Ezo foxes |
| Cloud Kingdom — cloud hills, floating islands, balloons | **Kyoto Autumn** — bamboo grove, momiji maples, machiya, Inari foxes |

Each world has its own sky gradient, ground/platform colors and layered
scenery, but the same gameplay layout underneath (platforms, question
blocks, enemies, collectibles).

A world is just data in `kobito/themes.py` (colors + which decorations
to draw, from the shape library in `kobito/scenery_shapes.py`) — adding
an 11th world doesn't require touching the rendering code, only a new
`Theme(...)` entry. The backdrop is layered for depth (back to front):
rolling silhouette layers, the sky layer (clouds/stars/snow/petals/...),
then ground props. Each layer scrolls at its own rate relative to the
camera (parallax); silhouette layers are clipped to the horizon so they
never hang into a ground gap, and ground props are only ever placed on
solid ground segments. Solid tiles get a lit top cap, a shaded underside
and tile seams. All of it is rendered generically by
`kobito/background.py`.

Each world also has living creatures that actually move over time (not
just scroll with the camera) — birds, butterflies and dragonflies;
camels, scorpions and lizards; fish, jellyfish, turtles and a whale;
snow monkeys, cranes and foxes; planes over Tokyo. Flying/swimming
creatures wander the level with a gentle bob and wrap around when they
exit; ground creatures patrol back and forth like a decorative,
non-colliding cousin of Enemy. A world adds creatures by listing
`FlyingCreature`/`GroundCreature` entries in its `Theme`.

## Difficulty and level progression

Before the first level, a difficulty-select screen (`kobito/difficulty_select_screen.py`)
offers three ways to get questions:

- **A JLPT level, N5 (beginner) to N1 (advanced)** — questions from that
  level; between levels it steps up (≥80% right) or down (≤40%).
- **AI Adaptive** — your companion tunes *every question* to you
  (`kobito/adaptive.py`): harder while you're on a roll, easier when you're
  stuck, always kept in a comfortable range. It combines:
  - an **Elo rating** learner model, as used in adaptive practice systems
    ([Pelánek 2016](https://www.fi.muni.cz/~xpelanek/publications/umuai-adaptive-practice.pdf)):
    you and each question have a rating, every answer is a "match", and
    both ratings move toward what happened — big steps while the tutor is
    still getting to know you, smaller ones later;
  - the **85% rule** for optimal learning
    ([Wilson et al., Nature Communications 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6831579)):
    the next question is the one you're predicted to get right ~85% of the
    time, only picked from questions inside a 65-95% comfort band — so it's
    never boring and never crushing. In simulation players settle around 80%
    real accuracy (above the badge's 70%), and a strong player climbs from
    N5 to N2 in about 15 questions;
  - **spaced repetition (Leitner boxes)** — a question you miss comes back
    after 4 others; get it right and it returns once more 9 questions later;
    right again and it's learned.

  The HUD shows the level the tutor thinks suits you (e.g. `LEVEL 2 · AI N3`),
  and its learner model is saved with your game.
- **Random** — any question from N5 to N1, a surprise every time.

A level is built as a chain of ground segments (`kobito/levels/level1.py`),
each carrying 2-3 question blocks, two ground patrols and one elevated
patrol, so enemy density scales with the level's length rather than
staying fixed. It ends at a **Japanese castle**
(`kobito/entities/goal.py`) — non-solid, the player runs straight into
it.

### 30 quiz boxes per level, 20 answers to qualify

Every level contains **30 yellow "?" quiz boxes** (`QUESTION_BLOCKS_PER_LEVEL`
in `kobito/constants.py`) — and never repeats a question within a level,
since each JLPT level's pool holds more than 30 (`assets/data/questions.json`).
You don't have to answer them all. Every quiz box has a **Skip** button (or press **S**, a gamepad shoulder button/Start, or tap it): nothing is lost — no XP, and it doesn't count as answered or wrong — and **the box stays a "?" box**, keeping that question for you. Come back to it later (step away and bump it again) and it asks the same question. The badge needs **at least 20 answered**
(`MIN_QUESTIONS_ANSWERED`), so you can skip up to 10 boxes — a tricky one,
or one in a risky spot. Later levels get harder through faster enemies and
tougher JLPT questions, not longer levels. Levels run about 400 tiles, with
at least 8 tiles between quiz boxes.

### Badges

Reaching the castle awards a **badge** — one of the 20 hexagonal prizes
in `kobito/badges.py`, grouped **four per JLPT level** so the prize
tracks proficiency rather than just how far you've played. Clearing at
N5 hands you an N5-tier badge; an N1 clear hands you an N1-tier one.
Within a tier the four cycle by level number.

| Level | Badges |
| --- | --- |
| **N5** | Hiragana Start (あ) · First Sprout (芽) · First Kanji (木) · Polite Form (礼) |
| **N4** | Milk Run (牛) · Travel Talk (旅) · Blossom Words (花) · Onsen Break (湯) |
| **N3** | Rest Day (眠) · Sound and Pitch (音) · Water Song (水) · Bookworm (本) |
| **N2** | Meadow Walk (草) · Sharp Eye (実) · Sunflower Sun (陽) · Friendship (友) |
| **N1** | Rain Shelter (雨) · Crab Claws (蟹) · Space Walk (宙) · Fish Rider (魚) |

Badge art loads from `assets/sprites/badges/<badge id>.png`. Any badge
without art falls back to a drawn hexagon in that badge's colors with
its kanji emblem — the same silhouette as the real artwork, so a
part-finished set still reads as one collection.

You don't need a clean sweep: answer **at least 20 questions, with 70%
of the ones you answered correct** (`BADGE_PASS_ACCURACY`) — 14 of 20, or
21 of 30 if you answer them all. The HUD tracks progress toward it as you
play ("answer 5 more for the badge"), and a badge you narrowly missed is
shown greyed out rather than hidden.
Because the bar is 70%, a wrong quiz answer costs XP but **not** a
life — otherwise a few mistakes would end the run before you could ever
reach it.

Reaching the castle also adaptively picks the *next* level's JLPT level:
answer most questions right (≥80% accuracy) and it steps up to a harder
level; answer most wrong (≤40%) and it steps down; anything in between
holds steady, clamped to N5..N1. Score carries over between levels;
`main.py` loops, building a fresh `Game` for each level with the
adjusted JLPT level until you quit or run out of lives.

## Adding real sprite art

Each mascot has a folder at `assets/sprites/<character_id>/` with `idle/`,
`run/`, and `jump/` subfolders. Drop transparent PNG frames into the
matching subfolder, named so they sort in playback order (`00.png`,
`01.png`, `02.png`, ...). They're picked up automatically — no code
changes needed. Until frames exist for a character, a flat-color
placeholder is used instead.

Character ids: `capybara`, `sloth`, `kitsune`, `wombat`, `otter`,
`scottish_fold`, `frenchie`.

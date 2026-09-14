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
- **1-4** — answer a question block's quiz
- **Enter/Space** — dismiss Kobito's hint after a wrong answer, or continue after completing a level
- **Esc** — quit

A gamepad works everywhere alongside the keyboard — plug one in before or
during play, it's picked up automatically (hot-plug supported):

- **D-pad / left stick** — move / navigate menus
- **A** (button 0) — jump; confirm a selection; continue after Kobito's hint or a level
- **B** (button 1) — cancel / quit
- **A/B/X/Y** (buttons 0-3) — answer a question block's quiz (choices 1-4)

Button numbers follow the common Xbox-style layout most gamepads report.

## Question blocks

Yellow "?" blocks (drawn slightly larger than a tile, Mario-block style)
pause gameplay and show a small black box — anchored right next to the
block, above it if there's room or below otherwise, rest of the level
still visible, with a tooltip-style tail that touches the block itself
(no floating gap) so the box clearly reads as popping up *from* it —
with a multiple-choice Japanese question (vocabulary,
kanji, grammar, or verb conjugation) drawn from
`assets/data/questions.json` (**150 questions** — 30 per JLPT level,
spread evenly across the four categories), filtered to the level's
current JLPT level (see Difficulty below).

A question's worth scales with its level, shown up front in the quiz box
as e.g. `N3 · GRAMMAR · 20 XP`:

| Level | Correct | Wrong |
| --- | --- | --- |
| N5 | +10 | −4 XP |
| N4 | +15 | −6 XP |
| N3 | +20 | −8 XP |
| N2 | +30 | −11 XP |
| N1 | +40 | −15 XP |

Correct answers feed the XP gauge as well as the score, so studying —
not just coin collecting — is what earns bonus lives. Each block only
fires once. Add more questions by appending objects to that JSON file — each needs `category`,
`jlpt` (`N5`-`N1`), `prompt`, a `choices` list, an `answer` index, an
`explanation`, and a `hint` — a nudge pointing at the useful clue (a
radical, a particle's role, a stem change) without giving the answer
away. Both feed Kobito's hint below.

Japanese text renders with a bundled font (`assets/fonts/ipag.ttf`,
IPA Font License v1.0) since pygame's default font has no CJK glyphs.

### Read more

If the question or the companion's hint isn't enough, press **R** once
an answer is locked in (right or wrong) to slide in a detail panel from
the right edge of the screen: the full question, the correct choice
spelled out, the complete explanation, and the authored hint, all in
one place. It's only available after answering, so it can never spoil
the question, and a small "R · Read more" tab stays visible the whole
time so it's discoverable without reading this README.

## Your AI hint companion

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
a classic JRPG-style textbox docked at the bottom of the screen (a
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

## Enemies, collectibles, and scenery

Simple patrol enemies (Goomba-style: walk back and forth, fall under
gravity, turn at their patrol bounds) roam the level; touching one costs
a life, with a brief blinking invulnerability window and knockback
afterward.

Collectibles — coins, shiitake mushrooms, and onigiri — are picked up on
touch (`kobito/entities/collectible.py`). Coins and onigiri add to your
score *and* fill an XP gauge (0-100, shown under the score); a shiitake
instead grants an extra life outright. Correct quiz answers fill it too.
Reaching/exceeding a full gauge grants a bonus life (classic "100 coins
= 1UP", just gauge-shaped), carrying over any remainder. An enemy hit
costs a life and knocks the gauge back by 5; a wrong quiz answer costs
XP only (scaled by JLPT level — see the table above). Add more collectibles
by calling `add_collectible(col, row, kind=...)` in
`kobito/levels/level1.py`.

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
lets you pick a starting **JLPT level** — N5 (beginner) through N1
(advanced) — or **AI Random**, which has Kobito pick one for you via a
Claude call (`kobito/difficulty.py`), falling back to a locally weighted
random pick (skewed toward beginner levels) if no API key/network.

A level is built as a chain of ground segments (`kobito/levels/level1.py`),
each carrying 2-3 question blocks, two ground patrols and one elevated
patrol, so enemy density scales with the level's length rather than
staying fixed. It ends at a **Japanese castle**
(`kobito/entities/goal.py`) — non-solid, the player runs straight into
it.

### Question count scales with level

Each JLPT level's question pool holds **30 questions**
(`assets/data/questions.json`), and how many of them a stage actually
asks climbs as you advance: level 1 needs 10 questions answered, and it
climbs by 2 per level (`QUESTIONS_PER_LEVEL_STEP` in
`kobito/constants.py`) up to that 30-question ceiling at level 11 and
beyond. The level generator keeps adding segments — and their question
blocks, enemies, and collectibles — until there are enough blocks to
comfortably clear that requirement, plus a small buffer
(`LEVEL_BLOCK_BUFFER`) so a player can skip one or two blocks and still
reach the bar.

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

You don't need a clean sweep — the bar is **70% correct** of that
level's required question count (`required_question_count()` and
`BADGE_PASS_ACCURACY` in `kobito/constants.py`) — 7 of 10 at level 1,
21 of 30 by level 11. The HUD tracks progress toward it as you play, and
a badge you narrowly missed is shown greyed out rather than hidden.
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

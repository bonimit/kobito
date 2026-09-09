# Kobito

An 8-bit style Japanese-learning platformer built with Pygame.

## Setup

```
pip install -r requirements.txt
python main.py
```

## Controls

- **Left/Right arrows or A/D** — choose mascot (select screen) / run (in-level)
- **Space / W / Up** — jump; **Enter/Space** — confirm mascot
- **1-4** — answer a question block's quiz
- **Esc** — quit

## Question blocks

Yellow "?" blocks in the level pause the game with a multiple-choice
Japanese question (vocabulary, kanji, grammar, or verb conjugation) drawn
from `assets/data/questions.json`. A correct answer adds to your score;
a wrong answer costs a life. Each block only fires once. Add more
questions by appending objects to that JSON file — each needs `category`,
`difficulty`, `prompt`, a `choices` list, an `answer` index, and an
optional `explanation` shown on a wrong answer.

Japanese text renders with a bundled font (`assets/fonts/ipag.ttf`,
IPA Font License v1.0) since pygame's default font has no CJK glyphs.

## Enemies, collectibles, and scenery

Simple patrol enemies (Goomba-style: walk back and forth, fall under
gravity, turn at their patrol bounds) roam the level; touching one costs
a life, with a brief blinking invulnerability window and knockback
afterward.

Collectibles — coins, shiitake mushrooms, and onigiri — are picked up on
touch (`kobito/entities/collectible.py`). Coins and onigiri add to your
score *and* fill a Life Gauge (0-100, shown under the score); a shiitake
instead grants an extra life outright. Reaching/exceeding a full gauge
grants a bonus life too (classic "100 coins = 1UP", just gauge-shaped),
carrying over any remainder. A wrong quiz answer or an enemy hit costs a
life *and* knocks the gauge back by 5 — mistakes cost progress toward
the next bonus life, not just the life you lose. Add more collectibles
by calling `add_collectible(col, row, kind=...)` in
`kobito/levels/level1.py`.

The backdrop is layered for depth (back to front): distant mountains,
two rolling-hill layers, clouds, then trees/bushes/flowers rooted in
the actual ground. Each layer scrolls at its own rate relative to the
camera (parallax — mountains barely move, hills a bit more, trees
scroll in lockstep since they're planted in the ground); trees, bushes,
and flowers are only ever placed on solid ground segments, never
floating over a gap. All of it is in `kobito/background.py`.

## Adding real sprite art

Each mascot has a folder at `assets/sprites/<character_id>/` with `idle/`,
`run/`, and `jump/` subfolders. Drop transparent PNG frames into the
matching subfolder, named so they sort in playback order (`00.png`,
`01.png`, `02.png`, ...). They're picked up automatically — no code
changes needed. Until frames exist for a character, a flat-color
placeholder is used instead.

Character ids: `capybara`, `sloth`, `kitsune`, `wombat`, `otter`,
`scottish_fold`, `frenchie`.

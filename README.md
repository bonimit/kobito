# Kobito

An 8-bit style Japanese-learning platformer built with Pygame.

## Setup

```
pip install -r requirements.txt
python main.py
```

## Controls

- **Left/Right arrows or A/D** — choose mascot/world (select screens) / run (in-level)
- **Space / W / Up** — jump; **Enter/Space** — confirm mascot/world
- **1-4** — answer a question block's quiz
- **Esc** — quit

## Question blocks

Yellow "?" blocks (drawn slightly larger than a tile, Mario-block style)
pause gameplay and show a small black box — anchored right next to the
block, above it if there's room or below otherwise, rest of the level
still visible — with a multiple-choice Japanese question (vocabulary,
kanji, grammar, or verb conjugation) drawn from
`assets/data/questions.json`. A correct answer adds to your score; a
wrong answer costs a life. Each block only fires once. Add more
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

## Worlds

Before a level starts, a world-select screen (mirroring the mascot
select screen) lets you pick from 5 themed worlds: Whispering Forest,
Sunfall Desert, Arabian Night, Coral Deep (underwater), and Cloud
Kingdom (sky). Each world has its own sky, ground/platform color, and
layered scenery (mountains/dunes/reef/cloud-hills in back; clouds/
stars+moon/bubbles/birds in the sky; trees/cacti/coral/floating-islands
rooted in the ground) — but the same gameplay layout underneath
(platforms, question blocks, enemies, collectibles).

A world is just data in `kobito/themes.py` (colors + which decorations
to draw, from the small shape library in `kobito/scenery_shapes.py`) —
adding a 6th world doesn't require touching the rendering code, only a
new `Theme(...)` entry. The backdrop is layered for depth (back to
front): mountains, two rolling-hill layers, the sky layer (clouds/
stars/bubbles/...), then ground props. Each layer scrolls at its own
rate relative to the camera (parallax); ground props are only ever
placed on solid ground segments, never floating over a gap. All of it
is rendered generically by `kobito/background.py`.

Each world also has living creatures that actually move over time
(not just scroll with the camera): Forest has birds and butterflies;
Desert has a hawk and a scorpion; Arabian Night has bats and a
scorpion; Coral Deep has fish, a squid, a whale, and a crab crawling
the seabed; Cloud Kingdom has a variety of birds. Flying/swimming
creatures wander the level with a gentle bob and wrap around when they
exit; ground creatures (crab, scorpion) patrol back and forth like a
decorative, non-colliding cousin of Enemy. A world adds creatures by
listing `FlyingCreature`/`GroundCreature` entries in its `Theme`.

## Adding real sprite art

Each mascot has a folder at `assets/sprites/<character_id>/` with `idle/`,
`run/`, and `jump/` subfolders. Drop transparent PNG frames into the
matching subfolder, named so they sort in playback order (`00.png`,
`01.png`, `02.png`, ...). They're picked up automatically — no code
changes needed. Until frames exist for a character, a flat-color
placeholder is used instead.

Character ids: `capybara`, `sloth`, `kitsune`, `wombat`, `otter`,
`scottish_fold`, `frenchie`.

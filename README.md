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

## Enemies and scenery

Simple patrol enemies (Goomba-style: walk back and forth, fall under
gravity, turn at their patrol bounds) roam the level; touching one costs
a life, with a brief blinking invulnerability window and knockback
afterward. Clouds and trees scroll behind the level at a slower rate
than the camera (parallax) for a sense of depth — purely decorative, no
collision. Both are defined in `kobito/levels/level1.py` and
`kobito/background.py`.

## Adding real sprite art

Each mascot has a folder at `assets/sprites/<character_id>/` with `idle/`,
`run/`, and `jump/` subfolders. Drop transparent PNG frames into the
matching subfolder, named so they sort in playback order (`00.png`,
`01.png`, `02.png`, ...). They're picked up automatically — no code
changes needed. Until frames exist for a character, a flat-color
placeholder is used instead.

Character ids: `capybara`, `sloth`, `kitsune`, `wombat`, `otter`,
`scottish_fold`, `frenchie`.

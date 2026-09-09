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
- **Esc** — quit

## Adding real sprite art

Each mascot has a folder at `assets/sprites/<character_id>/` with `idle/`,
`run/`, and `jump/` subfolders. Drop transparent PNG frames into the
matching subfolder, named so they sort in playback order (`00.png`,
`01.png`, `02.png`, ...). They're picked up automatically — no code
changes needed. Until frames exist for a character, a flat-color
placeholder is used instead.

Character ids: `capybara`, `sloth`, `kitsune`, `wombat`, `otter`,
`scottish_fold`, `frenchie`.

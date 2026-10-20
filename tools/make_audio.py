"""Composes and renders every sound in the game: a looping chiptune for
each world, secret stage and menu, plus the sound effects.

    python tools/make_audio.py           # writes assets/audio/{music,sfx}/*.ogg

Everything is synthesized here from code -- simple oscillators (square,
pulse, triangle, a plucked "koto", a bell), noise drums and envelopes --
so there are no samples or licences to worry about, and re-running gives
the same files every time (each track has its own random seed).

Each track is a TrackSpec: key, tempo, scale (Japanese yo / in /
Ryukyu, hijaz, blues, ...), two chord progressions, a lead instrument,
a rhythm feel and a drum pattern. A small composer turns that into
16 bars of melody (A A' B A form), bass, arpeggio and drums, rendered so
the end flows straight back into the start for a gapless loop.

Needs numpy and ffmpeg (with libvorbis) -- tools only; the game itself
just plays the .ogg files (see kobito/audio.py).
"""

import os
import random
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass, replace

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio")
SR = 22050

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pent": [0, 2, 4, 7, 9],              # major pentatonic
    "yo": [0, 2, 5, 7, 9],                # Japanese folk (min'yō)
    "in": [0, 1, 5, 7, 8],                # miyako-bushi -- Kyoto, koto music
    "ryukyu": [0, 4, 5, 7, 11],           # Okinawan
    "hijaz": [0, 1, 4, 5, 7, 8, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "whole": [0, 2, 4, 6, 8, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

MAJ, MIN = (0, 4, 7), (0, 3, 7)


@dataclass
class TrackSpec:
    key: int                  # MIDI note of the tonic (lead octave)
    bpm: int
    scale: str
    prog_a: list              # 4 chords: (semitones above the key, MAJ/MIN)
    prog_b: list
    lead: str = "square"      # square / pulse / tri / flute / koto / bell / saw
    feel: str = "bouncy"      # bouncy / calm / driving / swing / waltz
    drums: str = "pop"
    beats: int = 4            # 3 for a waltz
    arp: bool = True
    seed: int = 1
    lead_vol: float = 0.26


P = lambda *chords: list(chords)  # noqa: E731

TRACKS = {
    # Menus
    "title": TrackSpec(72, 116, "pent", P((0, MAJ), (9, MIN), (5, MAJ), (7, MAJ)),
                       P((5, MAJ), (7, MAJ), (4, MIN), (9, MIN)), "square", "bouncy", "pop", seed=11),
    "results": TrackSpec(69, 100, "major", P((0, MAJ), (5, MAJ), (7, MAJ), (0, MAJ)),
                         P((9, MIN), (5, MAJ), (2, MIN), (7, MAJ)), "bell", "calm", "light", seed=12),
    "town": TrackSpec(75, 108, "major", P((0, MAJ), (9, MIN), (2, MIN), (7, MAJ)),
                      P((5, MAJ), (4, MIN), (2, MIN), (7, MAJ)), "pulse", "swing", "swing", seed=13),
    "konbini": TrackSpec(70, 118, "pent", P((0, MAJ), (5, MAJ), (0, MAJ), (7, MAJ)),
                         P((9, MIN), (5, MAJ), (2, MIN), (7, MAJ)), "bell", "bouncy", "city", seed=14),
    "house": TrackSpec(72, 88, "major", P((0, MAJ), (4, MIN), (5, MAJ), (7, MAJ)),
                       P((9, MIN), (5, MAJ), (0, MAJ), (7, MAJ)), "tri", "calm", "light", seed=15),
    # Worlds
    "forest": TrackSpec(77, 112, "yo", P((0, MAJ), (5, MAJ), (0, MAJ), (7, MAJ)),
                        P((9, MIN), (5, MAJ), (2, MIN), (7, MAJ)), "flute", "bouncy", "light", seed=21),
    "desert": TrackSpec(74, 100, "hijaz", P((0, MAJ), (1, MAJ), (0, MAJ), (10, MIN)),
                        P((5, MIN), (1, MAJ), (10, MIN), (0, MAJ)), "pulse", "bouncy", "darbuka", seed=22),
    "arabian_night": TrackSpec(76, 92, "hijaz", P((0, MAJ), (5, MIN), (1, MAJ), (0, MAJ)),
                               P((8, MAJ), (1, MAJ), (5, MIN), (0, MAJ)), "flute", "calm", "darbuka", seed=23),
    "underwater": TrackSpec(75, 84, "whole", P((0, MAJ), (2, MAJ), (0, MAJ), (-2, MAJ)),
                            P((4, MAJ), (2, MAJ), (-2, MAJ), (0, MAJ)), "bell", "calm", "none", seed=24),
    "sky": TrackSpec(79, 108, "lydian", P((0, MAJ), (2, MAJ), (4, MIN), (2, MAJ)),
                     P((9, MIN), (7, MAJ), (2, MAJ), (0, MAJ)), "bell", "bouncy", "light", seed=25),
    "tokyo": TrackSpec(69, 124, "minor", P((8, MAJ), (10, MAJ), (7, MIN), (0, MIN)),
                       P((5, MIN), (10, MAJ), (3, MAJ), (8, MAJ)), "square", "driving", "city", seed=26),
    "nagano": TrackSpec(74, 96, "yo", P((0, MAJ), (5, MAJ), (2, MIN), (0, MAJ)),
                        P((9, MIN), (5, MAJ), (7, MAJ), (0, MAJ)), "koto", "calm", "taiko", seed=27),
    "okinawa": TrackSpec(72, 120, "ryukyu", P((0, MAJ), (5, MAJ), (7, MAJ), (0, MAJ)),
                         P((5, MAJ), (4, MIN), (7, MAJ), (0, MAJ)), "koto", "swing", "swing", seed=28),
    "hokkaido": TrackSpec(76, 100, "pent", P((0, MAJ), (9, MIN), (5, MAJ), (7, MAJ)),
                          P((5, MAJ), (0, MAJ), (2, MIN), (7, MAJ)), "bell", "calm", "light", seed=29),
    "kyoto": TrackSpec(74, 88, "in", P((0, MIN), (1, MAJ), (0, MIN), (8, MAJ)),
                       P((5, MIN), (1, MAJ), (8, MAJ), (0, MIN)), "koto", "calm", "taiko", seed=30),
    "island": TrackSpec(79, 118, "pent", P((0, MAJ), (5, MAJ), (7, MAJ), (5, MAJ)),
                        P((9, MIN), (5, MAJ), (0, MAJ), (7, MAJ)), "koto", "swing", "swing", seed=31),
    "fairy_tale": TrackSpec(70, 132, "major", P((0, MAJ), (7, MAJ), (9, MIN), (5, MAJ)),
                            P((2, MIN), (7, MAJ), (0, MAJ), (7, MAJ)), "bell", "waltz", "waltz", beats=3, seed=32),
    "london": TrackSpec(77, 112, "major", P((0, MAJ), (5, MAJ), (7, MAJ), (0, MAJ)),
                        P((9, MIN), (2, MIN), (7, MAJ), (0, MAJ)), "pulse", "bouncy", "march", seed=33),
    "new_york": TrackSpec(72, 126, "blues", P((0, MAJ), (5, MAJ), (0, MAJ), (7, MAJ)),
                          P((5, MAJ), (5, MAJ), (0, MAJ), (7, MAJ)), "square", "swing", "swing", seed=34),
    "korea": TrackSpec(79, 120, "pent", P((0, MAJ), (5, MAJ), (0, MAJ), (7, MAJ)),
                       P((9, MIN), (5, MAJ), (7, MAJ), (0, MAJ)), "flute", "waltz", "waltz", beats=3, seed=35),
    "okinawa_drive": TrackSpec(72, 132, "ryukyu", P((0, MAJ), (5, MAJ), (7, MAJ), (0, MAJ)),
                               P((5, MAJ), (4, MIN), (2, MIN), (7, MAJ)), "koto", "driving", "pop", seed=36),
    "aomori": TrackSpec(74, 104, "yo", P((0, MIN), (5, MAJ), (7, MIN), (0, MIN)),
                        P((10, MAJ), (5, MAJ), (7, MIN), (0, MIN)), "koto", "bouncy", "taiko", seed=37),
    "shizuoka": TrackSpec(77, 96, "pent", P((0, MAJ), (9, MIN), (5, MAJ), (7, MAJ)),
                          P((2, MIN), (7, MAJ), (5, MAJ), (0, MAJ)), "flute", "calm", "light", seed=38),
    "hokkaido_farm": TrackSpec(72, 116, "major", P((0, MAJ), (5, MAJ), (0, MAJ), (7, MAJ)),
                               P((5, MAJ), (0, MAJ), (7, MAJ), (0, MAJ)), "koto", "swing", "swing", seed=39),
    # Secret stages
    "subway": TrackSpec(69, 132, "minor", P((0, MIN), (8, MAJ), (10, MAJ), (0, MIN)),
                        P((5, MIN), (3, MAJ), (10, MAJ), (7, MIN)), "pulse", "driving", "drive", seed=41),
    "sewer": TrackSpec(64, 100, "minor", P((0, MIN), (5, MIN), (0, MIN), (7, MIN)),
                       P((8, MAJ), (5, MIN), (10, MAJ), (0, MIN)), "koto", "bouncy", "pop", seed=42),
    "mine": TrackSpec(62, 110, "phrygian", P((0, MIN), (1, MAJ), (0, MIN), (10, MIN)),
                      P((3, MAJ), (1, MAJ), (10, MIN), (0, MIN)), "tri", "driving", "taiko", seed=43),
    "rainbow": TrackSpec(72, 128, "major", P((0, MAJ), (7, MAJ), (9, MIN), (5, MAJ)),
                         P((5, MAJ), (7, MAJ), (4, MIN), (9, MIN)), "bell", "bouncy", "pop", seed=44),
    "thunder": TrackSpec(64, 140, "phrygian", P((0, MIN), (1, MAJ), (3, MAJ), (1, MAJ)),
                         P((5, MIN), (3, MAJ), (1, MAJ), (0, MIN)), "saw", "driving", "drive", seed=45),
    "moon": TrackSpec(80, 80, "lydian", P((0, MAJ), (2, MAJ), (0, MAJ), (7, MAJ)),
                      P((4, MIN), (2, MAJ), (9, MIN), (0, MAJ)), "bell", "calm", "none", seed=46),
}

# Every world has three tunes, one per stage in turn (kobito/game.py,
# Game._track): the original, then two variations on it that keep the
# world's scale and drums (its "sound") but change key, tempo, lead
# instrument, rhythm feel and melody -- "<world>_2" and "<world>_3".
WORLDS = ["forest", "desert", "arabian_night", "underwater", "sky", "tokyo", "nagano", "okinawa", "hokkaido",
          "kyoto", "island", "fairy_tale", "london", "new_york", "korea", "okinawa_drive", "aomori", "shizuoka",
          "hokkaido_farm"]
LEAD_SWAP = {"square": ("pulse", "flute"), "pulse": ("square", "bell"), "tri": ("flute", "pulse"),
             "flute": ("koto", "pulse"), "koto": ("flute", "bell"), "bell": ("tri", "koto"), "saw": ("pulse", "square")}
FEEL_SWAP = {"bouncy": ("driving", "calm"), "calm": ("bouncy", "swing"), "driving": ("bouncy", "swing"),
             "swing": ("bouncy", "calm"), "waltz": ("waltz", "waltz")}


def stage_variants(spec):
    """The 2nd and 3rd stage tunes of a world."""
    leads, feels = LEAD_SWAP[spec.lead], FEEL_SWAP[spec.feel]
    second = replace(spec, key=spec.key + 2, bpm=spec.bpm + 10, prog_a=spec.prog_b, prog_b=spec.prog_a,
                     lead=leads[0], feel=feels[0], seed=spec.seed + 100)
    third = replace(spec, key=spec.key - 3, bpm=max(80, spec.bpm - 12), lead=leads[1], feel=feels[1],
                    arp=not spec.arp, seed=spec.seed + 200,
                    drums=spec.drums if spec.drums in ("taiko", "darbuka", "waltz", "none") else "light")
    return second, third


for _world in WORLDS:
    TRACKS[f"{_world}_2"], TRACKS[f"{_world}_3"] = stage_variants(TRACKS[_world])

FEELS = {   # note lengths in 16th steps, and how likely each is
    "bouncy": ([2, 2, 2, 4, 1, 3], [5, 5, 5, 3, 1, 1], 0.12),
    "calm": ([4, 4, 8, 2, 6], [5, 5, 2, 2, 2], 0.15),
    "driving": ([2, 2, 1, 1, 4], [6, 6, 3, 3, 2], 0.08),
    "swing": ([2, 2, 4, 6, 3], [6, 6, 3, 1, 2], 0.12),
    "waltz": ([4, 2, 2, 8, 6], [6, 4, 4, 2, 2], 0.08),
}

DRUMS = {   # step -> instrument, over one bar (16 steps; 12 for 3/4)
    "pop": {0: "kick", 4: "snare", 8: "kick", 12: "snare", 2: "hat", 6: "hat", 10: "hat", 14: "hat"},
    "light": {0: "kick", 8: "rim", 4: "hat", 12: "hat"},
    "march": {0: "kick", 4: "snare", 8: "kick", 12: "snare", 14: "snare", 15: "snare"},
    "city": {0: "kick", 6: "kick", 8: "kick", 4: "snare", 12: "snare", 2: "ohat", 6.01: "hat", 10: "ohat",
             14: "hat"},
    "swing": {0: "kick", 8: "kick", 4: "snare", 12: "snare", 2: "hat", 6: "hat", 10: "hat", 14: "hat"},
    "taiko": {0: "taiko", 3: "taiko", 8: "taiko", 12: "rim", 14: "rim"},
    "darbuka": {0: "taiko", 6: "taiko", 4: "rim", 10: "rim", 12: "rim", 14: "rim"},
    "waltz": {0: "kick", 4: "hat", 8: "hat"},
    "drive": {0: "kick", 4: "snare", 8: "kick", 10: "kick", 12: "snare",
              **{s + 0.001: "hat" for s in range(0, 16, 2)}},
    "none": {},
}


# -- Synthesis -------------------------------------------------------------------

def freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def osc(kind, f, n, vibrato=0.0):
    t = np.arange(n) / SR
    if vibrato:
        # Vibrato fades in, like a held flute note.
        depth = vibrato * np.clip(t / 0.25, 0, 1)
        phase = np.cumsum(f * (1 + depth * np.sin(2 * np.pi * 5.5 * t))) / SR
    else:
        phase = f * t
    p = phase % 1.0
    if kind == "square":
        return np.where(p < 0.5, 1.0, -1.0)
    if kind == "pulse":
        return np.where(p < 0.25, 1.0, -1.0)
    if kind == "thin":
        return np.where(p < 0.125, 1.0, -1.0)
    if kind == "tri":
        return 4 * np.abs(p - 0.5) - 1
    if kind == "saw":
        return 2 * p - 1
    if kind == "sine":
        return np.sin(2 * np.pi * phase)
    raise ValueError(kind)


def adsr(n, attack=0.005, decay=0.08, sustain=0.6, release=0.05, hold=None):
    """An envelope n samples long: the note is held for `hold` samples (or
    all of it minus the release) then released."""
    hold = n - int(release * SR) if hold is None else hold
    hold = max(1, min(hold, n))
    env = np.full(n, sustain, dtype=float)
    a, d = int(attack * SR), int(decay * SR)
    a = max(1, min(a, hold))
    env[:a] = np.linspace(0, 1, a)
    d_end = min(hold, a + d)
    if d_end > a:
        env[a:d_end] = np.linspace(1, sustain, d_end - a)
    tail = n - hold
    if tail > 0:
        env[hold:] = env[hold - 1] * np.linspace(1, 0, tail)
    return env


def lowpass(x, width):
    if width <= 1:
        return x
    k = np.ones(width) / width
    return np.convolve(x, k, mode="same")


def instrument(name, midi, seconds):
    """One note of a named instrument, with its release tail."""
    f = freq(midi)
    if name in ("square", "pulse", "saw"):
        n = int((seconds + 0.06) * SR)
        wave_ = osc(name, f, n, vibrato=0.004)
        if name == "saw":
            wave_ = lowpass(wave_, 3)
        return wave_ * adsr(n, 0.004, 0.09, 0.55, 0.06) * (0.7 if name == "saw" else 1.0)
    if name == "tri":
        n = int((seconds + 0.06) * SR)
        return osc("tri", f, n, vibrato=0.003) * adsr(n, 0.004, 0.1, 0.8, 0.06) * 1.3
    if name == "flute":
        n = int((seconds + 0.08) * SR)
        body = osc("tri", f, n, vibrato=0.012) + 0.25 * osc("sine", f * 2, n)
        breath = np.random.default_rng(midi).normal(0, 0.04, n)
        return (body + lowpass(breath, 6)) * adsr(n, 0.03, 0.1, 0.8, 0.08)
    if name == "koto":   # plucked: bright attack that mellows and dies away
        n = int((min(seconds, 0.9) + 0.4) * SR)
        t = np.arange(n) / SR
        bright = osc("saw", f, n) * np.exp(-t * 9)
        mellow = osc("tri", f, n) * np.exp(-t * 3.2)
        return (lowpass(bright, 2) * 0.6 + mellow) * adsr(n, 0.002, 0.0, 1.0, 0.05) * 1.1
    if name == "bell":   # music box / glockenspiel
        n = int((min(seconds, 1.2) + 0.5) * SR)
        t = np.arange(n) / SR
        tone = osc("sine", f, n) + 0.35 * osc("sine", f * 2.0, n) * np.exp(-t * 6) + 0.2 * osc("sine", f * 3.01, n) * np.exp(-t * 9)
        return tone * np.exp(-t * 3.5) * adsr(n, 0.002, 0.0, 1.0, 0.04) * 1.2
    if name == "bass":
        n = int((seconds + 0.04) * SR)
        return osc("tri", f, n) * adsr(n, 0.004, 0.05, 0.9, 0.04)
    if name == "arp":
        n = int((seconds + 0.03) * SR)
        return osc("thin", f, n) * adsr(n, 0.002, 0.05, 0.3, 0.03)
    raise ValueError(name)


def drum(name, rng):
    if name == "kick":
        n = int(0.18 * SR)
        t = np.arange(n) / SR
        f = 120 * np.exp(-t * 28) + 42
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * 1.2
    if name == "taiko":
        n = int(0.32 * SR)
        t = np.arange(n) / SR
        f = 95 * np.exp(-t * 12) + 55
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
        slap = lowpass(rng.normal(0, 1, n), 8) * np.exp(-t * 60) * 0.5
        return (body + slap) * 1.2
    if name == "snare":
        n = int(0.14 * SR)
        t = np.arange(n) / SR
        noise = lowpass(rng.normal(0, 1, n), 2) * np.exp(-t * 26)
        tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
        return (noise * 0.55 + tone * 0.5)
    if name == "rim":
        n = int(0.05 * SR)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * 820 * t) * np.exp(-t * 90) * 0.5
    if name in ("hat", "ohat"):
        n = int((0.12 if name == "ohat" else 0.035) * SR)
        t = np.arange(n) / SR
        noise = rng.normal(0, 1, n)
        noise = noise - lowpass(noise, 3)   # crude high-pass
        return noise * np.exp(-t * (30 if name == "ohat" else 120)) * 0.35
    raise ValueError(name)


# -- Composition -----------------------------------------------------------------

def scale_notes(spec, low, high):
    """Every MIDI note of the track's scale between low and high."""
    steps = SCALES[spec.scale]
    root = spec.key % 12
    return [m for m in range(low, high + 1) if (m - root) % 12 in steps]


def chord_tones(spec, chord):
    root, quality = chord
    return {(spec.key + root + q) % 12 for q in quality}


def rhythm(spec, rng, steps):
    lengths, weights, rest_chance = FEELS[spec.feel]
    out, t = [], 0
    while t < steps:
        length = rng.choices(lengths, weights)[0]
        length = min(length, steps - t)
        out.append((t, length, rng.random() < rest_chance and t > 0))
        t += length
    return out


def motif(spec, rng, chords, start_note, steps_per_bar, register):
    """A 2-bar melody over two chords: a list of (step, length, midi or None)."""
    pool = scale_notes(spec, register[0], register[1])
    i = min(range(len(pool)), key=lambda k: abs(pool[k] - start_note))
    notes = []
    for bar, chord in enumerate(chords):
        tones = chord_tones(spec, chord)
        for step, length, rest in rhythm(spec, rng, steps_per_bar):
            if rest:
                notes.append((bar * steps_per_bar + step, length, None))
                continue
            i = max(0, min(len(pool) - 1, i + rng.choice([-2, -1, -1, 0, 1, 1, 2, 3, -3])))
            strong = step % (steps_per_bar // (2 if spec.beats == 4 else 3)) == 0
            if strong or length >= 4:   # land strong beats and long notes on the chord
                near = [k for k in range(len(pool)) if pool[k] % 12 in tones]
                if near:
                    i = min(near, key=lambda k: abs(k - i))
            notes.append((bar * steps_per_bar + step, length, pool[i]))
    return notes


def resolve(spec, notes, steps_per_bar):
    """Ends a phrase on the tonic: the last note becomes the nearest tonic,
    held to the end of the phrase."""
    for j in range(len(notes) - 1, -1, -1):
        step, length, midi = notes[j]
        if midi is not None:
            tonic = min((m for m in range(midi - 12, midi + 13) if (m - spec.key) % 12 == 0),
                        key=lambda m: abs(m - midi))
            end = 2 * steps_per_bar
            return notes[:j] + [(step, end - step, tonic)]
    return notes


def compose(spec):
    """Returns the whole loop as event lists for each part."""
    rng = random.Random(spec.seed)
    spb = spec.beats * 4
    reg = (spec.key - 5, spec.key + 12)
    a1 = motif(spec, rng, spec.prog_a[:2], spec.key, spb, reg)
    a2 = motif(spec, rng, spec.prog_a[2:], spec.key + 2, spb, reg)
    a2_end = resolve(spec, motif(spec, random.Random(spec.seed + 7), spec.prog_a[2:], spec.key + 2, spb, reg), spb)
    b1 = motif(spec, rng, spec.prog_b[:2], spec.key + 4, spb, (spec.key, spec.key + 15))
    b2 = motif(spec, rng, spec.prog_b[2:], spec.key + 5, spb, (spec.key, spec.key + 15))
    # A A' B A' -- the tune comes back so it's catchy, and the loop point
    # lands on the tonic.
    phrases = [a1, a2, a1, a2_end, b1, b2, a1, a2_end]
    lead = []
    for k, phrase in enumerate(phrases):
        lead += [(k * 2 * spb + s, length, m) for s, length, m in phrase]
    chords = (spec.prog_a + spec.prog_a + spec.prog_b + spec.prog_a)
    return lead, chords, spb


def swing_offset(spec, step):
    return 0.33 if spec.feel == "swing" and step % 4 == 2 else 0.0


def render_track(spec):
    lead, chords, spb = compose(spec)
    step_s = 60.0 / spec.bpm / 4
    bars = len(chords)
    total = int(round(bars * spb * step_s * SR))
    mix = np.zeros(total + SR * 2)
    rng = np.random.default_rng(spec.seed)

    def put(sound, start_step, vol):
        start = int(round(start_step * step_s * SR))
        mix[start:start + len(sound)] += sound * vol

    for step, length, midi in lead:
        if midi is not None:
            put(instrument(spec.lead, midi, length * step_s * 0.92), step + swing_offset(spec, step), spec.lead_vol)

    for bar, (root, quality) in enumerate(chords):
        base = bar * spb
        bass_root = spec.key - 24 + root
        while bass_root < spec.key - 31:
            bass_root += 12
        while bass_root > spec.key - 19:
            bass_root -= 12
        if spec.beats == 3:
            pattern = [(0, 4, 0), (4, 4, 7), (8, 4, 7)]
        elif spec.feel == "calm":
            pattern = [(0, 6, 0), (6, 2, 7), (8, 8, 0)]
        else:
            pattern = [(0, 3, 0), (3, 1, 0), (4, 2, 12), (6, 2, 7), (8, 3, 0), (11, 1, 0), (12, 2, 12), (14, 2, 7)]
        for s, length, interval in pattern:
            put(instrument("bass", bass_root + interval, length * step_s * 0.9), base + s + swing_offset(spec, s), 0.24)
        if spec.arp:
            tones = [spec.key - 12 + root + q for q in quality] + [spec.key + root]
            for s in range(0, spb, 2 if spec.feel == "calm" else 1):
                if spec.feel == "calm" and spec.lead == "bell" and s % 4:
                    continue
                put(instrument("arp", tones[(s // (2 if spec.feel == "calm" else 1)) % len(tones)], step_s * 0.8),
                    base + s + swing_offset(spec, s), 0.05)

        pattern = DRUMS[spec.drums]
        if spec.beats == 3:
            pattern = {k: v for k, v in pattern.items() if k < 12}
        for s, name in pattern.items():
            put(drum(name, rng), base + int(s) + swing_offset(spec, int(s)), 0.32)

    # Wrap the tail of the last notes round to the start: a seamless loop.
    out = mix[:total].copy()
    tail = mix[total:]
    out[:len(tail)] += tail[:total]
    peak = np.max(np.abs(out)) or 1.0
    return out / peak * 0.82


# -- Sound effects ---------------------------------------------------------------

def sweep(f0, f1, seconds, kind="square", curve=1.0):
    n = int(seconds * SR)
    t = np.linspace(0, 1, n)
    f = f0 + (f1 - f0) * t ** curve
    phase = np.cumsum(f) / SR
    p = phase % 1
    if kind == "square":
        return np.where(p < 0.5, 1.0, -1.0)
    if kind == "pulse":
        return np.where(p < 0.25, 1.0, -1.0)
    if kind == "tri":
        return 4 * np.abs(p - 0.5) - 1
    return np.sin(2 * np.pi * phase)


def fade(x, attack=0.003, power=1.0):
    n = len(x)
    env = np.linspace(1, 0, n) ** power
    a = max(1, int(attack * SR))
    env[:a] *= np.linspace(0, 1, a)
    return x * env


def seq(notes, step, kind="square", tail=0.0, vol=1.0):
    """A little jingle: notes is a list of MIDI numbers (None = rest)."""
    out = np.zeros(int((len(notes) * step + tail + 2.0) * SR))
    for i, m in enumerate(notes):
        if m is None:
            continue
        length = step + (tail if i == len(notes) - 1 else 0)
        n = int(length * SR)
        if kind == "bell":
            s = instrument("bell", m, length)
        else:
            s = osc(kind, freq(m), n) * adsr(n, 0.003, 0.05, 0.6, 0.04)
        start = int(i * step * SR)
        out[start:start + len(s)] += s * vol
    end = len(out)
    while end > 1 and abs(out[end - 1]) < 1e-4:
        end -= 1
    return out[:end]


def mixdown(*parts):
    out = np.zeros(max(len(p) for p in parts))
    for p in parts:
        out[:len(p)] += p
    return out


def noise(seconds, smooth=1, seed=0):
    return lowpass(np.random.default_rng(seed).normal(0, 1, int(seconds * SR)), smooth)


def make_sfx():
    s = {}
    s["jump"] = fade(sweep(300, 720, 0.14, "pulse", 0.6), power=1.5) * 0.45
    s["flap"] = fade(sweep(500, 900, 0.09, "pulse"), power=2) * 0.35
    s["coin"] = np.concatenate([fade(osc("square", freq(88), int(0.06 * SR)), power=0.3),
                                fade(osc("square", freq(93), int(0.22 * SR)), power=1.6)]) * 0.35
    s["item"] = seq([79, 83, 86, 91], 0.05, "pulse", 0.1) * 0.4
    s["powerup"] = seq([67, 71, 74, 79, 83, 86, 91, 95], 0.045, "square", 0.12) * 0.35
    s["stomp"] = fade(sweep(400, 90, 0.12, "square"), power=1.4) * 0.5
    s["zap"] = (fade(sweep(900, 200, 0.16, "square"), power=1.2) * 0.35 + fade(noise(0.16, 2, 1)) * 0.2)
    s["hit"] = (fade(sweep(220, 70, 0.25, "square"), power=0.8) * 0.45 + fade(noise(0.25, 3, 2), power=2) * 0.3)
    s["oneup"] = seq([76, 79, 88, 84, 86, 91], 0.075, "square", 0.1) * 0.35
    s["block"] = fade(sweep(180, 260, 0.08, "tri"), power=1.2) * 0.7
    s["correct"] = seq([84, 88, 91, 96], 0.07, "bell", 0.35) * 0.55
    s["wrong"] = (seq([62, 61], 0.13, "square", 0.12) * 0.25)
    s["skip"] = fade(sweep(600, 400, 0.12, "tri"), power=1.5) * 0.4
    s["select"] = fade(osc("pulse", freq(84), int(0.04 * SR))) * 0.25
    s["confirm"] = seq([79, 91], 0.05, "pulse", 0.08) * 0.35
    s["back"] = seq([79, 72], 0.05, "pulse", 0.06) * 0.3
    s["pause"] = seq([88, 84, 88, 84], 0.05, "square", 0.04) * 0.25
    s["gift"] = seq([72, 76, 79, 84, 88], 0.05, "bell", 0.3) * 0.5
    s["spring"] = fade(sweep(150, 1100, 0.32, "tri", 0.5), power=0.8) * 0.6
    s["fall"] = fade(sweep(800, 120, 0.6, "square", 0.7), power=0.5) * 0.3
    s["warp"] = (fade(sweep(200, 900, 0.4, "sine", 2.0)) * 0.4 + fade(sweep(300, 1350, 0.4, "tri", 2.0)) * 0.2)
    s["gate"] = seq([67, 63], 0.12, "pulse", 0.1) * 0.35
    s["throw"] = fade(sweep(700, 1200, 0.08, "pulse"), power=1.5) * 0.25
    s["clear"] = seq([72, 76, 79, 84, None, 79, 84, 88, 91], 0.1, "square", 0.6) * 0.35
    s["gameover"] = seq([72, 71, 70, 69, None, 64, 60], 0.16, "tri", 0.6) * 0.5
    s["levelup"] = seq([72, 76, 79, 84, 79, 84, 88, 96], 0.07, "bell", 0.6) * 0.55
    s["buy"] = mixdown(seq([96, 100], 0.06, "bell", 0.3) * 0.45, fade(noise(0.08, 1, 3), power=3) * 0.15)
    s["chime"] = seq([79, 76], 0.28, "bell", 0.8) * 0.5   # the konbini door
    s["equip"] = seq([76, 83, 88], 0.06, "pulse", 0.12) * 0.35
    s["denied"] = fade(osc("square", 110, int(0.22 * SR)), power=0.5) * 0.25
    s["copter"] = fade(sweep(380, 520, 0.12, "pulse"), power=0.6) * 0.18
    return s


# -- Output ----------------------------------------------------------------------

def write_ogg(path, samples, quality=0):
    pcm = (np.clip(samples, -1, 1) * 32000).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = tmp.name
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", str(quality),
                    path], check=True)
    os.unlink(wav)


def main(only=None):
    os.makedirs(os.path.join(OUT, "music"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "sfx"), exist_ok=True)
    for name, spec in TRACKS.items():
        if only and name not in only:
            continue
        samples = render_track(spec)
        write_ogg(os.path.join(OUT, "music", f"{name}.ogg"), samples)
        print(f"music/{name}.ogg  {len(samples) / SR:.1f}s")
    for name, samples in make_sfx().items():
        if only and name not in only:
            continue
        write_ogg(os.path.join(OUT, "sfx", f"{name}.ogg"), samples / max(1.0, np.max(np.abs(samples))), quality=4)
    print("sfx done")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)

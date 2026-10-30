"""A 45-second trailer for Kobito in a modern pixel-art style, made from the real game.

    python tools/make_ad45.py            # writes docs/ad45_16x9.mp4 (1920x1080, 45.0 s)

Art direction: a modern indie pixel trailer, not a 2000s TV spot.
  * Palette: deep night ink, warm off-white and one amber accent (a cyan
    for the odd detail) -- nothing else of our own on screen.
  * Cards (opening, levels, end) are drawn on a real 480x270 pixel canvas
    and blown up 4x with hard edges: an ordered-dither sky, 1-px stars,
    the logo assembling from scattered pixels, the fox running in.
  * Type: DotGothic16 rendered on its native 16-px grid without
    anti-aliasing and scaled by whole numbers, letter-spaced, with a 1-px
    hard shadow. Captions sit in the scene, not on a box: a soft vignette
    behind them, a small amber label ("01  EXPLORE"), a headline and a
    quiet M PLUS Rounded subtitle, each with a soft shadow.
  * Motion: hard cuts inside a chapter; a short pixel-mosaic dissolve
    between chapters; text slides up in whole pixel steps.

     0  opening -- the logo assembles, the capybara walks in
     4  01 EXPLORE   the overworld map
     9  02 PLAY      run · jump · stomp
    15  03 LEARN     every block is a quiz
    19  04 TRAVEL    Hawaii, the North Pole, Galápagos
    24  05 DISCOVER  secret rooms: fall in, parachute down
    29  06 STUDY     vocabulary, kanji, JLPT-style
    33  07 BUDDY     a wrong answer and a live AI hint
    39  end card

Every gameplay shot is the actual game, driven frame by frame by
tools/make_ad.py. Needs ffmpeg and numpy.
"""

import math
import os
import random
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_ad as ad  # noqa: E402  (sets up headless pygame + the fake clock / keyboard)

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from kobito import town_ui  # noqa: E402
from kobito.companion_select_screen import CompanionSelectScreen  # noqa: E402
from kobito.fonts import pixel_font, rounded_font  # noqa: E402
from kobito.game import Game  # noqa: E402
from kobito.questions import shuffled  # noqa: E402
from kobito.quiz_screen import PHASE_ANSWERING, QuizScreen  # noqa: E402
from kobito.world_select_screen import WorldSelectScreen  # noqa: E402

FPS = ad.FPS
LENGTH = 45 * FPS
W, H = 1920, 1080
LW, LH = 480, 270                      # the pixel canvas of the cards (x4)
RIGHT, UP, JUMP, RUN, FIRE = pygame.K_RIGHT, pygame.K_UP, pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_x
snap, place, reset, bot, quiz_frames = ad.snap, ad.place, ad.reset, ad.bot, ad.quiz_frames
held = ad.held

INK = (14, 11, 26)
INK_2 = (30, 24, 52)
INK_3 = (52, 42, 86)
PAPER = (244, 238, 226)
MUTED = (178, 168, 196)
AMBER = (255, 190, 76)
CYAN = (110, 214, 230)


def step(g, n=ad.SIM_STEPS):
    """Advance the game, with the companion's chatter line kept quiet (the captions sit there)."""
    ad.step(g, n)
    g.coach.speech = None


def frame(game=None, eyebrow=None, head=None, sub=None, card=None, top=False):
    """One frame of the trailer: a game picture (or a full-screen card) and
    its caption -- a small label, a headline and a subtitle. `top` moves the
    caption off the bottom (to the right-hand side), for shots whose action
    is at the bottom."""
    return {"game": game, "eyebrow": eyebrow, "head": head, "sub": sub, "card": card, "top": top}


# == Pixel type ===============================================================================

def px_text(text, color, size=16, scale=2, spacing=0, shadow=INK, bold=False):
    """Crisp pixel text: DotGothic16 at a multiple of its 16-px grid, no
    anti-aliasing, a 1-px hard shadow, scaled up by a whole number.
    `spacing` adds tracking between letters (for small all-caps labels;
    headlines keep the font's own spacing); `bold` doubles the stems."""
    font = pixel_font(size)

    def ink(col):
        if not spacing:
            return font.render(text, False, col)
        glyphs = [font.render(c, False, col) for c in text]
        surf = pygame.Surface((sum(gl.get_width() for gl in glyphs) + spacing * (len(text) - 1),
                               font.get_height()), pygame.SRCALPHA)
        x = 0
        for gl in glyphs:
            surf.blit(gl, (x, 0))
            x += gl.get_width() + spacing
        return surf

    face = ink(color)
    extra = 1 if bold else 0
    surf = pygame.Surface((face.get_width() + 1 + extra, face.get_height() + 1), pygame.SRCALPHA)
    if shadow:
        dark = ink(shadow)
        for dx in range(extra + 1):
            surf.blit(dark, (1 + dx, 1))
    for dx in range(extra + 1):
        surf.blit(face, (dx, 0))
    return pygame.transform.scale(surf, (surf.get_width() * scale, surf.get_height() * scale))


def soft_text(text, color, size=30):
    """The quiet subtitle face."""
    return rounded_font(size).render(text, True, color)


# == Pixel canvas helpers (the cards) ===========================================================

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def night(c, glow=AMBER):
    """An ordered-dither night sky: ink at the top, two dithered bands
    towards the horizon and a low warm glow."""
    c.fill(INK)
    for y in range(LH):
        k = y / LH
        for col, start in ((INK_2, 0.45), (INK_3, 0.78)):
            if k > start:
                level = min(1, (k - start) / 0.22) * 16
                for x in range(LW):
                    if BAYER[y % 4][x % 4] < level:
                        c.set_at((x, y), col)
    warm = tuple(round(a * 0.35 + b * 0.65) for a, b in zip(glow, INK_3))
    for y in range(LH - 24, LH):
        level = (y - (LH - 24)) / 24 * 10
        for x in range(LW):
            if BAYER[y % 4][x % 4] < level:
                c.set_at((x, y), warm)


_night_cache = {}


def night_bg(c, t):
    """The night sky (drawn once -- night() is per-pixel) with twinkling 1-px stars."""
    if "sky" not in _night_cache:
        sky = pygame.Surface((LW, LH))
        night(sky)
        _night_cache["sky"] = sky
    c.blit(_night_cache["sky"], (0, 0))
    rng = random.Random(11)
    for _ in range(70):
        x, y = rng.randrange(LW), rng.randrange(LH - 60)
        phase, speed = rng.uniform(0, 6.3), rng.uniform(1.5, 3)
        bright = rng.random() < 0.3
        if math.sin(t * speed + phase) > -0.2:
            c.set_at((x, y), PAPER if bright else MUTED)


# The wordmark, hand-lettered on a 5x7 grid (a font's bare "I" read as "KOB|TO").
GLYPHS = {
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
}
CELL = 5                                   # canvas pixels per grid cell


def logo_pixels():
    """Every canvas pixel of the KOBITO wordmark, and its size."""
    if "logo" not in _night_cache:
        pts, x = [], 0
        for ch in "KOBITO":
            for gy, row in enumerate(GLYPHS[ch]):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        pts += [(x + gx * CELL + i, gy * CELL + j) for i in range(CELL) for j in range(CELL)]
            x += 6 * CELL
        _night_cache["logo"] = (pts, (x - CELL, 7 * CELL))
    return _night_cache["logo"]


def draw_logo(c, t, center, assemble=1.0, seed=3):
    """The wordmark, assembling from scattered pixels while `assemble` < 1;
    settled pixels get a two-step amber extrusion underneath."""
    pts, (w, h) = logo_pixels()
    x0, y0 = center[0] - w // 2, center[1] - h // 2
    rng = random.Random(seed)
    placed = []
    for (x, y) in pts:
        delay = rng.uniform(0, 0.45)
        k = min(1.0, max(0.0, (assemble - delay) / 0.55))
        k = 1 - (1 - k) ** 3
        sx, sy = rng.randrange(LW), rng.randrange(LH)
        placed.append((round(sx + (x0 + x - sx) * k), round(sy + (y0 + y - sy) * k), k))
    for px, py, k in placed:
        if k >= 1:
            pygame.draw.rect(c, (150, 96, 40), (px, py + 1, 1, 3))
            c.set_at((px, py + 1), AMBER)
            c.set_at((px, py + 2), AMBER)
    for px, py, k in placed:
        if 0 <= px < LW and 0 <= py < LH:
            c.set_at((px, py), PAPER if k >= 1 else (AMBER if k > 0.5 else MUTED))


def upscale(c, out):
    pygame.transform.scale(c, (W, H), out)


def blit_center(out, img, cx, y):
    out.blit(img, (cx - img.get_width() // 2, y))


# == Shots ===================================================================================

def opening(n=120):
    mascot = town_ui.Mascot("capybara")
    canvas = pygame.Surface((LW, LH))

    def draw(out, t):
        night_bg(canvas, t)
        draw_logo(canvas, t, (LW // 2, 108), assemble=min(1.0, t / 2.0))
        # the capybara walks in along the horizon and stops under the logo
        k = min(1.0, t / 2.6)
        fx = round(-40 + (LW // 2 + 40) * (1 - (1 - k) ** 2))
        mascot.update(1 / FPS, k < 1)
        sprite = mascot.frame([], scale=1, moving=k < 1, facing_right=True)
        canvas.blit(sprite, sprite.get_rect(midbottom=(fx, LH - 26)))
        pygame.draw.rect(canvas, INK_3, (0, LH - 26, LW, 1))
        upscale(canvas, out)
        if t > 2.2:
            k2 = min(1.0, (t - 2.2) / 0.5)
            label = px_text("こびと", AMBER, 16, 3, spacing=4)
            blit_center(out, label, W // 2, round(560 - 8 * (1 - k2)) // 4 * 4)
        if t > 2.7:
            line = soft_text("A pixel platformer that teaches you Japanese", PAPER, 34)
            blit_center(out, line, W // 2, 660)

    for i in range(n):
        yield frame(card=lambda out, t=i / FPS: draw(out, t))


def world_map(n=150):
    m = WorldSelectScreen("capybara")
    towns = ["tokyo", "kyoto", "okinawa"]            # a little tour along the roads
    m.x, m.y = m.world.nodes["sky"]
    m._snap_camera()
    leg = 0
    for i in range(n):
        if not m.route and leg < len(towns):
            m.route = m.world.route(m.x, m.y, towns[leg])
            leg += 1
        dt = 1 / FPS
        m.time += dt
        m._walk(dt)
        m.mascot.update(dt, m.moving)
        m._follow(dt)
        m._draw()
        yield frame(m.screen.copy(), "01  EXPLORE", "Pick a world", "23 places on one big map")


def run_jump_stomp(g, n=165):
    reset(g, g.surface)
    place(g, 64)
    held.update({RIGHT, RUN})
    for i in range(n):
        bot(g)
        step(g)
        yield frame(snap(g), "02  PLAY", "Run, jump, stomp", "Classic platforming, from Tokyo to Hokkaido")
    held.clear()


def quiz_block(g):
    s = g.surface
    block = min((b for b in s.question_blocks if b.rect.x > g.player.rect.x + 60), key=lambda b: b.rect.x)
    question = shuffled(g.question_bank.questions[0], random.Random(3))       # 犬 (いぬ)
    reset(g)
    place(g, block.rect.centerx - 70)
    caps = ("03  LEARN", "Every block is a quiz", "Answer in Japanese to power up")
    held.add(RIGHT)
    for _ in range(10):
        if g.player.rect.centerx >= block.rect.centerx - 4:
            held.discard(RIGHT)
        step(g)
        yield frame(snap(g), *caps)
    held.discard(RIGHT)
    held.add(JUMP)
    real_check = g._check_question_blocks

    async def no_quiz():
        return None
    g._check_question_blocks = no_quiz
    for _ in range(12):
        step(g)
        if block in g.player.touched:
            break
        yield frame(snap(g), *caps)
    held.clear()
    block.mark_used()
    bg = snap(g)
    for i, f in enumerate(quiz_frames(g, question, block.rect.move(-g.camera_x, 0), bg, 54, n_reveal=30)):
        yield frame(f["game"], *(caps if i < 54 else ("03  LEARN", "Correct!", "犬 = いぬ, dog  ·  +10 XP")))
    block.mark_answered(True)
    g._add_effect_text("+10 XP", (block.rect.centerx, block.rect.top), (150, 255, 170))
    for _ in range(24):
        step(g)
        yield frame(snap(g), "03  LEARN", "Correct!", "犬 = いぬ, dog  ·  +10 XP")
    g._check_question_blocks = real_check


def around_the_world(per=56):
    stops = [("hawaii", "Hawaii", "ハワイ"), ("north_pole", "North Pole", "ほっきょく"),
             ("galapagos", "Galápagos", "ガラパゴス")]
    for theme, name, kana in stops:
        g = Game("capybara", theme, companion_id="hana", item_box={}, badges=[])
        g._take_hit = lambda *_: None
        reset(g)
        place(g, 400)
        held.update({RIGHT, RUN})
        step(g, 20)
        g.banner = None
        for _ in range(per):
            bot(g)
            step(g)
            g.effects = []                         # no pickup labels floating through the caption
            yield frame(snap(g), "04  TRAVEL", name, kana)
        held.clear()


def secret_rooms(g):
    s = g.surface
    pit = s.secret_pits[0]
    reset(g, s)
    place(g, (pit["x0"] + pit["x1"]) // 2, s.ground_y - 40)
    for i in range(75):
        step(g)
        if g.world is not s and g.transition is None:
            held.update({RIGHT, RUN})
            bot(g)
        yield frame(snap(g), "05  DISCOVER", "Secret rooms", "Subways, sewers and mines under every stage")
    held.clear()
    reset(g, s)
    g._enter_sky(next(iter(s.springs)).link)
    g._leave_hidden()
    step(g, 70)                       # let the chute drift into view first
    g.banner = None
    for _ in range(66):
        step(g)
        yield frame(snap(g), "05  DISCOVER", "Parachute down", "パラシュート  ·  back from the secret sky")


QUIZ_KINDS = [("Vocabulary", "gen_meaning_n4_地震"), ("Kanji", "kanji_n2_001"), ("JLPT-style", None)]


def learn(g):
    bank = {q["id"]: q for q in g.question_bank.questions}
    jlpt = next((q for q in g.question_bank.questions if q.get("style") == "jlpt" and "ordering" in q["id"]), None)
    reset(g, g.surface)
    place(g, 1500)
    step(g, 4)
    bg = snap(g)
    anchor = pygame.Rect(480, 420, 1, 1)
    for i, (name, qid) in enumerate(QUIZ_KINDS):
        q = jlpt if qid is None else bank.get(qid)
        if q is None:
            continue
        quiz = QuizScreen(g.screen, shuffled(q, random.Random(i)), background=bg, anchor_rect=anchor,
                          hint_service=g.hint_service, points=20)
        for _ in range(40):
            quiz._age += 1 / FPS
            quiz._draw(None, PHASE_ANSWERING)
            yield frame(g.screen.copy(), "06  STUDY", name, "Endless questions, from your first kana to JLPT N1")


def ai_buddy(g):
    picker = CompanionSelectScreen()
    for i in range(60):
        index = [0, 2][min(1, i // 30)]
        if index != picker.index:
            picker.index, picker.typed = index, 0.0
        picker.time += 1 / FPS
        picker.typed += 60 / FPS
        picker.backdrop.update(1 / FPS)
        picker._draw()
        yield frame(picker.screen.copy())          # a full screen of its own UI: no caption on top
    bank = {q["id"]: q for q in g.question_bank.questions}
    q = shuffled(bank["kanji_n5_001"], random.Random(1))
    reset(g, g.surface)
    place(g, 2900)
    step(g, 4)
    bg = snap(g)
    hint = ("Ooh, so close! 語 means 'language' and it's read ご -- so think 'Japan' + 'language'. "
            "You've got this!")
    for i, f in enumerate(quiz_frames(g, q, pygame.Rect(480, 430, 1, 1), bg, 24, answer_right=False,
                                      n_reveal=12, hint=hint, n_hint=90)):
        if i < 36:
            yield frame(f["game"], "07  BUDDY", "Stuck?", "Your buddy has your back", top=True)
        else:
            yield frame(f["game"], "07  BUDDY", "Live AI hints", "Written for you by Claude, Gemini or ChatGPT",
                        top=True)


def end_card(n):
    mascot = town_ui.Mascot("capybara")
    canvas = pygame.Surface((LW, LH))

    def draw(out, t):
        night_bg(canvas, t + 3)
        draw_logo(canvas, t, (LW // 2, 64), assemble=1.0)
        mascot.update(1 / FPS, False)
        sprite = mascot.frame([], scale=1, moving=False, facing_right=True)
        bob = 1 if (t * 2) % 1 < 0.5 else 0
        canvas.blit(sprite, sprite.get_rect(midbottom=(LW // 2, LH - 26 - bob)))
        pygame.draw.rect(canvas, INK_3, (0, LH - 26, LW, 1))
        upscale(canvas, out)
        blit_center(out, px_text("こびと", AMBER, 16, 3, spacing=4), W // 2, 408)
        if t > 0.4:
            blit_center(out, px_text("PLAY FREE IN YOUR BROWSER", PAPER, 16, 3, spacing=2), W // 2, 540)
        if t > 0.8:
            blit_center(out, soft_text("bonimit.itch.io/kobito", AMBER, 40), W // 2, 618)
        if t > 1.2:
            blit_center(out, soft_text("Keyboard or gamepad  ·  JLPT N5 to N1  ·  Free", PAPER, 28), W // 2, 1012)

    for i in range(n):
        yield frame(card=lambda out, t=i / FPS: draw(out, t))


# == Composition ================================================================================

_shade_cache = {}


def corner_shade(right):
    """A soft elliptical darkening that grows out of the caption's side of
    the screen -- a vignette, not a box -- so the words sit in the scene's
    own shadow. Bottom-left normally; the right edge for `right`."""
    if right not in _shade_cache:
        ys, xs = np.mgrid[0:H, 0:W]
        if right:
            d = np.sqrt(((xs - W) / 1150.0) ** 2 + ((ys - 600) / 520.0) ** 2)
        else:
            d = np.sqrt((xs / 1500.0) ** 2 + ((ys - (H - 230)) / 480.0) ** 2)    # centred on the words
        alpha = (np.clip(1 - d, 0, 1) ** 1.1 * 236).astype(np.uint8)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((*INK, 0))
        pygame.surfarray.pixels_alpha(shade)[:] = alpha.T
        _shade_cache[right] = shade
    return _shade_cache[right]


def soft_shadow(img, radius=6):
    """A blurred ink copy of `img` to lift text off the picture."""
    w, h = img.get_size()
    pad = radius * 3
    base = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    dark = img.copy()
    dark.fill((*INK, 255), special_flags=pygame.BLEND_RGBA_MIN)
    base.blit(dark, (pad, pad))
    small = pygame.transform.smoothscale(base, (max(1, base.get_width() // radius), max(1, base.get_height() // radius)))
    return pygame.transform.smoothscale(small, base.get_size()), pad


def caption(out, f, age):
    """Words in the scene, not on a card: a soft vignette from the corner,
    then an amber label, the headline and a quiet subtitle, each with a soft
    shadow. Lines rise in whole-pixel steps and arrive one after another."""
    lines = []
    if f["eyebrow"]:
        lines.append(("label", px_text(f["eyebrow"], AMBER, 16, 2, spacing=2), 0))
    if f["head"]:
        lines.append(("head", px_text(f["head"], PAPER, 16, 4, bold=True), 5))
    if f["sub"]:
        lines.append(("sub", soft_text(f["sub"], PAPER, 30), 10))
    if not lines:
        return
    gaps = {"label": 12, "head": 8, "sub": 0}
    shade = corner_shade(f["top"])
    shade.set_alpha(round(255 * min(1.0, age / 12)))
    out.blit(shade, (0, 0))
    height = sum(img.get_height() + gaps[kind] for kind, img, _ in lines)
    # bottom-left, clear of the game's own companion bar; or right-aligned mid-screen
    y = 600 - height // 2 if f["top"] else H - 150 - height
    for kind, img, delay in lines:
        x = W - 104 - img.get_width() if f["top"] else 104
        k = min(1.0, max(0.0, (age - delay) / 10))
        if k > 0:
            lift = round(12 * (1 - k)) // 4 * 4
            glow, pad = soft_shadow(img)
            glow.set_alpha(round(200 * k))
            out.blit(glow, (x - pad, y + lift - pad + 4))
            img = img.copy()
            img.set_alpha(round(255 * k))
            out.blit(img, (x, y + lift))
        y += img.get_height() + gaps[kind]


def compose(f, age):
    out = pygame.Surface((W, H))
    if f["card"]:
        f["card"](out)
    else:
        pygame.transform.scale(f["game"], (W, H), out)
        caption(out, f, age)
    return out


def mosaic(out, block):
    if block <= 1:
        return out
    small = pygame.transform.scale(out, (W // block, H // block))
    return pygame.transform.scale(small, (W, H))


# == Soundtrack =================================================================================

RATE = 44100


def _sq(freq, dur, duty=0.25, vol=0.2, decay=5.0):
    t = np.arange(int(RATE * dur)) / RATE
    return vol * np.where((t * freq) % 1.0 < duty, 1.0, -1.0) * np.exp(-decay * t) * np.minimum(1, t * 300)


def _tri(freq, dur, vol=0.3, decay=3.0):
    t = np.arange(int(RATE * dur)) / RATE
    return vol * (2 * np.abs(2 * ((t * freq) % 1.0) - 1) - 1) * np.exp(-decay * t) * np.minimum(1, t * 300)


def _nz(dur, vol, decay, seed=1):
    t = np.arange(int(RATE * dur)) / RATE
    return vol * np.random.default_rng(seed).uniform(-1, 1, len(t)) * np.exp(-decay * t)


def _hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _lowpass(x, k=0.25):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(0, len(x), 1):
        acc += k * (x[i] - acc)
        y[i] = acc
    return y


def soundtrack(duration, cuts, path):
    """Warm, modern chiptune at 100 bpm in D major-pentatonic: a soft
    triangle bass, a thin pulse lead with a dotted echo, a gentle kick and
    a hat. A quiet intro pad, a soft tick on each chapter, and a resolving
    chord on the end card."""
    total = np.zeros(int(RATE * (duration + 1)))

    def add(sig, at, gain=1.0):
        i = int(at * RATE)
        if i < len(total):
            total[i:i + len(sig)] += gain * sig[:len(total) - i]

    beat = 60 / 100
    intro, end = 2.9, duration - 6.0
    # Intro: a slow pad and a rising arpeggio as the logo forms.
    for n_ in (50, 57, 62, 66):
        add(_tri(_hz(n_), intro + 0.6, 0.06, 0.4), 0)
    for i, n_ in enumerate((74, 76, 78, 81, 83, 86)):
        add(_sq(_hz(n_), 0.3, 0.125, 0.05, 6), 0.35 + i * 0.22)
    chords = [(38, [62, 66, 69]), (35, [59, 62, 66]), (43, [62, 67, 71]), (45, [61, 64, 69])]   # D Bm G A
    lead = [74, -1, 76, 78, -1, 81, 78, 76, 74, -1, 71, 74, -1, 76, -1, -1,
            78, -1, 81, 83, -1, 81, 78, -1, 76, 78, -1, 74, -1, -1, -1, -1]
    k, t = 0, intro
    while t < end:
        root, chord = chords[(k // 16) % 4]
        if k % 4 == 0:
            add(_tri(_hz(root), beat * 1.6, 0.30, 1.6), t)
            add(_sq(52, 0.12, 0.5, 0.22, 30), t)                                   # soft kick
        if k % 4 == 2:
            add(_tri(_hz(root + 12), beat * 0.6, 0.16, 3), t)
        if k % 8 == 4:
            add(_nz(0.09, 0.07, 30, seed=k), t)                                     # light snare
        if k % 2 == 1:
            add(_nz(0.025, 0.025, 90, seed=3), t)                                   # hat
        if k % 8 == 0:
            for n_ in chord:
                add(_tri(_hz(n_), beat * 3.5, 0.035, 0.8), t)                       # pad
        note = lead[k % len(lead)]
        if note > 0:
            tone = _sq(_hz(note), beat * 0.4, 0.125, 0.06, 5)
            add(tone, t)
            add(tone, t + beat * 0.75, 0.35)                                        # dotted echo
        t += beat / 4 * 2
        k += 1
    # A soft tick on each chapter change.
    for at in cuts:
        add(_sq(_hz(98), 0.05, 0.5, 0.025, 40), at)
    # End: a warm resolving chord and the intro arpeggio once more.
    for n_ in (38, 50, 62, 66, 69, 74):
        add(_tri(_hz(n_), 5.5, 0.07, 0.6), end)
    for i, n_ in enumerate((74, 78, 81, 86)):
        add(_sq(_hz(n_), 0.35, 0.125, 0.045, 5), end + 0.2 + i * 0.2)
    total = total[:int(RATE * duration)]
    total = _lowpass(total, 0.55)
    fade = int(RATE * 1.2)
    total[-fade:] *= np.linspace(1, 0, fade)
    total /= max(1e-6, np.abs(total).max()) / 0.85
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((total * 32767).astype(np.int16).tobytes())


# == Main =======================================================================================

DISSOLVE = [2, 3, 4, 6, 8, 10, 10, 8, 6, 4, 3, 2]     # mosaic block size over the frames around a chapter cut


def main():
    out_dir = ad.OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    video_tmp = os.path.join(tmp, "video.mp4")
    enc = ad.encoder(video_tmp, (W, H))

    g = Game("capybara", "tokyo", companion_id="hana", item_box={}, badges=[])
    g._take_hit = lambda *_: None
    sections = [opening(), world_map(), run_jump_stomp(g), quiz_block(g), around_the_world(),
                secret_rooms(g), learn(g), ai_buddy(g)]
    cuts = []

    def stream():
        """Every frame in order; the end card fills whatever is left of the 45 s."""
        n = 0
        for section in sections:
            cuts.append(n)
            for f in section:
                yield f
                n += 1
        if LENGTH - n < 3 * FPS:
            raise SystemExit(f"shots run {n / FPS:.1f} s -- trim them, the end card needs 3 s")
        cuts.append(n)
        yield from end_card(LENGTH - n)

    # Frames go out a few behind the ones being made, so a dissolve can start before its cut.
    half = len(DISSOLVE) // 2
    last, age, buffer, i = None, 0, [], 0
    source = stream()
    done = False
    while not done or buffer:
        while not done and len(buffer) < half + 1:
            try:
                buffer.append(next(source))
            except StopIteration:
                done = True
        f = buffer.pop(0)
        ad.frame_no = i
        key = (f["eyebrow"], f["head"])
        age = age + 1 if key == last else 0
        last = key
        out = compose(f, age)
        for c in cuts[1:]:
            if c - half <= i < c + half:
                out = mosaic(out, DISSOLVE[i - (c - half)])
        enc.stdin.write(pygame.image.tobytes(out, "RGB"))
        i += 1
    enc.stdin.close()
    enc.wait()
    duration = i / FPS
    print(f"{i} frames = {duration:.1f} s; chapters at {', '.join(f'{c / FPS:.1f}' for c in cuts)}")

    audio = os.path.join(tmp, "music.wav")
    soundtrack(duration, [c / FPS for c in cuts[1:]], audio)
    out = os.path.join(out_dir, "ad45_16x9.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_tmp, "-i", audio, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"{out}: {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

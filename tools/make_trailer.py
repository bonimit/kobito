"""A one-minute trailer for Kobito in a modern pixel-art style, made from the real game.

    python tools/make_trailer.py         # writes docs/trailer_16x9.mp4 (1920x1080, 60.0 s)

Art direction: a modern indie pixel trailer, not a 2000s TV spot.
  * Palette: deep night ink, warm off-white and one amber accent (a cyan
    for the odd detail) -- nothing else of our own on screen.
  * Cards (opening, levels, end) are drawn on a real 480x270 pixel canvas
    and blown up 4x with hard edges: an ordered-dither sky, 1-px stars,
    the logo assembling from scattered pixels, the fox running in.
  * Type: DotGothic16 rendered on its native 16-px grid without
    anti-aliasing and scaled by whole numbers, letter-spaced, with a 1-px
    hard shadow. Captions sit quietly at the bottom right, in the scene
    rather than on a box: a soft vignette behind them, a small amber label
    ("01  EXPLORE"), a headline and a muted subtitle.
  * Music: Y2K eurodance / J-pop at 132 bpm -- supersaw stabs, octave
    bass, four-on-the-floor, a sparkle arpeggio; the drop lands on the map.
  * Motion: hard cuts inside a chapter; a half-second crossfade between
    chapters; text rises in whole pixel steps.

It tells one journey, each beat held long enough to take in, chapters
joined by a gentle half-second crossfade:

     0  opening -- the logo assembles, the capybara walks in
     5  THE JOURNEY BEGINS  walk the world map to Tokyo and hop in
    11  TOKYO               first steps: run, jump, stomp
    17  TOKYO               the first ? block -- a question, answered right
    22  UNDER THE CITY      drop down a hole, explore the secret room, climb back out
    33  A LITTLE HELP       a wrong answer; Hana's live hint
    39  FURTHER AWAY        Hawaii, the North Pole, Galápagos
    47  GROWING             harder questions, then N5 -> N1
    55  end card

The hero only ever falls into a hole in the "under the city" chapter (and
that shot follows it all the way down and back up); anywhere else the
render stops with an error if it does.

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
LENGTH = 60 * FPS
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
#
# One continuous journey: the same Tokyo stage (one Game) runs from the first
# steps through the quiz, the secret subway and the hint; then the world opens up.

class Detour(Exception):
    """The hero changed world (fell down a hole) in a shot that isn't about that."""


def run_bot(g, jump_holes=True):
    """make_ad's auto-runner, plus: take off early for every hole in the
    ground (at full run it otherwise reacts too late and drops into a
    secret pit, which only the 'under the city' chapter should show)."""
    bot(g)
    p = g.player
    if jump_holes and p.on_ground and not g.world.hidden:
        for pit in g.surface.secret_pits:
            if 0 < pit["x0"] - p.rect.right < 90:
                held.add(JUMP)


def ad_game(theme):
    """A Game for the trailer: no damage, and no interactive quiz popping up
    when the hero bumps a ? block (it would wait for a key press forever --
    the trailer draws its quizzes itself)."""
    g = Game("capybara", theme, companion_id="hana", item_box={}, badges=[])
    g._take_hit = lambda *_: None

    async def no_quiz():
        return None
    g._check_question_blocks = no_quiz
    return g


def stay_on_surface(g):
    if g.world is not g.surface:
        raise Detour("the hero fell into a hole outside the secret-room chapter")


def opening(n=150):
    mascot = town_ui.Mascot("capybara")
    canvas = pygame.Surface((LW, LH))

    def draw(out, t):
        night_bg(canvas, t)
        draw_logo(canvas, t, (LW // 2, 108), assemble=min(1.0, t / 2.2))
        # the capybara walks in along the horizon and stops under the logo
        k = min(1.0, t / 3.0)
        fx = round(-40 + (LW // 2 + 40) * (1 - (1 - k) ** 2))
        mascot.update(1 / FPS, k < 1)
        sprite = mascot.frame([], scale=1, moving=k < 1, facing_right=True)
        canvas.blit(sprite, sprite.get_rect(midbottom=(fx, LH - 26)))
        pygame.draw.rect(canvas, INK_3, (0, LH - 26, LW, 1))
        upscale(canvas, out)
        if t > 2.4:
            k2 = min(1.0, (t - 2.4) / 0.5)
            label = px_text("こびと", AMBER, 16, 3, spacing=4)
            blit_center(out, label, W // 2, round(560 - 8 * (1 - k2)) // 4 * 4)
        if t > 3.0:
            line = soft_text("A pixel platformer that teaches you Japanese", PAPER, 34)
            line.set_alpha(round(255 * min(1.0, (t - 3.0) / 0.6)))
            blit_center(out, line, W // 2, 660)

    for i in range(n):
        yield frame(card=lambda out, t=i / FPS: draw(out, t))


def world_map(walk=150, hold=10):
    """Choose Tokyo on the map: walk there along the roads, hop in, fade."""
    from kobito.world_select_screen import ENTER_SECONDS
    m = WorldSelectScreen("capybara")
    dest = "tokyo"
    # start from the town whose road to Tokyo is about four seconds' walk
    start = min((n for n in m.world.nodes if n != dest), key=lambda n: abs(_route_len(m, n, dest) - 760))
    m.x, m.y = m.world.nodes[start]
    m._snap_camera()
    m.route = m.world.route(m.x, m.y, dest)
    caps = ("THE JOURNEY BEGINS", "Pick where to go", "23 places on one big map")
    dt = 1 / FPS
    for i in range(walk + hold):
        m.time += dt
        m._walk(dt)
        m.mascot.update(dt, m.moving)
        m._follow(dt)
        m._draw()
        yield frame(m.screen.copy(), *caps)
    m._update_near(quiet=True)
    m.near = dest
    m._go_in()
    while m.entering[1] < ENTER_SECONDS:
        m.entering[1] += dt
        m.time += dt
        m.mascot.update(dt, False)
        m._draw()
        yield frame(m.screen.copy(), *caps)


def _route_len(m, start, dest):
    x, y = m.world.nodes[start]
    pts = [(x, y)] + list(m.world.route(x, y, dest))
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def first_steps(g, n=180):
    reset(g, g.surface)
    place(g, 64)
    held.update({RIGHT, RUN})
    for _ in range(n):
        run_bot(g)
        step(g)
        stay_on_surface(g)
        yield frame(snap(g), "TOKYO", "First steps", "Run, jump and stomp through the city")
    held.clear()


def first_question(g):
    s = g.surface
    block = min((b for b in s.question_blocks if b.rect.x > g.player.rect.x + 60), key=lambda b: b.rect.x)
    question = shuffled(g.question_bank.questions[0], random.Random(3))       # 犬 (いぬ)
    reset(g)
    place(g, block.rect.centerx - 140)
    caps = ("TOKYO", "Every block asks a question", "Answer in Japanese to power up")
    held.add(RIGHT)
    for _ in range(24):
        if g.player.rect.centerx >= block.rect.centerx - 4:
            held.discard(RIGHT)
        step(g)
        yield frame(snap(g), *caps)
    held.discard(RIGHT)
    held.add(JUMP)
    for _ in range(14):
        step(g)
        if block in g.player.touched:
            break
        yield frame(snap(g), *caps)
    held.clear()
    block.mark_used()
    bg = snap(g)
    right = ("TOKYO", "Correct!", "犬 = いぬ  ·  dog  ·  +10 XP")
    for i, f in enumerate(quiz_frames(g, question, block.rect.move(-g.camera_x, 0), bg, 60, n_reveal=36)):
        yield frame(f["game"], *(caps if i < 60 else right))
    block.mark_answered(True)
    g._add_effect_text("+10 XP", (block.rect.centerx, block.rect.top), (150, 255, 170))
    for _ in range(30):
        step(g)
        yield frame(snap(g), *right)


def under_the_city(g):
    """Run up to a hole, drop in, land in the hidden room, explore -- then
    climb the rope back out and hop onto the street. The whole round trip."""
    s = g.surface
    pit = min((p for p in s.secret_pits if p["x0"] > g.player.rect.right + 300), key=lambda p: p["x0"],
              default=s.secret_pits[0])
    reset(g, s)
    place(g, pit["x0"] - 260)
    held.update({RIGHT})
    caps = ("UNDER THE CITY", "A hole in the street…", "Some holes lead somewhere")
    for _ in range(150):                                          # walk in (no jumping) and fall
        step(g)
        yield frame(snap(g), *caps)
        if g.world is not s or g.transition is not None:
            break
    else:
        raise Detour("the hero never fell into the secret pit")
    held.clear()
    while g.transition is not None:                               # the fade, game paused
        step(g)
        yield frame(snap(g), *caps)
    room = g.world
    from kobito.game import HIDDEN_STYLES
    spec = HIDDEN_STYLES[room.style]                              # whichever room this hole leads to
    caps = ("UNDER THE CITY", f"A secret {spec['meaning']}", f"{spec['jp']} ({spec['reading']})  ·  hidden rooms under every stage")
    held.update({RIGHT})
    for _ in range(80):                                           # land, look around, explore
        if g.player.on_ground:
            run_bot(g, jump_holes=False)
        step(g)
        yield frame(snap(g), *caps)
    held.clear()
    # back up the rope
    reset(g, room)
    place(g, room.goal.rect.centerx, room.ground_y)
    held.add(UP)
    caps = ("UNDER THE CITY", "Climb back out", "のぼる  ·  to climb")
    for _ in range(150):                                          # climb, fade, hop out of the hole
        step(g)
        if g.world is s:
            held.clear()
        yield frame(snap(g), *caps)
        if g.world is s and g.climb_out is None and g.transition is None:
            break
    held.update({RIGHT})                                          # and carry on down the street
    for _ in range(24):
        step(g)
        yield frame(snap(g), *caps)
    held.clear()


def a_little_help(g):
    bank = {q["id"]: q for q in g.question_bank.questions}
    q = shuffled(bank["kanji_n5_001"], random.Random(1))
    reset(g, g.surface)
    step(g, 4)
    bg = snap(g)
    hint = ("Ooh, so close! 語 means 'language' and it's read ご -- so think 'Japan' + 'language'. "
            "You've got this!")
    for i, f in enumerate(quiz_frames(g, q, pygame.Rect(480, 430, 1, 1), bg, 45, answer_right=False,
                                      n_reveal=20, hint=hint, n_hint=120)):
        if i < 65:
            yield frame(f["game"], "A LITTLE HELP", "Stuck?", "Everyone gets stuck sometimes", top=True)
        else:
            yield frame(f["game"], "A LITTLE HELP", "Hana's got you", "Live hints from Claude, Gemini or ChatGPT",
                        top=True)


def travel(theme, name, kana, n=84):
    def shot():
        g = ad_game(theme)
        reset(g)
        place(g, 400)
        held.update({RIGHT, RUN})
        step(g, 20)
        g.banner = None
        for _ in range(n):
            run_bot(g)
            step(g)
            stay_on_surface(g)
            g.effects = []                         # no pickup labels floating through the caption
            yield frame(snap(g), "FURTHER AWAY", name, kana)
        held.clear()
    return shot()


QUIZ_KINDS = [("Vocabulary", "gen_meaning_n4_地震"), ("Kanji", "kanji_n2_001"), ("JLPT-style", None)]


def growing(g):
    bank = {q["id"]: q for q in g.question_bank.questions}
    jlpt = next((q for q in g.question_bank.questions if q.get("style") == "jlpt" and "ordering" in q["id"]), None)
    reset(g, g.surface)
    step(g, 4)
    bg = snap(g)
    anchor = pygame.Rect(480, 420, 1, 1)
    for i, (name, qid) in enumerate(QUIZ_KINDS):
        q = jlpt if qid is None else bank.get(qid)
        if q is None:
            continue
        quiz = QuizScreen(g.screen, shuffled(q, random.Random(i)), background=bg, anchor_rect=anchor,
                          hint_service=g.hint_service, points=20)
        for _ in range(45):
            quiz._age += 1 / FPS
            quiz._draw(None, PHASE_ANSWERING)
            yield frame(g.screen.copy(), "GROWING", name, "The questions grow with you", top=True)


def levels_card(n=105):
    canvas = pygame.Surface((LW, LH))
    levels = ["N5", "N4", "N3", "N2", "N1"]

    def draw(out, t):
        night_bg(canvas, t)
        tile, gap = 52, 12
        x0 = LW // 2 - (5 * tile + 4 * gap) // 2
        lit_upto = t / 0.35
        for i, lv in enumerate(levels):
            rect = pygame.Rect(x0 + i * (tile + gap), 74, tile, tile)
            lit = i < lit_upto
            pygame.draw.rect(canvas, INK, rect.move(2, 2))
            pygame.draw.rect(canvas, AMBER if lit else INK_2, rect)
            pygame.draw.rect(canvas, PAPER if lit else INK_3, rect, 1)
            label = px_text(lv, INK if lit else MUTED, 16, 1, shadow=None)
            canvas.blit(label, label.get_rect(center=rect.center))
            if i < 4:
                for d in range(2, gap - 1, 3):
                    canvas.set_at((rect.right + d, rect.centery), AMBER if i + 1 < lit_upto else INK_3)
        upscale(canvas, out)
        if t > 1.2:
            img = px_text("FROM YOUR FIRST KANA TO JLPT N1", PAPER, 16, 3, spacing=2)
            img.set_alpha(round(255 * min(1.0, (t - 1.2) / 0.5)))
            blit_center(out, img, W // 2, 660)
        if t > 1.8:
            img = soft_text("Endless questions, new every time you play", MUTED, 32)
            img.set_alpha(round(255 * min(1.0, (t - 1.8) / 0.5)))
            blit_center(out, img, W // 2, 760)

    for i in range(n):
        yield frame(card=lambda out, t=i / FPS: draw(out, t))


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
    """A soft darkening growing out of the bottom-right corner (or the right
    edge, mid-height, for `right`) -- a vignette, not a box, so the words sit
    in the scene's own shadow."""
    if right not in _shade_cache:
        ys, xs = np.mgrid[0:H, 0:W]
        cy = 560 if right else H - 160
        d = np.sqrt(((xs - W) / 980.0) ** 2 + ((ys - cy) / 360.0) ** 2)
        alpha = (np.clip(1 - d, 0, 1) ** 1.3 * 200).astype(np.uint8)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((*INK, 0))
        pygame.surfarray.pixels_alpha(shade)[:] = alpha.T
        _shade_cache[right] = shade
    return _shade_cache[right]


def soft_shadow(img, radius=5):
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
    """A quiet caption at the bottom right, right-aligned: a small amber
    label, the headline, a muted subtitle -- in the scene's shadow, never on
    a box. (`top` lifts it to mid-height on the right, above a bottom panel.)
    Lines fade in one after another, rising in whole-pixel steps."""
    lines = []
    if f["eyebrow"]:
        lines.append(("label", px_text(f["eyebrow"], AMBER, 16, 1, spacing=2, shadow=None), 0))
    if f["head"]:
        lines.append(("head", px_text(f["head"], PAPER, 16, 3), 5))
    if f["sub"]:
        lines.append(("sub", soft_text(f["sub"], MUTED, 24), 10))
    if not lines:
        return
    gaps = {"label": 8, "head": 6, "sub": 0}
    shade = corner_shade(f["top"])
    shade.set_alpha(round(255 * min(1.0, age / 12)))
    out.blit(shade, (0, 0))
    height = sum(img.get_height() + gaps[kind] for kind, img, _ in lines)
    y = 560 - height // 2 if f["top"] else H - 140 - height
    for kind, img, delay in lines:
        x = W - 96 - img.get_width()
        k = min(1.0, max(0.0, (age - delay) / 10))
        if k > 0:
            lift = round(8 * (1 - k)) // 4 * 4
            glow, pad = soft_shadow(img)
            glow.set_alpha(round(190 * k))
            out.blit(glow, (x - pad, y + lift - pad + 3))
            img = img.copy()
            img.set_alpha(round(235 * k))
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


# == Soundtrack =================================================================================

RATE = 44100


def _t(dur):
    return np.arange(int(RATE * dur)) / RATE


def _env(t, attack=0.004, decay=6.0):
    return np.minimum(1, t / attack) * np.exp(-decay * t)


def _saw(freq, t):
    return 2 * ((t * freq) % 1.0) - 1


def _supersaw(freq, dur, vol, decay=4.0, detune=(-0.12, -0.05, 0, 0.05, 0.12)):
    """Five detuned saws -- the shiny Y2K trance stab."""
    t = _t(dur)
    wave_ = sum(_saw(freq * 2 ** (c / 12), t + i * 0.0013) for i, c in enumerate(detune)) / len(detune)
    return vol * wave_ * _env(t, 0.003, decay)


def _sq(freq, dur, duty=0.25, vol=0.2, decay=5.0):
    t = _t(dur)
    return vol * np.where((t * freq) % 1.0 < duty, 1.0, -1.0) * _env(t, 0.002, decay)


def _kick(vol=0.9):
    t = _t(0.28)
    freq = 48 + 120 * np.exp(-28 * t)
    return vol * np.sin(2 * np.pi * np.cumsum(freq) / RATE) * np.exp(-9 * t)


def _noise(dur, vol, decay, seed=1):
    t = _t(dur)
    return vol * np.random.default_rng(seed).uniform(-1, 1, len(t)) * np.exp(-decay * t)


def _hp(x):
    """A crude high-pass: what's left after a running average."""
    return x - np.convolve(x, np.ones(8) / 8, mode="same")


def _hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def soundtrack(duration, cuts, path):
    """Y2K eurodance / J-pop at 132 bpm in B minor (Bm G D A): four-on-the-
    floor kick, clap on 2 and 4, open hats on the off-beats, an octave-
    bouncing bass, detuned supersaw stabs that pump against the kick, and a
    sparkly 16th-note square arpeggio. A filtered build with a noise riser
    under the logo, the drop when the map appears, a riser into each
    chapter, and a final stab with a cymbal on the end card."""
    total = np.zeros(int(RATE * (duration + 2)))

    def add(sig, at, gain=1.0):
        i = int(at * RATE)
        if 0 <= i < len(total):
            total[i:i + len(sig)] += gain * sig[:len(total) - i]

    beat = 60 / 132
    six = beat / 4
    drop, end = cuts[0], cuts[-1]
    prog = [(47, [66, 71, 74]), (43, [67, 71, 74]), (50, [66, 69, 74]), (45, [64, 69, 73])]   # Bm G D A
    arp = [0, 1, 2, 1, 2, 0, 1, 2, 3, 2, 1, 2, 0, 1, 2, 1]
    # Build: arpeggio alone, getting brighter, over a noise riser.
    n = int(drop / six)
    for k in range(n):
        root, chord = prog[(k // 16) % 4]
        notes = chord + [chord[0] + 12]
        add(_sq(_hz(notes[arp[k % 16]] + 12), six * 0.9, 0.125, 0.03 + 0.05 * k / n, 14), k * six)
        if k % 4 == 0 and k > n // 2:
            add(_kick(0.5), k * six)
    riser = _noise(drop, 1.0, 0, seed=9) * np.linspace(0, 1, int(RATE * drop)) ** 2 * 0.10
    add(_hp(riser), 0)
    # Main section.
    k, t = 0, drop
    while t < end:
        root, chord = prog[(k // 16) % 4]
        pos = k % 16
        if pos % 4 == 0:
            add(_kick(), t)
        if pos in (4, 12):
            add(_hp(_noise(0.16, 0.30, 18, seed=k)), t)                               # clap
        if pos % 4 == 2:
            add(_hp(_noise(0.12, 0.13, 14, seed=3)), t)                               # open hat
        else:
            add(_hp(_noise(0.03, 0.05, 90, seed=4)), t)                               # closed hat
        if pos % 2 == 0:                                                              # octave bass
            add(_sq(_hz(root + (12 if pos % 4 == 2 else 0)), six * 1.6, 0.5, 0.16, 7), t)
        if pos in (2, 6, 10, 14):                                                     # off-beat stabs
            for note in chord:
                add(_supersaw(_hz(note), beat * 0.45, 0.07, 7), t)
        notes = chord + [chord[0] + 12]
        add(_sq(_hz(notes[arp[pos]] + 12), six * 0.8, 0.125, 0.045, 14), t)            # sparkle arp
        t += six
        k += 1
    # A riser into each chapter after the drop.
    for c in cuts[1:-1]:
        length = beat * 2
        sweep = _noise(length, 1.0, 0, seed=int(c * 10)) * np.linspace(0, 1, int(RATE * length)) ** 3 * 0.12
        add(_hp(sweep), c - length)
    # End card: a big stab, a crash, a fading sparkle.
    for note in (47, 59, 66, 71, 74, 78):
        add(_supersaw(_hz(note), 4.0, 0.06, 0.8), end)
    add(_kick(), end)
    add(_hp(_noise(2.5, 0.22, 1.6, seed=7)), end)
    for i, note in enumerate((83, 86, 90, 95)):
        add(_sq(_hz(note), 0.3, 0.125, 0.04, 6), end + 0.25 + i * six * 2)
    # Pump: duck everything a little on each kick of the main section.
    pump = np.ones(len(total))
    k = 0
    while drop + k * beat < end:
        i = int((drop + k * beat) * RATE)
        dip = 1 - 0.35 * np.exp(-np.arange(int(RATE * beat)) / (RATE * 0.09))
        pump[i:i + len(dip)] = dip[:len(pump) - i]
        k += 1
    total *= pump
    total = total[:int(RATE * duration)]
    fade = int(RATE * 1.5)
    total[-fade:] *= np.linspace(1, 0, fade)
    total = np.tanh(total / max(1e-6, np.abs(total).max()) * 1.6)          # glue + loudness
    total /= np.abs(total).max() / 0.9
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((total * 32767).astype(np.int16).tobytes())


# == Main =======================================================================================

CROSSFADE = 15          # frames: each chapter fades in over the last frame of the one before


def main():
    out_dir = ad.OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    video_tmp = os.path.join(tmp, "video.mp4")
    enc = ad.encoder(video_tmp, (W, H))

    g = ad_game("tokyo")
    sections = [opening(), world_map(), first_steps(g), first_question(g), under_the_city(g), a_little_help(g),
                travel("hawaii", "Hawaii", "ハワイ"), travel("north_pole", "North Pole", "ほっきょく"),
                travel("galapagos", "Galápagos", "ガラパゴス"), growing(g), levels_card()]
    cuts = []

    def stream():
        """Every frame in order; the end card fills whatever is left of the minute."""
        n = 0
        for section in sections:
            cuts.append(n)
            for f in section:
                yield f
                n += 1
        if LENGTH - n < 4 * FPS:
            raise SystemExit(f"shots run {n / FPS:.1f} s -- trim them, the end card needs 4 s")
        cuts.append(n)
        yield from end_card(LENGTH - n)

    last, age, i = None, 0, 0
    previous = None                  # the last frame of the chapter before, for the crossfade
    for f in stream():
        ad.frame_no = i
        key = (f["eyebrow"], f["head"])
        age = age + 1 if key == last else 0
        last = key
        out = compose(f, age)
        since = i - max(c for c in cuts if c <= i)
        if previous is not None and i > 0 and since < CROSSFADE:
            k = (since + 1) / (CROSSFADE + 1)
            fade = previous.copy()
            fade.set_alpha(round(255 * (1 - k) ** 1.5))
            out.blit(fade, (0, 0))
        if since >= CROSSFADE or i == 0:
            held_frame = out
        enc.stdin.write(pygame.image.tobytes(out, "RGB"))
        if i + 1 in cuts:
            previous = held_frame
        i += 1
    enc.stdin.close()
    enc.wait()
    duration = i / FPS
    print(f"{i} frames = {duration:.1f} s; chapters at {', '.join(f'{c / FPS:.1f}' for c in cuts)}")

    audio = os.path.join(tmp, "music.wav")
    soundtrack(duration, [c / FPS for c in cuts[1:]], audio)
    out = os.path.join(out_dir, "trailer_16x9.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_tmp, "-i", audio, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"{out}: {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

"""A 45-second TV-style spot for Kobito: bright, fast and bouncy, made from the real game.

    python tools/make_ad45.py            # writes docs/ad45_16x9.mp4 (1920x1080, 45.0 s)

The look of a console-game commercial: big chunky words that pop in on a
tilted ribbon ("RUN!", "JUMP!", "STOMP!"), quick cuts, a colour-stripe wipe
between beats, a white flash on every new shot and a jingle on the logo.
Every shot is the actual game, driven frame by frame (tools/make_ad.py has
the driver; this file only adds the shots, the look and the music):

     0  logo burst
     3  the overworld map -- pick a world
     7  run · jump · stomp
    12  every ? block is a quiz
    16  around the world: Hawaii, the North Pole, Greenland, Galápagos ...
    21  secret rooms: fall in, climb the rope out, parachute down from the sky
    27  power-ups
    30  JLPT N5 -> N1, endless questions
    35  your AI buddy (a wrong answer, a live hint)
    41  end card: play free in your browser

Needs ffmpeg and numpy.
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

from kobito import ui  # noqa: E402
from kobito.companion_select_screen import CompanionSelectScreen  # noqa: E402
from kobito.game import Game  # noqa: E402
from kobito.questions import shuffled  # noqa: E402
from kobito.world_select_screen import WorldSelectScreen  # noqa: E402

FPS = ad.FPS
LENGTH = 45 * FPS
W, H = 1920, 1080
RIGHT, UP, JUMP, RUN, FIRE = pygame.K_RIGHT, pygame.K_UP, pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_x
snap, place, reset, bot, quiz_frames = ad.snap, ad.place, ad.reset, ad.bot, ad.quiz_frames


def step(g, n=ad.SIM_STEPS):
    """Advance the game, with the companion's chatter line kept quiet (the ad's own subtitle sits there)."""
    ad.step(g, n)
    g.coach.speech = None


held = ad.held

WHITE, INK = (255, 255, 255), (22, 16, 40)
RED, YELLOW, BLUE, GREEN, PINK = (238, 52, 64), (255, 212, 40), (40, 150, 255), (60, 200, 110), (255, 120, 180)
SKY_TOP, SKY_BOTTOM = (90, 200, 255), (200, 240, 255)


def frame(game=None, word=None, sub=None, color=RED, card=None, top=False):
    """One beat of the spot: a game picture (or a full-screen card), the
    big punch word on its ribbon, and a small line under it. `top` moves the
    words to the top of the screen, for shots whose action is at the bottom."""
    return {"game": game, "word": word, "sub": sub, "color": color, "card": card, "top": top}


# == Shots ==================================================================================

def logo_burst(n=90):
    def draw(s, t):
        _sky(s, t)
        _rays(s, (W // 2, H // 2 - 40), t, YELLOW)
        pop = _overshoot(min(1, t / 0.45))
        _logo(s, (W // 2, H // 2 - 70), 1.25 * pop)
        if t > 0.9:
            _ribbon(s, "A JAPANESE-LEARNING ADVENTURE!", (W // 2, H // 2 + 200), 56, BLUE, min(1, (t - 0.9) / 0.25))
        _sparkles(s, t, 26, seed=1)

    for i in range(n):
        yield frame(card=lambda s, t=i / FPS: draw(s, t))


def world_map(n=120):
    m = WorldSelectScreen("kitsune")
    towns = ["tokyo", "kyoto", "okinawa"]            # walk a little tour along the roads
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
        m._follow(dt)
        m.mascot.update(dt, m.moving)
        m._draw()
        word = "PICK A WORLD!" if i < 70 else "23 WORLDS!"
        yield frame(m.screen.copy(), word, "Walk the big map · every town is a new stage", BLUE)


def run_jump_stomp(g, n=150):
    reset(g, g.surface)
    place(g, 64)
    held.update({RIGHT, RUN})
    words = [("RUN!", RED), ("JUMP!", BLUE), ("STOMP!", GREEN)]
    for i in range(n):
        bot(g)
        step(g)
        word, color = words[min(2, i // 50)]
        yield frame(snap(g), word, "Tokyo, Kyoto, Okinawa, Hokkaido and more", color)
    held.clear()


def quiz_block(g):
    s = g.surface
    block = min((b for b in s.question_blocks if b.rect.x > g.player.rect.x + 60), key=lambda b: b.rect.x)
    question = shuffled(g.question_bank.questions[0], random.Random(3))       # 犬 (いぬ)
    reset(g)
    place(g, block.rect.centerx - 70)
    caps = dict(word="? = QUIZ!", sub="Hit a block · answer in Japanese · power up!", color=YELLOW)
    held.add(RIGHT)
    for _ in range(10):
        if g.player.rect.centerx >= block.rect.centerx - 4:
            held.discard(RIGHT)
        step(g)
        yield frame(snap(g), **caps)
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
        yield frame(snap(g), **caps)
    held.clear()
    block.mark_used()
    g.coach.speech = None
    bg = snap(g)
    for i, f in enumerate(quiz_frames(g, question, block.rect.move(-g.camera_x, 0), bg, 40, n_reveal=22)):
        right = i >= 40
        yield frame(f["game"], "RIGHT!" if right else caps["word"], caps["sub"], GREEN if right else caps["color"])
    block.mark_answered(True)
    g._add_effect_text("+10 XP", (block.rect.centerx, block.rect.top), (150, 255, 170))
    for _ in range(14):
        step(g)
        yield frame(snap(g), "RIGHT!", "+10 XP · your Japanese levels up as you play", GREEN)
    g._check_question_blocks = real_check


def around_the_world(per=24):
    stops = [("hawaii", "HAWAII!", PINK), ("north_pole", "NORTH POLE!", BLUE), ("greenland", "GREENLAND!", GREEN),
             ("galapagos", "GALÁPAGOS!", YELLOW), ("london", "LONDON!", RED), ("kyoto", "KYOTO!", PINK)]
    for theme, word, color in stops:
        g = Game("kitsune", theme, companion_id="hana", item_box={}, badges=[])
        g._take_hit = lambda *_: None
        reset(g)
        place(g, 400)
        held.update({RIGHT, RUN})
        step(g, 20)
        g.banner = None
        g.coach.speech = None
        for _ in range(per):
            bot(g)
            step(g)
            yield frame(snap(g), word, "Islands, cities, the sky, under the sea ...", color)
        held.clear()


def secret_rooms(g):
    s = g.surface
    # Fall down a hole ...
    pit = s.secret_pits[0]
    reset(g, s)
    place(g, (pit["x0"] + pit["x1"]) // 2, s.ground_y - 40)
    for i in range(62):
        step(g)
        if g.world is not s and g.transition is None:
            held.update({RIGHT, RUN})
            bot(g)
        yield frame(snap(g), "SECRET ROOMS!", "Drop down a hole: subways, sewers, mines ...", PINK)
    held.clear()
    # ... climb the rope back out ...
    room = g.world
    if room.underground:
        reset(g, room)
        place(g, room.goal.rect.centerx, room.ground_y)
        held.add(UP)
        for _ in range(40):
            step(g)
            yield frame(snap(g), "CLIMB OUT!", "のぼる (noboru) = to climb", YELLOW)
        held.clear()
    # ... or float down from a sky room.
    reset(g, s)
    link = next(iter(s.springs)).link
    g._enter_sky(link)
    g._leave_hidden()
    step(g, 70)                       # let the chute drift into view first
    g.banner = None
    for _ in range(50):
        step(g)
        yield frame(snap(g), "PARACHUTE DOWN!", "パラシュート · back from the secret sky", BLUE)


def power_ups(g):
    s = g.surface
    reset(g, s)
    sun = min((c for c in s.collectibles if c.kind == "sunflower"), key=lambda c: c.rect.x)
    stone = min((pl for pl in s.platforms if pl.rect.left <= sun.rect.centerx <= pl.rect.right
                 and pl.rect.top >= sun.rect.bottom - 4), key=lambda pl: pl.rect.top)
    place(g, stone.rect.left + 14, stone.rect.top)
    held.add(RIGHT)
    for i in range(84):
        if g.sun_power:
            held.discard(RIGHT)
            (held.add if i % 10 == 0 else held.discard)(FIRE)
        step(g)
        word = "POWER UP!" if i < 42 else "SUNBALLS!"
        yield frame(snap(g), word, "Onigiri, melon pan, elixirs · every item helps", RED)
    held.clear()


QUIZ_KINDS = [("VOCAB!", "gen_meaning_n4_地震", BLUE), ("KANJI!", "kanji_n2_001", RED),
              ("GRAMMAR!", "grammar_n2_001", GREEN), ("JLPT STYLE!", None, PINK),
              ("READING!", "read_n3_003", YELLOW)]


def learn(g):
    bank = {q["id"]: q for q in g.question_bank.questions}
    jlpt = next((q for q in g.question_bank.questions if q.get("style") == "jlpt" and "ordering" in q["id"]), None)
    reset(g, g.surface)
    place(g, 1500)
    step(g, 4)
    g.coach.speech = None
    bg = snap(g)
    anchor = pygame.Rect(480, 420, 1, 1)
    from kobito.quiz_screen import PHASE_ANSWERING, QuizScreen
    for i, (word, qid, color) in enumerate(QUIZ_KINDS):
        q = jlpt if qid is None else bank.get(qid)
        if q is None:
            continue
        quiz = QuizScreen(g.screen, shuffled(q, random.Random(i)), background=bg, anchor_rect=anchor,
                          hint_service=g.hint_service, points=20)
        for _ in range(18):
            quiz._age += 1 / FPS
            quiz._draw(None, PHASE_ANSWERING)
            yield frame(g.screen.copy(), word, "From your first kana to JLPT N1", color)
    yield from levels_card(60)


def levels_card(n):
    def draw(s, t):
        _sky(s, t)
        _rays(s, (W // 2, H // 2), t, (255, 255, 255))
        levels = ["N5", "N4", "N3", "N2", "N1"]
        colors = [GREEN, BLUE, YELLOW, PINK, RED]
        chip, gap = 240, 40
        x0 = W // 2 - (5 * chip + 4 * gap) // 2
        for i, (lv, col) in enumerate(zip(levels, colors)):
            k = _overshoot(min(1, max(0, (t - i * 0.12) / 0.3)))
            if k <= 0:
                continue
            rect = pygame.Rect(0, 0, round(chip * k), round(chip * k))
            rect.center = (x0 + i * (chip + gap) + chip // 2, H // 2 - 90)
            pygame.draw.rect(s, INK, rect.move(10, 12), border_radius=40)
            pygame.draw.rect(s, col, rect, border_radius=40)
            pygame.draw.rect(s, WHITE, rect, width=8, border_radius=40)
            _outlined(s, lv, rect.center, round(110 * k), WHITE)
        if t > 0.75:
            _ribbon(s, "ENDLESS QUESTIONS!", (W // 2, H // 2 + 170), 84, RED, min(1, (t - 0.75) / 0.2))
        if t > 1.1:
            _outlined(s, "New questions every time you play", (W // 2, H // 2 + 300), 46, WHITE)

    for i in range(n):
        yield frame(card=lambda s, t=i / FPS: draw(s, t))


def ai_buddy(g):
    picker = CompanionSelectScreen()
    for i in range(66):
        index = [0, 2, 4][min(2, i // 22)]
        if index != picker.index:
            picker.index, picker.typed = index, 0.0
        picker.time += 1 / FPS
        picker.typed += 60 / FPS
        picker.backdrop.update(1 / FPS)
        picker._draw()
        yield frame(picker.screen.copy(), "PICK A BUDDY!", "5 friends, each with their own perk", PINK)
    bank = {q["id"]: q for q in g.question_bank.questions}
    q = shuffled(bank["kanji_n5_001"], random.Random(1))
    reset(g, g.surface)
    place(g, 2900)
    step(g, 4)
    g.coach.speech = None
    bg = snap(g)
    hint = ("Ooh, so close! 語 means 'language' and it's read ご -- so think 'Japan' + 'language'. "
            "You've got this!")
    for i, f in enumerate(quiz_frames(g, q, pygame.Rect(480, 430, 1, 1), bg, 24, answer_right=False,
                                      n_reveal=12, hint=hint, n_hint=78)):
        word = "OOPS!" if i < 36 else "AI HINTS!"
        sub = "Stuck? Your buddy explains it" if i < 36 else "Live hints by Claude, Gemini or ChatGPT"
        yield frame(f["game"], word, sub, BLUE if i >= 36 else RED, top=i >= 36)    # the hint panel is at the bottom


def end_card(n):
    def draw(s, t):
        _sky(s, t)
        _rays(s, (W // 2, 330), t, YELLOW)
        pop = _overshoot(min(1, t / 0.4))
        _logo(s, (W // 2, 330), 1.0 * pop)
        if t > 0.5:
            _ribbon(s, "PLAY FREE IN YOUR BROWSER!", (W // 2, 640), 76, RED, min(1, (t - 0.5) / 0.2))
        if t > 1.0:
            _outlined(s, "bonimit.itch.io/kobito", (W // 2, 790), 64, WHITE, font=ui.body_font(64))
        if t > 1.4:
            x = W // 2 - 3 * 300 // 2
            for i, (label, col) in enumerate((("BROWSER", BLUE), ("KEYBOARD", GREEN), ("GAMEPAD", PINK))):
                rect = pygame.Rect(x + i * 300 + 20, 880, 260, 84)
                pygame.draw.rect(s, INK, rect.move(6, 8), border_radius=42)
                pygame.draw.rect(s, col, rect, border_radius=42)
                pygame.draw.rect(s, WHITE, rect, width=5, border_radius=42)
                _outlined(s, label, rect.center, 40, WHITE)
        _sparkles(s, t, 30, seed=7)

    for i in range(n):
        yield frame(card=lambda s, t=i / FPS: draw(s, t))


# == The look ===============================================================================

def _overshoot(k):
    """0 -> 1 with a springy bounce past 1 (the 'pop')."""
    if k >= 1:
        return 1.0
    return 1 + 2.2 * (k - 1) ** 3 + 1.2 * (k - 1) ** 2 * (1 if k > 0.5 else 0) if k > 0 else 0.0


def _sky(s, t):
    for y in range(0, H, 6):
        k = y / H
        col = [round(a + (b - a) * k) for a, b in zip(SKY_TOP, SKY_BOTTOM)]
        pygame.draw.rect(s, col, (0, y, W, 6))
    rng = random.Random(3)
    for _ in range(7):                                   # drifting clouds
        x = (rng.randrange(0, W + 400) + t * rng.uniform(30, 80)) % (W + 400) - 200
        y = rng.randrange(40, H - 200)
        r = rng.randrange(50, 90)
        for dx, dr in ((-r, 0.7), (0, 1.0), (r, 0.75)):
            pygame.draw.circle(s, WHITE, (round(x + dx), y), round(r * dr))


def _rays(s, center, t, color):
    layer = pygame.Surface((W, H), pygame.SRCALPHA)
    n = 16
    for i in range(n):
        a = t * 0.6 + i * 2 * math.pi / n
        b = a + math.pi / n * 0.55
        pts = [center, (center[0] + 2400 * math.cos(a), center[1] + 2400 * math.sin(a)),
               (center[0] + 2400 * math.cos(b), center[1] + 2400 * math.sin(b))]
        pygame.draw.polygon(layer, (*color, 70), pts)
    s.blit(layer, (0, 0))


def _sparkles(s, t, count, seed):
    rng = random.Random(seed)
    for _ in range(count):
        x, y = rng.randrange(0, W), rng.randrange(0, H)
        phase, speed = rng.uniform(0, 6.3), rng.uniform(3, 6)
        k = max(0.0, math.sin(t * speed + phase))
        r = round(18 * k)
        if r > 2:
            col = rng.choice([WHITE, YELLOW, PINK])
            pygame.draw.polygon(s, col, [(x, y - r), (x + r // 4, y - r // 4), (x + r, y), (x + r // 4, y + r // 4),
                                         (x, y + r), (x - r // 4, y + r // 4), (x - r, y), (x - r // 4, y - r // 4)])


def _outlined(s, text, center, size, color, outline=INK, font=None):
    font = font or ui.title_font(size)
    o = max(3, size // 14)
    base = font.render(text, True, outline)
    rect = base.get_rect(center=center)
    for dx in range(-o, o + 1, max(1, o // 2)):
        for dy in range(-o, o + 1, max(1, o // 2)):
            if dx * dx + dy * dy <= o * o:
                s.blit(base, rect.move(dx, dy))
    s.blit(base, rect.move(o // 2, o + 2))
    s.blit(font.render(text, True, color), rect)
    return rect


def _logo(s, center, scale):
    if scale <= 0.05:
        return
    size = round(210 * scale)
    letters = "KOBITO"
    colors = [RED, YELLOW, GREEN, BLUE, PINK, RED]
    font = ui.title_font(size)
    widths = [font.size(c)[0] for c in letters]
    x = center[0] - sum(widths) // 2
    t = pygame.time.get_ticks() / 1000
    for i, (c, wdt) in enumerate(zip(letters, widths)):
        bob = round(10 * scale * math.sin(t * 6 + i * 0.9))
        _outlined(s, c, (x + wdt // 2, center[1] + bob), size, colors[i])
        x += wdt
    _outlined(s, "こびと", (center[0], center[1] + round(150 * scale)), round(64 * scale), WHITE,
              font=ui.body_font(round(64 * scale)))


def _ribbon(s, text, center, size, color, k=1.0):
    """A tilted banner with the text on it, sliding in from the left."""
    font = ui.title_font(size)
    tw, th = font.size(text)
    band = pygame.Surface((tw + 140, th + 50), pygame.SRCALPHA)
    pygame.draw.rect(band, INK, band.get_rect().move(0, 0), border_radius=18)
    pygame.draw.rect(band, color, band.get_rect().inflate(-12, -12), border_radius=14)
    _outlined(band, text, (band.get_width() // 2, band.get_height() // 2 - 2), size, WHITE, font=font)
    band = pygame.transform.rotozoom(band, 3, 1.0)
    slide = (1 - min(1, k)) * -W
    s.blit(band, band.get_rect(center=(center[0] + slide, center[1])))


def compose(f, age, t):
    out = pygame.Surface((W, H))
    if f["card"]:
        f["card"](out)
    else:
        out.blit(pygame.transform.scale(f["game"], (W, H)), (0, 0))
        # a soft vignette at the bottom so the words always read
        shade = pygame.Surface((W, 360), pygame.SRCALPHA)
        for y in range(360):
            pygame.draw.line(shade, (10, 6, 24, round(170 * (y / 360) ** 1.6)), (0, y), (W, y))
        out.blit(shade, (0, H - 360))
        strip = 0 if f["top"] else H - 118
        pygame.draw.rect(out, (14, 10, 30), (0, strip, W, 118))            # the subtitle strip
        pygame.draw.rect(out, f["color"], (0, strip if not f["top"] else 112, W, 6))
        if f["word"]:
            # lower right, clear of the hero (the camera keeps them left of centre)
            k = _overshoot(min(1, age / 7))
            img = pygame.Surface((1100, 260), pygame.SRCALPHA)
            _ribbon(img, f["word"], (550, 130), 112, f["color"])
            if k != 1:
                img = pygame.transform.rotozoom(img, 0, max(0.05, k))
            out.blit(img, img.get_rect(center=(1340, 260 if f["top"] else H - 250)))
        if f["sub"] and age > 5:
            _outlined(out, f["sub"], (W // 2, strip + 62), 44, WHITE, font=ui.body_font(44))
    return out


def wipe(out, k, colors=(RED, YELLOW, BLUE)):
    """Diagonal colour stripes sweeping across: k 0 -> 1 covers, 1 -> 2 uncovers."""
    if k <= 0 or k >= 2:
        return
    band = 260
    for i, col in enumerate(colors):
        lag = i * 0.12
        if k < 1:
            edge = (k - lag) / (1 - 0.24)
            left, right = -band * 2, -band * 2 + edge * (W + band * 4)
        else:
            edge = (k - 1 - lag) / (1 - 0.24)
            left, right = -band * 2 + edge * (W + band * 4), W + band * 2
        if right <= left:
            continue
        pts = [(left, 0), (right + band, 0), (right, H), (left - band, H)]
        pygame.draw.polygon(out, col, pts)


# == Soundtrack =============================================================================

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


def soundtrack(duration, words, wipes, path):
    """A bright C-major chiptune at 150 bpm: a bouncy triangle bass, square
    lead, kick/snare/hats; a 'pop' on every new punch word, a swoosh on each
    wipe, a 'ko-bi-to!' jingle on the logo and a big final chord."""
    total = np.zeros(int(RATE * (duration + 1)))

    def add(sig, at):
        i = int(at * RATE)
        if i < len(total):
            total[i:i + len(sig)] += sig[:len(total) - i]

    beat = 60 / 150
    start, end = 2.6, duration - 4.0
    chords = [(48, [60, 64, 67]), (53, [65, 69, 72]), (55, [67, 71, 74]), (48, [64, 67, 72])]   # C F G C
    lead = [72, 76, 79, 76, 77, 76, 74, 72, 74, 76, 79, 81, 79, 77, 76, 74,
            72, 76, 79, 84, 81, 79, 77, 76, 77, 79, 76, 74, 72, 74, 72, -1]
    k, t = 0, start
    while t < end:
        bar = (k // 8) % 4
        root, chord = chords[bar]
        if k % 2 == 0:
            add(_tri(_hz(root if k % 4 == 0 else root + 7), beat * 0.9, 0.32, 3), t)
            add(_sq(55, 0.16, 0.5, 0.35 if k % 4 == 0 else 0.0, 28), t)                 # kick on 1 & 3
        if k % 4 == 2:
            add(_nz(0.16, 0.22, 22, seed=k), t)                                           # snare on 2 & 4
        add(_nz(0.04, 0.05, 80, seed=3), t)                                               # hats
        if k % 2 == 1:
            for n_ in chord:                                                              # off-beat stabs
                add(_sq(_hz(n_), 0.12, 0.5, 0.035, 18), t)
        note = lead[k % len(lead)]
        if note > 0:
            add(_sq(_hz(note), beat * 0.45, 0.25, 0.09, 6), t)
        t += beat / 2
        k += 1
    # Logo jingle at the start and the end: ko-bi-to!
    for at in (0.25, end + 0.45):
        for i, n_ in enumerate((72, 76, 79)):
            add(_sq(_hz(n_), 0.16, 0.5, 0.12, 8), at + i * 0.15)
        for n_ in (72, 76, 79, 84):
            add(_sq(_hz(n_), 1.6, 0.25, 0.06, 1.6), at + 0.45)
    # Pops on the punch words and swooshes on the wipes.
    for at in words:
        add(_sq(_hz(84), 0.06, 0.5, 0.08, 30), at)
        add(_sq(_hz(91), 0.08, 0.5, 0.06, 30), at + 0.05)
    for at in wipes:
        n = int(RATE * 0.4)
        add(np.random.default_rng(5).uniform(-1, 1, n) * np.sin(np.linspace(0, np.pi, n)) * 0.18, at - 0.2)
    # Final chord.
    for n_ in (48, 60, 64, 67, 72, 76):
        add(_sq(_hz(n_), 3.4, 0.5, 0.045, 0.9), end + 0.9)
    total = total[:int(RATE * duration)]
    fade = int(RATE * 0.6)
    total[-fade:] *= np.linspace(1, 0, fade)
    total /= max(1e-6, np.abs(total).max()) / 0.88
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((total * 32767).astype(np.int16).tobytes())


# == Main ===================================================================================

def main():
    out_dir = ad.OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    video_tmp = os.path.join(tmp, "video.mp4")
    enc = ad.encoder(video_tmp, (W, H))

    g = Game("kitsune", "tokyo", companion_id="hana", item_box={}, badges=[])
    g._take_hit = lambda *_: None
    sections = [logo_burst(), world_map(), run_jump_stomp(g), quiz_block(g), around_the_world(),
                secret_rooms(g), power_ups(g), learn(g), ai_buddy(g)]
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

    # Frames go out 6 behind the ones being made, so a wipe can start before the cut it covers.
    word_times, last, age, buffer, i = [], None, 0, [], 0
    source = stream()
    done = False
    while not done or buffer:
        while not done and len(buffer) < 7:
            try:
                buffer.append(next(source))
            except StopIteration:
                done = True
        f = buffer.pop(0)
        ad.frame_no = i
        key = f["word"]
        age = age + 1 if key == last else 0
        if age == 0 and key:
            word_times.append(i / FPS)
        last = key
        out = compose(f, age, i / FPS)
        near_cut = [c for c in cuts[1:] if c - 6 <= i < c + 6]
        for c in near_cut:
            wipe(out, (i - (c - 6)) / 6)
        if f["card"] is None and age < 4 and not near_cut:
            flash = pygame.Surface((W, H))
            flash.fill(WHITE)
            flash.set_alpha(round(150 * (1 - age / 4)))
            out.blit(flash, (0, 0))
        enc.stdin.write(pygame.image.tobytes(out, "RGB"))
        i += 1
    frames = range(i)
    enc.stdin.close()
    enc.wait()
    duration = len(frames) / FPS
    print(f"{len(frames)} frames = {duration:.1f} s; cuts at {', '.join(f'{c / FPS:.1f}' for c in cuts)}")

    audio = os.path.join(tmp, "music.wav")
    soundtrack(duration, word_times, [c / FPS for c in cuts[1:]], audio)
    out = os.path.join(out_dir, "ad45_16x9.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_tmp, "-i", audio, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"{out}: {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

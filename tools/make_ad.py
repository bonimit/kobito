"""A 30-second ad for Kobito, made from the real game.

    python tools/make_ad.py      # writes docs/ad_16x9.mp4 (1920x1080) and docs/ad_9x16.mp4 (1080x1920)

A hook, then three chapters -- HOW TO PLAY, WHAT YOU LEARN, YOUR AI
COMPANION -- and an end card. Every shot is the actual game (gameplay,
quiz boxes, the review, the companion screen), driven frame by frame by
this script, with big captions on top. The 16:9 cut is for YouTube / the
web, the 9:16 cut for TikTok, Reels and Shorts (the game sits in the middle,
captions above and below). The soundtrack -- a short chiptune in a Japanese
pentatonic scale with whooshes on the chapter cuts -- is synthesised here
too, so there are no audio assets to license.

Needs ffmpeg and numpy.
"""

import asyncio
import math
import os
import random
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["KOBITO_SAVE_PATH"] = os.path.join(tempfile.mkdtemp(), "save.json")
os.environ.pop("ANTHROPIC_API_KEY", None)

import numpy as np  # noqa: E402
import pygame  # noqa: E402

FPS = 30
SIM_STEPS = 2           # game updates per video frame (the game runs at 60)
OUT_DIR = os.path.join(ROOT, "docs")


class FakeClock:
    def tick(self, framerate=0):
        return 1000.0 / 60

    def get_fps(self):
        return 60.0


frame_no = 0
held = set()


class Keys:
    def __getitem__(self, key):
        return key in held


pygame.time.Clock = FakeClock
pygame.time.get_ticks = lambda: int(frame_no * 1000 / FPS)
pygame.key.get_pressed = lambda: Keys()
pygame.init()
pygame.display.set_mode((960, 540))

from kobito import ui  # noqa: E402
from kobito.companion_select_screen import CompanionSelectScreen  # noqa: E402
from kobito.entities.enemy import Enemy  # noqa: E402
from kobito.game import Game  # noqa: E402
from kobito.items import ITEMS, get_item  # noqa: E402
from kobito.questions import shuffled  # noqa: E402
from kobito.quiz_screen import PHASE_ANSWERING, PHASE_HINT, PHASE_REVEAL, QuizScreen  # noqa: E402
from kobito import stage_test  # noqa: E402
from kobito.stage_end_screens import ReviewScreen, TileScreen  # noqa: E402

RIGHT, JUMP, RUN, FIRE = pygame.K_RIGHT, pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_x
GOLD, CREAM, INK = (255, 206, 84), (255, 246, 226), (16, 11, 24)
KANA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん漢字日本語学"


# == Shot helpers ====================================================================

def step(g, n=SIM_STEPS):
    for _ in range(n):
        asyncio.run(g._update(1 / 60))


def snap(g):
    g._draw()
    return g.screen.copy()


def place(g, x, bottom=None):
    g._place_player(x, g.world.ground_y if bottom is None else bottom)


def reset(g, world=None):
    """A clean cut: no fade, banner, chatter or floating text left over
    from the previous shot."""
    g.transition = None
    if world is not None and g.world is not world:
        g._switch_world(world)
    g.banner = None
    g.coach.speech = None
    g.effects = []
    g.invulnerable_timer = 0.0
    held.clear()


def bot(g):
    """One frame of the auto-runner: hop onto enemies, over pits and walls."""
    p = g.player
    ahead = any(40 < e.rect.centerx - p.rect.centerx < 120 and abs(e.rect.bottom - p.rect.bottom) < 24
                for e in g.enemies if type(e) is Enemy)
    segs = g.world.ground_segments_px
    gap = any(10 < end - p.rect.centerx < 60 for (_, end), (start, _) in zip(segs, segs[1:]) if start > end)
    if p.on_ground and (ahead or gap or getattr(g, "_stuck", 0) > 6):
        held.add(JUMP)
    elif JUMP in held and not p.on_ground and p.velocity_y > -150:
        held.discard(JUMP)
    g._stuck = getattr(g, "_stuck", 0) + 1 if abs(p.rect.x - getattr(g, "_last_x", -1)) < 1 and p.on_ground else 0
    g._last_x = p.rect.x


def frame(game=None, headline=None, sub=None, tag=None, card=None, focus="crop", cx=480):
    """One video frame. `focus`: in the 9:16 cut, "crop" zooms into a
    640-wide slice of the game centred on `cx` (the camera keeps the hero
    in the middle); "wide" shows the whole screen (menus and text laid out
    across the full width)."""
    return {"game": game, "headline": headline, "sub": sub, "tag": tag, "card": card, "focus": focus, "cx": cx}


def quiz_frames(g, question, anchor, bg, n_answer, answer_right=True, n_reveal=24, hint=None, n_hint=0,
                focus="crop", hint_sub=None, **caps):
    """Frames of a quiz box: the highlight walks to an answer, then the
    reveal (and optionally the companion's hint). The 9:16 crop follows
    the box."""
    quiz = QuizScreen(g.screen, question, background=bg, anchor_rect=anchor, hint_service=g.hint_service,
                      points=10, penalty=5)
    place_box = quiz._position_box
    where = {"cx": 480}

    def remember(*args, **kwargs):
        box, side = place_box(*args, **kwargs)
        where["cx"] = box.centerx
        return box, side
    quiz._position_box = remember
    caps = dict(caps, focus=focus)
    target = question["answer"] if answer_right else (question["answer"] + 1) % len(question["choices"])
    for i in range(n_answer):
        quiz._age += 1 / FPS
        if i > 10 and i % 7 == 0 and quiz.cursor != target:
            quiz.move_cursor(1)
        quiz._draw(None, PHASE_ANSWERING)
        yield frame(g.screen.copy(), cx=where["cx"], **caps)
    for _ in range(n_reveal):
        quiz._age += 1 / FPS
        quiz._draw(target, PHASE_REVEAL)
        yield frame(g.screen.copy(), cx=where["cx"], **caps)
    for _ in range(n_hint):
        quiz._age += 1 / FPS
        quiz._draw(target, PHASE_HINT, hint_text=hint, companion_state="talking")
        yield frame(g.screen.copy(), cx=where["cx"], **dict(caps, sub=hint_sub or caps.get("sub")))


# == The shots ========================================================================

def hook(n=84):
    rng = random.Random(4)
    drops = [[rng.randrange(0, 1000), rng.uniform(-1.0, 0.0), rng.uniform(0.35, 0.9), rng.choice(KANA)]
             for _ in range(70)]

    def draw(surface, t):
        w, h = surface.get_size()
        s = w / 1920 if w > h else w / 1080
        surface.fill((10, 7, 20))
        font = ui.body_font(round(34 * s))
        for d in drops:
            x = d[0] / 1000 * w
            y = ((d[1] + t * d[2]) % 1.2) * h
            img = font.render(d[3], True, (90, 70, 140))
            img.set_alpha(110)
            surface.blit(img, (x, y))
        cx, cy = w // 2, h // 2
        if t > 0.15:
            a = min(1, (t - 0.15) / 0.3)
            img = ui.title_font(round(64 * s)).render("Can a video game", True, CREAM)
            img.set_alpha(round(255 * a))
            surface.blit(img, img.get_rect(center=(cx, cy - round(110 * s))))
        if t > 0.8:
            img = ui.title_font(round(64 * s)).render("teach you", True, CREAM)
            surface.blit(img, img.get_rect(center=(cx, cy - round(30 * s))))
        if t > 1.25:
            pop = 1 + 0.35 * max(0.0, 1 - (t - 1.25) / 0.25)
            size = round(118 * s * pop)
            for dx, dy, col in ((round(6 * s), round(6 * s), (120, 40, 40)), (0, 0, GOLD)):
                img = ui.title_font(size).render("JAPANESE?", True, col)
                surface.blit(img, img.get_rect(center=(cx + dx, cy + round(90 * s) + dy)))
        if t > 2.0:
            jp = ui.body_font(round(40 * s)).render("ゲームで にほんごを まなぼう", True, (190, 170, 240))
            surface.blit(jp, jp.get_rect(center=(cx, cy + round(210 * s))))

    for i in range(n):
        yield frame(card=lambda surface, t=i / FPS: draw(surface, t))


def chapter(number, title, jp, n=20):
    def draw(surface, t):
        w, h = surface.get_size()
        s = w / 1920 if w > h else w / 1080
        surface.fill((14, 10, 26))
        slide = (1 - min(1, t / 0.18)) * w * 0.4
        cx, cy = w // 2, h // 2
        pygame.draw.circle(surface, GOLD, (round(cx - slide), cy - round(120 * s)), round(66 * s))
        num = ui.title_font(round(84 * s)).render(str(number), True, INK)
        surface.blit(num, num.get_rect(center=(round(cx - slide), cy - round(118 * s))))
        img = ui.title_font(round(96 * s)).render(title, True, CREAM)
        surface.blit(img, img.get_rect(center=(round(cx + slide), cy + round(20 * s))))
        sub = ui.body_font(round(44 * s)).render(jp, True, GOLD)
        surface.blit(sub, sub.get_rect(center=(round(cx + slide), cy + round(110 * s))))

    for i in range(n):
        yield frame(card=lambda surface, t=i / FPS: draw(surface, t))


def how_to_play(g):
    tag = "HOW TO PLAY"
    # Run, jump, stomp.
    place(g, 64)
    held.update({RIGHT, RUN})
    for _ in range(54):
        bot(g)
        step(g)
        yield frame(snap(g), "RUN · JUMP · STOMP", "15 worlds, from Tokyo to the sky", tag)
    held.clear()

    # A quiz block.
    s = g.surface
    block = min((b for b in s.question_blocks if b.rect.x > g.player.rect.x + 60), key=lambda b: b.rect.x)
    question = shuffled(g.question_bank.questions[0], random.Random(3))      # 犬 (inu)
    reset(g)
    place(g, block.rect.centerx - 70)
    caps = dict(headline="EVERY ? BLOCK IS A QUIZ", sub="Answer in Japanese to power up", tag=tag)
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
    yield from quiz_frames(g, question, block.rect.move(-g.camera_x, 0), bg, 46, n_reveal=26, **caps)
    block.mark_answered(True)
    g.score += 10
    g._add_xp(10)
    g._add_effect_text("+10 XP", (block.rect.centerx, block.rect.top), (150, 255, 170))
    for _ in range(12):
        step(g)
        yield frame(snap(g), **caps)
    g._check_question_blocks = real_check

    # Secret stages.
    pit = s.secret_pits[0]
    reset(g)
    place(g, (pit["x0"] + pit["x1"]) // 2, s.ground_y - 40)     # already dropping into the pit
    caps = dict(headline="FIND SECRET STAGES", sub="Subways, sewers, mines… even the sky", tag=tag)
    for i in range(60):
        step(g)
        if g.world is not s and g.transition is None:
            held.update({RIGHT, RUN})
            bot(g)
        yield frame(snap(g), **caps)
    held.clear()

    # Power-ups.
    reset(g, s)
    sun = min((c for c in s.collectibles if c.kind == "sunflower"), key=lambda c: c.rect.x)
    stone = min((pl for pl in s.platforms if pl.rect.left <= sun.rect.centerx <= pl.rect.right
                 and pl.rect.top >= sun.rect.bottom - 4), key=lambda pl: pl.rect.top)   # the stone, not the ground
    place(g, stone.rect.left + 14, stone.rect.top)
    held.add(RIGHT)
    caps = dict(headline="GRAB POWER-UPS", sub="Sunflower = throw sunballs!", tag=tag)
    for i in range(45):
        if g.sun_power:
            held.discard(RIGHT)
            if i % 10 == 0:
                held.add(FIRE)
            else:
                held.discard(FIRE)
        step(g)
        yield frame(snap(g), **caps)
    held.clear()


TYPES = [
    ("VOCABULARY", "gen_meaning_n4_地震"),
    ("KANJI", "kanji_n2_001"),
    ("GRAMMAR", "grammar_n2_001"),
    ("VERBS", "gen_verb_n4_払う_potential"),
    ("EXPRESSIONS", "expr_n2_001"),
    ("LOANWORDS", "loan_n2_004"),
    ("READING", "read_n3_003"),
]


def what_you_learn(g):
    tag = "WHAT YOU LEARN"
    bank = {q["id"]: q for q in g.question_bank.questions}
    reset(g, g.surface)
    place(g, 1500)
    step(g, 4)
    g.coach.speech = None
    bg = snap(g)
    anchor = pygame.Rect(480, 420, 1, 1)
    for i, (kind, qid) in enumerate(TYPES):
        q = shuffled(bank[qid], random.Random(i))
        quiz = QuizScreen(g.screen, q, background=bg, anchor_rect=anchor, hint_service=g.hint_service, points=20)
        for k in range(13):
            quiz._draw(None, PHASE_ANSWERING)
            yield frame(g.screen.copy(), kind, f"7 kinds of questions  ·  {i + 1}/7", tag)

    # Scale.
    yield from stat_card(36)

    # Review + test.
    entries = []
    rng = random.Random(5)
    for qid, result in (("vocab_n5_001", "right"), ("expr_n5_005", "right"), ("kanji_n5_001", "wrong"),
                        ("loan_n5_001", "right"), ("read_n5_003", "right"), ("gen_meaning_n5_天気", "right")):
        q = shuffled(bank[qid], rng)
        entries.append({"question": q, "chosen": q["answer"] if result == "right" else (q["answer"] + 1) % 4,
                        "result": result})
    items = [get_item(i) for i in ("inari", "onigiri", "melon_pan", "green_tea")]
    words = stage_test.learned_words(entries, items, [])
    review = ReviewScreen(g.screen, bg, 1, entries, words, 12)
    for i in range(40):
        review.scroll = min(review.max_scroll, round(review.max_scroll * max(0, i - 8) / 26))
        review._draw()
        yield frame(g.screen.copy(), "REVIEW EVERY WORD", "Each stage ends with a recap…", tag, focus="wide")
    extra = [stage_test.word_from_item(i) for i in ITEMS.values()]
    test = stage_test.build_test(entries, words, g.question_bank.questions, "N5", random.Random(2), extra_words=extra)
    reading = next(t for t in test if t["kind"] == "reading")
    tile = TileScreen(g.screen, bg, reading, 3, 12)
    for i in range(36):
        if i in (10, 18):
            ch = reading["answer"][len(tile.placed)]
            tile._place(next(j for j, t in enumerate(reading["tiles"]) if t == ch and j not in tile.placed))
        if tile.result is not None:
            tile.result_time += 1 / FPS
        tile._draw()
        yield frame(g.screen.copy(), "…AND A STAGE TEST", "Read & write with kana tiles", tag, focus="wide")


def ai_companion(g):
    tag = "YOUR AI COMPANION"
    picker = CompanionSelectScreen()
    for i in range(72):
        index = [0, 2, 4][min(2, i // 24)]
        if index != picker.index:
            picker.index, picker.typed = index, 0.0
        picker.time += 1 / FPS
        picker.typed += 60 / FPS
        picker.backdrop.update(1 / FPS)
        picker._draw()
        yield frame(picker.screen.copy(), "PICK AN AI COMPANION", "5 personalities, each with a perk", tag,
                    focus="wide")

    # A wrong answer, and the companion's hint.
    bank = {q["id"]: q for q in g.question_bank.questions}
    q = shuffled(bank["kanji_n5_001"], random.Random(1))
    reset(g, g.surface)
    place(g, 2900)
    step(g, 4)
    g.coach.speech = None
    bg = snap(g)
    hint = ("Ooh, so close! 語 means 'language' and it's read ご -- so think 'Japan' + 'language'. "
            "You've got this!")
    yield from quiz_frames(g, q, pygame.Rect(480, 430, 1, 1), bg, 26, answer_right=False, n_reveal=14,
                           hint=hint, n_hint=44, focus="wide", headline="STUCK? IT HELPS YOU",
                           hint_sub="Hana: “So close! 語 = ‘language’, read ご”",
                           sub="Hints in its own voice, written live by Claude", tag=tag)

    # Adaptive difficulty.
    yield from adapt_card(48)


def _scale(surface):
    w, h = surface.get_size()
    return w / 1920 if w > h else w / 1080


def stat_card(n):
    """1,400+ counting up, the JLPT levels lighting up, the 7 kinds popping in."""
    levels = ["N5", "N4", "N3", "N2", "N1"]
    kinds = [k for k, _ in TYPES]

    def draw(surface, t):
        w, h = surface.get_size()
        s_ = _scale(surface)
        surface.fill((14, 10, 26))
        cx = w // 2
        cy = h // 2 - round(150 * s_) if h > w else h // 2 - round(60 * s_)
        count = min(1408, int(1408 * min(1, t / 0.7) ** 0.6))
        num = f"{count:,}" + ("+" if count >= 1400 else "")
        for dx, col in ((round(8 * s_), (90, 40, 30)), (0, GOLD)):
            img = ui.title_font(round(200 * s_)).render(num, True, col)
            surface.blit(img, img.get_rect(center=(cx + dx, cy - round(150 * s_) + dx)))
        sub = ui.title_font(round(60 * s_)).render("QUESTIONS", True, CREAM)
        surface.blit(sub, sub.get_rect(center=(cx, cy - round(10 * s_))))
        # JLPT N5 -> N1 chips
        chip_w, gap = round(150 * s_), round(22 * s_)
        x0 = cx - (5 * chip_w + 4 * gap) // 2
        for i, lv in enumerate(levels):
            lit = t > 0.35 + i * 0.1
            rect = pygame.Rect(x0 + i * (chip_w + gap), cy + round(70 * s_), chip_w, round(76 * s_))
            pygame.draw.rect(surface, GOLD if lit else (50, 42, 72), rect, border_radius=round(16 * s_))
            img = ui.title_font(round(48 * s_)).render(lv, True, INK if lit else (120, 110, 150))
            surface.blit(img, img.get_rect(center=rect.center))
        # the 7 kinds
        font = ui.label_font(round(30 * s_))
        rows = [kinds[:4], kinds[4:]]
        y = cy + round(200 * s_)
        k = 0
        for row in rows:
            widths = [font.size(word)[0] + round(36 * s_) for word in row]
            x = cx - (sum(widths) + round(16 * s_) * (len(row) - 1)) // 2
            for word, wd in zip(row, widths):
                if t > 0.6 + k * 0.07:
                    rect = pygame.Rect(x, y, wd, round(52 * s_))
                    pygame.draw.rect(surface, (60, 48, 92), rect, border_radius=rect.height // 2)
                    pygame.draw.rect(surface, (150, 120, 220), rect, width=2, border_radius=rect.height // 2)
                    img = font.render(word, True, CREAM)
                    surface.blit(img, img.get_rect(center=rect.center))
                x += wd + round(16 * s_)
                k += 1
            y += round(68 * s_)

    for i in range(n):
        yield frame(card=lambda surface, t=i / FPS: draw(surface, t))


def adapt_card(n):
    """Hana next to a difficulty meter: right answers push the marker up a
    level, a miss eases it back."""
    from kobito.companion_art import draw_companion
    marks = [(0.15, True), (0.35, True), (0.55, True), (0.75, True), (0.95, False), (1.15, True)]
    # marker position (0 = N5 .. 4 = N1) after each answer
    path = [0.0, 0.5, 1.0, 1.5, 2.0, 1.6, 2.0]

    def level_at(t):
        done = sum(1 for at, _ in marks if t >= at)
        a, b = path[max(0, done - 1)] if done else 0.0, path[done]
        start = marks[done - 1][0] if done else 0.0
        return a + (b - a) * min(1, (t - start) / 0.15) if done else 0.0

    def draw(surface, t):
        w, h = surface.get_size()
        s_ = _scale(surface)
        surface.fill((14, 10, 26))
        cx, cy = w // 2, h // 2
        title = ui.title_font(round(76 * s_)).render("IT ADAPTS TO YOU", True, CREAM)
        surface.blit(title, title.get_rect(center=(cx, cy - round(250 * s_))))
        sub = ui.body_font(round(38 * s_)).render("Harder when you're on a roll, easier when you're stuck", True, GOLD)
        if sub.get_width() > w - 60:
            sub = pygame.transform.smoothscale(sub, (w - 60, round(sub.get_height() * (w - 60) / sub.get_width())))
        surface.blit(sub, sub.get_rect(center=(cx, cy - round(170 * s_))))
        # the meter
        meter = pygame.Rect(0, 0, round(900 * s_), round(26 * s_))
        meter.center = (cx, cy + round(30 * s_))
        pygame.draw.rect(surface, (50, 42, 72), meter, border_radius=meter.height // 2)
        lv = level_at(t)
        fill = meter.copy()
        fill.width = round(meter.width * (0.1 + 0.8 * lv / 4))
        pygame.draw.rect(surface, GOLD, fill, border_radius=meter.height // 2)
        for i, name in enumerate(["N5", "N4", "N3", "N2", "N1"]):
            x = meter.x + round(meter.width * (0.1 + 0.8 * i / 4))
            img = ui.label_font(round(32 * s_)).render(name, True, CREAM if i <= lv + 0.01 else (120, 110, 150))
            surface.blit(img, img.get_rect(center=(x, meter.bottom + round(36 * s_))))
        marker_x = meter.x + round(meter.width * (0.1 + 0.8 * lv / 4))
        draw_companion(surface, "hana", marker_x, meter.y - round(70 * s_), round(110 * s_),
                       expression="happy" if t < 0.95 or t > 1.2 else "sympathetic")
        # the answers so far
        size = round(46 * s_)
        x = cx - (len(marks) * (size + round(18 * s_))) // 2
        for at, right in marks:
            if t >= at:
                box = pygame.Rect(x, cy + round(140 * s_), size, size)
                pygame.draw.rect(surface, (60, 150, 90) if right else (190, 70, 80), box, border_radius=round(10 * s_))
                c = box.center
                if right:
                    pygame.draw.lines(surface, CREAM, False, [(c[0] - size // 4, c[1]), (c[0] - size // 12, c[1] + size // 5),
                                                             (c[0] + size // 4, c[1] - size // 5)], max(3, size // 10))
                else:
                    for d in (-1, 1):
                        pygame.draw.line(surface, CREAM, (c[0] - size // 5, c[1] - d * size // 5),
                                         (c[0] + size // 5, c[1] + d * size // 5), max(3, size // 10))
            x += size + round(18 * s_)

    for i in range(n):
        yield frame(card=lambda surface, t=i / FPS: draw(surface, t), tag="YOUR AI COMPANION")


def end_card(n=84):
    def draw(surface, t):
        w, h = surface.get_size()
        s = w / 1920 if w > h else w / 1080
        surface.fill((14, 10, 26))
        cx, cy = w // 2, h // 2 - round(40 * s)
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        for r, a in ((round(520 * s), 30), (round(380 * s), 40), (round(250 * s), 50)):
            pygame.draw.circle(glow, (255, 200, 90, a), (cx, cy), r)
        surface.blit(glow, (0, 0))
        pop = 1 + 0.25 * max(0.0, 1 - t / 0.25)
        for dx, col in ((round(8 * s), (90, 40, 30)), (0, GOLD)):
            img = ui.title_font(round(170 * s * pop)).render("KOBITO", True, col)
            surface.blit(img, img.get_rect(center=(cx + dx, cy - round(60 * s) + dx)))
        jp = ui.body_font(round(48 * s)).render("こびと", True, CREAM)
        surface.blit(jp, jp.get_rect(center=(cx, cy + round(60 * s))))
        if t > 0.4:
            line = ui.title_font(round(56 * s)).render("Learn Japanese while you play", True, CREAM)
            surface.blit(line, line.get_rect(center=(cx, cy + round(150 * s))))
        if t > 0.9:
            small = ui.body_font(round(34 * s)).render("JLPT N5 → N1  ·  AI companion  ·  desktop & browser",
                                                       True, (190, 170, 240))
            surface.blit(small, small.get_rect(center=(cx, cy + round(230 * s))))

    for i in range(n):
        yield frame(card=lambda surface, t=i / FPS: draw(surface, t))


# == Layout: the two aspect ratios ========================================================

def _caption_alpha(age):
    return min(1.0, age / 5)


def render_wide(f, age):
    out = pygame.Surface((1920, 1080))
    if f["card"]:
        f["card"](out)
        return out
    out.blit(pygame.transform.scale(f["game"], (1920, 1080)), (0, 0))
    band = pygame.Surface((1920, 300), pygame.SRCALPHA)
    for y in range(300):     # solid behind the caption (hides the HUD), then fading out
        alpha = 240 if y < 200 else round(240 * (1 - (y - 200) / 100))
        pygame.draw.line(band, (8, 5, 16, alpha), (0, y), (1920, y))
    out.blit(band, (0, 0))
    a = _caption_alpha(age)
    if f["tag"]:
        _pill(out, f["tag"], (60, 44), ui.label_font(30))
    if f["headline"]:
        _headline(out, f["headline"], (960, 118), ui.title_font(80), a, pop=age)
    if f["sub"]:
        img = ui.body_font(40).render(f["sub"], True, GOLD)
        img.set_alpha(round(255 * a))
        out.blit(img, img.get_rect(center=(960, 198)))
    return out


def render_tall(f, age, t):
    out = pygame.Surface((1080, 1920))
    if f["card"]:
        f["card"](out)
        return out
    out.fill((14, 10, 26))
    rng = random.Random(9)
    font = ui.body_font(40)
    for k in range(40):   # a faint drift of kana behind everything
        x = rng.randrange(0, 1080)
        y = (rng.randrange(0, 1920) + t * rng.uniform(20, 60)) % 1920
        img = font.render(rng.choice(KANA), True, (60, 46, 96))
        out.blit(img, (x, y))
    a = _caption_alpha(age)
    if f["focus"] == "wide":
        game = pygame.transform.smoothscale(f["game"], (1080, 608))
        top = 640
    else:
        # The middle 640x540 of the game, zoomed to fill the width.
        left = max(0, min(320, f["cx"] - 320))
        game = pygame.transform.scale(f["game"].subsurface((left, 0, 640, 540)), (1080, 911))
        top = 470
    if f["tag"]:
        _pill(out, f["tag"], None, ui.label_font(40), center=(540, 150 if top < 600 else 230))
    if f["headline"]:
        _headline(out, f["headline"], (540, 310 if top < 600 else 420), ui.title_font(84), a, pop=age, width=1000)
    out.blit(game, (0, top))
    pygame.draw.line(out, GOLD, (0, top - 2), (1080, top - 2), 4)
    pygame.draw.line(out, GOLD, (0, top + game.get_height()), (1080, top + game.get_height()), 4)
    if f["sub"]:
        from kobito.setup_ui import wrap
        y = top + game.get_height() + 90
        for line in wrap(f["sub"], ui.body_font(54), 960)[:2]:
            img = ui.body_font(54).render(line, True, GOLD)
            img.set_alpha(round(255 * a))
            out.blit(img, img.get_rect(center=(540, y)))
            y += 74
    logo = ui.title_font(64).render("KOBITO", True, GOLD)
    out.blit(logo, logo.get_rect(center=(540, 1740)))
    jp = ui.body_font(36).render("こびと · Learn Japanese while you play", True, CREAM)
    out.blit(jp, jp.get_rect(center=(540, 1810)))
    return out


def _pill(surface, text, topleft, font, center=None):
    label = font.render(text, True, INK)
    box = label.get_rect().inflate(40, 18)
    if center:
        box.center = center
    else:
        box.topleft = topleft
    pygame.draw.rect(surface, GOLD, box, border_radius=box.height // 2)
    surface.blit(label, label.get_rect(center=box.center))


def _headline(surface, text, center, font, alpha, pop=99, width=None):
    from kobito.setup_ui import wrap
    lines = wrap(text, font, width) if width else [text]
    scale = 1 + 0.18 * max(0.0, 1 - pop / 5)
    y = center[1] - (len(lines) - 1) * font.get_height() // 2
    for line in lines:
        for dx, col in ((6, INK), (-3, INK), (0, CREAM)):
            img = font.render(line, True, col)
            if scale != 1:
                img = pygame.transform.scale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
            img.set_alpha(round(255 * alpha))
            surface.blit(img, img.get_rect(center=(center[0] + dx, y + abs(dx))))
        y += font.get_height()


# == Soundtrack ============================================================================

RATE = 44100


def _tone(freq, dur, duty=0.25, vol=0.2, decay=6.0):
    t = np.arange(int(RATE * dur)) / RATE
    wave_ = np.where((t * freq) % 1.0 < duty, 1.0, -1.0)
    env = np.exp(-decay * t) * np.minimum(1, t * 200)
    return vol * wave_ * env


def _noise(dur, vol, decay):
    t = np.arange(int(RATE * dur)) / RATE
    return vol * np.random.default_rng(1).uniform(-1, 1, len(t)) * np.exp(-decay * t)


def _note(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def soundtrack(duration, cut_times, path):
    """Hook: a low drone and a rising in-scale arpeggio. Then 120 bpm:
    kick, hats, a bass line and a yo-scale melody. Whooshes on chapter cuts,
    a final chord on the end card."""
    total = np.zeros(int(RATE * duration) + RATE)

    def add(sig, at):
        i = int(at * RATE)
        total[i:i + len(sig)] += sig[:len(total) - i]

    hook_end, end_start = cut_times[0], cut_times[-1]
    # Hook: in scale (D Eb G A Bb) rising, over a drone.
    insen = [62, 63, 67, 69, 70, 74, 75, 79]
    for k in range(int(hook_end / 0.25)):
        add(_tone(_note(insen[k % len(insen)] + 12 * (k // 8)), 0.22, 0.5, 0.10, 8), k * 0.25)
    add(_tone(_note(38), hook_end, 0.5, 0.08, 0.3), 0)
    # Main groove (yo scale: D E G A B).
    beat = 0.5
    yo = [74, 76, 79, 81, 83, 86]
    melody = [0, 2, 3, 2, 4, 3, 2, 1, 0, 2, 3, 5, 4, 3, 2, 3]
    bass = [50, 50, 55, 57]
    t = hook_end
    k = 0
    while t < end_start - 0.01:
        if k % 2 == 0:
            add(_tone(55, 0.18, 0.5, 0.35, 25), t)                   # kick
            add(_tone(_note(bass[(k // 8) % 4]), 0.45, 0.5, 0.12, 4), t)
        add(_noise(0.05, 0.05 if k % 2 else 0.03, 60), t)            # hat
        add(_tone(_note(yo[melody[k % 16]]), 0.22, 0.25, 0.09, 7), t)
        t += beat / 2
        k += 1
    # Whooshes on cuts.
    for c in cut_times[1:-1]:
        n = int(RATE * 0.35)
        sweep = np.random.default_rng(2).uniform(-1, 1, n) * np.linspace(0, 1, n) ** 2 * 0.25
        add(sweep, max(0, c - 0.3))
        add(_tone(_note(86), 0.12, 0.5, 0.10, 20), c)
    # End: a chord and sparkles.
    for n_ in (62, 66, 69, 74):
        add(_tone(_note(n_), 2.5, 0.5, 0.07, 1.2), end_start)
    for k, n_ in enumerate([86, 88, 91, 93, 98]):
        add(_tone(_note(n_), 0.25, 0.25, 0.06, 10), end_start + 0.1 * k)
    total = total[:int(RATE * duration)]
    fade = int(RATE * 0.8)
    total[-fade:] *= np.linspace(1, 0, fade)
    total /= max(1e-6, np.abs(total).max()) / 0.85
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((total * 32767).astype(np.int16).tobytes())


# == Main ==================================================================================

def encoder(path, size):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
         path], stdin=subprocess.PIPE)


def main():
    global frame_no
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = tempfile.mkdtemp()
    wide_tmp, tall_tmp = os.path.join(tmp, "wide.mp4"), os.path.join(tmp, "tall.mp4")
    wide, tall = encoder(wide_tmp, (1920, 1080)), encoder(tall_tmp, (1080, 1920))

    g = Game("kitsune", "tokyo", companion_id="hana", item_box={}, badges=[])
    g._take_hit = lambda *_: None
    sections = [hook(), chapter(1, "HOW TO PLAY", "あそびかた"), how_to_play(g),
                chapter(2, "WHAT YOU LEARN", "まなべること"), what_you_learn(g),
                chapter(3, "YOUR AI COMPANION", "AIの なかま"), ai_companion(g), end_card()]
    cuts = []
    last_caption, caption_age = None, 0
    for section in sections:
        cuts.append(frame_no / FPS)
        for f in section:
            key = (f["headline"], f["sub"])
            caption_age = caption_age + 1 if key == last_caption else 0
            last_caption = key
            wide.stdin.write(pygame.image.tobytes(render_wide(f, caption_age), "RGB"))
            tall.stdin.write(pygame.image.tobytes(render_tall(f, caption_age, frame_no / FPS), "RGB"))
            frame_no += 1
    for enc in (wide, tall):
        enc.stdin.close()
        enc.wait()
    duration = frame_no / FPS
    print(f"{frame_no} frames = {duration:.1f} s; chapters at {', '.join(f'{c:.1f}' for c in cuts)}")

    audio = os.path.join(tmp, "music.wav")
    soundtrack(duration, cuts, audio)
    for video, name in ((wide_tmp, "ad_16x9.mp4"), (tall_tmp, "ad_9x16.mp4")):
        out = os.path.join(OUT_DIR, name)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio, "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
        print(f"{out}: {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

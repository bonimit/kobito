"""Records the game playing itself -- a short demo for the README cover.

    python tools/record_cover.py            # writes docs/cover.mp4 and docs/cover.gif

Runs the real game headless with a scripted "director" at the controls:
it holds keys, presses buttons and answers questions, scene by scene, and
draws a caption saying what each scene shows. Every frame the game draws
(gameplay, quiz box, review, Stage Test, lucky draw) is piped to ffmpeg.

The clock is simulated (a steady 60 fps, no sleeping), so recording is
fast and the result is the same every time. Needs ffmpeg on the PATH.
"""

import asyncio
import math
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["KOBITO_SAVE_PATH"] = os.path.join(tempfile.mkdtemp(), "save.json")   # never touch a real save
os.environ.pop("ANTHROPIC_API_KEY", None)   # canned companion lines, no network

import pygame  # noqa: E402

SIM_FPS = 60          # the game runs at this rate...
OUT_FPS = 30          # ...and every other frame is recorded
W, H = 960, 540
OUT_DIR = os.path.join(ROOT, "docs")


# -- A simulated clock and keyboard ------------------------------------------------

class FakeClock:
    def tick(self, framerate=0):
        return 1000.0 / SIM_FPS

    def get_fps(self):
        return float(SIM_FPS)


frame_no = 0
held = set()


class Keys:
    def __getitem__(self, key):
        return key in held


pygame.time.Clock = FakeClock
pygame.time.get_ticks = lambda: int(frame_no * 1000 / SIM_FPS)
pygame.key.get_pressed = lambda: Keys()

pygame.init()
pygame.display.set_mode((W, H))

from kobito import game as game_mod, ui  # noqa: E402
from kobito import stage_end_screens, quiz_screen  # noqa: E402
from kobito.entities.enemy import Enemy  # noqa: E402
from kobito.questions import shuffled  # noqa: E402

RIGHT, LEFT, JUMP, RUN, FIRE = pygame.K_RIGHT, pygame.K_LEFT, pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_x


def press(key):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode="", scancode=0))


# Remember the screens the game opens, so the director can play them.
current = {"quiz": None, "tile": None, "draw": None}


def _track(cls, name):
    original = cls.__init__

    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        current[name] = self
    cls.__init__ = init


_track(quiz_screen.QuizScreen, "quiz")

# Is a quiz on screen right now, and did the script ask for it?
quiz_state = {"open": False, "expected": False}
_quiz_run = quiz_screen.QuizScreen.run


async def _run_quiz(self):
    quiz_state["open"] = True
    try:
        return await _quiz_run(self)
    finally:
        quiz_state["open"] = False


quiz_screen.QuizScreen.run = _run_quiz
_track(stage_end_screens.TileScreen, "tile")
_track(stage_end_screens.LuckyDrawScreen, "draw")

# The demo's Stage Test is just two questions (one of each kind of screen);
# the real one has 12.
_build_test = game_mod.build_test


def short_test(*args, **kwargs):
    test = _build_test(*args, **kwargs)
    mc = [t for t in test if t["kind"] == "mc"]
    return [mc[-1], next(t for t in test if t["kind"] == "reading")]   # a fresh question, not one already shown


game_mod.build_test = short_test


# -- Captions ---------------------------------------------------------------------

caption = {"text": None, "since": 0, "pos": "top"}
overlay = {"title": 0.0, "end": 0.0}


def set_caption(text, pos="top"):
    """Shows `text` in a pill at the top of the frame ("top") or near the
    bottom ("bottom", for screens with a title of their own)."""
    if text != caption["text"]:
        caption.update(text=text, since=frame_no, pos=pos)
        if text:
            print(f"{frame_no / SIM_FPS:6.1f}s  {text}")


def draw_caption(surface):
    text = caption["text"]
    if quiz_state["open"] and not quiz_state["expected"]:
        text = "Every ? block is a Japanese quiz"     # one the bot bumped on its way
    if not text:
        return
    age = (frame_no - caption["since"]) / SIM_FPS
    alpha = min(1.0, age / 0.25)
    font = ui.body_font(19)
    label = font.render(text, True, (255, 244, 214))
    slide = round(8 * (1 - alpha))
    if caption["pos"] == "top":
        box = label.get_rect(midtop=(W // 2, 7 - slide)).inflate(32, 10)
    else:
        box = label.get_rect(midbottom=(W // 2, H - 14 + slide)).inflate(32, 10)
    pill = pygame.Surface(box.size, pygame.SRCALPHA)
    pygame.draw.rect(pill, (24, 18, 38, round(225 * alpha)), pill.get_rect(), border_radius=box.height // 2)
    pygame.draw.rect(pill, (255, 200, 80, round(255 * alpha)), pill.get_rect(), width=2, border_radius=box.height // 2)
    label.set_alpha(round(255 * alpha))
    pill.blit(label, label.get_rect(center=(box.width // 2, box.height // 2)))
    surface.blit(pill, box)


def draw_title(surface, strength, lines):
    """A dark veil with the game's name, faded by `strength` (0..1)."""
    if strength <= 0:
        return
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((14, 10, 26, round(200 * strength)))
    surface.blit(veil, (0, 0))
    title = ui.title_font(96).render("KOBITO", True, (255, 214, 90))
    shadow = ui.title_font(96).render("KOBITO", True, (60, 30, 20))
    for img, dy in ((shadow, 5), (title, 0)):
        img.set_alpha(round(255 * strength))
        surface.blit(img, img.get_rect(center=(W // 2, 210 + dy)))
    y = 300
    for text, size, color in lines:
        img = ui.body_font(size).render(text, True, color)
        img.set_alpha(round(255 * strength))
        surface.blit(img, img.get_rect(center=(W // 2, y)))
        y += size + 14


TITLE_LINES = [("こびと  ·  a Japanese-learning platformer", 26, (255, 244, 214)),
               ("Run, jump, and answer JLPT N5 – N1 questions", 20, (190, 210, 255))]
END_LINES = [("Learn Japanese while you play", 26, (255, 244, 214)),
             ("1,400+ questions  ·  N5 – N1  ·  AI companion hints", 20, (190, 210, 255))]


# -- Recording ----------------------------------------------------------------------

class Recorder:
    def __init__(self, path):
        self.path = path
        self.proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(OUT_FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
             "-preset", "slow", "-movflags", "+faststart", path],
            stdin=subprocess.PIPE)
        self.frames = 0

    def write(self, surface):
        self.proc.stdin.write(pygame.image.tobytes(surface, "RGB"))
        self.frames += 1

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


recorder = None
director = None
director_game = None
answering = {}      # quiz screen -> its answering helper (None once done)
last_frame = None
_flip = pygame.display.flip


def on_flip(*_):
    """Called every time the game finishes a frame: record it (with the
    caption on top), then let the director act for the next frame."""
    global frame_no, last_frame
    frame_no += 1
    last_frame = pygame.display.get_surface().copy()
    snaps = os.environ.get("KOBITO_DEMO_SNAPS")
    if snaps and frame_no % SIM_FPS == 0:
        pygame.image.save(last_frame, os.path.join(snaps, f"{frame_no // SIM_FPS:03d}.png"))
    if frame_no % (SIM_FPS // OUT_FPS) == 0:
        frame = pygame.display.get_surface().copy()
        draw_caption(frame)
        draw_title(frame, overlay["title"], TITLE_LINES)
        recorder.write(frame)
    # Any quiz that opens gets answered (right) by a helper running
    # alongside the script.
    quiz = current["quiz"]
    if quiz is not None and quiz not in answering:
        answering[quiz] = answer_quiz(quiz)
    for q, helper in list(answering.items()):
        if helper is not None:
            try:
                next(helper)
            except StopIteration:
                answering[q] = None
    if director is not None:
        if os.environ.get("KOBITO_DEMO_SNAPS") and frame_no % (SIM_FPS * 5) == 0:
            gen = director
            while getattr(gen, "gi_yieldfrom", None) is not None:
                gen = gen.gi_yieldfrom
            frame = gen.gi_frame
            where = f"{frame.f_code.co_name}:{frame.f_lineno}" if frame else "done"
            print(f"  [{frame_no / SIM_FPS:5.0f}s] {where}  x={director_game.player.rect.centerx}", flush=True)
        try:
            next(director)
        except StopIteration:
            pass


pygame.display.flip = on_flip


# -- The director -------------------------------------------------------------------

def wait(frames):
    for _ in range(frames):
        yield


def wait_until(cond, limit=600):
    for _ in range(limit):
        if cond():
            return
        yield


def tap(key, frames=6):
    held.add(key)
    yield from wait(frames)
    held.discard(key)


def ground_enemy_ahead(g, lo, hi):
    p = g.player.rect
    return any(lo < e.rect.centerx - p.centerx < hi and abs(e.rect.bottom - p.bottom) < 24
               for e in g.enemies if not getattr(e, "flying", False) and type(e) is Enemy)


def gap_ahead(g, lo=10, hi=60):
    """True just before the end of a stretch of ground (a pit ahead)."""
    p = g.player.rect
    segs = g.world.ground_segments_px
    return any(lo < end - p.centerx < hi for (_, end), (start, _) in zip(segs, segs[1:]) if start > end)


def run_right(g, until_x, run=True, auto_jump=True, fire_every=0, limit=420):
    """Hold right (and run) until the player passes `until_x`, hopping
    onto ground enemies, over pits and over walls on the way."""
    held.update({RIGHT} | ({RUN} if run else set()))
    stuck, last_x = 0, g.player.rect.x
    for i in range(limit):
        p = g.player
        if p.rect.centerx >= until_x or g.level_complete:
            break
        if auto_jump and p.on_ground and (ground_enemy_ahead(g, 40, 120) or gap_ahead(g) or stuck > 6):
            held.add(JUMP)
        elif JUMP in held and not p.on_ground and p.velocity_y > -150:
            held.discard(JUMP)
        if fire_every and i % fire_every == 0:
            held.add(FIRE)
        elif FIRE in held:
            held.discard(FIRE)
        stuck = stuck + 1 if abs(p.rect.x - last_x) < 1 and p.on_ground else 0
        last_x = p.rect.x
        yield
    held.difference_update({RIGHT, RUN, JUMP, FIRE})


def teleport(g, x, bottom=None, world=None):
    """Fades out, moves the player (optionally to another room), fades in."""
    done = []

    def go():
        if world is not None and g.world is not world:
            g._switch_world(world)
        g._place_player(x, g.world.ground_y if bottom is None else bottom)
        g.invulnerable_timer = 0.6
        done.append(True)
    yield from wait_until(lambda: g.transition is None)    # a fade already running would swallow ours
    g._start_transition(go)
    yield from wait_until(lambda: done and g.transition is None)


def answer_quiz(quiz):
    """Moves the highlight to the right answer (one key press at a time) and confirms."""
    yield from wait(55)
    target = quiz.question["answer"]
    while quiz.cursor != target:
        press(pygame.K_DOWN if quiz.cursor < target else pygame.K_UP)
        yield from wait(18)
    yield from wait(20)
    press(pygame.K_RETURN)


def quiz_done():
    """Waits for the open quiz to be answered and closed."""
    yield from wait_until(lambda: current["quiz"] is not None, 120)
    quiz = current["quiz"]
    yield from wait_until(lambda: answering.get(quiz, 1) is None, 900)
    yield from wait(60)     # the "Correct!" moment
    current["quiz"] = None


def script(g):
    s = g.surface
    bank = {q["id"]: q for q in g.question_bank.questions}

    # -- Title ---------------------------------------------------------------
    overlay["title"] = 1.0
    yield from wait(80)
    for i in range(20):
        overlay["title"] = 1 - (i + 1) / 20
        yield

    # -- Run, jump, stomp ---------------------------------------------------
    set_caption("Run, jump and stomp the yōkai")
    yield from run_right(g, 560)
    yield from wait(4)

    # -- A question block ------------------------------------------------------
    block = min((b for b in s.question_blocks if b.rect.x > 580), key=lambda b: b.rect.x)
    block.pending_question = shuffled(bank["vocab_n5_001"], random.Random(3))
    quiz_state["expected"] = True
    set_caption("Bump a ? block to get a Japanese question")
    yield from wait(45)
    held.add(RIGHT)
    yield from wait_until(lambda: g.player.rect.centerx >= block.rect.centerx - 4)
    held.discard(RIGHT)
    yield from tap(JUMP, 10)
    yield from wait_until(lambda: current["quiz"] is not None)
    set_caption("Pick the answer: right answers earn XP")
    yield from quiz_done()
    quiz_state["expected"] = False
    yield from wait(30)

    # -- Sunflower power ---------------------------------------------------------
    sun = min((c for c in s.collectibles if c.kind == "sunflower"), key=lambda c: c.rect.x)
    stone = next(pl for pl in s.platforms if pl.rect.left <= sun.rect.centerx <= pl.rect.right
                 and pl.rect.top >= sun.rect.bottom - 4)
    yield from teleport(g, stone.rect.left + 14, stone.rect.top)
    set_caption("Eat a sunflower for sun power…")
    held.add(RIGHT)
    yield from wait_until(lambda: g.sun_power, 120)
    held.discard(RIGHT)
    yield from wait(50)
    set_caption("…then throw sunballs at enemies")
    yield from run_right(g, g.player.rect.centerx + 420, run=False, fire_every=22)
    yield from wait(20)

    # -- A secret pit -----------------------------------------------------------
    pit = s.secret_pits[0]
    yield from teleport(g, pit["x0"] - 260)
    set_caption("Drop into a secret pit…")
    held.add(RIGHT)
    yield from wait_until(lambda: g.world is not s and g.transition is None, 300)
    held.discard(RIGHT)
    set_caption("…to find hidden bonus stages")
    yield from wait(30)
    yield from run_right(g, g.player.rect.centerx + 700, limit=200)
    yield from wait(10)

    # -- Up to the clouds -------------------------------------------------------
    spring = min(s.springs, key=lambda sp: sp.rect.x)
    yield from teleport(g, spring.rect.centerx - 120, world=s)
    set_caption("Bounce on a cloud spring…")
    held.add(RIGHT)
    yield from wait_until(lambda: g.player.rect.centerx >= spring.rect.centerx - 62)
    yield from tap(JUMP, 14)
    yield from wait_until(lambda: g.player.rect.centerx >= spring.rect.centerx - 2, 60)
    held.discard(RIGHT)
    yield from wait_until(lambda: g.world is not s and g.transition is None, 240)
    set_caption("…up to secret sky stages")
    yield from wait(50)
    held.add(RIGHT)
    yield from wait(40)
    held.discard(RIGHT)
    yield from wait(40)

    # -- The finish ---------------------------------------------------------------
    # The recording skips most of the level, so count the 20 answers a
    # real run would have by now (the castle won't open without them).
    g.correct_count = max(g.correct_count, 20 - g.wrong_count)
    yield from teleport(g, s.goal.rect.left - 420, world=s)
    set_caption("Answer 20, then reach the ゴール")
    yield from run_right(g, s.goal.rect.right, limit=400)
    set_caption("Stage clear!", "bottom")
    yield from wait(100)
    set_caption("Then review everything you learned")
    press(pygame.K_RETURN)
    yield from wait(70)
    for _ in range(4):
        press(pygame.K_DOWN)
        yield from wait(8)
    yield from wait(30)
    quiz_state["expected"] = True
    set_caption("Take the Stage Test")
    press(pygame.K_RETURN)
    yield from quiz_done()
    yield from wait_until(lambda: current["tile"] is not None)
    set_caption("Build readings from kana tiles")
    tile = current["tile"]
    yield from wait(40)
    for ch in tile.answer:
        i = next(i for i, t in enumerate(tile.tiles) if t == ch and i not in tile.placed)
        while tile.cursor != i:
            press(pygame.K_RIGHT if tile.cursor < i else pygame.K_LEFT)
            yield from wait(7)
        yield from wait(8)
        press(pygame.K_RETURN)
        yield from wait(14)
    yield from wait(90)
    yield from wait(70)
    press(pygame.K_RETURN)

    # -- Lucky draw -------------------------------------------------------------------
    yield from wait_until(lambda: current["draw"] is not None)
    set_caption(None)
    draw = current["draw"]
    yield from wait(70)
    yield from tap(JUMP, 8)
    yield from wait_until(lambda: draw.finished, 400)
    yield from wait(100)
    press(pygame.K_RETURN)


async def main():
    global recorder, director
    os.makedirs(OUT_DIR, exist_ok=True)
    mp4 = os.path.join(OUT_DIR, "cover.mp4")
    recorder = Recorder(mp4)
    g = game_mod.Game("capybara", "tokyo", companion_id="kobito", item_box={}, badges=[])
    g.rng = random.Random(7)
    g._take_hit = lambda *_: None    # the demo never gets hurt
    global director_game
    director_game = g
    director = script(g)
    outcome = (await g.run())[0]
    if outcome != game_mod.OUTCOME_ADVANCE:
        raise SystemExit(f"the demo didn't finish the stage (outcome {outcome!r}, last caption {caption['text']!r})")

    # Closing card over the last frame.
    last = last_frame
    set_caption(None)
    for i in range(110):
        frame = last.copy()
        draw_title(frame, min(1.0, (i + 1) / 20), END_LINES)
        recorder.write(frame)
    recorder.close()
    print(f"{mp4}: {recorder.frames} frames ({recorder.frames / OUT_FPS:.1f} s)")

    gif = os.path.join(OUT_DIR, "cover.gif")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf",
         "fps=10,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];"
         "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", gif],
        check=True)
    for path in (mp4, gif):
        print(f"{path}: {os.path.getsize(path) / 1e6:.1f} MB")


if __name__ == "__main__":
    asyncio.run(main())

"""Design QA: finds text that leaves its box, runs off the screen or lands on other text.

    python tools/qa_text_overflow.py          # prints every problem it finds, exits 1 if any

It draws the screens with the longest realistic strings (the longest world names, 10-letter
player names, 8-digit scores, every item / product / trophy / coach line) and watches every
ui.text() and ui.panel() call: text whose middle is inside a panel but which hangs out of it,
text outside the 960x540 screen (or its own surface), and different texts that overlap.
Text drawn straight from a font (a few cards in the review and quiz screens) is checked by the
measurements at the end instead.
"""

import os
import random
import re
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["KOBITO_SAVE_PATH"] = os.path.join(tempfile.mkdtemp(), "save.json")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((960, 540))

from kobito import furigana, progress, save_game, stage_test, ui, wardrobe  # noqa: E402
from kobito.board_screen import TABS, BoardScreen  # noqa: E402
from kobito.characters import CHARACTERS  # noqa: E402
from kobito.companion_select_screen import CompanionSelectScreen  # noqa: E402
from kobito.companions import COMPANIONS  # noqa: E402
from kobito.daily_screen import DailyBonusScreen  # noqa: E402
from kobito.difficulty_select_screen import OPTIONS, DifficultySelectScreen  # noqa: E402
from kobito.account_screen import AccountScreen, NameEntryScreen, PinScreen  # noqa: E402
from kobito.fonts import get_font  # noqa: E402
from kobito.game import SPEECH_BOX, Game  # noqa: E402
from kobito.house_screen import HouseScreen  # noqa: E402
from kobito.item_coach import VOICES, ItemCoach  # noqa: E402
from kobito.items import ITEMS  # noqa: E402
from kobito.levels import sky as sky_levels  # noqa: E402
from kobito.levels import underground as underground_levels  # noqa: E402
from kobito.profile import Profile, exp_for_level  # noqa: E402
from kobito.questions import QuestionBank, shuffled  # noqa: E402
from kobito.select_screen import SelectScreen  # noqa: E402
from kobito.settings_screen import PAGE_ITEMS, SettingsScreen  # noqa: E402
from kobito.shop_screen import ShopScreen  # noqa: E402
from kobito.stage_end_screens import ReviewScreen, ResultsScreen, TileScreen, wrap  # noqa: E402
from kobito.themes import THEMES  # noqa: E402
from kobito.title_screen import TitleScreen  # noqa: E402
from kobito.town_screen import STOPS, TownScreen  # noqa: E402
from kobito.world_select_screen import WORLD_ORDER, WorldSelectScreen  # noqa: E402

SCREEN = pygame.Rect(0, 0, 960, 540)
texts, boxes, problems, _seen = [], [], [], set()
_text, _panel, _rect = ui.text, ui.panel, pygame.draw.rect


def _spy_text(surface, string, font, pos, *args, **kwargs):
    rect = _text(surface, string, font, pos, *args, **kwargs)
    if string.strip():
        texts.append((string, pygame.Rect(rect), surface))
    return rect


def _spy_panel(surface, rect, *args, **kwargs):
    rect = _panel(surface, rect, *args, **kwargs)
    boxes.append((pygame.Rect(rect), surface))
    return rect


def _spy_rect(surface, color, rect, width=0, *args, **kwargs):
    out = _rect(surface, color, rect, width, *args, **kwargs)
    if width == 0 and "border_radius" in kwargs:
        r = pygame.Rect(rect)
        if 30 <= r.w <= 900 and 18 <= r.h <= 300:
            boxes.append((r, surface))
    return out


ui.text, ui.panel, pygame.draw.rect = _spy_text, _spy_panel, _spy_rect
# A pixel font's line box is taller than its glyphs, so vertical overhangs under this many px are fine.
SLACK = 14
# Badges that hang off a card's edge on purpose (the house's NEW! tag).
ON_PURPOSE = {"NEW!"}


def audit(label, draw, overlap=0.35):
    texts.clear()
    boxes.clear()
    draw()
    found = []
    for string, rect, surface in texts:
        bounds = surface.get_rect().inflate(0, 12)
        if not bounds.contains(rect):
            found.append(f"OFF-SURFACE {string!r} {tuple(rect)}")
        for box, owner in boxes:
            if owner is surface and not (box.w > 900 and box.h > 400) and string not in ON_PURPOSE \
                    and box.collidepoint(rect.center) and not box.inflate(0, SLACK).contains(rect.inflate(-2, -2)):
                found.append(f"EXCEEDS-BOX {string!r} text={tuple(rect)} box={tuple(box)}")
                break
    # (line boxes are taller than the glyphs: compare the middle 60% of each)
    tight = [(s, r.inflate(0, -round(r.h * 0.4)), f) for s, r, f in texts]
    for i, (s1, r1, f1) in enumerate(tight):
        for s2, r2, f2 in tight[i + 1:]:
            clip = r1.clip(r2)
            if f1 is f2 and s1 != s2 and clip.w and clip.h and clip.w * clip.h > overlap * min(r1.w * r1.h, r2.w * r2.h):
                found.append(f"OVERLAP {s1!r} x {s2!r}")
    for item in dict.fromkeys(found):
        key = re.sub(r"\(\d+, \d+, ", "(", item)
        if key not in _seen:
            _seen.add(key)
            problems.append(f"[{label}] {item}")


def measure(ok, message):
    if not ok:
        problems.append(f"[measure] {message}")


def world_map():
    screen = WorldSelectScreen("capybara", ["kabuto", "cape"])
    for town in WORLD_ORDER:
        screen.x, screen.y = screen.world.nodes[town]
        screen.entering = None
        screen._update_near(quiet=True)
        screen._snap_camera()
        audit(f"map card {town}", screen._draw)
    for x, y in ((360, 140), (2700, 1300), (1400, 1900), (400, 1900), (2500, 200)):
        screen.x, screen.y, screen.near = x, y, None
        screen._snap_camera()
        audit("map walking", screen._draw)


def town_screens():
    rich = Profile(exp=exp_for_level(20) + 40, yen=1234567, equipped={"head": "crown", "back": "tengu_wings"})
    town = TownScreen(rich, "capybara")
    for index, stop in enumerate(STOPS):
        town.index, town.x = index, float(stop[1])
        audit(f"town stop {index}", lambda: town._draw(False))
    for level, yen in ((1, 0), (6, 3000), (20, 99999999)):
        house = HouseScreen(town.screen, Profile(exp=exp_for_level(level), yen=yen), "capybara")
        for row in range(2):
            for col in range(len(house.rows[row])):
                house.row, house.col = row, col
                audit(f"house Lv{level} {house.selected.id}", house._draw)
        shop = ShopScreen(town.screen, Profile(exp=0, yen=yen))
        for row, products in enumerate(shop.rows):
            for col, product in enumerate(products):
                shop.row, shop.col = row, col
                audit(f"shop {product.id} {yen}", shop._draw)
    fat = Profile(exp=exp_for_level(30), yen=99999999)
    fat.trophies = [t.id for t in progress.TROPHIES]
    fat.streak = {"days": 365, "best": 365}
    save_game.sign_in(save_game.create_account("WWWWWWWWWW", pin="1234"))
    for tab, *_ in TABS:
        board = BoardScreen(town.screen, fat, tab)
        for i in range(len(progress.TROPHIES) if tab == "trophies" else 1):
            board.trophy = i
            audit(f"board {tab} {i}", board._draw)
        if tab == "ranking":
            for b in range(len(progress.BOARDS)):
                board.board = b
                audit(f"board ranking {b}", board._draw)


def setup_screens():
    hero = SelectScreen()
    for i in range(len(CHARACTERS)):
        hero.index = i
        audit(f"hero {i}", hero._draw)
    companion = CompanionSelectScreen()
    for i in range(len(COMPANIONS)):
        companion.index = i
        audit(f"companion {i}", companion._draw)
    for c in COMPANIONS:
        level = DifficultySelectScreen(c["id"])
        for i, option in enumerate(OPTIONS):
            level.index, level.typed = i, 999.0
            audit(f"level {c['id']} {option}", level._draw)
    profile = Profile(exp=exp_for_level(30), yen=9999999)
    for theme in ("okinawa_drive", "hokkaido_farm", "arabian_night", "greenland", "galapagos"):
        run = {"character_id": CHARACTERS[-1]["id"], "companion_id": COMPANIONS[-1]["id"], "theme_id": theme,
               "jlpt_level": "N1", "level_number": 99, "score": 99999999, "xp": 9999999,
               "item_box": {k: 99 for k in ITEMS}, "badges": ["b"] * 20, "question_history": [],
               "difficulty_mode": "adaptive", "tutor": None}
        title = TitleScreen({"run": run, "level": None}, profile, "WWWWWWWWWW")
        audit(f"title {theme}", title._draw)
        title.confirm_new = True
        audit(f"title confirm {theme}", title._draw)
    for days in (1, 7, 366):
        daily = DailyBonusScreen(Profile(), {"days": days, "bonus": 400, "best": days}, "WWWWWWWWWW")
        daily.time = 5
        audit(f"daily {days}", daily._draw)
    for n in range(1, 6):
        try:
            save_game.create_account(f"Player{n}XYZ"[:10], pin="1234" if n % 2 else None)
        except ValueError:
            pass            # already there
    who = AccountScreen()
    audit("who's playing", who._draw)
    names = NameEntryScreen()
    names.name = "WWWWWWWWWW"
    audit("name entry", names._draw)
    for mode in ("enter", "create", "set", "new"):
        try:
            pin = PinScreen(mode, save_game.list_accounts()[0])
        except Exception:  # noqa: BLE001 - not every mode exists in every version
            continue
        pin.pin = "12"
        pin._say("Wrong PIN -- 2 tries left", ui.RED)
        audit(f"pin {mode}", pin._draw)


def game_screens():
    game = Game("capybara", "okinawa_drive", companion_id="hana", item_box={k: 999 for k in ITEMS}, badges=["x"] * 12,
                level_number=99, jlpt_level="N1", starting_score=99999999, starting_xp=99999999)
    game.profile.add_yen(9999999)
    game.lives, game.guard_left, game.boost_timer, game.power, game.combo = 9, 5, 12, 2, 99
    game.guard_left, game.boost_timer = 5, 12
    game.correct_count, game.wrong_count = 999, 999
    audit("hud extremes", game._draw)
    for theme in THEMES:
        audit(f"hud {theme}", Game("capybara", theme, companion_id="kobito", item_box={}, badges=[], level_number=99,
                                   jlpt_level="N1")._draw)
    for title, sub in (("SECRET AREA!", "地下鉄  ·  NYC SUBWAY"), ("LEVEL UP!  Lv 30", "NEW COSTUME: SAMURAI KABUTO (兜)")):
        game.banner = (title, sub, 3.0)
        audit(f"banner {title}", game._draw)
    game.banner = None
    game.guard_left, game.boost_timer, game.power = 0, 0, 10      # (their HUD tags sit where a pop-up may land)
    for x in (20, 940):                      # pickups at the very edge of the view
        game.effects = []
        for name in ("tsukimi_dango", "lucky_bag", "protein_bar"):
            game._add_effect_text(ITEMS[name].name, (game.camera_x + x, 200), (255, 255, 255))
            game._add_effect_text("FULL POWER  +1 LIFE  +200円", (game.camera_x + x, 260), (255, 214, 90))
        audit(f"pop-ups at {x}", game._draw, overlap=2)     # (stacked on purpose: ignore overlaps)
    game.effects = []
    game.sun_power, game.sun_time_left = True, 19.5
    audit("sun power", game._draw)
    game.sun_power = False
    for score in (1234, 999999, 99999999):
        game.score, game.level_complete, game.level_accuracy, game.next_jlpt_level, game.badge_earned = \
            score, True, 0.82, "N1", True
        game.stomps = game.snacks_eaten = 9999
        audit(f"stage clear {score}", game._draw)
        game.level_complete, game.game_over = False, True
        audit(f"game over {score}", game._draw)
        game.game_over = False
    for pit in game.surface.secret_pits:
        game._enter_underground(pit)
        audit(f"room {pit['style']}", game._draw)
        game._switch_world(game.surface)
    for spring in game.surface.springs:
        game._enter_sky(spring.link)
        audit(f"sky {spring.link['style']}", game._draw)
        game._switch_world(game.surface)


def stage_end_screens():
    game = Game("capybara", "forest", companion_id="hana", item_box={k: 100 for k in ITEMS}, badges=[])
    game._draw()
    background = game.screen.copy()
    settings = SettingsScreen(game.screen, background, game.item_box)
    audit("settings menu", settings._draw)
    items = SettingsScreen(game.screen, background, game.item_box, start_page=PAGE_ITEMS)
    for scroll in range(-(-len(ITEMS) // 3) - 3):
        items.scroll = scroll
        audit(f"item box {scroll}", items._draw)
    bank = QuestionBank().questions
    rng = random.Random(1)
    longest = sorted(bank, key=lambda q: -(len(q["prompt"]) + sum(len(c) for c in q["choices"])))[:10]
    entries = []
    for i, q in enumerate(longest):
        q = shuffled(q, rng)
        result = ("right", "wrong", "skipped")[i % 3]
        wrong = (q["answer"] + 1) % len(q["choices"])
        entries.append({"question": q, "chosen": q["answer"] if result == "right" else wrong if result == "wrong" else None,
                        "result": result})
    words = stage_test.learned_words(entries, list(ITEMS.values()), list(underground_levels.STYLES.values())
                                     + list(sky_levels.STYLES.values()))
    for translation in (False, True):
        if furigana.is_translation_visible() != translation:
            furigana.toggle_translation()
        for log in (False, True):
            review = ReviewScreen(game.screen, background, 99, entries, words, 12, log=log)
            for scroll in range(0, review.max_scroll + 120, 120):
                review.scroll = min(scroll, review.max_scroll)
                audit(f"review {translation} {log} {scroll}", review._draw)
        # the first line of every review card shares its row with the "N4 · READING" tag
        body, label = review_fonts()
        for q in bank:
            tag = label.size(f"{q['jlpt']} · {q['category'].upper().replace('_', ' ')}")[0]
            first = wrap(f"1. {q['prompt']}", body, 840 - 60, first_width=840 - 44 - tag - 28)[0]
            measure(body.size(first)[0] <= 840 - 44 - tag - 28 + 1, f"review card line runs into its tag: {q['id']}")
    col_w = (960 - 72 - 40) // 2
    for word in [stage_test.word_from_item(i) for i in ITEMS.values()] + words:
        reading = word["kana"] if word["kana"] and word["kana"] != word["jp"] else ""
        need = get_font(24).size(word["jp"])[0] + 10 + max(get_font(14).size(f"{reading}  {word['romaji']}".strip())[0],
                                                           get_font(14).size((word["meaning"] or "")[:42])[0])
        measure(need <= col_w - 8, f"learned word row too wide: {word['jp']}")
    for results in ([("mc", True)] * 12, [("mc", True)] * 8 + [("reading", None), ("writing", True)] * 2):
        screen = ResultsScreen(game.screen, background, results, 120)
        screen.age = 9
        audit("results", screen._draw)


def review_fonts():
    return get_font(16), ui.label_font(16)


def speech_lines():
    game = Game("capybara", "forest", companion_id="hana", item_box={}, badges=[])
    width = SPEECH_BOX.right - 22 - (SPEECH_BOX.x + SPEECH_BOX.height - 14 + 14)
    messages = []
    for voice in VOICES.values():
        for lines in voice.values():
            messages += [t.format(item="Kaminari Okoshi", jp="雷おこし", pet="Scottish Fold", power=10, place="Thunder Clouds")
                         for t in lines]
    messages += [ItemCoach.lesson_line(item) for item in ITEMS.values()]
    messages += [underground_levels.place_lesson(s) for s in underground_levels.STYLES]
    messages += [sky_levels.place_lesson(s) for s in sky_levels.STYLES]
    messages += [f"Level 20! New: {g.name} -- {g.jp} ({g.reading}). Try it on at home!" for g in wardrobe.GEAR.values()]
    messages += [game._finish_line(n, gate) for n in (1, 5, 20) for gate in (False, True)]
    for text in messages:
        font, lines = game._fit_speech(text, width)
        measure(not lines[-1].endswith("…") and len(lines) <= 4, f"coach line is cut off: {text[:60]}")
        measure(all(font.size(line)[0] <= width for line in lines), f"coach line is wider than the box: {text[:60]}")


def main():
    for scenario in (world_map, town_screens, setup_screens, game_screens, stage_end_screens, speech_lines):
        scenario()
    for line in problems:
        print(line)
    print(f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

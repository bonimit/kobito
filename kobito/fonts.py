from pathlib import Path

import pygame

# Bundled rather than relying on a system font: pygame's default font has
# no Japanese glyphs, and we can't assume every player's OS has a CJK
# font installed.
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Three faces, each with one job, so text has a clear hierarchy:
#   "body"    IPA Gothic -- the quiz. Widest coverage (every kanji and
#             symbol in the question bank). IPA Font License.
#   "pixel"   DotGothic16 -- the game's own voice: HUD numbers, labels,
#             headings, floating "+10"s. A pixel face built on a 16px grid,
#             so it's crispest at 16 / 32 / 48. SIL Open Font License.
#   "rounded" M PLUS Rounded 1c Bold -- anything read as a sentence outside
#             the quiz: the companion's lines, settings, the item box.
#             SIL Open Font License.
FACES = {
    "body": FONT_DIR / "ipag.ttf",
    "pixel": FONT_DIR / "dotgothic16.ttf",
    "rounded": FONT_DIR / "mplus-rounded-1c-bold.ttf",
}
FONT_PATH = FACES["body"]

_font_cache = {}


def get_font(size, face="body"):
    """Returns a cached pygame.font.Font for `face` at `size`.

    Re-creating a Font object is relatively expensive, and the same
    sizes get requested every frame (HUD, quiz screen), so we keep one
    instance per (face, size) around instead of reloading the file.
    """
    key = (face, size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(str(FACES[face]), size)
    return _font_cache[key]


def pixel_font(size):
    return get_font(size, "pixel")


def rounded_font(size):
    return get_font(size, "rounded")

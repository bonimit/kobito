from pathlib import Path

import pygame

# Bundled rather than relying on a system font: pygame's default font has
# no Japanese glyphs, and we can't assume every player's OS has a CJK
# font installed. See assets/fonts/LICENSE_ipag.txt for the license.
FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "ipag.ttf"

_font_cache = {}


def get_font(size):
    """Returns a cached pygame.font.Font at the given point size.

    Re-creating a Font object is relatively expensive, and the same
    sizes get requested every frame (HUD, quiz screen), so we keep one
    instance per size around instead of reloading the font file
    repeatedly.
    """
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(str(FONT_PATH), size)
    return _font_cache[size]

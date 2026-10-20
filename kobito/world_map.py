"""The overworld: an RPG-style map of every world (kobito/world_select_screen.py).

Nineteen places sit on little islands joined by dirt roads and causeways --
the player's mascot walks between them and picks one to play. Everything is
drawn in code, at half resolution and scaled up 2x for chunky pixels:

  * NODES -- where each world is, in map pixels (MAP_W x MAP_H)
  * EDGES -- which places a road joins; the roads are also what you walk
    along when you tap a place (route())
  * each island has its own biome: ground colour, scatter (pines, palms,
    cacti, apple trees, cows ...) and a landmark (Mt Fuji, a pagoda, Big Ben,
    the pyramids ...), all in LANDMARKS / BIOMES below

build() paints the whole map once and returns an Overworld: the picture, the
walkable mask (land and roads -- the sea is blocked) and the road graph.
"""

import math
import random
from collections import deque

import pygame

from kobito.assets import ASSETS_DIR

SCALE = 2                       # the map is drawn at half size and scaled up
MAP_W, MAP_H = 1440, 810        # map pixels (the world is 2880 x 1620 screen pixels)
ROAD_HALF = 11                  # half the width of a road
ISLAND_R = 46                   # the usual island radius
INK = (30, 24, 38)
OCEAN = (46, 100, 172)

# name (English, Japanese, reading) -- shown under each place and in the info panel
PLACES = {
    "forest": ("Whispering Forest", "森", "mori"),
    "desert": ("Sunfall Desert", "砂漠", "sabaku"),
    "arabian_night": ("Arabian Night", "アラビアンナイト", "arabian naito"),
    "underwater": ("Coral Deep", "海の中", "umi no naka"),
    "sky": ("Cloud Kingdom", "空", "sora"),
    "tokyo": ("Neon Tokyo", "東京", "tōkyō"),
    "nagano": ("Nagano Snowfield", "長野", "nagano"),
    "okinawa": ("Okinawa Shore", "沖縄", "okinawa"),
    "hokkaido": ("Hokkaido Lavender", "北海道", "hokkaidō"),
    "kyoto": ("Kyoto Autumn", "京都", "kyōto"),
    "okinawa_drive": ("Okinawa Island Drive", "ドライブ", "doraibu"),
    "aomori": ("Aomori Apple Orchard", "青森", "aomori"),
    "shizuoka": ("Shizuoka Tea Fields", "静岡", "shizuoka"),
    "hokkaido_farm": ("Hokkaido Dairy Farm", "牧場", "bokujō"),
    "island": ("Coconut Island", "島", "shima"),
    "fairy_tale": ("Enchanted Kingdom", "おとぎ話", "otogibanashi"),
    "london": ("Foggy London", "ロンドン", "rondon"),
    "new_york": ("Empire City", "ニューヨーク", "nyūyōku"),
    "korea": ("Seoul Palace", "韓国", "kankoku"),
}

# Map positions. The hero starts at the forest; the west is the wide world,
# the middle the deserts and seas, the east Japan from Hokkaido down to Okinawa.
NODES = {
    "forest": (170, 610), "london": (110, 410), "new_york": (170, 200), "fairy_tale": (370, 130),
    "sky": (610, 110), "island": (860, 140), "desert": (400, 570), "arabian_night": (620, 660),
    "underwater": (560, 390), "korea": (880, 400), "kyoto": (1000, 650), "nagano": (1110, 450),
    "aomori": (1270, 350), "hokkaido_farm": (1190, 220), "hokkaido": (1300, 100), "tokyo": (1300, 520),
    "shizuoka": (1180, 630), "okinawa_drive": (1190, 740), "okinawa": (1350, 715),
}
EDGES = [
    ("forest", "london"), ("london", "new_york"), ("new_york", "fairy_tale"), ("fairy_tale", "sky"),
    ("sky", "island"), ("forest", "desert"), ("desert", "arabian_night"), ("desert", "underwater"),
    ("fairy_tale", "underwater"), ("arabian_night", "kyoto"), ("underwater", "korea"), ("island", "korea"),
    ("korea", "nagano"), ("korea", "kyoto"), ("kyoto", "shizuoka"), ("shizuoka", "tokyo"),
    ("tokyo", "nagano"), ("nagano", "aomori"), ("tokyo", "aomori"), ("aomori", "hokkaido_farm"),
    ("hokkaido_farm", "hokkaido"), ("shizuoka", "okinawa_drive"), ("okinawa_drive", "okinawa"),
]

# Island ground colour, the scatter on it (kind, weight), how much of it, and a
# stripe pattern (crop rows) for the fields.
BIOMES = {
    "forest": dict(color=(94, 172, 82), scatter=[("oak", 5), ("pine", 3), ("mushroom", 2), ("flower", 3)], n=16),
    "desert": dict(color=(234, 198, 126), scatter=[("cactus", 4), ("rock", 3), ("dune", 4)], n=11),
    "arabian_night": dict(color=(168, 126, 92), scatter=[("palm", 4), ("rock", 2), ("dune", 3)], n=10),
    "underwater": dict(color=(118, 204, 200), scatter=[("coral", 3), ("shell", 3), ("bubbles", 3), ("star", 3)], n=9),
    "sky": dict(color=(238, 244, 252), scatter=[("puff", 6), ("star", 3)], n=10),
    "tokyo": dict(color=(122, 126, 142), scatter=[("tower", 6), ("lamp", 3)], n=10),
    "nagano": dict(color=(232, 238, 248), scatter=[("snowpine", 6), ("rock", 2)], n=14),
    "okinawa": dict(color=(246, 230, 178), scatter=[("palm", 5), ("hibiscus", 4), ("shell", 2)], n=11),
    "hokkaido": dict(color=(168, 134, 214), scatter=[("pine", 3), ("flower", 3)], n=8, stripes=((120, 82, 190), 5)),
    "kyoto": dict(color=(176, 132, 84), scatter=[("maple", 7), ("lamp", 2), ("rock", 2)], n=13),
    "okinawa_drive": dict(color=(228, 224, 200), scatter=[("palm", 5), ("shell", 3), ("hibiscus", 2)], n=9),
    "aomori": dict(color=(140, 184, 84), scatter=[("apple", 9), ("flower", 2)], n=18),
    "shizuoka": dict(color=(72, 152, 72), scatter=[("pine", 2), ("flower", 1)], n=6, stripes=((40, 112, 52), 4)),
    "hokkaido_farm": dict(color=(128, 188, 92), scatter=[("cow", 4), ("fence", 3), ("hay", 3), ("flower", 2)], n=12),
    "island": dict(color=(246, 234, 184), scatter=[("palm", 6), ("shell", 3), ("rock", 1)], n=10),
    "fairy_tale": dict(color=(190, 214, 150), scatter=[("pinktree", 6), ("mushroom", 4), ("flower", 4)], n=14),
    "london": dict(color=(136, 144, 152), scatter=[("house", 5), ("lamp", 3), ("oak", 2)], n=11),
    "new_york": dict(color=(112, 120, 136), scatter=[("tower", 7), ("lamp", 3)], n=11),
    "korea": dict(color=(152, 198, 114), scatter=[("pine", 5), ("house", 3), ("maple", 2)], n=12),
}
ROAD = (206, 172, 112)
ROAD_EDGE = (150, 112, 70)
GRASS = (104, 176, 90)
SAND = (244, 226, 170)


# --- tiny drawing helpers (map pixels; (x, y) is where the thing stands) ---------

_shadows = {}


def _shadow(s, x, y, w):
    if w not in _shadows:
        sh = pygame.Surface((w * 2 + 2, w + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 64), sh.get_rect())
        _shadows[w] = sh
    s.blit(_shadows[w], (x - w - 1, y - w // 2))


def _poly(s, color, pts, outline=True):
    pygame.draw.polygon(s, color, pts)
    if outline:
        pygame.draw.polygon(s, INK, pts, 1)


def _rect(s, color, rect, outline=True):
    pygame.draw.rect(s, color, rect)
    if outline:
        pygame.draw.rect(s, INK, rect, 1)


def _ball(s, color, center, r, hi=None):
    pygame.draw.circle(s, INK, center, r + 1)
    pygame.draw.circle(s, color, center, r)
    if hi:
        pygame.draw.circle(s, hi, (center[0] - r // 3, center[1] - r // 3), max(1, r // 3))


def _tree(s, x, y, leaf=(62, 142, 72), hi=(112, 192, 102), r=5):
    _shadow(s, x, y, r + 2)
    _rect(s, (120, 80, 48), (x - 1, y - r, 3, r))
    _ball(s, leaf, (x, y - r - r // 2), r, hi)


def _pine(s, x, y, leaf=(46, 118, 80), snow=False):
    _shadow(s, x, y, 5)
    _rect(s, (110, 74, 44), (x - 1, y - 3, 3, 3), False)
    for i, (w, top) in enumerate(((9, 9), (7, 15), (5, 20))):
        _poly(s, leaf, [(x - w // 2 - 1, y - top + 6), (x, y - top - 3), (x + w // 2 + 1, y - top + 6)])
        if snow:
            pygame.draw.line(s, (250, 252, 255), (x - w // 2 + 1, y - top + 4), (x + w // 2 - 1, y - top + 4), 2)


def _palm(s, x, y, big=1):
    _shadow(s, x, y, 5)
    top = (x + 2 * big, y - 14 * big)
    pygame.draw.line(s, INK, (x, y), top, 3)
    pygame.draw.line(s, (170, 120, 70), (x, y), top, 1)
    for dx, dy in ((-7, -2), (-5, 2), (0, -5), (6, 1), (7, -3), (3, -6)):
        pygame.draw.line(s, INK, top, (top[0] + dx * big, top[1] + dy * big), 3)
        pygame.draw.line(s, (70, 170, 80), top, (top[0] + dx * big, top[1] + dy * big), 1)
    pygame.draw.circle(s, (120, 80, 40), (top[0] + 1, top[1] + 2), 2)


def _cactus(s, x, y):
    _shadow(s, x, y, 4)
    _rect(s, (76, 150, 84), (x - 2, y - 12, 4, 12))
    _rect(s, (76, 150, 84), (x - 6, y - 9, 3, 2))
    _rect(s, (76, 150, 84), (x - 6, y - 12, 2, 4))
    _rect(s, (76, 150, 84), (x + 3, y - 7, 3, 2))
    _rect(s, (76, 150, 84), (x + 5, y - 10, 2, 4))


def _rock(s, x, y, color=(150, 146, 150)):
    _shadow(s, x, y, 5)
    _poly(s, color, [(x - 5, y), (x - 4, y - 5), (x, y - 7), (x + 4, y - 5), (x + 5, y)])
    pygame.draw.line(s, (210, 208, 212), (x - 2, y - 5), (x, y - 6))


def _mountain(s, x, y):
    _shadow(s, x, y, 9)
    _poly(s, (128, 124, 140), [(x - 12, y), (x - 4, y - 14), (x + 1, y - 9), (x + 6, y - 17), (x + 14, y)])
    _poly(s, (160, 156, 172), [(x - 4, y - 14), (x + 1, y - 9), (x - 3, y - 3), (x - 8, y - 4)], False)
    _poly(s, (250, 252, 255), [(x + 3, y - 13), (x + 6, y - 17), (x + 9, y - 12), (x + 6, y - 10)], False)


def _dune(s, x, y):
    pygame.draw.arc(s, (206, 164, 96), (x - 9, y - 6, 18, 10), 0.3, 2.8, 2)


def _mushroom(s, x, y):
    _rect(s, (240, 230, 210), (x - 1, y - 4, 3, 4))
    pygame.draw.ellipse(s, INK, (x - 5, y - 9, 11, 7))
    pygame.draw.ellipse(s, (220, 60, 70), (x - 4, y - 8, 9, 5))
    pygame.draw.circle(s, (255, 255, 255), (x - 1, y - 6), 1)
    pygame.draw.circle(s, (255, 255, 255), (x + 2, y - 7), 1)


def _flower(s, x, y, color=None):
    color = color or random.choice(((250, 200, 220), (255, 240, 120), (255, 255, 255), (250, 150, 120)))
    s.set_at((x, y), color)
    s.set_at((x + 1, y), color)
    s.set_at((x, y + 1), (60, 140, 70))


def _coral(s, x, y):
    color = random.choice(((240, 110, 140), (250, 150, 90), (180, 120, 220)))
    for dx, h in ((-3, 6), (0, 9), (3, 5)):
        pygame.draw.line(s, INK, (x + dx, y), (x + dx, y - h), 3)
        pygame.draw.line(s, color, (x + dx, y), (x + dx, y - h), 1)


def _shell(s, x, y):
    pygame.draw.ellipse(s, INK, (x - 3, y - 4, 7, 5))
    pygame.draw.ellipse(s, (252, 220, 214), (x - 2, y - 3, 5, 3))


def _bubbles(s, x, y):
    for dx, dy, r in ((0, 0, 2), (3, -4, 1), (-2, -7, 1)):
        pygame.draw.circle(s, (220, 244, 255), (x + dx, y + dy), r, 1)


def _puff(s, x, y):
    for dx, dy, r in ((-4, 0, 3), (0, -2, 4), (4, 0, 3)):
        pygame.draw.circle(s, (196, 214, 240), (x + dx, y + dy + 1), r)
    for dx, dy, r in ((-4, 0, 3), (0, -2, 4), (4, 0, 3)):
        pygame.draw.circle(s, (255, 255, 255), (x + dx, y + dy), r)


def _star(s, x, y):
    for dx, dy in ((0, -2), (0, 2), (-2, 0), (2, 0), (0, 0)):
        s.set_at((x + dx, y + dy), (255, 236, 150))


def _tower(s, x, y):
    h = random.choice((12, 16, 20, 24))
    c = random.choice(((90, 96, 120), (110, 118, 150), (74, 80, 104), (136, 110, 130)))
    _shadow(s, x, y, 6)
    _rect(s, c, (x - 4, y - h, 8, h))
    for wy in range(y - h + 2, y - 2, 4):
        for wx in (x - 2, x + 1):
            s.set_at((wx, wy), (255, 226, 140) if (wx + wy) % 3 else (60, 60, 80))


def _lamp(s, x, y):
    pygame.draw.line(s, INK, (x, y), (x, y - 9), 1)
    pygame.draw.circle(s, (255, 226, 140), (x, y - 10), 2)


def _maple(s, x, y):
    c = random.choice(((214, 80, 40), (232, 140, 40), (200, 50, 50), (240, 190, 60)))
    _tree(s, x, y, c, (255, 220, 120), 4)


def _apple(s, x, y):
    _tree(s, x, y, (84, 160, 64), (136, 204, 96), 5)
    for dx, dy in ((-3, -9), (2, -12), (3, -8), (-1, -6)):
        pygame.draw.circle(s, (230, 50, 60), (x + dx, y + dy), 1)
        s.set_at((x + dx, y + dy), (255, 150, 150))


def _cow(s, x, y):
    _shadow(s, x, y, 5)
    _rect(s, (250, 250, 250), (x - 4, y - 5, 8, 4))
    _rect(s, (250, 250, 250), (x + 3, y - 7, 3, 3))
    pygame.draw.rect(s, (40, 40, 48), (x - 2, y - 5, 3, 2))
    pygame.draw.rect(s, (40, 40, 48), (x - 3, y - 1, 1, 2))
    pygame.draw.rect(s, (40, 40, 48), (x + 2, y - 1, 1, 2))


def _fence(s, x, y):
    for dx in (-5, 0, 5):
        _rect(s, (180, 130, 80), (x + dx, y - 5, 1, 5), False)
    pygame.draw.line(s, (214, 170, 110), (x - 5, y - 4), (x + 5, y - 4))
    pygame.draw.line(s, (214, 170, 110), (x - 5, y - 2), (x + 5, y - 2))


def _hay(s, x, y):
    _shadow(s, x, y, 5)
    _ball(s, (232, 200, 90), (x, y - 4), 4, (252, 236, 150))


def _pinktree(s, x, y):
    _tree(s, x, y, (240, 150, 190), (255, 210, 230), 5)


def _house(s, x, y):
    wall = random.choice(((226, 214, 190), (200, 120, 90), (210, 190, 150)))
    _shadow(s, x, y, 6)
    _rect(s, wall, (x - 5, y - 6, 10, 6))
    _poly(s, (110, 90, 100), [(x - 7, y - 6), (x, y - 12), (x + 7, y - 6)])
    s.set_at((x, y - 3), (255, 226, 140))


def _hibiscus(s, x, y):
    _flower(s, x, y, (250, 70, 100))
    _flower(s, x + 2, y - 1, (255, 120, 140))


PROPS = {
    "mountain": _mountain, "oak": _tree, "pine": _pine, "snowpine": lambda s, x, y: _pine(s, x, y, (70, 128, 100), snow=True),
    "palm": _palm, "cactus": _cactus, "rock": _rock, "dune": _dune, "mushroom": _mushroom, "flower": _flower,
    "coral": _coral, "shell": _shell, "bubbles": _bubbles, "puff": _puff, "star": _star, "tower": _tower,
    "lamp": _lamp, "maple": _maple, "apple": _apple, "cow": _cow, "fence": _fence, "hay": _hay,
    "pinktree": _pinktree, "house": _house, "hibiscus": _hibiscus,
}


# --- landmarks: one per world, standing on the plaza at the island's centre -----

def _lm_forest(s, x, y):
    _tree(s, x - 9, y + 2, (46, 122, 66), (100, 184, 96), r=9)
    for px in (x + 8, x + 20):
        _rect(s, (210, 50, 50), (px, y - 15, 3, 15))
    _rect(s, (210, 50, 50), (x + 5, y - 18, 21, 3))
    _rect(s, (210, 50, 50), (x + 8, y - 12, 15, 2))


def _lm_desert(s, x, y):
    for cx, sc in ((x + 14, 0.55), (x - 6, 1.0)):
        w, h = 20 * sc, 28 * sc
        _poly(s, (226, 184, 102), [(cx - w, y), (cx, y - h), (cx + w, y)])
        _poly(s, (246, 214, 140), [(cx - w, y), (cx, y - h), (cx, y)], False)
        pygame.draw.polygon(s, INK, [(cx - w, y), (cx, y - h), (cx + w, y)], 1)


def _lm_arabian_night(s, x, y):
    for mx in (x - 19, x + 14):
        _rect(s, (236, 216, 176), (mx, y - 26, 5, 26))
        _poly(s, (90, 110, 210), [(mx - 1, y - 26), (mx + 2, y - 33), (mx + 6, y - 26)])
    _rect(s, (240, 222, 184), (x - 14, y - 14, 28, 14))
    _ball(s, (80, 100, 210), (x, y - 17), 10, (140, 160, 250))
    pygame.draw.line(s, (255, 214, 80), (x, y - 27), (x, y - 33), 1)
    pygame.draw.circle(s, (255, 214, 80), (x, y - 35), 3)
    pygame.draw.circle(s, (18, 16, 48), (x + 1, y - 36), 3)
    _rect(s, (60, 40, 90), (x - 3, y - 8, 6, 8))


def _lm_underwater(s, x, y):
    pygame.draw.ellipse(s, INK, (x - 18, y - 17, 36, 18))
    pygame.draw.ellipse(s, (80, 124, 208), (x - 17, y - 16, 34, 16))
    pygame.draw.ellipse(s, (220, 236, 250), (x - 12, y - 7, 24, 6))
    _poly(s, (80, 124, 208), [(x + 15, y - 8), (x + 24, y - 18), (x + 22, y - 6)])
    pygame.draw.circle(s, INK, (x - 9, y - 11), 1)
    for dx, dy in ((-8, -22), (-6, -27), (-9, -31)):
        pygame.draw.circle(s, (230, 248, 255), (x + dx, y + dy), 2, 1)


def _lm_sky(s, x, y):
    for i, c in enumerate(((232, 72, 72), (250, 200, 60), (110, 200, 100), (80, 160, 230))):
        pygame.draw.arc(s, c, (x - 18 + i * 2, y - 40 + i * 2, 36 - i * 4, 36 - i * 4), 0, math.pi, 2)
    for dx, dy, r in ((-11, -6, 8), (0, -11, 11), (11, -6, 8)):
        pygame.draw.circle(s, (170, 196, 232), (x + dx, y + dy + 1), r + 1)
    for dx, dy, r in ((-11, -6, 8), (0, -11, 11), (11, -6, 8)):
        pygame.draw.circle(s, (255, 255, 255), (x + dx, y + dy), r)


def _lm_tokyo(s, x, y):
    _poly(s, (230, 70, 50), [(x - 11, y), (x - 1, y - 34), (x + 1, y - 34), (x + 11, y)])
    for ty in (y - 8, y - 18, y - 27):
        k = (y - ty) / 34
        pygame.draw.line(s, (255, 255, 255), (x - 11 + 10 * k, ty), (x + 11 - 10 * k, ty), 2)
    _rect(s, (255, 150, 120), (x - 6, y - 17, 12, 3))
    _rect(s, (255, 150, 120), (x - 4, y - 28, 8, 2))
    pygame.draw.line(s, INK, (x, y - 34), (x, y - 46), 1)
    pygame.draw.line(s, (240, 240, 240), (x - 3, y - 4), (x + 3, y - 24))


def _lm_nagano(s, x, y):
    _poly(s, (112, 134, 178), [(x - 26, y), (x - 8, y - 32), (x + 2, y - 22), (x + 10, y - 30), (x + 28, y)])
    _poly(s, (250, 252, 255), [(x - 12, y - 24), (x - 8, y - 32), (x - 3, y - 25), (x - 6, y - 22), (x - 9, y - 25)], False)
    _poly(s, (250, 252, 255), [(x + 6, y - 24), (x + 10, y - 30), (x + 14, y - 24), (x + 10, y - 21)], False)
    _rect(s, (212, 172, 112), (x - 8, y - 8, 16, 8))
    _poly(s, (212, 184, 90), [(x - 11, y - 8), (x, y - 19), (x + 11, y - 8)])


def _lm_okinawa(s, x, y):
    _rect(s, (210, 200, 186), (x - 18, y - 3, 36, 3))
    _rect(s, (206, 50, 46), (x - 12, y - 14, 24, 11))
    _rect(s, (255, 214, 90), (x - 3, y - 10, 6, 7))
    _poly(s, (230, 110, 50), [(x - 19, y - 14), (x - 11, y - 22), (x + 11, y - 22), (x + 19, y - 14)])
    _poly(s, (230, 110, 50), [(x - 11, y - 22), (x - 5, y - 28), (x + 5, y - 28), (x + 11, y - 22)])
    _palm(s, x + 24, y + 2, 1.2)


def _lm_hokkaido(s, x, y):
    _rect(s, (246, 244, 236), (x - 5, y - 24, 10, 24))
    _ball(s, (255, 255, 255), (x, y - 17), 3)
    pygame.draw.line(s, INK, (x, y - 17), (x, y - 19))
    pygame.draw.line(s, INK, (x, y - 17), (x + 2, y - 17))
    _poly(s, (210, 60, 60), [(x - 8, y - 24), (x, y - 38), (x + 8, y - 24)])
    _rect(s, (160, 100, 70), (x - 2, y - 6, 4, 6))


def _lm_kyoto(s, x, y):
    _rect(s, (206, 200, 190), (x - 14, y - 2, 28, 3))
    for i in range(4):
        w, y0 = 24 - i * 4, y - 3 - i * 9
        _rect(s, (210, 60, 50) if i % 2 == 0 else (240, 230, 210), (x - w // 2 + 2, y0 - 5, w - 4, 6))
        _poly(s, (88, 124, 110), [(x - w // 2 - 3, y0), (x - w // 2 + 3, y0 - 6), (x + w // 2 - 3, y0 - 6), (x + w // 2 + 3, y0)])
    pygame.draw.line(s, INK, (x, y - 40), (x, y - 48))


def _lm_okinawa_drive(s, x, y):
    _rect(s, (70, 74, 86), (x - 24, y - 3, 48, 5), False)
    for dx in range(-20, 20, 8):
        pygame.draw.line(s, (240, 240, 220), (x + dx, y), (x + dx + 3, y))
    _rect(s, (222, 60, 70), (x - 14, y - 10, 28, 8))
    _rect(s, (150, 206, 240), (x - 5, y - 16, 10, 6))
    _rect(s, (222, 60, 70), (x - 7, y - 17, 3, 3), False)
    for wx in (x - 8, x + 8):
        _ball(s, (40, 40, 48), (wx, y - 2), 3, (150, 150, 160))
    pygame.draw.rect(s, (255, 236, 120), (x + 13, y - 8, 2, 2))
    _palm(s, x - 22, y - 2, 1.1)


def _lm_aomori(s, x, y):
    _ball(s, (226, 48, 60), (x, y - 14), 13, (255, 150, 150))
    _poly(s, (226, 48, 60), [(x - 4, y - 24), (x, y - 21), (x + 4, y - 24), (x + 2, y - 15), (x - 2, y - 15)], False)
    pygame.draw.line(s, (110, 72, 40), (x, y - 26), (x + 1, y - 31), 2)
    _poly(s, (80, 170, 70), [(x + 1, y - 30), (x + 8, y - 33), (x + 5, y - 27)])


def _lm_shizuoka(s, x, y):
    _poly(s, (92, 116, 188), [(x - 28, y), (x - 8, y - 32), (x + 8, y - 32), (x + 28, y)])
    _poly(s, (252, 252, 255), [(x - 9, y - 27), (x - 8, y - 32), (x + 8, y - 32), (x + 9, y - 27), (x + 4, y - 22), (x, y - 27), (x - 4, y - 22)], False)
    pygame.draw.polygon(s, INK, [(x - 28, y), (x - 8, y - 32), (x + 8, y - 32), (x + 28, y)], 1)
    _ball(s, (248, 244, 230), (x + 20, y - 4), 3)
    pygame.draw.line(s, (120, 190, 90), (x + 14, y), (x + 26, y), 2)


def _lm_hokkaido_farm(s, x, y):
    _rect(s, (206, 54, 46), (x - 14, y - 13, 28, 13))
    _poly(s, (150, 36, 40), [(x - 17, y - 13), (x - 10, y - 24), (x + 10, y - 24), (x + 17, y - 13)])
    _rect(s, (250, 250, 250), (x - 4, y - 9, 8, 9))
    pygame.draw.line(s, INK, (x - 4, y - 9), (x + 3, y - 1))
    pygame.draw.line(s, INK, (x + 3, y - 9), (x - 4, y - 1))
    _rect(s, (196, 200, 210), (x + 17, y - 24, 8, 24))
    _ball(s, (196, 200, 210), (x + 21, y - 25), 4)


def _lm_island(s, x, y):
    _palm(s, x - 8, y, 1.7)
    _rect(s, (150, 104, 66), (x + 6, y - 8, 12, 8))
    _poly(s, (206, 176, 80), [(x + 3, y - 8), (x + 12, y - 16), (x + 21, y - 8)])
    _rect(s, (60, 40, 30), (x + 10, y - 5, 4, 5), False)


def _lm_fairy_tale(s, x, y):
    for tx, h in ((x - 17, 20), (x + 9, 20), (x - 5, 30)):
        _rect(s, (242, 186, 206), (tx, y - h, 8 if tx != x - 5 else 10, h))
        w = 8 if tx != x - 5 else 10
        _poly(s, (90, 124, 224), [(tx - 2, y - h), (tx + w // 2, y - h - 12), (tx + w + 2, y - h)])
    _rect(s, (244, 196, 214), (x - 9, y - 12, 18, 12))
    _rect(s, (120, 70, 110), (x - 2, y - 7, 4, 7))
    pygame.draw.line(s, INK, (x, y - 42), (x, y - 49))
    _poly(s, (230, 60, 80), [(x, y - 49), (x + 6, y - 47), (x, y - 45)], False)


def _lm_london(s, x, y):
    _rect(s, (214, 184, 124), (x - 6, y - 34, 12, 34))
    _rect(s, (190, 160, 100), (x - 14, y - 9, 9, 9))
    _poly(s, (90, 112, 104), [(x - 7, y - 34), (x, y - 47), (x + 7, y - 34)])
    _ball(s, (255, 250, 230), (x, y - 26), 4)
    pygame.draw.line(s, INK, (x, y - 26), (x, y - 28))
    pygame.draw.line(s, INK, (x, y - 26), (x + 2, y - 25))
    _rect(s, (220, 40, 44), (x + 11, y - 7, 5, 7))


def _lm_new_york(s, x, y):
    _rect(s, (170, 170, 178), (x - 7, y - 10, 14, 10))
    _poly(s, (116, 192, 164), [(x - 5, y - 10), (x - 3, y - 27), (x + 3, y - 27), (x + 5, y - 10)])
    _ball(s, (116, 192, 164), (x, y - 30), 3)
    for dx in (-3, 0, 3):
        pygame.draw.line(s, (116, 192, 164), (x, y - 31), (x + dx, y - 35))
    pygame.draw.line(s, INK, (x + 3, y - 26), (x + 7, y - 38), 3)
    pygame.draw.line(s, (116, 192, 164), (x + 3, y - 26), (x + 7, y - 38), 1)
    _ball(s, (255, 214, 80), (x + 7, y - 40), 2)
    for bx, h in ((x - 20, 18), (x + 14, 24)):
        _rect(s, (92, 100, 130), (bx, y - h, 7, h))


def _lm_korea(s, x, y):
    _rect(s, (160, 160, 170), (x - 19, y - 8, 38, 8))
    _poly(s, (30, 30, 40), [(x - 5, y), (x - 5, y - 5), (x - 2, y - 8), (x + 2, y - 8), (x + 5, y - 5), (x + 5, y)], False)
    _rect(s, (206, 54, 50), (x - 13, y - 18, 26, 10))
    _poly(s, (50, 124, 120), [(x - 21, y - 17), (x - 14, y - 19), (x - 12, y - 27), (x + 12, y - 27), (x + 14, y - 19), (x + 21, y - 17)])
    _poly(s, (50, 124, 120), [(x - 10, y - 27), (x - 5, y - 36), (x + 5, y - 36), (x + 10, y - 27)])
    pygame.draw.line(s, (255, 214, 80), (x - 20, y - 17), (x + 20, y - 17))


LANDMARKS = {name[4:]: fn for name, fn in globals().items() if name.startswith("_lm_")}


# --- building the map ------------------------------------------------------------

def _seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _blob(center, radius, rng, squash=0.92):
    """An outline: a circle with a lumpy edge (never smaller than ~70%)."""
    ph = [rng.uniform(0, 6.28) for _ in range(3)]
    pts = []
    for i in range(36):
        a = i * math.tau / 36
        k = 1 + 0.12 * math.sin(a * 3 + ph[0]) + 0.08 * math.sin(a * 5 + ph[1]) + 0.05 * math.sin(a * 9 + ph[2])
        pts.append((center[0] + math.cos(a) * radius * k, center[1] + math.sin(a) * radius * k * squash))
    return pts


def _clip_halfplane(poly, point, normal):
    """Keeps the part of `poly` with (p - point) . normal <= 0 (Sutherland-Hodgman)."""
    def inside(p):
        return (p[0] - point[0]) * normal[0] + (p[1] - point[1]) * normal[1] <= 0

    out = []
    for i, cur in enumerate(poly):
        prev = poly[i - 1]
        if inside(cur) != inside(prev):
            d0 = (prev[0] - point[0]) * normal[0] + (prev[1] - point[1]) * normal[1]
            d1 = (cur[0] - point[0]) * normal[0] + (cur[1] - point[1]) * normal[1]
            t = d0 / (d0 - d1)
            out.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
        if inside(cur):
            out.append(cur)
    return out


def _wobble(poly, step=7):
    """Cell borders, broken into short steps and nudged by a smooth noise so they wander."""
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // step))
        for k in range(n):
            x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
            out.append((x + 5 * math.sin(y * 0.09 + x * 0.03), y + 5 * math.sin(x * 0.08 - y * 0.04)))
    return out


# The land: the loops of roads that are filled in as solid ground. The loop
# around the inner sea (fairy tale - sky - island - Korea - Coral Deep) is left
# as water, so Coral Deep and Coconut Island sit on a shore.
LAND_LOOPS = [
    ("forest", "london", "new_york", "fairy_tale", "underwater", "desert"),
    ("desert", "underwater", "korea", "kyoto", "arabian_night"),
    ("korea", "nagano", "tokyo", "shizuoka", "kyoto"),
    ("nagano", "aomori", "tokyo"),
]
LAKES = [(250, 460, 34, 22), (305, 320, 26, 18), (780, 560, 40, 22), (1050, 540, 30, 18), (470, 600, 24, 14)]
ISLETS = [(70, 90, 14), (60, 700, 12), (330, 750, 11), (760, 770, 14), (950, 40, 10), (1110, 780, 9), (1410, 420, 12),
          (500, 30, 9), (1400, 250, 10), (1000, 300, 8)]
NO_MOUNTAINS = {"sky", "underwater", "new_york", "tokyo", "okinawa", "island", "okinawa_drive", "london"}


MAP_DIR = ASSETS_DIR / "map"
PICTURE, WALKABLE = "world_map.png", "world_map_mask.png"


class Overworld:
    """The map. Painting it takes a second or two, so `python tools/make_world_map.py`
    bakes the picture and the walkable mask into assets/map/ and the game just loads
    those (it paints the map itself if they're missing)."""

    def __init__(self, paint=False):
        rng = random.Random(2024)
        self.nodes = {k: (x * SCALE, y * SCALE) for k, (x, y) in NODES.items()}      # screen-sized pixels
        self.neighbors = {k: [] for k in NODES}
        # Each road bends a little: a middle point pushed to the side.
        self.roads = {}
        for a, b in EDGES:
            pa, pb = NODES[a], NODES[b]
            mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
            length = math.hypot(pb[0] - pa[0], pb[1] - pa[1]) or 1
            bend = rng.uniform(-0.1, 0.1) * length
            mid = (mx - (pb[1] - pa[1]) / length * bend, my + (pb[0] - pa[0]) / length * bend)
            self.roads[(a, b)] = [pa, mid, pb]
            self.neighbors[a].append(b)
            self.neighbors[b].append(a)
        self.segments = [(a, b) for pts in self.roads.values() for a, b in zip(pts, pts[1:])]

        if not paint and (MAP_DIR / PICTURE).exists() and (MAP_DIR / WALKABLE).exists():
            self.native = pygame.image.load(str(MAP_DIR / PICTURE)).convert()
            self.mask = pygame.mask.from_surface(pygame.image.load(str(MAP_DIR / WALKABLE)))
        else:
            sil = self._land_silhouette(rng)
            self.mask = pygame.mask.from_surface(sil)
            native = pygame.Surface((MAP_W, MAP_H))
            self._paint_ocean(native, rng)
            self._islets(native, rng)
            self._shore(native, sil)
            land = self._paint_ground(sil, rng)
            native.blit(land, (0, 0))
            self._paint_lakes(native)
            self._paint_roads(native)
            self._paint_things(native, rng)
            self.native = native
        self.size = (MAP_W * SCALE, MAP_H * SCALE)
        # Where the waves twinkle: spots on the open sea.
        sea = random.Random(5)
        self.sparkles = []
        for _ in range(300):
            x, y = sea.randrange(8, MAP_W - 8), sea.randrange(8, MAP_H - 8)
            if not any(self.mask.get_at((x + dx, y + dy)) for dx in (-8, 0, 8) for dy in (-6, 0, 6)):
                self.sparkles.append((x * SCALE, y * SCALE, sea.uniform(0, 6.28)))

    def bake(self):
        """Writes the picture and the walkable mask to assets/map/."""
        MAP_DIR.mkdir(parents=True, exist_ok=True)
        pygame.image.save(self.native, str(MAP_DIR / PICTURE))
        pygame.image.save(self.mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)),
                          str(MAP_DIR / WALKABLE))

    # -- the picture ---------------------------------------------------------------

    def _land_silhouette(self, rng):
        sil = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        white = (255, 255, 255, 255)
        for x, y in NODES.values():
            pygame.draw.polygon(sil, white, _blob((x, y), 64, rng))
        for pts in self.roads.values():
            for a, b in zip(pts, pts[1:]):
                pygame.draw.line(sil, white, a, b, 62)
            for p in pts[1:-1]:
                pygame.draw.circle(sil, white, p, 31)
        for loop in LAND_LOOPS:
            pygame.draw.polygon(sil, white, [NODES[n] for n in loop])
        # A ragged coast: lumps grow out of it and coves bite into it (never near a road or a town).
        for _ in range(1400):
            x, y = rng.randrange(8, MAP_W - 8), rng.randrange(8, MAP_H - 8)
            here = sil.get_at((x, y))[3] > 0
            edge = any((sil.get_at((x + dx, y + dy))[3] > 0) != here for dx, dy in ((7, 0), (-7, 0), (0, 7), (0, -7)))
            if not edge:
                continue
            if here:
                if min(math.hypot(x - nx, y - ny) for nx, ny in NODES.values()) < 52:
                    continue
                if any(_seg_dist(x, y, a, b) < 28 for a, b in self.segments):
                    continue
                pygame.draw.circle(sil, (0, 0, 0, 0), (x, y), rng.randrange(3, 8))
            else:
                pygame.draw.circle(sil, white, (x, y), rng.randrange(3, 9))
        return sil

    def _paint_ocean(self, native, rng):
        native.fill(OCEAN)
        for _ in range(2600):
            x, y = rng.randrange(MAP_W), rng.randrange(MAP_H)
            pygame.draw.line(native, (58, 116, 190), (x, y), (x + rng.randrange(3, 8), y))
        for _ in range(700):
            x, y = rng.randrange(MAP_W), rng.randrange(MAP_H)
            pygame.draw.line(native, (36, 82, 150), (x, y), (x + rng.randrange(3, 7), y))

    def _islets(self, native, rng):
        for x, y, r in ISLETS:
            pygame.draw.polygon(native, (200, 232, 250), _blob((x, y), r + 4, rng))
            pygame.draw.polygon(native, SAND, _blob((x, y), r + 1, rng))
            pygame.draw.polygon(native, (98, 172, 88), _blob((x, y), r - 3, rng))
            _palm(native, x, y + 2)
        for x, y in ((250, 40), (700, 560), (30, 330), (1380, 620), (840, 700), (1050, 150)):   # sailboats
            pygame.draw.polygon(native, INK, [(x - 5, y), (x + 5, y), (x + 3, y + 3), (x - 3, y + 3)])
            pygame.draw.polygon(native, (250, 250, 250), [(x, y - 9), (x, y - 1), (x + 5, y - 1)])
            pygame.draw.line(native, INK, (x, y - 10), (x, y))

    def _shore(self, native, sil):
        flat = sil.copy()
        foam = flat.copy()
        foam.fill((200, 232, 250, 255), special_flags=pygame.BLEND_RGBA_MIN)
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if 9 <= dx * dx + dy * dy <= 20:
                    native.blit(foam, (dx, dy))
        beach = flat.copy()
        beach.fill((*SAND, 255), special_flags=pygame.BLEND_RGBA_MIN)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            native.blit(beach, (dx, dy))

    def _paint_ground(self, sil, rng):
        """The land, region by region: each world's patch of ground (the cells nearest
        its town), with speckles, fields and hills."""
        land = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        land.fill((*GRASS, 255))
        land.blit(sil, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        names = list(NODES)
        big = [(-60, -60), (MAP_W + 60, -60), (MAP_W + 60, MAP_H + 60), (-60, MAP_H + 60)]
        for name in names:
            cx, cy = NODES[name]
            cell = big
            for other in names:
                if other == name:
                    continue
                ox, oy = NODES[other]
                cell = _clip_halfplane(cell, ((cx + ox) / 2, (cy + oy) / 2), (ox - cx, oy - cy))
            cell = _wobble(cell)
            color = BIOMES[name]["color"]
            layer = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
            pygame.draw.polygon(layer, (*color, 255), cell)
            pygame.draw.polygon(layer, (*color, 255), cell, 3)
            stripes = BIOMES[name].get("stripes")
            if stripes:
                tone, gap = stripes
                for yy in range(int(cy - 60), int(cy + 60), gap):
                    pygame.draw.line(layer, (*tone, 255), (cx - 60, yy), (cx + 60, yy), 2)
                round_off = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
                pygame.draw.circle(round_off, (255, 255, 255, 255), (cx, cy), 56)
                stripe_layer = layer.copy()
                stripe_layer.blit(round_off, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                layer = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
                pygame.draw.polygon(layer, (*color, 255), cell)
                pygame.draw.polygon(layer, (*color, 255), cell, 3)
                layer.blit(stripe_layer, (0, 0))
            layer.blit(sil, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            land.blit(layer, (0, 0))
            # Speckles of lighter and darker ground.
            for _ in range(220):
                x, y = rng.randrange(MAP_W), rng.randrange(MAP_H)
                if self._cell_of(x, y) != name or not self.mask.get_at((x, y)):
                    continue
                k = rng.choice((-14, -8, 10, 16))
                land.set_at((x, y), tuple(max(0, min(255, c + k)) for c in color) + (255,))
                land.set_at((x + 1, y), tuple(max(0, min(255, c + k)) for c in color) + (255,))
        return land

    def _cell_of(self, x, y):
        return min(NODES, key=lambda n: (NODES[n][0] - x) ** 2 + (NODES[n][1] - y) ** 2)

    def _paint_lakes(self, native):
        for x, y, rx, ry in LAKES:
            if any(_seg_dist(x, y, a, b) < max(rx, ry) + ROAD_HALF + 6 for a, b in self.segments):
                continue                                      # never over a road
            if any(math.hypot(x - nx, y - ny) < max(rx, ry) + 34 for nx, ny in NODES.values()):
                continue                                      # nor a town
            for grow, color in ((3, SAND), (0, (70, 140, 210))):
                pygame.draw.ellipse(native, color, (x - rx - grow, y - ry - grow, 2 * (rx + grow), 2 * (ry + grow)))
            pygame.draw.line(native, (120, 180, 236), (x - rx // 2, y - 3), (x, y - 3))
            pygame.draw.line(native, (120, 180, 236), (x, y + 4), (x + rx // 2, y + 4))
            for ly in range(y - ry, y + ry):                  # lakes are not land: no walking on water
                for lx in range(x - rx, x + rx):
                    if ((lx - x) / rx) ** 2 + ((ly - y) / ry) ** 2 <= 1:
                        self.mask.set_at((lx, ly), 0)

    def _paint_roads(self, native):
        for pts in self.roads.values():
            for width, color in ((ROAD_HALF * 2 - 4, ROAD_EDGE), (ROAD_HALF * 2 - 7, ROAD)):
                for a, b in zip(pts, pts[1:]):
                    pygame.draw.line(native, color, a, b, width)
                for p in pts[1:-1]:
                    pygame.draw.circle(native, color, p, width // 2)

    def _paint_things(self, native, rng):
        """Scatter, hills, plazas and landmarks, back to front."""
        things = []
        random.seed(77)             # the flower colours
        placed = list(NODES.values())

        def free(x, y, gap=8, road=ROAD_HALF + 5):
            if not (2 <= x < MAP_W - 2 and 2 <= y < MAP_H - 2) or not self.mask.get_at((x, y)):
                return False
            if any(math.hypot(x - px, y - py) < gap for px, py in placed):
                return False
            if any(math.hypot(x - nx, (y - ny) * 1.3) < 30 for nx, ny in NODES.values()):
                return False
            return not any(_seg_dist(x, y, a, b) < road for a, b in self.segments)

        # Hills first: a few clusters, away from the roads and the cities.
        for _ in range(900):
            if sum(1 for t in things if t[2] == "mountain") >= 26:
                break
            x, y = rng.randrange(MAP_W), rng.randrange(MAP_H)
            cell = self._cell_of(x, y)
            if cell in NO_MOUNTAINS or not free(x, y, gap=22, road=26):
                continue
            placed.append((x, y))
            things.append((y, "prop", "mountain", x, y))
        for _ in range(9000):
            if sum(1 for t in things if t[1] == "prop") >= 1500:
                break
            x, y = rng.randrange(MAP_W), rng.randrange(MAP_H)
            if not free(x, y):
                continue
            ranked = sorted(NODES, key=lambda n: (NODES[n][0] - x) ** 2 + (NODES[n][1] - y) ** 2)
            near, second = ranked[0], ranked[1]
            if math.hypot(NODES[second][0] - x, NODES[second][1] - y) - math.hypot(NODES[near][0] - x, NODES[near][1] - y) < 9:
                continue
            biome = BIOMES[near]
            if rng.random() > biome["n"] / 17:
                continue
            kinds = [k for k, w in biome["scatter"] for _ in range(w)]
            placed.append((x, y))
            things.append((y, "prop", rng.choice(kinds), x, y))
        for node, (cx, cy) in NODES.items():
            things.append((cy, "landmark", node, cx, cy))
        for _, what, name, x, y in sorted(things, key=lambda t: t[0]):
            if what == "prop":
                PROPS[name](native, x, y)
            else:
                pygame.draw.ellipse(native, INK, (x - 22, y - 8, 44, 17))
                pygame.draw.ellipse(native, (214, 208, 196), (x - 21, y - 7, 42, 15))
                pygame.draw.ellipse(native, (180, 174, 168), (x - 21, y - 7, 42, 15), 1)
                _shadow(native, x, y + 1, 12)
                LANDMARKS[name](native, x, y + 2)

    # -- walking -------------------------------------------------------------------

    def walkable(self, x, y):
        """Can the hero's feet stand at (x, y) in screen-sized world pixels?"""
        mx, my = int(x // SCALE), int(y // SCALE)
        return 0 <= mx < MAP_W and 0 <= my < MAP_H and bool(self.mask.get_at((mx, my)))

    def nearest(self, x, y):
        return min(self.nodes, key=lambda n: math.hypot(self.nodes[n][0] - x, self.nodes[n][1] - y))

    def route(self, x, y, target):
        """Waypoints (world pixels) from (x, y) along the roads to `target`."""
        start = self.nearest(x, y)
        prev = {start: None}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for nxt in self.neighbors[node]:
                if nxt not in prev:
                    prev[nxt] = node
                    queue.append(nxt)
        if target not in prev:
            return []
        chain = []
        node = target
        while node is not None:
            chain.append(node)
            node = prev[node]
        chain.reverse()
        points = [self.nodes[start]]
        for a, b in zip(chain, chain[1:]):
            road = self.roads.get((a, b)) or list(reversed(self.roads[(b, a)]))
            points += [(px * SCALE, py * SCALE) for px, py in road[1:]]
        return points


_cached = None


def build():
    global _cached
    if _cached is None:
        _cached = Overworld()
    return _cached

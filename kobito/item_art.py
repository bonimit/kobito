"""Small hand-drawn icons for every item in kobito/items.py, drawn with
pygame shapes in the same flat, dark-outlined style as the coins and
scenery -- no image files needed. get_icon(item_id, size) returns a
cached square surface.

Each draw function paints onto a 26x26 canvas; get_icon scales it up
with nearest-neighbour when a bigger icon is wanted (HUD, popups), so
the pixels stay crisp.
"""

import math

import pygame

CANVAS = 26
INK = (44, 30, 30)
WHITE = (250, 248, 240)

_cache = {}


def _rr(s, color, rect, radius=3, outline=True):
    pygame.draw.rect(s, color, rect, border_radius=radius)
    if outline:
        pygame.draw.rect(s, INK, rect, width=2, border_radius=radius)


def _can(s, body, band, mark_color, x=8, w=10):
    _rr(s, body, (x, 5, w, 18), 3)
    pygame.draw.rect(s, band, (x + 1, 11, w - 2, 5))
    pygame.draw.rect(s, (200, 204, 212), (x + 1, 3, w - 2, 3))
    pygame.draw.rect(s, INK, (x + 1, 3, w - 2, 3), width=1)
    return mark_color


def _energy_drink(s):
    _can(s, (70, 130, 220), (250, 220, 70), None)
    pygame.draw.polygon(s, (255, 236, 90), [(14, 8), (10, 15), (13, 15), (11, 21), (17, 13), (14, 13), (16, 8)])


def _mega_can(s):
    _can(s, (36, 40, 40), (36, 40, 40), None, x=6, w=14)
    for dx in (0, 4, 8):
        pygame.draw.line(s, (120, 230, 90), (9 + dx, 8), (8 + dx, 20), 2)


def _ume_soda(s):
    pygame.draw.rect(s, (200, 220, 230), (11, 2, 4, 6))
    pygame.draw.rect(s, INK, (11, 2, 4, 6), width=1)
    _rr(s, (232, 130, 170), (7, 8, 12, 16), 5)
    pygame.draw.circle(s, (150, 40, 90), (13, 17), 3)
    pygame.draw.circle(s, WHITE, (12, 16), 1)


def _candy(s):
    pygame.draw.polygon(s, (255, 130, 170), [(2, 7), (8, 13), (2, 19)])
    pygame.draw.polygon(s, (255, 130, 170), [(24, 7), (18, 13), (24, 19)])
    pygame.draw.ellipse(s, (255, 110, 150), (6, 7, 14, 12))
    pygame.draw.ellipse(s, INK, (6, 7, 14, 12), width=2)
    pygame.draw.arc(s, WHITE, (8, 9, 10, 8), 0.5, 2.6, 2)


def _onigiri(s):
    pts = [(13, 3), (3, 22), (23, 22)]
    pygame.draw.polygon(s, WHITE, pts)
    pygame.draw.polygon(s, INK, pts, width=2)
    pygame.draw.rect(s, (36, 50, 40), (9, 14, 8, 8))


def _canned_coffee(s):
    _can(s, (150, 90, 50), (236, 220, 190), None)
    pygame.draw.circle(s, (110, 60, 30), (13, 13), 3)
    pygame.draw.line(s, (110, 60, 30), (13, 6), (13, 7), 1)


def _melon_pan(s):
    pygame.draw.ellipse(s, (230, 190, 90), (3, 6, 20, 16))
    clip = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    for i in range(-3, 4):
        pygame.draw.line(clip, (190, 140, 50), (13 + i * 4 - 8, 6), (13 + i * 4 + 8, 22), 1)
        pygame.draw.line(clip, (190, 140, 50), (13 + i * 4 + 8, 6), (13 + i * 4 - 8, 22), 1)
    mask = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), (4, 7, 18, 14))
    clip.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(clip, (0, 0))
    pygame.draw.ellipse(s, INK, (3, 6, 20, 16), width=2)


def _green_tea(s):
    pygame.draw.rect(s, (40, 130, 70), (11, 2, 4, 5))
    _rr(s, (90, 180, 100), (7, 7, 12, 17), 4)
    pygame.draw.rect(s, WHITE, (9, 12, 8, 7))
    pygame.draw.circle(s, (40, 130, 70), (13, 15), 2)


def _lucky_bag(s):
    pygame.draw.ellipse(s, (200, 40, 50), (3, 8, 20, 17))
    pygame.draw.ellipse(s, INK, (3, 8, 20, 17), width=2)
    pygame.draw.polygon(s, (200, 40, 50), [(9, 9), (17, 9), (21, 2), (5, 2)])
    pygame.draw.polygon(s, INK, [(9, 9), (17, 9), (21, 2), (5, 2)], width=2)
    pygame.draw.rect(s, (250, 210, 70), (8, 8, 10, 3))
    pygame.draw.circle(s, (250, 210, 70), (13, 17), 4)


def _golden_can(s):
    _can(s, (250, 200, 50), (255, 236, 130), None)
    pygame.draw.polygon(s, WHITE, [(14, 8), (10, 15), (13, 15), (11, 21), (17, 13), (14, 13), (16, 8)])
    for x, y in ((3, 4), (22, 7), (4, 20)):
        pygame.draw.polygon(s, (255, 244, 170), [(x, y - 3), (x + 1, y - 1), (x + 3, y), (x + 1, y + 1), (x, y + 3), (x - 1, y + 1), (x - 3, y), (x - 1, y - 1)])


def _yuzu(s):
    pygame.draw.circle(s, (250, 210, 60), (13, 15), 9)
    pygame.draw.circle(s, INK, (13, 15), 9, width=2)
    pygame.draw.circle(s, (210, 160, 30), (13, 8), 2)
    pygame.draw.ellipse(s, (80, 170, 80), (13, 2, 9, 5))
    pygame.draw.arc(s, (255, 240, 150), (7, 9, 8, 8), 2.4, 4.0, 2)


def _watermelon(s):
    pygame.draw.polygon(s, (80, 170, 80), [(2, 9), (24, 9), (13, 24)])
    pygame.draw.polygon(s, (236, 70, 80), [(4, 9), (22, 9), (13, 21)])
    pygame.draw.polygon(s, INK, [(2, 9), (24, 9), (13, 24)], width=2)
    for x, y in ((9, 12), (13, 14), (17, 12)):
        pygame.draw.ellipse(s, (36, 30, 30), (x - 1, y - 1, 3, 4))


def _leaf(s):
    pts = [(3, 22), (6, 8), (16, 3), (23, 4), (22, 14), (12, 22)]
    pygame.draw.polygon(s, (90, 190, 90), pts)
    pygame.draw.polygon(s, INK, pts, width=2)
    pygame.draw.line(s, (40, 120, 50), (5, 21), (19, 7), 2)


def _hibiscus(s):
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        pygame.draw.circle(s, (240, 70, 90), (13 + math.cos(a) * 6, 13 + math.sin(a) * 6), 5)
    pygame.draw.circle(s, (255, 214, 100), (13, 13), 3)
    pygame.draw.circle(s, INK, (13, 13), 3, width=1)


def _inari(s):
    pygame.draw.ellipse(s, (200, 130, 50), (2, 8, 22, 15))
    pygame.draw.ellipse(s, INK, (2, 8, 22, 15), width=2)
    pygame.draw.ellipse(s, (250, 246, 230), (8, 6, 10, 7))
    pygame.draw.ellipse(s, INK, (8, 6, 10, 7), width=1)


def _aburaage(s):
    _rr(s, (214, 150, 60), (3, 6, 20, 15), 5)
    for x, y in ((8, 11), (14, 9), (17, 15), (10, 16)):
        pygame.draw.circle(s, (240, 190, 100), (x, y), 2)


def _sweet_potato(s):
    pygame.draw.ellipse(s, (150, 70, 130), (2, 8, 22, 12))
    pygame.draw.ellipse(s, INK, (2, 8, 22, 12), width=2)
    pygame.draw.ellipse(s, (250, 210, 90), (18, 9, 5, 10))


def _grass(s):
    for x, top in ((6, 9), (10, 4), (14, 7), (18, 3), (21, 10)):
        pygame.draw.line(s, INK, (x, 24), (x + (x - 13) // 4, top), 4)
        pygame.draw.line(s, (80, 180, 70), (x, 24), (x + (x - 13) // 4, top), 2)


def _clam(s):
    pygame.draw.ellipse(s, (230, 200, 160), (2, 6, 22, 16))
    pygame.draw.ellipse(s, INK, (2, 6, 22, 16), width=2)
    for dx in (-6, -3, 0, 3, 6):
        pygame.draw.line(s, (170, 130, 90), (13, 20), (13 + dx * 1.4, 9), 1)


def _fish(s):
    pygame.draw.polygon(s, (90, 160, 230), [(17, 12), (23, 6), (23, 18)])
    pygame.draw.polygon(s, INK, [(17, 12), (23, 6), (23, 18)], width=2)
    pygame.draw.ellipse(s, (90, 160, 230), (2, 7, 17, 11))
    pygame.draw.ellipse(s, INK, (2, 7, 17, 11), width=2)
    pygame.draw.circle(s, WHITE, (7, 11), 2)
    pygame.draw.circle(s, INK, (7, 11), 1)


def _tuna(s):
    _rr(s, (200, 204, 212), (3, 8, 20, 14), 3)
    pygame.draw.ellipse(s, (236, 110, 120), (6, 11, 14, 8))
    pygame.draw.rect(s, (60, 100, 200), (3, 8, 20, 3))


def _milk(s):
    pygame.draw.rect(s, (70, 130, 220), (10, 2, 6, 4))
    _rr(s, WHITE, (7, 6, 12, 17), 3)
    pygame.draw.rect(s, (110, 170, 240), (9, 12, 8, 6))


def _bone(s):
    pygame.draw.line(s, INK, (7, 17), (19, 9), 8)
    pygame.draw.line(s, WHITE, (7, 17), (19, 9), 5)
    for x, y in ((5, 15), (7, 20), (19, 6), (21, 11)):
        pygame.draw.circle(s, INK, (x, y), 4)
        pygame.draw.circle(s, WHITE, (x, y), 3)


def _sausage(s):
    pygame.draw.line(s, INK, (6, 18), (19, 9), 9)
    pygame.draw.line(s, (200, 80, 60), (6, 18), (19, 9), 6)
    pygame.draw.line(s, (240, 140, 110), (8, 14), (15, 10), 2)


def _gummy(s):
    body, shine = (236, 70, 90), (255, 170, 180)
    for cx, cy, r in ((8, 6, 4), (18, 6, 4)):                  # ears
        pygame.draw.circle(s, INK, (cx, cy), r + 1)
        pygame.draw.circle(s, body, (cx, cy), r)
    pygame.draw.ellipse(s, INK, (4, 15, 18, 10))                  # belly
    pygame.draw.ellipse(s, body, (5, 16, 16, 8))
    pygame.draw.circle(s, INK, (13, 11), 8)                       # head
    pygame.draw.circle(s, body, (13, 11), 7)
    pygame.draw.circle(s, INK, (11, 10), 1)
    pygame.draw.circle(s, INK, (15, 10), 1)
    pygame.draw.circle(s, shine, (10, 8), 2)


def _dried_ume(s):
    pygame.draw.circle(s, INK, (13, 14), 10)
    pygame.draw.circle(s, (150, 52, 70), (13, 14), 9)
    for pts in (((7, 12), (11, 14), (9, 18)), ((15, 8), (17, 13), (14, 17)), ((10, 20), (15, 21), (19, 18))):
        pygame.draw.lines(s, (96, 28, 46), False, pts, 1)
    pygame.draw.circle(s, (205, 110, 120), (9, 10), 2)
    pygame.draw.line(s, INK, (13, 5), (15, 2), 2)
    pygame.draw.ellipse(s, (90, 170, 90), (14, 1, 8, 4))


def _nuts(s):
    # an almond and a peanut, side by side
    pygame.draw.ellipse(s, INK, (2, 9, 12, 16))
    pygame.draw.ellipse(s, (190, 130, 70), (3, 10, 10, 14))
    pygame.draw.line(s, (150, 96, 50), (8, 12), (8, 22), 1)
    for cy in (9, 16):                                            # peanut: two joined lobes
        pygame.draw.circle(s, INK, (19, cy), 6)
    for cy in (9, 16):
        pygame.draw.circle(s, (226, 184, 120), (19, cy), 5)
    for cy in (7, 11, 14, 18):
        pygame.draw.circle(s, (190, 146, 90), (18 + (cy % 3), cy), 1)


def _ekiben(s):
    # a bento box seen from above, its lid slid half off
    _rr(s, (180, 60, 50), (2, 7, 22, 16), 3)
    pygame.draw.rect(s, WHITE, (4, 9, 9, 12))
    for x, y in ((6, 12), (9, 15), (6, 18)):
        pygame.draw.circle(s, (30, 30, 30), (x, y), 1)        # sesame
    pygame.draw.circle(s, (220, 50, 70), (9, 11), 2)          # umeboshi
    pygame.draw.rect(s, (250, 200, 80), (14, 9, 8, 5))         # tamagoyaki
    pygame.draw.rect(s, (110, 180, 80), (14, 15, 8, 6))        # greens
    pygame.draw.line(s, INK, (13, 9), (13, 21), 1)
    _rr(s, (220, 170, 90), (4, 2, 20, 6), 2)                   # lid
    pygame.draw.line(s, (200, 40, 50), (14, 2), (14, 8), 2)    # string


def _pizza_bun(s):
    pygame.draw.ellipse(s, INK, (2, 6, 22, 18))
    pygame.draw.ellipse(s, (250, 236, 214), (3, 7, 20, 16))
    pygame.draw.ellipse(s, (232, 110, 50), (6, 7, 14, 9))      # orange pizza top
    for x, y in ((9, 10), (15, 9), (13, 13)):
        pygame.draw.circle(s, (200, 40, 40), (x, y), 2)         # pepperoni
    pygame.draw.circle(s, (120, 180, 90), (11, 13), 1)
    for x in (8, 13, 18):                                       # steam
        pygame.draw.arc(s, (200, 210, 230), (x - 2, 0, 4, 6), 1.6, 4.7, 1)


def _gem(s):
    top, mid, bottom = 5, 11, 23
    outline = [(7, top), (19, top), (24, mid), (13, bottom), (2, mid)]
    pygame.draw.polygon(s, (80, 200, 230), outline)
    pygame.draw.polygon(s, (150, 235, 250), [(7, top), (13, top), (10, mid), (2, mid)])
    pygame.draw.polygon(s, (40, 150, 200), [(13, bottom), (16, mid), (24, mid)])
    pygame.draw.line(s, (40, 150, 200), (2, mid), (24, mid), 1)
    pygame.draw.line(s, (40, 150, 200), (10, mid), (13, bottom), 1)
    pygame.draw.line(s, (40, 150, 200), (16, mid), (13, top), 1)
    pygame.draw.polygon(s, INK, outline, width=2)
    pygame.draw.polygon(s, WHITE, [(22, 1), (23, 3), (25, 4), (23, 5), (22, 7), (21, 5), (19, 4), (21, 3)])


def _kaminari_okoshi(s):
    # a block of puffed rice in a red wrapper with a lightning mark
    _rr(s, (232, 200, 140), (3, 6, 20, 16), 3)
    for x, y in ((7, 9), (12, 11), (17, 9), (9, 15), (15, 17), (19, 14), (6, 18)):
        pygame.draw.circle(s, (250, 232, 190), (x, y), 2)
        pygame.draw.circle(s, (196, 150, 90), (x + 1, y + 1), 1)
    pygame.draw.rect(s, (200, 40, 40), (10, 5, 6, 18))
    pygame.draw.rect(s, INK, (10, 5, 6, 18), width=1)
    pygame.draw.polygon(s, (255, 220, 70), [(14, 7), (11, 13), (13, 13), (12, 19), (15, 12), (13, 12)])


def _wataame(s):
    pygame.draw.line(s, (230, 210, 170), (13, 14), (13, 25), 3)
    pygame.draw.line(s, INK, (14, 15), (14, 25), 1)
    for x, y, r in ((9, 9, 7), (17, 9, 7), (13, 5, 6), (13, 12, 7)):
        pygame.draw.circle(s, INK, (x, y), r + 1)
    for x, y, r in ((9, 9, 7), (17, 9, 7), (13, 5, 6), (13, 12, 7)):
        pygame.draw.circle(s, (255, 170, 205), (x, y), r)
    for x, y in ((9, 6), (15, 4), (18, 10)):
        pygame.draw.circle(s, (255, 220, 236), (x, y), 2)


def _tsukimi_dango(s):
    # a pyramid of white dumplings on a little wooden stand (sanbo)
    pygame.draw.polygon(s, (200, 150, 90), [(3, 20), (23, 20), (21, 25), (5, 25)])
    pygame.draw.polygon(s, INK, [(3, 20), (23, 20), (21, 25), (5, 25)], width=1)
    for x, y in ((7, 16), (13, 16), (19, 16), (10, 10), (16, 10), (13, 4)):
        pygame.draw.circle(s, INK, (x, y), 4)
        pygame.draw.circle(s, (252, 250, 240), (x, y), 3)
        pygame.draw.circle(s, WHITE, (x - 1, y - 1), 1)


def _sunflower(s):
    pygame.draw.line(s, INK, (13, 16), (13, 25), 4)                     # stem
    pygame.draw.line(s, (80, 170, 70), (13, 16), (13, 25), 2)
    pygame.draw.ellipse(s, INK, (14, 18, 9, 6))                          # leaf
    pygame.draw.ellipse(s, (100, 190, 80), (15, 19, 7, 4))
    for i in range(10):                                                  # petals
        a = i * math.pi / 5
        cx, cy = 13 + math.cos(a) * 7, 10 + math.sin(a) * 7
        pygame.draw.circle(s, INK, (round(cx), round(cy)), 4)
    for i in range(10):
        a = i * math.pi / 5
        cx, cy = 13 + math.cos(a) * 7, 10 + math.sin(a) * 7
        pygame.draw.circle(s, (255, 206, 40), (round(cx), round(cy)), 3)
    pygame.draw.circle(s, INK, (13, 10), 6)
    pygame.draw.circle(s, (130, 80, 40), (13, 10), 5)                    # seed face
    for x, y in ((11, 8), (15, 9), (12, 12), (14, 11)):
        pygame.draw.circle(s, (90, 50, 24), (x, y), 1)


def _protein_bar(s):
    # a chunky bar in a foil wrapper, torn open at one end
    _rr(s, (60, 70, 150), (2, 8, 22, 11), 2)
    pygame.draw.rect(s, (150, 96, 60), (17, 9, 6, 9))                # the bar peeking out
    pygame.draw.line(s, (110, 66, 40), (19, 10), (19, 16), 1)
    pygame.draw.line(s, INK, (17, 8), (17, 18), 2)
    pygame.draw.rect(s, (255, 170, 60), (4, 11, 11, 5))              # label band
    pygame.draw.circle(s, INK, (9, 13), 3)                           # a little flexed-arm mark
    pygame.draw.circle(s, WHITE, (9, 13), 2)


def _elixir(s):
    # a round potion flask, glowing violet, with a cork
    pygame.draw.rect(s, (190, 150, 100), (10, 1, 6, 5))
    pygame.draw.rect(s, INK, (10, 1, 6, 5), width=1)
    pygame.draw.rect(s, (200, 220, 236), (10, 5, 6, 5))
    pygame.draw.rect(s, INK, (10, 5, 6, 5), width=1)
    pygame.draw.circle(s, INK, (13, 17), 9)
    pygame.draw.circle(s, (200, 220, 236), (13, 17), 8)
    pygame.draw.circle(s, (170, 90, 230), (13, 18), 7)
    pygame.draw.circle(s, (220, 170, 255), (11, 16), 3)
    pygame.draw.circle(s, WHITE, (10, 14), 1)
    for x, y in ((3, 6), (23, 9), (22, 3)):
        pygame.draw.polygon(s, (255, 236, 150), [(x, y - 2), (x + 1, y), (x, y + 2), (x - 1, y)])


def _maneki_neko(s):
    # the beckoning cat: white, one paw up, red collar and a gold coin
    pygame.draw.ellipse(s, INK, (4, 10, 18, 15))
    pygame.draw.ellipse(s, WHITE, (5, 11, 16, 13))                   # body
    pygame.draw.circle(s, INK, (13, 9), 7)
    pygame.draw.circle(s, WHITE, (13, 9), 6)                         # head
    for ear in ([(7, 6), (8, 1), (11, 4)], [(19, 6), (18, 1), (15, 4)]):
        pygame.draw.polygon(s, WHITE, ear)
        pygame.draw.polygon(s, INK, ear, width=1)
    pygame.draw.ellipse(s, INK, (19, 1, 6, 9))                       # raised paw
    pygame.draw.ellipse(s, WHITE, (20, 2, 4, 7))
    pygame.draw.circle(s, INK, (11, 9), 1)
    pygame.draw.circle(s, INK, (15, 9), 1)
    pygame.draw.line(s, (220, 50, 60), (8, 14), (18, 14), 2)         # collar
    pygame.draw.circle(s, INK, (13, 19), 4)
    pygame.draw.circle(s, (250, 210, 70), (13, 19), 3)               # koban coin


DRAWERS = {
    "energy_drink": _energy_drink, "mega_can": _mega_can, "ume_soda": _ume_soda, "candy": _candy,
    "onigiri": _onigiri, "gummy": _gummy, "dried_ume": _dried_ume, "nuts": _nuts, "canned_coffee": _canned_coffee, "melon_pan": _melon_pan, "green_tea": _green_tea,
    "protein_bar": _protein_bar,
    "lucky_bag": _lucky_bag, "golden_can": _golden_can, "elixir": _elixir, "maneki_neko": _maneki_neko,
    "sunflower": _sunflower,
    "ekiben": _ekiben, "pizza_bun": _pizza_bun, "gem": _gem,
    "kaminari_okoshi": _kaminari_okoshi, "wataame": _wataame, "tsukimi_dango": _tsukimi_dango,
    "yuzu": _yuzu, "watermelon": _watermelon, "leaf": _leaf, "hibiscus": _hibiscus, "inari": _inari,
    "aburaage": _aburaage, "sweet_potato": _sweet_potato, "grass": _grass, "clam": _clam, "fish": _fish,
    "tuna": _tuna, "milk": _milk, "bone": _bone, "sausage": _sausage,
}


def get_icon(item_id, size=24):
    key = (item_id, size)
    if key not in _cache:
        canvas = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
        DRAWERS[item_id](canvas)
        _cache[key] = canvas if size == CANVAS else pygame.transform.scale(canvas, (size, size))
    return _cache[key]

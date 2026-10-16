"""Small hand-drawn icons for every item in kobito/items.py, drawn with
pygame shapes in the same flat, dark-outlined style as the coins and
scenery -- no image files needed. get_icon(item_id, size) returns a
cached square surface.

Each draw function paints onto a 26x26 canvas; get_icon scales it up
with nearest-neighbour when a bigger icon is wanted (HUD, popups), so
the pixels stay crisp.
"""

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
    import math
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


DRAWERS = {
    "energy_drink": _energy_drink, "mega_can": _mega_can, "ume_soda": _ume_soda, "candy": _candy,
    "onigiri": _onigiri, "canned_coffee": _canned_coffee, "melon_pan": _melon_pan, "green_tea": _green_tea,
    "lucky_bag": _lucky_bag, "golden_can": _golden_can,
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

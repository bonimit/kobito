"""Draws costumes and accessories (kobito/wardrobe.py) onto the mascot, and
the icons for the house and the konbini.

Everything is drawn with plain pygame shapes at the sprites' own pixel
scale (a mascot is 48 px tall), so it matches the pixel art; icons are
the same drawings scaled up with hard edges.

dress() puts the worn gear on one animation frame. Mascots face right in
their frames. The head is found per frame from the pixels themselves --
the highest part of the silhouette, ignoring the back quarter where tails
are -- so a hat follows the head through the run cycle; each mascot's
ANCHOR says where its back is. Back items are drawn behind the mascot,
head items in front.
"""

import math

import pygame

from kobito import item_art, wardrobe

PAD_X = 20      # extra room either side of a dressed frame (capes, wings, poles)
PAD_TOP = 26    # ...and above it (hats, koinobori)

OUTLINE = (34, 22, 30)

# Per mascot, as fractions of the frame (facing right): where its back is.
ANCHORS = {
    "capybara": (0.28, 0.34),
    "sloth": (0.30, 0.40),
    "kitsune": (0.30, 0.46),
    "wombat": (0.28, 0.34),
    "otter": (0.30, 0.50),
    "scottish_fold": (0.28, 0.48),
    "frenchie": (0.32, 0.55),
}
DEFAULT_ANCHOR = (0.3, 0.45)
HEAD_ROWS = 8          # the head is the silhouette's top this many rows
TAIL_ZONE = 0.25       # ...left of this fraction of the frame is tail, not head

_cache = {}


def _head_x(frame):
    """The middle of the top of the silhouette (outside the tail zone)."""
    w, h = frame.get_size()
    x0 = int(w * TAIL_ZONE)
    top = next((y for y in range(h) if any(frame.get_at((x, y)).a > 40 for x in range(x0, w))), 0)
    xs = [x for y in range(top, min(h, top + HEAD_ROWS)) for x in range(x0, w) if frame.get_at((x, y)).a > 40]
    return round(sum(xs) / len(xs)) if xs else w // 2


def _head_top(frame, x):
    """The highest opaque pixel within a few columns of x."""
    w, h = frame.get_size()
    tops = []
    for cx in range(max(0, x - 3), min(w, x + 4)):
        for y in range(h):
            if frame.get_at((cx, y)).a > 40:
                tops.append(y)
                break
    return min(tops) if tops else h // 3


def anchors(frame, character_id):
    """((head x, head top), (back x, back y)) in frame pixels, facing right."""
    key = ("anchor", id(frame), character_id)
    if key not in _cache:
        w, h = frame.get_size()
        bx, by = ANCHORS.get(character_id, DEFAULT_ANCHOR)
        head_x = _head_x(frame)
        _cache[key] = ((head_x, _head_top(frame, head_x)), (round(bx * w), round(by * h)))
    return _cache[key]


def dress(frame, character_id, worn, t=0.0, moving=False):
    """`frame` (facing right) wearing the gear in `worn`, on a canvas
    PAD_X wider each side and PAD_TOP taller, bottom-aligned. Returns the
    frame itself when nothing is worn."""
    if not worn:
        return frame
    phase = int(t * 12) % 8
    key = (id(frame), character_id, tuple(worn), phase, moving)
    surf = _cache.get(key)
    if surf is not None:
        return surf
    w, h = frame.get_size()
    surf = pygame.Surface((w + 2 * PAD_X, h + PAD_TOP), pygame.SRCALPHA)
    (hx, hy), (bx, by) = anchors(frame, character_id)
    head = (hx + PAD_X, hy + PAD_TOP)
    back = (bx + PAD_X, by + PAD_TOP)
    gear = [wardrobe.GEAR[g] for g in worn]
    for g in gear:
        if g.slot == wardrobe.BACK:
            BACK_ART[g.id](surf, back, phase, moving)
    surf.blit(frame, (PAD_X, PAD_TOP))
    for g in gear:
        if g.slot == wardrobe.HEAD:
            HEAD_ART[g.id](surf, head, phase, moving)
    if len(_cache) > 4000:
        _cache.clear()
    _cache[key] = surf
    return surf


# -- Head items (anchor: centre-top of the head) ----------------------------------

def _outline_poly(s, color, points, width=1):
    pygame.draw.polygon(s, color, points)
    pygame.draw.polygon(s, OUTLINE, points, width)


def _hachimaki(s, a, phase, moving):
    x, y = a
    y += 2
    band = pygame.Rect(x - 12, y + 4, 24, 4)
    pygame.draw.rect(s, OUTLINE, band.inflate(2, 2))
    pygame.draw.rect(s, (250, 248, 240), band)
    pygame.draw.circle(s, (220, 40, 50), (x + 5, y + 6), 2)
    wave = (phase % 4) - 1.5 if moving else 0
    for dy in (0, 3):
        tail = [(x - 12, y + 5), (x - 19, y + 3 + dy + wave), (x - 18, y + 6 + dy + wave)]
        _outline_poly(s, (250, 248, 240), tail)


def _straw_hat(s, a, phase, moving):
    x, y = a
    straw, dark = (238, 200, 112), (176, 132, 60)
    crown = pygame.Rect(x - 9, y - 7, 18, 10)
    pygame.draw.rect(s, OUTLINE, crown.inflate(2, 2), border_radius=5)
    pygame.draw.rect(s, straw, crown, border_radius=4)
    pygame.draw.rect(s, (210, 50, 50), (x - 9, y, 18, 3))
    brim = pygame.Rect(x - 18, y + 1, 36, 7)
    pygame.draw.ellipse(s, OUTLINE, brim.inflate(2, 2))
    pygame.draw.ellipse(s, straw, brim)
    pygame.draw.ellipse(s, dark, brim, 1)
    for k in range(-14, 15, 5):
        s.set_at((x + k, y + 4), dark)


def _kabuto(s, a, phase, moving):
    x, y = a
    y += 3
    iron, rim = (52, 62, 104), (90, 104, 160)
    pygame.draw.circle(s, OUTLINE, (x, y + 6), 14, draw_top_left=True, draw_top_right=True)
    pygame.draw.circle(s, iron, (x, y + 6), 13, draw_top_left=True, draw_top_right=True)
    pygame.draw.line(s, rim, (x - 10, y - 1), (x + 10, y - 1))
    pygame.draw.rect(s, OUTLINE, (x - 15, y + 5, 30, 4))
    pygame.draw.rect(s, rim, (x - 14, y + 6, 28, 2))
    # Flared side guards and the golden horns (kuwagata).
    _outline_poly(s, iron, [(x - 15, y + 5), (x - 19, y + 1), (x - 18, y + 8)])
    _outline_poly(s, iron, [(x + 15, y + 5), (x + 19, y + 1), (x + 18, y + 8)])
    gold = (250, 200, 60)
    for side in (-1, 1):
        pygame.draw.line(s, OUTLINE, (x, y - 2), (x + side * 9, y - 14), 4)
        pygame.draw.line(s, gold, (x, y - 2), (x + side * 9, y - 14), 2)
    pygame.draw.circle(s, OUTLINE, (x, y - 2), 3)
    pygame.draw.circle(s, gold, (x, y - 2), 2)


def _fox_mask(s, a, phase, moving):
    x, y = a
    cx, cy = x - 10, y + 6     # worn on the back of the head, turned sideways
    face = pygame.Rect(cx - 6, cy - 7, 12, 15)
    for ear in (-1, 1):
        _outline_poly(s, (252, 250, 245), [(cx + ear * 2, cy - 5), (cx + ear * 6, cy - 12), (cx + ear * 6, cy - 3)])
    pygame.draw.ellipse(s, OUTLINE, face.inflate(2, 2))
    pygame.draw.ellipse(s, (252, 250, 245), face)
    red = (220, 50, 60)
    pygame.draw.line(s, red, (cx - 4, cy - 2), (cx - 1, cy), 1)
    pygame.draw.line(s, red, (cx + 4, cy - 2), (cx + 1, cy), 1)
    pygame.draw.line(s, red, (cx, cy - 6), (cx, cy - 4), 1)
    s.set_at((cx, cy + 5), OUTLINE)
    pygame.draw.line(s, red, (cx - 2, cy + 3), (cx + 2, cy + 3), 1)
    pygame.draw.line(s, (200, 60, 70), (cx + 5, cy - 2), (x + 8, y + 2), 1)   # the string


def _grad_cap(s, a, phase, moving):
    x, y = a
    black, edge = (34, 34, 44), (70, 70, 90)
    base = pygame.Rect(x - 8, y - 1, 16, 7)
    pygame.draw.rect(s, OUTLINE, base.inflate(2, 2))
    pygame.draw.rect(s, black, base)
    board = [(x - 16, y - 2), (x, y - 7), (x + 16, y - 2), (x, y + 3)]
    _outline_poly(s, black, board)
    pygame.draw.line(s, edge, (x - 13, y - 2), (x, y - 6))
    swing = 1 if moving and phase % 4 < 2 else 0
    gold = (250, 200, 60)
    pygame.draw.line(s, gold, (x, y - 2), (x + 11, y + 1), 1)
    pygame.draw.line(s, gold, (x + 11, y + 1), (x + 11 + swing, y + 8), 2)
    pygame.draw.rect(s, gold, (x + 10 + swing, y + 8, 3, 3))
    pygame.draw.circle(s, gold, (x, y - 2), 1)


def _crown(s, a, phase, moving):
    x, y = a
    gold, light = (250, 196, 50), (255, 236, 140)
    points = [(x - 11, y + 5), (x - 11, y - 5), (x - 6, y), (x, y - 9), (x + 6, y), (x + 11, y - 5), (x + 11, y + 5)]
    _outline_poly(s, gold, points)
    pygame.draw.line(s, light, (x - 10, y + 3), (x + 10, y + 3))
    for jx, color in ((-6, (90, 160, 250)), (0, (230, 50, 70)), (6, (90, 200, 120))):
        pygame.draw.circle(s, color, (x + jx, y + 2), 1)
    for px in (-11, 0, 11):
        top = y - 9 if px == 0 else y - 5
        pygame.draw.circle(s, light, (x + px, top), 1)


def _propeller(s, a, phase, moving):
    x, y = a
    colors = ((230, 60, 60), (250, 210, 60), (70, 140, 230), (250, 210, 60))
    pygame.draw.circle(s, OUTLINE, (x, y + 4), 12, draw_top_left=True, draw_top_right=True)
    for k in range(4):
        pygame.draw.circle(s, colors[k], (x, y + 4), 11 - k * 2, draw_top_left=True, draw_top_right=True)
    pygame.draw.line(s, OUTLINE, (x - 12, y + 4), (x + 12, y + 4))
    pygame.draw.line(s, (120, 120, 140), (x, y - 4), (x, y - 8), 2)
    # The blades spin: drawn foreshortened by the angle.
    angle = phase * math.pi / 4
    length = max(2, round(12 * abs(math.cos(angle))))
    pygame.draw.line(s, OUTLINE, (x - length - 1, y - 9), (x + length + 1, y - 9), 4)
    pygame.draw.line(s, (240, 70, 70), (x - length, y - 9), (x, y - 9), 2)
    pygame.draw.line(s, (60, 150, 240), (x, y - 9), (x + length, y - 9), 2)
    pygame.draw.circle(s, (250, 210, 60), (x, y - 9), 2)


HEAD_ART = {"hachimaki": _hachimaki, "straw_hat": _straw_hat, "kabuto": _kabuto, "fox_mask": _fox_mask,
            "grad_cap": _grad_cap, "crown": _crown, "propeller": _propeller}


# -- Back items (anchor: the top of the back) --------------------------------------

def _randoseru(s, a, phase, moving):
    x, y = a
    bag = pygame.Rect(x - 9, y - 4, 12, 16)
    pygame.draw.rect(s, OUTLINE, bag.inflate(2, 2), border_radius=4)
    pygame.draw.rect(s, (200, 40, 50), bag, border_radius=3)
    pygame.draw.rect(s, (160, 26, 36), (bag.x, bag.y, bag.width, 9), border_top_left_radius=3,
                     border_top_right_radius=3)
    pygame.draw.rect(s, (250, 200, 60), (bag.centerx - 1, bag.y + 8, 3, 3))
    pygame.draw.line(s, (120, 20, 30), (bag.right, bag.y + 2), (bag.right + 3, bag.y + 8), 2)


def _cape(s, a, phase, moving):
    x, y = a
    flutter = [0, 2, 3, 2, 0, -1, -2, -1][phase] if moving else 0
    reach = 16 if moving else 8
    points = [(x + 6, y - 4), (x - 2, y - 5), (x - reach, y + 10 + flutter), (x - reach + 3, y + 22 + flutter),
              (x + 4, y + 14)]
    _outline_poly(s, (210, 40, 60), points)
    pygame.draw.line(s, (150, 24, 40), (x - 2, y - 2), (x - reach + 4, y + 18 + flutter))
    pygame.draw.circle(s, (250, 200, 60), (x + 5, y - 4), 2)


def _koinobori(s, a, phase, moving):
    x, y = a
    pole_top = y - 30
    pygame.draw.line(s, OUTLINE, (x, y + 4), (x, pole_top), 3)
    pygame.draw.line(s, (200, 170, 110), (x, y + 4), (x, pole_top), 1)
    pygame.draw.circle(s, (250, 210, 60), (x, pole_top), 2)
    wave = [0, 1, 2, 1, 0, -1, -2, -1]
    for k, (color, belly) in enumerate((((50, 90, 200), (210, 230, 255)), ((220, 50, 60), (255, 220, 220)))):
        top = pole_top + 3 + k * 9
        w = wave[(phase + k * 2) % 8]
        body = [(x, top), (x - 16, top + w), (x - 20, top - 2 + w), (x - 18, top + 3 + w), (x - 20, top + 7 + w),
                (x - 16, top + 5 + w), (x, top + 6)]
        _outline_poly(s, color, body)
        pygame.draw.line(s, belly, (x - 2, top + 4), (x - 14, top + 4 + w))
        s.set_at((x - 3, top + 2), (255, 255, 255))


def _tengu_wings(s, a, phase, moving):
    x, y = a
    beat = [0, -1, -2, -3, -2, -1, 0, 1][phase]
    for k, shade in ((0, (40, 36, 52)), (1, (64, 58, 82))):
        dx = -k * 3
        points = [(x + 2, y), (x - 12 + dx, y - 12 + beat), (x - 20 + dx, y - 8 + beat), (x - 16 + dx, y - 2 + beat),
                  (x - 20 + dx, y + 3 + beat), (x - 13 + dx, y + 4 + beat), (x - 15 + dx, y + 9), (x + 2, y + 6)]
        _outline_poly(s, shade, points)
    pygame.draw.line(s, (110, 100, 130), (x - 2, y + 1), (x - 15, y - 9 + beat))


def _furoshiki(s, a, phase, moving):
    x, y = a
    green, swirl = (40, 140, 90), (210, 240, 220)
    bundle = pygame.Rect(x - 12, y - 4, 16, 14)
    pygame.draw.ellipse(s, OUTLINE, bundle.inflate(2, 2))
    pygame.draw.ellipse(s, green, bundle)
    for cx, cy in ((x - 8, y + 1), (x - 3, y + 5), (x - 6, y + 7)):
        pygame.draw.circle(s, swirl, (cx, cy), 2, 1)
    _outline_poly(s, green, [(x - 1, y - 4), (x + 4, y - 8), (x + 3, y - 2)])
    _outline_poly(s, green, [(x - 1, y - 4), (x - 5, y - 9), (x - 6, y - 3)])


def _taiko(s, a, phase, moving):
    x, y = a
    body = pygame.Rect(x - 13, y - 5, 14, 17)
    pygame.draw.rect(s, OUTLINE, body.inflate(2, 2), border_radius=6)
    pygame.draw.rect(s, (170, 70, 40), body, border_radius=5)
    for k in range(3):
        pygame.draw.line(s, (120, 46, 28), (body.x + 2 + k * 5, body.y + 2), (body.x + 2 + k * 5, body.bottom - 3))
    face = pygame.Rect(body.x - 3, body.y + 1, 6, 15)
    pygame.draw.ellipse(s, OUTLINE, face.inflate(2, 2))
    pygame.draw.ellipse(s, (250, 236, 200), face)
    pygame.draw.circle(s, (220, 50, 50), face.center, 2)
    pygame.draw.line(s, (90, 50, 30), (body.right, body.y + 4), (body.right + 4, body.y - 3), 2)   # a drumstick


BACK_ART = {"randoseru": _randoseru, "cape": _cape, "koinobori": _koinobori, "tengu_wings": _tengu_wings,
            "furoshiki": _furoshiki, "taiko": _taiko}


# -- Icons -------------------------------------------------------------------------

def gear_icon(gear_id, size, t=0.0):
    """The piece of gear on its own, scaled up to roughly size x size."""
    key = ("icon", gear_id, size, int(t * 12) % 8)
    if key in _cache:
        return _cache[key]
    native = pygame.Surface((44, 44), pygame.SRCALPHA)
    gear = wardrobe.GEAR[gear_id]
    if gear.slot == wardrobe.HEAD:
        offsets = {"fox_mask": (32, 18), "propeller": (22, 24), "kabuto": (22, 26), "straw_hat": (22, 22)}
        if gear_id == "fox_mask":
            native = pygame.Surface((30, 30), pygame.SRCALPHA)   # no room for the string
            offsets["fox_mask"] = (25, 11)
        HEAD_ART[gear_id](native, offsets.get(gear_id, (22, 22)), int(t * 12) % 8, True)
    else:
        offsets = {"koinobori": (32, 36), "tengu_wings": (30, 22), "cape": (30, 14)}
        BACK_ART[gear_id](native, offsets.get(gear_id, (26, 18)), int(t * 12) % 8, True)
    box = native.get_bounding_rect()
    icon = _scale_to(native.subsurface(box) if box.width and box.height else native, size)
    _cache[key] = icon
    return icon


def _scale_to(piece, size):
    """Scaled up with hard pixel edges to fit size x size: a whole-number
    scale when that fills most of it, otherwise as big as fits."""
    longest = max(piece.get_width(), piece.get_height())
    scale = (size - 4) // longest
    if scale < 2 or scale * longest < size * 0.7:
        scale = (size - 4) / longest
    return pygame.transform.scale(piece, (max(1, round(piece.get_width() * scale)),
                                          max(1, round(piece.get_height() * scale))))


def product_icon(product_id, size):
    """A konbini product: its gear icon, or a drawn study book / boost."""
    if product_id in wardrobe.GEAR:
        return gear_icon(product_id, size)
    if product_id not in PRODUCT_ART:
        return item_art.get_icon(product_id, size)   # a konbini item sold as is
    key = ("product", product_id, size)
    if key in _cache:
        return _cache[key]
    native = pygame.Surface((24, 24), pygame.SRCALPHA)
    PRODUCT_ART[product_id](native)
    icon = _scale_to(native.subsurface(native.get_bounding_rect()), size)
    _cache[key] = icon
    return icon


def _book(s, cover, label_color, pages=(250, 246, 232), spiral=False, thick=3):
    rect = pygame.Rect(4, 2, 15, 20)
    pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2 + thick))
    pygame.draw.rect(s, pages, (rect.x + 1, rect.y + 2, rect.width, rect.height + thick - 2))
    pygame.draw.rect(s, cover, rect)
    pygame.draw.rect(s, label_color, (rect.x + 3, rect.y + 4, rect.width - 6, 5))
    if spiral:
        for k in range(rect.y + 2, rect.bottom - 1, 3):
            s.set_at((rect.x, k), (200, 200, 210))
            s.set_at((rect.x - 1, k), OUTLINE)


def _notebook(s):
    _book(s, (90, 160, 230), (250, 250, 250), spiral=True, thick=1)


def _flashcards(s):
    for k, color in enumerate(((250, 200, 90), (120, 200, 140), (250, 250, 250))):
        rect = pygame.Rect(3 + k * 2, 4 + k * 3, 16, 10)
        pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2))
        pygame.draw.rect(s, color, rect)
    pygame.draw.line(s, (220, 60, 60), (10, 13), (17, 13))
    pygame.draw.circle(s, (160, 160, 170), (6, 12), 1)


def _kanji_drill(s):
    _book(s, (240, 120, 50), (255, 240, 200))
    pygame.draw.line(s, OUTLINE, (9, 8), (14, 8))
    pygame.draw.line(s, OUTLINE, (11, 6), (11, 9))


def _textbook(s):
    _book(s, (60, 70, 140), (250, 200, 60), thick=5)
    pygame.draw.line(s, (250, 200, 60), (6, 16), (16, 16))


def _omamori(s):
    rect = pygame.Rect(6, 6, 12, 16)
    pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2), border_top_left_radius=5, border_top_right_radius=5)
    pygame.draw.rect(s, (220, 40, 60), rect, border_top_left_radius=4, border_top_right_radius=4)
    pygame.draw.rect(s, (250, 210, 80), (rect.x + 2, rect.y + 5, rect.width - 4, 7))
    pygame.draw.line(s, (250, 210, 80), (12, 6), (10, 1))
    pygame.draw.line(s, (250, 210, 80), (12, 6), (14, 1))


def _sun_seeds(s):
    rect = pygame.Rect(4, 3, 16, 19)
    pygame.draw.rect(s, OUTLINE, rect.inflate(2, 2), border_radius=2)
    pygame.draw.rect(s, (240, 230, 200), rect, border_radius=2)
    pygame.draw.circle(s, (250, 196, 40), (12, 12), 5)
    pygame.draw.circle(s, (120, 70, 30), (12, 12), 2)
    pygame.draw.line(s, (90, 160, 80), (4, 6), (20, 6))


def _eiyo_drink(s):
    bottle = pygame.Rect(8, 7, 9, 15)
    pygame.draw.rect(s, OUTLINE, bottle.inflate(2, 2), border_radius=3)
    pygame.draw.rect(s, (150, 80, 30), bottle, border_radius=3)
    pygame.draw.rect(s, OUTLINE, (10, 2, 5, 6))
    pygame.draw.rect(s, (250, 210, 60), (11, 3, 3, 4))
    pygame.draw.rect(s, (250, 240, 220), (bottle.x + 1, bottle.y + 5, bottle.width - 2, 5))
    pygame.draw.line(s, (220, 50, 50), (bottle.x + 2, bottle.y + 7), (bottle.right - 3, bottle.y + 7))


PRODUCT_ART = {"notebook": _notebook, "flashcards": _flashcards, "kanji_drill": _kanji_drill,
               "textbook": _textbook, "omamori": _omamori, "sun_seeds": _sun_seeds, "eiyo_drink": _eiyo_drink}

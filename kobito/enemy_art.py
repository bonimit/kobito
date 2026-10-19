"""Hand-drawn enemy designs -- several species, each with its own
silhouette and bold colours, a dark outline so it pops off any world, and
two animation frames (a walk / waddle / flap).

Ground species (walk the ground and platforms):
  * slime   -- a bouncy jelly blob with angry brows
  * oni     -- a little horned demon with fangs and a tiger-stripe belt
  * daruma  -- a round red daruma doll that wobbles as it rolls along
  * kappa   -- the river imp: green, beaked, with a water dish on its head
  * critter -- a plain round body in custom colours (the hidden rooms' rats,
               gators, moles, sheep, imps and rabbits)

Flying species (patrol up and down):
  * bat       -- flapping wings, red eyes
  * chochin   -- chōchin-obake, the paper-lantern ghost with one eye and a tongue
  * karakasa  -- karakasa-obake, the one-eyed umbrella ghost hopping on its handle

More species fit particular worlds (kobito/themes.py WORLD_ENEMIES picks
each world's lineup): crabs, squid and flying fish by the sea, scorpions
and snakes in the desert, tanuki, beetles, caterpillars and snails in the
countryside, snowmen in the snow, bulls on the farm, rats and crows in
the city, ghosts and thunderclouds, bees and jellyfish, ...

render_ground(species, frame, colors) / render_flying(...) return a surface
facing right; the entity flips it when walking left.
"""

import math

import pygame

INK = (26, 18, 24)
WHITE = (255, 255, 255)
GROUND_SIZE = (36, 34)
FLYING_SIZE = (38, 32)

GROUND_SPECIES = ("slime", "oni", "daruma", "kappa")
FLYING_SPECIES = ("bat", "chochin", "karakasa")

SLIME_COLORS = [(170, 80, 235), (60, 200, 230), (255, 120, 60), (240, 70, 150)]


def _outlined_ellipse(s, color, rect, width=2):
    rect = pygame.Rect(rect)
    pygame.draw.ellipse(s, INK, rect.inflate(width * 2, width * 2))
    pygame.draw.ellipse(s, color, rect)


def _eye(s, center, r=4, look=1, angry=False):
    x, y = center
    pygame.draw.circle(s, INK, (x, y), r + 1)
    pygame.draw.circle(s, WHITE, (x, y), r)
    pygame.draw.circle(s, INK, (x + look, y + 1), max(1, r // 2))
    if angry:
        pygame.draw.line(s, INK, (x - r, y - r - 2), (x + r, y - r + 1), 2)


def _shadow(s):
    w, h = s.get_size()
    pygame.draw.ellipse(s, (0, 0, 0, 70), (4, h - 5, w - 8, 5))


def _mix(color, other, t):
    return tuple(round(c + (o - c) * t) for c, o in zip(color, other))


# -- Ground ---------------------------------------------------------------------

def _slime(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or SLIME_COLORS[0]
    squash = 3 if frame else 0
    rect = pygame.Rect(4, 8 + squash, w - 8, h - 14 - squash)
    _outlined_ellipse(s, body, rect)
    pygame.draw.rect(s, body, (rect.x, rect.centery, rect.width, rect.height // 2 - 1))
    pygame.draw.line(s, INK, (rect.x - 1, rect.bottom - 1), (rect.right, rect.bottom - 1), 2)
    pygame.draw.ellipse(s, _mix(body, WHITE, 0.55), (rect.x + 5, rect.y + 3, 8, 5))   # shine
    for ex in (rect.centerx - 6, rect.centerx + 6):
        _eye(s, (ex, rect.centery - 1), r=3, angry=True)


def _oni(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (232, 72, 60)
    horn = (250, 236, 200)
    for hx in (12, w - 12):                                              # horns
        pygame.draw.polygon(s, INK, [(hx - 4, 12), (hx + 4, 12), (hx, 1)])
        pygame.draw.polygon(s, horn, [(hx - 2, 11), (hx + 2, 11), (hx, 4)])
    _outlined_ellipse(s, body, (5, 8, w - 10, h - 15))
    pygame.draw.rect(s, (40, 30, 40), (9, 8, w - 18, 5), border_radius=2)  # hair fringe
    belt = pygame.Rect(7, h - 15, w - 14, 5)
    pygame.draw.rect(s, (250, 200, 40), belt)
    for x in range(belt.x + 2, belt.right, 5):
        pygame.draw.line(s, INK, (x, belt.y), (x + 2, belt.bottom - 1), 2)  # tiger stripes
    for ex in (w // 2 - 6, w // 2 + 6):
        _eye(s, (ex, 18), r=3, angry=True)
    pygame.draw.line(s, INK, (w // 2 - 5, 25), (w // 2 + 5, 25), 2)
    for fx in (w // 2 - 4, w // 2 + 3):                                  # fangs
        pygame.draw.polygon(s, WHITE, [(fx, 25), (fx + 2, 25), (fx + 1, 28)])
    lift = (0, 2) if frame else (2, 0)
    for i, fx in enumerate((9, w - 15)):                                # feet
        pygame.draw.ellipse(s, INK, (fx - 1, h - 9 - lift[i], 8, 6))


def _daruma(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (220, 40, 50)
    tilt = -1 if frame else 1
    _outlined_ellipse(s, body, (4 + tilt, 4, w - 8, h - 9))
    face = pygame.Rect(0, 0, 18, 15)
    face.center = (w // 2 + tilt, 15)
    pygame.draw.ellipse(s, (250, 236, 220), face)
    pygame.draw.ellipse(s, INK, face, width=1)
    for ex in (face.centerx - 4, face.centerx + 4):
        pygame.draw.circle(s, INK, (ex, face.centery), 3)
        pygame.draw.circle(s, WHITE, (ex - 1, face.centery - 1), 1)
    pygame.draw.line(s, INK, (face.x + 2, face.y + 2), (face.centerx - 2, face.y + 4), 2)   # bushy brows
    pygame.draw.line(s, INK, (face.right - 2, face.y + 2), (face.centerx + 2, face.y + 4), 2)
    pygame.draw.arc(s, (240, 190, 60), (8 + tilt, h - 18, w - 16, 10), 3.4, 6.0, 3)      # gold trim


def _kappa(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (90, 190, 90)
    pygame.draw.ellipse(s, INK, (w - 14, 12, 12, 16))                    # shell on the back
    pygame.draw.ellipse(s, (130, 96, 60), (w - 13, 13, 10, 14))
    _outlined_ellipse(s, body, (5, 8, w - 14, h - 15))
    pygame.draw.ellipse(s, INK, (8, 3, w - 20, 9))                       # water dish on the head
    pygame.draw.ellipse(s, (210, 236, 250), (9, 4, w - 22, 7))
    pygame.draw.polygon(s, INK, [(w - 15, 18), (w - 6, 21), (w - 15, 24)])  # beak
    pygame.draw.polygon(s, (250, 200, 60), [(w - 14, 19), (w - 8, 21), (w - 14, 23)])
    _eye(s, (w // 2 - 2, 16), r=4, look=2)
    lift = (0, 2) if frame else (2, 0)
    for i, fx in enumerate((8, w - 20)):
        pygame.draw.ellipse(s, INK, (fx - 1, h - 9 - lift[i], 9, 6))
        pygame.draw.ellipse(s, _mix(body, INK, 0.3), (fx, h - 8 - lift[i], 7, 4))


def _critter(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (150, 60, 50)
    foot = colors.get("foot") or _mix(body, INK, 0.4)
    bounce = 2 if frame else 0
    _outlined_ellipse(s, body, (5, 6 + bounce, w - 10, h - 14 - bounce))
    pygame.draw.ellipse(s, _mix(body, WHITE, 0.45), (10, 9 + bounce, 7, 4))
    lift = (0, 2) if frame else (2, 0)
    for i, fx in enumerate((8, w - 16)):
        pygame.draw.ellipse(s, INK, (fx - 1, h - 10 - lift[i], 10, 7))
        pygame.draw.ellipse(s, foot, (fx, h - 9 - lift[i], 8, 5))
    for ex in (w // 2 - 6, w // 2 + 6):
        _eye(s, (ex, 15 + bounce), r=3, angry=True)


# -- More ground species, one set per kind of world (see WORLD_ENEMIES in
# kobito/themes.py): seaside, desert, countryside, snow, farm, city. ---------

def _crab(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (236, 92, 60)
    shell = pygame.Rect(7, 13, w - 14, 13)
    for side in (-1, 1):                                                   # legs
        for k in range(3):
            x0 = w // 2 + side * (6 + k * 3)
            pygame.draw.line(s, INK, (x0, shell.bottom - 2), (x0 + side * 5, h - 6 + (k + frame) % 2), 2)
    for side, cx in ((-1, 5), (1, w - 6)):                                 # claws, snapping
        open_ = 3 if (frame == 0) == (side > 0) else 1
        pygame.draw.line(s, INK, (w // 2 + side * 8, shell.centery), (cx, 11), 3)
        pygame.draw.circle(s, INK, (cx, 9), 6)
        pygame.draw.circle(s, body, (cx, 9), 5)
        pygame.draw.polygon(s, INK, [(cx, 9), (cx + side * 6, 9 - open_), (cx + side * 6, 9 + open_)])
    _outlined_ellipse(s, body, shell)
    pygame.draw.ellipse(s, _mix(body, WHITE, 0.4), (shell.x + 4, shell.y + 2, 8, 4))
    for ex in (w // 2 - 4, w // 2 + 4):                                    # eyes on stalks
        pygame.draw.line(s, INK, (ex, shell.y + 1), (ex, shell.y - 5), 2)
        _eye(s, (ex, shell.y - 6), r=3, angry=True)


def _squid(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (240, 228, 248)
    spot = _mix(body, (200, 80, 160), 0.45)
    bob = 1 if frame else 0
    pygame.draw.polygon(s, INK, [(w // 2, 1 + bob), (w // 2 + 10, 10 + bob), (w // 2 - 10, 10 + bob)])   # fin
    pygame.draw.polygon(s, body, [(w // 2, 3 + bob), (w // 2 + 8, 10 + bob), (w // 2 - 8, 10 + bob)])
    mantle = pygame.Rect(w // 2 - 9, 7 + bob, 18, 17)
    _outlined_ellipse(s, body, mantle)
    for sx, sy in ((-4, 4), (3, 2), (0, 9)):
        pygame.draw.circle(s, spot, (mantle.centerx + sx, mantle.y + sy + 2), 2)
    for k in range(5):                                                     # wiggling tentacles
        x0 = mantle.x + 2 + k * 3.5
        sway = (2 if (k + frame) % 2 else -2)
        pygame.draw.line(s, INK, (x0, mantle.bottom - 2), (x0 + sway, h - 5), 3)
        pygame.draw.line(s, body, (x0, mantle.bottom - 2), (x0 + sway, h - 6), 1)
    for ex in (mantle.centerx - 4, mantle.centerx + 4):
        _eye(s, (ex, mantle.centery + 2), r=3, angry=True)


def _snake(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (150, 160, 66)
    dark = _mix(body, INK, 0.5)
    y0 = h - 9
    wave = 2 if frame else -2
    pts = [(3, y0), (10, y0 - 4 + wave), (17, y0), (24, y0 - 4 - wave), (w - 9, y0 - 6), (w - 7, 12)]
    pygame.draw.lines(s, INK, False, pts, 9)
    pygame.draw.lines(s, body, False, pts, 5)
    for x, y in pts[1:4]:
        pygame.draw.circle(s, dark, (x, y), 2)                             # diamond markings
    head = pygame.Rect(w - 15, 6, 13, 10)
    _outlined_ellipse(s, body, head)
    _eye(s, (head.centerx + 1, head.y + 3), r=2, angry=True)
    if frame:                                                              # flicking tongue
        pygame.draw.line(s, (230, 50, 70), (head.right, head.centery + 2), (w - 1, head.centery + 4), 1)


def _scorpion(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (120, 80, 50)
    for k in range(3):                                                     # legs
        x0 = 12 + k * 5
        pygame.draw.line(s, INK, (x0, h - 12), (x0 - 3 + (k + frame) % 2 * 2, h - 6), 2)
    _outlined_ellipse(s, body, (8, h - 18, 20, 10))
    tail = [(10, h - 14), (5, h - 22), (6, 9), (13, 5)]                    # tail curling over
    pygame.draw.lines(s, INK, False, tail, 6)
    pygame.draw.lines(s, body, False, tail, 3)
    sting = 1 if frame else 0
    pygame.draw.polygon(s, INK, [(13, 3 + sting), (19, 6 + sting), (13, 9 + sting)])
    pygame.draw.polygon(s, (230, 70, 60), [(14, 5 + sting), (17, 6 + sting), (14, 8 + sting)])
    for dy in (-3, 3):                                                     # pincers
        pygame.draw.line(s, INK, (26, h - 13), (w - 3, h - 14 + dy), 3)
        pygame.draw.circle(s, body, (w - 3, h - 14 + dy), 2)
    _eye(s, (24, h - 16), r=2, angry=True)


def _tanuki(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (150, 106, 70)
    dark = (60, 44, 36)
    pygame.draw.ellipse(s, INK, (1, 14, 13, 13))                           # striped tail
    pygame.draw.ellipse(s, body, (2, 15, 11, 11))
    pygame.draw.line(s, dark, (4, 18), (10, 18), 2)
    _outlined_ellipse(s, body, (7, 8, w - 13, h - 14))
    pygame.draw.ellipse(s, (236, 218, 190), (13, 17, w - 24, h - 22))     # belly
    for ex in (16, 26):                                                    # ears
        pygame.draw.circle(s, INK, (ex, 9), 4)
        pygame.draw.circle(s, dark, (ex, 9), 3)
    pygame.draw.ellipse(s, dark, (14, 11, 18, 8))                          # bandit mask
    for ex in (19, 27):
        _eye(s, (ex, 15), r=2, angry=True)
    pygame.draw.polygon(s, (90, 170, 70), [(20, 6), (26, 1), (25, 7)])     # magic leaf
    lift = (0, 2) if frame else (2, 0)
    for i, fx in enumerate((10, w - 14)):
        pygame.draw.ellipse(s, INK, (fx - 1, h - 9 - lift[i], 8, 6))


def _mushroom(s, frame, colors):
    w, h = s.get_size()
    cap = colors.get("body") or (226, 60, 60)
    hop = 2 if frame else 0
    stem = pygame.Rect(w // 2 - 8, 14 - hop, 16, h - 20)
    _outlined_ellipse(s, (246, 236, 214), stem)
    cap_rect = pygame.Rect(3, 2 - hop, w - 6, 18)
    pygame.draw.ellipse(s, INK, cap_rect.inflate(4, 4))
    pygame.draw.ellipse(s, cap, cap_rect)
    pygame.draw.rect(s, (246, 236, 214), (cap_rect.x + 3, cap_rect.centery + 3, cap_rect.width - 6, 3))
    for sx, sy, r in ((-8, 4, 3), (5, 3, 3), (-1, 9, 2), (10, 9, 2)):
        pygame.draw.circle(s, WHITE, (w // 2 + sx, cap_rect.y + sy), r)
    for ex in (w // 2 - 4, w // 2 + 4):
        _eye(s, (ex, stem.y + 9), r=2, angry=True)
    for i, fx in enumerate((w // 2 - 9, w // 2 + 2)):
        pygame.draw.ellipse(s, INK, (fx, h - 8 - (hop if i else 0), 8, 5))


def _snowman(s, frame, colors):
    w, h = s.get_size()
    snow = colors.get("body") or (246, 250, 255)
    tilt = 1 if frame else -1
    _outlined_ellipse(s, snow, (6 + tilt, 14, w - 12, h - 19))
    _outlined_ellipse(s, snow, (10, 4, w - 20, 14))
    pygame.draw.rect(s, INK, (11, 0, w - 22, 7))                           # bucket hat
    pygame.draw.rect(s, (220, 60, 60), (12, 1, w - 24, 5))
    for ex in (w // 2 - 4, w // 2 + 3):
        pygame.draw.circle(s, INK, (ex, 10), 2)
    pygame.draw.polygon(s, (250, 140, 40), [(w // 2, 12), (w // 2 + 9, 13), (w // 2, 15)])   # carrot
    for side in (-1, 1):                                                   # stick arms
        pygame.draw.line(s, (110, 76, 50), (w // 2 + side * 9, 20), (w // 2 + side * 16, 15 - tilt * side), 2)
    for by in (21, 26):
        pygame.draw.circle(s, INK, (w // 2 + tilt, by), 1)


def _beetle(s, frame, colors):
    w, h = s.get_size()
    shell = colors.get("body") or (90, 50, 34)
    for k in range(3):
        x0 = 10 + k * 7
        pygame.draw.line(s, INK, (x0, h - 12), (x0 - 2 + (k + frame) % 2 * 3, h - 5), 2)
    _outlined_ellipse(s, shell, (4, 11, w - 14, h - 19))
    pygame.draw.line(s, _mix(shell, INK, 0.5), (4 + (w - 14) // 2, 12), (4 + (w - 14) // 2, h - 9), 1)
    pygame.draw.ellipse(s, _mix(shell, WHITE, 0.45), (9, 13, 9, 4))        # gloss
    head = pygame.Rect(w - 13, 13, 10, 10)
    _outlined_ellipse(s, _mix(shell, INK, 0.3), head)
    horn = [(w - 8, 14), (w - 1, 2 + frame), (w - 4, 13)]                 # the big horn
    pygame.draw.lines(s, INK, False, horn, 4)
    pygame.draw.circle(s, (255, 90, 70), (w - 6, 18), 1)


def _caterpillar(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (120, 200, 70)
    for k in range(5):
        cx = 6 + k * 6
        cy = h - 11 - (2 if (k + frame) % 2 else 0)
        pygame.draw.circle(s, INK, (cx, cy), 6)
        pygame.draw.circle(s, body, (cx, cy), 5)
        pygame.draw.circle(s, _mix(body, WHITE, 0.4), (cx - 1, cy - 2), 1)
    head = (w - 6, h - 16)
    pygame.draw.circle(s, INK, head, 7)
    pygame.draw.circle(s, _mix(body, (250, 220, 80), 0.4), head, 6)
    for side in (-1, 1):
        pygame.draw.line(s, INK, (head[0] + side * 2, head[1] - 6), (head[0] + side * 4, head[1] - 11), 1)
    _eye(s, (head[0] + 1, head[1] - 1), r=2, angry=True)


def _snail(s, frame, colors):
    w, h = s.get_size()
    shell = colors.get("body") or (200, 120, 60)
    slime = (226, 210, 140)
    stretch = 2 if frame else 0
    foot = pygame.Rect(4, h - 12, w - 8 + stretch - 2, 7)
    _outlined_ellipse(s, slime, foot)
    neck = pygame.Rect(w - 12 + stretch, h - 22, 8, 14)
    _outlined_ellipse(s, slime, neck)
    for k in (-2, 3):                                                      # eye stalks
        pygame.draw.line(s, INK, (neck.centerx + k // 2, neck.y + 2), (neck.centerx + k, neck.y - 5), 2)
        pygame.draw.circle(s, INK, (neck.centerx + k, neck.y - 6), 2)
    pygame.draw.circle(s, INK, (14, h - 18), 11)
    pygame.draw.circle(s, shell, (14, h - 18), 10)
    for r in (7, 4):
        pygame.draw.circle(s, _mix(shell, INK, 0.45), (14 + (7 - r) // 2, h - 18), r, 1)


def _bull(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (52, 44, 48)
    lift = (0, 2) if frame else (2, 0)
    for i, lx in enumerate((8, 13, w - 16, w - 11)):
        pygame.draw.line(s, INK, (lx, h - 13), (lx, h - 6 - lift[i % 2]), 4)
    _outlined_ellipse(s, body, (3, 10, w - 12, h - 20))
    head = pygame.Rect(w - 15, 7, 13, 14)
    _outlined_ellipse(s, body, head)
    for side in (-1, 1):                                                   # horns
        hx = head.centerx + side * 5
        pygame.draw.line(s, INK, (hx, head.y + 2), (hx + side * 3, head.y - 4), 4)
        pygame.draw.line(s, (240, 230, 200), (hx, head.y + 2), (hx + side * 3, head.y - 4), 2)
    pygame.draw.ellipse(s, (230, 170, 170), (head.x + 3, head.bottom - 6, 10, 6))   # muzzle
    pygame.draw.circle(s, (250, 210, 70), (head.centerx + 1, head.bottom), 3, 1)   # nose ring
    _eye(s, (head.centerx + 2, head.y + 5), r=2, angry=True)
    if frame:                                                              # snort
        pygame.draw.circle(s, (220, 220, 230), (w - 2, head.bottom - 4), 2)


def _rat(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (150, 146, 160)
    tail = [(8, h - 10), (2, h - 14), (4, h - 20 + frame * 2)]
    pygame.draw.lines(s, (230, 160, 170), False, tail, 2)
    _outlined_ellipse(s, body, (6, 12, w - 12, h - 18))
    for ex, er in ((w - 15, 5), (w - 22, 4)):                              # round ears
        pygame.draw.circle(s, INK, (ex, 11), er + 1)
        pygame.draw.circle(s, (240, 180, 190), (ex, 11), er - 1)
    pygame.draw.circle(s, (240, 120, 140), (w - 5, 19), 2)                 # nose
    for dy in (-1, 2):
        pygame.draw.line(s, INK, (w - 7, 19 + dy), (w - 1, 18 + dy * 2), 1)  # whiskers
    _eye(s, (w - 12, 17), r=2, angry=True)
    lift = (0, 2) if frame else (2, 0)
    for i, fx in enumerate((10, w - 18)):
        pygame.draw.ellipse(s, (240, 170, 180), (fx, h - 8 - lift[i], 6, 4))


GROUND_DRAWERS = {"slime": _slime, "oni": _oni, "daruma": _daruma, "kappa": _kappa, "critter": _critter,
                  "crab": _crab, "squid": _squid, "snake": _snake, "scorpion": _scorpion, "tanuki": _tanuki,
                  "mushroom": _mushroom, "snowman": _snowman, "beetle": _beetle, "caterpillar": _caterpillar,
                  "snail": _snail, "bull": _bull, "rat": _rat}


def render_ground(species, frame, colors=None):
    s = pygame.Surface(GROUND_SIZE, pygame.SRCALPHA)
    _shadow(s)
    GROUND_DRAWERS.get(species, _critter)(s, frame, colors or {})
    return s


# -- Flying ---------------------------------------------------------------------

def _bat(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (70, 50, 100)
    wing = colors.get("wing") or (120, 84, 160)
    cx, cy = w // 2, h // 2
    up = frame == 0
    for side in (-1, 1):
        tip_y = cy - 12 if up else cy + 6
        pts = [(cx, cy - 2), (cx + side * (w // 2 - 1), tip_y), (cx + side * (w // 2 - 6), cy + 4),
               (cx + side * 8, cy + 2)]
        pygame.draw.polygon(s, INK, pts)
        inner = [(x - side, y + (1 if y < cy else -1)) for x, y in pts]
        pygame.draw.polygon(s, wing, inner)
    _outlined_ellipse(s, body, (cx - 7, cy - 7, 14, 14))
    for ex in (cx - 3, cx + 3):
        pygame.draw.circle(s, (255, 70, 70), (ex, cy - 1), 2)
    for fx in (cx - 3, cx + 2):
        pygame.draw.polygon(s, WHITE, [(fx, cy + 3), (fx + 2, cy + 3), (fx + 1, cy + 6)])


def _chochin(s, frame, colors):
    w, h = s.get_size()
    paper = colors.get("body") or (250, 150, 60)
    sway = 1 if frame else -1
    lantern = pygame.Rect(0, 0, 24, 26)
    lantern.center = (w // 2 + sway, h // 2 + 1)
    pygame.draw.rect(s, INK, lantern.inflate(4, 4), border_radius=10)
    pygame.draw.rect(s, paper, lantern, border_radius=9)
    for y in range(lantern.y + 5, lantern.bottom - 2, 5):                # paper ribs
        pygame.draw.line(s, _mix(paper, INK, 0.35), (lantern.x + 2, y), (lantern.right - 3, y), 1)
    for y in (lantern.y - 2, lantern.bottom - 1):                        # black caps
        pygame.draw.rect(s, INK, (lantern.x + 4, y, lantern.width - 8, 4))
    _eye(s, (lantern.centerx, lantern.y + 10), r=5, look=sway)
    mouth = pygame.Rect(lantern.centerx - 7, lantern.y + 17, 14, 6)
    pygame.draw.ellipse(s, INK, mouth)
    pygame.draw.ellipse(s, (230, 60, 80), (mouth.centerx - 2, mouth.y + 2, 6, 7 + frame * 2))   # tongue


def _karakasa(s, frame, colors):
    w, h = s.get_size()
    canopy = colors.get("body") or (230, 70, 70)
    hop = 2 if frame else 0
    top = 2 + hop
    pts = [(w // 2, top), (w - 2, top + 16), (2, top + 16)]
    pygame.draw.polygon(s, INK, [(x, y - 1 if y == top else y + 1) for x, y in pts])
    pygame.draw.polygon(s, canopy, pts)
    for x in (w // 4, w // 2, 3 * w // 4):                               # umbrella ribs
        pygame.draw.line(s, _mix(canopy, INK, 0.4), (w // 2, top + 2), (x, top + 15), 1)
    pygame.draw.line(s, (250, 230, 200), (6, top + 15), (w - 6, top + 15), 2)
    _eye(s, (w // 2, top + 9), r=4)
    pygame.draw.ellipse(s, (230, 60, 80), (w // 2 + 2, top + 13, 5, 7))  # tongue
    pygame.draw.line(s, INK, (w // 2, top + 17), (w // 2, h - 3), 4)     # wooden handle leg
    pygame.draw.line(s, (170, 120, 70), (w // 2, top + 17), (w // 2, h - 3), 2)


def _flying_fish(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (70, 130, 210)
    fin = colors.get("wing") or (170, 216, 252)
    cy = h // 2 + 3
    pygame.draw.polygon(s, INK, [(3, cy - 7), (10, cy), (3, cy + 7)])     # forked tail
    pygame.draw.polygon(s, body, [(4, cy - 5), (9, cy), (4, cy + 5)])
    _outlined_ellipse(s, body, (8, cy - 5, w - 14, 10))
    pygame.draw.ellipse(s, (226, 238, 250), (12, cy, w - 22, 4))           # silver belly
    _eye(s, (w - 10, cy - 1), r=2, angry=True)
    # The big "wing" fin it glides on: a wide fan, spread up or swept down.
    d = -1 if frame == 0 else 1
    fan = [(w // 2 + 6, cy + d), (w // 2 - 3, cy + d * 15), (w // 2 - 14, cy + d * 12), (w // 2 - 6, cy)]
    pygame.draw.polygon(s, fin, fan)
    pygame.draw.polygon(s, INK, fan, 2)
    for k in (0.4, 0.75):                                                  # fin rays
        pygame.draw.line(s, _mix(fin, INK, 0.35), (w // 2 + 2, cy + d), (w // 2 + 2 - 14 * k, cy + d * 14 * k), 1)


def _pufferfish(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (246, 206, 80)
    r = 11 + frame
    c = (w // 2, h // 2)
    for k in range(12):                                                    # spines
        a = k * math.pi / 6
        pygame.draw.line(s, INK, (c[0] + math.cos(a) * r, c[1] + math.sin(a) * r),
                         (c[0] + math.cos(a) * (r + 4), c[1] + math.sin(a) * (r + 4)), 2)
    pygame.draw.circle(s, INK, c, r + 1)
    pygame.draw.circle(s, body, c, r)
    pygame.draw.circle(s, (252, 244, 220), (c[0], c[1] + 4), r - 5)        # pale belly
    for sx, sy in ((-5, -5), (2, -7), (-7, 1)):
        pygame.draw.circle(s, _mix(body, INK, 0.5), (c[0] + sx, c[1] + sy), 1)
    _eye(s, (c[0] + 4, c[1] - 3), r=3, angry=True)
    pygame.draw.circle(s, INK, (c[0] + r - 1, c[1] + 2), 2)                # pouty mouth


def _jellyfish(s, frame, colors):
    w, h = s.get_size()
    bell = colors.get("body") or (240, 150, 210)
    squeeze = 2 if frame else 0
    rect = pygame.Rect(6 + squeeze, 2, w - 12 - squeeze * 2, 18)
    pygame.draw.ellipse(s, INK, rect.inflate(4, 4))
    pygame.draw.ellipse(s, bell, rect)
    pygame.draw.rect(s, (0, 0, 0, 0), (rect.x - 3, rect.centery + 3, rect.width + 6, 8))
    pygame.draw.line(s, INK, (rect.x, rect.centery + 3), (rect.right, rect.centery + 3), 2)
    pygame.draw.ellipse(s, _mix(bell, WHITE, 0.5), (rect.x + 4, rect.y + 3, 8, 4))
    for k in range(5):
        x0 = rect.x + 3 + k * (rect.width - 6) / 4
        sway = 2 if (k + frame) % 2 else -2
        pygame.draw.line(s, _mix(bell, INK, 0.25), (x0, rect.centery + 4), (x0 + sway, h - 2), 2)
    for ex in (w // 2 - 4, w // 2 + 4):
        _eye(s, (ex, rect.centery - 1), r=2)


def _seagull(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (250, 250, 252)
    wing = colors.get("wing") or (186, 196, 210)
    cx, cy = w // 2, h // 2 + 4
    up = frame == 0
    far = [(cx + 2, cy - 3), (cx + 8, cy - 13 if up else cy + 8), (cx + 12, cy - 2)]
    pygame.draw.polygon(s, INK, far)
    pygame.draw.polygon(s, _mix(wing, INK, 0.2), far)
    pygame.draw.polygon(s, INK, [(cx - 9, cy - 1), (cx - 16, cy - 4), (cx - 15, cy + 3)])   # tail
    _outlined_ellipse(s, body, (cx - 10, cy - 5, 20, 10))
    pygame.draw.polygon(s, (250, 196, 50), [(cx + 9, cy - 3), (cx + 16, cy - 1), (cx + 9, cy + 1)])
    _eye(s, (cx + 5, cy - 2), r=2, angry=True)
    # The near wing: broad, bent like a gull's, black at the tip.
    d = -1 if up else 1
    near = [(cx + 4, cy - 1), (cx - 3, cy + d * 11), (cx - 17, cy + d * 14), (cx - 7, cy + 1)]
    pygame.draw.polygon(s, wing, near)
    pygame.draw.polygon(s, INK, near, 2)
    pygame.draw.line(s, INK, near[2], (near[2][0] + 6, near[2][1] - d * 2), 4)


def _crow(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (36, 34, 46)
    wing = colors.get("wing") or (60, 58, 76)
    cx, cy = w // 2, h // 2 + 2
    up = frame == 0
    for side in (-1, 1):
        tip_y = cy - 13 if up else cy + 8
        pts = [(cx, cy - 3), (cx + side * (w // 2 - 1), tip_y), (cx + side * (w // 2 - 7), tip_y + 4),
               (cx + side * 5, cy + 3)]
        pygame.draw.polygon(s, INK, pts)
        pygame.draw.polygon(s, wing, [(x - side, y + (1 if y < cy else -1)) for x, y in pts])
    pygame.draw.polygon(s, body, [(cx - 12, cy + 1), (cx - 5, cy - 2), (cx - 5, cy + 4)])   # tail
    _outlined_ellipse(s, body, (cx - 7, cy - 6, 15, 12))
    pygame.draw.circle(s, INK, (cx + 9, cy - 3), 5)
    pygame.draw.circle(s, body, (cx + 9, cy - 3), 4)
    pygame.draw.polygon(s, (90, 86, 96), [(cx + 12, cy - 4), (cx + 18, cy - 2), (cx + 12, cy)])   # beak
    pygame.draw.circle(s, (250, 210, 70), (cx + 10, cy - 4), 2)
    pygame.draw.circle(s, INK, (cx + 10, cy - 4), 1)


def _bee(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (250, 196, 40)
    cx, cy = w // 2, h // 2 + 3
    wing = pygame.Rect(0, 0, 12, 10 if frame else 6)
    for dx in (-5, 3):                                                      # buzzing wings
        wing.midbottom = (cx + dx, cy - 4)
        pygame.draw.ellipse(s, INK, wing.inflate(2, 2))
        pygame.draw.ellipse(s, (226, 240, 255), wing)
    rect = pygame.Rect(cx - 11, cy - 6, 22, 13)
    _outlined_ellipse(s, body, rect)
    for x in (cx - 4, cx + 2):
        pygame.draw.line(s, INK, (x, rect.y + 1), (x, rect.bottom - 1), 3)   # stripes
    pygame.draw.polygon(s, INK, [(rect.x - 1, cy - 2), (rect.x - 6, cy), (rect.x - 1, cy + 2)])   # stinger
    _eye(s, (rect.right - 5, cy - 1), r=2, angry=True)
    pygame.draw.line(s, INK, (rect.right - 4, rect.y), (rect.right, rect.y - 5), 1)


def _ghost(s, frame, colors):
    w, h = s.get_size()
    body = colors.get("body") or (240, 244, 255)
    sway = 2 if frame else -2
    head = pygame.Rect(w // 2 - 10, 3, 20, 20)
    tail = [(head.x, head.centery), (head.right, head.centery), (w // 2 + 6 + sway, h - 6),
            (w // 2 + sway, h - 2), (w // 2 - 4, h - 8)]
    pygame.draw.polygon(s, INK, [(x + (1 if x > w // 2 else -1), y + 1) for x, y in tail])
    pygame.draw.polygon(s, body, tail)
    _outlined_ellipse(s, body, head)
    pygame.draw.polygon(s, WHITE, [(w // 2 - 4, head.y - 1), (w // 2 + 4, head.y - 1), (w // 2, head.y + 5)])
    pygame.draw.polygon(s, INK, [(w // 2 - 4, head.y - 1), (w // 2 + 4, head.y - 1), (w // 2, head.y + 5)], 1)
    for ex in (w // 2 - 4, w // 2 + 4):
        pygame.draw.line(s, INK, (ex - 2, head.centery), (ex + 2, head.centery + 1), 2)   # sleepy eyes
    pygame.draw.ellipse(s, INK, (w // 2 - 2, head.centery + 4, 5, 4))
    for hx in (head.x + 2, head.right - 2):
        pygame.draw.line(s, body, (hx, head.centery + 2), (hx + (-5 if hx < w // 2 else 5), head.centery + 6), 3)


def _thundercloud(s, frame, colors):
    w, h = s.get_size()
    cloud = colors.get("body") or (120, 124, 148)
    if frame:                                                              # lightning
        bolt = [(w // 2, 18), (w // 2 - 4, 25), (w // 2 + 1, 25), (w // 2 - 3, h - 1)]
        pygame.draw.lines(s, INK, False, bolt, 4)
        pygame.draw.lines(s, (255, 230, 80), False, bolt, 2)
    for cx, cy, r in ((10, 13, 7), (19, 9, 9), (28, 13, 7), (19, 16, 8)):
        pygame.draw.circle(s, INK, (cx, cy), r + 1)
    for cx, cy, r in ((10, 13, 7), (19, 9, 9), (28, 13, 7), (19, 16, 8)):
        pygame.draw.circle(s, cloud, (cx, cy), r)
    pygame.draw.circle(s, _mix(cloud, WHITE, 0.4), (16, 6), 3)
    for ex in (15, 23):
        _eye(s, (ex, 13), r=3, angry=True)


FLYING_DRAWERS = {"bat": _bat, "chochin": _chochin, "karakasa": _karakasa, "flying_fish": _flying_fish,
                  "pufferfish": _pufferfish, "jellyfish": _jellyfish, "seagull": _seagull, "crow": _crow,
                  "bee": _bee, "ghost": _ghost, "thundercloud": _thundercloud}


def render_flying(species, frame, colors=None):
    s = pygame.Surface(FLYING_SIZE, pygame.SRCALPHA)
    FLYING_DRAWERS.get(species, _bat)(s, frame, colors or {})
    return s


def frames_for(render, species, colors=None):
    """[(right_facing, left_facing)] for both animation frames."""
    out = []
    for frame in (0, 1):
        img = render(species, frame, colors)
        out.append((img, pygame.transform.flip(img, True, False)))
    return out


def flap(t, speed=6.0):
    return int(t * speed) % 2

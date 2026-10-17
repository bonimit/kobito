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


GROUND_DRAWERS = {"slime": _slime, "oni": _oni, "daruma": _daruma, "kappa": _kappa, "critter": _critter}


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


FLYING_DRAWERS = {"bat": _bat, "chochin": _chochin, "karakasa": _karakasa}


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

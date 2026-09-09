"""Small, self-contained pixel-art drawing functions for background
scenery. Each one draws a single decoration at a given anchor point.
Kept separate from kobito/background.py (which handles placement,
parallax, and picking which of these to call) and kobito/themes.py
(which picks colors/sizes per world) so each piece stays simple.

Every ground-rooted shape has the signature (screen, x, ground_y, size,
color) and anchors its base at (x, ground_y); every floaty shape (sky/
water layer) has the signature (screen, x, y, size, color) and centers
on (x, y). Keeping one consistent signature per category lets
Background place and call any of them generically, without needing to
know which specific shape it's drawing.
"""

import math

import pygame


# --- Ground-rooted props ---------------------------------------------


def draw_pine_tree(screen, x, ground_y, size, color, trunk_color=(92, 64, 40)):
    trunk_rect = pygame.Rect(0, 0, 10, 22)
    trunk_rect.midbottom = (x, ground_y)
    pygame.draw.rect(screen, trunk_color, trunk_rect)

    tiers = [(size, 1.0), (size * 0.7, 0.75), (size * 0.4, 0.5)]
    base_y = trunk_rect.top + 6
    for tier_height, width_scale in tiers:
        tier_width = size * width_scale
        top = (x, base_y - tier_height)
        left = (x - tier_width / 2, base_y)
        right = (x + tier_width / 2, base_y)
        pygame.draw.polygon(screen, color, [top, left, right])
        base_y -= tier_height * 0.45


def draw_cactus(screen, x, ground_y, size, color):
    trunk_w = 12
    trunk_rect = pygame.Rect(0, 0, trunk_w, size)
    trunk_rect.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, trunk_rect, border_radius=6)

    for side in (-1, 1):
        arm_h = size * 0.4
        arm_rect = pygame.Rect(0, 0, 8, arm_h)
        arm_rect.midbottom = (x + side * (trunk_w // 2 + 5), trunk_rect.top + size * 0.55)
        pygame.draw.rect(screen, color, arm_rect, border_radius=4)
        connector = pygame.Rect(0, 0, 9, 8)
        connector.midtop = (x + side * 4, arm_rect.bottom - 6)
        pygame.draw.rect(screen, color, connector, border_radius=3)


def draw_palm_tree(screen, x, ground_y, size, color, trunk_color=(120, 90, 55)):
    top = (x + size * 0.15, ground_y - size)
    pygame.draw.line(screen, trunk_color, (x, ground_y), top, 6)

    for angle_dx, angle_dy in ((-1.0, -0.2), (-0.6, -0.9), (0.1, -1.0), (0.6, -0.8), (1.0, -0.3)):
        tip = (top[0] + angle_dx * size * 0.45, top[1] + angle_dy * size * 0.35)
        pygame.draw.line(screen, color, top, tip, 5)


def draw_coral(screen, x, ground_y, size, color):
    for dx, scale in ((-size * 0.25, 0.7), (0, 1.0), (size * 0.25, 0.7)):
        branch_top = (x + dx, ground_y - size * scale)
        pygame.draw.line(screen, color, (x + dx, ground_y), branch_top, 6)
        pygame.draw.circle(screen, color, (int(branch_top[0]), int(branch_top[1])), 7)


def draw_seaweed(screen, x, ground_y, size, color):
    for dx in (-6, 0, 6):
        points = []
        segments = 5
        for i in range(segments + 1):
            t = i / segments
            wave = 5 * (1 if i % 2 == 0 else -1) * t
            points.append((x + dx + wave, ground_y - size * t))
        pygame.draw.lines(screen, color, False, points, 3)


def draw_minaret(screen, x, ground_y, size, color, dome_color=(230, 200, 90)):
    tower_w = 14
    tower_rect = pygame.Rect(0, 0, tower_w, size)
    tower_rect.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, tower_rect)

    dome_radius = tower_w * 0.75
    pygame.draw.circle(screen, dome_color, (x, tower_rect.top), dome_radius)
    pygame.draw.line(screen, dome_color, (x, tower_rect.top - dome_radius), (x, tower_rect.top - dome_radius - 8), 2)


def draw_floating_island(screen, x, ground_y, size, color, grass_color=(120, 195, 110)):
    body_rect = pygame.Rect(0, 0, size * 1.6, size * 0.8)
    body_rect.midtop = (x, ground_y - size * 0.4)
    pygame.draw.ellipse(screen, color, body_rect)

    grass_rect = pygame.Rect(0, 0, size * 1.6, size * 0.35)
    grass_rect.midtop = (x, ground_y - size * 0.55)
    pygame.draw.ellipse(screen, grass_color, grass_rect)

    for dx in (-size * 0.3, 0, size * 0.3):
        pygame.draw.line(
            screen, color,
            (x + dx, body_rect.bottom - 4),
            (x + dx * 1.3, body_rect.bottom + size * 0.35),
            3,
        )


def draw_bush(screen, x, ground_y, size, color):
    scale = size / 10
    for dx, dy, r in ((-8, 0, 9), (8, 0, 9), (0, -6, 10)):
        pygame.draw.circle(screen, color, (x + dx * scale, ground_y + dy * scale), r * scale)


def draw_flower(screen, x, ground_y, size, color, stem_color=(58, 130, 66)):
    scale = size / 12
    stem_top = ground_y - 12 * scale
    pygame.draw.line(screen, stem_color, (x, ground_y), (x, stem_top), 2)
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
        pygame.draw.circle(screen, color, (x + dx * scale, stem_top + dy * scale), 2 * scale)
    pygame.draw.circle(screen, (255, 214, 90), (x, stem_top), 2 * scale)


def draw_torii(screen, x, ground_y, size, color, accent_color=(40, 30, 30)):
    """A vermillion torii gate. The most recognizable Japanese landmark
    silhouette there is, so it does a lot of work anchoring the game's
    subject in the scenery itself.
    """
    half_w = size * 0.42
    pillar_w = max(4, round(size * 0.09))

    # Real torii pillars lean very slightly inward toward the top.
    for side in (-1, 1):
        top_x = x + side * half_w * 0.88
        base_x = x + side * half_w
        pygame.draw.polygon(screen, color, [
            (base_x - pillar_w / 2, ground_y),
            (base_x + pillar_w / 2, ground_y),
            (top_x + pillar_w / 2, ground_y - size * 0.78),
            (top_x - pillar_w / 2, ground_y - size * 0.78),
        ])

    # Nuki: the lower horizontal tie beam.
    nuki = pygame.Rect(0, 0, half_w * 1.85, max(3, round(size * 0.07)))
    nuki.center = (x, ground_y - size * 0.6)
    pygame.draw.rect(screen, color, nuki)

    # Kasagi: the wide top lintel, plus a thin dark strip beneath it.
    kasagi_y = ground_y - size * 0.82
    pygame.draw.polygon(screen, color, [
        (x - half_w * 1.22, kasagi_y + size * 0.06),
        (x + half_w * 1.22, kasagi_y + size * 0.06),
        (x + half_w * 1.12, kasagi_y - size * 0.04),
        (x - half_w * 1.12, kasagi_y - size * 0.04),
    ])
    accent = pygame.Rect(0, 0, half_w * 2.1, max(2, round(size * 0.035)))
    accent.center = (x, kasagi_y + size * 0.10)
    pygame.draw.rect(screen, accent_color, accent)


def draw_pagoda(screen, x, ground_y, size, color, roof_color=(120, 70, 80)):
    """A tiered pagoda, drawn bottom-up so each roof sits on the storey
    below it and every tier is a little narrower than the last.
    """
    tiers = 4
    tier_h = size / (tiers + 1)
    body_w = size * 0.34

    y = ground_y
    for i in range(tiers):
        width = body_w * (1 - i * 0.16)
        body = pygame.Rect(0, 0, width, tier_h * 0.62)
        body.midbottom = (x, y)
        pygame.draw.rect(screen, color, body)

        roof_w = width * 2.05
        roof_y = body.top
        pygame.draw.polygon(screen, roof_color, [
            (x - roof_w / 2, roof_y),
            (x + roof_w / 2, roof_y),
            (x + roof_w * 0.30, roof_y - tier_h * 0.42),
            (x - roof_w * 0.30, roof_y - tier_h * 0.42),
        ])
        y = roof_y - tier_h * 0.42

    pygame.draw.line(screen, roof_color, (x, y), (x, y - size * 0.14), max(2, round(size * 0.03)))


def draw_sakura_tree(screen, x, ground_y, size, color, trunk_color=(96, 70, 58)):
    trunk_top = ground_y - size * 0.55
    pygame.draw.line(screen, trunk_color, (x, ground_y), (x, trunk_top), max(4, round(size * 0.10)))
    for side, lift in ((-1, 0.72), (1, 0.66)):
        pygame.draw.line(
            screen, trunk_color,
            (x, trunk_top + size * 0.08),
            (x + side * size * 0.24, ground_y - size * lift),
            max(2, round(size * 0.055)),
        )

    # Overlapping blossom puffs read as one soft canopy.
    for dx, dy, r in ((0, 0.80, 0.30), (-0.26, 0.70, 0.22), (0.26, 0.70, 0.22), (-0.14, 0.92, 0.19), (0.16, 0.92, 0.19)):
        pygame.draw.circle(screen, color, (x + dx * size, ground_y - dy * size), max(2, r * size))


def draw_stone_lantern(screen, x, ground_y, size, color, light_color=(255, 226, 150)):
    """An ishidoro garden lantern, with its window lit."""
    post = pygame.Rect(0, 0, max(3, round(size * 0.14)), size * 0.44)
    post.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, post)

    plate = pygame.Rect(0, 0, size * 0.42, max(2, size * 0.07))
    plate.midbottom = (x, post.top)
    pygame.draw.rect(screen, color, plate)

    house = pygame.Rect(0, 0, size * 0.34, size * 0.26)
    house.midbottom = (x, plate.top)
    pygame.draw.rect(screen, color, house)
    window = pygame.Rect(0, 0, size * 0.16, size * 0.13)
    window.center = house.center
    pygame.draw.rect(screen, light_color, window)

    pygame.draw.polygon(screen, color, [
        (x - size * 0.26, house.top),
        (x + size * 0.26, house.top),
        (x, house.top - size * 0.17),
    ])


def draw_mushroom(screen, x, ground_y, size, color, stem_color=(240, 232, 214)):
    stem = pygame.Rect(0, 0, max(3, size * 0.34), size * 0.55)
    stem.midbottom = (x, ground_y)
    pygame.draw.rect(screen, stem_color, stem, border_radius=max(1, round(size * 0.12)))

    cap = pygame.Rect(0, 0, size * 1.15, size * 0.80)
    cap.midbottom = (x, stem.top + size * 0.12)
    pygame.draw.ellipse(screen, color, cap)
    for dx, r in ((-0.24, 0.10), (0.18, 0.13), (0.02, 0.07)):
        pygame.draw.circle(screen, stem_color, (x + dx * size, cap.centery), max(1, r * size))


def draw_grass_tuft(screen, x, ground_y, size, color):
    for dx, lean in ((-0.55, -0.35), (-0.20, -0.10), (0.15, 0.12), (0.50, 0.40)):
        pygame.draw.line(
            screen, color,
            (x + dx * size * 0.5, ground_y),
            (x + (dx + lean) * size, ground_y - size),
            max(1, round(size * 0.16)),
        )


def draw_rock(screen, x, ground_y, size, color, highlight_color=None):
    pygame.draw.polygon(screen, color, [
        (x - size * 0.60, ground_y),
        (x - size * 0.45, ground_y - size * 0.45),
        (x - size * 0.10, ground_y - size * 0.70),
        (x + size * 0.30, ground_y - size * 0.55),
        (x + size * 0.60, ground_y),
    ])
    if highlight_color:
        # A lit top facet stops the rock reading as a flat grey blob.
        pygame.draw.polygon(screen, highlight_color, [
            (x - size * 0.10, ground_y - size * 0.70),
            (x + size * 0.30, ground_y - size * 0.55),
            (x + size * 0.05, ground_y - size * 0.42),
        ])


def draw_pyramid(screen, x, ground_y, size, color, lit_color=None):
    half = size * 0.85
    apex = (x, ground_y - size)
    pygame.draw.polygon(screen, color, [(x - half, ground_y), (x + half, ground_y), apex])
    if lit_color:
        # Split down the apex ridge so one face catches the sun.
        pygame.draw.polygon(screen, lit_color, [apex, (x + half, ground_y), (x, ground_y)])


# --- Floaty (sky/water) props ------------------------------------------


def draw_cloud(screen, x, y, size, color=(255, 255, 255)):
    pygame.draw.ellipse(screen, color, (x, y, size * 1.6, size))
    pygame.draw.ellipse(screen, color, (x + size * 0.5, y - size * 0.35, size * 1.2, size * 0.9))
    pygame.draw.ellipse(screen, color, (x + size * 1.0, y, size * 1.0, size * 0.75))


def draw_star(screen, x, y, size, color=(255, 255, 235)):
    pygame.draw.line(screen, color, (x - size, y), (x + size, y), 2)
    pygame.draw.line(screen, color, (x, y - size), (x, y + size), 2)


def draw_moon(screen, x, y, size, color=(245, 235, 200)):
    shadow_color = (20, 20, 45)
    pygame.draw.circle(screen, color, (x, y), size)
    pygame.draw.circle(screen, shadow_color, (x + size * 0.4, y - size * 0.3), size * 0.85)


def draw_sun(screen, x, y, size, color=(255, 210, 90)):
    pygame.draw.circle(screen, color, (x, y), size)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        inner = (x + math.cos(rad) * size * 1.2, y + math.sin(rad) * size * 1.2)
        outer = (x + math.cos(rad) * size * 1.5, y + math.sin(rad) * size * 1.5)
        pygame.draw.line(screen, color, inner, outer, 3)


def draw_bubble(screen, x, y, size, color=(230, 245, 255)):
    pygame.draw.circle(screen, color, (x, y), size, width=2)
    pygame.draw.circle(screen, color, (x - size * 0.3, y - size * 0.3), max(1, size * 0.2))


def draw_glow(screen, x, y, size, color=(255, 240, 190)):
    """A soft halo built from stacked translucent circles -- large and
    faint first, small and stronger last, so the alpha accumulates
    toward the middle. Gives the sun and moon some atmosphere instead
    of a hard-edged disc pasted flat onto the sky.
    """
    size = max(2, round(size))
    layers = 10
    surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    for i in range(layers, 0, -1):
        t = i / layers
        # The outermost ring must land on alpha 0, otherwise the halo
        # ends on a faint but visible disc edge -- very obvious against
        # a dark night sky.
        pygame.draw.circle(surface, (*color, round(30 * (1 - t) ** 1.2)), (size, size), size * t)
    screen.blit(surface, (x - size, y - size))


def draw_petal(screen, x, y, size, color=(255, 200, 220)):
    """A drifting sakura petal -- a tiny tilted ellipse."""
    petal = pygame.Surface((max(2, size * 2), max(2, size * 2)), pygame.SRCALPHA)
    pygame.draw.ellipse(petal, color, (0, size * 0.5, size * 2, size))
    screen.blit(pygame.transform.rotate(petal, 30), (x - size, y - size))


def draw_shooting_star(screen, x, y, size, color=(255, 255, 235)):
    # A thin streak with a small bright head -- keeping the tail narrow
    # relative to its length is what makes it read as motion rather
    # than a lollipop.
    tail = size * 5
    pygame.draw.line(screen, color, (x, y), (x - tail, y + tail * 0.45), max(1, round(size * 0.35)))
    pygame.draw.circle(screen, color, (x, y), max(1, size * 0.7))


def draw_balloon(screen, x, y, size, color=(240, 120, 130), string_color=(235, 235, 240)):
    body = pygame.Rect(0, 0, size * 1.5, size * 1.85)
    body.center = (x, y)
    pygame.draw.ellipse(screen, color, body)

    # Knot at the bottom, then a thread trailing below it.
    pygame.draw.polygon(screen, color, [
        (x - size * 0.20, body.bottom - 2),
        (x + size * 0.20, body.bottom - 2),
        (x, body.bottom + size * 0.22),
    ])
    pygame.draw.line(screen, string_color, (x, body.bottom + size * 0.20), (x, body.bottom + size * 1.5), 1)
    # Specular highlight: sells it as a shiny balloon rather than an egg.
    pygame.draw.ellipse(screen, (255, 255, 255), (body.x + size * 0.25, body.y + size * 0.30, size * 0.32, size * 0.48))


def draw_bird(screen, x, y, size, color=(70, 60, 60), facing=1):
    pygame.draw.arc(screen, color, (x - size, y - size / 2, size, size), 0.3, 2.8, 2)
    pygame.draw.arc(screen, color, (x, y - size / 2, size, size), 0.3, 2.8, 2)


def draw_bat(screen, x, y, size, color=(50, 45, 60), facing=1):
    # Pointed membrane wings instead of a bird's simple arcs, and a
    # small round body, to read distinctly as a bat against a night sky.
    for side in (-1, 1):
        wing = [
            (x, y),
            (x + side * size * 1.1, y - size * 0.3),
            (x + side * size * 0.7, y + size * 0.1),
            (x + side * size * 1.0, y + size * 0.4),
            (x + side * size * 0.3, y + size * 0.2),
        ]
        pygame.draw.polygon(screen, color, wing)
    pygame.draw.circle(screen, color, (x, y), max(2, int(size * 0.25)))


def draw_butterfly(screen, x, y, size, color=(230, 150, 200), facing=1):
    # Four wings (big upper pair, smaller lower pair) rather than two
    # ovals -- that silhouette is what actually reads as a butterfly.
    for side in (-1, 1):
        upper = pygame.Rect(0, 0, size * 0.78, size * 0.72)
        upper.center = (x + side * size * 0.34, y - size * 0.20)
        pygame.draw.ellipse(screen, color, upper)

        lower = pygame.Rect(0, 0, size * 0.58, size * 0.52)
        lower.center = (x + side * size * 0.28, y + size * 0.30)
        pygame.draw.ellipse(screen, color, lower)

    pygame.draw.line(screen, (60, 50, 40), (x, y - size * 0.45), (x, y + size * 0.5), max(1, round(size * 0.14)))
    for side in (-1, 1):
        pygame.draw.line(
            screen, (60, 50, 40),
            (x, y - size * 0.45),
            (x + side * size * 0.22, y - size * 0.72),
            1,
        )


def draw_fish(screen, x, y, size, color=(230, 140, 90), facing=1):
    body_rect = pygame.Rect(0, 0, size * 1.6, size)
    body_rect.center = (x, y)
    pygame.draw.ellipse(screen, color, body_rect)
    if facing >= 0:
        tail = [(body_rect.left + 2, y), (body_rect.left - size * 0.5, y - size * 0.4), (body_rect.left - size * 0.5, y + size * 0.4)]
        eye_x = body_rect.right - size * 0.3
    else:
        tail = [(body_rect.right - 2, y), (body_rect.right + size * 0.5, y - size * 0.4), (body_rect.right + size * 0.5, y + size * 0.4)]
        eye_x = body_rect.left + size * 0.3
    pygame.draw.polygon(screen, color, tail)
    pygame.draw.circle(screen, (30, 30, 30), (int(eye_x), int(y)), max(1, int(size * 0.08)))


def draw_whale(screen, x, y, size, color=(90, 130, 170), facing=1):
    body_rect = pygame.Rect(0, 0, size * 2.2, size)
    body_rect.center = (x, y)
    pygame.draw.ellipse(screen, color, body_rect)

    tail_x = body_rect.left if facing >= 0 else body_rect.right
    tail_dir = -1 if facing >= 0 else 1
    tail = [
        (tail_x, y),
        (tail_x + tail_dir * size * 0.4, y - size * 0.5),
        (tail_x + tail_dir * size * 0.4, y + size * 0.5),
    ]
    pygame.draw.polygon(screen, color, tail)

    spout_x = body_rect.right - size * 0.3 if facing >= 0 else body_rect.left + size * 0.3
    pygame.draw.line(screen, (210, 235, 245), (spout_x, body_rect.top), (spout_x, body_rect.top - size * 0.4), 3)
    pygame.draw.circle(screen, (30, 30, 30), (int(spout_x - facing * size * 0.15), int(y - size * 0.1)), max(1, int(size * 0.06)))


def draw_squid(screen, x, y, size, color=(180, 110, 200), facing=1):
    mantle_rect = pygame.Rect(0, 0, size * 0.9, size * 1.1)
    mantle_rect.midbottom = (x, y)
    pygame.draw.ellipse(screen, color, mantle_rect)

    for i, dx in enumerate((-0.3, -0.1, 0.1, 0.3)):
        wave = 4 if i % 2 == 0 else -4
        pygame.draw.line(
            screen, color,
            (x + dx * size, y),
            (x + dx * size + wave, y + size * 0.6),
            3,
        )


def draw_crab(screen, x, ground_y, size, color=(210, 90, 70), facing=1):
    body_rect = pygame.Rect(0, 0, size * 1.3, size * 0.8)
    body_rect.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, color, body_rect)

    for side in (-1, 1):
        claw_x = x + side * size * 0.8
        pygame.draw.line(screen, color, (x + side * size * 0.5, body_rect.centery), (claw_x, body_rect.top), 3)
        pygame.draw.circle(screen, color, (int(claw_x), int(body_rect.top)), max(2, int(size * 0.18)))
        for leg_i in range(2):
            leg_y = body_rect.bottom - leg_i * 3
            pygame.draw.line(screen, color, (x + side * size * 0.3, leg_y), (x + side * (size * 0.5 + leg_i * 4), leg_y + 4), 2)


def draw_lizard(screen, x, ground_y, size, color=(120, 160, 90), facing=1):
    body_rect = pygame.Rect(0, 0, size * 1.4, size * 0.5)
    body_rect.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, color, body_rect)

    tail_dir = -1 if facing >= 0 else 1
    tail_tip = (body_rect.centerx + tail_dir * size * 1.1, ground_y - size * 0.15)
    pygame.draw.line(screen, color, (body_rect.centerx + tail_dir * size * 0.5, body_rect.centery), tail_tip, 3)

    for side in (-1, 1):
        leg_x = body_rect.centerx + side * size * 0.35
        pygame.draw.line(screen, color, (leg_x, body_rect.bottom - 2), (leg_x + side * 3, ground_y), 2)


def draw_scorpion(screen, x, ground_y, size, color=(70, 55, 50), facing=1):
    body_rect = pygame.Rect(0, 0, size, size * 0.5)
    body_rect.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, color, body_rect)

    tail_dir = -1 if facing >= 0 else 1
    points = [(body_rect.centerx - tail_dir * size * 0.3, body_rect.centery)]
    px, py = points[0]
    for i in range(3):
        px -= tail_dir * size * 0.22
        py -= size * 0.22
        points.append((px, py))
    pygame.draw.lines(screen, color, False, points, 3)
    pygame.draw.circle(screen, color, (int(points[-1][0]), int(points[-1][1])), max(2, int(size * 0.14)))

    for side in (-1, 1):
        claw_x = x + side * size * 0.75
        pygame.draw.line(screen, color, (x + side * size * 0.4, body_rect.centery), (claw_x, body_rect.centery - 3), 2)


def draw_dragonfly(screen, x, y, size, color=(110, 190, 200), facing=1):
    # Head forward, long slender abdomen trailing behind, and two pairs
    # of wings swept back from the thorax just behind the head.
    thorax_x = x + facing * size * 0.35
    tail_x = x - facing * size * 1.05

    pygame.draw.line(screen, color, (thorax_x, y), (tail_x, y), max(1, round(size * 0.13)))
    pygame.draw.circle(screen, color, (thorax_x, y), max(1, size * 0.22))
    pygame.draw.circle(screen, color, (thorax_x + facing * size * 0.28, y), max(1, size * 0.17))

    for dy in (-1, 1):
        for sweep in (0.30, 0.85):
            tip = (thorax_x - facing * size * sweep, y + dy * size * 0.62)
            pygame.draw.line(screen, color, (thorax_x, y), tip, 1)
            wing = pygame.Rect(0, 0, size * 0.34, max(2, size * 0.16))
            wing.center = ((thorax_x + tip[0]) / 2, (y + tip[1]) / 2)
            pygame.draw.ellipse(screen, color, wing, 1)


def draw_jellyfish(screen, x, y, size, color=(220, 170, 230), facing=1):
    bell = pygame.Rect(0, 0, size * 1.5, size * 1.2)
    bell.midtop = (x, y - size * 0.6)
    pygame.draw.ellipse(screen, color, bell)
    for dx in (-0.40, -0.13, 0.13, 0.40):
        pygame.draw.line(
            screen, color,
            (x + dx * size, bell.bottom - 2),
            (x + dx * size * 1.25, bell.bottom + size * 0.9),
            2,
        )


def draw_turtle(screen, x, y, size, color=(90, 150, 110), facing=1):
    shell = pygame.Rect(0, 0, size * 1.6, size)
    shell.center = (x, y)
    pygame.draw.ellipse(screen, color, shell)
    pygame.draw.circle(screen, color, (x + facing * size * 0.95, y), max(2, size * 0.30))
    for dx, dy in ((-0.45, 0.50), (0.35, 0.50)):
        flipper = pygame.Rect(0, 0, size * 0.50, size * 0.28)
        flipper.center = (x + facing * dx * size, y + dy * size)
        pygame.draw.ellipse(screen, color, flipper)
    # A lighter arc hints at the shell's plate seams.
    pygame.draw.arc(screen, (235, 245, 235), shell, 0.4, 2.7, 1)


def draw_starfish(screen, x, ground_y, size, color=(240, 150, 120), facing=1):
    center_y = ground_y - size * 0.5
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = size * 0.6 if i % 2 == 0 else size * 0.26
        points.append((x + math.cos(angle) * radius, center_y + math.sin(angle) * radius))
    pygame.draw.polygon(screen, color, points)


def draw_camel(screen, x, ground_y, size, color=(190, 150, 100), facing=1):
    body = pygame.Rect(0, 0, size * 1.7, size * 0.85)
    body.midbottom = (x, ground_y - size * 0.5)
    pygame.draw.ellipse(screen, color, body)

    for dx in (-0.22, 0.16):
        hump = pygame.Rect(0, 0, size * 0.62, size * 0.55)
        hump.midbottom = (x + dx * size, body.top + size * 0.16)
        pygame.draw.ellipse(screen, color, hump)

    neck_top = (x + facing * size * 0.85, ground_y - size * 1.45)
    pygame.draw.line(screen, color, (x + facing * size * 0.6, body.centery), neck_top, max(2, round(size * 0.22)))
    pygame.draw.circle(screen, color, neck_top, max(2, size * 0.22))

    for dx in (-0.45, -0.15, 0.20, 0.50):
        pygame.draw.line(
            screen, color,
            (x + dx * size, body.bottom - 2),
            (x + dx * size, ground_y),
            max(2, round(size * 0.13)),
        )

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


# --- City / regional landmarks ----------------------------------------


def draw_skyscraper(screen, x, ground_y, size, color, window_color=(255, 224, 150)):
    """A lit office tower. Window rows are what sell it as a city
    building rather than a plain rectangle, so they scale with size.
    """
    width = max(12, size * 0.34)
    body = pygame.Rect(0, 0, width, size)
    body.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, body)

    # A slimmer setback storey on top, plus an antenna.
    cap = pygame.Rect(0, 0, width * 0.55, size * 0.14)
    cap.midbottom = (x, body.top)
    pygame.draw.rect(screen, color, cap)
    pygame.draw.line(screen, color, (x, cap.top), (x, cap.top - size * 0.12), max(1, round(size * 0.02)))
    pygame.draw.circle(screen, (240, 90, 80), (x, cap.top - size * 0.12), max(1, size * 0.025))

    pane = max(2, round(width * 0.16))
    gap_x = max(3, round(width * 0.28))
    gap_y = max(4, round(size * 0.09))
    for row_y in range(int(body.top + gap_y), int(body.bottom - gap_y), int(gap_y)):
        for col_x in range(int(body.left + gap_x * 0.6), int(body.right - pane), int(gap_x)):
            # Deterministic "some lights are off" pattern -- no rng here,
            # so a building looks identical frame to frame.
            if (row_y // gap_y + col_x // gap_x) % 3:
                pygame.draw.rect(screen, window_color, (col_x, row_y, pane, pane))


def draw_tokyo_tower(screen, x, ground_y, size, color=(232, 96, 62), light_color=(255, 226, 150)):
    """The lattice tower silhouette: a wide splayed base narrowing to a
    mast, with two observation decks.
    """
    half = size * 0.30
    waist_y = ground_y - size * 0.52
    tip_y = ground_y - size

    for side in (-1, 1):
        pygame.draw.line(screen, color, (x + side * half, ground_y), (x + side * half * 0.30, waist_y), 3)
        pygame.draw.line(screen, color, (x + side * half * 0.30, waist_y), (x, tip_y + size * 0.14), 2)
    # Cross-bracing, the detail that reads as steel lattice.
    for t in (0.25, 0.5, 0.75):
        y = ground_y - size * 0.52 * t
        w = half * (1 - t * 0.70)
        pygame.draw.line(screen, color, (x - w, y), (x + w, y), 1)

    for deck_t, deck_w in ((0.52, 0.34), (0.78, 0.18)):
        deck = pygame.Rect(0, 0, size * deck_w, size * 0.06)
        deck.center = (x, ground_y - size * deck_t)
        pygame.draw.rect(screen, color, deck)
        pygame.draw.rect(screen, light_color, deck.inflate(-size * 0.06, -size * 0.03))

    pygame.draw.line(screen, color, (x, tip_y + size * 0.14), (x, tip_y), 2)


def draw_machiya(screen, x, ground_y, size, color=(198, 176, 148), roof_color=(72, 66, 66)):
    """A Kyoto townhouse: low, wide, dark tiled roof, warm lattice front."""
    body = pygame.Rect(0, 0, size * 1.25, size * 0.62)
    body.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, body)

    # Wooden lattice (koshi) across the frontage.
    for i in range(1, 8):
        lx = body.left + body.width * i / 8
        pygame.draw.line(screen, roof_color, (lx, body.top + size * 0.12), (lx, body.bottom - size * 0.06), 1)

    pygame.draw.polygon(screen, roof_color, [
        (body.left - size * 0.16, body.top),
        (body.right + size * 0.16, body.top),
        (body.right - size * 0.10, body.top - size * 0.28),
        (body.left + size * 0.10, body.top - size * 0.28),
    ])
    noren = pygame.Rect(0, 0, size * 0.30, size * 0.16)
    noren.midtop = (x, body.top + size * 0.10)
    pygame.draw.rect(screen, (168, 68, 60), noren)


def draw_bamboo(screen, x, ground_y, size, color=(126, 186, 96), node_color=(96, 152, 70)):
    """A bamboo culm: a tall stalk with segment nodes and a few leaves."""
    width = max(3, round(size * 0.10))
    pygame.draw.line(screen, color, (x, ground_y), (x, ground_y - size), width)

    segments = 5
    for i in range(1, segments):
        y = ground_y - size * i / segments
        pygame.draw.line(screen, node_color, (x - width / 2, y), (x + width / 2, y), max(1, width // 3))

    for i, (side, height_t) in enumerate(((-1, 0.62), (1, 0.78), (-1, 0.90))):
        leaf_y = ground_y - size * height_t
        pygame.draw.line(screen, color, (x, leaf_y), (x + side * size * 0.26, leaf_y - size * 0.10), 2)


def draw_maple_tree(screen, x, ground_y, size, color=(214, 88, 58), trunk_color=(92, 68, 56)):
    trunk_top = ground_y - size * 0.48
    pygame.draw.line(screen, trunk_color, (x, ground_y), (x, trunk_top), max(3, round(size * 0.09)))
    for side in (-1, 1):
        pygame.draw.line(
            screen, trunk_color,
            (x, trunk_top + size * 0.06),
            (x + side * size * 0.22, ground_y - size * 0.66),
            max(2, round(size * 0.05)),
        )
    for dx, dy, r in ((0, 0.78, 0.32), (-0.28, 0.66, 0.24), (0.28, 0.66, 0.24), (0, 0.98, 0.20)):
        pygame.draw.circle(screen, color, (x + dx * size, ground_y - dy * size), max(2, r * size))


def draw_lavender(screen, x, ground_y, size, color=(150, 118, 206), stem_color=(110, 148, 96)):
    for dx in (-0.5, 0, 0.5):
        base_x = x + dx * size * 0.5
        top_y = ground_y - size
        pygame.draw.line(screen, stem_color, (base_x, ground_y), (base_x, top_y + size * 0.35), 1)
        # Flower spike: stacked dots tapering toward the tip.
        for i in range(4):
            t = i / 4
            pygame.draw.circle(
                screen, color,
                (base_x, top_y + size * 0.35 * t),
                max(1, size * 0.13 * (1 - t * 0.5)),
            )


def draw_hibiscus(screen, x, ground_y, size, color=(238, 82, 96), center_color=(255, 214, 110)):
    stem_top = ground_y - size * 0.72
    pygame.draw.line(screen, (88, 150, 92), (x, ground_y), (x, stem_top), max(1, round(size * 0.10)))
    for i in range(5):
        angle = -math.pi / 2 + i * 2 * math.pi / 5
        pygame.draw.circle(
            screen, color,
            (x + math.cos(angle) * size * 0.24, stem_top + math.sin(angle) * size * 0.24),
            max(2, size * 0.20),
        )
    pygame.draw.circle(screen, center_color, (x, stem_top), max(1, size * 0.13))
    pygame.draw.line(screen, center_color, (x, stem_top), (x + size * 0.22, stem_top - size * 0.20), 1)


def draw_shisa(screen, x, ground_y, size, color=(206, 186, 158)):
    """An Okinawan shisa guardian lion on a plinth."""
    plinth = pygame.Rect(0, 0, size * 0.62, size * 0.24)
    plinth.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, plinth)

    body = pygame.Rect(0, 0, size * 0.44, size * 0.42)
    body.midbottom = (x, plinth.top)
    pygame.draw.ellipse(screen, color, body)

    head_y = body.top - size * 0.10
    pygame.draw.circle(screen, color, (x, head_y), max(2, size * 0.20))
    for side in (-1, 1):
        pygame.draw.circle(screen, color, (x + side * size * 0.16, head_y - size * 0.14), max(1, size * 0.08))
        pygame.draw.circle(screen, (60, 50, 46), (x + side * size * 0.07, head_y - size * 0.02), max(1, size * 0.03))
    # Open mouth -- the shisa that keeps good spirits in.
    pygame.draw.circle(screen, (110, 70, 60), (x, head_y + size * 0.10), max(1, size * 0.05))
    pygame.draw.line(screen, color, (x + size * 0.20, body.centery), (x + size * 0.34, body.top), 2)


def draw_snowflake(screen, x, y, size, color=(255, 255, 255)):
    for i in range(3):
        angle = i * math.pi / 3
        dx, dy = math.cos(angle) * size, math.sin(angle) * size
        pygame.draw.line(screen, color, (x - dx, y - dy), (x + dx, y + dy), 1)


def draw_maple_leaf(screen, x, y, size, color=(226, 112, 62)):
    """A drifting momiji leaf -- a small five-lobed star."""
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = size if i % 2 == 0 else size * 0.42
        points.append((x + math.cos(angle) * r, y + math.sin(angle) * r))
    pygame.draw.polygon(screen, color, points)


def draw_crane(screen, x, y, size, color=(250, 250, 250), facing=1):
    """A red-crowned crane in flight: long neck forward, long legs
    trailing behind -- the silhouette that makes a crane a crane.
    """
    body = pygame.Rect(0, 0, size * 1.1, size * 0.46)
    body.center = (x, y)
    pygame.draw.ellipse(screen, color, body)

    neck_tip = (x + facing * size * 1.05, y - size * 0.26)
    pygame.draw.line(screen, color, (x + facing * size * 0.42, y - size * 0.05), neck_tip, max(1, round(size * 0.11)))
    pygame.draw.circle(screen, (216, 62, 58), neck_tip, max(1, size * 0.10))

    for dy in (-1, 1):
        pygame.draw.polygon(screen, color, [
            (x, y),
            (x - facing * size * 0.34, y + dy * size * 0.72),
            (x + facing * size * 0.30, y + dy * size * 0.30),
        ])
    pygame.draw.line(screen, (60, 56, 52), (x - facing * size * 0.5, y + size * 0.10),
                     (x - facing * size * 1.15, y + size * 0.24), max(1, round(size * 0.07)))


def draw_plane(screen, x, y, size, color=(238, 240, 246), facing=1):
    fuselage = pygame.Rect(0, 0, size * 2.0, size * 0.34)
    fuselage.center = (x, y)
    pygame.draw.ellipse(screen, color, fuselage)
    pygame.draw.polygon(screen, color, [
        (x, y), (x - facing * size * 0.30, y - size * 0.62), (x + facing * size * 0.16, y - size * 0.04),
    ])
    pygame.draw.polygon(screen, color, [
        (x, y), (x - facing * size * 0.30, y + size * 0.62), (x + facing * size * 0.16, y + size * 0.04),
    ])
    pygame.draw.polygon(screen, color, [
        (x - facing * size * 0.86, y), (x - facing * size * 1.06, y - size * 0.44),
        (x - facing * size * 0.70, y - size * 0.04),
    ])


def draw_fox(screen, x, ground_y, size, color=(214, 128, 62), tip_color=(250, 246, 240), facing=1):
    """An Inari fox / Ezo red fox: pointed ears, bushy white-tipped tail."""
    body = pygame.Rect(0, 0, size * 0.98, size * 0.42)
    body.midbottom = (x, ground_y - size * 0.18)
    pygame.draw.ellipse(screen, color, body)

    for dx in (-0.34, -0.12, 0.16, 0.34):
        pygame.draw.line(
            screen, color,
            (x + dx * size, body.bottom - 2), (x + dx * size, ground_y),
            max(2, round(size * 0.10)),
        )

    # Bushy tail, angled up and back, with the white tip on its far edge.
    tail_x = x - facing * size * 0.52
    tail_y = body.centery - size * 0.10
    pygame.draw.circle(screen, color, (tail_x, tail_y), max(2, size * 0.21))
    pygame.draw.circle(
        screen, tip_color,
        (tail_x - facing * size * 0.15, tail_y - size * 0.10), max(1, size * 0.10),
    )

    head_x = x + facing * size * 0.44
    head_y = body.top - size * 0.03
    pygame.draw.circle(screen, color, (head_x, head_y), max(2, size * 0.21))
    # Snout.
    pygame.draw.polygon(screen, color, [
        (head_x + facing * size * 0.10, head_y - size * 0.02),
        (head_x + facing * size * 0.40, head_y + size * 0.08),
        (head_x + facing * size * 0.10, head_y + size * 0.14),
    ])
    # Two upright pointed ears.
    for offset in (-0.13, 0.11):
        base_x = head_x + facing * offset * size
        pygame.draw.polygon(screen, color, [
            (base_x, head_y - size * 0.14),
            (base_x + facing * size * 0.05, head_y - size * 0.40),
            (base_x + facing * size * 0.13, head_y - size * 0.12),
        ])
    pygame.draw.circle(
        screen, (56, 44, 40),
        (head_x + facing * size * 0.10, head_y), max(1, size * 0.035),
    )


def draw_tiki_totem(screen, x, ground_y, size, color=(150, 100, 60), carve_color=(90, 56, 32)):
    """A stacked tropical tiki totem: two carved faces on a wooden post."""
    post = pygame.Rect(0, 0, size * 0.42, size)
    post.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, post, border_radius=4)

    for t in (0.28, 0.72):
        face_y = post.bottom - size * t
        pygame.draw.circle(screen, carve_color, (x - size * 0.10, face_y), max(1, size * 0.05))
        pygame.draw.circle(screen, carve_color, (x + size * 0.10, face_y), max(1, size * 0.05))
        pygame.draw.arc(screen, carve_color, (x - size * 0.16, face_y, size * 0.32, size * 0.20), 3.5, 6.0, 2)
    pygame.draw.line(screen, carve_color, (post.left, ground_y - size * 0.5), (post.right, ground_y - size * 0.5), 2)


def draw_parrot(screen, x, y, size, color=(60, 190, 90), facing=1):
    """A bright macaw with a curved beak and a long trailing tail feather."""
    body = pygame.Rect(0, 0, size * 1.0, size * 0.6)
    body.center = (x, y)
    pygame.draw.ellipse(screen, color, body)

    head_x = x + facing * size * 0.42
    pygame.draw.circle(screen, color, (head_x, y - size * 0.16), max(2, size * 0.24))
    pygame.draw.polygon(screen, (230, 170, 40), [
        (head_x + facing * size * 0.18, y - size * 0.14),
        (head_x + facing * size * 0.42, y - size * 0.04),
        (head_x + facing * size * 0.18, y),
    ])
    tail_color = (230, 90, 70)
    pygame.draw.polygon(screen, tail_color, [
        (x - facing * size * 0.42, y),
        (x - facing * size * 1.05, y - size * 0.16),
        (x - facing * size * 1.0, y + size * 0.20),
    ])
    pygame.draw.line(screen, (255, 220, 90), (x - facing * size * 0.1, y), (x - facing * size * 0.55, y - size * 0.30), 2)


def draw_castle(screen, x, ground_y, size, color=(210, 190, 220), roof_color=(150, 70, 140)):
    """A fairy-tale castle: a wide keep with two flanking round towers,
    each topped by a pointed cone roof and a tiny pennant.
    """
    body = pygame.Rect(0, 0, size * 1.3, size * 0.72)
    body.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, body)

    for side in (-1, 1):
        tower = pygame.Rect(0, 0, size * 0.32, size * 0.95)
        tower.midbottom = (x + side * size * 0.62, ground_y)
        pygame.draw.rect(screen, color, tower)
        cone = [(tower.left - 3, tower.top), (tower.right + 3, tower.top), (tower.centerx, tower.top - size * 0.38)]
        pygame.draw.polygon(screen, roof_color, cone)
        pygame.draw.line(screen, roof_color, (tower.centerx, cone[2][1]), (tower.centerx, cone[2][1] - size * 0.14), 2)

    keep_cone = [(body.left - 4, body.top), (body.right + 4, body.top), (body.centerx, body.top - size * 0.26)]
    pygame.draw.polygon(screen, roof_color, keep_cone)

    door = pygame.Rect(0, 0, size * 0.20, size * 0.34)
    door.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, (90, 60, 44), door)
    for wx in (-0.4, 0.4):
        window = pygame.Rect(0, 0, size * 0.08, size * 0.10)
        window.center = (x + wx * size * 0.62, body.top + size * 0.28)
        pygame.draw.rect(screen, (255, 236, 150), window)


def draw_giant_mushroom(screen, x, ground_y, size, color=(226, 100, 120), spot_color=(255, 250, 240)):
    """An oversized storybook toadstool with a round little door in the
    stem -- the "someone lives here" touch that sells the fairy tale.
    """
    stem = pygame.Rect(0, 0, size * 0.46, size * 0.6)
    stem.midbottom = (x, ground_y)
    pygame.draw.rect(screen, spot_color, stem, border_radius=8)

    door = pygame.Rect(0, 0, size * 0.20, size * 0.26)
    door.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, (120, 80, 60), door)

    cap = pygame.Rect(0, 0, size * 1.15, size * 0.62)
    cap.midbottom = (x, stem.top + size * 0.08)
    pygame.draw.ellipse(screen, color, cap)
    for dx, dy in ((-0.32, -0.10), (0.30, -0.14), (0, -0.24), (-0.05, 0.05), (0.15, 0.10)):
        pygame.draw.circle(screen, spot_color, (x + dx * size, cap.centery + dy * size), max(2, size * 0.09))


def draw_wishing_well(screen, x, ground_y, size, color=(150, 130, 110), roof_color=(150, 60, 60)):
    base = pygame.Rect(0, 0, size * 0.7, size * 0.4)
    base.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, color, base)
    pygame.draw.rect(screen, color, (base.left, base.top, base.width, base.height / 2))

    for side in (-1, 1):
        post = pygame.Rect(0, 0, size * 0.08, size * 0.5)
        post.midbottom = (x + side * size * 0.32, base.top + size * 0.05)
        pygame.draw.rect(screen, (110, 90, 70), post)

    roof = [(x - size * 0.42, base.top - size * 0.42), (x + size * 0.42, base.top - size * 0.42), (x, base.top - size * 0.68)]
    pygame.draw.polygon(screen, roof_color, roof)
    pygame.draw.line(screen, (70, 60, 50), (x, base.top - size * 0.05), (x, base.top - size * 0.36), 1)


def draw_fairy(screen, x, y, size, color=(255, 220, 130), facing=1):
    """A small glowing sprite: a round body, a soft halo of light, and
    two translucent wings -- reads as magical rather than as an insect.
    """
    glow_radius = size * 0.9
    glow = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*color, 70), (glow_radius, glow_radius), glow_radius)
    screen.blit(glow, (x - glow_radius, y - glow_radius))

    for side in (-1, 1):
        wing = pygame.Rect(0, 0, size * 0.5, size * 0.7)
        wing.center = (x + side * size * 0.32, y)
        pygame.draw.ellipse(screen, (255, 255, 255), wing, width=1)
    pygame.draw.circle(screen, color, (x, y), max(2, size * 0.22))


def draw_big_ben(screen, x, ground_y, size, color=(180, 156, 96), face_color=(250, 246, 220)):
    """The Elizabeth Tower: a tall tan clock tower with a pointed spire
    and a lit clock face -- London's single most recognizable landmark.
    """
    tower = pygame.Rect(0, 0, size * 0.34, size)
    tower.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, tower)

    clock_y = tower.top + size * 0.18
    pygame.draw.circle(screen, face_color, (x, clock_y), max(3, size * 0.13))
    pygame.draw.circle(screen, (40, 34, 26), (x, clock_y), max(3, size * 0.13), width=2)
    pygame.draw.line(screen, (40, 34, 26), (x, clock_y), (x, clock_y - size * 0.08), 1)
    pygame.draw.line(screen, (40, 34, 26), (x, clock_y), (x + size * 0.06, clock_y), 1)

    spire = [(tower.left - 2, tower.top), (tower.right + 2, tower.top), (x, tower.top - size * 0.3)]
    pygame.draw.polygon(screen, (110, 96, 64), spire)
    pygame.draw.line(screen, (110, 96, 64), (x, spire[2][1]), (x, spire[2][1] - size * 0.08), 2)


def draw_phone_booth(screen, x, ground_y, size, color=(196, 40, 40)):
    """A red British telephone box."""
    body = pygame.Rect(0, 0, size * 0.5, size)
    body.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, body, border_radius=2)

    roof = pygame.Rect(0, 0, size * 0.58, size * 0.10)
    roof.midbottom = (x, body.top + 2)
    pygame.draw.rect(screen, color, roof)

    pane_color = (220, 235, 235)
    for row in range(3):
        for col in (-1, 1):
            pane = pygame.Rect(0, 0, size * 0.14, size * 0.16)
            pane.center = (x + col * size * 0.13, body.top + size * 0.18 + row * size * 0.20)
            pygame.draw.rect(screen, pane_color, pane)
    pygame.draw.rect(screen, (240, 240, 220), (body.centerx - size * 0.02, body.top + size * 0.55, size * 0.04, size * 0.3))


def draw_double_decker_bus(screen, x, ground_y, size, color=(196, 40, 40)):
    """A red London double-decker, parked at the roadside."""
    body = pygame.Rect(0, 0, size * 1.4, size * 0.62)
    body.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, body, border_radius=4)
    pygame.draw.line(screen, (150, 30, 30), (body.left, body.centery), (body.right, body.centery), 2)

    window_color = (220, 235, 245)
    for row_y in (body.top + size * 0.08, body.centery + size * 0.08):
        for i in range(4):
            window = pygame.Rect(0, 0, size * 0.18, size * 0.14)
            window.topleft = (body.left + size * 0.12 + i * size * 0.28, row_y)
            pygame.draw.rect(screen, window_color, window)

    for wheel_dx in (-0.45, 0.45):
        pygame.draw.circle(screen, (30, 30, 30), (x + wheel_dx * size, body.bottom), max(2, size * 0.11))


def draw_statue_of_liberty(screen, x, ground_y, size, color=(110, 170, 150)):
    """A simplified Lady Liberty: pedestal, robed figure, raised torch arm."""
    pedestal = pygame.Rect(0, 0, size * 0.4, size * 0.26)
    pedestal.midbottom = (x, ground_y)
    pygame.draw.rect(screen, (150, 140, 120), pedestal)

    body = pygame.Rect(0, 0, size * 0.34, size * 0.62)
    body.midbottom = (x, pedestal.top)
    pygame.draw.ellipse(screen, color, body)

    head_y = body.top - size * 0.02
    pygame.draw.circle(screen, color, (x, head_y), max(2, size * 0.10))
    for i in range(5):
        angle = -math.pi / 2 - math.pi / 5 + i * math.pi / 10
        tip = (x + math.cos(angle) * size * 0.16, head_y + math.sin(angle) * size * 0.16 - size * 0.02)
        pygame.draw.line(screen, color, (x, head_y), tip, 1)

    arm_top = (x + size * 0.22, body.top - size * 0.22)
    pygame.draw.line(screen, color, (x + size * 0.12, body.top + size * 0.05), arm_top, max(2, round(size * 0.05)))
    pygame.draw.line(screen, (200, 170, 90), arm_top, (arm_top[0], arm_top[1] - size * 0.14), 2)
    pygame.draw.circle(screen, (230, 200, 110), (arm_top[0], arm_top[1] - size * 0.17), max(1, size * 0.05))


def draw_yellow_cab(screen, x, ground_y, size, color=(240, 200, 40)):
    """A New York yellow taxi cab, low and boxy."""
    body = pygame.Rect(0, 0, size * 1.3, size * 0.42)
    body.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, body, border_radius=6)

    cabin = pygame.Rect(0, 0, size * 0.7, size * 0.28)
    cabin.midbottom = (x, body.top + 2)
    pygame.draw.rect(screen, color, cabin, border_radius=4)
    pygame.draw.rect(screen, (200, 225, 235), cabin.inflate(-size * 0.10, -size * 0.10))

    pygame.draw.rect(screen, (30, 30, 30), (body.centerx - size * 0.10, cabin.top - size * 0.05, size * 0.2, size * 0.05))
    for wheel_dx in (-0.42, 0.42):
        pygame.draw.circle(screen, (25, 25, 25), (x + wheel_dx * size, body.bottom), max(2, size * 0.10))


def draw_hanok(screen, x, ground_y, size, color=(230, 220, 200), roof_color=(60, 90, 100)):
    """A traditional Korean hanok house, with the sweeping curved-eave
    tiled roof that distinguishes it from Japan's machiya/pagoda silhouettes.
    """
    body = pygame.Rect(0, 0, size * 1.1, size * 0.5)
    body.midbottom = (x, ground_y)
    pygame.draw.rect(screen, color, body)

    for i in range(1, 5):
        lx = body.left + body.width * i / 5
        pygame.draw.line(screen, (150, 110, 70), (lx, body.top), (lx, body.bottom), 1)

    roof_points = [
        (body.left - size * 0.30, body.top + size * 0.06),
        (x, body.top - size * 0.30),
        (body.right + size * 0.30, body.top + size * 0.06),
        (body.right + size * 0.10, body.top + size * 0.14),
        (x, body.top - size * 0.14),
        (body.left - size * 0.10, body.top + size * 0.14),
    ]
    pygame.draw.polygon(screen, roof_color, roof_points)


def draw_palace_gate(screen, x, ground_y, size, color=(200, 60, 50), roof_color=(50, 100, 90)):
    """A Korean palace gate (like Gwanghwamun): a stone base pierced by
    an arch, two vermillion pillars, and a dark tiled crossbeam roof.
    """
    base = pygame.Rect(0, 0, size * 1.0, size * 0.30)
    base.midbottom = (x, ground_y)
    pygame.draw.rect(screen, (150, 140, 130), base)

    arch = pygame.Rect(0, 0, size * 0.42, size * 0.30)
    arch.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, (60, 50, 46), arch)

    for side in (-1, 1):
        pillar = pygame.Rect(0, 0, size * 0.10, size * 0.62)
        pillar.midbottom = (x + side * size * 0.42, base.top)
        pygame.draw.rect(screen, color, pillar)

    roof = pygame.Rect(0, 0, size * 1.2, size * 0.14)
    roof.midbottom = (x, base.top - size * 0.62 + size * 0.06)
    pygame.draw.rect(screen, roof_color, roof)
    eave = [(roof.left - size * 0.14, roof.bottom), (roof.left, roof.top), (roof.right, roof.top), (roof.right + size * 0.14, roof.bottom)]
    pygame.draw.polygon(screen, roof_color, eave)


def draw_paper_lantern(screen, x, ground_y, size, color=(230, 90, 70)):
    """A round Korean paper lantern (cheongsachorong-style), hung from a
    short post -- warm color pop against a hanok village street.
    """
    post = pygame.Rect(0, 0, max(2, size * 0.06), size * 0.5)
    post.midbottom = (x, ground_y)
    pygame.draw.rect(screen, (90, 70, 55), post)

    body_center = (x, post.top - size * 0.20)
    pygame.draw.circle(screen, color, body_center, max(3, size * 0.20))
    pygame.draw.circle(screen, (255, 230, 200), body_center, max(3, size * 0.20), width=1)
    pygame.draw.line(screen, (90, 70, 55), (x, post.top), body_center, 1)
    pygame.draw.line(screen, (255, 220, 150), body_center, (x, body_center[1] - size * 0.32), 1)


def draw_snow_monkey(screen, x, ground_y, size, color=(176, 158, 148), face_color=(228, 138, 130), facing=1):
    """A Jigokudani macaque, sitting the way they do in the onsen.

    Symmetrical, so `facing` is ignored -- it's accepted only to match
    the creature drawing signature Background calls every shape with.
    """
    body = pygame.Rect(0, 0, size * 0.86, size * 0.70)
    body.midbottom = (x, ground_y)
    pygame.draw.ellipse(screen, color, body)

    head_y = body.top - size * 0.04
    pygame.draw.circle(screen, color, (x, head_y), max(2, size * 0.30))
    for side in (-1, 1):
        pygame.draw.circle(screen, color, (x + side * size * 0.30, head_y), max(1, size * 0.11))
    pygame.draw.circle(screen, face_color, (x, head_y + size * 0.04), max(1, size * 0.19))
    for side in (-1, 1):
        pygame.draw.circle(screen, (50, 44, 42), (x + side * size * 0.08, head_y - size * 0.01), max(1, size * 0.035))

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
    for side in (-1, 1):
        wing_rect = pygame.Rect(0, 0, size * 0.8, size)
        wing_rect.center = (x + side * size * 0.35, y)
        pygame.draw.ellipse(screen, color, wing_rect)
    pygame.draw.line(screen, (60, 50, 40), (x, y - size * 0.5), (x, y + size * 0.5), 2)


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

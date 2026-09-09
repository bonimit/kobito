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


def draw_bird(screen, x, y, size, color=(70, 60, 60)):
    pygame.draw.arc(screen, color, (x - size, y - size / 2, size, size), 0.3, 2.8, 2)
    pygame.draw.arc(screen, color, (x, y - size / 2, size, size), 0.3, 2.8, 2)


def draw_fish(screen, x, y, size, color=(230, 140, 90)):
    body_rect = pygame.Rect(0, 0, size * 1.6, size)
    body_rect.center = (x, y)
    pygame.draw.ellipse(screen, color, body_rect)
    tail = [(body_rect.left + 2, y), (body_rect.left - size * 0.5, y - size * 0.4), (body_rect.left - size * 0.5, y + size * 0.4)]
    pygame.draw.polygon(screen, color, tail)
    pygame.draw.circle(screen, (30, 30, 30), (int(body_rect.right - size * 0.3), int(y)), max(1, int(size * 0.08)))

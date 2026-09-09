import random

import pygame

CLOUD_COLOR = (255, 255, 255)

MOUNTAIN_COLOR = (150, 178, 195)
HILL_FAR_COLOR = (139, 191, 141)
HILL_NEAR_COLOR = (104, 172, 108)

TREE_TRUNK_COLOR = (92, 64, 40)
TREE_LEAF_COLORS = [(36, 100, 53), (46, 125, 66), (58, 145, 80)]
TREE_MARGIN = 30  # keep trees clear of a segment's edges (and the gap)
TREE_SPACING_RANGE = (90, 150)

BUSH_COLORS = [(52, 130, 68), (66, 145, 80)]
BUSH_SPACING_RANGE = (55, 95)

FLOWER_COLORS = [(255, 255, 255), (255, 214, 90), (255, 150, 180)]
FLOWER_SPACING_RANGE = (40, 80)

# Parallax factor = how fast a layer scrolls relative to the camera.
# Lower = further away / drifts less as the camera moves -- stacking
# several layers at different factors (mountains slowest, then hills,
# then clouds, then trees/bushes/flowers at full speed since they're
# rooted in the actual ground) is what sells depth.
MOUNTAIN_PARALLAX = 0.1
HILL_FAR_PARALLAX = 0.2
HILL_NEAR_PARALLAX = 0.4
CLOUD_PARALLAX = 0.25


class Background:
    """Non-interactive scenery drawn behind the level, back to front:
    distant mountains, two rolling-hill layers, clouds, then trees /
    bushes / flowers rooted in the actual ground. Purely decorative --
    no collision, no gameplay effect.
    """

    def __init__(self, level_width, ground_y, ground_segments_px, seed=7):
        rng = random.Random(seed)  # fixed seed: same layout every run

        self.level_width = level_width
        self.ground_y = ground_y

        self.mountains = self._place_bumps(level_width, rng, spacing=(200, 280), radius=(90, 140))
        self.hills_far = self._place_bumps(level_width, rng, spacing=(160, 240), radius=(60, 90))
        self.hills_near = self._place_bumps(level_width, rng, spacing=(120, 190), radius=(38, 58))

        self.clouds = [
            (rng.randint(0, level_width), rng.randint(30, 170), rng.randint(26, 46))
            for _ in range(level_width // 260)
        ]

        self.trees = self._place_on_ground(ground_segments_px, rng, TREE_SPACING_RANGE, TREE_MARGIN)
        self.bushes = self._place_on_ground(ground_segments_px, rng, BUSH_SPACING_RANGE, 20)
        self.flowers = self._place_on_ground(ground_segments_px, rng, FLOWER_SPACING_RANGE, 15)

    def _place_bumps(self, level_width, rng, spacing, radius):
        # A continuous rolling silhouette, built from overlapping circles
        # spaced closely enough that they never gap. Covers the full
        # level width (plus a little extra) regardless of ground gaps --
        # these layers are a distant backdrop, not literal ground.
        bumps = []
        x = -100
        while x < level_width + 100:
            bumps.append((x, rng.randint(*radius)))
            x += rng.randint(*spacing)
        return bumps

    def _place_on_ground(self, ground_segments_px, rng, spacing_range, margin):
        placed = []
        for start_x, end_x in ground_segments_px:
            x = start_x + margin
            while x < end_x - margin:
                if x > 40:  # keep clear of the player spawn / HUD area
                    placed.append(x)
                x += rng.randint(*spacing_range)
        return placed

    def draw(self, screen, camera_x):
        screen_width = screen.get_width()

        # Each layer's circle center sits progressively closer to the
        # ground line, but never *at* it -- keeping most of the circle
        # above ground_y means only a sliver dips below where there's no
        # platform to cover it (e.g. over a gap), reading as a hill
        # meeting the horizon rather than a disc floating in the pit.
        self._draw_bumps(screen, self.mountains, camera_x, MOUNTAIN_PARALLAX, MOUNTAIN_COLOR, self.ground_y - 60)
        self._draw_bumps(screen, self.hills_far, camera_x, HILL_FAR_PARALLAX, HILL_FAR_COLOR, self.ground_y - 35)
        self._draw_bumps(screen, self.hills_near, camera_x, HILL_NEAR_PARALLAX, HILL_NEAR_COLOR, self.ground_y - 18)

        for x, y, size in self.clouds:
            draw_x = self._wrapped_x(x, camera_x, CLOUD_PARALLAX, screen_width)
            self._draw_cloud(screen, draw_x, y, size)

        for i, x in enumerate(self.bushes):
            draw_x = x - camera_x
            if -40 < draw_x < screen_width + 40:
                self._draw_bush(screen, draw_x, BUSH_COLORS[i % len(BUSH_COLORS)])

        for i, x in enumerate(self.flowers):
            draw_x = x - camera_x
            if -20 < draw_x < screen_width + 20:
                self._draw_flower(screen, draw_x, FLOWER_COLORS[i % len(FLOWER_COLORS)])

        for i, x in enumerate(self.trees):
            draw_x = x - camera_x
            if -80 < draw_x < screen_width + 80:
                height = 44 + (i * 37) % 29  # deterministic per-tree variation, no extra state needed
                color = TREE_LEAF_COLORS[i % len(TREE_LEAF_COLORS)]
                self._draw_tree(screen, draw_x, height, color)

    def _wrapped_x(self, world_x, camera_x, parallax, screen_width):
        # Wrapping with % lets a sparse layer still cover an arbitrarily
        # wide level without needing one entry per screen-width.
        span = self.level_width + screen_width
        return (world_x - camera_x * parallax) % span - screen_width / 2

    def _draw_bumps(self, screen, bumps, camera_x, parallax, color, base_y):
        screen_width = screen.get_width()
        for x, radius in bumps:
            draw_x = self._wrapped_x(x, camera_x, parallax, screen_width)
            if -radius < draw_x < screen_width + radius:
                pygame.draw.circle(screen, color, (draw_x, base_y), radius)

    def _draw_cloud(self, screen, x, y, size):
        pygame.draw.ellipse(screen, CLOUD_COLOR, (x, y, size * 1.6, size))
        pygame.draw.ellipse(screen, CLOUD_COLOR, (x + size * 0.5, y - size * 0.35, size * 1.2, size * 0.9))
        pygame.draw.ellipse(screen, CLOUD_COLOR, (x + size * 1.0, y, size * 1.0, size * 0.75))

    def _draw_tree(self, screen, x, height, leaf_color):
        trunk_w, trunk_h = 10, 22
        trunk_rect = pygame.Rect(0, 0, trunk_w, trunk_h)
        trunk_rect.midbottom = (x, self.ground_y)
        pygame.draw.rect(screen, TREE_TRUNK_COLOR, trunk_rect)

        # Three stacked triangles of shrinking width read as a simple
        # pine tree silhouette at this pixel-art scale.
        tiers = [(height, 1.0), (height * 0.7, 0.75), (height * 0.4, 0.5)]
        base_y = trunk_rect.top + 6
        for tier_height, width_scale in tiers:
            tier_width = height * width_scale
            top = (x, base_y - tier_height)
            left = (x - tier_width / 2, base_y)
            right = (x + tier_width / 2, base_y)
            pygame.draw.polygon(screen, leaf_color, [top, left, right])
            base_y -= tier_height * 0.45

    def _draw_bush(self, screen, x, color):
        base_y = self.ground_y
        for dx, dy, r in ((-8, 0, 9), (8, 0, 9), (0, -6, 10)):
            pygame.draw.circle(screen, color, (x + dx, base_y + dy), r)

    def _draw_flower(self, screen, x, petal_color):
        stem_top = self.ground_y - 12
        pygame.draw.line(screen, (58, 130, 66), (x, self.ground_y), (x, stem_top), 2)
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            pygame.draw.circle(screen, petal_color, (x + dx, stem_top + dy), 2)
        pygame.draw.circle(screen, (255, 214, 90), (x, stem_top), 2)

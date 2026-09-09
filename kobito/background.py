import random

import pygame

CLOUD_COLOR = (255, 255, 255)
TREE_TRUNK_COLOR = (92, 64, 40)
TREE_LEAF_COLORS = [(36, 100, 53), (46, 125, 66), (58, 145, 80)]

# How much slower each layer scrolls than the camera. Lower = further
# away / drifts less as the camera moves -- this difference in scroll
# speed between layers is what reads as depth ("parallax").
CLOUD_PARALLAX = 0.25
TREE_PARALLAX = 0.6


class Background:
    """Non-interactive scenery drawn behind the level: clouds and pine
    trees. Purely decorative -- no collision, no gameplay effect.
    """

    def __init__(self, level_width, ground_y, seed=7):
        rng = random.Random(seed)  # fixed seed: same layout every run

        self.level_width = level_width
        self.ground_y = ground_y
        self.clouds = [
            (rng.randint(0, level_width), rng.randint(30, 170), rng.randint(26, 46))
            for _ in range(level_width // 260)
        ]
        self.trees = [
            (x, rng.randint(44, 72), rng.choice(TREE_LEAF_COLORS))
            for x in range(60, level_width, rng.randint(150, 230))
        ]

    def draw(self, screen, camera_x):
        for x, y, size in self.clouds:
            draw_x = self._parallax_x(x, camera_x, CLOUD_PARALLAX, screen.get_width())
            self._draw_cloud(screen, draw_x, y, size)

        for x, height, color in self.trees:
            draw_x = self._parallax_x(x, camera_x, TREE_PARALLAX, screen.get_width())
            if -80 < draw_x < screen.get_width() + 80:
                self._draw_tree(screen, draw_x, height, color)

    def _parallax_x(self, world_x, camera_x, parallax, screen_width):
        # Scrolling a layer by less than the camera moved makes it
        # appear to lag behind -- i.e. further away. Wrapping with %
        # lets a sparse set of decorations still cover an arbitrarily
        # wide level without needing one entry per screen-width.
        span = self.level_width + screen_width
        return (world_x - camera_x * parallax) % span - screen_width / 2

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

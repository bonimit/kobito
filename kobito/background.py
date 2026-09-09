import random

import pygame

from kobito.constants import SCREEN_HEIGHT, SCREEN_WIDTH


def _build_sky_surface(top_color, bottom_color):
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    if top_color == bottom_color:
        surface.fill(top_color)
        return surface

    for y in range(SCREEN_HEIGHT):
        t = y / (SCREEN_HEIGHT - 1)
        color = tuple(round(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        pygame.draw.line(surface, color, (0, y), (SCREEN_WIDTH, y))
    return surface


class Background:
    """Renders one world Theme's scenery: a sky gradient, several
    rolling-silhouette layers (mountains/dunes/reef/...), a "floaty"
    layer (clouds/stars/bubbles/...), and ground-rooted props (trees/
    cacti/coral/...). None of this is theme-specific code -- everything
    about *what* a theme looks like lives in kobito/themes.py; this
    class only knows how to place and scroll whatever it's handed.

    Purely decorative -- no collision, no gameplay effect.
    """

    def __init__(self, level_width, ground_y, ground_segments_px, theme, seed=7):
        rng = random.Random(seed)  # fixed seed: same layout every run

        self.level_width = level_width
        self.ground_y = ground_y
        self.theme = theme
        self.sky_surface = _build_sky_surface(theme.sky_top, theme.sky_bottom)

        self.bumps = [
            (layer, self._place_bumps(level_width, rng, layer.spacing, layer.radius))
            for layer in theme.bump_layers
        ]
        self.floaties = [
            (layer, self._place_floaties(level_width, rng, layer))
            for layer in theme.floaty_layers
        ]
        self.ground_props = [
            (prop, self._place_on_ground(ground_segments_px, rng, prop.spacing_range, prop.margin))
            for prop in theme.ground_props
        ]

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

    def _place_floaties(self, level_width, rng, layer):
        count = layer.count(level_width)
        items = []
        for i in range(count):
            x = rng.randint(0, level_width) if count > 1 else level_width // 2
            y = rng.randint(*layer.y_range)
            size = rng.randint(*layer.size_range)
            color = layer.colors[i % len(layer.colors)]
            items.append((x, y, size, color))
        return items

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
        screen.blit(self.sky_surface, (0, 0))
        screen_width = screen.get_width()

        # Each bump layer's circle center sits progressively closer to
        # the ground line the nearer it is, but never *at* it -- keeping
        # most of the circle above ground_y means only a sliver dips
        # below where there's no platform to cover it (e.g. over a gap),
        # reading as landscape meeting the horizon rather than a shape
        # floating in the pit.
        for layer, bumps in self.bumps:
            base_y = self.ground_y - layer.base_offset
            for x, radius in bumps:
                draw_x = self._wrapped_x(x, camera_x, layer.parallax, screen_width)
                if -radius < draw_x < screen_width + radius:
                    pygame.draw.circle(screen, layer.color, (draw_x, base_y), radius)

        for layer, items in self.floaties:
            for x, y, size, color in items:
                draw_x = self._wrapped_x(x, camera_x, layer.parallax, screen_width)
                if -size * 2 < draw_x < screen_width + size * 2:
                    layer.draw_fn(screen, draw_x, y, size, color)

        for prop, positions in self.ground_props:
            for i, x in enumerate(positions):
                draw_x = x - camera_x  # rooted in the ground: scrolls in lockstep with the camera
                if -80 < draw_x < screen_width + 80:
                    size = prop.size_range[0] + (i * 37) % max(1, prop.size_range[1] - prop.size_range[0])
                    color = prop.colors[i % len(prop.colors)]
                    prop.draw_fn(screen, draw_x, self.ground_y, size, color)

    def _wrapped_x(self, world_x, camera_x, parallax, screen_width):
        # Wrapping with % lets a sparse layer still cover an arbitrarily
        # wide level without needing one entry per screen-width.
        span = self.level_width + screen_width
        return (world_x - camera_x * parallax) % span - screen_width / 2

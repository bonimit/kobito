import math
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
    layer (clouds/stars/bubbles/...), ground-rooted props (trees/cacti/
    coral/...), and living creatures that actually move over time
    (birds, fish, crabs, ...). None of this is theme-specific code --
    everything about *what* a theme looks like lives in
    kobito/themes.py; this class only knows how to place, scroll, and
    animate whatever it's handed.

    Purely decorative -- no collision, no gameplay effect. Call
    update(dt) once per frame (to advance creature motion) before draw().
    """

    def __init__(self, level_width, ground_y, ground_segments_px, theme, seed=7):
        rng = random.Random(seed)  # fixed seed: same layout every run

        self.level_width = level_width
        self.ground_y = ground_y
        self.ground_segments_px = ground_segments_px
        self.theme = theme
        self.sky_surface = _build_sky_surface(theme.sky_top, theme.sky_bottom)

        self.far = [
            (layer, self._place_floaties(level_width, rng, layer))
            for layer in theme.far_layers
        ]
        self.mid = [
            (layer, self._place_floaties(level_width, rng, layer))
            for layer in theme.mid_layers
        ]
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
        self.flying_creatures = [
            (creature, self._place_flying_creatures(level_width, rng, creature))
            for creature in theme.flying_creatures
        ]
        self.ground_creatures = [
            (creature, self._place_ground_creatures(ground_segments_px, rng, creature))
            for creature in theme.ground_creatures
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
            if layer.screen_x:
                x = rng.randint(*layer.screen_x) + SCREEN_WIDTH // 2   # see _wrapped_x
            else:
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

    def _place_flying_creatures(self, level_width, rng, creature):
        instances = []
        for i in range(creature.count(level_width)):
            speed = rng.uniform(*creature.speed_range)
            instances.append({
                "x": rng.uniform(0, level_width),
                "y_base": rng.randint(*creature.y_range),
                "size": rng.randint(*creature.size_range),
                "color": creature.colors[i % len(creature.colors)],
                "vx": speed if rng.random() < 0.5 else -speed,
                "phase": rng.uniform(0, 2 * math.pi),
            })
        return instances

    def _place_ground_creatures(self, ground_segments_px, rng, creature):
        if not ground_segments_px:
            return []

        instances = []
        for i in range(creature.count(self.level_width)):
            seg_start, seg_end = rng.choice(ground_segments_px)
            patrol_width = min(rng.randint(*creature.patrol_width_range), max(20, seg_end - seg_start - 40))
            usable_start, usable_end = seg_start + 20, seg_end - 20
            if usable_end <= usable_start:
                center = (seg_start + seg_end) / 2
            else:
                center = rng.uniform(usable_start, usable_end)
            min_x = max(seg_start + 10, center - patrol_width / 2)
            max_x = min(seg_end - 10, center + patrol_width / 2)
            if max_x <= min_x:
                max_x = min_x + 10

            speed = rng.uniform(*creature.speed_range)
            instances.append({
                "x": rng.uniform(min_x, max_x),
                "min_x": min_x,
                "max_x": max_x,
                "size": rng.randint(*creature.size_range),
                "color": creature.colors[i % len(creature.colors)],
                "vx": speed if rng.random() < 0.5 else -speed,
            })
        return instances

    def update(self, dt):
        """Advances every living creature's position/animation phase.
        Call once per frame before draw(). Purely decorative motion --
        no interaction with the player or level.
        """
        for creature, instances in self.flying_creatures:
            for inst in instances:
                inst["x"] += inst["vx"] * dt
                inst["phase"] += dt * (2 * math.pi / creature.bob_period)

        for creature, instances in self.ground_creatures:
            for inst in instances:
                inst["x"] += inst["vx"] * dt
                if inst["x"] <= inst["min_x"]:
                    inst["x"] = inst["min_x"]
                    inst["vx"] = abs(inst["vx"])
                elif inst["x"] >= inst["max_x"]:
                    inst["x"] = inst["max_x"]
                    inst["vx"] = -abs(inst["vx"])

    def draw(self, screen, camera_x):
        screen.blit(self.sky_surface, (0, 0))
        screen_width = screen.get_width()

        # Each bump layer's circle center sits progressively closer to
        # the ground line the nearer it is, but never *at* it -- keeping
        # most of the circle above ground_y means only a sliver dips
        # below where there's no platform to cover it (e.g. over a gap),
        # reading as landscape meeting the horizon rather than a shape
        # floating in the pit.
        # Two passes per layer: every silhouette first, then every
        # highlight. Drawing them interleaved would let a later hill's
        # base color paint over the previous hill's highlight where they
        # overlap, leaving the lit caps randomly chopped.
        # Clip every bump layer to the horizon. These are a distant
        # backdrop, so where the level has a gap in its ground there's
        # nothing to hide the bottom of the circles, and an unclipped
        # hill hangs into the pit looking like a loose ball. Clipped, the
        # gap reads as a clean drop to open sky instead.
        previous_clip = screen.get_clip()
        screen.set_clip(pygame.Rect(0, 0, screen_width, self.ground_y))

        # Far landmarks first, so the hills sit in front of them.
        for layer, items in self.far:
            for x, y, size, color in items:
                draw_x = self._wrapped_x(x, camera_x, layer.parallax, screen_width)
                if -size * 3 < draw_x < screen_width + size * 3:
                    layer.draw_fn(screen, draw_x, y, size, color)

        for layer, bumps in self.bumps:
            base_y = self.ground_y - layer.base_offset
            visible = []
            for x, radius in bumps:
                draw_x = self._wrapped_x(x, camera_x, layer.parallax, screen_width)
                if -radius < draw_x < screen_width + radius:
                    visible.append((draw_x, radius))
                    pygame.draw.circle(screen, layer.color, (draw_x, base_y), radius)

            # Offset straight up and only slightly smaller, so what shows
            # is a soft lit dome with a thin darker rim at the hill's
            # base. Offsetting sideways or shrinking much more makes the
            # highlight read as a separate inner circle -- hills end up
            # looking like soap bubbles rather than sunlit landforms.
            if layer.highlight:
                for draw_x, radius in visible:
                    pygame.draw.circle(
                        screen, layer.highlight,
                        (draw_x, base_y - radius * 0.12),
                        radius * 0.90,
                    )

        for layer, items in self.mid:
            for x, y, size, color in items:
                draw_x = self._wrapped_x(x, camera_x, layer.parallax, screen_width)
                if -size * 3 < draw_x < screen_width + size * 3:
                    layer.draw_fn(screen, draw_x, y, size, color)

        screen.set_clip(previous_clip)

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

        for creature, instances in self.flying_creatures:
            for inst in instances:
                draw_x = self._wrapped_x(inst["x"], camera_x, creature.parallax, screen_width)
                if -inst["size"] * 2 < draw_x < screen_width + inst["size"] * 2:
                    y = inst["y_base"] + math.sin(inst["phase"]) * creature.bob_amplitude
                    facing = 1 if inst["vx"] >= 0 else -1
                    creature.draw_fn(screen, draw_x, y, inst["size"], inst["color"], facing=facing)

        for creature, instances in self.ground_creatures:
            for inst in instances:
                draw_x = inst["x"] - camera_x
                if -60 < draw_x < screen_width + 60:
                    facing = 1 if inst["vx"] >= 0 else -1
                    creature.draw_fn(screen, draw_x, self.ground_y, inst["size"], inst["color"], facing=facing)

    def _wrapped_x(self, world_x, camera_x, parallax, screen_width):
        # Wrapping with % lets a sparse layer still cover an arbitrarily
        # wide level without needing one entry per screen-width.
        span = self.level_width + screen_width
        return (world_x - camera_x * parallax) % span - screen_width / 2

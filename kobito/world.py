"""One playable space: the level's surface, or one hidden underground room.

Game holds the surface World for the whole level and builds an
underground World the first time the player drops into a secret pit
(kept afterwards, so coins taken down there stay taken). Switching rooms
is just pointing Game at a different World.
"""

import pygame


class World:
    def __init__(self, level, background, kind="surface", style=None, entry_x=None, pit=None):
        self.kind = kind                  # "surface" | "underground"
        self.style = style                # underground only: "subway" | "sewer" | "mine"
        self.entry_x = entry_x            # underground only: where the player drops in
        self.pit = pit                    # underground only: the surface pit that leads here
        self.platforms = level.platforms
        self.question_blocks = level.question_blocks
        self.gift_boxes = level.gift_boxes
        self.enemies = level.enemies
        self.collectibles = level.collectibles
        self.goal = level.goal            # the castle on the surface, the Exit underground
        self.width_px = level.width_px
        self.ground_y = level.ground_y
        self.ground_segments_px = level.ground_segments_px
        self.secret_pits = getattr(level, "secret_pits", [])
        self.background = background
        self.all_sprites = pygame.sprite.Group(
            *self.platforms, *self.enemies, *self.collectibles, self.goal
        )
        # Levels are built the same way every time (seeded), so a save can
        # name "the 4th coin" or "the 2nd enemy" by its spawn index.
        self.spawned = {
            "blocks": list(self.question_blocks), "gifts": list(self.gift_boxes),
            "collectibles": list(self.collectibles), "enemies": list(self.enemies),
        }

    @property
    def underground(self):
        return self.kind == "underground"

    def objects_state(self):
        """Which question boxes / gift boxes are used and which coins,
        snacks and enemies are gone -- by spawn index."""
        alive_pickups, alive_enemies = set(self.collectibles), set(self.enemies)
        return {
            "used_blocks": [i for i, b in enumerate(self.spawned["blocks"]) if b.used],
            "used_gifts": [i for i, b in enumerate(self.spawned["gifts"]) if b.used],
            "taken": [i for i, c in enumerate(self.spawned["collectibles"]) if c not in alive_pickups],
            "defeated": [i for i, e in enumerate(self.spawned["enemies"]) if e not in alive_enemies],
        }

    def restore_objects(self, state):
        def picked(key, pool):
            return [pool[i] for i in state.get(key, []) if isinstance(i, int) and 0 <= i < len(pool)]

        for block in picked("used_blocks", self.spawned["blocks"]):
            block.mark_used()
        for box in picked("used_gifts", self.spawned["gifts"]):
            box.mark_used()
        for sprite in picked("taken", self.spawned["collectibles"]) + picked("defeated", self.spawned["enemies"]):
            sprite.kill()

    def secret_pit_at(self, x):
        for pit in self.secret_pits:
            if pit["x0"] - 8 <= x <= pit["x1"] + 8:
                return pit
        return None

    def ledge_before(self, x):
        """The x of a safe spot on the ground just before the gap at `x` --
        where a player who fell in comes back."""
        ends = [end for start, end in self.ground_segments_px if end <= x + 8]
        if not ends:
            return self.ground_segments_px[0][0] + 64 if self.ground_segments_px else 64
        return max(ends) - 48

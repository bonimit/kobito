import pygame

WALL_COLOR = (244, 240, 232)
WALL_SHADE = (214, 208, 198)
ROOF_COLOR = (58, 78, 106)
ROOF_EDGE = (38, 54, 78)
STONE_COLOR = (128, 126, 120)
STONE_SHADE = (104, 102, 98)
DOOR_COLOR = (96, 58, 44)
DOOR_GLOW = (255, 206, 120)
TRIM_COLOR = (206, 84, 66)
GOLD = (240, 198, 96)


class Goal(pygame.sprite.Sprite):
    """The Japanese castle at the end of the level -- what the player
    runs into to finish it and collect the level's badge.

    Deliberately not solid (not added to the platforms group): the
    player runs straight into it and Game checks for that overlap each
    frame to trigger level completion, same as the flagpole it replaced.
    """

    def __init__(self, x, ground_y, height=190):
        super().__init__()
        width = round(height * 1.05)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)

        cx = width // 2
        stone_h = round(height * 0.20)
        stone_top = height - stone_h

        # Stone base: a battered (inward-sloping) plinth, the way real
        # castle foundations are built.
        pygame.draw.polygon(self.image, STONE_COLOR, [
            (0, height),
            (width, height),
            (width - round(width * 0.10), stone_top),
            (round(width * 0.10), stone_top),
        ])
        for row in range(1, 3):
            y = stone_top + row * stone_h // 3
            inset = round(width * 0.10) * (1 - row / 3)
            pygame.draw.line(self.image, STONE_SHADE, (inset, y), (width - inset, y), 1)

        # Two storeys, the upper one narrower, each capped by a flared roof.
        storeys = [
            (0.62, 0.30, stone_top),          # (width fraction, height fraction, base y)
            (0.44, 0.24, None),               # base y filled in as we stack upward
        ]
        base_y = stone_top
        for width_frac, height_frac, _ in storeys:
            body_w = round(width * width_frac)
            body_h = round(height * height_frac)
            body = pygame.Rect(0, 0, body_w, body_h)
            body.midbottom = (cx, base_y)
            pygame.draw.rect(self.image, WALL_COLOR, body)
            pygame.draw.rect(self.image, WALL_SHADE, body, width=1)

            # Windows: a row of dark slits, classic castle look.
            window_y = body.top + body_h // 3
            for i in range(3):
                wx = body.left + body_w * (i + 1) // 4
                pygame.draw.rect(self.image, ROOF_COLOR, (wx - 3, window_y, 6, max(4, body_h // 4)))

            # Flared roof: wider than the storey it covers, with the
            # eaves sweeping down past the walls on both sides.
            roof_w = round(body_w * 1.72)
            roof_h = round(height * 0.13)
            roof_base = body.top
            pygame.draw.polygon(self.image, ROOF_COLOR, [
                (cx - roof_w // 2, roof_base),
                (cx + roof_w // 2, roof_base),
                (cx + round(roof_w * 0.20), roof_base - roof_h),
                (cx - round(roof_w * 0.20), roof_base - roof_h),
            ])
            pygame.draw.line(
                self.image, ROOF_EDGE,
                (cx - roof_w // 2, roof_base), (cx + roof_w // 2, roof_base), 2,
            )
            base_y = roof_base - roof_h

        # Golden shachihoko-style finials on the top ridge, and a small
        # ridge cap between them.
        pygame.draw.line(self.image, GOLD, (cx - 10, base_y), (cx + 10, base_y), 3)
        for side in (-1, 1):
            pygame.draw.circle(self.image, GOLD, (cx + side * 11, base_y - 3), 3)

        # Entrance: a lit doorway with a red trim beam above it, so the
        # castle clearly reads as somewhere you go *into*.
        door_w, door_h = round(width * 0.17), round(stone_h * 1.15)
        door = pygame.Rect(0, 0, door_w, door_h)
        door.midbottom = (cx, height)
        pygame.draw.rect(self.image, DOOR_COLOR, door)
        pygame.draw.rect(self.image, DOOR_GLOW, door.inflate(-6, 0).move(0, 4))
        pygame.draw.rect(self.image, TRIM_COLOR, (door.left - 4, door.top - 5, door_w + 8, 5))

        self.rect = self.image.get_rect(midbottom=(x, ground_y))

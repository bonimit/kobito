"""World themes: each one is just data (colors, which shapes to draw,
how densely, how fast each layer scrolls) consumed by the generic
renderer in kobito/background.py. Adding a new world means adding a
new Theme here -- no changes needed to Background or the shape
functions in kobito/scenery_shapes.py.
"""

from dataclasses import dataclass, field

from kobito import scenery_shapes as shapes


@dataclass
class BumpLayer:
    """A continuous rolling silhouette (mountains, dunes, reef, ...),
    built from overlapping circles. `base_offset` is how far above the
    ground line the circle centers sit -- bigger for layers meant to
    read as further away, so they don't dip far below the ground line
    over a gap (see Background._draw_bumps).
    """

    color: tuple
    spacing: tuple
    radius: tuple
    parallax: float
    base_offset: int
    # Optional lighter cap drawn as a smaller circle offset up-left, so
    # each hill reads as a lit, rounded landform instead of the flat
    # disc a single-color circle looks like.
    highlight: tuple = None


@dataclass
class FloatyLayer:
    """A sky/water layer (clouds, stars, bubbles, ...). `count` is a
    function of level width so sparser/denser layers scale with level
    length instead of needing a fixed number.
    """

    draw_fn: callable
    colors: list
    count: callable
    y_range: tuple
    size_range: tuple
    parallax: float
    # For a landmark that should always be in view (Mt Fuji, a far range):
    # where along the screen it stands at the level's start, instead of a
    # random spot along the whole level.
    screen_x: tuple = None


@dataclass
class GroundProp:
    """A decoration rooted in the actual ground (trees, cacti, coral,
    ...). Only ever placed within real ground segments -- see
    Background._place_on_ground.
    """

    draw_fn: callable
    colors: list
    size_range: tuple
    spacing_range: tuple
    margin: int


@dataclass
class FlyingCreature:
    """A living, moving sky/water creature (bird, fish, whale, ...).
    Unlike FloatyLayer, these actually travel across the level over
    time (see Background.update) with a gentle up/down bob, not just
    scroll with the camera -- what makes a world feel inhabited rather
    than a static painted backdrop.
    """

    draw_fn: callable
    colors: list
    count: callable
    y_range: tuple
    size_range: tuple
    speed_range: tuple  # pixels/second
    parallax: float
    bob_amplitude: float = 6.0
    bob_period: float = 2.0  # seconds per full up-down cycle


@dataclass
class GroundCreature:
    """A living, moving creature that crawls back and forth along the
    actual ground (crab, lizard, scorpion, ...) -- a decorative,
    non-colliding cousin of Enemy.
    """

    draw_fn: callable
    colors: list
    count: callable
    size_range: tuple
    speed_range: tuple
    patrol_width_range: tuple  # pixels, how wide a back-and-forth range


@dataclass
class Theme:
    id: str
    name: str
    sky_top: tuple
    sky_bottom: tuple
    ground_color: tuple
    platform_color: tuple
    # Lit top surface of solid tiles (grass over dirt, sun-bleached sand
    # over shadowed sand, ...). Platform draws this as a band across the
    # top edge, which is what gives terrain its classic platformer read.
    cap_color: tuple = None
    # Darker tone for the underside of solid tiles.
    shade_color: tuple = None
    bump_layers: list = field(default_factory=list)
    floaty_layers: list = field(default_factory=list)
    # Distant landmarks drawn *behind* the bump layers (Mt Fuji, the sea and
    # its bridge) and ones drawn just *in front of* them (flower- or
    # tea-striped hills): FloatyLayers, clipped to the horizon.
    far_layers: list = field(default_factory=list)
    mid_layers: list = field(default_factory=list)
    ground_props: list = field(default_factory=list)
    flying_creatures: list = field(default_factory=list)
    ground_creatures: list = field(default_factory=list)


FOREST = Theme(
    id="forest",
    name="Whispering Forest",
    sky_top=(96, 176, 226),
    sky_bottom=(196, 232, 244),
    ground_color=(139, 90, 43),
    platform_color=(139, 90, 43),
    cap_color=(94, 172, 82),
    shade_color=(96, 60, 28),
    bump_layers=[
        BumpLayer((150, 178, 195), spacing=(200, 280), radius=(90, 140), parallax=0.1, base_offset=60,
                  highlight=(172, 197, 211)),
        BumpLayer((139, 191, 141), spacing=(160, 240), radius=(60, 90), parallax=0.2, base_offset=35,
                  highlight=(163, 208, 162)),
        BumpLayer((104, 172, 108), spacing=(120, 190), radius=(38, 58), parallax=0.4, base_offset=18,
                  highlight=(128, 192, 130)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 248, 214)], lambda w: 1, (70, 70), (70, 70), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 232, 130)], lambda w: 1, (70, 70), (30, 30), 0.04),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 260, (30, 170), (26, 46), 0.25),
        FloatyLayer(shapes.draw_petal, [(255, 198, 220), (255, 214, 232)], lambda w: w // 90, (60, 300), (3, 5), 0.55),
    ],
    ground_props=[
        GroundProp(shapes.draw_torii, [(198, 58, 48)], (64, 86), (330, 470), 60),
        GroundProp(shapes.draw_pine_tree, [(36, 100, 53), (46, 125, 66), (58, 145, 80)], (44, 72), (90, 150), 30),
        GroundProp(shapes.draw_sakura_tree, [(248, 178, 206), (252, 196, 218)], (50, 70), (200, 300), 40),
        GroundProp(shapes.draw_stone_lantern, [(150, 150, 142)], (34, 44), (240, 340), 45),
        GroundProp(shapes.draw_bush, [(52, 130, 68), (66, 145, 80)], (9, 11), (55, 95), 20),
        GroundProp(shapes.draw_mushroom, [(206, 74, 66), (226, 128, 72)], (12, 17), (110, 180), 25),
        GroundProp(shapes.draw_grass_tuft, [(86, 158, 84), (104, 176, 96)], (10, 14), (34, 62), 12),
        GroundProp(shapes.draw_flower, [(255, 255, 255), (255, 214, 90), (255, 150, 180)], (11, 13), (40, 80), 15),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(80, 65, 55), (100, 80, 65)], lambda w: 4, (40, 130), (12, 16), (30, 55), 0.35),
        FlyingCreature(shapes.draw_dragonfly, [(110, 190, 200), (150, 200, 150)], lambda w: 3, (170, 250), (8, 11), (40, 70), 0.45, bob_amplitude=7, bob_period=1.1),
        FlyingCreature(shapes.draw_butterfly, [(230, 150, 200), (240, 200, 100), (150, 190, 240)], lambda w: 5, (150, 260), (7, 10), (15, 28), 0.5, bob_amplitude=10, bob_period=1.4),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_lizard, [(120, 160, 90), (140, 172, 100)], lambda w: 2, (14, 19), (16, 26), (60, 110)),
    ],
)

DESERT = Theme(
    id="desert",
    name="Sunfall Desert",
    sky_top=(96, 154, 214),
    sky_bottom=(255, 216, 158),
    ground_color=(224, 178, 110),
    platform_color=(224, 178, 110),
    cap_color=(242, 205, 143),
    shade_color=(176, 132, 76),
    bump_layers=[
        BumpLayer((230, 196, 140), spacing=(220, 300), radius=(80, 130), parallax=0.1, base_offset=50,
                  highlight=(242, 214, 166)),
        BumpLayer((214, 170, 105), spacing=(170, 240), radius=(55, 85), parallax=0.25, base_offset=25,
                  highlight=(230, 192, 133)),
        BumpLayer((196, 150, 85), spacing=(130, 190), radius=(35, 55), parallax=0.45, base_offset=12,
                  highlight=(214, 173, 111)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 226, 150)], lambda w: 1, (55, 55), (92, 92), 0.05),
        FloatyLayer(shapes.draw_sun, [(255, 210, 90)], lambda w: 1, (55, 55), (42, 42), 0.05),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: max(1, w // 500), (30, 70), (16, 22), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_pyramid, [(214, 176, 112)], (80, 120), (420, 600), 90),
        GroundProp(shapes.draw_cactus, [(60, 120, 70), (70, 135, 80)], (40, 60), (140, 220), 30),
        GroundProp(shapes.draw_palm_tree, [(96, 150, 88)], (44, 62), (260, 360), 40),
        GroundProp(shapes.draw_rock, [(178, 148, 104), (166, 138, 96)], (16, 26), (120, 200), 25),
        GroundProp(shapes.draw_bush, [(150, 140, 80), (160, 150, 90)], (7, 9), (70, 110), 20),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(90, 70, 50)], lambda w: 3, (35, 90), (14, 18), (20, 35), 0.2, bob_amplitude=3, bob_period=3.0),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_camel, [(196, 158, 106)], lambda w: 1, (18, 24), (10, 16), (120, 200)),
        GroundCreature(shapes.draw_scorpion, [(70, 55, 50), (85, 65, 55)], lambda w: 2, (16, 22), (18, 30), (60, 110)),
        GroundCreature(shapes.draw_lizard, [(168, 146, 92)], lambda w: 2, (13, 18), (20, 32), (70, 120)),
    ],
)

ARABIAN_NIGHT = Theme(
    id="arabian_night",
    name="Arabian Night",
    sky_top=(12, 12, 38),
    sky_bottom=(78, 46, 102),
    ground_color=(90, 65, 45),
    platform_color=(90, 65, 45),
    cap_color=(122, 92, 66),
    shade_color=(62, 44, 30),
    bump_layers=[
        BumpLayer((45, 40, 75), spacing=(220, 300), radius=(80, 130), parallax=0.1, base_offset=55,
                  highlight=(60, 54, 92)),
        BumpLayer((60, 50, 90), spacing=(170, 240), radius=(55, 85), parallax=0.25, base_offset=28,
                  highlight=(76, 64, 108)),
        BumpLayer((75, 60, 100), spacing=(130, 190), radius=(35, 55), parallax=0.45, base_offset=14,
                  highlight=(92, 74, 118)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_star, [(255, 255, 235)], lambda w: w // 110, (20, 140), (2, 4), 0.15),
        FloatyLayer(shapes.draw_glow, [(240, 232, 200)], lambda w: 1, (55, 55), (78, 78), 0.05),
        FloatyLayer(shapes.draw_moon, [(245, 235, 200)], lambda w: 1, (55, 55), (32, 32), 0.05),
        FloatyLayer(shapes.draw_shooting_star, [(255, 255, 240)], lambda w: max(1, w // 620), (40, 110), (2, 3), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_minaret, [(70, 55, 90), (80, 64, 100)], (55, 80), (180, 260), 40),
        GroundProp(shapes.draw_pagoda, [(72, 58, 96)], (70, 96), (360, 500), 70),
        GroundProp(shapes.draw_palm_tree, [(70, 150, 90)], (45, 65), (100, 160), 25),
        GroundProp(shapes.draw_stone_lantern, [(104, 88, 122)], (32, 42), (200, 300), 40),
        GroundProp(shapes.draw_rock, [(74, 58, 52)], (15, 24), (140, 220), 25),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bat, [(40, 35, 50), (55, 48, 65)], lambda w: 4, (30, 110), (9, 13), (35, 60), 0.3, bob_amplitude=8, bob_period=1.0),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_scorpion, [(60, 45, 55)], lambda w: 2, (16, 22), (18, 30), (60, 110)),
    ],
)

UNDERWATER = Theme(
    id="underwater",
    name="Coral Deep",
    sky_top=(96, 200, 214),
    sky_bottom=(6, 38, 78),
    ground_color=(194, 178, 128),
    platform_color=(194, 178, 128),
    cap_color=(216, 202, 156),
    shade_color=(150, 136, 96),
    bump_layers=[
        BumpLayer((50, 110, 130), spacing=(200, 280), radius=(80, 130), parallax=0.1, base_offset=50,
                  highlight=(64, 128, 146)),
        BumpLayer((40, 130, 140), spacing=(160, 230), radius=(55, 85), parallax=0.25, base_offset=25,
                  highlight=(56, 148, 156)),
        BumpLayer((30, 150, 150), spacing=(120, 180), radius=(35, 55), parallax=0.45, base_offset=12,
                  highlight=(48, 168, 166)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_bubble, [(230, 245, 255)], lambda w: w // 150, (20, 180), (4, 10), 0.3),
        FloatyLayer(shapes.draw_bubble, [(210, 236, 250)], lambda w: w // 220, (120, 320), (3, 6), 0.5),
    ],
    ground_props=[
        GroundProp(shapes.draw_coral, [(230, 110, 120), (240, 150, 90), (180, 110, 200)], (30, 50), (90, 150), 25),
        GroundProp(shapes.draw_seaweed, [(50, 140, 90), (60, 155, 100)], (35, 55), (60, 100), 15),
        GroundProp(shapes.draw_rock, [(122, 132, 130), (110, 122, 122)], (16, 26), (150, 240), 30),
        GroundProp(shapes.draw_starfish, [(240, 150, 120), (232, 178, 96)], (12, 17), (170, 260), 25),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_fish, [(230, 140, 90), (240, 170, 60), (150, 120, 210)], lambda w: w // 260, (60, 170), (12, 18), (25, 45), 0.25, bob_amplitude=8, bob_period=1.6),
        FlyingCreature(shapes.draw_squid, [(180, 110, 200), (150, 90, 180)], lambda w: max(1, w // 700), (40, 100), (18, 26), (10, 18), 0.2, bob_amplitude=12, bob_period=2.2),
        FlyingCreature(shapes.draw_whale, [(90, 130, 170)], lambda w: 1, (60, 90), (55, 70), (12, 16), 0.15, bob_amplitude=6, bob_period=4.0),
        FlyingCreature(shapes.draw_jellyfish, [(224, 172, 232), (198, 176, 240)], lambda w: 3, (90, 220), (12, 18), (8, 15), 0.3, bob_amplitude=14, bob_period=3.2),
        FlyingCreature(shapes.draw_turtle, [(90, 150, 110), (104, 162, 120)], lambda w: 2, (70, 190), (16, 22), (14, 22), 0.22, bob_amplitude=7, bob_period=2.8),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_crab, [(210, 90, 70), (190, 80, 60)], lambda w: 3, (14, 20), (14, 24), (50, 90)),
    ],
)

SKY = Theme(
    id="sky",
    name="Cloud Kingdom",
    sky_top=(118, 190, 250),
    sky_bottom=(240, 250, 255),
    ground_color=(235, 235, 240),
    platform_color=(235, 235, 240),
    cap_color=(255, 255, 255),
    shade_color=(198, 208, 224),
    bump_layers=[
        BumpLayer((255, 255, 255), spacing=(200, 280), radius=(90, 140), parallax=0.1, base_offset=55),
        BumpLayer((240, 248, 255), spacing=(160, 230), radius=(60, 90), parallax=0.25, base_offset=28,
                  highlight=(250, 253, 255)),
        BumpLayer((225, 240, 255), spacing=(120, 190), radius=(38, 58), parallax=0.45, base_offset=14,
                  highlight=(238, 247, 255)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 252, 226)], lambda w: 1, (64, 64), (74, 74), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 244, 170)], lambda w: 1, (64, 64), (28, 28), 0.04),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 300, (20, 80), (20, 30), 0.15),
        FloatyLayer(shapes.draw_balloon, [(240, 120, 130), (250, 196, 96), (130, 190, 240), (170, 220, 150)],
                    lambda w: max(2, w // 320), (90, 250), (10, 16), 0.4),
    ],
    ground_props=[
        GroundProp(shapes.draw_floating_island, [(150, 120, 90)], (40, 60), (160, 240), 40),
        GroundProp(shapes.draw_torii, [(206, 74, 62)], (58, 78), (400, 560), 70),
        GroundProp(shapes.draw_bush, [(130, 200, 110)], (8, 10), (70, 110), 20),
        GroundProp(shapes.draw_grass_tuft, [(150, 210, 130)], (9, 13), (44, 76), 15),
        GroundProp(shapes.draw_flower, [(255, 255, 255), (255, 222, 120), (255, 172, 200)], (11, 13), (60, 110), 20),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(90, 80, 80), (70, 100, 120), (120, 90, 70)], lambda w: 7, (40, 180), (8, 18), (25, 60), 0.3, bob_amplitude=5, bob_period=1.2),
        FlyingCreature(shapes.draw_dragonfly, [(140, 200, 220)], lambda w: 3, (180, 280), (8, 11), (35, 60), 0.45, bob_amplitude=8, bob_period=1.2),
    ],
)

# --- Real-place worlds ------------------------------------------------
# Five worlds built on actual Japanese regions, each carrying the
# landmarks and wildlife that region is actually known for -- so the
# scenery teaches a little geography alongside the language.

TOKYO = Theme(
    id="tokyo",
    name="Neon Tokyo",
    sky_top=(16, 20, 46),
    sky_bottom=(96, 62, 116),
    ground_color=(62, 64, 72),
    platform_color=(62, 64, 72),
    cap_color=(96, 98, 108),
    shade_color=(40, 42, 48),
    bump_layers=[
        # Kept very low-contrast: the skyline itself comes from the
        # skyscraper props below, so these only suggest distant haze.
        BumpLayer((34, 38, 68), spacing=(220, 300), radius=(80, 130), parallax=0.08, base_offset=60,
                  highlight=(42, 46, 78)),
        BumpLayer((46, 48, 82), spacing=(170, 240), radius=(50, 80), parallax=0.18, base_offset=30,
                  highlight=(54, 58, 92)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_star, [(255, 255, 235)], lambda w: w // 200, (20, 90), (2, 3), 0.12),
        FloatyLayer(shapes.draw_glow, [(238, 228, 200)], lambda w: 1, (58, 58), (66, 66), 0.05),
        FloatyLayer(shapes.draw_moon, [(244, 236, 208)], lambda w: 1, (58, 58), (26, 26), 0.05),
    ],
    ground_props=[
        # Dense and varied, which is what makes a skyline read as a city.
        GroundProp(shapes.draw_skyscraper, [(48, 54, 86), (58, 62, 96), (40, 46, 76)], (110, 190), (70, 130), 40),
        GroundProp(shapes.draw_tokyo_tower, [(240, 104, 68)], (120, 160), (1400, 2000), 90),
        GroundProp(shapes.draw_machiya, [(120, 104, 92)], (34, 46), (300, 440), 45),
        GroundProp(shapes.draw_stone_lantern, [(128, 122, 132)], (28, 36), (190, 280), 35),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_plane, [(226, 230, 240)], lambda w: 2, (30, 80), (7, 10), (55, 85), 0.15,
                       bob_amplitude=2, bob_period=5.0),
        FlyingCreature(shapes.draw_bird, [(26, 26, 32), (36, 34, 40)], lambda w: 5, (60, 160), (9, 13), (35, 60), 0.32),
    ],
)

NAGANO = Theme(
    id="nagano",
    name="Nagano Snowfield",
    sky_top=(150, 190, 226),
    sky_bottom=(236, 244, 252),
    ground_color=(226, 232, 242),
    platform_color=(226, 232, 242),
    cap_color=(255, 255, 255),
    shade_color=(186, 198, 216),
    bump_layers=[
        BumpLayer((186, 200, 220), spacing=(210, 290), radius=(95, 145), parallax=0.09, base_offset=62,
                  highlight=(212, 224, 238)),
        BumpLayer((206, 218, 234), spacing=(165, 235), radius=(60, 92), parallax=0.22, base_offset=32,
                  highlight=(230, 238, 248)),
        BumpLayer((224, 232, 244), spacing=(125, 190), radius=(38, 60), parallax=0.42, base_offset=16,
                  highlight=(244, 249, 255)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 252, 236)], lambda w: 1, (66, 66), (60, 60), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 250, 214)], lambda w: 1, (66, 66), (26, 26), 0.04),
        FloatyLayer(shapes.draw_snowflake, [(255, 255, 255)], lambda w: w // 70, (20, 320), (3, 6), 0.5),
    ],
    ground_props=[
        GroundProp(shapes.draw_pine_tree, [(28, 74, 52), (36, 90, 62)], (46, 76), (85, 145), 30),
        GroundProp(shapes.draw_torii, [(186, 62, 54)], (60, 80), (360, 520), 60),
        GroundProp(shapes.draw_stone_lantern, [(178, 182, 192)], (32, 42), (240, 350), 40),
        GroundProp(shapes.draw_rock, [(206, 212, 224)], (16, 26), (140, 220), 25),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(64, 58, 54), (84, 76, 68)], lambda w: 4, (40, 120), (13, 17), (30, 50), 0.3,
                       bob_amplitude=4, bob_period=2.6),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_snow_monkey, [(176, 158, 148), (188, 170, 158)], lambda w: 4, (16, 22), (10, 18),
                       (50, 100)),
    ],
)

OKINAWA = Theme(
    id="okinawa",
    name="Okinawa Shore",
    sky_top=(72, 180, 232),
    sky_bottom=(226, 246, 250),
    ground_color=(238, 222, 176),
    platform_color=(238, 222, 176),
    cap_color=(252, 242, 208),
    shade_color=(204, 184, 138),
    bump_layers=[
        BumpLayer((92, 176, 190), spacing=(220, 300), radius=(85, 135), parallax=0.09, base_offset=58,
                  highlight=(116, 198, 208)),
        BumpLayer((72, 190, 198), spacing=(170, 240), radius=(55, 88), parallax=0.22, base_offset=28,
                  highlight=(102, 212, 216)),
        BumpLayer((122, 216, 214), spacing=(130, 190), radius=(34, 56), parallax=0.42, base_offset=13,
                  highlight=(152, 232, 228)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 246, 200)], lambda w: 1, (58, 58), (78, 78), 0.05),
        FloatyLayer(shapes.draw_sun, [(255, 238, 150)], lambda w: 1, (58, 58), (34, 34), 0.05),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 320, (28, 100), (20, 32), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_palm_tree, [(72, 156, 92), (86, 170, 100)], (52, 76), (110, 180), 35),
        GroundProp(shapes.draw_shisa, [(212, 192, 164)], (44, 58), (300, 430), 50),
        GroundProp(shapes.draw_hibiscus, [(238, 82, 96), (250, 140, 90), (252, 196, 92)], (16, 22), (90, 150), 22),
        GroundProp(shapes.draw_starfish, [(244, 158, 124), (236, 182, 100)], (12, 17), (160, 250), 25),
        GroundProp(shapes.draw_grass_tuft, [(150, 186, 118)], (10, 14), (50, 85), 15),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(252, 252, 252), (240, 240, 244)], lambda w: 6, (40, 140), (11, 16),
                       (30, 55), 0.32),
        FlyingCreature(shapes.draw_butterfly, [(255, 210, 90), (250, 130, 170)], lambda w: 4, (160, 260), (7, 10),
                       (16, 30), 0.5, bob_amplitude=10, bob_period=1.4),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_crab, [(226, 104, 78), (208, 88, 64)], lambda w: 4, (14, 20), (14, 24), (50, 95)),
    ],
)

HOKKAIDO = Theme(
    id="hokkaido",
    name="Hokkaido Lavender",
    mid_layers=[
        # Biei / Furano's rainbow rows of flowers over the nearer hills.
        FloatyLayer(shapes.draw_flower_hill, [(150, 118, 206), (166, 132, 216)], lambda w: w // 600, (392, 410),
                    (60, 84), 0.3),
    ],
    sky_top=(88, 166, 224),
    sky_bottom=(218, 238, 250),
    ground_color=(138, 114, 86),
    platform_color=(138, 114, 86),
    cap_color=(126, 176, 102),
    shade_color=(102, 82, 60),
    bump_layers=[
        # Snow-capped peaks far back, rolling farmland nearer.
        BumpLayer((196, 208, 226), spacing=(230, 310), radius=(100, 150), parallax=0.08, base_offset=66,
                  highlight=(226, 234, 246)),
        BumpLayer((132, 174, 132), spacing=(170, 240), radius=(60, 92), parallax=0.22, base_offset=32,
                  highlight=(158, 196, 152)),
        BumpLayer((106, 156, 108), spacing=(130, 195), radius=(38, 60), parallax=0.42, base_offset=16,
                  highlight=(132, 180, 130)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 250, 220)], lambda w: 1, (62, 62), (66, 66), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 244, 160)], lambda w: 1, (62, 62), (30, 30), 0.04),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 280, (26, 110), (22, 36), 0.22),
    ],
    ground_props=[
        # Lavender packed tightly, the way Furano's rows actually look.
        GroundProp(shapes.draw_lavender, [(150, 118, 206), (166, 132, 216), (134, 104, 192)], (26, 36), (30, 52), 12),
        GroundProp(shapes.draw_pine_tree, [(60, 112, 78), (72, 126, 88)], (44, 70), (200, 300), 35),
        GroundProp(shapes.draw_bush, [(112, 162, 104)], (9, 12), (110, 180), 25),
        GroundProp(shapes.draw_flower, [(255, 255, 255), (255, 226, 120)], (11, 13), (140, 220), 20),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_crane, [(250, 250, 250)], lambda w: 3, (50, 150), (15, 21), (28, 46), 0.26,
                       bob_amplitude=5, bob_period=3.0),
        FlyingCreature(shapes.draw_bird, [(78, 70, 64)], lambda w: 4, (40, 120), (10, 14), (32, 55), 0.34),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_fox, [(214, 128, 62), (204, 116, 54)], lambda w: 3, (16, 22), (14, 24), (70, 130)),
    ],
)

KYOTO = Theme(
    id="kyoto",
    name="Kyoto Autumn",
    sky_top=(140, 172, 210),
    sky_bottom=(250, 228, 196),
    ground_color=(126, 102, 80),
    platform_color=(126, 102, 80),
    cap_color=(158, 134, 96),
    shade_color=(94, 76, 58),
    bump_layers=[
        BumpLayer((172, 166, 178), spacing=(215, 295), radius=(92, 140), parallax=0.09, base_offset=62,
                  highlight=(194, 188, 196)),
        BumpLayer((162, 126, 92), spacing=(168, 238), radius=(58, 90), parallax=0.22, base_offset=32,
                  highlight=(186, 148, 108)),
        BumpLayer((132, 132, 84), spacing=(128, 192), radius=(38, 58), parallax=0.42, base_offset=16,
                  highlight=(156, 156, 102)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 236, 194)], lambda w: 1, (64, 64), (70, 70), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 226, 148)], lambda w: 1, (64, 64), (28, 28), 0.04),
        FloatyLayer(shapes.draw_maple_leaf, [(226, 112, 62), (236, 156, 70), (198, 74, 58)],
                    lambda w: w // 80, (50, 310), (4, 6), 0.55),
    ],
    ground_props=[
        # A run of torii (Fushimi Inari), a bamboo grove (Arashiyama)
        # and momiji maples -- the three things Kyoto is pictured as.
        # Torii kept small and spaced out: at full size they crowd the
        # maples into one red-orange smear rather than reading as a row
        # of gates.
        GroundProp(shapes.draw_torii, [(206, 62, 52)], (42, 56), (240, 340), 45),
        GroundProp(shapes.draw_bamboo, [(126, 186, 96), (110, 170, 84)], (60, 92), (38, 62), 15),
        GroundProp(shapes.draw_maple_tree, [(214, 88, 58), (232, 140, 64), (196, 76, 62)], (44, 64), (230, 330), 40),
        GroundProp(shapes.draw_pagoda, [(122, 96, 88)], (72, 98), (460, 640), 70),
        GroundProp(shapes.draw_machiya, [(198, 176, 148)], (34, 46), (280, 400), 45),
        GroundProp(shapes.draw_stone_lantern, [(158, 152, 144)], (32, 42), (200, 300), 35),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(88, 74, 62), (104, 88, 70)], lambda w: 4, (40, 130), (11, 15), (30, 52), 0.34),
        FlyingCreature(shapes.draw_butterfly, [(240, 190, 110), (226, 140, 170)], lambda w: 4, (150, 260), (7, 10),
                       (15, 28), 0.5, bob_amplitude=10, bob_period=1.4),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_fox, [(224, 148, 78), (214, 128, 62)], lambda w: 3, (16, 22), (14, 24), (70, 130)),
    ],
)

# --- Second wave of worlds --------------------------------------------
# A tropical island, a storybook fairy-tale kingdom, and three
# international cities -- broadening the set beyond Japan while keeping
# every prop rooted in something the place is actually known for.

ISLAND = Theme(
    id="island",
    name="Coconut Island",
    sky_top=(70, 170, 226),
    sky_bottom=(180, 236, 232),
    ground_color=(238, 220, 176),
    platform_color=(238, 220, 176),
    cap_color=(252, 240, 206),
    shade_color=(202, 180, 132),
    bump_layers=[
        BumpLayer((90, 190, 200), spacing=(220, 300), radius=(85, 135), parallax=0.09, base_offset=56,
                  highlight=(120, 210, 214)),
        BumpLayer((66, 200, 200), spacing=(170, 240), radius=(55, 88), parallax=0.22, base_offset=27,
                  highlight=(100, 220, 214)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 248, 210)], lambda w: 1, (56, 56), (78, 78), 0.05),
        FloatyLayer(shapes.draw_sun, [(255, 232, 130)], lambda w: 1, (56, 56), (34, 34), 0.05),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 300, (25, 100), (20, 32), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_palm_tree, [(70, 158, 92), (84, 172, 100)], (50, 74), (100, 170), 35),
        GroundProp(shapes.draw_tiki_totem, [(150, 100, 60), (140, 92, 54)], (60, 84), (340, 480), 45),
        GroundProp(shapes.draw_hibiscus, [(240, 90, 100), (250, 150, 96)], (16, 22), (90, 150), 22),
        GroundProp(shapes.draw_starfish, [(244, 158, 124), (236, 182, 100)], (12, 17), (150, 240), 25),
        GroundProp(shapes.draw_grass_tuft, [(160, 190, 120)], (10, 14), (46, 80), 15),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_parrot, [(60, 190, 90), (220, 100, 60), (80, 140, 220)], lambda w: 4, (60, 170),
                       (13, 18), (20, 40), 0.32, bob_amplitude=8, bob_period=1.6),
        FlyingCreature(shapes.draw_bird, [(250, 250, 250)], lambda w: 4, (40, 130), (10, 14), (30, 55), 0.3),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_crab, [(226, 104, 78), (208, 88, 64)], lambda w: 3, (14, 20), (14, 24), (50, 95)),
    ],
)

FAIRY_TALE = Theme(
    id="fairy_tale",
    name="Enchanted Kingdom",
    sky_top=(148, 118, 196),
    sky_bottom=(252, 210, 232),
    ground_color=(150, 118, 90),
    platform_color=(150, 118, 90),
    cap_color=(140, 200, 120),
    shade_color=(108, 84, 62),
    bump_layers=[
        BumpLayer((190, 160, 210), spacing=(210, 290), radius=(90, 140), parallax=0.09, base_offset=60,
                  highlight=(212, 186, 226)),
        BumpLayer((160, 190, 150), spacing=(165, 235), radius=(58, 90), parallax=0.22, base_offset=30,
                  highlight=(182, 210, 168)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 236, 250)], lambda w: 1, (60, 60), (74, 74), 0.04),
        FloatyLayer(shapes.draw_star, [(255, 255, 255)], lambda w: w // 130, (20, 150), (2, 4), 0.18),
        FloatyLayer(shapes.draw_petal, [(255, 210, 236), (240, 220, 255)], lambda w: w // 100, (60, 300), (3, 5), 0.5),
    ],
    ground_props=[
        GroundProp(shapes.draw_castle, [(220, 200, 228), (208, 220, 236)], (150, 200), (900, 1300), 90),
        GroundProp(shapes.draw_giant_mushroom, [(226, 100, 120), (110, 150, 220)], (36, 54), (160, 260), 35),
        GroundProp(shapes.draw_wishing_well, [(150, 130, 110)], (44, 58), (280, 400), 45),
        GroundProp(shapes.draw_flower, [(255, 255, 255), (255, 214, 90), (255, 150, 220)], (11, 13), (44, 84), 15),
        GroundProp(shapes.draw_bush, [(120, 180, 110)], (8, 10), (60, 100), 20),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_fairy, [(255, 220, 130), (200, 230, 255), (255, 180, 220)], lambda w: 5, (60, 220),
                       (9, 13), (14, 26), 0.45, bob_amplitude=12, bob_period=1.8),
        FlyingCreature(shapes.draw_butterfly, [(240, 190, 230), (255, 224, 150)], lambda w: 4, (140, 250), (7, 10),
                       (16, 30), 0.5, bob_amplitude=10, bob_period=1.4),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_fox, [(230, 160, 90), (222, 150, 78)], lambda w: 2, (16, 22), (12, 20), (70, 130)),
    ],
)

LONDON = Theme(
    id="london",
    name="Foggy London",
    sky_top=(120, 130, 140),
    sky_bottom=(206, 212, 214),
    ground_color=(96, 96, 100),
    platform_color=(96, 96, 100),
    cap_color=(130, 130, 134),
    shade_color=(66, 66, 70),
    bump_layers=[
        BumpLayer((150, 154, 158), spacing=(220, 300), radius=(80, 130), parallax=0.08, base_offset=58,
                  highlight=(172, 176, 178)),
        BumpLayer((168, 172, 176), spacing=(170, 240), radius=(52, 82), parallax=0.2, base_offset=28,
                  highlight=(190, 192, 194)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_cloud, [(220, 222, 224)], lambda w: w // 200, (20, 120), (30, 50), 0.22),
        FloatyLayer(shapes.draw_cloud, [(236, 238, 238)], lambda w: w // 280, (10, 60), (18, 28), 0.14),
    ],
    ground_props=[
        GroundProp(shapes.draw_big_ben, [(180, 156, 96)], (140, 190), (1100, 1500), 80),
        GroundProp(shapes.draw_phone_booth, [(196, 40, 40)], (46, 62), (200, 300), 35),
        GroundProp(shapes.draw_double_decker_bus, [(196, 40, 40)], (60, 76), (360, 500), 55),
        GroundProp(shapes.draw_machiya, [(150, 140, 130)], (36, 48), (260, 380), 45),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(70, 68, 66), (90, 86, 82)], lambda w: 5, (40, 130), (10, 14), (28, 48), 0.3),
    ],
)

NEW_YORK = Theme(
    id="new_york",
    name="Empire City",
    sky_top=(70, 90, 150),
    sky_bottom=(240, 190, 150),
    ground_color=(80, 80, 86),
    platform_color=(80, 80, 86),
    cap_color=(112, 112, 118),
    shade_color=(54, 54, 60),
    bump_layers=[
        BumpLayer((50, 56, 90), spacing=(220, 300), radius=(80, 130), parallax=0.08, base_offset=60,
                  highlight=(62, 68, 104)),
        BumpLayer((64, 68, 100), spacing=(170, 240), radius=(50, 80), parallax=0.18, base_offset=30,
                  highlight=(78, 82, 116)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 220, 180)], lambda w: 1, (60, 60), (70, 70), 0.05),
        FloatyLayer(shapes.draw_sun, [(255, 200, 140)], lambda w: 1, (60, 60), (30, 30), 0.05),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 320, (24, 90), (18, 28), 0.18),
    ],
    ground_props=[
        GroundProp(shapes.draw_skyscraper, [(56, 60, 92), (68, 70, 100), (48, 52, 84)], (120, 210), (60, 120), 40),
        GroundProp(shapes.draw_statue_of_liberty, [(110, 170, 150)], (130, 170), (1500, 2100), 90),
        GroundProp(shapes.draw_yellow_cab, [(240, 200, 40)], (44, 56), (220, 320), 40),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_plane, [(226, 230, 240)], lambda w: 2, (30, 80), (7, 10), (55, 85), 0.15,
                       bob_amplitude=2, bob_period=5.0),
        FlyingCreature(shapes.draw_bird, [(60, 58, 56)], lambda w: 5, (50, 140), (9, 13), (32, 55), 0.32),
    ],
)

KOREA = Theme(
    id="korea",
    name="Seoul Palace",
    sky_top=(132, 178, 224),
    sky_bottom=(252, 224, 232),
    ground_color=(150, 118, 90),
    platform_color=(150, 118, 90),
    cap_color=(140, 190, 110),
    shade_color=(108, 84, 62),
    bump_layers=[
        BumpLayer((172, 176, 192), spacing=(215, 295), radius=(90, 140), parallax=0.09, base_offset=60,
                  highlight=(196, 200, 212)),
        BumpLayer((150, 190, 150), spacing=(168, 238), radius=(56, 88), parallax=0.22, base_offset=30,
                  highlight=(174, 210, 172)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 240, 220)], lambda w: 1, (62, 62), (70, 70), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 228, 160)], lambda w: 1, (62, 62), (28, 28), 0.04),
        FloatyLayer(shapes.draw_petal, [(255, 214, 226), (255, 236, 240)], lambda w: w // 90, (50, 300), (3, 5), 0.5),
    ],
    ground_props=[
        GroundProp(shapes.draw_palace_gate, [(200, 60, 50)], (90, 120), (700, 1000), 80),
        GroundProp(shapes.draw_hanok, [(230, 220, 200), (222, 210, 192)], (54, 74), (260, 380), 45),
        GroundProp(shapes.draw_paper_lantern, [(230, 90, 70), (220, 150, 60)], (34, 46), (150, 230), 25),
        GroundProp(shapes.draw_sakura_tree, [(250, 200, 216), (255, 224, 234)], (46, 64), (220, 320), 40),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_crane, [(250, 250, 250)], lambda w: 3, (50, 150), (14, 20), (28, 46), 0.26,
                       bob_amplitude=5, bob_period=3.0),
        FlyingCreature(shapes.draw_bird, [(84, 76, 68)], lambda w: 4, (40, 120), (10, 14), (30, 52), 0.32),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_fox, [(210, 150, 92)], lambda w: 2, (16, 22), (12, 20), (70, 130)),
    ],
)

OKINAWA_DRIVE = Theme(
    id="okinawa_drive",
    name="Okinawa Island Drive",
    sky_top=(40, 150, 226),
    sky_bottom=(206, 238, 250),
    # The ground is the coast road itself: asphalt with a pale kerb.
    ground_color=(92, 96, 106),
    platform_color=(92, 96, 106),
    cap_color=(232, 228, 214),
    shade_color=(66, 68, 78),
    far_layers=[
        FloatyLayer(shapes.draw_far_island, [(70, 150, 100), (86, 162, 108)], lambda w: w // 900, (380, 380),
                    (26, 40), 0.06),
        FloatyLayer(shapes.draw_sea_band, [(40, 190, 206)], lambda w: 1, (372, 372), (2000, 2000), 0.0),
        FloatyLayer(shapes.draw_sea_bridge, [(236, 238, 240)], lambda w: w // 2600 + 1, (392, 392), (110, 130),
                    0.12),
    ],
    bump_layers=[
        # Just a low green bank between the road and the sea.
        BumpLayer((96, 176, 110), spacing=(150, 220), radius=(36, 56), parallax=0.5, base_offset=8,
                  highlight=(120, 196, 124)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 246, 200)], lambda w: 1, (60, 60), (76, 76), 0.05),
        FloatyLayer(shapes.draw_sun, [(255, 236, 150)], lambda w: 1, (60, 60), (32, 32), 0.05),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 300, (26, 120), (20, 34), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_palm_tree, [(66, 150, 86), (82, 166, 96)], (52, 76), (150, 240), 35),
        GroundProp(shapes.draw_ryukyu_house, [(246, 242, 232), (240, 232, 214)], (44, 56), (420, 600), 60),
        GroundProp(shapes.draw_sugarcane, [(120, 186, 90), (104, 170, 80)], (40, 54), (70, 120), 20),
        GroundProp(shapes.draw_guardrail, [(246, 246, 250)], (20, 24), (260, 380), 40),
        GroundProp(shapes.draw_hibiscus, [(238, 82, 96), (250, 140, 90)], (16, 22), (130, 210), 22),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_bird, [(252, 252, 252)], lambda w: 5, (40, 150), (11, 16), (30, 55), 0.32),
        FlyingCreature(shapes.draw_butterfly, [(255, 210, 90), (120, 200, 250)], lambda w: 3, (170, 270), (7, 10),
                       (16, 30), 0.5, bob_amplitude=10, bob_period=1.4),
    ],
    ground_creatures=[
        # Rental cars cruising the coast road.
        GroundCreature(shapes.draw_car, [(240, 90, 90), (250, 250, 250), (90, 170, 230), (250, 210, 80)],
                       lambda w: w // 900, (14, 17), (70, 110), (260, 460)),
    ],
)

AOMORI = Theme(
    id="aomori",
    name="Aomori Apple Orchard",
    sky_top=(110, 168, 222),
    sky_bottom=(250, 232, 196),
    ground_color=(126, 96, 68),
    platform_color=(126, 96, 68),
    cap_color=(132, 176, 84),
    shade_color=(92, 70, 50),
    far_layers=[
        # Mt Iwaki, "Tsugaru Fuji", with its first autumn snow.
        FloatyLayer(lambda s, x, y, size, c: shapes.draw_fuji(s, x, y, size, c, (240, 244, 250)),
                    [(110, 126, 160)], lambda w: 1, (250, 250), (64, 64), 0.03, screen_x=(640, 700)),
    ],
    bump_layers=[
        BumpLayer((168, 166, 92), spacing=(200, 280), radius=(80, 120), parallax=0.12, base_offset=50,
                  highlight=(190, 184, 108)),
        BumpLayer((122, 160, 82), spacing=(150, 220), radius=(46, 72), parallax=0.28, base_offset=22,
                  highlight=(146, 180, 96)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 240, 200)], lambda w: 1, (70, 70), (64, 64), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 226, 140)], lambda w: 1, (70, 70), (28, 28), 0.04),
        FloatyLayer(shapes.draw_cloud, [(255, 252, 246)], lambda w: w // 340, (26, 110), (20, 32), 0.2),
        FloatyLayer(shapes.draw_maple_leaf, [(226, 112, 62), (240, 170, 70)], lambda w: w // 160, (120, 400),
                    (5, 8), 0.55),
    ],
    ground_props=[
        # Orchard rows: apple trees close together, crates between them.
        GroundProp(shapes.draw_apple_tree, [(84, 146, 70), (96, 158, 76)], (56, 72), (70, 120), 30),
        GroundProp(shapes.draw_apple_crate, [(196, 146, 92)], (22, 26), (300, 460), 40),
        GroundProp(shapes.draw_scarecrow, [(70, 110, 180), (180, 80, 70)], (44, 52), (600, 900), 60),
        GroundProp(shapes.draw_grass_tuft, [(140, 170, 80)], (10, 14), (50, 90), 15),
    ],
    flying_creatures=[
        # Red dragonflies (aka-tombo) -- the sign of autumn in Japan.
        FlyingCreature(shapes.draw_dragonfly, [(222, 70, 50), (236, 96, 60)], lambda w: 6, (220, 380), (8, 11),
                       (20, 40), 0.55, bob_amplitude=8, bob_period=1.6),
        FlyingCreature(shapes.draw_bird, [(70, 62, 58)], lambda w: 4, (40, 130), (10, 14), (30, 52), 0.3),
    ],
    ground_creatures=[
        GroundCreature(shapes.draw_fox, [(170, 130, 90)], lambda w: 2, (15, 20), (12, 20), (70, 130)),
    ],
)

SHIZUOKA = Theme(
    id="shizuoka",
    name="Shizuoka Tea Fields",
    sky_top=(96, 160, 224),
    sky_bottom=(222, 240, 250),
    ground_color=(118, 92, 66),
    platform_color=(118, 92, 66),
    cap_color=(88, 160, 76),
    shade_color=(86, 66, 48),
    far_layers=[
        # Mt Fuji fills the sky over the tea hills.
        FloatyLayer(shapes.draw_fuji, [(84, 108, 168)], lambda w: 1, (150, 150), (100, 100), 0.03,
                    screen_x=(640, 680)),
    ],
    mid_layers=[
        FloatyLayer(shapes.draw_tea_hill, [(74, 150, 74), (86, 160, 80)], lambda w: w // 420, (372, 400),
                    (56, 84), 0.2),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 360, (30, 110), (20, 32), 0.18),
        # The Tokaido Shinkansen's viaduct runs across the fields.
        FloatyLayer(shapes.draw_viaduct, [(196, 198, 204)], lambda w: 1, (418, 418), (2000, 2000), 0.3),
    ],
    ground_props=[
        GroundProp(shapes.draw_tea_bush, [(64, 140, 66), (74, 150, 72)], (26, 32), (58, 76), 30),
        GroundProp(shapes.draw_frost_fan, [(230, 232, 236)], (70, 84), (260, 380), 40),
        GroundProp(shapes.draw_stone_lantern, [(150, 146, 140)], (28, 36), (700, 1000), 50),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_shinkansen, [(250, 250, 252)], lambda w: w // 1500, (416, 416), (8, 8),
                       (260, 320), 0.3, bob_amplitude=0, bob_period=5.0),
        FlyingCreature(shapes.draw_bird, [(70, 64, 60)], lambda w: 4, (40, 130), (10, 14), (30, 52), 0.3),
        FlyingCreature(shapes.draw_butterfly, [(255, 236, 120), (255, 255, 255)], lambda w: 3, (300, 400), (6, 9),
                       (16, 28), 0.5, bob_amplitude=8, bob_period=1.4),
    ],
)

HOKKAIDO_FARM = Theme(
    id="hokkaido_farm",
    name="Hokkaido Dairy Farm",
    sky_top=(70, 150, 230),
    sky_bottom=(214, 236, 252),
    ground_color=(120, 98, 70),
    platform_color=(120, 98, 70),
    cap_color=(112, 178, 80),
    shade_color=(88, 72, 52),
    far_layers=[
        # The Daisetsuzan peaks, snow all year on top.
        FloatyLayer(lambda s, x, y, size, c: shapes.draw_fuji(s, x, y, size, c), [(126, 146, 186), (140, 158, 196)],
                    lambda w: 3, (250, 280), (50, 64), 0.04, screen_x=(200, 900)),
    ],
    bump_layers=[
        BumpLayer((120, 184, 96), spacing=(240, 320), radius=(110, 160), parallax=0.12, base_offset=70,
                  highlight=(142, 200, 108)),
        BumpLayer((104, 170, 84), spacing=(170, 240), radius=(60, 92), parallax=0.26, base_offset=26,
                  highlight=(126, 190, 96)),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_glow, [(255, 250, 220)], lambda w: 1, (64, 64), (66, 66), 0.04),
        FloatyLayer(shapes.draw_sun, [(255, 244, 170)], lambda w: 1, (64, 64), (30, 30), 0.04),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 260, (24, 120), (22, 38), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_red_barn, [(186, 52, 46)], (60, 72), (700, 1000), 70),
        GroundProp(shapes.draw_silo, [(214, 216, 222)], (70, 86), (900, 1300), 80),
        GroundProp(shapes.draw_ranch_fence, [(250, 250, 246)], (26, 30), (150, 230), 40),
        GroundProp(shapes.draw_hay_bale, [(244, 244, 236), (232, 208, 140)], (22, 28), (220, 340), 30),
        GroundProp(shapes.draw_birch, [(132, 188, 96), (150, 200, 104)], (60, 80), (260, 400), 35),
        GroundProp(shapes.draw_flower, [(255, 255, 255), (255, 226, 120)], (10, 12), (120, 200), 20),
    ],
    flying_creatures=[
        FlyingCreature(shapes.draw_crane, [(250, 250, 250)], lambda w: 2, (60, 150), (15, 20), (28, 46), 0.26,
                       bob_amplitude=5, bob_period=3.0),
        FlyingCreature(shapes.draw_bird, [(78, 70, 64)], lambda w: 4, (40, 120), (10, 14), (32, 55), 0.34),
    ],
    ground_creatures=[
        # Holsteins wandering the pasture.
        GroundCreature(shapes.draw_cow, [(250, 250, 248)], lambda w: w // 800, (22, 28), (8, 14), (80, 160)),
    ],
)


THEMES = {
    theme.id: theme
    for theme in (
        FOREST, DESERT, ARABIAN_NIGHT, UNDERWATER, SKY,
        TOKYO, NAGANO, OKINAWA, HOKKAIDO, KYOTO,
        ISLAND, FAIRY_TALE, LONDON, NEW_YORK, KOREA,
        OKINAWA_DRIVE, AOMORI, SHIZUOKA, HOKKAIDO_FARM,
    )
}


def get_theme(theme_id):
    return THEMES[theme_id]


# --- Enemy skins --------------------------------------------------------
# (body_color, foot_color) per world, keeping every enemy's silhouette
# but recoloring it to fit the setting -- a goblin-green forest imp reads
# very differently from a coconut-crab-orange island hazard even though
# both are the same Enemy class. Themes without an entry fall back to
# Enemy's own default red-brown palette.

ENEMY_PALETTES = {
    "forest": ((92, 130, 60), (58, 88, 38)),
    "desert": ((196, 150, 90), (140, 100, 58)),
    "arabian_night": ((90, 60, 110), (56, 36, 74)),
    "underwater": ((60, 140, 150), (34, 96, 104)),
    "sky": ((210, 210, 220), (160, 160, 176)),
    "tokyo": ((200, 70, 150), (140, 40, 108)),
    "nagano": ((200, 210, 224), (150, 162, 182)),
    "okinawa": ((214, 96, 70), (160, 66, 48)),
    "hokkaido": ((150, 108, 76), (104, 72, 48)),
    "kyoto": ((160, 96, 60), (112, 64, 38)),
    "island": ((230, 120, 60), (176, 84, 40)),
    "fairy_tale": ((150, 90, 190), (100, 56, 136)),
    "london": ((110, 110, 118), (74, 74, 82)),
    "new_york": ((120, 108, 100), (80, 70, 64)),
    "korea": ((200, 66, 60), (150, 42, 40)),
    "okinawa_drive": ((230, 120, 70), (176, 84, 48)),
    "aomori": ((180, 60, 60), (126, 40, 40)),
    "shizuoka": ((120, 120, 70), (82, 84, 46)),
    "hokkaido_farm": ((140, 104, 76), (98, 70, 50)),
}

# (body_color, wing_color) for FlyingEnemy, per world -- same idea, kept
# separate from ENEMY_PALETTES since flying and ground hazards use
# different color roles.
FLYING_ENEMY_PALETTES = {
    "forest": ((60, 46, 74), (86, 68, 104)),
    "arabian_night": ((40, 35, 50), (55, 48, 65)),
    "underwater": ((70, 60, 130), (100, 90, 170)),
    "sky": ((150, 150, 170), (190, 190, 210)),
    "tokyo": ((60, 50, 90), (110, 70, 150)),
    "nagano": ((80, 90, 120), (130, 140, 170)),
    "fairy_tale": ((160, 70, 140), (210, 130, 190)),
    "london": ((60, 60, 66), (90, 90, 98)),
    "new_york": ((50, 50, 58), (80, 80, 90)),
    "korea": ((90, 50, 60), (140, 80, 90)),
}

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
class Theme:
    id: str
    name: str
    sky_top: tuple
    sky_bottom: tuple
    ground_color: tuple
    platform_color: tuple
    bump_layers: list = field(default_factory=list)
    floaty_layers: list = field(default_factory=list)
    ground_props: list = field(default_factory=list)


FOREST = Theme(
    id="forest",
    name="Whispering Forest",
    sky_top=(135, 206, 235),
    sky_bottom=(135, 206, 235),
    ground_color=(139, 90, 43),
    platform_color=(139, 90, 43),
    bump_layers=[
        BumpLayer((150, 178, 195), spacing=(200, 280), radius=(90, 140), parallax=0.1, base_offset=60),
        BumpLayer((139, 191, 141), spacing=(160, 240), radius=(60, 90), parallax=0.2, base_offset=35),
        BumpLayer((104, 172, 108), spacing=(120, 190), radius=(38, 58), parallax=0.4, base_offset=18),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 260, (30, 170), (26, 46), 0.25),
    ],
    ground_props=[
        GroundProp(shapes.draw_pine_tree, [(36, 100, 53), (46, 125, 66), (58, 145, 80)], (44, 72), (90, 150), 30),
        GroundProp(shapes.draw_bush, [(52, 130, 68), (66, 145, 80)], (9, 11), (55, 95), 20),
        GroundProp(shapes.draw_flower, [(255, 255, 255), (255, 214, 90), (255, 150, 180)], (11, 13), (40, 80), 15),
    ],
)

DESERT = Theme(
    id="desert",
    name="Sunfall Desert",
    sky_top=(120, 170, 220),
    sky_bottom=(255, 224, 178),
    ground_color=(224, 178, 110),
    platform_color=(224, 178, 110),
    bump_layers=[
        BumpLayer((230, 196, 140), spacing=(220, 300), radius=(80, 130), parallax=0.1, base_offset=50),
        BumpLayer((214, 170, 105), spacing=(170, 240), radius=(55, 85), parallax=0.25, base_offset=25),
        BumpLayer((196, 150, 85), spacing=(130, 190), radius=(35, 55), parallax=0.45, base_offset=12),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_sun, [(255, 210, 90)], lambda w: 1, (55, 55), (42, 42), 0.05),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: max(1, w // 500), (30, 70), (16, 22), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_cactus, [(60, 120, 70), (70, 135, 80)], (40, 60), (140, 220), 30),
        GroundProp(shapes.draw_bush, [(150, 140, 80), (160, 150, 90)], (7, 9), (70, 110), 20),
    ],
)

ARABIAN_NIGHT = Theme(
    id="arabian_night",
    name="Arabian Night",
    sky_top=(18, 18, 50),
    sky_bottom=(58, 36, 82),
    ground_color=(90, 65, 45),
    platform_color=(90, 65, 45),
    bump_layers=[
        BumpLayer((45, 40, 75), spacing=(220, 300), radius=(80, 130), parallax=0.1, base_offset=55),
        BumpLayer((60, 50, 90), spacing=(170, 240), radius=(55, 85), parallax=0.25, base_offset=28),
        BumpLayer((75, 60, 100), spacing=(130, 190), radius=(35, 55), parallax=0.45, base_offset=14),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_star, [(255, 255, 235)], lambda w: w // 110, (20, 140), (2, 4), 0.15),
        FloatyLayer(shapes.draw_moon, [(245, 235, 200)], lambda w: 1, (55, 55), (32, 32), 0.05),
    ],
    ground_props=[
        GroundProp(shapes.draw_minaret, [(70, 55, 90), (80, 64, 100)], (55, 80), (180, 260), 40),
        GroundProp(shapes.draw_palm_tree, [(70, 150, 90)], (45, 65), (100, 160), 25),
    ],
)

UNDERWATER = Theme(
    id="underwater",
    name="Coral Deep",
    sky_top=(80, 180, 200),
    sky_bottom=(10, 50, 90),
    ground_color=(194, 178, 128),
    platform_color=(194, 178, 128),
    bump_layers=[
        BumpLayer((50, 110, 130), spacing=(200, 280), radius=(80, 130), parallax=0.1, base_offset=50),
        BumpLayer((40, 130, 140), spacing=(160, 230), radius=(55, 85), parallax=0.25, base_offset=25),
        BumpLayer((30, 150, 150), spacing=(120, 180), radius=(35, 55), parallax=0.45, base_offset=12),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_bubble, [(230, 245, 255)], lambda w: w // 150, (20, 180), (4, 10), 0.3),
        FloatyLayer(shapes.draw_fish, [(230, 140, 90), (240, 170, 60), (150, 120, 210)], lambda w: w // 300, (60, 160), (12, 18), 0.2),
    ],
    ground_props=[
        GroundProp(shapes.draw_coral, [(230, 110, 120), (240, 150, 90), (180, 110, 200)], (30, 50), (90, 150), 25),
        GroundProp(shapes.draw_seaweed, [(50, 140, 90), (60, 155, 100)], (35, 55), (60, 100), 15),
    ],
)

SKY = Theme(
    id="sky",
    name="Cloud Kingdom",
    sky_top=(150, 210, 255),
    sky_bottom=(225, 242, 255),
    ground_color=(235, 235, 240),
    platform_color=(235, 235, 240),
    bump_layers=[
        BumpLayer((255, 255, 255), spacing=(200, 280), radius=(90, 140), parallax=0.1, base_offset=55),
        BumpLayer((240, 248, 255), spacing=(160, 230), radius=(60, 90), parallax=0.25, base_offset=28),
        BumpLayer((225, 240, 255), spacing=(120, 190), radius=(38, 58), parallax=0.45, base_offset=14),
    ],
    floaty_layers=[
        FloatyLayer(shapes.draw_bird, [(90, 80, 80)], lambda w: 6, (40, 160), (10, 16), 0.3),
        FloatyLayer(shapes.draw_cloud, [(255, 255, 255)], lambda w: w // 300, (20, 80), (20, 30), 0.15),
    ],
    ground_props=[
        GroundProp(shapes.draw_floating_island, [(150, 120, 90)], (40, 60), (160, 240), 40),
        GroundProp(shapes.draw_bush, [(130, 200, 110)], (8, 10), (70, 110), 20),
    ],
)

THEMES = {theme.id: theme for theme in (FOREST, DESERT, ARABIAN_NIGHT, UNDERWATER, SKY)}


def get_theme(theme_id):
    return THEMES[theme_id]

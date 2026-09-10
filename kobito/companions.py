# The AI hint companion roster. `id` doubles as the folder name under
# assets/sprites/<id>/ for that companion's expression frames (see
# kobito/companion_art.py). `personality` feeds HintService's prompt to
# Claude so each companion's hints come back in its own voice; `color`
# only shades the placeholder art used for any expression without a
# real frame yet.
COMPANIONS = [
    {
        "id": "kobito",
        "name": "Kobito",
        "tagline": "A gentle forest spirit",
        "personality": "a small, warm, gentle forest-spirit companion who encourages softly",
        "color": (139, 195, 116),
    },
    {
        "id": "ushi",
        "name": "Ushi",
        "tagline": "A calm, motherly cow spirit",
        "personality": "a calm, patient, motherly cow spirit who reassures like an old friend",
        "color": (230, 220, 230),
    },
    {
        "id": "hana",
        "name": "Hana",
        "tagline": "A bright, cheerful flower spirit",
        "personality": "a bright, bubbly, endlessly cheerful flower spirit, full of energy",
        "color": (235, 90, 150),
    },
    {
        "id": "umeshu",
        "name": "Ume-shu",
        "tagline": "An elegant, quietly wise plum spirit",
        "personality": "an elegant, soft-spoken, quietly wise plum-blossom spirit",
        "color": (200, 150, 200),
    },
    {
        "id": "kinoko",
        "name": "Kinoko",
        "tagline": "A playful, quirky mushroom spirit",
        "personality": "a playful, quirky, slightly mischievous mushroom spirit who loves puns",
        "color": (206, 74, 66),
    },
]


def get_companion(companion_id):
    for companion in COMPANIONS:
        if companion["id"] == companion_id:
            return companion
    raise ValueError(f"Unknown companion id: {companion_id!r}")

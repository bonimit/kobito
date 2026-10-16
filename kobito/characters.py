# The mascot roster. `id` doubles as the folder name under
# assets/sprites/<id>/ where real frame PNGs go later; `color` is only
# used to generate placeholder art until those frames exist.
#
# `favorites` are two item ids (see kobito/items.py) that character loves:
# levels scatter them around, and picking one up earns extra score, a
# little power, and a happy reaction from the companion.
CHARACTERS = [
    {"id": "capybara", "name": "Capybara", "color": (150, 111, 51), "favorites": ["yuzu", "watermelon"]},
    {"id": "sloth", "name": "Sloth", "color": (121, 85, 61), "favorites": ["leaf", "hibiscus"]},
    {"id": "kitsune", "name": "Kitsune", "color": (240, 225, 200), "favorites": ["inari", "aburaage"]},
    {"id": "wombat", "name": "Wombat", "color": (163, 133, 96), "favorites": ["sweet_potato", "grass"]},
    {"id": "otter", "name": "Otter", "color": (101, 67, 33), "favorites": ["clam", "fish"]},
    {"id": "scottish_fold", "name": "Scottish Fold", "color": (180, 180, 190), "favorites": ["tuna", "milk"]},
    {"id": "frenchie", "name": "Frenchie", "color": (222, 184, 135), "favorites": ["bone", "sausage"]},
]


def get_character(character_id):
    for character in CHARACTERS:
        if character["id"] == character_id:
            return character
    raise ValueError(f"Unknown character id: {character_id!r}")

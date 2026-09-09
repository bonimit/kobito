# The mascot roster. `id` doubles as the folder name under
# assets/sprites/<id>/ where real frame PNGs go later; `color` is only
# used to generate placeholder art until those frames exist.
CHARACTERS = [
    {"id": "capybara", "name": "Capybara", "color": (150, 111, 51)},
    {"id": "sloth", "name": "Sloth", "color": (121, 85, 61)},
    {"id": "kitsune", "name": "Kitsune", "color": (240, 225, 200)},
    {"id": "wombat", "name": "Wombat", "color": (163, 133, 96)},
    {"id": "otter", "name": "Otter", "color": (101, 67, 33)},
    {"id": "scottish_fold", "name": "Scottish Fold", "color": (180, 180, 190)},
    {"id": "frenchie", "name": "Frenchie", "color": (222, 184, 135)},
]


def get_character(character_id):
    for character in CHARACTERS:
        if character["id"] == character_id:
            return character
    raise ValueError(f"Unknown character id: {character_id!r}")

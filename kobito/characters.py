# The mascot roster. `id` doubles as the folder name under
# assets/sprites/<id>/ where real frame PNGs go later; `color` is only
# used to generate placeholder art until those frames exist.
#
# `jp` and `blurb` are shown on the mascot-select screen.
#
# `favorites` are two item ids (see kobito/items.py) that character loves:
# levels scatter them around, and picking one up earns extra score, a
# little power, and a happy reaction from the companion.
CHARACTERS = [
    {"id": "capybara", "name": "Capybara", "jp": "カピバラ", "color": (150, 111, 51), "favorites": ["yuzu", "watermelon"],
     "blurb": "Unbothered and endlessly chill -- friends with absolutely everyone."},
    {"id": "sloth", "name": "Sloth", "jp": "ナマケモノ", "color": (121, 85, 61), "favorites": ["leaf", "hibiscus"],
     "blurb": "Slow and steady... very, very steady. Never in a hurry, never lost."},
    {"id": "kitsune", "name": "Kitsune", "jp": "きつね", "color": (240, 225, 200), "favorites": ["inari", "aburaage"],
     "blurb": "A clever little fox spirit with a weakness for fried tofu."},
    {"id": "wombat", "name": "Wombat", "jp": "ウォンバット", "color": (163, 133, 96), "favorites": ["sweet_potato", "grass"],
     "blurb": "Small, stubborn and built like a tank. Digs first, asks later."},
    {"id": "otter", "name": "Otter", "jp": "カワウソ", "color": (101, 67, 33), "favorites": ["clam", "fish"],
     "blurb": "A playful swimmer who never, ever lets go of a good clam."},
    {"id": "scottish_fold", "name": "Scottish Fold", "jp": "スコティッシュ", "color": (180, 180, 190),
     "favorites": ["tuna", "milk"], "blurb": "Folded ears, curious mind. Naps in boxes between levels."},
    {"id": "frenchie", "name": "Frenchie", "jp": "フレンチブル", "color": (222, 184, 135), "favorites": ["bone", "sausage"],
     "blurb": "Big ears, bigger heart. Snores like a tiny engine."},
]


def get_character(character_id):
    for character in CHARACTERS:
        if character["id"] == character_id:
            return character
    raise ValueError(f"Unknown character id: {character_id!r}")

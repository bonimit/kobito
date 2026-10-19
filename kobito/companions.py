# The AI hint companion roster. `id` doubles as the folder name under
# assets/sprites/<id>/ for that companion's expression frames (see
# kobito/companion_art.py). `personality` feeds HintService's prompt to
# Claude so each companion's hints come back in its own voice; `color`
# only shades the placeholder art used for any expression without a
# real frame yet.
#
# Each companion also carries a small, concrete gameplay ability
# (applied in Game._trigger_question and QuizScreen) so "pick a
# companion" is a real choice, not just a skin -- shown on the
# companion-select screen as `ability_name` / `ability_description`,
# along with `jp` (its name in Japanese) and a `greeting` in its voice;
# `reactions` open its hint after a wrong answer.
# Kobito is the baseline with no modifier; every multiplier/bonus below
# is relative to that.
COMPANIONS = [
    {
        "id": "kobito",
        "name": "Kobito",
        "jp": "こびと",
        "reactions": ["Not quite -- and that's okay!", "Almost! Let's look at it together."],
        "greeting": "Hi, I'm Kobito! Take your time -- I'll be right here whenever you get stuck.",
        "tagline": "A gentle forest spirit",
        "personality": "a small, warm, gentle forest-spirit companion who encourages softly",
        "color": (139, 195, 116),
        "ability_name": "Balanced Guide",
        "ability_description": "No bonus, no penalty -- steady, reliable hints.",
        "xp_gain_multiplier": 1.0,
        "xp_penalty_multiplier": 1.0,
        "bonus_score": 0,
        "always_show_explanation": False,
    },
    {
        "id": "ushi",
        "name": "Ushi",
        "jp": "うし",
        "reactions": ["Easy now, dear -- you were close.", "No worries. Let's see why together."],
        "greeting": "Moo~ No rush, dear. Every mistake is just a lesson wearing a disguise.",
        "tagline": "A calm, motherly cow spirit",
        "personality": "a calm, patient, motherly cow spirit who reassures like an old friend",
        "color": (230, 220, 230),
        "ability_name": "Steady Heart",
        "ability_description": "Wrong answers cost 25% less XP -- mistakes sting less.",
        "xp_gain_multiplier": 1.0,
        "xp_penalty_multiplier": 0.75,
        "bonus_score": 0,
        "always_show_explanation": False,
    },
    {
        "id": "hana",
        "name": "Hana",
        "jp": "はな",
        "reactions": ["Ooh, so close!", "Aww, almost! You've totally got this!"],
        "greeting": "Yay, let's go!! I'm going to cheer for every single right answer!",
        "tagline": "A bright, cheerful flower spirit",
        "personality": "a bright, bubbly, endlessly cheerful flower spirit, full of energy",
        "color": (235, 90, 150),
        "ability_name": "Bright Spark",
        "ability_description": "Correct answers earn 10% more XP.",
        "xp_gain_multiplier": 1.10,
        "xp_penalty_multiplier": 1.0,
        "bonus_score": 0,
        "always_show_explanation": False,
    },
    {
        "id": "umeshu",
        "name": "Ume-shu",
        "jp": "うめしゅ",
        "reactions": ["Not this time. Allow me to explain.", "A small slip. Here is the reason."],
        "greeting": "Shall we begin? I will always show you the why behind each answer.",
        "tagline": "An elegant, quietly wise plum spirit",
        "personality": "an elegant, soft-spoken, quietly wise plum-blossom spirit",
        "color": (200, 150, 200),
        "ability_name": "Deep Insight",
        "ability_description": "Hints always include the full explanation -- nothing stays unclear.",
        "xp_gain_multiplier": 1.0,
        "xp_penalty_multiplier": 1.0,
        "bonus_score": 0,
        "always_show_explanation": True,
    },
    {
        "id": "kinoko",
        "name": "Kinoko",
        "jp": "きのこ",
        "reactions": ["Oops! Mushroom for improvement!", "Whoopsie! Let's spore-t this out."],
        "greeting": "Hey hey! Ready for a fun-gi time? ...Fun-gi? Get it? Mushroom joke!",
        "tagline": "A playful, quirky mushroom spirit",
        "personality": "a playful, quirky, slightly mischievous mushroom spirit who loves puns",
        "color": (206, 74, 66),
        "ability_name": "Playful Streak",
        "ability_description": "Every correct answer earns +2 flat bonus points.",
        "xp_gain_multiplier": 1.0,
        "xp_penalty_multiplier": 1.0,
        "bonus_score": 2,
        "always_show_explanation": False,
    },
]


def get_companion(companion_id):
    for companion in COMPANIONS:
        if companion["id"] == companion_id:
            return companion
    raise ValueError(f"Unknown companion id: {companion_id!r}")

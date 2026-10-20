"""Costumes, accessories and the konbini's shelves.

GEAR is everything the mascot can wear -- one HEAD item and one BACK item
at a time (kobito/gear_art.py draws them on the sprite). Most of it is
unlocked by ability level (kobito/profile.py); a few pieces are bought
at the konbini. Some have a perk:

    fly    -- propeller cap: hold jump in mid-air to fly up for a while
    guard  -- samurai kabuto: the first enemy hit in each stage is blocked
    flap   -- tengu wings: one extra flap in the air
    lucky  -- crown: +50% 円 from everything

PRODUCTS is the konbini: study books (study EXP -> ability level), gear,
and boosts used up at the start of the next stage. Every name comes with
its Japanese word and reading, so shopping is vocabulary practice too.
"""

from dataclasses import dataclass

HEAD, BACK = "head", "back"
SLOTS = (HEAD, BACK)


@dataclass(frozen=True)
class Gear:
    id: str
    name: str
    jp: str
    reading: str
    slot: str
    blurb: str
    unlock_level: int = 0      # 0: bought at the konbini instead
    price: int = 0
    perk: str = ""
    perk_text: str = ""


_GEAR = [
    Gear("hachimaki", "Hachimaki", "はちまき", "hachimaki", HEAD,
         "A headband tied on for a big effort -- like exam week.", unlock_level=2),
    Gear("straw_hat", "Straw hat", "麦わら帽子", "mugiwara bōshi", HEAD,
         "Summer holidays in the countryside.", unlock_level=3),
    Gear("kabuto", "Samurai kabuto", "兜", "kabuto", HEAD,
         "A samurai helmet with golden horns.", unlock_level=5,
         perk="guard", perk_text="Blocks the first enemy hit in each stage."),
    Gear("fox_mask", "Fox mask", "きつねのお面", "kitsune no omen", HEAD,
         "A festival mask, worn on the side of the head.", unlock_level=7),
    Gear("grad_cap", "Graduation cap", "角帽", "kakubō", HEAD,
         "For a scholar who's studied hard.", unlock_level=10),
    Gear("crown", "Crown", "王冠", "ōkan", HEAD,
         "Only for the very best students.", unlock_level=15,
         perk="lucky", perk_text="+50% 円 from coins, answers and stage clears."),
    Gear("propeller", "Propeller cap", "プロペラ帽子", "puropera bōshi", HEAD,
         "A whirring cap that lifts you into the sky.", price=1500,
         perk="fly", perk_text="Hold jump in mid-air to fly up (2 seconds per jump)."),
    Gear("randoseru", "Randoseru", "ランドセル", "randoseru", BACK,
         "The sturdy school bag every first-grader carries.", unlock_level=4),
    Gear("cape", "Hero cape", "マント", "manto", BACK,
         "Flaps in the wind when you run.", unlock_level=6),
    Gear("koinobori", "Koinobori", "こいのぼり", "koinobori", BACK,
         "Carp streamers for Children's Day.", unlock_level=9),
    Gear("tengu_wings", "Tengu wings", "天狗の羽", "tengu no hane", BACK,
         "Wings of the mountain spirit.", unlock_level=12,
         perk="flap", perk_text="One extra flap in the air."),
    Gear("furoshiki", "Furoshiki bundle", "風呂敷", "furoshiki", BACK,
         "A cloth that wraps anything -- a lunch, a gift, a whole bundle.", price=400),
    Gear("taiko", "Taiko drum", "太鼓", "taiko", BACK,
         "A festival drum, ready for the summer matsuri.", price=900),
]
GEAR = {g.id: g for g in _GEAR}


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    jp: str
    reading: str
    kind: str            # "study" / "gear" / "boost"
    price: int
    text: str
    exp: int = 0         # study EXP (study books)


BOOSTS = {"omamori", "sun_seeds", "eiyo_drink", "protein_bar"}

PRODUCTS = [
    Product("notebook", "Notebook", "ノート", "nōto", "study", 200, "+60 study EXP", exp=60),
    Product("flashcards", "Flashcards", "単語カード", "tango kādo", "study", 350, "+110 study EXP", exp=110),
    Product("kanji_drill", "Kanji drill", "漢字ドリル", "kanji doriru", "study", 600, "+200 study EXP", exp=200),
    Product("textbook", "Study guide", "参考書", "sankōsho", "study", 1500, "+550 study EXP", exp=550),
    Product("propeller", "Propeller cap", "プロペラ帽子", "puropera bōshi", "gear", 1500,
            "Wear it to fly: hold jump in the air"),
    Product("furoshiki", "Furoshiki", "風呂敷", "furoshiki", "gear", 400, "A cloth bundle to wear on your back"),
    Product("taiko", "Taiko drum", "太鼓", "taiko", "gear", 900, "A festival drum to wear on your back"),
    Product("omamori", "Omamori charm", "お守り", "omamori", "boost", 400, "Next stage: +1 life"),
    Product("sun_seeds", "Sunflower seeds", "ひまわりの種", "himawari no tane", "boost", 500,
            "Next stage: start with sun power"),
    Product("eiyo_drink", "Energy drink", "栄養ドリンク", "eiyō dorinku", "boost", 250,
            "Next stage: 15 s speed boost"),
    Product("protein_bar", "Protein bar", "プロテインバー", "purotein bā", "boost", 350,
            "Next stage: GUARD ×2 -- two enemy hits bounce off"),
]
PRODUCT_BY_ID = {p.id: p for p in PRODUCTS}


def unlocks_by_level():
    """[(level, gear)] for everything levelling up unlocks, lowest first."""
    return sorted(((g.unlock_level, g) for g in _GEAR if g.unlock_level), key=lambda pair: pair[0])


def next_unlock(level):
    """The next piece of gear a higher level unlocks, or None."""
    for unlock_level, gear in unlocks_by_level():
        if unlock_level > level:
            return gear
    return None

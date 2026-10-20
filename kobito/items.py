"""Every collectible the player can pick up, as plain data.

Three families:
  * konbini  -- things you'd really grab at a Japanese convenience store
                (energy drinks, canned coffee, onigiri, candy ...). Each
                refills some POWER, which is how a drowsy player wakes up.
  * rare     -- lucky finds, mostly out of gift boxes.
  * favorite -- each mascot's own favourite food/toy (see characters.py).

Every item also carries the Japanese word for it, so the AI companion can
turn a pickup into a tiny vocabulary lesson (kobito/item_coach.py): the
word, its reading, what it means, and an example sentence.

And every item has a ROLE -- what it does for you -- shown when you pick it
up and in the Item Box (benefits() spells it out):
  * POWER    -- refills the power gauge (wakes a drowsy player)
  * SKILL    -- study EXP toward your ability level (the elixir, tea, coffee ...)
  * STRENGTH -- a guard: the next enemy hit(s) bounce off you, nothing lost
  * SPEED    -- a burst of running speed for a few seconds
  * LIFE     -- +1 life
  * LUCKY    -- 円 to spend at the konbini
  * SUN      -- sun power: throw sunballs, enemies can't hurt you

Brand names are deliberately not used; the energy drinks are generic.
"""

import random
from dataclasses import dataclass

from kobito.constants import FAVORITE_POWER, FAVORITE_SCORE

FAVORITE_EXP = 25


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    jp: str
    reading: str
    meaning: str
    example: str
    example_en: str
    group: str            # "konbini" | "rare" | "favorite" | "treasure" | "power"
    power: int = 0
    score: int = 10
    life: int = 0
    full_power: bool = False
    boost_seconds: float = 0.0   # temporary speed boost
    exp: int = 0                 # study EXP (SKILL)
    guard: int = 0               # enemy hits blocked (STRENGTH)
    yen: int = 0                 # 円 (LUCKY)
    role: str = "power"          # the main one, see ROLES


# Each role's label and colour (pickup pop-ups, the Item Box).
ROLES = {
    "power": ("POWER", (130, 230, 140)),
    "skill": ("SKILL", (150, 205, 255)),
    "strength": ("STRENGTH", (255, 170, 110)),
    "speed": ("SPEED", (120, 240, 230)),
    "life": ("LIFE", (255, 150, 160)),
    "lucky": ("LUCKY", (255, 214, 90)),
    "sun": ("SUN", (255, 190, 60)),
}


def benefits(item):
    """What an item does, as short tags: ["+4 POWER", "+20 SKILL", ...]."""
    tags = []
    if item.group == "power":
        tags.append("SUN POWER")
    if item.full_power:
        tags.append("FULL POWER")
    elif item.power:
        tags.append(f"+{item.power} POWER")
    if item.exp:
        tags.append(f"+{item.exp} SKILL")
    if item.guard:
        tags.append(f"GUARD ×{item.guard}")
    if item.boost_seconds:
        tags.append(f"SPEED {item.boost_seconds:g}s")
    if item.life:
        tags.append(f"+{item.life} LIFE")
    if item.yen:
        tags.append(f"+{item.yen}円")
    return tags


def role_text(item):
    """One plain sentence on what the item is for."""
    return {
        "power": "Refills your power gauge.",
        "skill": "Study EXP: raises your ability level.",
        "strength": "Makes you strong: enemy hits bounce off.",
        "speed": "A burst of speed.",
        "life": "An extra life.",
        "lucky": "円 to spend at the konbini.",
        "sun": "Throw sunballs; enemies can't hurt you.",
    }[item.role]


def _konbini(id, name, jp, reading, meaning, example, example_en, power, score=10, **role):
    return Item(id, name, jp, reading, meaning, example, example_en, "konbini", power=power, score=score, **role)


def _favorite(id, name, jp, reading, meaning, example, example_en):
    # Your very favourite thing: power, and the motivation to study (SKILL).
    return Item(id, name, jp, reading, meaning, example, example_en, "favorite",
                power=FAVORITE_POWER, score=FAVORITE_SCORE, exp=FAVORITE_EXP, role="skill")


ITEMS = {item.id: item for item in [
    _konbini("energy_drink", "Genki Can", "エナジードリンク", "enajii dorinku", "energy drink",
             "エナジードリンクをください。", "One energy drink, please.", 4, boost_seconds=4.0),
    _konbini("mega_can", "Mega Can", "大きい缶", "ookii kan", "big can",
             "この缶は大きいです。", "This can is big.", 5, 15, guard=1, role="strength"),
    _konbini("ume_soda", "Ume Soda", "梅ソーダ", "ume sooda", "plum soda",
             "梅ソーダが好きです。", "I like plum soda.", 3),
    _konbini("candy", "Candy", "飴", "ame", "candy",
             "飴を食べます。", "I eat a candy.", 1, 5, exp=10, role="skill"),
    _konbini("onigiri", "Onigiri", "おにぎり", "onigiri", "rice ball",
             "おにぎりを食べます。", "I eat an onigiri.", 3, guard=1, role="strength"),
    _konbini("canned_coffee", "Kan Coffee", "缶コーヒー", "kan koohii", "canned coffee",
             "缶コーヒーを飲みます。", "I drink canned coffee.", 3, exp=15, role="skill"),
    _konbini("melon_pan", "Melon Pan", "メロンパン", "meron pan", "melon bread",
             "メロンパンはおいしいです。", "Melon bread is delicious.", 3),
    _konbini("green_tea", "Ocha", "お茶", "ocha", "green tea",
             "お茶をください。", "Green tea, please.", 2, exp=20, role="skill"),
    _konbini("gummy", "Gummy", "グミ", "gumi", "gummy candy",
             "グミが好きです。", "I like gummy candy.", 2, boost_seconds=3.0, role="speed"),
    _konbini("dried_ume", "Dried Ume", "干し梅", "hoshi ume", "dried plum",
             "干し梅は酸っぱいです。", "Dried plums are sour.", 2, exp=10, role="skill"),
    _konbini("nuts", "Nuts", "ナッツ", "nattsu", "nuts",
             "ナッツを食べます。", "I eat nuts.", 3, guard=1, role="strength"),
    _konbini("protein_bar", "Protein Bar", "プロテインバー", "purotein baa", "protein bar",
             "プロテインバーで強くなります。", "A protein bar makes me strong.", 2, 15, guard=2, role="strength"),

    Item("lucky_bag", "Lucky Bag", "福袋", "fukubukuro", "lucky bag (a New Year mystery bag)",
         "福袋を買いました。", "I bought a lucky bag.", "rare",
         power=10, score=60, life=1, full_power=True, yen=200, role="lucky"),
    Item("golden_can", "Golden Can", "金の缶", "kin no kan", "golden can",
         "金の缶を見つけました。", "I found the golden can.", "rare",
         power=10, score=40, full_power=True, boost_seconds=8.0, role="speed"),
    Item("elixir", "Elixir", "エリクサー", "erikusaa", "elixir (a magic potion)",
         "エリクサーを飲んで、頭がよくなりました。", "I drank the elixir and got smarter.", "rare",
         power=10, score=60, full_power=True, exp=150, role="skill"),
    Item("maneki_neko", "Maneki Neko", "招き猫", "maneki neko", "beckoning cat (a lucky charm)",
         "招き猫はお金を招きます。", "The beckoning cat invites money.", "rare",
         power=2, score=50, yen=300, role="lucky"),

    # Treasures: one waits in each hidden underground stage (see
    # kobito/levels/underground.py) and nowhere else...
    Item("ekiben", "Ekiben", "駅弁", "ekiben", "station bento (a boxed lunch sold at train stations)",
         "駅弁を電車で食べます。", "I eat a station bento on the train.", "treasure",
         power=10, score=80, full_power=True, guard=2, role="strength"),
    Item("pizza_bun", "Pizza Bun", "ピザまん", "pizaman", "pizza bun (a steamed bun with pizza filling)",
         "ピザまんは熱いです。", "The pizza bun is hot.", "treasure",
         power=6, score=70, boost_seconds=6.0, role="speed"),
    Item("gem", "Gem", "宝石", "houseki", "gem, jewel",
         "宝石を見つけました。", "I found a gem.", "treasure",
         power=2, score=150, life=1, yen=300, role="lucky"),
    # ...and one in each hidden sky stage (kobito/levels/sky.py).
    Item("kaminari_okoshi", "Kaminari Okoshi", "雷おこし", "kaminari okoshi",
         "kaminari okoshi (a crunchy puffed-rice sweet from Asakusa)",
         "雷おこしはかたいです。", "Kaminari okoshi is crunchy.", "treasure",
         power=4, score=80, boost_seconds=8.0, guard=1, role="speed"),
    Item("wataame", "Cotton Candy", "綿あめ", "wataame", "cotton candy",
         "綿あめは雲みたいです。", "Cotton candy is like a cloud.", "treasure",
         power=6, score=70, exp=60, role="skill"),
    Item("tsukimi_dango", "Tsukimi Dango", "月見団子", "tsukimi dango", "moon-viewing dumplings",
         "月見団子を食べます。", "I eat moon-viewing dumplings.", "treasure",
         power=10, score=100, life=1, full_power=True, role="life"),

    # Power-up: eat it and the run button throws bouncing sunballs that
    # defeat enemies, and touching an enemy defeats it too -- no hit costs
    # power or XP while it lasts.
    Item("sunflower", "Sunflower", "ひまわり", "himawari", "sunflower",
         "ひまわりは太陽が好きです。", "Sunflowers love the sun.", "power",
         power=2, score=50, role="sun"),

    _favorite("yuzu", "Yuzu", "ゆず", "yuzu", "yuzu citrus",
              "ゆずの匂いが好きです。", "I like the smell of yuzu."),
    _favorite("watermelon", "Watermelon", "すいか", "suika", "watermelon",
              "すいかを食べます。", "I eat watermelon."),
    _favorite("leaf", "Leaf", "葉っぱ", "happa", "leaf",
              "葉っぱが大好きです。", "I love leaves."),
    _favorite("hibiscus", "Hibiscus", "ハイビスカス", "haibisukasu", "hibiscus",
              "ハイビスカスはきれいです。", "The hibiscus is pretty."),
    _favorite("inari", "Inari Sushi", "いなり寿司", "inari zushi", "inari sushi (rice in fried tofu)",
              "いなり寿司を食べます。", "I eat inari sushi."),
    _favorite("aburaage", "Aburaage", "油揚げ", "aburaage", "fried tofu pouch",
              "油揚げが大好きです。", "I love fried tofu."),
    _favorite("sweet_potato", "Sweet Potato", "さつまいも", "satsumaimo", "sweet potato",
              "さつまいもは甘いです。", "Sweet potatoes are sweet."),
    _favorite("grass", "Fresh Grass", "草", "kusa", "grass",
              "草が好きです。", "I like grass."),
    _favorite("clam", "Asari Clam", "あさり", "asari", "clam",
              "あさりを食べます。", "I eat clams."),
    _favorite("fish", "Fish", "魚", "sakana", "fish",
              "魚が好きです。", "I like fish."),
    _favorite("tuna", "Tuna", "ツナ", "tsuna", "tuna",
              "ツナが大好きです。", "I love tuna."),
    _favorite("milk", "Milk", "牛乳", "gyuunyuu", "milk",
              "牛乳を飲みます。", "I drink milk."),
    _favorite("bone", "Bone", "骨", "hone", "bone",
              "骨が好きです。", "I like bones."),
    _favorite("sausage", "Sausage", "ソーセージ", "sooseeji", "sausage",
              "ソーセージを食べます。", "I eat sausage."),
]}

KONBINI_IDS = [i.id for i in ITEMS.values() if i.group == "konbini"]
RARE_IDS = [i.id for i in ITEMS.values() if i.group == "rare"]
TREASURE_IDS = [i.id for i in ITEMS.values() if i.group == "treasure"]
BIG_DRINKS = ["energy_drink", "mega_can", "canned_coffee"]
SMALL_SNACKS = ["candy", "onigiri", "melon_pan", "green_tea", "ume_soda", "gummy", "dried_ume", "nuts", "protein_bar"]


def get_item(item_id):
    return ITEMS[item_id]


# What a gift box can hold. Weights add up to 100. A sleepy player gets a
# better table -- see roll_gift -- so a gift box is also a lifeline.
GIFT_TABLE = [
    ("coins", 20), ("snack", 28), ("drink", 18),
    ("favorite", 10), ("life", 10), ("rare", 8), ("sunflower", 6),
]
SLEEPY_GIFT_TABLE = [
    ("coins", 6), ("snack", 28), ("drink", 40),
    ("favorite", 6), ("life", 8), ("rare", 10), ("sunflower", 2),
]


def roll_gift(rng, favorites, sleepy=False):
    """Returns a dict describing one gift box's contents:
    {"kind": "coins"|"item"|"life", "item": Item|None, "coins": int}.
    `rng` is a random.Random so tests (and levels) can be deterministic.
    """
    table = SLEEPY_GIFT_TABLE if sleepy else GIFT_TABLE
    roll = rng.uniform(0, sum(w for _, w in table))
    kind = table[-1][0]
    for name, weight in table:
        roll -= weight
        if roll <= 0:
            kind = name
            break

    if kind == "coins":
        return {"kind": "coins", "item": None, "coins": rng.choice((3, 4, 5))}
    if kind == "life":
        return {"kind": "life", "item": None, "coins": 0}
    pool = {
        "snack": SMALL_SNACKS, "drink": BIG_DRINKS, "rare": RARE_IDS, "sunflower": ["sunflower"],
        "favorite": list(favorites) or SMALL_SNACKS,
    }[kind]
    return {"kind": "item", "item": get_item(rng.choice(pool)), "coins": 0}

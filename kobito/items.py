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

Brand names are deliberately not used; the energy drinks are generic.
"""

import random
from dataclasses import dataclass

from kobito.constants import FAVORITE_POWER, FAVORITE_SCORE


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    jp: str
    reading: str
    meaning: str
    example: str
    example_en: str
    group: str            # "konbini" | "rare" | "favorite"
    power: int = 0
    score: int = 10
    life: int = 0
    full_power: bool = False
    boost_seconds: float = 0.0   # temporary speed boost


def _konbini(id, name, jp, reading, meaning, example, example_en, power, score=10):
    return Item(id, name, jp, reading, meaning, example, example_en, "konbini", power=power, score=score)


def _favorite(id, name, jp, reading, meaning, example, example_en):
    return Item(id, name, jp, reading, meaning, example, example_en, "favorite",
                power=FAVORITE_POWER, score=FAVORITE_SCORE)


ITEMS = {item.id: item for item in [
    _konbini("energy_drink", "Genki Can", "エナジードリンク", "enajii dorinku", "energy drink",
             "エナジードリンクをください。", "One energy drink, please.", 4),
    _konbini("mega_can", "Mega Can", "大きい缶", "ookii kan", "big can",
             "この缶は大きいです。", "This can is big.", 5, 15),
    _konbini("ume_soda", "Ume Soda", "梅ソーダ", "ume sooda", "plum soda",
             "梅ソーダが好きです。", "I like plum soda.", 3),
    _konbini("candy", "Candy", "飴", "ame", "candy",
             "飴を食べます。", "I eat a candy.", 1, 5),
    _konbini("onigiri", "Onigiri", "おにぎり", "onigiri", "rice ball",
             "おにぎりを食べます。", "I eat an onigiri.", 2),
    _konbini("canned_coffee", "Kan Coffee", "缶コーヒー", "kan koohii", "canned coffee",
             "缶コーヒーを飲みます。", "I drink canned coffee.", 3),
    _konbini("melon_pan", "Melon Pan", "メロンパン", "meron pan", "melon bread",
             "メロンパンはおいしいです。", "Melon bread is delicious.", 2),
    _konbini("green_tea", "Ocha", "お茶", "ocha", "green tea",
             "お茶をください。", "Green tea, please.", 2),

    Item("lucky_bag", "Lucky Bag", "福袋", "fukubukuro", "lucky bag (a New Year mystery bag)",
         "福袋を買いました。", "I bought a lucky bag.", "rare",
         power=10, score=60, life=1, full_power=True),
    Item("golden_can", "Golden Can", "金の缶", "kin no kan", "golden can",
         "金の缶を見つけました。", "I found the golden can.", "rare",
         power=10, score=40, full_power=True, boost_seconds=8.0),

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
BIG_DRINKS = ["energy_drink", "mega_can", "canned_coffee"]
SMALL_SNACKS = ["candy", "onigiri", "melon_pan", "green_tea", "ume_soda"]


def get_item(item_id):
    return ITEMS[item_id]


# What a gift box can hold. Weights add up to 100. A sleepy player gets a
# better table -- see roll_gift -- so a gift box is also a lifeline.
GIFT_TABLE = [
    ("coins", 24), ("snack", 30), ("drink", 18),
    ("favorite", 10), ("life", 10), ("rare", 8),
]
SLEEPY_GIFT_TABLE = [
    ("coins", 6), ("snack", 30), ("drink", 40),
    ("favorite", 6), ("life", 8), ("rare", 10),
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
        "snack": SMALL_SNACKS, "drink": BIG_DRINKS, "rare": RARE_IDS,
        "favorite": list(favorites) or SMALL_SNACKS,
    }[kind]
    return {"kind": "item", "item": get_item(rng.choice(pool)), "coins": 0}

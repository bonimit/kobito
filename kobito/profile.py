"""The player's long-term progress: ability level, money, and the
costumes, accessories and gadgets they own.

Unlike a run (character, level number, item box -- see save_game), the
profile is kept across runs: starting a new game keeps your level, your
円 and everything in your house.

  * Ability level (Lv) grows with study EXP: every right answer, every
    item picked up, every stage cleared, and study books bought at the
    konbini. Higher levels unlock costumes (kobito/wardrobe.py).
  * 円 (yen) comes from coins, right answers and stage clears, and is
    spent at the konbini (kobito/shop_screen.py).
  * Owned / equipped gear: one head item and one back item can be worn
    at a time; they show on the mascot in every stage, and some have a
    perk (the propeller cap flies, the kabuto blocks a hit, ...).
  * Stage boosts bought at the konbini wait in `boosts` and are used up
    at the start of the next stage.
  * Gamification (kobito/progress.py): lifetime `stats`, earned
    `trophies`, the daily study `streak` and today's `missions`. Things
    worth celebrating (a trophy, a finished mission) queue up in `events`
    for whichever screen is showing to pop up; they aren't saved.
"""

from kobito import wardrobe

MAX_LEVEL = 20

# Study EXP...
EXP_CORRECT = 10       # a right answer in a stage
EXP_TEST = 5           # a right answer in the Stage Test
EXP_ITEM = 3           # any item picked up (snacks, favourites, treasures)
EXP_CLEAR = 30         # clearing a stage
EXP_BADGE = 40         # ...with its badge
# ...and 円
YEN_COIN = 10
YEN_CORRECT = 20
YEN_CLEAR = 200
YEN_BADGE = 100


def exp_for_level(level):
    """Total study EXP needed to reach `level`: 100 for Lv 2, 300 for Lv 3,
    600 for Lv 4, ... each level asking 100 more than the last."""
    return 50 * (level - 1) * level


def level_for_exp(exp):
    level = 1
    while level < MAX_LEVEL and exp >= exp_for_level(level + 1):
        level += 1
    return level


class Profile:
    def __init__(self, exp=0, yen=0, owned=None, equipped=None, boosts=None, seen=None, stats=None, trophies=None,
                 streak=None, missions=None):
        self.exp = max(0, int(exp))
        self.yen = max(0, int(yen))
        self.owned = [g for g in (owned or []) if g in wardrobe.GEAR]
        equipped = equipped or {}
        self.equipped = {slot: equipped.get(slot) if equipped.get(slot) in wardrobe.GEAR else None
                         for slot in wardrobe.SLOTS}
        self.boosts = [b for b in (boosts or []) if b in wardrobe.BOOSTS]
        # Gear the player has already been told about, so "NEW!" tags and
        # unlock announcements happen once.
        self.seen = [g for g in (seen or []) if g in wardrobe.GEAR]
        self.stats = {k: int(v) for k, v in (stats or {}).items() if isinstance(v, (int, float)) and v >= 0}
        self.trophies = [t for t in (trophies or []) if isinstance(t, str)]
        streak = streak if isinstance(streak, dict) else {}
        self.streak = {"last": str(streak.get("last", "")), "days": int(streak.get("days", 0)),
                       "best": int(streak.get("best", 0))}
        self.missions = missions if isinstance(missions, dict) else {}
        self.events = []

    # -- Level ---------------------------------------------------------------

    @property
    def level(self):
        return level_for_exp(self.exp)

    def level_progress(self):
        """(EXP into this level, EXP this level needs) -- for a bar."""
        level = self.level
        if level >= MAX_LEVEL:
            return 1, 1
        start, end = exp_for_level(level), exp_for_level(level + 1)
        return self.exp - start, end - start

    def add_exp(self, amount):
        """Adds study EXP; returns the gear this unlocked (levels gained
        unlock costumes), so the caller can celebrate."""
        before = self.level
        self.exp += max(0, int(amount))
        if self.level == before:
            return []
        return [g for g in wardrobe.GEAR.values() if g.unlock_level and before < g.unlock_level <= self.level]

    # -- Gear ----------------------------------------------------------------

    def has(self, gear_id):
        gear = wardrobe.GEAR[gear_id]
        if gear.unlock_level:
            return self.level >= gear.unlock_level
        return gear_id in self.owned

    def available(self):
        """Everything the player can wear right now."""
        return [g for g in wardrobe.GEAR.values() if self.has(g.id)]

    def equip(self, gear_id):
        """Wears it (taking off whatever was in that slot); wearing the
        same thing again takes it off. Returns True if it's now worn."""
        gear = wardrobe.GEAR[gear_id]
        if not self.has(gear_id):
            return False
        if self.equipped[gear.slot] == gear_id:
            self.equipped[gear.slot] = None
            return False
        self.equipped[gear.slot] = gear_id
        return True

    def worn(self):
        """The ids of the gear being worn, head first."""
        return [self.equipped[slot] for slot in wardrobe.SLOTS if self.equipped[slot]]

    def perk(self, name):
        """True when something worn has this perk."""
        return any(wardrobe.GEAR[g].perk == name for g in self.worn())

    def is_new(self, gear_id):
        return self.has(gear_id) and gear_id not in self.seen

    def mark_seen(self, gear_id):
        if gear_id not in self.seen:
            self.seen.append(gear_id)

    # -- Money and shopping ----------------------------------------------------

    def add_yen(self, amount):
        bonus = 1.5 if self.perk("lucky") else 1.0
        self.yen += max(0, round(amount * bonus))

    def can_buy(self, product):
        if product.kind == "gear" and product.id in self.owned:
            return False
        if product.kind == "boost" and product.id in self.boosts:
            return False
        return self.yen >= product.price

    def buy(self, product):
        """Pays for it and applies it. Returns a list of gear newly unlocked
        (a study book can push the level up), or None if it couldn't."""
        if not self.can_buy(product):
            return None
        self.yen -= product.price
        if product.kind == "study":
            return self.add_exp(product.exp)
        if product.kind == "gear":
            self.owned.append(product.id)
        elif product.kind == "boost":
            self.boosts.append(product.id)
        return []

    def take_boosts(self):
        """The boosts for the stage that's starting (used up)."""
        boosts, self.boosts = self.boosts, []
        return boosts

    # -- Saving ----------------------------------------------------------------

    def to_dict(self):
        return {"exp": self.exp, "yen": self.yen, "owned": list(self.owned), "equipped": dict(self.equipped),
                "boosts": list(self.boosts), "seen": list(self.seen), "stats": dict(self.stats),
                "trophies": list(self.trophies), "streak": dict(self.streak), "missions": self.missions}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        try:
            return cls(exp=data.get("exp", 0), yen=data.get("yen", 0), owned=data.get("owned"),
                       equipped=data.get("equipped") if isinstance(data.get("equipped"), dict) else None,
                       boosts=data.get("boosts"), seen=data.get("seen"),
                       stats=data.get("stats") if isinstance(data.get("stats"), dict) else None,
                       trophies=data.get("trophies"), streak=data.get("streak"), missions=data.get("missions"))
        except (TypeError, ValueError):
            return cls()

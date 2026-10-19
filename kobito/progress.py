"""Gamification: lifetime stats, trophies, daily missions, the daily login
bonus and study streak, and rank titles. Everything lives on the player's
Profile (kobito/profile.py), so it's saved with it.

    progress.record(profile, "correct")        # count something
    progress.record_best(profile, "best_combo", 7)
    progress.daily_login(profile)              # once per day per player
    progress.today_missions(profile)

Recording a stat moves today's missions along and checks the trophies;
whatever is newly earned is paid out (円, study EXP) and appended to
profile.events -- {"kind", "title", "sub"} -- for the screen that's showing
to pop up as a toast (kobito/toasts.py).

Stats counted (by kobito/game.py and the town): answered, correct,
best_combo, stages, badges, perfect_tests, best_score, coins, stomps,
items, gifts, secrets, sunflowers, buys, dressed, days.
"""

import datetime
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Trophy:
    id: str
    name: str
    jp: str
    text: str
    stat: str      # a stats key, or "level" / "streak"
    goal: int
    tier: int      # 0 bronze, 1 silver, 2 gold
    reward: int    # 円


TIER_COLORS = ((205, 127, 70), (196, 204, 220), (255, 206, 70))
TIER_NAMES = ("BRONZE", "SILVER", "GOLD")

TROPHIES = [
    Trophy("first_answer", "First Step", "はじめの一歩", "Answer your first question", "answered", 1, 0, 50),
    Trophy("correct_50", "Bright Spark", "ひらめき", "50 right answers", "correct", 50, 0, 150),
    Trophy("correct_250", "Bookworm", "本の虫", "250 right answers", "correct", 250, 1, 400),
    Trophy("correct_1000", "Walking Dictionary", "生き字引", "1,000 right answers", "correct", 1000, 2, 1500),
    Trophy("combo_5", "On a Roll", "れんぞく", "5 right answers in a row", "best_combo", 5, 0, 100),
    Trophy("combo_10", "Unstoppable", "とまらない", "10 right answers in a row", "best_combo", 10, 1, 300),
    Trophy("combo_20", "Perfect Memory", "かんぺき", "20 right answers in a row", "best_combo", 20, 2, 800),
    Trophy("stage_1", "Stage Clear!", "ステージクリア", "Clear your first stage", "stages", 1, 0, 100),
    Trophy("stage_10", "Traveller", "たびびと", "Clear 10 stages", "stages", 10, 1, 500),
    Trophy("stage_30", "Explorer", "たんけんか", "Clear 30 stages", "stages", 30, 2, 1500),
    Trophy("badge_5", "Badge Collector", "バッジあつめ", "Earn 5 badges", "badges", 5, 1, 400),
    Trophy("perfect_test", "Full Marks", "満点", "Get every Stage Test question right", "perfect_tests", 1, 1, 300),
    Trophy("coins_500", "Piggy Bank", "ちょきん", "Collect 500 coins", "coins", 500, 0, 150),
    Trophy("coins_3000", "Treasure Hunter", "トレジャーハンター", "Collect 3,000 coins", "coins", 3000, 1, 500),
    Trophy("stomps_100", "Monster Buster", "モンスターたいじ", "Defeat 100 enemies", "stomps", 100, 1, 300),
    Trophy("items_100", "Snack Lover", "食いしんぼう", "Pick up 100 items", "items", 100, 0, 200),
    Trophy("gifts_25", "Present Opener", "プレゼント", "Open 25 gift boxes", "gifts", 25, 0, 200),
    Trophy("secrets_5", "Secret Seeker", "ひみつ", "Find 5 secret rooms", "secrets", 5, 1, 300),
    Trophy("sun_10", "Sunshine", "おひさま", "Eat 10 sunflowers", "sunflowers", 10, 0, 150),
    Trophy("first_buy", "Shopper", "おかいもの", "Buy something at the konbini", "buys", 1, 0, 50),
    Trophy("dressed", "Fashionista", "おしゃれ", "Wear a costume", "dressed", 1, 0, 50),
    Trophy("level_5", "Student", "学生", "Reach Lv 5", "level", 5, 0, 200),
    Trophy("level_10", "Senpai", "先輩", "Reach Lv 10", "level", 10, 1, 600),
    Trophy("level_20", "Master", "名人", "Reach Lv 20", "level", 20, 2, 2000),
    Trophy("streak_3", "Habit", "しゅうかん", "Study 3 days in a row", "streak", 3, 0, 150),
    Trophy("streak_7", "One Week", "一週間", "Study 7 days in a row", "streak", 7, 1, 500),
    Trophy("streak_30", "Dedicated", "毎日", "Study 30 days in a row", "streak", 30, 2, 2000),
]
TROPHY_BY_ID = {t.id: t for t in TROPHIES}

# Rank titles by ability level: (from Lv, kanji, reading, English).
RANKS = [(1, "入門", "nyūmon", "Newcomer"), (3, "見習い", "minarai", "Apprentice"), (5, "学生", "gakusei", "Student"),
         (8, "先輩", "senpai", "Senpai"), (12, "達人", "tatsujin", "Expert"), (16, "先生", "sensei", "Sensei"),
         (20, "名人", "meijin", "Master")]

# Daily missions: (stat, goal, words, 円). Three a day, picked per player.
MISSION_POOL = [
    ("correct", 10, "Answer 10 questions right", 150),
    ("correct", 20, "Answer 20 questions right", 250),
    ("answered", 25, "Answer 25 questions", 200),
    ("best_combo", 5, "Get 5 right in a row", 200),
    ("coins", 40, "Collect 40 coins", 150),
    ("stomps", 8, "Defeat 8 enemies", 150),
    ("items", 12, "Pick up 12 items", 150),
    ("gifts", 3, "Open 3 gift boxes", 150),
    ("stages", 1, "Clear a stage", 250),
    ("secrets", 1, "Find a secret room", 200),
]
MAX_STATS = {"best_combo", "best_score"}   # these keep the highest, not a total
MISSIONS_PER_DAY = 3
ALL_MISSIONS_BONUS = 300
MISSION_EXP = 30
DAILY_BONUS = 100            # 円 on the first day...
DAILY_BONUS_STEP = 50        # ...and this much more for each day of the streak
DAILY_BONUS_MAX_STEPS = 6    # (topping out at a week)


def today_str(today=None):
    return (today or datetime.date.today()).isoformat()


def rank_for(level):
    """(kanji, reading, English) of the rank title for an ability level."""
    title = RANKS[0]
    for rank in RANKS:
        if level >= rank[0]:
            title = rank
    return title[1:]


def stat_value(profile, key):
    if key == "level":
        return profile.level
    if key == "streak":
        return profile.streak.get("best", 0)
    return profile.stats.get(key, 0)


def _event(profile, kind, title, sub):
    profile.events.append({"kind": kind, "title": title, "sub": sub})


# -- Stats ---------------------------------------------------------------------

def record(profile, key, amount=1):
    """Counts `amount` more of a stat; moves missions on; checks trophies."""
    if key in MAX_STATS:
        return record_best(profile, key, amount)
    profile.stats[key] = profile.stats.get(key, 0) + amount
    _advance_missions(profile, key, amount)
    check_trophies(profile)


def record_best(profile, key, value):
    """Keeps the best value of a stat (best combo, best score)."""
    if value > profile.stats.get(key, 0):
        profile.stats[key] = value
    _advance_missions(profile, key, value)
    check_trophies(profile)


def check_trophies(profile):
    """Awards any trophy whose goal has been reached. Returns the new ones."""
    earned = []
    for trophy in TROPHIES:
        if trophy.id not in profile.trophies and stat_value(profile, trophy.stat) >= trophy.goal:
            profile.trophies.append(trophy.id)
            profile.yen += trophy.reward
            earned.append(trophy)
            _event(profile, "trophy", f"TROPHY: {trophy.name.upper()}", f"{trophy.jp} -- {trophy.text}  +{trophy.reward}円")
    return earned


# -- Daily missions --------------------------------------------------------------

def today_missions(profile, today=None, seed=None):
    """Today's three missions, picked fresh each day (the same ones all day,
    and different for each player)."""
    seed = getattr(profile, "seed", "") if seed is None else seed
    day = today_str(today)
    if profile.missions.get("day") != day:
        rng = random.Random(f"{seed}-{day}")
        picks, stats = [], set()
        for stat, goal, words, reward in rng.sample(MISSION_POOL, len(MISSION_POOL)):
            if stat not in stats:
                stats.add(stat)
                picks.append({"stat": stat, "goal": goal, "words": words, "reward": reward, "progress": 0,
                              "done": False})
            if len(picks) == MISSIONS_PER_DAY:
                break
        profile.missions = {"day": day, "list": picks, "all_done": False}
    return profile.missions["list"]


def _advance_missions(profile, key, amount):
    missions = today_missions(profile)
    for mission in missions:
        if mission["stat"] != key or mission["done"]:
            continue
        if key in MAX_STATS:
            mission["progress"] = max(mission["progress"], min(mission["goal"], amount))
        else:
            mission["progress"] = min(mission["goal"], mission["progress"] + amount)
        if mission["progress"] >= mission["goal"]:
            mission["done"] = True
            profile.yen += mission["reward"]
            profile.add_exp(MISSION_EXP)
            _event(profile, "mission", "MISSION COMPLETE!", f"{mission['words']}  +{mission['reward']}円")
    if missions and all(m["done"] for m in missions) and not profile.missions.get("all_done"):
        profile.missions["all_done"] = True
        profile.yen += ALL_MISSIONS_BONUS
        _event(profile, "mission", "ALL MISSIONS DONE!", f"Today's bonus  +{ALL_MISSIONS_BONUS}円")


# -- Daily login and streak --------------------------------------------------------

def daily_bonus_for(days):
    return DAILY_BONUS + DAILY_BONUS_STEP * min(days - 1, DAILY_BONUS_MAX_STEPS)


def daily_login(profile, today=None, seed=None):
    """The first visit of the day: continues (or restarts) the study streak
    and pays the login bonus. Returns {"days", "bonus", "best"} -- or None
    if today's bonus was already collected."""
    today = today or datetime.date.today()
    day = today_str(today)
    streak = profile.streak
    if streak.get("last") == day:
        return None
    yesterday = (today - datetime.timedelta(days=1)).isoformat()
    days = streak.get("days", 0) + 1 if streak.get("last") == yesterday else 1
    profile.streak = {"last": day, "days": days, "best": max(days, streak.get("best", 0))}
    bonus = daily_bonus_for(days)
    profile.yen += bonus
    profile.stats["days"] = profile.stats.get("days", 0) + 1
    today_missions(profile, today, seed)
    check_trophies(profile)
    return {"days": days, "bonus": bonus, "best": profile.streak["best"]}


# -- Leaderboard values --------------------------------------------------------------

BOARDS = [
    ("level", "ABILITY", "Lv / study EXP"),
    ("score", "BEST SCORE", "best score in one run"),
    ("correct", "RIGHT ANSWERS", "all-time right answers"),
    ("streak", "STUDY STREAK", "longest run of days"),
    ("trophies", "TROPHIES", "trophies earned"),
]


def board_entry(profile):
    """What this player puts on each leaderboard: {board: (sort value, label)}."""
    return {
        "level": (profile.exp, f"Lv {profile.level}"),
        "score": (profile.stats.get("best_score", 0), f"{profile.stats.get('best_score', 0):,}"),
        "correct": (profile.stats.get("correct", 0), f"{profile.stats.get('correct', 0):,}"),
        "streak": (profile.streak.get("best", 0), f"{profile.streak.get('best', 0)} days"),
        "trophies": (len(profile.trophies), f"{len(profile.trophies)}/{len(TROPHIES)}"),
    }

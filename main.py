import asyncio
import os

# Keep reading the gamepad even when the game window isn't the focused one
# (on macOS it can open behind the Terminal it was started from).
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

from kobito import audio, online, progress, save_game  # noqa: E402
from kobito.account_screen import choose_player  # noqa: E402
from kobito.adaptive import AdaptiveTutor  # noqa: E402
from kobito.difficulty import MODE_ADAPTIVE  # noqa: E402
from kobito.companion_select_screen import CompanionSelectScreen  # noqa: E402
from kobito.daily_screen import DailyBonusScreen  # noqa: E402
from kobito.difficulty_select_screen import DifficultySelectScreen  # noqa: E402
from kobito.game import Game, OUTCOME_ADVANCE  # noqa: E402
from kobito.select_screen import SelectScreen  # noqa: E402
from kobito.title_screen import RESULT_CONTINUE, RESULT_PLAYER, RESULT_TOWN, TitleScreen  # noqa: E402
from kobito.town_screen import TownScreen  # noqa: E402
from kobito.world_select_screen import WorldSelectScreen  # noqa: E402


async def new_run():
    character_id = await SelectScreen().run()
    companion_id = await CompanionSelectScreen().run()
    theme_id = await WorldSelectScreen().run()
    difficulty_mode, jlpt_level = await DifficultySelectScreen(companion_id).run()
    run = {
        "character_id": character_id, "companion_id": companion_id, "theme_id": theme_id,
        "jlpt_level": jlpt_level, "level_number": 1, "score": 0, "xp": 0, "item_box": {}, "badges": [],
        "question_history": [],
        "difficulty_mode": difficulty_mode, "tutor": None,
    }
    # First checkpoint straight away, so even a run quit in level 1 can be
    # continued from its start.
    save_game.save_run(run)
    return run


async def sign_in():
    """Who's playing (kobito/account_screen.py), then -- once a day -- the
    daily bonus. Returns (account or None for guest, their profile)."""
    account = await choose_player()
    save_game.apply_saved_settings()   # furigana / translation / sound for this player
    profile = save_game.load_profile()
    bonus = progress.daily_login(profile)
    save_game.save_profile(profile)
    if bonus:
        await DailyBonusScreen(profile, bonus, account["name"] if account else None).run()
    return account, profile


async def main():
    save_game.apply_saved_settings()   # sound settings for the first screens
    audio.music(audio.MENU_TRACK)

    # Who's playing, then their title screen. Ability level, 円, wardrobe and
    # trophies (the profile) are kept across runs and shared by every level
    # and the town (kobito/profile.py); each player has their own.
    while True:
        account, profile = await sign_in()
        saved = save_game.load_run()
        choice = None
        while saved:
            audio.music(audio.MENU_TRACK)
            choice = await TitleScreen(saved, profile, account["name"] if account else None).run()
            if choice != RESULT_TOWN:
                break
            await TownScreen(profile, saved["run"]["character_id"], leave_label="TITLE", leave_jp="もどる").run()
        if choice != RESULT_PLAYER:
            break
    if choice == RESULT_CONTINUE:
        run, resume_state = saved["run"], saved["level"]
    else:
        run, resume_state = await new_run(), None
    save_game.touch_account(character_id=run["character_id"])   # their portrait on the player cards
    online.submit(account, profile, run["character_id"])

    # Each Game instance is one level. Reaching the goal castle ends it
    # with OUTCOME_ADVANCE plus a JLPT level for the next one, picked
    # adaptively from how this level's questions went -- loop here to
    # keep playing levels until the player quits or runs out of lives.
    # The item box and badge list are shared by every level of the run;
    # Game autosaves at each stage clear (and on Save / window close).
    # After each clear the player walks through Kobito Town before the
    # next stage starts, and their scores go to the world leaderboard
    # (if a server is set up, see kobito/online.py).
    score, xp, jlpt_level, level_number = run["score"], run["xp"], run["jlpt_level"], run["level_number"]
    item_box, badges = run["item_box"], run["badges"]
    question_history = run["question_history"]   # so new levels favour questions not seen yet
    # In AI Adaptive mode one tutor follows the player through every level
    # (and into the save), so what it has learned about them carries over.
    tutor = None
    if run["difficulty_mode"] == MODE_ADAPTIVE:
        tutor = AdaptiveTutor.from_state(run["tutor"]) if run.get("tutor") else AdaptiveTutor(jlpt_level)
    while True:
        outcome, score, jlpt_level, xp = await Game(
            run["character_id"],
            run["theme_id"],
            companion_id=run["companion_id"],
            jlpt_level=jlpt_level,
            level_number=level_number,
            starting_score=score,
            starting_xp=xp,
            item_box=item_box,
            badges=badges,
            resume_state=resume_state,
            difficulty_mode=run["difficulty_mode"],
            tutor=tutor,
            question_history=question_history,
            profile=profile,
        ).run()
        resume_state = None
        online.submit(account, profile, run["character_id"])
        if outcome != OUTCOME_ADVANCE:
            break
        level_number += 1
        # Between stages: the town -- change costumes, shop at the konbini,
        # check missions, trophies and the leaderboard.
        await TownScreen(profile, run["character_id"]).run()


if __name__ == "__main__":
    # asyncio.run (rather than a plain call) is what lets every screen's
    # loop yield with `await asyncio.sleep(0)` each frame -- required for
    # the Pygbag/Emscripten web build, and a harmless indirection here on
    # desktop, where the two builds otherwise share this exact code path.
    asyncio.run(main())

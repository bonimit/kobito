import asyncio

from kobito.companion_select_screen import CompanionSelectScreen
from kobito.difficulty_select_screen import DifficultySelectScreen
from kobito.game import Game, OUTCOME_ADVANCE
from kobito.select_screen import SelectScreen
from kobito.world_select_screen import WorldSelectScreen


async def main():
    character_id = await SelectScreen().run()
    companion_id = await CompanionSelectScreen().run()
    theme_id = await WorldSelectScreen().run()
    jlpt_level = await DifficultySelectScreen(companion_id).run()

    # Each Game instance is one level. Reaching the goal castle ends it
    # with OUTCOME_ADVANCE plus a JLPT level for the next one, picked
    # adaptively from how this level's questions went -- loop here to
    # keep playing levels until the player quits or runs out of lives.
    score = 0
    xp = 0
    level_number = 1
    item_box = {}  # everything picked up this run, shared across levels
    while True:
        outcome, score, jlpt_level, xp = await Game(
            character_id,
            theme_id,
            companion_id=companion_id,
            jlpt_level=jlpt_level,
            level_number=level_number,
            starting_score=score,
            starting_xp=xp,
            item_box=item_box,
        ).run()
        if outcome != OUTCOME_ADVANCE:
            break
        level_number += 1


if __name__ == "__main__":
    # asyncio.run (rather than a plain call) is what lets every screen's
    # loop yield with `await asyncio.sleep(0)` each frame -- required for
    # the Pygbag/Emscripten web build, and a harmless indirection here on
    # desktop, where the two builds otherwise share this exact code path.
    asyncio.run(main())

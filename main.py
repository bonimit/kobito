from kobito.companion_select_screen import CompanionSelectScreen
from kobito.difficulty_select_screen import DifficultySelectScreen
from kobito.game import Game, OUTCOME_ADVANCE
from kobito.select_screen import SelectScreen
from kobito.world_select_screen import WorldSelectScreen

if __name__ == "__main__":
    character_id = SelectScreen().run()
    companion_id = CompanionSelectScreen().run()
    theme_id = WorldSelectScreen().run()
    jlpt_level = DifficultySelectScreen(companion_id).run()

    # Each Game instance is one level. Reaching the goal castle ends it
    # with OUTCOME_ADVANCE plus a JLPT level for the next one, picked
    # adaptively from how this level's questions went -- loop here to
    # keep playing levels until the player quits or runs out of lives.
    score = 0
    level_number = 1
    while True:
        outcome, score, jlpt_level = Game(
            character_id,
            theme_id,
            companion_id=companion_id,
            jlpt_level=jlpt_level,
            level_number=level_number,
            starting_score=score,
        ).run()
        if outcome != OUTCOME_ADVANCE:
            break
        level_number += 1

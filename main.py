from kobito.game import Game
from kobito.select_screen import SelectScreen
from kobito.world_select_screen import WorldSelectScreen

if __name__ == "__main__":
    character_id = SelectScreen().run()
    theme_id = WorldSelectScreen().run()
    Game(character_id, theme_id).run()

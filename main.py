from kobito.game import Game
from kobito.select_screen import SelectScreen

if __name__ == "__main__":
    character_id = SelectScreen().run()
    Game(character_id).run()

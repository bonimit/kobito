"""Paints the overworld map (kobito/world_map.py) and saves it to assets/map/.

    python tools/make_world_map.py

Run it again after changing the map's layout or art in kobito/world_map.py.
The game loads the baked picture (fast, which matters most in the browser)
and only paints the map itself if the files are missing.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((960, 540))

from kobito import world_map  # noqa: E402

world = world_map.Overworld(paint=True)
world.bake()
print(f"wrote {world_map.MAP_DIR / world_map.PICTURE} and {world_map.WALKABLE}")

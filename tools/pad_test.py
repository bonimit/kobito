"""Checks that a gamepad works with Kobito.

    python tools/pad_test.py

Lists the controllers your computer reports, with the button layout the
game will use for each, then shows every button / d-pad / stick press as
the game sees it ("A", "B", "Start", ...) until you close the window or
press Ctrl+C. Keep the little window focused -- or don't: background
input is allowed here, just like in the game.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

import pygame  # noqa: E402

from kobito import input as game_input  # noqa: E402

NAMES = {game_input.A: "A", game_input.B: "B", game_input.X: "X", game_input.Y: "Y", game_input.LB: "LB",
         game_input.RB: "RB", game_input.BACK: "Back", game_input.START: "Start", game_input.UNMAPPED: "(unused)"}


def main():
    pygame.init()
    screen = pygame.display.set_mode((560, 220))
    pygame.display.set_caption("Kobito - gamepad test")
    font = pygame.font.Font(None, 28)
    pads = game_input.get_joysticks()
    print(f"pygame {pygame.version.ver}, SDL {'.'.join(map(str, pygame.get_sdl_version()))}", flush=True)
    if not pads:
        print("No controller found yet. Plug one in now (on a Mac, set a Logitech F310's switch to D).", flush=True)
    for pad in pads:
        print(f"Found: {pad.get_name()!r}  -> layout {game_input.layout_for(pad)!r}  "
              f"({pad.get_numbuttons()} buttons, {pad.get_numhats()} d-pad, {pad.get_numaxes()} axes)")
    print("Press buttons on the controller (close the window or Ctrl+C to stop).", flush=True)
    lines = ["Press buttons on the controller..."]
    clock = pygame.time.Clock()
    try:
        while True:
            for event in game_input.events():
                text = None
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.JOYDEVICEADDED:
                    game_input.handle_hotplug(event)
                    pad = game_input.get_joysticks()[-1]
                    text = f"Connected: {pad.get_name()} ({game_input.layout_for(pad)})"
                elif event.type == pygame.JOYDEVICEREMOVED:
                    text = "Controller unplugged"
                elif event.type == pygame.JOYBUTTONDOWN:
                    text = f"Button: {NAMES.get(event.button, event.button)}"
                elif event.type == pygame.JOYHATMOTION and event.value != (0, 0):
                    text = f"D-pad: {event.value}"
                elif event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.6 and event.axis < 2:
                    text = f"Stick {'x' if event.axis == 0 else 'y'}: {event.value:+.1f}"
                if text:
                    print(text, flush=True)
                    lines = (lines + [text])[-6:]
            screen.fill((20, 16, 36))
            for i, line in enumerate(lines):
                screen.blit(font.render(line, True, (255, 240, 210)), (16, 14 + i * 32))
            pygame.display.flip()
            clock.tick(30)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

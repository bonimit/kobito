"""Joystick/gamepad support, layered on top of (never replacing)
keyboard input everywhere in the game.

Uses raw pygame.joystick button/axis indices rather than SDL's
GameController abstraction, so button numbers follow the common
convention most USB/Xbox-style/generic pads share under SDL's default
mapping: 0/1/2/3 = the four face buttons (A/B/X/Y on an Xbox-style
pad), the left stick is axes 0 (x) and 1 (y), and the d-pad is a hat.
Layouts can vary by controller, but this covers the common case without
needing a full SDL_GameController mapping database.
"""

import pygame

AXIS_DEADZONE = 0.5
LEFT_STICK_X_AXIS = 0

# Face buttons, in the A/B/X/Y position most controllers agree on.
FACE_BUTTONS = (0, 1, 2, 3)
CONFIRM_BUTTONS = (0,)  # A
CANCEL_BUTTONS = (1,)  # B
JUMP_BUTTONS = (0,)  # A

_joysticks = None


def get_joysticks():
    """Returns the list of currently-open joysticks, opening any that
    are connected the first time this is called. Cheap to call
    repeatedly (every screen/Game does, once, in __init__) -- later
    calls just return the cached list.
    """
    global _joysticks
    if _joysticks is None:
        pygame.joystick.init()
        _joysticks = []
        for i in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            _joysticks.append(joystick)
    return _joysticks


def handle_hotplug(event):
    """Call for every pygame event (alongside normal handling) so a
    controller plugged in mid-session becomes usable immediately,
    without needing to restart the game.
    """
    if event.type == pygame.JOYDEVICEADDED:
        joystick = pygame.joystick.Joystick(event.device_index)
        joystick.init()
        get_joysticks().append(joystick)


def move_axis():
    """Returns -1.0..1.0 horizontal movement from the first connected
    joystick's d-pad or left stick (whichever is furthest from
    center), or 0.0 if none is connected/active. Meant to be combined
    with keyboard input, not replace it -- see Player.handle_input.
    """
    for joystick in get_joysticks():
        if joystick.get_numhats() > 0:
            hat_x, _ = joystick.get_hat(0)
            if hat_x != 0:
                return float(hat_x)
        if joystick.get_numaxes() > LEFT_STICK_X_AXIS:
            value = joystick.get_axis(LEFT_STICK_X_AXIS)
            if abs(value) >= AXIS_DEADZONE:
                return value
    return 0.0


def jump_held():
    return any(
        joystick.get_numbuttons() > button and joystick.get_button(button)
        for joystick in get_joysticks()
        for button in JUMP_BUTTONS
    )


class MenuNav:
    """Turns a joystick's d-pad/left stick and face buttons into
    discrete "just pressed" menu actions ("left", "right", "confirm",
    "cancel"), for select screens that otherwise only react to
    discrete KEYDOWN events. Call handle_event(event) for every pygame
    event inside a screen's normal event loop.
    """

    def __init__(self, deadzone=AXIS_DEADZONE):
        self.deadzone = deadzone
        self._axis_neutral = True

    def handle_event(self, event):
        if event.type == pygame.JOYHATMOTION:
            hat_x, _ = event.value
            if hat_x < 0:
                return "left"
            if hat_x > 0:
                return "right"
            return None

        if event.type == pygame.JOYAXISMOTION and event.axis == LEFT_STICK_X_AXIS:
            # Edge-detected like a button: only fires once per push past
            # the deadzone, resetting when the stick returns to center,
            # so holding the stick over doesn't repeat every frame.
            if event.value <= -self.deadzone:
                if self._axis_neutral:
                    self._axis_neutral = False
                    return "left"
            elif event.value >= self.deadzone:
                if self._axis_neutral:
                    self._axis_neutral = False
                    return "right"
            else:
                self._axis_neutral = True
            return None

        if event.type == pygame.JOYBUTTONDOWN:
            if event.button in CONFIRM_BUTTONS:
                return "confirm"
            if event.button in CANCEL_BUTTONS:
                return "cancel"

        return None

    def answer_index(self, event):
        """For quiz screens: maps a face-button press to a 0-3 answer
        choice (A/B/X/Y -> choices 1-4), or None for any other event.
        """
        if event.type == pygame.JOYBUTTONDOWN and event.button in FACE_BUTTONS:
            return FACE_BUTTONS.index(event.button)
        return None

"""Joystick/gamepad support, layered on top of (never replacing)
keyboard input everywhere in the game.

Uses raw pygame.joystick buttons/axes rather than SDL's GameController
API, and translates each controller's own button numbering into one
logical layout -- the XInput / Xbox one: A=0, B=1, X=2, Y=3, LB=4, RB=5,
Back=6, Start=7, left stick = axes 0 (x) and 1 (y), d-pad = hat 0. Every
check in the game uses those numbers; read events through events() (not
pygame.event.get()) and they arrive already translated.

Layouts recognised (see layout_for):
  * "xinput"   -- Xbox-style pads, and the Logitech F310 / F510 / F710
                  with the switch on the back set to X (the default).
  * "logitech_d" -- the same Logitech pads with the switch on D
                  (DirectInput; they report as "Logitech Dual Action" /
                  "RumblePad 2"): X=0, A=1, B=2, Y=3, LB=4, RB=5, LT=6,
                  RT=7, Back=8, Start=9.
  * "standard" -- the browser's Gamepad API (the web build): A=0 ... RB=5,
                  LT=6, RT=7, Back=8, Start=9, and the d-pad as buttons
                  12-15 instead of a hat, turned into hat events here.
"""

import pygame

from kobito.constants import IS_WEB

AXIS_DEADZONE = 0.5
LEFT_STICK_X_AXIS = 0

# Logical buttons (XInput numbering).
A, B, X, Y, LB, RB, BACK, START = range(8)
UNMAPPED = 99      # a button the game doesn't use (triggers, stick clicks, ...)

# Face buttons, in the A/B/X/Y position most controllers agree on.
FACE_BUTTONS = (A, B, X, Y)
CONFIRM_BUTTONS = (A,)
CANCEL_BUTTONS = (B,)
JUMP_BUTTONS = (A,)
RUN_BUTTONS = (B, X)  # hold to run; press to throw a sunball with sun power
SKIP_BUTTONS = (LB, RB, START)  # skip a quiz question (face buttons are the answers)

# Raw button index -> logical button, per layout.
LAYOUTS = {
    "xinput": {0: A, 1: B, 2: X, 3: Y, 4: LB, 5: RB, 6: BACK, 7: START},
    "logitech_d": {0: X, 1: A, 2: B, 3: Y, 4: LB, 5: RB, 8: BACK, 9: START},
    "standard": {0: A, 1: B, 2: X, 3: Y, 4: LB, 5: RB, 8: BACK, 9: START},
}
# The standard mapping's d-pad buttons, as hat directions.
STANDARD_DPAD = {12: (0, 1), 13: (0, -1), 14: (-1, 0), 15: (1, 0)}
# Logitech product ids of pads in D (DirectInput) mode: F310, F510, F710.
LOGITECH_VENDOR = "046d"
LOGITECH_D_PRODUCTS = {"c216", "c218", "c219"}

_joysticks = None
_layouts = {}       # joystick instance id -> layout name
_dpad = {}          # joystick instance id -> d-pad buttons held (standard layout)


def layout_for(joystick):
    """Which button layout a joystick uses -- see the module docstring."""
    if IS_WEB:
        return "standard"
    name = joystick.get_name().lower()
    guid = joystick.get_guid() if hasattr(joystick, "get_guid") else ""
    return _layout_from(name, guid)


def _layout_from(name, guid):
    # SDL GUIDs carry the USB vendor and product ids little-endian:
    # 03000000 6d04 0000 16c2 0000 ... -> vendor 046d, product c216.
    vendor = product = ""
    if len(guid) >= 20:
        vendor = guid[10:12] + guid[8:10]
        product = guid[18:20] + guid[16:18]
    if "dual action" in name or "rumblepad" in name or (
            vendor == LOGITECH_VENDOR and product in LOGITECH_D_PRODUCTS):
        return "logitech_d"
    return "xinput"


def _register(joystick):
    _layouts[joystick.get_instance_id()] = layout_for(joystick)


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
            _register(joystick)
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
        if joystick.get_instance_id() not in _layouts:
            _register(joystick)
            get_joysticks().append(joystick)


def events():
    """pygame.event.get(), with joystick buttons translated to the logical
    layout (and the web d-pad's buttons turned into hat motion)."""
    out = []
    for event in pygame.event.get():
        out.extend(translate(event))
    return out


def translate(event):
    """One raw event -> the events the game should see (a list)."""
    if event.type not in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
        return [event]
    joy = getattr(event, "instance_id", getattr(event, "joy", 0))
    layout = _layouts.get(joy, "standard" if IS_WEB else "xinput")
    if layout == "standard" and event.button in STANDARD_DPAD:
        held = _dpad.setdefault(joy, set())
        (held.add if event.type == pygame.JOYBUTTONDOWN else held.discard)(event.button)
        return [pygame.event.Event(pygame.JOYHATMOTION, joy=joy, instance_id=joy, hat=0,
                                   value=_dpad_value(held))]
    button = LAYOUTS[layout].get(event.button, UNMAPPED)
    return [pygame.event.Event(event.type, joy=joy, instance_id=joy, button=button)]


def _dpad_value(held):
    x = sum(STANDARD_DPAD[b][0] for b in held)
    y = sum(STANDARD_DPAD[b][1] for b in held)
    return (max(-1, min(1, x)), max(-1, min(1, y)))


def button_down(joystick, logical):
    """Is this logical button (A, B, ...) held on this joystick?"""
    layout = _layouts.get(joystick.get_instance_id(), "xinput")
    return any(joystick.get_button(raw) for raw, button in LAYOUTS[layout].items()
               if button == logical and raw < joystick.get_numbuttons())


def _hat_x(joystick):
    layout = _layouts.get(joystick.get_instance_id(), "xinput")
    if layout == "standard":
        n = joystick.get_numbuttons()
        left = n > 14 and joystick.get_button(14)
        right = n > 15 and joystick.get_button(15)
        return (1 if right else 0) - (1 if left else 0)
    if joystick.get_numhats() > 0:
        return joystick.get_hat(0)[0]
    return 0


def move_axis():
    """Returns -1.0..1.0 horizontal movement from the first connected
    joystick's d-pad or left stick (whichever is furthest from
    center), or 0.0 if none is connected/active. Meant to be combined
    with keyboard input, not replace it -- see Player.handle_input.
    """
    for joystick in get_joysticks():
        hat_x = _hat_x(joystick)
        if hat_x != 0:
            return float(hat_x)
        if joystick.get_numaxes() > LEFT_STICK_X_AXIS:
            value = joystick.get_axis(LEFT_STICK_X_AXIS)
            if abs(value) >= AXIS_DEADZONE:
                return value
    return 0.0


def jump_held():
    return any(button_down(joystick, button) for joystick in get_joysticks() for button in JUMP_BUTTONS)


def run_held():
    return bool(run_buttons_down())


def run_buttons_down():
    """Which run/throw gamepad buttons are down, e.g. {(0, 1)} -- so each
    button can be its own fresh press (hold B to run, tap X to throw)."""
    return {
        (i, button)
        for i, joystick in enumerate(get_joysticks())
        for button in RUN_BUTTONS
        if button_down(joystick, button)
    }


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


# --- On-screen touch controls -------------------------------------------
# Only meaningful in the Pygbag/Emscripten (browser) build -- IS_WEB is
# False in the desktop build, so nothing here is drawn or read there. A
# phone has no keyboard or joystick, so this is the only way to move/jump
# or navigate menus on one; it's layered on top of keyboard/joystick
# input exactly like the joystick support above is layered on keyboard.

TOUCH_BUTTON_RADIUS = 34
TOUCH_BUTTON_MARGIN = 26
TOUCH_BUTTON_GAP = 16
TOUCH_BUTTON_COLOR = (255, 255, 255, 80)
TOUCH_BUTTON_COLOR_ACTIVE = (255, 220, 120, 150)
TOUCH_BUTTON_BORDER = (255, 255, 255, 160)
TOUCH_LABEL_COLOR = (60, 50, 40)


def touch_tap_pos(event):
    """A touch/mouse-down event's position in screen pixels, or None for
    any other event. FINGERDOWN reports normalized 0..1 coordinates;
    MOUSEBUTTONDOWN (mouse, or touch translated to a mouse click by the
    browser) already reports pixels. Exposed for screens (like
    QuizScreen) that hit-test a tap against their own on-screen text
    rather than a fixed button, unlike GameplayTouchControls/
    MenuTouchControls below.
    """
    if event.type == pygame.FINGERDOWN:
        surface = pygame.display.get_surface()
        return event.x * surface.get_width(), event.y * surface.get_height()
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return event.pos
    return None


def _touch_event_up_id(event):
    """A released touch/mouse's id, matching what touch_tap_pos's
    caller stored it under, or None for any other event.
    """
    if event.type == pygame.FINGERUP:
        return event.finger_id
    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        return "mouse"
    return None


class GameplayTouchControls:
    """A left/right pair (bottom-left) and a jump button (bottom-right),
    tracked by touch/mouse id so holding movement while tapping jump
    works the way two separate fingers on a real d-pad + button would.
    """

    def __init__(self, screen_width, screen_height):
        cy = screen_height - TOUCH_BUTTON_MARGIN - TOUCH_BUTTON_RADIUS
        left_x = TOUCH_BUTTON_MARGIN + TOUCH_BUTTON_RADIUS
        self.buttons = {
            "left": (left_x, cy),
            "right": (left_x + TOUCH_BUTTON_RADIUS * 2 + TOUCH_BUTTON_GAP, cy),
            "jump": (screen_width - TOUCH_BUTTON_MARGIN - TOUCH_BUTTON_RADIUS, cy),
            # Run (hold) / throw a sunball (tap, with sun power), left of jump.
            "run": (screen_width - TOUCH_BUTTON_MARGIN - TOUCH_BUTTON_RADIUS * 3 - TOUCH_BUTTON_GAP, cy),
        }
        self._held = {}  # touch/mouse id -> button name

    def _button_at(self, pos):
        for name, center in self.buttons.items():
            dx, dy = pos[0] - center[0], pos[1] - center[1]
            if dx * dx + dy * dy <= TOUCH_BUTTON_RADIUS * TOUCH_BUTTON_RADIUS:
                return name
        return None

    def handle_event(self, event):
        """Feed every pygame event here, same as handle_hotplug. Returns
        True the instant jump is first pressed (edge-triggered, like a
        KEYDOWN), so Player only jumps once per tap even while held.
        """
        pos = touch_tap_pos(event)
        if pos is not None:
            button = self._button_at(pos)
            if button:
                touch_id = event.finger_id if event.type == pygame.FINGERDOWN else "mouse"
                self._held[touch_id] = button
                return button == "jump"
            return False

        up_id = _touch_event_up_id(event)
        if up_id is not None:
            self._held.pop(up_id, None)
        return False

    def move_axis(self):
        held = self._held.values()
        left, right = "left" in held, "right" in held
        if left and not right:
            return -1.0
        if right and not left:
            return 1.0
        return 0.0

    def jump_held(self):
        return "jump" in self._held.values()

    def run_held(self):
        return "run" in self._held.values()

    def draw(self, screen):
        self._draw_button(screen, "left", "<")
        self._draw_button(screen, "right", ">")
        self._draw_button(screen, "jump", "^")
        self._draw_button(screen, "run", "B")

    def _draw_button(self, screen, name, label):
        center = self.buttons[name]
        active = name in self._held.values()
        overlay = pygame.Surface((TOUCH_BUTTON_RADIUS * 2, TOUCH_BUTTON_RADIUS * 2), pygame.SRCALPHA)
        color = TOUCH_BUTTON_COLOR_ACTIVE if active else TOUCH_BUTTON_COLOR
        pygame.draw.circle(overlay, color, (TOUCH_BUTTON_RADIUS, TOUCH_BUTTON_RADIUS), TOUCH_BUTTON_RADIUS)
        pygame.draw.circle(overlay, TOUCH_BUTTON_BORDER, (TOUCH_BUTTON_RADIUS, TOUCH_BUTTON_RADIUS), TOUCH_BUTTON_RADIUS, width=2)
        screen.blit(overlay, (center[0] - TOUCH_BUTTON_RADIUS, center[1] - TOUCH_BUTTON_RADIUS))

        from kobito.fonts import get_font  # local import: avoids a load-time cycle with kobito.input
        font = get_font(28)
        text = font.render(label, True, TOUCH_LABEL_COLOR)
        screen.blit(text, text.get_rect(center=center))


class MenuTouchControls:
    """Prev/next arrows plus a confirm button, emitting the same
    discrete action strings as MenuNav ("left"/"right"/"confirm") so
    select screens can treat a tap exactly like a joystick press.
    """

    def __init__(self, screen_width, screen_height):
        cy = screen_height - TOUCH_BUTTON_MARGIN - TOUCH_BUTTON_RADIUS
        left_x = TOUCH_BUTTON_MARGIN + TOUCH_BUTTON_RADIUS
        self.buttons = {
            "left": (left_x, cy),
            "right": (left_x + TOUCH_BUTTON_RADIUS * 2 + TOUCH_BUTTON_GAP, cy),
            "confirm": (screen_width - TOUCH_BUTTON_MARGIN - TOUCH_BUTTON_RADIUS, cy),
        }
        self._labels = {"left": "<", "right": ">", "confirm": "OK"}

    def _button_at(self, pos):
        for name, center in self.buttons.items():
            dx, dy = pos[0] - center[0], pos[1] - center[1]
            if dx * dx + dy * dy <= TOUCH_BUTTON_RADIUS * TOUCH_BUTTON_RADIUS:
                return name
        return None

    def handle_event(self, event):
        pos = touch_tap_pos(event)
        if pos is None:
            return None
        return self._button_at(pos)

    def draw(self, screen):
        from kobito.fonts import get_font  # local import: avoids a load-time cycle with kobito.input
        font = get_font(22)
        for name, center in self.buttons.items():
            overlay = pygame.Surface((TOUCH_BUTTON_RADIUS * 2, TOUCH_BUTTON_RADIUS * 2), pygame.SRCALPHA)
            pygame.draw.circle(overlay, TOUCH_BUTTON_COLOR, (TOUCH_BUTTON_RADIUS, TOUCH_BUTTON_RADIUS), TOUCH_BUTTON_RADIUS)
            pygame.draw.circle(overlay, TOUCH_BUTTON_BORDER, (TOUCH_BUTTON_RADIUS, TOUCH_BUTTON_RADIUS), TOUCH_BUTTON_RADIUS, width=2)
            screen.blit(overlay, (center[0] - TOUCH_BUTTON_RADIUS, center[1] - TOUCH_BUTTON_RADIUS))
            text = font.render(self._labels[name], True, TOUCH_LABEL_COLOR)
            screen.blit(text, text.get_rect(center=center))


_gameplay_touch = None
_menu_touch = None


def get_gameplay_touch_controls(screen):
    """Lazily creates the singleton GameplayTouchControls sized to
    `screen`, or returns None outside the web build -- callers can use
    the result unconditionally (`if controls:`) without checking IS_WEB
    themselves.
    """
    global _gameplay_touch
    if not IS_WEB:
        return None
    if _gameplay_touch is None:
        _gameplay_touch = GameplayTouchControls(screen.get_width(), screen.get_height())
    return _gameplay_touch


def get_menu_touch_controls(screen):
    global _menu_touch
    if not IS_WEB:
        return None
    if _menu_touch is None:
        _menu_touch = MenuTouchControls(screen.get_width(), screen.get_height())
    return _menu_touch


def touch_move_axis():
    return _gameplay_touch.move_axis() if _gameplay_touch else 0.0


def touch_jump_held():
    return _gameplay_touch.jump_held() if _gameplay_touch else False


def touch_run_held():
    return _gameplay_touch.run_held() if _gameplay_touch else False

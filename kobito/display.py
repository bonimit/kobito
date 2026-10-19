"""The game window.

Everything is drawn on a 960 x 540 canvas (SCREEN_WIDTH x SCREEN_HEIGHT).
On desktop the window shows that canvas scaled up -- pygame's SCALED mode,
so pixels stay crisp and mouse / touch positions still come in canvas
coordinates -- and opens at about 85% of the screen. It can be resized by
dragging its edge (the picture keeps its shape, with bars if needed), and
F11 (or Alt+Enter, or Settings -> Full screen) switches to full screen;
that choice is remembered (kobito/save_game.py).

Every screen gets the window from screen(), which makes it only once:
recreating a scaled window would flicker, and some systems refuse to.
In the web build the browser page does the scaling, so it's a plain canvas.
"""

import pygame

from kobito.constants import IS_WEB, SCREEN_HEIGHT, SCREEN_WIDTH

WINDOW_FILL = 0.85     # how much of the desktop the window opens at
SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

_state = {"window": None, "fullscreen": False, "want_fullscreen": False}


def screen():
    """The canvas to draw on (the window is made the first time)."""
    surface = pygame.display.get_surface()
    if surface is not None and surface is _state["window"]:
        return surface
    if surface is not None and surface.get_size() == SIZE:
        return surface        # a window someone else already made (tests, tools)
    pygame.display.init()
    if IS_WEB:
        surface = pygame.display.set_mode(SIZE)
    else:
        try:
            surface = pygame.display.set_mode(SIZE, pygame.SCALED | pygame.RESIZABLE)
            _grow_window()
        except pygame.error:
            surface = pygame.display.set_mode(SIZE)
    _state["window"] = surface
    _state["fullscreen"] = False
    if _state["want_fullscreen"]:
        set_fullscreen(True)
    return surface


def _grow_window():
    """Opens the scaled window big: as large as fits in WINDOW_FILL of the
    desktop, keeping the 16:9 shape, centred -- a whole-number scale (2x,
    3x) when one fits, so every pixel is the same size."""
    try:
        from pygame._sdl2.video import Window
        desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
        scale = min(desktop_w * WINDOW_FILL / SIZE[0], desktop_h * WINDOW_FILL / SIZE[1])
        if scale <= 1:
            return
        if scale >= 2:
            scale = int(scale)
        window = Window.from_display_module()
        window.size = (round(SIZE[0] * scale), round(SIZE[1] * scale))
        window.position = ((desktop_w - window.size[0]) // 2, (desktop_h - window.size[1]) // 2)
    except Exception:
        pass   # an older pygame / unusual display: the normal-size window is fine


def is_fullscreen():
    return _state["fullscreen"] if _state["window"] is not None else _state["want_fullscreen"]


def set_fullscreen(on):
    _state["want_fullscreen"] = bool(on)
    if IS_WEB or _state["window"] is None or _state["fullscreen"] == bool(on):
        return
    try:
        if pygame.display.toggle_fullscreen():
            _state["fullscreen"] = bool(on)
    except pygame.error:
        pass


def toggle_fullscreen():
    set_fullscreen(not is_fullscreen())


def is_fullscreen_key(event):
    """F11, or Alt+Enter."""
    if event.type != pygame.KEYDOWN:
        return False
    return event.key == pygame.K_F11 or (event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
                                         and getattr(event, "mod", 0) & pygame.KMOD_ALT)

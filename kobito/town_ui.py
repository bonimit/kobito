"""Shared pieces for the town screens (kobito/town_screen.py, the house and
the konbini): grid navigation from any input, the Lv / 円 wallet chip,
and the dressed-up mascot."""

import math

import pygame

from kobito import gear_art, ui
from kobito import input as game_input
from kobito.assets import load_character_animations
from kobito.characters import get_character

STICK_X, STICK_Y = 0, 1
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_BACKSPACE)
KEY_ACTIONS = {pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right", pygame.K_d: "right",
               pygame.K_UP: "up", pygame.K_w: "up", pygame.K_DOWN: "down", pygame.K_s: "down"}


class Nav:
    """Any event -> "left" / "right" / "up" / "down" / "confirm" / "back"
    (or None). A held stick counts once until it comes back to centre."""

    def __init__(self):
        self._stick = {STICK_X: 0, STICK_Y: 0}

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in CONFIRM_KEYS:
                return "confirm"
            if event.key in BACK_KEYS:
                return "back"
            return KEY_ACTIONS.get(event.key)
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button in game_input.CONFIRM_BUTTONS:
                return "confirm"
            if event.button in game_input.CANCEL_BUTTONS + (game_input.BACK, game_input.START):
                return "back"
        if event.type == pygame.JOYHATMOTION:
            x, y = event.value
            if x:
                return "left" if x < 0 else "right"
            if y:
                return "up" if y > 0 else "down"
        if event.type == pygame.JOYAXISMOTION and event.axis in self._stick:
            direction = 0 if abs(event.value) < game_input.AXIS_DEADZONE else (1 if event.value > 0 else -1)
            fresh = direction and direction != self._stick[event.axis]
            self._stick[event.axis] = direction
            if fresh:
                if event.axis == STICK_X:
                    return "left" if direction < 0 else "right"
                return "up" if direction < 0 else "down"
        return None


def wallet(screen, profile, topright):
    """The Lv badge, a bar to the next level, and the 円 -- top right."""
    label = ui.label_font(16)
    yen = f"{profile.yen:,}円"
    # The chip grows to the left for a big purse (and the number shrinks past that), so the amount
    # never runs into the EXP bar or the button beside it.
    yen_font = ui.fit(yen, ui.body_font, 124, (19, 17, 15, 13, 11))
    rect = pygame.Rect(0, 0, max(300, 204 + yen_font.size(yen)[0] + 12), 44)
    rect.topright = topright
    ui.panel(screen, rect, bg=(20, 16, 36, 230), radius=12)
    lv = pygame.Rect(rect.x + 8, rect.y + 7, 64, 30)
    pygame.draw.rect(screen, ui.GOLD, lv, border_radius=8)
    ui.text(screen, f"Lv {profile.level}", label, lv.center, color=ui.OUTLINE, outline=None, anchor="center")
    into, needed = profile.level_progress()
    ui.bar(screen, (lv.right + 10, rect.y + 27, 110, 7), into / needed, (255, 196, 110), radius=3)
    ui.text(screen, "STUDY EXP", label, (lv.right + 10, rect.y + 6), color=ui.MUTED, thickness=1)
    ui.text(screen, yen, yen_font, (rect.right - 12, rect.centery), anchor="midright", thickness=2)
    return rect


class Mascot:
    """The player's mascot wearing its gear, big, with idle / run frames."""

    def __init__(self, character_id):
        self.character = get_character(character_id)
        self.animations = load_character_animations(character_id, self.character["color"])
        self.t = 0.0

    def update(self, dt, moving=False):
        self.t += dt
        self.animations["run" if moving else "idle"].update(dt)

    def frame(self, worn, scale=2, moving=False, facing_right=True):
        frame = self.animations["run" if moving else "idle"].current_frame
        dressed = gear_art.dress(frame, self.character["id"], worn, t=self.t, moving=moving)
        big = pygame.transform.scale(dressed, (dressed.get_width() * scale, dressed.get_height() * scale))
        return big if facing_right else pygame.transform.flip(big, True, False)


def bob(t, speed=4.0, height=3):
    return round(height * math.sin(t * speed))


def toast(screen, message, color, center):
    font = ui.label_font(16)
    rect = pygame.Rect(0, 0, font.size(message)[0] + 36, 32)
    rect.center = center
    ui.panel(screen, rect, bg=(20, 16, 36, 240), edge=(*color, 220), radius=16)
    ui.text(screen, message, font, rect.center, color=color, anchor="center", thickness=1)

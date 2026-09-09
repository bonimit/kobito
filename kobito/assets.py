from pathlib import Path

import pygame

from kobito.animation import Animation

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"

ANIMATION_NAMES = ("idle", "run", "jump")
FRAME_DURATIONS = {"idle": 0.5, "run": 0.12, "jump": 0.2}


def _scale_to_height(surface, height):
    width, current_height = surface.get_size()
    scale = height / current_height
    return pygame.transform.smoothscale(surface, (max(1, round(width * scale)), height))


def _load_frames_from_folder(folder, height):
    """Loads every PNG in a folder as one animation, in filename order.

    This is the hook for real art: drop frames named so they sort
    correctly (00.png, 01.png, 02.png, ...) into
    assets/sprites/<character_id>/<idle|run|jump>/, and they replace
    the placeholder automatically — nothing else in the code changes.
    """
    frames = []
    if folder.is_dir():
        for path in sorted(folder.glob("*.png")):
            image = pygame.image.load(str(path)).convert_alpha()
            frames.append(_scale_to_height(image, height))
    return frames


def _placeholder_frames(anim_name, color, width, height):
    if anim_name == "run":
        # Two flat-color frames of slightly different height so running
        # is visibly distinct from standing still, even before real
        # art exists.
        frame_a = pygame.Surface((width, height), pygame.SRCALPHA)
        frame_a.fill(color)
        frame_b = pygame.Surface((width, height - 4), pygame.SRCALPHA)
        frame_b.fill(color)
        return [frame_a, frame_b]

    if anim_name == "jump":
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        frame.fill(tuple(min(255, channel + 40) for channel in color))
        return [frame]

    # idle
    frame = pygame.Surface((width, height), pygame.SRCALPHA)
    frame.fill(color)
    return [frame]


def load_character_animations(character_id, color, width=28, height=48):
    """Builds {animation_name: Animation} for one character.

    Falls back to a flat-color placeholder per animation whenever real
    frames aren't present yet, so every character is playable/selectable
    from day one regardless of how much art exists.
    """
    base = SPRITES_DIR / character_id
    animations = {}
    for anim_name in ANIMATION_NAMES:
        frames = _load_frames_from_folder(base / anim_name, height)
        if not frames:
            frames = _placeholder_frames(anim_name, color, width, height)
        animations[anim_name] = Animation(frames, FRAME_DURATIONS[anim_name])
    return animations

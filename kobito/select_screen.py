import asyncio
import math

import pygame

from kobito import input as game_input
from kobito import setup_ui, ui
from kobito.assets import load_character_animations
from kobito.characters import CHARACTERS
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.item_art import get_icon
from kobito.items import get_item

HOP_PERIOD = 3.2       # seconds between the mascot's little hops on the stage
HOP_TIME = 0.55
HOP_HEIGHT = 46
CONFIRM_SECONDS = 0.45  # the pick's celebration before moving on


class SelectScreen:
    """Step 1 of a new game: pick a mascot.

    The highlighted mascot stands big on a lit stage (idle, with a hop
    every few seconds and whenever you switch to it), next to a card
    with its name, a line about it and its two favourite snacks -- the
    items that earn bonus points when found in a level. All seven sit
    in a roster strip along the bottom: arrows / A,D / d-pad / stick
    move through them, a click or tap on a card picks it (tap it again,
    or the CHOOSE button, to confirm), Enter / Space / A confirms.

    run() returns the chosen character's id.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Kobito - Choose your mascot")
        self.clock = pygame.time.Clock()
        self.index = 0
        self.time = 0.0
        self.hop = 0.0            # seconds into the current hop (>= HOP_TIME: standing)
        self.confirming = None    # seconds into the confirm celebration
        self.backdrop = setup_ui.backdrop()
        game_input.get_joysticks()
        self.joy_nav = game_input.MenuNav()
        self._arrows = {}
        self._cards = []
        self._confirm = setup_ui.CONFIRM

        # Every mascot's animations, big for the stage and small for the
        # roster, loaded up front so switching never stutters.
        self.big = {c["id"]: load_character_animations(c["id"], c["color"], width=100, height=150)
                    for c in CHARACTERS}
        self.small = {c["id"]: load_character_animations(c["id"], c["color"], width=30, height=46)["idle"]
                      for c in CHARACTERS}

    async def run(self):
        """Blocks until the player confirms a mascot, then returns its id."""
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in pygame.event.get():
                self._handle(event)
            if self.confirming is not None:
                self.confirming += dt
                if self.confirming >= CONFIRM_SECONDS:
                    return CHARACTERS[self.index]["id"]
            self._update(dt)
            self._draw()
            await asyncio.sleep(0)  # yields to the browser event loop; a no-op on desktop

    # -- Input -------------------------------------------------------------------

    def _select(self, index):
        index %= len(CHARACTERS)
        if index != self.index:
            self.index = index
            self.hop = 0.0        # say hello with a hop

    def _confirm_pick(self):
        if self.confirming is None:
            self.confirming = 0.0
            self.hop = 0.0

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        if self.confirming is not None:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                self._select(self.index - 1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                self._select(self.index + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._confirm_pick()
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit

        action = self.joy_nav.handle_event(event)
        if action in ("left", "right"):
            self._select(self.index + (1 if action == "right" else -1))
        elif action == "confirm":
            self._confirm_pick()
        elif action == "cancel":
            pygame.quit()
            raise SystemExit

        pos = game_input.touch_tap_pos(event)
        if pos is not None:
            for direction, rect in self._arrows.items():
                if rect.collidepoint(pos):
                    self._select(self.index + direction)
                    return
            for i, rect in enumerate(self._cards):
                if rect.collidepoint(pos):
                    if i == self.index:
                        self._confirm_pick()
                    else:
                        self._select(i)
                    return
            if self._confirm.collidepoint(pos):
                self._confirm_pick()

    # -- Drawing -----------------------------------------------------------------

    def _update(self, dt):
        self.backdrop.update(dt)
        anims = self.big[CHARACTERS[self.index]["id"]]
        anims["idle"].update(dt)
        anims["jump"].update(dt)
        for anim in self.small.values():
            anim.update(dt)
        self.hop += dt
        if self.hop > HOP_PERIOD:
            self.hop = 0.0

    def _draw(self):
        screen = self.screen
        self.backdrop.draw(screen)
        setup_ui.draw_steps(screen, 0)
        setup_ui.draw_title(screen, "CHOOSE YOUR HERO", "キャラクターを えらぼう")
        character = CHARACTERS[self.index]
        self._draw_stage(character)
        self._draw_card(character)
        self._cards = setup_ui.roster(screen, len(CHARACTERS), self.index, 82, self._draw_roster_item, self.time)
        flash = max(0.0, 1 - self.confirming / CONFIRM_SECONDS) if self.confirming is not None else 0.0
        self._confirm = setup_ui.confirm_button(screen, "CHOOSE", self.time, flash)
        setup_ui.hints(screen, [(setup_ui.ARROWS, "browse"), ("Enter", "choose"), ("Esc", "quit")])
        pygame.display.flip()

    def _draw_stage(self, character):
        screen, stage = self.screen, setup_ui.STAGE
        ui.panel(screen, stage, bg=setup_ui.STAGE_BG, radius=16)
        floor = setup_ui.spotlight(screen, stage, character["color"], self.time)
        anims = self.big[character["id"]]
        lift = 0
        frame = anims["idle"].current_frame
        if self.hop < HOP_TIME:
            p = self.hop / HOP_TIME
            lift = round(HOP_HEIGHT * math.sin(math.pi * p))
            frame = anims["jump"].current_frame
        shadow = pygame.Rect(0, 0, max(30, 100 - lift), 14)
        shadow.center = (stage.centerx, floor - 2)
        pygame.draw.ellipse(screen, (10, 6, 18), shadow)
        screen.blit(frame, frame.get_rect(midbottom=(stage.centerx, floor + 4 - lift)))
        if self.confirming is not None:
            for k in range(8):   # a little burst of sparkles on confirm
                a = k * math.pi / 4 + self.confirming * 3
                r = 60 + 120 * self.confirming
                setup_ui.sparkle(screen, (stage.centerx + r * math.cos(a), floor - 90 + r * math.sin(a)), 9, ui.GOLD)
        self._arrows = {
            -1: setup_ui.arrow_button(screen, (stage.x + 34, stage.centery - 10), -1),
            1: setup_ui.arrow_button(screen, (stage.right - 34, stage.centery - 10), 1),
        }
        ui.text(screen, f"{self.index + 1} / {len(CHARACTERS)}", ui.label_font(16), (stage.centerx, stage.bottom - 18),
                color=ui.MUTED, anchor="center", thickness=1)

    def _draw_card(self, character):
        screen, card = self.screen, setup_ui.CARD
        ui.panel(screen, card, bg=setup_ui.CARD_BG, radius=16)
        x = card.x + 24
        ui.text(screen, character["name"].upper(), ui.title_font(36), (x, card.y + 18), thickness=3)
        ui.text(screen, character["jp"], ui.body_font(20), (x, card.y + 64), color=ui.GOLD, thickness=1)
        y = card.y + 100
        for line in setup_ui.wrap(character["blurb"], ui.body_font(18), card.width - 48)[:2]:
            ui.text(screen, line, ui.body_font(18), (x, y), thickness=1)
            y += 26
        pygame.draw.line(screen, (80, 70, 110), (x, card.y + 164), (card.right - 24, card.y + 164), 1)
        ui.text(screen, "FAVOURITE SNACKS", ui.label_font(16), (x, card.y + 178), color=ui.GOLD)
        tile_w = (card.width - 48 - 12) // 2
        for i, item_id in enumerate(character["favorites"]):
            item = get_item(item_id)
            tile = ui.panel(screen, (x + i * (tile_w + 12), card.y + 202, tile_w, 62),
                            bg=(40, 32, 62, 230), radius=10)
            icon = get_icon(item_id, 52)
            screen.blit(icon, icon.get_rect(midleft=(tile.x + 8, tile.centery)))
            ui.text(screen, item.name, ui.body_font(17), (tile.x + 68, tile.y + 10), thickness=1)
            ui.text(screen, item.jp, ui.body_font(15), (tile.x + 68, tile.y + 34), color=ui.SKY, thickness=1)
        ui.text(screen, "Find them in a level for bonus points and a very happy hero.", ui.body_font(14),
                (x, card.bottom - 26), color=ui.MUTED, thickness=1)

    def _draw_roster_item(self, i, rect, selected):
        frame = self.small[CHARACTERS[i]["id"]].current_frame
        if not selected:
            frame = frame.copy()
            frame.set_alpha(150)
        self.screen.blit(frame, frame.get_rect(midbottom=(rect.centerx, rect.bottom - 6)))

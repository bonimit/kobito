"""Choose your world on an RPG overworld map (kobito/world_map.py).

The mascot -- in whatever it's wearing -- walks around the map with the
arrow keys / WASD / the stick or d-pad; every world is a town with its own
landmark (Mt Fuji, a pagoda, Big Ben, the pyramids ...). Stand on a town
and a card shows that world's look; Enter / Space / A goes there. With a
mouse or a finger, tap a town and the hero walks there along the roads, and
tap it again to go in.
"""

import asyncio
import math

import pygame

from kobito import audio, display, gear_art, setup_ui, town_ui, ui
from kobito import input as game_input
from kobito.background import Background
from kobito.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from kobito.themes import THEMES
from kobito.world_map import PLACES, SCALE, build

WORLD_ORDER = [
    "forest", "desert", "arabian_night", "underwater", "sky",
    "tokyo", "nagano", "okinawa", "hokkaido", "kyoto",
    "okinawa_drive", "aomori", "shizuoka", "hokkaido_farm",
    "island", "fairy_tale", "london", "new_york", "korea",
    "hawaii", "north_pole", "greenland", "galapagos",
]

WALK_SPEED = 210.0          # world pixels a second
AT_TOWN = 34                # this close to a town's centre is "at" the town
CARD = pygame.Rect(0, 0, 560, 118)
CARD.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 34)
MINI = pygame.Rect(SCREEN_WIDTH - 176, 50, 160, 90)
SCREEN = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
ENTER_SECONDS = 0.55
START_TOWN = "forest"

_last_town = [START_TOWN]    # the next map opens where you last chose


class WorldSelectScreen:
    def __init__(self, character_id="capybara", worn=()):
        pygame.init()
        self.screen = display.screen()
        pygame.display.set_caption("Kobito - Choose your world")
        self.clock = pygame.time.Clock()
        self.world = build()
        self.mascot = town_ui.Mascot(character_id)
        self.worn = list(worn)
        game_input.get_joysticks()

        self.x, self.y = self.world.nodes[_last_town[0]]
        self.facing_right = True
        self.moving = False
        self.route = []
        self.time = 0.0
        self.camera = [0.0, 0.0]
        self._snap_camera()
        self.near = None
        self._update_near(quiet=True)
        self.entering = None        # [town, seconds] while the hero hops in
        self.thumbs = {}
        self.minimap = pygame.transform.smoothscale(self.world.native, MINI.size)
        self.ring = self._ring()

    # -- the loop -------------------------------------------------------------------

    async def run(self):
        """Blocks until the player goes into a town, then returns its world id."""
        audio.music("map")
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in game_input.events():
                self._handle(event)
            if self.entering:
                self.entering[1] += dt
                if self.entering[1] >= ENTER_SECONDS:
                    _last_town[0] = self.entering[0]
                    return self.entering[0]
            else:
                self._walk(dt)
            self.mascot.update(dt, self.moving)
            self._follow(dt)
            self._draw()
            await asyncio.sleep(0)

    # -- input ----------------------------------------------------------------------

    def _handle(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        game_input.handle_hotplug(event)
        if self.entering:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in town_ui.CONFIRM_KEYS:
                self._go_in()
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit
        elif event.type == pygame.JOYBUTTONDOWN and event.button in game_input.CONFIRM_BUTTONS:
            self._go_in()
        tap = game_input.touch_tap_pos(event)
        if tap is not None:
            self._tap(tap)

    def _tap(self, pos):
        wx, wy = pos[0] + self.camera[0], pos[1] + self.camera[1]
        town = min(self.world.nodes, key=lambda n: math.hypot(self.world.nodes[n][0] - wx, self.world.nodes[n][1] - wy))
        tx, ty = self.world.nodes[town]
        if math.hypot(tx - wx, ty - wy) > 70:
            return                                  # not on a town
        if town == self.near:
            self._go_in()
        else:
            self.route = self.world.route(self.x, self.y, town)

    def _go_in(self):
        if self.near:
            audio.play("confirm")
            self.entering = [self.near, 0.0]
            self.route = []

    # -- walking --------------------------------------------------------------------

    def _walk(self, dt):
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        stick = game_input.move_axis()
        pad_y = game_input.climb_axis()
        if stick:
            dx = stick
        if pad_y:
            dy = pad_y
        step = WALK_SPEED * dt
        if dx or dy:
            self.route = []
            length = math.hypot(dx, dy)
            vx, vy = dx / length * step, dy / length * step
        elif self.route:
            tx, ty = self.route[0]
            dist = math.hypot(tx - self.x, ty - self.y)
            if dist <= step:
                self.x, self.y = tx, ty
                self.route.pop(0)
                vx = vy = 0.0
            else:
                vx, vy = (tx - self.x) / dist * step, (ty - self.y) / dist * step
        else:
            vx = vy = 0.0
        moved = False
        if vx and self.world.walkable(self.x + vx, self.y):          # slide along the shore
            self.x += vx
            moved = True
        if vy and self.world.walkable(self.x, self.y + vy):
            self.y += vy
            moved = True
        if vx:
            self.facing_right = vx > 0
        self.moving = moved or bool(self.route)
        self._update_near()

    def _update_near(self, quiet=False):
        """Which town (if any) the hero is standing at."""
        town = self.world.nearest(self.x, self.y)
        tx, ty = self.world.nodes[town]
        near = town if math.hypot(tx - self.x, ty - self.y) <= AT_TOWN else None
        if near and near != self.near and not quiet:
            audio.play("select")
        self.near = near

    def _snap_camera(self):
        self.camera = [self._camera_target(0), self._camera_target(1)]

    def _camera_target(self, axis):
        view = (SCREEN_WIDTH, SCREEN_HEIGHT)[axis]
        focus = (self.x, self.y - 20)[axis]
        return max(0.0, min(focus - view / 2, self.world.size[axis] - view))

    def _follow(self, dt):
        k = min(1.0, dt * 6)
        for axis in (0, 1):
            self.camera[axis] += (self._camera_target(axis) - self.camera[axis]) * k

    # -- drawing --------------------------------------------------------------------

    @staticmethod
    def _ring():
        ring = pygame.Surface((96, 48), pygame.SRCALPHA)
        pygame.draw.ellipse(ring, (255, 214, 90, 210), ring.get_rect(), 5)
        return ring

    def _thumb(self, town):
        """A small picture of that world's actual scenery (the same Background the stage uses)."""
        if town not in self.thumbs:
            back = Background(SCREEN_WIDTH, SCREEN_HEIGHT - 60, [(0, SCREEN_WIDTH)], THEMES[town])
            canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            back.draw(canvas, camera_x=0)
            self.thumbs[town] = pygame.transform.smoothscale(canvas, (160, 90))
        return self.thumbs[town]

    def _draw(self):
        screen = self.screen
        cx, cy = int(self.camera[0]) // SCALE * SCALE, int(self.camera[1]) // SCALE * SCALE
        view = self.world.native.subsurface(pygame.Rect(cx // SCALE, cy // SCALE, SCREEN_WIDTH // SCALE,
                                                        SCREEN_HEIGHT // SCALE))
        pygame.transform.scale(view, (SCREEN_WIDTH, SCREEN_HEIGHT), screen)
        self._draw_sea(cx, cy)
        self._draw_ring(cx, cy)
        self._draw_labels(cx, cy)
        self._draw_hero(cx, cy)
        self._draw_ui()
        if self.entering:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            veil.fill((250, 246, 230))
            veil.set_alpha(round(255 * max(0.0, self.entering[1] - 0.2) / (ENTER_SECONDS - 0.2)))
            screen.blit(veil, (0, 0))
        pygame.display.flip()

    def _draw_sea(self, cx, cy):
        """Twinkles on the open water."""
        for x, y, phase in self.world.sparkles:
            sx, sy = x - cx, y - cy
            if 0 <= sx < SCREEN_WIDTH and 0 <= sy < SCREEN_HEIGHT and math.sin(self.time * 2.2 + phase) > 0.75:
                pygame.draw.rect(self.screen, (214, 238, 255), (sx, sy, 6, 2))

    def _draw_ring(self, cx, cy):
        if not self.near:
            return
        x, y = self.world.nodes[self.near]
        pulse = 1 + 0.08 * math.sin(self.time * 5)
        ring = pygame.transform.scale(self.ring, (round(96 * pulse), round(48 * pulse)))
        self.screen.blit(ring, ring.get_rect(center=(x - cx, y + 4 - cy)))

    def _ui_zones(self):
        """Where the step bar, title, minimap and the card / prompt sit: town names stay out of them."""
        zones = [pygame.Rect(SCREEN_WIDTH // 2 - 280, 4, 560, 100), MINI.inflate(16, 16)]
        zones.append(CARD.inflate(8, 8) if self.near else pygame.Rect(0, SCREEN_HEIGHT - 70, SCREEN_WIDTH, 70))
        return zones

    def _draw_labels(self, cx, cy):
        """Every town's name under its landmark (kept on screen, and clear of the cards and bars);
        the one you're at lights up gold."""
        font = ui.label_font(16)
        zones = self._ui_zones()
        for town, (x, y) in self.world.nodes.items():
            sx, sy = x - cx, y - cy
            if not (0 <= sx < SCREEN_WIDTH and 0 <= sy < SCREEN_HEIGHT):
                continue
            here = town == self.near
            rect = ui.label_font(16).render(PLACES[town][0].upper(), True, ui.CREAM).get_rect(midtop=(sx, sy + 26))
            rect.clamp_ip(SCREEN.inflate(-8, -8))
            if any(rect.inflate(6, 2).colliderect(z) for z in zones):
                continue
            ui.text(self.screen, PLACES[town][0].upper(), font, rect.topleft, anchor="topleft",
                    color=ui.GOLD if here else ui.CREAM, thickness=2)

    def _draw_hero(self, cx, cy):
        hop = 0
        if self.entering:
            hop = round(abs(math.sin(self.entering[1] / ENTER_SECONDS * math.pi * 2)) * 26)
        sx, sy = round(self.x - cx), round(self.y - cy)
        shadow = pygame.Surface((36, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        self.screen.blit(shadow, shadow.get_rect(center=(sx, sy - 2)))
        frame = self.mascot.frame(self.worn, scale=1, moving=self.moving, facing_right=self.facing_right)
        bob = 0 if self.moving else town_ui.bob(self.time, 3, 1)
        self.screen.blit(frame, frame.get_rect(midbottom=(sx, sy + 2 - hop + bob)))

    def _draw_ui(self):
        screen = self.screen
        setup_ui.draw_steps(screen, 2)
        ui.text(screen, "WORLD MAP", ui.title_font(28), (SCREEN_WIDTH // 2, 54), anchor="midtop", thickness=3)
        self._draw_minimap()
        if self.near:
            self._draw_card(self.near)
        else:
            words = game_input.prompt("WALK TO A TOWN  ·  ARROWS / WASD", "WALK TO A TOWN  ·  D-PAD / STICK",
                                      "TAP A TOWN TO WALK THERE")
            rect = pygame.Rect(0, 0, ui.label_font(16).size(words)[0] + 40, 34)
            rect.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 28)
            ui.panel(screen, rect, bg=(20, 16, 36, 225), radius=17)
            ui.text(screen, words, ui.label_font(16), rect.center, anchor="center", thickness=1)

    def _draw_card(self, town):
        screen = self.screen
        name, jp, reading = PLACES[town]
        panel = ui.panel(screen, CARD, bg=(20, 16, 36, 238), edge=(*ui.GOLD, 220), radius=14)
        thumb = self._thumb(town)
        frame = pygame.Rect(panel.x + 12, panel.y + 14, 160, 90)
        screen.blit(thumb, frame)
        pygame.draw.rect(screen, ui.OUTLINE, frame.inflate(4, 4), width=3, border_radius=3)
        tx = frame.right + 18
        ui.text(screen, name.upper(), ui.title_font(24), (tx, panel.y + 14), thickness=2)
        ui.text(screen, f"{jp}", ui.body_font(22), (tx, panel.y + 48), color=ui.GOLD, thickness=1)
        jp_w = ui.body_font(22).size(jp)[0]
        ui.text(screen, reading, ui.label_font(16), (tx + jp_w + 12, panel.y + 54), color=ui.MUTED, thickness=1)
        if int(self.time * 2) % 2 == 0 or self.entering:
            words = game_input.prompt("ENTER: PLAY", "A: PLAY", "TAP THE TOWN: PLAY")
            ui.text(screen, words, ui.label_font(16), (tx, panel.bottom - 18), anchor="bottomleft", color=ui.GREEN)

    def _draw_minimap(self):
        screen = self.screen
        ui.panel(screen, MINI.inflate(10, 10), bg=(20, 16, 36, 220), radius=8)
        screen.blit(self.minimap, MINI)
        factor = MINI.width / self.world.size[0]
        for town, (x, y) in self.world.nodes.items():
            color = ui.GOLD if town == self.near else (255, 255, 255)
            pygame.draw.circle(screen, ui.OUTLINE, (MINI.x + x * factor, MINI.y + y * factor), 3)
            pygame.draw.circle(screen, color, (MINI.x + x * factor, MINI.y + y * factor), 2)
        px, py = MINI.x + self.x * factor, MINI.y + self.y * factor
        pygame.draw.circle(screen, ui.OUTLINE, (px, py), 5)
        pygame.draw.circle(screen, (255, 90, 90), (px, py), 3)
        view = pygame.Rect(MINI.x + self.camera[0] * factor, MINI.y + self.camera[1] * factor,
                           SCREEN_WIDTH * factor, SCREEN_HEIGHT * factor)
        pygame.draw.rect(screen, ui.CREAM, view, width=1)

"""
object_renderer.py
------------------
Everything that is drawn on screen:

  * procedural stone / mossy / door textures (no image files needed)
  * floor and ceiling gradients, textured wall slices with distance shading
  * billboard sprites (enemies, keys, potions) clipped by the wall depth buffer
  * torch flicker, vignette, damage flash, sword animation
  * the HUD (health bar, keys, minimap, messages) and the end screens
"""
import math
import random

import pygame

from settings import *


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------
def _clamp(value, lo=0, hi=255):
    return max(lo, min(hi, int(value)))


def _shift(color, amount):
    """Lighten (+) or darken (-) an RGB colour."""
    return (_clamp(color[0] + amount), _clamp(color[1] + amount), _clamp(color[2] + amount))


def light_factor(distance):
    """Brightness 0..1 at a given distance from the torch (walls and sprites share it)."""
    t = min(1.0, max(0.0, distance / FOG_DISTANCE))
    return AMBIENT_LIGHT + (1.0 - AMBIENT_LIGHT) * (1.0 - t) ** 1.7


def _tint(factor):
    """Multiplier colour: brightness factor times the warm torch tint."""
    return (_clamp(255 * factor * TORCH_TINT[0]),
            _clamp(255 * factor * TORCH_TINT[1]),
            _clamp(255 * factor * TORCH_TINT[2]))


# ----------------------------------------------------------------------
# Procedural textures
# ----------------------------------------------------------------------
def make_brick_texture(base, mortar, rng, mossy=False):
    """Stone brick wall: offset brick rows, bevelled edges, speckles, cracks, optional moss."""
    size = TEXTURE_SIZE
    surf = pygame.Surface((size, size))
    surf.fill(mortar)
    rows = 8
    brick_h = size // rows
    brick_w = size // 4
    shades = {(r, c): rng.randint(-20, 20) for r in range(rows) for c in range(4)}

    for r in range(rows):
        row_shift = brick_w // 2 if r % 2 else 0
        for c in range(-1, 5):
            rect = pygame.Rect(c * brick_w + row_shift + 1, r * brick_h + 1, brick_w - 2, brick_h - 2)
            color = _shift(base, shades[(r, c % 4)])
            pygame.draw.rect(surf, color, rect)
            # Bevel: light top/left edge, dark bottom/right edge.
            light, dark = _shift(color, 28), _shift(color, -32)
            pygame.draw.line(surf, light, rect.topleft, (rect.right - 1, rect.top))
            pygame.draw.line(surf, light, rect.topleft, (rect.left, rect.bottom - 1))
            pygame.draw.line(surf, dark, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
            pygame.draw.line(surf, dark, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1))
            # Speckled stone grain.
            for _ in range(26):
                px = rng.randint(rect.left, rect.right - 1)
                py = rng.randint(rect.top, rect.bottom - 1)
                if 0 <= px < size and 0 <= py < size:
                    surf.set_at((px, py), _shift(color, rng.randint(-26, 26)))
            # Occasional crack.
            if rng.random() < 0.12:
                cx = rng.randint(rect.left + 3, rect.right - 4)
                cy = rng.randint(rect.top + 2, rect.bottom - 6)
                pygame.draw.lines(surf, _shift(color, -45), False,
                                  [(cx, cy), (cx + 2, cy + 3), (cx - 1, cy + 6)])
            # Moss patches creeping over the bricks.
            if mossy and rng.random() < 0.6:
                for _ in range(rng.randint(2, 5)):
                    mx = rng.randint(rect.left, rect.right)
                    my = rng.randint(rect.top + brick_h // 2, rect.bottom)
                    g = rng.randint(-15, 15)
                    pygame.draw.circle(surf, (50 + g, 92 + g, 44 + g), (mx, my), rng.randint(2, 5))

    # Fine overall grain so large areas do not look flat.
    for _ in range(450):
        px, py = rng.randrange(size), rng.randrange(size)
        surf.set_at((px, py), _shift(surf.get_at((px, py))[:3], rng.randint(-14, 10)))
    return surf.convert()


def make_door_texture(rng):
    """Iron-banded wooden door with a golden lock plate (the locked exit)."""
    size = TEXTURE_SIZE
    surf = pygame.Surface((size, size))
    surf.fill((20, 14, 10))
    plank_w = size // 8
    for i in range(8):
        sh = rng.randint(-12, 12)
        color = (96 + sh, 60 + sh // 2, 32 + sh // 3)
        pygame.draw.rect(surf, color, (i * plank_w + 1, 0, plank_w - 2, size))
        for _ in range(6):                                   # wood grain
            gx = i * plank_w + rng.randint(2, plank_w - 3)
            pygame.draw.line(surf, _shift(color, -22), (gx, rng.randint(0, 40)), (gx, rng.randint(70, size)))
    for y in (20, 92):                                       # iron bands with rivets
        pygame.draw.rect(surf, (52, 54, 62), (0, y, size, 16))
        pygame.draw.line(surf, (96, 98, 108), (0, y), (size, y))
        for x in range(8, size, 24):
            pygame.draw.circle(surf, (120, 122, 132), (x, y + 8), 3)
    pygame.draw.circle(surf, (40, 40, 46), (64, 64), 23)     # lock plate
    pygame.draw.circle(surf, (200, 150, 40), (64, 64), 18)
    pygame.draw.circle(surf, (110, 20, 20), (64, 60), 5)     # keyhole
    pygame.draw.polygon(surf, (110, 20, 20), [(61, 62), (67, 62), (69, 77), (59, 77)])
    pygame.draw.rect(surf, (30, 28, 32), (0, 0, size, size), 5)   # stone frame
    return surf.convert()


def make_light_texture():
    """Warm glow shown beyond the exit door once it has opened."""
    size = TEXTURE_SIZE
    surf = pygame.Surface((size, size))
    surf.fill((225, 180, 100))
    for r in range(90, 0, -3):
        k = 1.0 - r / 90.0
        pygame.draw.circle(surf, (_clamp(225 + 30 * k), _clamp(180 + 75 * k), _clamp(100 + 140 * k)),
                           (size // 2, size // 2), r)
    return surf.convert()


# ----------------------------------------------------------------------
# The renderer
# ----------------------------------------------------------------------
class ObjectRenderer:
    SPRITE_SIZE = 128
    # name -> (height as a fraction of a wall, floating height above the floor)
    SPRITE_LAYOUT = {
        "enemy": (0.90, 0.0), "enemy_hurt": (0.90, 0.0),
        "key": (0.34, 0.20), "potion": (0.30, 0.06),
    }

    def __init__(self, screen, game_map):
        self.screen = screen
        self.map = game_map
        self.show_minimap = True
        self.torch = 0.0                         # flicker value, updated every frame

        self.font_small = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 30)
        self.font_medium = pygame.font.Font(None, 44)
        self.font_big = pygame.font.Font(None, 110)

        rng = random.Random(1337)                # fixed seed: same look every launch
        self.textures = self._build_wall_textures(rng)
        self._build_background()
        self._build_sprites()
        self._build_vignette()
        self._build_weapon()
        self.flash_surface = pygame.Surface(RES, pygame.SRCALPHA)
        self.build_minimap()

    # ------------------------------------------------------------------
    # One-time asset construction
    # ------------------------------------------------------------------
    def _build_wall_textures(self, rng):
        """Create every wall texture plus SHADE_LEVELS pre-darkened copies of each."""
        base = {
            WALL_STONE: make_brick_texture(*WALL_COLORS[WALL_STONE], rng),
            WALL_MOSSY: make_brick_texture(*WALL_COLORS[WALL_MOSSY], rng, mossy=True),
            WALL_DOOR: make_door_texture(rng),
            WALL_LIGHT: make_light_texture(),
        }
        textures = {}
        for tile, image in base.items():
            levels = []
            for level in range(SHADE_LEVELS):
                factor = light_factor(level / LEVELS_PER_UNIT)
                shaded = image.copy()
                if tile == WALL_LIGHT:           # the exit glow lights itself: no torch tint
                    grey = _clamp(255 * max(factor, 0.9))
                    shaded.fill((grey, grey, grey), special_flags=pygame.BLEND_RGB_MULT)
                else:
                    shaded.fill(_tint(factor), special_flags=pygame.BLEND_RGB_MULT)
                levels.append(shaded)
            textures[tile] = levels
        return textures

    def _build_background(self):
        """Ceiling and floor as vertical gradients: dark at the horizon, lighter near us."""
        h = HALF_HEIGHT + BOB_MARGIN
        self.floor = pygame.Surface((WIDTH, h))
        self.ceiling = pygame.Surface((WIDTH, h))
        for y in range(h):
            t = min(1.0, y / HALF_HEIGHT)        # 0 at the horizon, 1 at the screen edge
            floor_color = tuple(_clamp(c * (0.05 + 0.55 * t ** 1.1) * tt)
                                for c, tt in zip(FLOOR_COLOR, TORCH_TINT))
            ceil_color = tuple(_clamp(c * (0.03 + 0.40 * t ** 1.1) * tt)
                               for c, tt in zip(CEILING_COLOR, TORCH_TINT))
            pygame.draw.line(self.floor, floor_color, (0, y), (WIDTH, y))
            pygame.draw.line(self.ceiling, ceil_color, (0, h - 1 - y), (WIDTH, h - 1 - y))
        self.floor = self.floor.convert()
        self.ceiling = self.ceiling.convert()

    def _build_vignette(self):
        """Dark screen edges: a tiny alpha image smooth-scaled up to full size."""
        w, h = 80, 48
        small = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                nx, ny = (x - w / 2) / (w / 2), (y - h / 2) / (h / 2)
                d = min(1.0, math.hypot(nx, ny) / 1.35)
                small.set_at((x, y), (0, 0, 0, int(215 * d ** 2.4)))
        self.vignette = pygame.transform.smoothscale(small, RES).convert_alpha()

    def _build_sprites(self):
        self.sprites = {
            "key": self._draw_key(),
            "potion": self._draw_potion(),
            "enemy": self._draw_enemy(False),
            "enemy_hurt": self._draw_enemy(True),
        }
        self.key_icon = pygame.transform.smoothscale(self.sprites["key"], (40, 40))
        self.key_icon_dim = self.key_icon.copy()
        self.key_icon_dim.fill((85, 85, 100), special_flags=pygame.BLEND_RGB_MULT)

    def _blank(self):
        return pygame.Surface((self.SPRITE_SIZE, self.SPRITE_SIZE), pygame.SRCALPHA)

    def _draw_key(self):
        s = self._blank()
        gold, shine = (235, 190, 60), (255, 240, 170)
        for r in range(60, 20, -8):                          # soft golden glow
            pygame.draw.circle(s, (255, 210, 80, 16), (64, 62), r)
        pygame.draw.circle(s, gold, (64, 38), 20, 8)         # bow (ring)
        pygame.draw.rect(s, gold, (60, 56, 8, 54))           # shaft
        pygame.draw.rect(s, gold, (68, 88, 18, 8))           # teeth
        pygame.draw.rect(s, gold, (68, 100, 13, 8))
        pygame.draw.line(s, shine, (61, 58), (61, 108), 2)
        return s.convert_alpha()

    def _draw_potion(self):
        s = self._blank()
        pygame.draw.rect(s, (190, 210, 230), (54, 28, 20, 30))          # glass neck
        pygame.draw.rect(s, (120, 80, 40), (52, 18, 24, 14))            # cork
        pygame.draw.ellipse(s, (170, 20, 40), (34, 50, 60, 64))         # flask body
        pygame.draw.ellipse(s, (225, 70, 90), (44, 62, 16, 28))         # liquid highlight
        pygame.draw.ellipse(s, (60, 10, 20), (34, 50, 60, 64), 3)       # outline
        return s.convert_alpha()

    def _draw_enemy(self, hurt):
        s = self._blank()
        bone = (196, 186, 164)
        pygame.draw.polygon(s, (40, 32, 48), [(64, 22), (100, 54), (114, 126), (14, 126), (28, 54)])
        pygame.draw.polygon(s, (62, 50, 74), [(64, 40), (84, 60), (92, 126), (36, 126), (44, 60)])
        pygame.draw.line(s, bone, (30, 62), (10, 100), 5)                # bony arms
        pygame.draw.line(s, bone, (98, 62), (118, 100), 5)
        for dx in (-6, 0, 6):                                            # claws
            pygame.draw.line(s, (220, 210, 190), (10, 100), (10 + dx, 116), 2)
            pygame.draw.line(s, (220, 210, 190), (118, 100), (118 + dx, 116), 2)
        pygame.draw.ellipse(s, (24, 18, 30), (34, 8, 60, 64))            # hood
        pygame.draw.ellipse(s, (214, 204, 182), (46, 22, 36, 42))        # skull face
        pygame.draw.ellipse(s, (20, 0, 0), (51, 34, 10, 12))             # eye sockets
        pygame.draw.ellipse(s, (20, 0, 0), (67, 34, 10, 12))
        pygame.draw.circle(s, (255, 50, 30), (56, 40), 3)                # glowing eyes
        pygame.draw.circle(s, (255, 50, 30), (72, 40), 3)
        pygame.draw.polygon(s, (50, 36, 34), [(64, 48), (60, 56), (68, 56)])
        pygame.draw.rect(s, (230, 225, 210), (54, 58, 20, 6))            # teeth
        for x in range(58, 74, 4):
            pygame.draw.line(s, (60, 50, 50), (x, 58), (x, 63))
        if hurt:                                                         # red flash when hit
            s.fill((150, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
        return s.convert_alpha()

    def _build_weapon(self):
        """A simple first-person sword; pivot is the bottom-centre of the image."""
        w, h = 64, 300
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(s, (190, 196, 208), [(32, 0), (44, 30), (42, 210), (22, 210), (20, 30)])
        pygame.draw.line(s, (120, 126, 140), (32, 18), (32, 205), 3)     # fuller
        pygame.draw.line(s, (240, 244, 250), (23, 32), (23, 208), 2)     # edge highlight
        pygame.draw.polygon(s, (60, 64, 76), [(32, 0), (44, 30), (42, 210), (22, 210), (20, 30)], 2)
        pygame.draw.rect(s, (200, 150, 40), (8, 208, 48, 12))            # crossguard
        pygame.draw.rect(s, (90, 56, 30), (27, 220, 10, 56))             # grip
        pygame.draw.circle(s, (200, 150, 40), (32, 284), 9)              # pommel
        self.sword = s.convert_alpha()

    def build_minimap(self):
        """(Re)draw the static part of the minimap: walls and the exit door."""
        cell = MINIMAP_CELL
        surf = pygame.Surface((self.map.cols * cell, self.map.rows * cell), pygame.SRCALPHA)
        surf.fill((8, 8, 12, 175))
        for y, row in enumerate(self.map.grid):
            for x, tile in enumerate(row):
                if tile == EMPTY:
                    continue
                if tile == WALL_DOOR:
                    color = MINIMAP_DOOR_OPEN if self.map.exit_open else MINIMAP_DOOR_LOCKED
                else:
                    color = MINIMAP_WALL
                pygame.draw.rect(surf, color, (x * cell, y * cell, cell, cell))
        self.minimap = surf

    # ------------------------------------------------------------------
    # 3D scene
    # ------------------------------------------------------------------
    def render_scene(self, player, hits, depths, entities, time_s):
        """Draw floor, ceiling, walls, sprites, vignette and the sword."""
        # Smooth pseudo-random torch flicker in the range [-1, 1].
        self.torch = (0.5 * math.sin(time_s * 9.0) + 0.3 * math.sin(time_s * 17.3 + 1.0)
                      + 0.2 * math.sin(time_s * 3.1))
        horizon = HALF_HEIGHT + int(player.bob)

        self.screen.blit(self.ceiling, (0, horizon - self.ceiling.get_height()))
        self.screen.blit(self.floor, (0, horizon))
        self._draw_walls(hits, horizon)
        self._draw_sprites(player, entities, depths, horizon, time_s)
        self.screen.blit(self.vignette, (0, 0))
        self._draw_weapon(player)

    def _draw_walls(self, hits, horizon):
        """Draw one textured, distance-shaded slice per ray."""
        flicker = 1.0 + TORCH_FLICKER * self.torch
        draw_h = HEIGHT + 2 * BOB_MARGIN         # tall slices are cropped to this height
        scale = pygame.transform.scale
        slices = []
        for i, (depth, height, tile, offset, side) in enumerate(hits):
            level = int(depth * flicker * LEVELS_PER_UNIT) + (SIDE_SHADE_LEVELS if side else 0)
            levels = self.textures.get(tile, self.textures[WALL_STONE])
            texture = levels[min(level, SHADE_LEVELS - 1)]
            tex_x = min(TEXTURE_SIZE - 1, int(offset * TEXTURE_SIZE))

            if height < draw_h:                  # whole wall fits on screen
                h = max(1, int(height))
                column = scale(texture.subsurface((tex_x, 0, 1, TEXTURE_SIZE)), (SCALE, h))
                y = horizon - h // 2
            else:                                # wall is taller than the screen: crop texture
                tex_h = max(1, int(TEXTURE_SIZE * draw_h / height))
                top = HALF_TEXTURE_SIZE - tex_h // 2
                column = scale(texture.subsurface((tex_x, top, 1, tex_h)), (SCALE, draw_h))
                y = horizon - draw_h // 2
            slices.append((column, (i * SCALE, y)))
        self.screen.blits(slices, False)

    def _draw_sprites(self, player, entities, depths, horizon, time_s):
        """Billboard sprites, drawn far-to-near and hidden behind nearer walls."""
        visible = []
        for ent in entities:
            dx, dy = ent.x - player.x, ent.y - player.y
            theta = (math.atan2(dy, dx) - player.angle + math.pi) % math.tau - math.pi
            if abs(theta) > HALF_FOV + 0.6:      # generous margin: wide sprites at the edge
                continue
            depth = math.hypot(dx, dy) * math.cos(theta)
            if depth < 0.4:
                continue
            visible.append((depth, theta, ent))
        visible.sort(key=lambda v: v[0], reverse=True)

        flicker = 1.0 + TORCH_FLICKER * self.torch
        for depth, theta, ent in visible:
            name = ent.sprite_name
            rel_height, lift = self.SPRITE_LAYOUT[name]
            if ent.__class__.__name__ == "Pickup":
                lift += 0.05 * math.sin(time_s * 3.0 + ent.x * 2.0)      # items gently float
            proj = SCREEN_DIST / depth                                   # one wall height in px
            size = int(proj * rel_height)
            if size < 2 or size > 1800:
                continue

            screen_x = HALF_WIDTH + math.tan(theta) * SCREEN_DIST
            x_left = int(screen_x - size / 2)
            y_top = int(horizon + proj / 2 - lift * proj - size)

            image = pygame.transform.scale(self.sprites[name], (size, size))
            image.fill(_tint(light_factor(depth * flicker)), special_flags=pygame.BLEND_RGB_MULT)

            # Blit contiguous runs of columns that are not hidden behind a wall.
            first = max(0, x_left // SCALE + 1)
            last = min(NUM_RAYS - 1, (x_left + size) // SCALE)
            run_start = None
            for i in range(first, last + 2):
                shown = i <= last and depths[i] > depth
                if shown and run_start is None:
                    run_start = i
                elif not shown and run_start is not None:
                    src_x = run_start * SCALE - x_left
                    width = min((i - run_start) * SCALE, size - src_x)
                    if width > 0:
                        self.screen.blit(image, (run_start * SCALE, y_top), (src_x, 0, width, size))
                    run_start = None

    def _draw_weapon(self, player):
        """First-person sword: idles with the head bob and swings when attacking."""
        progress = player.swing_progress
        swing = math.sin(progress * math.pi) if progress is not None else 0.0
        angle = 18 + 62 * swing                                   # degrees, counter-clockwise
        pivot_x = HALF_WIDTH + 310 + math.sin(player.bob_phase * 0.5) * 6
        pivot_y = HEIGHT + 60 - 150 * swing + abs(math.sin(player.bob_phase)) * 6
        rotated = pygame.transform.rotate(self.sword, angle)
        half = self.sword.get_height() / 2
        rad = math.radians(angle)
        center = (pivot_x - half * math.sin(rad), pivot_y - half * math.cos(rad))
        self.screen.blit(rotated, rotated.get_rect(center=center))

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def _text(self, text, font, color, pos, center=False):
        image = font.render(text, True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        self.screen.blit(font.render(text, True, BLACK), rect.move(2, 2))   # drop shadow
        self.screen.blit(image, rect)
        return rect

    def draw_hud(self, player, game_map, fps, message, show_help):
        # Damage flash and low-health pulse.
        alpha = int(120 * player.damage_flash)
        if player.health < 30 and player.is_alive:
            alpha = max(alpha, int(35 + 25 * math.sin(pygame.time.get_ticks() / 180.0)))
        if alpha > 0:
            self.flash_surface.fill((190, 0, 0, alpha))
            self.screen.blit(self.flash_surface, (0, 0))

        # Crosshair.
        cx, cy = HALF_WIDTH, HALF_HEIGHT
        pygame.draw.line(self.screen, (230, 230, 230), (cx - 8, cy), (cx - 3, cy))
        pygame.draw.line(self.screen, (230, 230, 230), (cx + 3, cy), (cx + 8, cy))
        pygame.draw.line(self.screen, (230, 230, 230), (cx, cy - 8), (cx, cy - 3))
        pygame.draw.line(self.screen, (230, 230, 230), (cx, cy + 3), (cx, cy + 8))

        # Health bar (bottom-left).
        bar = pygame.Rect(24, HEIGHT - 64, 280, 24)
        ratio = player.health / PLAYER_MAX_HEALTH
        color = HEALTH_GOOD if ratio > 0.6 else HEALTH_MID if ratio > 0.3 else HEALTH_LOW
        panel = pygame.Surface((bar.width + 16, bar.height + 16), pygame.SRCALPHA)
        panel.fill((*UI_PANEL, 190))
        self.screen.blit(panel, (bar.x - 8, bar.y - 8))
        pygame.draw.rect(self.screen, (50, 14, 14), bar)
        pygame.draw.rect(self.screen, color, (bar.x, bar.y, int(bar.width * ratio), bar.height))
        pygame.draw.rect(self.screen, (200, 190, 170), bar, 2)
        self._text(f"HEALTH  {int(math.ceil(player.health))}", self.font_small, WHITE,
                   bar.center, center=True)

        # Key counter above the health bar.
        total = game_map.total_keys
        for i in range(total):
            icon = self.key_icon if i < player.keys else self.key_icon_dim
            self.screen.blit(icon, (24 + i * 44, HEIGHT - 114))
        self._text(f"{player.keys}/{total}", self.font, UI_GOLD, (24 + total * 44 + 6, HEIGHT - 104))

        # Top-left info.
        self._text(f"FPS {fps:.0f}", self.font_small, GREY, (14, 12))
        if game_map.exit_open:
            self._text("Exit is OPEN - reach the glowing door!", self.font, MINIMAP_DOOR_OPEN, (14, 34))
        else:
            self._text(f"Find all {total} keys to unlock the exit", self.font, UI_GOLD, (14, 34))

        if self.show_minimap:
            self.draw_minimap(player, game_map)

        if message:
            self._text(message, self.font_medium, WHITE, (HALF_WIDTH, 96), center=True)
        if show_help:
            self._text("WASD move   Mouse/Arrows look   SHIFT sprint   SPACE/Click attack   "
                       "M map   R restart   ESC quit",
                       self.font_small, GREY, (HALF_WIDTH, HEIGHT - 14), center=True)

    def draw_minimap(self, player, game_map):
        cell = MINIMAP_CELL
        ox = WIDTH - self.minimap.get_width() - MINIMAP_MARGIN
        oy = MINIMAP_MARGIN
        self.screen.blit(self.minimap, (ox, oy))
        pygame.draw.rect(self.screen, (170, 150, 110), (ox - 1, oy - 1, self.minimap.get_width() + 2,
                                                         self.minimap.get_height() + 2), 1)
        for pickup in game_map.pickups:
            if not pickup.collected:
                color = MINIMAP_KEY if pickup.kind == "key" else MINIMAP_POTION
                pygame.draw.circle(self.screen, color, (ox + int(pickup.x * cell), oy + int(pickup.y * cell)), 2)
        for enemy in game_map.enemies:
            pygame.draw.circle(self.screen, MINIMAP_ENEMY, (ox + int(enemy.x * cell), oy + int(enemy.y * cell)), 2)
        px, py = ox + player.x * cell, oy + player.y * cell
        tip = (px + math.cos(player.angle) * 9, py + math.sin(player.angle) * 9)
        pygame.draw.line(self.screen, MINIMAP_PLAYER, (px, py), tip, 2)
        pygame.draw.circle(self.screen, MINIMAP_PLAYER, (int(px), int(py)), 3)

    # ------------------------------------------------------------------
    # End screens
    # ------------------------------------------------------------------
    def draw_end_screen(self, victory, stats):
        overlay = pygame.Surface(RES, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))
        title, color = ("YOU ESCAPED!", UI_GOLD) if victory else ("YOU DIED", UI_RED)
        self._text(title, self.font_big, color, (HALF_WIDTH, HALF_HEIGHT - 90), center=True)
        minutes, seconds = divmod(int(stats["time"]), 60)
        self._text(f"Time {minutes:02d}:{seconds:02d}     Enemies slain {stats['kills']}"
                   f"     Keys {stats['keys']}/{stats['total_keys']}",
                   self.font_medium, WHITE, (HALF_WIDTH, HALF_HEIGHT), center=True)
        self._text("Press R or ENTER to enter a new dungeon", self.font_medium, GREY,
                   (HALF_WIDTH, HALF_HEIGHT + 70), center=True)
        self._text("Press ESC to quit", self.font, GREY, (HALF_WIDTH, HALF_HEIGHT + 110), center=True)

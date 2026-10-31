"""
map.py
------
The dungeon itself: a 2D grid (1 = wall, 0 = empty space) that is generated
as a maze, plus everything that lives inside it (keys, potions, enemies).

Grid values
    0  empty floor
    1  stone wall          2  mossy stone wall (just a visual variant)
    3  the locked exit door (solid until every key has been collected)

Grid indices are grid[row][column] == grid[y][x].  One grid cell is one world
unit, so the world coordinate (x, y) lies in cell (int(x), int(y)).
"""
import math
import random
from collections import deque

from settings import *

FOUR_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Pickup:
    """A collectable lying on the floor: a 'key' or a health 'potion'."""

    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.collected = False

    @property
    def sprite_name(self):
        return self.kind


class Enemy:
    """
    A basic dungeon ghoul.  It sleeps until the player gets within
    ENEMY_AGGRO_PATH cells (measured along corridors, not through walls),
    then follows the map's flow field towards the player and claws at them.
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.health = ENEMY_HEALTH
        self.alive = True
        self.alert = False
        self.attack_timer = 0.5
        self.hurt_timer = 0.0
        self.anim = random.uniform(0.0, math.tau)

    @property
    def sprite_name(self):
        return "enemy_hurt" if self.hurt_timer > 0 else "enemy"

    # ---------------------------------------------------------------- AI
    def update(self, dt, game_map, player):
        self.anim += dt
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)

        cell = (int(self.x), int(self.y))
        path_dist = game_map.flow_distance(cell[0], cell[1])
        self.alert = path_dist is not None and path_dist <= ENEMY_AGGRO_PATH
        if not self.alert:
            return

        dist = math.hypot(player.x - self.x, player.y - self.y)
        if dist < ENEMY_ATTACK_RANGE:               # close enough to bite
            if self.attack_timer <= 0.0:
                player.take_damage(ENEMY_DAMAGE)
                self.attack_timer = ENEMY_ATTACK_COOLDOWN
            return

        if cell == (int(player.x), int(player.y)):  # same cell: walk straight at them
            tx, ty = player.x, player.y
        else:                                       # otherwise follow the flow field
            nxt = game_map.next_step(cell[0], cell[1])
            if nxt is None:
                return
            tx, ty = nxt[0] + 0.5, nxt[1] + 0.5

        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy) or 1e-6
        step = ENEMY_SPEED * dt
        self._move(dx / d * step, dy / d * step, game_map)

    def _move(self, dx, dy, game_map):
        """Move with per-axis collision so the enemy slides along walls."""
        if not game_map.collides(self.x + dx, self.y, ENEMY_RADIUS):
            self.x += dx
        if not game_map.collides(self.x, self.y + dy, ENEMY_RADIUS):
            self.y += dy

    def take_damage(self, amount, from_x, from_y, game_map):
        """Lose health and get knocked back away from the attacker."""
        self.health -= amount
        self.hurt_timer = 0.25
        dx, dy = self.x - from_x, self.y - from_y
        d = math.hypot(dx, dy) or 1e-6
        self._move(dx / d * 0.4, dy / d * 0.4, game_map)
        if self.health <= 0:
            self.alive = False


class Map:
    """Holds the grid, the exit door, all pickups/enemies and the enemy flow field."""

    def __init__(self, seed=None):
        self.cols = MAZE_COLS
        self.rows = MAZE_ROWS
        self.generate(seed)

    # ------------------------------------------------------------------
    # Dungeon generation
    # ------------------------------------------------------------------
    def generate(self, seed=None):
        """Build a brand-new random dungeon and populate it."""
        rng = random.Random(seed)
        cols, rows = self.cols, self.rows
        grid = [[1] * cols for _ in range(rows)]

        # 1) Perfect maze with an iterative recursive-backtracker.
        #    Maze cells sit on odd coordinates; walls on even ones.
        grid[1][1] = 0
        stack = [(1, 1)]
        while stack:
            x, y = stack[-1]
            options = []
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                nx, ny = x + dx, y + dy
                if 1 <= nx < cols - 1 and 1 <= ny < rows - 1 and grid[ny][nx] == 1:
                    options.append((nx, ny, dx, dy))
            if options:
                nx, ny, dx, dy = rng.choice(options)
                grid[y + dy // 2][x + dx // 2] = 0      # knock down the wall between
                grid[ny][nx] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

        # 2) A few 3x3 "pillar rooms" (open space with a stone pillar in the middle).
        for _ in range(MAZE_ROOMS):
            rx = rng.randrange(1, cols - 4, 2)
            ry = rng.randrange(1, rows - 4, 2)
            for yy in range(ry, ry + 3):
                for xx in range(rx, rx + 3):
                    if (xx, yy) != (rx + 1, ry + 1):
                        grid[yy][xx] = 0

        # 3) Remove some wall segments so the maze contains loops (not only dead ends).
        loops, tries = MAZE_EXTRA_LOOPS, 0
        while loops > 0 and tries < 3000:
            tries += 1
            x = rng.randrange(1, cols - 1)
            y = rng.randrange(1, rows - 1)
            if grid[y][x] != 1:
                continue
            horizontal = grid[y][x - 1] == 0 and grid[y][x + 1] == 0
            vertical = grid[y - 1][x] == 0 and grid[y + 1][x] == 0
            if horizontal != vertical:                  # a wall between exactly two corridors
                grid[y][x] = 0
                loops -= 1

        # 4) Exit hall in the bottom-right corner with the locked door in the outer wall.
        exit_hall = set()
        for yy in range(rows - 4, rows - 1):
            for xx in range(cols - 4, cols - 1):
                grid[yy][xx] = 0
                exit_hall.add((xx, yy))
        self.door = (cols - 1, rows - 2)
        grid[self.door[1]][self.door[0]] = WALL_DOOR
        self.exit_open = False

        # 5) Visual variety: patches of mossy stone.
        offset = rng.randrange(4)
        for y in range(rows):
            for x in range(cols):
                if grid[y][x] == 1 and ((x // 2) * 5 + (y // 2) * 3 + (x // 2) * (y // 2) + offset) % 4 == 0:
                    grid[y][x] = WALL_MOSSY

        self.grid = grid
        self.start_pos = (1.5, 1.5)
        self.start_angle = 0.0 if grid[1][2] == 0 else math.pi / 2

        # 6) Populate the dungeon.
        self._populate(rng, exit_hall)

        # Enemy flow field (BFS distance towards the player), built lazily.
        self.flow = None
        self._flow_origin = None

    def _populate(self, rng, exit_hall):
        """Place keys (preferably in dead ends), potions and enemies."""
        dist = self._bfs((1, 1))
        open_cells = [c for c in dist if c not in exit_hall]
        dead_ends = [c for c in open_cells if self._open_neighbours(*c) == 1]
        rest = [c for c in open_cells if c not in dead_ends]
        rng.shuffle(dead_ends)
        rng.shuffle(rest)

        taken = set(exit_hall)
        taken.add((1, 1))
        key_cells = self._place(NUM_KEYS, dead_ends + rest, dist, 12, 10, taken)
        enemy_cells = self._place(NUM_ENEMIES, rest + dead_ends, dist, 9, 5, taken)
        potion_cells = self._place(NUM_POTIONS, dead_ends + rest, dist, 4, 8, taken)

        self.pickups = [Pickup(x + 0.5, y + 0.5, "key") for x, y in key_cells]
        self.pickups += [Pickup(x + 0.5, y + 0.5, "potion") for x, y in potion_cells]
        self.enemies = [Enemy(x + 0.5, y + 0.5) for x, y in enemy_cells]
        self.total_keys = len(key_cells)    # the exit needs exactly this many keys

    @staticmethod
    def _place(count, pool, dist, min_start, min_sep, taken):
        """Pick `count` cells from `pool`, far from the start and from each other."""
        chosen = []
        for sep in (min_sep, max(2, min_sep // 2), 0):   # relax spacing if needed
            for cell in pool:
                if len(chosen) >= count:
                    break
                if cell in taken or cell in chosen or dist[cell] < min_start:
                    continue
                if all(abs(cell[0] - o[0]) + abs(cell[1] - o[1]) >= sep for o in chosen):
                    chosen.append(cell)
            if len(chosen) >= count:
                break
        taken.update(chosen)
        return chosen

    def _open_neighbours(self, x, y):
        return sum(1 for dx, dy in FOUR_DIRS if self.grid[y + dy][x + dx] == 0)

    def _bfs(self, start):
        """Return {cell: steps_from_start} for every reachable empty cell."""
        dist = {start: 0}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in FOUR_DIRS:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in dist and 0 <= nx < self.cols and 0 <= ny < self.rows \
                        and self.grid[ny][nx] == 0:
                    dist[(nx, ny)] = dist[(x, y)] + 1
                    queue.append((nx, ny))
        return dist

    # ------------------------------------------------------------------
    # World queries
    # ------------------------------------------------------------------
    def is_wall(self, cx, cy):
        """True if grid cell (cx, cy) blocks movement (out of range counts as wall)."""
        if cx < 0 or cy < 0 or cx >= self.cols or cy >= self.rows:
            return True
        tile = self.grid[cy][cx]
        if tile == WALL_DOOR and self.exit_open:
            return False
        return tile != EMPTY

    def collides(self, x, y, radius):
        """Does a square body of half-size `radius` at world (x, y) touch a wall?"""
        for ox, oy in ((-radius, -radius), (radius, -radius), (-radius, radius), (radius, radius)):
            if self.is_wall(int(math.floor(x + ox)), int(math.floor(y + oy))):
                return True
        return False

    def has_line_of_sight(self, x0, y0, x1, y1):
        """Sample along the segment; blocked as soon as it crosses a wall cell."""
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = int(dist / 0.15) + 1
        for i in range(1, steps):
            t = i / steps
            if self.is_wall(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t)):
                return False
        return True

    # ------------------------------------------------------------------
    # Exit door
    # ------------------------------------------------------------------
    def unlock_exit(self):
        self.exit_open = True

    def reached_exit(self, x, y):
        """True when the player stands inside the (opened) door cell."""
        return self.exit_open and (int(x), int(y)) == self.door

    # ------------------------------------------------------------------
    # Enemy navigation (BFS flow field centred on the player)
    # ------------------------------------------------------------------
    def update_flow_field(self, px, py):
        """Recompute walking distances to the player, only when they change cell."""
        origin = (int(px), int(py))
        if origin == self._flow_origin:
            return
        self._flow_origin = origin
        flow = [[-1] * self.cols for _ in range(self.rows)]
        flow[origin[1]][origin[0]] = 0
        queue = deque([origin])
        limit = ENEMY_AGGRO_PATH + 2
        while queue:
            x, y = queue.popleft()
            d = flow[y][x]
            if d >= limit:
                continue
            for dx, dy in FOUR_DIRS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.cols and 0 <= ny < self.rows \
                        and self.grid[ny][nx] == 0 and flow[ny][nx] == -1:
                    flow[ny][nx] = d + 1
                    queue.append((nx, ny))
        self.flow = flow

    def flow_distance(self, x, y):
        """Walking distance (in cells) to the player, or None if out of range."""
        if self.flow is None:
            return None
        d = self.flow[y][x]
        return None if d < 0 else d

    def next_step(self, x, y):
        """The neighbouring cell that is closest to the player (or None)."""
        if self.flow is None:
            return None
        best, best_d = None, self.flow[y][x]
        for dx, dy in FOUR_DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.cols and 0 <= ny < self.rows:
                d = self.flow[ny][nx]
                if d != -1 and d < best_d:
                    best, best_d = (nx, ny), d
        return best

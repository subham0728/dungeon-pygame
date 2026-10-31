"""
settings.py
-----------
Central configuration for "Crypt of Embers", a Doom/Wolfenstein-style
raycasting dungeon explorer.  Every tunable number lives here so the other
modules never contain "magic numbers".
"""
import math

# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------
RES = WIDTH, HEIGHT = 1000, 600
HALF_WIDTH = WIDTH // 2
HALF_HEIGHT = HEIGHT // 2
FPS = 60
TITLE = "Crypt of Embers - 3D Dungeon Explorer"
BOB_MARGIN = 10            # extra pixels drawn above/below the screen for head bob

# --------------------------------------------------------------------------
# Raycasting
# --------------------------------------------------------------------------
FOV = math.pi / 3                          # 60 degree field of view
HALF_FOV = FOV / 2
NUM_RAYS = WIDTH // 2                      # one ray per 2-pixel wide column
SCALE = WIDTH // NUM_RAYS                  # pixel width of every wall slice
SCREEN_DIST = HALF_WIDTH / math.tan(HALF_FOV)   # distance to the projection plane
MAX_DEPTH = 24.0                           # rays stop after this many tiles

# --------------------------------------------------------------------------
# Wall / tile ids stored in the map grid
# --------------------------------------------------------------------------
EMPTY = 0
WALL_STONE = 1             # plain stone brick
WALL_MOSSY = 2             # mossy stone brick (visual variation)
WALL_DOOR = 3              # the locked exit door
WALL_LIGHT = 4             # glowing light seen through an opened exit

# --------------------------------------------------------------------------
# Textures and lighting
# --------------------------------------------------------------------------
TEXTURE_SIZE = 128
HALF_TEXTURE_SIZE = TEXTURE_SIZE // 2
SHADE_LEVELS = 28                          # pre-darkened copies of each texture
FOG_DISTANCE = 15.0                        # distance at which things are (almost) black
LEVELS_PER_UNIT = SHADE_LEVELS / FOG_DISTANCE
SIDE_SHADE_LEVELS = 3                      # north/south faces are rendered darker
AMBIENT_LIGHT = 0.03                       # minimum brightness at the edge of the fog
TORCH_TINT = (1.0, 0.84, 0.62)             # warm torch colour applied to lit surfaces
TORCH_FLICKER = 0.07                       # strength of the torch flicker

# --------------------------------------------------------------------------
# Player
# --------------------------------------------------------------------------
PLAYER_SPEED = 2.6                         # tiles per second
SPRINT_MULTIPLIER = 1.75
PLAYER_ROT_SPEED = 2.3                     # radians per second (arrow keys)
MOUSE_SENSITIVITY = 0.0022                 # radians per mouse pixel
MOUSE_MAX_REL = 60                         # clamp for a single mouse movement
PLAYER_RADIUS = 0.25                       # collision radius in tiles
PLAYER_ACCEL = 14.0                        # higher = snappier movement smoothing
PLAYER_MAX_HEALTH = 100
BOB_AMPLITUDE = 4.0                        # head bob in pixels
BOB_FREQUENCY = 3.5                        # radians of bob per tile walked

# Melee combat
ATTACK_COOLDOWN = 0.55
ATTACK_SWING_TIME = 0.28
ATTACK_RANGE = 1.7
ATTACK_ARC = 0.6                           # +/- radians in front of the player
ATTACK_DAMAGE = 1

# --------------------------------------------------------------------------
# Dungeon generation / gameplay
# --------------------------------------------------------------------------
MAZE_COLS = 31                             # must be odd
MAZE_ROWS = 21                             # must be odd
MAZE_ROOMS = 4                             # extra pillar rooms carved into the maze
MAZE_EXTRA_LOOPS = 24                      # walls removed to create loops
NUM_KEYS = 3
NUM_ENEMIES = 6
NUM_POTIONS = 3
POTION_HEAL = 35

ENEMY_HEALTH = 3
ENEMY_SPEED = 1.5                          # slower than the player's walk speed
ENEMY_RADIUS = 0.25
ENEMY_DAMAGE = 10
ENEMY_ATTACK_RANGE = 0.85
ENEMY_ATTACK_COOLDOWN = 1.1
ENEMY_AGGRO_PATH = 14                      # enemies wake when the player is this many cells away
PICKUP_RADIUS = 0.55

# --------------------------------------------------------------------------
# Colours
# --------------------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (235, 235, 235)
GREY = (150, 150, 150)
FLOOR_COLOR = (74, 64, 54)
CEILING_COLOR = (42, 40, 52)

# (brick colour, mortar colour) for each procedural wall texture
WALL_COLORS = {
    WALL_STONE: ((112, 108, 104), (38, 36, 40)),
    WALL_MOSSY: ((100, 106, 92), (34, 40, 32)),
}

UI_GOLD = (235, 190, 70)
UI_RED = (190, 30, 30)
UI_PANEL = (14, 12, 18)
HEALTH_GOOD = (60, 190, 80)
HEALTH_MID = (225, 180, 50)
HEALTH_LOW = (200, 40, 40)

# Minimap
MINIMAP_CELL = 6
MINIMAP_MARGIN = 14
MINIMAP_WALL = (110, 104, 100)
MINIMAP_DOOR_LOCKED = (190, 50, 40)
MINIMAP_DOOR_OPEN = (70, 220, 110)
MINIMAP_PLAYER = (80, 220, 255)
MINIMAP_KEY = (255, 215, 60)
MINIMAP_ENEMY = (230, 50, 50)
MINIMAP_POTION = (230, 90, 140)

"""
raycasting.py
-------------
A DDA (digital differential analyser) raycaster.

For every vertical screen column one ray is cast through the map grid.  The
result for each ray is a tuple:

    (depth, height, tile, offset, side)

    depth   perpendicular distance to the wall (fish-eye corrected)
    height  projected wall height in pixels
    tile    wall type id found (1 stone, 2 mossy, 3 door, 4 light)
    offset  0..1 position along the wall face (used to pick a texture column)
    side    0 if an east/west face was hit, 1 for a north/south face
"""
import math

from settings import *


class RayCaster:
    def __init__(self, game_map):
        self.map = game_map
        self.hits = [None] * NUM_RAYS           # per-ray results, refreshed each frame
        self.depths = [MAX_DEPTH] * NUM_RAYS    # depth buffer (also used for sprite clipping)

        # Pre-compute, for each column, the angle between the ray and the view
        # direction.  Using atan() on the pixel offset gives an exact planar
        # projection; cos() of that angle is the fish-eye correction factor.
        self.ray_offsets = []
        self.fisheye = []
        for i in range(NUM_RAYS):
            pixel_x = i * SCALE + SCALE / 2 - HALF_WIDTH
            offset = math.atan(pixel_x / SCREEN_DIST)
            self.ray_offsets.append(offset)
            self.fisheye.append(math.cos(offset))

    def cast(self, px, py, view_angle):
        """Cast every ray for the current camera position and angle."""
        for i in range(NUM_RAYS):
            depth, tile, offset, side = self.cast_ray(px, py, view_angle + self.ray_offsets[i])
            depth *= self.fisheye[i]            # remove fish-eye distortion
            depth = max(depth, 0.01)
            height = SCREEN_DIST / depth        # a wall is exactly 1 unit tall
            self.hits[i] = (depth, height, tile, offset, side)
            self.depths[i] = depth

    def cast_ray(self, ox, oy, angle):
        """
        Walk a single ray cell-by-cell through the grid (DDA) until it hits a wall.
        Returns (euclidean_distance, tile_id, texture_offset, side).
        """
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        if abs(sin_a) < 1e-9:                   # avoid division by zero
            sin_a = 1e-9
        if abs(cos_a) < 1e-9:
            cos_a = 1e-9

        grid = self.map.grid
        cols, rows = self.map.cols, self.map.rows
        door_open = self.map.exit_open

        map_x, map_y = int(ox), int(oy)
        delta_x = abs(1.0 / cos_a)              # ray length between two vertical grid lines
        delta_y = abs(1.0 / sin_a)              # ray length between two horizontal grid lines
        if cos_a > 0:
            step_x, side_x = 1, (map_x + 1.0 - ox) * delta_x
        else:
            step_x, side_x = -1, (ox - map_x) * delta_x
        if sin_a > 0:
            step_y, side_y = 1, (map_y + 1.0 - oy) * delta_y
        else:
            step_y, side_y = -1, (oy - map_y) * delta_y

        tile, side, dist = EMPTY, 0, 0.0
        while True:
            if side_x < side_y:                 # next boundary crossed is a vertical line
                dist = side_x
                side_x += delta_x
                map_x += step_x
                side = 0
            else:                               # next boundary crossed is a horizontal line
                dist = side_y
                side_y += delta_y
                map_y += step_y
                side = 1

            if dist > MAX_DEPTH:                # nothing within view distance
                return MAX_DEPTH, WALL_STONE, 0.5, side

            if map_x < 0 or map_y < 0 or map_x >= cols or map_y >= rows:
                tile = WALL_LIGHT               # ray left the map through the opened exit
                break

            tile = grid[map_y][map_x]
            if tile != EMPTY and not (tile == WALL_DOOR and door_open):
                break

        # Where along the wall face did the ray land? (0..1 texture coordinate)
        if side == 0:
            hit = oy + sin_a * dist
            offset = (hit - math.floor(hit)) if cos_a > 0 else 1.0 - (hit - math.floor(hit))
        else:
            hit = ox + cos_a * dist
            offset = 1.0 - (hit - math.floor(hit)) if sin_a > 0 else (hit - math.floor(hit))
        return dist, tile, offset, side

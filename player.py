"""
player.py
---------
The first-person player: movement (WASD + sprint), camera rotation
(arrow keys and mouse), wall collision, health, keys and a melee attack.

Coordinates: x grows to the right, y grows downwards (like the grid rows).
angle = 0 faces +x; a positive angle turns clockwise as seen on the minimap.
"""
import math

import pygame

from settings import *


class Player:
    def __init__(self, game_map):
        self.map = game_map
        self.reset()

    def reset(self):
        """Put the player back at the dungeon entrance with full health."""
        self.x, self.y = self.map.start_pos
        self.angle = self.map.start_angle
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.health = float(PLAYER_MAX_HEALTH)
        self.keys = 0
        self.kills = 0
        self.bob_phase = 0.0
        self.bob = 0.0                  # vertical head-bob offset in pixels
        self.damage_flash = 0.0         # 1.0 right after being hit, fades to 0
        self.attack_timer = 0.0

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    @property
    def is_alive(self):
        return self.health > 0

    @property
    def swing_progress(self):
        """0..1 while the sword swing animation plays, otherwise None."""
        elapsed = ATTACK_COOLDOWN - self.attack_timer
        if self.attack_timer > 0 and elapsed < ATTACK_SWING_TIME:
            return elapsed / ATTACK_SWING_TIME
        return None

    def take_damage(self, amount):
        self.health = max(0.0, self.health - amount)
        self.damage_flash = 1.0

    def heal(self, amount):
        self.health = min(float(PLAYER_MAX_HEALTH), self.health + amount)

    # ------------------------------------------------------------------
    # Input / combat
    # ------------------------------------------------------------------
    def handle_event(self, event, enemies):
        """SPACE or left mouse button swings the sword."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.try_attack(enemies)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.try_attack(enemies)

    def try_attack(self, enemies):
        """Hit every enemy that is close, in front of us and not behind a wall."""
        if self.attack_timer > 0:
            return 0
        self.attack_timer = ATTACK_COOLDOWN
        hits = 0
        for enemy in enemies:
            dx, dy = enemy.x - self.x, enemy.y - self.y
            if math.hypot(dx, dy) > ATTACK_RANGE:
                continue
            diff = (math.atan2(dy, dx) - self.angle + math.pi) % math.tau - math.pi
            if abs(diff) > ATTACK_ARC:
                continue
            if not self.map.has_line_of_sight(self.x, self.y, enemy.x, enemy.y):
                continue
            enemy.take_damage(ATTACK_DAMAGE, self.x, self.y, self.map)
            hits += 1
            if not enemy.alive:
                self.kills += 1
        return hits

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------
    def update(self, dt):
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.damage_flash = max(0.0, self.damage_flash - dt * 2.0)
        keys = pygame.key.get_pressed()
        self._rotate(keys, dt)
        self._move(keys, dt)

    def _rotate(self, keys, dt):
        """Arrow keys and the mouse both turn the camera."""
        turn = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        self.angle += turn * PLAYER_ROT_SPEED * dt

        mouse_dx, _ = pygame.mouse.get_rel()
        mouse_dx = max(-MOUSE_MAX_REL, min(MOUSE_MAX_REL, mouse_dx))
        self.angle += mouse_dx * MOUSE_SENSITIVITY
        self.angle %= math.tau

    def _move(self, keys, dt):
        """WASD movement with sprint, velocity smoothing and sliding collision."""
        forward = int(keys[pygame.K_w]) - int(keys[pygame.K_s])
        strafe = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = PLAYER_SPEED * (SPRINT_MULTIPLIER if sprinting else 1.0)

        sin_a, cos_a = math.sin(self.angle), math.cos(self.angle)
        wish_x = cos_a * forward - sin_a * strafe       # forward = (cos, sin), right = (-sin, cos)
        wish_y = sin_a * forward + cos_a * strafe
        length = math.hypot(wish_x, wish_y)
        if length > 0:                                  # no faster diagonal movement
            wish_x /= length
            wish_y /= length

        # Smooth acceleration/deceleration (frame-rate independent exponential blend).
        blend = 1.0 - math.exp(-PLAYER_ACCEL * dt)
        self.vel_x += (wish_x * speed - self.vel_x) * blend
        self.vel_y += (wish_y * speed - self.vel_y) * blend

        # Move one axis at a time so we slide along walls instead of sticking.
        new_x = self.x + self.vel_x * dt
        if not self.map.collides(new_x, self.y, PLAYER_RADIUS):
            self.x = new_x
        new_y = self.y + self.vel_y * dt
        if not self.map.collides(self.x, new_y, PLAYER_RADIUS):
            self.y = new_y

        # Head bob grows with speed.
        moved = math.hypot(self.vel_x, self.vel_y)
        self.bob_phase += moved * dt * BOB_FREQUENCY
        self.bob = math.sin(self.bob_phase) * BOB_AMPLITUDE * min(1.0, moved / PLAYER_SPEED)

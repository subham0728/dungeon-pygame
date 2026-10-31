"""
main.py
-------
Entry point.  Creates the window, owns the game loop and connects the other
modules together:

    Map          (map.py)             dungeon grid, keys, potions, enemies
    Player       (player.py)          input, movement, collision, health
    RayCaster    (raycasting.py)      casts the rays for the 3D view
    ObjectRenderer (object_renderer.py) draws the scene, HUD and end screens
"""
import math
import sys

import pygame

from settings import *
from map import Map
from player import Player
from raycasting import RayCaster
from object_renderer import ObjectRenderer


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(RES)
        pygame.display.set_caption(TITLE)
        pygame.mouse.set_visible(False)         # mouse look: hide and capture the cursor
        pygame.event.set_grab(True)
        self.clock = pygame.time.Clock()

        self.map = Map()
        self.player = Player(self.map)
        self.raycaster = RayCaster(self.map)
        self.renderer = ObjectRenderer(self.screen, self.map)

        self.running = True
        self.new_game(regenerate=False)

    # ------------------------------------------------------------------
    # Game state
    # ------------------------------------------------------------------
    def new_game(self, regenerate=True):
        """Start (or restart) a run, optionally in a freshly generated dungeon."""
        if regenerate:
            self.map.generate()
        self.player.reset()
        self.renderer.build_minimap()
        self.state = "playing"                  # "playing" | "victory" | "game_over"
        self.elapsed = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.hint_cooldown = 0.0
        self.show_message(f"Find all {self.map.total_keys} keys, then escape through the door!", 5.0)
        pygame.mouse.get_rel()                  # discard mouse movement from before the restart

    def show_message(self, text, seconds=3.0):
        self.message = text
        self.message_timer = seconds

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if event.key == pygame.K_r or self.state != "playing":
                        self.new_game()
                        continue
                elif event.key == pygame.K_m:
                    self.renderer.show_minimap = not self.renderer.show_minimap
            if self.state == "playing":
                self.player.handle_event(event, self.map.enemies)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt):
        if self.state != "playing":
            return
        self.elapsed += dt
        self.message_timer = max(0.0, self.message_timer - dt)
        self.hint_cooldown = max(0.0, self.hint_cooldown - dt)
        if self.message_timer == 0.0:
            self.message = ""

        self.player.update(dt)
        self.map.update_flow_field(self.player.x, self.player.y)
        for enemy in self.map.enemies:
            enemy.update(dt, self.map, self.player)
        self.map.enemies = [e for e in self.map.enemies if e.alive]

        self.check_pickups()
        self.check_exit()
        if not self.player.is_alive:
            self.state = "game_over"

    def check_pickups(self):
        for pickup in self.map.pickups:
            if pickup.collected:
                continue
            if math.hypot(pickup.x - self.player.x, pickup.y - self.player.y) > PICKUP_RADIUS:
                continue
            if pickup.kind == "key":
                pickup.collected = True
                self.player.keys += 1
                self.show_message(f"Key collected ({self.player.keys}/{self.map.total_keys})", 2.5)
                if self.player.keys >= self.map.total_keys:
                    self.map.unlock_exit()
                    self.renderer.build_minimap()       # door turns green on the minimap
                    self.show_message("All keys found! The exit door is open!", 4.0)
            elif pickup.kind == "potion" and self.player.health < PLAYER_MAX_HEALTH:
                pickup.collected = True
                self.player.heal(POTION_HEAL)
                self.show_message("Health potion restored your strength", 2.5)
        self.map.pickups = [p for p in self.map.pickups if not p.collected]

    def check_exit(self):
        if self.map.reached_exit(self.player.x, self.player.y):
            self.state = "victory"
            return
        # Friendly hint when bumping into the locked door.
        if not self.map.exit_open and self.hint_cooldown == 0.0:
            door_x, door_y = self.map.door[0] + 0.5, self.map.door[1] + 0.5
            if math.hypot(door_x - self.player.x, door_y - self.player.y) < 2.0:
                missing = self.map.total_keys - self.player.keys
                self.show_message(f"The door is locked - {missing} key(s) missing", 2.5)
                self.hint_cooldown = 4.0

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, time_s):
        self.raycaster.cast(self.player.x, self.player.y, self.player.angle)
        entities = [p for p in self.map.pickups if not p.collected] + self.map.enemies
        self.renderer.render_scene(self.player, self.raycaster.hits, self.raycaster.depths,
                                   entities, time_s)
        self.renderer.draw_hud(self.player, self.map, self.clock.get_fps(), self.message,
                               show_help=self.elapsed < 10.0)
        if self.state != "playing":
            self.renderer.draw_end_screen(self.state == "victory", {
                "time": self.elapsed, "kills": self.player.kills,
                "keys": self.player.keys, "total_keys": self.map.total_keys,
            })
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)   # cap dt so lag spikes don't teleport us
            self.handle_events()
            self.update(dt)
            self.draw(pygame.time.get_ticks() / 1000.0)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()

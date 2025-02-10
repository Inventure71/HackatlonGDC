import math
import os
import time
import pygame
from advanced_UI import game_UI
from components.world_gen import spawn_objects


# TODO: add controls for multiple players
# TODO: add dummy bots so that they can train models

class GameMusic:
    def __init__(self):
        pygame.mixer.init()

        self.current_track = None
        self.volume = 100

        # Define music tracks
        self.tracks = {
            'menu': os.path.join('components', 'music', 'Duran Duran - INVISIBLE.mp3'),
            'battle': os.path.join('components', 'music', 'Duran Duran - INVISIBLE.mp3'),
            'victory': os.path.join('components', 'music', 'Duran Duran - INVISIBLE.mp3'),
            'game_over': os.path.join('components', 'music', 'Duran Duran - INVISIBLE.mp3')
        }

        self.loaded_tracks = {}
        for key, filename in self.tracks.items():
            if os.path.exists(filename):
                try:
                    pygame.mixer.music.load(filename)
                    self.loaded_tracks[key] = filename
                    print(f"Loaded track: {filename}")
                except Exception as e:
                    print(f"Warning: Could not load music track {filename}. Error: {e}")
            else:
                print(f"Warning: File {filename} does not exist.")

    def play_track(self, track_name, loop=True):
        if track_name not in self.loaded_tracks:
            print(f"Track {track_name} not loaded.")
            return

        if self.current_track != track_name:
            pygame.mixer.music.load(self.loaded_tracks[track_name])
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1 if loop else 0)
            # Add these debug lines
            print("\nPlayback status:")
            print("Current volume:", pygame.mixer.music.get_volume())
            print("Music busy:", pygame.mixer.music.get_busy())
            self.current_track = track_name
            print(f"Now playing: {track_name}")

class Env:
    def __init__(self, training=False, use_game_ui=True, world_width=1280, world_height=1280, display_width=640,
                 display_height=640, n_of_obstacles=10):
        pygame.init()
        self.music = GameMusic()
        self.music.play_track('menu')


        self.training_mode = training

            # ONLY FOR DISPLAY
        # Create display window with desired display dimensions
        self.display_width = display_width
        self.display_height = display_height
        # Only create a window if not in training mode
        if not self.training_mode:
            self.screen = pygame.display.set_mode((display_width, display_height))
        else:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Disable actual video output
            pygame.display.set_mode((1, 1))  # Minimal display

            self.screen = pygame.Surface((display_width, display_height))

        # REAL WORLD DIMENSIONS
        # Create an off-screen surface for the game world
        self.world_width = world_width
        self.world_height = world_height
        self.world_surface = pygame.Surface((world_width, world_height))

        self.clock = pygame.time.Clock()
        self.running = True

        self.use_advanced_UI = use_game_ui
        if self.use_advanced_UI:
            self.advanced_UI = game_UI(self.world_surface, self.world_width, self.world_height)

        if not self.training_mode and self.use_advanced_UI:
            self.advanced_UI.display_opening_screen()

        self.n_of_obstacles = n_of_obstacles
        self.min_obstacle_size = (50, 50)
        self.max_obstacle_size = (100, 100)

        # INIT SOME VARIABLES
        self.OG_bots = None
        self.OG_players = None
        self.OG_obstacles = None

        self.bots = None
        self.players = None
        self.obstacles = None

        """REWARD VARIABLES"""
        self.last_positions = {}
        self.last_damage = {}
        self.last_kills = {}
        self.last_health = {}
        self.visited_areas = {}

        self.visited_areas.clear()
        self.last_positions.clear()
        self.last_health.clear()
        self.last_kills.clear()
        self.last_damage.clear()

        self.steps = 0

    def set_players_bots_objects(self, players, bots, obstacles=None):
        self.OG_players = players
        self.OG_bots = bots
        self.OG_obstacles = obstacles

        self.reset()

    def get_world_bounds(self):
        return (0, 0, self.world_width, self.world_height)

    def reset(self, randomize_objects=False, randomize_players=False):
        self.running = True
        if not self.training_mode:
            if not self.use_advanced_UI:
                self.screen.fill("green")
                pygame.display.flip()
                time.sleep(1)
            else:
                self.advanced_UI.display_background(1)

        else:
            # In training mode, you might simply clear the screen without delay.
            self.screen.fill("green")

        self.last_positions = {}
        self.last_damage = {}
        self.last_kills = {}
        self.last_health = {}
        self.visited_areas = {}

        """
        self.visited_areas.clear()
        self.last_positions.clear()
        self.last_health.clear()
        self.last_kills.clear()
        self.last_damage.clear()"""

        self.steps = 0

        # TODO: add variables for parameters
        if self.use_advanced_UI:
            # Use the obstacles from game_UI
            self.obstacles = self.advanced_UI.obstacles
        else:
            # Create new obstacles only if needed
            if randomize_objects or self.OG_obstacles is None:
                self.OG_obstacles = spawn_objects(
                    (0, 0, self.world_width, self.world_height),
                    self.max_obstacle_size,
                    self.min_obstacle_size,
                    self.n_of_obstacles
                )
            self.obstacles = self.OG_obstacles

        self.players = self.OG_players.copy()
        self.bots = self.OG_bots
        if randomize_players:
            self.bots = self.bots.shuffle()
            for index in range(len(self.players)):
                self.players[index].related_bot = self.bots[index]  # ensuring bots change location

        else:
            for index in range(len(self.players)):
                self.players[index].related_bot = self.bots[index]

        for player in self.players:
            player.reset()
            temp = self.players.copy()
            temp.remove(player)
            player.players = temp  # Other players
            player.objects = self.obstacles

    def step(self, debugging=False):
        if not self.training_mode:
            if self.use_advanced_UI:
                # Use the background from game_UI
                self.world_surface.blit(self.advanced_UI.background, (0, 0))
            else:
                self.world_surface.fill("purple")

        self.steps += 1

        players_info = {}
        alive_players = []

        for player in self.players:
            if player.alive:

                alive_players.append(player)
                player.reload()

                # Only draw if not in training mode.
                if not self.training_mode:
                    player.draw(self.world_surface)

                actions = player.related_bot.act(player.get_info())
                if debugging:
                    print("Bot would like to do:", actions)
                if actions["forward"]:
                    player.move_in_direction("forward")
                if actions["right"]:
                    player.move_in_direction("right")
                if actions["down"]:
                    player.move_in_direction("down")
                if actions["left"]:
                    player.move_in_direction("left")
                if actions["rotate"]:
                    player.add_rotate(actions["rotate"])
                if actions["shoot"]:
                    player.shoot()

                if not self.training_mode:
                    # Store position for trail
                    if not hasattr(player, 'previous_positions'):
                        player.previous_positions = []
                    player.previous_positions.append(player.rect.center)
                    if len(player.previous_positions) > 10:
                        player.previous_positions.pop(0)

            players_info[player.username] = player.get_info()

        new_dic = {
            "general_info": {
                "total_players": len(self.players),
                "alive_players": len(alive_players)
            },
            "players_info": players_info
        }

        if len(alive_players) == 1:
            print("Game Over, winner is:", alive_players[0].username)
            if not self.training_mode:
                if self.use_advanced_UI:
                    self.advanced_UI.display_winner_screen(alive_players)
                else:
                    self.screen.fill("green")

            # self.running = False
            return True, new_dic  # Game is over

        if self.use_advanced_UI:
            self.advanced_UI.draw_everything(new_dic, self.players, self.obstacles)
        elif not self.training_mode:
            # Draw obstacles manually if not using advanced UI
            for obstacle in self.obstacles:
                obstacle.draw(self.world_surface)

        if not self.training_mode:
            scaled_surface = pygame.transform.scale(self.world_surface, (self.display_width, self.display_height))
            self.screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

        # In training mode, you might not call tick or you can use a high tick rate.
        if not self.training_mode:
            self.clock.tick(120)
        else:
            self.clock.tick(10000000)  # Use a high FPS limit in training mode.

        return False, new_dic

    """TO MODIFY"""
    def calculate_reward_empty(self, info_dictionary, bot_username):
        """THIS FUNCTION IS USED TO CALCULATE THE REWARD FOR A BOT"""
        """NEEDS TO BE WRITTEN BY YOU TO FINE TUNE YOURS"""

        # retrieve the players' information from the dictionary
        players_info = info_dictionary.get("players_info", {})
        bot_info = players_info.get(bot_username)

        # if the bot is not found, return a default reward of 0
        if bot_info is None:
            print("Bot not found in the dictionary")
            return 0

        # Extract variables from the bot's info
        location = bot_info.get("location", [0, 0])
        rotation = bot_info.get("rotation", 0)
        rays = bot_info.get("rays", [])
        current_ammo = bot_info.get("current_ammo", 0)
        alive = bot_info.get("alive", False)
        kills = bot_info.get("kills", 0)
        damage_dealt = bot_info.get("damage_dealt", 0)
        meters_moved = bot_info.get("meters_moved", 0)
        total_rotation = bot_info.get("total_rotation", 0)
        health = bot_info.get("health", 0)

        # Calculate reward:
        reward = 0
        # Add your reward calculation here

        return reward

    def calculate_reward(self, info_dictionary, bot_username):
        """
        Reward function for training bots.
        Reward components (one-time per step):
          1. Walking: if the bot moves, +1 (only if it moved this step).
          2. Exploring: if the bot enters a new grid cell (e.g., 100x100), +5.
          3. Damage: reward the damage inflicted this frame.
          4. Kill: reward massively for new kills (+20 per kill).
          5. Negative reward for missing: if a shot was fired and no damage was dealt, -1.
          6. Negative reward if hit by enemy: if health decreases compared to last step, negative penalty.
          7. Negative reward for staying near the borders: if within 50 pixels of any border, -1.

        Additionally, all rewards are scaled by a time-based multiplier that decays over the episode.
        """
        players_info = info_dictionary.get("players_info", {})
        bot_info = players_info.get(bot_username)
        if bot_info is None:
            print(f"Bot {bot_username} not found in info dictionary.")
            return 0

        # Extract current values
        current_position = bot_info.get("location", [0, 0])
        damage_dealt = bot_info.get("damage_dealt", 0)
        kills = bot_info.get("kills", 0)
        alive = bot_info.get("alive", False)
        health = bot_info.get("health", 100)
        # Expect a flag indicating if a shot was fired this frame
        shot_fired = bot_info.get("shot_fired", False)

        # Initialize tracking dictionaries if necessary
        if bot_username not in self.last_positions:
            self.last_positions[bot_username] = current_position
        if bot_username not in self.last_damage:
            self.last_damage[bot_username] = damage_dealt
        if bot_username not in self.last_kills:
            self.last_kills[bot_username] = kills
        if bot_username not in self.last_health:
            self.last_health[bot_username] = health
        if bot_username not in self.visited_areas:
            self.visited_areas[bot_username] = set()

        reward = 0

        # 1. Walking reward (one-time): if moved at all, +1
        distance_moved = math.dist(current_position, self.last_positions[bot_username])
        if distance_moved > 0:
            reward += 0.01

        # 2. Exploration reward (one-time): if entering a new grid cell, +1
        grid_size = 100  # Adjust as needed.
        cell = (int(current_position[0] // grid_size), int(current_position[1] // grid_size))
        if cell not in self.visited_areas[bot_username]:
            reward += 0.1
            self.visited_areas[bot_username].add(cell)

        # 3. Damage reward: reward the damage inflicted this frame.
        delta_damage = damage_dealt - self.last_damage[bot_username]
        if delta_damage > 0:
            reward += delta_damage * 2  # 2 point per damage unit

        # 4. Kill reward: massive reward for new kills.
        delta_kills = kills - self.last_kills[bot_username]
        if delta_kills > 0:
            reward += delta_kills * 15  # 15 points per kill

        # 5. Negative reward for missing: if a shot was fired and no damage occurred.
        if shot_fired and delta_damage <= 0:
            reward -= 1

        # 6. Negative reward if hit by enemy: if health decreased.
        delta_health = self.last_health[bot_username] - health
        if delta_health > 0:
            reward -= delta_health * 0.2  # Adjust penalty factor as needed

        # 7. Negative reward for staying near the borders.
        border_threshold = 50
        near_border = (
                current_position[0] < border_threshold or
                current_position[0] > self.world_width - border_threshold or
                current_position[1] < border_threshold or
                current_position[1] > self.world_height - border_threshold
        )
        if near_border:
            reward -= 1

        # Update tracking values for next step.
        self.last_positions[bot_username] = current_position
        self.last_damage[bot_username] = damage_dealt
        self.last_kills[bot_username] = kills
        self.last_health[bot_username] = health

        decay_rate = 0.0001  # Determines how fast the multiplier decays per step.
        time_multiplier = max(0.2, 1 - decay_rate * self.steps)
        reward *= time_multiplier

        return reward
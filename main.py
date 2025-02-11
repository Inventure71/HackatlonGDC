import time

import pygame

from Environment import Env
from components.my_bot import MyBot
from components.character import Character

screen = pygame.display.set_mode((800, 800))

def main():
    # Environment parameters.
    world_width = 1280
    world_height = 1280
    display_width = 800
    display_height = 800
    n_of_obstacles = 25

    load_back = True
    state_size = 34

    # Create the environment.
    env = Env(training=True,
              use_game_ui=False,
              world_width=world_width,
              world_height=world_height,
              display_width=display_width,
              display_height=display_height,
              n_of_obstacles=n_of_obstacles)
    screen = env.world_surface
    world_bounds = env.get_world_bounds()

    # Setup two players (characters) with starting positions.
    # The players will be stuck if closer than 5 pixels to the border.
    players = [
        Character((world_bounds[2] - 100, world_bounds[3] - 100),
                  screen, boundaries=world_bounds, username="Ninja"),
        Character((world_bounds[0] + 10, world_bounds[1]+10),
                  screen, boundaries=world_bounds, username="Faze Jarvis")
    ]

    # Define the state size based on the info returned by get_info().
    # In this example, we assume:
    #   - location: 2 values
    #   - rotation: 1 value
    #   - current_ammo: 1 value
    #   - rays: 8 values (adjust as needed)
    # Total state size = 2 + 1 + 1 + 8 = 12


    bots = [MyBot(), MyBot()]

    if load_back:
        for idx, bot in enumerate(bots):
            save_path = f"bot_model_{idx}.pth"
            try:
                bot.load(save_path)
                print(f"Load model for player {players[idx].username} from {save_path}")
            except:
                print(f"Failed to load model for player {players[idx].username} from {save_path}")

    # Link players, bots, and obstacles into the environment.
    env.set_players_bots_objects(players, bots)

    # Training / Game parameters.
    time_limit = 10  # seconds per episode
    num_epochs = 100  # number of episodes

    for epoch in range(num_epochs):
        print(f"Starting epoch {epoch + 1}")
        env.reset(randomize_objects=True)
        start_time = time.time()

        while True:
            # If the time limit for this episode has been reached, break.
            if time.time() - start_time > time_limit:
                print("Time limit reached for this episode.")
                break

            # Take a step in the environment.
            # The environment calls each player's .act() method, which in turn uses the bot.
            finished, info = env.step(debugging=False)


            # THIS MAKES ME LOSE 20 FPS
            # For each player, calculate reward, update bot memory, and train the bot.
            for player, bot in zip(players, bots):
                # Calculate the reward for the current step (adjust calculate_reward as needed).
                reward = env.calculate_reward(info, player.username)
                # Retrieve the updated state for the player.
                next_info = player.get_info()
                # Store the transition (last state, action, reward, next state, done).
                bot.remember(reward, next_info, finished)

                # Train the bot from experience.
                #bot.replay()

                #print(f"Reward for {player.username}: {reward}")

            # If the game/episode is over, break out of the loop.
            if finished:
                print("Episode finished, took {:.3f} seconds.".format(time.time() - start_time))
                for _ in range(10):
                    for player, bot in zip(players, bots):
                        bot.replay()

                print("Training finished.")
                break

        # Optionally, save the model weights after each epoch.
        for idx, bot in enumerate(bots):
            save_path = f"bot_model_{idx}.pth"
            bot.save(save_path)
            print(f"Saved model for player {players[idx].username} to {save_path}")

    pygame.quit()

if __name__ == "__main__":
    main()
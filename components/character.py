import time
import pygame
from components.utils import find_hit_point_on_rectangle, distance_between_points

class Character:
    def __init__(self, starting_pos, screen, speed=5, boundaries=None, objects=None, username=None):
        self.rotation = 0
        self.max_boundaries = boundaries
        self.objects = objects if objects is not None else []
        self.starting_pos = starting_pos
        self.rect = pygame.Rect(starting_pos, (40, 40))

        self.related_bot = None

        """CHARACTER STATS"""
        self.username = "player {}".format(id(self)) if username is None else username # add way to personalize
        self.collision_w_objects = True # turn off if you want to move through objects
        self.health = 100
        self.speed = speed
        self.distance_vision = 1500
        self.damage = 20
        self.delay = 0.0 #(between shoots), a lot of time so it is longer but more intense
        self.max_ammo = 30
        self.current_ammo = self.max_ammo
        self.time_to_reload = 0
        self.alive = True
        self.is_reloading = False
        self.rays = []

        # Useful to train
        self.total_kills = 0
        self.damage_dealt = 0
        self.meters_moved = 0
        self.total_rotation = 0

        """TIMERS"""
        self.start_reloading_time = None
        self.last_shoot_time = None

        self.screen = screen
        self.players = []

    "<<<<FOR USERS START>>>>"
    """GETTERS"""
    def get_info(self):
        # returns a dictionary with the following keys: "location", "rotation", "rays" and "current_ammo"
        return {
            "location": self.get_location(),
            "rotation": self.get_rotation(),
            "rays": self.get_rays(),
            "current_ammo": self.current_ammo,
            "alive": self.alive,
            "health": self.health,
            "kills": self.total_kills,
            "damage_dealt": self.damage_dealt,
            "meters_moved": self.meters_moved,
            "total_rotation": self.total_rotation
        }

    def get_location(self):
        # returns the position of the character in (x, y) format
        return self.get_center()

    def get_rotation(self):
        # returns the rotation of the character in degrees
        return self.rotation

    def get_rays(self):
        # returns a list of rays, each represented by a tuple of the form ((start_x, start_y), (end_x, end_y), distance, hit_type)
        # distance is None if no intersection, hit_type is "object" or "player" if intersection
        # to get the values:
        """
        for ray in character.get_rays():
            vector = ray[0]
            distance = ray[1]
            hit_type = ray[2]
        """
        self.rays = self.create_rays()
        return self.rays

    """SETTERS"""

    def move_in_direction(self, direction):
        original_pos = self.rect.topleft
        move_x = 0
        move_y = 0

        # Determine movement vector based on direction
        if direction == "forward":
            move_y = -self.speed
        elif direction == "right":
            move_x = self.speed
        elif direction == "down":
            move_y = self.speed
        elif direction == "left":
            move_x = -self.speed

        # Try moving in both x and y directions independently
        new_x = self.rect.x + move_x
        new_y = self.rect.y + move_y

        # Create temporary rects for testing each axis independently
        temp_rect_x = self.rect.copy()
        temp_rect_x.x = new_x

        temp_rect_y = self.rect.copy()
        temp_rect_y.y = new_y

        # Check x-axis movement
        can_move_x = True
        if self.collision_w_objects:
            for obj in self.objects:
                if temp_rect_x.colliderect(obj.rect):
                    can_move_x = False
                    break

        # Check y-axis movement
        can_move_y = True
        if self.collision_w_objects:
            for obj in self.objects:
                if temp_rect_y.colliderect(obj.rect):
                    can_move_y = False
                    break

        # Check boundaries for x movement
        if not self.check_if_in_boundaries(new_x, self.rect.y):
            can_move_x = False

        # Check boundaries for y movement
        if not self.check_if_in_boundaries(self.rect.x, new_y):
            can_move_y = False

        # Apply the allowed movements
        if can_move_x:
            self.rect.x = new_x
            self.meters_moved += abs(move_x)

        if can_move_y:
            self.rect.y = new_y
            self.meters_moved += abs(move_y)

    def add_rotate(self, degrees):
        self.rotation += degrees
        self.total_rotation += abs(degrees)

    def shoot(self):
        if self.current_ammo > 0:
            if self.last_shoot_time is not None and time.time() - self.last_shoot_time < self.delay:
                print("still on delay")
                return False

            ray  = self.create_rays(num_rays=1, max_angle_view=1, distance=5000, damage=self.damage)[0]
            if ray[2] == "player":
                print("hit player, did damage", self.damage)
                color = "red"
            elif ray[2] == "object":
                color = "yellow"
            else:
                color = "gray"

                pygame.draw.line(self.screen, color, ray[0][0], ray[0][1], 5)
            self.last_shoot_time = time.time()

            self.current_ammo -= 1

            if self.time_to_reload == 0:
                self.current_ammo = self.max_ammo

            else:
                if self.current_ammo <= 0 and self.start_reloading_time is None:
                    self.is_reloading = True
                    print("is reloading", self.current_ammo)
                    self.reload()
                else:
                    print("is reloading (technically)")

        else:
            print("no ammo")

    "<<<<FOR USERS END>>>>"
    """UTILITIES"""
    def reset(self):
        self.rect.x = self.starting_pos[0]
        self.rect.y = self.starting_pos[1]
        self.rotation = 0
        self.health = 100
        self.current_ammo = self.max_ammo
        self.alive = True
        self.is_reloading = False
        self.start_reloading_time = None
        self.last_shoot_time = None
        self.rays = []
        self.total_kills = 0
        self.damage_dealt = 0
        self.meters_moved = 0
        self.total_rotation = 0

    def get_center(self):
        return self.rect.center

    def create_rays(self, num_rays=5, max_angle_view=80, distance=None, damage=0):
        # only works with odd numbers !!!!
        if distance is None:
            distance = self.distance_vision

        hit_distance = None
        rays = []
        for i in range(0, max_angle_view, max_angle_view//num_rays):
            # Reset hit_type for each ray
            hit_type = "none"

            # Middle point is 80/5 * (5-1)//2 --> max_angle_view/num_rays * (num_rays-1)//2
            # Calculate ray endpoint
            direction_vector = pygame.Vector2(0, -distance).rotate(i - max_angle_view/num_rays * (num_rays-1)//2).rotate(self.rotation)
            end_position = self.get_center() + direction_vector
            closest_end_position = (end_position[0], end_position[1])  # Store the closest intersection point

            # Check collision with each object
            for object in self.objects:
                point = find_hit_point_on_rectangle(self.get_center(), end_position, object.rect)
                if point is not None:
                    # Calculate distance to current intersection
                    current_distance = distance_between_points(self.get_center(), point)
                    # Calculate distance to current closest point
                    closest_distance = distance_between_points(self.get_center(), closest_end_position)

                    # Update closest point if this intersection is closer
                    if current_distance < closest_distance:
                        closest_end_position = (point[0], point[1])
                        hit_type = "object"
                        hit_distance = current_distance

            for player in self.players:
                point = find_hit_point_on_rectangle(self.get_center(), end_position, player.rect)
                if point is not None:
                    if damage > 0:
                        res = player.do_damage(damage, self)
                        if res[0]:
                            self.total_kills += 1
                        else:
                            self.damage_dealt += res[1]
                    else:
                        #print("Saw player")
                        None

                    # Calculate distance to current intersection
                    current_distance = distance_between_points(self.get_center(), point)
                    # Calculate distance to current closest point
                    closest_distance = distance_between_points(self.get_center(), closest_end_position)

                    # Update closest point if this intersection is closer
                    if current_distance < closest_distance:
                        closest_end_position = (point[0], point[1])
                        hit_type = "player"
                        hit_distance = current_distance

            # NEW: Check collision with world bounds.
            if self.max_boundaries is not None:
                # Create a rectangle representing the world boundaries.
                world_rect = pygame.Rect(
                    self.max_boundaries[0],
                    self.max_boundaries[1],
                    self.max_boundaries[2] - self.max_boundaries[0],
                    self.max_boundaries[3] - self.max_boundaries[1]
                )
                boundary_point = find_hit_point_on_rectangle(self.get_center(), end_position, world_rect)
                if boundary_point is not None:
                    current_distance = distance_between_points(self.get_center(), boundary_point)
                    closest_distance = distance_between_points(self.get_center(), closest_end_position)
                    if current_distance < closest_distance:
                        closest_end_position = (boundary_point[0], boundary_point[1])
                        # We treat the boundary as an object (or obstacle).
                        hit_type = "object"
                        hit_distance = current_distance

            # Add the ray with its closest intersection point (or original endpoint if no intersection)
            rays.append([(self.get_center(), closest_end_position), hit_distance, hit_type])

        return rays

    def reload(self):
        if self.is_reloading:
            if self.start_reloading_time is None:
                self.start_reloading_time = time.time()
            else:
                if time.time() - self.start_reloading_time >= self.time_to_reload:
                    self.current_ammo = self.max_ammo
                    self.start_reloading_time = None
                    self.is_reloading = False

    """PYGAME"""
    def do_damage(self, damage, by_player=None):
        self.health -= damage
        if self.health <= 0:
            if self.alive:
                self.alive = False
                self.rect.x = -1000
                self.rect.y = -1000
                self.current_ammo = 0
                print("player died, killer was:", by_player.username)
                return True, damage
            else:
                print("player is already dead (IGNORE THIS)")
                return False, 0
        else:
            print("player took damage, current health:", self.health)
            return False, damage

    def check_if_in_boundaries(self, x, y, margin=5):
        if self.max_boundaries is None:
            return True

        # Create a temporary rect to check the new position
        temp_rect = pygame.Rect(x, y, self.rect.width, self.rect.height)

        # Add margin to the boundaries
        boundaries_with_margin = (
            self.max_boundaries[0] + margin,  # left
            self.max_boundaries[1] + margin,  # top
            self.max_boundaries[2] - margin - self.rect.width,  # right (account for rect width)
            self.max_boundaries[3] - margin - self.rect.height  # bottom (account for rect height)
        )

        # Check if the position would be outside the boundaries
        if (x < boundaries_with_margin[0] or
                x > boundaries_with_margin[2] or
                y < boundaries_with_margin[1] or
                y > boundaries_with_margin[3]):
            return False

        return True

    def draw(self, screen):
        # Draw character body
        pygame.draw.rect(screen, "red", self.rect)

        # Draw direction indicator
        direction_vector = pygame.Vector2(0, -40).rotate(self.rotation)
        end_position = self.get_center() + direction_vector
        pygame.draw.line(screen, "blue", self.get_center(), end_position, 5)

        # Draw rays with different colors based on hit type

        for ray in self.rays:
            if ray[2] == "player":
                color = "green"
            elif ray[2] == "object":
                color = "yellow"
            else:
                color = "gray"

            pygame.draw.line(screen, color, ray[0][0], ray[0][1], 5)

        # Draw health and ammo
        font = pygame.font.Font(None, 24)  # Default font with size 24
        health_text = font.render(f"Health: {self.health}", True, pygame.Color("white"))
        ammo_text = font.render(f"Ammo: {self.current_ammo}", True, pygame.Color("white"))

        # Position the text above the character
        text_x, text_y = self.rect.topleft
        screen.blit(health_text, (text_x, text_y - 25))  # Above the character
        screen.blit(ammo_text, (text_x, text_y - 45))  # Even higher above the character

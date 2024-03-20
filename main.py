import pygame
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading
import random
from PIL import Image
import math
import subprocess
import sys

# Constants
FULLSCREEN = False
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
GROUND_HEIGHT = 100
IMAGES_FOLDER = "color_rotated_imgs"
FROG_STATIC = [
    f"{IMAGES_FOLDER}/Frog_Static1.png",
    f"{IMAGES_FOLDER}/Frog_Static2.png",
    f"{IMAGES_FOLDER}/Frog_Static3.png",
    f"{IMAGES_FOLDER}/Frog_Static4.png",
]
FROG_JUMPING = [
    f"{IMAGES_FOLDER}/Frog_Jumping1.png",
    f"{IMAGES_FOLDER}/Frog_Jumping2.png",
]
FROG_FALLING = [
    f"{IMAGES_FOLDER}/Frog_Falling1.png",
]
FROG_LEAPING = [
    f"{IMAGES_FOLDER}/Frog_Leaping1.png",
    f"{IMAGES_FOLDER}/Frog_Leaping2.png",
]
FROG_GRABBING = [
    f"{IMAGES_FOLDER}/Frog_Grabbing1.png",
    f"{IMAGES_FOLDER}/Frog_Grabbing2.png",
]

PLAYER_COLORS = {
    "Green": (0, 255, 0),
    "DarkTeal": (48, 102, 89),
    "DeepBlue": (14, 0, 163),
    "Purple": (197, 0, 227),
    "Pink": (223, 167, 232),
    "Yellow": (255, 255, 0),
}

# Initialize Pygame
pygame.init()

# Set up some variables
if FULLSCREEN:
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

clock = pygame.time.Clock()
players = {}
sprite_id_counter = 0
color_idx = 0
port_string = "Connect with: 10.17.116.127:5000"


class MapComponent(pygame.sprite.Sprite):
    def __init__(self, width, height, color, x, y):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

    def reset_image(self, width, height, color, x, y):
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))


class Player(pygame.sprite.Sprite):
    def __init__(self, sprite_id, color):
        super().__init__()
        self.color = color
        filename, file_extension = os.path.splitext(FROG_STATIC[0])
        self.image = pygame.image.load(
            filename + self.color + file_extension
        ).convert_alpha()
        self.image = pygame.transform.scale(
            self.image,
            (int(self.image.get_width() * 2 / 3), int(self.image.get_height() * 2 / 3)),
        )
        self.rect = self.image.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        self.velocity = pygame.Vector2(0, 0)
        self.gravity = 1.8
        self.friction = 0.1  # Add friction attribute
        self.id = sprite_id
        self.grabbing = False
        self.grabbed = False

        self.animation_counter = 0
        # animation flags
        self.facing_left = False
        self.leaping = False
        self.jumping = False
        self.falling = False
        self.grabbing_animation = False

    def update(self, map_components=[]):
        self.velocity.x *= 1 - self.friction
        self.rect.move_ip(self.velocity.x, self.velocity.y)

        # Vertical collision detection
        falling = True
        for component in map_components:
            if pygame.sprite.collide_rect(self, component):
                # Use linear interpolation to estimate the position of the sprite at the time of collision (before, since we're being lazy, and not using penetration depth)
                # This will allow us to detect the direction of the collision
                old_rect = self.rect.move(-self.velocity.x, -self.velocity.y)

                # If we're above the object, we're probably landing on it.
                if old_rect.bottom <= component.rect.top and self.velocity.y > 0:
                    self.rect.bottom = component.rect.top + 10
                    self.velocity.y = 0
                    falling = False

                # Check if we're resting on the object vertically
                if self.rect.bottom == component.rect.top + 10:
                    falling = False
                    self.falling = False
                    self.jumping = False

                # If we're below the object, we're probably hitting our head.
                if old_rect.top >= component.rect.bottom:
                    self.rect.top = component.rect.bottom
                    self.velocity.y = 0

                # If we're to the left of the object, we probably hit it from the right.
                if old_rect.right <= component.rect.left:
                    self.rect.right = component.rect.left
                    self.velocity.x = 0

                # If we're to the right of the object, we probably hit it from the left.
                if old_rect.left >= component.rect.right:
                    self.rect.left = component.rect.right
                    self.velocity.x = 0

        if falling and not self.grabbed:
            self.velocity.y += self.gravity
            self.falling = True

        if self.grabbing:
            # Check if the sprite is able to grab another player sprite, are they in range?
            for sprite in all_sprites:
                if isinstance(sprite, Player) and sprite.id != self.id:
                    if hasattr(sprite, "grabbed") and sprite.grabbed == self.id:
                        # If the player is grabbing another player, move the grabbed player with the grabbing player
                        sprite.rect.x = self.rect.x
                        sprite.rect.y = self.rect.y - 100

        self.animate()

    def animate(self):
        if self.grabbing_animation:
            idx = min(int((self.animation_counter) / 6), len(FROG_GRABBING) - 1)
            filename, file_extension = os.path.splitext(FROG_GRABBING[idx])
            self.image = pygame.image.load(
                filename + self.color + file_extension
            ).convert_alpha()
            if self.animation_counter > 12:
                self.grabbing_animation = False
        elif self.jumping:
            if self.velocity.y > 0:
                self.jumping = False
                self.falling = True  # True
                self.animation_counter = 0
            idx = min(int((self.animation_counter + 1) / 3), len(FROG_JUMPING) - 1)
            filename, file_extension = os.path.splitext(FROG_JUMPING[idx])
            self.image = pygame.image.load(
                filename + self.color + file_extension
            ).convert_alpha()
        elif self.falling:
            idx = 0
            filename, file_extension = os.path.splitext(FROG_FALLING[idx])
            self.image = pygame.image.load(
                filename + self.color + file_extension
            ).convert_alpha()
        elif self.leaping:
            idx = min(int((self.animation_counter) / 4), len(FROG_LEAPING) - 1)
            filename, file_extension = os.path.splitext(FROG_LEAPING[idx])
            self.image = pygame.image.load(
                filename + self.color + file_extension
            ).convert_alpha()
            if self.animation_counter > 6:
                self.leaping = False
        else:
            idx = int((self.animation_counter + 1) / 5) % len(FROG_STATIC)
            filename, file_extension = os.path.splitext(FROG_STATIC[idx])
            self.image = pygame.image.load(
                filename + self.color + file_extension
            ).convert_alpha()

        if self.facing_left:  # flip the image
            self.image = pygame.transform.flip(self.image, True, False)

        self.image = pygame.transform.scale(
            self.image,
            (int(self.image.get_width() * 2 / 3), int(self.image.get_height() * 2 / 3)),
        )

        self.animation_counter += 1


app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    global color_idx
    sprite_id = request.sid
    color_name, color_rgb = list(PLAYER_COLORS.items())[color_idx]
    color_idx = (color_idx + 1) % len(PLAYER_COLORS)

    new_sprite = Player(sprite_id, color=color_name)
    players[sprite_id] = new_sprite
    all_sprites.add(new_sprite)  # Add the sprite to the all_sprites group
    emit("sprite_created", {"id": sprite_id, "color": f"rgb{color_rgb}"})


@socketio.on("move")
def handle_move(data):
    direction = data["direction"]
    sprite_id = request.sid
    sprite = players.get(sprite_id)

    if sprite:
        if direction == "up":
            # Check if the sprite is on the ground or standing on a map component
            collided_with = pygame.sprite.spritecollideany(sprite, collision_sprites)
            if collided_with and (isinstance(collided_with, MapComponent)):
                sprite.velocity.y = -30
                sprite.jumping = True
                sprite.animation_counter = 0

        if direction == "left":
            sprite.velocity.x = -20
            sprite.facing_left = True
            sprite.leaping = True
            sprite.animation_counter = 0
        elif direction == "right":
            sprite.facing_left = False
            sprite.velocity.x = 20
            sprite.leaping = True
            sprite.animation_counter = 0
        elif direction == "grab":
            if sprite.grabbing:
                sprite.grabbing = False
                for object_sprite in list(players.values()):
                    if object_sprite.grabbed == sprite.id:
                        object_sprite.grabbed = False

            # Check if any sprites are in range, and if so, grab them and mark.
            if not sprite.grabbing:
                sprite.grabbing_animation = True
                sprite.animation_counter = 0
                for object_sprite in list(players.values()):
                    if object_sprite.id != sprite.id:
                        if sprite.facing_left and (
                            sprite.rect.centerx - 180
                            < object_sprite.rect.centerx
                            < sprite.rect.centerx
                            and sprite.rect.centery - 10
                            < object_sprite.rect.centery
                            < sprite.rect.centery + 10
                        ):
                            object_sprite.grabbed = sprite.id
                            sprite.grabbing = True

                        elif (
                            sprite.rect.centerx
                            < object_sprite.rect.centerx
                            < sprite.rect.centerx + 180
                            and sprite.rect.centery - 10
                            < object_sprite.rect.centery
                            < sprite.rect.centery + 10
                        ):
                            object_sprite.grabbed = sprite.id
                            sprite.grabbing = True


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")
    # Assuming each client has a unique sprite_id
    sprite_id = request.sid
    sprite = players.get(sprite_id)

    if sprite:
        all_sprites.remove(sprite)  # Remove the sprite from the all_sprites group
        del players[sprite_id]  # Delete the sprite from the sprites dictionary
        print(f"Sprite {sprite_id} removed")
    else:
        print(f"No sprite found for id {sprite_id}")


# Inside the game loop function:
def game_loop():
    global all_sprites
    global collision_sprites
    global port_string
    global map_components  # Global declaration used for map builder
    global camera_position  # Global declaration used for map builder
    all_sprites = pygame.sprite.Group()
    collision_sprites = pygame.sprite.Group()

    # Tracks our "camera position" to move everything around.
    camera_position = pygame.Vector2(0, 0)

    # Create MapComponents for your level
    map_components = [
        MapComponent(
            WINDOW_WIDTH, GROUND_HEIGHT, (0, 255, 0), 0, WINDOW_HEIGHT - GROUND_HEIGHT
        ),
        MapComponent(200, 20, (255, 0, 0), 300, 500),
        MapComponent(150, 20, (255, 0, 0), 600, 400),
        MapComponent(200, 20, (255, 0, 0), 1200, 700),
        MapComponent(200, 20, (255, 0, 0), 800, 900),
        MapComponent(200, 50, (255, 0, 0), 700, 800),
        MapComponent(200, 50, (255, 0, 0), 600, 700),
        MapComponent(1920, 50, (255, 0, 0), 1000, 0),
        MapComponent(200, 20, (255, 0, 0), 1900.0, 1020.0),
        MapComponent(170, 120, (255, 0, 0), 823.0, 307.0),
        MapComponent(140, 20, (255, 0, 0), 662.0, 154.0),
        MapComponent(120, 20, (255, 0, 0), 1077.0, 787.0),
        MapComponent(130, 60, (255, 0, 0), 1465.0, 557.0),
        MapComponent(170, 40, (255, 0, 0), 1218.0, 427.0),
        MapComponent(160, 20, (255, 0, 0), 1533.0, -173.0),
        MapComponent(160, 30, (255, 0, 0), 1163.0, -186.0),
        MapComponent(170, 30, (255, 0, 0), 1733.0, -316.0),
        MapComponent(170, 30, (255, 0, 0), 1323.0, -436.0),
        MapComponent(170, 60, (255, 0, 0), 993.0, -386.0),
        MapComponent(170, 40, (255, 0, 0), 1064.0, -569.0),
        MapComponent(150, 60, (255, 0, 0), 1966.0, -519.0),
        MapComponent(150, 40, (255, 0, 0), 593.0, -502.0),
        MapComponent(170, 60, (255, 0, 0), 265.0, -595.0),
        MapComponent(200, 20, (255, 0, 0), 215.0, -325.0),
        MapComponent(140, 40, (255, 0, 0), 655.0, -755.0),
        MapComponent(170, 20, (255, 0, 0), 6.0, -718.0),
        MapComponent(170, 50, (255, 0, 0), -284.0, -768.0),
        MapComponent(160, 70, (255, 0, 0), -524.0, -938.0),
        # Add more MapComponents as needed
    ]

    all_sprites.add(map_components)
    collision_sprites.add(map_components)

    background_image = pygame.image.load("imgs/border.png")
    backbackground_image = pygame.image.load("imgs/background.jpg")
    infoObject = pygame.display.Info()
    background_image = pygame.transform.scale(
        background_image, (infoObject.current_w, infoObject.current_h)
    )
    backbackground_image = pygame.transform.scale(
        backbackground_image, (infoObject.current_w * 1.4, infoObject.current_h * 1.4)
    )

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Get all sprite instances for collision detection
        sprites_list = [
            sprite for sprite in all_sprites.sprites() if isinstance(sprite, Player)
        ]

        # Update each sprite individually with the list of map components for collision detection
        for sprite in sprites_list:
            sprite.update(map_components)

        # Kill lowest players if needed
        # We have to find if they all fit vertically, so find the max distance between the highest and lowest player
        current_lowest_player = None
        current_highest_player = None
        for player in players.values():
            if (
                current_lowest_player is None
                or player.rect.bottom > current_lowest_player.rect.bottom
            ):
                current_lowest_player = player
            if (
                current_highest_player is None
                or player.rect.top < current_highest_player.rect.top
            ):
                current_highest_player = player

        if current_lowest_player is not None and current_highest_player is not None:
            if (
                current_lowest_player.rect.bottom - current_highest_player.rect.top
                > WINDOW_HEIGHT
            ):
                # Kill the lowest player
                dead_player_id = None
                for player_id, player_sprite in players.items():
                    if player_sprite == current_lowest_player:
                        dead_player_id = player_id
                        break

                if dead_player_id:
                    # Emit message to the specific player indicating frog death
                    socketio.emit("frog_dead", room=dead_player_id)

                # Perform any other actions for frog death, such as removing the sprite from the game
                all_sprites.remove(current_lowest_player)
                del players[dead_player_id]

        # Get average player coordinates
        player_positions = [sprite.rect.center for sprite in sprites_list]
        if player_positions:
            avg_x = sum([pos[0] for pos in player_positions]) / len(player_positions)
            avg_y = sum([pos[1] for pos in player_positions]) / len(player_positions)
            camera_position = pygame.Vector2(
                avg_x - WINDOW_WIDTH / 2, avg_y - WINDOW_HEIGHT / 2
            )

        screen.blit(backbackground_image, camera_position * -0.1)
        screen.blit(background_image, camera_position * -0.3)

        for sprite in sprites_list:
            if (
                sprite.rect.top > WINDOW_HEIGHT
            ):  # Assuming falling off the screen means death
                # Find the player associated with this sprite
                dead_player_id = None
                for player_id, player_sprite in players.items():
                    if player_sprite == sprite:
                        dead_player_id = player_id
                        break

                if dead_player_id:
                    # Emit message to the specific player indicating frog death
                    socketio.emit("frog_dead", room=dead_player_id)

                # Perform any other actions for frog death, such as removing the sprite from the game
                all_sprites.remove(sprite)
                del players[dead_player_id]

        for sprite in all_sprites:
            screen.blit(
                sprite.image,
                pygame.rect.Rect(
                    sprite.rect.topleft - camera_position, sprite.rect.size
                ),
            )

        font = pygame.font.Font(None, 24)
        text_surface = font.render(port_string, True, (0, 0, 0))
        text_rect = text_surface.get_rect()
        text_rect.bottomright = (
            WINDOW_WIDTH - 10,
            WINDOW_HEIGHT - text_rect.height - 50,
        )
        screen.blit(text_surface, text_rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000  # You can use any port you like, but make sure it's not already in use

    # Start the game loop in a separate thread
    game_thread = threading.Thread(target=game_loop)
    game_thread.start()

    # Start the Flask-SocketIO server
    socketio.run(app, host=host, port=port)

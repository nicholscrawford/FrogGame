import pygame
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading

# Constants
FULLSCREEN = False
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
GROUND_HEIGHT = 100
SPRITE_IMAGE_PATH = "imgs/frog.jpeg"

# Initialize Pygame
pygame.init()

# Set up some variables
if FULLSCREEN:
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

clock = pygame.time.Clock()
sprites = {}
sprite_id_counter = 0


class Ground(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((WINDOW_WIDTH, GROUND_HEIGHT))
        self.image.fill((0, 255, 0))
        self.rect = self.image.get_rect(
            center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT - GROUND_HEIGHT / 2)
        )


class MapComponent(pygame.sprite.Sprite):
    def __init__(self, width, height, color, x, y):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))


class Sprite(pygame.sprite.Sprite):
    def __init__(self, sprite_id):
        super().__init__()
        self.image = pygame.image.load(SPRITE_IMAGE_PATH).convert()
        self.image = pygame.transform.scale(
            self.image, (100, 100)
        )  # Resize to 100x100 pixels
        self.rect = self.image.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        self.velocity = pygame.Vector2(0, 0)
        self.gravity = 1
        self.friction = 0.1  # Add friction attribute
        self.id = sprite_id

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
                    self.rect.bottom = component.rect.top + 1
                    self.velocity.y = 0
                    falling = False

                # Check if we're resting on the object vertically
                if self.rect.bottom == component.rect.top + 1:
                    falling = False

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

        if falling:
            self.velocity.y += self.gravity

        if self.rect.bottom >= WINDOW_HEIGHT - GROUND_HEIGHT + 1:
            self.rect.bottom = WINDOW_HEIGHT - GROUND_HEIGHT + 1
            self.velocity.y = 0


app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    print("Client connected")
    sprite_id = request.sid

    new_sprite = Sprite(sprite_id)
    sprites[sprite_id] = new_sprite
    all_sprites.add(new_sprite)  # Add the sprite to the all_sprites group
    emit("sprite_created", {"id": sprite_id})


@socketio.on("move")
def handle_move(data):
    direction = data["direction"]
    sprite_id = request.sid
    sprite = sprites.get(sprite_id)

    if sprite:
        if direction == "up":
            # Check if the sprite is on the ground or standing on a map component
            collided_with = pygame.sprite.spritecollideany(sprite, collision_sprites)
            if collided_with and (
                isinstance(collided_with, Ground)
                or isinstance(collided_with, MapComponent)
            ):
                sprite.velocity.y = -30

        if direction == "left":
            sprite.velocity.x = -20
        elif direction == "right":
            sprite.velocity.x = 20


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")
    # Assuming each client has a unique sprite_id
    sprite_id = request.sid
    sprite = sprites.get(sprite_id)

    if sprite:
        all_sprites.remove(sprite)  # Remove the sprite from the all_sprites group
        del sprites[sprite_id]  # Delete the sprite from the sprites dictionary
        print(f"Sprite {sprite_id} removed")
    else:
        print(f"No sprite found for id {sprite_id}")


# Inside the game loop function:
def game_loop():
    global all_sprites
    global collision_sprites
    ground = Ground()
    all_sprites = pygame.sprite.Group()
    collision_sprites = pygame.sprite.Group()
    all_sprites.add(ground)
    collision_sprites.add(ground)

    # Create MapComponents for your level
    map_components = [
        MapComponent(200, 20, (255, 0, 0), 300, 500),
        MapComponent(150, 20, (255, 0, 0), 600, 400),
        MapComponent(200, 20, (255, 0, 0), 1200, 700),
        MapComponent(200, 20, (255, 0, 0), 800, 900),
        MapComponent(200, 50, (255, 0, 0), 700, 800),
        MapComponent(200, 50, (255, 0, 0), 600, 700),
        # Add more MapComponents as needed
    ]

    all_sprites.add(map_components)
    collision_sprites.add(map_components)

    background_image = pygame.image.load("imgs/background.jpg")
    infoObject = pygame.display.Info()
    background_image = pygame.transform.scale(
        background_image, (infoObject.current_w, infoObject.current_h)
    )

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Get all sprite instances for collision detection
        sprites_list = [
            sprite for sprite in all_sprites.sprites() if isinstance(sprite, Sprite)
        ]

        # Update each sprite individually with the list of map components for collision detection
        for sprite in sprites_list:
            sprite.update(map_components)

        screen.blit(background_image, (0, 0))

        all_sprites.draw(screen)

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

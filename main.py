import pygame
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading

# Constants
FULLSCREEN = False
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
GROUND_HEIGHT = 50
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


class Sprite(pygame.sprite.Sprite):
    def __init__(self, sprite_id):
        super().__init__()
        self.image = pygame.image.load(SPRITE_IMAGE_PATH).convert()
        self.image = pygame.transform.scale(
            self.image, (100, 100)
        )  # Resize to 100x100 pixels
        self.rect = self.image.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
        self.velocity = pygame.Vector2(0, 0)
        self.gravity = 0.5
        self.friction = 0.1  # Add friction attribute
        self.id = sprite_id

    def update(self):
        self.velocity.y += self.gravity
        self.velocity *= 1 - self.friction  # Apply friction to velocity
        self.rect.move_ip(self.velocity.x, self.velocity.y)

        if self.rect.bottom >= WINDOW_HEIGHT - GROUND_HEIGHT:
            self.rect.bottom = WINDOW_HEIGHT - GROUND_HEIGHT
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
            sprite.velocity.y = -10
        elif direction == "left":
            sprite.velocity.x = -10
        elif direction == "right":
            sprite.velocity.x = 10


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


def game_loop():
    global all_sprites
    ground = Ground()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(ground)

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

        all_sprites.update()

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

import threading
import main

from pynput import keyboard

current_mapcomponent = None
current_mapcomponent_x = None
current_mapcomponent_y = None
current_mapcomponent_color = None
current_mapcomponent_width = None
current_mapcomponent_height = None


def on_press(key):
    global current_mapcomponent
    global current_mapcomponent_x
    global current_mapcomponent_y
    global current_mapcomponent_color
    global current_mapcomponent_width
    global current_mapcomponent_height

    if str(key) == "'n'":
        print(
            f"MapComponent({current_mapcomponent_width}, {current_mapcomponent_height}, {current_mapcomponent_color}, {current_mapcomponent_x}, {current_mapcomponent_y}),"
        )
        if current_mapcomponent is not None:
            current_mapcomponent.reset_image(
                current_mapcomponent_width,
                current_mapcomponent_height,
                (0, 0, 255),
                current_mapcomponent_x,
                current_mapcomponent_y,
            )

        current_mapcomponent_x = main.camera_position.x + main.WINDOW_WIDTH / 2
        current_mapcomponent_y = main.camera_position.y + main.WINDOW_HEIGHT / 2
        current_mapcomponent_color = (255, 0, 0)
        current_mapcomponent_width = 200
        current_mapcomponent_height = 20

        current_mapcomponent = main.MapComponent(
            current_mapcomponent_width,
            current_mapcomponent_height,
            current_mapcomponent_color,
            current_mapcomponent_x,
            current_mapcomponent_y,
        )

        main.map_components.append(current_mapcomponent)
        main.all_sprites.add(current_mapcomponent)
        main.collision_sprites.add(current_mapcomponent)

    if str(key) == "Key.left":
        current_mapcomponent_x -= 10
    if str(key) == "Key.right":
        current_mapcomponent_x += 10
    if str(key) == "Key.up":
        current_mapcomponent_y -= 10
    if str(key) == "Key.down":
        current_mapcomponent_y += 10
    if str(key) == "'w'":
        current_mapcomponent_height -= 10
    if str(key) == "'s'":
        current_mapcomponent_height += 10
    if str(key) == "'a'":
        current_mapcomponent_width -= 10
    if str(key) == "'d'":
        current_mapcomponent_width += 10

    current_mapcomponent.reset_image(
        current_mapcomponent_width,
        current_mapcomponent_height,
        current_mapcomponent_color,
        current_mapcomponent_x,
        current_mapcomponent_y,
    )


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000  # You can use any port you like, but make sure it's not already in use

    # Start the game loop in a separate thread
    game_thread = threading.Thread(target=main.game_loop)
    game_thread.start()

    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    # Start the Flask-SocketIO server
    main.socketio.run(main.app, host=host, port=port)

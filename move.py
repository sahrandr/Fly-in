from pyray import *
from raylib import *

init_window(1200, 1000, 'MOVE TEST')

ship = load_texture('assets/spaceship.png')
ship_pos = Vector2(0,0)

while not window_should_close():
    # uptades
    ship_pos.x += 0.1

    # drawing
    begin_drawing()
    clear_background(BLUE)
    draw_texture_v(ship, ship_pos, WHITE)
    end_drawing()

close_window()
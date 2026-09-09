from pyray import *
from raylib import *

init_window(2000, 1000, 'MOVE TEST')

ship = load_texture('assets/spaceship.png')
pos_x = 0
pos_y = 0

while not window_should_close():
    begin_drawing()
    clear_background(BLUE)
    draw_texture(ship, pos_x, pos_y, WHITE)
    end_drawing()

close_window()
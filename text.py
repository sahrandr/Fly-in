from pyray import *
from pyray import Color
# import pyray
# print(dir(pyray))

C_BG = Color(8, 10, 15, 255)

C_GRID = Color(255, 255, 255, 6)

C_STRUCT = Color(64, 74, 92, 255)

C_PATH = Color(90, 222, 204, 255)

C_DEAD = Color(158, 62, 62, 255)

C_START = Color(96, 230, 130, 255)

C_GOAL = Color(255, 198, 70, 255)

C_EDGE_IDLE = Color(92, 106, 130, 46)

C_EDGE_HOT = Color(90, 222, 204, 70)

ORB_COLORS = [
    Color(255, 150, 120, 255),
    Color(140, 235, 205, 255),
    Color(155, 190, 255, 255),
    Color(255, 214, 130, 255),
    Color(232, 152, 238, 255),
    Color(150, 238, 238, 255),
]

init_window(800, 600, 'TEST')
colors = [
    C_BG, C_GRID, C_STRUCT, C_PATH,
    C_DEAD, C_START, C_GOAL,
    C_EDGE_IDLE, C_EDGE_HOT
] + ORB_COLORS

while not window_should_close():
    begin_drawing()
    clear_background(BLACK)

    for i, color in enumerate(colors):
        draw_rectangle(20 + i * 60, 50, 50, 50, color)

    end_drawing()

close_window()
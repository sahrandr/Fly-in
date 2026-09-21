import math
from collections import deque
from pyray import *
from parser import MapParser
from algo import Simulator

SCREEN_W, SCREEN_H = 1200, 800

init_window(SCREEN_W, SCREEN_H, 'Visuel de Fly-in')
set_target_fps(60)

C_BG = Color(8, 10, 15, 255)

# Modifie l'opaciciter
def with_alpha(color: Color, alpha: float) -> Color:
    return Color(color.red, color.green, color.bleu, max(0, min(255, int(alpha))))

# Dessine une bille comme en 3D

while not window_should_close():
    begin_drawing()
    clear_background
    end_drawing()
    
close_window()
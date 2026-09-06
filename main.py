# 

from pyray import *

init_window(900, 700, "Fly-in Simulation 3D")

camera = Camera3D()
camera.position = Vector3(10.0, 8.0, 10.0)
camera.target = Vector3(0.0, 0.0, 0.0)
camera.up = Vector3(0.0, 1.0, 0.0)
camera.fovy = 45.0
camera.projection = CAMERA_PERSPECTIVE

set_target_fps(60)

while not window_should_close():
    update_camera(camera, CAMERA_ORBITAL)

    begin_drawing()
    clear_background(RAYWHITE)

    begin_mode_3d(camera)
    draw_sphere(Vector3(0, 0, 0), 1.0, GREEN)
    draw_cube(Vector3(2, 0, 0), 4.0, 0.2, 0.2, GRAY)
    draw_grid(10, 1.0)
    end_mode_3d()

    end_drawing()

close_window()
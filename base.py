from pyray import *
from raylib import *
from os.path import join

init_window(1500, 1000, 'FLY-IN TEST 01 RAYLIB')

# import image/text
spaceship_texture = load_texture('spaceship.png')
spaceship_image = load_image('spaceship.png')
image_color_grayscale(spaceship_image)
new_texture = load_texture_from_image(spaceship_image)
cowbow_image = load_image('assets/animation/0.png')
image_color_invert(cowbow_image)
cowbow_texture = load_texture_from_image(cowbow_image)

# import font
font = load_font('assets/Zero Hour.otf')
while not window_should_close():
    begin_drawing()
    clear_background(BLACK)
 
    # custom shape drawing
    draw_pixel(100, 200, RAYWHITE)
    draw_pixel_v(Vector2(101,200), WHITE)
    draw_circle_v(Vector2(500,600), 200, RED)
    draw_circle(500, 600, 100,PINK)
    draw_line_ex(Vector2(50,700), Vector2(200,200), 10, WHITE)

    # displays  image
    draw_texture(spaceship_texture,0, 0, WHITE)
    draw_texture_v(new_texture,Vector2(100,0),WHITE)
    draw_texture(cowbow_texture, 900, 800, WHITE)

    # displays text
    draw_text('HELLO',0, 400, 100, WHITE)
    draw_text_ex(font, 'FONT', Vector2(0, 600), 20, 0, BLUE)
                
    end_drawing()

close_window()
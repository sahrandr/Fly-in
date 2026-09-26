from pyray import *
from ui import Colors
from scenes import TitleScene

class App:
    def __init__(self, width=0, height=0, title="Fly-in"):
        set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
        init_window(width, height, title)
        set_target_fps(60)
        
        # On initialise la première scène après la création de la fenêtre
        # pour que get_screen_width() fonctionne correctement.
        self.current_scene = TitleScene(has_save=False)
        self.running = True

    def change_scene(self, new_scene):
        self.current_scene = new_scene

    def quit(self):
        self.running = False

    def run(self):
        while self.running and not window_should_close():
            dt = get_frame_time()
            
            if self.current_scene:
                self.current_scene.update(dt, self)
            
            begin_drawing()
            clear_background(Colors.BG)
            
            # Dessin de la grille globale
            sw, sh = get_screen_width(), get_screen_height()
            for gx in range(0, sw, 40):
                draw_line(gx, 0, gx, sh, Colors.GRID)
            for gy in range(0, sh, 40):
                draw_line(0, gy, sw, gy, Colors.GRID)
                
            if self.current_scene:
                self.current_scene.draw()
                
            end_drawing()
            
        close_window()


if __name__ == "__main__":
    app = App()
    app.run()
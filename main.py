from typing import Any, Optional

from pyray import (
    ConfigFlags,
    begin_drawing,
    clear_background,
    close_window,
    draw_line,
    end_drawing,
    get_frame_time,
    get_screen_height,
    get_screen_width,
    init_window,
    set_config_flags,
    set_target_fps,
    window_should_close,
)

from scenes import TitleScene
from ui import Colors


class App:
    """Point d'entree du jeu: possede la fenetre et la scene active."""

    def __init__(
        self, width: int = 0, height: int = 0, title: str = "Fly-in"
    ) -> None:
        set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
        init_window(width, height, title)
        set_target_fps(60)

        self.current_scene: Optional[Any] = TitleScene(has_save=False)
        self.running = True

    def change_scene(self, new_scene: Any) -> None:
        """Remplace la scene active par `new_scene`."""
        self.current_scene = new_scene

    def quit(self) -> None:
        """Demande l'arret de la boucle principale au prochain tour."""
        self.running = False

    def run(self) -> None:
        """Boucle principale: update + dessin jusqu'a fermeture."""
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

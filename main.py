"""Entry point of Fly-in: window, main loop and scene management."""

import sys
from typing import Any, Optional

from pyray import (
    ConfigFlags,
    begin_drawing,
    clear_background,
    close_window,
    end_drawing,
    get_frame_time,
    get_screen_height,
    get_screen_width,
    init_window,
    set_config_flags,
    set_target_fps,
    window_should_close,
)

from algo import SimulationError
from parser import MapParsingError
from scenes import TitleScene
from ui import Colors, Renderer


class App:
    """Application entry point: owns the window and the active scene."""

    def __init__(
        self, width: int = 0, height: int = 0, title: str = "Fly-in"
    ) -> None:
        """Open the window and start on the title scene.

        Args:
            width: Window width in pixels (0 for the screen width).
            height: Window height in pixels (0 for the screen height).
            title: Title of the window.
        """
        set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
        init_window(width, height, title)
        set_target_fps(60)

        self.current_scene: Optional[Any] = TitleScene(has_save=False)
        self.running = True

    def change_scene(self, new_scene: Any) -> None:
        """Replace the active scene.

        Args:
            new_scene: The scene to display from now on.
        """
        self.current_scene = new_scene

    def quit(self) -> None:
        """Request the main loop to stop at the next iteration."""
        self.running = False

    def run(self) -> None:
        """Run the main loop (update, then draw) until the window closes."""
        while self.running and not window_should_close():
            dt = get_frame_time()

            if self.current_scene:
                self.current_scene.update(dt, self)

            begin_drawing()
            clear_background(Colors.BG)

            Renderer.draw_grid(get_screen_width(), get_screen_height())

            if self.current_scene:
                self.current_scene.draw()

            end_drawing()

        close_window()


if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except MapParsingError as e:
        print(f"Parsing Error: {e}", file=sys.stderr)
        sys.exit(1)
    except SimulationError as e:
        print(f"Simulation Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)

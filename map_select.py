"""Map selection screen: lists the available maps by difficulty."""

import os

from pyray import (
    Color,
    ConfigFlags,
    MouseButton,
    begin_drawing,
    clear_background,
    close_window,
    draw_rectangle,
    draw_text,
    end_drawing,
    get_frame_time,
    get_mouse_position,
    get_screen_height,
    get_screen_width,
    init_window,
    is_mouse_button_pressed,
    set_config_flags,
    set_target_fps,
    window_should_close,
)

from ui import Button, Colors, Renderer


class MapManager:
    """Discover map files and format their display."""

    CATEGORY_ORDER = ["easy", "medium", "hard", "challenger"]

    @staticmethod
    def get_category_color(cat: str) -> Color:
        """Return the accent color of a difficulty category.

        Args:
            cat: Category name, such as ``"easy"`` or ``"hard"``.

        Returns:
            The category color, or the default path color if the
            category is unknown.
        """
        colors = {
            "easy": Colors.START,
            "medium": Colors.GOAL,
            "hard": Color(225, 95, 95, 255),
            "challenger": Color(190, 130, 255, 255),
        }
        return colors.get(cat, Colors.PATH)

    @classmethod
    def scan_maps(cls, maps_root: str = "maps") -> dict[str, list[str]]:
        """Find the map files grouped by category folder.

        Args:
            maps_root: Directory containing one sub-folder per
                category, each holding ``.txt`` map files.

        Returns:
            A mapping from category name to the sorted list of map
            file paths. Empty if ``maps_root`` does not exist.
        """
        categories: dict[str, list[str]] = {}
        if not os.path.isdir(maps_root):
            return categories

        for entry in sorted(os.listdir(maps_root)):
            cat_path = os.path.join(maps_root, entry)
            if not os.path.isdir(cat_path):
                continue
            files = sorted(
                f for f in os.listdir(cat_path) if f.endswith(".txt")
            )
            if files:
                categories[entry] = [os.path.join(cat_path, f) for f in files]

        return categories

    @staticmethod
    def format_map_name(filename: str) -> str:
        """Build a readable label from a map file name.

        Args:
            filename: File name, such as ``"01_easy_path.txt"``.

        Returns:
            An upper-case label, such as ``"01 · EASY PATH"``.
        """
        name = filename[:-4] if filename.endswith(".txt") else filename
        parts = name.split("_", 1)
        if parts[0].isdigit() and len(parts) > 1:
            return f"{parts[0]} · {parts[1].replace('_', ' ').upper()}"
        return name.replace("_", " ").upper()


class MapSelectScene:
    """Screen letting the player pick a map."""

    def __init__(self, maps_root: str = "maps") -> None:
        """Scan the maps folder and lay out the buttons.

        Args:
            maps_root: Directory containing the map categories.
        """
        self.maps_root = maps_root
        self.screen_w = get_screen_width()
        self.screen_h = get_screen_height()
        self.headers: list[tuple[str, int, int, Color]] = []
        self.entries: list[tuple[Button, str]] = []

        self._setup_layout()

    def _setup_layout(self) -> None:
        """Compute the category headers and the map buttons."""
        categories = MapManager.scan_maps(self.maps_root)
        cat_names = [c for c in MapManager.CATEGORY_ORDER if c in categories]
        cat_names += sorted(
            c for c in categories if c not in MapManager.CATEGORY_ORDER
        )

        col_w = 250
        gap_x = 26
        total_w = len(cat_names) * col_w + max(0, len(cat_names) - 1) * gap_x

        self.start_x = max(60, (self.screen_w - total_w) // 2)
        top_y = 190
        btn_h = 38
        btn_gap = 10

        for i, cat in enumerate(cat_names):
            cx = self.start_x + i * (col_w + gap_x)
            color = MapManager.get_category_color(cat)
            self.headers.append((cat.upper(), cx, top_y, color))

            for j, path in enumerate(categories[cat]):
                label = MapManager.format_map_name(os.path.basename(path))
                by = top_y + 38 + j * (btn_h + btn_gap)
                btn = Button(label, cx, by, col_w, btn_h, accent=color)
                self.entries.append((btn, path))

    def update(self, dt: float) -> str | None:
        """Handle input for one frame.

        Args:
            dt: Elapsed time in seconds since the last frame.

        Returns:
            The path of the clicked map, or ``None`` if no button
            was clicked.
        """
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)

        for btn, path in self.entries:
            if btn.update(mouse, pressed, dt):
                return path
        return None

    def draw(self) -> None:
        """Render the title, the category headers and the buttons."""
        begin_drawing()
        clear_background(Colors.BG)

        Renderer.draw_grid(self.screen_w, self.screen_h)

        title = "CHOISIS UNE CARTE"
        Renderer.draw_text_spaced(title, self.start_x, 70, 30, Colors.TEXT, 4)
        sub = "clique une carte pour lancer la simulation"
        Renderer.draw_text_spaced(
            sub, self.start_x + 2, 108, 11,
            Renderer.with_alpha(Colors.MUTED, 220), 3,
        )

        for text, hx, hy, color in self.headers:
            draw_rectangle(int(hx), int(hy) - 2, 3, 16, color)
            Renderer.draw_text_spaced(text, hx + 10, hy - 2, 13, color, 2)

        for btn, _path in self.entries:
            btn.draw()

        if not self.entries:
            msg = f"aucune carte trouvée dans '{self.maps_root}/'"
            draw_text(
                msg, self.start_x, 210, 14,
                Renderer.with_alpha(Colors.MUTED, 220),
            )

        end_drawing()

    def run(self) -> str | None:
        """Run the selection loop until a map is chosen.

        Returns:
            The path of the chosen map, or ``None`` if the window was
            closed without a choice.
        """
        while not window_should_close():
            dt = get_frame_time()
            chosen_path = self.update(dt)
            if chosen_path:
                return chosen_path
            self.draw()
        return None


if __name__ == "__main__":
    set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
    init_window(0, 0, "Fly-in")
    set_target_fps(60)

    scene = MapSelectScene()
    choice = scene.run()
    print(f"Carte choisie: {choice}")
    close_window()

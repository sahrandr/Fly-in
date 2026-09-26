import os
from pyray import *
from title_screen import Button, Renderer, Colors


class MapManager:
    CATEGORY_ORDER = ["easy", "medium", "hard", "challenger"]
    
    @staticmethod
    def get_category_color(cat: str) -> Color:
        colors = {
            "easy": Colors.START,
            "medium": Colors.GOAL,
            "hard": Color(225, 95, 95, 255),
            "challenger": Color(190, 130, 255, 255),
        }
        return colors.get(cat, Colors.PATH)

    @classmethod
    def scan_maps(cls, maps_root: str = "maps") -> dict[str, list[str]]:
        categories = {}
        if not os.path.isdir(maps_root):
            return categories

        for entry in sorted(os.listdir(maps_root)):
            cat_path = os.path.join(maps_root, entry)
            if not os.path.isdir(cat_path):
                continue
            files = sorted(f for f in os.listdir(cat_path) if f.endswith(".txt"))
            if files:
                categories[entry] = [os.path.join(cat_path, f) for f in files]

        return categories

    @staticmethod
    def format_map_name(filename: str) -> str:
        name = filename[:-4] if filename.endswith(".txt") else filename
        parts = name.split("_", 1)
        if parts[0].isdigit() and len(parts) > 1:
            return f"{parts[0]} · {parts[1].replace('_', ' ').upper()}"
        return name.replace("_", " ").upper()


class MapSelectScene:
    def __init__(self, maps_root: str = "maps"):
        self.maps_root = maps_root
        self.screen_w = get_screen_width()
        self.screen_h = get_screen_height()
        self.headers = []
        self.entries = []
        
        self._setup_layout()

    def _setup_layout(self) -> None:
        categories = MapManager.scan_maps(self.maps_root)
        cat_names = [c for c in MapManager.CATEGORY_ORDER if c in categories]
        cat_names += sorted(c for c in categories if c not in MapManager.CATEGORY_ORDER)

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
                self.entries.append((Button(label, cx, by, col_w, btn_h, accent=color), path))

    def update(self, dt: float) -> str | None:
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)

        for btn, path in self.entries:
            if btn.update(mouse, pressed, dt):
                return path
        return None

    def draw(self) -> None:
        begin_drawing()
        clear_background(Colors.BG)

        Renderer.draw_grid(self.screen_w, self.screen_h)

        title = "CHOISIS UNE CARTE"
        Renderer.draw_text_spaced(title, self.start_x, 70, 30, Colors.TEXT, 4)
        sub = "clique une carte pour lancer la simulation"
        Renderer.draw_text_spaced(sub, self.start_x + 2, 108, 11, Renderer.with_alpha(Colors.MUTED, 220), 3)

        for text, hx, hy, color in self.headers:
            draw_rectangle(int(hx), int(hy) - 2, 3, 16, color)
            Renderer.draw_text_spaced(text, hx + 10, hy - 2, 13, color, 2)

        for btn, _path in self.entries:
            btn.draw()

        if not self.entries:
            msg = f"aucune carte trouvée dans '{self.maps_root}/'"
            Renderer.draw_text(msg, self.start_x, 210, 14, Renderer.with_alpha(Colors.MUTED, 220))

        end_drawing()

    def run(self) -> str | None:
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
    choix = scene.run()
    print(f"Carte choisie: {choix}")
    close_window()
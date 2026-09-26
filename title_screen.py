import math
from pyray import *


class Colors:
    BG = Color(8, 10, 15, 255)
    GRID = Color(255, 255, 255, 6)
    STRUCT = Color(64, 74, 92, 255)
    PATH = Color(90, 222, 204, 255)
    START = Color(96, 230, 130, 255)
    GOAL = Color(255, 198, 70, 255)
    TEXT = Color(226, 236, 242, 255)
    MUTED = Color(120, 132, 148, 255)
    DISABLED = Color(70, 76, 86, 255)
    ORBS = [
        Color(255, 150, 120, 255), Color(140, 235, 205, 255),
        Color(155, 190, 255, 255), Color(255, 214, 130, 255),
        Color(232, 152, 238, 255), Color(150, 238, 238, 255),
    ]


class Renderer:
    @staticmethod
    def with_alpha(c: Color, a: float) -> Color:
        return Color(c.r, c.g, c.b, max(0, min(255, int(a))))

    @staticmethod
    def draw_text(text: str, x: float, y: float, size: int, color: Color) -> None:
        draw_text(text, int(x), int(y), size, color)

    @staticmethod
    def draw_text_spaced(text: str, x: float, y: float, size: int, color: Color, spacing: int = 2) -> float:
        cx = x
        for ch in text:
            draw_text(ch, int(cx), int(y), size, color)
            cx += measure_text(ch, size) + spacing
        return cx - x

    @staticmethod
    def measure_spaced(text: str, size: int, spacing: int = 2) -> int:
        return sum(measure_text(c, size) + spacing for c in text) - spacing

    @staticmethod
    def glow_dot(x: float, y: float, radius: float, color: Color, layers: int = 4, power: float = 52) -> None:
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        for i in range(layers, 0, -1):
            k = i / layers
            draw_circle_v(Vector2(x, y), radius * (1 + k * 3.4),
                          Renderer.with_alpha(color, power * (1 - k) ** 1.6))
        end_blend_mode()
        draw_circle_v(Vector2(x, y), radius, color)
        draw_circle_v(Vector2(x - radius * 0.22, y - radius * 0.22),
                      radius * 0.42, Color(255, 255, 255, 210))

    @staticmethod
    def glow_ring(x: float, y: float, radius: float, thick: float, color: Color, alpha: float) -> None:
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        for i in range(3):
            draw_ring(Vector2(x, y), radius - thick / 2 - i * 2,
                      radius + thick / 2 + i * 2, 0, 360, 48,
                      Renderer.with_alpha(color, alpha / (2 + i * 2)))
        end_blend_mode()
        draw_ring(Vector2(x, y), radius - thick / 2, radius + thick / 2,
                  0, 360, 48, Renderer.with_alpha(color, alpha))

    @staticmethod
    def glow_line(a: Vector2, b: Vector2, thick: float, color: Color, alpha: float) -> None:
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_line_ex(a, b, thick * 4.0, Renderer.with_alpha(color, alpha * 0.18))
        draw_line_ex(a, b, thick * 2.0, Renderer.with_alpha(color, alpha * 0.35))
        end_blend_mode()
        draw_line_ex(a, b, thick, Renderer.with_alpha(color, alpha))

    @staticmethod
    def draw_grid(screen_w: int, screen_h: int, step: int = 40) -> None:
        for gx in range(0, screen_w, step):
            draw_line(gx, 0, gx, screen_h, Colors.GRID)
        for gy in range(0, screen_h, step):
            draw_line(0, gy, screen_w, gy, Colors.GRID)


class MiniPath:
    def __init__(self, ox: float, oy: float, w: float, h: float):
        raw = [
            ("start", 0.05, 0.55, "start"),
            ("a", 0.28, 0.30, "path"),
            ("b", 0.28, 0.78, "struct"),
            ("c", 0.55, 0.55, "path"),
            ("d", 0.80, 0.30, "path"),
            ("goal", 0.95, 0.55, "goal"),
        ]
        self.nodes = {n: (ox + rx * w, oy + ry * h, role) for n, rx, ry, role in raw}
        self.edges_hot = [("start", "a"), ("a", "c"), ("c", "d"), ("d", "goal")]
        self.edges_idle = [("start", "b"), ("b", "c")]
        self.path_order = ["start", "a", "c", "d", "goal"]
        self.orbs = [{"t": i / 3.0, "speed": 0.09, "color": Colors.ORBS[i % len(Colors.ORBS)]}
                     for i in range(3)]

    def role_color(self, role: str) -> Color:
        return {"start": Colors.START, "goal": Colors.GOAL, "path": Colors.PATH, "struct": Colors.STRUCT}[role]

    def point_on_path(self, t: float):
        segs = list(zip(self.path_order[:-1], self.path_order[1:]))
        t = t % 1.0
        seg_t = t * len(segs)
        i = min(int(seg_t), len(segs) - 1)
        local_t = seg_t - i
        a, b = segs[i]
        ax, ay, _ = self.nodes[a]
        bx, by, _ = self.nodes[b]
        return ax + (bx - ax) * local_t, ay + (by - ay) * local_t

    def update(self, dt: float) -> None:
        for o in self.orbs:
            o["t"] += o["speed"] * dt

    def draw(self, alpha_mult: float = 1.0) -> None:
        for a, b in self.edges_idle:
            ax, ay, _ = self.nodes[a]
            bx, by, _ = self.nodes[b]
            draw_line_ex(Vector2(ax, ay), Vector2(bx, by), 1.2,
                         Renderer.with_alpha(Color(92, 106, 130, 255), 46 * alpha_mult))
        for a, b in self.edges_hot:
            ax, ay, _ = self.nodes[a]
            bx, by, _ = self.nodes[b]
            Renderer.glow_line(Vector2(ax, ay), Vector2(bx, by), 1.4, Colors.PATH, 110 * alpha_mult)

        for name, (x, y, role) in self.nodes.items():
            col = self.role_color(role)
            r = 11 if role in ("start", "goal") else 6.5
            if role in ("start", "goal"):
                Renderer.glow_ring(x, y, r, 2.0, col, 190 * alpha_mult)
                draw_circle_v(Vector2(x, y), r - 2, Renderer.with_alpha(col, 55 * alpha_mult))
            else:
                draw_circle_v(Vector2(x, y), r, Color(14, 18, 24, int(255 * alpha_mult)))
                draw_ring(Vector2(x, y), r - 0.8, r + 0.8, 0, 360, 24,
                          Renderer.with_alpha(col, 160 * alpha_mult))

        for o in self.orbs:
            x, y = self.point_on_path(o["t"])
            Renderer.glow_dot(x, y, 3.6, Renderer.with_alpha(o["color"], 255 * alpha_mult))


class Button:
    def __init__(self, label: str, x: float, y: float, w: float, h: float, enabled: bool = True, accent: Color = None):
        self.label = label
        self.rect = Rectangle(x, y, w, h)
        self.enabled = enabled
        self.accent = accent if accent is not None else Colors.PATH
        self.hover_t = 0.0
        self.press_t = 0.0

    def update(self, mouse: Vector2, pressed: bool, dt: float) -> bool:
        hovering = self.enabled and check_collision_point_rec(mouse, self.rect)
        target = 1.0 if hovering else 0.0
        self.hover_t += (target - self.hover_t) * min(1.0, dt * 10.0)
        held = hovering and is_mouse_button_down(MouseButton.MOUSE_BUTTON_LEFT)
        self.press_t += ((1.0 if held else 0.0) - self.press_t) * min(1.0, dt * 14.0)
        return hovering and pressed

    def draw(self) -> None:
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        cx, cy = x + w / 2, y + h / 2
        lift = self.press_t * 2.0

        if not self.enabled:
            draw_rectangle_rounded(Rectangle(x, y + lift, w, h), 0.28, 8, Color(14, 17, 22, 255))
            draw_rectangle_rounded_lines_ex(Rectangle(x, y + lift, w, h), 0.28, 8, 1.1,
                                            Renderer.with_alpha(Colors.DISABLED, 150))
            tw = measure_text(self.label, 15)
            Renderer.draw_text(self.label, cx - tw / 2, cy - 7 + lift, 15,
                              Renderer.with_alpha(Colors.DISABLED, 200))
            return

        col = self.accent
        fill_alpha = 12 + self.hover_t * 26
        border_alpha = 110 + self.hover_t * 140

        draw_rectangle_rounded(Rectangle(x, y + lift, w, h), 0.28, 8, Color(12, 15, 20, 255))
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_rectangle_rounded(Rectangle(x, y + lift, w, h), 0.28, 8, Renderer.with_alpha(col, fill_alpha))
        end_blend_mode()
        draw_rectangle_rounded_lines_ex(Rectangle(x, y + lift, w, h), 0.28, 8, 1.3,
                                        Renderer.with_alpha(col, border_alpha))

        bar_h = 14 + self.hover_t * 4
        draw_rectangle(int(x + 16), int(cy - bar_h / 2 + lift), 2, int(bar_h),
                       Renderer.with_alpha(col, 140 + self.hover_t * 115))

        size = 14
        tw = Renderer.measure_spaced(self.label, size, 2)
        Renderer.draw_text_spaced(self.label, cx - tw / 2 + 6, cy - size / 2 + lift,
                                  size, Renderer.with_alpha(Colors.TEXT, 200 + self.hover_t * 55), 2)


class TitleScene:
    def __init__(self, has_save: bool = False, title: str = "FLY-IN", subtitle: str = "ESTHÉTIQUE DARK / NEON"):
        self.has_save = has_save
        self.title = title
        self.subtitle = subtitle
        self.screen_w = get_screen_width()
        self.screen_h = get_screen_height()
        self.t0 = get_time()
        
        self._setup_layout()

    def _setup_layout(self) -> None:
        panel_w = max(380, int(self.screen_w * 0.32))
        btn_w = min(300, panel_w - 80)
        btn_h = 50
        gap = 14
        self.btn_x = (panel_w - btn_w) // 2

        total_ui_h = 110 + (3 * btn_h + 2 * gap)
        start_y = max(60, (self.screen_h - total_ui_h) // 2)

        self.title_y = start_y
        buttons_y = self.title_y + 110

        preview_x = panel_w + 40
        preview_y = int(self.screen_h * 0.12)
        preview_w = self.screen_w - preview_x - 60
        preview_h = int(self.screen_h * 0.76)

        self.panel_w = panel_w
        self.preview = MiniPath(preview_x, preview_y, preview_w, preview_h)
        self.buttons = {
            "new game": Button("NEW GAME", self.btn_x, buttons_y, btn_w, btn_h),
            "continue": Button("CONTINUER", self.btn_x, buttons_y + 1 * (btn_h + gap),
                               btn_w, btn_h, enabled=self.has_save),
            "paramettres": Button("PARAMETTRES", self.btn_x, buttons_y + 2 * (btn_h + gap),
                                btn_w, btn_h, enabled=self.has_save),
            "settings": Button("QUIT", self.btn_x, buttons_y + 3 * (btn_h + gap),
                               btn_w, btn_h),
        }

    def update(self, dt: float) -> str | None:
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)
        self.preview.update(dt)

        for key, btn in self.buttons.items():
            if btn.update(mouse, pressed, dt):
                return key
        return None

    def draw(self) -> None:
        elapsed = get_time() - self.t0
        begin_drawing()
        clear_background(Colors.BG)

        Renderer.draw_grid(self.screen_w, self.screen_h)

        draw_line_ex(Vector2(self.panel_w, 40), Vector2(self.panel_w, self.screen_h - 40), 1.0,
                      Renderer.with_alpha(Color(255, 255, 255, 255), 14))

        self.preview.draw()

        title_size = 40
        Renderer.draw_text_spaced(self.title, self.btn_x, self.title_y, title_size, Colors.TEXT, 5)
        sub_size = 11
        Renderer.draw_text_spaced(self.subtitle, self.btn_x + 2, self.title_y + title_size + 12,
                                  sub_size, Renderer.with_alpha(Colors.MUTED, 220), 3)

        breathe = 1.0 + math.sin(elapsed * 1.4) * 0.08
        Renderer.glow_ring(self.btn_x + 6, self.title_y - 14, 3 * breathe, 1.2, Colors.PATH, 200)

        for btn in self.buttons.values():
            btn.draw()

        foot = "15 drones  ·  26 tours  ·  carte: ultimate_challenge"
        Renderer.draw_text(foot, self.btn_x, self.screen_h - 46, 11, Renderer.with_alpha(Colors.MUTED, 150))

        end_drawing()

    def run(self) -> str | None:
        while not window_should_close():
            dt = get_frame_time()
            action = self.update(dt)
            if action:
                return action
            self.draw()
        return None


if __name__ == "__main__":
    set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
    init_window(0, 0, "Fly-in")
    set_target_fps(60)

    scene = TitleScene(has_save=False)
    choice = scene.run()
    print(f"Choix: {choice}")
    close_window()
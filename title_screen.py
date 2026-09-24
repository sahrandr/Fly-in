import math
import random
from pyray import *


C_BG = Color(8, 10, 15, 255)
C_GRID = Color(255, 255, 255, 6)

C_STRUCT = Color(64, 74, 92, 255)
C_PATH = Color(90, 222, 204, 255)
C_START = Color(96, 230, 130, 255)
C_GOAL = Color(255, 198, 70, 255)
C_TEXT = Color(226, 236, 242, 255)
C_MUTED = Color(120, 132, 148, 255)
C_DISABLED = Color(70, 76, 86, 255)

ORB_COLORS = [
    Color(255, 150, 120, 255), Color(140, 235, 205, 255),
    Color(155, 190, 255, 255), Color(255, 214, 130, 255),
    Color(232, 152, 238, 255), Color(150, 238, 238, 255),
]


def with_alpha(c, a):
    return Color(c.r, c.g, c.b, max(0, min(255, int(a))))


def glow_dot(x, y, radius, color, layers=4, power=52):
    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
    for i in range(layers, 0, -1):
        k = i / layers
        draw_circle_v(Vector2(x, y), radius * (1 + k * 3.4),
                      with_alpha(color, power * (1 - k) ** 1.6))
    end_blend_mode()
    draw_circle_v(Vector2(x, y), radius, color)
    draw_circle_v(Vector2(x - radius * 0.22, y - radius * 0.22),
                  radius * 0.42, Color(255, 255, 255, 210))


def glow_ring(x, y, radius, thick, color, alpha):
    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
    for i in range(3):
        draw_ring(Vector2(x, y), radius - thick / 2 - i * 2,
                  radius + thick / 2 + i * 2, 0, 360, 48,
                  with_alpha(color, alpha / (2 + i * 2)))
    end_blend_mode()
    draw_ring(Vector2(x, y), radius - thick / 2, radius + thick / 2,
              0, 360, 48, with_alpha(color, alpha))


def glow_line(a, b, thick, color, alpha):
    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
    draw_line_ex(a, b, thick * 4.0, with_alpha(color, alpha * 0.18))
    draw_line_ex(a, b, thick * 2.0, with_alpha(color, alpha * 0.35))
    end_blend_mode()
    draw_line_ex(a, b, thick, with_alpha(color, alpha))


def draw_text_spaced(text, x, y, size, color, spacing=2):
    cx = x
    for ch in text:
        draw_text(ch, int(cx), int(y), size, color)
        cx += measure_text(ch, size) + spacing
    return cx - x


def measure_spaced(text, size, spacing=2):
    return sum(measure_text(c, size) + spacing for c in text) - spacing


# ============================================================
#  MINI GRAPHE DÉCORATIF
# ============================================================
class MiniPath:
    def __init__(self, ox, oy, w, h):
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

        self.orbs = [{"t": i / 3.0, "speed": 0.09, "color": ORB_COLORS[i % len(ORB_COLORS)]}
                     for i in range(3)]

    def role_color(self, role):
        return {"start": C_START, "goal": C_GOAL, "path": C_PATH, "struct": C_STRUCT}[role]

    def point_on_path(self, t):
        segs = list(zip(self.path_order[:-1], self.path_order[1:]))
        t = t % 1.0
        seg_t = t * len(segs)
        i = min(int(seg_t), len(segs) - 1)
        local_t = seg_t - i
        a, b = segs[i]
        ax, ay, _ = self.nodes[a]
        bx, by, _ = self.nodes[b]
        return ax + (bx - ax) * local_t, ay + (by - ay) * local_t

    def update(self, dt):
        for o in self.orbs:
            o["t"] += o["speed"] * dt

    def draw(self, alpha_mult=1.0):
        for a, b in self.edges_idle:
            ax, ay, _ = self.nodes[a]
            bx, by, _ = self.nodes[b]
            draw_line_ex(Vector2(ax, ay), Vector2(bx, by), 1.2,
                         with_alpha(Color(92, 106, 130, 255), 46 * alpha_mult))
        for a, b in self.edges_hot:
            ax, ay, _ = self.nodes[a]
            bx, by, _ = self.nodes[b]
            glow_line(Vector2(ax, ay), Vector2(bx, by), 1.4, C_PATH, 110 * alpha_mult)

        for name, (x, y, role) in self.nodes.items():
            col = self.role_color(role)
            r = 11 if role in ("start", "goal") else 6.5
            if role in ("start", "goal"):
                glow_ring(x, y, r, 2.0, col, 190 * alpha_mult)
                draw_circle_v(Vector2(x, y), r - 2, with_alpha(col, 55 * alpha_mult))
            else:
                draw_circle_v(Vector2(x, y), r, Color(14, 18, 24, int(255 * alpha_mult)))
                draw_ring(Vector2(x, y), r - 0.8, r + 0.8, 0, 360, 24,
                          with_alpha(col, 160 * alpha_mult))

        for o in self.orbs:
            x, y = self.point_on_path(o["t"])
            glow_dot(x, y, 3.6, with_alpha(o["color"], 255 * alpha_mult))


# ============================================================
#  BOUTON
# ============================================================
class Button:
    def __init__(self, label, x, y, w, h, enabled=True, accent=None):
        self.label = label
        self.rect = Rectangle(x, y, w, h)
        self.enabled = enabled
        self.accent = accent if accent is not None else C_PATH
        self.hover_t = 0.0
        self.press_t = 0.0

    def update(self, mouse, pressed, dt):
        hovering = self.enabled and check_collision_point_rec(mouse, self.rect)
        target = 1.0 if hovering else 0.0
        self.hover_t += (target - self.hover_t) * min(1.0, dt * 10.0)
        held = hovering and is_mouse_button_down(MouseButton.MOUSE_BUTTON_LEFT)
        self.press_t += ((1.0 if held else 0.0) - self.press_t) * min(1.0, dt * 14.0)
        return hovering and pressed

    def draw(self):
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        cx, cy = x + w / 2, y + h / 2
        lift = self.press_t * 2.0

        if not self.enabled:
            draw_rectangle_rounded(Rectangle(x, y + lift, w, h), 0.28, 8, Color(14, 17, 22, 255))
            draw_rectangle_rounded_lines_ex(Rectangle(x, y + lift, w, h), 0.28, 8, 1.1,
                                            with_alpha(C_DISABLED, 150))
            tw = measure_text(self.label, 15)
            draw_text(self.label, int(cx - tw / 2), int(cy - 7 + lift), 15,
                      with_alpha(C_DISABLED, 200))
            return

        col = self.accent
        fill_alpha = 12 + self.hover_t * 26
        border_alpha = 110 + self.hover_t * 140

        draw_rectangle_rounded(Rectangle(x, y + lift, w, h), 0.28, 8, Color(12, 15, 20, 255))
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_rectangle_rounded(Rectangle(x, y + lift, w, h), 0.28, 8, with_alpha(col, fill_alpha))
        end_blend_mode()
        draw_rectangle_rounded_lines_ex(Rectangle(x, y + lift, w, h), 0.28, 8, 1.3,
                                        with_alpha(col, border_alpha))

        bar_h = 14 + self.hover_t * 4
        draw_rectangle(int(x + 16), int(cy - bar_h / 2 + lift), 2, int(bar_h),
                       with_alpha(col, 140 + self.hover_t * 115))

        size = 14
        tw = measure_spaced(self.label, size, 2)
        draw_text_spaced(self.label, int(cx - tw / 2 + 6), int(cy - size / 2 + lift),
                         size, with_alpha(C_TEXT, 200 + self.hover_t * 55), 2)


# ============================================================
#  ÉCRAN-TITRE PRINCIPAL
# ============================================================
def run_title_screen(has_save=False, title="FLY-IN", subtitle="ESTHÉTIQUE DARK / NEON"):
    SCREEN_W = get_screen_width()
    SCREEN_H = get_screen_height()

    # Dynamic scaling calculations
    panel_w = max(380, int(SCREEN_W * 0.32))
    btn_w = min(300, panel_w - 80)
    btn_h = 50
    gap = 14
    btn_x = (panel_w - btn_w) // 2

    # Vertical centering of UI block
    total_ui_h = 110 + (3 * btn_h + 2 * gap)
    start_y = max(60, (SCREEN_H - total_ui_h) // 2)

    title_y = start_y
    buttons_y = title_y + 110

    preview_x = panel_w + 40
    preview_y = int(SCREEN_H * 0.12)
    preview_w = SCREEN_W - preview_x - 60
    preview_h = int(SCREEN_H * 0.76)

    preview = MiniPath(preview_x, preview_y, preview_w, preview_h)

    buttons = {
        "new game": Button("NEW GAME", btn_x, buttons_y, btn_w, btn_h),
        "continue": Button("CONTINUER", btn_x, buttons_y + 1 * (btn_h + gap),
                           btn_w, btn_h, enabled=has_save),
        "paramettres": Button("PARAMETTRES", btn_x, buttons_y + 2 * (btn_h + gap),
                    btn_w, btn_h, enabled=has_save),
        "settings": Button("QUIT", btn_x, buttons_y + 3 * (btn_h + gap),
                           btn_w, btn_h),
    }

    t0 = get_time()

    while not window_should_close():
        dt = get_frame_time()
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)
        elapsed = get_time() - t0

        preview.update(dt)

        for key, btn in buttons.items():
            if btn.update(mouse, pressed, dt):
                return key

        begin_drawing()
        clear_background(C_BG)

        # Background grid
        for gx in range(0, SCREEN_W, 40):
            draw_line(gx, 0, gx, SCREEN_H, C_GRID)
        for gy in range(0, SCREEN_H, 40):
            draw_line(0, gy, SCREEN_W, gy, C_GRID)

        # Panel separator
        draw_line_ex(Vector2(panel_w, 40), Vector2(panel_w, SCREEN_H - 40), 1.0,
                      with_alpha(Color(255, 255, 255, 255), 14))

        preview.draw()

        # Title block
        title_size = 40
        draw_text_spaced(title, btn_x, title_y, title_size, C_TEXT, 5)
        sub_size = 11
        draw_text_spaced(subtitle, btn_x + 2, title_y + title_size + 12,
                         sub_size, with_alpha(C_MUTED, 220), 3)

        breathe = 1.0 + math.sin(elapsed * 1.4) * 0.08
        glow_ring(btn_x + 6, title_y - 14, 3 * breathe, 1.2, C_PATH, 200)

        for btn in buttons.values():
            btn.draw()

        # Footer
        foot = "15 drones  ·  26 tours  ·  carte: ultimate_challenge"
        draw_text(foot, btn_x, SCREEN_H - 46, 11, with_alpha(C_MUTED, 150))

        end_drawing()

    return None


if __name__ == "__main__":
    # Correct full-screen borderless window initialization
    set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
    init_window(0, 0, "Fly-in")
    set_target_fps(60)

    choice = run_title_screen(has_save=False)
    print(f"Choix: {choice}")
    close_window()
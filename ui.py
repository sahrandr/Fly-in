"""Shared UI building blocks: colors, drawing helpers, button, preview."""

from typing import Any, Dict, List, Optional, Tuple

from pyray import (
    BlendMode,
    Color,
    MouseButton,
    Rectangle,
    Vector2,
    begin_blend_mode,
    check_collision_point_rec,
    draw_circle_v,
    draw_line,
    draw_line_ex,
    draw_rectangle,
    draw_rectangle_rounded,
    draw_rectangle_rounded_lines_ex,
    draw_ring,
    draw_text,
    end_blend_mode,
    is_mouse_button_down,
    measure_text,
)


class Colors:
    """Central palette of colors used throughout the UI."""

    BG = Color(8, 10, 15, 255)
    GRID = Color(255, 255, 255, 6)
    STRUCT = Color(64, 74, 92, 255)
    PATH = Color(90, 222, 204, 255)
    DEAD = Color(158, 62, 62, 255)
    START = Color(96, 230, 130, 255)
    GOAL = Color(255, 198, 70, 255)
    TEXT = Color(226, 236, 242, 255)
    MUTED = Color(120, 132, 148, 255)
    DISABLED = Color(70, 76, 86, 255)
    EDGE_IDLE = Color(92, 106, 130, 46)

    HARD = Color(225, 95, 95, 255)
    CHALLENGER = Color(190, 130, 255, 255)

    ORBS: List[Color] = [
        Color(255, 150, 120, 255), Color(140, 235, 205, 255),
        Color(155, 190, 255, 255), Color(255, 214, 130, 255),
        Color(232, 152, 238, 255), Color(150, 238, 238, 255),
    ]

    MAP_COLORS: Dict[str, Optional[Color]] = {
        "green": Color(110, 235, 140, 255),
        "blue": Color(110, 200, 255, 255),
        "red": Color(235, 95, 95, 255),
        "orange": Color(255, 165, 70, 255),
        "yellow": Color(255, 220, 80, 255),
        "purple": Color(190, 130, 255, 255),
        "brown": Color(200, 150, 105, 255),
        "black": Color(140, 145, 155, 255),
        "gold": Color(255, 205, 90, 255),
        "gray": Color(175, 182, 195, 255),
        "none": None,
    }


class Renderer:
    """Stateless drawing helpers built on top of raylib primitives."""

    @staticmethod
    def with_alpha(color: Color, alpha: float) -> Color:
        """Return a copy of ``color`` with a clamped alpha channel.

        Args:
            color: Source color to copy the RGB channels from.
            alpha: Desired alpha value; clamped to ``[0, 255]``.

        Returns:
            A new ``Color`` with the same RGB and the clamped alpha.
        """
        return Color(
            color.r, color.g, color.b, max(0, min(255, int(alpha)))
        )

    @staticmethod
    def shade(color: Color, k: float) -> Color:
        """Scale the RGB channels of ``color`` by factor ``k``.

        Args:
            color: Source color.
            k: Multiplicative brightness factor.

        Returns:
            A new, brightness-scaled ``Color`` (alpha unchanged).
        """
        return Color(
            min(255, int(color.r * k)),
            min(255, int(color.g * k)),
            min(255, int(color.b * k)),
            color.a,
        )

    @staticmethod
    def glow_dot(
        x: float,
        y: float,
        radius: float,
        color: Color,
        layers: int = 4,
        power: float = 52,
    ) -> None:
        """Draw a soft, additively-blended glowing dot.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            radius: Core dot radius.
            color: Base color of the dot and its glow.
            layers: Number of additive glow layers to draw.
            power: Base alpha intensity of the glow.
        """
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        for i in range(layers, 0, -1):
            k = i / layers
            draw_circle_v(
                Vector2(x, y),
                radius * (1 + k * 3.4),
                Renderer.with_alpha(color, power * (1 - k) ** 1.6),
            )
        end_blend_mode()
        draw_circle_v(Vector2(x, y), radius, color)
        draw_circle_v(
            Vector2(x - radius * 0.22, y - radius * 0.22),
            radius * 0.42,
            Color(255, 255, 255, 210),
        )

    @staticmethod
    def glow_ring(
        x: float,
        y: float,
        radius: float,
        thick: float,
        color: Color,
        alpha: float,
    ) -> None:
        """Draw a soft, additively-blended glowing ring outline.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            radius: Ring radius.
            thick: Ring stroke thickness.
            color: Ring color.
            alpha: Base alpha intensity of the ring and its glow.
        """
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        for i in range(3):
            draw_ring(
                Vector2(x, y),
                radius - thick / 2 - i * 2,
                radius + thick / 2 + i * 2,
                0,
                360,
                48,
                Renderer.with_alpha(color, alpha / (2 + i * 2)),
            )
        end_blend_mode()
        draw_ring(
            Vector2(x, y),
            radius - thick / 2,
            radius + thick / 2,
            0,
            360,
            48,
            Renderer.with_alpha(color, alpha),
        )

    @staticmethod
    def glow_line(
        a: Vector2, b: Vector2, thick: float, color: Color, alpha: float
    ) -> None:
        """Draw a soft, additively-blended glowing line segment.

        Args:
            a: Line start point.
            b: Line end point.
            thick: Core line thickness.
            color: Line color.
            alpha: Base alpha intensity of the line and its glow.
        """
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_line_ex(
            a, b, thick * 4.0, Renderer.with_alpha(color, alpha * 0.18)
        )
        draw_line_ex(
            a, b, thick * 2.0, Renderer.with_alpha(color, alpha * 0.35)
        )
        end_blend_mode()
        draw_line_ex(a, b, thick, Renderer.with_alpha(color, alpha))

    @staticmethod
    def draw_grid(width: int, height: int, spacing: int = 40) -> None:
        """Draw a faint background grid covering the given area.

        Args:
            width: Grid width in pixels.
            height: Grid height in pixels.
            spacing: Pixel spacing between grid lines.
        """
        for gx in range(0, width, spacing):
            draw_line(gx, 0, gx, height, Colors.GRID)
        for gy in range(0, height, spacing):
            draw_line(0, gy, width, gy, Colors.GRID)

    @staticmethod
    def draw_text_spaced(
        text: str,
        x: float,
        y: float,
        size: int,
        color: Color,
        spacing: int = 2,
    ) -> float:
        """Draw ``text`` one character at a time with extra spacing.

        Args:
            text: Text to render.
            x: Starting X coordinate.
            y: Baseline Y coordinate.
            size: Font size in pixels.
            color: Text color.
            spacing: Extra pixels of spacing between characters.

        Returns:
            The total pixel width consumed by the rendered text.
        """
        cx = x
        for ch in text:
            draw_text(ch, int(cx), int(y), size, color)
            cx += measure_text(ch, size) + spacing
        return cx - x

    @staticmethod
    def measure_spaced(text: str, size: int, spacing: int = 2) -> float:
        """Measure the pixel width of ``text`` drawn with extra spacing.

        Args:
            text: Text to measure.
            size: Font size in pixels.
            spacing: Extra pixels of spacing between characters.

        Returns:
            The total pixel width the text would occupy.
        """
        return sum(
            measure_text(c, size) + spacing for c in text
        ) - spacing


class Button:
    """A hoverable, pressable rectangular UI button."""

    def __init__(
        self,
        label: str,
        x: float,
        y: float,
        w: float,
        h: float,
        enabled: bool = True,
        accent: Optional[Color] = None,
    ) -> None:
        """Initialize the button geometry and visual state.

        Args:
            label: Text displayed on the button.
            x: Top-left X coordinate.
            y: Top-left Y coordinate.
            w: Button width.
            h: Button height.
            enabled: Whether the button can be interacted with.
            accent: Accent color; defaults to ``Colors.PATH``.
        """
        self.label: str = label
        self.rect: Rectangle = Rectangle(x, y, w, h)
        self.enabled: bool = enabled
        self.accent: Color = accent if accent is not None else Colors.PATH
        self.hover_t: float = 0.0
        self.press_t: float = 0.0

    def update(self, mouse: Vector2, pressed: bool, dt: float) -> bool:
        """Update hover/press animation state and report clicks.

        Args:
            mouse: Current mouse position.
            pressed: Whether a click was registered this frame.
            dt: Elapsed time in seconds since the last update.

        Returns:
            ``True`` if the button was clicked this frame.
        """
        hovering = self.enabled and check_collision_point_rec(
            mouse, self.rect
        )
        target = 1.0 if hovering else 0.0
        self.hover_t += (target - self.hover_t) * min(1.0, dt * 10.0)
        held = hovering and is_mouse_button_down(
            MouseButton.MOUSE_BUTTON_LEFT
        )
        self.press_t += (
            (1.0 if held else 0.0) - self.press_t
        ) * min(1.0, dt * 14.0)
        return hovering and pressed

    def draw(self) -> None:
        """Render the button in its current enabled/hover/press state."""
        x = self.rect.x
        y = self.rect.y
        w = self.rect.width
        h = self.rect.height
        cx, cy = x + w / 2, y + h / 2
        lift = self.press_t * 2.0

        if not self.enabled:
            draw_rectangle_rounded(
                Rectangle(x, y + lift, w, h),
                0.28,
                8,
                Color(14, 17, 22, 255),
            )
            draw_rectangle_rounded_lines_ex(
                Rectangle(x, y + lift, w, h),
                0.28,
                8,
                1.1,
                Renderer.with_alpha(Colors.DISABLED, 150),
            )
            tw: float = measure_text(self.label, 15)
            draw_text(
                self.label,
                int(cx - tw / 2),
                int(cy - 7 + lift),
                15,
                Renderer.with_alpha(Colors.DISABLED, 200),
            )
            return

        col = self.accent
        fill_alpha = 12 + self.hover_t * 26
        border_alpha = 110 + self.hover_t * 140

        draw_rectangle_rounded(
            Rectangle(x, y + lift, w, h), 0.28, 8, Color(12, 15, 20, 255)
        )
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_rectangle_rounded(
            Rectangle(x, y + lift, w, h),
            0.28,
            8,
            Renderer.with_alpha(col, fill_alpha),
        )
        end_blend_mode()
        draw_rectangle_rounded_lines_ex(
            Rectangle(x, y + lift, w, h),
            0.28,
            8,
            1.3,
            Renderer.with_alpha(col, border_alpha),
        )

        bar_h = 14 + self.hover_t * 4
        draw_rectangle(
            int(x + 16),
            int(cy - bar_h / 2 + lift),
            2,
            int(bar_h),
            Renderer.with_alpha(col, 140 + self.hover_t * 115),
        )

        size = 14
        tw = Renderer.measure_spaced(self.label, size, 2)
        Renderer.draw_text_spaced(
            self.label,
            int(cx - tw / 2 + 6),
            int(cy - size / 2 + lift),
            size,
            Renderer.with_alpha(Colors.TEXT, 200 + self.hover_t * 55),
            2,
        )


class MiniPath:
    """A small decorative animated path graph (start -> ... -> goal)."""

    def __init__(self, ox: float, oy: float, w: float, h: float) -> None:
        """Build the node graph and orb animation state.

        Args:
            ox: Origin X offset for the graph's bounding box.
            oy: Origin Y offset for the graph's bounding box.
            w: Bounding box width.
            h: Bounding box height.
        """
        raw = [
            ("start", 0.05, 0.55, "start"), ("a", 0.28, 0.30, "path"),
            ("b", 0.28, 0.78, "struct"), ("c", 0.55, 0.55, "path"),
            ("d", 0.80, 0.30, "path"), ("goal", 0.95, 0.55, "goal"),
        ]
        self.nodes: Dict[str, Tuple[float, float, str]] = {
            n: (ox + rx * w, oy + ry * h, role) for n, rx, ry, role in raw
        }
        self.edges_hot: List[Tuple[str, str]] = [
            ("start", "a"), ("a", "c"), ("c", "d"), ("d", "goal")
        ]
        self.edges_idle: List[Tuple[str, str]] = [
            ("start", "b"), ("b", "c")
        ]
        self.path_order: List[str] = ["start", "a", "c", "d", "goal"]
        self.orbs: List[Dict[str, Any]] = [
            {
                "t": i / 3.0,
                "speed": 0.09,
                "color": Colors.ORBS[i % len(Colors.ORBS)],
            }
            for i in range(3)
        ]

    def role_color(self, role: str) -> Color:
        """Return the color associated with a node ``role``.

        Args:
            role: One of ``"start"``, ``"goal"``, ``"path"`` or
                ``"struct"``.

        Returns:
            The matching ``Color``. Falls back to ``Colors.STRUCT``
            if ``role`` is not recognized, so a malformed node never
            crashes rendering.
        """
        roles = {
            "start": Colors.START,
            "goal": Colors.GOAL,
            "path": Colors.PATH,
            "struct": Colors.STRUCT,
        }
        try:
            return roles[role]
        except KeyError:
            return Colors.STRUCT

    def point_on_path(self, t: float) -> Tuple[float, float]:
        """Interpolate a point along ``path_order`` at position ``t``.

        Args:
            t: Progress along the path, wrapped into ``[0, 1)``.

        Returns:
            The interpolated ``(x, y)`` position. Returns the first
            node's position (or the origin) if the path does not
            have at least two nodes to interpolate between.
        """
        segs = list(zip(self.path_order[:-1], self.path_order[1:]))
        if not segs:
            first = next(iter(self.nodes.values()), None)
            return (first[0], first[1]) if first else (0.0, 0.0)

        t = t % 1.0
        seg_t = t * len(segs)
        i = min(int(seg_t), len(segs) - 1)
        local_t = seg_t - i
        a, b = segs[i]
        ax, ay, _ = self.nodes[a]
        bx, by, _ = self.nodes[b]
        return ax + (bx - ax) * local_t, ay + (by - ay) * local_t

    def update(self, dt: float) -> None:
        """Advance the orb animation state.

        Args:
            dt: Elapsed time in seconds since the last update.
        """
        for o in self.orbs:
            o["t"] += o["speed"] * dt

    def draw(self, alpha_mult: float = 1.0) -> None:
        """Render the path's edges, nodes, and animated orbs.

        Args:
            alpha_mult: Global alpha multiplier, e.g. for fade
                in/out transitions.
        """
        for a, b in self.edges_idle:
            ax, ay, _ = self.nodes[a]
            bx, by, _ = self.nodes[b]
            draw_line_ex(
                Vector2(ax, ay),
                Vector2(bx, by),
                1.2,
                Renderer.with_alpha(
                    Color(92, 106, 130, 255), 46 * alpha_mult
                ),
            )
        for a, b in self.edges_hot:
            ax, ay, _ = self.nodes[a]
            bx, by, _ = self.nodes[b]
            Renderer.glow_line(
                Vector2(ax, ay),
                Vector2(bx, by),
                1.4,
                Colors.PATH,
                110 * alpha_mult,
            )

        for _name, (x, y, role) in self.nodes.items():
            col = self.role_color(role)
            r = 11 if role in ("start", "goal") else 6.5
            if role in ("start", "goal"):
                Renderer.glow_ring(x, y, r, 2.0, col, 190 * alpha_mult)
                draw_circle_v(
                    Vector2(x, y),
                    r - 2,
                    Renderer.with_alpha(col, 55 * alpha_mult),
                )
            else:
                draw_circle_v(
                    Vector2(x, y),
                    r,
                    Color(14, 18, 24, int(255 * alpha_mult)),
                )
                draw_ring(
                    Vector2(x, y),
                    r - 0.8,
                    r + 0.8,
                    0,
                    360,
                    24,
                    Renderer.with_alpha(col, 160 * alpha_mult),
                )

        for o in self.orbs:
            x, y = self.point_on_path(o["t"])
            Renderer.glow_dot(
                x, y, 3.6, Renderer.with_alpha(o["color"], 255 * alpha_mult)
            )

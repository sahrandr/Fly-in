"""Application scenes for Fly-in.

Defines the ``Scene`` base interface and the three concrete scenes
that make up the application flow: the title screen, the map
selection screen, and the drone-path simulation viewer.
"""

import math
import os
import sys
from collections import deque
from typing import Any, Deque, Dict, List, Protocol, Set, Tuple

from pyray import (
    BlendMode,
    Color,
    MouseButton,
    Vector2,
    begin_blend_mode,
    draw_circle_v,
    draw_line_ex,
    draw_rectangle,
    draw_ring,
    draw_text,
    end_blend_mode,
    get_mouse_position,
    get_screen_height,
    get_screen_width,
    get_time,
    is_mouse_button_pressed,
    measure_text,
)

from algo import Simulator
from parser import MapParser, MapParsingError
from ui import Button as Button
from ui import Colors as Colors
from ui import MiniPath as MiniPath
from ui import Renderer as Renderer

Position = Tuple[float, float]


class AppProtocol(Protocol):
    """Minimal interface a scene needs from its owning application."""

    def change_scene(self, scene: "Scene") -> None:
        """Switch the application to a new active scene."""

    def quit(self) -> None:
        """Request that the application close."""


class Scene:
    """Base interface implemented by every screen in the app."""

    def update(self, dt: float, app: AppProtocol) -> None:
        """Advance scene state for a single frame.

        Args:
            dt: Elapsed time in seconds since the last update.
            app: The owning application (for scene switches / quit).
        """

    def draw(self) -> None:
        """Render the scene for a single frame."""


class TitleScene(Scene):
    """The title screen with the main menu buttons."""

    def __init__(self, has_save: bool = False) -> None:
        """Build the title screen layout.

        Args:
            has_save: Whether a save file exists, enabling the
                "continue" and "settings" menu entries.
        """
        self.screen_w: int = get_screen_width()
        self.screen_h: int = get_screen_height()

        panel_w = max(380, int(self.screen_w * 0.32))
        btn_w = min(300, panel_w - 80)
        btn_h = 50
        gap = 14
        self.btn_x: int = (panel_w - btn_w) // 2

        total_ui_h = 110 + (3 * btn_h + 2 * gap)
        start_y = max(60, (self.screen_h - total_ui_h) // 2)
        self.title_y: int = start_y
        buttons_y = self.title_y + 110

        preview_x = panel_w + 40
        self.preview: MiniPath = MiniPath(
            preview_x,
            int(self.screen_h * 0.12),
            self.screen_w - preview_x - 60,
            int(self.screen_h * 0.76),
        )

        self.buttons: Dict[str, Button] = {
            "new": Button("NEW GAME", self.btn_x, buttons_y, btn_w, btn_h),
            "continue": Button(
                "CONTINUER",
                self.btn_x,
                buttons_y + 1 * (btn_h + gap),
                btn_w,
                btn_h,
                enabled=has_save,
            ),
            "settings": Button(
                "PARAMETRES",
                self.btn_x,
                buttons_y + 2 * (btn_h + gap),
                btn_w,
                btn_h,
                enabled=has_save,
            ),
            "quit": Button(
                "QUIT",
                self.btn_x,
                buttons_y + 3 * (btn_h + gap),
                btn_w,
                btn_h,
            ),
        }
        self.t0: float = get_time()

    def update(self, dt: float, app: AppProtocol) -> None:
        """Handle input and switch scenes on button clicks."""
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)
        self.preview.update(dt)

        if self.buttons["new"].update(mouse, pressed, dt):
            app.change_scene(MapSelectScene())
        elif self.buttons["quit"].update(mouse, pressed, dt):
            app.quit()

    def draw(self) -> None:
        """Render the preview graph, title text, and menu buttons."""
        self.preview.draw()
        Renderer.draw_text_spaced(
            "FLY-IN", self.btn_x, self.title_y, 40, Colors.TEXT, 5
        )
        Renderer.draw_text_spaced(
            "ESTHETIQUE DARK / NEON",
            self.btn_x + 2,
            self.title_y + 52,
            11,
            Renderer.with_alpha(Colors.MUTED, 220),
            3,
        )

        breathe = 1.0 + math.sin((get_time() - self.t0) * 1.4) * 0.08
        Renderer.glow_ring(
            self.btn_x + 6, self.title_y - 14, 3 * breathe, 1.2,
            Colors.PATH, 200,
        )

        for btn in self.buttons.values():
            btn.draw()

        foot = "15 drones  |  26 tours  |  carte: ultimate_challenge"
        draw_text(
            foot,
            int(self.btn_x),
            int(self.screen_h - 46),
            11,
            Renderer.with_alpha(Colors.MUTED, 150),
        )


class MapSelectScene(Scene):
    """Lets the player pick a map, grouped by difficulty category."""

    def __init__(self, maps_root: str = "maps") -> None:
        """Scan ``maps_root`` for map files and lay out the picker.

        Args:
            maps_root: Directory containing one sub-folder per
                difficulty category, each holding ``.txt`` map files.
        """
        self.screen_w: int = get_screen_width()
        self.screen_h: int = get_screen_height()
        self.maps_root: str = maps_root
        self.categories: Dict[str, List[str]] = self._scan_maps()

        cat_order = ["easy", "medium", "hard", "challenger"]
        self.cat_names: List[str] = [
            c for c in cat_order if c in self.categories
        ] + sorted(c for c in self.categories if c not in cat_order)

        self.cat_colors: Dict[str, Color] = {
            "easy": Colors.START,
            "medium": Colors.GOAL,
            "hard": Colors.HARD,
            "challenger": Colors.CHALLENGER,
        }

        col_w = 250
        gap_x = 26
        total_w = (
            len(self.cat_names) * col_w
            + max(0, len(self.cat_names) - 1) * gap_x
        )
        self.start_x: int = max(60, (self.screen_w - total_w) // 2)

        self.headers: List[Tuple[str, int, int, Color]] = []
        self.entries: List[Tuple[Button, str]] = []

        top_y = 190
        for i, cat in enumerate(self.cat_names):
            cx = self.start_x + i * (col_w + gap_x)
            color = self.cat_colors.get(cat, Colors.PATH)
            self.headers.append((cat.upper(), cx, top_y, color))
            for j, path in enumerate(self.categories[cat]):
                label = self._format_name(os.path.basename(path))
                by = top_y + 38 + j * 48
                self.entries.append(
                    (Button(label, cx, by, col_w, 38, accent=color), path)
                )

    def _scan_maps(self) -> Dict[str, List[str]]:
        """Discover map files grouped by category sub-folder.

        Returns:
            A mapping from category name to the sorted list of
            ``.txt`` map file paths found in that category's folder.
        """
        cats: Dict[str, List[str]] = {}
        if os.path.isdir(self.maps_root):
            for entry in sorted(os.listdir(self.maps_root)):
                cat_path = os.path.join(self.maps_root, entry)
                if os.path.isdir(cat_path):
                    files = sorted(
                        f for f in os.listdir(cat_path)
                        if f.endswith(".txt")
                    )
                    if files:
                        cats[entry] = [
                            os.path.join(cat_path, f) for f in files
                        ]
        return cats

    def _format_name(self, filename: str) -> str:
        """Turn a map file name into a human-readable label.

        Args:
            filename: Base file name, e.g. ``"03_forest_run.txt"``.

        Returns:
            A display label, e.g. ``"03 · FOREST RUN"``.
        """
        name = filename[:-4] if filename.endswith(".txt") else filename
        parts = name.split("_", 1)
        if parts[0].isdigit() and len(parts) > 1:
            rest = parts[1].replace("_", " ").upper()
            return f"{parts[0]} \u00b7 {rest}"
        return name.replace("_", " ").upper()

    def update(self, dt: float, app: AppProtocol) -> None:
        """Switch to the simulation scene when a map is clicked."""
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)
        for btn, path in self.entries:
            if btn.update(mouse, pressed, dt):
                app.change_scene(SimulationScene(path))

    def draw(self) -> None:
        """Render category headers, map buttons, and empty-state text."""
        Renderer.draw_text_spaced(
            "CHOISIS UNE CARTE", self.start_x, 70, 30, Colors.TEXT, 4
        )
        Renderer.draw_text_spaced(
            "clique une carte pour lancer la simulation",
            self.start_x + 2,
            108,
            11,
            Renderer.with_alpha(Colors.MUTED, 220),
            3,
        )

        for text, hx, hy, color in self.headers:
            draw_rectangle(int(hx), int(hy) - 2, 3, 16, color)
            Renderer.draw_text_spaced(text, hx + 10, hy - 2, 13, color, 2)

        for btn, _ in self.entries:
            btn.draw()

        if not self.entries:
            draw_text(
                f"aucune carte trouvee dans '{self.maps_root}/'",
                self.start_x,
                210,
                14,
                Renderer.with_alpha(Colors.MUTED, 220),
            )


class SimulationScene(Scene):
    """Animates the parsed map and the simulator's drone routes.

    Most attributes derived from the parsed map and the simulator's
    output are typed as ``Any``: their concrete shape is defined by
    the external ``parser``/``algo`` modules, not by this file.
    """

    def __init__(self, map_path: str) -> None:
        """Parse ``map_path`` and run the simulation, then lay it out.

        Args:
            map_path: Path to the map file to load and simulate.

        On a parsing or simulation error, prints a message to
        stderr and exits the process (this is a deliberate,
        controlled exit rather than an unhandled crash).
        """
        try:
            self.parsed: Any = MapParser(map_path).parse()
            self.simulator: Any = Simulator(self.parsed)
            self.par_tour: Dict[int, List[Tuple[Any, Any]]] = (
                self.simulator.run()
            )
        except (MapParsingError, ValueError) as err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)

        self.screen_w: int = get_screen_width()
        self.screen_h: int = get_screen_height()
        self._init_geometry()
        self._init_state()

    def _init_geometry(self) -> None:
        """Compute screen-space layout for zones and connections."""
        pad_x, pad_y = 110, 90
        xs = [z.x for z in self.parsed.zones.values()]
        ys = [z.y for z in self.parsed.zones.values()]
        span_x = max(1e-6, max(xs) - min(xs))
        span_y = max(1e-6, max(ys) - min(ys))
        self.scale: float = min(
            (self.screen_w - 2 * pad_x) / span_x,
            (self.screen_h - 2 * pad_y) / span_y,
        )
        self.ox: float = (
            (self.screen_w - span_x * self.scale) / 2 - min(xs) * self.scale
        )
        self.oy: float = (
            (self.screen_h - span_y * self.scale) / 2 - min(ys) * self.scale
        )

        self.positions: Dict[Any, Position] = {}
        for key, zone in self.parsed.zones.items():
            pos = (
                zone.x * self.scale + self.ox,
                zone.y * self.scale + self.oy,
            )
            for k in {key, str(key), getattr(zone, "name", None)}:
                if k:
                    self.positions[k] = pos

        for conn in self.parsed.connections:
            pa = self.positions[conn.zone_a]
            pb = self.positions[conn.zone_b]
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            self.positions[f"{conn.zone_a}-{conn.zone_b}"] = mid
            self.positions[f"{conn.zone_b}-{conn.zone_a}"] = mid

        self.connections: List[Tuple[Any, Any]] = []
        self.degree: Dict[str, int] = {}
        for conn in self.parsed.connections:
            a = getattr(conn, "zone_a", None)
            b = getattr(conn, "zone_b", None)
            if a and b:
                self.connections.append((a, b))
                self.degree[str(a)] = self.degree.get(str(a), 0) + 1
                self.degree[str(b)] = self.degree.get(str(b), 0) + 1

        self.start_id: Any = getattr(self.parsed, "start_zone", None)
        self.end_id: Any = getattr(
            self.parsed, "end_zone", getattr(self.parsed, "target_zone", None)
        )

        self.used_nodes: Set[str] = {str(self.start_id)}
        for moves in self.par_tour.values():
            for _, dest in moves:
                self.used_nodes.add(str(dest))

    def _init_state(self) -> None:
        """Initialize per-drone animation and simulation progress."""
        self.drone_ids: List[str] = [
            f"D{i}" for i in range(1, self.parsed.nb_drones + 1)
        ]
        self.drone_from: Dict[str, Any] = {
            d: self.parsed.start_zone for d in self.drone_ids
        }
        self.drone_to: Dict[str, Any] = {
            d: self.parsed.start_zone for d in self.drone_ids
        }
        self.trails: Dict[str, Deque[Position]] = {
            d: deque(maxlen=14) for d in self.drone_ids
        }

        self.pulses: List[Dict[str, Any]] = []
        self.tour_sim: int = 0
        self.max_tours: int = (
            max(self.par_tour.keys()) if self.par_tour else 0
        )
        self.turn_frames: int = 48
        self.frame_counter: int = 0
        self.is_done: bool = False
        self.nodes_sorted: List[Tuple[Any, Any]] = list(
            self.parsed.zones.items()
        )

    def _orb_color(self, drone_id: str) -> Color:
        """Return the trail/glow color assigned to a drone.

        Args:
            drone_id: Drone identifier, e.g. ``"D3"``.

        Returns:
            The ``Color`` assigned to that drone's index.
        """
        return Colors.ORBS[(int(drone_id[1:]) - 1) % len(Colors.ORBS)]

    def _role_of(self, name: Any) -> str:
        """Classify a zone as start, goal, dead, path, or structural.

        Args:
            name: Zone key to classify.

        Returns:
            One of ``"start"``, ``"goal"``, ``"dead"``, ``"path"``
            or ``"struct"``.
        """
        k = str(name)
        if k == str(self.start_id):
            return "start"
        if k == str(self.end_id):
            return "goal"
        zone = self.parsed.zones.get(k)
        if zone and zone.zone_type == "blocked":
            return "dead"
        if k in self.used_nodes:
            return "path"
        return "struct"

    def _node_color(self, name: Any, zone: Any) -> Color:
        """Pick the display color for a zone node.

        Args:
            name: Zone key.
            zone: The zone object (used for its declared map color).

        Returns:
            The ``Color`` to draw this node with. Falls back to
            ``Colors.STRUCT`` if the zone's declared color maps to
            no color (e.g. an explicit ``"none"`` entry), so drawing
            never receives ``None`` in place of a ``Color``.
        """
        role = self._role_of(name)
        role_map = {
            "start": Colors.START,
            "goal": Colors.GOAL,
            "dead": Colors.DEAD,
            "path": Colors.PATH,
            "struct": Colors.STRUCT,
        }
        if role in ("start", "goal", "dead"):
            return role_map[role]
        fallback = role_map[role]
        color_key = getattr(zone, "color", None)
        key = str(color_key) if color_key is not None else "none"
        return Colors.MAP_COLORS.get(key, fallback) or fallback

    def _node_radius(self, name: Any) -> float:
        """Compute the draw radius of a zone node.

        Args:
            name: Zone key.

        Returns:
            The node radius in pixels, scaled by connection degree
            for non-start/goal nodes.
        """
        if self._role_of(name) in ("start", "goal"):
            return 13.0
        return 6.0 + min(self.degree.get(str(name), 1), 5) * 1.1

    def update(self, dt: float, app: AppProtocol) -> None:
        """Advance the turn-by-turn drone animation and handle input.

        Args:
            dt: Elapsed time in seconds since the last update
                (unused directly; animation is frame-counter based).
            app: The owning application, used to return to the map
                picker on a right click.
        """
        if not self.is_done:
            self.frame_counter += 1
            if self.frame_counter >= self.turn_frames:
                self.frame_counter = 0
                if self.tour_sim < self.max_tours:
                    self.tour_sim += 1
                    for d in self.drone_ids:
                        self.drone_from[d] = self.drone_to[d]
                    if self.tour_sim in self.par_tour:
                        for d, dest in self.par_tour[self.tour_sim]:
                            self.drone_to[d] = dest
                            p = self.positions.get(dest)
                            if p and dest in self.parsed.zones:
                                self.pulses.append({
                                    "x": p[0],
                                    "y": p[1],
                                    "t": 0.0,
                                    "color": self._orb_color(d),
                                })
                else:
                    for d in self.drone_ids:
                        self.drone_from[d] = self.drone_to[d]
                    self.frame_counter = self.turn_frames
                    self.is_done = True

        for pu in self.pulses:
            pu["t"] += 0.035
        self.pulses = [p for p in self.pulses if p["t"] < 1.0]

        if is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_RIGHT):
            app.change_scene(MapSelectScene())

    def draw(self) -> None:
        """Render connections, pulses, nodes, drones, and the HUD."""
        t = self.frame_counter / self.turn_frames
        ts = t * t * (3 - 2 * t)

        self._draw_connections()

        for pu in self.pulses:
            r = 10 + pu["t"] * 46
            Renderer.glow_ring(
                pu["x"], pu["y"], r, 1.6, pu["color"],
                120 * (1 - pu["t"]) ** 2,
            )

        self._draw_nodes()
        self._draw_drones(ts)
        self._draw_ui()

    def _draw_connections(self) -> None:
        """Draw edges between zones, highlighting the used path."""
        for u, v in self.connections:
            p1, p2 = self.positions.get(u), self.positions.get(v)
            if not (p1 and p2):
                continue
            hot = str(u) in self.used_nodes and str(v) in self.used_nodes
            ax, ay, bx, by = p1[0], p1[1], p2[0], p2[1]
            dx, dy = bx - ax, by - ay
            dist = math.hypot(dx, dy)
            if dist < 1:
                continue
            ux, uy = dx / dist, dy / dist
            ra = self._node_radius(u) + 3
            rb = self._node_radius(v) + 3
            a = Vector2(ax + ux * ra, ay + uy * ra)
            b = Vector2(bx - ux * rb, by - uy * rb)

            if hot:
                zv = self.parsed.zones.get(v)
                line_col = self._node_color(v, zv) if zv else Colors.PATH
                Renderer.glow_line(a, b, 1.6, line_col, 150)
            else:
                draw_line_ex(a, b, 1.2, Colors.EDGE_IDLE)

    def _draw_nodes(self) -> None:
        """Draw every zone node, plus hover labels near the cursor."""
        breathe = 1.0 + math.sin(get_time() * 2.0) * 0.06
        mouse = get_mouse_position()

        for name, zone in self.nodes_sorted:
            p = self.positions.get(name)
            if not p:
                continue
            px, py = p
            role = self._role_of(name)
            col = self._node_color(name, zone)
            r = self._node_radius(name)

            if role in ("start", "goal"):
                Renderer.glow_ring(px, py, r * breathe, 2.2, col, 210)
                begin_blend_mode(BlendMode.BLEND_ADDITIVE)
                draw_circle_v(
                    Vector2(px, py), r * 2.6, Renderer.with_alpha(col, 26)
                )
                end_blend_mode()
                draw_circle_v(
                    Vector2(px, py), r - 2, Renderer.with_alpha(col, 48)
                )
            else:
                draw_circle_v(Vector2(px, py), r, Color(14, 18, 24, 255))
                if role == "path":
                    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
                    draw_circle_v(
                        Vector2(px, py),
                        r * 1.8,
                        Renderer.with_alpha(col, 22),
                    )
                    end_blend_mode()
                    Renderer.glow_ring(px, py, r, 1.7, col, 175)
                else:
                    dead_alpha = 210 if role == "dead" else 95
                    draw_ring(
                        Vector2(px, py), r - 0.9, r + 0.9, 0, 360, 32,
                        Renderer.with_alpha(col, dead_alpha),
                    )

            if zone.zone_type == "restricted":
                draw_ring(
                    Vector2(px, py), r + 4, r + 5.2, 0, 360, 32,
                    Renderer.with_alpha(Colors.DEAD, 200),
                )
            elif zone.zone_type == "priority":
                draw_circle_v(
                    Vector2(px, py), 2.4, Renderer.with_alpha(Colors.GOAL, 230)
                )

            near = math.hypot(mouse.x - px, mouse.y - py) < 26
            if role in ("start", "goal") or near or role == "path":
                if role in ("start", "goal"):
                    alpha, size = 255, 14
                elif near:
                    alpha, size = 255, 13
                else:
                    alpha, size = 130, 11
                txt = str(name)
                w = measure_text(txt, size)
                offset = (int(abs(zone.x) + abs(zone.y)) % 2) * (size + 3)
                ty = py + r + 8 + offset
                draw_text(
                    txt, int(px - w / 2) + 1, int(ty) + 1, size,
                    Color(0, 0, 0, alpha),
                )
                draw_text(
                    txt, int(px - w / 2), int(ty), size,
                    Color(232, 238, 244, alpha),
                )

    def _draw_drones(self, ts: float) -> None:
        """Draw each drone's glowing trail and current position.

        Args:
            ts: Smoothed (eased) progress through the current turn,
                in ``[0, 1]``.
        """
        for d in self.drone_ids:
            pf = self.positions.get(self.drone_from[d])
            pt = self.positions.get(self.drone_to[d])
            if not (pf and pt):
                continue
            n = int(d[1:])
            cx = pf[0] + (pt[0] - pf[0]) * ts + math.cos(n * 1.7) * 7.0
            cy = pf[1] + (pt[1] - pf[1]) * ts + math.sin(n * 1.7) * 7.0

            self.trails[d].append((cx, cy))
            color = self._orb_color(d)
            pts = list(self.trails[d])

            begin_blend_mode(BlendMode.BLEND_ADDITIVE)
            for i, (tx, ty) in enumerate(pts[:-1]):
                k = (i + 1) / len(pts)
                draw_circle_v(
                    Vector2(tx, ty),
                    1.2 + 3.2 * k,
                    Renderer.with_alpha(color, 70 * k ** 2.2),
                )
            end_blend_mode()
            Renderer.glow_dot(cx, cy, 4.6, color)

    def _draw_ui(self) -> None:
        """Draw the turn counter, progress bar, and footer hints."""
        label = f"TOUR {self.tour_sim:02d} / {self.max_tours}"
        w = Renderer.measure_spaced(label, 18, 3)
        draw_rectangle(24, 26, 3, 24, Colors.PATH)
        Renderer.draw_text_spaced(label, 40, 27, 18, Colors.TEXT, 3)

        prog = self.tour_sim / self.max_tours if self.max_tours else 0
        draw_rectangle(40, 58, int(w), 2, Color(255, 255, 255, 28))
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_rectangle(
            40, 57, int(w * prog), 4, Renderer.with_alpha(Colors.PATH, 60)
        )
        end_blend_mode()
        draw_rectangle(40, 58, int(w * prog), 2, Colors.PATH)

        draw_text(f"{len(self.drone_ids)} drones", 40, 74, 11, Colors.MUTED)
        hint = (
            "anneau = restricted (2 tours)   point = priority   "
            "clic droit = retour menu"
        )
        draw_text(hint, 40, self.screen_h - 30, 11, Colors.MUTED)

        if self.is_done:
            Renderer.draw_text_spaced(
                "ARRIVEE", 40, 92, 13, Colors.GOAL, 2
            )

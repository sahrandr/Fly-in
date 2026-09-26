import os
import sys
import math
from collections import deque
from pyray import *
from ui import Colors, Renderer, Button, MiniPath
from parser import MapParser, MapParsingError
from algo import Simulator

class Scene:
    def update(self, dt, app):
        pass
    def draw(self):
        pass


class TitleScene(Scene):
    def __init__(self, has_save=False):
        self.screen_w = get_screen_width()
        self.screen_h = get_screen_height()
        
        panel_w = max(380, int(self.screen_w * 0.32))
        btn_w = min(300, panel_w - 80)
        btn_h = 50
        gap = 14
        self.btn_x = (panel_w - btn_w) // 2

        total_ui_h = 110 + (3 * btn_h + 2 * gap)
        start_y = max(60, (self.screen_h - total_ui_h) // 2)
        self.title_y = start_y
        buttons_y = self.title_y + 110

        self.preview = MiniPath(panel_w + 40, int(self.screen_h * 0.12), 
                                self.screen_w - (panel_w + 40) - 60, int(self.screen_h * 0.76))

        self.buttons = {
            "new": Button("NEW GAME", self.btn_x, buttons_y, btn_w, btn_h),
            "continue": Button("CONTINUER", self.btn_x, buttons_y + 1 * (btn_h + gap), btn_w, btn_h, enabled=has_save),
            "settings": Button("PARAMETRES", self.btn_x, buttons_y + 2 * (btn_h + gap), btn_w, btn_h, enabled=has_save),
            "quit": Button("QUIT", self.btn_x, buttons_y + 3 * (btn_h + gap), btn_w, btn_h),
        }
        self.t0 = get_time()

    def update(self, dt, app):
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)
        self.preview.update(dt)

        if self.buttons["new"].update(mouse, pressed, dt):
            app.change_scene(MapSelectScene())
        elif self.buttons["quit"].update(mouse, pressed, dt):
            app.quit()

    def draw(self):
        self.preview.draw()
        Renderer.draw_text_spaced("FLY-IN", self.btn_x, self.title_y, 40, Colors.TEXT, 5)
        Renderer.draw_text_spaced("ESTHÉTIQUE DARK / NEON", self.btn_x + 2, self.title_y + 52, 11, Renderer.with_alpha(Colors.MUTED, 220), 3)

        breathe = 1.0 + math.sin((get_time() - self.t0) * 1.4) * 0.08
        Renderer.glow_ring(self.btn_x + 6, self.title_y - 14, 3 * breathe, 1.2, Colors.PATH, 200)

        for btn in self.buttons.values():
            btn.draw()
       # Ligne 64 dans scenes.py
        draw_text("15 drones  ·  26 tours  ·  carte: ultimate_challenge", int(self.btn_x), int(self.screen_h - 46), 11, Renderer.with_alpha(Colors.MUTED, 150))

class MapSelectScene(Scene):
    def __init__(self, maps_root="maps"):
        self.screen_w = get_screen_width()
        self.screen_h = get_screen_height()
        self.maps_root = maps_root
        self.categories = self._scan_maps()
        
        cat_order = ["easy", "medium", "hard", "challenger"]
        self.cat_names = [c for c in cat_order if c in self.categories] + \
                         sorted(c for c in self.categories if c not in cat_order)

        self.cat_colors = {"easy": Colors.START, "medium": Colors.GOAL, 
                           "hard": Colors.HARD, "challenger": Colors.CHALLENGER}
        
        col_w = 250
        gap_x = 26
        total_w = len(self.cat_names) * col_w + max(0, len(self.cat_names) - 1) * gap_x
        self.start_x = max(60, (self.screen_w - total_w) // 2)
        
        self.headers = []
        self.entries = []
        
        top_y = 190
        for i, cat in enumerate(self.cat_names):
            cx = self.start_x + i * (col_w + gap_x)
            color = self.cat_colors.get(cat, Colors.PATH)
            self.headers.append((cat.upper(), cx, top_y, color))
            for j, path in enumerate(self.categories[cat]):
                label = self._format_name(os.path.basename(path))
                by = top_y + 38 + j * 48
                self.entries.append((Button(label, cx, by, col_w, 38, accent=color), path))

    def _scan_maps(self):
        cats = {}
        if os.path.isdir(self.maps_root):
            for entry in sorted(os.listdir(self.maps_root)):
                cat_path = os.path.join(self.maps_root, entry)
                if os.path.isdir(cat_path):
                    files = sorted(f for f in os.listdir(cat_path) if f.endswith(".txt"))
                    if files:
                        cats[entry] = [os.path.join(cat_path, f) for f in files]
        return cats

    def _format_name(self, filename):
        name = filename[:-4] if filename.endswith(".txt") else filename
        parts = name.split("_", 1)
        if parts[0].isdigit() and len(parts) > 1:
            return f"{parts[0]} \u00b7 {parts[1].replace('_', ' ').upper()}"
        return name.replace("_", " ").upper()

    def update(self, dt, app):
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)
        for btn, path in self.entries:
            if btn.update(mouse, pressed, dt):
                app.change_scene(SimulationScene(path))

    def draw(self):
        Renderer.draw_text_spaced("CHOISIS UNE CARTE", self.start_x, 70, 30, Colors.TEXT, 4)
        Renderer.draw_text_spaced("clique une carte pour lancer la simulation", self.start_x + 2, 108, 11, Renderer.with_alpha(Colors.MUTED, 220), 3)

        for text, hx, hy, color in self.headers:
            draw_rectangle(int(hx), int(hy) - 2, 3, 16, color)
            Renderer.draw_text_spaced(text, hx + 10, hy - 2, 13, color, 2)

        for btn, _ in self.entries:
            btn.draw()
        
        if not self.entries:
            draw_text(f"aucune carte trouvée dans '{self.maps_root}/'", self.start_x, 210, 14, Renderer.with_alpha(Colors.MUTED, 220))


class SimulationScene(Scene):
    def __init__(self, map_path):
        try:
            self.parsed = MapParser(map_path).parse()
            self.simulator = Simulator(self.parsed)
            self.par_tour = self.simulator.run()
        except (MapParsingError, ValueError) as err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)

        self.screen_w = get_screen_width()
        self.screen_h = get_screen_height()
        self._init_geometry()
        self._init_state()

    def _init_geometry(self):
        pad_x, pad_y = 110, 90
        xs = [z.x for z in self.parsed.zones.values()]
        ys = [z.y for z in self.parsed.zones.values()]
        span_x, span_y = max(1e-6, max(xs) - min(xs)), max(1e-6, max(ys) - min(ys))
        self.scale = min((self.screen_w - 2 * pad_x) / span_x, (self.screen_h - 2 * pad_y) / span_y)
        self.ox = (self.screen_w - span_x * self.scale) / 2 - min(xs) * self.scale
        self.oy = (self.screen_h - span_y * self.scale) / 2 - min(ys) * self.scale

        self.positions = {}
        for key, zone in self.parsed.zones.items():
            pos = (zone.x * self.scale + self.ox, zone.y * self.scale + self.oy)
            for k in {key, str(key), getattr(zone, "name", None)}:
                if k: self.positions[k] = pos

        for conn in self.parsed.connections:
            pa, pb = self.positions[conn.zone_a], self.positions[conn.zone_b]
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            self.positions[f"{conn.zone_a}-{conn.zone_b}"] = mid
            self.positions[f"{conn.zone_b}-{conn.zone_a}"] = mid

        self.connections = []
        self.degree = {}
        for conn in self.parsed.connections:
            a, b = getattr(conn, "zone_a", None), getattr(conn, "zone_b", None)
            if a and b:
                self.connections.append((a, b))
                self.degree[str(a)] = self.degree.get(str(a), 0) + 1
                self.degree[str(b)] = self.degree.get(str(b), 0) + 1

        self.start_id = getattr(self.parsed, "start_zone", None)
        self.end_id = getattr(self.parsed, "end_zone", getattr(self.parsed, "target_zone", None))
        
        self.used_nodes = {str(self.start_id)}
        for moves in self.par_tour.values():
            for _, dest in moves:
                self.used_nodes.add(str(dest))

    def _init_state(self):
        self.drone_ids = [f"D{i}" for i in range(1, self.parsed.nb_drones + 1)]
        self.drone_from = {d: self.parsed.start_zone for d in self.drone_ids}
        self.drone_to = {d: self.parsed.start_zone for d in self.drone_ids}
        self.trails = {d: deque(maxlen=14) for d in self.drone_ids}
        
        self.pulses = []
        self.tour_sim = 0
        self.max_tours = max(self.par_tour.keys()) if self.par_tour else 0
        self.turn_frames = 48
        self.frame_counter = 0
        self.is_done = False
        self.nodes_sorted = list(self.parsed.zones.items())

    def _orb_color(self, drone_id):
        return Colors.ORBS[(int(drone_id[1:]) - 1) % len(Colors.ORBS)]

    def _role_of(self, name):
        k = str(name)
        if k == str(self.start_id): return "start"
        if k == str(self.end_id): return "goal"
        if self.parsed.zones.get(k) and self.parsed.zones[k].zone_type == "blocked": return "dead"
        if k in self.used_nodes: return "path"
        return "struct"

    def _node_color(self, name, zone):
        role = self._role_of(name)
        role_map = {"start": Colors.START, "goal": Colors.GOAL, "dead": Colors.DEAD, 
                    "path": Colors.PATH, "struct": Colors.STRUCT}
        if role in ("start", "goal", "dead"): return role_map[role]
        return Colors.MAP_COLORS.get(getattr(zone, "color", None), role_map[role])

    def _node_radius(self, name):
        if self._role_of(name) in ("start", "goal"): return 13.0
        return 6.0 + min(self.degree.get(str(name), 1), 5) * 1.1

    def update(self, dt, app):
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
                                self.pulses.append({"x": p[0], "y": p[1], "t": 0.0, "color": self._orb_color(d)})
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

    def draw(self):
        t = self.frame_counter / self.turn_frames
        ts = t * t * (3 - 2 * t)
        
        self._draw_connections()
        
        for pu in self.pulses:
            r = 10 + pu["t"] * 46
            Renderer.glow_ring(pu["x"], pu["y"], r, 1.6, pu["color"], 120 * (1 - pu["t"]) ** 2)
            
        self._draw_nodes()
        self._draw_drones(ts)
        self._draw_ui()

    def _draw_connections(self):
        for u, v in self.connections:
            p1, p2 = self.positions.get(u), self.positions.get(v)
            if not (p1 and p2): continue
            hot = str(u) in self.used_nodes and str(v) in self.used_nodes
            ax, ay, bx, by = p1[0], p1[1], p2[0], p2[1]
            dx, dy = bx - ax, by - ay
            dist = math.hypot(dx, dy)
            if dist < 1: continue
            ux, uy = dx / dist, dy / dist
            ra, rb = self._node_radius(u) + 3, self._node_radius(v) + 3
            a, b = Vector2(ax + ux * ra, ay + uy * ra), Vector2(bx - ux * rb, by - uy * rb)
            
            if hot:
                zv = self.parsed.zones.get(v)
                line_col = self._node_color(v, zv) if zv else Colors.PATH
                Renderer.glow_line(a, b, 1.6, line_col, 150)
            else:
                draw_line_ex(a, b, 1.2, Colors.EDGE_IDLE)

    def _draw_nodes(self):
        breathe = 1.0 + math.sin(get_time() * 2.0) * 0.06
        mouse = get_mouse_position()
        
        for name, zone in self.nodes_sorted:
            p = self.positions.get(name)
            if not p: continue
            px, py = p
            role, col, r = self._role_of(name), self._node_color(name, zone), self._node_radius(name)

            if role in ("start", "goal"):
                Renderer.glow_ring(px, py, r * breathe, 2.2, col, 210)
                begin_blend_mode(BlendMode.BLEND_ADDITIVE)
                draw_circle_v(Vector2(px, py), r * 2.6, Renderer.with_alpha(col, 26))
                end_blend_mode()
                draw_circle_v(Vector2(px, py), r - 2, Renderer.with_alpha(col, 48))
            else:
                draw_circle_v(Vector2(px, py), r, Color(14, 18, 24, 255))
                if role == "path":
                    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
                    draw_circle_v(Vector2(px, py), r * 1.8, Renderer.with_alpha(col, 22))
                    end_blend_mode()
                    Renderer.glow_ring(px, py, r, 1.7, col, 175)
                else:
                    draw_ring(Vector2(px, py), r - 0.9, r + 0.9, 0, 360, 32, Renderer.with_alpha(col, 210 if role == "dead" else 95))

            if zone.zone_type == "restricted":
                draw_ring(Vector2(px, py), r + 4, r + 5.2, 0, 360, 32, Renderer.with_alpha(Colors.DEAD, 200))
            elif zone.zone_type == "priority":
                draw_circle_v(Vector2(px, py), 2.4, Renderer.with_alpha(Colors.GOAL, 230))
                
            # Labels hover
            near = math.hypot(mouse.x - px, mouse.y - py) < 26
            if role in ("start", "goal") or near or role == "path":
                alpha, size = (255, 14) if role in ("start", "goal") else ((255, 13) if near else (130, 11))
                txt = str(name)
                w = measure_text(txt, size)
                ty = py + r + 8 + (int(abs(zone.x) + abs(zone.y)) % 2) * (size + 3)
                draw_text(txt, int(px - w / 2) + 1, int(ty) + 1, size, Color(0, 0, 0, alpha))
                draw_text(txt, int(px - w / 2), int(ty), size, Color(232, 238, 244, alpha))

    def _draw_drones(self, ts):
        for d in self.drone_ids:
            pf, pt = self.positions.get(self.drone_from[d]), self.positions.get(self.drone_to[d])
            if not (pf and pt): continue
            n = int(d[1:])
            cx = pf[0] + (pt[0] - pf[0]) * ts + math.cos(n * 1.7) * 7.0
            cy = pf[1] + (pt[1] - pf[1]) * ts + math.sin(n * 1.7) * 7.0
            
            self.trails[d].append((cx, cy))
            color = self._orb_color(d)
            pts = list(self.trails[d])
            
            begin_blend_mode(BlendMode.BLEND_ADDITIVE)
            for i, (tx, ty) in enumerate(pts[:-1]):
                k = (i + 1) / len(pts)
                draw_circle_v(Vector2(tx, ty), 1.2 + 3.2 * k, Renderer.with_alpha(color, 70 * k ** 2.2))
            end_blend_mode()
            Renderer.glow_dot(cx, cy, 4.6, color)

    def _draw_ui(self):
        label = f"TOUR {self.tour_sim:02d} / {self.max_tours}"
        w = Renderer.measure_spaced(label, 18, 3)
        draw_rectangle(24, 26, 3, 24, Colors.PATH)
        Renderer.draw_text_spaced(label, 40, 27, 18, Colors.TEXT, 3)
        
        prog = self.tour_sim / self.max_tours if self.max_tours else 0
        draw_rectangle(40, 58, int(w), 2, Color(255, 255, 255, 28))
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_rectangle(40, 57, int(w * prog), 4, Renderer.with_alpha(Colors.PATH, 60))
        end_blend_mode()
        draw_rectangle(40, 58, int(w * prog), 2, Colors.PATH)

        draw_text(f"{len(self.drone_ids)} drones", 40, 74, 11, Colors.MUTED)
        draw_text("anneau = restricted (2 tours)   point = priority   clic droit = retour menu", 40, self.screen_h - 30, 11, Colors.MUTED)

        if self.is_done:
            Renderer.draw_text_spaced("ARRIVEE", 40, 92, 13, Colors.GOAL, 2)
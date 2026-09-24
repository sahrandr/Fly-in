from pyray import *
from title_screen import run_title_screen
from map_select import run_map_select
import math
import sys
from collections import deque
from parser import MapParser, MapParsingError
from algo import Simulator

set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
init_window(0, 0, "Fly-in")
set_target_fps(60)

resultat = run_title_screen(has_save=False)

map_path = None
if resultat == "play":
    map_path = run_map_select()

if map_path:

    try:
        parsed = MapParser(map_path).parse()
        simulator = Simulator(parsed)
        par_tour = simulator.run()
    except (MapParsingError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        close_window()
        sys.exit(1)

    simulator.display(par_tour)
    print(f"Total turns: {max(par_tour) if par_tour else 0}")

    SCREEN_W = get_screen_width() 
    SCREEN_H = get_screen_height()
    PAD_X, PAD_Y = 110, 90

    C_BG = Color(8, 10, 15, 255)
    C_GRID = Color(255, 255, 255, 6)

    C_STRUCT = Color(64, 74, 92, 255)
    C_PATH = Color(90, 222, 204, 255)
    C_DEAD = Color(158, 62, 62, 255)
    C_START = Color(96, 230, 130, 255)
    C_GOAL = Color(255, 198, 70, 255)

    C_EDGE_IDLE = Color(92, 106, 130, 46)
    C_EDGE_HOT = Color(90, 222, 204, 70)

    ORB_COLORS = [
        Color(255, 150, 120, 255), Color(140, 235, 205, 255),
        Color(155, 190, 255, 255), Color(255, 214, 130, 255),
        Color(232, 152, 238, 255), Color(150, 238, 238, 255),
    ]

    # Couleur declaree par la carte elle-meme (zone.color dans le fichier .txt).
    # C'est la source de verite pour la teinte d'un hub -- pas le role.
    MAP_COLOR = {
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


    def orb_color(drone_id):
        return ORB_COLORS[(int(drone_id[1:]) - 1) % len(ORB_COLORS)]


    def with_alpha(color, alpha):
        return Color(color.r, color.g, color.b, max(0, min(255, int(alpha))))


    def shade(color, k):
        return Color(min(255, int(color.r * k)), min(255, int(color.g * k)),
                    min(255, int(color.b * k)), color.a)


    #  3. HELPERS DE RENDU
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


    #  4. CONNEXIONS
    connections = []
    if getattr(parsed, "connections", None):
        for conn in parsed.connections:
            a = getattr(conn, "zone_a", None)
            b = getattr(conn, "zone_b", None)
            if (a is None or b is None) and isinstance(conn, (tuple, list)) and len(conn) >= 2:
                a, b = conn[0], conn[1]
            if a is not None and b is not None:
                connections.append((a, b))
    elif getattr(parsed, "graph", None):
        for u, neighbors in parsed.graph.items():
            for v in neighbors:
                connections.append((u, v))


    def key_of(ref):
        return str(getattr(ref, "name", ref))


    #  5. ROLES
    start_zone_id = getattr(parsed, "start_zone", None)
    end_zone_id = getattr(parsed, "end_zone", getattr(parsed, "target_zone", None))

    used_nodes = {key_of(start_zone_id)}
    for _tour, moves in par_tour.items():
        for _d, dest in moves:
            used_nodes.add(key_of(dest))

    degree = {}
    for u, v in connections:
        degree[key_of(u)] = degree.get(key_of(u), 0) + 1
        degree[key_of(v)] = degree.get(key_of(v), 0) + 1


    def role_of(name):
        k = key_of(name)
        if k == key_of(start_zone_id):
            return "start"
        if k == key_of(end_zone_id):
            return "goal"
        zone = parsed.zones.get(k)
        if zone is not None and zone.zone_type == "blocked":
            return "dead"
        if k in used_nodes:
            return "path"
        return "struct"


    ROLE_COLOR = {"start": C_START, "goal": C_GOAL, "path": C_PATH,
                "dead": C_DEAD, "struct": C_STRUCT}


    def node_color(name, zone):
        """La teinte vient de la carte (zone.color). Le role ne sert que si la
        carte n'a rien declare (couleur absente ou 'none'), et pour start/goal
        qui gardent leur identite visuelle meme si la carte leur donne une couleur."""
        role = role_of(name)
        if role in ("start", "goal", "dead"):
            return ROLE_COLOR[role]
        mapped = MAP_COLOR.get(getattr(zone, "color", None))
        if mapped is not None:
            return mapped
        return ROLE_COLOR[role]

    #  6. PROJECTION 2D — les coords du parser, mises a l'echelle
    xs = [z.x for z in parsed.zones.values()]
    ys = [z.y for z in parsed.zones.values()]
    span_x = max(1e-6, max(xs) - min(xs))
    span_y = max(1e-6, max(ys) - min(ys))
    SCALE = min((SCREEN_W - 2 * PAD_X) / span_x, (SCREEN_H - 2 * PAD_Y) / span_y)
    ox = (SCREEN_W - span_x * SCALE) / 2 - min(xs) * SCALE
    oy = (SCREEN_H - span_y * SCALE) / 2 - min(ys) * SCALE

    zone_positions = {}
    for key, zone in parsed.zones.items():
        pos = (zone.x * SCALE + ox, zone.y * SCALE + oy)
        for k in {key, str(key), getattr(zone, "name", None)}:
            if k:
                zone_positions[k] = pos


    # Un drone en vol vers une zone restricted a pour destination le NOM DE
    # LA CONNEXION ("a-b") : on le place au milieu des deux zones.
    for conn in parsed.connections:
        pa = zone_positions[conn.zone_a]
        pb = zone_positions[conn.zone_b]
        mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
        zone_positions[f"{conn.zone_a}-{conn.zone_b}"] = mid
        zone_positions[f"{conn.zone_b}-{conn.zone_a}"] = mid


    def get_zone_pos(ref):
        if ref in zone_positions:
            return zone_positions[ref]
        return zone_positions.get(str(ref))


    def node_radius(name):
        role = role_of(name)
        if role in ("start", "goal"):
            return 13.0
        return 6.0 + min(degree.get(key_of(name), 1), 5) * 1.1


    #  7. ETAT
    drone_ids = [f"D{i}" for i in range(1, parsed.nb_drones + 1)]
    drone_from = {d: parsed.start_zone for d in drone_ids}
    drone_to = {d: parsed.start_zone for d in drone_ids}
    trails = {d: deque(maxlen=14) for d in drone_ids}
    pulses = []  # {x, y, t, color}

    tour_simulation = 0
    nombre_max_tours = max(par_tour.keys()) if par_tour else 0
    TURN_DURATION_FRAMES = 48
    turn_frame_counter = 0
    simulation_terminee = False  # une fois vrai, plus jamais reinitialise

    nodes_sorted = list(parsed.zones.items())

    while not window_should_close():
        if not simulation_terminee:
            turn_frame_counter += 1
            if turn_frame_counter >= TURN_DURATION_FRAMES:
                turn_frame_counter = 0
                if tour_simulation < nombre_max_tours:
                    tour_simulation += 1
                    for d in drone_ids:
                        drone_from[d] = drone_to[d]
                    if tour_simulation in par_tour:
                        for d, dest in par_tour[tour_simulation]:
                            drone_to[d] = dest
                            p = get_zone_pos(dest)
                            if p and dest in parsed.zones:
                                pulses.append({"x": p[0], "y": p[1], "t": 0.0,
                                            "color": orb_color(d)})
                else:
                    for d in drone_ids:
                        drone_from[d] = drone_to[d]
                    turn_frame_counter = TURN_DURATION_FRAMES
                    simulation_terminee = True

        for pu in pulses:
            pu["t"] += 0.035
        pulses = [p for p in pulses if p["t"] < 1.0]

        t = turn_frame_counter / TURN_DURATION_FRAMES
        ts = t * t * (3 - 2 * t)

        begin_drawing()
        clear_background(C_BG)

        for gx in range(0, SCREEN_W, 40):
            draw_line(gx, 0, gx, SCREEN_H, C_GRID)
        for gy in range(0, SCREEN_H, 40):
            draw_line(0, gy, SCREEN_W, gy, C_GRID)

        for u, v in connections:
            p1, p2 = get_zone_pos(u), get_zone_pos(v)
            if not (p1 and p2):
                continue
            hot = key_of(u) in used_nodes and key_of(v) in used_nodes
            ax, ay, bx, by = p1[0], p1[1], p2[0], p2[1]
            dx, dy = bx - ax, by - ay
            dist = math.hypot(dx, dy)
            if dist < 1:
                continue
            ux, uy = dx / dist, dy / dist
            ra, rb = node_radius(u) + 3, node_radius(v) + 3
            a = Vector2(ax + ux * ra, ay + uy * ra)
            b = Vector2(bx - ux * rb, by - uy * rb)
            if hot:
                zv = parsed.zones.get(v) if hasattr(parsed.zones, "get") else None
                line_col = node_color(v, zv) if zv is not None else C_PATH
                glow_line(a, b, 1.6, line_col, 150)
            else:
                draw_line_ex(a, b, 1.2, C_EDGE_IDLE)

        for pu in pulses:
            r = 10 + pu["t"] * 46
            glow_ring(pu["x"], pu["y"], r, 1.6, pu["color"], 120 * (1 - pu["t"]) ** 2)

        breathe = 1.0 + math.sin(get_time() * 2.0) * 0.06
        for name, zone in nodes_sorted:
            p = get_zone_pos(name)
            if not p:
                continue
            px, py = p
            role = role_of(name)
            col = node_color(name, zone)
            r = node_radius(name)

            if role in ("start", "goal"):
                glow_ring(px, py, r * breathe, 2.2, col, 210)
                begin_blend_mode(BlendMode.BLEND_ADDITIVE)
                draw_circle_v(Vector2(px, py), r * 2.6, with_alpha(col, 26))
                end_blend_mode()
                draw_circle_v(Vector2(px, py), r - 2, with_alpha(col, 48))
            elif role == "path":
                draw_circle_v(Vector2(px, py), r, Color(14, 18, 24, 255))
                begin_blend_mode(BlendMode.BLEND_ADDITIVE)
                draw_circle_v(Vector2(px, py), r * 1.8, with_alpha(col, 22))
                end_blend_mode()
                glow_ring(px, py, r, 1.7, col, 175)
            elif role == "dead":
                draw_circle_v(Vector2(px, py), r, Color(14, 18, 24, 255))
                draw_ring(Vector2(px, py), r - 0.9, r + 0.9, 0, 360, 32,
                        with_alpha(col, 210))
            else:
                draw_circle_v(Vector2(px, py), r, Color(14, 18, 24, 255))
                draw_ring(Vector2(px, py), r - 0.9, r + 0.9, 0, 360, 32,
                        with_alpha(col, 95))

            if zone.zone_type == "restricted":
                draw_ring(Vector2(px, py), r + 4, r + 5.2, 0, 360, 32,
                        with_alpha(C_DEAD, 200))
            elif zone.zone_type == "priority":
                draw_circle_v(Vector2(px, py), 2.4, with_alpha(C_GOAL, 230))

        positions = []
        for d in drone_ids:
            pf, pt = get_zone_pos(drone_from[d]), get_zone_pos(drone_to[d])
            if not (pf and pt):
                continue
            n = int(d[1:])
            off = 7.0
            cx = pf[0] + (pt[0] - pf[0]) * ts + math.cos(n * 1.7) * off
            cy = pf[1] + (pt[1] - pf[1]) * ts + math.sin(n * 1.7) * off
            positions.append((d, cx, cy))

        for d, cx, cy in positions:
            trails[d].append((cx, cy))
            color = orb_color(d)
            pts = list(trails[d])
            begin_blend_mode(BlendMode.BLEND_ADDITIVE)
            for i, (tx, ty) in enumerate(pts[:-1]):
                k = (i + 1) / len(pts)
                draw_circle_v(Vector2(tx, ty), 1.2 + 3.2 * k,
                            with_alpha(color, 70 * k ** 2.2))
            end_blend_mode()

        for d, cx, cy in positions:
            glow_dot(cx, cy, 4.6, orb_color(d))

        mouse = get_mouse_position()
        for name, zone in nodes_sorted:
            p = get_zone_pos(name)
            if not p:
                continue
            px, py = p
            role = role_of(name)
            near = math.hypot(mouse.x - px, mouse.y - py) < 26

            if role in ("start", "goal"):
                alpha, size = 255, 14
            elif near:
                alpha, size = 255, 13
            elif role == "path":
                alpha, size = 130, 11
            else:
                continue

            txt = key_of(name)
            w = measure_text(txt, size)
            parity = int(abs(zone.x) + abs(zone.y)) % 2
            ty = py + node_radius(name) + 8 + parity * (size + 3)
            tx = int(px - w / 2)
            draw_text(txt, tx + 1, int(ty) + 1, size, Color(0, 0, 0, alpha))
            draw_text(txt, tx, int(ty), size, Color(232, 238, 244, alpha))

        label = f"TOUR {tour_simulation:02d} / {nombre_max_tours}"
        w = measure_spaced(label, 18, 3)
        draw_rectangle(24, 26, 3, 24, C_PATH)
        draw_text_spaced(label, 40, 27, 18, Color(226, 236, 242, 255), 3)
        prog = tour_simulation / nombre_max_tours if nombre_max_tours else 0
        draw_rectangle(40, 58, int(w), 2, Color(255, 255, 255, 28))
        begin_blend_mode(BlendMode.BLEND_ADDITIVE)
        draw_rectangle(40, 57, int(w * prog), 4, with_alpha(C_PATH, 60))
        end_blend_mode()
        draw_rectangle(40, 58, int(w * prog), 2, C_PATH)

        draw_text(f"{len(drone_ids)} drones", 40, 74, 11, Color(120, 132, 148, 255))
        # draw_text(f"nbr_tours =" ,len(connections))
        draw_text("anneau externe = restricted (2 tours)   "
                  "point = priority   anneau rouge = blocked",
                  40, SCREEN_H - 30, 11, Color(120, 132, 148, 255))

        if simulation_terminee:
            done_label = "ARRIVEE"
            dw = measure_spaced(done_label, 13, 2)
            draw_text_spaced(done_label, 40, 92, 13, C_GOAL, 2)

        end_drawing()

close_window()
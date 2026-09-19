from pyray import *
from parser import MapParser
from algo import Simulator

# ============================================================
#  ETAPE 4 — roles et couleurs.
#  On lance la simulation UNIQUEMENT pour savoir quels noeuds
#  sont reellement empruntes (par_tour). Pas d'animation encore:
#  le but est de valider que le classement des roles a du sens
#  avant d'ajouter des billes qui bougent.
# ============================================================

SCREEN_W, SCREEN_H = 1200, 800
PAD_X, PAD_Y = 110, 90

parsed = MapParser("maps/hard/03_ultimate_challenge.txt").parse()
simulator = Simulator(parsed)
par_tour = simulator.run()

init_window(SCREEN_W, SCREEN_H, "Fly-in")
set_target_fps(60)

C_BG = Color(8, 10, 15, 255)
C_GRID = Color(255, 255, 255, 6)
C_EDGE_IDLE = Color(92, 106, 130, 46)
C_EDGE_HOT = Color(90, 222, 204, 90)

C_STRUCT = Color(64, 74, 92, 255)
C_PATH = Color(90, 222, 204, 255)
C_DEAD = Color(158, 62, 62, 255)
C_START = Color(96, 230, 130, 255)
C_GOAL = Color(255, 198, 70, 255)
ROLE_COLOR = {"start": C_START, "goal": C_GOAL, "path": C_PATH,
              "dead": C_DEAD, "struct": C_STRUCT}

# --- projection ---
xs = [z.x for z in parsed.zones.values()]
ys = [z.y for z in parsed.zones.values()]
span_x = max(1e-6, max(xs) - min(xs))
span_y = max(1e-6, max(ys) - min(ys))
SCALE = min((SCREEN_W - 2 * PAD_X) / span_x, (SCREEN_H - 2 * PAD_Y) / span_y)
ox = (SCREEN_W - span_x * SCALE) / 2 - min(xs) * SCALE
oy = (SCREEN_H - span_y * SCALE) / 2 - min(ys) * SCALE

zone_positions = {}
for key, zone in parsed.zones.items():
    zone_positions[key] = (zone.x * SCALE + ox, zone.y * SCALE + oy)


def get_zone_pos(ref):
    if ref in zone_positions:
        return zone_positions[ref]
    return zone_positions.get(str(ref))


def key_of(ref):
    return str(getattr(ref, "name", ref))


# --- connexions ---
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

# --- roles ---
start_zone_id = getattr(parsed, "start_zone", None)
end_zone_id = getattr(parsed, "end_zone", getattr(parsed, "target_zone", None))

used_nodes = {key_of(start_zone_id)}
for _tour, moves in par_tour.items():
    for _d, dest in moves:
        used_nodes.add(key_of(dest))


def role_of(name):
    k = key_of(name)
    s = k.lower()
    if k == key_of(start_zone_id) or s == "start":
        return "start"
    if k == key_of(end_zone_id) or s in ("goal", "end"):
        return "goal"
    if k in used_nodes:
        return "path"
    if "trap" in s or "dead_end" in s:
        return "dead"
    return "struct"


counts = {}
for name in parsed.zones:
    counts[role_of(name)] = counts.get(role_of(name), 0) + 1
print(f"[ETAPE 4] repartition des roles: {counts}")

while not window_should_close():
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
        col = C_EDGE_HOT if hot else C_EDGE_IDLE
        draw_line_ex(Vector2(*p1), Vector2(*p2), 1.6 if hot else 1.2, col)

    for name, zone in parsed.zones.items():
        p = get_zone_pos(name)
        if not p:
            continue
        role = role_of(name)
        r = 12 if role in ("start", "goal") else 7
        draw_circle_v(Vector2(*p), r, ROLE_COLOR[role])

    # legende, en bas a gauche
    legend = [("start", C_START), ("goal", C_GOAL), ("path", C_PATH),
              ("dead", C_DEAD), ("struct", C_STRUCT)]
    ly = SCREEN_H - 30
    lx = 24
    for label, col in legend:
        draw_circle_v(Vector2(lx, ly), 6, col)
        draw_text(label, lx + 14, ly - 7, 14, Color(200, 208, 218, 255))
        lx += 14 + measure_text(label, 14) + 24

    end_drawing()

close_window()
import math
from collections import deque
from pyray import *
from parser import MapParser
from algo import Simulator

#  1. PARSING ET SIMULATION
parsed = MapParser("maps/hard/03_ultimate_challenge.txt").parse()
simulator = Simulator(parsed)
par_tour = simulator.run()

FACTOR = 2
SCREEN_W, SCREEN_H = 1200, 800

init_window(SCREEN_W, SCREEN_H, "Fly-in")
set_target_fps(60)

chateau_texture = load_texture("assets/chateau.png")
dragon_texture = load_texture("assets/dragon.png")

DRAGON_FRAME_SIZE = 180.0
DRAGON_COLS, DRAGON_ROWS = 4, 2
DRAGON_TOTAL_FRAMES = DRAGON_COLS * DRAGON_ROWS
DRAGON_ANIM_SPEED = 8

CHATEAU_SCALE_BASE = 0.35
DRAGON_SCALE_BASE = 0.45
TILE_WIDTH_BASE = 80.0
TILE_HEIGHT_BASE = 40.0

#  2. PALETTE — 4 roles, pas 9 teintes
# Le principe: la couleur encode le ROLE, pas l'index du noeud.
C_BG = Color(9, 11, 16, 255)
C_TILE_A = Color(18, 21, 28, 255)
C_TILE_B = Color(21, 25, 33, 255)
C_GRID = Color(255, 255, 255, 8)

C_STRUCT = Color(52, 60, 76, 255)      # noeud hors chemin: neutre, il recule
C_PATH = Color(90, 222, 204, 255)      # noeud sur un chemin emprunte: accent
C_DEAD = Color(150, 58, 58, 255)       # piege / cul-de-sac: rouge sourd
C_START = Color(96, 230, 130, 255)
C_GOAL = Color(255, 200, 70, 255)

C_EDGE_IDLE = Color(80, 96, 120, 60)
C_EDGE_HOT = Color(90, 222, 204, 110)
C_EDGE_CORE = Color(200, 255, 248, 200)

DRAGON_COLORS = [
    Color(255, 140, 120, 255), Color(140, 235, 200, 255),
    Color(150, 190, 255, 255), Color(255, 214, 130, 255),
    Color(230, 150, 235, 255), Color(150, 235, 235, 255),
]


def couleur_pour_drone(drone_id):
    return DRAGON_COLORS[(int(drone_id[1:]) - 1) % len(DRAGON_COLORS)]


def shade(c, k, alpha=None):
    return Color(
        max(0, min(255, int(c.r * k))),
        max(0, min(255, int(c.g * k))),
        max(0, min(255, int(c.b * k))),
        c.a if alpha is None else alpha,
    )


#  3. GEOMETRIE ISOMETRIQUE
def map_to_iso_raw(x, y):
    return (x - y) * (TILE_WIDTH_BASE / 2), (x + y) * (TILE_HEIGHT_BASE / 2)


def draw_iso_tile_flat(sx, sy, tw, th, color, outline=None):
    hw, hh = tw / 2, th / 2
    top = Vector2(sx, sy - hh)
    right = Vector2(sx + hw, sy)
    bottom = Vector2(sx, sy + hh)
    left = Vector2(sx - hw, sy)
    draw_triangle(top, left, bottom, color)
    draw_triangle(top, bottom, right, color)
    if outline:
        draw_line_v(top, right, outline)
        draw_line_v(right, bottom, outline)
        draw_line_v(bottom, left, outline)
        draw_line_v(left, top, outline)


def draw_iso_pillar(sx, sy, tw, th, depth, base_color, glow=0.0):
    """glow: 0..1 — halo au moment ou un dragon arrive sur le noeud."""
    hw, hh = tw / 2, th / 2

    if glow > 0.01:
        for i, k in enumerate((2.2, 1.7, 1.3)):
            a = int(70 * glow / (i + 1))
            draw_iso_tile_flat(sx, sy, tw * k, th * k, shade(base_color, 1.0, a))

    top = Vector2(sx, sy - hh - depth)
    right = Vector2(sx + hw, sy - depth)
    bottom = Vector2(sx, sy + hh - depth)
    left = Vector2(sx - hw, sy - depth)
    base_bottom = Vector2(sx, sy + hh)
    base_left = Vector2(sx - hw, sy)
    base_right = Vector2(sx + hw, sy)

    lift = 1.0 + glow * 0.45
    face_l = shade(base_color, 0.42 * lift)
    face_r = shade(base_color, 0.22 * lift)
    face_t = shade(base_color, lift)

    draw_triangle(left, base_left, base_bottom, face_l)
    draw_triangle(left, base_bottom, bottom, face_l)
    draw_triangle(bottom, base_bottom, base_right, face_r)
    draw_triangle(bottom, base_right, right, face_r)
    draw_triangle(top, left, bottom, face_t)
    draw_triangle(top, bottom, right, face_t)

    draw_line_v(top, left, Color(255, 255, 255, 26))
    draw_line_v(top, right, Color(255, 255, 255, 26))
    draw_line_v(left, bottom, Color(0, 0, 0, 110))
    draw_line_v(bottom, right, Color(0, 0, 0, 110))
    draw_line_v(bottom, base_bottom, Color(0, 0, 0, 110))


def draw_texture_centered(texture, x, y, scale, tint):
    w = texture.width * scale
    h = texture.height * scale
    draw_texture_ex(texture, Vector2(x - w / 2, y - h), 0.0, scale, tint)


def draw_dragon_frame(texture, frame_index, x, y, scale, tint):
    col = frame_index % DRAGON_COLS
    row = frame_index // DRAGON_COLS
    src = Rectangle(col * DRAGON_FRAME_SIZE, row * DRAGON_FRAME_SIZE,
                    DRAGON_FRAME_SIZE, DRAGON_FRAME_SIZE)
    w = h = DRAGON_FRAME_SIZE * scale
    draw_texture_pro(texture, src, Rectangle(x - w / 2, y - h, w, h),
                     Vector2(0, 0), 0.0, tint)


def draw_text_spaced(text, x, y, size, color, spacing=2):
    """draw_text ne gere pas le letter-spacing: on ecrit caractere par caractere."""
    cx = x
    for ch in text:
        draw_text(ch, int(cx), int(y), size, color)
        cx += measure_text(ch, size) + spacing
    return cx - x


def measure_spaced(text, size, spacing=2):
    return sum(measure_text(c, size) + spacing for c in text) - spacing


#  4. CONNEXIONS (une seule extraction, robuste)
connections = []
if getattr(parsed, "connections", None):
    for conn in parsed.connections:
        a = getattr(conn, "zone_a", None)
        b = getattr(conn, "zone_b", None)
        if a is None or b is None and isinstance(conn, (tuple, list)) and len(conn) >= 2:
            a, b = conn[0], conn[1]
        if a is not None and b is not None:
            connections.append((a, b))
elif getattr(parsed, "graph", None):
    for u, neighbors in parsed.graph.items():
        for v in neighbors:
            connections.append((u, v))

#  5. ROLES: quels noeuds sont reellement emprunts
start_zone_id = getattr(parsed, "start_zone", None)
end_zone_id = getattr(parsed, "end_zone", getattr(parsed, "target_zone", None))


def key_of(ref):
    return str(getattr(ref, "name", ref))


# noeuds traverses par au moins un dragon pendant la simulation
used_nodes = {key_of(start_zone_id)}
for tour, moves in par_tour.items():
    for _d, dest in moves:
        used_nodes.add(key_of(dest))


def role_of(name, zone):
    k = key_of(name)
    s = k.lower()
    if k == key_of(start_zone_id) or "start" in s:
        return "start"
    if k == key_of(end_zone_id) or s in ("goal", "end"):
        return "goal"
    if k in used_nodes:
        return "path"
    if "trap" in s or "dead_end" in s:
        return "dead"
    return "struct"


ROLE_COLOR = {"start": C_START, "goal": C_GOAL, "path": C_PATH,
              "dead": C_DEAD, "struct": C_STRUCT}

#  6. ZOOM ET CENTRAGE — sol resserre (le vide mangeait l'ecran)
all_x = [z.x * FACTOR for z in parsed.zones.values()]
all_y = [z.y * FACTOR for z in parsed.zones.values()]
MARGIN_TILES = 1  # etait 3: 2 rangees de damier vide en moins de chaque cote
min_x, max_x = min(all_x) - MARGIN_TILES, max(all_x) + MARGIN_TILES
min_y, max_y = min(all_y) - MARGIN_TILES, max(all_y) + MARGIN_TILES

terrain_map = {}
for x in range(min_x, max_x + 1):
    for y in range(min_y, max_y + 1):
        terrain_map[(x, y)] = C_TILE_A if (x + y) % 2 == 0 else C_TILE_B

castle_iso_raw = [map_to_iso_raw(z.x * FACTOR, z.y * FACTOR) for z in parsed.zones.values()]
c_xs = [p[0] for p in castle_iso_raw]
c_ys = [p[1] for p in castle_iso_raw]
width_needed = (max(c_xs) - min(c_xs)) + TILE_WIDTH_BASE * 3
height_needed = (max(c_ys) - min(c_ys)) + TILE_HEIGHT_BASE * 5

ZOOM_RAW = min((SCREEN_W - 80.0) / width_needed, (SCREEN_H - 100.0) / height_needed)
ZOOM = max(0.55, min(1.35, ZOOM_RAW))

TILE_WIDTH = TILE_WIDTH_BASE * ZOOM
TILE_HEIGHT = TILE_HEIGHT_BASE * ZOOM
CHATEAU_SCALE = CHATEAU_SCALE_BASE * ZOOM
DRAGON_SCALE = DRAGON_SCALE_BASE * max(0.75, ZOOM)
BLOCK_DEPTH = 25.0 * ZOOM


def map_to_iso(x, y):
    return (x - y) * (TILE_WIDTH / 2), (x + y) * (TILE_HEIGHT / 2)


all_iso = [map_to_iso(gx, gy) for (gx, gy) in terrain_map.keys()]
z_xs = [p[0] for p in all_iso]
z_ys = [p[1] for p in all_iso]
OFFSET_X = SCREEN_W / 2 - (min(z_xs) + max(z_xs)) / 2
OFFSET_Y = SCREEN_H / 2 - (min(z_ys) + max(z_ys)) / 2

zone_positions = {}
for key, zone in parsed.zones.items():
    px, py = map_to_iso(zone.x * FACTOR, zone.y * FACTOR)
    pos = (px + OFFSET_X, py + OFFSET_Y)
    for k in {key, str(key), getattr(zone, "name", None), str(getattr(zone, "name", ""))}:
        if k:
            zone_positions[k] = pos


def get_zone_pos(ref):
    if ref in zone_positions:
        return zone_positions[ref]
    return zone_positions.get(str(ref))


#  7. ETAT
drone_ids = [f"D{i}" for i in range(1, parsed.nb_drones + 1)]
drone_from = {d: parsed.start_zone for d in drone_ids}
drone_to = {d: parsed.start_zone for d in drone_ids}
trails = {d: deque(maxlen=7) for d in drone_ids}     # traînee
node_glow = {}                                        # name -> 0..1

tour_simulation = 0
nombre_max_tours = max(par_tour.keys()) if par_tour else 0
TURN_DURATION_FRAMES = 60
turn_frame_counter = 0
anim_tick = 0
current_frame = 0

sorted_zones = sorted(parsed.zones.items(),
                      key=lambda it: it[1].x * FACTOR + it[1].y * FACTOR)
sorted_terrain = sorted(terrain_map.items(), key=lambda it: it[0][0] + it[0][1])

#  8. BOUCLE
while not window_should_close():
    anim_tick += 1
    if anim_tick >= DRAGON_ANIM_SPEED:
        anim_tick = 0
        current_frame = (current_frame + 1) % DRAGON_TOTAL_FRAMES

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
                    node_glow[key_of(dest)] = 1.0   # declenche le halo

    for k in list(node_glow):
        node_glow[k] *= 0.94
        if node_glow[k] < 0.01:
            del node_glow[k]

    t = turn_frame_counter / TURN_DURATION_FRAMES
    t_smooth = t * t * (3 - 2 * t)

    begin_drawing()
    clear_background(C_BG)

    # --- A. SOL ---
    for (gx, gy), tile_color in sorted_terrain:
        ix, iy = map_to_iso(gx, gy)
        draw_iso_tile_flat(ix + OFFSET_X, iy + OFFSET_Y,
                           TILE_WIDTH, TILE_HEIGHT, tile_color, C_GRID)

    # --- B. ARETES (sous les piliers: elles passent au sol, plus lisible) ---
    MID_HEIGHT = BLOCK_DEPTH * 0.5
    GAP = TILE_WIDTH * 0.35
    for u, v in connections:
        p1, p2 = get_zone_pos(u), get_zone_pos(v)
        if not (p1 and p2):
            continue
        hot = key_of(u) in used_nodes and key_of(v) in used_nodes
        x1, y1 = p1[0], p1[1] - MID_HEIGHT
        x2, y2 = p2[0], p2[1] - MID_HEIGHT
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist <= GAP * 2:
            continue
        ux, uy = dx / dist, dy / dist
        a = Vector2(x1 + ux * GAP, y1 + uy * GAP)
        b = Vector2(x2 - ux * GAP, y2 - uy * GAP)
        if hot:
            draw_line_ex(a, b, 7.0 * ZOOM, C_EDGE_HOT)
            draw_line_ex(a, b, 1.6 * ZOOM, C_EDGE_CORE)
        else:
            draw_line_ex(a, b, 1.4 * ZOOM, C_EDGE_IDLE)

    # --- C. PILIERS + CHATEAUX ---
    for name, zone in sorted_zones:
        p = get_zone_pos(name)
        if not p:
            continue
        px, py = p
        role = role_of(name, zone)
        col = ROLE_COLOR[role]
        glow = node_glow.get(key_of(name), 0.0)
        h = BLOCK_DEPTH * (1.35 if role in ("start", "goal") else 1.0)
        draw_iso_pillar(px, py, TILE_WIDTH * 0.72, TILE_HEIGHT * 0.72, h, col, glow)
        if role in ("start", "goal"):
            draw_texture_centered(chateau_texture, px, py - h + (5 * ZOOM),
                                  CHATEAU_SCALE, col)

    # --- D. DRAGONS + TRAINEES ---
    bob = math.sin(get_time() * 5.0) * (4.0 * ZOOM)
    to_draw = []
    for d in drone_ids:
        pf, pt = get_zone_pos(drone_from[d]), get_zone_pos(drone_to[d])
        if not (pf and pt):
            continue
        n = int(d[1:])
        off_x = math.cos(n * 1.5) * (10.0 * ZOOM)
        off_y = math.sin(n * 1.5) * (5.0 * ZOOM)
        cx = pf[0] + (pt[0] - pf[0]) * t_smooth + off_x
        cy = pf[1] + (pt[1] - pf[1]) * t_smooth + off_y
        to_draw.append((d, cx, cy))

    for d, cx, cy in to_draw:
        trails[d].append((cx, cy - BLOCK_DEPTH + 18.0 * ZOOM))
        c = couleur_pour_drone(d)
        pts = list(trails[d])
        for i, (tx, ty) in enumerate(pts[:-1]):
            k = (i + 1) / len(pts)
            draw_circle_v(Vector2(tx, ty), (1.0 + 3.0 * k) * ZOOM,
                          shade(c, 1.0, int(90 * k * k)))

    to_draw.sort(key=lambda it: it[2])
    for d, cx, cy in to_draw:
        draw_dragon_frame(dragon_texture, current_frame, cx,
                          cy - BLOCK_DEPTH + (18.0 * ZOOM) + bob,
                          DRAGON_SCALE, couleur_pour_drone(d))

    # --- E. LABELS: seulement ce qui compte, et sans plaque opaque ---
    font_size = max(10, int(11 * ZOOM))
    hover = get_mouse_position()
    for name, zone in sorted_zones:
        p = get_zone_pos(name)
        if not p:
            continue
        px, py = p
        role = role_of(name, zone)
        near = math.hypot(hover.x - px, hover.y - py) < TILE_WIDTH * 0.5

        if role in ("start", "goal"):
            alpha, size = 255, font_size + 2
        elif near:
            alpha, size = 255, font_size + 1
        elif role == "path":
            alpha, size = 140, font_size
        else:
            continue  # les noeuds neutres ne s'annoncent qu'au survol

        txt = key_of(name)
        w = measure_text(txt, size)
        # decalage en quinconce: casse les collisions de labels voisins
        parity = (int(zone.x) + int(zone.y)) % 2
        ty = py + (11 * ZOOM) + (parity * (size + 3))
        tx = int(px - w / 2)
        draw_text(txt, tx + 1, int(ty) + 1, size, Color(0, 0, 0, alpha))  # ombre portee
        draw_text(txt, tx, int(ty), size, Color(235, 240, 245, alpha))

    # --- F. HUD ---
    label = f"TOUR {tour_simulation:02d} / {nombre_max_tours}"
    w = measure_spaced(label, 18, 3)
    draw_rectangle(24, 24, 4, 26, C_PATH)
    draw_text_spaced(label, 40, 26, 18, Color(225, 235, 240, 255), 3)
    prog = tour_simulation / nombre_max_tours if nombre_max_tours else 0
    draw_rectangle(40, 56, int(w), 2, Color(255, 255, 255, 30))
    draw_rectangle(40, 56, int(w * prog), 2, C_PATH)

    end_drawing()

unload_texture(chateau_texture)
unload_texture(dragon_texture)
close_window()
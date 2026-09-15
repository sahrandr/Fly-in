import math
from pyray import *
from parser import MapParser
from algo import Simulator

# 1. PARSING ET SIMULATION
parsed = MapParser("maps/easy/02_simple_fork.txt").parse()
simulator = Simulator(parsed)
par_tour = simulator.run()

FACTOR = 2

# 2. INITIALISATION
init_window(1200, 800, "Fly-in - Esthétique Dark/Néon")
set_target_fps(60)

# 3. TEXTURES
chateau_texture = load_texture("assets/chateau.png")
dragon_texture = load_texture("assets/dragon.png")

DRAGON_FRAME_SIZE = 256.0
DRAGON_COLS = 4
DRAGON_ROWS = 4
DRAGON_TOTAL_FRAMES = DRAGON_COLS * DRAGON_ROWS
DRAGON_ANIM_SPEED = 8

CHATEAU_SCALE_BASE = 0.35
DRAGON_SCALE_BASE = 0.45
TILE_WIDTH_BASE = 80.0
TILE_HEIGHT_BASE = 40.0

# 4. FONCTIONS DE TRACÉ ISOMÉTRIQUE ESTHÉTIQUE
def map_to_iso_raw(x, y):
    return (x - y) * (TILE_WIDTH_BASE / 2), (x + y) * (TILE_HEIGHT_BASE / 2)

def draw_iso_tile_flat(screen_x, screen_y, tile_w, tile_h, color, outline_color=None):
    half_w = tile_w / 2
    half_h = tile_h / 2
    top = Vector2(screen_x, screen_y - half_h)
    right = Vector2(screen_x + half_w, screen_y)
    bottom = Vector2(screen_x, screen_y + half_h)
    left = Vector2(screen_x - half_w, screen_y)
    
    draw_triangle(top, left, bottom, color)
    draw_triangle(top, bottom, right, color)
    
    if outline_color:
        draw_line_v(top, right, outline_color)
        draw_line_v(right, bottom, outline_color)
        draw_line_v(bottom, left, outline_color)
        draw_line_v(left, top, outline_color)

def draw_iso_pillar(screen_x, screen_y, tile_w, tile_h, depth, base_color):
    half_w = tile_w / 2
    half_h = tile_h / 2
    
    top = Vector2(screen_x, screen_y - half_h - depth)
    right = Vector2(screen_x + half_w, screen_y - depth)
    bottom = Vector2(screen_x, screen_y + half_h - depth)
    left = Vector2(screen_x - half_w, screen_y - depth)
    
    base_bottom = Vector2(screen_x, screen_y + half_h)
    base_left = Vector2(screen_x - half_w, screen_y)
    base_right = Vector2(screen_x + half_w, screen_y)

    r, g, b, a = base_color.r, base_color.g, base_color.b, base_color.a
    color_left = Color(max(0, int(r * 0.5)), max(0, int(g * 0.5)), max(0, int(b * 0.5)), a)
    color_right = Color(max(0, int(r * 0.25)), max(0, int(g * 0.25)), max(0, int(b * 0.25)), a)

    draw_triangle(left, base_left, base_bottom, color_left)
    draw_triangle(left, base_bottom, bottom, color_left)
    
    draw_triangle(bottom, base_bottom, base_right, color_right)
    draw_triangle(bottom, base_right, right, color_right)
    
    draw_triangle(top, left, bottom, base_color)
    draw_triangle(top, bottom, right, base_color)
    
    edge_color = Color(255, 255, 255, 30)
    draw_line_v(top, left, edge_color)
    draw_line_v(top, right, edge_color)
    draw_line_v(left, bottom, Color(0,0,0, 100))
    draw_line_v(bottom, right, Color(0,0,0, 100))
    draw_line_v(bottom, base_bottom, Color(0,0,0, 100))

def draw_texture_centered(texture, x, y, scale, tint):
    w = texture.width * scale
    h = texture.height * scale
    draw_texture_ex(texture, Vector2(x - w / 2, y - h), 0.0, scale, tint)

def draw_dragon_frame(texture, frame_index, x, y, scale, tint):
    col = frame_index % DRAGON_COLS
    row = frame_index // DRAGON_COLS
    source = Rectangle(col * DRAGON_FRAME_SIZE, row * DRAGON_FRAME_SIZE, DRAGON_FRAME_SIZE, DRAGON_FRAME_SIZE)
    w = DRAGON_FRAME_SIZE * scale
    h = DRAGON_FRAME_SIZE * scale
    dest = Rectangle(x - w / 2, y - h, w, h)
    draw_texture_pro(texture, source, dest, Vector2(0, 0), 0.0, tint)

# 5. DÉPART ET ARRIVÉE
start_zone_id = getattr(parsed, 'start_zone', None)
end_zone_id = getattr(parsed, 'end_zone', getattr(parsed, 'target_zone', None))

def is_start_or_end(name, zone):
    if name == start_zone_id or zone == start_zone_id: return True
    if name == end_zone_id or zone == end_zone_id: return True
    s_name = str(name).lower()
    return 'start' in s_name or 'goal' in s_name or 'end' in s_name or 'final' in s_name

# 6. PALETTE ET TERRAIN
COLOR_MAP = {
    "green": Color(80, 255, 120, 255),
    "blue": Color(80, 200, 255, 255),
    "red": Color(255, 80, 80, 255),
    "orange": Color(255, 160, 50, 255),
    "yellow": Color(255, 230, 50, 255),
    "purple": Color(200, 100, 255, 255),
    "brown": Color(200, 140, 90, 255),
    "black": Color(100, 100, 100, 255),
    "gold": Color(255, 215, 0, 255),
    "gray": Color(200, 200, 200, 255),
    "none": WHITE,
}

all_x = [z.x * FACTOR for z in parsed.zones.values()]
all_y = [z.y * FACTOR for z in parsed.zones.values()]
min_x, max_x = min(all_x) - 3, max(all_x) + 3
min_y, max_y = min(all_y) - 3, max(all_y) + 3

terrain_map = {}
for x in range(min_x, max_x + 1):
    for y in range(min_y, max_y + 1):
        terrain_map[(x, y)] = Color(25, 30, 40, 255) if (x + y) % 2 == 0 else Color(30, 35, 45, 255)

# Extraction robuste des connexions (gère graph ou connections)
connections = []
if hasattr(parsed, 'graph') and parsed.graph:
    for u, neighbors in parsed.graph.items():
        u_name = u.name if hasattr(u, 'name') else str(u)
        for v in neighbors:
            v_name = v.name if hasattr(v, 'name') else str(v)
            connections.append((u_name, v_name))
elif hasattr(parsed, 'connections') and parsed.connections:
    for conn in parsed.connections:
        if isinstance(conn, (tuple, list)) and len(conn) >= 2:
            connections.append((str(conn[0]), str(conn[1])))
        else:
            u = getattr(conn, 'u', getattr(conn, 'from_zone', getattr(conn, 'zone1', getattr(conn, 'source', getattr(conn, 'a', None)))))
            v = getattr(conn, 'v', getattr(conn, 'to_zone', getattr(conn, 'zone2', getattr(conn, 'target', getattr(conn, 'b', None)))))
            if u is not None and v is not None:
                u_name = u.name if hasattr(u, 'name') else str(u)
                v_name = v.name if hasattr(v, 'name') else str(v)
                connections.append((u_name, v_name))

# 7. EXTRACTION DES CONNEXIONS
connections = [(conn.zone_a, conn.zone_b) for conn in parsed.connections]

# 7. ZOOM ET CENTRAGE
castle_iso_raw = [map_to_iso_raw(z.x * FACTOR, z.y * FACTOR) for z in parsed.zones.values()]
c_xs = [p[0] for p in castle_iso_raw]
c_ys = [p[1] for p in castle_iso_raw]

width_needed = (max(c_xs) - min(c_xs)) + TILE_WIDTH_BASE * 4
height_needed = (max(c_ys) - min(c_ys)) + TILE_HEIGHT_BASE * 6

ZOOM_RAW = min((1200.0 - 100.0) / width_needed, (800.0 - 120.0) / height_needed)
ZOOM = max(0.55, min(1.2, ZOOM_RAW))

TILE_WIDTH = TILE_WIDTH_BASE * ZOOM
TILE_HEIGHT = TILE_HEIGHT_BASE * ZOOM
CHATEAU_SCALE = CHATEAU_SCALE_BASE * ZOOM
DRAGON_SCALE = DRAGON_SCALE_BASE * max(0.75, ZOOM)
BLOCK_DEPTH = 25.0 * ZOOM

def map_to_iso(x, y):
    return (x - y) * (TILE_WIDTH / 2), (x + y) * (TILE_HEIGHT / 2)

all_iso_zoomed = [map_to_iso(gx, gy) for (gx, gy) in terrain_map.keys()]
z_xs = [p[0] for p in all_iso_zoomed]
z_ys = [p[1] for p in all_iso_zoomed]
OFFSET_X = 600 - (min(z_xs) + max(z_xs)) / 2
OFFSET_Y = 400 - (min(z_ys) + max(z_ys)) / 2

zone_positions = {}
for key, zone in parsed.zones.items():
    px, py = map_to_iso(zone.x * FACTOR, zone.y * FACTOR)
    pos = (px + OFFSET_X, py + OFFSET_Y)
    zone_positions[key] = pos
    zone_positions[str(key)] = pos
    if hasattr(zone, 'name'): 
        zone_positions[zone.name] = pos
        zone_positions[str(zone.name)] = pos

def get_zone_pos(zone_ref):
    if zone_ref in zone_positions:
        return zone_positions[zone_ref]
    s_ref = str(zone_ref)
    if s_ref in zone_positions:
        return zone_positions[s_ref]
    for k, pos in zone_positions.items():
        if str(k) == s_ref:
            return pos
    print(f"[DEBUG] Échec résolution position pour: {zone_ref!r}")
    return None

# 8. DRAGONS
DRAGON_COLORS = [
    Color(255, 100, 100, 255), Color(100, 255, 150, 255),
    Color(100, 180, 255, 255), Color(255, 200, 80, 255),
    Color(230, 100, 230, 255), Color(100, 230, 230, 255),
]
def couleur_pour_drone(drone_id):
    return DRAGON_COLORS[(int(drone_id[1:]) - 1) % len(DRAGON_COLORS)]

drone_from = {f"D{i}": parsed.start_zone for i in range(1, parsed.nb_drones + 1)}
drone_to = {f"D{i}": parsed.start_zone for i in range(1, parsed.nb_drones + 1)}

# 9. ÉTAT SIMULATION
tour_simulation = 0
nombre_max_tours = max(par_tour.keys()) if par_tour else 0
TURN_DURATION_FRAMES = 60
turn_frame_counter = 0
anim_tick = 0
current_frame = 0

# 10. BOUCLE PRINCIPALE
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
            for d_id in drone_from: drone_from[d_id] = drone_to[d_id]
            if tour_simulation in par_tour:
                for d_id, dest in par_tour[tour_simulation]: drone_to[d_id] = dest

    t = turn_frame_counter / TURN_DURATION_FRAMES
    t_smooth = t * t * (3 - 2 * t)

    begin_drawing()
    
    # --- FOND ---
    draw_rectangle_gradient_v(0, 0, 1200, 800, Color(10, 15, 25, 255), Color(30, 45, 60, 255))

    # --- A. SOL (Grille infinie) ---
    sorted_terrain = sorted(terrain_map.items(), key=lambda item: item[0][0] + item[0][1])
    grid_line = Color(255, 255, 255, 10)
    for (gx, gy), tile_color in sorted_terrain:
        iso_x, iso_y = map_to_iso(gx, gy)
        draw_iso_tile_flat(iso_x + OFFSET_X, iso_y + OFFSET_Y, TILE_WIDTH, TILE_HEIGHT, tile_color, grid_line)

        # --- B. PILIERS ET CHÂTEAUX (dessinés en premier) ---
    sorted_zones = sorted(parsed.zones.items(), key=lambda item: item[1].x * FACTOR + item[1].y * FACTOR)

    for name, zone in sorted_zones:
        p = get_zone_pos(name)
        if not p: continue
        px, py = p
        color_fill = COLOR_MAP.get(zone.color, COLOR_MAP["gold"])

        draw_iso_pillar(px, py, TILE_WIDTH * 0.75, TILE_HEIGHT * 0.75, BLOCK_DEPTH, color_fill)

        if is_start_or_end(name, zone):
            tint = COLOR_MAP.get(zone.color, COLOR_MAP["none"])
            draw_texture_centered(chateau_texture, px, py - BLOCK_DEPTH + (5*ZOOM), CHATEAU_SCALE, tint)

    # --- C. LIGNES / PONTS ENTRE LES ZONES (dans l'espace, entre les cubes) ---
    MID_HEIGHT = BLOCK_DEPTH * 0.5
    GAP_MARGIN = TILE_WIDTH * 0.35

    for u, v in connections:
        p1 = get_zone_pos(u)
        p2 = get_zone_pos(v)
        if p1 and p2:
            x1, y1 = p1[0], p1[1] - MID_HEIGHT
            x2, y2 = p2[0], p2[1] - MID_HEIGHT

            dx = x2 - x1
            dy = y2 - y1
            dist = math.hypot(dx, dy)

            if dist > GAP_MARGIN * 2:
                ux, uy = dx / dist, dy / dist
                start_pos = Vector2(x1 + ux * GAP_MARGIN, y1 + uy * GAP_MARGIN)
                end_pos = Vector2(x2 - ux * GAP_MARGIN, y2 - uy * GAP_MARGIN)

                draw_line_ex(start_pos, end_pos, 6.0 * ZOOM, Color(80, 200, 255, 90))
                draw_line_ex(start_pos, end_pos, 2.0 * ZOOM, Color(220, 245, 255, 230))

                draw_circle_v(start_pos, 3.0 * ZOOM, Color(220, 245, 255, 255))
                draw_circle_v(end_pos, 3.0 * ZOOM, Color(220, 245, 255, 255))
    # --- D. DRAGONS (BIEN PLUS BAS) ---
    bobbing_y = math.sin(get_time() * 5.0) * (4.0 * ZOOM)
    
    dragons_to_draw = []
    for drone_id in drone_from.keys():
        p_from = get_zone_pos(drone_from[drone_id])
        p_to = get_zone_pos(drone_to[drone_id])
        if not p_from or not p_to: continue
        start_x, start_y = p_from
        target_x, target_y = p_to
        curr_x = start_x + (target_x - start_x) * t_smooth
        curr_y = start_y + (target_y - start_y) * t_smooth
        dragons_to_draw.append((drone_id, curr_x, curr_y))
    
    dragons_to_draw.sort(key=lambda d: d[2])

    for drone_id, curr_x, curr_y in dragons_to_draw:
        drone_num = int(drone_id[1:])
        angle = drone_num * 1.5
        radius = 10.0 * ZOOM
        decalage_x = math.cos(angle) * radius
        decalage_y = math.sin(angle) * radius * 0.5

        draw_dragon_frame(
            dragon_texture,
            current_frame,
            curr_x + decalage_x,
            # Hauteur abaissée au plus près des piliers avec un décalage positif de +18.0
            curr_y - BLOCK_DEPTH + (18.0 * ZOOM) + bobbing_y + decalage_y,
            DRAGON_SCALE,
            couleur_pour_drone(drone_id)
        )

    # --- E. LABELS (TEXTES) AU PREMIER PLAN ---
    font_size = max(10, int(12 * ZOOM))
    for name, zone in sorted_zones:
        p = get_zone_pos(name)
        if not p: continue
        px, py = p
        text_str = str(name)
        text_w = measure_text(text_str, font_size)
        text_x = int(px - text_w / 2)
        text_y = int(py + (10 * ZOOM))

        rect = Rectangle(text_x - 6, text_y - 3, text_w + 12, font_size + 6)
        draw_rectangle_rounded(rect, 0.5, 4, Color(15, 20, 25, 200))
        draw_text(text_str, text_x, text_y, font_size, WHITE)

    # UI Globale
    panel = Rectangle(10, 10, 180, 40)
    draw_rectangle_rounded(panel, 0.2, 4, Color(15, 20, 25, 200))
    draw_text(f"Tour: {tour_simulation} / {nombre_max_tours}", 20, 20, 20, WHITE)

    end_drawing()

unload_texture(chateau_texture)
unload_texture(dragon_texture)
close_window()

# print(f"[DEBUG] {len(connections)} connexions extraites")
# print(f"[DEBUG] Exemple: {connections[:5]}")
# print(f"[DEBUG] Clés zone_positions dispo (5 premières): {list(zone_positions.keys())[:5]}")
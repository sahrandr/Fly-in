import math
import random
from pyray import *
from parser import MapParser
from algo import Simulator

# 1. PARSING ET SIMULATION
parsed = MapParser("maps/challenger/01_the_impossible_dream.txt").parse()
simulator = Simulator(parsed)
par_tour = simulator.run()

# PARAMÈTRE D'ESPACEMENT (Ajuste la distance entre les châteaux)
FACTOR = 2  

# 2. INITIALISATION RAYLIB
init_window(1200, 800, "Fly-in - Isometrique")
set_target_fps(60)

# 3. CHARGEMENT DES TEXTURES ET PARAMÈTRES BASE
chateau_texture = load_texture("assets/chateau.png")
dragon_texture = load_texture("assets/dragon.png")

DRAGON_FRAME_SIZE = 256.0
DRAGON_COLS = 4
DRAGON_ROWS = 4
DRAGON_TOTAL_FRAMES = DRAGON_COLS * DRAGON_ROWS
DRAGON_ANIM_SPEED = 8

CHATEAU_SCALE_BASE = 0.35
# Taille du dragon augmentée (0.45 au lieu de 0.18)
DRAGON_SCALE_BASE = 0.45 
TILE_WIDTH_BASE = 80.0
TILE_HEIGHT_BASE = 40.0

# 4. FONCTIONS DE TRACÉ
def map_to_iso_raw(x, y):
    return (x - y) * (TILE_WIDTH_BASE / 2), (x + y) * (TILE_HEIGHT_BASE / 2)

def draw_iso_tile(screen_x, screen_y, tile_w, tile_h, color):
    half_w = tile_w / 2
    half_h = tile_h / 2
    
    top = Vector2(screen_x, screen_y - half_h)
    right = Vector2(screen_x + half_w, screen_y)
    bottom = Vector2(screen_x, screen_y + half_h)
    left = Vector2(screen_x - half_w, screen_y)
    
    draw_triangle(top, left, bottom, color)
    draw_triangle(top, bottom, right, color)
    
    grid_line = Color(0, 0, 0, 30)
    draw_line_v(top, right, grid_line)
    draw_line_v(right, bottom, grid_line)
    draw_line_v(bottom, left, grid_line)
    draw_line_v(left, top, grid_line)

def draw_texture_centered(texture, x, y, scale, tint):
    w = texture.width * scale
    h = texture.height * scale
    draw_texture_ex(texture, Vector2(x - w / 2, y - h), 0.0, scale, tint)

def draw_dragon_frame(texture, frame_index, x, y, scale, tint):
    col = frame_index % DRAGON_COLS
    row = frame_index // DRAGON_COLS

    source = Rectangle(
        col * DRAGON_FRAME_SIZE,
        row * DRAGON_FRAME_SIZE,
        DRAGON_FRAME_SIZE,
        DRAGON_FRAME_SIZE,
    )

    w = DRAGON_FRAME_SIZE * scale
    h = DRAGON_FRAME_SIZE * scale
    dest = Rectangle(x - w / 2, y - h, w, h)
    origin = Vector2(0, 0)

    draw_texture_pro(texture, source, dest, origin, 0.0, tint)

def get_line_tiles(x0, y0, x1, y1):
    tiles = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    curr_x, curr_y = x0, y0
    while True:
        tiles.append((curr_x, curr_y))
        if curr_x == x1 and curr_y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            curr_x += sx
        if e2 < dx:
            err += dx
            curr_y += sy
    return tiles

def parse_connection(conn):
    if isinstance(conn, (tuple, list)) and len(conn) >= 2:
        return conn[0], conn[1]
    u = getattr(conn, 'u', getattr(conn, 'from_zone', getattr(conn, 'zone1', getattr(conn, 'source', getattr(conn, 'a', None)))))
    v = getattr(conn, 'v', getattr(conn, 'to_zone', getattr(conn, 'zone2', getattr(conn, 'target', getattr(conn, 'b', None)))))
    if u and hasattr(u, 'name'): u = u.name
    if v and hasattr(v, 'name'): v = v.name
    return u, v

# 5. GENERATION DU TERRAIN CONTINU
COLOR_MAP = {
    "green": Color(140, 255, 160, 255),
    "blue": Color(140, 190, 255, 255),
    "red": Color(255, 140, 140, 255),
    "orange": Color(255, 190, 120, 255),
    "yellow": Color(255, 240, 140, 255),
    "purple": Color(200, 140, 255, 255),
    "brown": Color(180, 130, 90, 255),
    "black": Color(80, 80, 80, 255),
    "gold": Color(255, 215, 0, 255),
    "gray": Color(200, 200, 200, 255),
    "none": WHITE,
}

TERRAIN_COLORS = {
    "grass": Color(85, 170, 85, 255),
    "grass_dark": Color(70, 145, 70, 255),
    "water": Color(65, 130, 200, 255),
    "earth": Color(139, 90, 43, 255),
    "rock": Color(120, 120, 120, 255),
    "flower": Color(220, 100, 150, 255)
}

coords_chateaux = {(zone.x * FACTOR, zone.y * FACTOR) for zone in parsed.zones.values()}

connections = []
if hasattr(parsed, 'graph') and parsed.graph:
    for u, neighbors in parsed.graph.items():
        for v in neighbors:
            connections.append((u, v))
elif hasattr(parsed, 'connections') and parsed.connections:
    connections = parsed.connections

path_tiles = set()
for conn in connections:
    u, v = parse_connection(conn)
    if u and v and u in parsed.zones and v in parsed.zones:
        z1, z2 = parsed.zones[u], parsed.zones[v]
        line = get_line_tiles(z1.x * FACTOR, z1.y * FACTOR, z2.x * FACTOR, z2.y * FACTOR)
        path_tiles.update(line)

all_x = [z.x * FACTOR for z in parsed.zones.values()]
all_y = [z.y * FACTOR for z in parsed.zones.values()]
min_x, max_x = min(all_x) - 2, max(all_x) + 2
min_y, max_y = min(all_y) - 2, max(all_y) + 2

terrain_map = {}
for x in range(min_x, max_x + 1):
    for y in range(min_y, max_y + 1):
        if (x, y) in coords_chateaux or (x, y) in path_tiles:
            terrain_type = "earth"
        elif abs(x - y) < 2:
            terrain_type = "water"
        else:
            rand = random.random()
            if rand < 0.04: terrain_type = "rock"
            elif rand < 0.08: terrain_type = "flower"
            elif rand < 0.45: terrain_type = "grass_dark"
            else: terrain_type = "grass"
            
        terrain_map[(x, y)] = terrain_type

# 6. CALCUL DU ZOOM ET CENTRAGE
castle_iso_raw = [map_to_iso_raw(z.x * FACTOR, z.y * FACTOR) for z in parsed.zones.values()]
c_xs = [p[0] for p in castle_iso_raw]
c_ys = [p[1] for p in castle_iso_raw]

min_c_x, max_c_x = min(c_xs), max(c_xs)
min_c_y, max_c_y = min(c_ys), max(c_ys)

width_needed = (max_c_x - min_c_x) + TILE_WIDTH_BASE * 4
height_needed = (max_c_y - min_c_y) + TILE_HEIGHT_BASE * 6

ZOOM_RAW = min((1200.0 - 80.0) / width_needed, (800.0 - 100.0) / height_needed)
ZOOM = max(0.55, min(1.0, ZOOM_RAW))

TILE_WIDTH = TILE_WIDTH_BASE * ZOOM
TILE_HEIGHT = TILE_HEIGHT_BASE * ZOOM
CHATEAU_SCALE = CHATEAU_SCALE_BASE * ZOOM

# On garde un zoom généreux sur les dragons pour la visibilité
DRAGON_SCALE = DRAGON_SCALE_BASE * max(0.75, ZOOM)

def map_to_iso(x, y):
    screen_x = (x - y) * (TILE_WIDTH / 2)
    screen_y = (x + y) * (TILE_HEIGHT / 2)
    return screen_x, screen_y

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
    zone_positions[zone] = pos

def get_zone_pos(zone_ref):
    if zone_ref in zone_positions:
        return zone_positions[zone_ref]
    if hasattr(zone_ref, 'name') and zone_ref.name in zone_positions:
        return zone_positions[zone_ref.name]
    s_ref = str(zone_ref)
    if s_ref in zone_positions:
        return zone_positions[s_ref]
    for key, pos in zone_positions.items():
        if isinstance(key, str) and (key in s_ref or s_ref in key):
            return pos
    return list(zone_positions.values())[0] if zone_positions else (600, 400)

# 7. DRAGONS & COULEURS
DRAGON_COLORS = [
    Color(255, 120, 120, 255),
    Color(120, 255, 150, 255),
    Color(120, 170, 255, 255),
    Color(255, 190, 100, 255),
    Color(230, 120, 230, 255),
    Color(120, 230, 230, 255),
]

def couleur_pour_drone(drone_id):
    numero = int(drone_id[1:])
    return DRAGON_COLORS[(numero - 1) % len(DRAGON_COLORS)]

drone_from = {f"D{i}": parsed.start_zone for i in range(1, parsed.nb_drones + 1)}
drone_to = {f"D{i}": parsed.start_zone for i in range(1, parsed.nb_drones + 1)}

# 8. ÉTAT DE LA SIMULATION & ANIMATION
tour_simulation = 0
nombre_max_tours = max(par_tour.keys()) if par_tour else 0
TURN_DURATION_FRAMES = 60
turn_frame_counter = 0

anim_tick = 0
current_frame = 0

# 9. BOUCLE PRINCIPALE
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
            for drone_id in drone_from:
                drone_from[drone_id] = drone_to[drone_id]
            if tour_simulation in par_tour:
                for drone_id, destination in par_tour[tour_simulation]:
                    drone_to[drone_id] = destination

    t = turn_frame_counter / TURN_DURATION_FRAMES
    t_smooth = t * t * (3 - 2 * t)

    begin_drawing()
    clear_background(Color(135, 206, 235, 255))

    # A. DESSIN DU TERRAIN
    sorted_terrain = sorted(terrain_map.items(), key=lambda item: item[0][0] + item[0][1])
    for (gx, gy), t_type in sorted_terrain:
        iso_x, iso_y = map_to_iso(gx, gy)
        final_x = iso_x + OFFSET_X
        final_y = iso_y + OFFSET_Y
        draw_iso_tile(final_x, final_y, TILE_WIDTH, TILE_HEIGHT, TERRAIN_COLORS[t_type])

    # B. DESSIN DES CHÂTEAUX
    sorted_zones = sorted(parsed.zones.items(), key=lambda item: item[1].x * FACTOR + item[1].y * FACTOR)

    font_size = max(9, int(11 * ZOOM))
    for name, zone in sorted_zones:
        px, py = get_zone_pos(name)
        tint = COLOR_MAP.get(zone.color, COLOR_MAP["none"])
        draw_texture_centered(chateau_texture, px, py, CHATEAU_SCALE, tint)
        draw_text(str(name), int(px - len(str(name)) * (font_size / 3.2)), int(py + 2), font_size, WHITE)

    # C. VOL INTERPOLÉ DES DRAGONS
    bobbing_y = math.sin(get_time() * 5.0) * (5.0 * ZOOM)
    for drone_id in sorted(drone_from.keys()):
        start_x, start_y = get_zone_pos(drone_from[drone_id])
        target_x, target_y = get_zone_pos(drone_to[drone_id])
        
        curr_x = start_x + (target_x - start_x) * t_smooth
        curr_y = start_y + (target_y - start_y) * t_smooth

        drone_num = int(drone_id[1:])
        decalage_x = ((drone_num % 5) - 2) * (14.0 * ZOOM)

        # Hauteur augmentée (-45.0) pour accueillir le grand sprite du dragon
        draw_dragon_frame(
            dragon_texture,
            current_frame,
            curr_x + decalage_x,
            curr_y - (45.0 * ZOOM) + bobbing_y,
            DRAGON_SCALE,
            couleur_pour_drone(drone_id),
        )

    draw_text(f"Tour: {tour_simulation}/{nombre_max_tours}", 10, 10, 20, BLACK)

    end_drawing()

# 10. NETTOYAGE
unload_texture(chateau_texture)
unload_texture(dragon_texture)
close_window()
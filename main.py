import math
import random
from pyray import *
from parser import MapParser
from algo import Simulator

# ============================================================
# 1. CHARGEMENT DES DONNEES
# ============================================================
parsed = MapParser("maps/challenger/01_the_impossible_dream.txt").parse()
simulator = Simulator(parsed)
par_tour = simulator.run()

# ============================================================
# 2. INITIALISATION RAYLIB
# ============================================================
init_window(1200, 800, "Fly-in - Isometrique")
set_target_fps(60)

# ============================================================
# 3. CHARGEMENT DES TEXTURES ET PARAMÈTRES
# ============================================================
chateau_texture = load_texture("assets/chateau.png")
dragon_texture = load_texture("assets/dragon.png")

DRAGON_FRAME_SIZE = 256.0
DRAGON_COLS = 4
DRAGON_ROWS = 4
DRAGON_TOTAL_FRAMES = DRAGON_COLS * DRAGON_ROWS
DRAGON_ANIM_SPEED = 8

# Retour aux tailles d'origine bien visibles
CHATEAU_SCALE = 0.30
DRAGON_SCALE = 0.20

# ============================================================
# 4. PROJECTION ISOMETRIQUE STANDARD
# ============================================================
TILE_WIDTH = 80.0
TILE_HEIGHT = 40.0

def map_to_iso(x, y):
    screen_x = (x - y) * (TILE_WIDTH / 2)
    screen_y = (x + y) * (TILE_HEIGHT / 2)
    return screen_x, screen_y

def draw_iso_tile(screen_x, screen_y, color):
    half_w = TILE_WIDTH / 2
    half_h = TILE_HEIGHT / 2
    
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

# ============================================================
# 5. COULEURS ET GÉNÉRATION DU TERRAIN
# ============================================================
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

all_x = [z.x for z in parsed.zones.values()]
all_y = [z.y for z in parsed.zones.values()]
min_x, max_x = min(all_x) - 4, max(all_x) + 4
min_y, max_y = min(all_y) - 4, max(all_y) + 4

terrain_map = {}
coords_chateaux = {(zone.x, zone.y) for zone in parsed.zones.values()}

for x in range(min_x, max_x + 1):
    for y in range(min_y, max_y + 1):
        if (x, y) in coords_chateaux:
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

# ============================================================
# 6. CALCUL DES POSITIONS ECRAN
# ============================================================
raw_positions = {}
for name, zone in parsed.zones.items():
    raw_positions[name] = map_to_iso(zone.x, zone.y)

xs = [p[0] for p in raw_positions.values()]
ys = [p[1] for p in raw_positions.values()]
center_x = (min(xs) + max(xs)) / 2 if xs else 0
center_y = (min(ys) + max(ys)) / 2 if ys else 0

OFFSET_X = 600 - center_x
OFFSET_Y = 400 - center_y

zone_positions = {}
for name, (x, y) in raw_positions.items():
    zone_positions[name] = (x + OFFSET_X, y + OFFSET_Y)

# ============================================================
# 7. DRAGONS & COULEURS
# ============================================================
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

drone_positions = {
    f"D{i}": parsed.start_zone for i in range(1, parsed.nb_drones + 1)
}

# ============================================================
# 8. ETAT DE LA SIMULATION
# ============================================================
tour_simulation = 0
nombre_max_tours = max(par_tour.keys()) if par_tour else 0
compteur = 0
TOURS_PAR_SECONDE = 60

anim_tick = 0
current_frame = 0

# ============================================================
# 9. BOUCLE PRINCIPALE
# ============================================================
while not window_should_close():

    compteur += 1

    anim_tick += 1
    if anim_tick >= DRAGON_ANIM_SPEED:
        anim_tick = 0
        current_frame = (current_frame + 1) % DRAGON_TOTAL_FRAMES

    if compteur % TOURS_PAR_SECONDE == 0 and tour_simulation < nombre_max_tours:
        tour_simulation += 1
        if tour_simulation in par_tour:
            for drone_id, destination in par_tour[tour_simulation]:
                drone_positions[drone_id] = destination

    begin_drawing()
    clear_background(Color(135, 206, 235, 255))

    # A. DESSIN DU TERRAIN
    sorted_terrain = sorted(terrain_map.items(), key=lambda item: item[0][0] + item[0][1])
    for (gx, gy), t_type in sorted_terrain:
        iso_x, iso_y = map_to_iso(gx, gy)
        final_x = iso_x + OFFSET_X
        final_y = iso_y + OFFSET_Y
        draw_iso_tile(final_x, final_y, TERRAIN_COLORS[t_type])

    # B. PRÉPARATION DES DRAGONS
    drones_par_zone = {}
    for drone_id, zone_name in drone_positions.items():
        drones_par_zone.setdefault(zone_name, []).append(drone_id)

    bobbing_y = math.sin(get_time() * 5.0) * 5.0

    # C. DESSIN DES ENTITÉS
    sorted_zones = sorted(parsed.zones.items(), key=lambda item: item[1].x + item[1].y)

    for name, zone in sorted_zones:
        px, py = zone_positions[name]
        
        # 1. Rendu du Château (taille rétablie)
        tint = COLOR_MAP.get(zone.color, COLOR_MAP["none"])
        draw_texture_centered(chateau_texture, px, py, CHATEAU_SCALE, tint)
        
        # 2. Rendu des Dragons
        if name in drones_par_zone:
            drones = drones_par_zone[name]
            nb = len(drones)
            for i, drone_id in enumerate(sorted(drones)):
                decalage_x = (i - (nb - 1) / 2) * 16.0
                draw_dragon_frame(
                    dragon_texture,
                    current_frame,
                    px + decalage_x,
                    py - 30.0 + bobbing_y,
                    DRAGON_SCALE,
                    couleur_pour_drone(drone_id),
                )
                
        # 3. Rendu du Label
        draw_text(name, int(px - len(name) * 3), int(py + 4), 10, WHITE)

    draw_text(f"Tour: {tour_simulation}/{nombre_max_tours}", 10, 10, 20, BLACK)

    end_drawing()

# ============================================================
# 10. NETTOYAGE
# ============================================================
unload_texture(chateau_texture)
unload_texture(dragon_texture)
close_window()
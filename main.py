import pygame
from parser import parse_map
from algo import build_adjacency, dijkstra, reconstruct_path, planifier_tous_les_drones, organiser_par_tour

# 1. INITIALISATION DE PYGAME
pygame.init()

# 2. CHARGEMENT DE LA CARTE ET CALCUL DES CHEMINS
# Lecture du fichier de carte -> on récupère les zones, les connexions
# entre zones, la zone de départ, la zone d'arrivée et le nombre de drones
resultat = parse_map("maps/easy/03_basic_capacity.txt")
zones = resultat["zones"]
connections = resultat["connections"]

# Construction de la liste d'adjacence (quelle zone est reliée à quelle zone)
adjacency = build_adjacency(zones, connections)

# Dijkstra : calcule la distance la plus courte depuis la zone de départ
# vers toutes les autres zones, + le "previous" pour reconstruire le chemin
distances, previous = dijkstra(adjacency, zones, resultat["start_zone"])

# Reconstruction du chemin le plus court entre start_zone et end_zone
chemin = reconstruct_path(previous, resultat["start_zone"], resultat["end_zone"])

# Répartit ce chemin entre tous les drones disponibles
tous_les_chemins = planifier_tous_les_drones(chemin, zones, resultat["nb_drones"])

# Réorganise les déplacements par numéro de tour :
# par_tour[numero_tour] = liste de (drone_id, zone_a_atteindre)
par_tour = organiser_par_tour(tous_les_chemins)

print(par_tour)  # debug : affiche le planning tour par tour

# 3. CONVERSION COORDONNÉES CARTE -> COORDONNÉES ÉCRAN (PIXELS)
SCALE = 100                     # 1 unité de carte = 100 pixels à l'écran
OFFSENT_X, OFFSENT_Y = 100, 350 # décalage pour centrer/positionner la carte à l'écran

def map_to_pixel(x: int, y: int) -> tuple[int, int]:
    """Convertit une coordonnée logique de la carte (x, y) en position pixel à l'écran."""
    return OFFSENT_X + x * SCALE, OFFSENT_Y + y * SCALE

# Couleur affichée pour chaque zone selon sa couleur logique définie dans la carte
COLOR_MAP = {
    "green": (0, 180, 0),
    "blue": (0, 100, 220),
    "red": (200, 0, 0),
    "orange": (230, 140, 0),
    "yellow": (230, 200, 0),
    "gray": (150, 150, 150),
    "none": (100, 100, 100),
    "rainbow": (255, 0, 255),
}

# 4. VARIABLES DE SIMULATION (avancement des tours de jeu)
tour_simulation = 0
nombre_max_tours = max(par_tour.keys())  # dernier tour du planning

# Pré-calcul : position en pixels de chaque zone (évite de refaire le calcul
# à chaque frame dans la boucle principale)
zone_pixels = {}
for name, zone in zones.items():
    zone_pixels[name] = map_to_pixel(zone.x, zone.y)

# 5. CRÉATION DE LA FENÊTRE PYGAME
screen = pygame.display.set_mode((900, 700))          # largeur x hauteur
pygame.display.set_caption("Fly-in Simulation")
clock = pygame.time.Clock()
# clock.tick(60) plus bas : force la boucle à tourner à 60 images/seconde
# c'est ce qui rend notre "compteur" fiable (voir bloc 8)

# 6. POSITION INITIALE DE CHAQUE DRONE (tous à la zone de départ)
drone_positions = {}
for i in range(1, resultat["nb_drones"] + 1):
    drone_id = f"D{i}"
    drone_positions[drone_id] = resultat["start_zone"]

# 7. CHARGEMENT DU SPRITE SHEET DU DRONE (animation de vol)
# Chargé une seule fois AVANT la boucle while, pour ne pas relire
# le fichier image à chaque frame (ce serait très lent)
sprite_sheet = pygame.image.load("FLYING.png").convert_alpha()

TAILLE_DRONE = 80   # taille (en pixels) à laquelle chaque drone sera affiché
NB_FRAMES = 4        # nombre d'images d'animation dans le spritesheet
largeur_totale = sprite_sheet.get_width()
hauteur_totale = sprite_sheet.get_height()
largeur_frame = largeur_totale // NB_FRAMES  # largeur d'une seule frame

# Découpage du spritesheet en NB_FRAMES images individuelles,
# redimensionnées à TAILLE_DRONE x TAILLE_DRONE
frames = []
for i in range(NB_FRAMES):
    rect = pygame.Rect(i * largeur_frame, 0, largeur_frame, hauteur_totale)
    frame = sprite_sheet.subsurface(rect).copy()
    frame = pygame.transform.scale(frame, (TAILLE_DRONE, TAILLE_DRONE))
    frames.append(frame)

frame_actuelle = 0  # index de la frame d'animation actuellement affichée
compteur = 0         # compteur simple : +1 à chaque tour de boucle (~60 fois/seconde)

# 8. BOUCLE PRINCIPALE DU JEU
running = True
while running:

    # --- Gestion des événements (fermeture de la fenêtre, etc.) ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- Fond d'écran blanc (efface l'image précédente) ---
    screen.fill((255, 255, 255))

    # --- Dessin des connexions entre zones (les lignes/routes) ---
    for conn in connections:
        pygame.draw.line(screen, (150, 150, 150), zone_pixels[conn.zone_a], zone_pixels[conn.zone_b], 3)

    # --- Dessin des zones (les cercles colorés) ---
    for name, zone in zones.items():
        px, py = zone_pixels[name]
        couleur = COLOR_MAP.get(zone.color, COLOR_MAP["none"])
        pygame.draw.circle(screen, couleur, (px, py), 25)

    # --- Compteur : avance de 1 à chaque tour de boucle ---
    # Comme clock.tick(60) fixe la boucle à 60 fois/seconde :
    #   12 tours de boucle ≈ 0.2 seconde
    #   60 tours de boucle ≈ 1 seconde
    compteur += 1

    # --- Bloc animation : fait avancer les frames de vol (ailes qui battent) ---
    # Se déclenche toutes les 12 boucles (~0.2s), en continu,
    # indépendamment du tour de simulation
    if compteur % 6 == 0:
        frame_actuelle = (frame_actuelle + 1) % len(frames)

    # --- Bloc A : avancer le tour de simulation toutes les 60 boucles (~1s) ---
    # (met à jour drone_positions, NE DESSINE RIEN ici)
    if compteur % 60 == 0 and tour_simulation < nombre_max_tours:
        tour_simulation += 1
        # Si ce tour contient des déplacements, on met à jour la position
        # logique de chaque drone concerné
        if tour_simulation in par_tour:
            for drone_id, zone_name in par_tour[tour_simulation]:
                drone_positions[drone_id] = zone_name

    # --- Bloc B : dessiner CHAQUE drone à sa position actuelle, à CHAQUE frame ---
    # (le dessin se fait à chaque image, même si la position ne change pas,
    # pour que l'animation de vol continue de tourner)
    for drone_id, zone_name in drone_positions.items():
        px, py = zone_pixels[zone_name]
        screen.blit(frames[frame_actuelle], (px - TAILLE_DRONE // 2, py - TAILLE_DRONE // 2))

    # --- Mise à jour de l'affichage ---
    pygame.display.flip()
    clock.tick(60)  # limite la boucle à 60 images par seconde

# 9. FERMETURE PROPRE DE PYGAME
pygame.quit()
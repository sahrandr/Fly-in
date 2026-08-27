import pygame
from parser import parse_map
from algo import build_adjacency, dijkstra, reconstruct_path, planifier_tous_les_drones, organiser_par_tour

# 1. Initialisation de Pygame
pygame.init()

resultat = parse_map("maps/easy/03_basic_capacity.txt")
zones = resultat["zones"]
connections = resultat["connections"]
adjacency = build_adjacency(zones, connections)
distances, previous = dijkstra(adjacency, zones, resultat["start_zone"])
chemin = reconstruct_path(previous, resultat["start_zone"], resultat["end_zone"])
tous_les_chemins = planifier_tous_les_drones(chemin, zones, resultat["nb_drones"])
par_tour = organiser_par_tour(tous_les_chemins)

print(par_tour)

SCALE = 100
OFFSENT_X, OFFSENT_Y = 100, 350
def map_to_pixel(x: int, y: int) -> tuple[int, int]:
    return OFFSENT_X + x * SCALE, OFFSENT_Y + y * SCALE

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

tour_simulation = 0
dernier_changement = pygame.time.get_ticks()
# retourne le nombre de millisecondes ecoulees depuis le lancement du programme
delai_tour_ms = 1000  # 1 seconde entre chaque tour
nombre_max_tours = max(par_tour.keys())
zone_pixels = {}
for name, zone in zones.items():
    zone_pixels[name] = map_to_pixel(zone.x, zone.y)


# 2. Definition des dimensions (largeur, hauteur)
screen = pygame.display.set_mode((900, 700))

# 3. Creation de la fenetre
pygame.display.set_caption("Fly-in Simulation")
clock = pygame.time.Clock()
# controle la vitesse d'execution de la boucle et mesure le temps ecoule

drone_positions = {}
for i in range(1, resultat["nb_drones"] + 1):
    drone_id = f"D{i}"
    drone_positions[drone_id] = resultat["start_zone"]


# chargement une seule fois, avant la boucle while
sprite_sheet = pygame.image.load("FLYING.png").convert_alpha()

TAILLE_DRONE = 80
NB_FRAMES = 4
largeur_totale = sprite_sheet.get_width()
hauteur_totale = sprite_sheet.get_height()
largeur_frame = largeur_totale // NB_FRAMES

frames = []
for i in range(NB_FRAMES):
    rect = pygame.Rect(i * largeur_frame, 0, largeur_frame, hauteur_totale)
    frame = sprite_sheet.subsurface(rect).copy()
    frame = pygame.transform.scale(frame, (TAILLE_DRONE, TAILLE_DRONE))
    frames.append(frame)

frame_actuelle = 0
dernier_changement_frame = pygame.time.get_ticks()
delai_frame_ms = 200

# 4. Boucle principale pour maintenir la fenetre ouverte
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((255, 255, 255))

    # connexions
    for conn in connections:
        pygame.draw.line(screen, (150, 150, 150), zone_pixels[conn.zone_a], zone_pixels[conn.zone_b], 3)

    # zones
    for name, zone in zones.items():
        px, py = zone_pixels[name]
        couleur = COLOR_MAP.get(zone.color, COLOR_MAP["none"])
        pygame.draw.circle(screen, couleur, (px, py), 25)

    # Bloc animation - faire avancer les frames de vol (ailes qui battent)
    maintenant_frame = pygame.time.get_ticks()
    if maintenant_frame - dernier_changement_frame >= delai_frame_ms:
        frame_actuelle = (frame_actuelle + 1) % len(frames)
        dernier_changement_frame = maintenant_frame

    # Bloc A - avancer le tour de simulation si le delai est passe
    # (met a jour drone_positions, NE DESSINE RIEN ici)
    maintenant = pygame.time.get_ticks()
    if maintenant - dernier_changement >= delai_tour_ms and tour_simulation < nombre_max_tours:
        tour_simulation += 1
        dernier_changement = maintenant
        if tour_simulation in par_tour:
            for drone_id, zone_name in par_tour[tour_simulation]:
                drone_positions[drone_id] = zone_name

    # Bloc B - dessiner CHAQUE drone a sa position actuelle, a CHAQUE frame
    for drone_id, zone_name in drone_positions.items():
        px, py = zone_pixels[zone_name]
        screen.blit(frames[frame_actuelle], (px - TAILLE_DRONE // 2, py - TAILLE_DRONE // 2))

    pygame.display.flip()
    clock.tick(60)

# 5. Fermeture propre
pygame.quit()
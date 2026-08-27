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
delai_tour_ms = 1000  # 1 seconde entre chaque tour
nombre_max_tours = max(par_tour.keys())
zone_pixels = {}
for name, zone in zones.items():
    zone_pixels[name] = map_to_pixel(zone.x, zone.y)


# 2. Définition des dimensions (largeur, hauteur)
screen = pygame.display.set_mode((900, 700))

# 3. Création de la fenêtre
pygame.display.set_caption("Fly-in Simulation")
clock = pygame.time.Clock()
#contrôler la vitesse d'exécution de la boucle de jeu et à mesurer le temps écoulé. 

drone_positions = {}
for i in range(1, resultat["nb_drones"] + 1):
    drone_id = f"D{i}"
    drone_positions[drone_id] = resultat["start_zone"]


# 4. Boucle principale pour maintenir la fenêtre ouverte
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((255, 255, 255))

    for conn in connections:
        pygame.draw.line(screen, (150, 150, 150), zone_pixels[conn.zone_a], zone_pixels[conn.zone_b], 3)

    for name, zone in zones.items():
        px, py = zone_pixels[name]
        couleur = COLOR_MAP.get(zone.color, COLOR_MAP["none"])
        pygame.draw.circle(screen, couleur, (px, py), 25)

    # Bloc A — avancer le tour si le délai est passé
    maintenant = pygame.time.get_ticks()
    if maintenant - dernier_changement >= delai_tour_ms and tour_simulation < nombre_max_tours:
        tour_simulation += 1
        dernier_changement = maintenant
        if tour_simulation in par_tour:
            for drone_id, zone_name in par_tour[tour_simulation]:
                drone_positions[drone_id] = zone_name

    # Bloc B — dessiner les drones à leur position actuelle
    for drone_id, zone_name in drone_positions.items():
        px, py = zone_pixels[zone_name]
        pygame.draw.circle(screen, (0, 0, 0), (px, py), 8)

    pygame.display.flip()
    clock.tick(60)

# 5. Fermeture propre
pygame.quit()
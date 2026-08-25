from parser import parse_map
from parser import Zone
import heapq


# ÉTAPE 1 : CONSTRUIRE LE GRAPHE (qui est voisin de qui)
def build_adjacency(zones: dict, connections: list) -> dict[str, list[str]]:
    """
    Transforme la liste plate des connexions en une structure facile
    à consulter : pour chaque zone, la liste de ses voisins directs.

    Exemple de résultat :
        {'start': ['waypoint1'], 'waypoint1': ['start', 'waypoint2'], ...}

    Les zones "blocked" sont totalement exclues : elles n'apparaissent
    jamais comme voisines de personne (ni dans un sens, ni dans l'autre).
    """
    adjacency = {}

    # 1. On crée un "tiroir" vide pour chaque zone qui existe
    for nom_zone in zones:
        adjacency[nom_zone] = []

    # 2. On remplit ces tiroirs en parcourant toutes les connexions
    for conn in connections:
        zone_a_bloquee = zones[conn.zone_a].zone_type == "blocked"
        zone_b_bloquee = zones[conn.zone_b].zone_type == "blocked"

        # une connexion est bidirectionnelle : si NI a NI b n'est bloquée,
        # on ajoute chacune comme voisine de l'autre, dans les 2 sens
        if not zone_a_bloquee and not zone_b_bloquee:
            adjacency[conn.zone_a].append(conn.zone_b)
            adjacency[conn.zone_b].append(conn.zone_a)

    return adjacency


# ÉTAPE 2 : LE COÛT POUR ENTRER DANS UNE ZONE
def zone_cost(zone: Zone) -> int:
    """
    Retourne le coût en tours pour ENTRER dans cette zone
    (le coût dépend du type de la zone d'ARRIVÉE, jamais de départ).

    Règles du sujet :
    - normal   -> 1 tour
    - priority -> 1 tour (traité pareil que normal pour l'instant)
    - restricted -> 2 tours (plus cher, donc évité si possible)
    - blocked  -> pas géré ici, ces zones sont déjà exclues du graphe
                  par build_adjacency, donc on ne les croisera jamais
    """
    if zone.zone_type == "restricted":
        return 2
    else:
        return 1


# ÉTAPE 3 : DIJKSTRA — trouver le chemin le moins cher
def dijkstra(adjacency: dict, zones: dict, start: str) -> dict[str, float]:
    """
    Calcule, pour UN SEUL drone, le coût minimum (en tours) pour
    atteindre CHAQUE zone du réseau depuis 'start'.

    Retourne deux dicts :
    - distances : coût minimum pour atteindre chaque zone
    - previous  : pour chaque zone, la zone juste avant elle sur
                  le meilleur chemin trouvé (sert à reconstruire
                  le chemin complet ensuite, avec reconstruct_path)
    """

    # au départ, on suppose que TOUTES les zones sont inatteignables
    # (distance infinie), sauf le point de départ (distance 0)
    distances = {}
    for node in adjacency:
        distances[node] = float('inf')
    distances[start] = 0

    # previous[zone] = "d'où je viens pour arriver ici le moins cher"
    # None au départ pour tout le monde (on ne sait encore rien)
    previous = {node: None for node in adjacency}

    # la file d'attente prioritaire : elle nous donne toujours
    # en premier la zone la MOINS chère à explorer parmi celles connues
    queue = [(0, start)]

    while queue:
        # on récupère la zone la moins chère actuellement connue
        current_distance, current_node = heapq.heappop(queue)

        # si on a déjà trouvé un meilleur chemin entre-temps vers
        # cette zone, cette entrée est obsolète -> on l'ignore
        if current_distance > distances[current_node]:
            continue

        # on regarde chaque voisin direct de la zone actuelle
        for neighbor in adjacency[current_node]:
            # combien ça coûte d'entrer dans ce voisin ?
            weight = zone_cost(zones[neighbor])

            # coût total si je passe par current_node pour aller à neighbor
            distance = current_distance + weight

            # si ce chemin est meilleur que ce qu'on savait avant...
            if distance < distances[neighbor]:
                distances[neighbor] = distance          # on met à jour le record
                previous[neighbor] = current_node        # on note d'où on vient
                heapq.heappush(queue, (distance, neighbor))  # à explorer plus tard

    return distances, previous


# ÉTAPE 4 : RECONSTRUIRE LE CHEMIN COMPLET (pas juste le coût)
def reconstruct_path(previous: dict, start: str, end: str) -> list[str]:
    """
    Remonte le dict 'previous' depuis 'end' jusqu'à 'start',
    pour obtenir la vraie liste ordonnée des zones à traverser.

    Exemple : ['start', 'waypoint1', 'waypoint2', 'goal']
    """
    chemin = []
    node = end

    # on part de la fin et on remonte vers le début,
    # en suivant "d'où je viens" à chaque étape
    while node is not None:
        chemin.append(node)
        node = previous[node]

    # à ce stade, chemin est à l'ENVERS (de end vers start)
    # donc on l'inverse pour avoir l'ordre de lecture normal
    chemin.reverse()

    return chemin

# ETAPE 5 : LISTER DANS UN DICT LES CHEMIN DEJA PRIS
def chemin_avec_tours(chemin: list[str], zones: dict) -> dict[str, int]:
    """Transforme une liste de zones en dict {zone: tour_d_arrivee}"""
    path_use = {}
    nbr_tour = 0

    for name_zone in chemin:
        if name_zone == chemin[0]:
            path_use[name_zone] = 0

        else:
            cout = zone_cost(zones[name_zone])
            nbr_tour = nbr_tour + cout
            path_use[name_zone] = nbr_tour

    return path_use


def add_to_occupation(occupation: dict, drone_id: str, chemin_tours: dict) -> None:
    """Ajoute le passage d'un drone dans le registre d'occupation global."""
    for zone_name, tour in chemin_tours.items():
        
        # étape 1 : s'assurer que la zone existe dans occupation
        if zone_name not in occupation:
            occupation[zone_name] = {}
        
        # étape 2 : s'assurer que ce tour existe pour cette zone
        if tour not in occupation[zone_name]:
            occupation[zone_name][tour] = []
        
        # étape 3 : ajouter le drone à la liste de ce tour
        occupation[zone_name][tour].append(drone_id)


def zone_disponible(occupation: dict, zone_name: str, tour: int, zones: dict) -> bool:
    """Vérifie si une zone a encore de la place pour un drone de plus à ce tour."""
    
    # si personne n'est jamais allé dans cette zone, ou personne à ce tour précis,
    # alors il y a 0 drone présent
    if zone_name not in occupation:
        nbr_zone = 0
    elif tour not in occupation[zone_name]:
        nbr_zone = 0
    else:
        nbr_zone = len(occupation[zone_name][tour])
    
    max_capacite = zones[zone_name].max_drones
    
    if max_capacite > nbr_zone:
        return True
    else:
        return False

def planifier_chemin_avec_attente(chemin: list[str], zones: dict, occupation: dict) -> dict[str, int]:
    """
    Calcule à quel tour le drone arrive à chaque zone de son chemin,
    en insérant de l'attente si une zone est déjà occupée.
    """
    chemin_tours = {}
    tour_actuel = 0
    
    # la première zone, c'est le départ -> tour 0, toujours possible
    chemin_tours[chemin[0]] = 0
    
    for i in range(1, len(chemin)):
        zone_name = chemin[i]
        zone_precedente = chemin[i - 1]
        
        # le coût normal pour atteindre cette zone
        cout = zone_cost(zones[zone_name])
        tour_arrivee = tour_actuel + cout
        
        # tant que la zone n'est pas disponible à ce tour, on attend un tour de plus
        while not zone_disponible(occupation, zone_name, tour_arrivee, zones):
            tour_arrivee += 1
        
        chemin_tours[zone_name] = tour_arrivee
        tour_actuel = tour_arrivee
    
    return chemin_tours

def planifier_tous_les_drones(chemin: list[str], zones: dict, nb_drones: int) -> dict[str, dict]:
    """Calcule le chemin de TOUS les drones, un par un, en tenant compte des autres."""
    occupation = {}
    tous_les_chemins = {}

    for numero in range(1, nb_drones + 1):
        drone_id = f"D{numero}"
        
        chemin_tours = planifier_chemin_avec_attente(chemin, zones, occupation)
        add_to_occupation(occupation, drone_id, chemin_tours)
        
        tous_les_chemins[drone_id] = chemin_tours

    return tous_les_chemins


def organiser_par_tour(tous_les_chemins: dict) -> dict[int, list[tuple[str, str]]]:
    """
    Transforme {drone: {zone: tour}} en {tour: [(drone, zone), ...]}
    en ignorant le tour 0 (position de départ, pas un mouvement).
    """
    par_tour = {}
    
    for drone_id, chemin_tours in tous_les_chemins.items():
        for zone_name, tour in chemin_tours.items():
            if tour == 0:
                continue

            # s'assurer que ce tour existe dans par_tour
            if tour not in par_tour:
                par_tour[tour] = []
            
            # ajouter le couple (drone, zone) comme UN SEUL élément (un tuple)
            par_tour[tour].append((drone_id, zone_name))
    
    return par_tour

def afficher_simulation(par_tour: dict) -> None:
    """Affiche la simulation tour par tour, au format demandé par le sujet."""
    
    # il faut parcourir les tours DANS L'ORDRE (1, 2, 3, 4...)
    nombre_de_tours = max(par_tour.keys())
    
    for tour in range(1, nombre_de_tours + 1):
        if tour not in par_tour:
            continue  # personne ne bouge à ce tour (rare, mais possible)
        
        mouvements = par_tour[tour]
        
        # transformer chaque (drone_id, zone_name) en la chaîne "D1-bottleneck"
        morceaux_texte = []
        for drone_id, zone_name in mouvements:
            morceaux_texte.append(f"{drone_id}-{zone_name}")
        
        # assembler tous les morceaux d'un même tour, séparés par un espace
        ligne = " ".join(morceaux_texte)
        print(ligne)


if __name__ == "__main__":
    resultat = parse_map("maps/easy/03_basic_capacity.txt")
    adjacency = build_adjacency(resultat["zones"], resultat["connections"])
    distances, previous = dijkstra(adjacency, resultat["zones"], resultat["start_zone"])
    chemin = reconstruct_path(previous, resultat["start_zone"], resultat["end_zone"])

    tous_les_chemins = planifier_tous_les_drones(chemin, resultat["zones"], resultat["nb_drones"])

    for drone_id, chemin_tours in tous_les_chemins.items():
        print(drone_id, ":", chemin_tours)

    print()
    tous_les_chemins = planifier_tous_les_drones(chemin, resultat["zones"], resultat["nb_drones"])
    par_tour = organiser_par_tour(tous_les_chemins)
    print(par_tour)

    print()
    par_tour = organiser_par_tour(tous_les_chemins)
    afficher_simulation(par_tour)
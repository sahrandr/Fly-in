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


if __name__ == "__main__":
    # 1. on parse le fichier de carte -> zones, connexions, start/end
    resultat = parse_map("maps/hard/01_maze_nightmare.txt")

    # 2. on construit le graphe des voisins (sans les zones bloquées)
    adjacency = build_adjacency(resultat["zones"], resultat["connections"])

    # 3. on calcule le coût minimum vers chaque zone + la trace du chemin
    distances, previous = dijkstra(adjacency, resultat["zones"], resultat["start_zone"])

    # 4. on reconstruit le chemin complet, dans l'ordre, de start à goal
    chemin = reconstruct_path(previous, resultat["start_zone"], resultat["end_zone"])

    print(chemin)
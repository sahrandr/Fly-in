import heapq
from typing import Optional

from parser import Zone, Connection, ParsedMap


class Graph:
    """Représente le réseau de zones et leurs connexions."""

    def __init__(self, zones: dict[str, Zone], connections: list[Connection]) -> None:
        self.zones = zones
        self.connections = connections
        self.adjacency: dict[str, list[str]] = self._build_adjacency()

    def _build_adjacency(self) -> dict[str, list[str]]:
        """
        Transforme la liste plate des connexions en une structure facile
        à consulter : pour chaque zone, la liste de ses voisins directs.

        Exemple de résultat :
            {'start': ['waypoint1'], 'waypoint1': ['start', 'waypoint2'], ...}

        Les zones "blocked" sont totalement exclues : elles n'apparaissent
        jamais comme voisines de personne (ni dans un sens, ni dans l'autre).
        """
        adjacency: dict[str, list[str]] = {}

        # 1. on crée un "tiroir" vide pour chaque zone qui existe
        for zone_name in self.zones:
            adjacency[zone_name] = []

        # 2. on remplit ces tiroirs en parcourant toutes les connexions
        for conn in self.connections:
            zone_a_bloquee = self.zones[conn.zone_a].zone_type == "blocked"
            zone_b_bloquee = self.zones[conn.zone_b].zone_type == "blocked"

            # une connexion est bidirectionnelle : si NI a NI b n'est bloquée,
            # on ajoute chacune comme voisine de l'autre, dans les 2 sens
            if not zone_a_bloquee and not zone_b_bloquee:
                adjacency[conn.zone_a].append(conn.zone_b)
                adjacency[conn.zone_b].append(conn.zone_a)

        return adjacency

    def zone_cost(self, zone_name: str) -> int:
        """
        Retourne le coût en tours pour ENTRER dans cette zone
        (le coût dépend du type de la zone d'ARRIVÉE, jamais de départ).

        Règles du sujet :
        - normal   -> 1 tour
        - priority -> 1 tour (traité pareil que normal pour l'instant)
        - restricted -> 2 tours (plus cher, donc évité si possible par Dijkstra)
        - blocked  -> jamais rencontré ici (exclu du graphe par _build_adjacency)
        """
        zone = self.zones[zone_name]

        if zone.zone_type == "restricted":
            return 2
        else:
            return 1

    def find_connection(self, zone_a: str, zone_b: str) -> Connection:
        """Trouve la Connection entre deux zones, peu importe l'ordre donné."""
        for conn in self.connections:
            if (conn.zone_a == zone_a and conn.zone_b == zone_b) or (conn.zone_a == zone_b and conn.zone_b == zone_a):
                return conn
        raise ValueError(f"No connection found between {zone_a} and {zone_b}")

class PathFinder:
    """Calcule le chemin le moins coûteux entre deux zones d'un Graph."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def shortest_path(self, start: str, end: str) -> list[str]:
        """
        Combine Dijkstra (le coût) et la reconstruction du chemin (la liste
        ordonnée de zones) en une seule étape, pour l'appelant.
        """
        distances, previous = self._dijkstra(start)
        return self._reconstruct_path(previous, start, end)

    def _dijkstra(self, start: str) -> tuple[dict[str, float], dict[str, Optional[str]]]:
        """
        Calcule, depuis 'start', le coût minimum (en tours) pour
        atteindre CHAQUE zone du réseau.

        Retourne deux dicts :
        - distances : coût minimum pour atteindre chaque zone
        - previous  : pour chaque zone, la zone juste avant elle sur le
                      meilleur chemin trouvé (sert à reconstruire le chemin
                      complet ensuite, avec _reconstruct_path)
        """
        # au départ, on suppose que TOUTES les zones sont inatteignables
        # (distance infinie), sauf le point de départ (distance 0)
        distances: dict[str, float] = {node: float('inf') for node in self.graph.adjacency}
        distances[start] = 0

        # previous[zone] = "d'où je viens pour arriver ici le moins cher"
        # None au départ pour tout le monde (on ne sait encore rien)
        previous: dict[str, Optional[str]] = {node: None for node in self.graph.adjacency}

        # la file d'attente prioritaire : elle nous donne toujours
        # en premier la zone la MOINS chère à explorer parmi celles connues
        queue: list[tuple[float, str]] = [(0, start)]

        while queue:
            # on récupère la zone la moins chère actuellement connue
            current_distance, current_node = heapq.heappop(queue)

            # si on a déjà trouvé un meilleur chemin entre-temps vers
            # cette zone, cette entrée est obsolète -> on l'ignore
            if current_distance > distances[current_node]:
                continue

            # on regarde chaque voisin direct de la zone actuelle
            for neighbor in self.graph.adjacency[current_node]:
                # combien ça coûte d'entrer dans ce voisin ?
                weight = self.graph.zone_cost(neighbor)

                # coût total si je passe par current_node pour aller à neighbor
                distance = current_distance + weight

                # si ce chemin est meilleur que ce qu'on savait avant...
                if distance < distances[neighbor]:
                    distances[neighbor] = distance          # on met à jour le record
                    previous[neighbor] = current_node        # on note d'où on vient
                    heapq.heappush(queue, (distance, neighbor))  # à explorer plus tard

        return distances, previous

    def _reconstruct_path(
        self, previous: dict[str, Optional[str]], start: str, end: str
    ) -> list[str]:
        """
        Remonte le dict 'previous' depuis 'end' jusqu'à 'start',
        pour obtenir la vraie liste ordonnée des zones à traverser.

        Exemple : ['start', 'waypoint1', 'waypoint2', 'goal']
        """
        chemin = []
        node: Optional[str] = end

        # on part de la fin et on remonte vers le début,
        # en suivant "d'où je viens" à chaque étape
        while node is not None:
            chemin.append(node)
            node = previous[node]

        # à ce stade, chemin est à l'ENVERS (de end vers start)
        # donc on l'inverse pour avoir l'ordre de lecture normal
        chemin.reverse()

        return chemin

class OccupationRegistry:
    """
    Registre qui garde la trace de 'quel drone est où, à quel tour'.

    Structure interne : {zone_name: {tour: [liste_de_drone_ids]}}
    Exemple : {'waypoint1': {1: ['D1']}, 'waypoint2': {2: ['D1']}}
    """

    def __init__(self) -> None:
        # préfixé d'un underscore : c'est un détail d'implémentation privé,
        # les autres classes ne doivent passer que par register/is_available
        self._occupation: dict[str, dict[int, list[str]]] = {}

    def register(self, drone_id: str, schedule: dict[str, int]) -> None:
        """Ajoute le passage d'un drone dans le registre d'occupation global."""
        for zone_name, tour in schedule.items():

            # étape 1 : s'assurer que la zone existe dans le registre
            if zone_name not in self._occupation:
                self._occupation[zone_name] = {}

            # étape 2 : s'assurer que ce tour existe pour cette zone
            if tour not in self._occupation[zone_name]:
                self._occupation[zone_name][tour] = []

            # étape 3 : ajouter le drone à la liste de ce tour
            self._occupation[zone_name][tour].append(drone_id)

    def is_available(self, zone_name: str, tour: int, max_capacity: int) -> bool:
        """Vérifie si une zone a encore de la place pour un drone de plus à ce tour."""
        # si personne n'est jamais allé dans cette zone, ou personne à ce tour
        # précis, alors il y a 0 drone présent
        if zone_name not in self._occupation:
            nbr_zone = 0
        elif tour not in self._occupation[zone_name]:
            nbr_zone = 0
        else:
            nbr_zone = len(self._occupation[zone_name][tour])

        return max_capacity > nbr_zone


class LinkOccupationRegistry:
    """
    Registre qui garde la trace de 'quelle connexion est empruntée, par
    quel drone, à quel tour'.

    Structure interne : {(zone_a, zone_b) trié: {tour: [liste_de_drone_ids]}}
    Exemple : {('start', 'waypoint1'): {1: ['D1', 'D2']}}
    """

    def __init__(self) -> None:
        self._occupation: dict[tuple[str, str], dict[int, list[str]]] = {}

    def _cle(self, zone_a: str, zone_b: str) -> tuple[str, str]:
        """Retourne une clé unique pour identifier une connexion, peu importe le sens."""
        return tuple(sorted([zone_a, zone_b]))

    def register(self, drone_id: str, zone_a: str, zone_b: str, tour: int) -> None:
        """Enregistre qu'un drone a traversé cette connexion à ce tour."""
        cle = self._cle(zone_a, zone_b)

        if cle not in self._occupation:
            self._occupation[cle] = {}

        if tour not in self._occupation[cle]:
            self._occupation[cle][tour] = []

        self._occupation[cle][tour].append(drone_id)

    def is_available(self, zone_a: str, zone_b: str, tour: int, max_capacity: int) -> bool:
        """Vérifie si une connexion a encore de la capacité pour un drone de plus à ce tour."""
        cle = self._cle(zone_a, zone_b)

        if cle not in self._occupation:
            nb_deja_present = 0
        elif tour not in self._occupation[cle]:
            nb_deja_present = 0
        else:
            nb_deja_present = len(self._occupation[cle][tour])

        return max_capacity > nb_deja_present

class TimeAwarePathFinder:
    """
    Calcule le chemin d'un drone en tenant compte du temps : explore des
    états (tour, zone) plutôt que juste des zones, ce qui lui permet de
    choisir un autre chemin si une zone est occupée, plutôt que d'attendre
    bêtement.
    """

    def __init__(
        self,
        graph: Graph,
        occupation: OccupationRegistry,
        link_occupation: LinkOccupationRegistry,
    ) -> None:
        self.graph = graph
        self.occupation = occupation
        self.link_occupation = link_occupation

    def find_path(self, start: str, end: str) -> None:
        start_state = (0, start)
        distances: dict[tuple[int, str], float] = {start_state: 0}
        previous: dict[tuple[int, str], Optional[tuple]] = {start_state: None}
        queue: list[tuple[int, int, str]] = [(0, 0, start)]

        while queue:
            current_cost, current_tour, current_zone = heapq.heappop(queue)
            current_state = (current_tour, current_zone)

            if current_cost > distances.get(current_state, float('inf')):
                continue

            if current_zone == end:
                print("Arrivé !", current_state)
                return

            # ACTION 1 : attendre un tour de plus sur place
            wait_state = (current_tour + 1, current_zone)
            wait_cost = current_cost + 1
            if wait_cost < distances.get(wait_state, float('inf')):
                distances[wait_state] = wait_cost
                previous[wait_state] = current_state
                heapq.heappush(queue, (wait_cost, wait_state[0], wait_state[1]))

            # ACTION 2 : avancer vers chaque voisin, si disponible
            for neighbor in self.graph.adjacency[current_zone]:
                cout = self.graph.zone_cost(neighbor)
                arrival_tour = current_tour + cout
                arrival_cost = current_cost + cout

                max_capacite_zone = self.graph.zones[neighbor].max_drones
                connexion = self.graph.find_connection(current_zone, neighbor)
                max_capacite_lien = connexion.max_link_capacity

                zone_disponible = self.occupation.is_available(neighbor, arrival_tour, max_capacite_zone)
                lien_disponible = self.link_occupation.is_available(current_zone, neighbor, arrival_tour, max_capacite_lien)

                if zone_disponible and lien_disponible:
                    neighbor_state = (arrival_tour, neighbor)
                    if arrival_cost < distances.get(neighbor_state, float('inf')):
                        distances[neighbor_state] = arrival_cost
                        previous[neighbor_state] = current_state
                        heapq.heappush(queue, (arrival_cost, neighbor_state[0], neighbor_state[1]))

class Drone:
    def __init__(self, drone_id: str) -> None:
        self.drone_id = drone_id
        # events : liste de (tour, "ce qui s'affiche à ce tour")
        # remplace l'ancien schedule dict{zone: tour}
        self.events: list[tuple[int, str]] = []
        # on garde aussi un dict {zone: tour_d_arrivee_final} pour l'occupation
        # (savoir "à quel tour je suis VRAIMENT arrivé dans cette zone")
        self.schedule: dict[str, int] = {}

    def plan(
        self,
        chemin: list[str],
        graph: Graph,
        occupation: OccupationRegistry,
        link_occupation: LinkOccupationRegistry,
    ) -> None:
        schedule: dict[str, int] = {chemin[0]: 0}
        events: list[tuple[int, str]] = []
        tour_actuel = 0

        for i in range(1, len(chemin)):
            zone_precedente = chemin[i - 1]
            zone_name = chemin[i]

            cout = graph.zone_cost(zone_name)
            tour_arrivee = tour_actuel + cout

            max_capacite_zone = graph.zones[zone_name].max_drones
            connexion = graph.find_connection(zone_precedente, zone_name)
            max_capacite_lien = connexion.max_link_capacity

            while (
                not occupation.is_available(zone_name, tour_arrivee, max_capacite_zone)
                or not link_occupation.is_available(zone_precedente, zone_name, tour_arrivee, max_capacite_lien)
            ):
                tour_arrivee += 1

            # si le coût est de 2 tours (restricted), on ajoute un événement
            # intermédiaire "en transit sur la connexion" au tour juste avant
            if cout == 2:
                nom_connexion = f"{zone_precedente}{zone_name}"
                events.append((tour_arrivee - 1, nom_connexion))

            events.append((tour_arrivee, zone_name))

            schedule[zone_name] = tour_arrivee
            tour_actuel = tour_arrivee

        self.schedule = schedule
        self.events = events
        occupation.register(self.drone_id, schedule)

        zones_du_chemin = list(schedule.keys())
        for i in range(1, len(zones_du_chemin)):
            link_occupation.register(
                self.drone_id, zones_du_chemin[i - 1], zones_du_chemin[i], schedule[zones_du_chemin[i]]
            )

class Simulator:
    """Orchestre le parsing, le pathfinding et la planification de tous les drones."""

    def __init__(self, parsed_map: ParsedMap) -> None:
        self.parsed_map = parsed_map
        self.graph = Graph(parsed_map.zones, parsed_map.connections)
        self.pathfinder = PathFinder(self.graph)
        # un seul registre d'occupation, PARTAGÉ entre tous les drones,
        # c'est ce qui force naturellement l'attente en cas de conflit
        self.occupation = OccupationRegistry()
        self.drones: list[Drone] = []
        self.link_occupation = LinkOccupationRegistry()

    def run(self) -> dict[int, list[tuple[str, str]]]:
        """Calcule le chemin partagé, planifie tous les drones, et regroupe par tour."""
        # start_zone / end_zone sont Optional côté ParsedMap (avant parsing
        # complet), mais on sait qu'ils sont renseignés une fois parse()
        # terminé -> ces assert servent surtout à rassurer mypy ici
        assert self.parsed_map.start_zone is not None
        assert self.parsed_map.end_zone is not None

        # tous les drones empruntent le MÊME chemin de base (le plus court) ;
        # ce qui les différencie, c'est l'attente insérée par plan()
        chemin = self.pathfinder.shortest_path(
            self.parsed_map.start_zone, self.parsed_map.end_zone
        )

        # chaque drone est planifié DANS L'ORDRE, en tenant compte de toutes
        # les réservations déjà faites par les drones précédents
        for numero in range(1, self.parsed_map.nb_drones + 1):
            drone = Drone(f"D{numero}")
            drone.plan(chemin, self.graph, self.occupation, self.link_occupation)
            self.drones.append(drone)

        return self._organiser_par_tour()

    def _organiser_par_tour(self) -> dict[int, list[tuple[str, str]]]:
        par_tour: dict[int, list[tuple[str, str]]] = {}

        for drone in self.drones:
            for tour, destination in drone.events:
                if tour not in par_tour:
                    par_tour[tour] = []
                par_tour[tour].append((drone.drone_id, destination))

        return par_tour

    def display(self, par_tour: dict[int, list[tuple[str, str]]]) -> None:
        """Affiche la simulation tour par tour, au format demandé par le sujet."""
        if not par_tour:
            return

        # il faut parcourir les tours DANS L'ORDRE (1, 2, 3, 4...)
        nombre_de_tours = max(par_tour.keys())

        for tour in range(1, nombre_de_tours + 1):
            if tour not in par_tour:
                continue  # personne ne bouge à ce tour (rare, mais possible)

            # transformer chaque (drone_id, zone_name) en la chaîne "D1-bottleneck"
            morceaux_texte = [
                f"{drone_id}-{zone_name}" for drone_id, zone_name in par_tour[tour]
            ]

            # assembler tous les morceaux d'un même tour, séparés par un espace
            print(" ".join(morceaux_texte))

class MapParsingError(Exception):
    pass

if __name__ == "__main__":

    from parser import MapParser

    parsed = MapParser("maps/easy/01_linear_path.txt").parse()
    graph = Graph(parsed.zones, parsed.connections)
    occupation = OccupationRegistry()
    link_occupation = LinkOccupationRegistry()

    finder = TimeAwarePathFinder(graph, occupation, link_occupation)
    finder.find_path(parsed.start_zone, parsed.end_zone)

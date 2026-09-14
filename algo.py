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

        for zone_name in self.zones:
            adjacency[zone_name] = []

        for conn in self.connections:
            zone_a_bloquee = self.zones[conn.zone_a].zone_type == "blocked"
            zone_b_bloquee = self.zones[conn.zone_b].zone_type == "blocked"

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
    """Calcule le chemin le moins coûteux entre deux zones d'un Graph (sans
    tenir compte de l'occupation par d'autres drones)."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def shortest_path(self, start: str, end: str) -> list[str]:
        distances, previous = self._dijkstra(start)
        return self._reconstruct_path(previous, start, end)

    def _dijkstra(self, start: str) -> tuple[dict[str, float], dict[str, Optional[str]]]:
        distances: dict[str, float] = {node: float('inf') for node in self.graph.adjacency}
        distances[start] = 0

        previous: dict[str, Optional[str]] = {node: None for node in self.graph.adjacency}

        queue: list[tuple[float, str]] = [(0, start)]

        while queue:
            current_distance, current_node = heapq.heappop(queue)

            if current_distance > distances[current_node]:
                continue

            for neighbor in self.graph.adjacency[current_node]:
                weight = self.graph.zone_cost(neighbor)
                distance = current_distance + weight

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_node
                    heapq.heappush(queue, (distance, neighbor))

        return distances, previous

    def _reconstruct_path(
        self, previous: dict[str, Optional[str]], start: str, end: str
    ) -> list[str]:
        chemin = []
        node: Optional[str] = end

        while node is not None:
            chemin.append(node)
            node = previous[node]

        chemin.reverse()

        return chemin


class OccupationRegistry:
    """
    Registre qui garde la trace de 'quel drone est où, à quel tour'.

    Structure interne : {zone_name: {tour: [liste_de_drone_ids]}}
    Exemple : {'waypoint1': {1: ['D1']}, 'waypoint2': {2: ['D1']}}
    """

    def __init__(self) -> None:
        self._occupation: dict[str, dict[int, list[str]]] = {}

    def register(self, drone_id: str, schedule: dict[str, int]) -> None:
        """Ajoute le passage d'un drone dans le registre d'occupation global."""
        for zone_name, tour in schedule.items():

            if zone_name not in self._occupation:
                self._occupation[zone_name] = {}

            if tour not in self._occupation[zone_name]:
                self._occupation[zone_name][tour] = []

            self._occupation[zone_name][tour].append(drone_id)

    def is_available(self, zone_name: str, tour: int, max_capacity: int) -> bool:
        """Vérifie si une zone a encore de la place pour un drone de plus à ce tour."""
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
    Calcule le chemin d'UN drone en tenant compte du TEMPS : contrairement à
    PathFinder (qui calcule toujours le même chemin, peu importe qui est déjà
    passé par où), celui-ci explore des états (tour, zone) plutôt que juste
    des zones. Comme il connaît l'occupation déjà réservée par les drones
    précédents, il peut choisir un autre chemin pour éviter une zone
    occupée à un tour donné, plutôt que d'attendre bêtement sur place.
    """

    MAX_TOUR = 200  # garde-fou : évite une boucle infinie si aucun chemin n'existe

    def __init__(
        self,
        graph: Graph,
        occupation: OccupationRegistry,
        link_occupation: LinkOccupationRegistry,
    ) -> None:
        self.graph = graph
        self.occupation = occupation
        self.link_occupation = link_occupation

    def find_path(self, start: str, end: str) -> tuple[dict[str, int], list[tuple[int, str]]]:
        """
        Calcule le chemin d'un drone de start à end, en tenant compte de
        l'occupation déjà réservée par les drones précédents.

        Retourne (schedule, events) :
        - schedule : {zone: tour_d_arrivee} -> pour enregistrer dans les registres
        - events   : [(tour, "ce qui s'affiche")] -> pour le format de sortie final
        """
        start_state = (0, start)

        # distances/previous commencent VIDES (pas remplis pour toutes les
        # zones dès le départ comme dans PathFinder) car on ne connaît pas
        # à l'avance tous les états (tour, zone) possibles -> on ne remplit
        # que ceux qu'on découvre réellement au fil de l'exploration
        distances: dict[tuple[int, str], float] = {start_state: 0}
        previous: dict[tuple[int, str], Optional[tuple]] = {start_state: None}

        # chaque élément de la queue : (cout, tour, zone) - séparés plutôt
        # que groupés en (cout, (tour, zone)) car heapq compare plus
        # simplement des tuples "plats"
        queue: list[tuple[float, int, str]] = [(0, 0, start)]

        while queue:
            current_cost, current_tour, current_zone = heapq.heappop(queue)
            current_state = (current_tour, current_zone)

            # entrée obsolète (un meilleur chemin vers cet état a déjà été
            # trouvé entre-temps) -> on l'ignore, exactement comme dans
            # le Dijkstra classique de PathFinder
            if current_cost > distances.get(current_state, float('inf')):
                continue

            # arrivé à destination : on reconstruit le chemin complet
            if current_zone == end:
                return self._reconstruct(previous, current_state)

            if current_tour >= self.MAX_TOUR:
                continue

            # ACTION 1 : attendre un tour de plus sur place. Toujours
            # possible (coût 1), c'est l'option de secours qui garantit
            # que le drone ne reste jamais totalement bloqué face à une
            # zone/connexion momentanément occupée
            wait_state = (current_tour + 1, current_zone)
            wait_cost = current_cost + 1
            if wait_cost < distances.get(wait_state, float('inf')):
                distances[wait_state] = wait_cost
                previous[wait_state] = current_state
                heapq.heappush(queue, (wait_cost, wait_state[0], wait_state[1]))

            # ACTION 2 : essayer d'avancer vers chaque voisin direct.
            # Contrairement à PathFinder, on vérifie ICI si la zone ET la
            # connexion sont disponibles à ce tour précis -> c'est ce qui
            # permet à Dijkstra de "voir" qu'un autre chemin est parfois
            # plus rapide que d'attendre sur celui-ci
            for neighbor in self.graph.adjacency[current_zone]:
                cout = self.graph.zone_cost(neighbor)
                arrival_tour = current_tour + cout
                arrival_cost = current_cost + cout

                max_capacite_zone = self.graph.zones[neighbor].max_drones
                connexion = self.graph.find_connection(current_zone, neighbor)
                max_capacite_lien = connexion.max_link_capacity

                zone_disponible = self.occupation.is_available(
                    neighbor, arrival_tour, max_capacite_zone
                )
                lien_disponible = self.link_occupation.is_available(
                    current_zone, neighbor, arrival_tour, max_capacite_lien
                )

                # on ne considère cet état comme atteignable QUE si les
                # deux capacités (zone ET connexion) le permettent à ce tour
                if zone_disponible and lien_disponible:
                    neighbor_state = (arrival_tour, neighbor)
                    if arrival_cost < distances.get(neighbor_state, float('inf')):
                        distances[neighbor_state] = arrival_cost
                        previous[neighbor_state] = current_state
                        heapq.heappush(
                            queue, (arrival_cost, neighbor_state[0], neighbor_state[1])
                        )

        # la queue s'est vidée sans jamais atteindre "end" -> aucun chemin
        # disponible (carte impossible, ou capacités trop restrictives)
        raise ValueError(f"No available path found from {start} to {end}")

    def _reconstruct(
        self,
        previous: dict[tuple[int, str], Optional[tuple]],
        end_state: tuple[int, str],
    ) -> tuple[dict[str, int], list[tuple[int, str]]]:
        """
        Remonte le dict 'previous' depuis l'état final jusqu'au départ, pour
        obtenir la liste ORDONNEE des états traversés, puis la transforme en
        (schedule, events) exploitables par Drone/Simulator.
        """

        # ETAPE 1 : remonter previous, comme _reconstruct_path, mais avec
        # des ETATS (tour, zone) au lieu de simples noms de zone
        chemin_etats: list[tuple[int, str]] = []
        state: Optional[tuple[int, str]] = end_state

        while state is not None:
            chemin_etats.append(state)
            state = previous[state]

        chemin_etats.reverse()
        # exemple simple :   [(0, 'start'), (1, 'a'), (2, 'goal')]
        # exemple avec attente : [(0, 'start'), (1, 'start'), (2, 'a')]
        #   (le drone reste sur 'start' au tour 1 avant d'avancer au tour 2)

        # ETAPE 2 : parcourir ces états dans l'ordre et construire schedule/events
        schedule: dict[str, int] = {}
        events: list[tuple[int, str]] = []

        # le tout premier état est toujours le départ -> tour 0, jamais un
        # mouvement à afficher, donc on l'ajoute seulement à schedule
        premier_tour, premiere_zone = chemin_etats[0]
        schedule[premiere_zone] = premier_tour

        for i in range(1, len(chemin_etats)):
            tour_precedent, zone_precedente = chemin_etats[i - 1]
            tour_actuel, zone_actuelle = chemin_etats[i]

            # CAS 1 : la zone n'a PAS changé -> c'était une action
            # "attendre" (ACTION 1). Une attente n'est jamais affichée
            # dans la sortie finale -> on l'ignore complètement
            if zone_actuelle == zone_precedente:
                continue

            # CAS 2 : la zone a changé -> c'était une action "avancer"
            # (ACTION 2). On détermine si c'était normal (1 tour) ou
            # vers une zone restricted (2 tours)
            cout = tour_actuel - tour_precedent

            if cout == 2:
                # zone restricted : le drone est "en transit sur la
                # connexion" au tour juste AVANT d'arriver -> événement
                # intermédiaire, au format D<ID>-<connection>
                nom_connexion = f"{zone_precedente}{zone_actuelle}"
                events.append((tour_actuel - 1, nom_connexion))

            # dans TOUS les cas, on ajoute l'arrivée réelle dans la zone
            events.append((tour_actuel, zone_actuelle))

            # schedule retient toujours le dernier tour connu pour cette
            # zone -> utilisé ensuite par Drone.plan pour s'enregistrer
            # auprès des registres d'occupation
            schedule[zone_actuelle] = tour_actuel

        return schedule, events


class Drone:
    """Un drone individuel, capable de planifier son propre trajet en tenant
    compte du temps (via TimeAwarePathFinder) et de l'occupation déjà
    réservée par les drones précédents."""

    def __init__(self, drone_id: str) -> None:
        self.drone_id = drone_id
        self.schedule: dict[str, int] = {}
        self.events: list[tuple[int, str]] = []

    def plan(
        self,
        pathfinder: TimeAwarePathFinder,
        start: str,
        end: str,
        occupation: OccupationRegistry,
        link_occupation: LinkOccupationRegistry,
    ) -> None:
        """
        Calcule le trajet de ce drone (schedule + events), puis enregistre
        son passage dans les deux registres partagés, pour que les drones
        suivants en tiennent compte à leur tour.
        """
        schedule, events = pathfinder.find_path(start, end)

        self.schedule = schedule
        self.events = events

        occupation.register(self.drone_id, schedule)

        zones_du_chemin = list(schedule.keys())
        for i in range(1, len(zones_du_chemin)):
            link_occupation.register(
                self.drone_id,
                zones_du_chemin[i - 1],
                zones_du_chemin[i],
                schedule[zones_du_chemin[i]],
            )


class Simulator:
    """Orchestre le parsing, le pathfinding conscient du temps, et la
    planification de tous les drones."""

    def __init__(self, parsed_map: ParsedMap) -> None:
        self.parsed_map = parsed_map
        self.graph = Graph(parsed_map.zones, parsed_map.connections)

        # un seul jeu de registres, PARTAGÉ entre tous les drones : c'est
        # ce qui permet à TimeAwarePathFinder de "voir" les réservations
        # des drones précédents et d'adapter le chemin en conséquence
        self.occupation = OccupationRegistry()
        self.link_occupation = LinkOccupationRegistry()
        self.pathfinder = TimeAwarePathFinder(self.graph, self.occupation, self.link_occupation)

        self.drones: list[Drone] = []

    def run(self) -> dict[int, list[tuple[str, str]]]:
        """Planifie tous les drones un par un, et regroupe le résultat par tour."""
        assert self.parsed_map.start_zone is not None
        assert self.parsed_map.end_zone is not None

        # chaque drone est planifié DANS L'ORDRE : le pathfinder recalcule
        # un VRAI chemin (potentiellement différent) pour chacun, en tenant
        # compte de toutes les réservations déjà faites par les précédents
        for numero in range(1, self.parsed_map.nb_drones + 1):
            drone = Drone(f"D{numero}")
            drone.plan(
                self.pathfinder,
                self.parsed_map.start_zone,
                self.parsed_map.end_zone,
                self.occupation,
                self.link_occupation,
            )
            self.drones.append(drone)

        return self._organiser_par_tour()

    def _organiser_par_tour(self) -> dict[int, list[tuple[str, str]]]:
        """
        Transforme les events de chaque drone ({drone: [(tour, quoi)]}) en
        {tour: [(drone, quoi), ...]}, prêt pour l'affichage tour par tour.
        """
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

        nombre_de_tours = max(par_tour.keys())

        for tour in range(1, nombre_de_tours + 1):
            if tour not in par_tour:
                continue

            morceaux_texte = [
                f"{drone_id}-{zone_name}" for drone_id, zone_name in par_tour[tour]
            ]

            print(" ".join(morceaux_texte))


if __name__ == "__main__":
    from parser import MapParser

    parsed = MapParser("maps/challenger/01_the_impossible_dream.txt").parse()
    simulator = Simulator(parsed)
    par_tour = simulator.run()

    for drone in simulator.drones:
        print(drone.drone_id, ":", drone.schedule)

    print()
    simulator.display(par_tour)
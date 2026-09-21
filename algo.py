"""Pathfinding et simulation des drones (Dijkstra sur graphe temporel)."""
import heapq
import itertools
from collections import deque
from typing import Optional

from parser import Zone, Connection, ParsedMap

# Un etat = (tour, zone) : "le drone est dans `zone` a la fin du `tour`".
State = tuple[int, str]

# start et end n'ont pas de limite de capacite (sujet, section VII.4)
UNLIMITED = 10 ** 9


class Graph:
    """Graphe des zones, sans les zones blocked."""

    def __init__(
        self,
        zones: dict[str, Zone],
        connections: list[Connection],
        start: str,
        end: str,
    ) -> None:
        self.zones = zones
        self.connections = connections
        self.start = start
        self.end = end
        # acces O(1) a une connexion, quel que soit le sens
        self._conn: dict[frozenset[str], Connection] = {
            frozenset((c.zone_a, c.zone_b)): c for c in connections
        }
        self.adjacency: dict[str, list[str]] = self._build_adjacency()
        self._dist_cache: dict[str, dict[str, int]] = {}

    def _build_adjacency(self) -> dict[str, list[str]]:
        """Liste d'adjacence ; toute connexion touchant une zone blocked
        est ignoree (aucun chemin ne peut la traverser)."""
        adjacency: dict[str, list[str]] = {name: [] for name in self.zones}
        for conn in self.connections:
            a_bloquee = self.zones[conn.zone_a].zone_type == "blocked"
            b_bloquee = self.zones[conn.zone_b].zone_type == "blocked"
            if not a_bloquee and not b_bloquee:
                adjacency[conn.zone_a].append(conn.zone_b)
                adjacency[conn.zone_b].append(conn.zone_a)
        return adjacency

    def zone_cost(self, zone_name: str) -> int:
        """Cout en tours pour ENTRER dans la zone (restricted = 2)."""
        if self.zones[zone_name].zone_type == "restricted":
            return 2
        return 1

    def zone_capacity(self, zone_name: str) -> int:
        """Nombre max de drones simultanes ; illimite pour start/end."""
        if zone_name in (self.start, self.end):
            return UNLIMITED
        return self.zones[zone_name].max_drones

    def find_connection(self, zone_a: str, zone_b: str) -> Connection:
        """Connexion entre deux zones (O(1))."""
        return self._conn[frozenset((zone_a, zone_b))]

    def distances_to(self, target: str) -> dict[str, int]:
        """BFS non pondere depuis `target` (mis en cache).

        Sert uniquement a departager des etats de meme cout : a cout
        egal, on prefere celui qui rapproche du but.
        """
        if target in self._dist_cache:
            return self._dist_cache[target]

        dist: dict[str, int] = {target: 0}
        queue = deque([target])
        while queue:
            current = queue.popleft()
            for neighbor in self.adjacency[current]:
                if neighbor not in dist:
                    dist[neighbor] = dist[current] + 1
                    queue.append(neighbor)

        # zone inatteignable : "pire que tout" plutot qu'un KeyError
        pire = max(dist.values()) + 1
        for zone_name in self.zones:
            dist.setdefault(zone_name, pire)

        self._dist_cache[target] = dist
        return dist


class OccupationRegistry:
    """Nombre de drones presents dans chaque zone, tour par tour."""

    def __init__(self) -> None:
        self._occupation: dict[str, dict[int, int]] = {}

    def register(self, zone_name: str, tour: int) -> None:
        """Ajoute un drone dans `zone_name` a la fin du `tour`."""
        par_tour = self._occupation.setdefault(zone_name, {})
        par_tour[tour] = par_tour.get(tour, 0) + 1

    def is_available(
        self, zone_name: str, tour: int, max_capacity: int
    ) -> bool:
        """Vrai s'il reste de la place dans la zone a ce tour."""
        return self._occupation.get(zone_name, {}).get(tour, 0) \
            < max_capacity

    def total_count(self, zone_name: str) -> int:
        """Charge globale de la zone (tous tours confondus)."""
        return sum(self._occupation.get(zone_name, {}).values())


class LinkOccupationRegistry:
    """Nombre de drones sur chaque connexion, tour par tour."""

    def __init__(self) -> None:
        self._occupation: dict[frozenset[str], dict[int, int]] = {}

    def register(self, zone_a: str, zone_b: str, tour: int) -> None:
        """Ajoute un drone sur la connexion pendant ce tour."""
        par_tour = self._occupation.setdefault(
            frozenset((zone_a, zone_b)), {}
        )
        par_tour[tour] = par_tour.get(tour, 0) + 1

    def is_available(
        self, zone_a: str, zone_b: str, tour: int, max_capacity: int
    ) -> bool:
        """Vrai s'il reste de la place sur la connexion a ce tour."""
        par_tour = self._occupation.get(frozenset((zone_a, zone_b)), {})
        return par_tour.get(tour, 0) < max_capacity

    def total_count(self, zone_a: str, zone_b: str) -> int:
        """Charge globale de la connexion (tous tours confondus)."""
        par_tour = self._occupation.get(frozenset((zone_a, zone_b)), {})
        return sum(par_tour.values())


# (tour, penalite_priority, distance_au_but, charge, compteur, zone)
QueueItem = tuple[int, int, int, int, int, str]


class TimeAwarePathFinder:
    """Dijkstra sur l'espace (tour, zone), en tenant compte des
    reservations deja faites par les drones precedents."""

    def __init__(
        self,
        graph: Graph,
        occupation: OccupationRegistry,
        link_occupation: LinkOccupationRegistry,
        horizon: int,
    ) -> None:
        self.graph = graph
        self.occupation = occupation
        self.link_occupation = link_occupation
        self.horizon = horizon  # tour max explore (garde-fou)
        self._counter = itertools.count()

    def find_path(self, start: str, end: str) -> list[State]:
        """Chemin le plus rapide de `start` a `end`.

        Retourne TOUS les etats traverses, attentes comprises :
        [(0, 's'), (1, 's'), (2, 'a'), (3, 'g')].
        Le cout d'un etat est son tour ; a tour egal on prefere
        (1) plus de zones priority, (2) etat proche du but,
        (3) route la moins chargee.
        """
        graph = self.graph
        dist_to_goal = graph.distances_to(end)

        first: State = (0, start)
        best_pen: dict[State, int] = {first: 0}
        previous: dict[State, Optional[State]] = {first: None}
        queue: list[QueueItem] = [
            (0, 0, dist_to_goal[start], 0, next(self._counter), start)
        ]

        while queue:
            tour, pen, _dist, _charge, _n, zone = heapq.heappop(queue)
            state: State = (tour, zone)

            if pen > best_pen.get(state, 10 ** 9):
                continue  # entree obsolete

            if zone == end:
                return self._reconstruct(previous, state)

            if tour >= self.horizon:
                continue

            # ACTION 1 : attendre. Ce n'est permis que si la zone reste
            # disponible au tour suivant (un autre drone peut y arriver).
            if self.occupation.is_available(
                zone, tour + 1, graph.zone_capacity(zone)
            ):
                self._relax(
                    queue, best_pen, previous, state,
                    (tour + 1, zone), pen, dist_to_goal[zone], 0,
                )

            # ACTION 2 : avancer vers un voisin
            for neighbor in graph.adjacency[zone]:
                arrival = tour + graph.zone_cost(neighbor)

                if not self.occupation.is_available(
                    neighbor, arrival, graph.zone_capacity(neighbor)
                ):
                    continue

                # le lien est occupe pendant TOUTE la traversee
                # (1 tour normal, 2 tours vers une zone restricted)
                link_cap = graph.find_connection(
                    zone, neighbor
                ).max_link_capacity
                if not all(
                    self.link_occupation.is_available(
                        zone, neighbor, t, link_cap
                    )
                    for t in range(tour + 1, arrival + 1)
                ):
                    continue

                is_priority = graph.zones[neighbor].zone_type == "priority"
                new_pen = pen + (0 if is_priority else 1)
                charge = (
                    self.occupation.total_count(neighbor)
                    + self.link_occupation.total_count(zone, neighbor)
                )
                self._relax(
                    queue, best_pen, previous, state,
                    (arrival, neighbor), new_pen,
                    dist_to_goal[neighbor], charge,
                )

        raise ValueError(f"No available path found from {start} to {end}")

    def _relax(
        self,
        queue: list[QueueItem],
        best_pen: dict[State, int],
        previous: dict[State, Optional[State]],
        source: State,
        target: State,
        pen: int,
        dist: int,
        charge: int,
    ) -> None:
        """Enregistre `target` s'il est atteint avec une meilleure
        penalite que jusqu'ici."""
        if pen < best_pen.get(target, 10 ** 9):
            best_pen[target] = pen
            previous[target] = source
            heapq.heappush(
                queue,
                (target[0], pen, dist, charge,
                 next(self._counter), target[1]),
            )

    @staticmethod
    def _reconstruct(
        previous: dict[State, Optional[State]], end_state: State
    ) -> list[State]:
        """Remonte `previous` et retourne les etats dans l'ordre."""
        path: list[State] = []
        state: Optional[State] = end_state
        while state is not None:
            path.append(state)
            state = previous[state]
        path.reverse()
        return path


class Drone:
    """Un drone : son chemin (etats) et ses evenements d'affichage."""

    def __init__(self, drone_id: str) -> None:
        self.drone_id = drone_id
        self.states: list[State] = []
        self.events: list[tuple[int, str]] = []

    def plan(
        self,
        pathfinder: TimeAwarePathFinder,
        start: str,
        end: str,
        occupation: OccupationRegistry,
        link_occupation: LinkOccupationRegistry,
    ) -> None:
        """Calcule le chemin puis reserve zones et connexions."""
        self.states = pathfinder.find_path(start, end)
        self.events = []

        # chaque etat = 1 tour passe dans une zone (attentes comprises)
        for tour, zone in self.states:
            occupation.register(zone, tour)

        for i in range(1, len(self.states)):
            tour_prec, zone_prec = self.states[i - 1]
            tour_act, zone_act = self.states[i]

            if zone_act == zone_prec:
                continue  # attente : rien a afficher

            # le drone est sur la connexion pendant tout le trajet
            for tour in range(tour_prec + 1, tour_act + 1):
                link_occupation.register(zone_prec, zone_act, tour)

            if tour_act - tour_prec == 2:
                # zone restricted : 1er tour en vol sur la connexion
                self.events.append((tour_act - 1, f"{zone_prec}-{zone_act}"))
            self.events.append((tour_act, zone_act))


class Simulator:
    """Planifie les drones un par un et produit la sortie par tour."""

    def __init__(self, parsed_map: ParsedMap) -> None:
        assert parsed_map.start_zone is not None
        assert parsed_map.end_zone is not None
        self.parsed_map = parsed_map
        self.graph = Graph(
            parsed_map.zones,
            parsed_map.connections,
            parsed_map.start_zone,
            parsed_map.end_zone,
        )
        # registres PARTAGES : chaque drone voit les reservations
        # des drones precedents
        self.occupation = OccupationRegistry()
        self.link_occupation = LinkOccupationRegistry()

        # Borne large : attendre au depart (capacite illimitee) que les
        # drones precedents soient passes est toujours possible.
        horizon = 2 * len(parsed_map.zones) * (parsed_map.nb_drones + 1)
        self.pathfinder = TimeAwarePathFinder(
            self.graph, self.occupation, self.link_occupation, horizon
        )
        self.drones: list[Drone] = []

    def run(self) -> dict[int, list[tuple[str, str]]]:
        """Planifie tous les drones ; retourne {tour: [(drone, dest)]}.

        Raises:
            ValueError: si aucun chemin n'existe entre start et end.
        """
        assert self.parsed_map.start_zone is not None
        assert self.parsed_map.end_zone is not None

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
        """Regroupe les evenements de tous les drones par tour."""
        par_tour: dict[int, list[tuple[str, str]]] = {}
        for drone in self.drones:
            for tour, destination in drone.events:
                par_tour.setdefault(tour, []).append(
                    (drone.drone_id, destination)
                )
        return par_tour

    def display(self, par_tour: dict[int, list[tuple[str, str]]]) -> None:
        """Affiche une ligne par tour : `D1-roof1 D2-goal`."""
        for tour in range(1, max(par_tour, default=0) + 1):
            morceaux = [
                f"{drone_id}-{dest}"
                for drone_id, dest in par_tour.get(tour, [])
            ]
            print(" ".join(morceaux))
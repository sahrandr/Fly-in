"""Pathfinding and turn-by-turn simulation of drones on a zone network."""

import heapq
import itertools
from collections import deque
from typing import Optional

from parser import Connection, ParsedMap, Zone

State = tuple[int, str]

UNLIMITED = 10**9


class SimulationError(Exception):
    """Error raised during pathfinding or simulation."""


class Graph:
    """Graph of zones, excluding blocked ones."""

    def __init__(
        self,
        zones: dict[str, Zone],
        connections: list[Connection],
        start: str,
        end: str,
    ) -> None:
        """Build the graph and its adjacency list.

        Args:
            zones: All zones of the map, indexed by name.
            connections: All bidirectional connections of the map.
            start: Name of the start zone.
            end: Name of the end zone.
        """
        self.zones = zones
        self.connections = connections
        self.start = start
        self.end = end
        self._conn: dict[frozenset[str], Connection] = {
            frozenset((c.zone_a, c.zone_b)): c for c in connections
        }
        self.adjacency: dict[str, list[str]] = self._build_adjacency()
        self._dist_cache: dict[str, dict[str, int]] = {}

    def _build_adjacency(self) -> dict[str, list[str]]:
        """Build the adjacency list, ignoring blocked zones.

        Any connection touching a blocked zone is skipped, since no
        path can go through it.

        Returns:
            A mapping from each zone name to its reachable neighbors.
        """
        adjacency: dict[str, list[str]] = {name: [] for name in self.zones}
        for conn in self.connections:
            a_blocked = self.zones[conn.zone_a].zone_type == "blocked"
            b_blocked = self.zones[conn.zone_b].zone_type == "blocked"
            if not a_blocked and not b_blocked:
                adjacency[conn.zone_a].append(conn.zone_b)
                adjacency[conn.zone_b].append(conn.zone_a)
        return adjacency

    def zone_cost(self, zone_name: str) -> int:
        """Return the number of turns needed to ENTER a zone.

        Args:
            zone_name: Name of the zone to enter.

        Returns:
            2 for a restricted zone, 1 otherwise.
        """
        if self.zones[zone_name].zone_type == "restricted":
            return 2
        return 1

    def zone_capacity(self, zone_name: str) -> int:
        """Return the maximum number of simultaneous drones in a zone.

        Args:
            zone_name: Name of the zone.

        Returns:
            ``UNLIMITED`` for the start and end zones, otherwise the
            zone's ``max_drones`` value.
        """
        if zone_name in (self.start, self.end):
            return UNLIMITED
        return self.zones[zone_name].max_drones

    def find_connection(self, zone_a: str, zone_b: str) -> Connection:
        """Return the connection between two zones in O(1).

        Args:
            zone_a: Name of the first zone.
            zone_b: Name of the second zone.

        Returns:
            The ``Connection`` linking the two zones.

        Raises:
            KeyError: If the two zones are not directly connected.
        """
        return self._conn[frozenset((zone_a, zone_b))]

    def distances_to(self, target: str) -> dict[str, int]:
        """Compute unweighted BFS distances from ``target`` (cached).

        Only used as a tie-breaker between states of equal cost: the
        one closer to the goal is preferred.

        Args:
            target: Zone from which distances are computed.

        Returns:
            A mapping from each zone name to its distance to
            ``target``. Unreachable zones get a value worse than any
            reachable one, rather than being missing.
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

        worst = max(dist.values(), default=0) + 1
        for zone_name in self.zones:
            dist.setdefault(zone_name, worst)

        self._dist_cache[target] = dist
        return dist


class OccupationRegistry:
    """Number of drones present in each zone, turn by turn."""

    def __init__(self) -> None:
        """Create an empty registry."""
        self._occupation: dict[str, dict[int, int]] = {}

    def register(self, zone_name: str, turn: int) -> None:
        """Add one drone to a zone at the end of a turn.

        Args:
            zone_name: Name of the zone occupied.
            turn: Turn number at which the drone is present.
        """
        per_turn = self._occupation.setdefault(zone_name, {})
        per_turn[turn] = per_turn.get(turn, 0) + 1

    def is_available(
        self, zone_name: str, turn: int, max_capacity: int
    ) -> bool:
        """Tell whether a zone still has room at a given turn.

        Args:
            zone_name: Name of the zone.
            turn: Turn number to check.
            max_capacity: Maximum number of simultaneous drones.

        Returns:
            ``True`` if the zone is below its capacity at that turn.
        """
        return self._occupation.get(zone_name, {}).get(turn, 0) < max_capacity

    def total_count(self, zone_name: str) -> int:
        """Return the overall load of a zone, all turns combined.

        Args:
            zone_name: Name of the zone.

        Returns:
            The total number of drone-turns registered in the zone.
        """
        return sum(self._occupation.get(zone_name, {}).values())


class LinkOccupationRegistry:
    """Number of drones on each connection, turn by turn."""

    def __init__(self) -> None:
        """Create an empty registry."""
        self._occupation: dict[frozenset[str], dict[int, int]] = {}

    def register(self, zone_a: str, zone_b: str, turn: int) -> None:
        """Add one drone to a connection during a turn.

        Args:
            zone_a: One end of the connection.
            zone_b: The other end of the connection.
            turn: Turn number during which the link is used.
        """
        per_turn = self._occupation.setdefault(
            frozenset((zone_a, zone_b)), {}
        )
        per_turn[turn] = per_turn.get(turn, 0) + 1

    def is_available(
        self, zone_a: str, zone_b: str, turn: int, max_capacity: int
    ) -> bool:
        """Tell whether a connection still has room at a given turn.

        Args:
            zone_a: One end of the connection.
            zone_b: The other end of the connection.
            turn: Turn number to check.
            max_capacity: Maximum number of simultaneous drones.

        Returns:
            ``True`` if the link is below its capacity at that turn.
        """
        per_turn = self._occupation.get(frozenset((zone_a, zone_b)), {})
        return per_turn.get(turn, 0) < max_capacity

    def total_count(self, zone_a: str, zone_b: str) -> int:
        """Return the overall load of a connection, all turns combined.

        Args:
            zone_a: One end of the connection.
            zone_b: The other end of the connection.

        Returns:
            The total number of drone-turns registered on the link.
        """
        per_turn = self._occupation.get(frozenset((zone_a, zone_b)), {})
        return sum(per_turn.values())


QueueItem = tuple[int, int, int, int, int, str]


class TimeAwarePathFinder:
    """Dijkstra over the (turn, zone) space.

    Takes into account the reservations already made by previous
    drones.
    """

    def __init__(
        self,
        graph: Graph,
        occupation: OccupationRegistry,
        link_occupation: LinkOccupationRegistry,
        horizon: int,
    ) -> None:
        """Initialize the pathfinder.

        Args:
            graph: The zone graph to search.
            occupation: Zone reservations made by earlier drones.
            link_occupation: Connection reservations made by earlier
                drones.
            horizon: Maximum turn explored (safety guard).
        """
        self.graph = graph
        self.occupation = occupation
        self.link_occupation = link_occupation
        self.horizon = horizon
        self._counter = itertools.count()

    def find_path(self, start: str, end: str) -> list[State]:
        """Find the fastest path from ``start`` to ``end``.

        Returns ALL traversed states, waits included, for example
        ``[(0, 's'), (1, 's'), (2, 'a'), (3, 'g')]``. The cost of a
        state is its turn; at equal turn, the preference goes to
        (1) more priority zones, (2) a state closer to the goal,
        (3) the least loaded route.

        Args:
            start: Name of the start zone.
            end: Name of the end zone.

        Returns:
            The ordered list of ``(turn, zone)`` states.

        Raises:
            SimulationError: If no path is available within the
                horizon.
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
            turn, pen, _dist, _load, _n, zone = heapq.heappop(queue)
            state: State = (turn, zone)

            if pen > best_pen.get(state, 10**9):
                continue

            if zone == end:
                return self._reconstruct(previous, state)

            if turn >= self.horizon:
                continue

            if self.occupation.is_available(
                zone, turn + 1, graph.zone_capacity(zone)
            ):
                self._relax(
                    queue,
                    best_pen,
                    previous,
                    state,
                    (turn + 1, zone),
                    pen,
                    dist_to_goal[zone],
                    0,
                )

            for neighbor in graph.adjacency[zone]:
                arrival = turn + graph.zone_cost(neighbor)

                if not self.occupation.is_available(
                    neighbor, arrival, graph.zone_capacity(neighbor)
                ):
                    continue

                link_cap = graph.find_connection(
                    zone, neighbor
                ).max_link_capacity
                if not all(
                    self.link_occupation.is_available(
                        zone, neighbor, t, link_cap
                    )
                    for t in range(turn + 1, arrival + 1)
                ):
                    continue

                is_priority = graph.zones[neighbor].zone_type == "priority"
                new_pen = pen + (0 if is_priority else 1)
                load = self.occupation.total_count(
                    neighbor
                ) + self.link_occupation.total_count(zone, neighbor)
                self._relax(
                    queue,
                    best_pen,
                    previous,
                    state,
                    (arrival, neighbor),
                    new_pen,
                    dist_to_goal[neighbor],
                    load,
                )

        raise SimulationError(
            f"No available path found from '{start}' to '{end}'"
        )

    def _relax(
        self,
        queue: list[QueueItem],
        best_pen: dict[State, int],
        previous: dict[State, Optional[State]],
        source: State,
        target: State,
        pen: int,
        dist: int,
        load: int,
    ) -> None:
        """Record ``target`` if reached with a better penalty so far.

        Args:
            queue: The priority queue to push the new state into.
            best_pen: Best penalty known for each state.
            previous: Predecessor of each state, for path rebuilding.
            source: State the move comes from.
            target: State the move leads to.
            pen: Priority penalty accumulated to reach ``target``.
            dist: Distance from ``target`` to the goal.
            load: Load of the route used to reach ``target``.
        """
        if pen < best_pen.get(target, 10**9):
            best_pen[target] = pen
            previous[target] = source
            heapq.heappush(
                queue,
                (
                    target[0],
                    pen,
                    dist,
                    load,
                    next(self._counter),
                    target[1],
                ),
            )

    @staticmethod
    def _reconstruct(
        previous: dict[State, Optional[State]], end_state: State
    ) -> list[State]:
        """Walk back through ``previous`` and return the ordered path.

        Args:
            previous: Predecessor of each state.
            end_state: Final state of the path.

        Returns:
            The states from the initial one to ``end_state``.
        """
        path: list[State] = []
        state: Optional[State] = end_state
        while state is not None:
            path.append(state)
            state = previous[state]
        path.reverse()
        return path


class Drone:
    """A drone: its path (states) and its display events."""

    def __init__(self, drone_id: str) -> None:
        """Create a drone with an empty path.

        Args:
            drone_id: Identifier of the drone, such as ``"D1"``.
        """
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
        """Compute the drone's path, then reserve zones and links.

        Args:
            pathfinder: Pathfinder used to compute the route.
            start: Name of the start zone.
            end: Name of the end zone.
            occupation: Registry in which zone usage is recorded.
            link_occupation: Registry in which link usage is recorded.

        Raises:
            SimulationError: If no path can be found.
        """
        self.states = pathfinder.find_path(start, end)
        self.events = []

        for turn, zone in self.states:
            occupation.register(zone, turn)

        for i in range(1, len(self.states)):
            prev_turn, prev_zone = self.states[i - 1]
            cur_turn, cur_zone = self.states[i]

            if cur_zone == prev_zone:
                continue

            for turn in range(prev_turn + 1, cur_turn + 1):
                link_occupation.register(prev_zone, cur_zone, turn)

            if cur_turn - prev_turn == 2:
                self.events.append((cur_turn - 1, f"{prev_zone}-{cur_zone}"))
            self.events.append((cur_turn, cur_zone))


class Simulator:
    """Plan drones one by one and produce the per-turn output."""

    def __init__(self, parsed_map: ParsedMap) -> None:
        """Set up the graph, the registries and the pathfinder.

        Args:
            parsed_map: The validated map to simulate.

        Raises:
            SimulationError: If the map has no start or end zone.
        """
        if parsed_map.start_zone is None or parsed_map.end_zone is None:
            raise SimulationError(
                "Start or end zone is missing from parsed map."
            )

        self.parsed_map = parsed_map
        self.graph = Graph(
            parsed_map.zones,
            parsed_map.connections,
            parsed_map.start_zone,
            parsed_map.end_zone,
        )
        self.occupation = OccupationRegistry()
        self.link_occupation = LinkOccupationRegistry()

        horizon = 2 * len(parsed_map.zones) * (parsed_map.nb_drones + 1)
        self.pathfinder = TimeAwarePathFinder(
            self.graph, self.occupation, self.link_occupation, horizon
        )
        self.drones: list[Drone] = []

    def run(self) -> dict[int, list[tuple[str, str]]]:
        """Plan every drone and return the moves grouped by turn.

        Returns:
            A mapping ``{turn: [(drone_id, destination), ...]}``.

        Raises:
            SimulationError: If the start or end zone is missing, or
                if a drone cannot find a path.
        """
        start = self.parsed_map.start_zone
        end = self.parsed_map.end_zone

        if start is None or end is None:
            raise SimulationError(
                "Start or end zone is missing from parsed map."
            )

        for number in range(1, self.parsed_map.nb_drones + 1):
            drone = Drone(f"D{number}")
            drone.plan(
                self.pathfinder,
                start,
                end,
                self.occupation,
                self.link_occupation,
            )
            self.drones.append(drone)

        return self._group_by_turn()

    def _group_by_turn(self) -> dict[int, list[tuple[str, str]]]:
        """Group the events of all drones by turn.

        Returns:
            A mapping ``{turn: [(drone_id, destination), ...]}``.
        """
        by_turn: dict[int, list[tuple[str, str]]] = {}
        for drone in self.drones:
            for turn, destination in drone.events:
                by_turn.setdefault(turn, []).append(
                    (drone.drone_id, destination)
                )
        return by_turn

    def display(self, by_turn: dict[int, list[tuple[str, str]]]) -> None:
        """Print one line per turn, such as ``D1-roof1 D2-goal``.

        Args:
            by_turn: Moves grouped by turn, as returned by ``run``.
        """
        for turn in range(1, max(by_turn, default=0) + 1):
            moves = by_turn.get(turn, [])
            parts = [
                f"{drone_id}-{dest}" for drone_id, dest in moves
            ]
            line = " ".join(parts)

            print(f"{line}")

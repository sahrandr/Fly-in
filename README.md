*This project has been created as part of the 42 curriculum by sahrandr.*

# Fly-in

## Description

Fly-in is a fleet-routing simulator: a set of drones must travel from a
single start zone to a single end zone through a network of connected
zones, in the fewest possible simulation turns, while respecting per-zone
and per-connection capacity limits, zone-type movement costs (`normal`,
`restricted`, `priority`, `blocked`), and simultaneous-movement scheduling.

The project has three independent pieces, kept in separate files so each
can be reasoned about on its own:

- **`parser.py`** — reads and validates a map file into a `ParsedMap`
  (zones, connections, drone count, start/end hubs).
- **`algo.py`** — the routing engine: a time-expanded A* pathfinder plans
  one drone at a time, aware of every reservation made by drones planned
  before it, so later drones route around already-occupied zones/links
  instead of colliding with them.
- **`main.py`** (with `title_screen.py`,`map_select.py`,`ui.py` and `scenes.py`) — a raylib
  2D interface: a title screen, a map browser that scans the `maps/`
  folder, and the live simulation view.

## Instructions

### Requirements

- Python 3.10 or later
- The `raylib` Python bindings (provides the `pyray` module used for the
  graphical interface)

```bash
pip install raylib
```

### Running the simulation

```bash
python3 main.py
```

This opens a single window that walks through three screens in order:

1. **Title screen** — `NEW GAME` (play), `CONTINUER` (disabled until a save system exists),`PARAMETTRES`(disabled) and `QUIT` (settings).
2. **Map selection** — every `.txt` file found under `maps/`, grouped by
   its sub-folder (`easy`, `medium`, `hard`, `challenger`, or any other
   folder you add — no code change needed to pick up new maps).
3. **Simulation** — the chosen map is parsed, routed, and animated.

Controls during the simulation:

- Hovering a zone shows its name even if it isn't on any drone's path.

The terminal also prints the simulation in the exact turn-by-turn format
required by the subject (one line per turn, `D<id>-<zone>` entries,
space-separated), followed by the total turn count.

## Algorithm choices and implementation strategy

### Time-expanded search, one drone at a time

Each drone is planned in order (`D1`, `D2`, ...) against a **shared**
pair of registries: `OccupationRegistry` (per-zone, per-turn drone
counts) and `LinkOccupationRegistry` (per-connection, per-turn drone
counts). A drone's path is *not* computed on the plain zone graph:
states are `(turn, zone)` pairs, so the search reasons about *when* a
zone or connection is free, not just whether it is reachable.
At every state, two actions are considered:

- **wait** one turn in place, only if the zone still has room at the
  next turn. This is how the algorithm expresses "strategic waiting
  when movement is not possible".
- **advance** to a neighboring zone, only if the destination zone has
  room at the arrival turn and the connection has room on every transit
  turn. A move into a `restricted` zone costs 2 turns and reserves the
  connection for both of them, matching the rule that the drone
  occupies the connection for the whole transit.

Because later drones see every reservation made by earlier ones, the
schedule is conflict-free by construction: no separate deadlock
detection is needed. The start and end zones have unlimited capacity.

### Dijkstra over (turn, zone)

The cost of a state is its turn number, and every move costs 1 turn
(2 for `restricted`), so a Dijkstra search returns the fastest
arrival for the current drone, given the reservations already made.
The priority queue is ordered by this tuple, compared in order:

1. **turn**: the Dijkstra cost.
2. **priority penalty**: the number of non-`priority` zones entered so
   far. Among equally fast paths, the one crossing the most `priority`
   zones wins, as the subject requires.
3. **BFS distance** to the end zone (see below).
4. **load**: drone-turns already registered on the destination zone
   and the link, which spreads traffic over parallel routes.
5. **insertion counter**: keeps the heap ordering deterministic.

The search stops when the end zone is popped, or fails with a
`SimulationError` if the turn horizon
(`2 x zones x (drones + 1)`) is exceeded.

### BFS as a tie-breaker

An unweighted BFS from the end zone gives each zone its hop distance
to the goal. It is computed once per target and cached in `Graph`.
It is **not** added to the cost: it only orders states
that already share the same turn and the same priority penalty,
preferring the one closer to the goal. Unreachable zones get a
distance worse than any reachable one, instead of raising a `KeyError`.

### Optimality

Each drone gets a fastest path *given the earlier reservations*. Since
drones are planned greedily in order, the global schedule is not
guaranteed to be optimal.
 
### Correctness details worth flagging

- **Start and end zones have no capacity limit**, per the subject
  : "all drones may start in the start zone, and any number of
  drones may be delivered to the end zone." The parser's own `max_drones`
  default (`1`) would otherwise apply to these two zones as well, so the
  pathfinder explicitly overrides their capacity to unlimited rather
  than trusting the parsed value for these two specific zones.
- **Occupancy is continuous, not just at arrival.** A drone that waits
  several turns in a zone is registered as present on *every* one of
  those turns (including the wait turns), not only the turn it first
  arrived — otherwise another drone could be scheduled into a zone that
  is, in fact, still occupied.

### Complexity

For a single drone, the search explores at most `O(V · T)` states, where
`V` is the number of zones and `T` is the bound on turns before giving
up (`TimeAwarePathFinder.MAX_TOUR = 200`, a safety net against an
unsolvable map rather than a tuning parameter). Each state expansion is
`O(deg(zone))`. With `heapq`, each push/pop is `O(log(V·T))`. Planning
`N` drones sequentially gives roughly `O(N · V · T · log(V·T))` overall.
Paths are **not** cached or reused between drones — each drone's
occupancy constraints differ from the previous one's, so a cached path
would usually be stale anyway; recomputing keeps the implementation
simple at a cost that stays small in practice for the map sizes
provided.

## Visual representation

The interface is a 2D raylib scene rather than an isometric one — this
keeps every element's screen position a direct, cheap linear
transform of its map coordinates, so the whole layout recomputes
instantly on window resize (used for the borderless-fullscreen toggle).

- **Zones** are colored by the role they play in *this* solved
  simulation, not just by their declared type: `start` and `goal` keep a
  fixed identity color; a zone actually used by at least one drone's
  path is drawn brighter than one that's never visited; a `blocked` zone
  is dimmed. A zone's own declared `color=` metadata is used as its base
  tint whenever the map specifies one, so the graphical view reflects
  what the map author intended, not just an internal role label.
  `restricted` zones get an extra outer ring, `priority` zones an extra
  inner dot — so the zone-type rules from the subject are visible at a
  glance without reading the map file.
- **Drones** are rendered as small glowing orbs (additive-blended
  circles) that interpolate smoothly between their `(turn)` and
  `(turn + 1)` zone positions, each leaving a short fading trail — this
  turns the discrete, turn-by-turn schedule the algorithm produces into
  a continuous animation, which makes it much easier to *see* things
  like several drones converging on the end zone at once, or a drone
  waiting in place, than reading raw `D<id>-<zone>` log lines would.
- A **HUD** shows the current turn out of the total, a progress bar, and
  the drone count; an "ARRIVEE" marker appears once every drone is
  delivered and the animation holds on the final frame instead of
  looping or resetting.
- The **map browser** screen groups available maps by difficulty folder,
  color-coded (`easy` green, `medium` gold, `hard` red, `challenger`
  purple), so the player can gauge a map's difficulty before opening it.

## Example input and output

Given a map such as (this is the example from the subject itself):

```
nb_drones: 5

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: tunnelB 7 4 [zone=normal color=red]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: hub-roof1
connection: hub-corridorA
connection: roof1-roof2
connection: roof2-goal
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal
```

running `algo.py` = 

```
D1-roof1 D2-corridorA
D1-roof2 D2-tunnelB
D1-goal D2-goal
Total turns: 3
```

(the exact routes and turn count depend on the map's own capacities and
the number of drones; this snippet only illustrates the *format*.)

## Resources

- Dijkstra's algorithm: https://youtu.be/rHylCtXtdNs?si=bM3PfGSC79w3O2Wl and https://www.geeksforgeeks.org/python/python-program-for-dijkstras-shortest-path-algorithm-greedy-algo-7/
- raylib tutorial: https://youtu.be/UoAsDlUwjy0?si=Nor58-gEOTOoVNgM
- raylib documentation: https://pypi.org/project/raylib/
- Python: https://www.python.org/
- BFS : https://www.datacamp.com/tutorial/breadth-first-search-in-python


**AI usage:** An AI assistant was used for several distinct tasks during this project:

- **Writing test/debug** helpers to exercise the parser and the pathfinder without having to write throwaway scripts by hand each time.
- **Helping install and get started** with raylib (the pyray Python bindings), including troubleshooting the initial setup.
- **Explaining complex** parts of the subject in plainer terms — turn mechanics, zone-occupancy rules, and the exact capacity exemptions for start_hub/end_hub.
- **Brainstorming visualization ideas** for the graphical interface (the glowing-orb renderer, the title screen, the map browser) before settling on the final look.
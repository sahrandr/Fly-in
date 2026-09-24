*This project has been created as part of the 42 curriculum by sahrandr.*

# Fly-in

## Description

**Fly-in** routes a fleet of drones from a start zone to an end zone through a
network of connected zones, in the **fewest possible simulation turns**, while
respecting zone capacities, connection capacities and per-zone movement costs.

The program:

1. parses a map file (zones, connections, drone count) and validates it;
2. plans every drone's route with a time-aware pathfinding algorithm;
3. prints the plan in the required text format (one line per turn);
4. plays the result as an animated graphical simulation (raylib).

No graph library is used: the graph, the search and the reservation system are
implemented from scratch, in an object-oriented design.

![Simulation view](docs/screenshot.png)

## Instructions

### Requirements

- Python **3.10 or later**
- [raylib](https://pypi.org/project/raylib/) (provides the `pyray` module) for
  the graphical interface
- `flake8` and `mypy` for linting

### Installation

Create a virtual environment **outside the repository** (`flake8 .` scans every
sub-folder, including a `venv` placed inside it), then install:

```bash
python3 -m venv ~/.venvs/fly-in
source ~/.venvs/fly-in/bin/activate
make install
```

### Running

Maps are read from `maps/<category>/<name>.txt`. Run from the repository root:

```bash
make run
```

1. Click **JOUER** on the title screen.
2. Click a map: categories and files are discovered automatically by scanning
   `maps/`, so a new `.txt` file dropped in a sub-folder appears without any
   code change.
3. The plan is printed in the terminal, then the animation plays. Hover a zone
   to display its name. Close the window to quit.

If the map is invalid, the program prints `Error: Line N: <cause>` on stderr and
exits with status 1, without a traceback.

### Makefile rules

| Rule | Description |
|---|---|
| `make install` | Install `raylib`, `flake8` and `mypy` with pip |
| `make run` | Launch the program (`python3 main.py`) |
| `make debug` | Launch the program under `pdb` |
| `make clean` | Remove `__pycache__`, `.mypy_cache` and other caches |
| `make lint` | `flake8 .` and `mypy .` with the flags required by the subject |
| `make lint-strict` | `flake8 .` and `mypy . --strict` |

### Map file format

```text
# A comment is a full line starting with '#'
# First line: number of drones (positive integer)
nb_drones: 5
# Exactly one start and one end
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
# Regular zones: <name> <x> <y> [metadata, any order]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority max_drones=2]
hub: tunnelB 7 4
# Bidirectional connections: <zone1>-<zone2> [metadata]
connection: hub-roof1
connection: corridorA-tunnelB [max_link_capacity=2]
```

| Metadata | Applies to | Values | Default |
|---|---|---|---|
| `zone` | hubs | `normal`, `blocked`, `restricted`, `priority` | `normal` |
| `color` | hubs | any single word | `none` |
| `max_drones` | hubs | positive integer (ignored on start and end) | `1` |
| `max_link_capacity` | connections | positive integer | `1` |

Zone names cannot contain dashes or spaces. Comments must be on their own line (starting with `#`). The parser
rejects: a missing or misplaced `nb_drones`, duplicate zone names, non-integer
coordinates, malformed brackets or `key=value` pairs, unknown metadata keys,
invalid zone types, non-positive capacities, connections to undefined zones,
self-connections and duplicate connections (`a-b` and `b-a` are the same).

## Example

Input (`nb_drones: 5`, the map from the subject):

```text
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

Output (one line per turn, 6 turns):

```text
D1-corridorA D3-hub-roof1
D1-tunnelB D2-corridorA D3-roof1
D1-goal D2-tunnelB D3-roof2 D4-corridorA
D2-goal D3-goal D4-tunnelB D5-corridorA
D4-goal D5-tunnelB
D5-goal
Total turns: 6
```

How to read it: on turn 1, `D3` leaves for the **restricted** zone `roof1`. That
costs two turns, so it is *in flight* on the connection (`D3-hub-roof1`, named
`<zone1>-<zone2>`) and lands in `roof1` on turn 2. `D1` and `D2` share the
`corridorA`/`tunnelB` route, `corridorA` allowing 2 drones, `tunnelB` only 1 (so
`D2` follows `D1` one turn behind). The `blocked` zone `obstacleX` is never used.

## Algorithm

### Overview

Routing is done by **prioritized (sequential) planning on a time-expanded
graph**:

- drones are planned one after the other (`D1`, then `D2`, ...);
- each drone runs a **Dijkstra search over states `(turn, zone)`** that takes
  into account every reservation made by the drones already planned;
- once a drone's path is found, all the zones and connections it uses are
  **reserved turn by turn**, and the next drone plans around them.

Because a path is only accepted if it fits inside the existing reservations,
conflicts and deadlocks cannot occur by construction, and a drone that cannot
advance simply **waits**, which is an explicit action of the search.

### The search (`TimeAwarePathFinder`)

A state `(t, z)` means "at the end of turn `t`, the drone is in zone `z`". From a
state, two kinds of actions are explored:

- **Wait**: go to `(t+1, z)`, only if zone `z` still has capacity at turn `t+1`
  (another drone may be scheduled to arrive there).
- **Move** to a neighbour `n`: go to `(t + cost(n), n)` where `cost` is 1 for
  `normal` and `priority` zones and 2 for `restricted` zones. The move is
  allowed only if `n` has room at the arrival turn and the connection has room
  on **every turn of the crossing**. `blocked` zones are removed from the graph
  before the search starts.

Since the cost of a state is its turn number, the first time the search pops the
end zone, it has found the **earliest possible arrival for this drone** given
the reservations.

Ties between equally fast paths are broken in this order:

1. **Priority zones**: fewer non-`priority` zones entered (so `priority` zones
   are preferred, as the subject requires);
2. **Distance to the goal**: unweighted BFS distance, computed once and cached;
3. **Load**: how many reservations the next zone and connection already carry,
   which spreads drones over parallel routes.

### Rules handled

| Rule of the subject | Implementation |
|---|---|
| Zone capacity `max_drones` | `OccupationRegistry`: drones per zone **per turn**, waiting turns included |
| Start / end unlimited | `Graph.zone_capacity` returns "unlimited" for them |
| Link capacity | `LinkOccupationRegistry`: drones per connection per turn |
| Moving out frees capacity the same turn | occupancy is counted on end-of-turn states, so a drone can enter as another leaves |
| Restricted zone = 2 turns, cannot wait on the link | state jumps `(t, a) -> (t+2, b)`; the link is reserved on both turns; capacity of `b` is checked at arrival only |
| Output of a drone in flight | turn `t+1`: `D<ID>-<zone1>-<zone2>`, turn `t+2`: `D<ID>-<zone2>` |
| Any number of drones | search horizon scales with `nb_drones`; the start is unlimited, so waiting there is always possible |

### Complexity and caching

With `Z` zones, `N` drones, `d` the maximum degree and `T` the number of turns
explored (bounded by a horizon proportional to `Z * N`, and close to the final
number of turns in practice):

- one drone: at most `Z * T` states, each expanded in `O(d)` with `O(1)`
  reservation lookups (dictionaries), so `O(Z * T * d * log(Z * T))`;
- all drones: `N` times that;
- memory: `O(N * T)` reservations plus `O(Z * T)` for the current search.

Caching: BFS distances to the goal are computed **once**, and connections are
found in `O(1)` through a dictionary. Paths themselves are *not* cached between
drones on purpose, since each one depends on the reservations of the previous
drones.

Measured on the development machine: 1000 drones through a 3-zone chain are
planned in about 0.8 s, and 100 drones on a 62-zone grid with restricted and
priority zones in about 0.6 s.

### Limitations

Sequential planning is a **heuristic**: the result depends on the drone order
and is not proven optimal. A joint optimization (for example a min-cost flow on
the time-expanded graph, or conflict-based search) could find shorter plans on
some maps, at a higher cost.

### Results against the reference targets

| Map | Drones | Target | Obtained |
|---|---|---|---|
| Linear path | 2 | <= 6 | TODO |
| Simple fork | 4 | <= 8 | TODO |
| Basic capacity | 4 | <= 6 | TODO |
| Dead end trap | 5 | <= 12 | TODO |
| Circular loop | 6 | <= 15 | TODO |
| Priority puzzle | 5 | <= 12 | TODO |
| Maze nightmare | 8 | <= 30 | TODO |
| Capacity hell | 12 | <= 35 | TODO |
| Ultimate challenge | 15 | <= 45 | TODO |
| The Impossible Dream (optional) | 25 | record 45 | TODO |

## Visual representation

The graphical interface (raylib) is designed so that the state of the simulation
can be read at a glance:

- **Zone colors come from the map** (`color=...`). Known names are drawn in their
  own tint; unknown names fall back to a role color.
- **Start** and **end** are drawn as large glowing rings (green and gold).
- **Zone types** are visible on the map: a red outer ring marks a `restricted`
  zone (2 turns), a small central dot marks a `priority` zone, and a red ring
  marks a `blocked` zone. A legend is displayed at the bottom left.
- **Edges and zones used by at least one drone glow**, unused ones stay dim, so
  the routes chosen by the algorithm stand out from the rest of the network.
- **Each drone is a glowing orb with its own color and a fading trail**, moving
  smoothly between zones (48 frames per turn). A drone flying toward a
  `restricted` zone is drawn halfway along the connection, matching the text
  output.
- A **pulse ring** appears in a zone each time a drone arrives.
- The **HUD** shows `TOUR n / total`, a progress bar and the number of drones,
  and displays `ARRIVEE` once every drone is delivered.
- **Hovering a zone** shows its name; start and end are always labeled.
- Before the animation, the same plan is printed in the terminal in the format
  required by the subject, so the graphical and text outputs can be compared.

The title screen and the map selection screen follow the same visual identity.

## Project structure

```text
.
├── main.py            # entry point: parsing, simulation, graphical rendering
├── parser.py          # MapParser, Zone, Connection, ParsedMap, MapParsingError
├── algo.py            # Graph, registries, TimeAwarePathFinder, Drone, Simulator
├── title_screen.py    # title screen
├── map_select.py      # map selection screen (scans maps/)
├── maps/              # maps grouped by category (easy, medium, hard, challenger)
├── docs/screenshot.png
├── Makefile
└── README.md
```

## Resources

### References

- Dijkstra, E. W., *A note on two problems in connexion with graphs* (1959).
- Erdmann, M. and Lozano-Perez, T., *On multiple moving objects*, Algorithmica
  (1987): origin of prioritized planning.
- Silver, D., *Cooperative Pathfinding*, AIIDE (2005): searching in
  space-time with reservation tables.
- Sharon, G. et al., *Conflict-based search for optimal multi-agent
  pathfinding*, Artificial Intelligence (2015).
- Stern, R. et al., *Multi-Agent Pathfinding: Definitions, Variants, and
  Benchmarks*, SoCS (2019).
- Python documentation: <https://docs.python.org/3/> (`heapq`, `collections`,
  `typing`).
- raylib and its Python bindings: <https://www.raylib.com/>.
- PEP 8, PEP 257, flake8 and mypy documentation.

### Use of AI

AI (Claude, by Anthropic) was used during this project for:

- **Code review** of the whole project against the subject, which found rule
  violations in the first version of the planner (capacity of the end zone,
  occupation of waiting zones, connection reservation during multi-turn moves,
  connection naming, fixed turn limit, ignored `priority` zones);
- **`algo.py`**: rewriting the reservation system and the search to fix those
  issues, and adding docstrings and type hints;
- **`parser.py`**: hardening the validation so that every invalid input raises a
  `MapParsingError` with a line number;
- **`main.py`**: error handling, terminal output, drones in flight and zone
  types on screen;
- **a standalone validator** (not part of this repository) that replays the
  output and checks every occupancy, capacity and cost rule; it was run on the
  subject example, hand-written maps and 800 random maps;
- **this README and the Makefile**.

[TO COMPLETE: describe any other use of AI, for example for the graphical
screens, and what you reviewed, rewrote or tested yourself.]

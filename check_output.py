"""Rejoue la sortie de Simulator et verifie les regles du sujet."""
from parser import MapParser
from algo import Simulator


def validate(path):
    parsed = MapParser(path).parse()
    sim = Simulator(parsed)
    par_tour = sim.run()
    T = max(par_tour) if par_tour else 0
    zones = parsed.zones
    start, end = parsed.start_zone, parsed.end_zone
    conn = {}
    concat = {}
    for c in parsed.connections:
        k = frozenset((c.zone_a, c.zone_b))
        conn[k] = c
        concat[c.zone_a + c.zone_b] = (c.zone_a, c.zone_b)
        concat[c.zone_b + c.zone_a] = (c.zone_b, c.zone_a)
        concat[c.zone_a + "-" + c.zone_b] = (c.zone_a, c.zone_b)
        concat[c.zone_b + "-" + c.zone_a] = (c.zone_b, c.zone_a)
    drones = [f"D{i}" for i in range(1, parsed.nb_drones + 1)]
    pos = {d: start for d in drones}            # zone ou None si en vol
    flight = {}                                  # d -> (a, b)
    errors = []
    for t in range(1, T + 1):
        ev = dict()
        for d, dest in par_tour.get(t, []):
            if d in ev:
                errors.append(f"t{t}: {d} 2 events")
            ev[d] = dest
        link_use = {}
        for d in drones:
            if d in flight:
                a, b = flight[d]
                if ev.get(d) != b:
                    errors.append(f"t{t}: {d} en vol {a}->{b} doit arriver")
                    continue
                pos[d] = b
                del flight[d]
                link_use.setdefault(frozenset((a, b)), []).append(d)
                continue
            if d not in ev:
                continue
            dest = ev[d]
            cur = pos[d]
            if cur is None:
                continue
            if dest in zones:
                k = frozenset((cur, dest))
                if k not in conn:
                    errors.append(f"t{t}: {d} {cur}->{dest} pas de connexion")
                    continue
                if zones[dest].zone_type == "blocked":
                    errors.append(f"t{t}: {d} entre dans blocked {dest}")
                if zones[dest].zone_type == "restricted":
                    errors.append(f"t{t}: {d} restricted {dest} en 1 tour")
                pos[d] = dest
                link_use.setdefault(k, []).append(d)
            elif dest in concat:
                a, b = concat[dest]
                if a != cur:
                    errors.append(f"t{t}: {d} connexion {dest} depuis {cur}")
                flight[d] = (a, b)
                pos[d] = None
                link_use.setdefault(frozenset((a, b)), []).append(d)
            else:
                errors.append(f"t{t}: {d} destination inconnue {dest}")
        occ = {}
        for d, z in pos.items():
            if z is not None:
                occ.setdefault(z, []).append(d)
        for z, ds in occ.items():
            if z in (start, end):
                continue
            if len(ds) > zones[z].max_drones:
                errors.append(f"t{t}: zone {z} cap {zones[z].max_drones} "
                              f"mais {len(ds)} drones {ds}")
        for k, ds in link_use.items():
            if len(ds) > conn[k].max_link_capacity:
                errors.append(f"t{t}: lien {tuple(k)} cap "
                              f"{conn[k].max_link_capacity} mais {ds}")
    not_done = [d for d in drones if pos[d] != end]
    if not_done:
        errors.append(f"non livres: {not_done}")
    return T, errors, sim


if __name__ == "__main__":
    import sys
    T, errs, _ = validate(sys.argv[1])
    print(f"{T} tours, {len(errs)} violation(s)")
    for e in errs:
        print("  ", e)
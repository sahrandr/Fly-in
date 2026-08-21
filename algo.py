from parser import parse_map

def build_adjacency(zones: dict, connections: list) -> dict[str, list[str]]:
    adjacency = {}
    for nom_zone in zones:
        adjacency[nom_zone] = []

    for conn in connections:
        zone_a_bloquee = zones[conn.zone_a].zone_type == "blocked"
        zone_b_bloquee = zones[conn.zone_b].zone_type == "blocked"

        # ajouter b comme voisin de a, seulement si NI a NI b n'est bloquée
        if not zone_a_bloquee and not zone_b_bloquee:
            adjacency[conn.zone_a].append(conn.zone_b)
            adjacency[conn.zone_b].append(conn.zone_a)

    return adjacency

if __name__ == "__main__":
    resultat = parse_map("maps/test_blocked.txt")
    adjacency = build_adjacency(resultat["zones"], resultat["connections"])
    print(adjacency)


# def zone_cost(zone: Zone) -> int:
#     """Retourne le coût en tours pour entrer dans cette zone."""
#     if zone.zone_type == "restricted":
#         return 2
#     else:
#         return 1
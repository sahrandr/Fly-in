"""Parser for Fly-in map files."""


class Zone:
    def __init__(self, name: str, x: int, y: int, metadata: dict[str, str]) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.color = metadata.get("color", "none")
        self.zone_type = metadata.get("zone", "normal")
        self.max_drones = int(metadata.get("max_drones", 1))

    def __repr__(self) -> str:
        return f"Zone({self.name}, x={self.x}, y={self.y}, type={self.zone_type})"


class Connection:
    def __init__(self, zone_a: str, zone_b: str, metadata: dict[str, str]) -> None:
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = int(metadata.get("max_link_capacity", 1))

    def __repr__(self) -> str:
        return f"Connection({self.zone_a}-{self.zone_b}, capacity={self.max_link_capacity})"


def extract_name_x_y(ligne: str) -> tuple[str, int, int]:
    """Extrait le nom, x, y d'une ligne hub:/start_hub:/end_hub:"""
    reste = ligne.split(":", 1)[1].strip()
    if "[" in reste:
        part_principal = reste.split("[")[0].strip()
    else:
        part_principal = reste
    piece = part_principal.split()
    name = piece[0]
    x = int(piece[1])
    y = int(piece[2])
    return name, x, y


def extract_metadata(ligne: str) -> dict[str, str]:
    """Extrait le contenu entre [ ] et le transforme en dict."""
    if "[" not in ligne:
        return {}
    interieur = ligne.split("[")[1].replace("]", "")
    paires = interieur.split()
    my_dict = {}
    for paire in paires:
        cle, valeur = paire.split("=")
        my_dict[cle.strip()] = valeur.strip()
    return my_dict


def extract_connection(ligne: str) -> tuple[str, str]:
    """'connection: start-junction' -> ('start', 'junction')"""
    reste = ligne.split(":", 1)[1].strip()
    if "[" in reste:
        reste = reste.split("[")[0].strip()
    parties = reste.split("-")
    return (parties[0].strip(), parties[1].strip())


def extract_nb_drones(ligne: str) -> int:
    """'nb_drones: 3' -> 3"""
    reste = ligne.split(":", 1)[1].strip()
    return int(reste)


def parse_map(filepath: str) -> dict:
    zones = {}
    connections = []
    nb_drones = 0
    start_zone = None
    end_zone = None

    with open(filepath, "r") as f:
        for ligne in f:
            ligne = ligne.strip()

            if ligne == "" or ligne.startswith("#"):
                continue

            if ligne.startswith("nb_drones:"):
                nb_drones = extract_nb_drones(ligne)

            elif ligne.startswith("start_hub:"):
                name, x, y = extract_name_x_y(ligne)
                metadata = extract_metadata(ligne)
                zones[name] = Zone(name, x, y, metadata)
                start_zone = name

            elif ligne.startswith("end_hub:"):
                name, x, y = extract_name_x_y(ligne)
                metadata = extract_metadata(ligne)
                zones[name] = Zone(name, x, y, metadata)
                end_zone = name

            elif ligne.startswith("hub:"):
                name, x, y = extract_name_x_y(ligne)
                metadata = extract_metadata(ligne)
                zones[name] = Zone(name, x, y, metadata)

            elif ligne.startswith("connection:"):
                zone_a, zone_b = extract_connection(ligne)
                metadata = extract_metadata(ligne)
                connections.append(Connection(zone_a, zone_b, metadata))

    return {
        "nb_drones": nb_drones,
        "start_zone": start_zone,
        "end_zone": end_zone,
        "zones": zones,
        "connections": connections,
    }


if __name__ == "__main__":
    resultat = parse_map("maps/easy/03_basic_capacity.txt")

    print("nb_drones:", resultat["nb_drones"])
    print("start_zone:", resultat["start_zone"])
    print("end_zone:", resultat["end_zone"])

    print("\n--- zones ---")
    for nom, zone in resultat["zones"].items():
        print(zone)

    print("\n--- connections ---")
    for conn in resultat["connections"]:
        print(conn)

    bottleneck = resultat["zones"]["bottleneck"]
    print("\nmax_drones de bottleneck:", bottleneck.max_drones, type(bottleneck.max_drones))
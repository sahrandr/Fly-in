from typing import Optional


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


class ParsedMap:
    """Regroupe le résultat complet du parsing d'un fichier de carte."""

    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.start_zone: Optional[str] = None
        self.end_zone: Optional[str] = None
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []

    def __repr__(self) -> str:
        return (
            f"ParsedMap(nb_drones={self.nb_drones}, start={self.start_zone}, "
            f"end={self.end_zone}, zones={len(self.zones)}, "
            f"connections={len(self.connections)})"
        )


class MapParser:
    """Transforme un fichier .txt de carte en objet ParsedMap.

    Usage:
        parsed = MapParser("maps/easy/03_basic_capacity.txt").parse()
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath

    def parse(self) -> ParsedMap:
        """Lit le fichier ligne par ligne et construit le ParsedMap."""
        result = ParsedMap()

        with open(self.filepath, "r") as f:
            for ligne in f:
                ligne = ligne.strip()

                if ligne == "" or ligne.startswith("#"):
                    continue

                self._parse_line(ligne, result)

        return result

    def _parse_line(self, ligne: str, result: ParsedMap) -> None:
        """Identifie le type de la ligne et met à jour le ParsedMap en conséquence."""
        if ligne.startswith("nb_drones:"):
            result.nb_drones = self._extract_nb_drones(ligne)

        elif ligne.startswith("start_hub:"):
            name, x, y = self._extract_name_x_y(ligne)
            metadata = self._extract_metadata(ligne)
            result.zones[name] = Zone(name, x, y, metadata)
            result.start_zone = name

        elif ligne.startswith("end_hub:"):
            name, x, y = self._extract_name_x_y(ligne)
            metadata = self._extract_metadata(ligne)
            result.zones[name] = Zone(name, x, y, metadata)
            result.end_zone = name

        elif ligne.startswith("hub:"):
            name, x, y = self._extract_name_x_y(ligne)
            metadata = self._extract_metadata(ligne)
            result.zones[name] = Zone(name, x, y, metadata)

        elif ligne.startswith("connection:"):
            zone_a, zone_b = self._extract_connection(ligne)
            metadata = self._extract_metadata(ligne)
            result.connections.append(Connection(zone_a, zone_b, metadata))

    @staticmethod
    def _extract_name_x_y(ligne: str) -> tuple[str, int, int]:
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

    @staticmethod
    def _extract_metadata(ligne: str) -> dict[str, str]:
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

    @staticmethod
    def _extract_connection(ligne: str) -> tuple[str, str]:
        """'connection: start-junction' -> ('start', 'junction')"""
        reste = ligne.split(":", 1)[1].strip()
        if "[" in reste:
            reste = reste.split("[")[0].strip()
        parties = reste.split("-")
        return (parties[0].strip(), parties[1].strip())

    @staticmethod
    def _extract_nb_drones(ligne: str) -> int:
        """'nb_drones: 3' -> 3"""
        reste = ligne.split(":", 1)[1].strip()
        return int(reste)


if __name__ == "__main__":
    parsed = MapParser("maps/easy/03_basic_capacity.txt").parse()

    print("nb_drones:", parsed.nb_drones)
    print("start_zone:", parsed.start_zone)
    print("end_zone:", parsed.end_zone)

    print("\n--- zones ---")
    for nom, zone in parsed.zones.items():
        print(zone)

    print("\n--- connections ---")
    for conn in parsed.connections:
        print(conn)

    bottleneck = parsed.zones["bottleneck"]
    print("\nmax_drones de bottleneck:", bottleneck.max_drones, type(bottleneck.max_drones))
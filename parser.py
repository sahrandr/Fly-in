from typing import Optional

class MapParsingError(Exception):
    """Levée quand le fichier de carte contient une erreur de syntaxe ou de contenu."""
    pass

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

    VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}

    def _valider_zone_type(self, metadata: dict[str, str], numero_ligne: int) -> None:
        zone_type = metadata.get("zone", "normal")

        if zone_type not in self.VALID_ZONE_TYPES:
            raise MapParsingError(
                f"Line {numero_ligne}: invalid zone type '{zone_type}'. "
                f"Must be one of: {self.VALID_ZONE_TYPES}"
            )

    def _valider_capacite(self, valeur_str: str, nom_champ: str, numero_ligne: int) -> int:
        """Vérifie qu'une chaîne représente bien un entier positif, et la convertit."""
        if not valeur_str.isdigit():
            raise MapParsingError(
                f"Line {numero_ligne}: {nom_champ} must be a positive integer, got '{valeur_str}'"
            )

        valeur = int(valeur_str)

        if valeur <= 0:
            raise MapParsingError(
                f"Line {numero_ligne}: {nom_champ} must be positive, got {valeur}"
            )

        return valeur

    def _parse_line(self, ligne: str, result: ParsedMap, numero_ligne: int) -> None:
        """Identifie le type de la ligne et met à jour le ParsedMap en conséquence."""
        if ligne.startswith("nb_drones:"):
            reste = ligne.split(":", 1)[1].strip()
            result.nb_drones = self._valider_capacite(reste, "nb_drones", numero_ligne)

        elif ligne.startswith("start_hub:"):
            if result.start_zone is not None:
                raise MapParsingError(
            f"Line {numero_ligne}: duplicate start_hub (already defined as '{result.start_zone}')"
        )
            name, x, y = self._extract_name_x_y(ligne)
            metadata = self._extract_metadata(ligne)
            self._valider_zone_type(metadata, numero_ligne)
            if "max_drones" in metadata:
                self._valider_capacite(metadata["max_drones"], "max_drones", numero_ligne)
            result.zones[name] = Zone(name, x, y, metadata)
            result.start_zone = name

        elif ligne.startswith("end_hub:"):
            if result.end_zone is not None:
                        raise MapParsingError(
            f"Line {numero_ligne}: duplicate end_hub (already defined as '{result.end_zone}')"
        )
            name, x, y = self._extract_name_x_y(ligne)
            metadata = self._extract_metadata(ligne)
            self._valider_zone_type(metadata, numero_ligne)
            if "max_drones" in metadata:
                self._valider_capacite(metadata["max_drones"], "max_drones", numero_ligne)
            result.zones[name] = Zone(name, x, y, metadata)
            result.end_zone = name

        elif ligne.startswith("connection:"):
            zone_a, zone_b = self._extract_connection(ligne)

            if zone_a not in result.zones:
                raise MapParsingError(
                    f"Line {numero_ligne}: connection references undefined zone '{zone_a}'"
                )
            if zone_b not in result.zones:
                raise MapParsingError(
                    f"Line {numero_ligne}: connection references undefined zone '{zone_b}'"
                )
            nouvelle_cle = tuple(sorted([zone_a, zone_b]))
            for conn_existante in result.connections:
                cle_existante = tuple(sorted([conn_existante.zone_a, conn_existante.zone_b]))
                if cle_existante == nouvelle_cle:
                    raise MapParsingError(
                f"Line {numero_ligne}: duplicate connection between '{zone_a}' and '{zone_b}'"
            )

            metadata = self._extract_metadata(ligne)
            if "max_link_capacity" in metadata:
                self._valider_capacite(metadata["max_link_capacity"], "max_link_capacity", numero_ligne)
            result.connections.append(Connection(zone_a, zone_b, metadata))

        elif ligne.startswith("hub:"):
            name, x, y = self._extract_name_x_y(ligne)
            metadata = self._extract_metadata(ligne)
            self._valider_zone_type(metadata, numero_ligne)
            if "max_drones" in metadata:
                self._valider_capacite(metadata["max_drones"], "max_drones", numero_ligne)

            result.zones[name] = Zone(name, x, y, metadata)

        else:
            raise MapParsingError(f"Line {numero_ligne}: unrecognized line format: '{ligne}'")

    def parse(self) -> ParsedMap:
        # crée un ParsedMap vide, à remplir au fur et à mesure du parsing
        result = ParsedMap()

        with open(self.filepath, "r") as f:
            for numero_ligne, ligne in enumerate(f, start=1):
                ligne = ligne.strip()
                if ligne == "" or ligne.startswith("#"):
                    continue
                self._parse_line(ligne, result, numero_ligne)
        if result.start_zone is None or result.end_zone is None:
            raise MapParsingError("Map must have exactly one start_hub and one end_hub")

        return result

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
    from parser import MapParser, MapParsingError

    try:
        parsed = MapParser("maps/test_connection_dupliquee.txt").parse()
    except MapParsingError as e:
        print("Erreur détectée:", e)
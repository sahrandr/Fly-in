
import sys
from typing import Optional


class MapParsingError(Exception):
    """Erreur de syntaxe ou de validation dans un fichier de carte."""
    pass

class Zone:
    """Une zone du reseau."""

    def __init__(
        self, name: str, x: int, y: int, metadata: dict[str, str]
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.color = metadata.get("color", "none")
        self.zone_type = metadata.get("zone", "normal")
        self.max_drones = int(metadata.get("max_drones", 1))

    def __repr__(self) -> str:
        return (
            f"Zone({self.name}, x={self.x}, y={self.y}, "
            f"type={self.zone_type})"
        )


class Connection:
    """Une connexion bidirectionnelle entre deux zones."""

    def __init__(
        self, zone_a: str, zone_b: str, metadata: dict[str, str]
    ) -> None:
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = int(metadata.get("max_link_capacity", 1))

    def __repr__(self) -> str:
        return (
            f"Connection({self.zone_a}-{self.zone_b}, "
            f"capacity={self.max_link_capacity})"
        )


class ParsedMap:
    """Resultat du parsing."""

    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.start_zone: Optional[str] = None
        self.end_zone: Optional[str] = None
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []

    def __repr__(self) -> str:
        return (
            f"ParsedMap(nb_drones={self.nb_drones}, "
            f"start={self.start_zone}, end={self.end_zone}, "
            f"zones={len(self.zones)}, "
            f"connections={len(self.connections)})"
        )


class MapParser:
    """Lit un fichier de carte et le valide ligne par ligne."""

    VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
    ZONE_KEYS = {"zone", "color", "max_drones"}
    CONNECTION_KEYS = {"max_link_capacity"}

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self._connexions_vues: set[frozenset[str]] = set()

    # ------------------------------------------------------------------
    #  Validation
    # ------------------------------------------------------------------
    def _valider_zone_type(
        self, metadata: dict[str, str], numero_ligne: int
    ) -> None:
        """Le type de zone doit etre l'un des 4 types connus."""
        zone_type = metadata.get("zone", "normal")
        if zone_type not in self.VALID_ZONE_TYPES:
            raise MapParsingError(
                f"Line {numero_ligne}: invalid zone type '{zone_type}'. "
                f"Must be one of: {sorted(self.VALID_ZONE_TYPES)}"
            )

    def _valider_capacite(
        self, valeur_str: str, nom_champ: str, numero_ligne: int
    ) -> int:
        """Entier strictement positif, sinon MapParsingError."""
        if not (valeur_str.isascii() and valeur_str.isdigit()):
            raise MapParsingError(
                f"Line {numero_ligne}: {nom_champ} must be a positive "
                f"integer, got '{valeur_str}'"
            )
        valeur = int(valeur_str)
        if valeur <= 0:
            raise MapParsingError(
                f"Line {numero_ligne}: {nom_champ} must be positive, "
                f"got {valeur}"
            )
        return valeur

    @staticmethod
    def _valider_nom(nom: str, numero_ligne: int) -> None:
        """Un nom de zone ne contient ni tiret ni espace."""
        if nom == "" or "-" in nom or " " in nom:
            raise MapParsingError(
                f"Line {numero_ligne}: invalid zone name '{nom}' "
                f"(dashes and spaces are forbidden)"
            )

    # ------------------------------------------------------------------
    #  Extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _split_metadata(reste: str, numero_ligne: int) -> tuple[str, str]:
        """Separe 'partie principale' et 'contenu des crochets'.

        Retourne (principal, "") s'il n'y a pas de metadata.
        """
        if "[" not in reste and "]" not in reste:
            return reste.strip(), ""
        if reste.count("[") != 1 or reste.count("]") != 1:
            raise MapParsingError(
                f"Line {numero_ligne}: malformed metadata brackets"
            )
        debut = reste.index("[")
        fin = reste.index("]")
        if fin < debut or reste[fin + 1:].strip() != "":
            raise MapParsingError(
                f"Line {numero_ligne}: malformed metadata brackets"
            )
        return reste[:debut].strip(), reste[debut + 1:fin]

    def _extract_metadata(
        self,
        interieur: str,
        cles_valides: set[str],
        numero_ligne: int,
    ) -> dict[str, str]:
        """Transforme 'a=1 b=2' en dict, en validant la syntaxe."""
        metadata: dict[str, str] = {}
        for paire in interieur.split():
            if paire.count("=") != 1:
                raise MapParsingError(
                    f"Line {numero_ligne}: invalid metadata '{paire}' "
                    f"(expected key=value)"
                )
            cle, valeur = paire.split("=")
            if cle == "" or valeur == "":
                raise MapParsingError(
                    f"Line {numero_ligne}: invalid metadata '{paire}' "
                    f"(empty key or value)"
                )
            if cle not in cles_valides:
                raise MapParsingError(
                    f"Line {numero_ligne}: unknown metadata key '{cle}'. "
                    f"Allowed: {sorted(cles_valides)}"
                )
            if cle in metadata:
                raise MapParsingError(
                    f"Line {numero_ligne}: duplicate metadata key '{cle}'"
                )
            metadata[cle] = valeur
        return metadata

    def _extract_zone(
        self, ligne: str, numero_ligne: int
    ) -> tuple[str, int, int, dict[str, str]]:
        """Parse '<prefix>: <name> <x> <y> [metadata]'."""
        reste = ligne.split(":", 1)[1]
        principal, interieur = self._split_metadata(reste, numero_ligne)
        morceaux = principal.split()
        if len(morceaux) != 3:
            raise MapParsingError(
                f"Line {numero_ligne}: expected '<name> <x> <y>', "
                f"got '{principal}'"
            )
        nom, x_str, y_str = morceaux
        self._valider_nom(nom, numero_ligne)
        try:
            x, y = int(x_str), int(y_str)
        except ValueError:
            raise MapParsingError(
                f"Line {numero_ligne}: coordinates must be integers, "
                f"got '{x_str}' '{y_str}'"
            ) from None
        metadata = self._extract_metadata(
            interieur, self.ZONE_KEYS, numero_ligne
        )
        return nom, x, y, metadata

    def _extract_connection(
        self, ligne: str, numero_ligne: int
    ) -> tuple[str, str, dict[str, str]]:
        """Parse 'connection: <a>-<b> [metadata]'."""
        reste = ligne.split(":", 1)[1]
        principal, interieur = self._split_metadata(reste, numero_ligne)
        parties = principal.split("-")
        if len(parties) != 2 or parties[0] == "" or parties[1] == "":
            raise MapParsingError(
                f"Line {numero_ligne}: expected '<zone1>-<zone2>', "
                f"got '{principal}'"
            )
        metadata = self._extract_metadata(
            interieur, self.CONNECTION_KEYS, numero_ligne
        )
        return parties[0], parties[1], metadata

    # ------------------------------------------------------------------
    #  Parsing
    # ------------------------------------------------------------------
    def _add_zone(
        self,
        ligne: str,
        result: ParsedMap,
        numero_ligne: int,
        ignorer_capacite: bool,
    ) -> str:
        """Ajoute une zone (hub, start_hub ou end_hub). Retourne son nom.

        Sur start/end, max_drones est ignore (sujet, VII.4).
        """
        nom, x, y, metadata = self._extract_zone(ligne, numero_ligne)
        if nom in result.zones:
            raise MapParsingError(
                f"Line {numero_ligne}: duplicate zone name '{nom}'"
            )
        self._valider_zone_type(metadata, numero_ligne)
        if ignorer_capacite:
            metadata.pop("max_drones", None)
        elif "max_drones" in metadata:
            self._valider_capacite(
                metadata["max_drones"], "max_drones", numero_ligne
            )
        result.zones[nom] = Zone(nom, x, y, metadata)
        return nom

    def _parse_line(
        self, ligne: str, result: ParsedMap, numero_ligne: int
    ) -> None:
        """Interprete une ligne non vide et non commentee."""
        if ligne.startswith("nb_drones:"):
            if result.nb_drones != 0:
                raise MapParsingError(
                    f"Line {numero_ligne}: duplicate nb_drones"
                )
            reste = ligne.split(":", 1)[1].strip()
            result.nb_drones = self._valider_capacite(
                reste, "nb_drones", numero_ligne
            )

        elif ligne.startswith("start_hub:"):
            if result.start_zone is not None:
                raise MapParsingError(
                    f"Line {numero_ligne}: duplicate start_hub "
                    f"(already defined as '{result.start_zone}')"
                )
            result.start_zone = self._add_zone(
                ligne, result, numero_ligne, True
            )

        elif ligne.startswith("end_hub:"):
            if result.end_zone is not None:
                raise MapParsingError(
                    f"Line {numero_ligne}: duplicate end_hub "
                    f"(already defined as '{result.end_zone}')"
                )
            result.end_zone = self._add_zone(
                ligne, result, numero_ligne, True
            )

        elif ligne.startswith("hub:"):
            self._add_zone(ligne, result, numero_ligne, False)

        elif ligne.startswith("connection:"):
            zone_a, zone_b, metadata = self._extract_connection(
                ligne, numero_ligne
            )
            for nom in (zone_a, zone_b):
                if nom not in result.zones:
                    raise MapParsingError(
                        f"Line {numero_ligne}: connection references "
                        f"undefined zone '{nom}'"
                    )
            if zone_a == zone_b:
                raise MapParsingError(
                    f"Line {numero_ligne}: connection from '{zone_a}' "
                    f"to itself"
                )
            cle = frozenset((zone_a, zone_b))
            if cle in self._connexions_vues:
                raise MapParsingError(
                    f"Line {numero_ligne}: duplicate connection between "
                    f"'{zone_a}' and '{zone_b}'"
                )
            if "max_link_capacity" in metadata:
                self._valider_capacite(
                    metadata["max_link_capacity"],
                    "max_link_capacity",
                    numero_ligne,
                )
            self._connexions_vues.add(cle)
            result.connections.append(Connection(zone_a, zone_b, metadata))

        else:
            raise MapParsingError(
                f"Line {numero_ligne}: unrecognized line format: "
                f"'{ligne}'"
            )

    def parse(self) -> ParsedMap:
        """Parse le fichier.

        Raises:
            MapParsingError: fichier illisible ou carte invalide.
        """
        result = ParsedMap()
        self._connexions_vues = set()
        premiere_ligne_vue = False

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                for numero_ligne, brut in enumerate(f, start=1):
                    ligne = brut.strip()
                    
                    if ligne == "" or ligne.startswith("#"):
                        continue
                        
                    # la 1re ligne utile doit etre nb_drones
                    if not premiere_ligne_vue:
                        premiere_ligne_vue = True
                        if not ligne.startswith("nb_drones:"):
                            raise MapParsingError(
                                f"Line {numero_ligne}: the first line "
                                f"must define nb_drones"
                            )
                            
                    self._parse_line(ligne, result, numero_ligne)
                    
        except (OSError, UnicodeDecodeError) as err:
            raise MapParsingError(
                f"Cannot read '{self.filepath}': {err}"
            ) from err

        # --- VÉRIFICATIONS FINALES ---
        
        # 1. Si premiere_ligne_vue est toujours False, c'est qu'il n'y avait rien à lire
        if not premiere_ligne_vue:
            raise MapParsingError("Le fichier est completement vide.")
            
        # 2. Vérification des données requises
        if result.nb_drones == 0:
            raise MapParsingError("Map must define nb_drones")
            
        if result.start_zone is None or result.end_zone is None:
            raise MapParsingError(
                "Map must have exactly one start_hub and one end_hub"
            )
        
        coordones_vue = set()
        for nom_zone, zone in result.zones.items():
            coord = (zone.x, zone.y)
            if coord in coordones_vue:
                raise MapParsingError(
                    f"Invalid map: Les zones ne peuvent pas se superposer. "
                    f"Coordonnées {coord} en double trouvées sur la zone '{nom_zone}'."
                )
            coordones_vue.add(coord)
            
        return result
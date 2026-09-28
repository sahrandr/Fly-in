"""Parsing and validation of Fly-in map files."""

from typing import Optional


class MapParsingError(Exception):
    """Syntax or validation error in a map file."""

    pass


class Zone:
    """A zone of the network."""

    def __init__(
        self, name: str, x: int, y: int, metadata: dict[str, str]
    ) -> None:
        """Create a zone from its coordinates and metadata.

        Args:
            name: Unique name of the zone.
            x: X coordinate of the zone.
            y: Y coordinate of the zone.
            metadata: Optional ``color``, ``zone`` and ``max_drones``
                values, as raw strings.
        """
        self.name = name
        self.x = x
        self.y = y
        self.color = metadata.get("color", "none")
        self.zone_type = metadata.get("zone", "normal")
        self.max_drones = int(metadata.get("max_drones", 1))

    def __repr__(self) -> str:
        """Return a short readable description of the zone."""
        return (
            f"Zone({self.name}, x={self.x}, y={self.y}, "
            f"type={self.zone_type})"
        )


class Connection:
    """A bidirectional connection between two zones."""

    def __init__(
        self, zone_a: str, zone_b: str, metadata: dict[str, str]
    ) -> None:
        """Create a connection between two zones.

        Args:
            zone_a: Name of the first zone.
            zone_b: Name of the second zone.
            metadata: Optional ``max_link_capacity`` value, as a raw
                string.
        """
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = int(metadata.get("max_link_capacity", 1))

    def __repr__(self) -> str:
        """Return a short readable description of the connection."""
        return (
            f"Connection({self.zone_a}-{self.zone_b}, "
            f"capacity={self.max_link_capacity})"
        )


class ParsedMap:
    """Result of the parsing."""

    def __init__(self) -> None:
        """Create an empty parsed map."""
        self.nb_drones: int = 0
        self.start_zone: Optional[str] = None
        self.end_zone: Optional[str] = None
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []

    def __repr__(self) -> str:
        """Return a short summary of the parsed map."""
        return (
            f"ParsedMap(nb_drones={self.nb_drones}, "
            f"start={self.start_zone}, end={self.end_zone}, "
            f"zones={len(self.zones)}, "
            f"connections={len(self.connections)})"
        )


class MapParser:
    """Read a map file and validate it line by line."""

    VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
    ZONE_KEYS = {"zone", "color", "max_drones"}
    CONNECTION_KEYS = {"max_link_capacity"}

    def __init__(self, filepath: str) -> None:
        """Create a parser for the given map file.

        Args:
            filepath: Path of the map file to parse.
        """
        self.filepath = filepath
        self._seen_connections: set[frozenset[str]] = set()

    def _validate_zone_type(
        self, metadata: dict[str, str], line_number: int
    ) -> None:
        """Check that the zone type is one of the 4 known types.

        Args:
            metadata: Zone metadata, possibly containing ``zone``.
            line_number: Line number, used in error messages.

        Raises:
            MapParsingError: If the zone type is unknown.
        """
        zone_type = metadata.get("zone", "normal")
        if zone_type not in self.VALID_ZONE_TYPES:
            raise MapParsingError(
                f"Line {line_number}: invalid zone type '{zone_type}'. "
                f"Must be one of: {sorted(self.VALID_ZONE_TYPES)}"
            )

    def _validate_capacity(
        self, value_str: str, field_name: str, line_number: int
    ) -> int:
        """Convert a string to a strictly positive integer.

        Args:
            value_str: Raw value to convert.
            field_name: Name of the field, used in error messages.
            line_number: Line number, used in error messages.

        Returns:
            The value as an integer.

        Raises:
            MapParsingError: If the value is not a strictly positive
                integer.
        """
        if not (value_str.isascii() and value_str.isdigit()):
            raise MapParsingError(
                f"Line {line_number}: {field_name} must be a positive "
                f"integer, got '{value_str}'"
            )
        value = int(value_str)
        if value <= 0:
            raise MapParsingError(
                f"Line {line_number}: {field_name} must be positive, "
                f"got {value}"
            )
        return value

    @staticmethod
    def _validate_name(name: str, line_number: int) -> None:
        """Check that a zone name has no dash and no space.

        Args:
            name: Zone name to check.
            line_number: Line number, used in error messages.

        Raises:
            MapParsingError: If the name is empty or contains a dash
                or a space.
        """
        if name == "" or "-" in name or " " in name:
            raise MapParsingError(
                f"Line {line_number}: invalid zone name '{name}' "
                f"(dashes and spaces are forbidden)"
            )

    @staticmethod
    def _split_metadata(rest: str, line_number: int) -> tuple[str, str]:
        """Split the main part from the content of the brackets.

        Args:
            rest: Text following the ``prefix:`` of a line.
            line_number: Line number, used in error messages.

        Returns:
            A tuple ``(main_part, inside)``, where ``inside`` is an
            empty string if there is no metadata.

        Raises:
            MapParsingError: If the brackets are malformed.
        """
        if "[" not in rest and "]" not in rest:
            return rest.strip(), ""
        if rest.count("[") != 1 or rest.count("]") != 1:
            raise MapParsingError(
                f"Line {line_number}: malformed metadata brackets"
            )
        start = rest.index("[")
        end = rest.index("]")
        if end < start or rest[end + 1:].strip() != "":
            raise MapParsingError(
                f"Line {line_number}: malformed metadata brackets"
            )
        return rest[:start].strip(), rest[start + 1:end]

    def _extract_metadata(
        self,
        inside: str,
        valid_keys: set[str],
        line_number: int,
    ) -> dict[str, str]:
        """Turn ``'a=1 b=2'`` into a dict, validating the syntax.

        Args:
            inside: Content found between the brackets.
            valid_keys: Keys allowed for this kind of line.
            line_number: Line number, used in error messages.

        Returns:
            The metadata as a ``{key: value}`` dict.

        Raises:
            MapParsingError: If a pair is malformed, has an unknown
                key, or repeats a key.
        """
        metadata: dict[str, str] = {}
        for pair in inside.split():
            if pair.count("=") != 1:
                raise MapParsingError(
                    f"Line {line_number}: invalid metadata '{pair}' "
                    f"(expected key=value)"
                )
            key, value = pair.split("=")
            if key == "" or value == "":
                raise MapParsingError(
                    f"Line {line_number}: invalid metadata '{pair}' "
                    f"(empty key or value)"
                )
            if key not in valid_keys:
                raise MapParsingError(
                    f"Line {line_number}: unknown metadata key '{key}'. "
                    f"Allowed: {sorted(valid_keys)}"
                )
            if key in metadata:
                raise MapParsingError(
                    f"Line {line_number}: duplicate metadata key '{key}'"
                )
            metadata[key] = value
        return metadata

    def _extract_zone(
        self, line: str, line_number: int
    ) -> tuple[str, int, int, dict[str, str]]:
        """Parse ``'<prefix>: <name> <x> <y> [metadata]'``.

        Args:
            line: The full line to parse.
            line_number: Line number, used in error messages.

        Returns:
            A tuple ``(name, x, y, metadata)``.

        Raises:
            MapParsingError: If the line is malformed.
        """
        rest = line.split(":", 1)[1]
        main_part, inside = self._split_metadata(rest, line_number)
        parts = main_part.split()
        if len(parts) != 3:
            raise MapParsingError(
                f"Line {line_number}: expected '<name> <x> <y>', "
                f"got '{main_part}'"
            )
        name, x_str, y_str = parts
        self._validate_name(name, line_number)
        try:
            x, y = int(x_str), int(y_str)
        except ValueError:
            raise MapParsingError(
                f"Line {line_number}: coordinates must be integers, "
                f"got '{x_str}' '{y_str}'"
            ) from None
        metadata = self._extract_metadata(
            inside, self.ZONE_KEYS, line_number
        )
        return name, x, y, metadata

    def _extract_connection(
        self, line: str, line_number: int
    ) -> tuple[str, str, dict[str, str]]:
        """Parse ``'connection: <a>-<b> [metadata]'``.

        Args:
            line: The full line to parse.
            line_number: Line number, used in error messages.

        Returns:
            A tuple ``(zone_a, zone_b, metadata)``.

        Raises:
            MapParsingError: If the line is malformed.
        """
        rest = line.split(":", 1)[1]
        main_part, inside = self._split_metadata(rest, line_number)
        parts = main_part.split("-")
        if len(parts) != 2 or parts[0] == "" or parts[1] == "":
            raise MapParsingError(
                f"Line {line_number}: expected '<zone1>-<zone2>', "
                f"got '{main_part}'"
            )
        metadata = self._extract_metadata(
            inside, self.CONNECTION_KEYS, line_number
        )
        return parts[0], parts[1], metadata

    def _add_zone(
        self,
        line: str,
        result: ParsedMap,
        line_number: int,
        ignore_capacity: bool,
    ) -> str:
        """Add a zone (hub, start_hub or end_hub) to the result.

        On start and end zones, ``max_drones`` is ignored (subject,
        VII.4).

        Args:
            line: The full line to parse.
            result: The parsed map being built.
            line_number: Line number, used in error messages.
            ignore_capacity: Whether to discard ``max_drones``.

        Returns:
            The name of the added zone.

        Raises:
            MapParsingError: If the line is invalid or the zone name
                is already used.
        """
        name, x, y, metadata = self._extract_zone(line, line_number)
        if name in result.zones:
            raise MapParsingError(
                f"Line {line_number}: duplicate zone name '{name}'"
            )
        self._validate_zone_type(metadata, line_number)
        if ignore_capacity:
            metadata.pop("max_drones", None)
        elif "max_drones" in metadata:
            self._validate_capacity(
                metadata["max_drones"], "max_drones", line_number
            )
        result.zones[name] = Zone(name, x, y, metadata)
        return name

    def _parse_line(
        self, line: str, result: ParsedMap, line_number: int
    ) -> None:
        """Interpret a line that is neither empty nor a comment.

        Args:
            line: The stripped line to interpret.
            result: The parsed map being built.
            line_number: Line number, used in error messages.

        Raises:
            MapParsingError: If the line is invalid, duplicated, or
                references an undefined zone.
        """
        if line.startswith("nb_drones:"):
            if result.nb_drones != 0:
                raise MapParsingError(
                    f"Line {line_number}: duplicate nb_drones"
                )
            rest = line.split(":", 1)[1].strip()
            result.nb_drones = self._validate_capacity(
                rest, "nb_drones", line_number
            )

        elif line.startswith("start_hub:"):
            if result.start_zone is not None:
                raise MapParsingError(
                    f"Line {line_number}: duplicate start_hub "
                    f"(already defined as '{result.start_zone}')"
                )
            result.start_zone = self._add_zone(
                line, result, line_number, True
            )

        elif line.startswith("end_hub:"):
            if result.end_zone is not None:
                raise MapParsingError(
                    f"Line {line_number}: duplicate end_hub "
                    f"(already defined as '{result.end_zone}')"
                )
            result.end_zone = self._add_zone(
                line, result, line_number, True
            )

        elif line.startswith("hub:"):
            self._add_zone(line, result, line_number, False)

        elif line.startswith("connection:"):
            zone_a, zone_b, metadata = self._extract_connection(
                line, line_number
            )
            for name in (zone_a, zone_b):
                if name not in result.zones:
                    raise MapParsingError(
                        f"Line {line_number}: connection references "
                        f"undefined zone '{name}'"
                    )
            if zone_a == zone_b:
                raise MapParsingError(
                    f"Line {line_number}: connection from '{zone_a}' "
                    f"to itself"
                )
            key = frozenset((zone_a, zone_b))
            if key in self._seen_connections:
                raise MapParsingError(
                    f"Line {line_number}: duplicate connection between "
                    f"'{zone_a}' and '{zone_b}'"
                )
            if "max_link_capacity" in metadata:
                self._validate_capacity(
                    metadata["max_link_capacity"],
                    "max_link_capacity",
                    line_number,
                )
            self._seen_connections.add(key)
            result.connections.append(Connection(zone_a, zone_b, metadata))

        else:
            raise MapParsingError(
                f"Line {line_number}: unrecognized line format: "
                f"'{line}'"
            )

    def parse(self) -> ParsedMap:
        """Parse the map file.

        Returns:
            The validated ``ParsedMap``.

        Raises:
            MapParsingError: If the file is unreadable or the map is
                invalid.
        """
        result = ParsedMap()
        self._seen_connections = set()
        first_line_seen = False

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                for line_number, raw in enumerate(f, start=1):
                    line = raw.strip()

                    if line == "" or line.startswith("#"):
                        continue

                    if not first_line_seen:
                        first_line_seen = True
                        if not line.startswith("nb_drones:"):
                            raise MapParsingError(
                                f"Line {line_number}: the first line "
                                f"must define nb_drones"
                            )

                    self._parse_line(line, result, line_number)

        except (OSError, UnicodeDecodeError) as err:
            raise MapParsingError(
                f"Cannot read '{self.filepath}': {err}"
            ) from err

        if not first_line_seen:
            raise MapParsingError("The file is completely empty.")

        if result.nb_drones == 0:
            raise MapParsingError("Map must define nb_drones")

        if result.start_zone is None or result.end_zone is None:
            raise MapParsingError(
                "Map must have exactly one start_hub and one end_hub"
            )

        seen_coords: set[tuple[int, int]] = set()
        for zone_name, zone in result.zones.items():
            coord = (zone.x, zone.y)
            if coord in seen_coords:
                raise MapParsingError(
                    f"Invalid map: zones cannot overlap. "
                    f"Duplicate coordinates {coord} found on zone "
                    f"'{zone_name}'."
                )
            seen_coords.add(coord)

        return result

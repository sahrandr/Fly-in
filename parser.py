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

    # 1. Isoler le contenu entre crochets (en utilisant "ligne", pas un texte inventé)
    interieur = ligne.split("[")[1].replace("]", "")
    # ex: "color=yellow max_drones=2"

    # 2. Découper par espaces -> une paire par élément
    paires = interieur.split()
    # ex: ["color=yellow", "max_drones=2"]

    # 3. Boucler sur chaque paire et construire le dict
    my_dict = {}
    for paire in paires:
        cle, valeur = paire.split("=")
        my_dict[cle.strip()] = valeur.strip()

    return my_dict

def extract_connection(ligne: str) -> tuple[str, str]:
    """'connection: start-junction' -> ('start', 'junction')"""
    # 1. enlever "connection:" du début (comme pour hub:)
    reste = ligne.split(":", 1)[1].strip()
    # reste = "start-junction" ou "corridorA-tunnelB [max_link_capacity=2]"

    # 2. enlever la partie [metadata] si elle existe
    if "[" in reste:
        reste = reste.split("[")[0].strip()
    # reste = "start-junction" ou "corridorA-tunnelB"

    # 3. découper sur le "-"
    parties = reste.split("-")
    return (parties[0].strip(), parties[1].strip())


def extract_nb_drones(ligne: str) -> int:
    """'nb_drones: 3' -> 3"""
    reste = ligne.split(":", 1)[1].strip()
    inter = int(reste)
    return(inter)

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
                zones[name] = {"x": x, "y": y, "metadata": metadata}
                start_zone = name

            elif ligne.startswith("end_hub:"):
                name, x, y = extract_name_x_y(ligne)
                metadata = extract_metadata(ligne)
                zones[name] = {"x": x, "y": y, "metadata": metadata}
                end_zone = name

            elif ligne.startswith("hub:"):
                name, x, y = extract_name_x_y(ligne)
                metadata = extract_metadata(ligne)
                zones[name] = {"x": x, "y": y, "metadata": metadata}

            elif ligne.startswith("connection:"):
                zone_a, zone_b = extract_connection(ligne)
                connections.append((zone_a, zone_b))

    return {
        "nb_drones": nb_drones,
        "start_zone": start_zone,
        "end_zone": end_zone,
        "zones": zones,
        "connections": connections,
    }
# Fly-in — Journal de progression

*Résumé de ce qui a été appris et construit jusqu'ici sur le projet.*

## 1. Le parser (`parser.py`)

### Objectif
Transformer le fichier `.txt` de carte (texte brut) en objets Python utilisables par le reste du programme.

### Ce qui a été construit

**Deux classes de données :**
- `Zone` — nom, x, y, type (`normal`/`restricted`/`priority`/`blocked`), couleur, `max_drones`
- `Connection` — les deux zones reliées, `max_link_capacity`

Chaque classe a une méthode `__repr__` : une méthode spéciale (un "dunder", double underscore) que Python appelle automatiquement avec `print()`, pour afficher un objet de façon lisible au lieu de son adresse mémoire brute.

**Quatre fonctions d'extraction**, chacune testée isolément avant d'être assemblée :
- `extract_name_x_y(ligne)` — récupère nom/x/y d'une ligne `hub:`/`start_hub:`/`end_hub:`
- `extract_metadata(ligne)` — transforme le contenu entre `[...]` en dict (`color=yellow max_drones=2` → `{'color': 'yellow', 'max_drones': '2'}`)
- `extract_connection(ligne)` — récupère les deux noms de zones reliées
- `extract_nb_drones(ligne)` — récupère le nombre de drones

**Une fonction d'assemblage :**
- `parse_map(filepath)` — lit le fichier ligne par ligne, ignore commentaires/lignes vides, identifie le type de chaque ligne, construit les objets `Zone`/`Connection`, retourne le tout dans un dict (`nb_drones`, `start_zone`, `end_zone`, `zones`, `connections`)

### Concepts clés appris
- Lire un fichier ligne par ligne avec `with open(...) as f: for ligne in f:`
- `.strip()`, `.split()`, `.startswith()` pour découper du texte
- Une fonction (`def`) ne s'exécute que si on l'**appelle** — la définir ne suffit pas
- Une fonction doit être définie **une seule fois**, en dehors de toute boucle
- `__init__` et `__repr__` sont des méthodes spéciales appelées automatiquement par Python

## 2. Construction du graphe (`build_adjacency`)

### Objectif
Transformer la liste plate de connexions en une structure où chaque zone connaît directement ses voisins — indispensable pour que l'algorithme de pathfinding puisse naviguer efficacement.

### Principe
Pour chaque connexion (bidirectionnelle), on ajoute chaque zone comme voisine de l'autre, **sauf si l'une des deux est `blocked`** — auquel cas on n'ajoute rien du tout, dans aucun des deux sens.

```python
{'start': ['waypoint1'], 'waypoint1': ['start', 'waypoint2'], ...}
```

### Piège rencontré et corrigé
Un premier essai ne vérifiait qu'un seul "sens" à la fois, ce qui laissait une zone bloquée avec des voisins dans sa propre liste. La correction : vérifier **les deux zones concernées** avant d'ajouter quoi que ce soit, dans un seul `if` combiné.

## 3. Le coût des zones (`zone_cost`)

### Règle du sujet
Le coût pour se déplacer dépend du type de la zone d'**arrivée** (jamais du départ) :
- `normal` → 1 tour
- `priority` → 1 tour
- `restricted` → 2 tours
- `blocked` → déjà exclu du graphe par `build_adjacency`, donc jamais rencontré ici

## 4. Dijkstra (`dijkstra`)

### Objectif
Pour **un seul drone**, calculer le coût minimum (en tours) pour atteindre chaque zone depuis le départ, en tenant compte des coûts de zones.

### Principe général
1. Toutes les distances commencent à l'infini, sauf le départ (0)
2. Une file d'attente prioritaire (`heapq`) explore toujours en premier la zone la moins chère connue
3. Pour chaque voisin exploré, on calcule si on peut l'atteindre moins cher qu'avant
4. Si oui, on met à jour son coût et on programme son exploration future
5. On répète jusqu'à épuisement de la file

### Concepts clés appris
- `heapq` : une structure de "tas" qui retourne toujours l'élément le plus petit en premier
- La vérification `if current_distance > distances[current_node]: continue` sert à ignorer les entrées obsolètes qui peuvent traîner dans la file après qu'un meilleur chemin a été trouvé entre-temps
- `previous[zone]` retient "d'où je viens" pour chaque zone sur le meilleur chemin trouvé — la base pour reconstruire le chemin complet ensuite

## 5. Reconstruction du chemin (`reconstruct_path`)

### Objectif
Dijkstra donne le **coût**, pas le **chemin**. Cette fonction remonte le dict `previous` depuis l'arrivée jusqu'au départ, pour obtenir la vraie liste ordonnée des zones à traverser.

### Principe
On part de `end`, on suit `previous` à l'envers jusqu'à tomber sur `None` (= le départ), puis on inverse la liste obtenue (`.reverse()`) pour la remettre dans l'ordre de lecture normal.

## 6. Chemin avec tours (`chemin_avec_tours` / `planifier_chemin_avec_attente`)

### Le problème de départ
Appeler `dijkstra` plusieurs fois avec les mêmes paramètres donne toujours **le même chemin** — l'algorithme ne sait rien des autres drones. Il fallait donc ajouter une notion de **temps** (le tour) à chaque étape du chemin, pas juste la distance totale.

### `chemin_avec_tours` (version simple, sans conflit)
Transforme une liste de zones (`['start', 'waypoint1', 'waypoint2', 'goal']`) en un dict `{zone: tour_d_arrivee}`, en utilisant `zone_cost` pour savoir de combien le tour avance à chaque étape (1 pour normal/priority, 2 pour restricted).

### `planifier_chemin_avec_attente` (version avec gestion des conflits)
Reprend le même principe, mais avant d'accepter le tour d'arrivée calculé pour une zone, vérifie avec `zone_disponible` si elle est déjà pleine à ce tour. Si oui, **incrémente le tour** (le drone attend un tour de plus) jusqu'à trouver un tour où la zone est libre.

## 7. Le registre d'occupation (`add_to_occupation` / `zone_disponible`)

### Objectif
Garder la trace de "qui est où, à quel tour", pour permettre à chaque nouveau drone de vérifier s'il peut avancer ou doit attendre.

### Structure retenue
Un dict à deux niveaux : `{zone_name: {tour: [liste_de_drone_ids]}}`.

```python
{'waypoint1': {1: ['D1']}, 'waypoint2': {2: ['D1']}}
```

### `add_to_occupation(occupation, drone_id, chemin_tours)`
Parcourt le chemin d'un drone et enregistre sa présence dans le registre global, en créant les niveaux manquants (`zone`, puis `tour`) au fur et à mesure.

### `zone_disponible(occupation, zone_name, tour, zones)`
Compare le nombre de drones déjà présents dans une zone à un tour donné avec `zone.max_drones`. Gère le cas où la zone/le tour n'existe pas encore dans `occupation` (= personne présent, donc disponible).

### Piège rencontré et corrigé
Accéder directement à `occupation[zone_name][tour]` sans vérifier son existence provoque un `KeyError` dès qu'une zone/tour n'a encore jamais été visité — il faut vérifier l'existence à chaque niveau avant d'y accéder.

## 8. Généraliser à N drones (`planifier_tous_les_drones`)

### Objectif
Ne plus coder "D1", "D2" en dur, mais boucler automatiquement sur `nb_drones`.

### Principe
```python
for numero in range(1, nb_drones + 1):
    drone_id = f"D{numero}"
    chemin_tours = planifier_chemin_avec_attente(chemin, zones, occupation)
    add_to_occupation(occupation, drone_id, chemin_tours)
```

Chaque drone est planifié **dans l'ordre**, en tenant compte de toutes les réservations déjà faites par les drones précédents — c'est cette dépendance à l'`occupation` partagée qui force naturellement l'attente quand une zone est déjà prise.

### Résultat validé
Testé sur `03_basic_capacity.txt` (4 drones, `bottleneck` avec `max_drones=2`) : D1/D2 passent ensemble au tour 1, D3/D4 doivent attendre et passent au tour 2 — comportement conforme aux règles de capacité du sujet.

## 9. Le format de sortie (`organiser_par_tour` / `afficher_simulation`)

### Le problème
`planifier_tous_les_drones` donne les données organisées **par drone** (`{drone: {zone: tour}}`), mais le format de sortie attendu par le sujet est organisé **par tour** (une ligne par tour, listant tous les drones qui bougent).

### `organiser_par_tour`
Réorganise `{drone: {zone: tour}}` en `{tour: [(drone, zone), ...]}`, en ignorant le tour 0 (le départ n'est pas un mouvement).

### `afficher_simulation`
Parcourt les tours dans l'ordre (`1` à `max`), et pour chaque tour, assemble tous les mouvements en une ligne texte du type `D1-bottleneck D2-bottleneck`, avec `" ".join(...)` pour coller les morceaux séparés par un espace.

### Résultat obtenu (exemple sur `03_basic_capacity.txt`)
```
D1-bottleneck D2-bottleneck
D1-wide_area D2-wide_area D3-bottleneck D4-bottleneck
D1-goal D2-goal D3-wide_area D4-wide_area
D3-goal D4-goal
```

## Pipeline complet obtenu à ce stade

```
fichier .txt
  → parse_map                        (Zone, Connection, nb_drones, start/end)
  → build_adjacency                  (graphe, zones bloquées exclues)
  → dijkstra + reconstruct_path      (chemin le plus court, un seul drone)
  → planifier_tous_les_drones        (chemin de chaque drone + attente si conflit)
  → organiser_par_tour               (regroupement par tour)
  → afficher_simulation              (texte au format attendu par le sujet)
```

## Ce qui reste à faire

- [ ] Gestion des **erreurs de parsing** (fichier mal formé → message clair avec numéro de ligne, VII.4)
- [ ] Transformer le parser et l'algo en vraies **classes** (`MapParser`, `Simulator`...) pour être pleinement orienté objet
- [ ] Gérer la capacité des **connexions** (`max_link_capacity`) — actuellement seule la capacité des zones est vérifiée
- [ ] Gérer correctement les zones `restricted` dans la sortie : le drone est "en transit sur la connexion" pendant 2 tours et devrait apparaître avec le format `D<ID>-<connection>` pendant ce temps (actuellement traité comme un saut direct)
- [ ] Ajouter la **visualisation** (pygame — écran, zones, connexions, animation des drones)
- [ ] Écrire le vrai `README.md` du projet (format imposé par le sujet, Chapitre VIII)
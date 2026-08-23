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

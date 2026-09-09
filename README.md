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

## 10. Passage en architecture orientée objet complète

### Objectif
Respecter la contrainte du sujet (Chapitre V : *"The project must be completely object-oriented"*), en remplaçant les fonctions libres par des classes dédiées, chacune avec une seule responsabilité.

### Classes obtenues (dans `algo.py`)
- `Graph` — encapsule `zones`, `connections`, l'adjacence (`_build_adjacency`), et `zone_cost`. Construit l'adjacence une seule fois à la création, pas recalculée à chaque appel.
- `PathFinder` — encapsule Dijkstra (`_dijkstra`) et la reconstruction de chemin (`_reconstruct_path`), exposés via une seule méthode publique `shortest_path(start, end)`.
- `OccupationRegistry` — le registre d'occupation des zones (équivalent de `add_to_occupation`/`zone_disponible`, mais en classe : `register()` et `is_available()`).
- `Drone` — un drone individuel, avec son `drone_id` et sa méthode `plan()` qui calcule son propre trajet en tenant compte d'un `OccupationRegistry` partagé.
- `Simulator` — orchestre tout : construit le `Graph`, le `PathFinder`, les `Drone`, et regroupe le résultat par tour (`run()`, `_organiser_par_tour()`, `display()`).

### Piège rencontré et corrigé
Une classe `Simulator` a été accidentellement définie deux fois dans le même fichier — en Python, la deuxième définition écrase silencieusement la première, ce qui masquait le bug sans lever d'erreur immédiate. Un bug d'indentation similaire (une méthode désindentée par erreur, sortie de sa classe) a provoqué une `AttributeError` du type *"object has no attribute"* alors que la méthode existait bien dans le fichier, juste au mauvais niveau d'indentation.

### `ParsedMap` (dans `parser.py`)
Une classe qui regroupe le résultat complet du parsing (`nb_drones`, `start_zone`, `end_zone`, `zones`, `connections`), avec des valeurs par défaut dans `__init__()` — donc s'instancie sans argument (`ParsedMap()`), à ne pas confondre avec un appel avec mots-clés qui ferait planter le constructeur.

## 11. Capacité des connexions (`max_link_capacity`)

### Le problème
La capacité des zones (`max_drones`) était déjà gérée, mais pas celle des connexions (`max_link_capacity`) — un drone pouvait emprunter n'importe quelle connexion sans limite.

### La difficulté : identifier une connexion de façon unique
Une connexion est bidirectionnelle (`a-b` ou `b-a`), donc il faut une clé qui donne le même résultat peu importe le sens :
```python
def _cle(self, zone_a: str, zone_b: str) -> tuple[str, str]:
    return tuple(sorted([zone_a, zone_b]))
```
`sorted([...])` trie alphabétiquement, donc `("start", "waypoint1")` est obtenu que l'entrée soit `start, waypoint1` ou `waypoint1, start`.

### `LinkOccupationRegistry`
Même structure et principe que `OccupationRegistry`, mais indexée par cette clé triée plutôt que par un simple nom de zone : `{(zone_a, zone_b) triée: {tour: [drone_ids]}}`.

### Piège rencontré et corrigé (import circulaire)
`algo.py` important depuis `parser.py`, et `parser.py` important depuis `algo.py` en retour (pour une exception `MapParsingError`) créait un import circulaire, provoquant une `ImportError` déroutante. Solution : l'exception doit vivre dans le fichier qui en a la responsabilité logique (`parser.py`, puisqu'elle concerne des erreurs de parsing), et les autres fichiers l'importent depuis là — jamais l'inverse.

### Résultat testé
Sur une carte de test avec `max_link_capacity=1` et 3 drones, chaque drone traverse la connexion limitée **un par un**, à des tours différents, plutôt que tous simultanément.

## 12. Gestion d'erreurs de parsing (VII.4)

### Principe général
Une exception personnalisée, `MapParsingError`, levée avec un message qui précise toujours le **numéro de ligne** et la **cause**, plutôt que de laisser Python planter avec une erreur brute.

### Suivi du numéro de ligne
```python
for numero_ligne, ligne in enumerate(f, start=1):
```
`enumerate(f, start=1)` donne `(numero_ligne, ligne)` à chaque itération, en commençant à `1` (plus naturel pour un humain que `0`).

### Validations mises en place
- **Type de zone invalide** — vérifie que `zone_type` fait partie de `{normal, blocked, restricted, priority}`
- **`max_drones`/`max_link_capacity`/`nb_drones` positifs** — `_valider_capacite` vérifie qu'une chaîne est un entier positif (`.isdigit()` rejette déjà les nombres négatifs, puisque le signe `-` n'est pas un chiffre) avant de la convertir
- **Connexion vers une zone non définie** — vérifie que `zone_a` et `zone_b` existent déjà dans `result.zones` au moment du parsing de la ligne `connection:`
- **Connexion dupliquée** (a-b == b-a) — compare la clé triée de la nouvelle connexion à celles déjà enregistrées
- **Doublon de `start_hub:`/`end_hub:`** — vérifie que `result.start_zone`/`result.end_zone` valent encore `None` avant de les assigner
- **Absence de `start_hub:`/`end_hub:`** — vérifiée après la boucle de parsing complète, puisqu'on ne peut être sûr de leur absence qu'une fois tout le fichier lu
- **Ligne de format non reconnu** — un `else` final dans `_parse_line` qui lève une erreur si aucun des `elif` ne correspond

## 13. Zones `restricted` en transit (format `D<ID>-<connection>`)

### Le problème
Une zone `restricted` coûte 2 tours, mais était traitée comme un simple saut direct — le drone "disparaissait" un tour, sans jamais apparaître comme "en transit sur la connexion", contrairement à ce qu'exige le sujet (VII.3/VII.5).

### La restructuration
`Drone` ne stocke plus seulement `{zone: tour_arrivee}` (le `schedule`), mais aussi une liste `events` de `(tour, ce_qui_s_affiche)` :
- zone `normal`/`priority` (coût 1) → une seule entrée `(tour, zone_name)`
- zone `restricted` (coût 2) → deux entrées : `(tour - 1, nom_connexion)` (transit) puis `(tour, zone_name)` (arrivée)

Le nom de la connexion pendant le transit est simplement la concaténation des deux noms de zones : `f"{zone_precedente}{zone_name}"`.

### `Simulator._organiser_par_tour` simplifiée
Comme `events` ne contient plus jamais le tour 0 (départ), la vérification `if tour == 0: continue` a pu être retirée — la boucle se contente de regrouper chaque `(tour, destination)` par tour.

### Résultat testé
Sur une carte de test forçant le passage par une zone restricted (`start → roof1 (restricted) → goal`) :
```
D1-startroof1     <- tour 1 : transit vers roof1
D1-roof1          <- tour 2 : arrivée à roof1
D1-goal           <- tour 3 : arrivée à goal
```

## 14. Visualisation graphique (pygame)

### Architecture — classe `FlyInVisualizer`
Une seule classe qui encapsule toute la partie graphique : chargement de la carte et du planning (via `Simulator`), conversion coordonnées carte → pixels, chargement/découpage du spritesheet d'animation, boucle de jeu.

### Principes clés
- **`map_to_pixel(x, y)`** : convertit les coordonnées logiques (souvent petites, 0 à 5) en pixels à l'écran, via un `SCALE` et un `OFFSET` — sans ça, toute la carte serait collée dans un coin, minuscule
- **Timing sans bloquer la fenêtre** : `pygame.time.get_ticks()` (millisecondes écoulées depuis le lancement) plutôt que `time.sleep()`, qui gèlerait complètement la fenêtre (elle deviendrait "ne répond pas" au niveau de l'OS)
- **Animation par frames** : un spritesheet (plusieurs images côte à côte dans un seul PNG) est découpé avec `pygame.Rect` + `.subsurface()`, puis les frames défilent en boucle avec le même principe de chronomètre que ci-dessus
- **GIF animé en fond** : pygame ne lit pas nativement les GIF multi-frames — Pillow (`PIL.Image`) sert de traducteur : `.seek(i)` déplace le curseur de lecture vers la frame `i`, `.tobytes()` puis `pygame.image.fromstring(...)` reconstruit une vraie `Surface` pygame à partir des données brutes
- **Teinte par drone** : `surface.fill(couleur, special_flags=pygame.BLEND_RGBA_MULT)` teinte un sprite tout en conservant ses ombres/contours (contrairement à peindre un carré uni par-dessus) — toujours appelé sur une `.copy()` de l'image, sinon ça modifierait l'original de façon permanente pour tous les drones
- **Anti-superposition** : les drones partageant une même zone sont légèrement décalés (petite grille de décalages `(index % 3, index // 3)`), sinon ils se dessinent exactement au même endroit et se cachent mutuellement
- **Mise à l'échelle dynamique** : `SCALE`/`OFFSET` fixes fonctionnent pour les petites cartes, mais une carte aux coordonnées plus grandes (ex: x=21) sort du cadre visible avec des valeurs fixes — la solution est de calculer `SCALE`/`OFFSET` dynamiquement à partir du min/max réel des coordonnées de la carte chargée

### Pièges rencontrés et corrigés
- Une méthode `_draw_drones` mal ordonnée mélangeait mise à jour de position et dessin dans le même bloc — la mise à jour doit se faire une fois par tour (dans la logique de simulation), le dessin à chaque frame (60x/seconde), jamais les deux confondus dans la même boucle
- `clock.tick(0.8)` au lieu de `clock.tick(60)` rendait l'animation extrêmement saccadée (0.8 image par seconde)

## 15. Exploration de raylib/pyray (nouvelle bibliothèque 3D)

### Contexte
Après avoir terminé un visualiseur pygame fonctionnel, exploration d'une bibliothèque 3D (raylib, via son wrapper Python `pyray`) à but d'apprentissage personnel, en parallèle du projet Fly-in.

### Problème d'installation rencontré et sa cause exacte
`from pyray import *` puis `init_window(...)` levait `NameError: name 'init_window' is not defined`, malgré `pyray` visiblement installé.

**Cause racine** : il existe sur PyPI un package nommé `pyray` totalement indépendant du vrai projet raylib — un package vide/placeholder (version `0.1.0`, aucune fonction réelle). Un conflit de nom malheureux. Le vrai module `pyray` (les bindings Python de raylib) est censé être installé **automatiquement**, comme un second dossier, par `pip install raylib` — il ne faut **jamais** faire `pip install pyray` séparément (confirmé par la documentation officielle du projet `raylib-python-cffi`).

**Complication supplémentaire** : après avoir désinstallé le faux `pyray` (`pip uninstall pyray -y`), l'erreur persistait — le dossier `pyray/` existait toujours sur le disque, mais **sans fichier `__init__.py`** à l'intérieur (un résidu vide, laissé par l'installation précédente et non nettoyé par la désinstallation).

**Solution en cours** : supprimer manuellement ce dossier résiduel (`rm -rf .../site-packages/pyray`), puis réinstaller `raylib` en forçant (`pip install --force-reinstall --no-cache-dir raylib`) pour que le vrai module `pyray` (avec son `__init__.py` complet) soit recréé correctement à cette place.

### Comparaison Ursina vs raylib (pour référence future)
- **Ursina** : très haut niveau, installation simple, boucle de jeu automatique (`app.run()`), bon point d'entrée pour découvrir la 3D rapidement, mais moins transférable à d'autres technologies
- **raylib** : plus bas niveau (boucle `while` à gérer soi-même, comme pygame), installation plus capricieuse selon la plateforme/version Python, mais concepts (caméra, matrices, boucle de rendu) transférables à d'autres langages/moteurs, grosse communauté gamedev indé

## Pipeline complet obtenu à ce stade

```
fichier .txt
  → MapParser.parse()                (ParsedMap : Zone, Connection, nb_drones, start/end)
                                        avec validations d'erreurs à chaque étape
  → Graph                            (adjacence, zones bloquées exclues, zone_cost)
  → PathFinder.shortest_path()       (Dijkstra + reconstruction, un seul drone)
  → Simulator.run()                  (planifie chaque Drone, gère OccupationRegistry
                                        + LinkOccupationRegistry, zones restricted en transit)
  → Simulator._organiser_par_tour()  (regroupement par tour)
  → Simulator.display()              (texte au format attendu par le sujet)
  → FlyInVisualizer                  (pygame : zones, connexions, drones animés et
                                        teintés, fond animé, rejoue la simulation calculée)
```

## Ce qui reste à faire

- [ ] Résoudre définitivement l'installation raylib/pyray (dossier résiduel à nettoyer + réinstallation forcée), si la suite du projet visuel se fait sur raylib plutôt que pygame
- [ ] Écrire le `Makefile` (install/run/debug/clean/lint, Chapitre III.2)
- [ ] Écrire le `.gitignore` (Chapitre III.3)
- [ ] Vérifier le code avec `flake8` et `mypy --strict` (Chapitre III.1, V)
- [ ] Écrire le vrai `README.md` du projet, au format imposé par le sujet (Chapitre VIII : première ligne italique avec login 42, sections Description/Instructions/Resources obligatoires)
- [ ] Décider si la visualisation finale reste sur pygame (déjà fonctionnelle et complète) ou si l'exploration raylib est poussée jusqu'à remplacer pygame dans le rendu final

Installation pip install raylib puis python3 -m pip install raylib
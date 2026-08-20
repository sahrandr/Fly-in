# Fly-in

1-On commence par parser la map ave la commande ```tar -xzf maps.tar.gz``` pour extraire les maps.
Puis creer le fichier parser.py 

1. PARSER en premier   → lire le .txt et le transformer en objets Python
2. ALGORITHME ensuite  → calculer les déplacements des drones
3. SORTIE TEXTE         → afficher le résultat au format demandé
4. ÉCRAN VISUEL en dernier → pygame vient rejouer ce qui a déjà été calculé

## Le fichier parser.py:
- Lire le fichier ligne par ligne
- Ignorer lignes vides/commentaires
- Identifier le type de ligne (start_hub:, end_hub:, hub:, connection:)
- Extraire nom, x, y pour les zones
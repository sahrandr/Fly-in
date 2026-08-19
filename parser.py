# lire le fichier et ignore ce qui n'est pas utile
with open("maps/easy/02_simple_fork.txt", "r") as f:
    for ligne in f:
        ligne = ligne.strip()
        '''En Python, la méthode strip() supprime les espaces de début 
        et de fin ou les caractères spécifiés d'une chaîne, renvoyant 
        une nouvelle chaîne tout en laissant l'original inchangé.'''

        if ligne == "" or ligne == ligne.startswith("#"):
            continue

        print(ligne)
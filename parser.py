# lire le fichier et ignore ce qui n'est pas utile
with open("maps/easy/02_simple_fork.txt", "r") as f:
    for ligne in f:
        ligne = ligne.strip()
        '''En Python, la méthode strip() supprime les espaces de début 
        et de fin ou les caractères spécifiés d'une chaîne, renvoyant 
        une nouvelle chaîne tout en laissant l'original inchangé.'''

        if ligne == "" or ligne == ligne.startswith("#"):
            continue

        # if ligne == ligne.startswith("nb_drones:"):
        #     print("C'est le nombre de drones:", ligne)
        
        # elif ligne.startswith("start_hub:"):
        #     print("C'est la zone de départ:", ligne)
        
        # elif ligne.startswith("end_hub:"):
        #     print("C'est la zone d'arrivée:", ligne)
        
        # elif ligne.startswith("hub:"):
        #     print("C'est une zone normale:", ligne)
        
        # elif ligne.startswith("connection:"):
        #     print("C'est une connexion:", ligne)

        if ligne.startswith("hub:"):
            # ligne =  hub: junction 1 0 [color=yellow max_drones=2]

            #on enleve le :hub du debut
            reste = ligne.split(":", 1)[1]  # -> " junction 1 0 [color=yellow max_drones=2]"
            reste = reste.strip()  # -> " junction 1 0 [color=yellow max_drones=2]"

            #on separe la partie [metadata] du reste
            if "[" in reste:
                part_principal = reste.split("[")[0].strip() # junction 1 0
            else:
                part_principal = reste

            # on decoupe junction 1 0 par espace
            piece = part_principal.split()
            '''split = separator'''
            name = piece[0]
            x = int(piece[1])
            y = int(piece[2])

            print(f"Area find : name={name}, x={x}, y={y}")
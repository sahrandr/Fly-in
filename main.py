import pygame

# 1. Initialisation de Pygame
pygame.init()

# 2. Définition des dimensions (largeur, hauteur)
screen = pygame.display.set_mode((900, 650))

# 3. Création de la fenêtre
pygame.display.set_caption("Fly-in Simulation")

# 4. Boucle principale pour maintenir la fenêtre ouverte
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((255, 255, 255))  # fond blanc, sinon écran figé/noir

    # Rafraîchissement de l'affichage
    pygame.display.flip()  # affiche ce qu'on vient de dessiner

# 5. Fermeture propre
pygame.quit()
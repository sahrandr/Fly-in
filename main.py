# Importation de toutes les fonctions et constantes de la bibliothèque Raylib
from pyray import *

# Initialise la fenêtre graphique (Largeur: 900px, Hauteur: 700px, Titre)
init_window(900, 700, "Fly-in Simulation 3D")

# --- INITIALISATION DE LA CAMÉRA 3D ---
camera = Camera3D()
camera.position = Vector3(10.0, 8.0, 10.0)  # Emplacement 3D initial de la caméra (X, Y, Z)
camera.target = Vector3(0.0, 0.0, 0.0)     # Point 3D que la caméra regarde au départ
camera.up = Vector3(0.0, 1.0, 0.0)         # Axe vertical de référence (l'axe Y pointe vers le haut)
camera.fovy = 45.0                          # Field of View Y : Angle de vision vertical en degrés
camera.projection = CAMERA_PERSPECTIVE      # Rendu en perspective (les objets lointains apparaissent plus petits)

# Fixe la limite d'affichage à 60 images par seconde (FPS)
set_target_fps(60)

# --- FACTEURS DE SENSIBILITÉ ET VITESSE ---
SENSITIVITY = 0.05      # Vitesse de rotation avec la souris
MOVE_SPEED = 0.2        # Vitesse de déplacement au clavier
ZOOM_SENSITIVITY = 0.5  # Vitesse de zoom avec la molette

# Boucle principale du jeu : s'exécute tant que la fenêtre n'est pas fermée (Croix ou Échap)
while not window_should_close():
    
    # Récupère le déplacement de la souris depuis la dernière image (dX, dY)
    mouse_delta = get_mouse_delta()
    # Récupère le mouvement de la molette (valeur positive ou négative)
    wheel_move = get_mouse_wheel_move()

    # --- 1. CHANGEMENT D'ANGLE / ORIENTATION (SOURIS) ---
    rotation_yaw = 0.0    # Angle de rotation horizontale (Lacet / Gauche-Droite)
    rotation_pitch = 0.0  # Angle de rotation verticale (Tangage / Haut-Bas)

    # Si le bouton droit de la souris est maintenu enfoncé
    if is_mouse_button_down(MOUSE_BUTTON_RIGHT):
        rotation_yaw = -mouse_delta.x * SENSITIVITY    # Pivote latéralement selon l'axe X de la souris
        rotation_pitch = -mouse_delta.y * SENSITIVITY  # Modifie l'inclinaison verticale selon l'axe Y

    # --- 2. MODIFICATION DE L'ANGLE FOV (CHAMP DE VISION / ZOOM OPTIQUE) ---
    if is_key_down(KEY_PAGE_UP):
        camera.fovy -= 1.0  # Réduit l'angle = effet de zoom / téléobjectif
    if is_key_down(KEY_PAGE_DOWN):
        camera.fovy += 1.0  # Augmente l'angle = effet grand angle / dézoom

    # --- 3. DÉPLACEMENT SPATIAL (CLAVIER) ---
    move_forward = 0.0  # Déplacement avant/arrière
    move_strafe = 0.0   # Déplacement latéral (gauche/droite)
    move_up = 0.0       # Déplacement vertical (hauteur)

    # Contrôles pour avancer et reculer
    if is_key_down(KEY_UP):
        move_forward = MOVE_SPEED
    if is_key_down(KEY_DOWN):
        move_forward = -MOVE_SPEED

    # Contrôles pour les pas latéraux (strafe)
    if is_key_down(KEY_LEFT):
        move_strafe = -MOVE_SPEED
    if is_key_down(KEY_RIGHT):
        move_strafe = MOVE_SPEED

    # Contrôles d'altitude (Monter / Descendre)
    if is_key_down(KEY_SPACE):
        move_up = MOVE_SPEED
    if is_key_down(KEY_LEFT_SHIFT):
        move_up = -MOVE_SPEED

    # Met à jour la position et la direction de la caméra d'un seul coup
    # update_camera_pro(camera, mouvement_3D, rotation_3D, zoom_molette)
    update_camera_pro(
        camera,
        Vector3(move_strafe, move_forward, move_up),  # Vecteur de déplacement local
        Vector3(rotation_yaw, rotation_pitch, 0.0),   # Vecteur de rotations (Yaw, Pitch, Roll)
        -wheel_move * ZOOM_SENSITIVITY                # Inversion du signe de la molette pour zoomer
    )

    # --- 4. PHASE DE RENDU / DESSIN ---
    begin_drawing()                         # Démarre la frame de rendu
    clear_background(RAYWHITE)              # Efface le buffer vidéo en appliquant un fond blanc-gris

    # Active la matrice de projection 3D basée sur les paramètres de la caméra
    begin_mode_3d(camera)
    
    # Dessine une sphère : (Position(x,y,z), Rayon, Couleur)
    draw_sphere(Vector3(0, 0, 0), 1.0, GREEN)
    
    # Dessine un cube/pavé : (Position(x,y,z), LargeurX, HauteurY, ProfondeurZ, Couleur)
    draw_cube(Vector3(2, 0, 0), 4.0, 0.2, 0.2, GRAY)
    
    # Dessine un quadrillage au sol : (Nombre de lignes de chaque côté, Taille des carreaux)
    draw_grid(10, 1.0)
    
    end_mode_3d()                           # Quitte le mode 3D pour repasser en coordonnées 2D d'écran

    # --- 5. INTERFACE UTILISATEUR (2D OVERLAY) ---
    # draw_text(Texte, Position_X, Position_Y, Taille_police, Couleur)
    draw_text(f"Angle FOV actuel: {int(camera.fovy)} degres", 10, 10, 20, DARKGRAY)
    draw_text("PageUp/PageDown: Modifier l'angle FOV", 10, 35, 16, GRAY)
    draw_text("Espace/Shift: Monter/Descendre", 10, 55, 16, GRAY)

    end_drawing()                           # Affiche l'image calculée à l'écran (Double Buffering)

# Ferme le contexte graphique OpenGL et libère les ressources système
close_window()
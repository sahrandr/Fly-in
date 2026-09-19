from pyray import *

def dessiner_bouton(x, y, texte):
    bouton = Rectangle(x, y, 200, 50)
    souris = get_mouse_position()
    survole = check_collision_point_rec(souris, bouton)
    clique = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)

    if survole and clique:
        couleur = Color(90, 222, 204, 255)
    else:
        couleur = Color(40, 45, 55, 255)
    draw_rectangle_rec(bouton, couleur)
    largeur_text = measure_text(texte, 20)
    centre_bouton_x = bouton.x + bouton.width / 2
    centre_bouton_y = bouton.y + bouton.height / 2
    taille_police = 20
    x_texte = centre_bouton_x - largeur_text / 2
    y_texte = centre_bouton_y - (taille_police / 2)
    draw_text(texte, int(x_texte), int(y_texte), taille_police, RED)
    return survole and clique

def afficher_menu():
    il_faut_sortir = False
    bouton_choisi = None

    while not window_should_close():
        begin_drawing()
        clear_background(Color(15, 17, 22, 255))
        if dessiner_bouton(800, 425, "START"):
            il_faut_sortir = True
            bouton_choisi = "start"

        if dessiner_bouton(800, 491, "CONTINUE"):
            bouton_choisi = "continue"
            il_faut_sortir = True

        if dessiner_bouton(800, 557, "SETTINGS"):
            bouton_choisi = "settings"
            il_faut_sortir = True
        end_drawing()

        if il_faut_sortir:
            break
    return bouton_choisi
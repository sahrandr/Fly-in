import os
from pyray import *
from title_screen import (
    Button, with_alpha, draw_text_spaced, measure_spaced, glow_ring,
    C_BG, C_GRID, C_TEXT, C_MUTED, C_PATH, C_START, C_GOAL,
)


C_HARD = Color(225, 95, 95, 255)
C_CHALLENGER = Color(190, 130, 255, 255)

CATEGORY_ORDER = ["easy", "medium", "hard", "challenger"]
CATEGORY_COLOR = {
    "easy": C_START,
    "medium": C_GOAL,
    "hard": C_HARD,
    "challenger": C_CHALLENGER,
}


def scan_maps(maps_root="maps"):
    """
    Retourne {nom_categorie: [chemins_de_fichiers_tries]}, uniquement
    pour les sous-dossiers qui contiennent au moins un .txt.
    """
    categories = {}
    if not os.path.isdir(maps_root):
        return categories

    for entry in sorted(os.listdir(maps_root)):
        cat_path = os.path.join(maps_root, entry)
        if not os.path.isdir(cat_path):
            continue
        files = sorted(f for f in os.listdir(cat_path) if f.endswith(".txt"))
        if files:
            categories[entry] = [os.path.join(cat_path, f) for f in files]

    return categories


def format_map_name(filename):
    """'01_linear_path.txt' -> '01 · LINEAR PATH'"""
    name = filename[:-4] if filename.endswith(".txt") else filename
    parts = name.split("_", 1)
    if parts[0].isdigit() and len(parts) > 1:
        return f"{parts[0]} \u00b7 {parts[1].replace('_', ' ').upper()}"
    return name.replace("_", " ").upper()


def run_map_select(maps_root="maps"):
    """
    Boucle bloquante: affiche les cartes disponibles, groupées par
    catégorie. Retourne le CHEMIN du fichier .txt cliqué, ou None si
    la fenêtre est fermée pendant la sélection.
    """
    # 1. On récupère dynamiquement la VRAIE taille de l'écran 
    # au lieu de l'importer statiquement depuis title_screen.
    SCREEN_W = get_screen_width()
    SCREEN_H = get_screen_height()

    categories = scan_maps(maps_root)
    cat_names = [c for c in CATEGORY_ORDER if c in categories]
    cat_names += sorted(c for c in categories if c not in CATEGORY_ORDER)

    col_w = 250
    gap_x = 26
    total_w = len(cat_names) * col_w + max(0, len(cat_names) - 1) * gap_x
    
    # 2. Le centrage de l'interface utilisera maintenant le SCREEN_W réel
    start_x = max(60, (SCREEN_W - total_w) // 2)
    top_y = 190
    btn_h = 38
    btn_gap = 10

    headers = []          # (texte, x, y, couleur)
    entries = []          # (Button, chemin_fichier)

    for i, cat in enumerate(cat_names):
        cx = start_x + i * (col_w + gap_x)
        color = CATEGORY_COLOR.get(cat, C_PATH)
        headers.append((cat.upper(), cx, top_y, color))

        for j, path in enumerate(categories[cat]):
            label = format_map_name(os.path.basename(path))
            by = top_y + 38 + j * (btn_h + btn_gap)
            entries.append((Button(label, cx, by, col_w, btn_h, accent=color), path))

    while not window_should_close():
        dt = get_frame_time()
        mouse = get_mouse_position()
        pressed = is_mouse_button_pressed(MouseButton.MOUSE_BUTTON_LEFT)

        chosen = None
        for btn, path in entries:
            if btn.update(mouse, pressed, dt):
                chosen = path

        begin_drawing()
        clear_background(C_BG)

        for gx in range(0, SCREEN_W, 40):
            draw_line(gx, 0, gx, SCREEN_H, C_GRID)
        for gy in range(0, SCREEN_H, 40):
            draw_line(0, gy, SCREEN_W, gy, C_GRID)

        title = "CHOISIS UNE CARTE"
        draw_text_spaced(title, start_x, 70, 30, C_TEXT, 4)
        sub = "clique une carte pour lancer la simulation"
        draw_text_spaced(sub, start_x + 2, 108, 11, with_alpha(C_MUTED, 220), 3)

        for text, hx, hy, color in headers:
            draw_rectangle(int(hx), int(hy) - 2, 3, 16, color)
            draw_text_spaced(text, hx + 10, hy - 2, 13, color, 2)

        for btn, _path in entries:
            btn.draw()

        if not entries:
            msg = f"aucune carte trouvée dans '{maps_root}/'"
            draw_text(msg, start_x, top_y + 20, 14, with_alpha(C_MUTED, 220))

        end_drawing()

        if chosen:
            return chosen

    return None


if __name__ == "__main__":
    # 3. Initialisation borderless sans bordures comme sur le main.py
    set_config_flags(ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE)
    init_window(0, 0, "Fly-in")
    set_target_fps(60)
    
    choix = run_map_select()
    print(f"Carte choisie: {choix}")
    close_window()
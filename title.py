import math
import random
from pyray import *

# ============================================================
# 1. PARAMÈTRES GLOBAUX ET FENÊTRE
# ============================================================
SCREEN_W, SCREEN_H = 1200, 800

# ============================================================
# 2. PALETTE DE COULEURS (Thème sombre & néon)
# ============================================================
C_BG = Color(8, 10, 15, 255)         # Le fond bleu très sombre
C_GRID = Color(255, 255, 255, 6)     # La grille de fond (presque invisible, alpha à 6)

# Couleurs des éléments d'interface et du graphe
C_STRUCT = Color(64, 74, 92, 255)    # Gris bleuté pour les éléments inactifs
C_PATH = Color(90, 222, 204, 255)    # Le cyan vif (boutons, lignes actives)
C_START = Color(96, 230, 130, 255)   # Vert (point de départ)
C_GOAL = Color(255, 198, 70, 255)    # Orange/Jaune (point d'arrivée)
C_TEXT = Color(226, 236, 242, 255)   # Blanc cassé pour le texte lisible
C_MUTED = Color(120, 132, 148, 255)  # Gris pour les sous-titres
C_DISABLED = Color(70, 76, 86, 255)  # Gris foncé pour les boutons désactivés

# Couleurs des drones/billes lumineuses
ORB_COLORS = [
    Color(255, 150, 120, 255), Color(140, 235, 205, 255),
    Color(155, 190, 255, 255), Color(255, 214, 130, 255),
    Color(232, 152, 238, 255), Color(150, 238, 238, 255),
]

# ============================================================
# 3. FONCTION UTILITAIRE (Cruciale pour les effets visuels)
# ============================================================
def with_alpha(c, a):
    """
    Prend une couleur Pyray existante et renvoie une copie avec 
    une nouvelle valeur d'opacité (alpha).
    Le 'max(0, min(255, int(a)))' empêche le programme de planter 
    si on donne une valeur en dehors de 0-255 lors des calculs.
    """
    return Color(c.r, c.g, c.b, max(0, min(255, int(a))))

def glow_dot(x, y, radius, color, layers=4, power=52):
    """Crée une bille lumineuse (utilisée pour les drones qui se déplacent)."""
    # Active l'addition des couleurs pour l'effet de lumière
    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
    
    # Dessine plusieurs cercles concentriques de plus en plus petits
    for i in range(layers, 0, -1):
        k = i / layers
        # Plus le cercle est grand (k élevé), plus il est transparent
        draw_circle_v(Vector2(x, y), radius * (1 + k * 3.4),
                    with_alpha(color, power * (1 - k) ** 1.6))
                    
    end_blend_mode() # On désactive le mode additif pour le centre
    
    # Le cœur de la bille (solide) et un micro-reflet blanc
    draw_circle_v(Vector2(x, y), radius, color)
    draw_circle_v(Vector2(x - radius * 0.22, y - radius * 0.22),
                radius * 0.42, Color(255, 255, 255, 210))

def glow_ring(x, y, radius, thick, color, alpha):
    """Crée un anneau lumineux (utilisé pour le départ et l'arrivée)."""
    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
    for i in range(3):
        # On dessine 3 anneaux diffus
        draw_ring(Vector2(x, y), radius - thick / 2 - i * 2,
                radius + thick / 2 + i * 2, 0, 360, 48,
                with_alpha(color, alpha / (2 + i * 2)))
    end_blend_mode()
    # L'anneau central net
    draw_ring(Vector2(x, y), radius - thick / 2, radius + thick / 2,
            0, 360, 48, with_alpha(color, alpha))

def glow_line(a, b, thick, color, alpha):
    """Crée un segment de chemin lumineux."""
    begin_blend_mode(BlendMode.BLEND_ADDITIVE)
    # Deux lignes épaisses et très transparentes pour le halo
    draw_line_ex(a, b, thick * 4.0, with_alpha(color, alpha * 0.18))
    draw_line_ex(a, b, thick * 2.0, with_alpha(color, alpha * 0.35))
    end_blend_mode()
    # La ligne centrale nette
    draw_line_ex(a, b, thick, with_alpha(color, alpha))

def draw_text_spaced(text, x, y, size, color, spacing=2):
    """Dessine du texte en ajoutant un espacement personnalisé entre les lettres."""
    cx = x
    for ch in text:
        draw_text(ch, int(cx), int(y), size, color)
        # On décale la position X pour la prochaine lettre
        cx += measure_text(ch, size) + spacing
    return cx - x # Retourne la largeur totale utilisée

def measure_spaced(text, size, spacing=2):
    """Calcule la largeur totale d'un texte espacé (utile pour le centrer)."""
    return sum(measure_text(c, size) + spacing for c in text) - spacing

if __name__ == "__main__":
    init_window(SCREEN_W, SCREEN_H, "Fly-in - Etape 2")
    set_target_fps(60)

    while not window_should_close():
        begin_drawing()
        clear_background(C_BG)

        for gx in range(0, SCREEN_W, 40):
            draw_line(gx, 0, gx, SCREEN_H, C_GRID)
        for gy in range(0, SCREEN_H, 40):
            draw_line(0, gy, SCREEN_W, gy, C_GRID)
            
        # --- TEST DES EFFETS NÉON ---
        # 1. Un segment lumineux
        glow_line(Vector2(300, 300), Vector2(600, 400), 2.0, C_PATH, 255)
        
        # 2. Un anneau de départ (vert)
        glow_ring(300, 300, 15, 3.0, C_START, 255)
        
        # 3. Un drone (orange/saumon)
        glow_dot(450, 350, 5, ORB_COLORS[0])
        
        # 4. Le texte stylisé
        draw_text_spaced("TEST DU MOTEUR VISUEL", 300, 200, 20, C_TEXT, 6)
        # -----------------------------

        end_drawing()

    close_window()
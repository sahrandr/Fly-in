import pygame
from PIL import Image

from algo import Simulator
from parser import MapParser


class FlyInVisualizer:
    """Gère toute la partie graphique (Pygame) de la simulation Fly-in.

    Une instance de cette classe s'occupe de :
    - charger la carte et calculer le planning des drones (via Simulator)
    - convertir les coordonnées logiques de la carte en pixels à l'écran
    - charger et découper le spritesheet d'animation des drones
    - teinter le sprite d'une couleur différente pour chaque drone
    - charger et animer un fond de type GIF (caverne de lave)
    - faire tourner la boucle de jeu (événements, dessin, avancement des tours)
    """

    # --- Constantes de rendu ---
    SCALE = 100
    OFFSET_X, OFFSET_Y = 100, 350
    WINDOW_SIZE = (900, 700)
    TAILLE_DRONE = 80
    NB_FRAMES = 4
    FPS = 60
    TOURS_PAR_SECONDE = 60
    FRAMES_PAR_ANIMATION = 6
    DELAI_BG_MS = 100  # vitesse d'animation du fond (même rythme que le gif d'origine)
    VOILE_ALPHA = 140  # opacite du voile sombre pose sur le fond (0=invisible, 255=opaque)

    COLOR_MAP = {
        "green": (0, 180, 0),
        "blue": (0, 100, 220),
        "red": (200, 0, 0),
        "orange": (230, 140, 0),
        "yellow": (230, 200, 0),
        "gray": (150, 150, 150),
        "none": (100, 100, 100),
        "rainbow": (255, 0, 255),
    }

    COULEURS_DRONES = [
        (255, 0, 0),      # D1 - rouge
        (0, 255, 0),      # D2 - vert
        (0, 100, 255),    # D3 - bleu
        (255, 165, 0),    # D4 - orange
        (255, 0, 255),    # D5 - magenta
        (0, 255, 255),    # D6 - cyan
    ]

    def __init__(self, map_path: str, sprite_path: str, background_path: str) -> None:
        """Initialise Pygame, charge la carte, calcule le planning, prépare les sprites et le fond."""
        pygame.init()

        # 1. CHARGEMENT DE LA CARTE ET CALCUL DES CHEMINS
        self.parsed = MapParser(map_path).parse()
        assert self.parsed.start_zone is not None

        self.simulator = Simulator(self.parsed)
        self.par_tour: dict[int, list[tuple[str, str]]] = self.simulator.run()
        self.nombre_max_tours = max(self.par_tour.keys()) if self.par_tour else 0

        # 2. PRÉ-CALCUL : position en pixels de chaque zone
        self.zone_pixels: dict[str, tuple[int, int]] = {
            name: self._map_to_pixel(zone.x, zone.y)
            for name, zone in self.parsed.zones.items()
        }

        # 3. CRÉATION DE LA FENÊTRE PYGAME
        self.screen = pygame.display.set_mode(self.WINDOW_SIZE)
        pygame.display.set_caption("Fly-in Simulation")
        self.clock = pygame.time.Clock()

        # 4. POSITION INITIALE DE CHAQUE DRONE (tous à la zone de départ)
        self.drone_positions: dict[str, str] = {
            f"D{i}": self.parsed.start_zone
            for i in range(1, self.parsed.nb_drones + 1)
        }

        # 5. CHARGEMENT DU SPRITE SHEET DU DRONE (sprite "neutre", non teinté)
        self.frames = self._load_sprite_frames(sprite_path)

        # 5bis. PRÉ-CALCUL des versions TEINTÉES du sprite, une par drone.
        # Fait une seule fois ici, au lancement, car teinter une image a un
        # cout de calcul non negligeable a repeter 60 fois par seconde.
        self.frames_par_drone: dict[str, list[pygame.Surface]] = {}
        for i in range(1, self.parsed.nb_drones + 1):
            drone_id = f"D{i}"
            couleur = self._couleur_pour_drone(drone_id)
            self.frames_par_drone[drone_id] = [
                self._teinter_sprite(frame, couleur) for frame in self.frames
            ]

        # 6. CHARGEMENT DU FOND ANIME (gif de caverne de lave), avec un voile
        # sombre applique une seule fois sur chaque frame pour garder les
        # zones/connexions bien lisibles par-dessus ce fond tres detaille.
        self.background_frames = self._load_gif_frames(background_path)
        self._appliquer_voile(self.background_frames, self.VOILE_ALPHA)
        self.background_frame_actuelle = 0
        self.dernier_changement_bg = pygame.time.get_ticks()

        # 7. VARIABLES D'ÉTAT DE LA BOUCLE DE JEU
        self.tour_simulation = 0
        self.frame_actuelle = 0
        self.compteur = 0
        self.dernier_changement = pygame.time.get_ticks()
        self.running = True

    # Chargement / préparation des ressources (appelé une seule fois)
    def _map_to_pixel(self, x: int, y: int) -> tuple[int, int]:
        """Convertit une coordonnée logique de la carte (x, y) en position pixel à l'écran."""
        return self.OFFSET_X + x * self.SCALE, self.OFFSET_Y + y * self.SCALE

    def _load_sprite_frames(self, sprite_path: str) -> list[pygame.Surface]:
        """Découpe le spritesheet en NB_FRAMES images individuelles, redimensionnées."""
        sprite_sheet = pygame.image.load(sprite_path).convert_alpha()

        largeur_totale = sprite_sheet.get_width()
        hauteur_totale = sprite_sheet.get_height()
        largeur_frame = largeur_totale // self.NB_FRAMES

        frames = []
        for i in range(self.NB_FRAMES):
            rect = pygame.Rect(i * largeur_frame, 0, largeur_frame, hauteur_totale)
            frame = sprite_sheet.subsurface(rect).copy()
            frame = pygame.transform.scale(frame, (self.TAILLE_DRONE, self.TAILLE_DRONE))
            frames.append(frame)

        return frames

    def _load_gif_frames(self, gif_path: str) -> list[pygame.Surface]:
        """Extrait toutes les frames d'un GIF animé et les convertit en Surfaces pygame,
        redimensionnées à la taille de la fenêtre."""
        gif = Image.open(gif_path)
        frames = []

        for i in range(gif.n_frames):
            gif.seek(i)
            frame_rgba = gif.convert("RGBA")
            data = frame_rgba.tobytes()
            surface = pygame.image.fromstring(data, frame_rgba.size, "RGBA")
            surface = pygame.transform.scale(surface, self.WINDOW_SIZE)
            frames.append(surface)

        return frames

    def _appliquer_voile(self, frames: list[pygame.Surface], alpha: int) -> None:
        """Assombrit une liste de frames avec un voile semi-transparent, pour que
        les zones/connexions restent bien visibles par-dessus un fond chargé."""
        voile = pygame.Surface(self.WINDOW_SIZE)
        voile.set_alpha(alpha)
        voile.fill((0, 0, 0))
        for frame in frames:
            frame.blit(voile, (0, 0))

    def _couleur_pour_drone(self, drone_id: str) -> tuple[int, int, int]:
        """Retourne une couleur distincte pour un drone donné, selon son numéro."""
        numero = int(drone_id[1:])
        index = (numero - 1) % len(self.COULEURS_DRONES)
        return self.COULEURS_DRONES[index]

    def _teinter_sprite(self, sprite: pygame.Surface, couleur: tuple[int, int, int]) -> pygame.Surface:
        """Applique une teinte de couleur sur un sprite, en conservant sa forme/ombres."""
        sprite_teinte = sprite.copy()
        sprite_teinte.fill(couleur, special_flags=pygame.BLEND_RGBA_MULT)
        return sprite_teinte

    # Boucle principale
    def run(self) -> None:
        """Boucle principale du jeu : événements, dessin, animation, avancement des tours."""
        while self.running:
            self._handle_events()
            self._draw_frame()

            self.compteur += 1
            self._advance_animation()
            self._advance_simulation()
            self._advance_background()

            pygame.display.flip()
            self.clock.tick(self.FPS)

        pygame.quit()

    def _handle_events(self) -> None:
        """Gère les événements Pygame (fermeture de la fenêtre, etc.)."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    # Dessin
    def _draw_frame(self) -> None:
        """Dessine une image complète : fond animé, connexions, zones, puis drones."""
        self.screen.blit(self.background_frames[self.background_frame_actuelle], (0, 0))
        self._draw_connections()
        self._draw_zones()
        self._draw_drones()

    def _draw_connections(self) -> None:
        """Dessine les lignes représentant les connexions entre zones."""
        for conn in self.parsed.connections:
            pygame.draw.line(
                self.screen,
                (150, 150, 150),
                self.zone_pixels[conn.zone_a],
                self.zone_pixels[conn.zone_b],
                3,
            )

    def _draw_zones(self) -> None:
        """Dessine les zones sous forme de cercles colorés."""
        for name, zone in self.parsed.zones.items():
            px, py = self.zone_pixels[name]
            couleur = self.COLOR_MAP.get(zone.color, self.COLOR_MAP["none"])
            pygame.draw.circle(self.screen, couleur, (px, py), 25)

    def _draw_drones(self) -> None:
        """
        Dessine chaque drone à sa position actuelle, avec son propre sprite
        teinté, et un léger décalage si plusieurs drones partagent la même zone.
        """
        drones_par_zone: dict[str, list[str]] = {}
        for drone_id, zone_name in self.drone_positions.items():
            drones_par_zone.setdefault(zone_name, []).append(drone_id)

        for zone_name, liste_drones in drones_par_zone.items():
            px, py = self.zone_pixels[zone_name]

            for index, drone_id in enumerate(liste_drones):
                decalage_x = (index % 3) * 20 - 20
                decalage_y = (index // 3) * 20 - 20
                centre = (px + decalage_x, py + decalage_y)

                sprite_du_drone = self.frames_par_drone[drone_id][self.frame_actuelle]
                self.screen.blit(
                    sprite_du_drone,
                    (centre[0] - self.TAILLE_DRONE // 2, centre[1] - self.TAILLE_DRONE // 2),
                )

    # Avancement des animations / de la simulation
    def _advance_animation(self) -> None:
        """Fait avancer les frames de vol des drones (ailes qui battent), en continu."""
        if self.compteur % self.FRAMES_PAR_ANIMATION == 0:
            self.frame_actuelle = (self.frame_actuelle + 1) % len(self.frames)

    def _advance_background(self) -> None:
        """Fait avancer l'animation du fond (feu qui vacille), en continu."""
        maintenant = pygame.time.get_ticks()
        if maintenant - self.dernier_changement_bg >= self.DELAI_BG_MS:
            self.background_frame_actuelle = (self.background_frame_actuelle + 1) % len(self.background_frames)
            self.dernier_changement_bg = maintenant

    def _advance_simulation(self) -> None:
        """Avance le tour de simulation une fois par seconde environ, et met à
        jour la position logique de chaque drone concerné par ce tour."""
        tour_pas_encore_termine = self.tour_simulation < self.nombre_max_tours
        if self.compteur % self.TOURS_PAR_SECONDE == 0 and tour_pas_encore_termine:
            self.tour_simulation += 1

            if self.tour_simulation in self.par_tour:
                for drone_id, zone_name in self.par_tour[self.tour_simulation]:
                    self.drone_positions[drone_id] = zone_name


if __name__ == "__main__":
    visualizer = FlyInVisualizer(
        "maps/easy/03_basic_capacity.txt",
        "FLYING.png",
        "assets/h1ll.gif",
    )
    visualizer.run()
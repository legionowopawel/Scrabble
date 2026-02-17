import pygame
import sys
import random

# --- KONFIGURACJA I KOLORY ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 900
BOARD_SIZE = 15
CELL_SIZE = 50
BOARD_OFFSET_X = (SCREEN_WIDTH - (BOARD_SIZE * CELL_SIZE)) // 2
BOARD_OFFSET_Y = 50

# Kolory (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BG_COLOR = (230, 230, 230)     # Szare tło
BOARD_COLOR = (245, 245, 220)  # Beżowa plansza
TILE_COLOR = (250, 235, 215)   # "Drewniany" kolor kafelka
TILE_BORDER = (139, 69, 19)    # Brązowa ramka kafelka

# Kolory pól premiowych (zbliżone do oryginału)
TW_COLOR = (255, 51, 51)   # Czerwony (Potrójne słowo)
DW_COLOR = (255, 153, 153) # Różowy (Podwójne słowo)
TL_COLOR = (51, 51, 255)   # Ciemnoniebieski (Potrójna litera)
DL_COLOR = (153, 204, 255) # Jasnoniebieski (Podwójna litera)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Python Scrabble GUI")
font_big = pygame.font.SysFont('Arial', 36, bold=True)
font_small = pygame.font.SysFont('Arial', 14)
clock = pygame.time.Clock()

# --- DANE SCRABBLE ---
LETTER_POINTS = {
    'A': 1, 'Ą': 5, 'B': 3, 'C': 2, 'Ć': 6, 'D': 2, 'E': 1, 'Ę': 5,
    'F': 5, 'G': 2, 'H': 3, 'I': 1, 'J': 3, 'K': 2, 'L': 2, 'Ł': 3,
    'M': 2, 'N': 1, 'Ń': 7, 'O': 1, 'Ó': 5, 'P': 2, 'R': 1, 'S': 1,
    'Ś': 5, 'T': 2, 'U': 3, 'W': 1, 'Y': 2, 'Z': 1, 'Ź': 9, 'Ż': 5
}
# Uproszczony worek do testów (można zastąpić pełnym z poprzednich wersji)
INITIAL_BAG = ['A']*9 + ['E']*7 + ['I']*8 + ['K']*3 + ['O']*6 + ['Z']*5 + ['W']*4 + ['S']*4 + ['C']*3 + ['Ó']*2

# --- KLASA KAFELKA (TILE) ---
class Tile:
    def __init__(self, letter, x, y):
        self.letter = letter
        self.points = LETTER_POINTS.get(letter, 0)
        self.rect = pygame.Rect(x, y, CELL_SIZE - 2, CELL_SIZE - 2)
        self.is_dragging = False
        self.rack_pos = (x, y) # Zapamiętuje pozycję na stojaku, by tam wrócić

    def draw(self, surface):
        # Rysowanie kafelka (tło i ramka)
        pygame.draw.rect(surface, TILE_COLOR, self.rect, border_radius=5)
        pygame.draw.rect(surface, TILE_BORDER, self.rect, 2, border_radius=5)
        
        # Rysowanie dużej litery na środku
        text_surf = font_big.render(self.letter, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
        # Rysowanie małych punktów w rogu
        points_surf = font_small.render(str(self.points), True, BLACK)
        surface.blit(points_surf, (self.rect.right - 15, self.rect.bottom - 15))

# --- GŁÓWNA KLASA GRY ---
class ScrabbleGUI:
    def __init__(self):
        self.grid_multipliers = self._init_multipliers()
        self.placed_tiles = {} # Słownik: (row, col) -> Tile object
        self.bag = INITIAL_BAG.copy()
        random.shuffle(self.bag)
        self.rack = []
        self.fill_rack()
        self.dragging_tile = None
        self.drag_offset = (0, 0)

    def _init_multipliers(self):
        grid = [["" for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        tw = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        dw = [(1,1), (2,2), (3,3), (4,4), (1,13), (2,12), (3,11), (4,10), (13,1), (12,2), (11,3), (10,4), (13,13), (12,12), (11,11), (10,10), (7,7)]
        tl = [(1,5), (1,9), (5,1), (5,5), (5,9), (5,13), (9,1), (9,5), (9,9), (9,13), (13,5), (13,9)]
        dl = [(0,3), (0,11), (2,6), (2,8), (3,0), (3,7), (3,14), (6,2), (6,6), (6,8), (6,12), (7,3), (7,11), (8,2), (8,6), (8,8), (8,12), (11,0), (11,7), (11,14), (12,6), (12,8), (14,3), (14,11)]
        for r, c in tw: grid[r][c] = "TW"
        for r, c in dw: grid[r][c] = "DW"
        for r, c in tl: grid[r][c] = "TL"
        for r, c in dl: grid[r][c] = "DL"
        return grid

    def fill_rack(self):
        start_x = BOARD_OFFSET_X + (CELL_SIZE * 4)
        start_y = SCREEN_HEIGHT - 80
        
        current_rack_slots = len(self.rack)
        needed = 7 - current_rack_slots
        
        for i in range(needed):
            if self.bag:
                letter = self.bag.pop()
                # Obliczamy pozycję dla nowego kafelka na stojaku
                slot_x = start_x + (current_rack_slots + i) * (CELL_SIZE + 5)
                self.rack.append(Tile(letter, slot_x, start_y))

    def draw_board(self):
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x = BOARD_OFFSET_X + c * CELL_SIZE
                y = BOARD_OFFSET_Y + r * CELL_SIZE
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                
                # Wybór koloru pola na podstawie mnożnika
                mult = self.grid_multipliers[r][c]
                color = BOARD_COLOR
                if mult == "TW": color = TW_COLOR
                elif mult == "DW": color = DW_COLOR
                elif mult == "TL": color = TL_COLOR
                elif mult == "DL": color = DL_COLOR
                
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, WHITE, rect, 1) # Biała siatka

                # Rysowanie tekstu premii (jeśli pole puste)
                if mult and (r,c) not in self.placed_tiles:
                    text = font_small.render(mult, True, BLACK)
                    screen.blit(text, text.get_rect(center=rect.center))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # --- KLIKNIĘCIE MYSZKĄ (Początek przeciągania) ---
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Lewy przycisk
                    mouse_pos = event.pos
                    # Sprawdzamy, czy kliknięto kafelek na stojaku
                    for tile in self.rack:
                        if tile.rect.collidepoint(mouse_pos):
                            self.dragging_tile = tile
                            self.dragging_tile.is_dragging = True
                            # Obliczamy offset, żeby kafelek nie "skakał" pod kursorem
                            self.drag_offset = (tile.rect.x - mouse_pos[0], tile.rect.y - mouse_pos[1])
                            break

            # --- PUSZCZENIE MYSZKI (Koniec przeciągania) ---
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.dragging_tile:
                    # Obliczamy środek upuszczonego kafelka
                    drop_x, drop_y = self.dragging_tile.rect.center
                    
                    # Sprawdzamy, na którym polu planszy wylądował
                    col = (drop_x - BOARD_OFFSET_X) // CELL_SIZE
                    row = (drop_y - BOARD_OFFSET_Y) // CELL_SIZE
                    
                    valid_drop = False
                    # Czy upuszczono w granicach planszy?
                    if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
                        # Czy pole jest puste?
                        if (row, col) not in self.placed_tiles:
                            # "Przyklejamy" kafelek do siatki
                            snap_x = BOARD_OFFSET_X + col * CELL_SIZE + 1
                            snap_y = BOARD_OFFSET_Y + row * CELL_SIZE + 1
                            self.dragging_tile.rect.topleft = (snap_x, snap_y)
                            
                            # Przenosimy kafelek ze stojaka na planszę
                            self.placed_tiles[(row, col)] = self.dragging_tile
                            self.rack.remove(self.dragging_tile)
                            valid_drop = True

                    # Jeśli upuszczenie było nieprawidłowe, kafelek wraca na stojak
                    if not valid_drop:
                        self.dragging_tile.rect.topleft = self.dragging_tile.rack_pos

                    self.dragging_tile.is_dragging = False
                    self.dragging_tile = None

            # --- RUCH MYSZKĄ (Aktualizacja pozycji przeciąganego kafelka) ---
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_tile:
                    mouse_x, mouse_y = event.pos
                    self.dragging_tile.rect.x = mouse_x + self.drag_offset[0]
                    self.dragging_tile.rect.y = mouse_y + self.drag_offset[1]

    def run(self):
        while True:
            self.handle_events()
            
            # Rysowanie wszystkiego
            screen.fill(BG_COLOR)
            self.draw_board()
            
            # Rysowanie tła stojaka
            pygame.draw.rect(screen, (100, 100, 100), (0, SCREEN_HEIGHT-100, SCREEN_WIDTH, 100))

            # Rysowanie kafelków leżących na planszy
            for pos, tile in self.placed_tiles.items():
                tile.draw(screen)

            # Rysowanie kafelków na stojaku (w odwrotnej kolejności, żeby przeciągany był na wierzchu)
            for tile in self.rack[::-1]:
                tile.draw(screen)
                
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    game = ScrabbleGUI()
    game.run()
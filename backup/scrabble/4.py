import pygame
import sys
import random
import time

# --- KONFIGURACJA I KOLORY ---
# Zwiększamy szerokość, by pomieścić panel boczny
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
BOARD_SIZE = 15
# Obliczamy rozmiar pola zależnie od wysokości ekranu, zostawiając margines
CELL_SIZE = (SCREEN_HEIGHT - 40) // BOARD_SIZE 
BOARD_START_X = 20
BOARD_START_Y = 20

# Paleta kolorów z gry Scrabmania
BG_GREEN_DARK = (0, 100, 0)       # Ciemne tło za planszą
BG_GREEN_LIGHT = (0, 180, 0)      # Jaśniejsze tło panelu bocznego
BOARD_GREEN = (50, 205, 50)       # Kolor zwykłego pola na planszy
BOARD_GRID_LINE = (0, 80, 0)      # Kolor linii siatki
BONUS_TEXT_COLOR = (144, 238, 144) # Jasnozielony tekst premii

TILE_COLOR = (238, 221, 130)      # Żółtawy/beżowy kolor klocka
TILE_BORDER = (184, 134, 11)      # Ciemniejsza ramka klocka
TEXT_BLACK = (0, 0, 0)
TEXT_WHITE = (255, 255, 255)
BUTTON_PURPLE = (148, 0, 211)     # Kolor przycisku OK

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Scrabmania Remake Python")
clock = pygame.time.Clock()

# Próba załadowania pogrubionej czcionki systemowej Arial
try:
    font_tile_big = pygame.font.SysFont('arialbd', int(CELL_SIZE * 0.6))
    font_tile_small = pygame.font.SysFont('arialbd', int(CELL_SIZE * 0.25))
    font_bonus = pygame.font.SysFont('arialbd', int(CELL_SIZE * 0.22))
    font_ui_big = pygame.font.SysFont('arialbd', 36)
    font_ui_small = pygame.font.SysFont('arialbd', 24)
except:
    # Fallback do domyślnej, jeśli Arial nie jest dostępny
    font_tile_big = pygame.font.Font(None, int(CELL_SIZE * 0.7))
    font_tile_small = pygame.font.Font(None, int(CELL_SIZE * 0.3))
    font_bonus = pygame.font.Font(None, int(CELL_SIZE * 0.25))
    font_ui_big = pygame.font.Font(None, 40)
    font_ui_small = pygame.font.Font(None, 28)

# --- DANE SCRABBLE (Polskie) ---
LETTER_POINTS = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 
    'D': (2, 3), 'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 
    'H': (3, 2), 'I': (1, 8), 'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 
    'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5), 'Ń': (7, 1), 'O': (1, 6), 
    'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4), 'Ś': (5, 1), 
    'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5), 
    'Ź': (9, 1), 'Ż': (5, 1), ' ': (0, 2) # Blank
}

# --- KLASA KAFELKA ---
class Tile:
    def __init__(self, letter, points, x, y, is_on_board=False):
        self.letter = letter
        self.points = points
        # Margines 2px dla ładniejszego wyglądu
        self.rect = pygame.Rect(x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4)
        self.is_dragging = False
        self.rack_pos = (x + 2, y + 2)
        self.is_on_board = is_on_board

    def draw(self, surface):
        # Cień klocka
        shadow_rect = self.rect.copy()
        shadow_rect.move_ip(2, 2)
        pygame.draw.rect(surface, (100, 100, 0), shadow_rect, border_radius=4)
        
        # Główny klocek
        pygame.draw.rect(surface, TILE_COLOR, self.rect, border_radius=4)
        pygame.draw.rect(surface, TILE_BORDER, self.rect, 2, border_radius=4)
        
        # Litera
        text_surf = font_tile_big.render(self.letter, True, TEXT_BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        # Lekka korekta pozycji dla liter z ogonkami
        text_rect.centery -= 3 
        surface.blit(text_surf, text_rect)
        
        # Punkty (jeśli większe od 0)
        if self.points > 0:
            points_surf = font_tile_small.render(str(self.points), True, TEXT_BLACK)
            surface.blit(points_surf, (self.rect.right - 14, self.rect.bottom - 14))

# --- GŁÓWNA KLASA GRY ---
class ScrabmaniaGame:
    def __init__(self):
        self.bonus_map = self._init_bonuses()
        self.placed_tiles = {} # Słownik: (row, col) -> Tile object
        
        # Inicjalizacja worka
        self.bag = []
        for letter, (pts, count) in LETTER_POINTS.items():
            for _ in range(count):
                self.bag.append((letter, pts))
        random.shuffle(self.bag)

        # Gracze
        self.player_rack = []
        self.player_score = 0
        self.ai_rack = []
        self.ai_score = 0
        
        self.fill_rack(self.player_rack)
        self.fill_rack(self.ai_rack)

        # Stan gry
        self.turn = "PLAYER" # lub "AI"
        self.dragging_tile = None
        self.drag_offset = (0, 0)
        
        # UI Elements
        self.ok_button_rect = pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - 100, 80, 80)
        self.ai_thinking_start = 0

    def _init_bonuses(self):
        # Mapa bonusów wzorowana na zdjęciu (przybliżona)
        bonuses = {}
        # 5 WYRAZ (Rogi)
        for r, c in [(0,0), (0,14), (14,0), (14,14)]: bonuses[(r,c)] = "5 WYRAZ"
        # 4 WYRAZ
        for r, c in [(1,1), (1,13), (13,1), (13,13)]: bonuses[(r,c)] = "4 WYRAZ"
        # 3 WYRAZ
        for r, c in [(2,2), (2,12), (12,2), (12,12)]: bonuses[(r,c)] = "3 WYRAZ"
        # 2 WYRAZ (Środek i przekątne)
        for r, c in [(7,7), (3,3), (3,11), (11,3), (11,11)]: bonuses[(r,c)] = "2 WYRAZ"
        
        # Premie literowe (rozmieszczone gęsto jak na zdjęciu)
        # 5 LITERA
        for r, c in [(0,6), (0,8), (6,0), (8,0), (14,6), (14,8), (6,14), (8,14)]: bonuses[(r,c)] = "5 LITERA"
        # 4 LITERA (obok rogów)
        for r, c in [(0,1), (0,13), (1,0), (13,0), (14,1), (14,13), (1,14), (13,14)]: bonuses[(r,c)] = "4 LITERA"
        # 3 LITERA
        for r, c in [(4,6), (4,8), (6,4), (8,4), (10,6), (10,8), (6,10), (8,10), (2,6), (2,8), (6,2), (8,2), (12,6), (12,8), (6,12), (8,12) ]: bonuses[(r,c)] = "3 LITERA"
        # 2 LITERA (reszta charakterystycznych)
        for r, c in [(1,5), (1,9), (5,1), (5,5), (5,9), (5,13), (9,1), (9,5), (9,9), (9,13), (13,5), (13,9), (0,3), (0,11), (3,0), (11,0), (14,3), (14,11), (3,14), (11,14), (7,2), (7,12), (2,7), (12,7)]: bonuses[(r,c)] = "2 LITERA"

        return bonuses

    def fill_rack(self, rack_list):
        while len(rack_list) < 7 and self.bag:
            letter, pts = self.bag.pop()
            # Pozycja tymczasowa, zostanie zaktualizowana przy rysowaniu UI
            rack_list.append(Tile(letter, pts, 0, 0))

    def ai_turn_logic(self):
        # --- Prosta symulacja tury AI ---
        current_time = pygame.time.get_ticks()
        
        # Jeśli AI dopiero zaczyna myśleć
        if self.ai_thinking_start == 0:
            self.ai_thinking_start = current_time
            print("AI myśli...")
            
        # Czekaj 2 sekundy (symulacja myślenia)
        if current_time - self.ai_thinking_start > 2000:
            print("AI kończy turę (PASS/WYMIANA).")
            # Tutaj w przyszłości byłaby logika szukania słów.
            # Na razie AI wymienia litery jeśli może, lub pasuje.
            if len(self.bag) >= 7:
                old_rack = self.ai_rack.copy()
                self.ai_rack.clear()
                self.fill_rack(self.ai_rack)
                for tile in old_rack:
                    self.bag.append((tile.letter, tile.points))
                random.shuffle(self.bag)
            
            self.turn = "PLAYER"
            self.ai_thinking_start = 0

    def draw_board(self):
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x = BOARD_START_X + c * CELL_SIZE
                y = BOARD_START_Y + r * CELL_SIZE
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                
                pygame.draw.rect(screen, BOARD_GREEN, rect)
                pygame.draw.rect(screen, BOARD_GRID_LINE, rect, 1) # Siatka

                bonus_text = self.bonus_map.get((r,c))
                if bonus_text and (r,c) not in self.placed_tiles:
                    # Rysowanie tekstu premii w dwóch liniach
                    parts = bonus_text.split()
                    line1 = font_bonus.render(parts[0], True, BONUS_TEXT_COLOR)
                    line2 = font_bonus.render(parts[1], True, BONUS_TEXT_COLOR)
                    
                    r1 = line1.get_rect(center=rect.center)
                    r2 = line2.get_rect(center=rect.center)
                    r1.centery -= 8
                    r2.centery += 8
                    screen.blit(line1, r1)
                    screen.blit(line2, r2)

    def draw_ui(self):
        # Prawy panel tła
        ui_rect = pygame.Rect(BOARD_START_X + BOARD_SIZE * CELL_SIZE + 20, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(screen, BG_GREEN_LIGHT, ui_rect)

        ui_start_x = ui_rect.left + 20

        # Logo
        logo = font_ui_big.render("SCRAB MANIA", True, (255, 215, 0)) # Złoty kolor
        pygame.draw.rect(screen, (0,50,0), (ui_start_x - 5, 15, logo.get_width()+10, logo.get_height()+5)) # Cień logo
        screen.blit(logo, (ui_start_x, 20))

        # Wyniki
        y_pos = 150
        screen.blit(font_ui_small.render("TY (punkty):", True, TEXT_WHITE), (ui_start_x, y_pos))
        screen.blit(font_ui_big.render(str(self.player_score), True, TEXT_WHITE), (ui_start_x + 150, y_pos - 5))
        
        y_pos += 60
        screen.blit(font_ui_small.render("KOMPUTER:", True, TEXT_WHITE), (ui_start_x, y_pos))
        screen.blit(font_ui_big.render(str(self.ai_score), True, TEXT_WHITE), (ui_start_x + 150, y_pos - 5))

        # Stojak gracza
        y_pos += 150
        rack_bg = pygame.Rect(ui_start_x - 10, y_pos - 10, 7 * (CELL_SIZE + 5) + 20, CELL_SIZE + 20)
        pygame.draw.rect(screen, (0, 60, 0), rack_bg, border_radius=10)

        current_rack_x = ui_start_x
        for i, tile in enumerate(self.player_rack):
            # Aktualizujemy pozycję "domową" kafelka na stojaku
            tile.rack_pos = (current_rack_x, y_pos)
            if not tile.is_dragging:
                tile.rect.topleft = tile.rack_pos
            
            tile.draw(screen)
            current_rack_x += CELL_SIZE + 5

        # Informacje o worku i turze
        y_pos += CELL_SIZE + 60
        screen.blit(font_ui_small.render(f"w worku: {len(self.bag)}", True, TEXT_WHITE), (ui_start_x, y_pos))
        
        turn_text = "Twoja tura" if self.turn == "PLAYER" else "Tura Komputera..."
        turn_color = (255, 255, 0) if self.turn == "PLAYER" else (200, 200, 200)
        screen.blit(font_ui_small.render(turn_text, True, turn_color), (ui_start_x, y_pos + 40))

        # Przycisk OK
        pygame.draw.circle(screen, BUTTON_PURPLE, self.ok_button_rect.center, 40)
        pygame.draw.circle(screen, (200, 200, 200), self.ok_button_rect.center, 40, 3) # Ramka
        ok_text = font_ui_big.render("OK!", True, TEXT_WHITE)
        screen.blit(ok_text, ok_text.get_rect(center=self.ok_button_rect.center))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if self.turn == "PLAYER":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # Kliknięcie przycisku OK
                        if self.ok_button_rect.collidepoint(event.pos):
                            # Tu powinna być walidacja słowa i liczenie punktów
                            # Na potrzeby demo, po prostu kończymy turę i dobieramy litery
                            tiles_to_remove = []
                            for pos, tile in self.placed_tiles.items():
                                if not tile.is_on_board: # To są te nowo położone
                                    tile.is_on_board = True
                                    # Symulacja punktów (prosta suma)
                                    self.player_score += tile.points
                                    if tile in self.player_rack: tiles_to_remove.append(tile)
                            
                            for t in tiles_to_remove: self.player_rack.remove(t)
                            self.fill_rack(self.player_rack)
                            self.turn = "AI"
                        
                        # Kliknięcie kafelka do przeciągania
                        else:
                            for tile in self.player_rack:
                                if tile.rect.collidepoint(event.pos):
                                    self.dragging_tile = tile
                                    self.dragging_tile.is_dragging = True
                                    self.drag_offset = (tile.rect.x - event.pos[0], tile.rect.y - event.pos[1])
                                    # Jeśli klocek był na planszy (ale jeszcze nie zatwierdzony), usuń go ze słownika
                                    keys_to_remove = [k for k, v in self.placed_tiles.items() if v == tile]
                                    for k in keys_to_remove: del self.placed_tiles[k]
                                    break

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.dragging_tile:
                        drop_x, drop_y = self.dragging_tile.rect.center
                        col = (drop_x - BOARD_START_X) // CELL_SIZE
                        row = (drop_y - BOARD_START_Y) // CELL_SIZE
                        
                        valid_drop = False
                        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
                            if (row, col) not in self.placed_tiles:
                                snap_x = BOARD_START_X + col * CELL_SIZE
                                snap_y = BOARD_START_Y + row * CELL_SIZE
                                self.dragging_tile.rect.topleft = (snap_x + 2, snap_y + 2)
                                self.placed_tiles[(row, col)] = self.dragging_tile
                                valid_drop = True

                        if not valid_drop:
                            self.dragging_tile.rect.topleft = self.dragging_tile.rack_pos

                        self.dragging_tile.is_dragging = False
                        self.dragging_tile = None

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging_tile:
                        self.dragging_tile.rect.x = event.pos[0] + self.drag_offset[0]
                        self.dragging_tile.rect.y = event.pos[1] + self.drag_offset[1]
        return True

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            
            if self.turn == "AI":
                self.ai_turn_logic()

            screen.fill(BG_GREEN_DARK)
            self.draw_board()
            
            # Rysowanie kafelków już leżących na planszy
            for pos, tile in self.placed_tiles.items():
                tile.draw(screen)

            self.draw_ui()

            # Rysowanie przeciąganego kafelka na samym wierzchu
            if self.dragging_tile:
                self.dragging_tile.draw(screen)
                
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = ScrabmaniaGame()
    game.run()
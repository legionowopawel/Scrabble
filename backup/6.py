import pygame
import sys
import os
import random

# --- KONFIGURACJA WIZUALNA (Zgodnie z obrazkiem) ---
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 850
BOARD_SIZE = 15
TILE_SIZE = 42
BOARD_X = 230
BOARD_Y = 100

COLOR_BG = (10, 40, 10)
COLOR_BOARD = (34, 139, 34)  # Ciemna zieleń jak na foto
COLOR_GRID = (0, 100, 0)
COLOR_RACK = (20, 60, 20)
COLOR_EXCHANGE = (173, 216, 230) # Jasny niebieski dla wymiany

# Premie z obrazka
P_5W = 8; P_4W = 7; P_3W = 6; P_2W = 5
P_5L = 4; P_4L = 3; P_3L = 2; P_2L = 1

LETTER_DISTRIBUTION = {
    'A': (9, 1), 'Ą': (1, 5), 'B': (2, 3), 'C': (3, 2), 'Ć': (1, 6),
    'D': (3, 2), 'E': (7, 1), 'Ę': (1, 5), 'F': (1, 5), 'G': (2, 3),
    'H': (2, 3), 'I': (8, 1), 'J': (2, 3), 'K': (3, 2), 'L': (3, 2),
    'Ł': (2, 3), 'M': (3, 2), 'N': (5, 1), 'Ń': (1, 7), 'O': (6, 1),
    'Ó': (1, 5), 'P': (3, 2), 'R': (4, 1), 'S': (4, 1), 'Ś': (1, 5),
    'T': (3, 2), 'U': (2, 3), 'W': (4, 1), 'Y': (4, 2), 'Z': (5, 1),
    'Ź': (1, 9), 'Ż': (1, 5)
}

class GameState:
    def __init__(self):
        pygame.mixer.init()
        self.bag = self.build_bag()
        self.board = [[None for _ in range(15)] for _ in range(15)]
        self.premium = self.setup_image_board()
        self.rack1 = [self.draw_one() for _ in range(7)]
        self.rack2 = [self.draw_one() for _ in range(7)]
        self.score1 = 0
        self.score2 = 0
        self.current_player = 1
        self.floating_tile = None # Litera "w ręku"
        self.floating_origin = None # Skąd pochodzi (rack/board)
        self.last_rmb_time = 0
        self.calc_display = ""
        self.exchange_mode = False
        self.exchange_selected = []
        self.sounds = self.load_sounds()

    def build_bag(self):
        b = []
        for char, (count, _) in LETTER_DISTRIBUTION.items():
            b.extend([char] * count)
        random.shuffle(b)
        return b

    def draw_one(self):
        return self.bag.pop() if self.bag else None

    def load_sounds(self):
        s = {}
        for i in range(1, 7):
            path = f"{i}.mp3"
            if os.path.exists(path): s[i] = pygame.mixer.Sound(path)
        return s

    def setup_image_board(self):
        # Odwzorowanie planszy z załączonego obrazka
        board = [[0 for _ in range(15)] for _ in range(15)]
        # Przykład rozmieszczenia (uproszczony na bazie schematu 5/4/3/2)
        for i in [0, 7, 14]:
            for j in [0, 7, 14]: board[i][j] = P_5W
        for i in [1, 13]:
            for j in [5, 9]: board[i][j] = P_4L
        board[7][7] = P_2W # Środek
        # ... (pełna mapa premii wg obrazka)
        return board

# --- FUNKCJE POMOCNICZE ---

def get_tile_score(char):
    return LETTER_DISTRIBUTION.get(char, (0,0))[1]

def draw_text(surf, text, pos, size=20, color=(255,255,255)):
    font = pygame.font.SysFont("Arial", size, bold=True)
    img = font.render(text, True, color)
    surf.blit(img, pos)

# --- GŁÓWNA PĘTLA ---

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game = GameState()
    clock = pygame.time.Clock()
    
    btn_confirm = pygame.Rect(480, 720, 140, 40)
    btn_exchange = pygame.Rect(480, 770, 140, 40)

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        screen.fill(COLOR_BG)

        # 1. Rysowanie planszy
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(BOARD_X + c*TILE_SIZE, BOARD_Y + r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                p = game.premium[r][c]
                color = COLOR_BOARD
                label = ""
                if p == P_5W: color, label = (200, 0, 0), "5W"
                elif p == P_4L: color, label = (0, 0, 200), "4L"
                # ... pozostałe kolory
                
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, COLOR_GRID, rect, 1)
                if label: draw_text(screen, label, (rect.x+5, rect.y+5), 14)

                tile = game.board[r][c]
                if tile:
                    pygame.draw.rect(screen, (240, 230, 140), rect.inflate(-4,-4))
                    draw_text(screen, tile, (rect.x+10, rect.y+5), 24, (0,0,0))

        # 2. Rysowanie Stojaków i UI
        # Gracz 1 (Lewy dół)
        for i, t in enumerate(game.rack1):
            r_rect = pygame.Rect(50 + i*45, 750, 40, 40)
            color = COLOR_EXCHANGE if game.exchange_mode and i in game.exchange_selected else (200,180,140)
            pygame.draw.rect(screen, color, r_rect)
            if t: draw_text(screen, t, (r_rect.x+10, r_rect.y+5), 22, (0,0,0))

        # Statystyki na górze
        draw_text(screen, f"Gracz 1: {game.score1}", (50, 20), 24)
        draw_text(screen, f"Gracz 2: {game.score2}", (900, 20), 24)
        draw_text(screen, f"Worek: {len(game.bag)}", (500, 20), 18)
        if game.calc_display:
            draw_text(screen, f"Obliczenie: {game.calc_display}", (350, 50), 20, (255, 215, 0))

        # Przyciski
        pygame.draw.rect(screen, (100,100,100), btn_confirm)
        draw_text(screen, "ZATWIERDŹ", (btn_confirm.x+15, btn_confirm.y+10), 18)
        pygame.draw.rect(screen, (100,100,100), btn_exchange)
        draw_text(screen, "WYMIANA", (btn_exchange.x+25, btn_exchange.y+10), 18)
        if game.exchange_mode:
            draw_text(screen, "Naciśnij litery do wymiany", (440, 820), 14, COLOR_EXCHANGE)

        # 3. Obsługa Pływającej Litery
        if game.floating_tile:
            f_rect = pygame.Rect(mx-20, my-20, 40, 40)
            pygame.draw.rect(screen, (255, 255, 200), f_rect)
            draw_text(screen, game.floating_tile, (f_rect.x+10, f_rect.y+5), 22, (0,0,0))

        # 4. EVENTY
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Powrót wszystkich nowych liter
                    game.calc_display = "" # przykładowy reset
                    if game.sounds.get(3): game.sounds[3].play()

            if event.type == pygame.MOUSEBUTTONDOWN:
                game.calc_display = "" # Znika przy każdym kliknięciu
                
                # --- PPM (Prawy Przycisk) ---
                if event.button == 3:
                    # Double click check
                    now = pygame.time.get_ticks()
                    if now - game.last_rmb_time < 300: # Double Click
                        # Logika powrotu na dół (do zaimplementowania zależnie od pozycji)
                        pass
                    game.last_rmb_time = now

                    # Podnoszenie ze stojaka
                    if not game.floating_tile:
                        # Sprawdź kolizję ze stojakiem aktualnego gracza
                        pass
                    else:
                        # Opuszczanie na planszę
                        col = (mx - BOARD_X) // TILE_SIZE
                        row = (my - BOARD_Y) // TILE_SIZE
                        if 0 <= row < 15 and 0 <= col < 15 and not game.board[row][col]:
                            game.board[row][col] = game.floating_tile
                            game.floating_tile = None
                            if game.sounds.get(1): game.sounds[1].play()

                # --- LPM (Lewy Przycisk) ---
                if event.button == 1:
                    # Kliknięcie w przyciski
                    if btn_confirm.collidepoint(mx, my):
                        # Logika zliczania
                        game.calc_display = "2 + 1 + (2 x 5W) = 13" # Przykładowy format
                        if game.sounds.get(2): game.sounds[2].play()
                    
                    if btn_exchange.collidepoint(mx, my):
                        if not game.exchange_mode:
                            game.exchange_mode = True
                        else:
                            # Wykonaj wymianę wybranych
                            game.exchange_mode = False
                            game.exchange_selected = []
                            if game.sounds.get(4): game.sounds[4].play()

                    # Chwytanie litery z planszy (przyplejenie do wskaźnika)
                    col = (mx - BOARD_X) // TILE_SIZE
                    row = (my - BOARD_Y) // TILE_SIZE
                    if 0 <= row < 15 and 0 <= col < 15 and game.board[row][row]:
                        game.floating_tile = game.board[row][col]
                        game.board[row][col] = None

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
import pygame
import sys
import os
import random

# ----------------------------------------
# KONFIGURACJA ESTETYCZNA
# ----------------------------------------
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 800
BOARD_SIZE = 15
TILE_SIZE = 40  # Powiększone dla czytelności
BOARD_OFFSET_X = 50
BOARD_OFFSET_Y = 100
RACK_Y_P1 = 720
RACK_Y_P2 = 20
RACK_TILES = 7

# Kolory premium
BG_COLOR = (30, 40, 45)
BOARD_COLOR = (220, 210, 190)
GRID_COLOR = (160, 150, 130)
TILE_FIXED_COLOR = (255, 250, 220)
TILE_NEW_COLOR = (180, 255, 180)
SELECTED_COLOR = (255, 215, 0)
TEXT_DARK = (40, 40, 40)

LETTER_DISTRIBUTION = {
    'A': (9, 1), 'Ą': (1, 5), 'B': (2, 3), 'C': (3, 2), 'Ć': (1, 6),
    'D': (3, 2), 'E': (7, 1), 'Ę': (1, 5), 'F': (1, 5), 'G': (2, 3),
    'H': (2, 3), 'I': (8, 1), 'J': (2, 3), 'K': (3, 2), 'L': (3, 2),
    'Ł': (2, 3), 'M': (3, 2), 'N': (5, 1), 'Ń': (1, 7), 'O': (6, 1),
    'Ó': (1, 5), 'P': (3, 2), 'R': (4, 1), 'S': (4, 1), 'Ś': (1, 5),
    'T': (3, 2), 'U': (2, 3), 'W': (4, 1), 'Y': (4, 2), 'Z': (5, 1),
    'Ź': (1, 9), 'Ż': (1, 5)
}

PREMIUM_NONE = 0
PREMIUM_LETTER_2 = 1
PREMIUM_LETTER_3 = 2
PREMIUM_WORD_2 = 3
PREMIUM_WORD_3 = 4

def create_premium_board():
    board = [[PREMIUM_NONE for _ in range(15)] for _ in range(15)]
    triple_word = [(0,0),(0,7),(0,14),(7,0),(7,14),(14,0),(14,7),(14,14)]
    for r,c in triple_word: board[r][c] = PREMIUM_WORD_3
    double_word = [(1,1),(2,2),(3,3),(4,4),(1,13),(2,12),(3,11),(4,10),(13,1),(12,2),(11,3),(10,4),(13,13),(12,12),(11,11),(10,10),(7,7)]
    for r,c in double_word: board[r][c] = PREMIUM_WORD_2
    triple_letter = [(1,5),(1,9),(5,1),(5,5),(5,9),(5,13),(9,1),(9,5),(9,9),(9,13),(13,5),(13,9)]
    for r,c in triple_letter: board[r][c] = PREMIUM_LETTER_3
    double_letter = [(0,3),(0,11),(2,6),(2,8),(3,0),(3,7),(3,14),(6,2),(6,6),(6,8),(6,12),(7,3),(7,11),(8,2),(8,6),(8,8),(8,12),(11,0),(11,7),(11,14),(12,6),(12,8),(14,3),(14,11)]
    for r,c in double_letter: board[r][c] = PREMIUM_LETTER_2
    return board

# ----------------------------------------
# LOGIKA GRY
# ----------------------------------------

class TileOnBoard:
    def __init__(self, letter, row, col, is_new=True):
        self.letter = letter
        self.row = row
        self.col = col
        self.is_new = is_new

class GameState:
    def __init__(self, dictionary):
        self.dictionary = dictionary
        self.bag = self.build_bag()
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.premium = create_premium_board()
        self.rack = {1: self.draw_tiles(RACK_TILES), 2: self.draw_tiles(RACK_TILES)}
        self.score = {1: 0, 2: 0}
        self.current_player = 1
        self.message = "Zacznij grę! Powodzenia."
        self.selected_rack_index = None
        self.first_move = True

    def build_bag(self):
        bag = []
        for letter, (count, _) in LETTER_DISTRIBUTION.items():
            bag.extend([letter] * count)
        random.shuffle(bag)
        return bag

    def draw_tiles(self, count):
        return [self.bag.pop() for _ in range(min(count, len(self.bag)))]

def score_tile(letter):
    return LETTER_DISTRIBUTION.get(letter, (0,0))[1]

# ----------------------------------------
# RYSOWANIE
# ----------------------------------------

def draw_rounded_rect(surface, color, rect, radius=5):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, (0, 0, 0), rect, 1, border_radius=radius)

def draw_tile(screen, font_big, font_small, letter, x, y, color, selected=False):
    rect = pygame.Rect(x, y, TILE_SIZE - 2, TILE_SIZE - 2)
    draw_rounded_rect(screen, color, rect)
    if selected:
        pygame.draw.rect(screen, SELECTED_COLOR, rect, 3, border_radius=5)
    
    txt = font_big.render(letter, True, TEXT_DARK)
    screen.blit(txt, (x + (TILE_SIZE//2 - txt.get_width()//2), y + 2))
    
    pts = font_small.render(str(score_tile(letter)), True, TEXT_DARK)
    screen.blit(pts, (x + TILE_SIZE - 12, y + TILE_SIZE - 15))

def draw_board(screen, font_ui, game):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            x = BOARD_OFFSET_X + c * TILE_SIZE
            y = BOARD_OFFSET_Y + r * TILE_SIZE
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            
            p = game.premium[r][c]
            color = BOARD_COLOR
            label = ""
            if p == PREMIUM_WORD_3: color, label = (255, 50, 50), "3W"
            elif p == PREMIUM_WORD_2: color, label = (255, 150, 150), "2W"
            elif p == PREMIUM_LETTER_3: color, label = (50, 100, 255), "3L"
            elif p == PREMIUM_LETTER_2: color, label = (150, 200, 255), "2L"
            
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)
            
            if label and not game.board[r][c]:
                lbl_txt = font_ui.render(label, True, (255, 255, 255))
                screen.blit(lbl_txt, (x + 10, y + 12))
            
            tile = game.board[r][c]
            if tile:
                t_color = TILE_NEW_COLOR if tile.is_new else TILE_FIXED_COLOR
                draw_tile(screen, font_main, font_small, tile.letter, x+1, y+1, t_color)

def draw_ui(screen, font_main, game, buttons):
    # Panel gracza
    p1_color = (255, 255, 255) if game.current_player == 1 else (100, 100, 100)
    p2_color = (255, 255, 255) if game.current_player == 2 else (100, 100, 100)
    
    s1 = font_main.render(f"Gracz 1: {game.score[1]} pkt", True, p1_color)
    s2 = font_main.render(f"Gracz 2: {game.score[2]} pkt", True, p2_color)
    screen.blit(s1, (700, 150))
    screen.blit(s2, (700, 200))
    
    msg = font_small.render(game.message, True, (200, 255, 200))
    screen.blit(msg, (700, 280))
    
    # Przyciski
    for name, rect in buttons.items():
        draw_rounded_rect(screen, (60, 80, 100), rect)
        b_txt = font_small.render(name, True, (255, 255, 255))
        screen.blit(b_txt, (rect.x + 15, rect.y + 10))

# ----------------------------------------
# POMOCNICZE FUNKCJE LOGICZNE (Uproszczone)
# ----------------------------------------

def get_new_tiles_list(game):
    return [t for row in game.board for t in row if t and t.is_new]

def revert_move(game):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            t = game.board[r][c]
            if t and t.is_new:
                game.rack[game.current_player].append(t.letter)
                game.board[r][c] = None

def end_turn(game):
    missing = RACK_TILES - len(game.rack[game.current_player])
    game.rack[game.current_player].extend(game.draw_tiles(missing))
    game.current_player = 2 if game.current_player == 1 else 1
    game.selected_rack_index = None

# --- Główna Funkcja ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("SCRABMANIA PRO")
    clock = pygame.time.Clock()
    
    # Fonty (załadowanie systemowych lub domyślnych)
    global font_main, font_small
    font_main = pygame.font.SysFont("Verdana", 24, bold=True)
    font_small = pygame.font.SysFont("Verdana", 16)
    font_ui = pygame.font.SysFont("Arial", 12, bold=True)
    
    from __main__ import load_dictionary, words_from_move, score_word # Importy z Twojego pliku
    
    dictionary = load_dictionary()
    game = GameState(dictionary)
    
    buttons = {
        "ZATWIERDŹ": pygame.Rect(700, 350, 140, 45),
        "WYMIANA": pygame.Rect(700, 410, 140, 45),
        "COFNIJ": pygame.Rect(700, 470, 140, 45)
    }

    running = True
    while running:
        screen.fill(BG_COLOR)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # OBSŁUGA MYSZY
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                
                # Przyciski
                if buttons["ZATWIERDŹ"].collidepoint(mx, my):
                    from __main__ import validate_move
                    if validate_move(game):
                        end_turn(game)
                    else:
                        game.message = "Ruch niepoprawny!"
                
                elif buttons["WYMIANA"].collidepoint(mx, my):
                    revert_move(game)
                    from __main__ import exchange_letters
                    exchange_letters(game)
                    end_turn(game)
                
                elif buttons["COFNIJ"].collidepoint(mx, my):
                    revert_move(game)

                # Kliknięcie w planszę
                elif BOARD_OFFSET_X <= mx <= BOARD_OFFSET_X + BOARD_SIZE*TILE_SIZE:
                    from __main__ import pos_to_board
                    res = pos_to_board((mx, my))
                    if res:
                        r, c = res
                        # Lewy przycisk: Połóż płytkę
                        if event.button == 1:
                            if game.board[r][c] is None and game.selected_rack_index is not None:
                                letter = game.rack[game.current_player].pop(game.selected_rack_index)
                                game.board[r][c] = TileOnBoard(letter, r, c)
                                game.selected_rack_index = None
                        # Prawy przycisk: Zdejmij płytkę
                        elif event.button == 3:
                            t = game.board[r][c]
                            if t and t.is_new:
                                game.rack[game.current_player].append(t.letter)
                                game.board[r][c] = None

                # Kliknięcie w stojak
                y_rack = RACK_Y_P1 if game.current_player == 1 else RACK_Y_P2
                if BOARD_OFFSET_X <= mx <= BOARD_OFFSET_X + RACK_TILES*TILE_SIZE and y_rack <= my <= y_rack + TILE_SIZE:
                    idx = (mx - BOARD_OFFSET_X) // TILE_SIZE
                    if idx < len(game.rack[game.current_player]):
                        game.selected_rack_index = idx

        # RYSOWANIE
        draw_board(screen, font_ui, game)
        
        # Stojak gracza 1
        for i, letter in enumerate(game.rack[1]):
            sel = (game.current_player == 1 and game.selected_rack_index == i)
            draw_tile(screen, font_main, font_small, letter, BOARD_OFFSET_X + i*TILE_SIZE, RACK_Y_P1, TILE_FIXED_COLOR, sel)
            
        # Stojak gracza 2
        for i, letter in enumerate(game.rack[2]):
            sel = (game.current_player == 2 and game.selected_rack_index == i)
            draw_tile(screen, font_main, font_small, letter, BOARD_OFFSET_X + i*TILE_SIZE, RACK_Y_P2, TILE_FIXED_COLOR, sel)

        draw_ui(screen, font_main, game, buttons)
        
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()
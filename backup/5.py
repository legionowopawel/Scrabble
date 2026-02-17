import pygame
import sys
import random
import os

# --- USTAWIENIA WIZUALNE ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1100, 850
BOARD_SIZE = 15
TILE_SIZE = 45
BOARD_X, BOARD_Y = 50, 80
FPS = 60

# Kolory
COLOR_BG = (20, 30, 35)
COLOR_GRID = (50, 50, 50)
COLOR_TILE = (240, 230, 200)
COLOR_TILE_NEW = (170, 255, 170)
COLOR_TEXT = (30, 30, 30)

# Punktacja i rozkład liter (Polska)
LETTERS = {
    'A': (9, 1), 'Ą': (1, 5), 'B': (2, 3), 'C': (3, 2), 'Ć': (1, 6),
    'D': (3, 2), 'E': (7, 1), 'Ę': (1, 5), 'F': (1, 5), 'G': (2, 3),
    'H': (2, 3), 'I': (8, 1), 'J': (2, 3), 'K': (3, 2), 'L': (3, 2),
    'Ł': (2, 3), 'M': (3, 2), 'N': (5, 1), 'Ń': (1, 7), 'O': (6, 1),
    'Ó': (1, 5), 'P': (3, 2), 'R': (4, 1), 'S': (4, 1), 'Ś': (1, 5),
    'T': (3, 2), 'U': (2, 3), 'W': (4, 1), 'Y': (4, 2), 'Z': (5, 1),
    'Ź': (1, 9), 'Ż': (1, 5)
}

class ScrabbleGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("SCRABMANIA 2.0 - Tryb Towarzyski")
        self.clock = pygame.time.Clock()
        
        # Czcionki
        self.font_tile = pygame.font.SysFont("Verdana", 26, bold=True)
        self.font_pts = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_ui = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 14)

        # Ładowanie dźwięków
        self.sounds = {}
        for i in range(1, 7):
            fname = f"{i}.mp3"
            if os.path.exists(fname):
                self.sounds[i] = pygame.mixer.Sound(fname)
            else:
                print(f"Uwaga: Nie znaleziono pliku {fname}")
                self.sounds[i] = None

        self.reset_game()

    def play_sound(self, key):
        if self.sounds.get(key):
            self.sounds[key].play()

    def reset_game(self):
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.bag = [l for l, (count, _) in LETTERS.items() for _ in range(count)]
        random.shuffle(self.bag)
        
        self.racks = {1: self.draw_from_bag(7), 2: self.draw_from_bag(7)}
        self.scores = {1: 0, 2: 0}
        self.current_player = 1
        self.selected_idx = None
        self.msg = "Zaczyna Gracz 1"
        self.game_over = False

    def draw_from_bag(self, n):
        drawn = []
        for _ in range(min(n, len(self.bag))):
            drawn.append(self.bag.pop())
        return drawn

    def get_premium(self, r, c):
        tw = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        dw = [(1,1), (2,2), (3,3), (4,4), (1,13), (2,12), (3,11), (4,10), (13,1), (12,2), (11,3), (10,4), (13,13), (12,12), (11,11), (10,10), (7,7)]
        tl = [(1,5), (1,9), (5,1), (5,5), (5,9), (5,13), (9,1), (9,5), (9,9), (9,13), (13,5), (13,9)]
        dl = [(0,3), (0,11), (2,6), (2,8), (3,0), (3,7), (3,14), (6,2), (6,6), (6,8), (6,12), (7,3), (7,11), (8,2), (8,6), (8,8), (8,12), (11,0), (11,7), (11,14), (12,6), (12,8), (14,3), (14,11)]
        
        if (r,c) in tw: return ("3W", (200, 50, 50))
        if (r,c) in dw: return ("2W", (255, 120, 120))
        if (r,c) in tl: return ("3L", (50, 80, 200))
        if (r,c) in dl: return ("2L", (120, 150, 255))
        return None

    def calculate_turn_score(self):
        new_tiles = [(r, c, self.board[r][c]['letter']) 
                     for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) 
                     if self.board[r][c] and self.board[r][c]['new']]
        
        if not new_tiles: return 0
        
        turn_total = 0
        word_multiplier = 1
        
        for r, c, letter in new_tiles:
            val = LETTERS[letter][1]
            premium = self.get_premium(r, c)
            if premium:
                ptype, _ = premium
                if ptype == "2L": val *= 2
                elif ptype == "3L": val *= 3
                elif ptype == "2W": word_multiplier *= 2
                elif ptype == "3W": word_multiplier *= 3
            turn_total += val
            
        return turn_total * word_multiplier

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # Rysowanie planszy
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x, y = BOARD_X + c * TILE_SIZE, BOARD_Y + r * TILE_SIZE
                rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                
                prem = self.get_premium(r, c)
                color = prem[1] if prem else (40, 45, 50)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLOR_GRID, rect, 1)
                
                if prem and not self.board[r][c]:
                    p_txt = self.font_small.render(prem[0], True, (255, 255, 255))
                    self.screen.blit(p_txt, (x+10, y+15))

                tile = self.board[r][c]
                if tile:
                    t_color = COLOR_TILE_NEW if tile['new'] else COLOR_TILE
                    self.draw_single_tile(tile['letter'], x, y, t_color)

        # UI - Panel boczny
        p1_c = (255, 255, 255) if self.current_player == 1 else (100, 100, 100)
        p2_c = (255, 255, 255) if self.current_player == 2 else (100, 100, 100)
        
        self.screen.blit(self.font_ui.render(f"GRACZ 1: {self.scores[1]}", True, p1_c), (780, 100))
        self.screen.blit(self.font_ui.render(f"GRACZ 2: {self.scores[2]}", True, p2_c), (780, 150))
        
        msg_box = self.font_small.render(self.msg, True, (200, 255, 200))
        self.screen.blit(msg_box, (50, 40))

        # Stojak gracza
        rack = self.racks[self.current_player]
        for i, letter in enumerate(rack):
            rx, ry = BOARD_X + i * (TILE_SIZE + 10), 780
            t_col = (255, 215, 0) if self.selected_idx == i else COLOR_TILE
            self.draw_single_tile(letter, rx, ry, t_col)

        # Przyciski
        self.btn_ok = pygame.Rect(780, 300, 180, 50)
        self.btn_ex = pygame.Rect(780, 370, 180, 50)
        pygame.draw.rect(self.screen, (60, 80, 100), self.btn_ok, border_radius=10)
        pygame.draw.rect(self.screen, (60, 80, 100), self.btn_ex, border_radius=10)
        self.screen.blit(self.font_ui.render("ZATWIERDŹ", True, (255,255,255)), (800, 310))
        self.screen.blit(self.font_ui.render("WYMIANA", True, (255,255,255)), (815, 380))

        pygame.display.flip()

    def draw_single_tile(self, letter, x, y, color):
        rect = pygame.Rect(x, y, TILE_SIZE-2, TILE_SIZE-2)
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        pygame.draw.rect(self.screen, (0,0,0), rect, 1, border_radius=5)
        
        txt = self.font_tile.render(letter, True, COLOR_TEXT)
        self.screen.blit(txt, (x + 8, y + 2))
        
        pts = self.font_pts.render(str(LETTERS[letter][1]), True, COLOR_TEXT)
        self.screen.blit(pts, (x + 30, y + 28))

    def handle_input(self, pos, button):
        mx, my = pos
        
        # Przyciski
        if self.btn_ok.collidepoint(mx, my):
            self.submit_turn()
            return

        if self.btn_ex.collidepoint(mx, my):
            self.exchange_tiles()
            return

        # Stojak
        if 780 <= my <= 780 + TILE_SIZE:
            idx = (mx - BOARD_X) // (TILE_SIZE + 10)
            if 0 <= idx < len(self.racks[self.current_player]):
                self.selected_idx = idx

        # Plansza
        if BOARD_X <= mx <= BOARD_X + BOARD_SIZE * TILE_SIZE and \
           BOARD_Y <= my <= BOARD_Y + BOARD_SIZE * TILE_SIZE:
            col = (mx - BOARD_X) // TILE_SIZE
            row = (my - BOARD_Y) // TILE_SIZE
            
            if button == 1: # Lewy - połóż
                if self.selected_idx is not None and self.board[row][col] is None:
                    letter = self.racks[self.current_player].pop(self.selected_idx)
                    self.board[row][col] = {'letter': letter, 'new': True}
                    self.selected_idx = None
                    self.play_sound(1)
            elif button == 3: # Prawy - cofnij
                tile = self.board[row][col]
                if tile and tile['new']:
                    self.racks[self.current_player].append(tile['letter'])
                    self.board[row][col] = None
                    self.play_sound(3)

    def submit_turn(self):
        pts = self.calculate_turn_score()
        if pts == 0:
            self.msg = "Błąd: Połóż litery na planszy!"
            self.play_sound(3)
            return

        self.scores[self.current_player] += pts
        
        # Utrwalenie
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] and self.board[r][c]['new']:
                    self.board[r][c]['new'] = False
        
        self.msg = f"Gracz {self.current_player} zdobył {pts} pkt!"
        self.play_sound(2)
        self.next_turn()

    def exchange_tiles(self):
        # Cofnij litery z planszy
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] and self.board[r][c]['new']:
                    self.racks[self.current_player].append(self.board[r][c]['letter'])
                    self.board[r][c] = None
        
        if not self.racks[self.current_player]: return
        
        # Wymiana
        old_rack = self.racks[self.current_player]
        self.bag.extend(old_rack)
        random.shuffle(self.bag)
        self.racks[self.current_player] = self.draw_from_bag(7)
        self.msg = f"Gracz {self.current_player} wymienił litery."
        self.play_sound(4)
        self.next_turn()

    def next_turn(self):
        # Dobierz litery
        needed = 7 - len(self.racks[self.current_player])
        self.racks[self.current_player].extend(self.draw_from_bag(needed))
        
        # Sprawdzenie końca
        if not self.bag and not self.racks[self.current_player]:
            self.end_game()
            return

        self.current_player = 2 if self.current_player == 1 else 1
        self.selected_idx = None

    def end_game(self):
        self.game_over = True
        if self.scores[1] > self.scores[2]:
            self.msg = "KONIEC GRY! WYGRYWA GRACZ 1!"
            self.play_sound(5)
        elif self.scores[2] > self.scores[1]:
            self.msg = "KONIEC GRY! WYGRYWA GRACZ 2!"
            self.play_sound(6)
        else:
            self.msg = "REMIS!"

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if not self.game_over and event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_input(event.pos, event.button)
            
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    ScrabbleGame().run()
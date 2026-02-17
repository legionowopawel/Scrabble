import pygame
import sys
import random
import os

# --- KONFIGURACJA ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1100, 850
BOARD_SIZE = 15
TILE_SIZE = 42
BOARD_X, BOARD_Y = 230, 100

# Kolory z obrazka
COLOR_BG = (10, 45, 10)
COLOR_BOARD = (34, 139, 34)
COLOR_GRID = (0, 100, 0)
COLOR_TILE = (245, 222, 179)
COLOR_TEXT = (40, 40, 40)
COLOR_SELECT = (173, 216, 230) # Jasnoniebieski do wymiany

# Punktacja Polska
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
        pygame.display.set_caption("SCRABMANIA PRO 2.0")
        
        self.font_tile = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_ui = pygame.font.SysFont("Verdana", 20, bold=True)
        self.font_calc = pygame.font.SysFont("Courier New", 18, bold=True)

        self.sounds = self.load_sounds()
        self.reset_game()

    def load_sounds(self):
        s = {}
        for i in range(1, 7):
            path = f"{i}.mp3"
            if os.path.exists(path): s[i] = pygame.mixer.Sound(path)
        return s

    def reset_game(self):
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.bag = [l for l, (count, _) in LETTERS.items() for _ in range(count)]
        random.shuffle(self.bag)
        
        self.racks = {1: self.draw_tiles(7), 2: self.draw_tiles(7)}
        self.scores = {1: 0, 2: 0}
        self.current_player = 1
        self.floating_tile = None 
        self.exchange_selected = []
        self.exchange_mode = False
        self.calc_text = ""
        self.game_over = False

    def draw_tiles(self, n):
        return [self.bag.pop() for _ in range(min(n, len(self.bag)))]

    def get_premium(self, r, c):
        # Definicja pól wg Twojego obrazka (5W w rogach i środkach boków)
        tw5 = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        tl4 = [(1,5), (1,9), (5,1), (5,13), (9,1), (9,13), (13,5), (13,9)]
        if (r,c) in tw5: return ("5W", (200, 0, 0))
        if (r,c) in tl4: return ("4L", (0, 0, 180))
        return None

    def calculate_score(self):
        new_tiles = [(r, c, self.board[r][c]['letter']) 
                     for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) 
                     if self.board[r][c] and self.board[r][c]['new']]
        
        if not new_tiles: return 0, ""
        
        points = 0
        multiplier = 1
        math_parts = []
        
        for r, c, letter in new_tiles:
            val = LETTERS[letter][1]
            prem = self.get_premium(r, c)
            if prem:
                ptype, _ = prem
                if ptype == "4L":
                    points += (val * 4)
                    math_parts.append(f"({val}x4L)")
                elif ptype == "5W":
                    points += val
                    multiplier *= 5
                    math_parts.append(str(val))
                else:
                    points += val
                    math_parts.append(str(val))
            else:
                points += val
                math_parts.append(str(val))
        
        total = points * multiplier
        math_str = " + ".join(math_parts)
        if multiplier > 1: math_str = f"({math_str}) x {multiplier}W"
        return total, f"{math_str} = {total} pkt"

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # UI - Punkty i obliczenia na górze
        self.screen.blit(self.font_ui.render(f"Gracz 1: {self.scores[1]}", True, (255,255,255)), (50, 20))
        self.screen.blit(self.font_ui.render(f"Gracz 2: {self.scores[2]}", True, (255,255,255)), (880, 20))
        self.screen.blit(self.font_ui.render(f"Worek: {len(self.bag)}", True, (200,200,200)), (500, 20))
        if self.calc_text:
            txt = self.font_calc.render(self.calc_text, True, (255, 255, 0))
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 60))

        # Plansza
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x, y = BOARD_X + c * TILE_SIZE, BOARD_Y + r * TILE_SIZE
                rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                
                prem = self.get_premium(r, c)
                color = prem[1] if prem else COLOR_BOARD
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLOR_GRID, rect, 1)
                
                if prem and not self.board[r][c]:
                    p_img = self.font_small.render(prem[0], True, (255,255,255))
                    self.screen.blit(p_img, (x+10, y+15))

                tile = self.board[r][c]
                if tile:
                    self.draw_tile_obj(tile['letter'], x, y, (200, 255, 200) if tile['new'] else COLOR_TILE)

        # Stojaki
        # Gracz 1 - Lewy dół
        for i, l in enumerate(self.racks[1]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==1 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, 50, 300 + i*50, col)
            
        # Gracz 2 - Prawy dół
        for i, l in enumerate(self.racks[2]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==2 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, 1000, 300 + i*50, col)

        # Przyciski
        self.btn_ok = pygame.Rect(480, 750, 140, 40)
        self.btn_ex = pygame.Rect(480, 800, 140, 40)
        pygame.draw.rect(self.screen, (100,100,100), self.btn_ok)
        pygame.draw.rect(self.screen, (100,100,100), self.btn_ex)
        self.screen.blit(self.font_ui.render("ZATWIERDŹ", True, (255,255,255)), (488, 758))
        self.screen.blit(self.font_ui.render("WYMIANA", True, (255,255,255)), (500, 808))
        
        if self.exchange_mode:
            self.screen.blit(self.font_small.render("Zaznacz litery i kliknij WYMIANA ponownie", True, COLOR_SELECT), (420, 840))

        # Pływająca litera
        if self.floating_tile:
            mx, my = pygame.mouse.get_pos()
            self.draw_tile_obj(self.floating_tile, mx-20, my-20, (255, 255, 200))

        pygame.display.flip()

    def draw_tile_obj(self, letter, x, y, color):
        rect = pygame.Rect(x, y, TILE_SIZE-2, TILE_SIZE-2)
        pygame.draw.rect(self.screen, color, rect, border_radius=4)
        pygame.draw.rect(self.screen, (0,0,0), rect, 1)
        self.screen.blit(self.font_tile.render(letter, True, COLOR_TEXT), (x+10, y+2))
        self.screen.blit(self.font_small.render(str(LETTERS[letter][1]), True, COLOR_TEXT), (x+30, y+28))

    def handle_click(self, pos, button):
        self.calc_text = "" # Znikanie obliczeń przy kliknięciu
        mx, my = pos

        # Przyciski
        if self.btn_ok.collidepoint(mx, my):
            self.confirm_move()
            return
        if self.btn_ex.collidepoint(mx, my):
            self.handle_exchange_btn()
            return

        # Kliknięcie w stojak (wybór do przenoszenia lub wymiany)
        if self.current_player == 1:
            if 50 <= mx <= 50+TILE_SIZE:
                idx = (my - 300) // 50
                if 0 <= idx < len(self.racks[1]):
                    if self.exchange_mode:
                        if idx in self.exchange_selected: self.exchange_selected.remove(idx)
                        else: self.exchange_selected.append(idx)
                    else:
                        self.floating_tile = self.racks[1].pop(idx)
                        if self.sounds.get(1): self.sounds[1].play()

        if self.current_player == 2:
            if 1000 <= mx <= 1000+TILE_SIZE:
                idx = (my - 300) // 50
                if 0 <= idx < len(self.racks[2]):
                    if self.exchange_mode:
                        if idx in self.exchange_selected: self.exchange_selected.remove(idx)
                        else: self.exchange_selected.append(idx)
                    else:
                        self.floating_tile = self.racks[2].pop(idx)
                        if self.sounds.get(1): self.sounds[1].play()

        # Kliknięcie w planszę
        if BOARD_X <= mx <= BOARD_X + BOARD_SIZE*TILE_SIZE and BOARD_Y <= my <= BOARD_Y + BOARD_SIZE*TILE_SIZE:
            c = (mx - BOARD_X) // TILE_SIZE
            r = (my - BOARD_Y) // TILE_SIZE
            
            if self.floating_tile: # Połóż
                if not self.board[r][c]:
                    self.board[r][c] = {'letter': self.floating_tile, 'new': True}
                    self.floating_tile = None
                    if self.sounds.get(1): self.sounds[1].play()
            else: # Podnieś nową literę
                if self.board[r][c] and self.board[r][c]['new']:
                    self.floating_tile = self.board[r][c]['letter']
                    self.board[r][c] = None
                    if self.sounds.get(1): self.sounds[1].play()

    def confirm_move(self):
        pts, math = self.calculate_score()
        if pts > 0:
            self.scores[self.current_player] += pts
            self.calc_text = math
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if self.board[r][c]: self.board[r][c]['new'] = False
            
            # Dobieranie
            needed = 7 - len(self.racks[self.current_player])
            self.racks[self.current_player].extend(self.draw_tiles(needed))
            self.current_player = 2 if self.current_player == 1 else 1
            if self.sounds.get(2): self.sounds[2].play()
        else:
            if self.sounds.get(3): self.sounds[3].play()

    def handle_exchange_btn(self):
        if not self.exchange_mode:
            self.exchange_mode = True
        else:
            if self.exchange_selected:
                # Wykonaj wymianę
                self.exchange_selected.sort(reverse=True)
                for i in self.exchange_selected:
                    letter = self.racks[self.current_player].pop(i)
                    self.bag.append(letter)
                random.shuffle(self.bag)
                self.racks[self.current_player].extend(self.draw_tiles(len(self.exchange_selected)))
                
                if self.sounds.get(4): self.sounds[4].play()
                self.current_player = 2 if self.current_player == 1 else 1
            
            self.exchange_mode = False
            self.exchange_selected = []

    def run(self):
        while not self.game_over:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Powrót liter z planszy na stojak
                        for r in range(BOARD_SIZE):
                            for c in range(BOARD_SIZE):
                                if self.board[r][c] and self.board[r][c]['new']:
                                    self.racks[self.current_player].append(self.board[r][c]['letter'])
                                    self.board[r][c] = None
                        if self.sounds.get(3): self.sounds[3].play()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos, event.button)
            
            self.draw()
            pygame.time.Clock().tick(60)

if __name__ == "__main__":
    ScrabbleGame().run()
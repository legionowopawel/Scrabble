import pygame
import sys
import os
import random
import pandas as pd

# --- KONFIGURACJA EKRANU ---
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 850
COLOR_BG = (10, 45, 10)
COLOR_BOARD = (34, 139, 34)
COLOR_GRID = (0, 100, 0)
COLOR_TILE = (245, 222, 179)
COLOR_TEXT = (40, 40, 40)
COLOR_SELECT = (173, 216, 230) # Jasnoniebieski dla wymiany

LETTERS_DATA = {
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
        pygame.display.set_caption("SCRABBLE PRO - ODS MODE")
        
        # Czcionki
        self.font_tile = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_ui = pygame.font.SysFont("Verdana", 18, bold=True)
        self.font_calc = pygame.font.SysFont("Courier New", 18, bold=True)

        self.sounds = self.load_sounds()
        
        # Inicjalizacja zmiennych planszy (aby uniknąć AttributeError)
        self.board_dim = 15
        self.tile_size = 40
        self.board_x = 0
        self.board_y = 0
        self.premium_map = {}
        
        self.load_board_from_ods()
        self.reset_game_state()

    def load_sounds(self):
        s = {}
        for i in range(1, 7):
            path = f"{i}.mp3"
            if os.path.exists(path):
                s[i] = pygame.mixer.Sound(path)
        return s

    def load_board_from_ods(self):
        file_path = "plansza.ods"
        # Domyślne wymiary jeśli plik zawiedzie
        self.board_dim = 15
        self.premium_map = {}
        
        if os.path.exists(file_path):
            try:
                # Wymuszenie silnika odf (odfpy)
                df = pd.read_excel(file_path, engine="odf", header=None)
                df = df.fillna("")
                rows, cols = df.shape
                self.board_dim = max(rows, cols)
                
                for r in range(rows):
                    for c in range(cols):
                        val = str(df.iloc[r, c]).strip().upper()
                        if val:
                            if val.endswith('S') or val.endswith('W'):
                                mult = int(val[:-1])
                                self.premium_map[(r, c)] = ("S", mult, (200, 0, 0))
                            elif val.endswith('L'):
                                mult = int(val[:-1])
                                self.premium_map[(r, c)] = ("L", mult, (0, 0, 180))
                print(f"Wczytano planszę {self.board_dim}x{self.board_dim}")
            except Exception as e:
                print(f"Błąd czytania ODS: {e}. Używam 15x15.")

        # Przeliczenie współrzędnych rysowania
        self.tile_size = min(600 // self.board_dim, 45)
        self.board_x = (SCREEN_WIDTH - (self.board_dim * self.tile_size)) // 2
        self.board_y = 100

    def reset_game_state(self):
        self.board_state = [[None for _ in range(self.board_dim)] for _ in range(self.board_dim)]
        self.bag = [l for l, (count, _) in LETTERS_DATA.items() for _ in range(count)]
        random.shuffle(self.bag)
        
        self.racks = {1: self.draw_tiles(7), 2: self.draw_tiles(7)}
        self.scores = {1: 0, 2: 0} # Suma punktów w dolnych rogach
        self.current_player = 1
        self.floating_tile = None 
        self.exchange_mode = False
        self.exchange_selected = []
        self.calc_text = ""

    def draw_tiles(self, n):
        return [self.bag.pop() for _ in range(min(n, len(self.bag)))]

    def calculate_current_score(self):
        new_tiles = [(r, c, self.board_state[r][c]['letter']) 
                     for r in range(self.board_dim) for c in range(self.board_dim) 
                     if self.board_state[r][c] and self.board_state[r][c]['new']]
        
        if not new_tiles: return 0, ""
        
        points = 0
        word_mult = 1
        math_parts = []
        
        for r, c, letter in new_tiles:
            val = LETTERS_DATA[letter][1]
            prem = self.premium_map.get((r, c))
            if prem:
                ptype, mult, _ = prem
                if ptype == "L":
                    points += (val * mult)
                    math_parts.append(f"({val}x{mult}L)")
                else:
                    points += val
                    word_mult *= mult
                    math_parts.append(str(val))
            else:
                points += val
                math_parts.append(str(val))
        
        total = points * word_mult
        math_str = " + ".join(math_parts)
        if word_mult > 1: math_str = f"({math_str}) x {word_mult}S"
        return total, f"{math_str} = {total}"

    def draw_tile(self, letter, x, y, color, size):
        rect = pygame.Rect(x, y, size-2, size-2)
        pygame.draw.rect(self.screen, color, rect, border_radius=4)
        pygame.draw.rect(self.screen, (0,0,0), rect, 1)
        # Litera
        l_img = self.font_tile.render(letter, True, COLOR_TEXT)
        self.screen.blit(l_img, (x + (size - l_img.get_width())//2, y + 2))
        # Punkty
        p_img = self.font_small.render(str(LETTERS_DATA[letter][1]), True, COLOR_TEXT)
        self.screen.blit(p_img, (x + size - 12, y + size - 15))

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # PUNKTY W ROGACH
        p1_txt = self.font_ui.render(f"GRACZ 1: {self.scores[1]} pkt", True, (255, 255, 255))
        self.screen.blit(p1_txt, (50, SCREEN_HEIGHT - 60))
        p2_txt = self.font_ui.render(f"GRACZ 2: {self.scores[2]} pkt", True, (255, 255, 255))
        self.screen.blit(p2_txt, (SCREEN_WIDTH - 250, SCREEN_HEIGHT - 60))

        # INFO O WORKU I OBLICZENIA
        bag_txt = self.font_ui.render(f"Worek: {len(self.bag)}", True, (180, 180, 180))
        self.screen.blit(bag_txt, (SCREEN_WIDTH//2 - bag_txt.get_width()//2, 20))
        
        if self.calc_text:
            calc_img = self.font_calc.render(self.calc_text, True, (255, 255, 0))
            self.screen.blit(calc_img, (SCREEN_WIDTH//2 - calc_img.get_width()//2, 60))

        # PLANSZA
        for r in range(self.board_dim):
            for c in range(self.board_dim):
                x, y = self.board_x + c * self.tile_size, self.board_y + r * self.tile_size
                rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
                
                prem = self.premium_map.get((r, c))
                color = prem[2] if prem else COLOR_BOARD
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLOR_GRID, rect, 1)
                
                if prem and not self.board_state[r][c]:
                    p_txt = self.font_small.render(f"{prem[1]}{prem[0]}", True, (255,255,255))
                    self.screen.blit(p_txt, (x + (self.tile_size - p_txt.get_width())//2, y + self.tile_size//3))

                tile = self.board_state[r][c]
                if tile:
                    t_color = (200, 255, 200) if tile['new'] else COLOR_TILE
                    self.draw_tile(tile['letter'], x, y, t_color, self.tile_size)

        # STOJAKI
        for i, l in enumerate(self.racks[1]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==1 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile(l, 50, 200 + i*50, col, 42)
            
        for i, l in enumerate(self.racks[2]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==2 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile(l, SCREEN_WIDTH - 92, 200 + i*50, col, 42)

        # PRZYCISKI
        self.btn_ok = pygame.Rect(SCREEN_WIDTH//2 - 70, SCREEN_HEIGHT - 130, 140, 40)
        self.btn_ex = pygame.Rect(SCREEN_WIDTH//2 - 70, SCREEN_HEIGHT - 80, 140, 40)
        pygame.draw.rect(self.screen, (80,80,80), self.btn_ok)
        pygame.draw.rect(self.screen, (80,80,80), self.btn_ex)
        self.screen.blit(self.font_ui.render("ZATWIERDŹ", True, (255,255,255)), (self.btn_ok.x + 10, self.btn_ok.y + 8))
        self.screen.blit(self.font_ui.render("WYMIANA", True, (255,255,255)), (self.btn_ex.x + 22, self.btn_ex.y + 8))
        
        # PŁYWAJĄCA LITERA
        if self.floating_tile:
            mx, my = pygame.mouse.get_pos()
            self.draw_tile(self.floating_tile, mx-20, my-20, (255, 255, 180), 42)

        pygame.display.flip()

    def handle_click(self, pos):
        self.calc_text = "" # Znika po kliknięciu
        mx, my = pos

        # Przyciski
        if self.btn_ok.collidepoint(mx, my):
            pts, math = self.calculate_current_score()
            if pts > 0:
                self.scores[self.current_player] += pts
                self.calc_text = math
                for r in range(self.board_dim):
                    for c in range(self.board_dim):
                        if self.board_state[r][c]: self.board_state[r][c]['new'] = False
                # Dobieranie
                self.racks[self.current_player].extend(self.draw_tiles(7 - len(self.racks[self.current_player])))
                self.current_player = 2 if self.current_player == 1 else 1
                if self.sounds.get(2): self.sounds[2].play()
            return

        if self.btn_ex.collidepoint(mx, my):
            if not self.exchange_mode:
                self.exchange_mode = True
            else:
                if self.exchange_selected:
                    self.exchange_selected.sort(reverse=True)
                    for i in self.exchange_selected:
                        l = self.racks[self.current_player].pop(i)
                        self.bag.append(l)
                    random.shuffle(self.bag)
                    self.racks[self.current_player].extend(self.draw_tiles(len(self.exchange_selected)))
                    self.current_player = 2 if self.current_player == 1 else 1
                    if self.sounds.get(4): self.sounds[4].play()
                self.exchange_mode = False
                self.exchange_selected = []
            return

        # Kliknięcie w stojaki
        if self.current_player == 1 and 50 <= mx <= 92:
            idx = (my - 200) // 50
            if 0 <= idx < len(self.racks[1]):
                if self.exchange_mode:
                    if idx in self.exchange_selected: self.exchange_selected.remove(idx)
                    else: self.exchange_selected.append(idx)
                else:
                    self.floating_tile = self.racks[1].pop(idx)

        elif self.current_player == 2 and SCREEN_WIDTH-92 <= mx <= SCREEN_WIDTH-50:
            idx = (my - 200) // 50
            if 0 <= idx < len(self.racks[2]):
                if self.exchange_mode:
                    if idx in self.exchange_selected: self.exchange_selected.remove(idx)
                    else: self.exchange_selected.append(idx)
                else:
                    self.floating_tile = self.racks[2].pop(idx)

        # Kliknięcie w planszę
        if self.board_x <= mx <= self.board_x + self.board_dim * self.tile_size:
            c = (mx - self.board_x) // self.tile_size
            r = (my - self.board_y) // self.tile_size
            if 0 <= r < self.board_dim and 0 <= c < self.board_dim:
                if self.floating_tile: # Połóż
                    if not self.board_state[r][c]:
                        self.board_state[r][c] = {'letter': self.floating_tile, 'new': True}
                        self.floating_tile = None
                        if self.sounds.get(1): self.sounds[1].play()
                else: # Podnieś nową
                    if self.board_state[r][c] and self.board_state[r][c]['new']:
                        self.floating_tile = self.board_state[r][c]['letter']
                        self.board_state[r][c] = None

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # ESC: Powrót nowych liter na stojak
                        for r in range(self.board_dim):
                            for c in range(self.board_dim):
                                if self.board_state[r][c] and self.board_state[r][c]['new']:
                                    self.racks[self.current_player].append(self.board_state[r][c]['letter'])
                                    self.board_state[r][c] = None
                        if self.sounds.get(3): self.sounds[3].play()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
            
            self.draw()
            clock.tick(60)

if __name__ == "__main__":
    ScrabbleGame().run()
import pygame
import sys
import random
import os
import pandas as pd
import calc

# --- KONFIGURACJA ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1100, 850
COLOR_BG = (10, 45, 10)
COLOR_BOARD = (34, 139, 34)
COLOR_GRID = (0, 100, 0)
COLOR_TILE = (245, 222, 179)
COLOR_TEXT = (40, 40, 40)
COLOR_SELECT = (173, 216, 230)

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
        pygame.display.set_caption("SCRABMANIA PRO - ODS Edition")
        
        self.font_tile = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_ui = pygame.font.SysFont("Verdana", 18, bold=True)
        self.font_calc = pygame.font.SysFont("Courier New", 16, bold=True)

        self.sounds = self.load_sounds()
        self.load_board_config() # Wczytanie ODS przed resetem
        self.reset_game()

    def load_board_config(self):
        """Wczytuje strukturę planszy z pliku ODS"""
        file_path = "plansza.ods"
        if not os.path.exists(file_path):
            print("Błąd: Brak pliku plansza.ods! Tworzę domyślną 15x15.")
            self.board_dim = 15
            self.premium_map = {}
            return

        try:
            # Wczytujemy arkusz (pierwszy z brzegu)
            df = pd.read_excel(file_path, engine="odfpy", header=None)
            df = df.fillna("") # Zamiana NaN na pusty ciąg
            
            rows, cols = df.shape
            self.board_dim = max(rows, cols) # Zawsze kwadratowa
            self.premium_map = {}

            for r in range(rows):
                for c in range(cols):
                    val = str(df.iloc[r, c]).strip().upper()
                    if val:
                        # Rozpoznawanie typu premii (np. 5S, 10L)
                        if val.endswith('S') or val.endswith('W'):
                            multiplier = int(val[:-1])
                            self.premium_map[(r, c)] = ("S", multiplier, (200, 0, 0))
                        elif val.endswith('L'):
                            multiplier = int(val[:-1])
                            self.premium_map[(r, c)] = ("L", multiplier, (0, 0, 180))
            
            # Dynamiczne obliczanie rozmiaru pola, by zmieścić się na ekranie
            self.tile_size = min(600 // self.board_dim, 45)
            self.board_x = (SCREEN_WIDTH - (self.board_dim * self.tile_size)) // 2
            self.board_y = 120

        except Exception as e:
            print(f"Błąd podczas czytania ODS: {e}")
            self.board_dim = 15
            self.premium_map = {}

    def load_sounds(self):
        s = {}
        for i in range(1, 7):
            path = f"{i}.mp3"
            if os.path.exists(path): s[i] = pygame.mixer.Sound(path)
        return s

    def reset_game(self):
        self.board_state = [[None for _ in range(self.board_dim)] for _ in range(self.board_dim)]
        self.bag = [l for l, (count, _) in LETTERS.items() for _ in range(count)]
        random.shuffle(self.bag)
        
        self.racks = {1: self.draw_tiles(7), 2: self.draw_tiles(7)}
        self.scores = {1: 0, 2: 0} # To są sumaryczne punkty
        self.current_player = 1
        self.floating_tile = None 
        self.exchange_selected = []
        self.exchange_mode = False
        self.calc_text = ""
        self.game_over = False

    def draw_tiles(self, n):
        return [self.bag.pop() for _ in range(min(n, len(self.bag)))]

    def calculate_score(self):
        """Zlicza punkty z aktualnego ruchu na podstawie premii z ODS"""
        new_tiles = [(r, c, self.board_state[r][c]['letter']) 
                     for r in range(self.board_dim) for c in range(self.board_dim) 
                     if self.board_state[r][c] and self.board_state[r][c]['new']]
        
        if not new_tiles: return 0, ""
        
        points = 0
        word_multiplier = 1
        math_parts = []
        
        for r, c, letter in new_tiles:
            val = LETTERS[letter][1]
            prem = self.premium_map.get((r, c))
            
            if prem:
                type_p, mult, _ = prem
                if type_p == "L":
                    points += (val * mult)
                    math_parts.append(f"({val}x{mult}L)")
                elif type_p == "S":
                    points += val
                    word_multiplier *= mult
                    math_parts.append(str(val))
            else:
                points += val
                math_parts.append(str(val))
        
        total = points * word_multiplier
        math_str = " + ".join(math_parts)
        if word_multiplier > 1: math_str = f"({math_str}) x {word_multiplier}S"
        return total, f"{math_str} = {total}"

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # UI - Sumaryczne punkty w rogach (Zgodnie z prośbą)
        # Dolny lewy róg: Gracz 1
        p1_score_txt = self.font_ui.render(f"PUNKTY G1: {self.scores[1]}", True, (255, 255, 255))
        self.screen.blit(p1_score_txt, (50, SCREEN_HEIGHT - 60))
        
        # Dolny prawy róg: Gracz 2
        p2_score_txt = self.font_ui.render(f"PUNKTY G2: {self.scores[2]}", True, (255, 255, 255))
        self.screen.blit(p2_score_txt, (SCREEN_WIDTH - 220, SCREEN_HEIGHT - 60))

        # Obliczenia na górze
        if self.calc_text:
            txt = self.font_calc.render(self.calc_text, True, (255, 255, 0))
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 80))

        # Plansza (Dynamiczna)
        for r in range(self.board_dim):
            for c in range(self.board_dim):
                x, y = self.board_x + c * self.tile_size, self.board_y + r * self.tile_size
                rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
                
                prem = self.premium_map.get((r, c))
                color = prem[2] if prem else COLOR_BOARD
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, COLOR_GRID, rect, 1)
                
                if prem and not self.board_state[r][c]:
                    p_img = self.font_small.render(f"{prem[1]}{prem[0]}", True, (255,255,255))
                    self.screen.blit(p_img, (x + (self.tile_size//2 - p_img.get_width()//2), y + self.tile_size//3))

                tile = self.board_state[r][c]
                if tile:
                    self.draw_tile_obj(tile['letter'], x, y, (200, 255, 200) if tile['new'] else COLOR_TILE, self.tile_size)

        # Stojaki
        for i, l in enumerate(self.racks[1]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==1 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, 50, 200 + i*50, col, 42)
            
        for i, l in enumerate(self.racks[2]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==2 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, SCREEN_WIDTH - 92, 200 + i*50, col, 42)

        # Przyciski
        self.btn_ok = pygame.Rect(SCREEN_WIDTH//2 - 70, SCREEN_HEIGHT - 120, 140, 40)
        self.btn_ex = pygame.Rect(SCREEN_WIDTH//2 - 70, SCREEN_HEIGHT - 70, 140, 40)
        pygame.draw.rect(self.screen, (100,100,100), self.btn_ok)
        pygame.draw.rect(self.screen, (100,100,100), self.btn_ex)
        self.screen.blit(self.font_ui.render("ZATWIERDŹ", True, (255,255,255)), (self.btn_ok.x + 10, self.btn_ok.y + 8))
        self.screen.blit(self.font_ui.render("WYMIANA", True, (255,255,255)), (self.btn_ex.x + 22, self.btn_ex.y + 8))
        
        if self.floating_tile:
            mx, my = pygame.mouse.get_pos()
            self.draw_tile_obj(self.floating_tile, mx-20, my-20, (255, 255, 200), 42)

        pygame.display.flip()

    def draw_tile_obj(self, letter, x, y, color, size):
        rect = pygame.Rect(x, y, size-2, size-2)
        pygame.draw.rect(self.screen, color, rect, border_radius=4)
        pygame.draw.rect(self.screen, (0,0,0), rect, 1)
        self.screen.blit(self.font_tile.render(letter, True, COLOR_TEXT), (x + size//4, y + 2))
        self.screen.blit(self.font_small.render(str(LETTERS[letter][1]), True, COLOR_TEXT), (x + size - 12, y + size - 15))

    def handle_click(self, pos):
        self.calc_text = ""
        mx, my = pos

        if self.btn_ok.collidepoint(mx, my):
            self.confirm_move()
            return
        if self.btn_ex.collidepoint(mx, my):
            self.handle_exchange_btn()
            return

        # Kliknięcie w stojak
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

        # Plansza
        if self.board_x <= mx <= self.board_x + self.board_dim * self.tile_size:
            c = (mx - self.board_x) // self.tile_size
            r = (my - self.board_y) // self.tile_size
            if 0 <= r < self.board_dim and 0 <= c < self.board_dim:
                if self.floating_tile:
                    if not self.board_state[r][c]:
                        self.board_state[r][c] = {'letter': self.floating_tile, 'new': True}
                        self.floating_tile = None
                        if self.sounds.get(1): self.sounds[1].play()
                else:
                    if self.board_state[r][c] and self.board_state[r][c]['new']:
                        self.floating_tile = self.board_state[r][c]['letter']
                        self.board_state[r][c] = None

    def confirm_move(self):
        pts, math = self.calculate_score()
        if pts > 0:
            self.scores[self.current_player] += pts # Sumowanie punktów
            self.calc_text = math
            for r in range(self.board_dim):
                for c in range(self.board_dim):
                    if self.board_state[r][c]: self.board_state[r][c]['new'] = False
            
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
        clock = pygame.time.Clock()
        while not self.game_over:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
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
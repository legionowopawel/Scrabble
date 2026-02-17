import pygame
import sys
import random
import requests
import time
import re

# --- KOLORY ---
COLORS = {
    'bg': (34, 139, 34),
    'tile': (240, 230, 140),
    'text': (0, 0, 0),
    'white': (255, 255, 255),
    'button': (128, 0, 128),
    'panel': (180, 180, 220),
    'grid': (0, 80, 0)
}

LETTER_DATA = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 'D': (2, 3),
    'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 'H': (3, 2), 'I': (1, 8),
    'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5),
    'Ń': (7, 1), 'O': (1, 6), 'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4),
    'Ś': (5, 1), 'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5),
    'Ź': (9, 1), 'Ż': (5, 1)
}

class Tile:
    def __init__(self, letter):
        self.letter = letter
        self.points = LETTER_DATA[letter][0]
        self.rect = pygame.Rect(0, 0, 45, 45)
        self.on_board = False
        self.temp_placed = False
        self.last_click = 0

    def draw(self, surface, f_tile, f_pts):
        pygame.draw.rect(surface, COLORS['tile'], self.rect, border_radius=5)
        l_s = f_tile.render(self.letter, True, COLORS['text'])
        p_s = f_pts.render(str(self.points), True, COLORS['text'])
        surface.blit(l_s, l_s.get_rect(center=(self.rect.centerx, self.rect.centery-2)))
        surface.blit(p_s, (self.rect.right-12, self.rect.bottom-14))

class ScrabbleGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 850), pygame.RESIZABLE)
        self.grid = [[None for _ in range(15)] for _ in range(15)]
        self.bag = [l for l, d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7)]
        self.ai_rack = [self.bag.pop() for _ in range(7)]
        self.player_score = 0
        self.ai_score = 0
        self.turn = "PLAYER"
        self.first_move = True
        self.definition = "Czekam na słowo..."
        self.bonuses = self._init_bonuses()
        self.dragging = None
        self.update_assets()

    def _init_bonuses(self):
        b = {}
        # Zgodnie z dostarczonym zdjęciem
        tw5 = [(0,0), (0,14), (14,0), (14,14), (0,7), (7,0), (14,7), (7,14)]
        tw4 = [(0,4), (4,0), (14,4), (4,14), (0,10), (10,0), (14,10), (10,14)]
        tw3 = [(4,4), (4,10), (10,4), (10,10), (7,7)]
        for p in tw5: b[p] = ("5 WYRAZ", 5, "W")
        for p in tw4: b[p] = ("4 WYRAZ", 4, "W")
        for p in tw3: b[p] = ("3 WYRAZ", 3, "W")
        # Dodaj resztę tl2, tl3 itd. analogicznie
        return b

    def update_assets(self):
        h = self.screen.get_height()
        self.f_ui = pygame.font.SysFont('Arial', 24, bold=True)
        self.f_tile = pygame.font.SysFont('Arial', 28, bold=True)
        self.f_pts = pygame.font.SysFont('Arial', 14, bold=True)
        self.f_def = pygame.font.SysFont('Arial', 16, italic=True)
        self.cell_size = min(self.screen.get_width() // 22, h // 18)

    def get_online_data(self, word):
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=3)
            if "nie występuje w słowniku" in r.text: return None
            # Wyciąganie definicji z HTML
            parts = re.split(r'<(?:p|br)>', r.text)
            for p in parts:
                clean = re.sub('<[^<]+?>', '', p).strip()
                if len(clean) > 5 and not clean.startswith("dopuszczalne"):
                    return (clean[:50] + "...") if len(clean) > 50 else clean
            return "Brak opisu, ale słowo poprawne."
        except: return "Błąd sieci."

    def validate_and_score(self):
        temp = [(r, c) for r in range(15) for c in range(15) if self.grid[r][c] and self.grid[r][c].temp_placed]
        if not temp: return False
        
        # Zasada krzyżówki: Czy dotyka starych klocków?
        if not self.first_move:
            touching = False
            for r, c in temp:
                for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nr, nc = r+dr, c+dc
                    if 0<=nr<15 and 0<=nc<15 and self.grid[nr][nc] and not self.grid[nr][nc].temp_placed:
                        touching = True
            if not touching: return False

        # Sprawdź słownik
        word = self._extract_word(temp)
        definition = self.get_online_data(word)
        if definition is None: return False
        
        self.definition = f"{word}: {definition}"
        # Oblicz punkty z bonusami
        m = 1
        score = 0
        for r, c in temp:
            p = self.grid[r][c].points
            if (r,c) in self.bonuses:
                bonus = self.bonuses[(r,c)]
                if bonus[2] == "L": p *= bonus[1]
                else: m *= bonus[1]
            score += p
        
        self.player_score += (score * m)
        for r, c in temp: self.grid[r][c].temp_placed = False
        return True

    def _extract_word(self, temp):
        temp.sort()
        r0, c0 = temp[0]
        word = ""
        if all(p[0] == r0 for p in temp): # Horiz
            c = c0
            while c > 0 and self.grid[r0][c-1]: c -= 1
            while c < 15 and self.grid[r0][c]:
                word += self.grid[r0][c].letter; c += 1
        else: # Vert
            r = r0
            while r > 0 and self.grid[r-1][c0]: r -= 1
            while r < 15 and self.grid[r][c0]:
                word += self.grid[r][c0].letter; r += 1
        return word

    def draw(self):
        self.screen.fill(COLORS['bg'])
        ox, oy = 30, (self.screen.get_height() - (15 * self.cell_size)) // 2
        
        # Rysowanie planszy i bonusów
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*self.cell_size, oy + r*self.cell_size, self.cell_size, self.cell_size)
                pygame.draw.rect(self.screen, COLORS['grid'], rect, 1)
                if (r,c) in self.bonuses:
                    txt = self.f_def.render(self.bonuses[(r,c)][0], True, COLORS['text'])
                    self.screen.blit(txt, txt.get_rect(center=rect.center))
                if self.grid[r][c]:
                    self.grid[r][c].rect = rect.inflate(-4,-4)
                    self.grid[r][c].draw(self.screen, self.f_tile, self.f_pts)

        # Panel definicji (Prawy dolny róg)
        ui_x = ox + 15*self.cell_size + 20
        def_r = pygame.Rect(ui_x, self.screen.get_height()-120, 250, 80)
        pygame.draw.rect(self.screen, COLORS['panel'], def_r, border_radius=10)
        self.screen.blit(self.f_def.render(self.definition[:40], True, COLORS['text']), (ui_x+5, self.screen.get_height()-110))
        if len(self.definition) > 40:
             self.screen.blit(self.f_def.render(self.definition[40:80], True, COLORS['text']), (ui_x+5, self.screen.get_height()-90))

        # Przyciski
        self.btn_ok = pygame.Rect(ui_x, 300, 100, 50)
        pygame.draw.rect(self.screen, COLORS['button'], self.btn_ok, border_radius=5)
        self.screen.blit(self.f_ui.render("OK", True, COLORS['white']), (ui_x+30, 310))
        
        # Stojak
        for i, t in enumerate([t for t in self.player_rack if not t.on_board]):
            t.rect = pygame.Rect(ox + i*50, self.screen.get_height()-60, 45, 45)
            t.draw(self.screen, self.f_tile, self.f_pts)

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: pygame.quit(); sys.exit()
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.btn_ok.collidepoint(e.pos):
                        if self.validate_and_score():
                            self.first_move = False
                            # Dobieranie klocków
                            self.player_rack = [t for t in self.player_rack if t.on_board is False]
                            while len(self.player_rack) < 7 and self.bag:
                                self.player_rack.append(Tile(self.bag.pop()))
                            self.turn = "AI" # Tu można dodać ai_move()
                    # Przeciąganie i 2-klik (powrót na stojak)
                    for t in self.player_rack:
                        if t.rect.collidepoint(e.pos):
                            if pygame.time.get_ticks() - t.last_click < 300 and t.on_board:
                                t.on_board = False; t.temp_placed = False
                                # Znajdź w siatce i usuń
                                for r in range(15):
                                    for c in range(15):
                                        if self.grid[r][c] == t: self.grid[r][c] = None
                            else:
                                t.last_click = pygame.time.get_ticks()
                                self.dragging = t
                if e.type == pygame.MOUSEBUTTONUP and self.dragging:
                    ox, oy = 30, (self.screen.get_height() - (15 * self.cell_size)) // 2
                    c, r = (e.pos[0]-ox)//self.cell_size, (e.pos[1]-oy)//self.cell_size
                    if 0<=r<15 and 0<=c<15 and not self.grid[r][c]:
                        self.grid[r][c] = self.dragging
                        self.dragging.on_board = True
                        self.dragging.temp_placed = True
                    self.dragging = None
            self.draw(); pygame.display.flip()

if __name__ == "__main__":
    ScrabbleGame().run()
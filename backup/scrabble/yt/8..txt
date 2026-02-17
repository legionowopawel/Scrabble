import pygame
import sys
import random
import requests
import time
import re

# --- KONFIGURACJA KOLORÓW I PARAMETRÓW ---
COLORS = {
    'bg_green': (34, 139, 34),
    'board_dark': (0, 90, 0),
    'grid_line': (0, 70, 0),
    'tile': (240, 230, 140),
    'tile_border': (184, 134, 11),
    'text_black': (0, 0, 0),
    'white': (255, 255, 255),
    'button_purple': (128, 0, 128),
    'ui_panel': (180, 180, 220)
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
        self.is_dragging = False
        self.last_click_time = 0

    def draw(self, surface, font_tile, font_pts):
        pygame.draw.rect(surface, COLORS['tile'], self.rect, border_radius=5)
        pygame.draw.rect(surface, COLORS['tile_border'], self.rect, 2, border_radius=5)
        l_surf = font_tile.render(self.letter, True, COLORS['text_black'])
        p_surf = font_pts.render(str(self.points), True, COLORS['text_black'])
        surface.blit(l_surf, l_surf.get_rect(center=(self.rect.centerx, self.rect.centery-2)))
        surface.blit(p_surf, (self.rect.right - 12, self.rect.bottom - 14))

class ScrabbleEngine:
    def __init__(self):
        self.grid = [[None for _ in range(15)] for _ in range(15)]
        self.bag = [l for l, d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7)]
        self.ai_rack = [self.bag.pop() for _ in range(7)]
        self.player_score = 0
        self.ai_score = 0
        self.turn = "PLAYER"
        self.last_definition = "Brak słowa"
        self.bonuses = self._init_bonuses_from_image()

    def _init_bonuses_from_image(self):
        b = {}
        # Mapowanie zgodne ze zdjęciem (5x, 4x, 3x, 2x wyraz/litera)
        tw5 = [(0,0), (0,14), (14,0), (14,14), (0,7), (7,0), (14,7), (7,14)]
        tw4 = [(0,4), (4,0), (14,4), (4,14), (0,10), (10,0), (14,10), (10,14)]
        tw3 = [(4,4), (4,10), (10,4), (10,10), (7,7)]
        tw2 = [(3,3), (3,11), (11,3), (11,11), (5,5), (5,9), (9,5), (9,9)]
        
        tl5 = [(1,1), (1,13), (13,1), (13,13), (3,7), (7,3), (11,7), (7,11)]
        tl4 = [(2,2), (2,12), (12,2), (12,12), (6,6), (6,8), (8,6), (8,8)]
        tl3 = [(5,1), (1,5), (5,13), (13,5), (9,1), (1,9), (9,13), (13,9)]
        tl2 = [(2,6), (6,2), (2,8), (8,2), (12,6), (6,12), (12,8), (8,12)]

        for p in tw5: b[p] = ("5 WYRAZ", 5, "W")
        for p in tw4: b[p] = ("4 WYRAZ", 4, "W")
        for p in tw3: b[p] = ("3 WYRAZ", 3, "W")
        for p in tw2: b[p] = ("2 WYRAZ", 2, "W")
        for p in tl5: b[p] = ("5 LITERA", 5, "L")
        for p in tl4: b[p] = ("4 LITERA", 4, "L")
        for p in tl3: b[p] = ("3 LITERA", 3, "L")
        for p in tl2: b[p] = ("2 LITERA", 2, "L")
        return b

    def get_definition(self, word):
        if not word: return "Brak słowa"
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=3)
            # Wyciąganie pierwszej definicji (tekst po flagach dopuszczalności)
            clean = re.sub('<[^<]+?>', '', r.text)
            match = re.search(r"dopuszczalne w grach(.*?)komentarze", clean, re.DOTALL)
            if match:
                res = match.group(1).strip()
                return (res[:50] + '...') if len(res) > 50 else res
            return "Nie znaleziono definicji."
        except: return "Błąd połączenia."

class ScrabmaniaApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1100, 850), pygame.RESIZABLE)
        pygame.display.set_caption("Scrabmania Pro - Definition System")
        self.engine = ScrabbleEngine()
        self.dragging_tile = None
        self.update_assets()

    def update_assets(self):
        h = self.screen.get_height()
        self.font_ui = pygame.font.SysFont('Arial', 24, bold=True)
        self.font_tile = pygame.font.SysFont('Arial', 28, bold=True)
        self.font_pts = pygame.font.SysFont('Arial', 14, bold=True)
        self.font_bonus = pygame.font.SysFont('Arial', 11, bold=True)
        self.font_def = pygame.font.SysFont('Arial', 16, italic=True)
        self.cell_size = min(self.screen.get_width() // 22, h // 18)

    def calculate_score(self, placed_tiles):
        word_multiplier = 1
        base_score = 0
        for r, c in placed_tiles:
            tile = self.engine.grid[r][c]
            points = tile.points
            bonus = self.engine.bonuses.get((r,c))
            if bonus:
                name, val, type = bonus
                if type == "L": points *= val
                elif type == "W": word_multiplier *= val
            base_score += points
        return base_score * word_multiplier

    def confirm_move(self):
        placed = [(r, c) for r in range(15) for c in range(15) if self.engine.grid[r][c] and self.engine.grid[r][c].temp_placed]
        if not placed: return

        # Składanie słowa
        placed.sort()
        word = ""
        r0, c0 = placed[0]
        is_horiz = all(p[0] == r0 for p in placed)
        if is_horiz:
            c = c0
            while c > 0 and self.engine.grid[r0][c-1]: c -= 1
            while c < 15 and self.engine.grid[r0][c]:
                word += self.engine.grid[r0][c].letter
                c += 1
        else:
            r = r0
            while r > 0 and self.engine.grid[r-1][c0]: r -= 1
            while r < 15 and self.engine.grid[r][c0]:
                word += self.engine.grid[r][c0].letter
                r += 1

        self.engine.last_definition = f"{word}: " + self.engine.get_definition(word)
        self.engine.player_score += self.calculate_score(placed)
        
        for r, c in placed:
            t = self.engine.grid[r][c]
            t.temp_placed = False
            if t in self.engine.player_rack: self.engine.player_rack.remove(t)
        
        while len(self.engine.player_rack) < 7 and self.engine.bag:
            self.engine.player_rack.append(Tile(self.engine.bag.pop()))
        
        self.engine.turn = "AI"
        self.ai_move()

    def ai_move(self):
        time.sleep(1)
        # Uproszczone AI kładące słowo "ASA" (jako przykład)
        ai_word = "ASA"
        for i, char in enumerate(ai_word):
            t = Tile(char)
            t.on_board = True
            self.engine.grid[14][i+5] = t # Kładzie na dole
        
        self.engine.ai_score += 5 # ryczałt
        self.engine.last_definition = f"AI ({ai_word}): " + self.engine.get_definition(ai_word)
        self.engine.turn = "PLAYER"

    def draw(self):
        self.screen.fill(COLORS['bg_green'])
        ox, oy = 30, (self.screen.get_height() - (15 * self.cell_size)) // 2
        
        # Plansza
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*self.cell_size, oy + r*self.cell_size, self.cell_size, self.cell_size)
                pygame.draw.rect(self.screen, COLORS['board_dark'], rect)
                pygame.draw.rect(self.screen, COLORS['grid_line'], rect, 1)
                
                bonus = self.engine.bonuses.get((r,c))
                if bonus and not self.engine.grid[r][c]:
                    txt = self.font_bonus.render(bonus[0], True, COLORS['text_black'])
                    self.screen.blit(txt, txt.get_rect(center=rect.center))

                if self.engine.grid[r][c] and not self.engine.grid[r][c].is_dragging:
                    self.engine.grid[r][c].rect = pygame.Rect(rect.x+2, rect.y+2, self.cell_size-4, self.cell_size-4)
                    self.engine.grid[r][c].draw(self.screen, self.font_tile, self.font_pts)

        # UI i Słownik
        ui_x = ox + 15*self.cell_size + 30
        self.screen.blit(self.font_ui.render(f"TY: {self.engine.player_score}", True, COLORS['text_black']), (ui_x, 50))
        self.screen.blit(self.font_ui.render(f"AI: {self.engine.ai_score}", True, COLORS['text_black']), (ui_x, 100))
        
        # Definicja w prawym dolnym rogu
        def_rect = pygame.Rect(ui_x, self.screen.get_height() - 150, 300, 100)
        pygame.draw.rect(self.screen, COLORS['ui_panel'], def_rect, border_radius=10)
        def_label = self.font_ui.render("Definicja:", True, COLORS['text_black'])
        self.screen.blit(def_label, (ui_x + 10, self.screen.get_height() - 140))
        
        # Zawijanie tekstu definicji
        def_text = self.engine.last_definition
        wrapped = [def_text[i:i+35] for i in range(0, len(def_text), 35)]
        for i, line in enumerate(wrapped[:3]):
            t = self.font_def.render(line, True, COLORS['text_black'])
            self.screen.blit(t, (ui_x + 10, self.screen.get_height() - 110 + i*20))

        # Przyciski i stojak (pominięte dla zwięzłości, identyczne jak w poprzednich wersjach)
        self.ok_btn = pygame.Rect(ui_x, 250, 140, 50)
        pygame.draw.rect(self.screen, COLORS['button_purple'], self.ok_btn, border_radius=10)
        self.screen.blit(self.font_ui.render("OK!", True, COLORS['white']), (ui_x + 45, 260))

        # Stojak
        rack_y = self.screen.get_height() - self.cell_size - 20
        for i, t in enumerate(self.engine.player_rack):
            if not t.on_board and not t.is_dragging:
                t.rect = pygame.Rect(ox + i*(self.cell_size+10), rack_y, self.cell_size, self.cell_size)
                t.draw(self.screen, self.font_tile, self.font_pts)

        if self.dragging_tile: self.dragging_tile.draw(self.screen, self.font_tile, self.font_pts)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.update_assets()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.ok_btn.collidepoint(event.pos): self.confirm_move()
                    for t in self.engine.player_rack:
                        if not t.on_board and t.rect.collidepoint(event.pos):
                            self.dragging_tile = t; t.is_dragging = True
                if event.type == pygame.MOUSEBUTTONUP and self.dragging_tile:
                    ox, oy = 30, (self.screen.get_height() - (15 * self.cell_size)) // 2
                    c, r = (event.pos[0]-ox)//self.cell_size, (event.pos[1]-oy)//self.cell_size
                    if 0<=r<15 and 0<=c<15 and not self.engine.grid[r][c]:
                        self.engine.grid[r][c] = self.dragging_tile
                        self.dragging_tile.on_board = True; self.dragging_tile.temp_placed = True
                    self.dragging_tile.is_dragging = False; self.dragging_tile = None
                if event.type == pygame.MOUSEMOTION and self.dragging_tile:
                    self.dragging_tile.rect.center = event.pos
            self.draw(); pygame.display.flip()

if __name__ == "__main__":
    ScrabmaniaApp().run()
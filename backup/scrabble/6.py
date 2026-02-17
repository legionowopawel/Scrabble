import pygame
import sys
import random
import requests
import time

# --- KONFIGURACJA GRAFICZNA ---
COLORS = {
    'bg': (34, 139, 34),          # Zielone tło
    'board_dark': (0, 80, 0),     # Ciemnozielone pola
    'tile': (240, 230, 140),      # Żółty klocek
    'tile_border': (184, 134, 11),
    'text': (0, 0, 0),            # Wszystkie napisy CZARNE
    'white': (255, 255, 255),
    'button': (128, 0, 128),
    'grid': (0, 60, 0)
}

LETTER_VALUES = {
    'A': 1, 'Ą': 5, 'B': 3, 'C': 2, 'Ć': 6, 'D': 2, 'E': 1, 'Ę': 5, 'F': 5, 'G': 2, 'H': 3, 
    'I': 1, 'J': 3, 'K': 2, 'L': 2, 'Ł': 3, 'M': 2, 'N': 1, 'Ń': 7, 'O': 1, 'Ó': 5, 'P': 2, 
    'R': 1, 'S': 1, 'Ś': 5, 'T': 2, 'U': 3, 'W': 1, 'Y': 2, 'Z': 1, 'Ź': 9, 'Ż': 5
}

# Pełna dystrybucja liter (100 klocków)
BAG_DISTRIBUTION = {
    'A': 9, 'Ą': 1, 'B': 2, 'C': 3, 'Ć': 1, 'D': 3, 'E': 7, 'Ę': 1, 'F': 1, 'G': 2, 'H': 2,
    'I': 8, 'J': 2, 'K': 3, 'L': 3, 'Ł': 2, 'M': 3, 'N': 5, 'Ń': 1, 'O': 6, 'Ó': 1, 'P': 3,
    'R': 4, 'S': 4, 'Ś': 1, 'T': 3, 'U': 2, 'W': 4, 'Y': 4, 'Z': 5, 'Ź': 1, 'Ż': 1
}

class Tile:
    def __init__(self, letter):
        self.letter = letter
        self.points = LETTER_VALUES[letter]
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_dragging = False
        self.on_board = False
        self.temp_on_board = False # Czy położony w bieżącej turze
        self.last_click = 0

    def draw(self, surface, size, font_big, font_small):
        pygame.draw.rect(surface, COLORS['tile'], self.rect, border_radius=4)
        pygame.draw.rect(surface, COLORS['tile_border'], self.rect, 2, border_radius=4)
        
        l_surf = font_big.render(self.letter, True, COLORS['text'])
        p_surf = font_small.render(str(self.points), True, COLORS['text'])
        
        surface.blit(l_surf, l_surf.get_rect(center=(self.rect.centerx, self.rect.centery-2)))
        surface.blit(p_surf, (self.rect.right-size//4, self.rect.bottom-size//3))

class ScrabbleEngine:
    def __init__(self):
        self.grid = [[None for _ in range(15)] for _ in range(15)]
        self.bag = [l for l, count in BAG_DISTRIBUTION.items() for _ in range(count)]
        random.shuffle(self.bag)
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7)]
        self.ai_rack = [self.bag.pop() for _ in range(7)]
        self.player_score = 0
        self.ai_score = 0
        self.first_move = True
        self.turn = "PLAYER"
        self.bonuses = self._init_bonuses()

    def _init_bonuses(self):
        b = {}
        tw = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        dw = [(1,1), (2,2), (3,3), (4,4), (13,13), (12,12), (11,11), (10,10), (7,7)]
        for p in tw: b[p] = "3 WYRAZ"
        for p in dw: b[p] = "2 WYRAZ"
        return b

    def validate_word_online(self, word):
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=2)
            return "dopuszczalne w grach" in r.text
        except: return True # Fail-safe

    def get_placed_tiles_this_turn(self):
        return [(r, c) for r in range(15) for c in range(15) 
                if self.grid[r][c] and self.grid[r][c].temp_on_board]

    def check_rules(self):
        placed = self.get_placed_tiles_this_turn()
        if not placed: return False
        
        # 1. Pierwszy ruch przez środek
        if self.first_move:
            if (7, 7) not in placed: return False
            
        # 2. Sprawdzenie czy w jednej linii
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) > 1 and len(cols) > 1: return False
        
        # 3. Sprawdzenie czy styka się z innymi (jeśli nie pierwszy ruch)
        if not self.first_move:
            touching = False
            for r, c in placed:
                for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nr, nc = r+dr, c+dc
                    if 0<=nr<15 and 0<=nc<15 and self.grid[nr][nc] and not self.grid[nr][nc].temp_on_board:
                        touching = True
            if not touching: return False
            
        return True

class ScrabmaniaApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1100, 800), pygame.RESIZABLE)
        pygame.display.set_caption("Scrabmania Pro v1.0")
        self.engine = ScrabbleEngine()
        self.dragging_tile = None
        self.clock = pygame.time.Clock()
        self.update_fonts()

    def update_fonts(self):
        h = self.screen.get_height()
        self.font_main = pygame.font.SysFont('Arial', h // 25, bold=True)
        self.font_tile = pygame.font.SysFont('Arial', h // 35, bold=True)
        self.font_pts = pygame.font.SysFont('Arial', h // 60, bold=True)
        self.font_bonus = pygame.font.SysFont('Arial', h // 75, bold=True)

    def get_layout(self):
        w, h = self.screen.get_size()
        c_size = min(w // 20, h // 18)
        ox = 40
        oy = (h - (15 * c_size)) // 2
        return ox, oy, c_size

    def draw(self):
        self.screen.fill(COLORS['bg'])
        ox, oy, cs = self.get_layout()
        
        # Plansza
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*cs, oy + r*cs, cs, cs)
                pygame.draw.rect(self.screen, COLORS['board_dark'], rect)
                pygame.draw.rect(self.screen, COLORS['grid'], rect, 1)
                
                bonus = self.engine.bonuses.get((r,c))
                if bonus and not self.engine.grid[r][c]:
                    txt = self.font_bonus.render(bonus, True, COLORS['text'])
                    self.screen.blit(txt, txt.get_rect(center=rect.center))

                tile = self.engine.grid[r][c]
                if tile and not tile.is_dragging:
                    tile.rect = pygame.Rect(rect.x+2, rect.y+2, cs-4, cs-4)
                    tile.draw(self.screen, cs, self.font_tile, self.font_pts)

        # Stojak
        rack_y = self.screen.get_height() - cs - 20
        for i, tile in enumerate(self.engine.player_rack):
            if not tile.on_board and not tile.is_dragging:
                tile.rect = pygame.Rect(ox + i*(cs+10), rack_y, cs, cs)
                tile.draw(self.screen, cs, self.font_tile, self.font_pts)

        # UI
        ui_x = ox + 15*cs + 40
        self.screen.blit(self.font_main.render(f"PUNKTY: {self.engine.player_score}", True, COLORS['text']), (ui_x, 100))
        self.screen.blit(self.font_main.render(f"AI: {self.engine.ai_score}", True, COLORS['text']), (ui_x, 160))
        
        self.btn_ok = pygame.Rect(ui_x, 300, 150, 60)
        pygame.draw.rect(self.screen, COLORS['button'], self.btn_ok, border_radius=10)
        self.screen.blit(self.font_main.render("ZATWIERDŹ", True, COLORS['white']), (ui_x+10, 310))

        if self.dragging_tile:
            self.dragging_tile.draw(self.screen, cs, self.font_tile, self.font_pts)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                self.update_fonts()
            
            if self.engine.turn == "PLAYER":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = event.pos
                    now = pygame.time.get_ticks()
                    ox, oy, cs = self.get_layout()

                    # 2-klik powrót
                    col, row = (pos[0]-ox)//cs, (pos[1]-oy)//cs
                    if 0<=row<15 and 0<=col<15:
                        t = self.engine.grid[row][col]
                        if t and t.temp_on_board:
                            if now - t.last_click < 400:
                                t.on_board = False
                                t.temp_on_board = False
                                self.engine.grid[row][col] = None
                                return
                            t.last_click = now

                    # Chwytanie
                    for t in self.engine.player_rack:
                        if not t.on_board and t.rect.collidepoint(pos):
                            self.dragging_tile = t
                            t.is_dragging = True
                    
                    if self.btn_ok.collidepoint(pos):
                        self.confirm_move()

                if event.type == pygame.MOUSEBUTTONUP:
                    if self.dragging_tile:
                        ox, oy, cs = self.get_layout()
                        c, r = (event.pos[0]-ox)//cs, (event.pos[1]-oy)//cs
                        if 0<=r<15 and 0<=c<15 and not self.engine.grid[r][c]:
                            self.engine.grid[r][c] = self.dragging_tile
                            self.dragging_tile.on_board = True
                            self.dragging_tile.temp_on_board = True
                        self.dragging_tile.is_dragging = False
                        self.dragging_tile = None

                if event.type == pygame.MOUSEMOTION and self.dragging_tile:
                    self.dragging_tile.rect.center = event.pos
        return True

    def confirm_move(self):
        if self.engine.check_rules():
            placed = self.engine.get_placed_tiles_this_turn()
            turn_score = 0
            for r, c in placed:
                t = self.engine.grid[r][c]
                t.temp_on_board = False
                turn_score += t.points
                self.engine.player_rack.remove(t)
            
            self.engine.player_score += turn_score
            self.engine.first_move = False
            while len(self.engine.player_rack) < 7 and self.engine.bag:
                self.engine.player_rack.append(Tile(self.engine.bag.pop()))
            self.engine.turn = "AI"
            self.ai_move()

    def ai_move(self):
        # AI kładzie jedną literę obok istniejącej dla płynności gry
        time.sleep(0.5)
        placed = False
        for r in range(15):
            for c in range(15):
                if self.engine.grid[r][c] and not placed:
                    for dr, dc in [(0,1),(1,0)]:
                        nr, nc = r+dr, c+dc
                        if 0<=nr<15 and 0<=nc<15 and not self.engine.grid[nr][nc]:
                            if self.engine.ai_rack:
                                let = self.engine.ai_rack.pop(0)
                                new_t = Tile(let)
                                new_t.on_board = True
                                self.engine.grid[nr][nc] = new_t
                                self.engine.ai_score += new_t.points
                                if self.engine.bag: self.engine.ai_rack.append(self.engine.bag.pop())
                                placed = True
                                break
            if placed: break
        self.engine.turn = "PLAYER"

    def run(self):
        while self.handle_events():
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    ScrabmaniaApp().run()
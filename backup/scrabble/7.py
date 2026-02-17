import pygame
import sys
import random
import requests
import time

# --- KONFIGURACJA KOLORÓW ---
COLORS = {
    'bg_green': (34, 139, 34),
    'board_dark': (0, 100, 0),
    'grid_line': (0, 70, 0),
    'tile': (240, 230, 140),
    'tile_border': (184, 134, 11),
    'text_black': (0, 0, 0),
    'white': (255, 255, 255),
    'button_purple': (128, 0, 128),
    'error_red': (255, 0, 0)
}

# Polskie litery: (Wartość punktowa, Ilość w worku)
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
        self.is_dragging = False
        self.on_board = False
        self.temp_placed = False # Czy położony w TEJ turze
        self.last_click_time = 0

    def draw(self, surface, font_tile, font_pts):
        pygame.draw.rect(surface, COLORS['tile'], self.rect, border_radius=5)
        pygame.draw.rect(surface, COLORS['tile_border'], self.rect, 2, border_radius=5)
        
        # Litery i punkty zawsze CZARNE
        l_surf = font_tile.render(self.letter, True, COLORS['text_black'])
        p_surf = font_pts.render(str(self.points), True, COLORS['text_black'])
        
        l_rect = l_surf.get_rect(center=(self.rect.centerx, self.rect.centery-2))
        surface.blit(l_surf, l_rect)
        surface.blit(p_surf, (self.rect.right - 14, self.rect.bottom - 15))

class ScrabmaniaGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 800), pygame.RESIZABLE)
        pygame.display.set_caption("Scrabmania Pro v1.0")
        
        self.grid = [[None for _ in range(15)] for _ in range(15)]
        self.bag = [l for l, d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7) if self.bag]
        self.ai_rack = [self.bag.pop() for _ in range(7) if self.bag]
        
        self.player_score = 0
        self.ai_score = 0
        self.turn = "PLAYER"
        self.first_move = True
        self.dragging_tile = None
        self.msg = ""
        self.msg_time = 0
        
        self.bonuses = self._init_bonuses()
        self.update_assets()

    def _init_bonuses(self):
        b = {}
        tw = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        dw = [(1,1), (2,2), (3,3), (4,4), (7,7), (10,10), (11,11), (12,12), (13,13)]
        for p in tw: b[p] = "3 WYRAZ"
        for p in dw: b[p] = "2 WYRAZ"
        return b

    def update_assets(self):
        h = self.screen.get_height()
        self.font_ui = pygame.font.SysFont('Arial', h // 25, bold=True)
        self.font_tile = pygame.font.SysFont('Arial', h // 30, bold=True)
        self.font_pts = pygame.font.SysFont('Arial', h // 60, bold=True)
        self.font_bonus = pygame.font.SysFont('Arial', h // 80, bold=True)
        self.cell_size = min(self.screen.get_width() // 22, h // 18)

    def validate_sjp(self, word):
        if len(word) < 2: return False
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=2)
            return "dopuszczalne w grach" in r.text
        except: return True

    def get_full_word(self):
        # Pobiera litery położone w tej turze
        placed = [(r, c) for r in range(15) for c in range(15) if self.grid[r][c] and self.grid[r][c].temp_placed]
        if not placed: return ""
        placed.sort()
        
        r_start, c_start = placed[0]
        word = ""
        # Kierunek (H lub V)
        is_horizontal = all(p[0] == r_start for p in placed)
        
        if is_horizontal:
            # Znajdź faktyczny początek (mogą być litery przed nowym słowem)
            c = c_start
            while c > 0 and self.grid[r_start][c-1]: c -= 1
            while c < 15 and self.grid[r_start][c]:
                word += self.grid[r_start][c].letter
                c += 1
        else:
            r = r_start
            while r > 0 and self.grid[r-1][c_start]: r -= 1
            while r < 15 and self.grid[r][c_start]:
                word += self.grid[r][c_start].letter
                r += 1
        return word

    def check_placement_rules(self):
        placed = [(r, c) for r in range(15) for c in range(15) if self.grid[r][c] and self.grid[r][c].temp_placed]
        if not placed: return False
        if self.first_move and (7, 7) not in placed: 
            self.show_msg("Pierwszy ruch musi być przez środek!")
            return False
        
        rows, cols = set(p[0] for p in placed), set(p[1] for p in placed)
        if len(rows) > 1 and len(cols) > 1:
            self.show_msg("Litery muszą być w jednej linii!")
            return False
        
        if not self.first_move:
            has_contact = False
            for r, c in placed:
                for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nr, nc = r+dr, c+dc
                    if 0<=nr<15 and 0<=nc<15 and self.grid[nr][nc] and not self.grid[nr][nc].temp_placed:
                        has_contact = True
            if not has_contact:
                self.show_msg("Słowo musi stykać się z innymi!")
                return False
        return True

    def show_msg(self, text):
        self.msg = text
        self.msg_time = pygame.time.get_ticks()

    def confirm_move(self):
        if not self.check_placement_rules(): return
        
        word = self.get_full_word()
        if self.validate_sjp(word):
            score = 0
            to_remove = []
            for r in range(15):
                for c in range(15):
                    t = self.grid[r][c]
                    if t and t.temp_placed:
                        score += t.points
                        t.temp_placed = False
                        to_remove.append(t)
            
            self.player_score += score
            self.first_move = False
            for t in to_remove: self.player_rack.remove(t)
            while len(self.player_rack) < 7 and self.bag:
                self.player_rack.append(Tile(self.bag.pop()))
            
            self.turn = "AI"
        else:
            self.show_msg(f"Słowo '{word}' jest niedopuszczalne!")

    def ai_move(self):
        time.sleep(1) # AI "myśli"
        # Prosta logika AI: szuka wolnego miejsca obok klocka i kładzie literę
        done = False
        for r in range(15):
            for c in range(15):
                if self.grid[r][c] and not done:
                    for dr, dc in [(0,1),(1,0),(0,-1),(-1,0)]:
                        nr, nc = r+dr, c+dc
                        if 0<=nr<15 and 0<=nc<15 and not self.grid[nr][nc] and self.ai_rack:
                            let = self.ai_rack.pop(0)
                            tile = Tile(let)
                            tile.on_board = True
                            self.grid[nr][nc] = tile
                            self.ai_score += tile.points
                            if self.bag: self.ai_rack.append(self.bag.pop())
                            done = True
                            break
        self.turn = "PLAYER"

    def draw(self):
        self.screen.fill(COLORS['bg_green'])
        ox = 40
        oy = (self.screen.get_height() - (15 * self.cell_size)) // 2
        
        # Plansza
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*self.cell_size, oy + r*self.cell_size, self.cell_size, self.cell_size)
                pygame.draw.rect(self.screen, COLORS['board_dark'], rect)
                pygame.draw.rect(self.screen, COLORS['grid_line'], rect, 1)
                
                bonus = self.bonuses.get((r, c))
                if bonus and not self.grid[r][c]:
                    b_surf = self.font_bonus.render(bonus, True, COLORS['text_black'])
                    self.screen.blit(b_surf, b_surf.get_rect(center=rect.center))

                if self.grid[r][c] and not self.grid[r][c].is_dragging:
                    self.grid[r][c].rect.topleft = (rect.x + 2, rect.y + 2)
                    self.grid[r][c].rect.size = (self.cell_size-4, self.cell_size-4)
                    self.grid[r][c].draw(self.screen, self.font_tile, self.font_pts)

        # UI
        ui_x = ox + (15 * self.cell_size) + 40
        self.screen.blit(self.font_ui.render(f"TY: {self.player_score}", True, COLORS['text_black']), (ui_x, 100))
        self.screen.blit(self.font_ui.render(f"KOMPUTER: {self.ai_score}", True, COLORS['text_black']), (ui_x, 160))
        self.screen.blit(self.font_ui.render(f"WOREK: {len(self.bag)}", True, COLORS['text_black']), (ui_x, 220))
        
        self.ok_btn = pygame.Rect(ui_x, 350, 160, 60)
        pygame.draw.rect(self.screen, COLORS['button_purple'], self.ok_btn, border_radius=10)
        self.screen.blit(self.font_ui.render("Zatwierdź", True, COLORS['white']), (ui_x + 15, 360))

        # Komunikat błędu
        if pygame.time.get_ticks() - self.msg_time < 3000:
            err = self.font_ui.render(self.msg, True, COLORS['error_red'])
            self.screen.blit(err, (ox, 10))

        # Stojak
        rack_y = self.screen.get_height() - self.cell_size - 30
        for i, tile in enumerate(self.player_rack):
            if not tile.on_board and not tile.is_dragging:
                tile.rect.topleft = (ox + i*(self.cell_size+10), rack_y)
                tile.rect.size = (self.cell_size, self.cell_size)
                tile.draw(self.screen, self.font_tile, self.font_pts)

        if self.dragging_tile:
            self.dragging_tile.draw(self.screen, self.font_tile, self.font_pts)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.update_assets()
                
                if self.turn == "PLAYER":
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        now = pygame.time.get_ticks()
                        # Obsługa 2-kliku (powrót na stojak)
                        ox, oy = 40, (self.screen.get_height() - (15 * self.cell_size)) // 2
                        c, r = (event.pos[0]-ox)//self.cell_size, (event.pos[1]-oy)//self.cell_size
                        if 0<=r<15 and 0<=c<15 and self.grid[r][c] and self.grid[r][c].temp_placed:
                            if now - self.grid[r][c].last_click_time < 300:
                                self.grid[r][c].on_board = False
                                self.grid[r][c].temp_placed = False
                                self.grid[r][c] = None
                                continue
                            self.grid[r][c].last_click_time = now

                        for tile in self.player_rack:
                            if not tile.on_board and tile.rect.collidepoint(event.pos):
                                self.dragging_tile = tile
                                tile.is_dragging = True
                        
                        if self.ok_btn.collidepoint(event.pos):
                            self.confirm_move()

                    if event.type == pygame.MOUSEBUTTONUP and self.dragging_tile:
                        ox, oy = 40, (self.screen.get_height() - (15 * self.cell_size)) // 2
                        c, r = (event.pos[0]-ox)//self.cell_size, (event.pos[1]-oy)//self.cell_size
                        if 0<=r<15 and 0<=c<15 and not self.grid[r][c]:
                            self.grid[r][c] = self.dragging_tile
                            self.dragging_tile.on_board = True
                            self.dragging_tile.temp_placed = True
                        self.dragging_tile.is_dragging = False
                        self.dragging_tile = None

                    if event.type == pygame.MOUSEMOTION and self.dragging_tile:
                        self.dragging_tile.rect.center = event.pos

            if self.turn == "AI":
                self.draw(); pygame.display.flip()
                self.ai_move()

            self.draw()
            pygame.display.flip()

if __name__ == "__main__":
    ScrabmaniaGame().run()
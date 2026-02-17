# scrabble.py
import pygame
import sys
import random
import requests
import time

# --- KONFIGURACJA I ZASOBY ---
pygame.init()
pygame.display.set_caption("Scrabmania Edu - Scrabble edukacyjne")

# Kolory
COLORS = {
    'bg': (34, 139, 34),
    'board': (0, 100, 0),
    'grid': (0, 60, 0),
    'tile': (240, 230, 140),
    'tile_border': (140, 100, 20),
    'text': (0, 0, 0),
    'button': (128, 0, 128),
    'panel': (230, 230, 240)
}

# Litery: (punkty, liczba)
LETTER_DATA = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 'D': (2, 3),
    'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 'H': (3, 2), 'I': (1, 8),
    'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5),
    'Ń': (7, 1), 'O': (1, 6), 'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4),
    'Ś': (5, 1), 'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5),
    'Ź': (9, 1), 'Ż': (5, 1)
}

# Rozkład bonusów: (opis, wartość, typ 'L' litera / 'W' wyraz)
def default_bonuses():
    b = {}
    # przykładowe rozmieszczenie (możesz rozszerzyć)
    tw = [(0,0),(0,7),(0,14),(7,0),(7,14),(14,0),(14,7),(14,14)]
    dw = [(1,1),(2,2),(3,3),(4,4),(13,13),(12,12),(11,11),(10,10),(7,7)]
    tl = [(1,5),(5,1),(5,13),(13,5),(9,1),(1,9),(9,13),(13,9)]
    dl = [(2,6),(6,2),(2,8),(8,2),(12,6),(6,12),(12,8),(8,12)]
    for p in tw: b[p] = ("3 WYRAZ", 3, 'W')
    for p in dw: b[p] = ("2 WYRAZ", 2, 'W')
    for p in tl: b[p] = ("3 LITERA", 3, 'L')
    for p in dl: b[p] = ("2 LITERA", 2, 'L')
    # środek jako zwykłe pole (można dodać specjalne)
    return b

# --- KLASA KAFELKA ---
class Tile:
    def __init__(self, letter):
        self.letter = letter
        self.points = LETTER_DATA[letter][0]
        self.rect = pygame.Rect(0,0,0,0)
        self.on_board = False
        self.temp = False  # położony w bieżącej turze
        self.dragging = False
        self.last_click = 0

    def draw(self, surf, font_letter, font_pts):
        pygame.draw.rect(surf, COLORS['tile'], self.rect, border_radius=6)
        pygame.draw.rect(surf, COLORS['tile_border'], self.rect, 2, border_radius=6)
        l = font_letter.render(self.letter, True, COLORS['text'])
        p = font_pts.render(str(self.points), True, COLORS['text'])
        surf.blit(l, l.get_rect(center=(self.rect.centerx, self.rect.centery-4)))
        surf.blit(p, (self.rect.right - 14, self.rect.bottom - 16))

# --- SILNIK GRY ---
class ScrabbleEngine:
    def __init__(self):
        self.grid = [[None]*15 for _ in range(15)]
        self.bag = [l for l, d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7)]
        self.ai_rack = [self.bag.pop() for _ in range(7)]
        self.player_score = 0
        self.ai_score = 0
        self.first_move = True
        self.turn = "PLAYER"
        self.bonuses = default_bonuses()
        self.last_definition = "Brak słowa"

    def refill_rack(self, rack):
        while len(rack) < 7 and self.bag:
            rack.append(Tile(self.bag.pop()))

    def placed_this_turn(self):
        return [(r,c) for r in range(15) for c in range(15) if self.grid[r][c] and self.grid[r][c].temp]

    def validate_rules(self):
        placed = self.placed_this_turn()
        if not placed:
            return False, "Brak położonych płytek."
        # pierwszy ruch musi zawierać środek
        if self.first_move:
            if (7,7) not in placed:
                return False, "Pierwszy ruch musi przechodzić przez środek planszy."
        # wszystkie w jednej linii
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) > 1 and len(cols) > 1:
            return False, "Płytki muszą być w jednej linii."
        # jeśli nie pierwszy ruch, musi stykać z istniejącymi
        if not self.first_move:
            touching = False
            for r,c in placed:
                for dr,dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nr, nc = r+dr, c+dc
                    if 0<=nr<15 and 0<=nc<15 and self.grid[nr][nc] and not self.grid[nr][nc].temp:
                        touching = True
            if not touching:
                return False, "Nowe płytki muszą stykać z istniejącymi słowami."
        return True, ""

    def extract_word(self):
        placed = self.placed_this_turn()
        if not placed: return ""
        placed.sort()
        r0, c0 = placed[0]
        # poziomo?
        if all(p[0] == r0 for p in placed):
            # idź w lewo do początku
            c = c0
            while c>0 and self.grid[r0][c-1]:
                c -= 1
            word = ""
            while c<15 and self.grid[r0][c]:
                word += self.grid[r0][c].letter
                c += 1
            return word
        else:
            # pionowo
            r = r0
            while r>0 and self.grid[r-1][c0]:
                r -= 1
            word = ""
            while r<15 and self.grid[r][c0]:
                word += self.grid[r][c0].letter
                r += 1
            return word

    def score_placed(self):
        placed = self.placed_this_turn()
        word_mul = 1
        base = 0
        for r,c in placed:
            tile = self.grid[r][c]
            pts = tile.points
            bonus = self.bonuses.get((r,c))
            if bonus:
                name, val, typ = bonus
                if typ == 'L':
                    pts *= val
                else:
                    word_mul *= val
            base += pts
        return base * word_mul

    def validate_word_online(self, word):
        # próba walidacji przez sjp.pl; jeśli błąd sieci, traktujemy jako poprawne (fail-safe)
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=2)
            text = r.text.lower()
            # proste heurystyki: jeśli strona zawiera "dopuszczalne w grach" lub definicję
            if "dopuszczalne w grach" in text or "hasło" in text or "znaczenie" in text:
                return True
            # jeśli wyraźnie napisane, że nie występuje
            if "nie występuje w słowniku" in text or "nie znaleziono" in text:
                return False
            return True
        except Exception:
            return True  # fail-safe: brak połączenia nie blokuje gry

    def commit_move(self):
        word = self.extract_word()
        valid, msg = self.validate_rules()
        if not valid:
            return False, msg
        if not word:
            return False, "Nie udało się złożyć słowa."
        ok = self.validate_word_online(word)
        if not ok:
            return False, f"Słowo '{word}' nie znalezione w słowniku."
        pts = self.score_placed()
        self.player_score += pts
        # usuwamy kafelki z stojaka (te które były położone)
        for r,c in self.placed_this_turn():
            t = self.grid[r][c]
            t.temp = False
            t.on_board = True
            # usuń z racka jeśli tam jest
            for rck in list(self.player_rack):
                if rck is t:
                    self.player_rack.remove(rck)
        self.first_move = False
        self.refill_rack(self.player_rack)
        self.turn = "AI"
        return True, f"Słowo '{word}' zaakceptowane. +{pts} pkt."

    def ai_play(self):
        # prosty AI: jeśli są jakieś kafelki na planszy, dokłada jedną literę obok pierwszego znalezionego
        time.sleep(0.6)
        placed = False
        for r in range(15):
            for c in range(15):
                if self.grid[r][c] and not placed:
                    for dr,dc in [(0,1),(1,0),(0,-1),(-1,0)]:
                        nr, nc = r+dr, c+dc
                        if 0<=nr<15 and 0<=nc<15 and not self.grid[nr][nc]:
                            if self.ai_rack:
                                let = self.ai_rack.pop(0)
                                t = Tile(let)
                                t.on_board = True
                                self.grid[nr][nc] = t
                                self.ai_score += t.points
                                if self.bag:
                                    self.ai_rack.append(self.bag.pop())
                                placed = True
                                break
            if placed: break
        # jeśli plansza pusta, AI położy losowo jedną literę w pobliżu środka
        if not placed:
            if self.ai_rack:
                let = self.ai_rack.pop(0)
                t = Tile(let)
                r, c = 7, 8
                if not self.grid[r][c]:
                    t.on_board = True
                    self.grid[r][c] = t
                    self.ai_score += t.points
                    if self.bag:
                        self.ai_rack.append(self.bag.pop())
        self.turn = "PLAYER"

# --- INTERFEJS GRAFICZNY I LOGIKA UI ---
class ScrabbleApp:
    def __init__(self):
        self.fullscreen = False
        self.screen = pygame.display.set_mode((1200, 850), pygame.RESIZABLE)
        self.engine = ScrabbleEngine()
        self.dragging = None
        self.clock = pygame.time.Clock()
        self.update_fonts()
        self.ok_btn = pygame.Rect(0,0,0,0)

    def update_fonts(self):
        h = self.screen.get_height()
        self.font_main = pygame.font.SysFont('Arial', max(18, h//30), bold=True)
        self.font_tile = pygame.font.SysFont('Arial', max(20, h//28), bold=True)
        self.font_pts = pygame.font.SysFont('Arial', max(12, h//50), bold=True)
        self.font_bonus = pygame.font.SysFont('Arial', max(10, h//60), bold=True)

    def layout(self):
        w,h = self.screen.get_size()
        cell = min(w//22, h//18)
        ox = 30
        oy = (h - 15*cell)//2
        return ox, oy, cell

    def draw_board(self):
        ox, oy, cs = self.layout()
        # tło
        self.screen.fill(COLORS['bg'])
        # plansza
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*cs, oy + r*cs, cs, cs)
                pygame.draw.rect(self.screen, COLORS['board'], rect)
                pygame.draw.rect(self.screen, COLORS['grid'], rect, 1)
                bonus = self.engine.bonuses.get((r,c))
                if bonus and not self.engine.grid[r][c]:
                    txt = self.font_bonus.render(bonus[0], True, COLORS['text'])
                    self.screen.blit(txt, txt.get_rect(center=rect.center))
                tile = self.engine.grid[r][c]
                if tile and not tile.dragging:
                    tile.rect = pygame.Rect(rect.x+4, rect.y+4, cs-8, cs-8)
                    tile.draw(self.screen, self.font_tile, self.font_pts)
        # stojak gracza
        rack_y = self.screen.get_height() - cs - 20
        for i, t in enumerate(self.engine.player_rack):
            if not t.on_board and not t.dragging:
                t.rect = pygame.Rect(ox + i*(cs+10), rack_y, cs, cs)
                t.draw(self.screen, self.font_tile, self.font_pts)
        # panel boczny
        ui_x = ox + 15*cs + 30
        self.screen.blit(self.font_main.render(f"PUNKTY: {self.engine.player_score}", True, COLORS['text']), (ui_x, 60))
        self.screen.blit(self.font_main.render(f"AI: {self.engine.ai_score}", True, COLORS['text']), (ui_x, 110))
        # definicja / informacja
        panel_rect = pygame.Rect(ui_x, self.screen.get_height()-170, 320, 140)
        pygame.draw.rect(self.screen, COLORS['panel'], panel_rect, border_radius=8)
        self.screen.blit(self.font_main.render("Słowo:", True, COLORS['text']), (ui_x+10, self.screen.get_height()-160))
        # ostatnia definicja (zawijanie)
        def_text = self.engine.last_definition
        lines = [def_text[i:i+40] for i in range(0, len(def_text), 40)]
        for idx, line in enumerate(lines[:4]):
            surf = self.font_pts.render(line, True, COLORS['text'])
            self.screen.blit(surf, (ui_x+10, self.screen.get_height()-130 + idx*20))
        # przycisk OK
        self.ok_btn = pygame.Rect(ui_x, 200, 140, 60)
        pygame.draw.rect(self.screen, COLORS['button'], self.ok_btn, border_radius=8)
        self.screen.blit(self.font_main.render("ZATWIERDŹ", True, (255,255,255)), (ui_x+8, 212))
        # jeśli przeciągamy kafelek, rysujemy go na wierzchu
        if self.dragging:
            self.dragging.draw(self.screen, self.font_tile, self.font_pts)

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                self.update_fonts()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F11:
                    # toggle fullscreen
                    self.fullscreen = not self.fullscreen
                    if self.fullscreen:
                        self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
                    else:
                        self.screen = pygame.display.set_mode((1200,850), pygame.RESIZABLE)
                    self.update_fonts()
            if self.engine.turn == "PLAYER":
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    pos = ev.pos
                    now = pygame.time.get_ticks()
                    ox, oy, cs = self.layout()
                    # dwuklik na kafelce położonej w tej turze -> cofnięcie
                    col = (pos[0]-ox)//cs
                    row = (pos[1]-oy)//cs
                    if 0<=row<15 and 0<=col<15:
                        t = self.engine.grid[row][col]
                        if t and t.temp:
                            if now - t.last_click < 400:
                                # cofnij
                                t.on_board = False
                                t.temp = False
                                # usuń z planszy
                                self.engine.grid[row][col] = None
                                # dodaj z powrotem do stojaka
                                self.engine.player_rack.append(t)
                                return
                            t.last_click = now
                    # klik na stojaku
                    for t in self.engine.player_rack:
                        if t.rect.collidepoint(pos):
                            self.dragging = t
                            t.dragging = True
                    # klik na OK
                    if self.ok_btn.collidepoint(pos):
                        ok, msg = self.engine.commit_move()
                        self.engine.last_definition = msg
                        if ok:
                            # AI ruch
                            self.engine.ai_play()
                if ev.type == pygame.MOUSEBUTTONUP:
                    if self.dragging:
                        ox, oy, cs = self.layout()
                        c = (ev.pos[0]-ox)//cs
                        r = (ev.pos[1]-oy)//cs
                        if 0<=r<15 and 0<=c<15 and not self.engine.grid[r][c]:
                            # położenie kafelka
                            self.engine.grid[r][c] = self.dragging
                            self.dragging.on_board = True
                            self.dragging.temp = True
                        self.dragging.dragging = False
                        self.dragging = None
                if ev.type == pygame.MOUSEMOTION and self.dragging:
                    self.dragging.rect.center = ev.pos

    def run(self):
        while True:
            self.handle_events()
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    ScrabbleApp().run()

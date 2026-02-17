# scrabble_edu.py
import pygame
import sys
import random
import requests
import time
import re

pygame.init()
pygame.display.set_caption("Scrabmania Edu - Scrabble edukacyjne")

# ----------------- KOLORY I PARAMETRY -----------------
COLORS = {
    'bg': (34, 139, 34),
    'board': (0, 100, 0),
    'grid': (0, 60, 0),
    'tile': (240, 230, 140),
    'tile_border': (140, 100, 20),
    'text': (0, 0, 0),
    'button': (128, 0, 128),
    'panel': (230, 230, 240),
    'log_bg': (245, 245, 255)
}

LETTER_DATA = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 'D': (2, 3),
    'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 'H': (3, 2), 'I': (1, 8),
    'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5),
    'Ń': (7, 1), 'O': (1, 6), 'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4),
    'Ś': (5, 1), 'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5),
    'Ź': (9, 1), 'Ż': (5, 1)
}

# ----------------- BONUSY (zgodnie z załączonym obrazem) -----------------
# Zwracamy etykietę jako tuple: (linia1, linia2, multiplier, type)
# line1 = "3x" line2 = "LITERA" lub "SŁOWO"
def board_bonuses():
    b = {}
    # Pozycje multiplikatorów słowa (wartości przykładowe zgodne z obrazem: 5x,4x,3x,2x)
    # Uwaga: w oryginalnym obrazie są pola 5x,4x,3x,2x - tu odwzorowane przykładowo
    tw5 = [(0,0),(0,14),(14,0),(14,14)]
    tw4 = [(0,7),(7,0),(7,14),(14,7)]
    tw3 = [(7,7),(4,4),(4,10),(10,4),(10,10)]
    tw2 = [(1,1),(2,2),(3,3),(11,11),(12,12),(13,13),(1,13),(13,1)]
    for p in tw5: b[p] = ("5x", "SŁOWO", 5, 'W')
    for p in tw4: b[p] = ("4x", "SŁOWO", 4, 'W')
    for p in tw3: b[p] = ("3x", "SŁOWO", 3, 'W')
    for p in tw2: b[p] = ("2x", "SŁOWO", 2, 'W')

    # Multiplikatory liter
    tl5 = [(1,5),(1,9),(5,1),(5,13),(9,1),(9,13),(13,5),(13,9)]
    tl4 = [(2,6),(2,8),(6,2),(6,12),(8,2),(8,12),(12,6),(12,8)]
    tl3 = [(3,7),(7,3),(7,11),(11,7)]
    tl2 = [(4,1),(1,4),(4,13),(13,4),(10,1),(1,10),(10,13),(13,10)]
    for p in tl5: b[p] = ("5x", "LITERA", 5, 'L')
    for p in tl4: b[p] = ("4x", "LITERA", 4, 'L')
    for p in tl3: b[p] = ("3x", "LITERA", 3, 'L')
    for p in tl2: b[p] = ("2x", "LITERA", 2, 'L')

    return b

# ----------------- KLASA TILE -----------------
class Tile:
    def __init__(self, letter):
        self.letter = letter
        self.points = LETTER_DATA[letter][0]
        self.rect = pygame.Rect(0,0,0,0)
        self.on_board = False
        self.temp = False
        self.dragging = False
        self.last_click = 0

    def draw(self, surf, font_letter, font_pts):
        pygame.draw.rect(surf, COLORS['tile'], self.rect, border_radius=6)
        pygame.draw.rect(surf, COLORS['tile_border'], self.rect, 2, border_radius=6)
        l = font_letter.render(self.letter, True, COLORS['text'])
        p = font_pts.render(str(self.points), True, COLORS['text'])
        surf.blit(l, l.get_rect(center=(self.rect.centerx, self.rect.centery-6)))
        surf.blit(p, (self.rect.right - 14, self.rect.bottom - 16))

# ----------------- SILNIK GRY -----------------
class ScrabbleEngine:
    def __init__(self):
        self.grid = [[None]*15 for _ in range(15)]
        self.bag = [l for l,d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7)]
        # AI rack jako litery (będziemy tworzyć Tile przy kładzeniu)
        self.ai_rack = [self.bag.pop() for _ in range(7)]
        self.player_score = 0
        self.ai_score = 0
        self.first_move = True
        self.turn = "PLAYER"
        self.bonuses = board_bonuses()
        self.last_player_word = ""
        self.last_ai_word = ""
        self.last_player_def = ""
        self.last_ai_def = ""

    def refill_rack(self, rack):
        while len(rack) < 7 and self.bag:
            rack.append(Tile(self.bag.pop()))

    def refill_ai(self):
        while len(self.ai_rack) < 7 and self.bag:
            self.ai_rack.append(self.bag.pop())

    def placed_this_turn(self):
        return [(r,c) for r in range(15) for c in range(15) if self.grid[r][c] and self.grid[r][c].temp]

    def validate_rules(self):
        placed = self.placed_this_turn()
        if not placed:
            return False, "Brak położonych płytek."
        if self.first_move and (7,7) not in placed:
            return False, "Pierwszy ruch musi przechodzić przez środek planszy."
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) > 1 and len(cols) > 1:
            return False, "Płytki muszą być w jednej linii."
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
        if all(p[0] == r0 for p in placed):
            c = c0
            while c>0 and self.grid[r0][c-1]:
                c -= 1
            word = ""
            while c<15 and self.grid[r0][c]:
                word += self.grid[r0][c].letter
                c += 1
            return word
        else:
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
                _, _, val, typ = bonus
                if typ == 'L':
                    pts *= val
                else:
                    word_mul *= val
            base += pts
        return base * word_mul

    def validate_word_online(self, word):
        if not word: return False
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=3)
            text = r.text.lower()
            if "dopuszczalne w grach" in text or "hasło" in text or "znaczenie" in text:
                return True
            if "nie występuje w słowniku" in text or "nie znaleziono" in text:
                return False
            return True
        except Exception:
            return True  # fail-safe

    def fetch_definition(self, word):
        if not word: return "Brak słowa"
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=3)
            clean = re.sub('<[^<]+?>', '', r.text)
            # Spróbuj znaleźć fragment po "dopuszczalne w grach" lub pierwsze zdanie
            m = re.search(r"dopuszczalne w grach(.*?)(komentarz|komentarze|$)", clean, re.DOTALL)
            if m:
                res = m.group(1).strip()
                res = re.sub(r'\s+', ' ', res)
                return (res[:200] + '...') if len(res) > 200 else res
            # fallback: pierwsze 200 znaków tekstu bez tagów
            txt = re.sub(r'\s+', ' ', clean).strip()
            return (txt[:200] + '...') if len(txt) > 200 else txt
        except Exception:
            return "Błąd połączenia."

    def commit_move(self):
        ok, msg = self.validate_rules()
        if not ok:
            return False, msg
        word = self.extract_word()
        if not word:
            return False, "Nie udało się złożyć słowa."
        valid = self.validate_word_online(word)
        if not valid:
            return False, f"Słowo '{word}' nie znalezione w słowniku."
        pts = self.score_placed()
        # finalize tiles: mark on_board, remove from player's rack
        for r,c in self.placed_this_turn():
            t = self.grid[r][c]
            t.temp = False
            t.on_board = True
            # remove exact tile object from rack if present
            for rck in list(self.player_rack):
                if rck is t:
                    self.player_rack.remove(rck)
        self.player_score += pts
        self.first_move = False
        # fetch definition and store
        self.last_player_word = word
        self.last_player_def = self.fetch_definition(word)
        print(f"Gracz: {word} -> {self.last_player_def}")
        # refill rack
        self.refill_rack(self.player_rack)
        self.turn = "AI"
        return True, f"Słowo '{word}' zaakceptowane. +{pts} pkt."

    def ai_play(self):
        time.sleep(0.6)
        placed = False
        ai_word = ""
        # try to place next to existing tile
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
                                ai_word = let
                                if self.bag:
                                    self.ai_rack.append(self.bag.pop())
                                placed = True
                                break
            if placed: break
        if not placed:
            # place one tile near center
            if self.ai_rack:
                let = self.ai_rack.pop(0)
                t = Tile(let)
                r, c = 7, 8
                if not self.grid[r][c]:
                    t.on_board = True
                    self.grid[r][c] = t
                    self.ai_score += t.points
                    ai_word = let
                    if self.bag:
                        self.ai_rack.append(self.bag.pop())
        # set AI word and definition (single-letter word may be invalid but for demo)
        self.last_ai_word = ai_word
        self.last_ai_def = self.fetch_definition(ai_word) if ai_word else "Brak"
        print(f"Komputer: {self.last_ai_word} -> {self.last_ai_def}")
        self.refill_ai()
        self.turn = "PLAYER"

    def return_tile_to_bag(self, tile):
        # remove tile from board if present
        for r in range(15):
            for c in range(15):
                if self.grid[r][c] is tile:
                    self.grid[r][c] = None
        # put letter back to bag and shuffle
        self.bag.append(tile.letter)
        random.shuffle(self.bag)
        # ensure player's rack has 7 tiles
        # remove tile object from rack if present (we will create new Tile from bag)
        for rck in list(self.player_rack):
            if rck is tile:
                self.player_rack.remove(rck)
        self.refill_rack(self.player_rack)

# ----------------- UI APLIKACJI -----------------
class ScrabbleApp:
    def __init__(self):
        self.fullscreen = False
        self.screen = pygame.display.set_mode((1200, 850), pygame.RESIZABLE)
        self.engine = ScrabbleEngine()
        self.dragging = None
        self.clock = pygame.time.Clock()
        self.update_fonts()
        # log window
        self.log_rect = pygame.Rect(50, 50, 360, 180)
        self.log_dragging = False
        self.log_offset = (0,0)
        self.log_lines = []  # list of strings
        # ensure always 7 tiles
        self.engine.refill_rack(self.engine.player_rack)

    def update_fonts(self):
        h = self.screen.get_height()
        self.font_main = pygame.font.SysFont('Arial', max(18, h//30), bold=True)
        self.font_tile = pygame.font.SysFont('Arial', max(20, h//28), bold=True)
        self.font_pts = pygame.font.SysFont('Arial', max(12, h//50), bold=True)
        self.font_bonus_big = pygame.font.SysFont('Arial', max(12, h//45), bold=True)
        self.font_bonus_small = pygame.font.SysFont('Arial', max(10, h//60), bold=True)

    def layout(self):
        w,h = self.screen.get_size()
        cell = min(w//22, h//18)
        ox = 30
        oy = (h - 15*cell)//2
        return ox, oy, cell

    def draw_bonus(self, surf, rect, bonus):
        # bonus: (line1, line2, val, type)
        line1, line2, _, _ = bonus
        # draw two-line centered: first line smaller, second line slightly larger
        l1 = self.font_bonus_small.render(line1, True, COLORS['text'])
        l2 = self.font_bonus_big.render(line2, True, COLORS['text'])
        # center both lines in rect
        surf.blit(l1, l1.get_rect(center=(rect.centerx, rect.centery-8)))
        surf.blit(l2, l2.get_rect(center=(rect.centerx, rect.centery+8)))

    def draw_board(self):
        ox, oy, cs = self.layout()
        self.screen.fill(COLORS['bg'])
        # plansza
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*cs, oy + r*cs, cs, cs)
                pygame.draw.rect(self.screen, COLORS['board'], rect)
                pygame.draw.rect(self.screen, COLORS['grid'], rect, 1)
                bonus = self.engine.bonuses.get((r,c))
                if bonus and not self.engine.grid[r][c]:
                    self.draw_bonus(self.screen, rect, bonus)
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
        # woreczek info
        self.screen.blit(self.font_pts.render(f"W worku: {len(self.engine.bag)}", True, COLORS['text']), (ui_x, 160))
        # definicje (ostatnie)
        panel_rect = pygame.Rect(ui_x, self.screen.get_height()-220, 360, 200)
        pygame.draw.rect(self.screen, COLORS['panel'], panel_rect, border_radius=8)
        self.screen.blit(self.font_main.render("Słowo gracza:", True, COLORS['text']), (ui_x+10, self.screen.get_height()-210))
        self.screen.blit(self.font_pts.render(self.engine.last_player_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-185))
        # wrap player def
        pdef = self.engine.last_player_def or ""
        lines = [pdef[i:i+60] for i in range(0, len(pdef), 60)]
        for idx, line in enumerate(lines[:4]):
            self.screen.blit(self.font_pts.render(line, True, COLORS['text']), (ui_x+10, self.screen.get_height()-160 + idx*18))
        # AI
        self.screen.blit(self.font_main.render("Słowo komputera:", True, COLORS['text']), (ui_x+10, self.screen.get_height()-100))
        self.screen.blit(self.font_pts.render(self.engine.last_ai_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-75))
        adef = self.engine.last_ai_def or ""
        alines = [adef[i:i+60] for i in range(0, len(adef), 60)]
        for idx, line in enumerate(alines[:3]):
            self.screen.blit(self.font_pts.render(line, True, COLORS['text']), (ui_x+10, self.screen.get_height()-55 + idx*18))
        # przycisk OK
        self.ok_btn = pygame.Rect(ui_x, 200, 140, 60)
        pygame.draw.rect(self.screen, COLORS['button'], self.ok_btn, border_radius=8)
        self.screen.blit(self.font_main.render("ZATWIERDŹ", True, (255,255,255)), (ui_x+8, 212))
        # log window
        self.draw_log_window()

        # jeśli przeciągamy kafelek, rysujemy go na wierzchu
        if self.dragging:
            self.dragging.draw(self.screen, self.font_tile, self.font_pts)

    def draw_log_window(self):
        # background
        pygame.draw.rect(self.screen, COLORS['log_bg'], self.log_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLORS['tile_border'], self.log_rect, 2, border_radius=6)
        title = self.font_main.render("LOG SŁÓW (przeciągnij)", True, COLORS['text'])
        self.screen.blit(title, (self.log_rect.x + 8, self.log_rect.y + 6))
        # draw lines
        y = self.log_rect.y + 36
        for line in self.log_lines[-6:][::-1]:  # show last 6 entries newest first
            txt = self.font_pts.render(line, True, COLORS['text'])
            self.screen.blit(txt, (self.log_rect.x + 8, y))
            y += 20

    def add_log(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.log_lines.append(f"[{timestamp}] {text}")

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                self.update_fonts()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F11:
                    self.fullscreen = not self.fullscreen
                    if self.fullscreen:
                        self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
                    else:
                        self.screen = pygame.display.set_mode((1200,850), pygame.RESIZABLE)
                    self.update_fonts()
            # log window dragging
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.log_rect.collidepoint(ev.pos):
                    self.log_dragging = True
                    mx, my = ev.pos
                    self.log_offset = (mx - self.log_rect.x, my - self.log_rect.y)
                # player interactions only when player's turn
                if self.engine.turn == "PLAYER":
                    pos = ev.pos
                    now = pygame.time.get_ticks()
                    ox, oy, cs = self.layout()
                    # dwuklik na kafelce położonej w tej turze -> cofnięcie i zwrot do woreczka
                    col = (pos[0]-ox)//cs
                    row = (pos[1]-oy)//cs
                    if 0<=row<15 and 0<=col<15:
                        t = self.engine.grid[row][col]
                        if t and t.temp:
                            if now - t.last_click < 400:
                                # cofnij: usuń z planszy i zwróć literę do woreczka
                                self.engine.grid[row][col] = None
                                self.engine.return_tile_to_bag(t)
                                self.add_log(f"Cofnięto {t.letter} -> do woreczka")
                                print(f"Cofnięto {t.letter} -> do woreczka")
                                return
                            t.last_click = now
                    # klik na stojaku - zacznij przeciągać
                    for t in self.engine.player_rack:
                        if t.rect.collidepoint(pos):
                            self.dragging = t
                            t.dragging = True
                    # klik na OK
                    if self.ok_btn.collidepoint(pos):
                        ok, msg = self.engine.commit_move()
                        self.add_log(msg)
                        print(msg)
                        if ok:
                            # log definitions and print to terminal
                            self.add_log(f"Gracz: {self.engine.last_player_word}")
                            self.add_log(f"Def: {self.engine.last_player_def[:80]}")
                            print(f"Definicja gracza: {self.engine.last_player_def}")
                            # AI ruch
                            self.engine.ai_play()
                            self.add_log(f"Komputer: {self.engine.last_ai_word}")
                            self.add_log(f"Def AI: {self.engine.last_ai_def[:80]}")
                            print(f"Definicja komputera: {self.engine.last_ai_def}")
            if ev.type == pygame.MOUSEBUTTONUP:
                # stop dragging log
                if self.log_dragging:
                    self.log_dragging = False
                # drop tile
                if self.dragging:
                    ox, oy, cs = self.layout()
                    c = (ev.pos[0]-ox)//cs
                    r = (ev.pos[1]-oy)//cs
                    if 0<=r<15 and 0<=c<15 and not self.engine.grid[r][c]:
                        self.engine.grid[r][c] = self.dragging
                        self.dragging.on_board = True
                        self.dragging.temp = True
                    else:
                        # if not placed, keep on rack (no change)
                        pass
                    self.dragging.dragging = False
                    self.dragging = None
            if ev.type == pygame.MOUSEMOTION:
                if self.dragging:
                    self.dragging.rect.center = ev.pos
                if self.log_dragging:
                    mx, my = ev.pos
                    ox = mx - self.log_offset[0]
                    oy = my - self.log_offset[1]
                    # keep log inside window bounds
                    sw, sh = self.screen.get_size()
                    ox = max(0, min(ox, sw - self.log_rect.width))
                    oy = max(0, min(oy, sh - self.log_rect.height))
                    self.log_rect.topleft = (ox, oy)

    def run(self):
        while True:
            self.handle_events()
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    ScrabbleApp().run()

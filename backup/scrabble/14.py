# scrabble_complete.py
import pygame
import sys
import random
import requests
import time
import re
import html

# ---------- KONFIGURACJA ----------
pygame.init()
pygame.display.set_caption("Scrabmania Edu - Scrabble edukacyjne")

COLORS = {
    'bg': (34, 139, 34),
    'board': (0, 100, 0),
    'grid': (0, 60, 0),
    'tile': (240, 230, 140),
    'tile_border': (140, 100, 20),
    'text': (0, 0, 0),
    'button': (128, 0, 128),
    'button_pass': (200, 200, 200),
    'panel': (230, 230, 240),
    'log_bg': (245, 245, 255)
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

# Dozwolone jednopłytkowe słowa (opcjonalne). Jeśli puste, wymagamy min długości 2.
ALLOWED_SINGLE = set(['A','I','O','U','W','Z','S','Y'])

# ---------- BONUSY (dwuliniowe etykiety: "3x" nad "LITERA"/"SŁOWO") ----------
def board_bonuses():
    b = {}
    # przykładowe rozmieszczenie (możesz doprecyzować)
    tw5 = [(0,0),(0,14),(14,0),(14,14)]
    tw4 = [(0,7),(7,0),(7,14),(14,7)]
    tw3 = [(7,7),(4,4),(4,10),(10,4),(10,10)]
    tw2 = [(1,1),(2,2),(3,3),(11,11),(12,12),(13,13),(1,13),(13,1)]
    for p in tw5: b[p] = ("5x", "SŁOWO", 5, 'W')
    for p in tw4: b[p] = ("4x", "SŁOWO", 4, 'W')
    for p in tw3: b[p] = ("3x", "SŁOWO", 3, 'W')
    for p in tw2: b[p] = ("2x", "SŁOWO", 2, 'W')

    tl5 = [(1,5),(1,9),(5,1),(5,13),(9,1),(9,13),(13,5),(13,9)]
    tl4 = [(2,6),(2,8),(6,2),(6,12),(8,2),(8,12),(12,6),(12,8)]
    tl3 = [(3,7),(7,3),(7,11),(11,7)]
    tl2 = [(4,1),(1,4),(4,13),(13,4),(10,1),(1,10),(10,13),(13,10)]
    for p in tl5: b[p] = ("5x", "LITERA", 5, 'L')
    for p in tl4: b[p] = ("4x", "LITERA", 4, 'L')
    for p in tl3: b[p] = ("3x", "LITERA", 3, 'L')
    for p in tl2: b[p] = ("2x", "LITERA", 2, 'L')
    return b

# ---------- KLASA TILE ----------
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

# ---------- SILNIK GRY ----------
class ScrabbleEngine:
    def __init__(self):
        self.grid = [[None]*15 for _ in range(15)]
        self.bag = [l for l,d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7)]
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
        return [(r,c) for r in range(15) for c in range(15)
                if self.grid[r][c] and self.grid[r][c].temp]

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

    def extract_word_from(self, r, c, horiz=True):
        if horiz:
            col = c
            while col>0 and self.grid[r][col-1]:
                col -= 1
            word = ""
            while col<15 and self.grid[r][col]:
                word += self.grid[r][col].letter
                col += 1
            return word
        else:
            row = r
            while row>0 and self.grid[row-1][c]:
                row -= 1
            word = ""
            while row<15 and self.grid[row][c]:
                word += self.grid[row][c].letter
                row += 1
            return word

    def _main_orientation(self):
        placed = self.placed_this_turn()
        if not placed: return None
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) == 1: return 'H'
        if len(cols) == 1: return 'V'
        return None

    def words_created_by_placing(self, r, c):
        words = []
        orient = self._main_orientation()
        if orient is None:
            w1 = self.extract_word_from(r, c, horiz=True)
            w2 = self.extract_word_from(r, c, horiz=False)
            if w1: words.append(w1)
            if w2 and w2 != w1: words.append(w2)
            return words
        if orient == 'H':
            main = self.extract_word_from(r, c, horiz=True)
            if main: words.append(main)
            # vertical cross
            up = (r-1, c); down = (r+1, c)
            if (0<=up[0]<15 and self.grid[up[0]][up[1]]) or (0<=down[0]<15 and self.grid[down[0]][down[1]]):
                w = self.extract_word_from(r, c, horiz=False)
                if len(w) > 1: words.append(w)
        else:
            main = self.extract_word_from(r, c, horiz=False)
            if main: words.append(main)
            left = (r, c-1); right = (r, c+1)
            if (0<=left[1]<15 and self.grid[left[0]][left[1]]) or (0<=right[1]<15 and self.grid[right[0]][right[1]]):
                w = self.extract_word_from(r, c, horiz=True)
                if len(w) > 1: words.append(w)
        return list(dict.fromkeys([w for w in words if w]))

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
            # brak sieci: fail-safe -> traktujemy jako poprawne, ale logujemy
            print("Uwaga: brak połączenia z sjp.pl — walidacja online pominięta (fail-safe).")
            return True

    def fetch_definition(self, word):
        if not word: return "Brak słowa"
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=3)
            clean = re.sub('<[^<]+?>', '', r.text)
            clean = html.unescape(clean)
            m = re.search(r"dopuszczalne w grach(.*?)(komentarz|komentarze|$)", clean, re.DOTALL)
            if m:
                res = m.group(1).strip()
                res = re.sub(r'\s+', ' ', res)
                return (res[:400] + '...') if len(res) > 400 else res
            txt = re.sub(r'\s+', ' ', clean).strip()
            return (txt[:400] + '...') if len(txt) > 400 else txt
        except Exception:
            return "Błąd połączenia."

    def extract_full_placed_word(self):
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

    def commit_move(self):
        ok, msg = self.validate_rules()
        if not ok:
            return False, msg
        placed = self.placed_this_turn()
        if not placed:
            return False, "Brak położonych płytek."
        # zbierz wszystkie słowa powstałe przez położenie kafelków
        all_words = set()
        for r,c in placed:
            ws = self.words_created_by_placing(r, c)
            for w in ws:
                all_words.add(w)
        # walidacja: długość i online
        for w in all_words:
            if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                return False, f"Słowo '{w}' jest za krótkie."
            if not self.validate_word_online(w):
                return False, f"Słowo '{w}' nie znalezione w słowniku."
        # jeśli wszystkie ok -> policz punkty i zatwierdź
        pts = self.score_placed()
        for r,c in placed:
            t = self.grid[r][c]
            t.temp = False
            t.on_board = True
            for rck in list(self.player_rack):
                if rck is t:
                    self.player_rack.remove(rck)
        self.player_score += pts
        self.first_move = False
        self.last_player_word = self.extract_full_placed_word()
        self.last_player_def = self.fetch_definition(self.last_player_word)
        # print definition to terminal (cleaned, truncated)
        print(f"Gracz: {self.last_player_word} -> {self.last_player_def}")
        self.refill_rack(self.player_rack)
        self.turn = "AI"
        return True, f"Słowo '{self.last_player_word}' zaakceptowane. +{pts} pkt."

    # ---------- AI: próby ruchów (symulacja + walidacja) ----------
    def ai_try_place_single_tile(self):
        # AI próbuje położyć pojedynczą literę obok istniejących kafelków tak, aby wszystkie powstałe słowa były poprawne
        for r in range(15):
            for c in range(15):
                if self.grid[r][c]:
                    for dr,dc in [(0,1),(1,0),(0,-1),(-1,0)]:
                        nr, nc = r+dr, c+dc
                        if 0<=nr<15 and 0<=nc<15 and not self.grid[nr][nc]:
                            for i, let in enumerate(list(self.ai_rack)):
                                t = Tile(let)
                                # symulacja
                                self.grid[nr][nc] = t
                                words = self.words_created_by_placing(nr, nc)
                                valid_all = True
                                for w in words:
                                    if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                                        valid_all = False; break
                                    if not self.validate_word_online(w):
                                        valid_all = False; break
                                if valid_all and words:
                                    # commit
                                    t.on_board = True
                                    self.ai_score += t.points
                                    self.ai_rack.pop(i)
                                    if self.bag:
                                        self.ai_rack.append(self.bag.pop())
                                    self.last_ai_word = ", ".join(words)
                                    self.last_ai_def = self.fetch_definition(words[0]) if words else ""
                                    print(f"Komputer: {self.last_ai_word} -> {self.last_ai_def}")
                                    return True
                                # revert
                                self.grid[nr][nc] = None
        return False

    def ai_try_place_two_tiles_center(self):
        # jeśli plansza pusta, spróbuj położyć 2 litery obok siebie (środek)
        empty = all(self.grid[r][c] is None for r in range(15) for c in range(15))
        if not empty:
            return False
        r, c = 7, 7
        n = len(self.ai_rack)
        for i in range(n):
            for j in range(i+1, n):
                a = self.ai_rack[i]; b = self.ai_rack[j]
                for order in [(a,b),(b,a)]:
                    t1 = Tile(order[0]); t2 = Tile(order[1])
                    self.grid[r][c] = t1; self.grid[r][c+1] = t2
                    words = { self.extract_word_from(r, c, horiz=True) }
                    valid_all = True
                    for w in words:
                        if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                            valid_all = False; break
                        if not self.validate_word_online(w):
                            valid_all = False; break
                    if valid_all:
                        t1.on_board = True; t2.on_board = True
                        # usuń z ai_rack (pop j, pop i)
                        self.ai_rack.pop(j); self.ai_rack.pop(i)
                        self.ai_score += t1.points + t2.points
                        if self.bag:
                            self.ai_rack.append(self.bag.pop())
                        if self.bag:
                            self.ai_rack.append(self.bag.pop())
                        self.last_ai_word = self.extract_word_from(r, c, horiz=True)
                        self.last_ai_def = self.fetch_definition(self.last_ai_word)
                        print(f"Komputer: {self.last_ai_word} -> {self.last_ai_def}")
                        return True
                    self.grid[r][c] = None; self.grid[r][c+1] = None
        return False

    def ai_play(self):
        time.sleep(0.6)
        placed = False
        # jeśli plansza pusta -> spróbuj 2 litery
        if all(self.grid[r][c] is None for r in range(15) for c in range(15)):
            if self.ai_try_place_two_tiles_center():
                placed = True
        if not placed:
            if self.ai_try_place_single_tile():
                placed = True
        if not placed:
            # AI passes
            self.last_ai_word = ""
            self.last_ai_def = ""
            print("Komputer: opuszcza kolejkę (brak poprawnego ruchu).")
            self.turn = "PLAYER"
            return False
        self.refill_ai()
        self.turn = "PLAYER"
        return True

    def return_tile_to_bag(self, tile):
        # usuń z planszy jeśli tam jest
        for r in range(15):
            for c in range(15):
                if self.grid[r][c] is tile:
                    self.grid[r][c] = None
        # zwróć literę do woreczka i potasuj
        self.bag.append(tile.letter)
        random.shuffle(self.bag)
        # usuń obiekt z racka jeśli tam jest
        for rck in list(self.player_rack):
            if rck is tile:
                self.player_rack.remove(rck)
        # uzupełnij rack do 7
        self.refill_rack(self.player_rack)

# ---------- UI APLIKACJI ----------
class ScrabbleApp:
    def __init__(self):
        self.fullscreen = False
        self.screen = pygame.display.set_mode((1200, 850), pygame.RESIZABLE)
        self.engine = ScrabbleEngine()
        self.dragging = None
        self.clock = pygame.time.Clock()
        self.update_fonts()
        self.log_rect = pygame.Rect(40, 40, 380, 200)
        self.log_dragging = False
        self.log_offset = (0,0)
        self.log_lines = []
        self.engine.refill_rack(self.engine.player_rack)

    def update_fonts(self):
        h = self.screen.get_height()
        # czcionki: etykiety premii zmniejszone o połowę
        self.font_bonus_big = pygame.font.SysFont('Arial', max(12, h//60), bold=True)
        self.font_bonus_small = pygame.font.SysFont('Arial', max(10, h//90), bold=True)
        self.font_tile = pygame.font.SysFont('Arial', max(20, h//28), bold=True)
        self.font_pts = pygame.font.SysFont('Arial', max(12, h//50), bold=True)
        self.font_main = pygame.font.SysFont('Arial', max(18, h//30), bold=True)

    def layout(self):
        w,h = self.screen.get_size()
        cell = min(w//22, h//18)
        ox = 30
        oy = (h - 15*cell)//2
        return ox, oy, cell

    def draw_bonus(self, surf, rect, bonus):
        line1, line2, _, _ = bonus
        l1 = self.font_bonus_small.render(line1, True, COLORS['text'])
        l2 = self.font_bonus_big.render(line2, True, COLORS['text'])
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
        self.screen.blit(self.font_pts.render(f"W worku: {len(self.engine.bag)}", True, COLORS['text']), (ui_x, 160))
        panel_rect = pygame.Rect(ui_x, self.screen.get_height()-220, 360, 200)
        pygame.draw.rect(self.screen, COLORS['panel'], panel_rect, border_radius=8)
        # pokazujemy tylko słowa (bez definicji)
        self.screen.blit(self.font_bonus_big.render("Słowo gracza", True, COLORS['text']), (ui_x+10, self.screen.get_height()-210))
        self.screen.blit(self.font_bonus_big.render(self.engine.last_player_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-185))
        self.screen.blit(self.font_bonus_big.render("Słowo komputera", True, COLORS['text']), (ui_x+10, self.screen.get_height()-140))
        self.screen.blit(self.font_bonus_big.render(self.engine.last_ai_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-115))
        # przyciski: ZATWIERDŹ i mały PASS
        self.ok_btn = pygame.Rect(ui_x, 200, 140, 60)
        pygame.draw.rect(self.screen, COLORS['button'], self.ok_btn, border_radius=8)
        self.screen.blit(self.font_main.render("ZATWIERDŹ", True, (255,255,255)), (ui_x+8, 212))
        self.pass_btn = pygame.Rect(ui_x+150, 220, 160, 30)
        pygame.draw.rect(self.screen, COLORS['button_pass'], self.pass_btn, border_radius=6)
        self.screen.blit(self.font_pts.render("Opuszczam 1 kolejkę", True, (0,0,0)), (ui_x+155, 224))
        # log
        self.draw_log_window()
        # rysuj przeciągany kafelek na wierzchu
        if self.dragging:
            self.dragging.draw(self.screen, self.font_tile, self.font_pts)

    def draw_log_window(self):
        pygame.draw.rect(self.screen, COLORS['log_bg'], self.log_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLORS['tile_border'], self.log_rect, 2, border_radius=6)
        title = self.font_main.render("LOG SŁÓW (przeciągnij)", True, COLORS['text'])
        self.screen.blit(title, (self.log_rect.x + 8, self.log_rect.y + 6))
        y = self.log_rect.y + 36
        for line in self.log_lines[-8:][::-1]:
            txt = self.font_pts.render(line, True, COLORS['text'])
            self.screen.blit(txt, (self.log_rect.x + 8, y))
            y += 18

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
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.log_rect.collidepoint(ev.pos):
                    self.log_dragging = True
                    mx, my = ev.pos
                    self.log_offset = (mx - self.log_rect.x, my - self.log_rect.y)
                if self.engine.turn == "PLAYER":
                    pos = ev.pos
                    now = pygame.time.get_ticks()
                    ox, oy, cs = self.layout()
                    col = (pos[0]-ox)//cs
                    row = (pos[1]-oy)//cs
                    if 0<=row<15 and 0<=col<15:
                        t = self.engine.grid[row][col]
                        if t and t.temp:
                            if now - t.last_click < 400:
                                # cofnięcie kafelka -> do woreczka
                                self.engine.grid[row][col] = None
                                self.engine.return_tile_to_bag(t)
                                self.add_log(f"Cofnięto {t.letter} -> do woreczka")
                                print(f"Cofnięto {t.letter} -> do woreczka")
                                return
                            t.last_click = now
                    # przeciąganie z racka
                    for t in self.engine.player_rack:
                        if t.rect.collidepoint(pos):
                            self.dragging = t
                            t.dragging = True
                    # klik ZATWIERDŹ
                    if self.ok_btn.collidepoint(pos):
                        ok, msg = self.engine.commit_move()
                        self.add_log(msg)
                        print(msg)
                        if ok:
                            self.add_log(f"Gracz: {self.engine.last_player_word}")
                            self.add_log("Definicja wypisana do terminala")
                            # AI ruch
                            moved = self.engine.ai_play()
                            if moved:
                                self.add_log(f"Komputer: {self.engine.last_ai_word}")
                                self.add_log("Definicja AI wypisana do terminala")
                            else:
                                self.add_log("Komputer opuścił kolejkę")
                    # klik PASS
                    if self.pass_btn.collidepoint(pos):
                        self.add_log("Gracz: opuszcza 1 kolejkę")
                        print("Gracz: opuszcza 1 kolejkę")
                        self.engine.turn = "AI"
                        moved = self.engine.ai_play()
                        if moved:
                            self.add_log(f"Komputer: {self.engine.last_ai_word}")
                            self.add_log("Definicja AI wypisana do terminala")
                        else:
                            self.add_log("Komputer opuścił kolejkę")
            if ev.type == pygame.MOUSEBUTTONUP:
                if self.log_dragging:
                    self.log_dragging = False
                if self.dragging:
                    ox, oy, cs = self.layout()
                    c = (ev.pos[0]-ox)//cs
                    r = (ev.pos[1]-oy)//cs
                    if 0<=r<15 and 0<=c<15 and not self.engine.grid[r][c]:
                        self.engine.grid[r][c] = self.dragging
                        self.dragging.on_board = True
                        self.dragging.temp = True
                    # jeśli nie położono, kafelek pozostaje na stojaku
                    self.dragging.dragging = False
                    self.dragging = None
            if ev.type == pygame.MOUSEMOTION:
                if self.dragging:
                    self.dragging.rect.center = ev.pos
                if self.log_dragging:
                    mx, my = ev.pos
                    ox = mx - self.log_offset[0]
                    oy = my - self.log_offset[1]
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

# scrabble_threaded.py
import pygame
import sys
import random
import requests
import time
import re
import html
import threading
import queue
from collections import namedtuple
from itertools import permutations, combinations

# ---------- KONFIGURACJA ----------
pygame.init()
pygame.display.set_caption("Scrabmania Edu - Scrabble (threaded)")

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
    'log_bg': (245, 245, 255),
    'invalid': (200, 80, 80)
}

LETTER_DATA = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 'D': (2, 3),
    'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 'H': (3, 2), 'I': (1, 8),
    'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5),
    'Ń': (7, 1), 'O': (1, 6), 'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4),
    'Ś': (5, 1), 'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5),
    'Ź': (9, 1), 'Ż': (5, 1),
    '_': (0, 2)  # blank/joker
}

ALLOWED_SINGLE = set(['A','I','O','U','W','Z','S','Y'])

def board_bonuses():
    b = {}
    tw5 = [(0,0),(0,14),(14,0),(14,14)]
    tw4 = [(0,7),(7,0),(7,14),(14,7)]
    tw3 = [(7,7),(4,4),(4,10),(10,4),(10,10)]
    tw2 = [(1,1),(2,2),(3,3),(11,11),(12,12),(13,13),(1,13),(13,1)]
    for p in tw5: b[p] = ("5x","SŁOWO",5,'W')
    for p in tw4: b[p] = ("4x","SŁOWO",4,'W')
    for p in tw3: b[p] = ("3x","SŁOWO",3,'W')
    for p in tw2: b[p] = ("2x","SŁOWO",2,'W')
    tl5 = [(1,5),(1,9),(5,1),(5,13),(9,1),(9,13),(13,5),(13,9)]
    tl4 = [(2,6),(2,8),(6,2),(6,12),(8,2),(8,12),(12,6),(12,8)]
    tl3 = [(3,7),(7,3),(7,11),(11,7)]
    tl2 = [(4,1),(1,4),(4,13),(13,4),(10,1),(1,10),(10,13),(13,10)]
    for p in tl5: b[p] = ("5x","LITERA",5,'L')
    for p in tl4: b[p] = ("4x","LITERA",4,'L')
    for p in tl3: b[p] = ("3x","LITERA",3,'L')
    for p in tl2: b[p] = ("2x","LITERA",2,'L')
    return b

# ---------- pomocnicze struktury ----------
Placement = namedtuple('Placement', ['r','c','tile'])

# ---------- DICTIONARY (local or online with cache) ----------
class Dictionary:
    def __init__(self, local_file='dict.txt'):
        self.local = False
        self.words = set()
        self.cache = {}
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                for line in f:
                    w = line.strip().upper()
                    if w: self.words.add(w)
            if self.words:
                self.local = True
                print(f"Używam lokalnego słownika: {len(self.words)} słów.")
        except Exception:
            print("Brak lokalnego słownika; używam walidacji online z cache.")
            self.local = False

    def is_word(self, word):
        if not word: return False
        w = word.upper()
        if self.local:
            return w in self.words
        if w in self.cache:
            return self.cache[w]
        try:
            r = requests.get(f"https://sjp.pl/{w.lower()}", timeout=2)
            text = r.text.lower()
            ok = ("dopuszczalne w grach" in text) or ("hasło" in text) or ("znaczenie" in text)
            if "nie występuje w słowniku" in text or "nie znaleziono" in text:
                ok = False
            self.cache[w] = ok
            return ok
        except Exception:
            print("Uwaga: brak połączenia z sjp.pl — walidacja online pominięta (fail-safe).")
            self.cache[w] = True
            return True

    def get_definition(self, word):
        if not word: return "Brak słowa"
        w = word.upper()
        if self.local:
            return "Definicja lokalna niedostępna."
        try:
            r = requests.get(f"https://sjp.pl/{w.lower()}", timeout=2)
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

# ---------- SCORING ENGINE ----------
class ScoringEngine:
    def __init__(self, bonuses):
        self.bonuses = bonuses

    def score_word(self, grid, positions, new_positions):
        word_mul = 1
        base = 0
        for (r,c) in positions:
            tile = grid[r][c]
            pts = tile.points
            if (r,c) in new_positions:
                bonus = self.bonuses.get((r,c))
                if bonus:
                    _, _, val, typ = bonus
                    if typ == 'L':
                        pts *= val
                    else:
                        word_mul *= val
            base += pts
        return base * word_mul

    def score_move(self, grid, placed_positions):
        words = []
        for (r,c) in placed_positions:
            # horizontal
            cl = c
            while cl>0 and grid[r][cl-1]:
                cl -= 1
            cr = c
            while cr<14 and grid[r][cr+1]:
                cr += 1
            if cr - cl >= 1:
                pos = [(r,cc) for cc in range(cl, cr+1)]
                if pos not in words: words.append(pos)
            # vertical
            rt = r
            while rt>0 and grid[rt-1][c]:
                rt -= 1
            rb = r
            while rb<14 and grid[rb+1][c]:
                rb += 1
            if rb - rt >= 1:
                pos = [(rr,c) for rr in range(rt, rb+1)]
                if pos not in words: words.append(pos)
        unique = []
        for w in words:
            if w not in unique: unique.append(w)
        total = 0
        new_set = set(placed_positions)
        for wpos in unique:
            total += self.score_word(grid, wpos, new_set)
        return total, unique

# ---------- TILE ----------
class Tile:
    def __init__(self, letter):
        self.letter = letter
        self.points = LETTER_DATA[letter][0]
        self.rect = pygame.Rect(0,0,0,0)
        self.on_board = False
        self.temp = False
        self.dragging = False
        self.last_click = 0
        self.assigned = None

    def display_letter(self):
        if self.letter == '_' and self.assigned:
            return self.assigned
        return self.letter

    def draw(self, surf, font_letter, font_pts):
        pygame.draw.rect(surf, COLORS['tile'], self.rect, border_radius=6)
        pygame.draw.rect(surf, COLORS['tile_border'], self.rect, 2, border_radius=6)
        l = font_letter.render(self.display_letter(), True, COLORS['text'])
        p = font_pts.render(str(self.points), True, COLORS['text'])
        surf.blit(l, l.get_rect(center=(self.rect.centerx, self.rect.centery-6)))
        surf.blit(p, (self.rect.right - 14, self.rect.bottom - 16))

# ---------- SCRABBLE ENGINE ----------
class ScrabbleEngine:
    def __init__(self, dictionary, scoring):
        self.grid = [[None]*15 for _ in range(15)]
        self.bag = [l for l,d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        self.player_rack = [Tile(self.bag.pop()) for _ in range(7)]
        self.ai_rack = [self.bag.pop() for _ in range(7)]
        self.player_score = 0
        self.ai_score = 0
        self.first_move = True
        self.turn = "PLAYER"
        self.bonuses = scoring.bonuses
        self.scoring = scoring
        self.dict = dictionary
        self.last_player_word = ""
        self.last_ai_word = ""
        self.last_player_def = ""
        self.last_ai_def = ""
        self.pass_count = 0
        self.move_history = []
        self.game_over = False

    def refill_rack(self, rack):
        while len(rack) < 7 and self.bag:
            rack.append(Tile(self.bag.pop()))

    def refill_ai(self):
        while len(self.ai_rack) < 7 and self.bag:
            self.ai_rack.append(self.bag.pop())

    def placed_this_turn(self):
        return [(r,c) for r in range(15) for c in range(15) if self.grid[r][c] and self.grid[r][c].temp]

    def validate_rules_basic(self):
        placed = self.placed_this_turn()
        if not placed:
            return False, "Brak położonych płytek."
        if self.first_move and (7,7) not in placed:
            return False, "Pierwszy ruch musi przechodzić przez środek planszy."
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) > 1 and len(cols) > 1:
            return False, "Płytki muszą być w jednej linii."
        if len(rows) == 1:
            r = next(iter(rows))
            cs = sorted(p[1] for p in placed)
            for c in range(cs[0], cs[-1]+1):
                if self.grid[r][c] is None and (r,c) not in placed:
                    return False, "Między skrajnymi pozycjami nie może być pustych pól."
        else:
            c = next(iter(cols))
            rs = sorted(p[0] for p in placed)
            for r in range(rs[0], rs[-1]+1):
                if self.grid[r][c] is None and (r,c) not in placed:
                    return False, "Między skrajnymi pozycjami nie może być pustych pól."
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
            positions = []
            while col<15 and self.grid[r][col]:
                word += self.grid[r][col].display_letter()
                positions.append((r,col))
                col += 1
            return word, positions
        else:
            row = r
            while row>0 and self.grid[row-1][c]:
                row -= 1
            word = ""
            positions = []
            while row<15 and self.grid[row][c]:
                word += self.grid[row][c].display_letter()
                positions.append((row,c))
                row += 1
            return word, positions

    def words_created_by_placing(self, r, c):
        words = []
        placed = self.placed_this_turn()
        if not placed:
            return []
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) == 1:
            w_main, pos_main = self.extract_word_from(r, c, horiz=True)
            if w_main: words.append((w_main, pos_main))
            w_cross, pos_cross = self.extract_word_from(r, c, horiz=False)
            if len(w_cross) > 1: words.append((w_cross, pos_cross))
        elif len(cols) == 1:
            w_main, pos_main = self.extract_word_from(r, c, horiz=False)
            if w_main: words.append((w_main, pos_main))
            w_cross, pos_cross = self.extract_word_from(r, c, horiz=True)
            if len(w_cross) > 1: words.append((w_cross, pos_cross))
        else:
            w1,p1 = self.extract_word_from(r,c,horiz=True)
            w2,p2 = self.extract_word_from(r,c,horiz=False)
            if w1: words.append((w1,p1))
            if w2 and w2 != w1: words.append((w2,p2))
        uniq = []
        seen = set()
        for w,pos in words:
            key = tuple(pos)
            if key not in seen:
                seen.add(key)
                uniq.append((w,pos))
        return uniq

    def score_move(self, placed_positions):
        return self.scoring.score_move(self.grid, placed_positions)

    def commit_move(self):
        ok, msg = self.validate_rules_basic()
        if not ok:
            return False, msg
        placed = self.placed_this_turn()
        if not placed:
            return False, "Brak położonych płytek."
        all_words = []
        for r,c in placed:
            ws = self.words_created_by_placing(r,c)
            for w,pos in ws:
                if (w,pos) not in all_words:
                    all_words.append((w,pos))
        for w,pos in all_words:
            if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                return False, f"Słowo '{w}' jest za krótkie."
            if not self.dict.is_word(w):
                return False, f"Słowo '{w}' nie znalezione w słowniku."
        pts, words = self.score_move(placed)
        rack_snapshot = [t.letter for t in self.player_rack]
        ai_snapshot = list(self.ai_rack)
        removed = []
        self.move_history.append((list(placed), removed, rack_snapshot, ai_snapshot, (self.player_score, self.ai_score), self.first_move))
        for r,c in placed:
            t = self.grid[r][c]
            t.temp = False
            t.on_board = True
            if t.letter == '_' and not t.assigned:
                t.assigned = 'A'  # automatyczne przypisanie, brak blokującego input()
            for rck in list(self.player_rack):
                if rck is t:
                    self.player_rack.remove(rck)
        self.player_score += pts
        self.first_move = False
        self.last_player_word = ", ".join([w for w,pos in all_words])
        self.last_player_def = self.dict.get_definition(self.last_player_word)
        print(f"Gracz: {self.last_player_word} -> {self.last_player_def}")
        self.refill_rack(self.player_rack)
        self.pass_count = 0
        self.turn = "AI"
        self.check_end_conditions()
        return True, f"Słowo '{self.last_player_word}' zaakceptowane. +{pts} pkt."

    def undo_last_move(self):
        if not self.move_history:
            return False, "Brak ruchu do cofnięcia."
        placed, removed, rack_snapshot, ai_snapshot, scores_snapshot, first_flag = self.move_history.pop()
        for (r,c) in placed:
            t = self.grid[r][c]
            if t:
                self.grid[r][c] = None
                self.bag.append(t.letter)
        random.shuffle(self.bag)
        self.player_rack = [Tile(l) for l in rack_snapshot]
        self.ai_rack = list(ai_snapshot)
        self.player_score, self.ai_score = scores_snapshot
        self.first_move = first_flag
        return True, "Cofnięto ostatni ruch."

    def exchange_letters(self, indices):
        if len(self.bag) < 7:
            return False, "W worku mniej niż 7 liter; wymiana niedozwolona."
        if not indices:
            return False, "Brak wybranych liter."
        removed = []
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self.player_rack):
                removed.append(self.player_rack.pop(idx))
        for t in removed:
            self.bag.append(t.letter)
        random.shuffle(self.bag)
        while len(self.player_rack) < 7 and self.bag:
            self.player_rack.append(Tile(self.bag.pop()))
        self.turn = "AI"
        self.pass_count = 0
        return True, f"Wymieniono {len(removed)} liter. Tracisz kolejkę."

    def ai_play(self, max_len=4, time_limit=0.8):
        start_time = time.time()
        best = None
        has_tiles = any(self.grid[r][c] for r in range(15) for c in range(15))
        anchors = set()
        if not has_tiles:
            anchors.add((7,7))
        else:
            for r in range(15):
                for c in range(15):
                    if self.grid[r][c]:
                        for dr,dc in [(0,1),(1,0),(0,-1),(-1,0)]:
                            nr, nc = r+dr, c+dc
                            if 0<=nr<15 and 0<=nc<15 and not self.grid[nr][nc]:
                                anchors.add((nr,nc))
        rack = list(self.ai_rack)
        letters_for_blank = [k for k in LETTER_DATA.keys() if k != '_']
        # helper simulate
        def simulate(placements):
            created = []
            for r,c,let,assigned in placements:
                t = Tile(let)
                if let == '_':
                    t.assigned = assigned
                self.grid[r][c] = t
                t.temp = True
                created.append((r,c,t))
            placed_positions = [(r,c) for r,c,_,_ in placements]
            all_words = []
            for (r,c) in placed_positions:
                ws = self.words_created_by_placing(r,c)
                for w,pos in ws:
                    if (w,pos) not in all_words:
                        all_words.append((w,pos))
            for w,pos in all_words:
                if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                    for r,c,t in created: self.grid[r][c] = None
                    return None
                if not self.dict.is_word(w):
                    for r,c,t in created: self.grid[r][c] = None
                    return None
            pts, words = self.score_move(placed_positions)
            for r,c,t in created: self.grid[r][c] = None
            return pts, words
        # generate candidates (limited)
        for anchor in anchors:
            if time.time() - start_time > time_limit: break
            ar, ac = anchor
            for horiz in [True, False]:
                for length in range(1, max_len+1):
                    if time.time() - start_time > time_limit: break
                    if horiz:
                        for start_c in range(ac - (length-1), ac+1):
                            start_r = ar
                            positions = [(start_r, start_c + i) for i in range(length)]
                            if any(not (0<=cc<15) for rr,cc in positions): continue
                            if (ar,ac) not in positions: continue
                            to_place = [(rr,cc) for rr,cc in positions if not self.grid[rr][cc]]
                            if not to_place: continue
                            if len(to_place) > len(rack): continue
                            indices = list(range(len(rack)))
                            for idxs in combinations(indices, len(to_place)):
                                if time.time() - start_time > time_limit: break
                                for perm in set(permutations(idxs)):
                                    placements = []
                                    for (pos_idx,(rr,cc)) in zip(perm, to_place):
                                        let = rack[pos_idx]
                                        if let == '_':
                                            assigned = 'A'
                                            placements.append((rr,cc,let,assigned))
                                        else:
                                            placements.append((rr,cc,let,None))
                                    res = simulate(placements)
                                    if res:
                                        pts, words = res
                                        key = (pts, sum(len(w) for w,pos in words))
                                        if not best or key > (best[0], best[1]):
                                            best = (pts, key[1], placements, words)
                    else:
                        for start_r in range(ar - (length-1), ar+1):
                            start_c = ac
                            positions = [(start_r + i, start_c) for i in range(length)]
                            if any(not (0<=rr<15) for rr,cc in positions): continue
                            if (ar,ac) not in positions: continue
                            to_place = [(rr,cc) for rr,cc in positions if not self.grid[rr][cc]]
                            if not to_place: continue
                            if len(to_place) > len(rack): continue
                            indices = list(range(len(rack)))
                            for idxs in combinations(indices, len(to_place)):
                                if time.time() - start_time > time_limit: break
                                for perm in set(permutations(idxs)):
                                    placements = []
                                    for (pos_idx,(rr,cc)) in zip(perm, to_place):
                                        let = rack[pos_idx]
                                        if let == '_':
                                            assigned = 'A'
                                            placements.append((rr,cc,let,assigned))
                                        else:
                                            placements.append((rr,cc,let,None))
                                    res = simulate(placements)
                                    if res:
                                        pts, words = res
                                        key = (pts, sum(len(w) for w,pos in words))
                                        if not best or key > (best[0], best[1]):
                                            best = (pts, key[1], placements, words)
        if best:
            pts, _, placements, words = best
            placed_positions = []
            for r,c,let,assigned in placements:
                t = Tile(let)
                if let == '_': t.assigned = assigned
                t.on_board = True
                t.temp = False
                self.grid[r][c] = t
                placed_positions.append((r,c))
                for i,x in enumerate(self.ai_rack):
                    if x == let:
                        self.ai_rack.pop(i)
                        break
            pts_final, words_final = self.score_move(placed_positions)
            self.ai_score += pts_final
            self.last_ai_word = ", ".join([w for w,pos in words_final])
            self.last_ai_def = self.dict.get_definition(self.last_ai_word)
            print(f"Komputer: {self.last_ai_word} -> {self.last_ai_def}")
            self.refill_ai()
            self.pass_count = 0
            self.turn = "PLAYER"
            self.check_end_conditions()
            return True
        else:
            print("Komputer: opuszcza kolejkę (brak poprawnego ruchu).")
            self.pass_count += 1
            self.turn = "PLAYER"
            self.check_end_conditions()
            return False

    def return_tile_to_bag(self, tile):
        for r in range(15):
            for c in range(15):
                if self.grid[r][c] is tile:
                    self.grid[r][c] = None
        self.bag.append(tile.letter)
        random.shuffle(self.bag)
        for rck in list(self.player_rack):
            if rck is tile:
                self.player_rack.remove(rck)
        self.refill_rack(self.player_rack)

    def check_end_conditions(self):
        if not self.bag and (len(self.player_rack) == 0 or len(self.ai_rack) == 0):
            self.finalize_game()
            return
        if self.pass_count >= 2:
            self.finalize_game()
            return

    def finalize_game(self):
        player_penalty = sum([t.points for t in self.player_rack])
        ai_penalty = sum([LETTER_DATA[l][0] if l != '_' else 0 for l in self.ai_rack])
        self.player_score -= player_penalty
        self.ai_score -= ai_penalty
        print("Koniec gry.")
        print(f"Punkty gracza: {self.player_score}, punkty AI: {self.ai_score}")
        self.game_over = True

# ---------- UI / APLIKACJA ----------
class ScrabbleApp:
    def __init__(self):
        self.screen = pygame.display.set_mode((1200, 850), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.dict = Dictionary()
        self.scoring = ScoringEngine(board_bonuses())
        self.engine = ScrabbleEngine(self.dict, self.scoring)
        self.dragging = None
        self.log_rect = pygame.Rect(40, 40, 380, 200)
        self.log_dragging = False
        self.log_offset = (0,0)
        self.log_lines = []
        self.update_fonts()
        self.engine.refill_rack(self.engine.player_rack)
        # queues for background tasks
        self.def_queue = queue.Queue()
        self.ai_queue = queue.Queue()

    def update_fonts(self):
        h = self.screen.get_height()
        self.font_bonus_big = pygame.font.SysFont('Arial', max(12, h//60), bold=True)
        self.font_bonus_small = pygame.font.SysFont('Arial', max(10, h//90), bold=True)
        self.font_tile = pygame.font.SysFont('Arial', max(20, h//28), bold=True)
        self.font_pts = pygame.font.SysFont('Arial', max(12, h//50), bold=True)
        self.font_main = pygame.font.SysFont('Arial', max(18, h//30), bold=True)
        self.font_small = pygame.font.SysFont('Arial', max(12, h//60))

    def layout(self):
        w,h = self.screen.get_size()
        cell = min(w//22, h//18)
        ox = 30
        oy = (h - 15*cell)//2
        return ox, oy, cell

    def add_log(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.log_lines.append(f"[{timestamp}] {text}")

    def draw_bonus(self, surf, rect, bonus):
        line1, line2, _, _ = bonus
        l1 = self.font_bonus_small.render(line1, True, COLORS['text'])
        l2 = self.font_bonus_big.render(line2, True, COLORS['text'])
        surf.blit(l1, l1.get_rect(center=(rect.centerx, rect.centery-8)))
        surf.blit(l2, l2.get_rect(center=(rect.centerx, rect.centery+8)))

    def draw_board(self):
        ox, oy, cs = self.layout()
        self.screen.fill(COLORS['bg'])
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*cs, oy + r*cs, cs, cs)
                pygame.draw.rect(self.screen, COLORS['board'], rect)
                pygame.draw.rect(self.screen, COLORS['grid'], rect, 1)
                bonus = self.engine.bonuses.get((r,c))
                if bonus and not self.engine.grid[r][c]:
                    self.draw_bonus(self.screen, rect, bonus)
                tile = self.engine.grid[r][c]
                if tile:
                    tile.rect = pygame.Rect(rect.x+4, rect.y+4, cs-8, cs-8)
                    tile.draw(self.screen, self.font_tile, self.font_pts)
        rack_y = self.screen.get_height() - cs - 20
        for i, t in enumerate(self.engine.player_rack):
            if not t.on_board and not t.dragging:
                t.rect = pygame.Rect(ox + i*(cs+10), rack_y, cs, cs)
                t.draw(self.screen, self.font_tile, self.font_pts)
        ui_x = ox + 15*cs + 30
        self.screen.blit(self.font_main.render(f"PUNKTY: {self.engine.player_score}", True, COLORS['text']), (ui_x, 60))
        self.screen.blit(self.font_main.render(f"AI: {self.engine.ai_score}", True, COLORS['text']), (ui_x, 110))
        self.screen.blit(self.font_pts.render(f"W worku: {len(self.engine.bag)}", True, COLORS['text']), (ui_x, 160))
        placed = self.engine.placed_this_turn()
        preview_score = 0
        preview_words = []
        invalid = False
        if placed:
            preview_score, preview_words = self.engine.score_move(placed)
            for w,pos in preview_words:
                if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                    invalid = True
                elif not self.dict.is_word(w):
                    invalid = True
        panel_rect = pygame.Rect(ui_x, self.screen.get_height()-260, 360, 240)
        pygame.draw.rect(self.screen, COLORS['panel'], panel_rect, border_radius=8)
        self.screen.blit(self.font_bonus_big.render("Słowo gracza", True, COLORS['text']), (ui_x+10, self.screen.get_height()-250))
        self.screen.blit(self.font_bonus_big.render(self.engine.last_player_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-225))
        self.screen.blit(self.font_bonus_big.render("Słowo komputera", True, COLORS['text']), (ui_x+10, self.screen.get_height()-190))
        self.screen.blit(self.font_bonus_big.render(self.engine.last_ai_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-165))
        pv_text = f"Podgląd pkt: {preview_score}"
        pv_col = COLORS['invalid'] if invalid else COLORS['text']
        self.screen.blit(self.font_main.render(pv_text, True, pv_col), (ui_x+10, self.screen.get_height()-135))
        self.ok_btn = pygame.Rect(ui_x, 200, 140, 60)
        pygame.draw.rect(self.screen, COLORS['button'], self.ok_btn, border_radius=8)
        self.screen.blit(self.font_main.render("ZATWIERDŹ", True, (255,255,255)), (ui_x+8, 212))
        self.pass_btn = pygame.Rect(ui_x+150, 220, 160, 30)
        pygame.draw.rect(self.screen, COLORS['button_pass'], self.pass_btn, border_radius=6)
        self.screen.blit(self.font_pts.render("Opuszczam 1 kolejkę", True, (0,0,0)), (ui_x+155, 224))
        self.exchange_btn = pygame.Rect(ui_x, 270, 140, 30)
        pygame.draw.rect(self.screen, COLORS['button_pass'], self.exchange_btn, border_radius=6)
        self.screen.blit(self.font_pts.render("Wymień litery", True, (0,0,0)), (ui_x+10, 274))
        self.undo_btn = pygame.Rect(ui_x+150, 270, 160, 30)
        pygame.draw.rect(self.screen, COLORS['button_pass'], self.undo_btn, border_radius=6)
        self.screen.blit(self.font_pts.render("Cofnij ruch", True, (0,0,0)), (ui_x+170, 274))
        self.draw_log_window()
        if invalid and placed:
            for (r,c) in placed:
                rect = pygame.Rect(ox + c*cs, oy + r*cs, cs, cs)
                pygame.draw.rect(self.screen, COLORS['invalid'], rect, 3)
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

    def handle_background_queues(self):
        try:
            while True:
                word, def_text = self.def_queue.get_nowait()
                if def_text:
                    print(f"Definicja {word}: {def_text}")
        except queue.Empty:
            pass
        try:
            moved = self.ai_queue.get_nowait()
            if moved:
                self.add_log(f"Komputer: {self.engine.last_ai_word}")
                self.add_log("Definicja AI wypisana do terminala")
                print(f"Definicja komputera: {self.engine.last_ai_def}")
            else:
                self.add_log("Komputer opuścił kolejkę")
        except queue.Empty:
            pass

    def start_fetch_definition(self, word):
        def worker(w, out_q, dictionary):
            d = dictionary.get_definition(w)
            out_q.put((w, d))
        threading.Thread(target=worker, args=(word, self.def_queue, self.dict), daemon=True).start()

    def start_ai_thread(self):
        def worker(engine, out_q):
            moved = engine.ai_play(time_limit=0.8)
            out_q.put(moved)
        threading.Thread(target=worker, args=(self.engine, self.ai_queue), daemon=True).start()

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
                self.update_fonts()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    self.update_fonts()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.log_rect.collidepoint(ev.pos):
                    self.log_dragging = True
                    mx, my = ev.pos
                    self.log_offset = (mx - self.log_rect.x, my - self.log_rect.y)
                if self.engine.turn == "PLAYER" and not self.engine.game_over:
                    pos = ev.pos
                    now = pygame.time.get_ticks()
                    ox, oy, cs = self.layout()
                    col = (pos[0]-ox)//cs
                    row = (pos[1]-oy)//cs
                    if 0<=row<15 and 0<=col<15:
                        t = self.engine.grid[row][col]
                        if t and t.temp:
                            if now - t.last_click < 400:
                                self.engine.grid[row][col] = None
                                self.engine.return_tile_to_bag(t)
                                self.add_log(f"Cofnięto {t.display_letter()} -> do woreczka")
                                print(f"Cofnięto {t.display_letter()} -> do woreczka")
                                return
                            t.last_click = now
                    for i, t in enumerate(self.engine.player_rack):
                        if t.rect.collidepoint(pos):
                            self.dragging = t
                            t.dragging = True
                    if self.ok_btn.collidepoint(pos):
                        ok, msg = self.engine.commit_move()
                        self.add_log(msg)
                        print(msg)
                        if ok:
                            self.add_log(f"Gracz: {self.engine.last_player_word}")
                            self.add_log("Definicja wypisana do terminala")
                            print(f"Definicja gracza: {self.engine.last_player_def}")
                            self.start_ai_thread()
                    if self.pass_btn.collidepoint(pos):
                        self.add_log("Gracz: opuszcza 1 kolejkę")
                        print("Gracz: opuszcza 1 kolejkę")
                        self.engine.pass_count += 1
                        self.engine.turn = "AI"
                        self.start_ai_thread()
                    if self.exchange_btn.collidepoint(pos):
                        if len(self.engine.bag) < 7:
                            self.add_log("W worku mniej niż 7 liter; wymiana niedozwolona.")
                            print("W worku mniej niż 7 liter; wymiana niedozwolona.")
                        else:
                            # prosty exchange: wymień losowo 2 litery (bez inputu)
                            n = min(2, len(self.engine.player_rack))
                            indices = random.sample(range(len(self.engine.player_rack)), n)
                            ok, msg = self.engine.exchange_letters(indices)
                            self.add_log(msg)
                            print(msg)
                            self.start_ai_thread()
                    if self.undo_btn.collidepoint(pos):
                        ok, msg = self.engine.undo_last_move()
                        self.add_log(msg)
                        print(msg)
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
            self.handle_background_queues()
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    ScrabbleApp().run()

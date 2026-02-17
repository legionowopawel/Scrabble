# scrabble_improved.py
# Wersja: Scrabble Edu - Improved
# Wymagania: pygame, requests
# Uruchom: python scrabble_improved.py

import pygame
import sys
import random
import requests
import time
import re
import html
from collections import defaultdict, namedtuple
from itertools import permutations, combinations, product

# ---------- KONFIGURACJA ----------
pygame.init()
pygame.display.set_caption("Scrabmania Edu - Scrabble (improved)")

# Kolory
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
    'invalid': (200, 80, 80),
    'highlight': (200, 200, 80)
}

# Litery: (punkty, liczba)
LETTER_DATA = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 'D': (2, 3),
    'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 'H': (3, 2), 'I': (1, 8),
    'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5),
    'Ń': (7, 1), 'O': (1, 6), 'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4),
    'Ś': (5, 1), 'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5),
    'Ź': (9, 1), 'Ż': (5, 1),
    '_': (0, 2)  # blank/joker: 0 points, 2 in bag
}

# Dozwolone jednopłytkowe słowa (opcjonalne)
ALLOWED_SINGLE = set(['A','I','O','U','W','Z','S','Y'])

# Bonusy: (label1, label2, value, type 'L' or 'W')
def board_bonuses():
    b = {}
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

# ---------- STRUKTURY ----------
Placement = namedtuple('Placement', ['r','c','tile'])  # tile: Tile object

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
        # online with cache
        if w in self.cache:
            return self.cache[w]
        try:
            r = requests.get(f"https://sjp.pl/{w.lower()}", timeout=3)
            text = r.text.lower()
            ok = ("dopuszczalne w grach" in text) or ("hasło" in text) or ("znaczenie" in text)
            if "nie występuje w słowniku" in text or "nie znaleziono" in text:
                ok = False
            self.cache[w] = ok
            return ok
        except Exception:
            # fail-safe: treat as valid but log
            print("Uwaga: brak połączenia z sjp.pl — walidacja online pominięta (fail-safe).")
            self.cache[w] = True
            return True

    def get_definition(self, word):
        if not word: return "Brak słowa"
        w = word.upper()
        if self.local:
            return "Definicja lokalna niedostępna."
        try:
            r = requests.get(f"https://sjp.pl/{w.lower()}", timeout=3)
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
        self.bonuses = bonuses  # dict (r,c) -> (l1,l2,val,type)

    def score_word(self, grid, word_positions, new_positions):
        """
        grid: 15x15 with Tile objects (Tile.letter, Tile.points)
        word_positions: list of (r,c) positions forming the word in order
        new_positions: set of positions that were newly placed this turn
        Returns integer score for that word
        Rules:
         - sum letter points (for blanks use 0)
         - letter bonuses apply only to newly placed tiles
         - word multipliers multiply the whole word; if multiple word multipliers from newly placed tiles, multiply them
        """
        word_mul = 1
        base = 0
        for (r,c) in word_positions:
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
        """
        placed_positions: list of (r,c) newly placed positions
        Compute score for the move: sum of scores of all words created/extended by the placed tiles.
        """
        words = []
        # For each placed tile, find main word and cross word if any
        for (r,c) in placed_positions:
            # horizontal word
            # find leftmost
            cl = c
            while cl>0 and grid[r][cl-1]:
                cl -= 1
            cr = c
            while cr<14 and grid[r][cr+1]:
                cr += 1
            if cr - cl >= 1:  # length >=2
                pos = [(r,cc) for cc in range(cl, cr+1)]
                if pos not in words:
                    words.append(pos)
            # vertical word
            rt = r
            while rt>0 and grid[rt-1][c]:
                rt -= 1
            rb = r
            while rb<14 and grid[rb+1][c]:
                rb += 1
            if rb - rt >= 1:
                pos = [(rr,c) for rr in range(rt, rb+1)]
                if pos not in words:
                    words.append(pos)
        # remove duplicates
        unique = []
        for w in words:
            if w not in unique:
                unique.append(w)
        total = 0
        new_set = set(placed_positions)
        for wpos in unique:
            total += self.score_word(grid, wpos, new_set)
        return total, unique

# ---------- TILE ----------
class Tile:
    def __init__(self, letter):
        self.letter = letter  # '_' for blank
        self.points = LETTER_DATA[letter][0]
        self.rect = pygame.Rect(0,0,0,0)
        self.on_board = False
        self.temp = False
        self.dragging = False
        self.last_click = 0
        self.assigned = None  # for blank: assigned letter when placed

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

# ---------- SCRABBLE ENGINE (reguły + ruchy gracza) ----------
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
        self.pass_count = 0  # consecutive passes (for end game)
        self.move_history = []  # for undo: list of (placed_positions, removed_tiles, player_rack_snapshot, ai_rack_snapshot, scores_snapshot, first_move_flag)
        self.game_over = False

    # ---------- pomocnicze ----------
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
        if self.first_move:
            if (7,7) not in placed:
                return False, "Pierwszy ruch musi przechodzić przez środek planszy."
        # all in one line
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) > 1 and len(cols) > 1:
            return False, "Płytki muszą być w jednej linii."
        # continuity: between min and max there must be no gaps
        if len(rows) == 1:
            r = rows.pop()
            cs = sorted(p[1] for p in placed)
            if any(self.grid[r][c] is None and (r,c) not in placed for c in range(cs[0], cs[-1]+1)):
                return False, "Między skrajnymi pozycjami nie może być pustych pól."
        else:
            c = cols.pop()
            rs = sorted(p[0] for p in placed)
            if any(self.grid[r][c] is None and (r,c) not in placed for r in range(rs[0], rs[-1]+1)):
                return False, "Między skrajnymi pozycjami nie może być pustych pól."
        # touching existing tiles (if not first move)
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
        # main orientation detection based on all placed tiles
        placed = self.placed_this_turn()
        if not placed:
            return []
        rows = set(p[0] for p in placed)
        cols = set(p[1] for p in placed)
        if len(rows) == 1:
            # horizontal main
            w_main, pos_main = self.extract_word_from(r, c, horiz=True)
            if w_main: words.append((w_main, pos_main))
            # vertical cross
            w_cross, pos_cross = self.extract_word_from(r, c, horiz=False)
            if len(w_cross) > 1: words.append((w_cross, pos_cross))
        elif len(cols) == 1:
            w_main, pos_main = self.extract_word_from(r, c, horiz=False)
            if w_main: words.append((w_main, pos_main))
            w_cross, pos_cross = self.extract_word_from(r, c, horiz=True)
            if len(w_cross) > 1: words.append((w_cross, pos_cross))
        else:
            # single tile placed
            w1, p1 = self.extract_word_from(r, c, horiz=True)
            w2, p2 = self.extract_word_from(r, c, horiz=False)
            if w1: words.append((w1, p1))
            if w2 and w2 != w1: words.append((w2, p2))
        # unique by positions
        uniq = []
        seen = set()
        for w,pos in words:
            key = tuple(pos)
            if key not in seen:
                seen.add(key)
                uniq.append((w,pos))
        return uniq

    def score_move(self, placed_positions):
        # placed_positions: list of (r,c)
        total = 0
        words = []
        new_set = set(placed_positions)
        # collect all words created by placed tiles
        for (r,c) in placed_positions:
            ws = self.words_created_by_placing(r,c)
            for w,pos in ws:
                if tuple(pos) not in [tuple(x[1]) for x in words]:
                    words.append((w,pos))
        # score each word using ScoringEngine
        for w,pos in words:
            total += self.scoring.score_word(self.grid, pos, new_set)
        return total, words

    # ---------- commit_move (player) ----------
    def commit_move(self):
        ok, msg = self.validate_rules_basic()
        if not ok:
            return False, msg
        placed = self.placed_this_turn()
        if not placed:
            return False, "Brak położonych płytek."
        # gather all words created
        all_words = []
        for r,c in placed:
            ws = self.words_created_by_placing(r,c)
            for w,pos in ws:
                if (w,pos) not in all_words:
                    all_words.append((w,pos))
        # validate words: length and dictionary
        for w,pos in all_words:
            if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                return False, f"Słowo '{w}' jest za krótkie."
            if not self.dict.is_word(w):
                return False, f"Słowo '{w}' nie znalezione w słowniku."
        # compute score
        pts, words = self.score_move(placed)
        # save history for undo
        rack_snapshot = [t.letter for t in self.player_rack]
        ai_snapshot = list(self.ai_rack)
        removed = []  # none removed from board in this simplified model
        self.move_history.append((list(placed), removed, rack_snapshot, ai_snapshot, (self.player_score, self.ai_score), self.first_move))
        # finalize tiles: mark on_board and remove from rack
        for r,c in placed:
            t = self.grid[r][c]
            t.temp = False
            t.on_board = True
            # if blank, ensure assigned letter exists (if not, ask)
            if t.letter == '_' and not t.assigned:
                # ask in terminal for assigned letter
                assigned = None
                while not assigned:
                    assigned = input(f"Przypisz literę dla blanku na pozycji ({r},{c}) (wielka litera): ").strip().upper()
                    if not assigned or len(assigned) != 1 or assigned not in LETTER_DATA or assigned == '_':
                        print("Nieprawidłowa litera. Spróbuj ponownie.")
                        assigned = None
                t.assigned = assigned
            # remove tile object from player's rack if present
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
        # check end game
        self.check_end_conditions()
        return True, f"Słowo '{self.last_player_word}' zaakceptowane. +{pts} pkt."

    # ---------- undo last move ----------
    def undo_last_move(self):
        if not self.move_history:
            return False, "Brak ruchu do cofnięcia."
        placed, removed, rack_snapshot, ai_snapshot, scores_snapshot, first_flag = self.move_history.pop()
        # remove placed tiles from board and return to bag
        for (r,c) in placed:
            t = self.grid[r][c]
            if t:
                # return letter to bag
                self.bag.append(t.letter)
                self.grid[r][c] = None
        random.shuffle(self.bag)
        # restore racks and scores
        self.player_rack = [Tile(l) for l in rack_snapshot]
        self.ai_rack = list(ai_snapshot)
        self.player_score, self.ai_score = scores_snapshot
        self.first_move = first_flag
        return True, "Cofnięto ostatni ruch."

    # ---------- exchange letters ----------
    def exchange_letters(self, indices):
        # indices: list of indices in player_rack to exchange
        if len(self.bag) < 7:
            return False, "W worku mniej niż 7 liter; wymiana niedozwolona."
        if not indices:
            return False, "Brak wybranych liter."
        # remove selected letters to temp, put back to bag, draw new
        removed = []
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self.player_rack):
                removed.append(self.player_rack.pop(idx))
        # return letters to bag
        for t in removed:
            self.bag.append(t.letter)
        random.shuffle(self.bag)
        # draw same number
        while len(self.player_rack) < 7 and self.bag:
            self.player_rack.append(Tile(self.bag.pop()))
        # cost: lose turn
        self.turn = "AI"
        self.pass_count = 0
        return True, f"Wymieniono {len(removed)} liter. Tracisz kolejkę."

    # ---------- AI (brute-force search, maximize score) ----------
    def ai_play(self, max_len=4):
        """
        AI strategy:
         - generate candidate placements by:
           * for each anchor (existing tile) try to place sequences of 1..max_len tiles from ai_rack in adjacent empty cells forming words
           * if board empty, try center placements of length 2..max_len
         - for each candidate simulate placement, validate all created words, compute score using scoring engine
         - choose candidate with max score (prefer longer words on tie)
         - if none valid, AI passes
        """
        time.sleep(0.6)
        best = None  # (score, placements, words, rack_changes)
        # helper to simulate placement
        def simulate_and_score(placements):
            # placements: list of (r,c,letter,assigned_for_blank)
            # create tile objects and place
            created_tiles = []
            for r,c,let,assigned in placements:
                t = Tile(let)
                if let == '_':
                    t.assigned = assigned
                self.grid[r][c] = t
                t.temp = True
                created_tiles.append((r,c,t))
            # collect words
            placed_positions = [(r,c) for r,c,_,_ in placements]
            all_words = []
            for (r,c) in placed_positions:
                ws = self.words_created_by_placing(r,c)
                for w,pos in ws:
                    if (w,pos) not in all_words:
                        all_words.append((w,pos))
            # validate
            for w,pos in all_words:
                if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                    # revert
                    for r,c,t in created_tiles:
                        self.grid[r][c] = None
                    return None
                if not self.dict.is_word(w):
                    for r,c,t in created_tiles:
                        self.grid[r][c] = None
                    return None
            # compute score
            pts, words = self.score_move(placed_positions)
            # revert (we only simulate)
            for r,c,t in created_tiles:
                self.grid[r][c] = None
            return pts, all_words

        # gather anchors (cells adjacent to existing tiles) or center if empty
        anchors = set()
        has_tiles = any(self.grid[r][c] for r in range(15) for c in range(15))
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
        # generate candidate placements around anchors
        rack_letters = list(self.ai_rack)
        # include blanks: for blanks we will try assigned letters A..Z (from LETTER_DATA keys excluding '_')
        letters_for_blank = [k for k in LETTER_DATA.keys() if k != '_']
        # limit search: try lengths 1..max_len but prefer >=2
        for anchor in anchors:
            ar, ac = anchor
            # try horizontal and vertical placements that include anchor
            for horiz in [True, False]:
                for length in range(1, max_len+1):
                    # positions for a word of given length that include anchor
                    if horiz:
                        for start_c in range(ac - (length-1), ac+1):
                            start_r = ar
                            positions = [(start_r, start_c + i) for i in range(length)]
                            if any(not (0<=cc<15) for rr,cc in positions): continue
                            # must include anchor
                            if (ar,ac) not in positions: continue
                            # ensure positions are empty or existing tile (we only place on empty)
                            conflict = False
                            for rr,cc in positions:
                                if self.grid[rr][cc] and not self.grid[rr][cc].temp:
                                    # existing tile is fine (we extend), but we cannot place over existing tile
                                    pass
                            # build list of empty positions where we need to place letters
                            to_place = [(rr,cc) for rr,cc in positions if not self.grid[rr][cc]]
                            if not to_place:
                                continue
                            # limit number of tiles placed to len(ai_rack)
                            if len(to_place) > len(self.ai_rack): continue
                            # generate permutations of letters from rack for these slots (combinatorial explosion -> limit)
                            # choose combinations of rack indices
                            indices = list(range(len(self.ai_rack)))
                            for idxs in combinations(indices, len(to_place)):
                                # for each permutation of chosen letters
                                for perm in set(permutations(idxs)):
                                    placements = []
                                    valid_perm = True
                                    for (pos,(rr,cc)) in zip(perm, to_place):
                                        let = self.ai_rack[pos]
                                        if let == '_':
                                            # try assigned letters limited set (A..Z)
                                            # to limit, try only vowels+common consonants
                                            assigned_candidates = ['A','E','I','O','U','R','S','T','N','L']
                                            assigned = assigned_candidates[0]
                                            # we'll try only first candidate to limit complexity; AI could try more
                                            placements.append((rr,cc,let,assigned))
                                        else:
                                            placements.append((rr,cc,let,None))
                                    # simulate
                                    res = simulate_and_score(placements)
                                    if res:
                                        pts, words = res
                                        # prefer longer words and higher pts
                                        score_key = (pts, len("".join([w for w,pos in words])))
                                        if not best or score_key > (best[0], best[1]):
                                            best = (pts, score_key[1], placements, words)
                    else:
                        for start_r in range(ar - (length-1), ar+1):
                            start_c = ac
                            positions = [(start_r + i, start_c) for i in range(length)]
                            if any(not (0<=rr<15) for rr,cc in positions): continue
                            if (ar,ac) not in positions: continue
                            to_place = [(rr,cc) for rr,cc in positions if not self.grid[rr][cc]]
                            if not to_place: continue
                            if len(to_place) > len(self.ai_rack): continue
                            indices = list(range(len(self.ai_rack)))
                            for idxs in combinations(indices, len(to_place)):
                                for perm in set(permutations(idxs)):
                                    placements = []
                                    for (pos,(rr,cc)) in zip(perm, to_place):
                                        let = self.ai_rack[pos]
                                        if let == '_':
                                            assigned_candidates = ['A','E','I','O','U','R','S','T','N','L']
                                            assigned = assigned_candidates[0]
                                            placements.append((rr,cc,let,assigned))
                                        else:
                                            placements.append((rr,cc,let,None))
                                    res = simulate_and_score(placements)
                                    if res:
                                        pts, words = res
                                        score_key = (pts, len("".join([w for w,pos in words])))
                                        if not best or score_key > (best[0], best[1]):
                                            best = (pts, score_key[1], placements, words)
        # if best found, commit it
        if best:
            pts, _, placements, words = best
            # place tiles permanently and update ai_rack and score
            placed_positions = []
            used_indices = []
            for r,c,let,assigned in placements:
                t = Tile(let)
                if let == '_':
                    t.assigned = assigned
                t.on_board = True
                t.temp = False
                self.grid[r][c] = t
                placed_positions.append((r,c))
                # remove one occurrence of letter from ai_rack
                for i, x in enumerate(self.ai_rack):
                    if x == let:
                        used_indices.append(i)
                        self.ai_rack.pop(i)
                        break
            # compute final score (including cross words)
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
            # AI passes
            print("Komputer: opuszcza kolejkę (brak poprawnego ruchu).")
            self.pass_count += 1
            self.turn = "PLAYER"
            self.check_end_conditions()
            return False

    # ---------- return tile to bag (on undo or double-click) ----------
    def return_tile_to_bag(self, tile):
        # remove tile from board if present
        for r in range(15):
            for c in range(15):
                if self.grid[r][c] is tile:
                    self.grid[r][c] = None
        # return letter to bag and shuffle
        self.bag.append(tile.letter)
        random.shuffle(self.bag)
        # remove tile object from rack if present
        for rck in list(self.player_rack):
            if rck is tile:
                self.player_rack.remove(rck)
        self.refill_rack(self.player_rack)

    # ---------- end game detection ----------
    def check_end_conditions(self):
        # end if bag empty and one player has empty rack
        if not self.bag and (len(self.player_rack) == 0 or len(self.ai_rack) == 0):
            self.finalize_game()
            return
        # if both players passed twice consecutively
        if self.pass_count >= 2:
            self.finalize_game()
            return

    def finalize_game(self):
        # subtract points for remaining tiles
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
        # board
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
        # rack
        rack_y = self.screen.get_height() - cs - 20
        for i, t in enumerate(self.engine.player_rack):
            if not t.on_board and not t.dragging:
                t.rect = pygame.Rect(ox + i*(cs+10), rack_y, cs, cs)
                t.draw(self.screen, self.font_tile, self.font_pts)
        # side panel
        ui_x = ox + 15*cs + 30
        self.screen.blit(self.font_main.render(f"PUNKTY: {self.engine.player_score}", True, COLORS['text']), (ui_x, 60))
        self.screen.blit(self.font_main.render(f"AI: {self.engine.ai_score}", True, COLORS['text']), (ui_x, 110))
        self.screen.blit(self.font_pts.render(f"W worku: {len(self.engine.bag)}", True, COLORS['text']), (ui_x, 160))
        # preview score for current tentative placement
        placed = self.engine.placed_this_turn()
        preview_score = 0
        preview_words = []
        invalid = False
        if placed:
            preview_score, preview_words = self.engine.score_move(placed)
            # validate words quickly
            for w,pos in preview_words:
                if len(w) == 1 and w.upper() not in ALLOWED_SINGLE:
                    invalid = True
                elif not self.dict.is_word(w):
                    invalid = True
        # panel words (only words, no definitions)
        panel_rect = pygame.Rect(ui_x, self.screen.get_height()-260, 360, 240)
        pygame.draw.rect(self.screen, COLORS['panel'], panel_rect, border_radius=8)
        self.screen.blit(self.font_bonus_big.render("Słowo gracza", True, COLORS['text']), (ui_x+10, self.screen.get_height()-250))
        self.screen.blit(self.font_bonus_big.render(self.engine.last_player_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-225))
        self.screen.blit(self.font_bonus_big.render("Słowo komputera", True, COLORS['text']), (ui_x+10, self.screen.get_height()-190))
        self.screen.blit(self.font_bonus_big.render(self.engine.last_ai_word, True, COLORS['text']), (ui_x+10, self.screen.get_height()-165))
        # preview
        pv_text = f"Podgląd pkt: {preview_score}"
        pv_col = COLORS['invalid'] if invalid else COLORS['text']
        self.screen.blit(self.font_main.render(pv_text, True, pv_col), (ui_x+10, self.screen.get_height()-135))
        # buttons: OK, PASS, EXCHANGE, UNDO
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
        # log
        self.draw_log_window()
        # highlight invalid placed tiles
        if invalid and placed:
            for (r,c) in placed:
                rect = pygame.Rect(ox + c*cs, oy + r*cs, cs, cs)
                pygame.draw.rect(self.screen, COLORS['invalid'], rect, 3)
        # draw dragging tile on top
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
                # player interactions only when player's turn and game not over
                if self.engine.turn == "PLAYER" and not self.engine.game_over:
                    pos = ev.pos
                    now = pygame.time.get_ticks()
                    ox, oy, cs = self.layout()
                    # double-click on board tile placed this turn -> return to bag
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
                    # click on rack to start dragging
                    for i, t in enumerate(self.engine.player_rack):
                        if t.rect.collidepoint(pos):
                            self.dragging = t
                            t.dragging = True
                    # click ZATWIERDŹ
                    if self.ok_btn.collidepoint(pos):
                        ok, msg = self.engine.commit_move()
                        self.add_log(msg)
                        print(msg)
                        if ok:
                            self.add_log(f"Gracz: {self.engine.last_player_word}")
                            self.add_log("Definicja wypisana do terminala")
                            print(f"Definicja gracza: {self.engine.last_player_def}")
                            # AI move
                            moved = self.engine.ai_play()
                            if moved:
                                self.add_log(f"Komputer: {self.engine.last_ai_word}")
                                self.add_log("Definicja AI wypisana do terminala")
                                print(f"Definicja komputera: {self.engine.last_ai_def}")
                            else:
                                self.add_log("Komputer opuścił kolejkę")
                    # click PASS
                    if self.pass_btn.collidepoint(pos):
                        self.add_log("Gracz: opuszcza 1 kolejkę")
                        print("Gracz: opuszcza 1 kolejkę")
                        self.engine.pass_count += 1
                        self.engine.turn = "AI"
                        moved = self.engine.ai_play()
                        if moved:
                            self.add_log(f"Komputer: {self.engine.last_ai_word}")
                            self.add_log("Definicja AI wypisana do terminala")
                            print(f"Definicja komputera: {self.engine.last_ai_def}")
                        else:
                            self.add_log("Komputer opuścił kolejkę")
                    # click EXCHANGE
                    if self.exchange_btn.collidepoint(pos):
                        # simple terminal-based exchange: ask indices
                        if len(self.engine.bag) < 7:
                            self.add_log("W worku mniej niż 7 liter; wymiana niedozwolona.")
                            print("W worku mniej niż 7 liter; wymiana niedozwolona.")
                        else:
                            print("Twoje litery:", " ".join([t.letter for t in self.engine.player_rack]))
                            idxs = input("Podaj indeksy liter do wymiany (np. 0 2 3) lub pusty aby anulować: ").strip()
                            if idxs:
                                try:
                                    indices = sorted([int(x) for x in idxs.split()], reverse=True)
                                    ok, msg = self.engine.exchange_letters(indices)
                                    self.add_log(msg)
                                    print(msg)
                                    # after exchange AI moves
                                    moved = self.engine.ai_play()
                                    if moved:
                                        self.add_log(f"Komputer: {self.engine.last_ai_word}")
                                        self.add_log("Definicja AI wypisana do terminala")
                                        print(f"Definicja komputera: {self.engine.last_ai_def}")
                                    else:
                                        self.add_log("Komputer opuścił kolejkę")
                                except Exception as e:
                                    print("Błąd wymiany:", e)
                    # click UNDO
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
                        # place tile
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
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    ScrabbleApp().run()

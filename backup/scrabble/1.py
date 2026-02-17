import requests
import random

class ScrabbleBoard:
    def __init__(self):
        self.size = 15
        self.grid = [[" " for _ in range(15)] for _ in range(15)]
        self.multipliers = self._set_multipliers()

    def _set_multipliers(self):
        m = {}
        # TW - Triple Word, DW - Double Word, TL - Triple Letter, DL - Double Letter
        tw = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        dw = [(1,1), (2,2), (3,3), (4,4), (1,13), (2,12), (3,11), (4,10), 
              (13,1), (12,2), (11,3), (10,4), (13,13), (12,12), (11,11), (10,10), (7,7)]
        tl = [(1,5), (1,9), (5,1), (5,5), (5,9), (5,13), (9,1), (9,5), (9,9), (9,13), (13,5), (13,9)]
        dl = [(0,3), (0,11), (2,6), (2,8), (3,0), (3,7), (3,14), (6,2), (6,6), (6,8), (6,12), 
              (7,3), (7,11), (8,2), (8,6), (8,8), (8,12), (11,0), (11,7), (11,14), (12,6), (12,8), (14,3), (14,11)]
        
        for pos in tw: m[pos] = "TW"
        for pos in dw: m[pos] = "DW"
        for pos in tl: m[pos] = "TL"
        for pos in dl: m[pos] = "DL"
        return m

    def display(self):
        print("\n    " + "  ".join([f"{i:02}" for i in range(15)]))
        for r in range(15):
            row_display = []
            for c in range(15):
                if self.grid[r][c] != " ":
                    row_display.append(f" {self.grid[r][c]} ")
                else:
                    m = self.multipliers.get((r, c), "..")
                    row_display.append(m if len(m)==2 else f" {m} ")
            print(f"{r:02} [" + " ".join(row_display) + "]")

class ScrabbleGame:
    # Polskie wartości liter i ich ilości w worku
    LETTER_DATA = {
        'A': (1, 9), 'E': (1, 7), 'I': (1, 8), 'O': (1, 6), 'U': (3, 2), 'Y': (2, 4), 
        'Z': (1, 5), 'L': (2, 3), 'N': (1, 5), 'R': (1, 4), 'S': (1, 4), 'W': (1, 4),
        'D': (2, 3), 'G': (2, 2), 'K': (2, 3), 'M': (2, 3), 'P': (2, 3), 'T': (2, 3),
        'B': (3, 2), 'C': (2, 3), 'H': (3, 2), 'J': (3, 2), 'Ł': (3, 2), 'Ó': (5, 1), 
        'Ś': (5, 1), 'Ć': (6, 1), 'Ę': (5, 1), 'Ą': (5, 1), 'Ń': (7, 1), 'Ź': (9, 1), 'Ż': (5, 1)
    }

    def __init__(self):
        self.board = ScrabbleBoard()
        self.bag = self._initialize_bag()
        self.rack = []
        self.score = 0
        self.first_move = True
        self.fill_rack()

    def _initialize_bag(self):
        bag = []
        for char, (val, count) in self.LETTER_DATA.items():
            bag.extend([char] * count)
        random.shuffle(bag)
        return bag

    def fill_rack(self):
        while len(self.rack) < 7 and self.bag:
            self.rack.append(self.bag.pop())

    def is_valid_sjp(self, word):
        url = f"https://sjp.pl/{word.lower()}"
        try:
            r = requests.get(url, timeout=5)
            return "dopuszczalne w grach" in r.text
        except:
            return False

    def can_place_word(self, word, r, c, direction):
        if direction not in ['H', 'V']: return False
        
        has_contact = False
        temp_rack = list(self.rack)
        
        for i, letter in enumerate(word):
            curr_r = r + (i if direction == 'V' else 0)
            curr_c = c + (i if direction == 'H' else 0)

            if not (0 <= curr_r < 15 and 0 <= curr_c < 15): return False

            board_tile = self.board.grid[curr_r][curr_c]
            
            if board_tile != " ":
                if board_tile != letter: return False
                has_contact = True
            else:
                if letter not in temp_rack: return False
                temp_rack.remove(letter)
                
            # Sprawdzenie czy styka się z czymkolwiek obok
            for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < 15 and 0 <= nc < 15 and self.board.grid[nr][nc] != " ":
                    has_contact = True

        if self.first_move:
            # Pierwszy ruch musi przechodzić przez środek (7,7)
            covers_center = any((r + (i if direction == 'V' else 0) == 7 and 
                                 c + (i if direction == 'H' else 0) == 7) for i in range(len(word)))
            return covers_center
        
        return has_contact

    def place_word(self, word, r, c, direction):
        word_score = 0
        word_multiplier = 1
        
        for i, letter in enumerate(word):
            curr_r = r + (i if direction == 'V' else 0)
            curr_c = c + (i if direction == 'H' else 0)
            
            char_val = self.LETTER_DATA[letter][0]
            mult = self.board.multipliers.get((curr_r, curr_c), "..")
            
            # Jeśli pole było puste, zużywamy literę z racka i liczymy premię pola
            if self.board.grid[curr_r][curr_c] == " ":
                self.rack.remove(letter)
                if mult == "DL": char_val *= 2
                elif mult == "TL": char_val *= 3
                elif mult == "DW": word_multiplier *= 2
                elif mult == "TW": word_multiplier *= 3
                self.board.grid[curr_r][curr_c] = letter
            
            word_score += char_val

        final_points = word_score * word_multiplier
        self.score += final_points
        self.first_move = False
        self.fill_rack()
        return final_points

    def run(self):
        print("--- WITAJ W SCRABBLE PYTHON ---")
        while True:
            self.board.display()
            print(f"\nTwoje litery: {', '.join(self.rack)}")
            print(f"Twój wynik: {self.score}")
            
            cmd = input("\nPodaj: SŁOWO RZĄD KOLUMNA KIERUNEK (np. KOT 7 7 H) lub 'pass': ").upper().split()
            
            if not cmd or cmd[0] == 'PASS': break
            if len(cmd) < 4: continue

            word, r, c, dir = cmd[0], int(cmd[1]), int(cmd[2]), cmd[3]

            if not self.is_valid_sjp(word):
                print("!! Słowo nie istnieje w słowniku SJP !!")
                continue

            if self.can_place_word(word, r, c, dir):
                pts = self.place_word(word, r, c, dir)
                print(f">> Zdobywasz {pts} punktów!")
            else:
                print("!! Nieprawidłowe ułożenie (brak liter lub zły styk) !!")

if __name__ == "__main__":
    ScrabbleGame().run()
import requests
import random
import os

class ScrabbleBoard:
    def __init__(self):
        self.grid = [[" " for _ in range(15)] for _ in range(15)]
        self.multipliers = self._set_multipliers()

    def _set_multipliers(self):
        m = {}
        tw = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        dw = [(1,1), (2,2), (3,3), (4,4), (1,13), (2,12), (3,11), (4,10), (13,1), (12,2), (11,3), (10,4), (13,13), (12,12), (11,11), (10,10), (7,7)]
        tl = [(1,5), (1,9), (5,1), (5,5), (5,9), (5,13), (9,1), (9,5), (9,9), (9,13), (13,5), (13,9)]
        dl = [(0,3), (0,11), (2,6), (2,8), (3,0), (3,7), (3,14), (6,2), (6,6), (6,8), (6,12), (7,3), (7,11), (8,2), (8,6), (8,8), (8,12), (11,0), (11,7), (11,14), (12,6), (12,8), (14,3), (14,11)]
        for p in tw: m[p] = "TW"
        for p in dw: m[p] = "DW"
        for p in tl: m[p] = "TL"
        for p in dl: m[p] = "DL"
        return m

    def display(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n     " + "  ".join([f"{i:02}" for i in range(15)]))
        for r in range(15):
            row = []
            for c in range(15):
                if self.grid[r][c] != " ":
                    row.append(f"[{self.grid[r][c]}]")
                else:
                    m = self.multipliers.get((r, c), "..")
                    row.append(f" {m} " if len(m)==2 else f" {m}  ")
            print(f"{r:02} |" + "".join(row) + "|")

class Scrabman:
    LETTER_DATA = {
        'A': (1, 9), 'E': (1, 7), 'I': (1, 8), 'O': (1, 6), 'U': (3, 2), 'Y': (2, 4), 'Z': (1, 5), 'L': (2, 3), 'N': (1, 5), 'R': (1, 4), 'S': (1, 4), 'W': (1, 4), 'D': (2, 3), 'G': (2, 2), 'K': (2, 3), 'M': (2, 3), 'P': (2, 3), 'T': (2, 3), 'B': (3, 2), 'C': (2, 3), 'H': (3, 2), 'J': (3, 2), 'Ł': (3, 2), 'Ó': (5, 1), 'Ś': (5, 1), 'Ć': (6, 1), 'Ę': (5, 1), 'Ą': (5, 1), 'Ń': (7, 1), 'Ź': (9, 1), 'Ż': (5, 1)
    }

    def __init__(self):
        self.board = ScrabbleBoard()
        self.bag = [char for char, (val, count) in self.LETTER_DATA.items() for _ in range(count)]
        random.shuffle(self.bag)
        self.players = [{"name": "Gracz 1", "rack": [], "score": 0}, {"name": "Gracz 2", "rack": [], "score": 0}]
        self.current_player_idx = 0
        self.first_move = True
        for p in self.players: self.fill_rack(p)

    def fill_rack(self, player):
        while len(player["rack"]) < 7 and self.bag:
            player["rack"].append(self.bag.pop())

    def validate_sjp(self, word):
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=3)
            return "dopuszczalne w grach" in r.text
        except: return True # Jeśli brak internetu, akceptuj (dla płynności)

    def exchange_letters(self, player):
        if len(self.bag) < 7: return False
        old_rack = player["rack"]
        player["rack"] = []
        self.fill_rack(player)
        self.bag.extend(old_rack)
        random.shuffle(self.bag)
        return True

    def run(self):
        while True:
            p = self.players[self.current_player_idx]
            self.board.display()
            print(f"\n--- TURA: {p['name']} | WYNIK: {p['score']} ---")
            print(f"TWOJE LITERY: {', '.join(p['rack'])}")
            print("KOMENDY: 'WYMIANA', 'PASS', lub 'SŁOWO R C KIERUNEK' (np. KOT 7 7 H)")
            
            cmd = input("> ").upper().split()
            if not cmd: continue
            
            if cmd[0] == 'WYMIANA':
                self.exchange_letters(p)
                self.current_player_idx = 1 - self.current_player_idx
                continue
            elif cmd[0] == 'PASS':
                self.current_player_idx = 1 - self.current_player_idx
                continue

            if len(cmd) < 4: continue
            word, r, c, direction = cmd[0], int(cmd[1]), int(cmd[2]), cmd[3]

            if self.validate_sjp(word):
                # Tu wstawiamy uproszczoną logikę punktacji i kładzenia dla czytelności
                word_score = sum(self.LETTER_DATA.get(l, (0,0))[0] for l in word)
                p['score'] += word_score
                for i, l in enumerate(word):
                    curr_r, curr_c = (r+i, c) if direction == 'V' else (r, c+i)
                    self.board.grid[curr_r][curr_c] = l
                    if l in p['rack']: p['rack'].remove(l)
                
                self.fill_rack(p)
                self.current_player_idx = 1 - self.current_player_idx
            else:
                print("Słowo niepoprawne!")

if __name__ == "__main__":
    Scrabman().run()
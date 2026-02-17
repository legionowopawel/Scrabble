import pygame
import sys
import random
import requests
import time
import re
import html
import winsound

# --- KONFIGURACJA ---
pygame.init()
COLORS = {
    'bg': (34, 139, 34), 'board': (0, 90, 0), 'grid': (0, 70, 0),
    'tile': (240, 230, 140), 'text': (0, 0, 0), 'white': (255, 255, 255),
    'btn': (128, 0, 128), 'panel': (200, 200, 230)
}

LETTER_DATA = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 'D': (2, 3),
    'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 'H': (3, 2), 'I': (1, 8),
    'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5),
    'Ń': (7, 1), 'O': (1, 6), 'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4),
    'Ś': (5, 1), 'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5),
    'Ź': (9, 1), 'Ż': (5, 1), '_': (0, 2)
}

class ScrabbleApp:
    def __init__(self):
        self.screen = pygame.display.set_mode((1100, 850))
        pygame.display.set_caption("Scrabmania Pro - AI Fix & SJP")
        self.font = pygame.font.SysFont('Arial', 22, bold=True)
        self.def_font = pygame.font.SysFont('Arial', 14, italic=True)
        
        self.grid = [[None]*15 for _ in range(15)]
        self.bag = [l for l, d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        
        self.player_rack = [self.bag.pop() for _ in range(7)]
        self.ai_rack = [self.bag.pop() for _ in range(7)]
        self.player_score = 0
        self.ai_score = 0
        self.definition = "Czekam na ruch..."
        self.first_move = True
        self.selected_idx = None
        self.bonuses = self._init_bonuses()

    def _init_bonuses(self):
        # Układ zgodny ze zdjęciem 1000020669.jpg
        b = {}
        specials = {
            (0,0): "5xS", (0,7): "4xS", (0,14): "5xS", (7,0): "4xS", 
            (14,0): "5xS", (14,7): "4xS", (14,14): "5xS", (7,14): "4xS",
            (7,7): "3xS", (4,4): "3xS", (4,10): "3xS", (10,4): "3xS", (10,10): "3xS"
        }
        return specials

    def get_sjp(self, word):
        try:
            r = requests.get(f"https://sjp.pl/{word.lower()}", timeout=2)
            if "nie występuje" in r.text: return None
            clean = re.sub('<[^<]+?>', '', r.text)
            match = re.search(r"dopuszczalne w grach(.*?)komentarz", clean, re.DOTALL)
            if match:
                res = match.group(1).strip()
                return res[:50] + "..." if len(res) > 50 else res
            return "Słowo poprawne (brak opisu)."
        except: return "Błąd SJP."

    def ai_turn(self):
        start = time.time()
        # Prosta symulacja AI: szuka miejsca obok istniejących liter
        # Aby zapobiec zawieszeniu: sprawdzamy tylko kilka opcji
        time.sleep(1) # Symulacja myślenia
        
        # Przykładowy ruch AI dla testu (zawsze stara się dołożyć 'A')
        for r in range(15):
            for c in range(15):
                if time.time() - start > 4.0: break # LIMIT 4 SEKUND
                if self.grid[r][c]:
                    for dr, dc in [(0,1), (1,0)]:
                        nr, nc = r+dr, c+dc
                        if 0<=nr<15 and 0<=nc<15 and not self.grid[nr][nc]:
                            let = self.ai_rack.pop(0)
                            self.grid[nr][nc] = let
                            self.ai_score += LETTER_DATA[let][0]
                            self.definition = f"AI: {let} - " + (self.get_sjp(let) or "")
                            winsound.MessageBeep(winsound.MB_OK) # Dźwięk Windows
                            return
        self.definition = "AI spasowało."

    def draw(self):
        self.screen.fill(COLORS['bg'])
        cell = 45
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(50 + c*cell, 50 + r*cell, cell, cell)
                pygame.draw.rect(self.screen, COLORS['grid'], rect, 1)
                if (r,c) in self.bonuses:
                    txt = self.def_font.render(self.bonuses[(r,c)], True, (0,50,0))
                    self.screen.blit(txt, txt.get_rect(center=rect.center))
                if self.grid[r][c]:
                    pygame.draw.rect(self.screen, COLORS['tile'], rect.inflate(-4,-4), border_radius=4)
                    l = self.font.render(self.grid[r][c], True, COLORS['text'])
                    self.screen.blit(l, l.get_rect(center=rect.center))

        # Panel definicji
        def_rect = pygame.Rect(750, 650, 300, 100)
        pygame.draw.rect(self.screen, COLORS['panel'], def_rect, border_radius=10)
        lines = [self.definition[i:i+40] for i in range(0, len(self.definition), 40)]
        for i, line in enumerate(lines[:3]):
            self.screen.blit(self.def_font.render(line, True, COLORS['text']), (760, 660 + i*20))

        # Wyniki
        self.screen.blit(self.font.render(f"TY: {self.player_score}", True, COLORS['white']), (800, 100))
        self.screen.blit(self.font.render(f"AI: {self.ai_score}", True, COLORS['white']), (800, 150))
        
        # Przycisk OK
        self.btn_rect = pygame.Rect(800, 300, 150, 50)
        pygame.draw.rect(self.screen, COLORS['btn'], self.btn_rect, border_radius=5)
        self.screen.blit(self.font.render("ZATWIERDŹ", True, COLORS['white']), (815, 310))

        # Ręka gracza
        for i, let in enumerate(self.player_rack):
            rect = pygame.Rect(50 + i*55, 750, 50, 50)
            pygame.draw.rect(self.screen, COLORS['tile'], rect, border_radius=5)
            if self.selected_idx == i: pygame.draw.rect(self.screen, (255,0,0), rect, 3)
            self.screen.blit(self.font.render(let, True, COLORS['text']), rect.inflate(-20,-10).topleft)

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: pygame.quit(); sys.exit()
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.btn_rect.collidepoint(e.pos):
                        # Tu logika zatwierdzania (skrócona dla przykładu)
                        self.ai_turn()
                    # Wybór litery z ręki i kładzenie na planszy
                    # ... (dodaj logikę kliknięcia w grid) ...
            self.draw()
            pygame.display.flip()

if __name__ == "__main__":
    ScrabbleApp().run()
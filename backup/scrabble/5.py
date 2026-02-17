import pygame
import sys
import random
import requests
import time

# --- USTAWIENIA ---
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800 # Zwiększony startowy rozmiar
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Scrabmania Pro - AI Edition")

# Kolory
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BG_GREEN = (34, 139, 34)
BOARD_DARK_GREEN = (0, 100, 0)
TILE_COLOR = (240, 230, 140)
TILE_BORDER = (184, 134, 11)
BUTTON_OK = (128, 0, 128)

# Czcionki
font_tile = pygame.font.SysFont('Arial', 24, bold=True)
font_pts = pygame.font.SysFont('Arial', 12, bold=True)
font_bonus = pygame.font.SysFont('Arial', 10, bold=True)
font_ui = pygame.font.SysFont('Arial', 30, bold=True)

LETTER_DATA = {
    'A': (1, 9), 'Ą': (5, 1), 'B': (3, 2), 'C': (2, 3), 'Ć': (6, 1), 'D': (2, 3),
    'E': (1, 7), 'Ę': (5, 1), 'F': (5, 1), 'G': (2, 2), 'H': (3, 2), 'I': (1, 8),
    'J': (3, 2), 'K': (2, 3), 'L': (2, 3), 'Ł': (3, 2), 'M': (2, 3), 'N': (1, 5),
    'Ń': (7, 1), 'O': (1, 6), 'Ó': (5, 1), 'P': (2, 3), 'R': (1, 4), 'S': (1, 4),
    'Ś': (5, 1), 'T': (2, 3), 'U': (3, 2), 'W': (1, 4), 'Y': (2, 4), 'Z': (1, 5),
    'Ź': (9, 1), 'Ż': (5, 1)
}

class Tile:
    def __init__(self, letter, pts):
        self.letter = letter
        self.points = pts
        self.rect = pygame.Rect(0, 0, 40, 40)
        self.is_dragging = False
        self.on_board = False
        self.grid_pos = None # (row, col)
        self.last_click_time = 0

    def draw(self, surface, pos=None):
        if pos: self.rect.topleft = pos
        pygame.draw.rect(surface, TILE_COLOR, self.rect, border_radius=4)
        pygame.draw.rect(surface, TILE_BORDER, self.rect, 2, border_radius=4)
        
        # Litery i punkty - ZAWSZE CZARNE
        l_surf = font_tile.render(self.letter, True, BLACK)
        p_surf = font_pts.render(str(self.points), True, BLACK)
        surface.blit(l_surf, l_surf.get_rect(center=(self.rect.centerx, self.rect.centery-2)))
        surface.blit(p_surf, (self.rect.right-12, self.rect.bottom-14))

class ScrabbleGame:
    def __init__(self):
        self.board_size = 15
        self.cell_size = 45
        self.grid = [[None for _ in range(15)] for _ in range(15)]
        self.bag = [l for l, d in LETTER_DATA.items() for _ in range(d[1])]
        random.shuffle(self.bag)
        
        self.player_rack = [Tile(l, LETTER_DATA[l][0]) for l in self._draw_from_bag(7)]
        self.ai_rack = [Tile(l, LETTER_DATA[l][0]) for l in self._draw_from_bag(7)]
        
        self.player_score = 0
        self.ai_score = 0
        self.dragging_tile = None
        self.turn = "PLAYER" # PLAYER / AI
        self.bonuses = self._init_bonuses()

    def _init_bonuses(self):
        b = {}
        # Uproszczony schemat premii dla czytelności kodu
        tw = [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]
        dw = [(7,7), (1,1), (2,2), (3,3), (4,4), (10,10), (11,11), (12,12), (13,13)]
        for p in tw: b[p] = "5 WYRAZ"
        for p in dw: b[p] = "2 WYRAZ"
        # ... tutaj można dodać resztę jak na zdjęciu
        return b

    def _draw_from_bag(self, n):
        drawn = self.bag[:n]
        self.bag = self.bag[n:]
        return drawn

    def get_layout_params(self):
        # Dynamika okna
        w, h = screen.get_size()
        board_w = self.board_size * self.cell_size
        offset_x = 50
        offset_y = (h - board_w) // 2
        return offset_x, offset_y, w, h

    def draw(self):
        ox, oy, w, h = self.get_layout_params()
        screen.fill(BG_GREEN)
        
        # Rysowanie planszy
        for r in range(15):
            for c in range(15):
                rect = pygame.Rect(ox + c*self.cell_size, oy + r*self.cell_size, self.cell_size, self.cell_size)
                pygame.draw.rect(screen, BOARD_DARK_GREEN, rect)
                pygame.draw.rect(screen, (0, 80, 0), rect, 1)
                
                bonus = self.bonuses.get((r,c))
                if bonus:
                    txt = font_bonus.render(bonus, True, BLACK)
                    screen.blit(txt, txt.get_rect(center=rect.center))

                if self.grid[r][c]:
                    self.grid[r][c].rect.topleft = (rect.x + 2, rect.y + 2)
                    self.grid[r][c].draw(screen)

        # UI i Stojak
        rack_y = h - 80
        for i, tile in enumerate(self.player_rack):
            if not tile.is_dragging and not tile.on_board:
                tile.draw(screen, (ox + i*50, rack_y))

        # Panel boczny
        info_x = ox + (15 * self.cell_size) + 40
        screen.blit(font_ui.render(f"PUNKTY: {self.player_score}", True, BLACK), (info_x, 100))
        screen.blit(font_ui.render(f"KOMPUTER: {self.ai_score}", True, BLACK), (info_x, 150))
        screen.blit(font_ui.render(f"W WORKU: {len(self.bag)}", True, BLACK), (info_x, 200))
        
        # Przycisk OK
        self.ok_rect = pygame.Rect(info_x, 300, 100, 50)
        pygame.draw.rect(screen, BUTTON_OK, self.ok_rect, border_radius=10)
        screen.blit(font_ui.render("OK!", True, WHITE), (info_x + 25, 305))

        if self.dragging_tile:
            self.dragging_tile.draw(screen)

    def handle_click(self, pos):
        now = pygame.time.get_ticks()
        ox, oy, _, _ = self.get_layout_params()

        # Sprawdź 2-klik (powrót do puli)
        for r in range(15):
            for c in range(15):
                tile = self.grid[r][c]
                if tile and tile.rect.collidepoint(pos):
                    if now - tile.last_click_time < 300: # 300ms na double click
                        tile.on_board = False
                        self.grid[r][c] = None
                        return
                    tile.last_click_time = now

        # Przeciąganie ze stojaka
        for tile in self.player_rack:
            if not tile.on_board and tile.rect.collidepoint(pos):
                self.dragging_tile = tile
                tile.is_dragging = True
                return

    def handle_release(self, pos):
        if not self.dragging_tile: return
        ox, oy, _, _ = self.get_layout_params()
        
        col = (pos[0] - ox) // self.cell_size
        row = (pos[1] - oy) // self.cell_size
        
        if 0 <= row < 15 and 0 <= col < 15 and self.grid[row][col] is None:
            self.grid[row][col] = self.dragging_tile
            self.dragging_tile.on_board = True
            self.dragging_tile.grid_pos = (row, col)
        
        self.dragging_tile.is_dragging = False
        self.dragging_tile = None

    def ai_play(self):
        # Uproszczony algorytm AI: kładzie 3 pierwsze litery pionowo na środku
        # W prawdziwej grze tutaj byłoby przeszukiwanie słownika
        print("AI myśli...")
        time.sleep(1)
        start_r, start_c = 5, 10
        for i in range(min(3, len(self.ai_rack))):
            tile = self.ai_rack.pop(0)
            if self.grid[start_r+i][start_c] is None:
                self.grid[start_r+i][start_c] = tile
                tile.on_board = True
                self.ai_score += tile.points
        
        new_tiles = self._draw_from_bag(3)
        self.ai_rack.extend([Tile(l, LETTER_DATA[l][0]) for l in new_tiles])
        self.turn = "PLAYER"

    def confirm_move(self):
        # Gracz kończy ruch
        placed = []
        for r in range(15):
            for c in range(15):
                tile = self.grid[r][c]
                if tile and tile in self.player_rack:
                    placed.append(tile)
                    self.player_score += tile.points # Prosta punktacja
        
        for t in placed:
            self.player_rack.remove(t)
        
        self.player_rack.extend([Tile(l, LETTER_DATA[l][0]) for l in self._draw_from_bag(len(placed))])
        self.turn = "AI"

game = ScrabbleGame()

# --- PĘTLA GŁÓWNA ---
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        
        if event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            
        if game.turn == "PLAYER":
            if event.type == pygame.MOUSEBUTTONDOWN:
                game.handle_click(event.pos)
                if game.ok_rect.collidepoint(event.pos):
                    game.confirm_move()
            
            if event.type == pygame.MOUSEBUTTONUP:
                game.handle_release(event.pos)
            
            if event.type == pygame.MOUSEMOTION and game.dragging_tile:
                game.dragging_tile.rect.center = event.pos

    if game.turn == "AI":
        game.draw()
        pygame.display.flip()
        game.ai_play()

    game.draw()
    pygame.display.flip()
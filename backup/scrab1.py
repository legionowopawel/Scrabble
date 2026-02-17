import pygame
import sys
import os
import random

# ----------------------------------------
# KONFIGURACJA
# ----------------------------------------

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
BOARD_SIZE = 15
TILE_SIZE = 32
BOARD_OFFSET_X = 50
BOARD_OFFSET_Y = 50
RACK_Y = 600
RACK_TILES = 7

BG_COLOR = (20, 60, 20)
BOARD_COLOR = (230, 220, 200)
GRID_COLOR = (120, 80, 40)
TEXT_COLOR = (10, 10, 10)
RACK_COLOR = (200, 180, 140)
BUTTON_COLOR = (80, 120, 200)
BUTTON_TEXT_COLOR = (255, 255, 255)
HIGHLIGHT_COLOR = (255, 255, 0)
NEW_TILE_COLOR = (200, 255, 200)

FPS = 30

# Polskie litery i punktacja – uproszczona
LETTER_DISTRIBUTION = {
    'A': (9, 1), 'Ą': (1, 5), 'B': (2, 3), 'C': (3, 2), 'Ć': (1, 6),
    'D': (3, 2), 'E': (7, 1), 'Ę': (1, 5), 'F': (1, 5), 'G': (2, 3),
    'H': (2, 3), 'I': (8, 1), 'J': (2, 3), 'K': (3, 2), 'L': (3, 2),
    'Ł': (2, 3), 'M': (3, 2), 'N': (5, 1), 'Ń': (1, 7), 'O': (6, 1),
    'Ó': (1, 5), 'P': (3, 2), 'R': (4, 1), 'S': (4, 1), 'Ś': (1, 5),
    'T': (3, 2), 'U': (2, 3), 'W': (4, 1), 'Y': (4, 2), 'Z': (5, 1),
    'Ź': (1, 9), 'Ż': (1, 5)
}

# Prosty układ premii: 2x litera, 3x litera, 2x słowo, 3x słowo
# Dla uproszczenia – kilka przykładowych pól
PREMIUM_NONE = 0
PREMIUM_LETTER_2 = 1
PREMIUM_LETTER_3 = 2
PREMIUM_WORD_2 = 3
PREMIUM_WORD_3 = 4

def create_premium_board():
    board = [[PREMIUM_NONE for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    # Przykładowe pola – nie jest to oficjalny układ Scrabble
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            if (i == j) or (i + j == BOARD_SIZE - 1):
                board[i][j] = PREMIUM_WORD_2
    board[7][7] = PREMIUM_WORD_3
    for i in range(0, BOARD_SIZE, 4):
        board[7][i] = PREMIUM_LETTER_2
        board[i][7] = PREMIUM_LETTER_3
    return board

# ----------------------------------------
# LOGIKA SŁOWNIKA
# ----------------------------------------

def load_dictionary(path="Wyrazy_dozwolone.txt"):
    words = set()
    if not os.path.exists(path):
        # Na razie tworzymy plik testowy z kilkoma słowami
        sample = ["ALA", "KOT", "DOM", "LAS", "ŁAD", "ŁÓDŹ", "MAMA", "TATA", "RYBA", "ŻABA"]
        with open(path, "w", encoding="utf-8") as f:
            for w in sample:
                f.write(w + "\n")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().upper()
            if w:
                words.add(w)
    return words

# ----------------------------------------
# LOGIKA PŁYTEK
# ----------------------------------------

def build_bag():
    bag = []
    for letter, (count, score) in LETTER_DISTRIBUTION.items():
        bag.extend([letter] * count)
    random.shuffle(bag)
    return bag

def draw_tiles_from_bag(bag, count):
    drawn = []
    for _ in range(count):
        if not bag:
            break
        drawn.append(bag.pop())
    return drawn

def letter_score(letter):
    return LETTER_DISTRIBUTION.get(letter, (0, 0))[1]

# ----------------------------------------
# STRUKTURY GRY
# ----------------------------------------

class TileOnBoard:
    def __init__(self, letter, row, col, is_new=False):
        self.letter = letter
        self.row = row
        self.col = col
        self.is_new = is_new

class GameState:
    def __init__(self, dictionary):
        self.dictionary = dictionary
        self.bag = build_bag()
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.premium = create_premium_board()
        self.rack = draw_tiles_from_bag(self.bag, RACK_TILES)
        self.score = 0
        self.message = "Ułóż słowo i kliknij OK."
        self.selected_rack_index = None
        self.new_tiles = []  # list of TileOnBoard
        self.first_move = True
        self.sound = None

    def load_sound(self, path="dzwiek.wav"):
        if os.path.exists(path):
            try:
                self.sound = pygame.mixer.Sound(path)
            except Exception:
                self.sound = None

    def play_sound(self):
        if self.sound:
            self.sound.play()

# ----------------------------------------
# RYSOWANIE
# ----------------------------------------

def draw_board(screen, font, game):
    pygame.draw.rect(screen, BOARD_COLOR,
                     (BOARD_OFFSET_X, BOARD_OFFSET_Y,
                      BOARD_SIZE * TILE_SIZE, BOARD_SIZE * TILE_SIZE))
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            x = BOARD_OFFSET_X + col * TILE_SIZE
            y = BOARD_OFFSET_Y + row * TILE_SIZE
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)

            premium = game.premium[row][col]
            if premium != PREMIUM_NONE:
                if premium == PREMIUM_LETTER_2:
                    color = (180, 220, 255)
                    text = "2L"
                elif premium == PREMIUM_LETTER_3:
                    color = (120, 180, 255)
                    text = "3L"
                elif premium == PREMIUM_WORD_2:
                    color = (255, 200, 180)
                    text = "2W"
                else:
                    color = (255, 150, 150)
                    text = "3W"
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, GRID_COLOR, rect, 1)
                t = font.render(text, True, TEXT_COLOR)
                screen.blit(t, (x + 4, y + 4))

            tile = game.board[row][col]
            if tile:
                draw_tile(screen, font, tile.letter, x, y,
                          NEW_TILE_COLOR if tile.is_new else (240, 240, 200))

def draw_tile(screen, font, letter, x, y, color):
    pygame.draw.rect(screen, color, (x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2))
    pygame.draw.rect(screen, (0, 0, 0), (x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2), 1)
    text = font.render(letter, True, TEXT_COLOR)
    screen.blit(text, (x + 6, y + 4))
    score = font.render(str(letter_score(letter)), True, TEXT_COLOR)
    screen.blit(score, (x + TILE_SIZE - 14, y + TILE_SIZE - 18))

def draw_rack(screen, font, game):
    pygame.draw.rect(screen, RACK_COLOR, (BOARD_OFFSET_X, RACK_Y, RACK_TILES * TILE_SIZE, TILE_SIZE + 10))
    for i, letter in enumerate(game.rack):
        x = BOARD_OFFSET_X + i * TILE_SIZE
        y = RACK_Y + 5
        color = (255, 255, 180) if game.selected_rack_index == i else (240, 240, 200)
        draw_tile(screen, font, letter, x, y, color)

def draw_ui(screen, font, game, ok_button_rect, exchange_button_rect):
    score_text = font.render(f"Punkty: {game.score}", True, (255, 255, 255))
    screen.blit(score_text, (BOARD_OFFSET_X, RACK_Y - 40))

    msg_text = font.render(game.message, True, (255, 255, 255))
    screen.blit(msg_text, (BOARD_OFFSET_X, RACK_Y + TILE_SIZE + 20))

    pygame.draw.rect(screen, BUTTON_COLOR, ok_button_rect)
    pygame.draw.rect(screen, (0, 0, 0), ok_button_rect, 2)
    ok_text = font.render("OK", True, BUTTON_TEXT_COLOR)
    screen.blit(ok_text, (ok_button_rect.x + 10, ok_button_rect.y + 5))

    pygame.draw.rect(screen, BUTTON_COLOR, exchange_button_rect)
    pygame.draw.rect(screen, (0, 0, 0), exchange_button_rect, 2)
    ex_text = font.render("Wymiana", True, BUTTON_TEXT_COLOR)
    screen.blit(ex_text, (exchange_button_rect.x + 5, exchange_button_rect.y + 5))

# ----------------------------------------
# POMOCNICZE
# ----------------------------------------

def pos_to_board_cell(pos):
    x, y = pos
    if x < BOARD_OFFSET_X or y < BOARD_OFFSET_Y:
        return None
    col = (x - BOARD_OFFSET_X) // TILE_SIZE
    row = (y - BOARD_OFFSET_Y) // TILE_SIZE
    if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
        return row, col
    return None

def pos_to_rack_index(pos):
    x, y = pos
    if y < RACK_Y or y > RACK_Y + TILE_SIZE + 10:
        return None
    if x < BOARD_OFFSET_X or x > BOARD_OFFSET_X + RACK_TILES * TILE_SIZE:
        return None
    idx = (x - BOARD_OFFSET_X) // TILE_SIZE
    if 0 <= idx < len(game.rack):
        return idx
    return None

# ----------------------------------------
# WALIDACJA RUCHU
# ----------------------------------------

def get_new_tiles(game):
    tiles = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            tile = game.board[r][c]
            if tile and tile.is_new:
                tiles.append(tile)
    return tiles

def words_from_move(game):
    new_tiles = get_new_tiles(game)
    if not new_tiles:
        return []

    rows = {t.row for t in new_tiles}
    cols = {t.col for t in new_tiles}

    if len(rows) == 1:
        direction = "H"
        row = list(rows)[0]
        cols_sorted = sorted(cols)
        for c in range(cols_sorted[0], cols_sorted[-1] + 1):
            if game.board[row][c] is None:
                return []
    elif len(cols) == 1:
        direction = "V"
        col = list(cols)[0]
        rows_sorted = sorted(rows)
        for r in range(rows_sorted[0], rows_sorted[-1] + 1):
            if game.board[r][col] is None:
                return []
    else:
        return []

    main_word, main_word_tiles = build_word(game, new_tiles, direction)
    if not main_word:
        return []

    words = [(main_word, main_word_tiles)]

    for t in new_tiles:
        if direction == "H":
            w, tiles = build_word(game, [t], "V")
        else:
            w, tiles = build_word(game, [t], "H")
        if w and len(tiles) > 1:
            words.append((w, tiles))

    return words

def build_word(game, tiles, direction):
    if direction == "H":
        row = tiles[0].row
        cols = [t.col for t in tiles]
        c_min = min(cols)
        c_max = max(cols)
        c = c_min
        while c - 1 >= 0 and game.board[row][c - 1]:
            c -= 1
        start = c
        c = c_max
        while c + 1 < BOARD_SIZE and game.board[row][c + 1]:
            c += 1
        end = c
        letters = []
        word_tiles = []
        for col in range(start, end + 1):
            tile = game.board[row][col]
            if tile:
                letters.append(tile.letter)
                word_tiles.append(tile)
            else:
                return "", []
        return "".join(letters), word_tiles
    else:
        col = tiles[0].col
        rows = [t.row for t in tiles]
        r_min = min(rows)
        r_max = max(rows)
        r = r_min
        while r - 1 >= 0 and game.board[r - 1][col]:
            r -= 1
        start = r
        r = r_max
        while r + 1 < BOARD_SIZE and game.board[r + 1][col]:
            r += 1
        end = r
        letters = []
        word_tiles = []
        for row in range(start, end + 1):
            tile = game.board[row][col]
            if tile:
                letters.append(tile.letter)
                word_tiles.append(tile)
            else:
                return "", []
        return "".join(letters), word_tiles

def score_word(game, word_tiles):
    word_multiplier = 1
    total = 0
    for t in word_tiles:
        base = letter_score(t.letter)
        letter_mult = 1
        if t.is_new:
            premium = game.premium[t.row][t.col]
            if premium == PREMIUM_LETTER_2:
                letter_mult = 2
            elif premium == PREMIUM_LETTER_3:
                letter_mult = 3
            elif premium == PREMIUM_WORD_2:
                word_multiplier *= 2
            elif premium == PREMIUM_WORD_3:
                word_multiplier *= 3
        total += base * letter_mult
    return total * word_multiplier

def validate_and_score_move(game):
    new_tiles = get_new_tiles(game)
    if not new_tiles:
        game.message = "Nie położyłeś żadnej litery."
        return False

    if game.first_move:
        if not any(t.row == 7 and t.col == 7 for t in new_tiles):
            game.message = "Pierwsze słowo musi przechodzić przez środek."
            return False

    words = words_from_move(game)
    if not words:
        game.message = "Złe ułożenie."
        return False

    total_score = 0
    for w, tiles in words:
        if w not in game.dictionary:
            game.message = f"Nie znany wyraz: {w}"
            return False
        total_score += score_word(game, tiles)

    for t in new_tiles:
        t.is_new = False
    game.score += total_score
    game.message = f"Zdobyłeś {total_score} punktów."
    game.first_move = False
    game.play_sound()
    return True

def revert_new_tiles(game):
    new_tiles = get_new_tiles(game)
    for t in new_tiles:
        game.board[t.row][t.col] = None
        game.rack.append(t.letter)
    game.new_tiles.clear()

# ----------------------------------------
# WYMIANA LITER
# ----------------------------------------

def exchange_letters(game):
    if not game.rack:
        game.message = "Brak liter do wymiany."
        return
    game.bag.extend(game.rack)
    random.shuffle(game.bag)
    game.rack = draw_tiles_from_bag(game.bag, RACK_TILES)
    game.message = "Wymieniono litery. Teraz ułóż słowo."

# ----------------------------------------
# GŁÓWNA PĘTLA
# ----------------------------------------

pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("SCRABMANIA – wersja testowa (bez AI)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 18)

dictionary = load_dictionary()
game = GameState(dictionary)
game.load_sound()

ok_button_rect = pygame.Rect(BOARD_OFFSET_X + 400, RACK_Y - 40, 60, 30)
exchange_button_rect = pygame.Rect(BOARD_OFFSET_X + 480, RACK_Y - 40, 100, 30)

running = True
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if ok_button_rect.collidepoint(pos):
                if validate_and_score_move(game):
                    missing = RACK_TILES - len(game.rack)
                    if missing > 0:
                        game.rack.extend(draw_tiles_from_bag(game.bag, missing))
                    game.new_tiles.clear()
                else:
                    revert_new_tiles(game)

            elif exchange_button_rect.collidepoint(pos):
                revert_new_tiles(game)
                exchange_letters(game)

            else:
                cell = pos_to_board_cell(pos)
                if cell:
                    row, col = cell
                    if game.selected_rack_index is not None and game.board[row][col] is None:
                        letter = game.rack.pop(game.selected_rack_index)
                        tile = TileOnBoard(letter, row, col, is_new=True)
                        game.board[row][col] = tile
                        game.new_tiles.append(tile)
                        game.selected_rack_index = None
                    else:
                        tile = game.board[row][col]
                        if tile and tile.is_new:
                            game.rack.append(tile.letter)
                            game.board[row][col] = None
                            game.new_tiles = [t for t in game.new_tiles if not (t.row == row and t.col == col)]
                else:
                    idx = pos_to_rack_index(pos)
                    if idx is not None and idx < len(game.rack):
                        if game.selected_rack_index == idx:
                            game.selected_rack_index = None
                        else:
                            game.selected_rack_index = idx

    screen.fill(BG_COLOR)
    draw_board(screen, font, game)
    draw_rack(screen, font, game)
    draw_ui(screen, font, game, ok_button_rect, exchange_button_rect)
    pygame.display.flip()

pygame.quit()
sys.exit()

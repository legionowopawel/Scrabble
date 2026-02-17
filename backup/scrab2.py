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
RACK_Y_P1 = 600
RACK_Y_P2 = 10
RACK_TILES = 7

BG_COLOR = (20, 60, 20)
BOARD_COLOR = (230, 220, 200)
GRID_COLOR = (120, 80, 40)
TEXT_COLOR = (10, 10, 10)
RACK_COLOR = (200, 180, 140)
BUTTON_COLOR = (80, 120, 200)
BUTTON_TEXT_COLOR = (255, 255, 255)
NEW_TILE_COLOR = (200, 255, 200)

FPS = 30

LETTER_DISTRIBUTION = {
    'A': (9, 1), 'Ą': (1, 5), 'B': (2, 3), 'C': (3, 2), 'Ć': (1, 6),
    'D': (3, 2), 'E': (7, 1), 'Ę': (1, 5), 'F': (1, 5), 'G': (2, 3),
    'H': (2, 3), 'I': (8, 1), 'J': (2, 3), 'K': (3, 2), 'L': (3, 2),
    'Ł': (2, 3), 'M': (3, 2), 'N': (5, 1), 'Ń': (1, 7), 'O': (6, 1),
    'Ó': (1, 5), 'P': (3, 2), 'R': (4, 1), 'S': (4, 1), 'Ś': (1, 5),
    'T': (3, 2), 'U': (2, 3), 'W': (4, 1), 'Y': (4, 2), 'Z': (5, 1),
    'Ź': (1, 9), 'Ż': (1, 5)
}

PREMIUM_NONE = 0
PREMIUM_LETTER_2 = 1
PREMIUM_LETTER_3 = 2
PREMIUM_WORD_2 = 3
PREMIUM_WORD_3 = 4

def create_premium_board():
    board = [[PREMIUM_NONE for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    for i in range(BOARD_SIZE):
        board[i][i] = PREMIUM_WORD_2
        board[i][BOARD_SIZE - 1 - i] = PREMIUM_WORD_2
    board[7][7] = PREMIUM_WORD_3
    return board

# ----------------------------------------
# SŁOWNIK
# ----------------------------------------

def load_dictionary(path="Wyrazy_dozwolone.txt"):
    if not os.path.exists(path):
        sample = ["ALA", "KOT", "DOM", "LAS", "ŁAD", "ŁÓDŹ", "MAMA", "TATA", "RYBA", "ŻABA"]
        with open(path, "w", encoding="utf-8") as f:
            for w in sample:
                f.write(w + "\n")
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip().upper() for line in f if line.strip())

# ----------------------------------------
# PŁYTKI
# ----------------------------------------

def build_bag():
    bag = []
    for letter, (count, _) in LETTER_DISTRIBUTION.items():
        bag.extend([letter] * count)
    random.shuffle(bag)
    return bag

def draw_tiles(bag, count):
    return [bag.pop() for _ in range(min(count, len(bag)))]

def letter_score(letter):
    return LETTER_DISTRIBUTION[letter][1]

# ----------------------------------------
# STRUKTURY
# ----------------------------------------

class TileOnBoard:
    def __init__(self, letter, row, col, is_new=True):
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

        self.rack = {
            1: draw_tiles(self.bag, RACK_TILES),
            2: draw_tiles(self.bag, RACK_TILES)
        }

        self.score = {1: 0, 2: 0}
        self.current_player = 1
        self.message = "Tura gracza 1"
        self.selected_rack_index = None
        self.new_tiles = []
        self.first_move = True

        self.sound = None
        if os.path.exists("dzwiek.wav"):
            try:
                self.sound = pygame.mixer.Sound("dzwiek.wav")
            except:
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

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            x = BOARD_OFFSET_X + c * TILE_SIZE
            y = BOARD_OFFSET_Y + r * TILE_SIZE
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)

            tile = game.board[r][c]
            if tile:
                draw_tile(screen, font, tile.letter, x, y,
                          NEW_TILE_COLOR if tile.is_new else (240, 240, 200))

def draw_tile(screen, font, letter, x, y, color):
    pygame.draw.rect(screen, color, (x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2))
    pygame.draw.rect(screen, (0, 0, 0), (x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2), 1)
    screen.blit(font.render(letter, True, TEXT_COLOR), (x + 6, y + 4))
    screen.blit(font.render(str(letter_score(letter)), True, TEXT_COLOR),
                (x + TILE_SIZE - 14, y + TILE_SIZE - 18))

def draw_rack(screen, font, game, player):
    y = RACK_Y_P1 if player == 1 else RACK_Y_P2
    pygame.draw.rect(screen, RACK_COLOR,
                     (BOARD_OFFSET_X, y, RACK_TILES * TILE_SIZE, TILE_SIZE + 10))

    for i, letter in enumerate(game.rack[player]):
        x = BOARD_OFFSET_X + i * TILE_SIZE
        color = (255, 255, 180) if (game.selected_rack_index == i and game.current_player == player) else (240, 240, 200)
        draw_tile(screen, font, letter, x, y + 5, color)

def draw_ui(screen, font, game, ok_button, exchange_button):
    screen.blit(font.render(f"Gracz 1: {game.score[1]} pkt", True, (255, 255, 255)), (50, 740))
    screen.blit(font.render(f"Gracz 2: {game.score[2]} pkt", True, (255, 255, 255)), (800, 740))
    screen.blit(font.render(game.message, True, (255, 255, 255)), (50, 720))

    pygame.draw.rect(screen, BUTTON_COLOR, ok_button)
    screen.blit(font.render("OK", True, BUTTON_TEXT_COLOR), (ok_button.x + 10, ok_button.y + 5))

    pygame.draw.rect(screen, BUTTON_COLOR, exchange_button)
    screen.blit(font.render("Wymiana", True, BUTTON_TEXT_COLOR), (exchange_button.x + 5, exchange_button.y + 5))

# ----------------------------------------
# LOGIKA RUCHU
# ----------------------------------------

def pos_to_board(pos):
    x, y = pos
    if x < BOARD_OFFSET_X or y < BOARD_OFFSET_Y:
        return None
    col = (x - BOARD_OFFSET_X) // TILE_SIZE
    row = (y - BOARD_OFFSET_Y) // TILE_SIZE
    if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
        return row, col
    return None

def pos_to_rack(pos, game):
    x, y = pos
    y1 = RACK_Y_P1
    y2 = RACK_Y_P2

    if game.current_player == 1 and y1 <= y <= y1 + TILE_SIZE + 10:
        idx = (x - BOARD_OFFSET_X) // TILE_SIZE
        return idx if 0 <= idx < len(game.rack[1]) else None

    if game.current_player == 2 and y2 <= y <= y2 + TILE_SIZE + 10:
        idx = (x - BOARD_OFFSET_X) // TILE_SIZE
        return idx if 0 <= idx < len(game.rack[2]) else None

    return None

def get_new_tiles(game):
    return [t for row in game.board for t in row if t and t.is_new]

def build_word(game, tiles, direction):
    if direction == "H":
        row = tiles[0].row
        cols = sorted(t.col for t in tiles)
        c = cols[0]
        while c > 0 and game.board[row][c - 1]:
            c -= 1
        start = c
        c = cols[-1]
        while c < BOARD_SIZE - 1 and game.board[row][c + 1]:
            c += 1
        end = c
        letters = []
        word_tiles = []
        for col in range(start, end + 1):
            tile = game.board[row][col]
            if not tile:
                return "", []
            letters.append(tile.letter)
            word_tiles.append(tile)
        return "".join(letters), word_tiles

    else:
        col = tiles[0].col
        rows = sorted(t.row for t in tiles)
        r = rows[0]
        while r > 0 and game.board[r - 1][col]:
            r -= 1
        start = r
        r = rows[-1]
        while r < BOARD_SIZE - 1 and game.board[r + 1][col]:
            r += 1
        end = r
        letters = []
        word_tiles = []
        for row in range(start, end + 1):
            tile = game.board[row][col]
            if not tile:
                return "", []
            letters.append(tile.letter)
            word_tiles.append(tile)
        return "".join(letters), word_tiles

def words_from_move(game):
    new_tiles = get_new_tiles(game)
    if not new_tiles:
        return []

    rows = {t.row for t in new_tiles}
    cols = {t.col for t in new_tiles}

    if len(rows) == 1:
        direction = "H"
    elif len(cols) == 1:
        direction = "V"
    else:
        return []

    main_word, main_tiles = build_word(game, new_tiles, direction)
    if not main_word:
        return []

    words = [(main_word, main_tiles)]

    for t in new_tiles:
        if direction == "H":
            w, tiles = build_word(game, [t], "V")
        else:
            w, tiles = build_word(game, [t], "H")
        if w and len(tiles) > 1:
            words.append((w, tiles))

    return words

def score_word(game, tiles):
    total = 0
    mult = 1
    for t in tiles:
        base = letter_score(t.letter)
        if t.is_new:
            p = game.premium[t.row][t.col]
            if p == PREMIUM_LETTER_2:
                base *= 2
            elif p == PREMIUM_LETTER_3:
                base *= 3
            elif p == PREMIUM_WORD_2:
                mult *= 2
            elif p == PREMIUM_WORD_3:
                mult *= 3
        total += base
    return total * mult

def validate_move(game):
    new_tiles = get_new_tiles(game)
    if not new_tiles:
        game.message = "Nie położyłeś litery."
        return False

    if game.first_move:
        if not any(t.row == 7 and t.col == 7 for t in new_tiles):
            game.message = "Pierwsze słowo musi przechodzić przez środek."
            return False

    words = words_from_move(game)
    if not words:
        game.message = "Złe ułożenie."
        return False

    total = 0
    for w, tiles in words:
        if w not in game.dictionary:
            game.message = f"Nieznany wyraz: {w}"
            return False
        total += score_word(game, tiles)

    for t in new_tiles:
        t.is_new = False

    game.score[game.current_player] += total
    game.message = f"Gracz {game.current_player} zdobył {total} pkt"
    game.first_move = False
    game.play_sound()
    return True

def revert_move(game):
    new_tiles = get_new_tiles(game)
    for t in new_tiles:
        game.board[t.row][t.col] = None
        game.rack[game.current_player].append(t.letter)
    game.new_tiles.clear()

def exchange_letters(game):
    if not game.rack[game.current_player]:
        game.message = "Brak liter."
        return
    game.bag.extend(game.rack[game.current_player])
    random.shuffle(game.bag)
    game.rack[game.current_player] = draw_tiles(game.bag, RACK_TILES)
    game.message = "Wymieniono litery."

def end_turn(game):
    missing = RACK_TILES - len(game.rack[game.current_player])
    if missing > 0:
        game.rack[game.current_player].extend(draw_tiles(game.bag, missing))

    game.new_tiles.clear()
    game.current_player = 2 if game.current_player == 1 else 1
    game.message = f"Tura gracza {game.current_player}"

def check_game_end(game):
    if not game.bag and not game.rack[1] and not game.rack[2]:
        if game.score[1] > game.score[2]:
            game.message = "Koniec gry! Wygrywa gracz 1"
        elif game.score[2] > game.score[1]:
            game.message = "Koniec gry! Wygrywa gracz 2"
        else:
            game.message = "Remis!"
        return True
    return False

# ----------------------------------------
# GŁÓWNA PĘTLA
# ----------------------------------------

pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("SCRABMANIA – 2 GRACZY")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 18)

dictionary = load_dictionary()
game = GameState(dictionary)

ok_button = pygame.Rect(600, 720, 60, 30)
exchange_button = pygame.Rect(680, 720, 100, 30)

running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if ok_button.collidepoint(pos):
                if validate_move(game):
                    end_turn(game)
                else:
                    revert_move(game)

            elif exchange_button.collidepoint(pos):
                revert_move(game)
                exchange_letters(game)

            else:
                cell = pos_to_board(pos)
                if cell:
                    r, c = cell
                    if game.board[r][c] is None and game.selected_rack_index is not None:
                        letter = game.rack[game.current_player].pop(game.selected_rack_index)
                        tile = TileOnBoard(letter, r, c)
                        game.board[r][c] = tile
                        game.new_tiles.append(tile)
                        game.selected_rack_index = None
                    else:
                        tile = game.board[r][c]
                        if tile and tile.is_new:
                            game.rack[game.current_player].append(tile.letter)
                            game.board[r][c] = None
                            game.new_tiles = [t for t in game.new_tiles if not (t.row == r and t.col == c)]
                else:
                    idx = pos_to_rack(pos, game)
                    if idx is not None and idx < len(game.rack[game.current_player]):
                        if game.selected_rack_index == idx:
                            game.selected_rack_index = None
                        else:
                            game.selected_rack_index = idx

    if check_game_end(game):
        pass

    screen.fill(BG_COLOR)
    draw_board(screen, font, game)
    draw_rack(screen, font, game, 1)
    draw_rack(screen, font, game, 2)
    draw_ui(screen, font, game, ok_button, exchange_button)
    pygame.display.flip()

pygame.quit()
sys.exit()

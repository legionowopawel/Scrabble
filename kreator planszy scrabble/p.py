import pandas as pd
import random

def generate_test_board():
    size = 25
    # Tworzymy pustą macierz
    board = [["" for _ in range(size)] for _ in range(size)]
    
    # Lista ekstremalnych promocji
    promos = ["12S", "10L", "8S", "6L", "5S", "4L", "3S", "2L"]
    
    # Obliczamy ile pól to 30%
    total_cells = size * size
    promo_count = int(total_cells * 0.30)
    
    # Losujemy pozycje dla promocji
    positions = [(r, c) for r in range(size) for c in range(size)]
    promo_positions = random.sample(positions, promo_count)
    
    for r, c in promo_positions:
        board[r][c] = random.choice(promos)
        
    # Gwarantowane ekstremalne w rogach i na środku
    board[0][0] = board[0][24] = board[24][0] = board[24][24] = "12S"
    board[12][12] = "3S" # Start
    
    df = pd.DataFrame(board)
    df.to_excel("plansza.ods", engine="odf", index=False, header=False)
    print("Plik plansza.ods (25x25) został wygenerowany!")

if __name__ == "__main__":
    generate_test_board()
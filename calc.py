def get_word_at(board, r, c, direction, board_dim):
    dr, dc = direction
    start_r, start_c = r, c
    while 0 <= start_r - dr < board_dim and 0 <= start_c - dc < board_dim and board[start_r - dr][start_c - dc] is not None:
        start_r -= dr
        start_c -= dc
    word_tiles = []
    curr_r, curr_c = start_r, start_c
    while 0 <= curr_r < board_dim and 0 <= curr_c < board_dim and board[curr_r][curr_c] is not None:
        word_tiles.append((curr_r, curr_c, board[curr_r][curr_c]))
        curr_r += dr
        curr_c += dc
    return word_tiles if len(word_tiles) > 1 else []

def calculate_full_score(board_state, premium_map, board_dim, letters_data):
    new_tiles_pos = [(r, c) for r in range(board_dim) for c in range(board_dim) 
                     if board_state[r][c] and board_state[r][c]['new']]
    if not new_tiles_pos: return 0, ""

    detected_words = []
    found_fingerprints = set()
    for r, c in new_tiles_pos:
        for direction in [(0, 1), (1, 0)]:
            word = get_word_at(board_state, r, c, direction, board_dim)
            if word:
                fp = tuple(sorted([(t[0], t[1]) for t in word]))
                if fp not in found_fingerprints:
                    detected_words.append(word)
                    found_fingerprints.add(fp)

    total_score = 0
    math_lines = []
    for word in detected_words:
        word_str = "".join([t[2]['letter'] for t in word])
        base_pts = 0
        word_mult = 1
        comp_desc, add_desc = [], []
        for r, c, tile in word:
            let, val = tile['letter'], letters_data[tile['letter']][1]
            curr_val, suffix = val, ""
            if tile['new']:
                prem = premium_map.get((r, c))
                if prem:
                    if prem[0] == "L": curr_val = val * prem[1]; suffix = f"x{prem[1]}L"
                    elif prem[0] == "S": word_mult *= prem[1]; suffix = f"(Słowox{prem[1]})"
            base_pts += curr_val
            comp_desc.append(f"{let}{val}{suffix}"); add_desc.append(str(curr_val))
        f_pts = base_pts * word_mult
        total_score += f_pts
        line = f"{word_str} = {', '.join(comp_desc)} = {'+'.join(add_desc)}"
        if word_mult > 1: line += f" = ({base_pts}) x {word_mult}S = {f_pts}"
        else: line += f" = {f_pts}"
        math_lines.append(line)
    if len(new_tiles_pos) == 7:
        total_score += 50
        math_lines.append("BINGO! (+50 pkt)")
    return total_score, " | ".join(math_lines)
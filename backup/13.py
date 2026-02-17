import pygame
import sys
import os
import random
import pandas as pd
import calc
import datetime

# --- STAŁE ---
COLOR_BG = (10, 45, 10)
COLOR_BOARD = (34, 139, 34)
COLOR_GRID = (0, 100, 0)
COLOR_TILE = (245, 222, 179)
COLOR_TEXT = (40, 40, 40)
COLOR_SELECT = (173, 216, 230)

LETTERS = {
    'A': (9, 1), 'Ą': (1, 5), 'B': (2, 3), 'C': (3, 2), 'Ć': (1, 6),
    'D': (3, 2), 'E': (7, 1), 'Ę': (1, 5), 'F': (1, 5), 'G': (2, 3),
    'H': (2, 3), 'I': (8, 1), 'J': (2, 3), 'K': (3, 2), 'L': (3, 2),
    'Ł': (2, 3), 'M': (3, 2), 'N': (5, 1), 'Ń': (1, 7), 'O': (6, 1),
    'Ó': (1, 5), 'P': (3, 2), 'R': (4, 1), 'S': (4, 1), 'Ś': (1, 5),
    'T': (3, 2), 'U': (2, 3), 'W': (4, 1), 'Y': (4, 2), 'Z': (5, 1),
    'Ź': (1, 9), 'Ż': (1, 5)
}

RESOLUTIONS = [(1024, 768), (1280, 720), (1920, 1080), (0, 0)]

class ScrabbleGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        pygame.display.set_caption("SCRABMANIA PRO")
        
        self.sounds = self.load_sounds()
        self.board_dim = 15
        self.premium_map = {}
        self.load_board_config()
        self.recalculate_dimensions()
        
        self.game_state = "START_SCREEN"
        self.player_names = {1: "Gracz 1", 2: "Gracz 2"}
        self.input_active = 1
        
        self.last_exit_click_time = 0
        self.last_tile_click_time = 0
        self.last_tile_coords = None
        
        self.reset_game()
        self.show_res_menu = False

    def load_sounds(self):
        s = {}
        for i in range(1, 7):
            path = f"{i}.mp3"
            if os.path.exists(path): s[i] = pygame.mixer.Sound(path)
        return s

    def play_snd(self, i):
        if i in self.sounds: self.sounds[i].play()

    def load_board_config(self):
        if os.path.exists("plansza.ods"):
            try:
                df = pd.read_excel("plansza.ods", engine="odf", header=None).fillna("")
                self.board_dim = max(df.shape)
                for r in range(df.shape[0]):
                    for c in range(df.shape[1]):
                        val = str(df.iloc[r, c]).strip().upper()
                        if val.endswith(('S', 'W')): self.premium_map[(r, c)] = ("S", int(val[:-1]), (200, 0, 0))
                        elif val.endswith('L'): self.premium_map[(r, c)] = ("L", int(val[:-1]), (0, 0, 180))
            except: pass

    def recalculate_dimensions(self):
        sw, sh = self.screen.get_size()
        self.tile_size = int((sh * 0.70) // self.board_dim)
        self.board_x = (sw - (self.board_dim * self.tile_size)) // 2
        self.board_y = int(sh * 0.15)
        self.font_tile = pygame.font.SysFont("Arial", int(self.tile_size * 0.5), bold=True)
        self.font_small = pygame.font.SysFont("Arial", int(self.tile_size * 0.25), bold=True)
        self.font_ui = pygame.font.SysFont("Verdana", int(sh * 0.025), bold=True)
        self.font_calc = pygame.font.SysFont("Courier New", int(sh * 0.016), bold=True)

    def reset_game(self):
        self.board_state = [[None for _ in range(self.board_dim)] for _ in range(self.board_dim)]
        self.bag = [l for l, (count, _) in LETTERS.items() for _ in range(count)]
        random.shuffle(self.bag)
        self.racks = {1: self.draw_tiles(7), 2: self.draw_tiles(7)}
        self.scores = {1: 0, 2: 0}
        self.current_player = 1
        self.floating_tile = None 
        self.exchange_mode = False
        self.exchange_selected = []
        self.calc_text = ""
        
        if not os.path.exists("Wyniki_gry"): os.makedirs("Wyniki_gry")
        now = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        self.report_words_file = f"Wyniki_gry/{now}.txt"
        self.report_walak_file = f"Wyniki_gry/Walak_{now}.txt"

    def draw_tiles(self, n):
        return [self.bag.pop() for _ in range(min(n, len(self.bag)))]

    def return_tiles_to_rack(self):
        for r in range(self.board_dim):
            for c in range(self.board_dim):
                tile = self.board_state[r][c]
                if tile and tile['new']:
                    self.racks[self.current_player].append(tile['letter'])
                    self.board_state[r][c] = None
        if self.floating_tile:
            self.racks[self.current_player].append(self.floating_tile)
            self.floating_tile = None
        self.play_snd(1)

    def write_to_reports(self, words_info, math_info):
        with open(self.report_words_file, "a", encoding="utf-8") as f:
            f.write(f"{self.player_names[self.current_player]}: {words_info}\n")
        with open(self.report_walak_file, "a", encoding="utf-8") as f:
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{time_str}] {self.player_names[self.current_player]} | Pkt: {math_info}\n")

    def draw_tile_obj(self, letter, x, y, color, size):
        rect = pygame.Rect(x, y, size-2, size-2)
        pygame.draw.rect(self.screen, color, rect, border_radius=int(size*0.1))
        pygame.draw.rect(self.screen, (0,0,0), rect, 1)
        l_surf = self.font_tile.render(letter, True, COLOR_TEXT)
        self.screen.blit(l_surf, (x + (size - l_surf.get_width())//2, y + size//10))
        p_surf = self.font_small.render(str(LETTERS[letter][1]), True, COLOR_TEXT)
        self.screen.blit(p_surf, (x + size - p_surf.get_width() - 2, y + size - p_surf.get_height() - 2))

    def draw(self):
        self.screen.fill(COLOR_BG)
        sw, sh = self.screen.get_size()

        if self.game_state == "START_SCREEN":
            self.draw_start_screen(sw, sh)
            return

        # UI GÓRA
        worek_txt = self.font_ui.render(f"WOREK: {len(self.bag)}", True, (255,255,255))
        self.screen.blit(worek_txt, (sw*0.02, sh*0.02))
        
        turn_txt = self.font_ui.render(f"RUCH: {self.player_names[self.current_player]}", True, (255,255,0))
        self.screen.blit(turn_txt, (sw//2 - turn_txt.get_width()//2, sh*0.02))

        if self.calc_text:
            c_surf = self.font_calc.render(self.calc_text, True, (255,255,0))
            self.screen.blit(c_surf, (sw//2 - c_surf.get_width()//2, sh*0.08))

        # PLANSZA
        for r in range(self.board_dim):
            for c in range(self.board_dim):
                x, y = self.board_x + c * self.tile_size, self.board_y + r * self.tile_size
                rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
                prem = self.premium_map.get((r, c))
                pygame.draw.rect(self.screen, prem[2] if prem else COLOR_BOARD, rect)
                pygame.draw.rect(self.screen, COLOR_GRID, rect, 1)
                tile = self.board_state[r][c]
                if tile:
                    t_col = (200, 255, 200) if tile['new'] else COLOR_TILE
                    self.draw_tile_obj(tile['letter'], x, y, t_col, self.tile_size)
                elif prem:
                    p_txt = self.font_small.render(f"{prem[1]}{prem[0]}", True, (255,255,255))
                    self.screen.blit(p_txt, (x + (self.tile_size-p_txt.get_width())//2, y + self.tile_size//3))

        # STOJAKI
        rack_size = int(self.tile_size * 1.1)
        for i, l in enumerate(self.racks[1]):
            color = COLOR_SELECT if (self.exchange_mode and self.current_player==1 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, sw*0.02, self.board_y + i*rack_size, color, rack_size)
        for i, l in enumerate(self.racks[2]):
            color = COLOR_SELECT if (self.exchange_mode and self.current_player==2 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, sw*0.92, self.board_y + i*rack_size, color, rack_size)

        # PRZYCISKI
        self.btn_ok = pygame.Rect(sw//2 - 250, sh*0.9, 150, sh*0.05)
        self.btn_ex = pygame.Rect(sw//2 - 75, sh*0.9, 150, sh*0.05)
        self.btn_exit = pygame.Rect(sw//2 + 100, sh*0.9, 150, sh*0.05)
        self.btn_res = pygame.Rect(sw - 160, 10, 150, 30)
        
        btns = [(self.btn_ok, "ZATWIERDŹ"), (self.btn_ex, "WYMIANA"), (self.btn_exit, "WYJDŹ"), (self.btn_res, "WIDOK")]
        for b, txt in btns:
            pygame.draw.rect(self.screen, (100,100,100), b, border_radius=5)
            t_s = self.font_ui.render(txt, True, (255,255,255))
            self.screen.blit(t_s, (b.centerx - t_s.get_width()//2, b.centery - t_s.get_height()//2))

        # PUNKTY
        p1_txt = self.font_ui.render(f"{self.player_names[1]}: {self.scores[1]}", True, (255,255,255))
        self.screen.blit(p1_txt, (sw*0.02, sh*0.9))
        p2_txt = self.font_ui.render(f"{self.player_names[2]}: {self.scores[2]}", True, (255,255,255))
        self.screen.blit(p2_txt, (sw*0.98 - p2_txt.get_width(), sh*0.9))

        if self.exchange_mode:
            ex_info = self.font_small.render("WYBIERZ LITERY I NACIŚNIJ WYMIANA LUB ESC", True, (255,100,100))
            self.screen.blit(ex_info, (self.btn_ex.centerx - ex_info.get_width()//2, self.btn_ex.top - 25))

        if self.show_res_menu: self.draw_res_menu()
        if self.floating_tile:
            mx, my = pygame.mouse.get_pos()
            self.draw_tile_obj(self.floating_tile, mx-rack_size//2, my-rack_size//2, (255,255,200), rack_size)
        pygame.display.flip()

    def draw_start_screen(self, sw, sh):
        overlay = pygame.Surface((sw, sh))
        overlay.fill((30, 30, 30))
        self.screen.blit(overlay, (0,0))
        
        # Pola do klikania dla imion
        self.rect_p1 = pygame.Rect(sw//2 - 205, sh//2 - 65, 410, 45)
        self.rect_p2 = pygame.Rect(sw//2 - 205, sh//2 - 5, 410, 45)
        
        for r, active in [(self.rect_p1, 1), (self.rect_p2, 2)]:
            col = (60, 60, 60) if self.input_active != active else (100, 100, 0)
            pygame.draw.rect(self.screen, col, r, border_radius=5)
        
        t1 = self.font_ui.render(f"Gracz 1: {self.player_names[1]} {'|' if self.input_active==1 else ''}", True, (255,255,255))
        t2 = self.font_ui.render(f"Gracz 2: {self.player_names[2]} {'|' if self.input_active==2 else ''}", True, (255,255,255))
        self.screen.blit(t1, (sw//2 - 200, sh//2 - 60))
        self.screen.blit(t2, (sw//2 - 200, sh//2))
        
        self.btn_start = pygame.Rect(sw//2 - 75, sh//2 + 80, 150, 50)
        pygame.draw.rect(self.screen, (0, 150, 0), self.btn_start, border_radius=5)
        st_txt = self.font_ui.render("START", True, (255,255,255))
        self.screen.blit(st_txt, (self.btn_start.centerx - st_txt.get_width()//2, self.btn_start.centery - st_txt.get_height()//2))
        pygame.display.flip()

    def handle_click(self, pos):
        sw, sh = self.screen.get_size() # <--- TO TU BYŁ BŁĄD, TERAZ JEST NA GÓRZE
        mx, my = pos
        
        if self.game_state == "START_SCREEN":
            if self.btn_start.collidepoint(mx, my): self.game_state = "PLAYING"
            if self.rect_p1.collidepoint(mx, my): self.input_active = 1
            if self.rect_p2.collidepoint(mx, my): self.input_active = 2
            return

        if self.show_res_menu:
            for rect, res in self.res_rects:
                if rect.collidepoint(mx, my):
                    if res[0] == 0: self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
                    else: self.screen = pygame.display.set_mode(res, pygame.RESIZABLE)
                    self.recalculate_dimensions(); self.show_res_menu = False; self.play_snd(5)
            return

        if self.btn_res.collidepoint(mx, my): self.show_res_menu = True; return
        if self.btn_ok.collidepoint(mx, my): self.confirm_move(); return
        if self.btn_ex.collidepoint(mx, my): self.handle_exchange(); return
        if self.btn_exit.collidepoint(mx, my): self.handle_exit_logic(); return

        rack_size = int(self.tile_size * 1.1)
        # Obsługa stojaków
        if mx < sw*0.1 and self.current_player == 1:
            idx = (my - self.board_y) // rack_size
            if 0 <= idx < len(self.racks[1]):
                if self.exchange_mode:
                    if idx in self.exchange_selected: self.exchange_selected.remove(idx)
                    else: self.exchange_selected.append(idx)
                else: self.floating_tile = self.racks[1].pop(idx); self.play_snd(1)
        elif mx > sw*0.9 and self.current_player == 2:
            idx = (my - self.board_y) // rack_size
            if 0 <= idx < len(self.racks[2]):
                if self.exchange_mode:
                    if idx in self.exchange_selected: self.exchange_selected.remove(idx)
                    else: self.exchange_selected.append(idx)
                else: self.floating_tile = self.racks[2].pop(idx); self.play_snd(1)
        
        # Plansza
        c, r = (mx - self.board_x) // self.tile_size, (my - self.board_y) // self.tile_size
        if 0 <= r < self.board_dim and 0 <= c < self.board_dim:
            now = pygame.time.get_ticks()
            if self.board_state[r][c] and self.board_state[r][c]['new']:
                if self.last_tile_coords == (r, c) and now - self.last_tile_click_time < 500:
                    self.racks[self.current_player].append(self.board_state[r][c]['letter'])
                    self.board_state[r][c] = None; self.play_snd(1)
                else: self.last_tile_click_time = now; self.last_tile_coords = (r, c)
            
            if self.floating_tile and not self.board_state[r][c]:
                self.board_state[r][c] = {'letter': self.floating_tile, 'new': True}
                self.floating_tile = None; self.play_snd(1)

    def handle_exit_logic(self):
        now = pygame.time.get_ticks()
        if now - self.last_exit_click_time < 500: # Szybkie podwójne kliknięcie pod rząd
            pygame.quit(); sys.exit()
        else:
            self.return_tiles_to_rack()
            self.exchange_mode = False
            self.last_exit_click_time = now

    def confirm_move(self):
        new_tiles = [(r, c) for r in range(self.board_dim) for c in range(self.board_dim) 
                     if self.board_state[r][c] and self.board_state[r][c]['new']]
        
        if not new_tiles:
            self.write_to_reports("PAS (strata kolejki)", "0")
            self.current_player = 2 if self.current_player == 1 else 1
            self.calc_text = "PAS - STRATA KOLEJKI"
            self.play_snd(3)
            return

        pts, math = calc.calculate_full_score(self.board_state, self.premium_map, self.board_dim, LETTERS)
        if pts > 0:
            words_only = math.split('=')[0].strip()
            self.write_to_reports(words_only, math)
            self.scores[self.current_player] += pts
            self.calc_text = math
            for r, c in new_tiles: self.board_state[r][c]['new'] = False
            needed = 7 - len(self.racks[self.current_player])
            self.racks[self.current_player].extend(self.draw_tiles(needed))
            self.current_player = 2 if self.current_player == 1 else 1
            self.play_snd(2)
        else: self.play_snd(3)

    def handle_exchange(self):
        if len(self.bag) < 7:
            self.calc_text = "WYMIANA NIEMOŻLIWA (Worek < 7)"
            return

        if not self.exchange_mode:
            self.return_tiles_to_rack()
            self.exchange_mode = True
        else:
            if self.exchange_selected:
                self.exchange_selected.sort(reverse=True)
                for i in self.exchange_selected:
                    l = self.racks[self.current_player].pop(i)
                    self.bag.append(l)
                random.shuffle(self.bag)
                self.racks[self.current_player].extend(self.draw_tiles(len(self.exchange_selected)))
                self.write_to_reports("WYMIANA LITER", f"Wymieniono {len(self.exchange_selected)} szt.")
                self.current_player = 2 if self.current_player == 1 else 1
                self.play_snd(4)
            self.exchange_mode = False; self.exchange_selected = []

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.VIDEORESIZE: self.recalculate_dimensions()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.return_tiles_to_rack(); self.exchange_mode = False
                    if self.game_state == "START_SCREEN":
                        if event.key == pygame.K_BACKSPACE: self.player_names[self.input_active] = self.player_names[self.input_active][:-1]
                        elif event.key == pygame.K_TAB: self.input_active = 2 if self.input_active == 1 else 1
                        elif event.key == pygame.K_RETURN: self.game_state = "PLAYING"
                        else:
                            if len(self.player_names[self.input_active]) < 15: self.player_names[self.input_active] += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN: self.handle_click(event.pos)
            self.draw()
            clock.tick(60)

if __name__ == "__main__": ScrabbleGame().run()
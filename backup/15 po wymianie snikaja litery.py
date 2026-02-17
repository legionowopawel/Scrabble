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
        self.resolutions = self.load_resolutions()
        
        self.game_state = "START_SCREEN"
        self.player_names = {1: "Gracz 1", 2: "Gracz 2"}
        self.input_active = 1
        self.winner_text = ""
        self.show_res_menu = False
        
        self.last_exit_click_time = 0
        self.last_tile_click_time = 0
        self.last_tile_coords = None
        
        self.recalculate_dimensions()
        self.reset_game()

    def load_resolutions(self):
        res = []
        if os.path.exists("rozdzielczosc.txt"):
            with open("rozdzielczosc.txt", "r") as f:
                for line in f:
                    try:
                        w, h = map(int, line.strip().lower().split('x'))
                        res.append((w, h))
                    except: continue
        if not res: res = [(1024, 768), (1280, 720), (1600, 900)]
        return res

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
        
        # Fonty
        self.font_tile = pygame.font.SysFont("Arial", int(self.tile_size * 0.5), bold=True)
        self.font_small = pygame.font.SysFont("Arial", int(self.tile_size * 0.25), bold=True)
        self.font_ui = pygame.font.SysFont("Verdana", int(sh * 0.022), bold=True)
        self.font_ui_tiny = pygame.font.SysFont("Verdana", int(sh * 0.013), bold=True)
        self.font_calc = pygame.font.SysFont("Courier New", int(sh * 0.018), bold=True)
        self.font_stojak = pygame.font.SysFont("Arial", int(sh * 0.015), italic=True)

        # Logika podziału dolnego paska (Dla przycisków)
        # Rezerwujemy 15% szerokości po bokach na punkty, środek (70%) dzielimy na 4 przyciski
        button_area_width = sw * 0.65
        start_x = (sw - button_area_width) // 2
        spacing = 10
        btn_w = (button_area_width - (3 * spacing)) // 4
        btn_h = sh * 0.06
        btn_y = sh * 0.91

        self.btn_ok = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        self.btn_ex = pygame.Rect(start_x + (btn_w + spacing), btn_y, btn_w, btn_h)
        self.btn_end = pygame.Rect(start_x + 2*(btn_w + spacing), btn_y, btn_w, btn_h)
        self.btn_exit = pygame.Rect(start_x + 3*(btn_w + spacing), btn_y, btn_w, btn_h)
        
        # Przycisk Rozdzielczości w menu górnym
        self.btn_res_toggle = pygame.Rect(10, 5, 180, 25)

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

        # MENU GÓRNE
        pygame.draw.rect(self.screen, (40, 40, 40), (0, 0, sw, 35))
        pygame.draw.rect(self.screen, (80, 80, 80), self.btn_res_toggle, border_radius=3)
        res_t = self.font_ui_tiny.render("Zmień rozdzielczość", True, (255,255,255))
        self.screen.blit(res_t, (self.btn_res_toggle.centerx - res_t.get_width()//2, self.btn_res_toggle.centery - res_t.get_height()//2))

        # WOREK I RUCH
        worek_txt = self.font_ui_tiny.render(f"WOREK: {len(self.bag)}", True, (200,200,200))
        self.screen.blit(worek_txt, (sw - worek_txt.get_width() - 10, 8))
        
        turn_txt = self.font_ui.render(f"RUCH: {self.player_names[self.current_player]}", True, (255,255,0))
        self.screen.blit(turn_txt, (sw//2 - turn_txt.get_width()//2, 40))

        if self.calc_text:
            c_surf = self.font_calc.render(self.calc_text, True, (255,255,255))
            self.screen.blit(c_surf, (sw//2 - c_surf.get_width()//2, 85))

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
                    self.screen.blit(p_txt, (x + (self.tile_size - p_txt.get_width())//2, y + (self.tile_size - p_txt.get_height())//2))

        # STOJAKI
        rack_size = int(self.tile_size * 1.1)
        self.screen.blit(self.font_stojak.render(f"Stojak: {self.player_names[1]}", True, (180,180,180)), (sw*0.01, self.board_y - 20))
        for i, l in enumerate(self.racks[1]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==1 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, sw*0.01, self.board_y + i*rack_size, col, rack_size)
        
        self.screen.blit(self.font_stojak.render(f"Stojak: {self.player_names[2]}", True, (180,180,180)), (sw*0.92, self.board_y - 20))
        for i, l in enumerate(self.racks[2]):
            col = COLOR_SELECT if (self.exchange_mode and self.current_player==2 and i in self.exchange_selected) else COLOR_TILE
            self.draw_tile_obj(l, sw*0.92, self.board_y + i*rack_size, col, rack_size)

        # PRZYCISKI DOLNE
        ex_color = (200, 0, 0) if self.exchange_mode else (80, 80, 80)
        btns = [
            (self.btn_ok, "ZATWIERDŹ", self.font_ui, (80,80,80)),
            (self.btn_ex, "WYMIANA", self.font_ui, ex_color),
            (self.btn_end, "ZAKOŃCZ I PODSUMUJ", self.font_ui_tiny, (80,80,80)),
            (self.btn_exit, "WYJDŹ", self.font_ui, (80,80,80))
        ]
        for b, txt, font, col in btns:
            pygame.draw.rect(self.screen, col, b, border_radius=8)
            pygame.draw.rect(self.screen, (200,200,200), b, 1, border_radius=8)
            t_s = font.render(txt, True, (255,255,255))
            self.screen.blit(t_s, (b.centerx - t_s.get_width()//2, b.centery - t_s.get_height()//2))

        # PUNKTY (PO BOKACH PRZYCISKÓW)
        p1_pts = self.font_ui.render(f"{self.player_names[1]}: {self.scores[1]}", True, (255,255,255))
        self.screen.blit(p1_pts, (20, sh * 0.92))
        p2_pts = self.font_ui.render(f"{self.player_names[2]}: {self.scores[2]}", True, (255,255,255))
        self.screen.blit(p2_pts, (sw - p2_pts.get_width() - 20, sh * 0.92))

        if self.show_res_menu: self.draw_res_list(sw, sh)
        if self.game_state == "GAME_OVER": self.draw_summary_overlay(sw, sh)
        if self.floating_tile:
            mx, my = pygame.mouse.get_pos()
            self.draw_tile_obj(self.floating_tile, mx-rack_size//2, my-rack_size//2, (255,255,200), rack_size)
        pygame.display.flip()

    def draw_res_list(self, sw, sh):
        menu_w, menu_h = 200, len(self.resolutions) * 30
        self.res_rects = []
        pygame.draw.rect(self.screen, (50,50,50), (10, 30, menu_w, menu_h))
        for i, res in enumerate(self.resolutions):
            r_rect = pygame.Rect(10, 30 + i*30, menu_w, 30)
            self.res_rects.append((r_rect, res))
            pygame.draw.rect(self.screen, (100,100,100), r_rect, 1)
            t = self.font_ui_tiny.render(f"{res[0]} x {res[1]}", True, (255,255,255))
            self.screen.blit(t, (r_rect.x + 10, r_rect.y + 5))

    def draw_start_screen(self, sw, sh):
        overlay = pygame.Surface((sw, sh)); overlay.fill((20, 20, 20))
        self.screen.blit(overlay, (0,0))
        self.rect_p1 = pygame.Rect(sw//2 - 200, sh//2 - 60, 400, 45)
        self.rect_p2 = pygame.Rect(sw//2 - 200, sh//2 + 5, 400, 45)
        pygame.draw.rect(self.screen, (120,120,0) if self.input_active==1 else (60,60,60), self.rect_p1, border_radius=5)
        pygame.draw.rect(self.screen, (120,120,0) if self.input_active==2 else (60,60,60), self.rect_p2, border_radius=5)
        t1 = self.font_ui.render(f"{self.player_names[1]}", True, (255,255,255))
        t2 = self.font_ui.render(f"{self.player_names[2]}", True, (255,255,255))
        self.screen.blit(t1, (self.rect_p1.x+10, self.rect_p1.y+5))
        self.screen.blit(t2, (self.rect_p2.x+10, self.rect_p2.y+5))
        self.btn_start = pygame.Rect(sw//2-75, sh//2+80, 150, 50)
        pygame.draw.rect(self.screen, (0,150,0), self.btn_start, border_radius=10)
        st = self.font_ui.render("START", True, (255,255,255))
        self.screen.blit(st, (self.btn_start.centerx-st.get_width()//2, self.btn_start.centery-st.get_height()//2))
        pygame.display.flip()

    def draw_summary_overlay(self, sw, sh):
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA); overlay.fill((0,0,0,240))
        self.screen.blit(overlay, (0,0))
        win_txt = self.font_ui.render(self.winner_text, True, (255,255,0))
        self.screen.blit(win_txt, (sw//2 - win_txt.get_width()//2, sh//2 - 100))
        s1 = self.font_ui.render(f"{self.player_names[1]}: {self.scores[1]} pkt", True, (255,255,255))
        s2 = self.font_ui.render(f"{self.player_names[2]}: {self.scores[2]} pkt", True, (255,255,255))
        self.screen.blit(s1, (sw//2 - s1.get_width()//2, sh//2 - 20))
        self.screen.blit(s2, (sw//2 - s2.get_width()//2, sh//2 + 25))
        self.btn_ok_final = pygame.Rect(sw//2-60, sh//2+100, 120, 50)
        pygame.draw.rect(self.screen, (0,180,0), self.btn_ok_final, border_radius=5)
        ok_t = self.font_ui.render("OK", True, (255,255,255))
        self.screen.blit(ok_t, (self.btn_ok_final.centerx-ok_t.get_width()//2, self.btn_ok_final.centery-ok_t.get_height()//2))

    def handle_click(self, pos):
        sw, sh = self.screen.get_size()
        mx, my = pos
        
        if self.show_res_menu:
            for rect, res in self.res_rects:
                if rect.collidepoint(mx, my):
                    self.screen = pygame.display.set_mode(res, pygame.RESIZABLE)
                    self.recalculate_dimensions()
                    self.show_res_menu = False
                    return
            self.show_res_menu = False; return

        if self.game_state == "START_SCREEN":
            if self.btn_start.collidepoint(mx, my): self.game_state = "PLAYING"
            if self.rect_p1.collidepoint(mx, my): self.input_active = 1
            if self.rect_p2.collidepoint(mx, my): self.input_active = 2
            return
            
        if self.game_state == "GAME_OVER":
            if self.btn_ok_final.collidepoint(mx, my): pygame.quit(); sys.exit()
            return

        if self.btn_res_toggle.collidepoint(mx, my): self.show_res_menu = True; return
        if self.btn_ok.collidepoint(mx, my): self.confirm_move(); return
        if self.btn_end.collidepoint(mx, my): self.end_game(manual=True); return
        if self.btn_exit.collidepoint(mx, my): self.handle_exit_logic(); return
        if self.btn_ex.collidepoint(mx, my): self.handle_exchange(); return

        rack_size = int(self.tile_size * 1.1)
        # Kliknięcia stojaków
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

        # Kliknięcie w planszę
        c, r = (mx - self.board_x) // self.tile_size, (my - self.board_y) // self.tile_size
        if 0 <= r < self.board_dim and 0 <= c < self.board_dim:
            if self.floating_tile and not self.board_state[r][c]:
                self.board_state[r][c] = {'letter': self.floating_tile, 'new': True}; self.floating_tile = None; self.play_snd(1)
            elif self.board_state[r][c] and self.board_state[r][c]['new']:
                self.racks[self.current_player].append(self.board_state[r][c]['letter']); self.board_state[r][c] = None; self.play_snd(1)

    def handle_exit_logic(self):
        now = pygame.time.get_ticks()
        if now - self.last_exit_click_time < 500: pygame.quit(); sys.exit()
        else: self.return_tiles_to_rack(); self.exchange_mode = False; self.last_exit_click_time = now

    def end_game(self, manual=False):
        if not manual and not self.bag:
            p1_rem = sum(LETTERS[l][1] for l in self.racks[1])
            p2_rem = sum(LETTERS[l][1] for l in self.racks[2])
            if not self.racks[1]: self.scores[1] += p2_rem; self.scores[2] -= p2_rem
            elif not self.racks[2]: self.scores[2] += p1_rem; self.scores[1] -= p1_rem
        
        if self.scores[1] > self.scores[2]: self.winner_text = f"ZWYCIĘŻYŁ: {self.player_names[1]}"
        elif self.scores[2] > self.scores[1]: self.winner_text = f"ZWYCIĘŻYŁ: {self.player_names[2]}"
        else: self.winner_text = "REMIS!"
        
        with open(self.report_walak_file, "a", encoding="utf-8") as f:
            f.write(f"--- KONIEC GRY --- Finał: {self.scores[1]} - {self.scores[2]}\n")
        self.game_state = "GAME_OVER"

    def confirm_move(self):
        new_tiles = [(r, c) for r in range(self.board_dim) for c in range(self.board_dim) if self.board_state[r][c] and self.board_state[r][c]['new']]
        if not new_tiles:
            self.calc_text = "PAS"; self.current_player = 2 if self.current_player == 1 else 1; return
        
        pts, math = calc.calculate_full_score(self.board_state, self.premium_map, self.board_dim, LETTERS)
        if pts > 0:
            self.calc_text = math
            self.scores[self.current_player] += pts
            with open(self.report_walak_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {self.player_names[self.current_player]} | {math} | Worek: {len(self.bag)}\n")
            for r, c in new_tiles: self.board_state[r][c]['new'] = False
            self.racks[self.current_player].extend(self.draw_tiles(7 - len(self.racks[self.current_player])))
            if not self.bag and not self.racks[self.current_player]: self.end_game(manual=False)
            else: self.current_player = 2 if self.current_player == 1 else 1
            self.play_snd(2)
        else: self.play_snd(3)

    def handle_exchange(self):
        if len(self.bag) < 7: self.calc_text = "Worek zbyt pusty!"; return
        if not self.exchange_mode: self.return_tiles_to_rack(); self.exchange_mode = True
        else:
            if self.exchange_selected:
                self.exchange_selected.sort(reverse=True)
                for i in self.exchange_selected: self.bag.append(self.racks[self.current_player].pop(i))
                random.shuffle(self.bag); self.racks[self.current_player].extend(self.draw_tiles(len(self.exchange_selected)))
                self.current_player = 2 if self.current_player == 1 else 1; self.play_snd(4)
            self.exchange_mode = False; self.exchange_selected = []

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.VIDEORESIZE: self.recalculate_dimensions()
                if event.type == pygame.KEYDOWN and self.game_state == "START_SCREEN":
                    if event.key == pygame.K_BACKSPACE: self.player_names[self.input_active] = self.player_names[self.input_active][:-1]
                    else: self.player_names[self.input_active] += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN: self.handle_click(event.pos)
            self.draw(); clock.tick(60)

if __name__ == "__main__": ScrabbleGame().run()
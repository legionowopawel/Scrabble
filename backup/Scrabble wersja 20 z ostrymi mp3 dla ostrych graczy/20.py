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
        pygame.display.set_caption("SCRABBLE PRO - Pełna Wersja")
        
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
        self.floating_tile = None 
        
        self.recalculate_dimensions()
        self.reset_game()

    def load_resolutions(self):
        res = []
        if os.path.exists("rozdzielczosc.txt"):
            with open("rozdzielczosc.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if 'x' in line.lower():
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
        
        self.font_tile = pygame.font.SysFont("Arial", int(self.tile_size * 0.5), bold=True)
        self.font_small = pygame.font.SysFont("Arial", int(self.tile_size * 0.25), bold=True)
        self.font_ui = pygame.font.SysFont("Verdana", int(sh * 0.022), bold=True)
        self.font_ui_tiny = pygame.font.SysFont("Verdana", int(sh * 0.014), bold=True)
        self.font_calc = pygame.font.SysFont("Courier New", int(sh * 0.018), bold=True)

        self.rack_size = int(self.tile_size * 1.1)
        self.rack1_x = self.board_x - self.tile_size - self.rack_size
        self.rack2_x = self.board_x + (self.board_dim * self.tile_size) + self.tile_size

        btn_w, btn_h, spacing = int(sw * 0.18), int(sh * 0.06), 15
        start_x = (sw - (4 * btn_w + 3 * spacing)) // 2
        btn_y = int(sh * 0.91)

        self.btn_ok = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        self.btn_ex = pygame.Rect(start_x + (btn_w + spacing), btn_y, btn_w, btn_h)
        self.btn_end = pygame.Rect(start_x + 2 * (btn_w + spacing), btn_y, btn_w, btn_h)
        self.btn_exit = pygame.Rect(start_x + 3 * (btn_w + spacing), btn_y, btn_w, btn_h)
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

    def draw_tiles(self, n):
        tiles = []
        for _ in range(min(n, len(self.bag))):
            tiles.append(self.bag.pop())
        return tiles

    def return_tiles_to_rack(self):
        if self.floating_tile:
            self.racks[self.current_player].append(self.floating_tile)
            self.floating_tile = None
        for r in range(self.board_dim):
            for c in range(self.board_dim):
                tile = self.board_state[r][c]
                if tile and tile['new']:
                    self.racks[self.current_player].append(tile['letter'])
                    self.board_state[r][c] = None

    def draw_tile_obj(self, letter, x, y, color, size):
        rect = pygame.Rect(x, y, size-2, size-2)
        pygame.draw.rect(self.screen, color, rect, border_radius=int(size*0.1))
        pygame.draw.rect(self.screen, (0,0,0), rect, 1)
        l_surf = self.font_tile.render(letter, True, COLOR_TEXT)
        self.screen.blit(l_surf, (x + (size - l_surf.get_width())//2, y + size//10))
        p_surf = self.font_small.render(str(LETTERS[letter][1]), True, COLOR_TEXT)
        self.screen.blit(p_surf, (x + size - p_surf.get_width() - 2, y + size - p_surf.get_height() - 2))

    def draw_res_list(self):
        menu_w, menu_h = 220, len(self.resolutions) * 30
        self.res_rects = []
        pygame.draw.rect(self.screen, (30,30,30), (10, 35, menu_w, menu_h))
        for i, res in enumerate(self.resolutions):
            r_rect = pygame.Rect(10, 35 + i*30, menu_w, 30)
            self.res_rects.append((r_rect, res))
            t = self.font_ui_tiny.render(f"{res[0]} x {res[1]}", True, (255,255,255))
            self.screen.blit(t, (r_rect.x + 10, r_rect.y + 5))

    def draw(self):
        sw, sh = self.screen.get_size()
        if self.game_state == "START_SCREEN":
            self.draw_start_screen(sw, sh)
            return

        self.screen.fill(COLOR_BG)
        pygame.draw.rect(self.screen, (30, 30, 30), (0, 0, sw, 40))
        
        # Przyciski góra
        pygame.draw.rect(self.screen, (70, 70, 70), self.btn_res_toggle, border_radius=4)
        res_t = self.font_ui_tiny.render("Rozdzielczość", True, (255, 255, 255))
        self.screen.blit(res_t, (self.btn_res_toggle.centerx - res_t.get_width()//2, self.btn_res_toggle.centery - res_t.get_height()//2))

        bag_count_txt = self.font_ui.render(f"W worku: {len(self.bag)}", True, (255, 255, 0))
        self.screen.blit(bag_count_txt, (sw // 2 - bag_count_txt.get_width() // 2, 5))

        turn_txt = self.font_ui.render(f"GRACZ: {self.player_names[self.current_player]}", True, (255, 255, 255))
        self.screen.blit(turn_txt, (sw//2 - turn_txt.get_width()//2, 45))
        if self.calc_text:
            c_surf = self.font_calc.render(self.calc_text, True, (0, 255, 0))
            self.screen.blit(c_surf, (sw//2 - c_surf.get_width()//2, 85))

        # PLANSZA Z NAPISAMI PROMOCJI
        for r in range(self.board_dim):
            for c in range(self.board_dim):
                x, y = self.board_x + c * self.tile_size, self.board_y + r * self.tile_size
                rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
                prem = self.premium_map.get((r, c))
                
                # Tło pola
                pygame.draw.rect(self.screen, prem[2] if prem else COLOR_BOARD, rect)
                pygame.draw.rect(self.screen, COLOR_GRID, rect, 1)
                
                tile = self.board_state[r][c]
                if tile:
                    t_col = (200, 255, 200) if tile['new'] else COLOR_TILE
                    self.draw_tile_obj(tile['letter'], x, y, t_col, self.tile_size)
                elif prem:
                    # TUTAJ PRZYWRÓCONE NAPISY: np. 3S lub 2L
                    label = f"{prem[1]}{prem[0]}"
                    p_txt = self.font_small.render(label, True, (255,255,255))
                    self.screen.blit(p_txt, (x + (self.tile_size - p_txt.get_width())//2, y + (self.tile_size - p_txt.get_height())//2))

        # STOJAKI
        for p in [1, 2]:
            rx = self.rack1_x if p == 1 else self.rack2_x
            for i, l in enumerate(self.racks[p]):
                col = COLOR_SELECT if (self.exchange_mode and self.current_player==p and i in self.exchange_selected) else COLOR_TILE
                self.draw_tile_obj(l, rx, self.board_y + i*self.rack_size, col, self.rack_size)

        # PRZYCISKI DOLNE
        ex_color = (0, 100, 200) if self.exchange_mode else (80, 80, 80)
        btns = [(self.btn_ok, "OK", (0, 100, 0)), (self.btn_ex, "WYMIANA", ex_color), 
                (self.btn_end, "PODSUMUJ", (60, 60, 60)), (self.btn_exit, "WYJDŹ", (150, 0, 0))]
        for b, txt, col in btns:
            pygame.draw.rect(self.screen, col, b, border_radius=8)
            t_s = self.font_ui_tiny.render(txt, True, (255,255,255))
            self.screen.blit(t_s, (b.centerx - t_s.get_width()//2, b.centery - t_s.get_height()//2))

        # WYNIKI
        p1_pts = self.font_ui.render(f"{self.player_names[1]}: {self.scores[1]}", True, (255,255,255))
        self.screen.blit(p1_pts, (20, sh * 0.92))
        p2_pts = self.font_ui.render(f"{self.player_names[2]}: {self.scores[2]}", True, (255,255,255))
        self.screen.blit(p2_pts, (sw - p2_pts.get_width() - 20, sh * 0.92))

        if self.show_res_menu: self.draw_res_list()
        if self.game_state == "GAME_OVER": self.draw_summary_overlay(sw, sh)
        if self.floating_tile:
            mx, my = pygame.mouse.get_pos()
            self.draw_tile_obj(self.floating_tile, mx-self.rack_size//2, my-self.rack_size//2, (255,255,200), self.rack_size)
        pygame.display.flip()

    def draw_start_screen(self, sw, sh):
        self.screen.fill((20, 30, 20))
        self.rect_p1 = pygame.Rect(sw//2 - 200, sh//2 - 60, 400, 45)
        self.rect_p2 = pygame.Rect(sw//2 - 200, sh//2 + 5, 400, 45)
        pygame.draw.rect(self.screen, (100, 100, 0) if self.input_active==1 else (50, 50, 50), self.rect_p1, border_radius=5)
        pygame.draw.rect(self.screen, (100, 100, 0) if self.input_active==2 else (50, 50, 50), self.rect_p2, border_radius=5)
        t1 = self.font_ui.render(self.player_names[1], True, (255,255,255))
        t2 = self.font_ui.render(self.player_names[2], True, (255,255,255))
        self.screen.blit(t1, (self.rect_p1.x+10, self.rect_p1.y+5))
        self.screen.blit(t2, (self.rect_p2.x+10, self.rect_p2.y+5))
        self.btn_start = pygame.Rect(sw//2-75, sh//2+80, 150, 50)
        pygame.draw.rect(self.screen, (0,150,0), self.btn_start, border_radius=10)
        st = self.font_ui.render("START", True, (255,255,255))
        self.screen.blit(st, (self.btn_start.centerx-st.get_width()//2, self.btn_start.centery-st.get_height()//2))
        pygame.display.flip()

    def handle_click(self, pos):
        mx, my = pos
        if self.show_res_menu:
            for rect, res in self.res_rects:
                if rect.collidepoint(mx, my):
                    self.screen = pygame.display.set_mode(res, pygame.RESIZABLE)
                    self.recalculate_dimensions(); self.show_res_menu = False; return
            self.show_res_menu = False; return

        if self.game_state == "START_SCREEN":
            if self.btn_start.collidepoint(mx, my): self.game_state = "PLAYING"
            elif self.rect_p1.collidepoint(mx, my): self.input_active = 1
            elif self.rect_p2.collidepoint(mx, my): self.input_active = 2
            return

        if self.btn_res_toggle.collidepoint(mx, my): self.show_res_menu = True; return
        if self.btn_ok.collidepoint(mx, my): self.confirm_move(); return
        if self.btn_ex.collidepoint(mx, my): self.handle_exchange(); return
        if self.btn_end.collidepoint(mx, my): self.end_game(manual=True); return
        if self.btn_exit.collidepoint(mx, my): self.handle_exit_logic(); return

        curr_rack_x = self.rack1_x if self.current_player == 1 else self.rack2_x
        if curr_rack_x <= mx <= curr_rack_x + self.rack_size:
            if self.floating_tile:
                if len(self.racks[self.current_player]) < 7:
                    self.racks[self.current_player].append(self.floating_tile)
                    self.floating_tile = None; self.play_snd(1)
                return
            else:
                idx = (my - self.board_y) // self.rack_size
                if 0 <= idx < len(self.racks[self.current_player]):
                    if self.exchange_mode:
                        if idx in self.exchange_selected: self.exchange_selected.remove(idx)
                        else: self.exchange_selected.append(idx)
                    else:
                        self.floating_tile = self.racks[self.current_player].pop(idx)
                        self.play_snd(1)
                return

        c, r = (mx - self.board_x) // self.tile_size, (my - self.board_y) // self.tile_size
        if 0 <= r < self.board_dim and 0 <= c < self.board_dim:
            if self.floating_tile and not self.board_state[r][c]:
                self.board_state[r][c] = {'letter': self.floating_tile, 'new': True}
                self.floating_tile = None; self.play_snd(1)
            elif self.board_state[r][c] and self.board_state[r][c]['new']:
                self.racks[self.current_player].append(self.board_state[r][c]['letter'])
                self.board_state[r][c] = None; self.play_snd(1)

    def handle_exchange(self):
        if len(self.bag) < 7: self.calc_text = "Za mało w worku!"; return
        if not self.exchange_mode:
            self.return_tiles_to_rack()
            self.exchange_mode = True; self.exchange_selected = []; self.calc_text = "Wybierz litery i kliknij WYMIANA"
        else:
            if self.exchange_selected:
                self.exchange_selected.sort(reverse=True)
                for i in self.exchange_selected:
                    self.bag.append(self.racks[self.current_player].pop(i))
                random.shuffle(self.bag)
                needed = 7 - len(self.racks[self.current_player])
                self.racks[self.current_player].extend(self.draw_tiles(needed))
                self.current_player = 2 if self.current_player == 1 else 1
                self.play_snd(4); self.calc_text = "Wymieniono."
            self.exchange_mode = False; self.exchange_selected = []

    def confirm_move(self):
        new_tiles = [(r, c) for r in range(self.board_dim) for c in range(self.board_dim) 
                     if self.board_state[r][c] and self.board_state[r][c]['new']]
        if not new_tiles:
            self.current_player = 2 if self.current_player == 1 else 1; return
        pts, math = calc.calculate_full_score(self.board_state, self.premium_map, self.board_dim, LETTERS)
        if pts > 0:
            self.scores[self.current_player] += pts
            for r, c in new_tiles: self.board_state[r][c]['new'] = False
            needed = 7 - len(self.racks[self.current_player])
            self.racks[self.current_player].extend(self.draw_tiles(needed))
            self.current_player = 2 if self.current_player == 1 else 1
            self.play_snd(2); self.calc_text = math
        else: self.play_snd(3)

    def end_game(self, manual=False):
        for p in [1, 2]: self.scores[p] -= sum(LETTERS[l][1] for l in self.racks[p])
        s1, s2 = self.scores[1], self.scores[2]
        self.winner_text = f"WYGRAŁ {self.player_names[1]}!" if s1 > s2 else (f"WYGRAŁ {self.player_names[2]}!" if s2 > s1 else "REMIS!")
        self.game_state = "GAME_OVER"

    def handle_exit_logic(self):
        now = pygame.time.get_ticks()
        if now - self.last_exit_click_time < 500: pygame.quit(); sys.exit()
        else:
            self.return_tiles_to_rack(); self.exchange_mode = False
            self.calc_text = "Kliknij 2x by wyjść"; self.last_exit_click_time = now

    def draw_summary_overlay(self, sw, sh):
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA); overlay.fill((0,0,0,230))
        self.screen.blit(overlay, (0,0))
        win_t = self.font_ui.render(self.winner_text, True, (255,255,0))
        self.screen.blit(win_t, (sw//2 - win_t.get_width()//2, sh//2 - 50))
        self.btn_ok_final = pygame.Rect(sw//2-50, sh//2+50, 100, 40)
        pygame.draw.rect(self.screen, (0,150,0), self.btn_ok_final)
        ok_t = self.font_ui_tiny.render("KONIEC", True, (255,255,255))
        self.screen.blit(ok_t, (self.btn_ok_final.centerx-ok_t.get_width()//2, self.btn_ok_final.centery-ok_t.get_height()//2))

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.VIDEORESIZE: self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE); self.recalculate_dimensions()
                if event.type == pygame.MOUSEBUTTONDOWN: self.handle_click(event.pos)
                if event.type == pygame.KEYDOWN:
                    if self.game_state == "START_SCREEN":
                        if event.key == pygame.K_BACKSPACE: self.player_names[self.input_active] = self.player_names[self.input_active][:-1]
                        elif event.key == pygame.K_RETURN: self.game_state = "PLAYING"
                        else: self.player_names[self.input_active] += event.unicode
                    elif event.key == pygame.K_ESCAPE: self.return_tiles_to_rack()
            self.draw(); clock.tick(60)

if __name__ == "__main__":
    ScrabbleGame().run()
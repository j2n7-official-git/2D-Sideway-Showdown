"""
twodss_pause.py — Hộp thoại PAUSE riêng cho 2D Sideway Showdown
─────────────────────────────────────────────────────────────────────
• Mở/đóng bằng phím  P  (đúng như icon pause chữ "P" trong game).
• Panel (cái bảng nâu "PAUSED" + bảng KEYBINDS) → em XUẤT ẢNH ra rồi
  thả vào: assets/ui-race-mode/2dss-pause-panel.png
  Module này chỉ VẼ 3 NÚT cam đè lên đúng 3 ô trống của panel.
• 3 nút: RESUME · RESTART · QUIT TO SHOWROOM
• Nút: nền cam, gradient linear tối dần 12% tại vị trí 64% (dọc).
• Chữ nút: font SVN-New Athletic M54 trong assets/font/.

CÁCH DÙNG (trong file track-*.py): xem khối ví dụ cuối file.
─────────────────────────────────────────────────────────────────────
"""
import pygame, os, sys, glob

# ── PATH an toàn cho .exe ───────────────────────────────────────────
def _resource_path(base_dir, rel):
    base = sys._MEIPASS if hasattr(sys,"_MEIPASS") else base_dir
    return os.path.join(base, rel)

# ── MÀU ─────────────────────────────────────────────────────────────
ORANGE       = (236, 138, 32)     # nền nút cơ bản (cam)
ORANGE_HOVER = (252, 162, 56)     # khi rê chuột / chọn
TEXT_CREAM   = (250, 238, 222)    # chữ kem (khớp tông panel)
TEXT_DARK    = ( 60,  28,  10)    # chữ nâu đậm (tương phản trên cam)
DIM          = (0, 0, 0, 150)     # lớp tối nền game phía sau

# ── Vị trí 3 ô nút (TỈ LỆ theo panel — đo thật từ ảnh thiết kế) ──────
#   x: 0.237 → 0.761  |  box1 0.144-0.250 · box2 0.281-0.387 · box3 0.418-0.525
_BOX_X0, _BOX_X1 = 0.237, 0.761
_BOXES_Y = [(0.144, 0.250), (0.281, 0.387), (0.418, 0.525)] #-12px để đưa lên phía trên

# Gradient: tối dần tới -12% tại vị trí 64%, sau đó giữ nguyên.
_GRAD_DARK = 0.12
_GRAD_STOP = 0.64


def _make_gradient_button(w, h, base, radius=14):
    """Nút bo góc, nền base với gradient dọc tối dần 12% ở mốc 64%."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        if t <= _GRAD_STOP:
            f = 1.0 - _GRAD_DARK * (t / _GRAD_STOP)     # 1.0 → 0.88
        else:
            f = 1.0 - _GRAD_DARK                         # giữ 0.88
        col = (int(base[0]*f), int(base[1]*f), int(base[2]*f))
        pygame.draw.line(surf, col, (0, y), (w, y))
    # mặt nạ bo góc
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255,255,255,255), mask.get_rect(), border_radius=radius)
    surf.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    return surf


class PauseMenu:
    """Hộp thoại pause. Trả action: 'resume' | 'restart' | 'quit_showroom'."""

    BUTTONS = [
        ("resume",        "RESUME"),
        ("restart",       "RESTART"),
        ("quit_showroom", "QUIT TO SHOWROOM"),
    ]

    def __init__(self, screen, base_dir,
                 panel_rel="assets/ui-race-mode/2dss-pause-panel.png",
                 panel_scale=0.72):
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        self.base_dir = base_dir
        self.open = False
        self.sel = 0                      # nút đang chọn (cho điều khiển bàn phím)

        # ── Panel ảnh em xuất ra ──
        self.panel = None
        p = _resource_path(base_dir, panel_rel)
        try:
            raw = pygame.image.load(p).convert_alpha()
            pw = int(self.sw * panel_scale)
            ph = int(raw.get_height() * pw / raw.get_width())
            self.panel = pygame.transform.smoothscale(raw, (pw, ph))
            print(f"[PAUSE] panel {self.panel.get_size()}")
        except Exception as e:
            print(f"[PAUSE] panel chưa có ({p}) → dùng nền tạm. {e}")
            pw, ph = int(self.sw*panel_scale), int(self.sh*panel_scale*0.83)

        self.prect = pygame.Rect(0, 0, pw, ph)
        self.prect.center = (self.sw//2, self.sh//2)

        # ── Font ──
        self.font = self._load_font(int(ph * 0.05))

        # ── Tạo rect + surface cho 3 nút (theo tỉ lệ panel) ──
        self.btn_rects, self.btn_surf, self.btn_surf_hover = [], [], []
        bx0 = self.prect.x + int(_BOX_X0 * pw)
        bx1 = self.prect.x + int(_BOX_X1 * pw)
        bw  = bx1 - bx0
        for (y0f, y1f) in _BOXES_Y:
            by0 = self.prect.y + int(y0f * ph)
            by1 = self.prect.y + int(y1f * ph)
            r = pygame.Rect(bx0, by0, bw, by1 - by0)
            self.btn_rects.append(r)
            self.btn_surf.append(_make_gradient_button(r.w, r.h, ORANGE))
            self.btn_surf_hover.append(_make_gradient_button(r.w, r.h, ORANGE_HOVER))

    def _load_font(self, size):
        # tự dò file font "athletic" trong assets/font/
        fdir = _resource_path(self.base_dir, os.path.join("assets","fonts"))
        cands = []
        cands += [os.path.join(fdir, n) for n in
                  ("SVN-New Athletic M54.ttf")]
        for c in cands:
            if os.path.exists(c):
                try:
                    print(f"[PAUSE] font: {os.path.basename(c)}")
                    return pygame.font.Font(c, size)
                except Exception as e:
                    print(f"[PAUSE] font lỗi {c}: {e}")
        print("[PAUSE] không thấy font athletic → fallback arial bold")
        return pygame.font.SysFont("arial", size, bold=True)

    # ── ĐIỀU KHIỂN ──────────────────────────────────────────────────
    def toggle(self):
        self.open = not self.open
        if self.open: self.sel = 0

    def handle_event(self, ev):
        """Gọi trong vòng lặp sự kiện. Trả 'resume'|'restart'|'quit_showroom'
        khi 1 nút được kích, ngược lại None. Tự xử lý đóng/mở bằng P."""
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_p:
            self.toggle(); return None
        if not self.open:
            return None
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.open = False; return "resume"
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.BUTTONS)
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.BUTTONS)
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._fire(self.sel)
        if ev.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.btn_rects):
                if r.collidepoint(ev.pos): self.sel = i
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, r in enumerate(self.btn_rects):
                if r.collidepoint(ev.pos): return self._fire(i)
        return None

    def _fire(self, i):
        action = self.BUTTONS[i][0]
        if action == "resume":
            self.open = False
        return action

    # ── VẼ ──────────────────────────────────────────────────────────
    def draw(self):
        """Vẽ overlay pause LÊN TRÊN frame game đã render. Gọi cuối mỗi
        frame khi self.open == True (trước pygame.display.flip())."""
        if not self.open:
            return
        dim = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        dim.fill(DIM)
        self.screen.blit(dim, (0, 0))
        if self.panel is not None:
            self.screen.blit(self.panel, self.prect)
        for i, r in enumerate(self.btn_rects):
            surf = self.btn_surf_hover[i] if i == self.sel else self.btn_surf[i]
            self.screen.blit(surf, r)
            label = self.BUTTONS[i][1]
            col = TEXT_DARK if i == self.sel else TEXT_CREAM
            txt = self.font.render(label, True, col)
            self.screen.blit(txt, txt.get_rect(center=r.center))


# ════════════════════════════════════════════════════════════════════
# TÍCH HỢP vào track-*.py — chỉ vài dòng:
#
#   from twodss_pause import PauseMenu
#   pause = PauseMenu(screen, BASE_DIR)
#
#   # trong vòng lặp sự kiện:
#   for ev in pygame.event.get():
#       if ev.type == pygame.QUIT: running = False
#       act = pause.handle_event(ev)        # P để mở/đóng
#       if act == "restart":      ...reset ván đua (countdown_t=COUNTDOWN_START, spawn lại)...
#       elif act == "quit_showroom": running = False   # hoặc gọi màn showroom
#       # act == "resume" hoặc None → chạy tiếp
#
#   # khi pause.open == True → DỪNG cập nhật vật lý:
#   if race_active and not pause.open:
#       player.update_player(...);  for bot in bots: bot.update_bot(...)
#
#   # cuối frame, sau khi vẽ HUD, TRƯỚC display.flip():
#   pause.draw()
#   pygame.display.flip()
# ════════════════════════════════════════════════════════════════════

# ── CHẠY THỬ ĐỘC LẬP (xem nút trông ra sao): python twodss_pause.py ──
if __name__ == "__main__":
    pygame.init()
    scr = pygame.display.set_mode((1280, 800))
    pygame.display.set_caption("PauseMenu preview — nhấn P")
    base = os.path.dirname(os.path.abspath(__file__))
    pm = PauseMenu(scr, base); pm.open = True
    clk = pygame.time.Clock(); run = True
    while run:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: run = False
            a = pm.handle_event(ev)
            if a: print("ACTION:", a)
            if a == "quit_showroom": run = False
        scr.fill((20, 22, 30))
        pm.draw()
        pygame.display.flip(); clk.tick(60)
    pygame.quit()

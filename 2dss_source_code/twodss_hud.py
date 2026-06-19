"""
=====================================================================
TWODSS_HUD.PY  —  2D Sideway Showdown
HUD rebuild — Phase 1 + Nitro bar
=====================================================================

Assets: BASE_DIR/assets/ui-race-mode/
  Phase 1 : paused.png, 2dss-ui-racetime-board.png,
            2dss-ui-pos-board.png, 2dss-ui-lap-board.png
  Phase 2  : 2dss-ui-nitro-bar.png  (NITRO_W × NITRO_H px)

Nitro bar gradient fill — #97DCFC:
  bottom (0%)  →  100% brightness
  37% height   →   85% brightness  (-15%)
  74% height   →   70% brightness  (-30%)  ← giữ ở đây đến đỉnh
=====================================================================
"""

import pygame
import sys
import os


# =====================================================================
# HELPERS
# =====================================================================

def _fmt_time(secs: float) -> str:
    secs = max(0.0, secs)
    m  = int(secs // 60)
    s  = int(secs  % 60)
    ms = int((secs - int(secs)) * 100)
    return f"{m:02d}:{s:02d}.{ms:02d}"


def _draw_shadow(surf, text, font, color, x, y, soff=2):
    surf.blit(font.render(text, True, (0, 0, 0)), (x + soff, y + soff))
    surf.blit(font.render(text, True, color),     (x, y))


def _find_asset(filename: str, base_dir: str = None) -> str | None:
    if hasattr(sys, '_MEIPASS'):
        for sub in [os.path.join("assets","ui-race-mode"), ""]:
            p = os.path.join(sys._MEIPASS, sub, filename)
            if os.path.isfile(p): return p

    candidates = []
    if base_dir:
        candidates += [
            os.path.join(base_dir, "assets", "ui-race-mode", filename),
            os.path.join(base_dir, "assets", filename),
            os.path.join(base_dir, filename),
        ]
    _here = os.path.dirname(os.path.abspath(__file__))
    candidates += [
        os.path.join(_here, "assets", "ui-race-mode", filename),
        os.path.join(_here, "assets", filename),
        os.path.join(_here, filename),
        os.path.join(os.getcwd(), "assets", "ui-race-mode", filename),
    ]
    for c in candidates:
        if os.path.isfile(c): return c
    return None


def _load_img(filename: str, base_dir: str = None):
    path = _find_asset(filename, base_dir)
    if path is None:
        print(f"[HUD] ✗ NOT FOUND: {filename}")
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        print(f"[HUD] ✓ loaded : {filename}  {img.get_size()}  ← {path}")
        return img
    except Exception as e:
        print(f"[HUD] ✗ error  : {filename} — {e}")
        return None


def _load_font(filename: str, size: int, base_dir: str = None) -> pygame.font.Font:
    candidates = []
    if hasattr(sys, '_MEIPASS'):
        candidates += [os.path.join(sys._MEIPASS, "assets", "fonts", filename),
                       os.path.join(sys._MEIPASS, filename)]
    if base_dir:
        candidates += [os.path.join(base_dir, "assets", "fonts", filename),
                       os.path.join(base_dir, "assets", filename),
                       os.path.join(base_dir, filename)]
    _here = os.path.dirname(os.path.abspath(__file__))
    candidates += [os.path.join(_here, "assets", "fonts", filename),
                   os.path.join(_here, "assets", filename),
                   os.path.join(_here, filename),
                   os.path.join(os.getcwd(), "assets", "fonts", filename)]
    for c in candidates:
        if os.path.isfile(c):
            try:
                font = pygame.font.Font(c, size)
                print(f"[HUD] ✓ font    : {filename}  size={size}  ← {c}")
                return font
            except Exception as e:
                print(f"[HUD] ✗ font err: {filename} — {e}")
    print(f"[HUD] ✗ font n/f: {filename} — fallback Arial {size}px")
    return pygame.font.SysFont("arial", size, bold=True)


def _apply_brightness(base_rgb: tuple, factor: float) -> tuple:
    """Nhân brightness theo factor. Clamp 0–255 (factor có thể > 1.0)."""
    return (min(255, max(0, int(base_rgb[0]*factor))),
            min(255, max(0, int(base_rgb[1]*factor))),
            min(255, max(0, int(base_rgb[2]*factor))))


# =====================================================================
# HUD CLASS
# =====================================================================

class HUD:

    # ── Tọa độ panels ─────────────────────────────────────────────────
    PAUSE_Y         =  10
    RACETIME_X      =  16
    RACETIME_Y      =  64
    POS_LAP_Y       =  64
    POS_LAP_MX      =  16
    POS_LAP_GAP     =   6

    # ── Scale panels chính (pause, racetime, pos, lap) ────────────────
    SCALE = 0.275

    # ── Text overlay ──────────────────────────────────────────────────
    FONT_SIZE_VAL   = 56
    FONT_VAL_FILE   = "Graduate-Regular.ttf"
    TEXT_PAD_L      = 20
    TEXT_VAL_Y_RATIO= 0.62
    VAL_COLOR       = (255, 255, 255)

    # ── Nitro bar ─────────────────────────────────────────────────────
    NITRO_X         =  25    # vị trí X (px) — góc trái thanh
    NITRO_Y         = 460    # vị trí Y (px) — góc trên thanh
    NITRO_W         = 135    # chiều RỘNG  thanh (px) — chỉnh trực tiếp
    NITRO_H         = 590    # chiều CAO   thanh (px) — chỉnh trực tiếp

    # Vùng fill bên trong ống (pixel offset từ viền ảnh — dễ chỉnh hơn tỉ lệ)
    #
    #   NITRO_X ──┐
    #             │← NITRO_FILL_L →│       │← NITRO_FILL_R →│
    #   NITRO_Y ──┼────────────────┼───────┼────────────────┤ ← NITRO_FILL_T (px từ trên)
    #             │                ░░░fill░░░                │
    #             │                ░░░fill░░░                │
    #             │                ░░░fill░░░                │
    #             ├────────────────┼───────┼────────────────┤ ← NITRO_H - NITRO_FILL_B
    #             │   bottle icon area (không fill vào)      │
    #   NITRO_Y   │                                          │
    #   +NITRO_H ─┘
    #
    # Ví dụ với NITRO_W=60, NITRO_H=350:
    #   L=18 → fill bắt đầu tại x+18
    #   R=18 → fill kết thúc tại x+42  (60-18)
    #   T= 3 → fill bắt đầu tại y+3
    #   B=80 → fill kết thúc tại y+270 (350-80)
    NITRO_FILL_L    =  30   # px từ viền TRÁI  ảnh → left  edge fill
    NITRO_FILL_R    =  30   # px từ viền PHẢI  ảnh → right edge fill  (fill_xr = x+W-R)
    NITRO_FILL_T    =   3    # px từ viền TRÊN  ảnh → top   edge fill (đặt 0 nó là MAX)
    NITRO_FILL_B    =  92   # px từ viền DƯỚI  ảnh → bottom edge fill (fill_yb = y+H-B)

    # Gradient fill — màu gốc + brightness theo chiều cao
    # #97DCFC = (151, 220, 252)
    # bottom (0%)  → 100% brightness
    # 37% height   →  85% brightness  (-15%)
    # 74% height   →  70% brightness  (-30%)  ← giữ từ đây đến đỉnh
    NITRO_BASE_CLR  = (0x97, 0xDC, 0xFC)
    NITRO_CLR_ACTIVE= (255, 140,  40)   # màu khi nitro đang bơm
    NITRO_CLR_CD    = ( 60,  60,  80)   # màu khi đang cooldown

    # Gradient stops — horizontal (trái→phải) — chỉnh 3 dòng này
    # factor nhân với NITRO_BASE_CLR:  1.0=base  1.15=+15%sáng  0.70=-30%tối
    NITRO_GRAD_P0   = 1.00   # x=0%   trái  — base color
    NITRO_GRAD_P37  = 1.15   # x=37%  peak  — sáng hơn base +15%
    NITRO_GRAD_P74  = 0.70   # x=74%+ phải  — tối hơn base -30%

    # ── Speedometer — góc dưới PHẢI ───────────────────────────────
    #
    #   SPEEDO_W = đường kính px SAU khi scale — số pixel thật trên màn hình
    #   Dùng pixel tuyệt đối để tránh ảnh gốc quá to gây overflow
    #   Cả 2 ảnh giữ NGUYÊN tỉ lệ khung hình (không ép vuông)
    #   Tâm tự tính: cx = screen_W - speedo_w//2 - SPEEDO_MX
    #                cy = screen_H - speedo_h//2 - SPEEDO_MY
    SPEEDO_W            = 345   # ← đường kính px THẬT trên màn hình (chỉnh tại đây)
    SPEEDO_MX           =  25   # margin phải  (px từ viền phải màn hình)
    SPEEDO_MY           =  25   # margin dưới  (px từ viền dưới màn hình)
    YOU_SCALE           = 0.48  # scale YOU badge so với native size
    YOU_Y_OFFSET        = -85   # px từ car_y lên trên (âm = lên)
    SPEEDO_MAX_KPH      = 350   # max speed tất cả xe
    # scania_svempa_frostfire = 350 | r730 = 325 | pagani_utopia = 313
    # → kim full sweep khi đạt 350 KPH
    # → xe sedan 188 KPH chỉ lên ~54% mặt số (thực tế)
    # Chuyển đổi PowerPoint (CW+) → pygame (CCW+): negate rồi swap
    #   PowerPoint: 0KPH=320°, 300KPH=220°
    #   pygame:     0KPH= -220+360 =  220°   (CCW)
    #              300KPH= -320+360 = -40°   (=320° CCW = -40)
    #   Sweep: 220 → -40  (giảm dần -260° = CW ✓)
    #   Đổi dấu CẢ 2 nếu kim chạy ngược chiều
    NEEDLE_ANGLE_ZERO   =  225  # 0 KPH   → PowerPoint 320° → pygame 220°
    NEEDLE_ANGLE_MAX    =  -45  # 300 KPH → PowerPoint 220° → pygame -40°

    # Scale kim (tỉ lệ so với SPEEDO_W) — 1.0 = cùng kích cỡ mặt số
    # Kim GIỮ tỉ lệ khung hình gốc (rectangle, không ép vuông)
    NEEDLE_SCALE        =  0.5  # ← chỉnh nếu muốn kim to/nhỏ hơn mặt số

    # Offset tâm kim so với tâm taplo (px) — chỉnh khi kim lệch khỏi hub
    # Dương X = dịch phải | Âm X = dịch trái
    # Dương Y = dịch xuống | Âm Y = dịch lên
    NEEDLE_OFFSET_X     =   0   # ← chỉnh để căn kim vào tâm tròn xám
    NEEDLE_OFFSET_Y     =   -7   # ← chỉnh để căn kim vào tâm tròn xám

    # KPH digital display (seven-segment font)
    # File đặt tại: BASE_DIR/assets/fonts/
    SPEEDO_FONT_FILE    = "Seven Segment.ttf"          # assets/fonts/Seven Segment.ttf
    SPEEDO_FONT_SIZE    =  32   # px — tăng/giảm theo SPEEDO_W
    SPEEDO_KPH_OFFSET_Y =  88   # px từ tâm xuống dưới → vị trí ô số KPH (7–12px lên so với 95)
    SPEEDO_KPH_COLOR    = (255, 255, 255)  # màu chữ số KPH

    def __init__(self,
                 screen:        pygame.Surface,
                 total_racers:  int  = 6,
                 max_laps:      int  = 3,
                 screen_w:      int  = 1920,
                 screen_h:      int  = 1080,
                 base_dir:      str  = None,
                 car_screen_x:  int  = None,
                 car_screen_y:  int  = None):

        self.screen       = screen
        self.total_racers = total_racers
        self.max_laps     = max_laps
        self.W            = screen_w
        self.H            = screen_h
        self.base_dir     = base_dir
        self.car_x        = car_screen_x if car_screen_x is not None else screen_w // 2
        self.car_y        = car_screen_y if car_screen_y is not None else screen_h // 2

        # ── Fonts ────────────────────────────────────────────────────
        self.font_cd  = pygame.font.SysFont("arial", 60, bold=True)   # countdown 5-4-3-2-1
        self.font_go  = pygame.font.SysFont("arial", 70, bold=True)   # GO! to hơn +10px
        self.font_md  = pygame.font.SysFont("arial", 28, bold=True)
        self.font_xl  = pygame.font.SysFont("arial", 72, bold=True)
        self.font_val  = _load_font(self.FONT_VAL_FILE,  self.FONT_SIZE_VAL,  base_dir)
        # Seven-segment font cho đồng hồ tốc độ (luôn hiện từ đầu)
        self.font_kph  = _load_font(self.SPEEDO_FONT_FILE, self.SPEEDO_FONT_SIZE, base_dir)

        # ── Load assets ───────────────────────────────────────────────
        print("[HUD] ── Loading assets ────────────────────────────────")
        self._img_pause    = _load_img("paused.png",                 base_dir)
        self._img_racetime = _load_img("2dss-ui-racetime-board.png", base_dir)
        self._img_pos      = _load_img("2dss-ui-pos-board.png",      base_dir)
        self._img_lap      = _load_img("2dss-ui-lap-board.png",      base_dir)
        self._img_nitro    = _load_img("2dss-ui-nitro-bar.png",      base_dir)
        self._img_you      = _load_img("2dss-ui-urplace.png",         base_dir)
        self._img_speedo   = _load_img("2dss-speedometer.png",        base_dir)
        self._img_needle   = _load_img("2dss-needlemark.png",         base_dir)

        # ── Scale helper ──────────────────────────────────────────────
        def _sc(img, fallback, scale):
            if img is None:
                w, h = fallback
                return None, (int(w*scale), int(h*scale))
            w0, h0 = img.get_size()
            w1, h1 = max(1, int(w0*scale)), max(1, int(h0*scale))
            if abs(scale - 1.0) < 0.01:
                return img, (w0, h0)
            return pygame.transform.smoothscale(img, (w1, h1)), (w1, h1)

        self._img_pause,    self._sz_pause    = _sc(self._img_pause,    (54,  58),  self.SCALE)
        self._img_racetime, self._sz_racetime = _sc(self._img_racetime, (240, 80),  self.SCALE)
        self._img_pos,      self._sz_pos      = _sc(self._img_pos,      (150, 80),  self.SCALE)
        self._img_lap,      self._sz_lap      = _sc(self._img_lap,      (150, 80),  self.SCALE)
        # Nitro: scale đến đúng NITRO_W × NITRO_H pixel
        if self._img_nitro:
            self._img_nitro = pygame.transform.smoothscale(
                self._img_nitro, (self.NITRO_W, self.NITRO_H))
        self._sz_nitro = (self.NITRO_W, self.NITRO_H)

        # Speedometer: scale cả 2 ảnh về đúng SPEEDO_W px
        # Speedometer: scale về SPEEDO_W px (giữ aspect ratio, không ép vuông)
        if self._img_speedo:
            sw0, sh0 = self._img_speedo.get_size()
            # Fit theo chiều rộng = SPEEDO_W, chiều cao theo tỉ lệ gốc
            sw = self.SPEEDO_W
            sh = max(1, int(sh0 * sw / sw0))
            self._img_speedo = pygame.transform.smoothscale(self._img_speedo, (sw, sh))
            self._sz_speedo  = (sw, sh)
        else:
            self._sz_speedo = (self.SPEEDO_W, self.SPEEDO_W)

        # Kim: SPEEDO_W × NEEDLE_SCALE, GIỮ tỉ lệ khung hình gốc (KHÔNG ép vuông)
        if self._img_needle:
            nw0, nh0 = self._img_needle.get_size()
            nw2 = max(1, int(self.SPEEDO_W * self.NEEDLE_SCALE))
            nh2 = max(1, int(nh0 * nw2 / nw0))   # giữ tỉ lệ
            self._img_needle = pygame.transform.smoothscale(self._img_needle, (nw2, nh2))
            self._sz_needle  = (nw2, nh2)
            print(f"[HUD]   speedo: {self._sz_speedo}  needle: {self._sz_needle}")
        else:
            self._sz_needle = self._sz_speedo

        # YOU: scale giữ aspect ratio
        if self._img_you:
            yw0, yh0 = self._img_you.get_size()
            yw = max(1, int(yw0 * self.YOU_SCALE))
            yh = max(1, int(yh0 * self.YOU_SCALE))
            self._img_you = pygame.transform.smoothscale(self._img_you, (yw, yh))
            self._sz_you  = (yw, yh)
        else:
            self._sz_you = (120, 60)

        # ── Pre-render nitro gradient surface (full height, 100% fill) ─
        # Blit cắt theo mức nitro mỗi frame — không tính lại màu mỗi frame
        self._nitro_grad = self._build_nitro_gradient(self.NITRO_BASE_CLR)
        self._nitro_grad_active = self._build_nitro_gradient(self.NITRO_CLR_ACTIVE)

        # ── Tính tọa độ blit ─────────────────────────────────────────
        pw, _  = self._sz_pause
        posw, _= self._sz_pos
        lapw, _= self._sz_lap

        self._pos_pause    = (self.W // 2 - pw // 2, self.PAUSE_Y)
        self._pos_racetime = (self.RACETIME_X, self.RACETIME_Y)
        total_pl = posw + self.POS_LAP_GAP + lapw
        pos_bx   = self.W - total_pl - self.POS_LAP_MX
        lap_bx   = pos_bx + posw + self.POS_LAP_GAP
        self._pos_pos   = (pos_bx, self.POS_LAP_Y)
        self._pos_lap   = (lap_bx, self.POS_LAP_Y)
        self._pos_nitro = (self.NITRO_X, self.NITRO_Y)
        # Tâm speedometer = góc dưới-phải chừa margin
        _sw, _sh = self._sz_speedo
        self._speedo_cx = self.W - _sw // 2 - self.SPEEDO_MX
        self._speedo_cy = self.H - _sh // 2 - self.SPEEDO_MY
        # YOU badge: căn giữa trên xe player
        _yw, _yh = self._sz_you
        self._pos_you = (self.car_x - _yw // 2,
                         self.car_y + self.YOU_Y_OFFSET - _yh)

        print("[HUD] ── Blit positions ─────────────────────────────────")
        print(f"  paused.png          xy={self._pos_pause}   sz={self._sz_pause}")
        print(f"  racetime-board.png  xy={self._pos_racetime}  sz={self._sz_racetime}")
        print(f"  pos-board.png       xy={self._pos_pos}   sz={self._sz_pos}")
        print(f"  lap-board.png       xy={self._pos_lap}   sz={self._sz_lap}")
        nw2,nh2=self._sz_nitro
        print(f"  nitro-bar.png       xy={self._pos_nitro}   sz={self._sz_nitro}")
        print(f"  nitro fill area     xl={self.NITRO_X+self.NITRO_FILL_L}  "
              f"xr={self.NITRO_X+nw2-self.NITRO_FILL_R}  "
              f"yt={self.NITRO_Y+self.NITRO_FILL_T}  "
              f"yb={self.NITRO_Y+nh2-self.NITRO_FILL_B}  "
              f"(L={self.NITRO_FILL_L} R={self.NITRO_FILL_R} T={self.NITRO_FILL_T} B={self.NITRO_FILL_B})")
        print(f"  speedometer         cx={self._speedo_cx}  cy={self._speedo_cy}  sz={self._sz_speedo}  W={self.SPEEDO_W}")
        print("[HUD] ─────────────────────────────────────────────────")

    # -----------------------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------------------

    def draw(self, player, elapsed: float, you_alpha: int = 255):
        self._blit_pause()
        self._blit_racetime(elapsed)
        self._blit_pos_lap(player)
        self._blit_nitro(player)
        self._blit_speedometer(player)
        if you_alpha > 0:
            self._blit_you(you_alpha)

    def draw_countdown(self, ct: float, go_elapsed: float = 0.0):
        """
        ct          = countdown_t hiện tại
        go_elapsed  = giây kể từ khi GO! xuất hiện lần đầu
        5-4-3-2-1   → alpha 255 (không fade)
        GO! [0,1s]  → alpha 255
        GO! [1,1.3s]→ fade out 0.3s
        """
        if ct < 0:
            return
        # ct=0 nhưng GO! vẫn fade
        if ct == 0 and (go_elapsed <= 0 or go_elapsed >= 1.3):
            return

        phase = min(int(ct), 5)
        if phase >= 1:
            text  = str(phase)
            color = {5:(255,60,60), 4:(255,140,0), 3:(255,220,0),
                     2:(100,220,100), 1:(60,255,60)}.get(phase,(255,255,255))
            alpha = 255
        else:
            text, color = "GO!", (255, 220, 50)
            if go_elapsed > 1.0:
                fade  = (go_elapsed - 1.0) / 0.3
                alpha = max(0, int(255 * (1.0 - fade)))
            else:
                alpha = 255

        _font = self.font_go if phase == 0 else self.font_cd
        t_s   = _font.render(text, True, color)
        s_s   = _font.render(text, True, (0, 0, 0))
        if alpha < 255:
            t_s.set_alpha(alpha)
            s_s.set_alpha(alpha)
        _, ph = self._sz_pause
        cx = self.W // 2 - t_s.get_width() // 2
        cy = self.PAUSE_Y + ph + 8
        self.screen.blit(s_s, (cx+2, cy+2))
        self.screen.blit(t_s, (cx,   cy))

    def draw_finish_overlay(self, player):
        ov = pygame.Surface((self.W, 300), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, self.H // 2 - 110))
        title = "RACE COMPLETE!"
        _draw_shadow(self.screen, title, self.font_xl, (255,220,50),
                     self.W//2 - self.font_xl.size(title)[0]//2, self.H//2-100)
        for i, lt in enumerate(player.lap_times):
            row = f"Lap {i+1}:  {_fmt_time(lt)}"
            col = (255,220,50) if lt == min(player.lap_times) else (220,220,220)
            _draw_shadow(self.screen, row, self.font_md, col,
                         self.W//2-140, self.H//2-20+i*40)
        footer = (f"Total: {_fmt_time(sum(player.lap_times))}"
                  f"   Pos: {player.pos}/{self.total_racers}   ESC to exit")
        _draw_shadow(self.screen, footer, self.font_md, (160,200,255),
                     self.W//2 - self.font_md.size(footer)[0]//2, self.H//2+110)

    # -----------------------------------------------------------------
    # PRIVATE
    # -----------------------------------------------------------------

    def _build_nitro_gradient(self, base_clr: tuple) -> pygame.Surface:
        """
        Pre-render gradient surface — HORIZONTAL (trái → phải).
        Angle 90 PowerPoint = ngang. Fill level vẫn đi LÊN theo chiều dọc.

        3 đoạn tuyến tính dùng NITRO_GRAD_P* (chỉnh ở đầu class):
          x=0%  → P0   (base, trái)
          x=37% → P37  (peak sáng)
          x=74% → P74  (tối, phải) — giữ nguyên đến 100%
        """
        nw, nh = self._sz_nitro
        fill_w = max(1, nw - self.NITRO_FILL_L - self.NITRO_FILL_R)
        fill_h = max(1, nh - self.NITRO_FILL_T - self.NITRO_FILL_B)

        surf  = pygame.Surface((fill_w, fill_h))
        STRIP = 2

        p0  = self.NITRO_GRAD_P0
        p37 = self.NITRO_GRAD_P37
        p74 = self.NITRO_GRAD_P74

        for x in range(0, fill_w, STRIP):
            w = x / fill_w   # 0.0=trái, 1.0=phải
            if w <= 0.37:
                factor = p0  + (w / 0.37) * (p37 - p0)
            elif w <= 0.74:
                factor = p37 + ((w - 0.37) / 0.37) * (p74 - p37)
            else:
                factor = p74
            color = _apply_brightness(base_clr, factor)
            pygame.draw.rect(surf, color, (x, 0, STRIP, fill_h))

        return surf


    def _blit_pause(self):
        if self._img_pause:
            self.screen.blit(self._img_pause, self._pos_pause)

    def _blit_racetime(self, elapsed: float = 0.0):
        px, py = self._pos_racetime
        pw, ph = self._sz_racetime
        if self._img_racetime:
            self.screen.blit(self._img_racetime, (px, py))
        val = _fmt_time(elapsed)
        t_s = self.font_val.render(val, True, self.VAL_COLOR)
        s_s = self.font_val.render(val, True, (0, 0, 0))
        tx  = px + self.TEXT_PAD_L
        ty  = py + int(ph * self.TEXT_VAL_Y_RATIO) - t_s.get_height() // 2
        self.screen.blit(s_s, (tx+1, ty+1))
        self.screen.blit(t_s, (tx,   ty))

    def _blit_pos_lap(self, player=None):
        # POS
        px, py = self._pos_pos
        pw, ph = self._sz_pos
        if self._img_pos:
            self.screen.blit(self._img_pos, (px, py))
        if player is not None:
            pos_str = f"{player.pos}/{self.total_racers}"
            t_s = self.font_val.render(pos_str, True, self.VAL_COLOR)
            s_s = self.font_val.render(pos_str, True, (0, 0, 0))
            tx  = px + self.TEXT_PAD_L
            ty  = py + int(ph * self.TEXT_VAL_Y_RATIO) - t_s.get_height() // 2
            self.screen.blit(s_s, (tx+1, ty+1))
            self.screen.blit(t_s, (tx,   ty))

        # LAP
        lx, ly = self._pos_lap
        lw, lh = self._sz_lap
        if self._img_lap:
            self.screen.blit(self._img_lap, (lx, ly))
        if player is not None:
            if not player.race_started:
                cur = 1
            else:
                cur = min(player.lap_count + 1, self.max_laps)
                if player.finished: cur = self.max_laps
            lap_str = f"{cur}/{self.max_laps}"
            t_s = self.font_val.render(lap_str, True, self.VAL_COLOR)
            s_s = self.font_val.render(lap_str, True, (0, 0, 0))
            tx  = lx + self.TEXT_PAD_L
            ty  = ly + int(lh * self.TEXT_VAL_Y_RATIO) - t_s.get_height() // 2
            self.screen.blit(s_s, (tx+1, ty+1))
            self.screen.blit(t_s, (tx,   ty))

    def _blit_nitro(self, player=None):
        """
        Thứ tự layer (theo yêu cầu):
          Layer SAU  : gradient fill (màu xanh #97DCFC)
          Layer TRƯỚC: frame ảnh nitro-bar (khung kim loại)

        Frame PNG có vùng transparent ở ống kính
        → fill phía sau show xuyên qua phần trong suốt
        → border kim loại của frame tự che phần tràn ra ngoài
        """
        if player is None:
            return

        nw, nh = self._sz_nitro
        nx, ny = self._pos_nitro

        fill_xl = nx + self.NITRO_FILL_L                  # x + offset trái
        fill_xr = nx + nw - self.NITRO_FILL_R             # x + W - offset phải
        fill_yt = ny + self.NITRO_FILL_T                  # y + offset trên
        fill_yb = ny + nh - self.NITRO_FILL_B             # y + H - offset dưới
        fill_w  = max(1, fill_xr - fill_xl)
        fill_h  = max(1, fill_yb - fill_yt)

        level   = max(0.0, min(1.0, player.nitro_amount / 100.0))
        fill_px = int(fill_h * level)

        # ── Layer SAU: vẽ fill trước ────────────────────────────────
        if fill_px > 0:
            # v2: KHÔNG còn nitro_cd_timer/cooldown (hết nitro nạp lại
            # ngay) — màu CD riêng không còn ý nghĩa, luôn vẽ theo active.
            grad  = self._nitro_grad_active if player.nitro_active else self._nitro_grad
            src_y = fill_h - fill_px
            self.screen.blit(grad,
                             (fill_xl, fill_yb - fill_px),
                             (0, src_y, fill_w, fill_px))

        # ── Layer TRƯỚC: frame ảnh đè lên fill ──────────────────────
        if self._img_nitro:
            self.screen.blit(self._img_nitro, (nx, ny))


    def _blit_speedometer(self, player=None):
        """
        Speedometer góc dưới-phải.
          Layer 1: 2dss-speedometer.png  (mặt số nền)
          Layer 2: KPH số (seven-segment font) — luôn hiện từ đầu với "000"
          Layer 3: 2dss-needlemark.png   (kim xoay theo tốc độ)

        Angles (pygame CCW+):
          NEEDLE_ANGLE_ZERO = 220  →  0 KPH   (PowerPoint 320°)
          NEEDLE_ANGLE_MAX  = -40  →  max KPH (PowerPoint 220°)
          Sweep: 220 → -40 = -260° (CW ✓)
        """
        cx, cy  = self._speedo_cx, self._speedo_cy
        sw, sh  = self._sz_speedo

        # ── Layer 1: mặt số nền ──────────────────────────────────
        if self._img_speedo:
            self.screen.blit(self._img_speedo, (cx - sw//2, cy - sh//2))

        # ── Layer 2: số KPH (seven-segment, luôn hiện) ───────────
        speed = max(0.0, min(abs(player.velocity) if player else 0.0,
                             self.SPEEDO_MAX_KPH))
        kph_str = f"{int(speed):03d}"   # "000" → "300"
        ks = self.font_kph.render(kph_str, True, self.SPEEDO_KPH_COLOR)
        ss = self.font_kph.render(kph_str, True, (0, 0, 0))
        kx = cx - ks.get_width() // 2
        ky = cy + self.SPEEDO_KPH_OFFSET_Y - ks.get_height() // 2
        self.screen.blit(ss, (kx + 1, ky + 1))
        self.screen.blit(ks, (kx,     ky))

        # ── Layer 3: kim xoay ────────────────────────────────────
        if self._img_needle and player is not None:
            t       = speed / self.SPEEDO_MAX_KPH
            angle   = self.NEEDLE_ANGLE_ZERO + t * (self.NEEDLE_ANGLE_MAX - self.NEEDLE_ANGLE_ZERO)
            rotated = pygame.transform.rotate(self._img_needle, angle)
            rw, rh  = rotated.get_size()
            # NEEDLE_OFFSET_X/Y: dịch tâm kim để căn với hub tròn
            self.screen.blit(rotated,
                             (cx - rw // 2 + self.NEEDLE_OFFSET_X,
                              cy - rh // 2 + self.NEEDLE_OFFSET_Y))


    def _blit_you(self, alpha: int = 255):
        """YOU badge trên xe player — fade out khi cuộc đua bắt đầu."""
        if not self._img_you:
            return
        if alpha >= 255:
            self.screen.blit(self._img_you, self._pos_you)
        else:
            img_copy = self._img_you.copy()
            img_copy.set_alpha(alpha)
            self.screen.blit(img_copy, self._pos_you)


# ── Expose helpers ────────────────────────────────────────────────────
fmt_time    = _fmt_time
draw_shadow = _draw_shadow
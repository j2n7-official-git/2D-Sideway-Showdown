"""
=====================================================================
TWODSS_MAPSELECT.PY  —  Màn hình chọn map đua của 2D Sideway Showdown
=====================================================================

MỤC TIÊU:
    Quản lý toàn bộ UI màn hình chọn map, xuất hiện sau khi người chơi
    nhấn LET'S RACE ở showroom. Người chơi xem thumbnail từng map,
    lướt qua danh sách, rồi xác nhận đua hoặc quay về garage.

TƯ DUY THIẾT KẾ:
    - Cùng pattern với twodss_showroom.py: class độc lập, core_main
      chỉ cần gọi handle_event / update / draw mỗi frame.
    - Data map được import từ twodss_map_data.py — module này chỉ
      lo phần UI, không chứa data cứng, đúng nguyên tắc separation
      of concerns.
    - Map index 0 là map đầu tiên, KHÔNG có card inactive ở bên trái
      khi đang ở vị trí đầu — tránh hiển thị map cuối list lộ ra.
    - Cơ chế KHÔNG wrap-around: lướt đến đầu/cuối thì dừng lại.

Ý ĐỊNH & SÁNG KIẾN:
    - Slide animation dùng cubic ease-in-out, tách 2 nhánh dir rõ ràng,
      offset luôn dương tránh bug nhân âm.
    - Hiệu ứng scale + dim khi chuyển card: card mới active phóng to từ
      CARD_INACTIVE_SCALE lên 1.0, đồng thời sáng dần; card vừa rời
      active thu nhỏ xuống CARD_INACTIVE_SCALE và tối đi 20%.
      Tất cả được nội suy theo slide_t qua ease_in_out.
    - Background riêng: map_choosing_2dss_bg.png thay vì dùng chung
      nền showroom, tạo cảm giác màn hình mới hoàn toàn.
    - Dot + nav bar hạ xuống Y=850 để không che card thumbnail.

LUỒNG SỬ DỤNG (từ twodss_core_main.py):
    mapselect = MapSelectScreen(base_dir, fonts)
    mapselect.handle_event(event)
    mapselect.update(dt)
    mapselect.draw(screen)

handle_event trả về:
    "race"   → xác nhận đua, core_main đọc selected_map_id
    "garage" → quay lại showroom
    None     → không đổi state
=====================================================================
"""

import pygame
import os
from twodss_map_data import MAP_LIST, get_map_count

SCREEN_W, SCREEN_H = 1920, 1080
MAP_TOTAL = get_map_count()

# =====================================================================
# LAYOUT CONSTANTS
# =====================================================================

# ── Card active (giữa) ───────────────────────────────────────────────
CARD_ACTIVE_W = 566     # 472 × 1.2
CARD_ACTIVE_H = 480     # 400 × 1.2
CARD_ACTIVE_X = (SCREEN_W - CARD_ACTIVE_W) // 2
CARD_ACTIVE_Y = 300      # dịch lên chút vì card cao hơn



# ── Card inactive (trái / phải) ──────────────────────────────────────
# Tỉ lệ gốc thiết kế: 9.79/12.51 ≈ 0.783
CARD_INACTIVE_SCALE = 0.783
CARD_INACTIVE_W     = int(CARD_ACTIVE_W * CARD_INACTIVE_SCALE)   # ~370px
CARD_INACTIVE_H     = int(CARD_ACTIVE_H * CARD_INACTIVE_SCALE)   # ~360px

# Canh dọc: tâm card inactive = tâm card active
CARD_INACTIVE_Y = CARD_ACTIVE_Y + (CARD_ACTIVE_H - CARD_INACTIVE_H) // 2

# Che 60%: phần hiện ra = 40%
CARD_PEEK_RATIO = 0.40      # <== đổi 0.60 → 0.40
CARD_PEEK_W     = int(CARD_INACTIVE_W * CARD_PEEK_RATIO)

# X cố định của card trái / phải (khi idle)
CARD_LEFT_X  = -CARD_INACTIVE_W + CARD_PEEK_W - 250   # đẩy ra trái thêm 120px
CARD_RIGHT_X = SCREEN_W - CARD_PEEK_W + 250            # đẩy ra phải thêm 120px

# ── Thumbnail bên trong card ─────────────────────────────────────────
THUMB_PADDING    = 18
THUMB_ACTIVE_W   = CARD_ACTIVE_W - THUMB_PADDING * 2
THUMB_ACTIVE_H   = CARD_ACTIVE_H - THUMB_PADDING * 2 - 60   # chừa chỗ tên
THUMB_INACTIVE_W = int(THUMB_ACTIVE_W * CARD_INACTIVE_SCALE)
THUMB_INACTIVE_H = int(THUMB_ACTIVE_H * CARD_INACTIVE_SCALE)

# ── Màu sắc card ─────────────────────────────────────────────────────
COLOR_CARD_ACTIVE   = (75,  165, 215)
COLOR_CARD_INACTIVE = (45,  100, 145)
COLOR_CARD_BORDER   = (140, 210, 255)
COLOR_THUMB_BG      = (90,  120, 180)
CARD_RADIUS         = 24
DIM_INACTIVE        = 0.80   # inactive = 80% độ sáng (tối hơn 20%)

# ── Title ────────────────────────────────────────────────────────────
TITLE_Y = 22    # px từ top  <== CHỈNH

# ── Nav bar (dot + mũi tên) — hạ xuống Y~850 ─────────────────────────
DOT_SIZE    = 38
DOT_GAP     = 16
DOT_Y       = 955   # <== CHỈNH: toàn bộ hàng dot + mũi tên nằm ở Y này
DOT_ROW_W   = MAP_TOTAL * DOT_SIZE + (MAP_TOTAL - 1) * DOT_GAP
DOT_START_X = (SCREEN_W - DOT_ROW_W) // 2

# Nút mũi tên — nhỏ hơn dot 30% so với bản trước
NAV_BTN_SIZE = 49                               # 70 × 0.7 ≈ 49  <== CHỈNH
NAV_Y        = DOT_Y + (DOT_SIZE - NAV_BTN_SIZE) // 2   # canh giữa với dot
NAV_PREV_X   = DOT_START_X - NAV_BTN_SIZE - 28
NAV_NEXT_X   = DOT_START_X + DOT_ROW_W + 28

# ── Nút BACK TO GARAGE + LET'S RACE ─────────────────────────────────
BTN_W      = 220
BTN_H      = 75
BTN_Y      = SCREEN_H - BTN_H - 15
BACK_BTN_X = 15
RACE_BTN_X = SCREEN_W - BTN_W - 15

# ── Slide animation ──────────────────────────────────────────────────
SLIDE_DURATION = 0.50   # giây  <== CHỈNH


# =====================================================================
# HÀM TIỆN ÍCH
# =====================================================================

def ease_in_out(t):
    """Cubic ease-in-out: f(t) = t²(3−2t). Mượt 2 đầu, nhanh giữa."""
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    """Nội suy tuyến tính từ a đến b theo t ∈ [0,1]."""
    return a + (b - a) * t


def get_asset(base_dir, *paths):
    """Đường dẫn tuyệt đối đến file trong assets/."""
    return os.path.join(base_dir, "assets", *paths)


def _apply_dim(surface, factor):
    """
    Tối màu surface xuống factor (0.0=đen, 1.0=nguyên bản).
    Dùng pygame.Surface.fill với BLEND_RGB_MULT.
    """
    dim_surf = surface.copy()
    v = int(255 * factor)
    dim_surf.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    return dim_surf


# =====================================================================
# CLASS CHÍNH
# =====================================================================

class MapSelectScreen:
    """
    Màn hình chọn map đua. Khởi tạo 1 lần, dùng lại mỗi khi quay lại.

    Tham số __init__:
        base_dir : thư mục gốc dự án (chứa assets/)
        fonts    : dict {"large": font80, "medium": font45, "small": font25}
    """

    def __init__(self, base_dir, fonts: dict, bg_image=None):
        self.base_dir = base_dir
        self.font_lg  = fonts.get("large")
        self.font_md  = fonts.get("medium")
        self.font_sm  = fonts.get("small")

        # Font UI — load đúng size, không scale bitmap
        font_path = get_asset(base_dir, "fonts", "SVN-New Athletic M54.ttf")
        try:
            self.font_btn   = pygame.font.Font(font_path, 26)
            self.font_title = pygame.font.Font(font_path, 72)
            self.font_name  = pygame.font.Font(font_path, 32)
            self.font_soon  = pygame.font.Font(font_path, 28)
        except Exception as e:
            print(f"[MAPSELECT FONT] Fallback SysFont: {e}")
            self.font_btn   = pygame.font.SysFont("impact", 26)
            self.font_title = pygame.font.SysFont("impact", 72)
            self.font_name  = pygame.font.SysFont("impact", 32)
            self.font_soon  = pygame.font.SysFont("impact", 28)

        # Background riêng cho màn hình chọn map
        self.bg = None
        try:
            raw     = pygame.image.load(
                get_asset(base_dir, "background_game", "map_choosing_2dss_bg.png")
            ).convert()
            self.bg = pygame.transform.smoothscale(raw, (SCREEN_W, SCREEN_H))
            print("[MAPSELECT BG] Loaded: map_choosing_2dss_bg.png")
        except Exception as e:
            print(f"[MAPSELECT BG] Không load được: {e} — dùng màu fallback")

        # ── Trạng thái slide ─────────────────────────────────────────
        # selected  : index map đang active
        # slide_t   : tiến trình [0.0 → 1.0]; 1.0 = idle
        # slide_dir : +1 = next, -1 = prev
        # slide_from: index map cũ, dùng để vẽ transition
        self.selected   = 0
        self.slide_t    = 1.0
        self.slide_dir  = 0
        self.slide_from = 0

        # ── Rect nút ─────────────────────────────────────────────────
        self.rect_back = pygame.Rect(BACK_BTN_X, BTN_Y, BTN_W, BTN_H)
        self.rect_race = pygame.Rect(RACE_BTN_X, BTN_Y, BTN_W, BTN_H)
        self.rect_prev = pygame.Rect(NAV_PREV_X, NAV_Y, NAV_BTN_SIZE, NAV_BTN_SIZE)
        self.rect_next = pygame.Rect(NAV_NEXT_X, NAV_Y, NAV_BTN_SIZE, NAV_BTN_SIZE)

        self._load_assets()

    # ------------------------------------------------------------------
    def _load_assets(self):
        """
        Load thumbnail tất cả map + icon mũi tên + dot.
        try/except từng asset — game không crash khi thiếu file.
        """
        def ga(*p):
            return get_asset(self.base_dir, *p)

        # Thumbnail — load 1 lần khi khởi tạo, không load lại mỗi frame
        self.thumbs = []
        for m in MAP_LIST:
            img = self._load_thumb(ga("map_thumbnails", m["file"] + ".png"))
            self.thumbs.append(img)

        # Nút mũi tên
        try:
            raw = pygame.image.load(ga("ui-interactive", "next-button.png")).convert_alpha()
            self.img_next = pygame.transform.smoothscale(raw, (NAV_BTN_SIZE, NAV_BTN_SIZE))
        except:
            self.img_next = None

        try:
            raw = pygame.image.load(ga("ui-interactive", "previous-button.png")).convert_alpha()
            self.img_prev = pygame.transform.smoothscale(raw, (NAV_BTN_SIZE, NAV_BTN_SIZE))
        except:
            self.img_prev = None

        # Dot indicator
        try:
            raw = pygame.image.load(ga("ui-interactive", "active-select-dot.png")).convert_alpha()
            self.img_dot_on = pygame.transform.smoothscale(raw, (DOT_SIZE, DOT_SIZE))
        except:
            self.img_dot_on = None

        try:
            raw = pygame.image.load(ga("ui-interactive", "inactive-select-dot.png")).convert_alpha()
            self.img_dot_off = pygame.transform.smoothscale(raw, (DOT_SIZE, DOT_SIZE))
        except:
            self.img_dot_off = None

    # ------------------------------------------------------------------
    def _load_thumb(self, path):
        """Load + scale thumbnail giữ aspect ratio. None nếu thiếu file."""
        try:
            raw    = pygame.image.load(path).convert_alpha()
            rw, rh = raw.get_size()
            scale  = min(THUMB_ACTIVE_W / rw, THUMB_ACTIVE_H / rh)
            return pygame.transform.smoothscale(raw, (int(rw * scale), int(rh * scale)))
        except:
            return None

    # ------------------------------------------------------------------
    def handle_event(self, event):
        """
        Xử lý input. Trả về "race" / "garage" / None.
        Không wrap-around: không cho lướt khi đã ở đầu/cuối.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = event.pos

            if self.rect_next.collidepoint(mp) and self.slide_t >= 1.0:
                if self.selected < MAP_TOTAL - 1:
                    self._start_slide(+1)
            elif self.rect_prev.collidepoint(mp) and self.slide_t >= 1.0:
                if self.selected > 0:
                    self._start_slide(-1)
            elif self.rect_race.collidepoint(mp):
                if not MAP_LIST[self.selected]["coming_soon"]:
                    return "race"
            elif self.rect_back.collidepoint(mp):
                return "garage"
            else:
                for i in range(MAP_TOTAL):
                    dx       = DOT_START_X + i * (DOT_SIZE + DOT_GAP)
                    dot_rect = pygame.Rect(dx, DOT_Y, DOT_SIZE, DOT_SIZE)
                    if dot_rect.collidepoint(mp) and i != self.selected and self.slide_t >= 1.0:
                        diff            = i - self.selected
                        self.slide_from = self.selected
                        self.selected   = i
                        self.slide_t    = 0.0
                        self.slide_dir  = 1 if diff > 0 else -1

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT and self.slide_t >= 1.0:
                if self.selected < MAP_TOTAL - 1:
                    self._start_slide(+1)
            elif event.key == pygame.K_LEFT and self.slide_t >= 1.0:
                if self.selected > 0:
                    self._start_slide(-1)
            elif event.key == pygame.K_RETURN:
                if not MAP_LIST[self.selected]["coming_soon"]:
                    return "race"
            elif event.key == pygame.K_BACKSPACE:
                return "garage"

        return None

    # ------------------------------------------------------------------
    def _start_slide(self, direction):
        """Khởi động slide. direction: +1=next, -1=prev."""
        self.slide_from = self.selected
        self.selected   = self.selected + direction   # không % MAP_TOTAL vì no wrap
        self.slide_dir  = direction
        self.slide_t    = 0.0

    # ------------------------------------------------------------------
    def update(self, dt_ms):
        """Tăng slide_t theo thời gian thực, độc lập FPS."""
        if self.slide_t < 1.0:
            self.slide_t = min(self.slide_t + dt_ms / (SLIDE_DURATION * 1000), 1.0)

    # ------------------------------------------------------------------
    def draw(self, screen):
        """Vẽ toàn bộ màn hình: nền → title → cards → nav → buttons."""
        if self.bg:
            screen.blit(self.bg, (0, 0))
        else:
            screen.fill((10, 28, 65))

        self._draw_title(screen)
        self._draw_cards(screen)
        self._draw_nav_buttons(screen)
        self._draw_dots(screen)
        self._draw_blue_button(screen, self.rect_back, "BACK TO GARAGE", self.font_btn)
        self._draw_race_button(screen)

    # ------------------------------------------------------------------
    def _draw_title(self, screen):
        """Tiêu đề căn giữa với shadow + outline 4 hướng."""
        text = "CHOOSE A MAP TO RACE"
        sx   = (SCREEN_W - self.font_title.size(text)[0]) // 2
        sh   = self.font_title.render(text, True, (0, 0, 0))
        sh.set_alpha(160)
        screen.blit(sh, (sx + 3, TITLE_Y + 4))
        out = self.font_title.render(text, True, (0, 30, 80))
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            screen.blit(out, (sx + dx, TITLE_Y + dy))
        screen.blit(self.font_title.render(text, True, (255, 255, 255)), (sx, TITLE_Y))

    # ------------------------------------------------------------------
    def _build_card_surf(self, map_idx, card_w, card_h, thumb_w, thumb_h,
                         is_active, dim_factor=1.0):
        """
        Tạo Surface card hoàn chỉnh.

        dim_factor: 0.0=đen → 1.0=nguyên bản
                    Dùng để animate dim/brighten khi chuyển active.
        """
        surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)

        # Nền + viền
        base_color   = COLOR_CARD_ACTIVE if is_active else COLOR_CARD_INACTIVE
        border_alpha = 255 if is_active else 140
        pygame.draw.rect(surf, base_color, surf.get_rect(), border_radius=CARD_RADIUS)
        pygame.draw.rect(surf, COLOR_CARD_BORDER + (border_alpha,),
                         surf.get_rect(), width=3, border_radius=CARD_RADIUS)

        # Thumbnail
        thumb_x  = (card_w - thumb_w) // 2
        thumb_y  = THUMB_PADDING
        map_data = MAP_LIST[map_idx]

        # Thumbnail — load ảnh bất kể coming_soon, chỉ hiện "?" overlay nếu chưa có file
        raw_thumb = self.thumbs[map_idx]
        if raw_thumb:
            rw, rh = raw_thumb.get_size()
            scale = min(thumb_w / rw, thumb_h / rh)
            scaled = pygame.transform.smoothscale(
                raw_thumb, (int(rw * scale), int(rh * scale))
            )
            tb = pygame.Surface((thumb_w, thumb_h), pygame.SRCALPHA)
            pygame.draw.rect(tb, COLOR_THUMB_BG + (200,), tb.get_rect(), border_radius=10)
            surf.blit(tb, (thumb_x, thumb_y))
            surf.blit(scaled, (
                thumb_x + (thumb_w - scaled.get_width()) // 2,
                thumb_y + (thumb_h - scaled.get_height()) // 2,
            ))
            pygame.draw.rect(surf, (100, 160, 220, 160),
                             pygame.Rect(thumb_x, thumb_y, thumb_w, thumb_h),
                             width=2, border_radius=10)
        else:
            pc = map_data.get("preview_color", (90, 120, 180))
            ts = pygame.Surface((thumb_w, thumb_h), pygame.SRCALPHA)
            pygame.draw.rect(ts, pc + (200,), ts.get_rect(), border_radius=10)
            if map_data["coming_soon"]:
                q = self.font_title.render("?", True, (180, 200, 230))
                ts.blit(q, q.get_rect(center=(thumb_w // 2, thumb_h // 2)))
            surf.blit(ts, (thumb_x, thumb_y))

        # Tên map
        name     = map_data["name"]
        font     = self.font_name if is_active else self.font_soon
        name_col = (255, 255, 255) if is_active else (180, 210, 240)
        name_y   = thumb_y + thumb_h + 10
        out = font.render(name, True, (0, 0, 0))
        nx  = (card_w - out.get_width()) // 2
        for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            surf.blit(out, (nx + ddx, name_y + ddy))
        surf.blit(font.render(name, True, name_col), (nx, name_y))

        # Áp dim nếu cần (inactive hoặc đang transition)
        if dim_factor < 1.0:
            surf = _apply_dim(surf, dim_factor)

        return surf

    # ------------------------------------------------------------------
    def _draw_cards(self, screen):
        t = ease_in_out(self.slide_t)
        # SLOT_W = khoảng cách tâm card active đến tâm card bên cạnh
        # = chiều rộng card inactive hiện ra (peek) + phần active còn lại mỗi bên
        SLOT_W = CARD_ACTIVE_W // 2 + int(CARD_INACTIVE_W * CARD_PEEK_RATIO) + 480

        if self.slide_t >= 1.0:
            current_offset = self.selected * SLOT_W
        else:
            current_offset = lerp(self.slide_from * SLOT_W, self.selected * SLOT_W, t)

        screen_cx = SCREEN_W // 2

        indices_to_draw = set()
        for center in (self.selected, self.slide_from if self.slide_t < 1.0 else self.selected):
            for delta in (-1, 0, 1):
                idx = center + delta
                if 0 <= idx < MAP_TOTAL:
                    indices_to_draw.add(idx)

        # Vẽ inactive trước, active sau (đè lên trên)
        draw_order = sorted(indices_to_draw, key=lambda i: 1 if i == self.selected else 0)

        for i in draw_order:
            card_cx = screen_cx + (i * SLOT_W) - current_offset

            if card_cx < -CARD_ACTIVE_W or card_cx > SCREEN_W + CARD_ACTIVE_W:
                continue

            if self.slide_t >= 1.0:
                active_level = 1.0 if i == self.selected else 0.0
            else:
                if i == self.selected:
                    active_level = t
                elif i == self.slide_from:
                    active_level = 1.0 - t
                else:
                    active_level = 0.0

            sc = lerp(CARD_INACTIVE_SCALE, 1.0, active_level)
            dm = lerp(DIM_INACTIVE,        1.0, active_level)

            cw = int(CARD_ACTIVE_W * sc)
            ch = int(CARD_ACTIVE_H * sc)
            tw = int(THUMB_ACTIVE_W * sc)
            th = int(THUMB_ACTIVE_H * sc)

            blit_x = card_cx - cw // 2
            blit_y = CARD_ACTIVE_Y + (CARD_ACTIVE_H - ch) // 2

            is_active = (active_level > 0.5)
            card = self._build_card_surf(i, cw, ch, tw, th,
                                         is_active=is_active, dim_factor=dm)

            clip = pygame.Rect(0, CARD_ACTIVE_Y - 10, SCREEN_W, CARD_ACTIVE_H + 20)
            screen.set_clip(clip)
            screen.blit(card, (blit_x, blit_y))
            screen.set_clip(None)
    # ------------------------------------------------------------------
    def _draw_nav_buttons(self, screen):
        """
        Vẽ mũi tên trái/phải.
        Ẩn mũi tên trái khi ở map đầu (selected=0),
        ẩn mũi tên phải khi ở map cuối (selected=MAP_TOTAL-1).
        """
        mp = pygame.mouse.get_pos()

        # ── Mũi tên trái ──────────────────────────────────────────────
        if self.selected > 0:
            if self.img_prev:
                if self.rect_prev.collidepoint(mp):
                    img = pygame.transform.smoothscale(
                        self.img_prev,
                        (int(NAV_BTN_SIZE * 1.15), int(NAV_BTN_SIZE * 1.15))
                    )
                    screen.blit(img, img.get_rect(center=self.rect_prev.center))
                else:
                    screen.blit(self.img_prev, self.rect_prev)
            else:
                color = (200, 230, 255) if self.rect_prev.collidepoint(mp) else (120, 160, 210)
                pygame.draw.polygon(screen, color, [
                    (NAV_PREV_X + NAV_BTN_SIZE, NAV_Y),
                    (NAV_PREV_X,                NAV_Y + NAV_BTN_SIZE // 2),
                    (NAV_PREV_X + NAV_BTN_SIZE, NAV_Y + NAV_BTN_SIZE),
                ])

        # ── Mũi tên phải ──────────────────────────────────────────────
        if self.selected < MAP_TOTAL - 1:
            if self.img_next:
                if self.rect_next.collidepoint(mp):
                    img = pygame.transform.smoothscale(
                        self.img_next,
                        (int(NAV_BTN_SIZE * 1.15), int(NAV_BTN_SIZE * 1.15))
                    )
                    screen.blit(img, img.get_rect(center=self.rect_next.center))
                else:
                    screen.blit(self.img_next, self.rect_next)
            else:
                color = (200, 230, 255) if self.rect_next.collidepoint(mp) else (120, 160, 210)
                pygame.draw.polygon(screen, color, [
                    (NAV_NEXT_X,                NAV_Y),
                    (NAV_NEXT_X + NAV_BTN_SIZE, NAV_Y + NAV_BTN_SIZE // 2),
                    (NAV_NEXT_X,                NAV_Y + NAV_BTN_SIZE),
                ])

    # ------------------------------------------------------------------
    def _draw_dots(self, screen):
        """8 dot indicator. Dot active khác màu/ảnh."""
        for i in range(MAP_TOTAL):
            dx        = DOT_START_X + i * (DOT_SIZE + DOT_GAP)
            is_active = (i == self.selected)
            if is_active and self.img_dot_on:
                screen.blit(self.img_dot_on, (dx, DOT_Y))
            elif not is_active and self.img_dot_off:
                screen.blit(self.img_dot_off, (dx, DOT_Y))
            else:
                color = (173, 216, 230) if is_active else (20, 50, 110)
                cx    = dx + DOT_SIZE // 2
                cy    = DOT_Y + DOT_SIZE // 2
                pygame.draw.circle(screen, color,           (cx, cy), DOT_SIZE // 2)
                pygame.draw.circle(screen, (100, 160, 220), (cx, cy), DOT_SIZE // 2, 2)

    # ------------------------------------------------------------------
    def _draw_blue_button(self, screen, rect, text, font):
        """Nút gradient xanh (BACK TO GARAGE). Hover sáng hơn 10%."""
        mp    = pygame.mouse.get_pos()
        hover = rect.collidepoint(mp)
        surf  = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for y in range(rect.height):
            ratio = y / rect.height
            b = int(200 - ratio * 10)
            g = int(100 - ratio * 5)
            if hover:
                b = min(255, int(b * 1.1))
                g = min(255, int(g * 1.1))
            pygame.draw.line(surf, (0, g, b), (0, y), (rect.width, y))
        pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), width=3, border_radius=10)
        if font:
            sh = font.render(text, True, (0, 0, 0))
            lb = font.render(text, True, (255, 255, 255))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                surf.blit(sh, sh.get_rect(center=(rect.width//2+dx, rect.height//2+dy)))
            surf.blit(lb, lb.get_rect(center=(rect.width//2, rect.height//2)))
        screen.blit(surf, rect.topleft)

    # ------------------------------------------------------------------
    def _draw_race_button(self, screen):
        """LET'S RACE = xanh lá khi playable, xám khi coming soon."""
        is_cs = MAP_LIST[self.selected]["coming_soon"]
        mp    = pygame.mouse.get_pos()
        hover = self.rect_race.collidepoint(mp) and not is_cs
        surf  = pygame.Surface((BTN_W, BTN_H), pygame.SRCALPHA)
        for y in range(BTN_H):
            ratio = y / BTN_H
            if is_cs:
                v     = int(80 - ratio * 10)
                color = (v, v, v)
            else:
                g     = int(180 - ratio * 20)
                b     = int(60  - ratio * 10)
                color = (0, g, b)
                if hover:
                    color = tuple(min(255, int(c * 1.15)) for c in color)
            pygame.draw.line(surf, color, (0, y), (BTN_W, y))
        pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), width=3, border_radius=10)
        label_text = "LET'S RACE" if not is_cs else "COMING SOON"
        label_col  = (255, 255, 255) if not is_cs else (160, 160, 160)
        if self.font_btn:
            sh = self.font_btn.render(label_text, True, (0, 0, 0))
            lb = self.font_btn.render(label_text, True, label_col)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                surf.blit(sh, sh.get_rect(center=(BTN_W//2+dx, BTN_H//2+dy)))
            surf.blit(lb, lb.get_rect(center=(BTN_W//2, BTN_H//2)))
        screen.blit(surf, self.rect_race.topleft)

    # ------------------------------------------------------------------
    @property
    def selected_map_id(self):
        """ID map đang chọn — core_main truyền vào engine."""
        return MAP_LIST[self.selected]["id"]

    @property
    def selected_map_name(self):
        """Tên hiển thị map đang chọn."""
        return MAP_LIST[self.selected]["name"]
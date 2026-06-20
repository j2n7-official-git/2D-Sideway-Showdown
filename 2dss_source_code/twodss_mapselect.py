"""
=====================================================================
TWODSS_MAPSELECT.PY  —  MÀN HÌNH CHỌN MAP (STATIC LAYOUT — FIXED)
=====================================================================
BẢN SỬA LỖI:
    Bản trước (do Gemini làm) dùng pygame.Rect với số pixel CỨNG
    (vd: TITLE_RECT = pygame.Rect(1100, 200, 650, 80)). Cách này
    chỉ đúng khi panel ảnh nền y hệt 1 kích thước cố định — chỉ cần
    đổi độ phân giải màn hình, build .exe trên máy khác, hoặc panel
    ảnh bị export lại với size khác 1 chút là toạ độ lệch hết, sinh
    ra "lỗi vặt" (ảnh đè lên viền, nút lệch khỏi khung, v.v).

CÁCH SỬA:
    Mọi toạ độ trong file này được đo trực tiếp trên ảnh panel gốc
    (kích thước thật: 5776×3440 px) rồi quy về TỈ LỆ % (0.0 → 1.0)
    so với chiều rộng/cao của chính ảnh panel đó.
    Khi vẽ, ta chỉ cần lấy panel_img.get_size() hiện tại (dù panel
    bị pygame.transform.scale về kích thước màn hình nào) và nhân
    lại với tỉ lệ % này → toạ độ luôn khớp 100% với ảnh, bất kể
    màn hình là 1920x1080, 1600x900, hay full HD khác tỉ lệ khung hình
    gần giống (panel vẫn được scale theo đúng aspect ratio gốc để
    không bị méo — xem hàm _fit_panel()).

NGUỒN ẢNH ĐO ĐẠC (panel gốc 5776x3440 px):
    - Khung trái (chứa 5 nút tròn chọn map)  : x∈[99,2027]   y∈[404,3354]
    - Khung tiêu đề tên map (phải, trên)     : x∈[2127,5685] y∈[356,725]
    - Khung thumbnail (phải, giữa, có viền
      chấm trắng để lắp ảnh map)             : x∈[2127,5685] y∈[755,2918]
    - Khung nút LET'S RACE (phải, dưới)      : x∈[2127,5685] y∈[3018,3320]
    - 5 nút tròn: đường kính 293px, tâm x=1082,
      tâm y = 695, 1258, 1814, 2406, 3027

ASSET SỬ DỤNG (đường dẫn thật do người dùng cung cấp):
    assets/ui-map-selection/2dss-map-selection-panel.png   ← khung nền
    assets/ui-interactive/active-select-dot.png            ← chấm tròn đang chọn
    assets/ui-interactive/inactive-select-dot.png          ← chấm tròn chưa chọn
    assets/map_thumbnails/<file>.png                       ← ảnh map (từ twodss_map_data.py)
=====================================================================
"""

import pygame
import os
from twodss_map_data import MAP_LIST, get_map_count

# Kích thước tham chiếu — chỉ dùng để khởi tạo lần đầu nếu cần,
# layout thật luôn tính lại theo kích thước panel_img hiện tại.
SCREEN_W, SCREEN_H = 1920, 1080
MAP_TOTAL = get_map_count()

# =====================================================================
# TỈ LỆ % ĐO TỪ ẢNH PANEL GỐC (5776 x 3440 px) — KHÔNG SỬA TRỪ KHI
# PANEL ẢNH GỐC THAY ĐỔI LAYOUT. Format: (x, y, w, h) theo fraction.
# =====================================================================
LEFT_PANEL_FRAC  = (0.0171, 0.1174, 0.3338, 0.8576)   # khung chứa 5 dot
TITLE_FRAC       = (0.3682, 0.1035, 0.6160, 0.1073)   # khung tên map
THUMB_FRAC       = (0.3682, 0.2195, 0.6160, 0.6288)   # khung ảnh map (vùng viền chấm trắng)
RACE_BTN_FRAC    = (0.3682, 0.8773, 0.6160, 0.0878)   # khung nút LET'S RACE

# Vị trí 5 chấm tròn — tâm theo % chiều rộng/cao panel
DOT_CX_FRAC      = 0.1873                              # tâm X (chung cho cả cột)
DOT_DIAM_FRAC_W  = 0.0507                               # đường kính theo % width
DOT_DIAM_FRAC_H  = 0.0852                               # đường kính theo % height
DOT_CY_FRACS     = [0.2020, 0.3657, 0.5273, 0.6994, 0.8799]  # tâm Y của tối đa 5 dot

# Nếu map nhiều hơn 5, các dot còn lại được nội suy đều trong khung trái
DOT_TOP_FRAC     = DOT_CY_FRACS[0]
DOT_BOTTOM_FRAC  = DOT_CY_FRACS[-1]


def _lerp_dot_centers(n):
    """Trả về list n tâm-Y (fraction) cho n nút tròn, dùng layout đã đo
    nếu n == 5 (đúng số đo gốc), còn lại thì nội suy đều trong khoảng
    [DOT_TOP_FRAC, DOT_BOTTOM_FRAC] để không bị lỗi khi thêm/bớt map."""
    if n == len(DOT_CY_FRACS):
        return DOT_CY_FRACS
    if n == 1:
        return [(DOT_TOP_FRAC + DOT_BOTTOM_FRAC) / 2]
    span = DOT_BOTTOM_FRAC - DOT_TOP_FRAC
    return [DOT_TOP_FRAC + span * i / (n - 1) for i in range(n)]


class MapSelectScreen:
    """Class quản lý UI chọn map theo cơ chế Static (không slide).
    Toàn bộ toạ độ tự scale theo kích thước panel hiện tại — không còn
    pixel cứng, không còn lỗi lệch UI khi đổi resolution / build .exe.
    """

    def __init__(self, base_dir, fonts, bg_image=None, screen_size=(SCREEN_W, SCREEN_H)):
        self.base_dir = base_dir
        self.fonts = fonts
        self.selected = 0
        self.screen_w, self.screen_h = screen_size

        # ---- Đường dẫn asset (khớp đúng cấu trúc thư mục thật) ----
        panel_path        = os.path.join(base_dir, "assets", "ui-map-selection", "2dss-map-selection-panel.png")
        dot_active_path   = os.path.join(base_dir, "assets", "ui-interactive", "active-select-dot.png")
        dot_inactive_path = os.path.join(base_dir, "assets", "ui-interactive", "inactive-select-dot.png")

        # ---- Load panel nền, giữ nguyên tỉ lệ khung hình gốc rồi
        #      scale để vừa khít màn hình hiện tại (letterbox nếu cần) ----
        self.panel_img_raw = self._safe_load(panel_path)
        self.panel_img, self.panel_rect = self._fit_panel(self.panel_img_raw, self.screen_w, self.screen_h)

        # ---- Load 2 ảnh chấm tròn (active / inactive) ----
        self.dot_active_raw   = self._safe_load(dot_active_path)
        self.dot_inactive_raw = self._safe_load(dot_inactive_path)

        # ---- Load thumbnail từng map theo twodss_map_data.py ----
        self.thumbs = []
        for m in MAP_LIST:
            path = os.path.join(base_dir, "assets", "map_thumbnails", m["file"] + ".png")
            self.thumbs.append(self._safe_load(path))

        # ---- Tính sẵn toạ độ pixel thật từ fraction + panel hiện tại ----
        self._recompute_layout()

    # -----------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------
    def _safe_load(self, path):
        """Load ảnh an toàn — không crash nếu thiếu file, chỉ cảnh báo
        ra console để dev biết đường dẫn nào sai mà không sập cả game."""
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception as e:
            print(f"[MAPSELECT][ASSET WARNING] Không load được: {path}  ({e})")
            return None

    def _fit_panel(self, raw_img, target_w, target_h):
        """Scale panel theo đúng tỉ lệ khung hình gốc (không méo hình),
        canh giữa màn hình (letterbox nếu màn hình không đúng tỉ lệ ảnh).
        Trả về (surface_đã_scale, rect_vị_trí_trên_màn_hình)."""
        if raw_img is None:
            # Fallback: tạo surface màu nền tối để game không sập
            fallback = pygame.Surface((target_w, target_h))
            fallback.fill((30, 40, 55))
            return fallback, fallback.get_rect(topleft=(0, 0))

        raw_w, raw_h = raw_img.get_size()
        scale = min(target_w / raw_w, target_h / raw_h)
        new_w, new_h = int(raw_w * scale), int(raw_h * scale)
        scaled = pygame.transform.smoothscale(raw_img, (new_w, new_h))
        rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
        return scaled, rect

    def _frac_to_rect(self, frac):
        """Chuyển (x,y,w,h) tỉ lệ % của panel -> pygame.Rect tuyệt đối
        trên màn hình, dựa theo panel_rect hiện tại (đã fit/letterbox)."""
        fx, fy, fw, fh = frac
        pw, ph = self.panel_rect.size
        px, py = self.panel_rect.topleft
        return pygame.Rect(
            int(px + fx * pw),
            int(py + fy * ph),
            int(fw * pw),
            int(fh * ph),
        )

    def _recompute_layout(self):
        """Tính lại toàn bộ Rect pixel từ fraction — gọi 1 lần khi init
        và bất cứ khi nào resize/đổi resolution (resize() bên dưới)."""
        self.title_rect    = self._frac_to_rect(TITLE_FRAC)
        self.thumb_rect     = self._frac_to_rect(THUMB_FRAC)
        self.race_btn_rect  = self._frac_to_rect(RACE_BTN_FRAC)
        left_rect           = self._frac_to_rect(LEFT_PANEL_FRAC)

        pw, ph = self.panel_rect.size
        px, py = self.panel_rect.topleft

        dot_cx = int(px + DOT_CX_FRAC * pw)
        dot_w  = max(1, int(DOT_DIAM_FRAC_W * pw))
        dot_h  = max(1, int(DOT_DIAM_FRAC_H * ph))
        dot_radius_px = max(dot_w, dot_h) // 2

        centers_y_frac = _lerp_dot_centers(MAP_TOTAL)
        self.dot_rects = []
        for fy in centers_y_frac:
            cy = int(py + fy * ph)
            rect = pygame.Rect(0, 0, dot_w, dot_h)
            rect.center = (dot_cx, cy)
            self.dot_rects.append(rect)

        # Pre-scale 2 ảnh chấm tròn đúng kích thước tính được (so với panel)
        self._dot_active_scaled   = self._scale_or_none(self.dot_active_raw, dot_w, dot_h)
        self._dot_inactive_scaled = self._scale_or_none(self.dot_inactive_raw, dot_w, dot_h)
        self._dot_radius_px       = dot_radius_px

    def _scale_or_none(self, img, w, h):
        if img is None:
            return None
        return pygame.transform.smoothscale(img, (max(1, w), max(1, h)))

    def resize(self, new_w, new_h):
        """Gọi khi đổi resolution / vào fullscreen khác kích thước —
        tính lại toàn bộ layout để UI không bao giờ bị lệch."""
        self.screen_w, self.screen_h = new_w, new_h
        self.panel_img, self.panel_rect = self._fit_panel(self.panel_img_raw, new_w, new_h)
        self._recompute_layout()

    # -----------------------------------------------------------------
    # PROPERTIES
    # -----------------------------------------------------------------
    @property
    def selected_map_id(self):
        return MAP_LIST[self.selected]["id"]

    @property
    def selected_map_name(self):
        return MAP_LIST[self.selected]["name"]

    # -----------------------------------------------------------------
    # EVENT HANDLING
    # -----------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = pygame.mouse.get_pos()

            # Click nút LET'S RACE
            if self.race_btn_rect.collidepoint(mp):
                if not MAP_LIST[self.selected]["coming_soon"]:
                    return "race"

            # Click vào 1 trong các chấm tròn
            for i, dot_rect in enumerate(self.dot_rects):
                # Dùng hit-test hình tròn cho chuẩn (rect.collidepoint
                # vẫn ổn vì ảnh dot gần như full khung, nhưng test tròn
                # mượt hơn ở mép)
                cx, cy = dot_rect.center
                dx, dy = mp[0] - cx, mp[1] - cy
                if (dx * dx + dy * dy) <= (self._dot_radius_px ** 2) * 1.15:
                    self.selected = i
                    return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                return "garage"
            if event.key == pygame.K_LEFT:
                self.selected = (self.selected - 1) % MAP_TOTAL
            if event.key == pygame.K_RIGHT or event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % MAP_TOTAL
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % MAP_TOTAL
            if event.key == pygame.K_RETURN:
                if not MAP_LIST[self.selected]["coming_soon"]:
                    return "race"

        return None

    def update(self, dt):
        pass  # Layout tĩnh — không cần animation theo frame

    # -----------------------------------------------------------------
    # DRAW
    # -----------------------------------------------------------------
    def draw(self, screen):
        # Nền đen lấp đầy phần letterbox (nếu màn hình không cùng tỉ lệ panel)
        screen.fill((0, 0, 0))

        # 1. Vẽ panel nền (đã scale đúng tỉ lệ, canh giữa)
        screen.blit(self.panel_img, self.panel_rect.topleft)

        # 2. Vẽ tên map vào khung tiêu đề
        name_surf = self.fonts["large"].render(self.selected_map_name, True, (255, 255, 255))
        screen.blit(name_surf, name_surf.get_rect(center=self.title_rect.center))

        # 3. Vẽ thumbnail map vào khung viền chấm trắng
        thumb_img = self.thumbs[self.selected]
        if thumb_img is not None:
            scaled = pygame.transform.smoothscale(
                thumb_img, (self.thumb_rect.width, self.thumb_rect.height)
            )
            screen.blit(scaled, self.thumb_rect.topleft)
        else:
            # Fallback: tô màu preview_color nếu thiếu ảnh, để dev biết
            # ngay map nào chưa có thumbnail mà không vỡ layout
            color = MAP_LIST[self.selected].get("preview_color", (60, 60, 90))
            pygame.draw.rect(screen, color, self.thumb_rect)

        if MAP_LIST[self.selected]["coming_soon"]:
            tag = self.fonts["medium"].render("COMING SOON", True, (255, 210, 60))
            screen.blit(tag, tag.get_rect(center=self.thumb_rect.center))

        # 4. Vẽ nút LET'S RACE — tô đầy khung đã đo, chữ giữa khung
        is_locked = MAP_LIST[self.selected]["coming_soon"]
        btn_color = (60, 60, 60) if is_locked else (44, 82, 145)
        pygame.draw.rect(screen, btn_color, self.race_btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), self.race_btn_rect, width=3)
        label = "LOCKED" if is_locked else "LET'S RACE"
        txt = self.fonts["medium"].render(label, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=self.race_btn_rect.center))

        # 5. Vẽ các chấm tròn điều hướng — dùng đúng 2 ảnh asset
        #    active-select-dot.png / inactive-select-dot.png
        for i, dot_rect in enumerate(self.dot_rects):
            img = self._dot_active_scaled if i == self.selected else self._dot_inactive_scaled
            if img is not None:
                screen.blit(img, img.get_rect(center=dot_rect.center))
            else:
                # Fallback nếu thiếu asset chấm tròn
                color = (255, 255, 255) if i == self.selected else (90, 90, 90)
                pygame.draw.circle(screen, color, dot_rect.center, self._dot_radius_px)
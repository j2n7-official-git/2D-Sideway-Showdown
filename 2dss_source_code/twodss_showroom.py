import pygame
import os
import math
from twodss_car_data import CAR_LIST as _RAW_LIST

# =====================================================================
# SCREEN_SHOWROOM MODULE
# Dùng: from screen_showroom import ShowroomScreen
#
# Module này quản lý toàn bộ màn hình chọn xe (Showroom).
# Được gọi từ twodss_core_main.py theo pattern:
#   showroom = ShowroomScreen(base_dir, fonts, bg_image)
#   showroom.handle_event(event)   ← trong event loop
#   showroom.update(dt)            ← cập nhật animation mỗi frame
#   showroom.draw(screen)          ← vẽ toàn bộ UI
# =====================================================================

SCREEN_W, SCREEN_H = 1920, 1080

# Chuyển đổi car_data từ dict sang tuple (name, file, brand_logo)
# Lý do dùng tuple thay dict: truy cập theo index [0][1][2] nhanh hơn,
# và module này chỉ cần 3 trường, không cần toàn bộ thông tin xe
CAR_LIST = [(c["name"], c["file"], c.get("brand_logo")) for c in _RAW_LIST]

# =====================================================================
# LAYOUT CONSTANTS — Tất cả tọa độ/kích thước UI tập trung ở đây
# Nguyên tắc: KHÔNG hardcode số trong hàm vẽ, luôn dùng constant
# để dễ chỉnh sửa layout mà không cần tìm từng dòng code
# =====================================================================

# Khung hiển thị xe
# [FIX 5] 0.55 → 0.617 để khung rộng thêm ~129px (≈ 60px mỗi bên)
# ĐỂ CHỈNH: đổi 0.617 → nhỏ hơn (0.55) hoặc lớn hơn (0.70)
CAR_FRAME_W  = int(SCREEN_W * 0.617)  # ~1185px  <== CHỈNH TẠI ĐÂY
CAR_FRAME_H  = int(CAR_FRAME_W * 0.52)            # <== ĐỔI 0.52 để khung cao/thấp hơn
CAR_FRAME_X  = (SCREEN_W - CAR_FRAME_W) // 2      # tự căn giữa, không cần sửa

# [FIX 3] Dịch frame xe xuống 100px để đáy xe gần sát "sàn" showroom hơn
# Công thức gốc: 0.28 * 1080 = ~302px → sau fix: ~402px (≈ 0.37 * 1080)
CAR_FRAME_Y  = int(SCREEN_H * 0.28) + 100  # <== ĐỔI 0.28 (vị trí dọc) hoặc +100 (tinh chỉnh px)

# Thời gian 1 lần slide chuyển xe: 1.0 giây, chia đều ease-in 0.5s + ease-out 0.5s
SLIDE_DURATION = 1.0  # <== ĐỔI nếu muốn slide nhanh hơn (0.6) hoặc chậm hơn (1.5)

# Dot indicator ở đáy màn hình — mỗi dot = 1 xe
DOT_SIZE    = 44        # px  <== ĐỔI kích thước từng dot
DOT_GAP     = 18        #     <== ĐỔI khoảng cách giữa 2 dot
DOT_Y       = SCREEN_H - 70  # <== ĐỔI 70 để hàng dot lên/xuống (số lớn hơn = lên cao hơn)
DOT_TOTAL   = len(CAR_LIST)
DOT_ROW_W   = DOT_TOTAL * DOT_SIZE + (DOT_TOTAL - 1) * DOT_GAP
DOT_START_X = (SCREEN_W - DOT_ROW_W) // 2  # tự căn giữa, không cần sửa

# Nút mũi tên điều hướng trái/phải
NAV_BTN_SIZE = 90  # <== ĐỔI kích thước nút mũi tên (hình vuông)
# NAV_Y tự tính theo tâm khung xe, không cần sửa trực tiếp
NAV_Y        = CAR_FRAME_Y + CAR_FRAME_H // 2 - NAV_BTN_SIZE // 2

# [FIX 5] 70 → 220: đẩy mũi tên ra thêm 150px mỗi bên
# ĐỂ CHỈNH: đổi 220 → số khác (nhỏ hơn = gần khung xe, lớn hơn = xa hơn)
NAV_PREV_X   = CAR_FRAME_X - NAV_BTN_SIZE - 220  # <== ĐỔI 220 = khoảng cách nút trái với khung xe
NAV_NEXT_X   = CAR_FRAME_X + CAR_FRAME_W + 220   # <== ĐỔI 220 = khoảng cách nút phải với khung xe

# [FIX 4] Cả 2 nút RACE + MENU cùng kích thước 200x60 để giao diện đồng bộ
RACE_BTN_W  = 200  # <== ĐỔI chiều rộng nút LET'S RACE
RACE_BTN_H  = 80   # <== ĐỔI chiều cao nút LET'S RACE
RACE_BTN_X  = SCREEN_W - RACE_BTN_W - 10  # <== ĐỔI 10 = margin phải
RACE_BTN_Y  = SCREEN_H - RACE_BTN_H - 10  # <== ĐỔI 10 = margin dưới

MENU_BTN_W  = 200  # <== ĐỔI chiều rộng nút MAIN MENU (nên giữ = RACE_BTN_W)
MENU_BTN_H  = 80   # <== ĐỔI chiều cao nút MAIN MENU (nên giữ = RACE_BTN_H)
MENU_BTN_X  = 10   # <== ĐỔI margin trái
MENU_BTN_Y  = SCREEN_H - MENU_BTN_H - 10  # <== ĐỔI 10 = margin dưới

# Header góc trên trái: [LOGO BOX] + [NAME BOX]
# [FIX 1] Logo box rộng thêm 30px (110→140px), name box rộng thêm 100px (620→720px)
LOGO_BOX_SIZE = 140  # <== ĐỔI kích thước ô vuông logo hãng xe
LOGO_BOX_X    = 40   # <== ĐỔI vị trí X (cách lề trái)
LOGO_BOX_Y    = 30   # <== ĐỔI vị trí Y (cách lề trên)
NAME_BOX_X    = LOGO_BOX_X + LOGO_BOX_SIZE + 18  # tự tính sát phải logo, chỉ đổi gap (18)
NAME_BOX_Y    = LOGO_BOX_Y                         # cùng hàng logo, không cần sửa
NAME_BOX_W    = 720  # <== ĐỔI chiều rộng ô tên xe (nếu tên vẫn tràn thì tăng lên)
NAME_BOX_H    = LOGO_BOX_SIZE  # tự bằng logo, không cần sửa


# =====================================================================
# HÀM TIỆN ÍCH
# =====================================================================

def ease_in_out(t):
    """
    Hàm nội suy cubic ease-in-out: f(t) = t² × (3 - 2t), với t ∈ [0, 1]

    Đặc điểm:
      - t=0.0 → f=0.0  (điểm bắt đầu, vận tốc = 0 → khởi động mượt)
      - t=0.5 → f=0.5  (điểm giữa)
      - t=1.0 → f=1.0  (điểm kết thúc, vận tốc = 0 → dừng mượt)

    Dùng cho slide chuyển xe: offset = ease_in_out(slide_t) × CAR_FRAME_W
    Thay vì linear (giật cục), cubic cho cảm giác xe "lướt" tự nhiên hơn.
    """
    return t * t * (3 - 2 * t)


def get_asset_base(base_dir, *paths):
    """
    Tạo đường dẫn tuyệt đối đến file asset.
    base_dir: thư mục gốc dự án (chứa folder assets/)
    *paths  : các subfolder và tên file, VD: "brandlogo", "mazda.png"
    Trả về : base_dir/assets/brandlogo/mazda.png
    """
    return os.path.join(base_dir, "assets", *paths)


# =====================================================================
# CLASS CHÍNH
# =====================================================================

class ShowroomScreen:
    def __init__(self, base_dir, fonts: dict, bg_image=None):
        """
        Khởi tạo màn hình showroom.

        Tham số:
          base_dir  : đường dẫn gốc dự án — dùng để tìm assets/
          fonts     : dict font từ core_main, gồm "large"(80px), "medium"(45px), "small"(25px)
          bg_image  : Surface nền đã load sẵn từ core_main — nếu None thì tự load hoặc dùng màu

        Luồng khởi tạo:
          1. Lưu font tham chiếu
          2. Tạo font riêng 20px cho nút bấm
          3. Lưu/load background
          4. Khởi tạo biến trạng thái slide
          5. Tạo Rect cho 2 nút RACE + MENU
          6. Gọi _load_assets() để load ảnh xe, logo, icon
        """
        self.base_dir = base_dir
        self.font_lg  = fonts.get("large")    # 80px — tiêu đề lớn (hiện chưa dùng)
        self.font_md  = fonts.get("medium")   # 45px — tên xe, placeholder text
        self.font_sm  = fonts.get("small")    # 25px — text phụ

        # [FIX 4] Font riêng 20px cho nút RACE + MENU
        # Không tái dùng font_sm (25px) vì nút chỉ cao 60px, 25px sẽ bị chật
        # Không scale surface chữ vì scale bitmap làm mờ nét — phải render đúng size
        font_path = os.path.join(base_dir, "assets", "fonts", "SVN-New Athletic M54.ttf")
        try:
            self.font_btn = pygame.font.Font(font_path, 25)
        except:
            # Fallback system font khi file .ttf không tồn tại (môi trường khác)
            self.font_btn = pygame.font.SysFont("impact", 25)

        # Nhận background từ core_main (đã scale 1920x1080)
        # Nếu core_main không truyền vào thì tự load theo đường dẫn cứng
        if bg_image:
            self.bg = bg_image
        else:
            try:
                bg_path = r"D:\2D Sideway Showdown\assets\background_game\showroom-car-select.png"
                raw_bg  = pygame.image.load(bg_path).convert()
                self.bg = pygame.transform.smoothscale(raw_bg, (SCREEN_W, SCREEN_H))
            except Exception as e:
                print(f"[SHOWROOM BG LOAD ERROR] {e}")
                self.bg = None  # sẽ fallback fill màu đặc trong draw()

        # ── Trạng thái slide ──────────────────────────────────────────
        # selected  : index xe hiện tại đang hiển thị (0 đến DOT_TOTAL-1)
        # slide_t   : tiến trình animation [0.0 → 1.0]; khi = 1.0 nghĩa là không slide
        # slide_dir : +1 = chuyển sang phải (next), -1 = chuyển sang trái (prev)
        # slide_from: index xe CŨ đang trượt ra, dùng để vẽ 2 xe song song khi slide
        self.selected   = 0
        self.slide_t    = 1.0
        self.slide_dir  = 0
        self.slide_from = 0

        # Rect click-detection cho 2 nút góc màn hình
        # pygame.Rect(x, y, w, h) — dùng .collidepoint(mouse_pos) để kiểm tra hover/click
        self.rect_race = pygame.Rect(RACE_BTN_X, RACE_BTN_Y, RACE_BTN_W, RACE_BTN_H)
        self.rect_menu = pygame.Rect(MENU_BTN_X, MENU_BTN_Y, MENU_BTN_W, MENU_BTN_H)

        self._load_assets()

    # ------------------------------------------------------------------
    def _load_assets(self):
        """
        Load toàn bộ ảnh cần thiết cho showroom.
        Dùng pattern try/except cho từng asset: nếu thiếu file thì self.img_xxx = None
        và các hàm vẽ sẽ tự fallback (tam giác, vòng tròn, placeholder vàng).
        Điều này giúp game không crash khi thiếu asset trong quá trình dev.
        """
        def ga(*p):
            """Shorthand nội bộ cho get_asset_base — tránh viết self.base_dir lặp lại."""
            return get_asset_base(self.base_dir, *p)

        # ── Nút điều hướng (PNG có alpha) ─────────────────────────────
        # convert_alpha() chuyển surface sang format có kênh alpha riêng biệt
        # → blit nhanh hơn SRCALPHA surface thông thường
        try:
            raw = pygame.image.load(ga("ui-interactive", "next-button.png")).convert_alpha()
            self.img_next = pygame.transform.smoothscale(raw, (NAV_BTN_SIZE, NAV_BTN_SIZE))
        except:
            self.img_next = None  # fallback: vẽ tam giác trong _draw_nav_buttons

        try:
            raw = pygame.image.load(ga("ui-interactive", "previous-button.png")).convert_alpha()
            self.img_prev = pygame.transform.smoothscale(raw, (NAV_BTN_SIZE, NAV_BTN_SIZE))
        except:
            self.img_prev = None

        # ── Dot indicator (active/inactive) ───────────────────────────
        try:
            raw = pygame.image.load(ga("ui-interactive", "active-select-dot.png")).convert_alpha()
            self.img_dot_on = pygame.transform.smoothscale(raw, (DOT_SIZE, DOT_SIZE))
        except:
            self.img_dot_on = None   # fallback: vẽ circle màu sáng

        try:
            raw = pygame.image.load(ga("ui-interactive", "inactive-select-dot.png")).convert_alpha()
            self.img_dot_off = pygame.transform.smoothscale(raw, (DOT_SIZE, DOT_SIZE))
        except:
            self.img_dot_off = None  # fallback: vẽ circle màu tối

        # ── Ảnh xe — load trước toàn bộ vào list self.car_imgs ────────
        # Lý do load hết 1 lần: tránh đọc file disk mỗi frame khi slide,
        # smoothscale tốn CPU nếu làm realtime
        self.car_imgs = []
        for _, fname, _ in CAR_LIST:
            img = self._load_car(ga("car_model_display", fname + ".png"))
            self.car_imgs.append(img)  # None nếu file không tồn tại

        # ── Brand logo ────────────────────────────────────────────────
        # [FIX 1] LOGO_BOX_SIZE tăng 140px, logo bên trong = 110px (có padding 15px mỗi bên)
        # Công thức LOGO_INNER = LOGO_BOX_SIZE - 30 để padding tự động scale nếu đổi box
        LOGO_INNER = LOGO_BOX_SIZE - 30
        self.brand_logos = []
        for _, _, logo_file in CAR_LIST:
            img = None
            if logo_file:
                try:
                    raw = pygame.image.load(ga("brandlogo", logo_file)).convert_alpha()
                    img = pygame.transform.smoothscale(raw, (LOGO_INNER, LOGO_INNER))
                except:
                    pass  # None → hiện chữ "LOGO" fallback
            self.brand_logos.append(img)

        # Rect click-detection cho 2 nút mũi tên
        # Tạo ở đây (sau khi có NAV constants) thay vì __init__ vì phụ thuộc NAV_Y
        # được tính từ CAR_FRAME_Y (runtime constant)
        self.rect_next = pygame.Rect(NAV_NEXT_X, NAV_Y, NAV_BTN_SIZE, NAV_BTN_SIZE)
        self.rect_prev = pygame.Rect(NAV_PREV_X, NAV_Y, NAV_BTN_SIZE, NAV_BTN_SIZE)

    # ------------------------------------------------------------------
    def _load_car(self, path):
        """
        Load 1 ảnh xe và scale vừa khung CAR_FRAME_W × CAR_FRAME_H.

        Scale strategy: giữ nguyên tỉ lệ (aspect ratio) bằng cách lấy
        min của 2 hệ số scale ngang/dọc — tránh méo xe.
          scale = min(frame_w / img_w, frame_h / img_h)

        Trả về Surface đã scale, hoặc None nếu file không tồn tại.
        None sẽ được xử lý trong _get_car_surf() → hiện placeholder.
        """
        try:
            raw = pygame.image.load(path).convert_alpha()
            rw, rh = raw.get_size()
            scale  = min(CAR_FRAME_W / rw, CAR_FRAME_H / rh)
            return pygame.transform.smoothscale(raw, (int(rw * scale), int(rh * scale)))
        except:
            return None

    # ------------------------------------------------------------------
    def _placeholder(self, label="Sắp ra mắt"):
        """
        Tạo Surface placeholder màu vàng khi ảnh xe chưa có.

        Trả về Surface kích thước CAR_FRAME_W × CAR_FRAME_H với:
          - Nền vàng bán trong suốt (alpha=200)
          - Viền vàng sáng (alpha=255)
          - Text thông báo xe chưa có
        SRCALPHA cho phép vẽ màu có alpha riêng từng pixel.
        """
        surf = pygame.Surface((CAR_FRAME_W, CAR_FRAME_H), pygame.SRCALPHA)
        # Nền vàng bán trong (alpha 200/255 ≈ 78% đục)
        pygame.draw.rect(surf, (220, 180, 40, 200), surf.get_rect(), border_radius=18)
        # Viền vàng sáng hoàn toàn đục
        pygame.draw.rect(surf, (255, 220, 80, 255), surf.get_rect(), width=3, border_radius=18)
        if self.font_md:
            line1 = self.font_md.render("🚗  Xe đang được cập nhật", True, (255, 255, 255))
            line2 = self.font_sm.render("Sẽ được bổ sung trong bản cập nhật tới!", True, (255, 240, 180))
            # get_rect(center=...) trả về Rect đã căn giữa tại điểm cho trước
            surf.blit(line1, line1.get_rect(center=(CAR_FRAME_W//2, CAR_FRAME_H//2 - 28)))
            surf.blit(line2, line2.get_rect(center=(CAR_FRAME_W//2, CAR_FRAME_H//2 + 24)))
        return surf

    # ------------------------------------------------------------------
    def _get_car_surf(self, idx):
        """
        Lấy Surface xe tại index idx, đã đặt vào khung CAR_FRAME_W × CAR_FRAME_H.

        Truck (Scania) fix:
          _load_car scale ảnh vừa khung sedan. Nếu shift Y lên → đỉnh cabin bị
          cắt bởi surface boundary. Giải pháp: rescale ảnh truck còn 78% TRƯỚC
          khi đặt vào surf → padding đều 4 phía → shift nhẹ lên -25px để xe
          "ngồi" cao hơn trung tâm, không bị cắt bất kỳ phía nào.
        """
        img = self.car_imgs[idx]
        if img is None:
            return self._placeholder()

        fname = CAR_LIST[idx][1]
        if "scania" in fname:
            # Rescale nhỏ lại 78% → đảm bảo fit trong frame có padding
            iw, ih = img.get_size()
            img = pygame.transform.smoothscale(img, (int(iw * 0.78), int(ih * 0.78)))
            y_offset = -25   # dịch lên nhẹ — không bị cắt vì ảnh đã có margin
        else:
            y_offset = 0

        surf = pygame.Surface((CAR_FRAME_W, CAR_FRAME_H), pygame.SRCALPHA)
        rect = img.get_rect(center=(CAR_FRAME_W//2, CAR_FRAME_H//2 + y_offset))
        surf.blit(img, rect)
        return surf

    # ------------------------------------------------------------------
    def handle_event(self, event):
        """
        Xử lý input người dùng — được gọi từ event loop của core_main.

        Trả về:
          "race"  → người dùng nhấn LET'S RACE (core_main chuyển STATE_RACE)
          "menu"  → người dùng nhấn MAIN MENU  (core_main chuyển STATE_MENU)
          None    → click bình thường (điều hướng xe), không đổi state

        Ưu tiên kiểm tra theo thứ tự if/elif:
          1. Nút NEXT (mũi tên phải)
          2. Nút PREV (mũi tên trái)
          3. Nút RACE  ← [FIX] đặt trước else-dot để không bị chặn
          4. Nút MENU  ← tương tự
          5. Dot indicator (click chọn thẳng xe theo vị trí)

        Điều kiện slide_t >= 1.0: chặn input khi đang trong animation slide
        để tránh người dùng spam click gây giật loạn.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = event.pos
            if self.rect_next.collidepoint(mp) and self.slide_t >= 1.0:
                self._start_slide(+1)
            elif self.rect_prev.collidepoint(mp) and self.slide_t >= 1.0:
                self._start_slide(-1)
            elif self.rect_race.collidepoint(mp):
                # Không cần check slide_t vì nút này không liên quan animation xe
                return "race"
            elif self.rect_menu.collidepoint(mp):
                return "menu"
            else:
                # Click dot: tính index dot được click, nếu khác xe hiện tại thì slide
                for i in range(DOT_TOTAL):
                    dx       = DOT_START_X + i * (DOT_SIZE + DOT_GAP)
                    dot_rect = pygame.Rect(dx, DOT_Y, DOT_SIZE, DOT_SIZE)
                    if dot_rect.collidepoint(mp) and i != self.selected and self.slide_t >= 1.0:
                        diff           = i - self.selected  # dương = nhảy về phía phải
                        self.slide_from = self.selected
                        self.selected  = i
                        self.slide_t   = 0.0
                        # diff > 0 → xe mới ở bên phải → slide_dir = +1 (xe cũ đi trái)
                        self.slide_dir = 1 if diff > 0 else -1

        # Phím bàn phím: LEFT/RIGHT arrow thay cho nút mũi tên
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT and self.slide_t >= 1.0:
                self._start_slide(+1)
            elif event.key == pygame.K_LEFT and self.slide_t >= 1.0:
                self._start_slide(-1)

        return None

    # ------------------------------------------------------------------
    def _start_slide(self, direction):
        """
        Bắt đầu animation trượt chuyển xe.

        direction: +1 = tiến (next), -1 = lùi (prev)
        Logic: tính index xe mới (vòng tròn % DOT_TOTAL),
               lưu index xe cũ vào slide_from để vẽ song song 2 xe khi trượt,
               reset slide_t = 0.0 để bắt đầu animation từ đầu.
        """
        new_idx         = (self.selected + direction) % DOT_TOTAL
        self.slide_from = self.selected
        self.selected   = new_idx
        self.slide_dir  = direction
        self.slide_t    = 0.0

    # ------------------------------------------------------------------
    def update(self, dt_ms):
        """
        Cập nhật tiến trình animation slide mỗi frame.

        dt_ms: delta time tính bằng milliseconds từ clock.tick(FPS)
        Tăng slide_t tuyến tính theo thời gian thực (không phụ thuộc FPS):
          slide_t += dt_ms / (SLIDE_DURATION * 1000)
        min(..., 1.0) đảm bảo slide_t không vượt quá 1.0 (kết thúc animation).
        """
        if self.slide_t < 1.0:
            self.slide_t = min(self.slide_t + dt_ms / (SLIDE_DURATION * 1000), 1.0)

    # ------------------------------------------------------------------
    def draw(self, screen):
        """
        Vẽ toàn bộ màn hình showroom theo thứ tự layer (dưới → trên):
          1. Background (nền)
          2. Header (logo hãng + tên xe)
          3. Khung xe + animation slide
          4. Nút mũi tên điều hướng
          5. Nút LET'S RACE + MAIN MENU
          6. Dot indicator

        Thứ tự blit quan trọng: blit sau sẽ đè lên blit trước (painter's algorithm).
        """
        # Vẽ nền — nếu không có ảnh thì fill màu tối làm fallback
        if self.bg:
            screen.blit(self.bg, (0, 0))
        else:
            screen.fill((10, 18, 38))  # xanh đen đậm

        self._draw_header(screen)
        self._draw_car_slot(screen)
        self._draw_nav_buttons(screen)
        self._draw_race_button(screen)
        self._draw_menu_button(screen)
        self._draw_dots(screen)

    # ------------------------------------------------------------------
    def _draw_header(self, screen):
        """
        Vẽ header góc trên trái gồm 2 phần:
          [LOGO BOX] — hình vuông chứa logo hãng xe
          [NAME BOX] — hình chữ nhật chứa tên model xe

        Cả 2 đều là Surface SRCALPHA (trong suốt) vẽ lên rồi blit ra screen,
        tạo hiệu ứng nền bán trong suốt mà không ảnh hưởng background.

        [FIX 1] Adaptive font size cho tên xe theo số ký tự:
          ≤25 ký tự → 40px  | ≤35 ký tự → 30px  | >35 ký tự → 25px
        [FIX 1] Text tên xe: LEFT ALIGN thay vì center để tên dài không bị cắt.
        """
        # ── LOGO BOX ──────────────────────────────────────────────────
        # SRCALPHA: mỗi pixel có kênh alpha riêng → draw.rect với alpha hoạt động đúng
        logo_surf = pygame.Surface((LOGO_BOX_SIZE, LOGO_BOX_SIZE), pygame.SRCALPHA)
        # Nền xanh tối, alpha=200 (~78% đục) để nhìn thấu background một phần
        pygame.draw.rect(logo_surf, (40, 40, 120, 200), logo_surf.get_rect(), border_radius=14)
        # Viền xanh nhạt alpha=200, width=2 → chỉ vẽ viền, không fill
        pygame.draw.rect(logo_surf, (140, 160, 255, 200), logo_surf.get_rect(), width=2, border_radius=14)

        brand_img = self.brand_logos[self.selected]
        if brand_img:
            # Căn giữa logo trong box bằng cách tính offset từ kích thước
            bx = (LOGO_BOX_SIZE - brand_img.get_width())  // 2
            by = (LOGO_BOX_SIZE - brand_img.get_height()) // 2
            logo_surf.blit(brand_img, (bx, by))
        elif self.font_sm:
            # Fallback khi chưa có file logo: hiện chữ "LOGO"
            t = self.font_sm.render("LOGO", True, (255, 255, 255))
            logo_surf.blit(t, t.get_rect(center=(LOGO_BOX_SIZE//2, LOGO_BOX_SIZE//2)))
        screen.blit(logo_surf, (LOGO_BOX_X, LOGO_BOX_Y))

        # ── NAME BOX ──────────────────────────────────────────────────
        name_surf = pygame.Surface((NAME_BOX_W, NAME_BOX_H), pygame.SRCALPHA)
        # Nền xanh vừa đậm hơn logo box, alpha=180
        pygame.draw.rect(name_surf, (60, 80, 180, 180), name_surf.get_rect(), border_radius=14)
        pygame.draw.rect(name_surf, (140, 160, 255, 200), name_surf.get_rect(), width=2, border_radius=14)

        car_name = CAR_LIST[self.selected][0]  # index 0 = name trong tuple (name, file, logo)
        name_len = len(car_name)

        # [FIX 1] Adaptive font: load font đúng size thay vì scale surface
        # Lý do KHÔNG scale: pygame scale bitmap font → vỡ/mờ nét
        # Lý do load mỗi frame được chấp nhận: pygame.font.Font() cache font object,
        # chỉ tốn CPU khi size thay đổi (tức là khi đổi xe có tên khác nhóm độ dài)
        font_path = os.path.join(self.base_dir, "assets", "fonts", "SVN-New Athletic M54.ttf")
        if name_len <= 25:
            size = 50   # tên ngắn: "Ferrari F430 2005" (17 ký tự)
        elif name_len <= 35:
            size = 40   # tên vừa: "Nissan Skyline GT-R34 1999" (26 ký tự)
        else:
            size = 32   # tên dài: "Lamborghini Murcielago LP670-4 SV 2010" (39 ký tự)
        try:
            name_font = pygame.font.Font(font_path, size)
        except:
            name_font = pygame.font.SysFont("impact", size)

        # [FIX 1] LEFT ALIGN với padding 18px từ cạnh trái
        # căn dọc giữa: text_y = (chiều cao box - chiều cao chữ) / 2
        # font.size(text) trả về (width, height) mà không cần render — hiệu quả hơn
        PADDING_LEFT = 18
        text_y = (NAME_BOX_H - name_font.size(car_name)[1]) // 2

        # Kỹ thuật outline chữ: render màu đen lệch 4 hướng (+/-1px) trước,
        # sau đó render màu trắng đè chính giữa → tạo viền đen tự nhiên
        out = name_font.render(car_name, True, (0, 0, 0))
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            name_surf.blit(out, (PADDING_LEFT + dx, text_y + dy))
        t = name_font.render(car_name, True, (255, 255, 255))
        name_surf.blit(t, (PADDING_LEFT, text_y))

        screen.blit(name_surf, (NAME_BOX_X, NAME_BOX_Y))

    # ------------------------------------------------------------------
    def _draw_car_slot(self, screen):
        """
        Vẽ xe (hoặc 2 xe khi đang slide) vào khung CAR_FRAME.

        Cơ chế slide:
          - slide_t  : tiến trình [0→1], tăng theo thời gian thực trong update()
          - t_eased  : slide_t sau khi qua ease_in_out() → chuyển động mượt
          - offset   : số pixel đã dịch chuyển = t_eased × CAR_FRAME_W (luôn dương)

        Khi đang slide (slide_t < 1.0), vẽ ĐỒNG THỜI 2 xe:
          - surf_old: xe cũ, trượt ra theo chiều slide_dir
          - surf_new: xe mới, từ phía ngược lại trượt vào

        [FIX 5] Tách riêng 2 nhánh dir=+1 / dir=-1 để tránh bug nhân âm:
          dir=+1 (next): xe cũ ra trái, xe mới vào từ phải
          dir=-1 (prev): xe cũ ra phải, xe mới vào từ trái

        set_clip(): giới hạn vùng vẽ về đúng khung xe
        → xe không "tràn" ra ngoài khung khi đang trượt
        → gọi set_clip(None) để bỏ giới hạn sau khi vẽ xong
        """
        t_eased = ease_in_out(self.slide_t)

        if self.slide_t >= 1.0:
            # Không slide: vẽ thẳng xe hiện tại
            surf = self._get_car_surf(self.selected)
            screen.blit(surf, (CAR_FRAME_X, CAR_FRAME_Y))
        else:
            # offset luôn dương: số pixel đã trượt trong khoảng [0, CAR_FRAME_W]
            offset   = int(t_eased * CAR_FRAME_W)
            surf_old = self._get_car_surf(self.slide_from)
            surf_new = self._get_car_surf(self.selected)

            # Clip: chỉ vẽ trong vùng chữ nhật của khung xe
            clip_rect = pygame.Rect(CAR_FRAME_X, CAR_FRAME_Y, CAR_FRAME_W, CAR_FRAME_H)
            screen.set_clip(clip_rect)

            if self.slide_dir == 1:
                # next → xe cũ trượt ra bên trái, xe mới vào từ bên phải
                screen.blit(surf_old, (CAR_FRAME_X - offset,               CAR_FRAME_Y))
                screen.blit(surf_new, (CAR_FRAME_X + CAR_FRAME_W - offset, CAR_FRAME_Y))
            else:
                # prev → xe cũ trượt ra bên phải, xe mới vào từ bên trái
                screen.blit(surf_old, (CAR_FRAME_X + offset,               CAR_FRAME_Y))
                screen.blit(surf_new, (CAR_FRAME_X - CAR_FRAME_W + offset, CAR_FRAME_Y))

            screen.set_clip(None)  # bắt buộc reset clip sau khi dùng xong

    # ------------------------------------------------------------------
    def _draw_nav_buttons(self, screen):
        """
        Vẽ 2 nút mũi tên PREV (trái) và NEXT (phải).

        Hiệu ứng hover: khi chuột đè lên nút, scale lên 108% (×1.08)
        và căn giữa tại đúng rect.center để không bị lệch khi to ra.

        Nếu không có file PNG (img_prev/img_next = None):
        vẽ fallback là tam giác pygame.draw.polygon() với màu thay đổi khi hover.
        """
        mouse_pos = pygame.mouse.get_pos()

        # ── NÚT PREV (mũi tên trái) ───────────────────────────────────
        if self.img_prev:
            if self.rect_prev.collidepoint(mouse_pos):
                # Hover: scale lên 8%, căn giữa theo tâm rect gốc
                img = pygame.transform.smoothscale(
                    self.img_prev,
                    (int(NAV_BTN_SIZE * 1.08), int(NAV_BTN_SIZE * 1.08))
                )
                r = img.get_rect(center=self.rect_prev.center)
                screen.blit(img, r)
            else:
                screen.blit(self.img_prev, self.rect_prev)
        else:
            # Fallback: tam giác hướng trái
            color = (200, 220, 255) if self.rect_prev.collidepoint(mouse_pos) else (140, 160, 220)
            pts = [
                (NAV_PREV_X + NAV_BTN_SIZE, NAV_Y),               # đỉnh phải trên
                (NAV_PREV_X,                NAV_Y + NAV_BTN_SIZE//2),  # đỉnh trái giữa
                (NAV_PREV_X + NAV_BTN_SIZE, NAV_Y + NAV_BTN_SIZE),    # đỉnh phải dưới
            ]
            pygame.draw.polygon(screen, color, pts)

        # ── NÚT NEXT (mũi tên phải) ───────────────────────────────────
        if self.img_next:
            if self.rect_next.collidepoint(mouse_pos):
                img = pygame.transform.smoothscale(
                    self.img_next,
                    (int(NAV_BTN_SIZE * 1.08), int(NAV_BTN_SIZE * 1.08))
                )
                r = img.get_rect(center=self.rect_next.center)
                screen.blit(img, r)
            else:
                screen.blit(self.img_next, self.rect_next)
        else:
            color = (200, 220, 255) if self.rect_next.collidepoint(mouse_pos) else (140, 160, 220)
            pts = [
                (NAV_NEXT_X,                NAV_Y),
                (NAV_NEXT_X + NAV_BTN_SIZE, NAV_Y + NAV_BTN_SIZE//2),
                (NAV_NEXT_X,                NAV_Y + NAV_BTN_SIZE),
            ]
            pygame.draw.polygon(screen, color, pts)

    # ------------------------------------------------------------------
    def _draw_dots(self, screen):
        """
        Vẽ hàng dot indicator ở đáy màn hình.
        Mỗi dot = 1 xe; dot active (xe đang chọn) khác màu/ảnh so với inactive.

        Nếu có file PNG → blit ảnh dot
        Nếu không có   → vẽ circle fallback: active=xanh nhạt, inactive=xanh tối
        """
        for i in range(DOT_TOTAL):
            # Tính tọa độ x của từng dot: căn đều từ DOT_START_X
            dx        = DOT_START_X + i * (DOT_SIZE + DOT_GAP)
            is_active = (i == self.selected)

            if is_active and self.img_dot_on:
                screen.blit(self.img_dot_on, (dx, DOT_Y))
            elif not is_active and self.img_dot_off:
                screen.blit(self.img_dot_off, (dx, DOT_Y))
            else:
                # Fallback circle
                color  = (173, 216, 230) if is_active else (20, 40, 100)
                border = (100, 150, 220)
                cx = dx + DOT_SIZE // 2
                cy = DOT_Y + DOT_SIZE // 2
                pygame.draw.circle(screen, color,  (cx, cy), DOT_SIZE // 2)
                pygame.draw.circle(screen, border, (cx, cy), DOT_SIZE // 2, 2)  # viền, width=2

    # ------------------------------------------------------------------
    def _draw_blue_button(self, screen, rect, text, font):
        """
        Hàm vẽ nút chung cho cả RACE và MENU — tránh lặp code (DRY principle).

        Đặc điểm đồ họa:
          - Nền gradient xanh: tối dần 5% từ trên xuống (b: 200→190, g: 100→95)
          - Hover: nhân sáng ×1.1 trên cả b và g
          - Viền đen border_radius=10 để bo góc

        Kỹ thuật gradient bằng pygame:
          Không có API gradient sẵn → vẽ từng dòng ngang (draw.line) với màu thay đổi dần
          theo biến ratio (0.0 ở trên → 1.0 ở dưới). Chi phí: rect.height lần draw.line/frame.

        Kỹ thuật outline chữ trên nút:
          Render text màu đen lệch 4 hướng ±1px → render text trắng chính giữa đè lên
          Kết quả: chữ trắng có viền đen mỏng, dễ đọc trên mọi màu nền nút.
        """
        mp    = pygame.mouse.get_pos()
        hover = rect.collidepoint(mp)

        # SRCALPHA để border_radius hoạt động đúng (trong suốt ở góc bo)
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        for y in range(rect.height):
            ratio = y / rect.height          # 0.0 (trên) → 1.0 (dưới)
            b = int(200 - ratio * 10)        # xanh: 200 → 190
            g = int(100 - ratio * 5)         # lục:  100 → 95
            if hover:
                b = min(255, int(b * 1.1))   # sáng hơn 10% khi hover
                g = min(255, int(g * 1.1))
            pygame.draw.line(surf, (0, g, b), (0, y), (rect.width, y))

        # Viền đen bo góc, width=3 → chỉ viền, không fill đè gradient
        pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), width=3, border_radius=10)

        if font:
            shadow = font.render(text, True, (0, 0, 0))
            label  = font.render(text, True, (255, 255, 255))
            # Outline 4 hướng
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                surf.blit(shadow, shadow.get_rect(center=(rect.width//2 + dx, rect.height//2 + dy)))
            surf.blit(label, label.get_rect(center=(rect.width//2, rect.height//2)))

        screen.blit(surf, rect.topleft)

    # ------------------------------------------------------------------
    def _draw_race_button(self, screen):
        """
        Vẽ nút LET'S RACE! ở góc phải dưới màn hình.
        [FIX 4] Dùng self.font_btn (20px) — đồng nhất kích thước font với MAIN MENU.
        """
        self._draw_blue_button(screen, self.rect_race, "LET'S RACE!", self.font_btn)

    # ------------------------------------------------------------------
    def _draw_menu_button(self, screen):
        """
        Vẽ nút MAIN MENU ở góc trái dưới màn hình.
        [FIX 4] Dùng self.font_btn (20px) — cùng font và size với LET'S RACE!
        """
        self._draw_blue_button(screen, self.rect_menu, "MAIN MENU", self.font_btn)

    # ------------------------------------------------------------------
    @property
    def selected_car_name(self):
        """
        Property trả về tên xe đang được chọn.
        Dùng @property để core_main có thể đọc bằng showroom.selected_car_name
        thay vì showroom.selected_car_name() — giao diện sạch hơn.
        """
        return CAR_LIST[self.selected][0]  # index 0 = name trong tuple (name, file, logo)
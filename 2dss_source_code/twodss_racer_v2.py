"""
twodss_racer_v2.py — Racer + AI Brain v2 (REWRITE)
=====================================================================
THAY THẾ HOÀN TOÀN twodss_racer.py.

NGUYÊN TẮC v2 (theo brief):
  - AI không cần THÔNG MINH, chỉ cần KHÔNG THỂ NGU — luôn follow track,
    luôn né tường, luôn né xe, luôn tự thoát kẹt, không bao giờ random
    khi ra quyết định (trừ chọn driver/aggr lúc khởi tạo race).
  - Mỗi hàm = 1 trách nhiệm. KHÔNG gộp wall-avoid + stuck-recovery +
    overtake + speed-control + path-follow vào 1 hàm update_bot() khổng lồ
    như v1 (đó là lý do v1 giật/ngu — quá nhiều biến chồng chéo).
  - brain_update() CHỈ quyết định hàm nào chạy (priority dispatcher).
    Từng hàm con quyết định NÓ chạy NHƯ THẾ NÀO.

GIỮ NGUYÊN từ v1 (đã chạy ổn, KHÔNG phải AI, không đụng):
  - setup_map(), load_sprite(), FILE_MAP
  - Racer: nitro system, lap tracking, _move/_try_rotate (bicycle model),
    update_player(), race_progress(), _lookahead_point(), _path_curvature()

MỚI trong v2:
  - DRIVER_ROSTER: 42 tên + 5 mức aggression (1.00 → 1.35) đã random
    qua wheel-of-names (3 lần quay, lấy lần cuối) — xem lịch sử chat.
  - 12 FUNCTION não bộ (FUNCTION 01-12) — đang viết theo thứ tự,
    PHẦN NÀY CHƯA XONG, sẽ bổ sung dần qua các bước sau:
      [x] FUNCTION 01 — detect_wall_ahead()
      [x] FUNCTION 02 — choose_escape_direction()
      [x] FUNCTION 03 — detect_stuck()
      [x] FUNCTION 04 — recover_from_stuck()
      [x] FUNCTION 05 — find_safe_waypoint()
      [x] FUNCTION 06 — teleport_recovery()
      [x] FUNCTION 07 — detect_car_ahead()
      [x] FUNCTION 08 — choose_overtake_side()
      [x] FUNCTION 09 — avoid_car_collision()
      [x] FUNCTION 10 — compute_target_speed()
      [x] FUNCTION 11 — follow_path()
      [x] FUNCTION 12 — brain_update()  (dispatcher — XONG, đã thay update_bot())

  update_bot() hiện tại CHỈ còn shim tạm gọi follow_path đơn giản để file
  chạy được trong lúc chờ FUNCTION 03-12 — sẽ thay bằng brain_update() khi
  xong toàn bộ 12 hàm.
=====================================================================
"""
import math, os, random
import pygame
import twodss_physics as physics
from twodss_car_data import CAR_STATS

# =====================================================================
# MAP CONTEXT (set bởi setup_map) — GIỮ NGUYÊN TỪ v1
# =====================================================================
_WAYPOINTS     = []
_GATE_Y        = 0
_GATE_X1       = 0
_GATE_X2       = 0
_MAX_LAPS      = 3
_BASE_DIR      = ""
_CAR_DISPLAY_W = 90
_MAP_SCALE     = 1.0   # MỚI — nhận từ track file qua setup_map(), KHÔNG hardcode nữa

FILE_MAP = {
    "mazda_axela_2012"          : "mazda_axela_sedan_2012",
    "mazda3_fastback_2020"      : "mazda_3_fastback_2020",
    "toyota_ae86_1987"          : "toyota_ae86_trueno",
    "toyota_altezza_gita_2003"  : "toyota_altezza_gita",
    "nissan_gtr_r34"            : "nissan_skyline_gtr_r34",
    "lamborghini_murcielago_sv" : "lamborghini_murcielago_lp670-4_superveloce",
    "ferrari_f430_2005"         : "ferrari_f430_2005",
    "hyundai_n_vision_74"       : "hyundai-n-vision-74",
    "mclaren_600lt"             : "mclaren_600lt",
    "koenigsegg_gemera"         : "koenigsegg_gemera",
    "lamborghini_centenario"    : "lamborghini_centenario",
    "lamborghini_countach_2021" : "lamborghini_countach_lpi800-4",
    "pagani_utopia"             : "pagani_utopia",
    "scania_r730_2010"          : "scania_r730_topline",
    "scania_svempa_frostfire"   : "scania_svempa_frostfire",
}

def setup_map(waypoints, gate_y, gate_x1, gate_x2,
              max_laps=3, base_dir="", car_display_w=90, map_scale=1.0):
    """Gọi 1 lần sau khi load track, trước khi tạo Racer."""
    global _WAYPOINTS,_GATE_Y,_GATE_X1,_GATE_X2
    global _MAX_LAPS,_BASE_DIR,_CAR_DISPLAY_W,_MAP_SCALE
    _WAYPOINTS     = waypoints
    _GATE_Y        = gate_y
    _GATE_X1       = gate_x1
    _GATE_X2       = gate_x2
    _MAX_LAPS      = max_laps
    _BASE_DIR      = base_dir
    _CAR_DISPLAY_W = car_display_w
    _MAP_SCALE     = map_scale

def load_sprite(car_id, display_w=None, tint=None):
    """Load top-down sprite. tint=(R,G,B) cho bot."""
    w = display_w or _CAR_DISPLAY_W
    fname = FILE_MAP.get(car_id)
    if fname:
        path = os.path.join(_BASE_DIR, "assets", "car_model_topdown", fname+".png")
        try:
            raw = pygame.image.load(path).convert_alpha()
            bbox = raw.get_bounding_rect(min_alpha=10)
            raw  = raw.subsurface(bbox).copy()
            rw, rh = raw.get_size()
            sh  = int(rh * w / rw)
            spr = pygame.transform.smoothscale(raw, (w, sh))
            if tint:
                ts = pygame.Surface(spr.get_size())
                ts.fill(tint)
                spr.blit(ts, (0,0), special_flags=pygame.BLEND_RGB_MULT)
            return spr, w, sh
        except Exception as e:
            print(f"[SPRITE] {car_id}: {e}")
    fw, fh = w, int(w*1.8)
    fb = pygame.Surface((fw,fh), pygame.SRCALPHA)
    col = tint if tint else (0,180,255)
    pygame.draw.rect(fb, col, (2,7,fw-4,fh-14), border_radius=7)
    pygame.draw.rect(fb, (0,0,0), (2,7,fw-4,fh-14), width=2, border_radius=7)
    return fb, fw, fh


# =====================================================================
# DRIVER ROSTER v2 (MỚI) — 42 tên + 5 mức aggression
# =====================================================================
# AGGR_LEVELS: hệ số nhân tốc độ/risk — dùng ở FUNCTION 10 (compute_target_speed)
#   và làm ngưỡng phản xạ ở FUNCTION 01/07 (mức cao = quét muộn hơn = risk hơn).
# Chia đều 1.00 → 1.35 / 5 mức = bước 0.0875.
COMPOSURE_LEVELS = [1.00, 1.0875, 1.175, 1.2625, 1.35]   # giữ y số cũ
COMPOSURE_LABELS = ["Ngay Ngo", "Long Ngong", "Vung Tay", "Lao Luyen", "Tinh Ruou"]
#                  thấp nhất, vô tri, dễ panic        trung bình        cao nhất — tỉnh, làm chủ, biết DRIFT qua cua
COMPOSURE_VARIANCE  = 0.25   # ± biên dao động quanh composure GỐC
COMPOSURE_LERP_RATE = 0.5    # /giây — tốc độ trôi về "đích" mới, không nhảy cục
AVOID_RADIUS_BOOST = 1.30   # +30% bán kính kiểm soát/né xe, KHÔNG áp cho wall-scan/lookahead

# DRIVER_ROSTER: (name, country, aggr_level_index 0-4)
# Kết quả random wheel-of-names — 3 lần quay/người, lấy lần cuối (đã chốt).
DRIVER_ROSTER = [
    # ── UK ──
    ("Leo Finch","UK",3), ("Blake Ryder","UK",2), ("Kai Thorne","UK",2),
    ("Mia Brooks","UK",0), ("Jax Wright","UK",1), ("Faye Sterling","UK",2),
    ("Cole Vance","UK",2),
    # ── USA ──
    ("Colt Hayes","USA",3), ("Nova Archer","USA",0), ("Lexi Vance","USA",2),
    ("Jaxson Reed","USA",0), ("Roxy Miller","USA",0), ("Zane Wyatt","USA",1),
    ("Chase Vance","USA",4),
    # ── AUS ──
    ("Cruz Miller","AUS",1), ("Finn Stark","AUS",1), ("Tess Oliver","AUS",1),
    ("Skye Hunter","AUS",3), ("Jace Evans","AUS",4), ("Reed Adler","AUS",4),
    ("Amber West","AUS",1),
    # ── JPN ──
    ("Asuka Koga","JPN",3), ("Ryu Mori","JPN",2), ("Kenji Sato","JPN",3),
    ("Sora Endo","JPN",3), ("Ren Kaze","JPN",4), ("Mai Hoshi","JPN",4),
    ("Yuki Honda","JPN",3),
    # ── KOR ──
    ("Min Woo","KOR",1), ("Ha Neul","KOR",3), ("Tae Yang","KOR",0),
    ("Seo Jun","KOR",4), ("Jin Kim","KOR",0), ("Ji Hoon","KOR",4),
    ("Soo Bin","KOR",4),
    # ── CHN ──
    ("Jian Tao","CHN",1), ("Mei Ling","CHN",3), ("Bo Lin","CHN",1),
    ("Jun Jie","CHN",2), ("Hao Yu","CHN",0), ("Li Wei","CHN",2),
    ("Chen Bo","CHN",0),
]

def pick_drivers(n, exclude_names=None):
    """
    Random KHÔNG lặp n driver từ DRIVER_ROSTER cho 1 race.
    exclude_names: set tên cần loại (ví dụ tên đã gán cho player nếu có).
    Trả về list[(name, country, aggr_value)] — aggr đã đổi từ index → float.
    """
    pool = [d for d in DRIVER_ROSTER if not exclude_names or d[0] not in exclude_names]
    n = min(n, len(pool))
    chosen = random.sample(pool, n)
    return [(name, country, COMPOSURE_LEVELS[idx]) for (name, country, idx) in chosen]

def _sc(px_tuned_at_scale_1: float) -> float:
    """Quy đổi khoảng cách px đã tune ở MAP_SCALE=1.0 sang map hiện tại.
    Dùng cho MỌI hằng số khoảng cách trong AI brain (curvature lookahead,
    wall scan, car-detect range...) để không lặp lại bug 'số cứng không
    theo kịp MAP_SCALE' mỗi khi đổi zoom."""
    return px_tuned_at_scale_1 * _MAP_SCALE

class Racer:
    def __init__(self, car_id, x, y, angle, is_player=False, tint=None,
                 waypoints=None, driver_name=None, driver_country=None,
                 composure=None):
        """
        waypoints: list[(int,int)] — bộ waypoint riêng cho xe này.
          None  → dùng _WAYPOINTS global (tương thích ngược).
        driver_name/driver_country/aggr: profile từ DRIVER_ROSTER (v2 mới).
          aggr=None → mặc định 1.00 (Hien) — KHÔNG random ngầm trong __init__,
          việc random driver phải làm RÕ RÀNG ở nơi gọi (pick_drivers()),
          để không có 2 nguồn random giẫm nhau (lý do v1 bị "vừa lí vừa não vấn đề").
        """
        self.car_id    = car_id
        self.x         = float(x)
        self.y         = float(y)
        self.angle     = float(angle)
        self.velocity  = 0.0
        self.is_player = is_player
        self._waypoints = waypoints  # None or list[(x,y)]
        self._escape_commit_t = 0.0 # FUNCTION 02 — đồng hồ commit hướng escape
        self._escape_commit_time = 1.0  # có thể tinh chỉnh
        # PATCH START: drift flag
        self.is_drifting = False

        # ── Driver profile (v2 MỚI) ───────────────────────────────────
        self.driver_name    = driver_name or ("YOU" if is_player else "???")
        self.driver_country = driver_country or "--"
        self.composure = float(composure) if composure is not None else 1.00
        self.composure_instant = self.composure
        self._composure_target = self.composure
        self._composure_retarget_t = random.uniform(1.5, 4.0)

        s = CAR_STATS[car_id]
        self.max_speed    = s["max_speed"]
        self.acceleration = s["acceleration"] * 1.4
        self.brake_power  = s["brake"]
        self.friction      = s["friction"]
        self.tier          = s["tier"]
        self.turn_speed    = {"A":110,"B":120,"C":125,"D":130,"S":95}[self.tier]
        self.sprite, self.car_w, self.car_h = load_sprite(car_id, tint=tint)

        # ── Nitro v2 — luật mới (xem twodss_physics.py: update_nitro_v2) ──
        # "nitro_timer"/"nitro_cd_timer" (v1) ĐÃ BỎ: v2 không còn cooldown
        # (hết nitro -> nạp lại ngay) và không còn đếm ngược thời lượng cố
        # định (v2 dùng GIỮ/NHẢ LCTRL, không phải "kích 1 lần chạy hết giờ").
        self._nitro_duration   = float(s.get("nitro_duration",   10.0))
        self._nitro_boost      = float(s.get("nitro_boost",      50.0))
        self._nitro_boost_time = float(s.get("nitro_boost_time",  4.0))
        _r13 = float(s.get("nitro_refill_1per3", 6.8))
        self._nitro_refill_rate = 33.33 / _r13   # %/s — tốc độ nạp khi chạy bình thường

        self.nitro_amount   = 0.0     # % nhiên liệu nitro, 0..100
        self.nitro_active   = False   # True khi đang GIỮ LCTRL và còn nitro để xài
        self._nitro_hold_t  = 0.0     # giây đã giữ LIÊN TỤC — dùng để ramp boost (nitro_boost_time)
        self._nitro_top_bonus = 0.0   # +kph hiện tại đang cộng lên max_speed (ramp lên / decay xuống)

        # Bot-only: mô phỏng "giữ phím" bằng đồng hồ tự nhả sau X giây
        # (xem _try_activate_nitro/_update_bot_nitro_hold) — player dùng
        # phím LCTRL thật (KEYDOWN/KEYUP) nên không cần đồng hồ này.
        self._bot_nitro_release_t = 0.0
        self._drifting = False   # cờ frame-trước, set bởi follow_path() — đọc bởi _update_nitro()

        # Lap
        self.race_started = False
        self.lap_count    = 0
        self.lap_prev_y   = self.y
        self.lap_times    = []
        self.lap_start    = 0.0
        self.race_start   = 0.0
        self.lap_debounce = 0.0
        self.finished     = False

        # AI / position
        self.wp_idx   = 0
        self.wp_total = 0
        self.pos      = 1

        # ── AI brain state (v2 — sẽ dùng dần khi thêm FUNCTION 03-12) ──
        self.stuck_t        = 0.0   # FUNCTION 03/04 — số giây đã neo dưới ngưỡng speed
        self._stuck_anchor  = None  # FUNCTION 03 — (x,y) tại lúc speed lần đầu tụt dưới ngưỡng
        self._curve_ema     = 0.0   # FUNCTION 10 — làm mượt _path_curvature() theo thời gian
                                       # (bổ sung sau khi test phát hiện curvature dao động mạnh
                                       # giữa các waypoint liền kề ở khúc cua gấp thật)
        self._recover_phase = None  # FUNCTION 04 — None | "reverse" | "forward"
        self._recover_t     = 0.0   # FUNCTION 04 — thời gian đã trôi trong pha hiện tại
        self._recover_dir   = 0     # FUNCTION 04 — hướng full-lock đã chọn (cố định cả pha reverse)
        self.wall_stuck_t   = 0.0   # FUNCTION 06 — đồng hồ kẹt DÀI HẠN (ngưỡng 6s, khác stuck_t 2s)
        self._teleport_anchor = None  # FUNCTION 06 — anchor riêng, KHÔNG dùng chung với _stuck_anchor
        self._no_collide_t  = 0.0   # FUNCTION 06 bước 5 — disable collision sau teleport
        self._blink_count   = 0     # FUNCTION 06 bước 6 — số lần nhấp nháy còn lại
        self._blink_t       = 0.0   # FUNCTION 06 bước 6 — đồng hồ nhịp nhấp nháy
        self.visible        = True  # FUNCTION 06 bước 6 — render loop đọc cờ này để
                                       # quyết định CÓ VẼ sprite frame này không (nhấp nháy)
        self._escape_dir    = 0     # FUNCTION 02 — hướng escape đang commit
        self._overtake_side = 0     # FUNCTION 08
        self._yield_hold_t  = 0.0  # giữ trạng thái "đang nhường" thêm 1 khoảng sau khi rời vùng gần

        # Physics state
        self._cached_normal  = None
        self._wall_contact_t = 0.0
        self.player_stuck_t  = 0.0
        self._move_dir = float(angle)

    @property
    def _wp(self):
        return self._waypoints if self._waypoints is not None else _WAYPOINTS

    # ── NITRO v2 — LUẬT MỚI (xem đặc tả: chat "cập nhật nitro") ──────────
    def _update_nitro(self, dt, want_nitro=False, drifting=False, is_moving=True):
        """
        Cập nhật nitro mỗi frame. DÙNG CHUNG cho player VÀ bot — cùng 1
        công thức, cùng 1 hệ số, để giữ đúng "BÌNH ĐẲNG MỌI BOT MỌI XE"
        (chỉ khác nhau qua _nitro_* lấy từ CAR_STATS của từng xe, đúng
        bảng xlsx — không có số riêng cho bot).

        Tham số:
          want_nitro : True nếu đang GIỮ phím nitro (LCTRL ở player,
                       hoặc "đang giữ" mô phỏng ở bot) VÀ còn nhiên liệu.
          drifting   : True nếu xe đang drift (SPACE/handbrake) ngay
                       frame này — ảnh hưởng tốc độ NẠP (không phải hao).
          is_moving  : False nếu xe gần như đứng yên (velocity~0) —
                       đứng yên thì KHÔNG được nạp nitro (brief: "nhưng
                       xe đứng yên thì nitro sẽ không được tăng lên").

        ── NẠP (refill) ────────────────────────────────────────────────
        Luôn cộng refill nếu xe đang chạy — CẢ KHI đang xài nitro cùng
        lúc (khác v1: v1 chỉ refill khi KHÔNG active). Đây chính là cơ
        chế "bù trừ" theo brief: refill (nhỏ) cộng song song với drain
        (lớn hơn) -> nitro vẫn tụt khi xài, nhưng tụt CHẬM HƠN nếu đang
        drift, vì lúc đó refill được +40%. Không cần số "-40% drain"
        cứng — kết quả tự ra từ 2 lực cộng/trừ độc lập trên cùng 1 biến.

        ── HAO (drain) ────────────────────────────────────────────────
        Chỉ hao khi nitro_active=True (đang giữ phím VÀ còn nhiên liệu).
        DRAIN = 100/nitro_duration — giữ nguyên công thức v1, không đổi.

        ── KÍCH HOẠT / TẮT (hold-release, KHÔNG còn cooldown) ───────────
        want_nitro=True và nitro_amount>0 -> nitro_active=True.
        Nhả ra (want_nitro=False) hoặc hết nhiên liệu -> nitro_active=False
        NGAY (đúng brief: "nhả ra để tiết kiệm nitro"). Hết nitro thì nạp
        lại liền, không chờ cooldown (bỏ hẳn nitro_cd_timer của v1).

        ── TOP SPEED BONUS (ramp lên / decay mượt xuống) ────────────────
        Khi active: bonus ramp dần lên _nitro_boost theo _nitro_boost_time
        (giữ nguyên công thức ramp v1, chỉ đổi nguồn input từ "đang active
        do timer" sang "đang active do giữ phím").
        Khi KHÔNG active (vừa nhả hoặc vừa hết xăng): bonus giảm MƯỢT về 0
        theo slope tuyến tính -1.5 (kph/s, theo % thang full boost, xem
        physics._DECAY_SLOPE) — KHÔNG cắt cụt như v1.

        Trả về: top_speed hiện tại = max_speed + bonus.
        """
        NITRO_MAX = 100.0
        DRAIN     = 100.0 / self._nitro_duration
        # Về đích rồi -> nitro vô hiệu hoàn toàn: không refill, không
        # drain, không active, top speed trả về max_speed gốc luôn.
        if self.finished:
            self.nitro_active = False
            self._nitro_hold_t = 0.0
            self._nitro_top_bonus = 0.0
            return self.max_speed

        # ── Bật/tắt active theo giữ phím + còn nhiên liệu (tính TRƯỚC
        #    refill, vì refill phụ thuộc trạng thái active của CHÍNH
        #    frame này — đang xài nitro mà không drift thì KHÔNG được
        #    cộng refill, chỉ có drain thuần) ─────────────────────────
        self.nitro_active = bool(want_nitro and self.nitro_amount > 0 and not self.finished)

        # ── Nạp (refill) ──────────────────────────────────────────────
        # - KHÔNG xài nitro, đang chạy: nạp bình thường (hoặc +40% nếu
        #   đang drift) — đúng "xe chạy thì nitro tích trữ dần".
        # - ĐANG xài nitro (active) KHÔNG drift: KHÔNG nạp gì cả — chỉ
        #   có drain thuần, tụt với tốc độ đầy đủ.
        # - ĐANG xài nitro VÀ đang drift: ĐÂY MỚI là lúc refill (do
        #   drift sinh ra) được cộng vào để BÙ một phần drain -> tụt
        #   CHẬM HƠN, nhưng luôn luôn vẫn tụt (refill_do_drift luôn nhỏ
        #   hơn DRAIN, không bao giờ đứng yên hay tăng lên khi đang xài).
        if is_moving and (not self.nitro_active or drifting):
            refill = self._nitro_refill_rate * (1.4 if drifting else 1.0)
            if self.nitro_active:
                refill = min(refill, DRAIN)  # chặn trần: không bao giờ vượt DRAIN -> chỉ tiệm cận 0, không tăng
            self.nitro_amount = min(self.nitro_amount + refill * dt, NITRO_MAX)

        # ── Hao (drain) — chỉ khi active ───────────────────────────────
        if self.nitro_active:
            self.nitro_amount = max(0.0, self.nitro_amount - DRAIN * dt)
            self._nitro_hold_t += dt
            if self.nitro_amount <= 0:
                self.nitro_active  = False
                self._nitro_hold_t = 0.0
        else:
            self._nitro_hold_t = 0.0

        # ── Top speed bonus: ramp lên khi active, decay mượt khi tắt ───
        if self.nitro_active:
            ramp = min(1.0, self._nitro_hold_t / max(0.01, self._nitro_boost_time))
            target_bonus = ramp * self._nitro_boost
            self._nitro_top_bonus = physics.step_nitro_bonus(
                self._nitro_top_bonus, target_bonus, dt,
                full_boost=self._nitro_boost, boost_time=self._nitro_boost_time)
        else:
            self._nitro_top_bonus = physics.step_nitro_bonus(
                self._nitro_top_bonus, 0.0, dt,
                full_boost=self._nitro_boost, boost_time=self._nitro_boost_time)

        return self.max_speed + self._nitro_top_bonus

    # ── WAYPOINT ADVANCE — GIỮ NGUYÊN TỪ v1 ──────────────────────────
    def _advance_waypoint(self):
        n = len(self._wp)
        if n == 0:
            return
        for _ in range(3):
            ci  = self.wp_idx % n
            pi  = (self.wp_idx - 1) % n
            cx, cy   = self._wp[ci]
            px2, py2 = self._wp[pi]
            sdx = cx - px2;  sdy = cy - py2
            seg_len = math.hypot(sdx, sdy)
            dcx = self.x - cx;  dcy = self.y - cy
            d_cur = math.hypot(dcx, dcy)
            dot = dcx * sdx + dcy * sdy
            if (seg_len > 1 and dot >= 0) or d_cur < 90:
                self.wp_idx = (self.wp_idx + 1) % n
                self.wp_total += 1
            else:
                break

    def _check_lap(self, dt, now):
        if self.lap_debounce > 0:
            self.lap_debounce -= dt
        crossed = (
            self.lap_prev_y > _GATE_Y >= self.y
            and _GATE_X1 <= self.x <= _GATE_X2
            and self.velocity > 5.0
            and self.lap_debounce <= 0
        )
        if crossed:
            if not self.race_started:
                self.race_started = True
                self.race_start   = now
                self.lap_start    = now
                self.lap_debounce = 4.0
            else:
                self.lap_count += 1
                self.lap_times.append(now-self.lap_start)
                self.lap_start    = now
                self.lap_debounce = 4.0
                if self.lap_count >= _MAX_LAPS:
                    self.finished = True
        self.lap_prev_y = self.y

    # ── MOVE — GIỮ NGUYÊN TỪ v1 (delegate physics, không đụng) ───────
    def _move(self, dt):
        physics.move_car(self, dt)

    def _try_rotate(self, d_ang):
        r0 = math.radians(self.angle)
        fx, fy = math.cos(r0), math.sin(r0)
        half = self.car_h * 0.5
        piv = 0.8 if self.velocity >= 0 else -0.8
        piv_x = self.x + fx * half * piv
        piv_y = self.y + fy * half * piv
        na  = self.angle + d_ang
        r1  = math.radians(na)
        nfx, nfy = math.cos(r1), math.sin(r1)
        nx = piv_x - nfx * half * piv
        ny = piv_y - nfy * half * piv
        nose = (nx + nfx * half, ny + nfy * half)
        tail = (nx - nfx * half, ny - nfy * half)
        if physics.is_hard_wall(*nose) or physics.is_hard_wall(*tail):
            return False
        self.angle = na
        self.x, self.y = nx, ny
        return True

    # ── PLAYER UPDATE — v2: nitro hold/release qua LCTRL ─────────────
    def update_player(self, dt, now, keys, handbrake, want_nitro=False):
        """
        want_nitro: True khi player ĐANG GIỮ LCTRL (đọc bằng
        keys[pygame.K_LCTRL] ở map file — KHÔNG còn dùng KEYDOWN 1 lần
        như v1). "Giữ bao nhiêu tăng bấy nhiêu, nhả ra để tiết kiệm
        nitro" — đúng nghĩa đen: chỉ cần đổi nguồn bool truyền vào đây.
        """
        if self.finished:
            self.nitro_active = False    # tắt khói/lửa nitro ngay khi về đích
            if abs(self.velocity) > 0.5:
                sign = 1.0 if self.velocity>0 else -1.0
                self.velocity -= sign*60.0*dt
            else:
                self.velocity = 0.0
            self._move(dt)
            return

        # is_moving lấy TRƯỚC khi nitro cập nhật (đầu frame) — đúng brief
        # "xe đứng yên thì nitro không được tăng": ngưỡng nhỏ (>0.5 kph)
        # để tránh nhiễu số thực ở vận tốc ~0 chặn refill oan.
        is_moving = abs(self.velocity) > 0.5
        top = self._update_nitro(dt, want_nitro=want_nitro,
                                  drifting=handbrake, is_moving=is_moving)

        if keys[pygame.K_w]:
            # Vùng D (tiến) — đường cong S thật theo % top speed.
            # handbrake giảm nhẹ lực kéo (0.85x) như cũ, KHÔNG đổi hình
            # dạng cong, chỉ nhân thêm vào mult.
            physics.apply_throttle(self, dt, reverse=False,
                                    mult=(0.85 if handbrake else 1.0))
        elif keys[pygame.K_s]:
            if self.velocity > 3:
                # Đang chạy tiến + bấm S = PHANH CHỦ ĐỘNG → tuyến tính
                # cứng như cũ (hệ số góc riêng theo brake_power của xe).
                self.velocity -= self.brake_power*dt
            else:
                # Đã gần 0 hoặc đang lùi + giữ S = Vùng R (số lùi) —
                # cũng đi theo đường cong S, lật dấu (reverse=True).
                # 0.55 giữ nguyên như multiplier cũ của số R so với D.
                physics.apply_throttle(self, dt, reverse=True, mult=0.55)
        else:
            # KHÔNG bấm gì — nhả ga về 0, đi theo đường cong (chậm ở 2
            # đầu, hãm rõ ở giữa dải) — KHÔNG cắt cụt tuyến tính nữa.
            physics.release_throttle_decay(self, dt)

        if handbrake:
            sign = 1.0 if self.velocity>0 else (-1.0 if self.velocity<0 else 0.0)
            self.velocity -= sign*85.0*dt
            if abs(self.velocity)<1.0: self.velocity=0.0

        # ── Nitro tự đẩy xe (lực đẩy độc lập với W) ─────────────────────
        # Brief: "nitro có tác dụng làm lực đẩy khiến xe tự chạy kể cả
        # tốc độ 0 ... khi đã lên tốc độ cao thì nó cũng tăng đến max
        # theo bản chất xe thì sẽ thôi". Nghĩa là: bất kể có bấm W hay
        # không, hễ nitro_active thì velocity được KÉO dần lên top
        # (max_speed + bonus). Dùng acceleration y hệt ga thường (không
        # cộng 2 lần với nhánh W phía trên — nếu đang bấm W thì velocity
        # đã tăng rồi, đoạn này chỉ "kéo thêm" phần chưa đạt top).
        if self.nitro_active and self.velocity < top:
            self.velocity += self.acceleration * dt
            self.velocity = min(self.velocity, top)

        self.velocity = physics.clamp(self.velocity, -self.max_speed*0.4, top)

        self._cur_top = top
        steer_in = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
        physics.steer(self, steer_in, dt, handbrake=handbrake)

        grip = 3.5 if handbrake else 16.0
        dirdiff = physics.angle_diff(self.angle, self._move_dir)
        self._move_dir += dirdiff * min(1.0, grip * dt)

        self._move(dt)
        self._advance_waypoint()
        self._check_lap(dt, now)

        if abs(self.velocity) < 3 and keys[pygame.K_w]:
            self.player_stuck_t += dt
        else:
            self.player_stuck_t = 0.0

    # ── PATH HELPERS — GIỮ NGUYÊN TỪ v1 (sẽ dùng lại ở FUNCTION 11) ──
    def _lookahead_point(self, La):
        n = len(self._wp)
        idx = self.wp_idx % n
        px, py = self.x, self.y
        remain = La
        for _ in range(8):
            tx, ty = self._wp[idx]
            d = math.hypot(tx - px, ty - py)
            if d >= remain:
                t = remain / max(d, 1e-6)
                return px + (tx - px) * t, py + (ty - py) * t
            remain -= d
            px, py = tx, ty
            idx = (idx + 1) % n
        return self._wp[idx]

    def _path_curvature(self):
        """
        Đo độ cong đường sắp tới.

        SỬA (bug thật phát hiện lúc tích hợp FUNCTION 10/12, KHÔNG phải
        lúc viết ban đầu — hàm này tưởng "giữ nguyên từ v1, an toàn",
        nhưng mô phỏng 1 khúc cua bán kính 335px lộ ra: bản CŨ đo độ
        cong bằng cách nhảy qua SỐ WAYPOINT cố định (+2, +4 index) —
        nếu waypoint đặt DÀY (nhiều điểm/mét, như track thật thường
        làm), 2 điểm cách nhau vài index chỉ cách nhau VÀI PX, đo được
        góc bé tí dù cua thật rất gắt. Số liệu thật: đường tròn 335px
        (cua khá gắt) đo curvature=0.13 (gắn nhãn THẲNG, 100% tốc độ)
        khi waypoint đặt 6°/điểm, nhưng đo curvature=0.40 khi đặt thưa
        hơn (18°/điểm) — CÙNG 1 khúc cua vật lý, kết quả khác hẳn chỉ
        vì mật độ điểm. Bot phóng full speed vào cua thật rồi lao ra
        tường — đây mới là nguyên nhân CHÍNH của hiện tượng "bám mép
        tường" em phát hiện (không phải do logic vượt xe).

        CÁCH ĐO MỚI: dùng _lookahead_point() (đã có, đo theo KHOẢNG
        CÁCH THẬT tính bằng px dọc đường, không phải số waypoint) lấy 2
        điểm ở 2 mốc khoảng cách cố định (60px và 150px) phía trước —
        kết quả CHỈ phụ thuộc hình dạng đường thật, không phụ thuộc
        waypoint đặt dày hay thưa.
        """
        p0 = (self.x, self.y)
        p1 = self._lookahead_point(_sc(60))
        p2 = self._lookahead_point(_sc(150))
        a1 = math.degrees(math.atan2(p1[1]-p0[1], p1[0]-p0[0]))
        a2 = math.degrees(math.atan2(p2[1]-p1[1], p2[0]-p1[0]))
        bend = abs(physics.angle_diff(a2, a1))
        return min(bend / 90.0, 1.0)

    # =================================================================
    # AI BRAIN v2 — viết dần, từng FUNCTION
    # =================================================================

    # ── FUNCTION 01 — detect_wall_ahead() ────────────────────────────
    WALL_SCAN_DIST  = 160  # BASE ở MAP_SCALE=1.0 — scale thật tính lúc dùng, xem detect_wall_ahead()
    WALL_SCAN_STEP  = 8    # px — độ phân giải march mỗi ray
    WALL_SCAN_SPREAD = 42   # độ — góc lệch của ray left/right so với center, tăng rộng để nó quét góc

    def detect_wall_ahead(self, max_dist=None, step=None, spread_deg=None):
        """
        FUNCTION 01 — Phát hiện tường phía trước xe.

        Input (theo brief): x, y, angle — lấy trực tiếp từ self
          (self.x, self.y, self._move_dir — hướng DI CHUYỂN thực,
           không dùng self.angle để raycast vì khi drift 2 hướng lệch nhau).

        Method: cast 3 ray — left / center / right, march từng WALL_SCAN_STEP px
          tới khi đụng physics.is_hard_wall() hoặc hết max_dist.
          Đây là raycast THẬT (đi từng bước dò), không phải sample 1 điểm
          như v1 — để biết CHÍNH XÁC khoảng cách, phục vụ FUNCTION 02.

        Output: (wall_ahead: bool, rays: dict)
          wall_ahead = True nếu ray "center" đụng tường trong max_dist.
          rays = {"left": px_hoặc_None, "center": ..., "right": ...}
            None = ray đó đi hết max_dist không đụng tường (an toàn).
        """
        max_dist = max_dist if max_dist is not None else _sc(self.WALL_SCAN_DIST)
        step = step if step is not None else self.WALL_SCAN_STEP
        spread_deg = spread_deg if spread_deg is not None else self.WALL_SCAN_SPREAD

        # Dynamic spread: thu hẹp khi xe chạy nhanh, mở rộng khi chậm
        # Giữ an toàn: không nhỏ hơn 18°, không lớn hơn base
        try:
            top = max(getattr(self, '_cur_top', self.max_speed), 1.0)
            speed_ratio = min(1.0, abs(self.velocity) / top)
            shrink = speed_ratio * 10.0  # tối đa thu hẹp 10 độ
            spread_deg = max(18.0, spread_deg - shrink)
        except Exception:
            pass

        base = getattr(self, "_move_dir", self.angle)
        rays = {}
        for label, off in (("left", -spread_deg), ("center", 0.0), ("right", spread_deg)):
            fx, fy = physics.fwd_vec(base + off)
            hit = None
            d = step
            while d <= max_dist:
                px = self.x + fx * d
                py = self.y + fy * d
                if physics.is_hard_wall(int(px), int(py)):
                    hit = d
                    break
                d += step
            rays[label] = hit

        wall_ahead = rays["center"] is not None
        return wall_ahead, rays

    # ── FUNCTION 02 — choose_escape_direction() ──────────────────────
    def choose_escape_direction(self, rays, dt=0.0):
        """
        FUNCTION 02 — Chọn hướng lái an toàn nhất.

        Input: rays — dict trả về từ detect_wall_ahead() (BẮT BUỘC truyền
          vào, không tự gọi lại detect_wall_ahead ở đây — 1 hàm 1 trách
          nhiệm: 01 là "đo", 02 là "quyết định" từ số đã đo).

        Output: -1 (lái trái) / 0 (không cần né) / +1 (lái phải)

        Rule CỨNG, đúng yêu cầu brief "Never choose random direction":
          - Bên nào free space (khoảng cách tới tường) XA hơn → né về bên đó.
          - free space của ray None (không đụng) quy ước = WALL_SCAN_DIST
            (an toàn tối đa, không dùng infinity để còn so sánh được).
          - Trường hợp trái = phải y hệt (hiếm, sàn đối xứng) → KHÔNG random,
            dùng tie-break xác định: lệch theo hướng waypoint sắp tới
            (đường mình ĐANG ĐI vốn đã có chủ đích, không phải may rủi).
        """
        """
                Trả -1/0/+1. dt: thời gian frame hiện tại (giây) để giảm _escape_commit_t chính xác.
                """
        D = _sc(self.WALL_SCAN_DIST)
        left_d = rays["left"] if rays["left"] is not None else D
        right_d = rays["right"] if rays["right"] is not None else D

        # Giữ hướng escape ít nhất commit_time giây để tránh giật vô-lăng
        if getattr(self, "_escape_commit_t", 0.0) > 0.0:
            self._escape_commit_t = max(0.0, self._escape_commit_t - dt)
            return getattr(self, "_escape_dir", 0)

        # Cả 3 thoáng hẳn → không có gì để né
        if rays["center"] is None and left_d >= D and right_d >= D:
            self._escape_dir = 0
        elif left_d > right_d:
            self._escape_dir = -1
        elif right_d > left_d:
            self._escape_dir = 1
        else:
            # Tie-break: theo hướng waypoint kế tiếp
            gx, gy = self._lookahead_point(80)
            target_ang = math.degrees(math.atan2(gy - self.y, gx - self.x))
            diff = physics.angle_diff(target_ang, self.angle)
            self._escape_dir = 1 if diff >= 0 else -1

        # commit time (giữ hướng ít nhất)
        self._escape_commit_t = getattr(self, "_escape_commit_time", 1.0)
        return self._escape_dir

    # ── FUNCTION 03 — detect_stuck() ─────────────────────────────────
    STUCK_SPEED_THRESH = 10.0   # kph — dưới ngưỡng này coi là "có thể đang kẹt"
    STUCK_DIST_THRESH  = 20.0   # px  — phải dịch chuyển ít hơn mức này
    STUCK_TIME_THRESH  = 2.0    # giây — phải kẹt liên tục đủ lâu mới tính True

    def detect_stuck(self, dt):
        """
        FUNCTION 03 — Phát hiện xe bị kẹt (trapped).

        Điều kiện đúng theo brief:  speed < 10  VÀ  moved_distance < 20px
        LIÊN TỤC trong 2 giây — không phải chỉ 1 frame tức thời (1 frame
        speed thấp là chuyện thường khi vào cua/phanh, không phải kẹt).

        Cách đo "liên tục 2s": neo (_stuck_anchor) lại vị trí xe ngay tại
        thời điểm speed LẦN ĐẦU tụt dưới ngưỡng. Mỗi frame sau đó:
          - speed vượt ngưỡng trở lại → xe đang chạy ổn, HỦY anchor, không kẹt.
          - speed vẫn dưới ngưỡng → so quãng đường đã di chuyển so với anchor:
              * đã đủ STUCK_TIME_THRESH giây VÀ di chuyển < STUCK_DIST_THRESH
                → STUCK = True.
              * di chuyển đã vượt STUCK_DIST_THRESH (xe vẫn nhích đi được,
                kiểu đang rà tường chậm) → dời anchor sang vị trí mới,
                theo dõi tiếp cửa sổ kế — không báo kẹt oan.

        Output: True / False.
        Side effect: self.stuck_t = số giây đã neo (FUNCTION 04 dùng số
        này để biết kẹt bao lâu rồi, không phải gọi lại detect_stuck).
        """
        speed = abs(self.velocity)

        if speed >= self.STUCK_SPEED_THRESH:
            self._stuck_anchor = None
            self.stuck_t = 0.0
            return False

        if self._stuck_anchor is None:
            self._stuck_anchor = (self.x, self.y)
            self.stuck_t = 0.0
            return False

        ax, ay = self._stuck_anchor
        moved = math.hypot(self.x - ax, self.y - ay)
        self.stuck_t += dt

        if moved >= self.STUCK_DIST_THRESH:
            # Vẫn nhích đi được — không phải kẹt, theo dõi cửa sổ tiếp theo
            self._stuck_anchor = (self.x, self.y)
            self.stuck_t = 0.0
            return False

        return self.stuck_t >= self.STUCK_TIME_THRESH

    # ── FUNCTION 04 — recover_from_stuck() ───────────────────────────
    # Giới hạn thời gian lùi động — giúp xe phản ứng tự nhiên hơn
    # MIN: luôn lùi ít nhất chừng này để chắc chắn thoát khỏi pixel kẹt
    # MAX: nếu vẫn chưa thoát, lùi tối đa chừng này rồi chuyển sang tiến
    # Khoảng 1.5 → 3.5 giây là cân bằng: đủ để thoát, không gây chậm nhịp đua
    RECOVER_REVERSE_MIN = 1.5
    RECOVER_REVERSE_MAX = 3.5
    RECOVER_FORWARD_TIME = 0.8  # tiến nhẹ sau lùi, không quá lâu
    RECOVER_REVERSE_SPEED = -25.0  # kph — lùi đủ mạnh, không quá gắt
    RECOVER_FORWARD_SPEED = 16.0  # kph — tiến nhẹ sau lùi, chưa full gas ngay

    def recover_from_stuck(self, dt):
        """
        FUNCTION 04 — Thoát kẹt đơn giản (simple trap).

        Quy trình:
            - Pha "reverse": lùi full lock một hướng cố định, ít nhất MIN giây,
            nếu thoát sớm thì chuyển ngay sang forward, nếu chưa thoát thì
            lùi tối đa MAX giây rồi chuyển sang forward.
            - Pha "forward": tiến thẳng nhẹ nhàng trong RECOVER_FORWARD_TIME giây,
            sau đó trả quyền lại cho brain_update().

        Hướng bẻ lái ở pha reverse: tái sử dụng FUNCTION 01 + 02 để chọn,
        KHÔNG random. Nếu choose_escape_direction trả 0 thì dùng waypoint
        kế tiếp làm tie-break.
        """
        if self._recover_phase is None:
            _, rays = self.detect_wall_ahead()
            self._recover_dir = self.choose_escape_direction(rays)
            if self._recover_dir == 0:
                gx, gy = self._lookahead_point(80)
                target_ang = math.degrees(math.atan2(gy - self.y, gx - self.x))
                diff = physics.angle_diff(target_ang, self.angle)
                self._recover_dir = 1 if diff >= 0 else -1
            self._recover_phase = "reverse"
            self._recover_t = 0.0

        self._recover_t += dt

        if self._recover_phase == "reverse":
            self.velocity = self.RECOVER_REVERSE_SPEED
            physics.steer(self, self._recover_dir, dt)  # full lock, hướng cố định

            # Nếu đã thoát khỏi tường → chuyển ngay sang forward
            if not physics.is_hard_wall(int(self.x), int(self.y)) and self._recover_t >= self.RECOVER_REVERSE_MIN:
                self._recover_phase = "forward"
                self._recover_t = 0.0

            # Nếu chưa thoát, nhưng đã vượt quá MAX → chuyển sang forward
            elif self._recover_t >= self.RECOVER_REVERSE_MAX:
                self._recover_phase = "forward"
                self._recover_t = 0.0

            return True

        if self._recover_phase == "forward":
            self.velocity = self.RECOVER_FORWARD_SPEED
            physics.steer(self, 0.0, dt)  # tiến thẳng, hết lái lock
            if self._recover_t >= self.RECOVER_FORWARD_TIME:
                self._recover_phase = None
                self._recover_t = 0.0
                self._recover_dir = 0
                return False
            return True

        # Phòng hờ state lạ — reset an toàn
        self._recover_phase = None
        return False

    @property
    def is_recovering(self):
        """Tiện ích cho FUNCTION 12: biết đang giữa quy trình recover hay không."""
        return self._recover_phase is not None

    # ── FUNCTION 05 — find_safe_waypoint() ───────────────────────────
    def _find_fallback_spot_40px(self):
        """
        Helper nội bộ (KHÔNG thuộc 12 FUNCTION) — CHỈ dùng khi
        find_safe_waypoint() (FUNCTION 05) không tìm được waypoint hợp
        lệ nào (cực hiếm — toàn bộ track gần đó coi như "hỏng dữ
        liệu"). Theo yêu cầu: thử respawn CÁCH vị trí hiện tại 40px,
        dò đủ 8 hướng la bàn, trả về điểm ĐẦU TIÊN không nằm trong
        tường và không offroad — TUYỆT ĐỐI không trả về 1 điểm vẫn kẹt
        tường. Trả None nếu cả 8 hướng đều thất bại (cực hiếm).
        """
        OFFSET = 40.0
        for goc in (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0):
            fx, fy = physics.fwd_vec(goc)
            nx = self.x + fx * OFFSET
            ny = self.y + fy * OFFSET
            if (not physics.is_hard_wall(int(nx), int(ny))
                    and not physics.is_offroad(int(nx), int(ny))):
                return nx, ny
        return None

    def find_safe_waypoint(self):
        """
        FUNCTION 05 — Tìm waypoint hồi phục GẦN NHẤT và HỢP LỆ.

        Điều kiện hợp lệ (ĐÚNG theo brief — "must be on road, not inside
        wall, not outside track"):
          - không nằm trong tường cứng       → NOT physics.is_hard_wall()
          - không offroad / không ngoài map  → NOT physics.is_offroad()
            (is_offroad() đã tự bao gồm "outside track": ngoài biên map
            trả True luôn, xem twodss_physics.py — không cần check riêng).

        Cách đảm bảo đúng nghĩa "NEAREST": tính khoảng cách thật từ xe
        tới TẤT CẢ waypoint, sort tăng dần theo khoảng cách, trả waypoint
        hợp lệ ĐẦU TIÊN gặp được — đây chính là cái gần nhất theo định
        nghĩa, không suy luận qua chỉ số index (2 waypoint gần index có
        thể nằm xa nhau thật ở đoạn track gấp khúc/giao nhau).

        Output: index (int) trong self._wp. Trả None nếu KHÔNG có
        waypoint nào hợp lệ (toàn bộ track hỏng dữ liệu — cực hiếm),
        để teleport_recovery() tự quyết fallback.
        """
        wp = self._wp
        n = len(wp)
        if n == 0:
            return None

        order = sorted(
            range(n),
            key=lambda i: (wp[i][0] - self.x) ** 2 + (wp[i][1] - self.y) ** 2,
        )
        for i in order:
            wx, wy = wp[i]
            if not physics.is_hard_wall(wx, wy) and not physics.is_offroad(wx, wy):
                return i
        return None

    # ── FUNCTION 06 — teleport_recovery() ────────────────────────────
    TELEPORT_TRIGGER_TIME   = 6.0   # giây — ĐÚNG brief ("stuck_time > 6 seconds")
    TELEPORT_DIST_THRESH    = 120.0 # px — BUG THẬT phát hiện lúc test
                                      # tích hợp FUNCTION 12: lúc đầu để
                                      # 30px (chỉ hơi rộng hơn 20px của
                                      # FUNCTION 03), nhưng mỗi VÒNG
                                      # recover_from_stuck() (reverse 1.5s
                                      # + forward 0.8s) tự đẩy xe dao động
                                      # 1 đoạn ĐỦ VƯỢT 30px trong CÙNG 1
                                      # cái hốc tường — khiến đồng hồ 6s
                                      # bị RESET mỗi ~2-3s, KHÔNG BAO GIỜ
                                      # chạm mốc teleport (xem log test:
                                      # xe lùi/tiến lặp ở x≈373-387 suốt
                                      # 14s mà đồng hồ cứ về 0). Đây CHÍNH
                                      # LÀ lỗi "vòng lặp vô hạn ở góc
                                      # tường" mà FUNCTION 06 phải chặn —
                                      # nếu ngưỡng quá nhỏ, FUNCTION 06 tự
                                      # vô hiệu hóa chính nó. 120px (≈ 1
                                      # lần WALL_SCAN_DIST) đủ rộng để xe
                                      # dao động trong CÙNG 1 hốc không bị
                                      # tính nhầm là "đã thoát", chỉ reset
                                      # khi xe THẬT SỰ rời hẳn khu vực kẹt.
    TELEPORT_NOCOLLIDE_TIME = 0.5   # giây — ĐÚNG brief bước 5
    TELEPORT_BLINK_COUNT    = 5     # ĐÚNG brief bước 6 ("Blink vehicle 5 times")
    TELEPORT_BLINK_PERIOD   = 0.1   # giây/nhịp — KHÔNG có trong brief (brief chỉ
                                      # nói "5 times" không nói tốc độ), chọn 0.1s
                                      # để 5 nhịp gọn trong ~0.5s = đúng khung
                                      # TELEPORT_NOCOLLIDE_TIME ở bước 5.

    def teleport_recovery(self, dt):
        """
        FUNCTION 06 — Ultimate recovery: chặn vòng lặp kẹt tường vô hạn.

        ĐIỀU KIỆN (đúng brief): stuck_time > 6 giây LIÊN TỤC.
        "stuck_time" ở đây là self.wall_stuck_t — đồng hồ kẹt DÀI HẠN,
        CỐ Ý tách riêng khỏi self.stuck_t (FUNCTION 03). Đồng hồ này CHỈ
        dựa vào QUÃNG ĐƯỜNG THẬT đã di chuyển so với 1 điểm neo
        (_teleport_anchor), TUYỆT ĐỐI KHÔNG dựa vào speed — xem giải
        thích kỹ ở trong thân hàm (bug thật phát hiện lúc test FUNCTION
        12: recover_from_stuck() tự đặt velocity cao trong lúc nó chạy,
        nếu teleport_recovery() nhìn speed mà đoán "đã thoát" thì sẽ bị
        chính FUNCTION 04 đánh lừa, reset đồng hồ liên tục, KHÔNG BAO
        GIỜ chạm mốc 6s — đúng pattern lặp vô hạn ở ảnh 2/3 em gửi).

        PROCEDURE — đủ 6 bước đúng brief:
          1. find_safe_waypoint()      (FUNCTION 05, tái dùng — không viết lại)
          2. Teleport xe tới waypoint đó
          3. velocity = 0
          4. angle quay về hướng waypoint KẾ TIẾP (xuất phát đúng chiều đua)
          5. Disable collision 0.5s    → set self._no_collide_t
          6. Blink 5 lần               → set self._blink_count/_blink_t

        LƯU Ý TÍCH HỢP (chưa làm ở bước này, cần xác nhận riêng):
          - Bước 5 cần handle_car_collisions()/handle_capsule_collisions()
            trong twodss_physics.py tự kiểm tra self._no_collide_t > 0 và
            BỎ QUA xe đó khi resolve va chạm — file physics.py hiện CHƯA
            có check này (physics.py em nói giữ nguyên phần wall-physics,
            nhưng đây là 1 dòng thêm ở collision function, không đụng gì
            tới wall-align physics đã thống nhất giữ nguyên).
          - Bước 6 cần render loop (track-greenwood-circuit.py, hàm
            render_world) tự đọc _blink_count/_blink_t để ẩn/hiện sprite —
            cũng CHƯA nối, vì đó thuộc file map/track.
          Racer-side (bước 1-4 + đặt cờ cho 5-6) đã đầy đủ và test được
          ngay; phần render/collision sẽ nối khi mình đụng tới 2 file đó.

        Gọi MỖI FRAME (như FUNCTION 04). Trả về:
          True  — vừa thực hiện teleport ở frame này.
          False — chưa đủ điều kiện, không làm gì.
        """
        # GHI CHÚ QUAN TRỌNG (bug thật phát hiện lúc test FUNCTION 12):
        # KHÔNG check speed ở đây để quyết định "xe đang chạy bình
        # thường, không kẹt". Lý do: recover_from_stuck() (FUNCTION 04)
        # TỰ ĐẶT velocity cao trong lúc nó chạy (-25 lúc lùi, +20 lúc
        # tiến) — nếu teleport_recovery() nhìn speed cao mà coi là "thoát
        # rồi", nó sẽ liên tục bị FUNCTION 04 đánh lừa: mỗi vòng
        # reverse/forward lại làm speed v passable threshold rồi reset
        # đồng hồ — kẹt mãi mà KHÔNG BAO GIỜ chạm mốc 6s (đã thấy tận
        # mắt qua log test: xe lùi/tiến lặp suốt 14s, đồng hồ reset liên
        # tục đúng lúc velocity=-25). CHỈ dựa vào QUÃNG ĐƯỜNG THẬT ĐÃ DI
        # CHUYỂN (so với anchor) — đây mới là thước đo đúng "xe có thật
        # sự thoát khỏi khu vực kẹt hay không", không quan tâm xe đang
        # lệnh tốc độ bao nhiêu.
        if self._teleport_anchor is None:
            self._teleport_anchor = (self.x, self.y)
            self.wall_stuck_t = 0.0
            return False

        ax, ay = self._teleport_anchor
        moved = math.hypot(self.x - ax, self.y - ay)
        self.wall_stuck_t += dt

        if moved >= self.TELEPORT_DIST_THRESH:
            self._teleport_anchor = (self.x, self.y)
            self.wall_stuck_t = 0.0
            return False

        if self.wall_stuck_t <= self.TELEPORT_TRIGGER_TIME:
            return False

        # ── Đủ điều kiện — thực hiện PROCEDURE 6 bước ──────────────────
        n = len(self._wp)
        if n == 0:
            return False   # không có waypoint nào — không thể teleport có ý nghĩa

        safe_idx = self.find_safe_waypoint()                       # bước 1
        if safe_idx is not None:
            wx, wy = self._wp[safe_idx]
        else:
            # BỔ SUNG theo yêu cầu: find_safe_waypoint() KHÔNG tìm được
            # waypoint hợp lệ nào (cực hiếm) -> thử respawn CÁCH vị trí
            # đang kẹt 40px, dò 8 hướng la bàn, lấy điểm ĐẦU TIÊN không
            # nằm trong tường/offroad. KHÔNG được phép respawn vào 1
            # điểm vẫn kẹt tường — đây là yêu cầu rõ ràng, không phải
            # cứ lùi 40px bất kỳ hướng nào cũng được.
            fallback = self._find_fallback_spot_40px()
            if fallback is not None:
                wx, wy = fallback
                safe_idx = min(range(n), key=lambda i:
                                (self._wp[i][0]-wx)**2 + (self._wp[i][1]-wy)**2)
            else:
                safe_idx = self.wp_idx % n   # cực hiếm — cả waypoint lẫn 8 hướng 40px đều thất bại
                wx, wy = self._wp[safe_idx]

        self.x, self.y = float(wx), float(wy)                      # bước 2
        self.velocity  = 0.0                                       # bước 3

        next_idx = (safe_idx + 1) % n
        nx, ny = self._wp[next_idx]
        self.angle     = math.degrees(math.atan2(ny - wy, nx - wx))  # bước 4
        self._move_dir = self.angle

        self.wp_idx        = safe_idx
        self._no_collide_t = self.TELEPORT_NOCOLLIDE_TIME           # bước 5 (cờ)
        self._blink_count  = self.TELEPORT_BLINK_COUNT              # bước 6 (cờ)
        self._blink_t       = 0.0

        # Reset toàn bộ state kẹt — xe "tái sinh" sạch, tránh dính lại
        # ngay quy trình recover/teleport ở frame kế tiếp.
        self._teleport_anchor = None
        self.wall_stuck_t      = 0.0
        self._stuck_anchor     = None
        self.stuck_t           = 0.0
        self._recover_phase    = None
        self._recover_t        = 0.0
        self._cached_normal    = None
        self._wall_contact_t   = 0.0

        return True

    # ── FUNCTION 07 — detect_car_ahead() ─────────────────────────────
    CAR_DETECT_RANGE_MIN = 120   # px — ĐÚNG brief ("Range: 120 to 180 px")
    CAR_DETECT_RANGE_MAX = 180   # px
    CAR_DETECT_LATERAL   = 60    # px — KHÔNG có trong brief (brief chỉ cho
                                    # khoảng dọc). Tự thêm cone ngang này vì
                                    # nếu không có, 1 xe ở LANE KHÁC nhưng
                                    # cách đường chim bay 150px vẫn bị tính
                                    # nhầm là "ahead" — 60px ≈ bề ngang 1 xe
                                    # + nửa khoảng lane, đủ để chỉ bắt xe
                                    # thật sự cùng làn/sắp cùng làn.

    def detect_car_ahead(self, others):
        """
        FUNCTION 07 — Phát hiện xe CHẬM HƠN phía trước.

        Input: others — list TẤT CẢ racer khác (không cần tự loại self,
          hàm tự skip nếu lỡ truyền cả self vào).

        Range ĐÚNG brief (120-180px) đo theo PROJECTION lên hướng di
        chuyển (forward), không phải khoảng cách đường chim bay — 1 xe
        nằm CHÉO phía trước-bên cũng phải tính đúng khoảng cách dọc thật,
        không bị khoảng lệch ngang làm sai số. Cộng thêm cone ngang
        CAR_DETECT_LATERAL để loại xe ở làn quá xa (xem giải thích trên).

        Lọc "CHẬM HƠN" — đúng Purpose của brief: chỉ tính xe có
        velocity < self.velocity. Xe nhanh hơn/ngang mình tự rời xa,
        không phải đối tượng cần né/vượt.

        Output: (target: Racer | None, forward_dist: float | None).
        Nhiều xe cùng thỏa điều kiện → chọn xe GẦN NHẤT (forward_dist nhỏ
        nhất) — đây là xe cần phản ứng trước tiên.
        """
        base = getattr(self, "_move_dir", self.angle)
        fx, fy = physics.fwd_vec(base)
        rx, ry = -fy, fx   # vector ngang (right) — cùng quy ước FUNCTION 01/02

        best, best_dist = None, None
        for o in others:
            if o is self:
                continue
            dx = o.x - self.x
            dy = o.y - self.y
            fwd = dx * fx + dy * fy
            lat = dx * rx + dy * ry
            if not (_sc(self.CAR_DETECT_RANGE_MIN) <= fwd <= _sc(self.CAR_DETECT_RANGE_MAX)):
                continue
            if abs(lat) > _sc(self.CAR_DETECT_LATERAL):
                continue
            if o.velocity >= self.velocity:
                continue
            if best is None or fwd < best_dist:
                best, best_dist = o, fwd

        return best, best_dist

    # ── FUNCTION 08 — choose_overtake_side() ─────────────────────────
    OVERTAKE_SCAN_DIST    = 90   # px — KHÔNG có trong brief, tự chọn ~1.5
                                    # thân xe để đủ "thấy" lề/giải phân cách
                                    # khi đánh giá có nên đổi lane không.
    OVERTAKE_BLOCK_RADIUS = 50   # px — coi 1 bên là "đã có xe chiếm" nếu
                                    # tâm 1 xe khác (không phải target) nằm
                                    # trong bán kính này quanh điểm đang xét.
    OVERTAKE_MIN_GAP      = 50   # px — KHÔNG có trong brief. BẮT BUỘC thêm
                                    # sau khi test phát hiện bug: nếu chỉ so
                                    # "free space trái > phải" mà không có
                                    # sàn tối thiểu, 1 khe 30px (hẹp hơn nửa
                                    # thân xe ~45px) vẫn bị coi là "trống" và
                                    # chọn đổi lane vào đó → đâm tường ngay.
                                    # 50px ≈ nửa chiều ngang xe (car_w mặc
                                    # định 90px / 2) — dưới mức này KHÔNG
                                    # đủ chỗ thật, phải coi như bị chặn.
    OVERTAKE_TIE_MARGIN   = 25   # px — BUG THẬT phát hiện qua mô phỏng 1
                                    # khúc cua dài + 1 xe chậm bám phía
                                    # trước liên tục: bán kính xe trôi từ
                                    # đường tâm (335px) lên tới SÁT TƯỜNG
                                    # NGOÀI (442px, tường ở 450px!). Nguyên
                                    # nhân: NGOÀI CUA LUÔN rộng hơn TRONG
                                    # CUA về mặt hình học, nên mỗi frame hàm
                                    # này đều chọn "bên ngoài" — lặp lại
                                    # hàng trăm frame liên tục thành trôi
                                    # dạt tích lũy ra sát tường ngoài (đúng
                                    # hiện tượng "xe không thích đi vào
                                    # trong track" em phát hiện). Fix: nếu 2
                                    # bên không khác biệt RÕ RÀNG (chưa đủ
                                    # 25px), coi như "không có lý do thật để
                                    # đổi lane" → trả 0, để follow_path() tự
                                    # giữ xe ở giữa đường — không ép chọn 1
                                    # bên chỉ vì nó nhích hơn vài px.

    def choose_overtake_side(self, target, others):
        """
        FUNCTION 08 — Chọn bên vượt (LEFT/RIGHT).

        Input: target (từ FUNCTION 07 — xe đang chặn đường), others (để
          kiểm tra có xe THỨ 3 nào đã chiếm sẵn bên mình định vượt không,
          ví dụ tình huống 3 xe dồn 1 cụm như ảnh 2/3 em gửi).

        Check ĐỦ CHỖ mỗi bên bằng march-raycast VUÔNG GÓC (90°) với
        hướng di chuyển — TÁI DÙNG kỹ thuật march của FUNCTION 01. 1 bên
        bị loại (free=0, "không đi được") nếu: có xe khác chiếm
        (OVERTAKE_BLOCK_RADIUS) HOẶC khe hở hẹp hơn OVERTAKE_MIN_GAP.

        ĐÃ ĐỔI TIÊU CHÍ CHỌN BÊN (bug thật phát hiện qua mô phỏng 1 khúc
        cua dài + 1 xe chậm bám phía trước liên tục — xem log test):
        bản ĐẦU dùng "bên nào RỘNG HƠN thắng" (đúng câu chữ brief), NHƯNG
        trên 1 khúc cua, NGOÀI CUA LUÔN rộng hơn TRONG CUA về mặt hình
        học — nên hàm cứ chọn ngoài cua MỖI FRAME, lặp lại liên tục
        thành trôi dạt tích lũy ra SÁT TƯỜNG NGOÀI (bán kính xe đo được
        từ 335px lên tới 442px khi tường ngoài ở 450px). Thêm ngưỡng
        "khác biệt nhỏ thì bỏ qua" (OVERTAKE_TIE_MARGIN) KHÔNG đủ, vì
        khác biệt trong/ngoài cua là khác biệt HÌNH HỌC THẬT, không phải
        nhiễu — test lại vẫn drift y như cũ.

        TIÊU CHÍ MỚI: ưu tiên bên TRÙNG VỚI HƯỚNG ĐƯỜNG ĐUA đang muốn đi
        (so điểm nhắm phía trước — _lookahead_point, giống FUNCTION 11
        dùng — đường rẽ trái thì ưu tiên trái, rẽ phải thì ưu tiên phải),
        CHỈ kiểm tra "đủ chỗ hay không" (qua OVERTAKE_MIN_GAP) — KHÔNG
        còn so "bên nào rộng hơn" nữa. Nếu hướng đường đua muốn đi không
        đủ chỗ (bị chặn/hẹp), mới đánh fallback dùng bên còn lại. Cách
        này giữ xe bám SÁT Ý ĐỊNH ĐƯỜNG ĐUA thay vì bị kéo lệch ra chỗ
        "trống nhất" — đúng hướng sửa em đề xuất (ưu tiên giữa track,
        không lao ra mép chỉ vì mép đó trống hơn).

        Output: -1 (LEFT) / +1 (RIGHT) / 0 — không bên nào đủ chỗ, đừng
        vượt lúc này (để FUNCTION 09 tự fallback sang giảm tốc).
        """
        base = getattr(self, "_move_dir", self.angle)
        free = {}
        for label, off in (("left", -90.0), ("right", 90.0)):
            fx, fy = physics.fwd_vec(base + off)
            hit = _sc(self.OVERTAKE_SCAN_DIST)
            d = self.WALL_SCAN_STEP
            while d <= _sc(self.OVERTAKE_SCAN_DIST):
                px = self.x + fx * d
                py = self.y + fy * d
                if physics.is_hard_wall(int(px), int(py)):
                    hit = float(d)
                    break
                d += self.WALL_SCAN_STEP

            mid_x = self.x + fx * (hit * 0.6)
            mid_y = self.y + fy * (hit * 0.6)
            car_blocked = False
            for o in others:
                if o is self or o is target:
                    continue
                if math.hypot(o.x - mid_x, o.y - mid_y) < _sc(self.OVERTAKE_BLOCK_RADIUS):
                    car_blocked = True
                    break
            too_narrow = hit < _sc(self.OVERTAKE_MIN_GAP)
            free[label] = 0.0 if (car_blocked or too_narrow) else hit

        left_ok  = free["left"]  > 0.0
        right_ok = free["right"] > 0.0
        if not left_ok and not right_ok:
            return 0

        # Bên mà ĐƯỜNG ĐUA đang muốn đi (KHÔNG phải bên rộng hơn).
        gx, gy = self._lookahead_point(80)
        target_ang = math.degrees(math.atan2(gy - self.y, gx - self.x))
        diff = physics.angle_diff(target_ang, self.angle)   # >0: đường muốn rẽ PHẢI
        path_wants_right = diff >= 0

        if path_wants_right and right_ok:
            return 1
        if (not path_wants_right) and left_ok:
            return -1

        # Hướng đường đua muốn đi không đủ chỗ -> đánh fallback bên còn lại
        if right_ok:
            return 1
        if left_ok:
            return -1
        return 0

    # ── FUNCTION 09 — avoid_car_collision() ──────────────────────────
    SAFETY_DISTANCE = 150   # px — brief chỉ nói "distance < safety_distance"
                              # không cho số cụ thể. Chọn giữa khoảng detect
                              # (120-180px) của FUNCTION 07: đủ sớm để brake/
                              # đổi lane êm, không phải phản ứng giật ở 120px
                              # (lúc đó coi như đã cận kề thật).
    CROWD_RADIUS = 140  # px (base, scale qua _sc khi dùng)
    CROWD_COUNT_FORCE_YIELD = 2  # >=2 xe khác (ngoài target) quanh đây -> nhường hẳn

    def _is_crowded(self, others, exclude):
        n, R = 0, _sc(self.CROWD_RADIUS)
        for o in others:
            if o is self or o in exclude:
                continue
            if (o.x - self.x) ** 2 + (o.y - self.y) ** 2 <= R * R:
                n += 1
                if n >= self.CROWD_COUNT_FORCE_YIELD:
                    return True
        return False

    def avoid_car_collision(self, target, distance, others, dt):
        """
        FUNCTION 09 — Ngăn va chạm từ phía sau (rear-end).

        Input: target + distance — LẤY TRỰC TIẾP từ FUNCTION 07 (KHÔNG
          gọi lại detect_car_ahead — đúng nguyên tắc liên kết, 1 lần đo
          dùng lại nhiều nơi). others — truyền tiếp cho FUNCTION 08.

        Đây là hàm "ACT" (giống FUNCTION 04/06: trực tiếp sửa
        velocity/steer), KHÁC FUNCTION 07/08 (chỉ "đo"/"quyết định" rồi
        trả giá trị) — vì Purpose của brief là "Actions: reduce throttle
        OR change lane", tức bản thân hàm phải THỰC HIỆN hành động.

        Điều kiện đúng brief: distance < SAFETY_DISTANCE.
        Hành động — đúng 2 lựa chọn brief:
          - change lane: nếu choose_overtake_side() (FUNCTION 08, tái
            dùng) tìm được bên trống → nudge steer NHẸ (0.6, không full
            lock — đổi lane phải êm, khác hẳn thoát kẹt khẩn cấp của
            FUNCTION 04) về bên đó.
          - reduce throttle: nếu KHÔNG bên nào trống → giảm tốc, bám theo
            90% tốc độ xe trước (chừa biên an toàn, không bám sát 100%).

        Output (ĐỔI so với bản đầu — lý do xem ghi chú dưới): chuỗi mô tả
          ĐÚNG hành động đã làm, không chỉ True/False nữa:
            "lane_change" — đã đổi lane (đã steer rồi, brain_update() KHÔNG
                            được gọi follow_path()/steer thêm lần nữa).
            "brake"       — đã giảm tốc, CHƯA hề đụng tới steer (brain_update()
                            VẪN PHẢI tự gọi follow_path() để xe có lái).
            None          — distance >= SAFETY_DISTANCE, chưa cần làm gì.
          (Lúc viết brain_update() — FUNCTION 12 — mới phát hiện ra: nếu
          chỉ trả True/False thì brain_update() KHÔNG BIẾT được hành động
          vừa rồi có steer hay chưa, dễ gọi follow_path() chồng lên lane-
          change làm 2 lệnh lái đánh nhau, hoặc bỏ sót không lái gì khi
          chỉ brake xong. Đổi sang trả chữ rõ nghĩa để hết mơ hồ.)
        """
        near = (target is not None and distance is not None
                and distance < _sc(self.SAFETY_DISTANCE) * AVOID_RADIUS_BOOST)
        if near:
            self._yield_hold_t = 0.6
        else:
            self._yield_hold_t = max(0.0, self._yield_hold_t - dt)
        if target is None or self._yield_hold_t <= 0.0:
            return None

        side = self.choose_overtake_side(target, others)
        if self._is_crowded(others, exclude={target}):
            cap = max(5.0, abs(target.velocity) * 0.85)
            if self.velocity > cap:
                self.velocity -= self.brake_power * dt
            return "brake"

        if side != 0:
            physics.steer(self, side * 0.6, dt)
            # Nitro công bằng: bot dùng ĐÚNG CÙNG luật với player (xem
            # _try_activate_nitro()) — gắn vào đúng lúc xe QUYẾT ĐỊNH
            # vượt, vì lý do nitro tồn tại (theo brief mới) là "để vượt
            # qua", không phải dùng tùy hứng bất kỳ lúc nào.
            self._try_activate_nitro()
            return "lane_change"

        cap = max(5.0, abs(target.velocity) * 0.9)
        if self.velocity > cap:
            self.velocity -= self.brake_power * dt
        return "brake"

    # Thời gian bot "giữ" nitro mỗi lần kích — mô phỏng player giữ LCTRL
    # một khoảng vừa đủ để vượt xe, KHÔNG giữ tới khi cạn xăng (player
    # thật cũng nhả ra giữa chừng để tiết kiệm, bot nên hành xử giống).
    BOT_NITRO_HOLD_SEC = 1.6

    def _try_activate_nitro(self):
        """
        Helper nội bộ (KHÔNG thuộc 12 FUNCTION) — bot KHÔNG có khái niệm
        "giữ phím" như player, nên mô phỏng bằng 1 đồng hồ: gọi hàm này
        khi bot QUYẾT ĐỊNH vượt xe (FUNCTION 09) sẽ "bắt đầu giữ" trong
        BOT_NITRO_HOLD_SEC giây rồi tự nhả — ĐÚNG nghĩa "nitro cũng góp
        phần để emergency pass position", không dùng tùy hứng lúc khác.

        Không còn cooldown (v1 có CD=15s, v2 BỎ — hết nitro thì nạp lại
        ngay, đúng luật mới). Điều kiện duy nhất: còn nitro_amount > 0,
        chưa giữ sẵn, chưa về đích.

        Output: True nếu vừa bắt đầu giữ, False nếu chưa đủ điều kiện.
        """
        if (self._bot_nitro_release_t <= 0.0
                and self.nitro_amount > 0 and not self.finished):
            self._bot_nitro_release_t = self.BOT_NITRO_HOLD_SEC
            return True
        return False

    def _bot_want_nitro(self, dt) -> bool:
        """
        Trả về True trong lúc đồng hồ BOT_NITRO_HOLD_SEC còn chạy (mô
        phỏng "đang giữ phím"), tự đếm lùi và hết hạn thì nhả — gọi mỗi
        frame ở brain_update() TRƯỚC _update_nitro(), y như việc player
        đọc keys[K_LCTRL] mỗi frame ở map file.
        """
        if self._bot_nitro_release_t > 0.0:
            self._bot_nitro_release_t = max(0.0, self._bot_nitro_release_t - dt)
            return True
        return False

    # ── FUNCTION 10 — compute_target_speed() ─────────────────────────
    # CÁCH TÍNH: chia độ cong đường thành 4 MỨC RÕ RÀNG, mỗi mức 1 % CỐ
    # ĐỊNH — KHÔNG dùng công thức cong/mượt (v1 dùng top*(1-curve*0.58),
    # nhìn số ra không biết xe đang "ở mức nào"). Lợi ích của cách chia
    # mức: debug dễ — in ra "mức 3 = CUA TRUNG = 60%" là hiểu ngay, không
    # cần tính lại công thức trong đầu.
    SPEED_CURVE_STRAIGHT_MAX = 0.25   # curve dưới mức này = coi là ĐƯỜNG THẲNG
    SPEED_CURVE_LIGHT_MAX    = 0.50   # curve dưới mức này = CUA NHẸ
    SPEED_CURVE_MEDIUM_MAX   = 0.75   # curve dưới mức này = CUA TRUNG, từ đây lên = CUA GẮT

    SPEED_PERCENT_STRAIGHT = 1.00   # ĐÚNG brief: "Straight road: 100%"
    SPEED_PERCENT_LIGHT    = 0.80   # ĐÚNG brief: "Light corner: 80%"
    SPEED_PERCENT_MEDIUM   = 0.60   # ĐÚNG brief: "Medium corner: 60%"
    SPEED_PERCENT_SHARP    = 0.40   # ĐÚNG brief: "Sharp corner: 40%"
    SPEED_PERCENT_WALL     = 0.30   # ĐÚNG brief: "Wall nearby: 30%"

    def compute_target_speed(self, top_speed, wall_ahead=None, others=None):
        """
        FUNCTION 10 — Quyết định TỐC ĐỘ MONG MUỐN (target speed).

        Hàm này CHỈ TRẢ VỀ 1 SỐ — không tự sửa self.velocity. Việc tăng/
        giảm máy thật để bám theo số này là việc của brain_update()
        (FUNCTION 12), giữ đúng "1 hàm 1 trách nhiệm".

        3 input ĐÚNG brief: "road curvature, wall proximity, traffic" —
        làm đúng 4 bước sau, theo thứ tự, KHÔNG gộp chung 1 dòng:

        BƯỚC 1 — đọc độ cong đường sắp tới.
          Dùng _path_curvature() có sẵn (curve=0.0 thẳng, 1.0 cua gắt
          nhất) — KHÔNG viết lại logic đo cua ở đây, chỉ lấy kết quả.

        BƯỚC 2 — so curve với 4 MỨC ở trên, chọn % tương ứng.
          So bằng if/elif tuần tự từ thấp lên cao — đọc 1 lần là hiểu,
          không cần tính toán gì thêm trong đầu.

        BƯỚC 3 — nếu có tường gần phía trước, ĐÈ % xuống 30% NGAY,
          không cộng/trừ thêm với % đã chọn ở bước 2. "Có tường" là 1
          MỨC RIÊNG theo brief, không phải hệ số nhân chồng lên cua.

        BƯỚC 4 — nếu phía trước có xe chậm hơn (traffic), KHÔNG để
          target_speed vượt quá 90% tốc độ xe đó. Logic đơn giản: "đừng
          định lao nhanh hơn xe ngay trước mặt".

        Input:
          top_speed  — tốc độ tối đa hiện tại (đã gồm nitro nếu có).
                       LẤY SẴN từ nơi gọi (self._update_nitro()) — hàm
                       này KHÔNG tự gọi nitro để tránh tính 2 lần/frame.
          wall_ahead — kết quả CÓ SẴN từ detect_wall_ahead() (FUNCTION 01)
                       nếu nơi gọi đã tính rồi, truyền vào để KHỎI TÍNH
                       LẠI. Để None thì hàm tự gọi detect_wall_ahead()
                       (tiện khi test/gọi riêng hàm này một mình).
          others     — list racer khác, cho BƯỚC 4. Để None thì BỎ QUA
                       bước 4 (không lỗi, không bắt buộc lúc nào cũng có).

        Output: target_speed — 1 SỐ kph cụ thể (KHÔNG phải %).
        """
        # BƯỚC 1
        curve_tho = self._path_curvature()

        # BƯỚC 1b — LÀM MƯỢT (EMA), BỔ SUNG sau khi test trên waypoint
        # THẬT của Greenwood Circuit: curvature đo được dao động rất
        # mạnh giữa các waypoint liền kề ngay tại khúc cua gấp (ví dụ đo
        # được 1.000 rồi chỉ ~54px sau đã tụt về 0.127) — vì khúc cua
        # gấp dồn vào 1 đoạn rất ngắn. Nếu dùng thẳng số thô, BƯỚC 2 sẽ
        # nhảy mức liên tục (40% rồi lại 100% ngay khung hình kế) →
        # bot tăng/giảm ga giật cục qua cua — đúng kiểu "giật giật" ban
        # đầu. EMA (trộn dần 25% số mới / giữ 75% số cũ) giúp số dùng
        # để quyết định mượt qua khúc cua, không nhảy cục.
        alpha = 0.25
        self._curve_ema = alpha * curve_tho + (1.0 - alpha) * self._curve_ema
        curve = self._curve_ema

        # BƯỚC 2 — if/elif tuần tự, đọc từ trên xuống là hiểu ngay
        if curve < self.SPEED_CURVE_STRAIGHT_MAX:
            percent = self.SPEED_PERCENT_STRAIGHT      # đường thẳng
        elif curve < self.SPEED_CURVE_LIGHT_MAX:
            percent = self.SPEED_PERCENT_LIGHT         # cua nhẹ
        elif curve < self.SPEED_CURVE_MEDIUM_MAX:
            percent = self.SPEED_PERCENT_MEDIUM        # cua trung
        else:
            percent = self.SPEED_PERCENT_SHARP         # cua gắt

        # BƯỚC 3 — tường gần thì ĐÈ thẳng xuống 30%, không tính chung với BƯỚC 2
        if wall_ahead is None:
            wall_ahead, _ = self.detect_wall_ahead()
        if wall_ahead:
            percent = self.SPEED_PERCENT_WALL

        target_speed = top_speed * percent

        # BƯỚC 4 — có xe chậm phía trước thì giới hạn lại, không vượt 90% tốc độ xe đó
        if others is not None:
            slower_car, _ = self.detect_car_ahead(others)
            if slower_car is not None:
                speed_limit_vi_co_xe_truoc = abs(slower_car.velocity) * 0.90
                if target_speed > speed_limit_vi_co_xe_truoc:
                    target_speed = speed_limit_vi_co_xe_truoc

        return target_speed

    # ── FUNCTION 11 — follow_path() ───────────────────────────────────
    FOLLOW_LOOKAHEAD_BASE          = 120   # px — khoảng nhắm phía trước
                                              # CƠ BẢN lúc xe đứng yên.
                                              # Không có số này trong brief
                                              # — lấy lại từ v1 (phần lái
                                              # mượt đã chạy ổn, không phải
                                              # AI logic đang sửa).
    FOLLOW_LOOKAHEAD_SPEED_FACTOR  = 1.1   # xe chạy NHANH thì nhắm điểm
                                              # XA hơn 1 chút — lý do: nhắm
                                              # gần khi tốc độ cao làm xe
                                              # "giật cổ" lái liên tục.
    FOLLOW_STEER_SENSITIVITY       = 35.0  # độ lệch hướng (độ) ứng với
                                              # FULL LÁI 1 BÊN. Số NHỎ hơn
                                              # = lái nhạy/gắt hơn. Số LỚN
                                              # hơn = lái êm/mượt hơn.

    def follow_path(self, dt):
        """
        FUNCTION 11 — Hành vi CHÍNH: CHỈ bám theo đường đua.

        ĐÚNG 3 trách nhiệm brief liệt ra, KHÔNG làm gì ngoài 3 việc này:
          1. Follow waypoint path
          2. Keep vehicle centered  (điểm nhắm luôn NẰM TRÊN đường tâm
             track, không tự bịa lệch ra ngoài)
          3. Smooth steering        (đổi góc lệch thành lệnh lái bằng 1
             phép CHIA THẲNG đơn giản — không bình phương, không hàm mũ)

        TUYỆT ĐỐI KHÔNG GỌI ở đây (đúng brief "No wall logic, No
        recovery logic" — đây chính là điều brief nhấn mạnh để KHÔNG
        gộp nhiều việc vào 1 hàm như update_bot() khổng lồ của v1):
          - KHÔNG gọi detect_wall_ahead / choose_escape_direction
          - KHÔNG gọi detect_stuck / recover_from_stuck
          - KHÔNG gọi detect_car_ahead / avoid_car_collision
        Mấy hàm trên phải được brain_update() (FUNCTION 12) CHẶN TRƯỚC —
        follow_path() chỉ được gọi khi KHÔNG có gì cần xử lý trước nó.

        Hàm này KHÔNG đụng tới self.velocity — chỉ XOAY xe (steer), đúng
        nghĩa đen "follow PATH" (đường đi), không phải "follow speed".

        Quy trình — 4 bước, mỗi bước 1 lệnh, KHÔNG gộp dòng:
          BƯỚC 1: tìm điểm nhắm phía trước, trên đường tâm track.
          BƯỚC 2: tính GÓC cần quay để mũi xe hướng đúng điểm nhắm đó.
          BƯỚC 3: đổi góc đó thành lệnh lái [-1..+1] bằng 1 phép CHIA.
          BƯỚC 4: ra lệnh xoay xe (gọi physics.steer có sẵn, không viết
                   lại logic xoay xe ở đây).

        Output: không trả gì (None) — tác dụng phụ duy nhất là xe được
        xoay đúng hướng qua physics.steer().
        """
        # BƯỚC 1 — điểm nhắm xa hơn khi xe chạy nhanh, gần hơn khi xe chậm
        khoang_nham = _sc(self.FOLLOW_LOOKAHEAD_BASE) + abs(self.velocity) * self.FOLLOW_LOOKAHEAD_SPEED_FACTOR

        # BƯỚC 1b — giảm khoảng nhắm khi đang vào cua gắt. BỔ SUNG sau
        # khi test phát hiện bug "cắt cua": thuật toán pure-pursuit (lái
        # thẳng hướng tới 1 điểm nhắm xa) tự nhiên kéo xe CẮT GỌN dây
        # cung khi điểm nhắm đặt quá xa trên 1 khúc cua hẹp — y hệt vật
        # lý lái xe thật (nhắm xa quá trên cua gắt sẽ bị trượt rộng ra
        # ngoài). Dùng self._curve_ema (đã làm mượt ở FUNCTION 10) để
        # rút ngắn khoảng nhắm dần tới còn 50% khi cua gắt nhất
        # (curve_ema=1.0) — VẪN đúng trách nhiệm "Keep vehicle centered"
        # của follow_path() (đây là dữ liệu HÌNH DẠNG ĐƯỜNG, không phải
        # đọc wall_mask, nên không phạm luật "No wall logic").
        khoang_nham *= (1.0 - self._curve_ema * 0.5)
        khoang_nham = max(khoang_nham, 30.0)   # sàn tối thiểu — nhắm quá gần gây lái giật run tay

        diem_nham_x, diem_nham_y = self._lookahead_point(khoang_nham)

        # BƯỚC 2 — góc thật từ vị trí xe tới điểm nhắm, rồi so với góc xe đang hướng
        goc_toi_diem_nham = math.degrees(math.atan2(diem_nham_y - self.y, diem_nham_x - self.x))
        do_lech_goc       = physics.angle_diff(goc_toi_diem_nham, self.angle)

        # BƯỚC 3 — lệch FOLLOW_STEER_SENSITIVITY độ = lái full 1 bên. Phép
        # chia thẳng, không công thức cong. clamp để không vượt quá [-1,1].
        lenh_lai = do_lech_goc / self.FOLLOW_STEER_SENSITIVITY
        lenh_lai = physics.clamp(lenh_lai, -1.0, 1.0)

        # BƯỚC 4 — thực hiện lái thật qua physics.steer (đã có sẵn, không viết lại)
        want_drift = (self.composure_instant >= COMPOSURE_LEVELS[3] and self._curve_ema > 0.45)
        # Lưu lại để _update_nitro() ở brain_update() frame SAU đọc được
        # (nitro tính ở ĐẦU brain_update, trước khi follow_path chạy —
        # trễ đúng 1 frame, không đáng kể vì _curve_ema đã mượt theo
        # thời gian rồi, không nhảy cục giữa các frame liền kề).
        self._drifting = want_drift
        physics.steer(self, lenh_lai, dt, handbrake=want_drift)

    # ── Helper nội bộ (KHÔNG thuộc 12 FUNCTION của brief) ────────────
    # 2 hàm nhỏ dưới đây CHỈ để khỏi phải LẶP LẠI cùng vài dòng code
    # 4-5 lần bên trong brain_update() — không thêm logic/quyết định gì
    # mới, chỉ là "gói gọn" thao tác đã có sẵn (move + check lap, và
    # tăng/giảm velocity để bám theo 1 con số tốc độ mong muốn).
    def _finish_frame(self, dt, now):
        """Set hướng di chuyển = hướng mũi xe, di chuyển xe thật theo
        physics, rồi kiểm tra qua vạch đích. Y HỆT 3 dòng cuối từng có ở
        mọi nhánh của shim cũ — viết riêng 1 hàm để KHỎI LẶP.

        CỘNG THÊM (tích hợp FUNCTION 06 bước 5+6): đếm ngược
        _no_collide_t (disable collision sau teleport) và cập nhật nhịp
        nhấp nháy — đặt CHUNG vào đây vì hàm này CHẮC CHẮN chạy đúng 1
        lần MỖI FRAME cho mọi bot, là chỗ tự nhiên nhất để 2 đồng hồ này
        luôn được đếm đều, không phải rải thêm code ở nơi khác."""
        self._move_dir = self.angle
        self._move(dt)
        self._check_lap(dt, now)

        if self._no_collide_t > 0.0:                       # FUNCTION 06 bước 5
            self._no_collide_t = max(0.0, self._no_collide_t - dt)
        self._update_blink(dt)                              # FUNCTION 06 bước 6

    def _update_blink(self, dt):
        """
        Helper nội bộ (KHÔNG thuộc 12 FUNCTION) — cập nhật nhịp nhấp
        nháy sau teleport (FUNCTION 06 bước 6: "Blink vehicle 5 times").

        Cách tính ĐƠN GIẢN: mỗi TELEPORT_BLINK_PERIOD giây thì đổi
        self.visible giữa True/False 1 lần. Mỗi khi đổi TỪ ẨN SANG HIỆN
        (visible chuyển False -> True) tính là ĐÃ XONG 1 lần nhấp nháy
        (1 chu kỳ ẨN-rồi-HIỆN = 1 lần), trừ _blink_count đi 1. Hết
        _blink_count thì luôn hiện (visible=True) trở lại bình thường.

        Render loop (track-greenwood-circuit.py) CHỈ cần đọc
        racer.visible: True thì vẽ sprite, False thì bỏ qua frame đó —
        không cần biết gì về _blink_count/_blink_t.
        """
        if self._blink_count <= 0:
            self.visible = True
            return

        self._blink_t += dt
        if self._blink_t >= self.TELEPORT_BLINK_PERIOD:
            self._blink_t = 0.0
            was_visible = self.visible
            self.visible = not self.visible
            if was_visible is False and self.visible is True:
                self._blink_count -= 1   # vừa xong đúng 1 chu kỳ ẨN -> HIỆN

        if self._blink_count <= 0:
            self.visible = True

    def _apply_speed_toward(self, desired_speed, dt, top):
        """Tăng/giảm self.velocity thật để từ từ bám theo desired_speed
        (KHÔNG nhảy thẳng tới số đó — giữ cảm giác ga/phanh tự nhiên).
        Tăng tốc dùng ĐƯỜNG CONG THẬT (apply_throttle, y hệt player W),
        giảm tốc vẫn TUYẾN TÍNH cứng theo brake_power (phanh chủ động —
        đúng như update_player nhánh S, bình đẳng player/bot)."""
        if self.velocity < desired_speed - 2:
            physics.apply_throttle(self, dt, reverse=False)
        elif self.velocity > desired_speed + 2:
            self.velocity -= self.brake_power * 0.9 * dt   # đang nhanh hơn mong muốn -> giảm tốc
        self.velocity = physics.clamp(self.velocity, 5.0, top)

    _COMPOSURE_NEUTRAL = COMPOSURE_LEVELS[2]

    def _update_composure(self, dt):
        self._composure_retarget_t -= dt
        if self._composure_retarget_t <= 0:
            lo = self.composure * (1.0 - COMPOSURE_VARIANCE)
            hi = self.composure * (1.0 + COMPOSURE_VARIANCE)
            self._composure_target = random.uniform(lo, hi)
            self._composure_retarget_t = random.uniform(1.5, 4.0)
        self.composure_instant += (self._composure_target - self.composure_instant) \
                                  * min(1.0, COMPOSURE_LERP_RATE * dt)

    def _speed_confidence(self):
        return self.composure_instant / self._COMPOSURE_NEUTRAL

    # ── FUNCTION 12 — brain_update() ─────────────────────────────────
    def brain_update(self, others, dt, now):
        """
        FUNCTION 12 — DUY NHẤT 1 hàm quyết định AI làm gì mỗi frame.
        Đây là hàm THAY THẾ HOÀN TOÀN cho update_bot() shim cũ — toàn bộ
        11 hàm trước đó (FUNCTION 01-11) chỉ là "công cụ", brain_update()
        là nơi QUYẾT ĐỊNH dùng công cụ nào, đúng thứ tự nào.

        Input MỚI so với update_bot() cũ: "others" — list TẤT CẢ racer
        khác (kể cả player), CẦN có để FUNCTION 07/08/09 (né xe) hoạt
        động. Đây là lý do tên hàm đổi từ update_bot() sang brain_update():
        chữ ký hàm đã khác (thêm tham số others), không thể giữ tên cũ
        mà âm thầm đổi nghĩa.

        QUY TẮC QUAN TRỌNG NHẤT — đúng PRIORITY ORDER của brief: kiểm
        tra TUẦN TỰ từ MỨC 1 xuống MỨC 6, hễ rơi vào 1 MỨC thì xử lý
        XONG rồi DỪNG NGAY (return) — KHÔNG rớt tiếp xuống mức thấp hơn
        trong CÙNG 1 frame. Đây chính là thứ mà update_bot() bản v1
        KHÔNG có (v1 trộn chung nhiều điều kiện if/elif/else cùng lúc
        trong 1 hàm khổng lồ, gây ra hành vi giật/không nhất quán):

          MỨC 1 — Teleport Recovery     (FUNCTION 06)
          MỨC 2 — Stuck Recovery        (FUNCTION 03 + 04)
          MỨC 3 — Wall Avoidance        (FUNCTION 01 + 02)
          MỨC 4/5 — Vehicle Avoidance / Overtaking
                    (FUNCTION 07 phát hiện xe + FUNCTION 09 tự quyết
                    định "đổi lane" hay "giảm tốc", FUNCTION 09 đã gộp
                    sẵn đúng 2 mức 4 và 5 của brief trong 1 lần gọi)
          MỨC 6 — Path Following        (FUNCTION 10 + 11)
        """
        # ── Xe đã về đích — phanh trượt dần, không chạy AI nữa ─────────
        if self.finished:
            self.nitro_active = False    # tắt khói/lửa nitro ngay khi về đích
            if abs(self.velocity) > 0.5:
                sign = 1.0 if self.velocity > 0 else -1.0
                self.velocity -= sign * 120.0 * dt
            else:
                self.velocity = 0.0
            self._finish_frame(dt, now)
            return

        self._advance_waypoint()
        is_moving = abs(self.velocity) > 0.5
        want_nitro = self._bot_want_nitro(dt)
        top = self._update_nitro(dt, want_nitro=want_nitro,
                                  drifting=self._drifting, is_moving=is_moving)
        # Nitro tự đẩy bot kể cả khi chưa tới đoạn cần ga thêm — y hệt
        # player (xem update_player). _apply_speed_toward() ở MỨC 6 vẫn
        # chạy bình thường sau đó và sẽ clamp đúng theo `top` mới này.
        if self.nitro_active and self.velocity < top:
            self.velocity += self.acceleration * dt
            self.velocity = min(self.velocity, top)
        self._cur_top = top
        self._update_composure(dt)

        # ── MỨC 1 — Teleport Recovery ──────────────────────────────────
        # Gọi MỖI FRAME, KHÔNG có điều kiện "if" trước nó — vì
        # teleport_recovery() (FUNCTION 06) tự nuôi đồng hồ 6s riêng bên
        # trong, cần được nuôi đều mỗi frame mới đếm đúng. Hàm chỉ THỰC
        # SỰ teleport (và trả True) khi đủ 6 giây kẹt liên tục.
        if self.teleport_recovery(dt):
            self._finish_frame(dt, now)
            return

        # ── MỨC 2 — Stuck Recovery ─────────────────────────────────────
        # is_recovering=True nghĩa là ĐANG GIỮA quy trình lùi/tiến của
        # FUNCTION 04 — phải COMMIT cho xong, không bỏ ngang giữa đường
        # (bỏ ngang giữa pha "đang lùi" sẽ làm xe quay đầu lung tung).
        if self.is_recovering or self.detect_stuck(dt):
            self.recover_from_stuck(dt)
            self._finish_frame(dt, now)
            return

        # ── MỨC 3 — Wall Avoidance ───────────────────────────────────────
        wall_ahead, rays = self.detect_wall_ahead()
        if wall_ahead:
            huong_ne = self.choose_escape_direction(rays)
            physics.steer(self, huong_ne, dt)
            # Tường gần -> compute_target_speed() (FUNCTION 10) tự đè
            # xuống 30% ở BƯỚC 3 của nó — không cần quan tâm traffic lúc
            # này, đang lo né tường là việc gấp hơn.
            desired_speed = self.compute_target_speed(top, wall_ahead=True) * self._speed_confidence()
            self._apply_speed_toward(min(desired_speed, top), dt, top)
            self._finish_frame(dt, now)
            return

        # ── MỨC 4/5 — Vehicle Avoidance / Overtaking ──────────────────────
        target, dist = self.detect_car_ahead(others)
        if target is not None:
            # avoid_car_collision() (FUNCTION 09) tự quyết định và TỰ
            # LÀM LUÔN 1 trong 2 việc, trả về CHỮ để brain_update() biết
            # đã làm gì rồi, tránh làm trùng/đánh nhau:
            #   "lane_change" -> FUNCTION 09 ĐÃ tự lái (steer) rồi.
            #   "brake"       -> FUNCTION 09 CHỈ giảm tốc, CHƯA lái gì.
            #   None          -> xe trước còn xa (chưa tới SAFETY_DISTANCE),
            #                     chưa cần làm gì, đi xuống MỨC 6 như thường.
            action = self.avoid_car_collision(target, dist, others, dt)

            if action == "lane_change":
                # Đã lái rồi -> KHÔNG gọi follow_path() nữa (2 lệnh lái
                # cùng 1 frame sẽ đánh nhau, xe lái giật).
                desired_speed = self.compute_target_speed(top, wall_ahead=False, others=others) * self._speed_confidence()
                self._apply_speed_toward(min(desired_speed, top), dt, top)
                self._finish_frame(dt, now)
                return

            if action == "brake":
                # FUNCTION 09 CHỈ giảm tốc, CHƯA lái -> vẫn cần
                # follow_path() lo việc lái theo đường trong lúc đang
                # bám theo xe trước. KHÔNG gọi compute_target_speed +
                # _apply_speed_toward ở đây nữa — FUNCTION 09 đã tự
                # giảm tốc xong rồi, gọi thêm sẽ làm velocity bị tính 2
                # lần trong 1 frame (1 bên giảm, 1 bên lại kéo tăng lên
                # theo desired_speed, đánh nhau).
                self.follow_path(dt)
                self._finish_frame(dt, now)
                return

            # action is None -> rơi xuống MỨC 6 phía dưới, KHÔNG return ở đây

        # ── MỨC 6 — Path Following ────────────────────────────────────
        # Không có gì cần xử lý ở các mức trên -> lái theo đường bình
        # thường, tính tốc độ mong muốn rồi bám theo.
        self.follow_path(dt)
        desired_speed = self.compute_target_speed(top, wall_ahead=False, others=others) * self._speed_confidence()
        self._apply_speed_toward(min(desired_speed, top), dt, top)
        self._finish_frame(dt, now)

    # ── update_bot() — LỚP GỌI MỎNG sang brain_update(), GIỮ TÊN CŨ ──
    def update_bot(self, dt, now, others=None):
        """
        Giữ nguyên TÊN HÀM update_bot() để main loop CŨ
        (track-greenwood-circuit.py) gọi được mà KHÔNG lỗi ngay — bộ
        não THẬT giờ nằm hoàn toàn trong brain_update() (FUNCTION 12)
        ở trên, hàm này CHỈ còn là 1 lớp gọi mỏng (delegate).

        others=None (mặc định, vì main loop CŨ chưa truyền tham số này):
          FUNCTION 07/08/09 (né xe) sẽ KHÔNG hoạt động — coi như map
          không có xe nào khác. KHÔNG crash, chỉ là thiếu 1 lớp phòng
          vệ. Cần sửa main loop để gọi update_bot(dt, now, all_racers)
          (hoặc đổi thẳng sang gọi brain_update()) thì né xe mới chạy
          thật trong game.
        """
        self.brain_update(others if others is not None else [], dt, now)

    # ── RACE PROGRESS — GIỮ NGUYÊN TỪ v1 (2 tiêu chí: lap > vị trí) ───
    def race_progress(self):
        """
        Trả về (lap_done, wp_total + frac) để so hạng.
        frac = projection vị trí xe lên segment [wp_prev → wp_cur],
        clamp [0,1] — chính xác hơn nội suy 1-d/seg vì tính cả thành
        phần dọc segment, không chỉ khoảng cách thẳng tới điểm cuối.
        """
        n = len(self._wp)
        lap_done = self.lap_count + (1 if self.race_started else 0)
        if n == 0:
            return (lap_done, 0.0)
        ci  = self.wp_idx % n
        pi  = (self.wp_idx - 1) % n
        cx, cy   = self._wp[ci]
        px2, py2 = self._wp[pi]
        sdx  = cx - px2;  sdy  = cy - py2
        seg2 = sdx*sdx + sdy*sdy
        if seg2 < 1:
            frac = 0.0
        else:
            t = ((self.x - px2)*sdx + (self.y - py2)*sdy) / seg2
            frac = max(0.0, min(1.0, t))
        return (lap_done, self.wp_total + frac)
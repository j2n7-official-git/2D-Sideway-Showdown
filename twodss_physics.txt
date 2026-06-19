"""
=====================================================================
TWODSS_PHYSICS.PY  —  2D Sideway Showdown
Module vật lý dùng chung cho tất cả các map.
=====================================================================

MỤC TIÊU MODULE:
    Tách toàn bộ logic vật lý ra khỏi file map để:
    - Tái sử dụng cho nhiều map mà không copy-paste code
    - Dễ test, debug từng phần độc lập
    - Tường minh theo nguyên lý Separation of Concerns

CÁCH DÙNG (trong file map):
    import twodss_physics as physics
    physics.setup(track, wall_mask, MAP_W, MAP_H, physics.MOVE_SCALE, gate_safe)
    physics.handle_car_collisions(all_racers, dt)
    # Trong Racer._move: physics.move_car(self, dt)
=====================================================================
"""

import math


# =====================================================================
# MODULE-LEVEL CONTEXT — set bởi setup() khi load map
# =====================================================================

_track = None
# Kiểu: pygame.Surface | None
# Mục đích: ảnh track gốc đã scale theo MAP_SCALE.
# Dùng trong: is_offroad() — đọc màu pixel tại (ix,iy) để xác định
#   loại bề mặt (cỏ xanh, nước, đường nhựa).
# Lý do cần: mỗi map có track riêng, không thể hardcode.

_wall_mask = None
# Kiểu: pygame.Surface | None
# Mục đích: ảnh mask trắng/đen cùng kích thước track.
#   Pixel TRẮNG (R,G,B > 200) = tường cứng (jersey barrier).
#   Pixel ĐEN = đường xe có thể đi.
# Dùng trong: is_hard_wall() — kiểm tra pixel tại (ix,iy).
# Lý do dùng ảnh thay vì công thức màu: công thức màu bê tông hay
#   false-positive trên track có ánh sáng phức tạp (perspective, shadow).

_MAP_W = 0
_MAP_H = 0
# Kiểu: int (pixel)
# Mục đích: kích thước track đã nhân MAP_SCALE.
# Dùng trong: is_offroad(), is_hard_wall() — kiểm tra boundary (ix,iy).
#   move_car() — clamp vị trí xe không ra ngoài map.
# Công thức: MAP_W = track_raw.get_width() * MAP_SCALE

# =====================================================================
# MOVE_SCALE — HẰNG SỐ TỐC ĐỘ DI CHUYỂN DÙNG CHUNG CHO MỌI MAP
# =====================================================================
# Trước đây mỗi file map (track-xxx.py) tự khai báo riêng 1 số
# MOVE_SCALE khác nhau → khó đồng bộ khi có nhiều map (4 map cũ + map
# mới = 5 map). Giờ TẤT CẢ map dùng CHUNG hằng số này — đổi 1 lần ở
# đây, mọi map tự động đổi theo, không cần sửa từng file map riêng.
#
# Cách dùng trong file map (track-xxx.py):
#   import twodss_physics as physics
#   MOVE_SCALE = physics.MOVE_SCALE
#   ...
#   setup_map(..., move_scale=MOVE_SCALE, ...)
#
# Nếu 1 map nào đó CẦN tốc độ khác biệt riêng (hiếm, ví dụ map test),
# vẫn có thể truyền số khác trực tiếp vào setup_map() — hằng số này
# chỉ là GIÁ TRỊ MẶC ĐỊNH dùng chung, không bắt buộc.
MOVE_SCALE = 3.8
# Kiểu: float (px/s per kph)
# Lịch sử: 2.5 (v1) -> 3.2 -> 3.8 (hiện tại, theo yêu cầu "đua nhanh
#   hơn", áp dụng đồng bộ cho cả 5 map).

_MOVE_SCALE = MOVE_SCALE
# Kiểu: float (px/s per kph) — biến NỘI BỘ, KHÔNG sửa trực tiếp ở đây.
# Mục đích: giá trị THẬT đang dùng khi chạy (có thể bị setup() ghi đè
#   nếu map truyền move_scale khác MOVE_SCALE mặc định ở trên).
# Công thức tính vị trí mỗi frame:
#   movement_px = velocity_kph * _MOVE_SCALE * dt_seconds
# Ví dụ: xe 200 kph, dt=1/90s → 200 * 3.8 * (1/90) ≈ 8.4 px/frame

_GATE_SAFE = (0, 0, 0, 0)
# Kiểu: tuple (x1, x2, y1, y2) — tọa độ pixel trong map đã scale
# Mục đích: vùng an toàn quanh vạch xuất phát (checkered flag).
# Lý do cần: vạch ca-rô có pixel xám nhạt → is_offroad() và
#   is_hard_wall() sẽ false-positive → xe bị chặn ngay vạch xuất phát.
# Fix: trong vùng này, cả 2 hàm đều trả về False (coi như đường thường).
# Công thức ví dụ Greenwood:
#   x1 = int(170 * MAP_SCALE), x2 = int(430 * MAP_SCALE)
#   y1 = int(1080 * MAP_SCALE), y2 = int(1310 * MAP_SCALE)


def setup(track, wall_mask, map_w: int, map_h: int,
          move_scale: float = MOVE_SCALE,
          gate_safe: tuple = (0, 0, 0, 0)):
    """Khởi tạo physics context cho map. Gọi 1 lần sau khi load track."""
    global _track, _wall_mask, _MAP_W, _MAP_H, _MOVE_SCALE, _GATE_SAFE
    _track      = track
    _wall_mask  = wall_mask
    _MAP_W      = map_w
    _MAP_H      = map_h
    _MOVE_SCALE = move_scale
    _GATE_SAFE  = gate_safe


# =====================================================================
# HELPERS
# =====================================================================

def clamp(v, lo, hi):
    """Giới hạn v trong [lo, hi]. Dùng để chặn velocity và tọa độ."""
    return max(lo, min(v, hi))


# =====================================================================
# NITRO v2 — chuyển đổi MƯỢT cho top-speed bonus (ramp lên / decay xuống)
# =====================================================================
# _NITRO_DECAY_SLOPE: hệ số góc (kph/s) khi BONUS ĐANG GIẢM (nhả nitro
# hoặc hết nhiên liệu). Theo brief: "giảm xuống theo hình thái mượt mà
# ... hệ số góc -1.5 sẽ tốt hơn". -1.5 ở đây là hệ số NHÂN trên thang
# %/s chuẩn hoá theo nitro_boost của xe (mỗi xe boost max khác nhau,
# 50-77 kph theo xlsx), không phải -1.5 kph/s cứng cho mọi xe — nếu
# cứng 1 số kph/s thì xe boost 77 (Svempa) và xe boost 50 (Mazda) sẽ
# mất CÙNG thời gian giảm dù bonus gốc khác xa nhau (vô lý vật lý).
# Công thức: rate = _NITRO_DECAY_SLOPE * (current_bonus_nonzero ? full_boost : full_boost)
# Quy về: mỗi giây giảm 1.5x "đơn vị chuẩn hoá" của riêng xe đó, đơn vị
# chuẩn hoá = full_boost / nitro_boost_time (tốc độ mà nó đã ramp LÊN
# trong 1s ở tốc độ trung bình) — vừa mượt, vừa tỉ lệ đúng với xe nhanh/chậm.
_NITRO_DECAY_SLOPE = 1.5

# _NITRO_RAMP_RATE_MULT: ramp LÊN (đang giữ phím, đẩy bonus tới target)
# dùng tốc độ y hệt v1 (full_boost/nitro_boost_time mỗi giây) — KHÔNG
# đổi cảm giác turbo-lag cũ, chỉ áp dụng decay mượt hơn lúc tắt.


def step_nitro_bonus(current: float, target: float, dt: float,
                      full_boost: float = None, boost_time: float = None) -> float:
    """
    Tiến `current` (kph bonus hiện tại) một bước về `target` (0 khi tắt
    nitro, hoặc giá trị ramp khi đang active), KHÔNG nhảy bậc.

    - target > current (đang RAMP LÊN khi mới bật nitro): tăng tuyến
      tính với tốc độ chuẩn dựa trên full_boost/boost_time của chính
      racer (truyền qua 2 tham số tùy chọn). Nếu không truyền, coi như
      gọi viên đã tự tính sẵn target theo ramp (trường hợp dùng trong
      _update_nitro: target_bonus đã là số đúng theo ramp của frame này)
      -> bước thẳng tới target luôn (không double-ramp).
    - target < current (đang DECAY MƯỢT khi nhả/hết xăng): giảm tuyến
      tính với hệ số góc _NITRO_DECAY_SLOPE × (full_boost cũ / boost_time
      cũ nếu có, hoặc dùng current làm mốc nếu không truyền).

    Trả về giá trị bonus mới (đã clamp không vượt target khi đang tiến
    gần, không âm).
    """
    if abs(target - current) < 0.01:
        return target

    if target >= current:
        # Đang ramp lên: target đã được _update_nitro tính sẵn theo
        # đúng tiến trình ramp của frame này -> nhận thẳng, không lặp
        # thêm 1 lớp lerp nữa (tránh ramp kép làm turbo-lag bị "ì" hơn
        # 2 lần so với _nitro_boost_time cấu hình trong xlsx).
        return target

    # Đang giảm — decay MƯỢT, KHÔNG cắt cụt.
    # rate (kph/s) = slope × "1 đơn vị chuẩn hoá" của xe này.
    # Đơn vị chuẩn hoá = full_boost/boost_time nếu có, fallback dùng
    # current (bonus lúc bắt đầu giảm) chia đều trong ~1s nếu thiếu info.
    if full_boost and boost_time:
        unit = full_boost / max(0.01, boost_time)
    else:
        unit = max(current, 1.0)
    rate = _NITRO_DECAY_SLOPE * unit
    new_val = current - rate * dt
    return max(target, new_val)


def fwd_vec(a: float):
    """
    Trả về vector đơn vị (cos a°, sin a°) — hướng tiến của xe.
    Hệ tọa độ pygame: Y tăng xuống dưới.
      angle=270° → (0, -1) = hướng BẮC (lên trên màn hình)
      angle=0°   → (1,  0) = hướng ĐÔNG (sang phải)
    """
    r = math.radians(a)
    return math.cos(r), math.sin(r)


def angle_diff(a: float, b: float) -> float:
    """
    Hiệu góc a - b chuẩn hóa về (-180°, 180°].
    Dùng để tính hướng steer: dương = xoay phải, âm = xoay trái.
    Công thức: d = (a - b) % 360; nếu d > 180 thì d -= 360.
    """
    d = (a - b) % 360
    return d - 360 if d > 180 else d


# =====================================================================
# TERRAIN DETECTION
# =====================================================================

def _in_gate_safe_zone(ix: int, iy: int) -> bool:
    """True nếu pixel (ix,iy) nằm trong vùng an toàn vạch xuất phát."""
    x1, x2, y1, y2 = _GATE_SAFE
    return x1 <= ix <= x2 and y1 <= iy <= y2


def is_offroad(px: float, py: float) -> bool:
    """
    True nếu điểm (px,py) là cỏ xanh, nước xanh lam, hoặc ngoài biên map.

    Chỉ detect cỏ và nước — jersey barrier do is_hard_wall() xử lý riêng.
    Bỏ qua vùng gate để tránh false-positive tại vạch ca-rô.

    Thuật toán phân loại màu pixel:
      r, g, b = màu pixel tại (ix, iy) từ track surface
      avg     = (r+g+b)/3     → độ sáng trung bình
      gdom    = g > r+10 AND g > b+10  → xanh lá dominant?

      Cỏ xanh : gdom = True  AND avg > 55  (tránh nhầm bóng tối)
      Nước    : b > r+18 AND b > g+8 AND avg > 75
    """
    ix, iy = int(px), int(py)
    if ix < 0 or iy < 0 or ix >= _MAP_W or iy >= _MAP_H:
        return True   # ngoài biên map = offroad
    if _in_gate_safe_zone(ix, iy):
        return False
    try:
        c = _track.get_at((ix, iy))
    except:
        return True
    r, g, b = int(c[0]), int(c[1]), int(c[2])
    avg  = (r + g + b) / 3.0
    gdom = g > r + 10 and g > b + 10
    if gdom and avg > 55:                      return True  # cỏ xanh
    if b > r + 18 and b > g + 8 and avg > 75: return True  # nước
    return False


def is_hard_wall(px: float, py: float) -> bool:
    """
    True nếu điểm (px,py) là tường cứng (jersey barrier).

    Dùng wall_mask PNG: pixel trắng (R,G,B đều > 200) = tường.
    Nếu không có wall_mask → return False (không có tường cứng).

    Lý do dùng PNG thay công thức màu:
      Jersey barrier xám nhạt trùng màu đường nhựa cũ hoặc curb
      → công thức false-positive nhiều.
      PNG do người vẽ = chính xác tuyệt đối.
    """
    ix, iy = int(px), int(py)
    if ix < 0 or iy < 0 or ix >= _MAP_W or iy >= _MAP_H:
        return True
    if _in_gate_safe_zone(ix, iy):
        return False
    if _wall_mask is not None:
        try:
            c = _wall_mask.get_at((ix, iy))
            return c[0] > 200 and c[1] > 200 and c[2] > 200
        except:
            return False
    return False


# =====================================================================
# WALL-ALIGN MOVEMENT PHYSICS
# =====================================================================

# =====================================================================
# STEERING — BICYCLE MODEL (dùng chung cho player VÀ bot)
# =====================================================================

# =====================================================================
# THROTTLE CURVE — gia tốc THẬT theo % top speed (KHÔNG tuyến tính)
# =====================================================================
# Brief 2a/2b/2c: xe số thật KHÔNG tăng tốc theo y = ax+b. Đề ga đi qua
# 3 vùng dựa trên % so với top speed HIỆN TẠI (max_speed gốc, KHÔNG
# tính nitro — nitro là lực đẩy riêng, không qua hàm này):
#
#   Vùng D (tiến, accel > 0):
#     0%  -> 25% top : RA CHẬM   (giống ì số 1, torque thấp lúc đầu)
#     25% -> 75% top : CAO TRÀO  (mid-range torque, tăng nhanh nhất)
#     75% -> 100% top: TIỆM CẬN CHẬM DẦN (drag ~ v² thắng dần lực kéo,
#                       gần max thì gần như đi ngang, giữ y nguyên)
#   Vùng R (lùi) và NHẢ GA VỀ 0 (không phanh chủ động):
#     Cùng hình dạng, lật ngược dấu — mô tả ở 2e: xe có range -56..350
#     (ví dụ minh hoạ), khúc gần 0 cũng bo cong mượt thay vì cắt cụt.
#
# Hệ số góc tại mỗi vùng lấy từ self.acceleration GỐC của xe (đã tune
# theo CAR_STATS/xlsx) nhân với 1 multiplier theo vùng — KHÔNG đổi
# acceleration tuyệt đối của xe (đúng yêu cầu trước đó "car_data tăng
# tốc/friction tuyệt đối không được đổi lại"), chỉ đổi NHỊP áp dụng nó
# theo thời điểm trong dải tốc độ.
_THR_LOW_FRAC    = 0.25   # ngưỡng % top: hết vùng RA CHẬM
_THR_HIGH_FRAC   = 0.75   # ngưỡng % top: hết vùng CAO TRÀO, vào TIỆM CẬN
_THR_LOW_MULT    = 0.55   # hệ số nhân accel trong vùng RA CHẬM (ì máy)
_THR_MID_MULT    = 1.35   # hệ số nhân accel trong vùng CAO TRÀO (đỉnh lực kéo)
_THR_HIGH_MULT   = 0.18   # hệ số nhân accel trong vùng TIỆM CẬN (gần max)


def _throttle_mult(ratio: float) -> float:
    """
    ratio = |velocity| / top_speed, đã clamp [0,1].
    Trả về hệ số nhân lên accel GỐC tại điểm % này — đây chính là hình
    dạng đường cong chữ S trong ảnh minh hoạ (2e): bằng phẳng thấp ở
    đầu, dốc nhất ở giữa, bằng phẳng cao ở cuối (tiệm cận).
    Nội suy TUYẾN TÍNH giữa 3 mức để không có bước nhảy giật (continuity)
    tại 2 ngưỡng 25%/75% — mỗi đoạn nhỏ là thẳng nhưng nối lại thành
    cảm giác cong mượt khi accel áp theo từng frame dt nhỏ.
    """
    if ratio <= 0.0:
        return _THR_LOW_MULT
    if ratio < _THR_LOW_FRAC:
        # 0% -> 25%: trượt dần từ LOW lên giữa LOW và MID
        t = ratio / _THR_LOW_FRAC
        return _THR_LOW_MULT + (_THR_MID_MULT - _THR_LOW_MULT) * t * 0.5
    if ratio < _THR_HIGH_FRAC:
        # 25% -> 75%: CAO TRÀO — đỉnh ở giữa khoảng (ratio=0.5), thoai
        # thoải 2 đầu để nối mượt với vùng LOW/HIGH liền kề
        t = (ratio - _THR_LOW_FRAC) / (_THR_HIGH_FRAC - _THR_LOW_FRAC)  # 0..1
        # parabol lật ngược: đỉnh giữa = _THR_MID_MULT, 2 đầu thấp hơn 1 chút
        peak = _THR_MID_MULT
        edge = _THR_MID_MULT * 0.78
        return edge + (peak - edge) * (1.0 - abs(t - 0.5) * 2.0)
    if ratio < 1.0:
        # 75% -> 100%: TIỆM CẬN — giảm mạnh dần về _THR_HIGH_MULT
        t = (ratio - _THR_HIGH_FRAC) / (1.0 - _THR_HIGH_FRAC)  # 0..1
        start = _THR_MID_MULT * 0.78
        return start + (_THR_HIGH_MULT - start) * t
    return _THR_HIGH_MULT


def apply_throttle(racer, dt: float, reverse: bool = False,
                    mult: float = 1.0) -> None:
    """
    Tăng racer.velocity theo ĐƯỜNG CONG THẬT (không tuyến tính), dùng
    CHUNG cho player (phím W) và bot (đang chậm hơn target_speed).

    KHÔNG dùng cho: phanh chủ động (S/brake_power — vẫn tuyến tính cứng
    theo yêu cầu, vì đó là decel CHỦ ĐỘNG khác hệ số góc tuỳ xe), và
    KHÔNG dùng cho nitro-pull (nitro là lực đẩy riêng, xem update_player/
    brain_update — ảnh hưởng của nó lên độ dốc tại điểm tiệm cận là
    không đáng kể, không cần qua hàm này).

    racer cần có: .velocity, .acceleration, .max_speed
    reverse=True  -> áp dụng cho chiều LÙI (số R), dùng |velocity| để
                     tính ratio, cộng/trừ đúng hướng âm.
    mult          -> hệ số phụ ngoài (vd handbrake *0.85 như code cũ),
                     nhân THÊM vào sau _throttle_mult(), không thay nó.
    """
    top = max(racer.max_speed, 1.0)
    ratio = clamp(abs(racer.velocity) / top, 0.0, 1.0)
    m = _throttle_mult(ratio) * mult
    step = racer.acceleration * m * dt
    if reverse:
        racer.velocity -= step
    else:
        racer.velocity += step


def release_throttle_decay(racer, dt: float) -> None:
    """
    NHẢ GA về 0 (không bấm gì, không phanh chủ động) — cũng đi theo
    đường cong, KHÔNG cắt cụt tuyến tính. Dùng |velocity|/top_speed
    tương tự apply_throttle() nhưng hệ số LẤY NGƯỢC: gần 0 thì giảm
    chậm (engine braking yếu ở vòng tua thấp), ở dải giữa giảm rõ hơn
    (đúng cảm giác "nhả ga xe tự hãm" thật), rồi lại chậm dần khi xe
    gần như đã dừng hẳn — đối xứng với hình dạng tăng tốc.
    Dùng racer.friction GỐC làm hệ số góc cơ sở (KHÔNG đổi friction
    tuyệt đối của xe, chỉ đổi nhịp áp dụng nó).
    """
    top = max(racer.max_speed, 1.0)
    ratio = clamp(abs(racer.velocity) / top, 0.0, 1.0)
    # Hình chuông nhẹ: thấp ở 2 đầu (gần 0% và gần 100%), cao ở giữa.
    decel_mult = 0.35 + 0.9 * math.sin(math.pi * ratio)
    d = racer.friction * decel_mult * dt
    if abs(racer.velocity) <= d:
        racer.velocity = 0.0
    else:
        sign = 1.0 if racer.velocity > 0 else -1.0
        racer.velocity -= sign * d


def steer(racer, steer_input: float, dt: float, handbrake: bool = False):
    """
    Lái xe theo mô hình bicycle (Ackermann) — VẬT LÝ THẬT.
    Dùng chung cho player và bot → cả 2 quay y hệt nhau (bình đẳng).

    ── CÔNG THỨC CỐT LÕI ─────────────────────────────────────────────
        ω = (v / L) × tan(δ)
      ω = tốc độ quay (rad/s) — kết quả
      v = vận tốc xe (px/s)
      L = wheelbase (khoảng cách trục trước–sau)
      δ = góc đánh lái bánh trước (rad)

    ── 3 HỆ QUẢ VẬT LÝ ───────────────────────────────────────────────
      1. v=0 → ω=0: xe ĐỨNG YÊN đánh lái KHÔNG quay (hết bug xoay loạn
         tại vạch xuất phát khi countdown).
      2. v càng lớn → quay càng nhanh, NHƯNG δ_max giảm theo tốc độ
         (không ai bẻ lái gắt ở 180 km/h).
      3. Xe pivot quanh TRỤC BÁNH SAU → mũi vẽ cung, đuôi bám theo.

    Tham số:
      steer_input : -1.0 (full trái) … 0 … +1.0 (full phải)
      handbrake   : True → drift, góc lái rộng hơn + ít giảm theo tốc độ

    Trả về True nếu xoay được (không bị tường chặn).
    """
    v_px = racer.velocity * _MOVE_SCALE       # px/s

    # v=0 → không quay (hệ quả 1)
    if abs(v_px) < 4.0 or abs(steer_input) < 0.01:
        return False

    # δ_max: góc lái tối đa, GIẢM theo tốc độ (hệ quả 2)
    # base 34° lúc chậm → 14° lúc top speed
    top      = getattr(racer, '_cur_top', racer.max_speed)
    spd_r    = min(abs(racer.velocity) / max(top, 1), 1.0)
    delta_max = (38.0 - spd_r * 18.0) + (12.0 if handbrake else 0.0) #nới nhẹ giới hạn góc lái:
    delta     = math.radians(steer_input * delta_max)   # góc lái thực

    # L: wheelbase ≈ 62% chiều dài xe
    L = max(racer.car_h * 0.62, 8.0)

    # ω = (v/L)·tan(δ)  → đổi sang độ/frame
    omega_deg = math.degrees(v_px / L * math.tan(delta)) * dt
    # lùi (v<0): lái ngược chiều như xe thật
    if racer.velocity < 0:
        omega_deg = -omega_deg

    return _rotate_about_rear(racer, omega_deg)


def _rotate_about_rear(racer, d_ang: float) -> bool:
    """
    Xoay xe quanh TRỤC BÁNH SAU (không phải tâm sprite).
    Check mũi + đuôi sau khi xoay: chạm tường → KHÔNG xoay (option A).
    """
    r0 = math.radians(racer.angle)
    fx, fy = math.cos(r0), math.sin(r0)
    half = racer.car_h * 0.5
    # Trục bánh sau = lùi 50% nửa thân (gần cầu sau thật)
    rear_x = racer.x - fx * half * 0.5
    rear_y = racer.y - fy * half * 0.5

    na = racer.angle + d_ang
    r1 = math.radians(na)
    nfx, nfy = math.cos(r1), math.sin(r1)
    nx = rear_x + nfx * half * 0.5
    ny = rear_y + nfy * half * 0.5

    nose = (nx + nfx * half, ny + nfy * half)
    tail = (nx - nfx * half, ny - nfy * half)
    if is_hard_wall(*nose) or is_hard_wall(*tail):
        return False
    racer.angle = na
    racer.x, racer.y = nx, ny
    return True

_POLY_N    = 24    # số đỉnh polygon mô phỏng viền xe (20-25 — cân bằng
                    # giữa chính xác và chi phí; siêu xe góc cạnh phức
                    # tạp như F1/Devel Sixteen cần nhiều hơn, nhưng xe
                    # đua thường trong game không cần tới mức đó)
_POLY_STEP = 1.5    # px giữa 2 điểm sample dọc mỗi cạnh — NHỎ HƠN 1
                    # pixel của ảnh tường → không còn khoảng hở có nghĩa
                    # nào để tường "lọt qua" được (tường cũng là dữ liệu
                    # pixel rời rạc, không có nét nào mỏng hơn 1px)
_POLY_FLAT_FRONT = 0.55   # mũi — giữ nguyên tỉ lệ cũ
_POLY_FLAT_REAR  = 0.80   # đuôi — chỉ vuốt nhọn 20% cuối (đuôi xe vuông hơn mũi)


def _car_width_profile(s, hw):
    a = abs(s)
    flat = _POLY_FLAT_REAR if s < 0 else _POLY_FLAT_FRONT   # MỚI: đuôi (s<0) dùng ngưỡng riêng
    if a <= flat:
        return hw
    t = (a - flat) / (1.0 - flat)
    return hw * math.sqrt(max(0.0, 1.0 - t*t))


def _car_polygon_world(racer, x, y):
    """_POLY_N điểm (toạ độ THẾ GIỚI) khép viền cong THẬT quanh xe tại
    vị trí ứng viên (x,y) — KHÔNG dùng racer.x,racer.y trực tiếp vì
    hàm này còn được gọi để TEST các vị trí giả định trong swept-check,
    chưa chắc xe đã thật sự ở đó."""
    fx, fy = fwd_vec(racer.angle)
    px, py = -fy, fx
    L  = racer.car_h * 0.48
    hw = racer.car_w * 0.48
    half_n = _POLY_N // 2
    verts = []
    for i in range(half_n):                            # đuôi → mũi, cạnh PHẢI
        s = -1.0 + 2.0 * i / (half_n - 1)
        w = _car_width_profile(s, hw)
        lx, ly = s * L, w
        verts.append((x + lx*fx + ly*px, y + lx*fy + ly*py))
    for i in range(half_n):                            # mũi → đuôi, cạnh TRÁI
        s = 1.0 - 2.0 * i / (half_n - 1)
        w = _car_width_profile(s, hw)
        lx, ly = s * L, -w
        verts.append((x + lx*fx + ly*px, y + lx*fy + ly*py))
    return verts


def _car_outline_clear(racer, x, y):
    """True nếu TOÀN BỘ viền cong thật của xe (24 đỉnh, đi bộ dọc từng
    cạnh mỗi ~1.5px) tại vị trí (x,y) đều không chạm tường. Thay hẳn
    cho sampling rời rạc kiểu cũ (nose/tail/corner) — không còn khoảng
    hở nào giữa các điểm có thể bị tường "lọt qua" trên ảnh 2D phẳng."""
    verts = _car_polygon_world(racer, x, y)
    n = len(verts)
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        seg = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(seg / _POLY_STEP))
        for k in range(steps + 1):
            t = k / steps
            wx = x0 + (x1 - x0) * t
            wy = y0 + (y1 - y0) * t
            if is_hard_wall(int(wx), int(wy)):
                return False
    return True


def _swept_advance(racer, dx, dy, steps=8):
    """Tìm % quãng đường (dx,dy) tối đa mà xe đi được mà KHÔNG để bất
    kỳ điểm nào trên viền cong thật (24 cạnh) lọt tường. Chặn xe lại
    đúng tại biên — không cho overlap xảy ra trước."""
    if _car_outline_clear(racer, racer.x+dx, racer.y+dy):
        return racer.x+dx, racer.y+dy, False
    lo, hi, ok = 0.0, 1.0, 0.0
    for _ in range(steps):
        mid = (lo+hi)*0.5
        if _car_outline_clear(racer, racer.x+dx*mid, racer.y+dy*mid):
            ok, lo = mid, mid
        else:
            hi = mid
    return racer.x+dx*ok, racer.y+dy*ok, True


def resolve_wall_collision(racer, tx, ty, fx, fy, dt):
    """
    ── PATCH FIX: xử lý va chạm tường ───────────────────────────────
    Phân loại góc va chạm và áp dụng phản lực + ma sát.
    """
    # Vector pháp tuyến (normal) giả định ngược hướng xe
    nx, ny = -fx, -fy
    tangent = (-ny, nx)

    # Vận tốc hiện tại (px/s)
    v_px = racer.velocity * _MOVE_SCALE

    # Phân rã vận tốc thành vuông góc + song song
    v_n = v_px * (fx * nx + fy * ny)
    v_t = v_px - v_n

    # Phân loại góc va chạm
    approach_cos = abs(v_n) / (abs(v_px) + 1e-6)
    if approach_cos > 0.55:
        # HEAD-ON: bật ngược, dừng lại
        v_n *= -0.5
        v_t *= 0.2
    else:
        # GLANCING: trượt song song
        v_n *= -0.3
        v_t *= 0.85

    # Cập nhật vận tốc mới
    racer.velocity = (v_n + v_t) / _MOVE_SCALE

    # Đẩy xe ra khỏi tường theo normal
    racer.x = tx + nx * 2.0
    racer.y = ty + ny * 2.0
    racer._cached_normal = (nx, ny)


def move_car(racer, dt: float) -> None:
    """
    Cập nhật vị trí racer theo wall-align physics.
    Được gọi từ Racer._move(dt) mỗi frame.
    """
    fx, fy = fwd_vec(getattr(racer, '_move_dir', racer.angle))
    spd = racer.velocity * _MOVE_SCALE
    vx, vy = fx * spd, fy * spd

    # ── [A] ESCAPE: xe đang NẰM TRONG tường ──────────────────────────
    if is_hard_wall(int(racer.x), int(racer.y)):
        for dist in [6, 12, 20, 32, 48]:
            for a_deg in range(0, 360, 30):
                ar = math.radians(a_deg)
                ex = racer.x + math.cos(ar) * dist
                ey = racer.y + math.sin(ar) * dist
                if not is_hard_wall(int(ex), int(ey)) and not is_offroad(ex, ey):
                    racer.x, racer.y = ex, ey
                    racer.velocity   = max(abs(racer.velocity) * 0.2, 3.0)
                    racer._cached_normal = None
                    return
        racer.velocity *= 0.5
        return

    # ── [B] Swept collision ──────────────────────────────────────────
    tx, ty, _hit_wall = _swept_advance(racer, vx * dt, vy * dt)

    if not _hit_wall:
        if not is_offroad(tx, ty):
            racer.x, racer.y = tx, ty
        elif not is_offroad(tx, racer.y):
            racer.x = tx
            racer.velocity *= 0.82 ** dt
        elif not is_offroad(racer.x, ty):
            racer.y = ty
            racer.velocity *= 0.82 ** dt
        else:
            racer.velocity *= 0.30 ** dt
    else:
        # ── [C] Va chạm tường → gọi xử lý phản lực ───────────────────
        resolve_wall_collision(racer, tx, ty, fx, fy, dt)

# =====================================================================
# CAR-TO-CAR COLLISION — OBB / SAT
# =====================================================================

_COLL_E = 0.35
# Kiểu: float (0.0 – 1.0)
# Ý nghĩa vật lý: hệ số phục hồi (coefficient of restitution).
#   0.0 = va chạm hoàn toàn không đàn hồi (dính chặt)
#   1.0 = va chạm hoàn toàn đàn hồi (nảy lại 100%)
#   0.35 = xe đua thực tế: nảy vừa phải, mất ~65% năng lượng khi va.
# Dùng trong công thức impulse:
#   impulse = (1 + COLL_E) * (afp - bfp) * 0.5

_COLL_ANG = 0.055
# Kiểu: float
# Mục đích: hệ số spin khi va chạm lệch tâm.
# Công thức: angle_change = cross_product * impulse * COLL_ANG
# cross_product = a_fx * cny - a_fy * cnx
#   = sin(góc giữa hướng xe và collision normal)
#   → càng lệch tâm (đâm vào hông) → cross_product càng lớn → spin nhiều
# 0.055 = thực nghiệm: đủ để thấy xe xoay khi đâm, không quá bạo lực.

_COLL_ITERS = 5
# Kiểu: int
# Mục đích: số lần resolve collision per frame.
# Lý do cần nhiều pass: khi 3+ xe cluster (vd tại vạch xuất phát),
#   1 pass chỉ tách 2 xe, nhưng tách xong xe A lại chồng xe C.
#   5 pass = đủ cho 6 xe giải quyết hết chain reaction mỗi frame.
# Ảnh hưởng CPU: 5 * C(6,2) = 5 * 15 = 75 lần check SAT per frame.

_MAX_IMPULSE = 28.0
# Kiểu: float (kph)
# Mục đích: giới hạn tối đa thay đổi velocity từ 1 va chạm.
# Lý do: không có cap → xe đâm ở 200 kph có thể làm xe khác bị
#   đẩy lùi -60 kph trong 1 frame → cảm giác không thực tế.
# 28 kph: thay đổi tối đa = ~15% top speed xe tier A (188 kph).


def _obb_sat(ax, ay, a_ang, a_hw, a_hh,
             bx, by, b_ang, b_hw, b_hh):
    """
    SAT (Separating Axis Theorem) collision giữa 2 OBB.
    Trả về (collision: bool, nx: float, ny: float, depth: float).

    ── THUẬT TOÁN SAT ────────────────────────────────────────────────
    Hai hình chữ nhật KHÔNG va chạm khi tồn tại ít nhất 1 trục
    phân tách (separating axis) mà projection 2 hình lên trục đó
    không overlap.

    Với 2 OBB: kiểm tra 4 trục tiềm năng (2 cạnh của mỗi hình).
    Nếu tất cả 4 trục đều overlap → va chạm.
    Trục có overlap nhỏ nhất = minimum penetration axis →
      normal va chạm = hướng đẩy xe ra.

    ── BIẾN ─────────────────────────────────────────────────────────

    afx, afy — forward vector của xe A (cos angle_A, sin angle_A)
    arx, ary — right vector của xe A = (-afy, afx) = vuông góc +90°
    bfx, bfy, brx, bry — tương tự cho xe B

    ddx, ddy — vector từ tâm A đến tâm B (offset vector)

    4 trục kiểm tra: (afx,afy), (arx,ary), (bfx,bfy), (brx,bry)
    = 2 cạnh của A và 2 cạnh của B (SAT chuẩn cho 2D OBB)

    Với mỗi trục (nx, ny):
      a_ext — half-extent của A chiếu lên trục
        = |dot(A_forward, axis)| * a_hh + |dot(A_right, axis)| * a_hw
        Ý nghĩa: "chiều rộng" của A nhìn từ hướng axis.

      b_ctr — offset tâm B so với tâm A chiếu lên trục
        = dot(ddx, ddy, axis)
        Ý nghĩa: khoảng cách giữa 2 tâm theo hướng axis.

      b_ext — half-extent của B chiếu lên trục (tương tự a_ext)

      sep — khoảng cách giữa 2 hình theo trục này
        = |b_ctr| - (a_ext + b_ext)
        sep > 0: có khoảng trống → trục phân tách → KHÔNG va chạm
        sep < 0: overlap → -sep = depth (độ xuyên thấu)

    min_depth, best_nx, best_ny:
      Trục có sep âm nhỏ nhất (ít overlap nhất) = minimum penetration.
      Normal = hướng đẩy xe ra = (nx, ny) * sign(b_ctr)
      depth = -sep = độ sâu xuyên thấu (px)
    """
    afx = math.cos(math.radians(a_ang));  afy = math.sin(math.radians(a_ang))
    arx = -afy;                           ary =  afx
    bfx = math.cos(math.radians(b_ang));  bfy = math.sin(math.radians(b_ang))
    brx = -bfy;                           bry =  bfx
    ddx = bx - ax;  ddy = by - ay
    min_depth = 1e9;  best_nx = 1.0;  best_ny = 0.0

    for (nx, ny) in [(afx, afy), (arx, ary), (bfx, bfy), (brx, bry)]:
        a_ext = abs(afx*nx + afy*ny) * a_hh + abs(arx*nx + ary*ny) * a_hw
        b_ctr = ddx*nx + ddy*ny
        b_ext = abs(bfx*nx + bfy*ny) * b_hh + abs(brx*nx + bry*ny) * b_hw
        sep   = abs(b_ctr) - (a_ext + b_ext)
        if sep > 0:
            return False, 0.0, 0.0, 0.0  # trục phân tách → không va chạm
        depth = -sep
        if depth < min_depth:
            min_depth = depth
            sign      = 1.0 if b_ctr >= 0 else -1.0
            best_nx   = nx * sign
            best_ny   = ny * sign

    return True, best_nx, best_ny, min_depth


def handle_car_collisions(racers: list, dt: float) -> None:
    """
    OBB collision resolution với impulse-based physics.
    Gọi mỗi frame trong main loop, sau khi tất cả xe đã update.

    ── THUẬT TOÁN ────────────────────────────────────────────────────
    _COLL_ITERS passes per frame:
      Pass 0: tách xe (position) + tính velocity impulse
      Pass 1-4: chỉ tách xe (giải quyết chain reaction)

    ── BIẾN TRONG HÀM ────────────────────────────────────────────────

    a_hw, a_hh — half-width và half-height của hitbox xe A (px)
      = car_w * 0.48, car_h * 0.48
      0.48 thay vì 0.5: hitbox nhỏ hơn sprite 4% → cảm giác không quá "tight"

    coll, cnx, cny, depth — kết quả từ _obb_sat()
      cnx, cny: collision normal (hướng từ A → B)
      depth: độ overlap (px)

    push — lượng đẩy xe ra mỗi pass (px)
      = depth * 0.52 + 0.8
      52% overlap mỗi bên + 0.8px buffer → sau 1 pass xe cách nhau đủ

    afp — velocity của A chiếu lên collision normal
      = dot(A_forward_vec, collision_normal) * A.velocity
      Ý nghĩa: tốc độ A theo hướng A→B
      afp > 0: A đang tiến về phía B
      afp < 0: A đang lui xa B

    bfp — tương tự cho B
      Điều kiện xử lý: afp - bfp > 0
      = A đang tiến về B nhanh hơn B tiến về A
      = 2 xe đang tiếp cận nhau → cần impulse

    frontal — mức độ "thẳng mặt" của va chạm
      = |dot(A_forward, collision_normal)|
      1.0: A đâm thẳng vào B (frontal)
      0.0: A đi song song với B (lateral/side)
      Ngưỡng 0.40: >= 0.40 = frontal, < 0.40 = lateral

    imp — impulse lực đẩy (kph)
      Frontal: imp = (1 + COLL_E) * (afp - bfp) * 0.5
        Công thức va chạm đàn hồi 1 chiều (equal mass)
        cap tại MAX_IMPULSE để tránh pushback cực đoan
      Lateral: không dùng imp, chỉ friction

    fric — hệ số ma sát khi cọ hông (lateral)
      = min(0.08, depth * 0.005)
      Proportional với độ overlap: chồng nhiều = ma sát lớn hơn
    """
    n = len(racers)
    for iteration in range(_COLL_ITERS):
        for i in range(n):
            for j in range(i + 1, n):
                a, b = racers[i], racers[j]
                # KHÔNG skip xe finished — vật lý xe-chạm-xe
                # phải hoạt động mọi lúc, kể cả sau RACE COMPLETE
                # (fix bug: xe đè lên nhau sau khi đua xong)

                # Tích hợp FUNCTION 06 bước 5 — xem giải thích đầy đủ ở
                # handle_capsule_collisions() phía trên (cùng lý do).
                if getattr(a, "_no_collide_t", 0.0) > 0.0 or getattr(b, "_no_collide_t", 0.0) > 0.0:
                    continue

                # Broad-phase: bỏ qua cặp quá xa (tối ưu CPU)
                if (b.x-a.x)**2 + (b.y-a.y)**2 > 200*200:
                    continue

                a_hw = a.car_w * 0.48;  a_hh = a.car_h * 0.48
                b_hw = b.car_w * 0.48;  b_hh = b.car_h * 0.48

                coll, cnx, cny, depth = _obb_sat(
                    a.x, a.y, a.angle, a_hw, a_hh,
                    b.x, b.y, b.angle, b_hw, b_hh
                )
                if not coll or depth < 0.1:
                    continue

                # FIX 4: cap push tại 4px/frame
                # Cũ: depth lớn → push lớn → nhân 5 iters → teleport 30px
                # Mới: tối đa 4px/frame × 5 iters = 20px total, mượt hơn
                push = min(depth * 0.52 + 0.8, 4.0)
                a.x -= cnx * push;  a.y -= cny * push
                b.x += cnx * push;  b.y += cny * push

                if iteration > 0:
                    continue  # velocity chỉ tính pass 0

                a_fx, a_fy = fwd_vec(a.angle)
                b_fx, b_fy = fwd_vec(b.angle)
                afp = (a_fx * cnx + a_fy * cny) * a.velocity
                bfp = (b_fx * cnx + b_fy * cny) * b.velocity
                if afp - bfp <= 0:
                    continue  # đang tách ra → không cần impulse

                frontal = abs(a_fx * cnx + a_fy * cny)

                if frontal > 0.40:
                    # FRONTAL: impulse mạnh + spin
                    imp = min((1 + _COLL_E) * (afp - bfp) * 0.5, _MAX_IMPULSE)
                    a.velocity -= imp * 0.88
                    b.velocity += imp * 0.70
                    cross_a = a_fx * cny - a_fy * cnx
                    cross_b = b_fx * cny - b_fy * cnx
                    raw_da  = cross_a * imp * _COLL_ANG
                    raw_db  = cross_b * imp * _COLL_ANG
                    # Cap 2.5°/collision — ngăn spin tích lũy
                    # Khi bám tường (_wall_contact_t>0): giảm 70%
                    # → xe không bị xoay 180° do bị đè sát tường
                    wall_damp_a = 0.30 if getattr(a,'_wall_contact_t',0)>0 else 1.0
                    wall_damp_b = 0.30 if getattr(b,'_wall_contact_t',0)>0 else 1.0
                    MAX_SPIN = 2.5
                    a.angle -= clamp(raw_da * wall_damp_a, -MAX_SPIN, MAX_SPIN)
                    b.angle += clamp(raw_db * wall_damp_b, -MAX_SPIN, MAX_SPIN)
                else:
                    # LATERAL: chỉ friction + đẩy nhẹ
                    fric = min(0.08, depth * 0.005)
                    a.velocity *= (1.0 - fric)
                    b.velocity *= (1.0 - fric)
                    if afp - bfp > 3.0:
                        g = min((afp - bfp) * 0.20, 10.0)
                        a.velocity -= g * 0.40
                        b.velocity += g * 0.32

                a.velocity = clamp(a.velocity, -a.max_speed * 0.35, a.max_speed * 1.05)
                b.velocity = clamp(b.velocity, -b.max_speed * 0.35, b.max_speed * 1.05)


# =====================================================================
# CAPSULE-CAPSULE COLLISION (thay thế OBB)
# =====================================================================
# Capsule = đường thẳng (spine) + bán kính r
# Spine của xe = từ đuôi đến mũi theo trục dọc xe
# r = car_w / 2 (nửa chiều rộng xe)
#
# Ưu điểm so với OBB:
#   - Không có góc nhọn → không bị "snagging" (mắc góc)
#   - Normal va chạm luôn xác định rõ ràng
#   - Gần với hình dạng thực của xe đua hơn (bumper tròn)
# =====================================================================

def _closest_points_segments(p1, p2, q1, q2):
    """
    Tìm 2 điểm gần nhất giữa đoạn thẳng P (p1→p2) và Q (q1→q2).
    Trả về (cp, cq): điểm gần nhất trên P và trên Q.

    Thuật toán Ericson (Real-Time Collision Detection, 2005):
      Tham số hoá: P(s) = p1 + s*(p2-p1), Q(t) = q1 + t*(q2-q1)
      s, t ∈ [0,1] → tìm s,t sao cho |P(s)-Q(t)| nhỏ nhất.

    Biến:
      d1 = p2 - p1   : direction vector của P
      d2 = q2 - q1   : direction vector của Q
      r  = p1 - q1   : vector từ q1 đến p1
      a  = dot(d1,d1): |d1|² (độ dài² của P)
      e  = dot(d2,d2): |d2|² (độ dài² của Q)
      f  = dot(d2,r) : projection của r lên d2
      b  = dot(d1,d2): cosine giữa 2 đoạn (nhân với độ dài)
      c  = dot(d1,r) : projection của r lên d1
      denom = a*e - b*b : sin²(angle) * |d1|² * |d2|² ≠ 0 nếu không song song
    """
    d1x, d1y = p2[0]-p1[0], p2[1]-p1[1]
    d2x, d2y = q2[0]-q1[0], q2[1]-q1[1]
    rx,  ry  = p1[0]-q1[0], p1[1]-q1[1]

    a = d1x*d1x + d1y*d1y   # |d1|²
    e = d2x*d2x + d2y*d2y   # |d2|²
    f = d2x*rx  + d2y*ry    # dot(d2, r)

    if a < 1e-6 and e < 1e-6:
        # Cả 2 đều là điểm (độ dài ≈ 0)
        return p1, q1

    if a < 1e-6:
        # P là điểm, Q là đoạn → chiếu p1 lên Q
        s = 0.0
        t = clamp(f / e, 0.0, 1.0)
    else:
        c = d1x*rx + d1y*ry  # dot(d1, r)
        if e < 1e-6:
            # Q là điểm, P là đoạn → chiếu q1 lên P
            t = 0.0
            s = clamp(-c / a, 0.0, 1.0)
        else:
            b     = d1x*d2x + d1y*d2y  # dot(d1, d2)
            denom = a*e - b*b           # sin²θ × |d1|² × |d2|²
            if denom > 1e-6:
                # 2 đoạn không song song → có nghiệm duy nhất
                s = clamp((b*f - c*e) / denom, 0.0, 1.0)
            else:
                # Song song → chọn s=0 (arbitrary)
                s = 0.0

            # Tính t từ s đã biết
            t = (b*s + f) / e
            if t < 0.0:
                t = 0.0;  s = clamp(-c / a, 0.0, 1.0)
            elif t > 1.0:
                t = 1.0;  s = clamp((b - c) / a, 0.0, 1.0)

    cp = (p1[0] + s*d1x, p1[1] + s*d1y)  # điểm gần nhất trên P
    cq = (q1[0] + t*d2x, q1[1] + t*d2y)  # điểm gần nhất trên Q
    return cp, cq


def handle_capsule_collisions(racers: list, dt: float) -> None:
    """
    Capsule collision resolution — hitbox đường cong (spine + radius).
    Thay thế cho handle_car_collisions() khi muốn va chạm mượt hơn.

    Mỗi xe là 1 capsule:
      Spine: từ đuôi xe → mũi xe (theo trục dọc, độ dài = car_h * 0.44)
      Radius: car_w * 0.48 / 2

    ── PHÂN LOẠI VA CHẠM ────────────────────────────────────────────
    approach_cos = |dot(v_rel, normal)| / |v_rel|
      → approach_cos cao: 2 xe lao thẳng vào nhau  → ĐẬP MẠNH
      → approach_cos thấp: 2 xe đi cùng chiều, cọ nhau → XÔ XÁT

    Ngưỡng: _CAPS_FRONTAL_THRESH = 0.40
      Frontal (>0.40): impulse đẩy mạnh + spin góc
      Lateral (≤0.40): friction giảm tốc nhẹ

    ── BIẾN TRONG HÀM ───────────────────────────────────────────────
    """
    n = len(racers)
    for _ in range(_COLL_ITERS):
        for i in range(n):
            for j in range(i + 1, n):
                a, b = racers[i], racers[j]
                # KHÔNG skip xe finished — vật lý xe-chạm-xe
                # phải hoạt động mọi lúc, kể cả sau RACE COMPLETE
                # (fix bug: xe đè lên nhau sau khi đua xong)

                # Tích hợp FUNCTION 06 (teleport_recovery, twodss_racer_v2.py)
                # bước 5 "Disable collision 0.5s": xe vừa teleport ra khỏi
                # tường cần được BỎ QUA va chạm trong _no_collide_t giây,
                # nếu không xe khác có thể đẩy nó ngay lại vào đúng chỗ vừa
                # thoát. getattr(...,0.0): an toàn nếu dùng với Racer không
                # có field này (ví dụ bản v1 cũ), không lỗi, coi như = 0.
                if getattr(a, "_no_collide_t", 0.0) > 0.0 or getattr(b, "_no_collide_t", 0.0) > 0.0:
                    continue

                # Broad-phase
                if (b.x-a.x)**2 + (b.y-a.y)**2 > 220*220:
                    continue

                # ── Tính spine của mỗi xe ─────────────────────────
                # half_len: nửa chiều dài spine (px)
                # = car_h * 0.44 (nhỏ hơn sprite một chút)
                ra = a.car_w * 0.5 * 0.92   # FIX: radius = nửa rộng xe
                rb = b.car_w * 0.5 * 0.92

                # ra = radius của xe a = nửa chiều rộng hitbox
                # FIX: spine = nửa dài TRỪ radius (capsule nhô bán cầu 2 đầu)
                # Bug cũ: hlen=car_h*0.44 không trừ r → hitbox dài hơn xe 40%
                a_hlen = max(a.car_h * 0.5 - ra, 4.0)
                b_hlen = max(b.car_h * 0.5 - rb, 4.0)

                # Tính forward vector của mỗi xe (trục dọc)
                a_fx, a_fy = fwd_vec(a.angle)
                b_fx, b_fy = fwd_vec(b.angle)

                # Spine: từ đuôi đến mũi
                # a_p1 = đuôi xe A, a_p2 = mũi xe A
                a_p1 = (a.x - a_fx*a_hlen, a.y - a_fy*a_hlen)
                a_p2 = (a.x + a_fx*a_hlen, a.y + a_fy*a_hlen)
                b_p1 = (b.x - b_fx*b_hlen, b.y - b_fy*b_hlen)
                b_p2 = (b.x + b_fx*b_hlen, b.y + b_fy*b_hlen)

                # ── Tìm điểm gần nhất giữa 2 spine ───────────────
                # (KHÔNG phụ thuộc radius — chỉ là hình học 2 đoạn thẳng,
                # nên tính trước, taper radius sau vẫn an toàn)
                cp, cq = _closest_points_segments(a_p1, a_p2, b_p1, b_p2)

                # sa, sb — vị trí điểm chạm dọc thân xe (-1=đuôi, 0=tâm, +1=mũi)
                #   = chiếu (contact - tâm) lên forward vector / hlen
                # Tính SỚM (trước khi check va chạm) vì cần để taper radius.
                sa = ((cp[0]-a.x)*a_fx + (cp[1]-a.y)*a_fy) / max(a_hlen,1.0)
                sb = ((cq[0]-b.x)*b_fx + (cq[1]-b.y)*b_fy) / max(b_hlen,1.0)
                sa = clamp(sa,-1.0,1.0);  sb = clamp(sb,-1.0,1.0)

                # ── TAPER bán kính ở mũi/đuôi ─────────────────────
                # Capsule cũ: bán kính CỐ ĐỊNH suốt chiều dài (như xúc
                # xích) → 2 đầu phình rộng hơn hình xe thật (PNG đã cắt
                # nền, mũi/đuôi thu nhỏ dần) → đẩy xe khác/tường xa hơn
                # mức cần thiết. Taper: thu nhỏ bán kính dần về 2 đầu
                # (sa²/sb² = 0 ở tâm, 1 ở mũi/đuôi) — khớp hình hexagon
                # thu hẹp 2 đầu như sprite thật, không còn "phình".
                _TAPER = 0.35   # giảm tối đa 35% bán kính tại mũi/đuôi
                ra_t = ra * (1.0 - _TAPER * sa*sa)
                rb_t = rb * (1.0 - _TAPER * sb*sb)

                # dx, dy = vector từ điểm gần nhất của B → A
                dx = cp[0] - cq[0]
                dy = cp[1] - cq[1]
                # d = khoảng cách giữa 2 điểm gần nhất
                d  = math.hypot(dx, dy)

                # sum_r = tổng bán kính ĐÃ TAPER (ngưỡng va chạm)
                sum_r = ra_t + rb_t

                if d >= sum_r or d < 0.01:
                    # Không va chạm hoặc tâm trùng nhau (degenerate)
                    continue

                # ── Normal va chạm ────────────────────────────────
                # cnx, cny = collision normal (từ B về phía A)
                # = vector đẩy A ra xa B
                inv_d = 1.0 / d
                cnx   = dx * inv_d   # normal x (đơn vị)
                cny   = dy * inv_d   # normal y (đơn vị)

                # depth = mức độ xuyên thấu (px)
                # = tổng radius (đã taper) - khoảng cách thực tế
                depth = sum_r - d

                # lat — thành phần NGANG của lực so với thân xe
                #   = cross(forward, normal) ∈ [-1,1]
                #   lực dọc thân (húc đuôi thẳng) → lat≈0 → không xoay
                #   lực ngang thân (đâm hông)     → |lat|≈1 → xoay tối đa
                lat_a = a_fx*cny - a_fy*cnx
                lat_b = b_fx*cny - b_fy*cnx

                push = depth * 0.52 + 0.8

                # Phân bổ push: chạm càng xa tâm → càng nhiều XOAY, ít TỊNH TIẾN
                #   rot_frac = |s| × 0.65  (tâm: 100% tịnh tiến, mũi: chỉ 35%)
                rot_a = abs(sa) * 0.65
                rot_b = abs(sb) * 0.65
                a.x += cnx*push*(1.0-rot_a);  a.y += cny*push*(1.0-rot_a)
                b.x -= cnx*push*(1.0-rot_b);  b.y -= cny*push*(1.0-rot_b)

                # Torque: τ = vị_trí_chạm × lực_ngang
                #   đâm mũi (sa=+1) lực sang phải (lat=+1) → mũi văng phải
                #   (angle tăng = clockwise trong hệ pygame y-down)
                # Torque CHỈ khi xe đang chạy (đứng yên không có động năng
                # để xoay) → tránh xoay loạn tại grid lúc countdown.
                # Hệ số 0.45 (giảm từ 1.1) cho cảm giác tự nhiên.
                spd_factor = min(abs(a.velocity) / 30.0, 1.0)
                a.angle += sa * lat_a * push * 0.45 * spd_factor
                spd_factor_b = min(abs(b.velocity) / 30.0, 1.0)
                b.angle -= sb * lat_b * push * 0.45 * spd_factor_b

                # ── Velocity impulse (chỉ pass đầu) ──────────────
                # afp = tốc độ xe A chiếu lên normal (px/s)
                # afp > 0: A đang lao về phía B
                afp = (a_fx*cnx + a_fy*cny) * a.velocity
                bfp = (b_fx*cnx + b_fy*cny) * b.velocity

                # Chỉ xử lý khi 2 xe đang tiếp cận nhau
                rel = afp - bfp   # relative approach speed
                if rel <= 0:
                    continue

                # approach_cos: mức độ "thẳng mặt"
                # = |v_rel chiếu lên normal| / |v_rel|
                # Dùng dot product của forward A với normal
                approach_cos = abs(a_fx*cnx + a_fy*cny)

                if approach_cos > 0.40:
                    # ── ĐẬP MẠNH (FRONTAL) ───────────────────────
                    # Công thức impulse va chạm đàn hồi 1 chiều (equal mass):
                    #   imp = (1 + e) × rel / 2
                    # Cap tại _MAX_IMPULSE để tránh pushback cực đoan
                    imp = min((1 + _COLL_E) * rel * 0.5, _MAX_IMPULSE)
                    a.velocity -= imp * 0.88  # A bị thụt lùi
                    b.velocity += imp * 0.70  # B bị đẩy tiến

                    # Angular impulse: xe xoay khi đâm lệch tâm
                    # cross = sin(góc lệch giữa hướng xe và normal)
                    # Lớn khi đâm vào hông → spin nhiều
                    cross_a = a_fx*cny - a_fy*cnx
                    cross_b = b_fx*cny - b_fy*cnx
                    a.angle -= cross_a * imp * _COLL_ANG
                    b.angle += cross_b * imp * _COLL_ANG
                    # MỚI: xoay luôn _move_dir theo 1 NỬA mức xoay angle —
                    # nếu không, sau va chạm góc mũi xe (angle) và hướng
                    # di chuyển thật (_move_dir) lệch quá xa nhau, lúc đó
                    # nếu chạm tường thì công thức ma sát ở move_car() sẽ
                    # coi lệch hướng quá lớn → "ăn" gần hết tốc độ mỗi
                    # frame dù đang giữ W → cảm giác y như WASD không phản hồi.
                    a._move_dir = getattr(a, '_move_dir', a.angle) - cross_a * imp * _COLL_ANG * 0.5
                    b._move_dir = getattr(b, '_move_dir', b.angle) + cross_b * imp * _COLL_ANG * 0.5

                else:
                    # ── XÔ XÁT (LATERAL/SCRAPING) ────────────────
                    # Friction tỉ lệ với độ overlap:
                    #   depth lớn → cọ nhiều → friction lớn hơn
                    # min(0.08): giới hạn tối đa 8% tốc độ / lần cọ
                    fric = min(0.08, depth * 0.005)
                    a.velocity *= (1.0 - fric)
                    b.velocity *= (1.0 - fric)
                    # Thêm 1 chút đẩy ngang nếu chênh tốc độ đủ lớn
                    if rel > 3.0:
                        g = min(rel * 0.18, 8.0)
                        a.velocity -= g * 0.35
                        b.velocity += g * 0.28

                a.velocity = clamp(a.velocity, -a.max_speed*0.35, a.max_speed*1.05)
                b.velocity = clamp(b.velocity, -b.max_speed*0.35, b.max_speed*1.05)
"""
=====================================================================
TWODSS_MAP_DATA.PY  —  Dữ liệu map đua của 2D Sideway Showdown
=====================================================================

MỤC TIÊU:
    File này là "nguồn sự thật duy nhất" (single source of truth) cho
    toàn bộ danh sách map đua trong game. Mọi module khác như
    twodss_mapselect.py, game engine, leaderboard... đều import từ
    đây thay vì tự khai báo riêng — tránh data bị lệch giữa các file.

TƯ DUY THIẾT KẾ:
    - Tách data hoàn toàn ra khỏi logic UI, giống cách twodss_car_data.py
      phục vụ cho twodss_showroom.py. Khi cần thêm map mới, dev chỉ
      cần mở đúng 1 file này, không cần động vào bất kỳ file UI nào.
    - Mỗi map là 1 dict độc lập, dễ đọc, dễ copy-paste để nhân bản.
    - Trường "coming_soon" kiểm soát khóa/mở map mà không cần xóa
      dòng data — tiện preview / teaser trước khi map sẵn sàng.

Ý ĐỊNH & SÁNG KIẾN:
    - Helper functions ở cuối file (get_map_by_id, get_available_maps)
      giúp các module khác truy vấn nhanh, không cần tự lọc list.
    - Trường "file" tách riêng khỏi "name" — tên file thumbnail có thể
      đổi (rename, re-export) mà không ảnh hưởng text hiển thị trên UI.
    - Trường "preview_color" là màu fallback khi file thumbnail chưa có,
      mỗi map mang một sắc thái màu gợi lên không khí đường đua đó.

CẤU TRÚC MỖI ENTRY:
    "id"           : str       — key định danh duy nhất, dùng trong engine
    "name"         : str       — tên hiển thị trên UI
    "file"         : str       — tên file KHÔNG có đuôi, trong assets/map_thumbnails/
    "coming_soon"  : bool      — True = khoá LET'S RACE + hiện dấu "?"
    "preview_color": (R, G, B) — màu nền fallback khi thiếu thumbnail

THÊM MAP MỚI:
    Copy 1 block dict ở dưới, điền thông tin, đặt coming_soon = False.

TÊN FILE THUMBNAIL (trong assets/map_thumbnails/):
    greenwood-circuit-thumbnail.png
    sportpit-track-thumbnail.png
    sandy-circuit-thumbnail.png        ← không có hậu tố -thumbnail
    velodrama-thumbnail.png
    commingsoon-thumbnail.png
=====================================================================
"""

# =====================================================================
# DANH SÁCH MAP
# =====================================================================
MAP_LIST = [

    # ── MAP 1 ─────────────────────────────────────────────────────────
    {
        "id"            : "greenwood_circuit",
        "name"          : "GREENWOOD CIRCUIT",
        "file"          : "greenwood-circuit-thumbnail",
        "coming_soon"   : False,
        "preview_color" : (60, 120, 60),    # xanh lá — gợi đường đua cây cối
    },

    # ── MAP 2 ─────────────────────────────────────────────────────────
    {
        "id"            : "sportpit_track",
        "name"          : "SPORTPIT TRACK",
        "file"          : "sportpit-track-thumbnail",
        "coming_soon"   : False,
        "preview_color" : (80, 80, 160),    # xanh tím — kỹ thuật cao
    },

    # ── MAP 3 ─────────────────────────────────────────────────────────
    {
        "id"            : "sandy_circuit",
        "name"          : "SANDY CIRCUIT",
        "file"          : "sandy-circuit-thumbnail",
        "coming_soon"   : False,
        "preview_color" : (180, 140, 60),   # vàng cát — sa mạc
    },

    # ── MAP 4 ─────────────────────────────────────────────────────────
    {
        "id"            : "velodrama_track",
        "name"          : "VELODRAMA TRACK",
        "file"          : "velodrama-thumbnail",
        "coming_soon"   : False,
        "preview_color" : (40, 80, 140),    # xanh đêm — thành phố
    },

    # ══════════════════════════════════════════════════════════════════
    # COMING SOON — 4 slot giữ chỗ, dùng chung 1 ảnh comingsoon-thumbnail.png
    # Khi map mới ra: đổi coming_soon = False, cập nhật id / name / file
    # ══════════════════════════════════════════════════════════════════
    {
        "id"            : "coming_soon_5",
        "name"          : "COMING SOON",
        "file"          : "comingsoon-thumbnail",
        "coming_soon"   : True,
        "preview_color" : (50, 50, 80),
    },
    {
        "id"            : "coming_soon_6",
        "name"          : "COMING SOON",
        "file"          : "comingsoon-thumbnail",
        "coming_soon"   : True,
        "preview_color" : (50, 50, 80),
    },
    {
        "id"            : "coming_soon_7",
        "name"          : "COMING SOON",
        "file"          : "comingsoon-thumbnail",
        "coming_soon"   : True,
        "preview_color" : (50, 50, 80),
    },
    {
        "id"            : "coming_soon_8",
        "name"          : "COMING SOON",
        "file"          : "comingsoon-thumbnail",
        "coming_soon"   : True,
        "preview_color" : (50, 50, 80),
    },

    # ──────────────────────────────────────────────────────────────────
    # THÊM MAP MỚI VÀO ĐÂY — copy block dưới, bỏ dấu # và điền vào
    # ──────────────────────────────────────────────────────────────────
    # {
    #     "id"            : "night_city_loop",
    #     "name"          : "NIGHT CITY LOOP",
    #     "file"          : "night-city-loop-thumbnail",
    #     "coming_soon"   : False,
    #     "preview_color" : (20, 20, 60),
    # },
]

# =====================================================================
# HELPERS — dùng trong twodss_mapselect.py và game engine
# =====================================================================

def get_available_maps():
    """Trả về list chỉ gồm các map có thể chơi ngay (coming_soon = False)."""
    return [m for m in MAP_LIST if not m["coming_soon"]]


def get_map_by_id(map_id: str):
    """
    Tìm và trả về dict map theo id.
    Trả về None nếu không tìm thấy.
    Dùng trong game engine để load đúng file khi bắt đầu race.
    """
    return next((m for m in MAP_LIST if m["id"] == map_id), None)


def get_map_count():
    """Tổng số map trong danh sách, kể cả coming soon."""
    return len(MAP_LIST)
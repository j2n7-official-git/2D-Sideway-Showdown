"""
track-velodrama-circuit.py — Velodrama Circuit (2 TẦNG / OVERPASS)
2D Sideway Showdown | 1v1 hoặc 6 xe | 3 vòng

Điều khiển: W/S ga-phanh  A/D lái  SPACE drift  LCTRL (GIỮ) nitro  ESC thoát

════════════════════════════════════════════════════════════════════
GHI CHÚ KỸ THUẬT — ĐỌC TRƯỚC KHI SỬA (map này KHÁC 3 map trước):
════════════════════════════════════════════════════════════════════
• Đây là map 2 TẦNG (cầu vượt). 1 vòng đua = 1 đường kín đi qua CẢ 2
  tầng, mỗi điểm cắt (ô VÀNG) đi qua đúng 2 lần: 1 lần tầng dưới, 1 lần
  tầng trên — đúng kiểu overpass thật.

      ┌──vòng tai trái──┐        ═══ CẦU (tầng trên) ═══   ┌──vòng tai phải──┐
      │                 ▓VÀNG▓══════════════════════▓VÀNG▓                  │
      │                 │ (lên/xuống cầu)            │ (lên/xuống cầu)      │
      └── đường dọc trái─┘                            └─ đường dọc phải ─────┘
                          └─────── chữ U (tầng dưới) ──────┘

• _WP_ORIG = 100 waypoint tâm-đường, DÒ THẬT từ velodrama-walls.png
  (3200x3200) bằng: mask đường (xanh ∪ vàng) → skeletonize → cắt 2 điểm
  giao → ghép "đi thẳng xuyên qua" tại mỗi giao (overpass) → đi 1 vòng
  kín → resample đều 100 điểm. KHÔNG vẽ tay. → 2 làn = tổng 200 wp.

• _WP_LEVEL[i] song song _WP_ORIG: 0 = tầng DƯỚI (chữ U + 2 đường dọc),
  1 = tầng TRÊN (cầu + 2 vòng tai). Chuyển tầng tại idx 38 (lên cầu,
  bên phải) và idx 94 (xuống cầu, bên trái).

• OCCLUSION (điểm mới so với 3 map trước): khi xe ĐANG Ở TẦNG DƯỚI và
  chui vào VÙNG VÀNG (gầm cầu), xe bị che MỜ DẦN → mất hẳn dưới gầm →
  hiện lại khi đã ra khỏi vùng vàng / hoặc khi đã LÊN tầng trên (lúc đó
  vẽ đè lên cầu = thấy bình thường). Mức che bám theo _WP_LEVEL của
  từng xe (theo wp_idx) + vị trí so với OCCLUDERS, KHÔNG đoán theo toạ
  độ đơn thuần (vì tại ô vàng 2 tầng chồng nhau, toạ độ không phân biệt
  được tầng).

• .EXE: ảnh load qua resource_path() → chạy được cả khi PyInstaller gói
  vào _MEIPASS. Lệnh build mẫu (xem cuối file).
════════════════════════════════════════════════════════════════════
"""
import pygame, math, os, sys, time, random

# ── IMPORTS MODULE (engine dùng chung với 3 map trước) ──────────────
from twodss_hud      import HUD, fmt_time, draw_shadow
from twodss_car_data import CAR_STATS
import twodss_physics as physics
from twodss_racer_v2  import Racer, setup_map, pick_drivers
from twodss_pause import PauseMenu

# ── PATH / RESOURCE (an toàn cho .exe) ──────────────────────────────
def _base_dir():
    if hasattr(sys,"_MEIPASS"): return sys._MEIPASS
    s=os.path.dirname(os.path.abspath(__file__))
    p=os.path.dirname(s)
    for c in [p,s,os.getcwd()]:
        if os.path.isdir(os.path.join(c,"assets")): return c
    return s

BASE_DIR = _base_dir()

def resource_path(rel):
    """Trả đường dẫn asset chạy được cả khi dev lẫn khi đã gói .exe.
    PyInstaller giải nén asset vào sys._MEIPASS lúc runtime."""
    base = sys._MEIPASS if hasattr(sys,"_MEIPASS") else BASE_DIR
    return os.path.join(base, rel)

# KHÔNG đổi tên 2 file png này khi build; nếu đổi phải sửa 2 dòng dưới.
TRACK_PATH     = resource_path(os.path.join("assets","track","velodrama-track.png"))
WALL_MASK_PATH = resource_path(os.path.join("assets","track","velodrama-walls.png"))
NITRO_SMOKE_PATH = resource_path(os.path.join("assets","ui-race-mode","2dss-nitrosmoke.png"))

# ── CONFIG ──────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1920, 1080
FPS             = 90
MAP_SCALE       = 1.5        # ảnh đã 4800x4800 so với 3200x3200 gốc
MAX_LAPS        = 3
CROP_SIZE       = 2250
CAR_SCREEN_X    = SCREEN_W//2
CAR_SCREEN_Y    = int(SCREEN_H*0.62)
COUNTDOWN_START = 6.0

# ── PYGAME ──────────────────────────────────────────────────────────
pygame.init()
try:
    screen=pygame.display.set_mode((SCREEN_W,SCREEN_H),
        pygame.FULLSCREEN|pygame.DOUBLEBUF|pygame.HWSURFACE)
except:
    screen=pygame.display.set_mode((SCREEN_W,SCREEN_H),pygame.DOUBLEBUF)
pygame.display.set_caption("2D Sideway Showdown — Velodrama Circuit")
clock=pygame.time.Clock()

# ── TRACK + WALL MASK ───────────────────────────────────────────────
if not os.path.exists(TRACK_PATH):
    print(f"[CRITICAL] Track PNG not found: {TRACK_PATH}")
    pygame.quit(); sys.exit(1)

track_raw=pygame.image.load(TRACK_PATH).convert()
track=pygame.transform.smoothscale(track_raw,
    (int(track_raw.get_width()*MAP_SCALE),
     int(track_raw.get_height()*MAP_SCALE))) if abs(MAP_SCALE-1)>0.001 else track_raw
MAP_W,MAP_H=track.get_width(),track.get_height()
print(f"[TRACK] {MAP_W}x{MAP_H}")

skid_layer=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA)

wall_mask=None
try:
    wraw=pygame.image.load(WALL_MASK_PATH).convert()
    # scale nearest thay smoothscale: tránh viền xám antialiased làm
    # is_hard_wall() bắt nhầm → 'tường vô hình'.
    wall_mask=pygame.transform.scale(wraw,(MAP_W,MAP_H)) if abs(MAP_SCALE-1)>0.001 else wraw
    print(f"[WALL MASK] {wall_mask.get_size()}")
except FileNotFoundError:
    print(f"[WALL MASK] Not found: {WALL_MASK_PATH}")
except Exception as e:
    print(f"[WALL MASK] {e}")

# ── NITRO SMOKE FX ──────────────────────────────────────────────────
nitro_smoke_img=None
try:
    _ns_raw=pygame.image.load(NITRO_SMOKE_PATH).convert_alpha()
    nitro_smoke_img=pygame.transform.smoothscale(_ns_raw,
        (int(_ns_raw.get_width()*0.4), int(_ns_raw.get_height()*0.4)))
    print(f"[NITRO SMOKE] {nitro_smoke_img.get_size()}")
except FileNotFoundError:
    print("[NITRO SMOKE] Not found —", NITRO_SMOKE_PATH)
except Exception as e:
    print(f"[NITRO SMOKE] {e}")

# ── PHYSICS SETUP ───────────────────────────────────────────────────
# gate_safe: đo từ mask — đường dọc trái tại vạch cờ (y≈1895) rộng
# x≈677..912. Cho khoảng an toàn quanh vạch xuất phát.
physics.setup(
    track      = track,
    wall_mask  = wall_mask,
    map_w      = MAP_W,
    map_h      = MAP_H,
    move_scale = physics.MOVE_SCALE,
    gate_safe  = (
        int(660*MAP_SCALE), int(930*MAP_SCALE),
        int(1820*MAP_SCALE),int(1970*MAP_SCALE),
    ),
)

# ── WAYPOINTS (dò thật từ velodrama-walls.png) ──────────────────────
_WP_ORIG=[
    (795,1895),(793,1999),(791,2102),(788,2205),(787,2310),
    (788,2414),(800,2513),(829,2605),(880,2689),(956,2756),
    (1040,2805),(1133,2832),(1232,2846),(1333,2855),(1437,2855),
    (1542,2855),(1646,2855),(1751,2855),(1853,2851),(1954,2842),
    (2050,2821),(2139,2784),(2220,2728),(2287,2655),(2323,2566),
    (2339,2468),(2344,2366),(2339,2264),(2334,2161),(2329,2059),
    (2324,1957),(2319,1854),(2314,1752),(2308,1650),(2304,1547),
    (2299,1445),(2296,1342),(2296,1237),(2290,1133),(2283,1030),
    (2281,927),(2292,827),(2321,734),(2385,659),(2470,612),
    (2566,592),(2666,600),(2756,635),(2832,700),(2875,786),
    (2892,883),(2874,980),(2826,1065),(2749,1127),(2659,1161),
    (2560,1174),(2457,1177),(2352,1178),(2248,1175),(2144,1174),
    (2040,1173),(1936,1173),(1831,1173),(1727,1173),(1626,1177),
    (1525,1175),(1424,1175),(1328,1174),(1226,1173),(1122,1173),
    (1017,1173),(913,1173),(809,1179),(705,1171),(600,1171),
    (496,1171),(395,1162),(305,1129),(226,1069),(172,987),
    (149,891),(164,794),(198,703),(265,629),(352,587),
    (450,572),(550,585),(639,623),(718,682),(767,766),
    (789,861),(800,961),(804,1064),(803,1168),(807,1272),
    (806,1376),(804,1480),(802,1584),(799,1687),(797,1790),
]
# _WP_LEVEL song song: 1 = tầng TRÊN (cầu+vòng tai), 0 = tầng DƯỚI (U).
_WP_LEVEL=[
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,0,0,0,0,0,0,
]
WAYPOINTS=[(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in _WP_ORIG]

# ── VÙNG CHE (OCCLUDERS) = gầm cầu tại 2 ô vàng (toạ độ đã scale) ────
# Lấy theo bbox ô vàng trong walls.png, nới rộng X theo bề ngang cầu.
# Xe TẦNG DƯỚI nằm trong rect này sẽ bị che (alpha giảm dần).
def _rect(x0,y0,x1,y1):
    return (int(x0*MAP_SCALE),int(y0*MAP_SCALE),int(x1*MAP_SCALE),int(y1*MAP_SCALE))
OCCLUDERS=[
    _rect(660, 1055, 950, 1305),    # ô vàng TRÁI  (gầm cầu trái)
    _rect(2160,1055, 2440,1305),    # ô vàng PHẢI (gầm cầu phải)
]
OCC_FADE = int(150*MAP_SCALE)       # px nới dưới đáy rect để mờ DẦN (không tắt phụt)

# ── DUAL-LANE WAYPOINTS (giống pattern 3 map trước) ─────────────────
_LANE_SPLIT  = 8
_LANE_OFFSET = int(55 * MAP_SCALE)

def _make_lane_wps(wps, offset_x):
    """Lệch offset_x px (trục X) cho _LANE_SPLIT wp đầu (đoạn thẳng xuất
    phát), rồi lerp về tâm trong 6 wp kế. Trả (wps_lệch, level_giữ_nguyên)."""
    result=list(wps); lerp_n=6
    for i in range(len(wps)):
        if i < _LANE_SPLIT:                 ox=offset_x
        elif i < _LANE_SPLIT+lerp_n:        ox=int(offset_x*(1.0-(i-_LANE_SPLIT)/lerp_n))
        else:                               ox=0
        result[i]=(wps[i][0]+ox, wps[i][1])
    return result

WAYPOINTS_LEFT  = _make_lane_wps(WAYPOINTS, -_LANE_OFFSET)
WAYPOINTS_RIGHT = _make_lane_wps(WAYPOINTS, +_LANE_OFFSET)

# ── DENSIFY (nội suy dày) — kèm theo level đồng bộ từng điểm ─────────
WP_DENSE_STEP = 5   # px giữa 2 wp dày

def _densify(wps, levels, step=WP_DENSE_STEP):
    """Nội suy tuyến tính wps thành dày ~step px; trả (dense_wps, dense_level).
    level lấy theo wp NGUỒN của đoạn (giữ ranh giới tầng sắc nét tại ô vàng)."""
    if len(wps)<2: return list(wps), list(levels)
    out=[]; out_lv=[]
    for i in range(len(wps)):
        x0,y0=wps[i]; x1,y1=wps[(i+1)%len(wps)]
        lv=levels[i]
        seg=math.hypot(x1-x0,y1-y0)
        if seg<step:
            out.append((x0,y0)); out_lv.append(lv); continue
        n=max(1,int(seg/step))
        for s in range(n):
            t=s/n
            out.append((int(x0+(x1-x0)*t),int(y0+(y1-y0)*t)))
            out_lv.append(lv)
    return out, out_lv

WAYPOINTS_LEFT_DENSE,  LEVEL_LEFT_DENSE  = _densify(WAYPOINTS_LEFT,  _WP_LEVEL)
WAYPOINTS_RIGHT_DENSE, LEVEL_RIGHT_DENSE = _densify(WAYPOINTS_RIGHT, _WP_LEVEL)
WAYPOINTS_DENSE,       LEVEL_DENSE       = _densify(WAYPOINTS,       _WP_LEVEL)
print(f"[WP] sparse={len(WAYPOINTS)}  dense={len(WAYPOINTS_DENSE)}  "
      f"step={WP_DENSE_STEP}px  lv_trans={[i for i in range(len(_WP_LEVEL)) if _WP_LEVEL[i]!=_WP_LEVEL[i-1]]}")

# ── GATE (vạch xuất phát, đã có cờ vẽ sẵn trong ảnh, trên đường dọc trái) ──
GATE_Y  = int(1895*MAP_SCALE)
GATE_X1 = int(677 *MAP_SCALE)
GATE_X2 = int(912 *MAP_SCALE)

# ── RACER SETUP ─────────────────────────────────────────────────────
setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2,
          max_laps=MAX_LAPS, base_dir=BASE_DIR, map_scale=MAP_SCALE)

# ── GRID SPAWN — 2×3 chữ nhật đều, NGAY TRƯỚC vạch cờ ────────────────
# Cờ ở (≈795,1895) trên đường dọc trái; xe đi XUỐNG (south, +y) → "trước
# cờ" = phía TRÊN cờ (y nhỏ hơn). Hàng đầu cách cờ 40px, các hàng cách
# nhau 100px. 2 cột lệch ±55px quanh tâm đường (x≈795).
_FLAG_X, _FLAG_Y = 795, 1895
_COL_DX = 50
_ROW_TOP =400       # hàng đầu cách cờ 40px
_ROW_GAP  = 160      # các hàng cách nhau 100px
_GRID_SLOTS=[]
for r in range(3):                       # 3 hàng
    y = _FLAG_Y + _ROW_TOP - r * _ROW_GAP # lên phía trên (trước cờ)
    _GRID_SLOTS.append((_FLAG_X-_COL_DX, y))   # cột trái  (slot chẵn)
    _GRID_SLOTS.append((_FLAG_X+_COL_DX, y))   # cột phải (slot lẻ)

# Xe đi xuống → mặt xe hướng south. fwd_vec(90°)=(0,+1) = south.
_SPAWN_ANGLE = 270

def _slot_wp(slot_idx):
    """Trả (dense_wps, dense_level) cho slot (chẵn=làn trái, lẻ=làn phải)."""
    if slot_idx%2==0: return WAYPOINTS_LEFT_DENSE,  LEVEL_LEFT_DENSE
    else:             return WAYPOINTS_RIGHT_DENSE, LEVEL_RIGHT_DENSE

def _slot_pos(i):
    x,y=_GRID_SLOTS[i]; return x*MAP_SCALE, y*MAP_SCALE

_slots=list(range(6)); random.shuffle(_slots)

# ── TẠO XE ─────────────────────────────────────────────────────────
# Đổi NUM_BOTS=1 để 1v1, NUM_BOTS=5 để 6 xe
NUM_BOTS = 5

_p_slot=_slots[0]
px,py=_slot_pos(_p_slot)
_p_wp,_p_lv=_slot_wp(_p_slot)
player=Racer("ferrari_f430_2005", px, py, _SPAWN_ANGLE, is_player=True, waypoints=_p_wp)
player._levels=_p_lv     # bảng tầng theo wp_idx (dùng cho occlusion)
print(f"[PLAYER] grid=P{_p_slot+1}  lane={'L' if _p_slot%2==0 else 'R'}")

_other_cars=[c for c in CAR_STATS.keys() if c!="ferrari_f430_2005"]
_bot_ids=random.sample(_other_cars, min(NUM_BOTS,len(_other_cars)))
_drivers=pick_drivers(NUM_BOTS)

bots=[]
for k in range(NUM_BOTS):
    _b_slot=_slots[k+1]
    bx,by=_slot_pos(_b_slot)
    _b_wp,_b_lv=_slot_wp(_b_slot)
    _name,_country,_aggr=_drivers[k]
    bot=Racer(_bot_ids[k], bx, by, _SPAWN_ANGLE, waypoints=_b_wp,
              driver_name=_name, driver_country=_country, composure=_aggr)
    bot._levels=_b_lv
    bot.wp_idx=min(range(len(_b_wp)),
                   key=lambda i,bx=bx,by=by: math.hypot(_b_wp[i][0]-bx,_b_wp[i][1]-by))
    bot.velocity=k*5.0
    bots.append(bot)
    print(f"[BOT {k+1}] {_bot_ids[k]}  driver={_name} ({_country})  aggr={_aggr:.4f}  "
          f"grid=P{_b_slot+1}  lane={'L' if _b_slot%2==0 else 'R'}")

all_racers=[player]+bots

# ── OCCLUSION HELPER — mức hiện (alpha) của xe theo tầng + gầm cầu ───
def racer_alpha(racer):
    """Trả alpha 0..255. Xe TẦNG TRÊN (level=1) luôn 255 (vẽ đè lên cầu).
    Xe TẦNG DƯỚI (level=0) khi vào vùng vàng (gầm cầu) bị che MỜ DẦN:
      - lọt hẳn trong dải vàng  → alpha 0  (mất dưới gầm)
      - ngay dưới đáy vùng vàng → alpha tăng dần theo OCC_FADE
      - ngoài vùng              → 255
    Ranh giới tầng đọc theo wp_idx (không đoán theo toạ độ vì 2 tầng
    chồng nhau tại ô vàng)."""
    lv=1
    levels=getattr(racer,'_levels',None)
    if levels:
        i=getattr(racer,'wp_idx',0)
        i=max(0,min(i,len(levels)-1))
        lv=levels[i]
    if lv==1:
        return 255                          # tầng trên: luôn rõ
    # tầng dưới: kiểm tra gầm cầu
    rx,ry=racer.x,racer.y
    a=255
    for x0,y0,x1,y1 in OCCLUDERS:
        if x0<=rx<=x1:
            if y0<=ry<=y1:                  # trong dải vàng → khuất hẳn
                return 0
            if y1<ry<=y1+OCC_FADE:          # ngay dưới gầm → mờ dần
                a=min(a, int(255*(ry-y1)/OCC_FADE))
            elif y0-OCC_FADE<=ry<y0:        # ngay trên gầm → mờ dần
                a=min(a, int(255*(y0-ry)/OCC_FADE))
    return max(0,a)

# ── HELPERS ─────────────────────────────────────────────────────────
def fwd_vec(a):
    r=math.radians(a); return math.cos(r),math.sin(r)

def draw_skid(racer, dt):
    if not racer.is_player: return
    hw,hh=racer.car_w//2,racer.car_h//2
    fx,fy=fwd_vec(racer.angle); px2,py2=-fy,fx
    for side in(-1,1):
        wx=racer.x-fx*hh*0.6+px2*hw*0.7*side
        wy=racer.y-fy*hh*0.6+py2*hw*0.7*side
        ix,iy=int(wx),int(wy)
        if 0<=ix<MAP_W and 0<=iy<MAP_H:
            pygame.draw.circle(skid_layer,(50,50,50,200),(ix,iy),3)

def render_world(player):
    crop=pygame.Surface((CROP_SIZE,CROP_SIZE)); crop.fill((26,30,42))
    ox=CROP_SIZE//2-int(player.x); oy=CROP_SIZE//2-int(player.y)
    crop.blit(track,(ox,oy)); crop.blit(skid_layer,(ox,oy))
    for bot in bots:
        if not bot.visible:
            continue
        a=racer_alpha(bot)          # ← occlusion 2 tầng
        if a<=0:                    # khuất hẳn dưới gầm cầu → bỏ vẽ
            continue
        bx2=CROP_SIZE//2+int(bot.x-player.x)
        by2=CROP_SIZE//2+int(bot.y-player.y)
        if nitro_smoke_img is not None and bot.nitro_active and a>=255:
            fx,fy=fwd_vec(bot.angle)
            sx2=bx2-fx*bot.car_h*0.5; sy2=by2-fy*bot.car_h*0.5
            smoke=pygame.transform.rotate(nitro_smoke_img,270-bot.angle)
            crop.blit(smoke,smoke.get_rect(center=(sx2,sy2)))
        spr=pygame.transform.rotate(bot.sprite,270-bot.angle)
        if a<255:                   # mờ dần khi chui gầm cầu
            spr=spr.copy(); spr.set_alpha(a)
        crop.blit(spr,spr.get_rect(center=(bx2,by2)))
    rot=pygame.transform.rotate(crop,90.0+player.angle)
    screen.fill((0,0,0))
    screen.blit(rot,rot.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))
    if nitro_smoke_img is not None and player.nitro_active:
        sx=CAR_SCREEN_X; sy=CAR_SCREEN_Y+player.car_h*0.5
        screen.blit(nitro_smoke_img, nitro_smoke_img.get_rect(center=(sx,sy)))
    # player vẽ ở tâm màn hình (camera). Khi player tầng dưới chui gầm
    # cầu → cũng mờ nhẹ cho ăn khớp, nhưng KHÔNG tắt hẳn (tránh mất camera).
    pa=racer_alpha(player)
    psp=player.sprite
    if pa<255:
        psp=psp.copy(); psp.set_alpha(max(70,pa))
    screen.blit(psp,psp.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))

def update_positions():
    progs=[(r,r.race_progress()) for r in all_racers]
    progs.sort(key=lambda x:x[1], reverse=True)
    for rank,(r,_) in enumerate(progs,1):
        r.pos=rank

# ── HUD ─────────────────────────────────────────────────────────────
hud=HUD(screen, total_racers=len(all_racers), max_laps=MAX_LAPS,
        base_dir=BASE_DIR, car_screen_x=CAR_SCREEN_X, car_screen_y=CAR_SCREEN_Y)
pause = PauseMenu(screen, BASE_DIR)        # ← thêm dòng này

# ── MAIN LOOP ───────────────────────────────────────────────────────
running=True
countdown_t=COUNTDOWN_START; _go_time=None; _go_shown=False
_go_appear_t=None; _you_fade_t=None

while running:
    dt=min(clock.tick(FPS)/1000.0, 1/30.0)
    now=time.monotonic()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT: running = False
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: running = False
        act = pause.handle_event(ev)  # ← thêm
        if act == "restart":  # ← thêm
            countdown_t = COUNTDOWN_START
            _go_shown = False;
            _go_time = None;
            _go_appear_t = None;
            _you_fade_t = None
            for i, r in enumerate(all_racers):
                gx, gy = _slot_pos(_slots[i]);
                r.x, r.y = gx, gy
                r.angle = _SPAWN_ANGLE;
                r.velocity = 0.0;
                r.wp_idx = 0
                r.finished = False
                if hasattr(r, '_finish_time'): del r._finish_time
        elif act == "quit_showroom":  # ← thêm
            running = False

    keys=pygame.key.get_pressed()
    handbrake=keys[pygame.K_SPACE]  if countdown_t<=1.0 else False
    want_nitro=keys[pygame.K_LCTRL] if countdown_t<=1.0 else False

    if countdown_t>0:
        countdown_t-=dt
        if countdown_t<0: countdown_t=0

    if countdown_t>0 and countdown_t<1.0 and _go_appear_t is None:
        _go_appear_t=now

    race_active=(countdown_t<=1.0)
    if race_active and not _go_shown:
        _go_time=now; _go_shown=True
    if race_active and _you_fade_t is None:
        _you_fade_t=now

    if race_active and not pause.open:
        player.update_player(dt,now,keys,handbrake,want_nitro)
        if not player.finished and handbrake and abs(player.velocity)>25:
            draw_skid(player,dt)
        for bot in bots:
            bot.update_bot(dt,now,all_racers)

    physics.handle_capsule_collisions(all_racers,dt)
    update_positions()

    if player.finished and not hasattr(player,'_finish_time'):
        player._finish_time=now

    render_world(player)

    if _go_shown:
        end_t=getattr(player,'_finish_time',now); elapsed=end_t-_go_time
    else:
        elapsed=0.0
    if _you_fade_t is None:
        _you_alpha=255
    else:
        _you_alpha=max(0,int(255*(1.0-(now-_you_fade_t)/0.2)))
    _go_elapsed=(now-_go_appear_t) if _go_appear_t is not None else 0.0
    hud.draw(player, elapsed, you_alpha=_you_alpha)

    if getattr(player,'player_stuck_t',0)>1.5:
        _f=pygame.font.SysFont("arial",42,bold=True)
        _t=_f.render("REVERSE TO ESCAPE  (S)",True,(255,220,60))
        screen.blit(_t,_t.get_rect(center=(SCREEN_W//2,SCREEN_H//2-160)))
    if player.finished:
        hud.draw_finish_overlay(player)
    if countdown_t>0 or _go_elapsed<1.3:
        hud.draw_countdown(countdown_t, _go_elapsed)

    if countdown_t > 0 or _go_elapsed < 1.3:
        hud.draw_countdown(countdown_t, _go_elapsed)

    pause.draw()  # ← thêm, ngay trước flip
    pygame.display.flip()

pygame.quit(); sys.exit()

# ════════════════════════════════════════════════════════════════════
# BUILD .EXE (PyInstaller) — gói luôn ảnh map vào, chạy không cần assets rời:
#
#   pyinstaller --onefile --windowed track-velodrama-circuit.py ^
#     --add-data "assets/track/velodrama-track.png;assets/track" ^
#     --add-data "assets/track/velodrama-walls.png;assets/track" ^
#     --add-data "assets/ui-race-mode/2dss-nitrosmoke.png;assets/ui-race-mode"
#
#   (Windows dùng ';' ngăn cách; Linux/macOS đổi thành ':'.)
#   resource_path() ở đầu file tự trỏ vào sys._MEIPASS khi chạy .exe.
# ════════════════════════════════════════════════════════════════════

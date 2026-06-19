"""
track-sandy-circuit.py — Sandy Circuit (sa mạc)
2D Sideway Showdown | 1v1 hoặc 6 xe | 3 vòng

Điều khiển: W/S ga-phanh  A/D lái  SPACE drift  LCTRL (GIỮ) nitro  ESC thoát

GHI CHÚ KỸ THUẬT (đọc trước khi sửa):
- Toạ độ WAYPOINT gốc (_WP_ORIG) KHÔNG vẽ tay như Greenwood — được dò thật
  từ ảnh assets/track/sandy-circuit-track.png (3200x3200) bằng cách:
  tách mask đường đua (pixel xám, không sat) -> skeletonize -> đi theo
  đường tâm bằng nearest-neighbor walk -> làm mượt -> resample đều ~80px.
  Vì vậy toạ độ ở đây bám khá sát tâm đường thật, ít cần chỉnh tay so với
  việc đoán bằng mắt. Nếu xe vẫn lệch làn ở khúc nào, chỉnh trực tiếp
  điểm đó trong _WP_ORIG (không cần re-trace toàn bộ).
- Đường có 1 NHÁNH RẼ (fork) ở góc trên-phải (khúc cua hình móng ngựa /
  hairpin nhìn thấy trong ảnh map). Thấy rõ trong sandy-circuit-track.png:
  đoạn vòng nhỏ nhô lên phía trên đường chính. _BRANCH_* định nghĩa 2 lựa
  chọn đường đi tại đó: "main" (đường chính, đã verify bằng trace) và
  "loop" (đường nhánh móng ngựa, ước lượng theo hình — nên test lại khi
  build .exe vì đây là đoạn duy nhất KHÔNG được trace pixel-by-pixel).
  Mỗi Racer (bot + player) random chọn 1 trong 2 lúc khởi tạo ván đua.
- TODO (làm SAU CÙNG theo yêu cầu, chưa code trong file này):
  "Đi một chiều" — chặn xe quay đầu/đi lùi lâu trên track để tránh đâm
  ngược chiều xe khác. Gợi ý hướng làm khi tới lúc: so sánh wp_idx hiện
  tại với wp_idx trước đó mỗi N frame; nếu lùi quá K waypoint liên tục
  (không phải do va chạm) thì coi là "đi ngược", có thể giảm dần lực kéo
  hoặc hiện cảnh báo. Chưa bật vì cần test kỹ ở từng track trước, đặc
  biệt là đoạn có nhánh rẽ này (rẽ nhánh dễ bị tính nhầm là "đi lùi").
"""
import pygame, math, os, sys, time, random

# ── IMPORTS MODULE ──────────────────────────────────────────────────
from twodss_hud      import HUD, fmt_time, draw_shadow
from twodss_car_data import CAR_STATS
import twodss_physics as physics
from twodss_racer_v2  import Racer, setup_map, pick_drivers
from twodss_pause import PauseMenu

# ── PATH ────────────────────────────────────────────────────────────
def _base_dir():
    if hasattr(sys,"_MEIPASS"): return sys._MEIPASS
    s=os.path.dirname(os.path.abspath(__file__))
    p=os.path.dirname(s)
    for c in [p,s,os.getcwd()]:
        if os.path.isdir(os.path.join(c,"assets")): return c
    return s

def resource_path(rel):
    base=sys._MEIPASS if hasattr(sys,"_MEIPASS") else BASE_DIR
    return os.path.join(base,rel)

BASE_DIR   = _base_dir()
# Khi build .exe (PyInstaller --add-data), ảnh nằm trong _MEIPASS, vẫn
# qua đường dẫn assets/track/... này — KHÔNG đổi tên file png khi build,
# nếu đổi phải sửa lại 2 dòng TRACK_PATH / WALL_MASK_PATH dưới đây.
TRACK_PATH = os.path.join(BASE_DIR,"assets","track","sandy-circuit-track.png")

# ── CONFIG ──────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1920, 1080
FPS             = 90
MAP_SCALE       = 1.45      # ảnh map đã 3200x3200, không cần phóng to thêm
MOVE_SCALE      = physics.MOVE_SCALE
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
pygame.display.set_caption("2D Sideway Showdown — Sandy Circuit")
clock=pygame.time.Clock()

# ── TRACK + WALL MASK ───────────────────────────────────────────────
# Nếu thiếu PNG -> báo lỗi rõ ràng ngay, không để game đứng im khó hiểu
# (đặc biệt quan trọng sau khi đóng .exe, lúc đó người chơi không có
# console để xem traceback gốc).
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

WALL_MASK_PATH=os.path.join(BASE_DIR,"assets","track","sandy-circuit-walls.png")
wall_mask=None
try:
    wraw=pygame.image.load(WALL_MASK_PATH).convert()
    # scale (nearest) thay smoothscale: tránh viền xám antialiased
    # làm is_hard_wall() trigger sai → 'tường vô hình'
    wall_mask=pygame.transform.scale(wraw,(MAP_W,MAP_H))
    print(f"[WALL MASK] {wall_mask.get_size()}")
except FileNotFoundError:
    print(f"[WALL MASK] Not found: {WALL_MASK_PATH}")
except Exception as e:
    print(f"[WALL MASK] {e}")

# ── NITRO SMOKE FX ──────────────────────────────────────────────────
NITRO_SMOKE_PATH=os.path.join(BASE_DIR,"assets","ui-race-mode","2dss-nitrosmoke.png")
nitro_smoke_img=None
try:
    _ns_raw=pygame.image.load(NITRO_SMOKE_PATH).convert_alpha()
    _ns_w=int(_ns_raw.get_width()*0.4)
    _ns_h=int(_ns_raw.get_height()*0.4)
    nitro_smoke_img=pygame.transform.smoothscale(_ns_raw,(_ns_w,_ns_h))
    print(f"[NITRO SMOKE] {nitro_smoke_img.get_size()}")
except FileNotFoundError:
    print("[NITRO SMOKE] Not found —", NITRO_SMOKE_PATH)
except Exception as e:
    print(f"[NITRO SMOKE] {e}")

# ── PHYSICS SETUP ───────────────────────────────────────────────────
# gate_safe ước lượng theo bề rộng đường tại line xuất phát (đo thật từ
# mask ảnh: đường rộng ~280px quanh x=190..460 ở khu vực gần finish).
physics.setup(
    track      = track,
    wall_mask  = wall_mask,
    map_w      = MAP_W,
    map_h      = MAP_H,
    move_scale = MOVE_SCALE,
    gate_safe  = (
        int(160*MAP_SCALE), int(420*MAP_SCALE),
        int(1480*MAP_SCALE),int(1700*MAP_SCALE),
    ),
)

# ── WAYPOINTS (dò thật từ sandy-circuit-track.png, KHÔNG vẽ tay) ─────
# Quy trình: mask đường (pixel xám, low-saturation) -> skeletonize ->
# nearest-neighbor walk theo đường tâm -> smooth -> resample đều ~80px.
# Điểm đầu tiên nằm sát line xuất phát (cờ checker, mép trái track).
_WP_ORIG=[
    (317,1582),(310,1534),(285,1454),(266,1366),(258,1297),
    (260,1209),(287,1131),(297,1037),(322,936), (396,835),
    (459,762), (544,710), (647,680), (748,652), (850,631),
    (947,627), (1043,626),(1139,626),(1239,630),(1351,647),
    (1462,646),(1573,626),(1680,594),(1784,554),(1888,514),
    (1994,479),(2103,456),                       # ── vào khu vực ngã rẽ (xem _BRANCH dưới) ──
    (2206,459),(2306,487),                        # ── ra khỏi khu vực ngã rẽ ──
    (2402,535),(2490,600),(2565,682),(2628,776),(2679,875),
    (2714,981),(2735,1093),(2749,1208),(2762,1323),(2775,1438),
    (2787,1554),(2799,1669),(2809,1785),(2808,1904),(2798,2020),
    (2774,2129),(2731,2223),(2666,2296),(2581,2348),(2478,2379),
    (2363,2393),(2244,2396),(2125,2396),(2005,2395),(1885,2395),
    (1766,2399),(1651,2412),(1541,2438),(1437,2478),(1336,2527),
    (1236,2578),(1134,2623),(1028,2657),(916,2675), (801,2678),
    (687,2666), (581,2635), (489,2586), (417,2519), (351,2458),
    (306,2367), (296,2270), (297,2184), (321,2072), (322,1959),
    (325,1878), (323,1797), (324,1675),
]

# ── NGÃ RẼ (BRANCH / FORK) ────────────────────────────────────────
# Vị trí: giữa waypoint index 25 "(1994,479)/(2103,456)" và 27
# "(2206,459)/(2306,487)" trong _WP_ORIG — khúc móng ngựa nhô lên ở
# góc trên-phải map (thấy rõ trong ảnh sandy-circuit-track.png).
# main = đi thẳng theo _WP_ORIG (đã verify bằng trace pixel).
# loop = vòng qua nhánh móng ngựa phía trên rồi nhập lại — toạ độ
# ước lượng theo hình ảnh, NÊN test lại trong game vì không trace
# pixel-by-pixel đoạn này (mask bị nhiễu texture cát/đá ở đó).
BRANCH_ENTRY_IDX = 26          # index của (2103,456) trong _WP_ORIG
BRANCH_EXIT_IDX  = 28          # index của (2306,487) trong _WP_ORIG
_BRANCH_LOOP_PTS = [
    (2150,330),(2260,255),(2420,235),(2580,265),(2700,345),
    (2740,430),
]

def _build_route(use_branch_loop=False):
    """
    Trả về 1 bộ waypoint hoàn chỉnh (list[(x,y)]):
      - use_branch_loop=False -> route chính (mặc định, an toàn)
      - use_branch_loop=True  -> chèn nhánh móng ngựa giữa entry/exit
    Dùng để mỗi Racer (bot/player) random chọn 1 route lúc spawn,
    tạo cảm giác "có lựa chọn đường đua" như yêu cầu.
    """
    if not use_branch_loop:
        return list(_WP_ORIG)
    route = _WP_ORIG[:BRANCH_ENTRY_IDX+1] + _BRANCH_LOOP_PTS + _WP_ORIG[BRANCH_EXIT_IDX:]
    return route

WAYPOINTS = _build_route(use_branch_loop=False)
WAYPOINTS=[(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in WAYPOINTS]

# ── DUAL-LANE WAYPOINTS cho grid 2×3 ────────────────────────────────
# Mục đích: xe cột trái và cột phải bắt đầu từ đúng làn đường
# → không bị kéo chéo sang cột kia ngay từ đầu → không quay đầu loạn.
#
# Offset ngang ±50px (trước khi scale) so với WP gốc (giữa đường).
# Chỉ áp dụng cho 8 WP đầu tiên (đoạn thẳng xuất phát); phần còn lại
# hội tụ về giữa đường cho AI đua bình thường.
_LANE_SPLIT   = 8      # số WP đầu giữ offset làn, sau đó lerp về giữa
_LANE_OFFSET  = int(50 * MAP_SCALE)   # px offset sang trái/phải

def _make_lane_wps(wps, offset_x):
    """
    Tạo bộ waypoint lệch offset_x px (trục X) cho _LANE_SPLIT WP đầu,
    sau đó lerp dần về WP gốc trong 6 WP tiếp theo rồi giữ nguyên.
    """
    result = list(wps)
    lerp_n = 6
    for i in range(len(wps)):
        if i < _LANE_SPLIT:
            ox = offset_x
        elif i < _LANE_SPLIT + lerp_n:
            t  = (i - _LANE_SPLIT) / lerp_n   # 0 → 1
            ox = int(offset_x * (1.0 - t))
        else:
            ox = 0
        result[i] = (wps[i][0] + ox, wps[i][1])
    return result

def _route_for(use_branch_loop):
    base = [(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in _build_route(use_branch_loop)]
    return base

# ── WAYPOINT DENSIFICATION ────────────────────────────────────────────
# Noi suy WP thua thanh day dac de xe di muot hon.
# Theo yeu cau: 3px / lan (muot hon ban Greenwood 5px, vi track nay co
# nhieu khuc cong + nga re can do chinh xac cao hon cho bot bam lan).
WP_DENSE_STEP = 3   # px giua 2 WP — 3 = muot, doi hoi nhieu RAM/CPU hon

def _densify(wps, step=None):
    """
    Noi suy tuyen tinh wps thanh day dac moi `step` px.
    Giu nguyen keyframe goc, them diem trung gian giua 2 WP lien tiep.
    Segment ngan hon step -> giu 1 diem (khong them).
    """
    if step is None: step = WP_DENSE_STEP
    if len(wps) < 2: return list(wps)
    result = []
    for i in range(len(wps)):
        x0, y0 = wps[i]
        x1, y1 = wps[(i + 1) % len(wps)]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < step:
            result.append((x0, y0))
            continue
        n = max(1, int(seg / step))
        for s in range(n):
            t = s / n
            result.append((int(x0 + (x1 - x0) * t),
                           int(y0 + (y1 - y0) * t)))
    return result

def _make_dense_route(use_branch_loop, offset_x=0):
    base = _route_for(use_branch_loop)
    laned = _make_lane_wps(base, offset_x) if offset_x != 0 else base
    return _densify(laned)

# Bộ dense mặc định (route chính, không offset) — dùng cho setup_map /
# fallback nếu cần 1 đường tham chiếu chung.
WAYPOINTS_DENSE = _densify(WAYPOINTS)
print(f'[WP] sparse={len(WAYPOINTS)}  dense={len(WAYPOINTS_DENSE)}  '
      f'step={WP_DENSE_STEP}px  branch_entry_idx={BRANCH_ENTRY_IDX}')

GATE_Y  = int(1324*MAP_SCALE)
GATE_X1 = int(190 *MAP_SCALE)
GATE_X2 = int(450 *MAP_SCALE)

# ── RACER SETUP ─────────────────────────────────────────────────────
setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2,
          max_laps=MAX_LAPS, base_dir=BASE_DIR, map_scale=MAP_SCALE,
          car_display_w=97)

# ── GRID SPAWN ──────────────────────────────────────────────────────
# Slot layout:  col L (idx 0,2,4)  col R (idx 1,3,5)
# Xe cột trái  → route LEFT (lane trái)   xuất phát không bị kéo sang phải
# Xe cột phải  → route RIGHT (lane phải)  xuất phát không bị kéo sang trái
# Toạ độ grid đặt ngay trước line xuất phát (GATE_Y=1580), trên đoạn
# đường thẳng dò được ở _WP_ORIG[0]≈(317,1582).
_ROW_GAP = 180; _COL_L=250; _COL_R=380; _ROW_TOP=1450
_GRID_SLOTS=[
    (_COL_L,_ROW_TOP),(_COL_R,_ROW_TOP),
    (_COL_L,_ROW_TOP+_ROW_GAP),(_COL_R,_ROW_TOP+_ROW_GAP),
    (_COL_L,_ROW_TOP+_ROW_GAP*2),(_COL_R,_ROW_TOP+_ROW_GAP*2),
]

def _slot_pos(i):
    x,y=_GRID_SLOTS[i]; return x*MAP_SCALE,y*MAP_SCALE

_slots=list(range(6)); random.shuffle(_slots)

# Mỗi xe (player + bot) random chọn route chính/nhánh móng ngựa độc
# lập với nhau — đúng tinh thần "có lựa chọn đường đua" của track 2
# nhánh. Xác suất đi nhánh thấp hơn vì đây là đoạn ít test (xem cảnh
# báo ở _BRANCH_LOOP_PTS phía trên).
_BRANCH_CHANCE = 0.35

def _slot_wp(slot_idx, use_branch_loop):
    """Tra ve waypoint dense cho slot_idx (chan=lane trai, le=lane phai)."""
    offset = -_LANE_OFFSET if slot_idx % 2 == 0 else _LANE_OFFSET
    return _make_dense_route(use_branch_loop, offset)

# ── TẠO XE ─────────────────────────────────────────────────────────
# Đổi NUM_BOTS=1 để 1v1, NUM_BOTS=5 để 6 xe
NUM_BOTS = 5

_p_slot = _slots[0]
_p_branch = random.random() < _BRANCH_CHANCE
px,py=_slot_pos(_p_slot)
player=Racer("ferrari_f430_2005", px, py, 270.0, is_player=True,
             waypoints=_slot_wp(_p_slot, _p_branch))
print(f"[PLAYER] route={'BRANCH-LOOP' if _p_branch else 'MAIN'}  lane={'L' if _p_slot%2==0 else 'R'}")

_other_cars=[c for c in CAR_STATS.keys() if c!="ferrari_f430_2005"]
_bot_ids=random.sample(_other_cars, min(NUM_BOTS,len(_other_cars)))

# Lấy driver (tên + quốc gia + aggression) từ bảng 42 người đã quay
# wheel-of-names — xem twodss_racer_v2.py (DRIVER_ROSTER).
_drivers = pick_drivers(NUM_BOTS)

BOT_TINTS=[(220,60,60),(60,180,60),(60,60,220),(200,180,0),(180,0,180)]
bots=[]
for k in range(NUM_BOTS):
    _b_slot = _slots[k+1]
    _b_branch = random.random() < _BRANCH_CHANCE
    bx,by=_slot_pos(_b_slot)
    _b_wp = _slot_wp(_b_slot, _b_branch)
    _name, _country, _aggr = _drivers[k]
    bot=Racer(_bot_ids[k], bx, by, 270.0, waypoints=_b_wp,
              driver_name=_name, driver_country=_country, composure=_aggr)
    bot.wp_idx=min(range(len(_b_wp)),
                   key=lambda i,bx=bx,by=by: math.hypot(_b_wp[i][0]-bx,_b_wp[i][1]-by))
    bot.velocity=k*5.0
    bots.append(bot)
    print(f"[BOT {k+1}] {_bot_ids[k]}  driver={_name} ({_country})  aggr={_aggr:.4f}  "
          f"lane={'L' if _b_slot%2==0 else 'R'}  route={'BRANCH-LOOP' if _b_branch else 'MAIN'}")

all_racers=[player]+bots

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
    crop=pygame.Surface((CROP_SIZE,CROP_SIZE)); crop.fill((230,170,75))
    ox=CROP_SIZE//2-int(player.x); oy=CROP_SIZE//2-int(player.y)
    crop.blit(track,(ox,oy)); crop.blit(skid_layer,(ox,oy))
    for bot in bots:
        if not bot.visible:
            continue
        bx2=CROP_SIZE//2+int(bot.x-player.x)
        by2=CROP_SIZE//2+int(bot.y-player.y)
        if nitro_smoke_img is not None and bot.nitro_active:
            fx,fy=fwd_vec(bot.angle)
            sx2 = bx2 - fx*bot.car_h*0.5    # lùi về ĐÍT xe = nửa chiều dài xe ĐÓ
            sy2 = by2 - fy*bot.car_h*0.5    # tự co giãn theo từng xe, không cần biết trước size
            smoke=pygame.transform.rotate(nitro_smoke_img,270-bot.angle)
            crop.blit(smoke,smoke.get_rect(center=(sx2,sy2)))
        spr=pygame.transform.rotate(bot.sprite,270-bot.angle)
        crop.blit(spr,spr.get_rect(center=(bx2,by2)))
    rot=pygame.transform.rotate(crop,90.0+player.angle)
    screen.fill((0,0,0))
    screen.blit(rot,rot.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))
    if nitro_smoke_img is not None and player.nitro_active:
        sx = CAR_SCREEN_X
        sy = CAR_SCREEN_Y + player.car_h*0.5   # player luôn hướng lên màn hình -> đít = xuống dưới
        screen.blit(nitro_smoke_img, nitro_smoke_img.get_rect(center=(sx,sy)))
    screen.blit(player.sprite,player.sprite.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))

def update_positions():
    """
    Xếp hạng real-time 2 tiêu chí:
      1. lap lớn hơn → auto trên
      2. cùng lap → so progress từng pixel
    race_progress() trả tuple (lap, prog) — sort reverse là đúng thứ tự.
    """
    progs=[(r,r.race_progress()) for r in all_racers]
    progs.sort(key=lambda x:x[1], reverse=True)
    for rank,(r,_) in enumerate(progs,1):
        r.pos=rank

# ── HUD ─────────────────────────────────────────────────────────────
hud=HUD(screen, total_racers=len(all_racers), max_laps=MAX_LAPS,
        base_dir=BASE_DIR, car_screen_x=CAR_SCREEN_X, car_screen_y=CAR_SCREEN_Y)
pause = PauseMenu(screen, BASE_DIR)        # ← thêm dòng này

# ── MAIN LOOP ───────────────────────────────────────────────────────
running=True; race_clock=0.0
countdown_t=COUNTDOWN_START; _go_time=None; _go_shown=False
_go_appear_t  = None   # khi GO! lần đầu xuất hiện (ct < 1.0)
_you_fade_t   = None   # khi race_active → YOU bắt đầu fade

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
                gx, gy = _slot_pos(_slots[i])
                r.x, r.y = gx, gy
                r.angle = 270.0
                r.velocity = 0.0
                r.wp_idx = 0
                r.finished = False
                if hasattr(r, '_finish_time'): del r._finish_time
        elif act == "quit_showroom":  # ← thêm
            running = False

    keys=pygame.key.get_pressed()
    handbrake=keys[pygame.K_SPACE] if countdown_t<=1.0 else False
    want_nitro=keys[pygame.K_LCTRL] if countdown_t<=1.0 else False

    if countdown_t>0:
        countdown_t-=dt
        if countdown_t<0: countdown_t=0

    # Ghi nhận khi GO! xuất hiện lần đầu (ct < 1.0)
    if countdown_t > 0 and countdown_t < 1.0 and _go_appear_t is None:
        _go_appear_t = now

    race_active=(countdown_t<=1.0)  # GO! xuất hiện → đua NGAY
    if race_active and not _go_shown:
        _go_time=now; _go_shown=True
    # Bắt đầu fade YOU khi race_active
    if race_active and _you_fade_t is None:
        _you_fade_t = now

    if race_active and not pause.open:
        # Luôn update player — kể cả khi finished
        # (logic phanh trượt nằm trong update_player, cần được gọi mỗi frame)
        player.update_player(dt,now,keys,handbrake,want_nitro)
        if not player.finished and handbrake and abs(player.velocity)>25:
            draw_skid(player,dt)
        for bot in bots:
            bot.update_bot(dt,now,all_racers)

    physics.handle_capsule_collisions(all_racers,dt)
    update_positions()

    # Ghi lại thời điểm finish 1 lần để đóng băng timer
    if player.finished and not hasattr(player,'_finish_time'):
        player._finish_time = now

    render_world(player)
    # Timer: dừng tại thời điểm finish, không chạy tiếp
    if _go_shown:
        end_t   = getattr(player,'_finish_time', now)
        elapsed = end_t - _go_time
    else:
        elapsed = 0.0
    # YOU badge: alpha 255 trong countdown, fade 0.2s sau race start
    if _you_fade_t is None:
        _you_alpha = 255
    else:
        _fade_prog = (now - _you_fade_t) / 0.2
        _you_alpha = max(0, int(255 * (1.0 - _fade_prog)))
    # GO! elapsed: giây kể từ khi GO! xuất hiện
    _go_elapsed = (now - _go_appear_t) if _go_appear_t is not None else 0.0
    hud.draw(player, elapsed, you_alpha=_you_alpha)
    # Hint thoát tường: stuck > 1.5s → chỉ dẫn nhấn S
    if getattr(player,'player_stuck_t',0) > 1.5:
        _f=pygame.font.SysFont("arial",42,bold=True)
        _t=_f.render("REVERSE TO ESCAPE  (S)",True,(255,220,60))
        screen.blit(_t,_t.get_rect(center=(SCREEN_W//2,SCREEN_H//2-160)))
    if player.finished:
        hud.draw_finish_overlay(player)
    # Vẽ countdown + GO! fade (kể cả khi ct=0 nhưng GO! vẫn fading)
    if countdown_t > 0 or _go_elapsed < 1.3:
        hud.draw_countdown(countdown_t, _go_elapsed)

    if countdown_t > 0 or _go_elapsed < 1.3:
        hud.draw_countdown(countdown_t, _go_elapsed)

    pause.draw()  # ← thêm, ngay trước flip
    pygame.display.flip()


pygame.quit(); sys.exit()
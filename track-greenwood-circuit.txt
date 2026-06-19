"""
track-greenwood-circuit.py — Greenwood Circuit
2D Sideway Showdown | 1v1 hoặc 6 xe | 3 vòng

Điều khiển: W/S ga-phanh  A/D lái  SPACE drift  LCTRL (GIỮ) nitro  ESC thoát
"""
import pygame, math, os, sys, time, random

# ── IMPORTS MODULE ──────────────────────────────────────────────────
from twodss_hud      import HUD, fmt_time, draw_shadow
from twodss_car_data import CAR_STATS
import twodss_physics as physics
from twodss_racer_v2  import Racer, setup_map, pick_drivers

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
TRACK_PATH = os.path.join(BASE_DIR,"assets","track","greenwood-circuit-track.png")

# ── CONFIG ──────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1920, 1080
FPS             = 90
MAP_SCALE       = 1.5
# MOVE_SCALE KHÔNG còn khai báo ở đây — dùng thẳng physics.MOVE_SCALE
# (xem dòng gọi setup_map() phía dưới) để KHÔNG THỂ bị conflict/lệch
# số giữa các map. Đổi tốc độ đua cho TẤT CẢ map: sửa đúng 1 hằng số
# MOVE_SCALE ở đầu twodss_physics.py, không sửa map file nào cả.
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
pygame.display.set_caption("2D Sideway Showdown — Greenwood Circuit")
clock=pygame.time.Clock()

# ── TRACK + WALL MASK ───────────────────────────────────────────────
if not os.path.exists(TRACK_PATH):
    print("[CRITICAL] Track PNG not found"); pygame.quit(); sys.exit(1)

track_raw=pygame.image.load(TRACK_PATH).convert()
track=pygame.transform.smoothscale(track_raw,
    (int(track_raw.get_width()*MAP_SCALE),
     int(track_raw.get_height()*MAP_SCALE))) if abs(MAP_SCALE-1)>0.001 else track_raw
MAP_W,MAP_H=track.get_width(),track.get_height()
print(f"[TRACK] {MAP_W}x{MAP_H}")

skid_layer=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA)

WALL_MASK_PATH=os.path.join(BASE_DIR,"assets","track","greenwood-circuit-walls.png")
wall_mask=None
try:
    wraw=pygame.image.load(WALL_MASK_PATH).convert()
    # scale (nearest) thay smoothscale: tránh viền xám antialiased
    # làm is_hard_wall() trigger sai → 'tường vô hình'
    wall_mask=pygame.transform.scale(wraw,(MAP_W,MAP_H))
    print(f"[WALL MASK] {wall_mask.get_size()}")
except FileNotFoundError:
    print("[WALL MASK] Not found")
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
physics.setup(
    track      = track,
    wall_mask  = wall_mask,
    map_w      = MAP_W,
    map_h      = MAP_H,
    move_scale = physics.MOVE_SCALE,
    gate_safe  = (
        int(170*MAP_SCALE), int(430*MAP_SCALE),
        int(1080*MAP_SCALE),int(1310*MAP_SCALE),
    ),
)

# ── WAYPOINTS ───────────────────────────────────────────────────────
_WP_ORIG=[
    (300,1220),(300,1120),(300,1020),(300,920),(300,820),
    (300,720),(300,620),(300,520),(300,420),(300,320),
    (350,310),(420,340),(500,360),(580,365),(660,368),
    (740,370),(820,372),(880,372),
    (930,377),(980,388),(1030,399),(1080,422),(1130,509),
    (1180,544),(1230,563),(1280,615),(1330,670),(1380,701),
    (1430,716),(1480,727),(1530,738),(1580,741),(1630,660),
    (1680,739),(1730,730),(1780,637),(1830,636),(1880,627),
    (1930,570),
    (1980,517),(2040,468),(2100,431),(2160,378),(2220,321),
    (2280,385),(2340,372),(2400,371),(2460,370),(2520,385),
    (2580,352),(2640,378),(2700,448),(2760,543),
    (2800,600),(2800,700),(2800,800),(2800,900),(2800,1000),
    (2800,1100),(2800,1200),(2800,1300),(2800,1400),(2800,1500),
    (2800,1600),(2800,1700),(2800,1800),(2800,1900),(2800,2000),
    (2700,2050),(2580,2050),(2460,2050),(2340,2050),(2220,2050),
    (2100,2050),(1980,2050),(1860,2050),(1770,1810),(1710,1790),
    (1650,1767),(1590,1764),(1530,1761),(1470,1790),(1410,1808),
    (1350,1849),(1230,2020),(1110,2050),(990,2050),(870,2050),
    (750,2050),(630,2050),(510,2050),(390,2050),
    (290,1980),(285,1880),(285,1780),(285,1680),(285,1580),
    (285,1480),(285,1380),(290,1280),
]
WAYPOINTS=[(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in _WP_ORIG]

# ── DUAL-LANE WAYPOINTS cho grid 2×3 ────────────────────────────────
# Mục đích: xe cột trái và cột phải bắt đầu từ đúng làn đường
# → không bị kéo chéo sang cột kia ngay từ đầu → không quay đầu loạn.
#
# Offset ngang ±60px (trước khi scale) so với WP gốc (giữa đường).
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

WAYPOINTS_LEFT  = _make_lane_wps(WAYPOINTS, -_LANE_OFFSET)
WAYPOINTS_RIGHT = _make_lane_wps(WAYPOINTS, +_LANE_OFFSET)

# ── WAYPOINT DENSIFICATION ────────────────────────────────────────────
# Noi suy WP thua (~134px/WP) thanh day dac de xe di muot hon.
# _LANE_OFFSET ap dung truoc densify de lane offset cung duoc noi suy.
# sparse=100 WP x ~134px / 5px = ~2688 diem moi set
WP_DENSE_STEP = 5   # px giua 2 WP — chinh 3 (muot hon) hoac 7 (nhe hon)

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

# Dense — Racer._wp dung cho guidance, advance, lookahead
# Sparse WAYPOINTS van dung cho setup_map (gate detection khong can day)
WAYPOINTS_DENSE       = _densify(WAYPOINTS)
WAYPOINTS_LEFT_DENSE  = _densify(WAYPOINTS_LEFT)
WAYPOINTS_RIGHT_DENSE = _densify(WAYPOINTS_RIGHT)
print(f'[WP] sparse={len(WAYPOINTS)}  dense={len(WAYPOINTS_DENSE)}  '
      f'step={WP_DENSE_STEP}px')

GATE_Y  = int(1184*MAP_SCALE)
GATE_X1 = int(190 *MAP_SCALE)
GATE_X2 = int(410 *MAP_SCALE)

# ── RACER SETUP ─────────────────────────────────────────────────────
setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2,
          max_laps=MAX_LAPS, base_dir=BASE_DIR, map_scale=MAP_SCALE)   # ← thêm map_scale

# ── GRID SPAWN ──────────────────────────────────────────────────────
# Slot layout:  col L (idx 0,2,4)  col R (idx 1,3,5)
# Xe cột trái  → WAYPOINTS_LEFT   (xuất phát không bị kéo sang phải)
# Xe cột phải  → WAYPOINTS_RIGHT  (xuất phát không bị kéo sang trái)
_ROW_GAP=160; _COL_L=240; _COL_R=360; _ROW_TOP=1263
_GRID_SLOTS=[
    (_COL_L,_ROW_TOP),(_COL_R,_ROW_TOP),
    (_COL_L,_ROW_TOP+_ROW_GAP),(_COL_R,_ROW_TOP+_ROW_GAP),
    (_COL_L,_ROW_TOP+_ROW_GAP*2),(_COL_R,_ROW_TOP+_ROW_GAP*2),
]
# Slot chẵn (0,2,4) = cột TRÁI; slot lẻ (1,3,5) = cột PHẢI
def _slot_wp(slot_idx):
    """Tra ve waypoint dense cho slot_idx (chan=trai, le=phai)."""
    return WAYPOINTS_LEFT_DENSE if slot_idx % 2 == 0 else WAYPOINTS_RIGHT_DENSE

def _slot_pos(i):
    x,y=_GRID_SLOTS[i]; return x*MAP_SCALE,y*MAP_SCALE

_slots=list(range(6)); random.shuffle(_slots)

# ── TẠO XE ─────────────────────────────────────────────────────────
# Đổi NUM_BOTS=1 để 1v1, NUM_BOTS=5 để 6 xe
NUM_BOTS = 5

_p_slot = _slots[0]
px,py=_slot_pos(_p_slot)
player=Racer("ferrari_f430_2005", px, py, 270.0, is_player=True,
             waypoints=_slot_wp(_p_slot))

_other_cars=[c for c in CAR_STATS.keys() if c!="ferrari_f430_2005"]
_bot_ids=random.sample(_other_cars, min(NUM_BOTS,len(_other_cars)))

# Lấy driver (tên + quốc gia + aggression) từ bảng 42 người đã quay
# wheel-of-names — xem twodss_racer_v2.py (DRIVER_ROSTER) — thay cho
# công thức _aggr ad-hoc cũ (0.88 + k*0.07 + random.uniform...).
_drivers = pick_drivers(NUM_BOTS)

BOT_TINTS=[(220,60,60),(60,180,60),(60,60,220),(200,180,0),(180,0,180)]
bots=[]
for k in range(NUM_BOTS):
    _b_slot = _slots[k+1]
    bx,by=_slot_pos(_b_slot)
    _b_wp = _slot_wp(_b_slot)
    _name, _country, _aggr = _drivers[k]
    bot=Racer(_bot_ids[k], bx, by, 270.0, waypoints=_b_wp,
              driver_name=_name, driver_country=_country, composure=_aggr)
    bot.wp_idx=min(range(len(_b_wp)),
                   key=lambda i,bx=bx,by=by: math.hypot(_b_wp[i][0]-bx,_b_wp[i][1]-by))
    bot.velocity=k*5.0
    bots.append(bot)
    print(f"[BOT {k+1}] {_bot_ids[k]}  driver={_name} ({_country})  aggr={_aggr:.4f}  lane={'L' if _b_slot%2==0 else 'R'}")

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
    crop=pygame.Surface((CROP_SIZE,CROP_SIZE)); crop.fill((145,170,75))
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
        base_dir=BASE_DIR,
        car_screen_x=CAR_SCREEN_X, car_screen_y=CAR_SCREEN_Y)

# ── MAIN LOOP ───────────────────────────────────────────────────────
running=True; race_clock=0.0
countdown_t=COUNTDOWN_START; _go_time=None; _go_shown=False
_go_appear_t  = None   # khi GO! lần đầu xuất hiện (ct < 1.0)
_you_fade_t   = None   # khi race_active → YOU bắt đầu fade

while running:
    dt=min(clock.tick(FPS)/1000.0, 1/30.0)
    now=time.monotonic()

    for ev in pygame.event.get():
        if ev.type==pygame.QUIT: running=False
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: running=False
            # LCTRL nitro v2: KHÔNG còn kích 1 lần ở KEYDOWN — giờ đọc
            # held mỗi frame bên dưới (want_nitro), "giữ bao nhiêu tăng
            # bấy nhiêu, nhả ra để tiết kiệm nitro".

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

    if race_active:
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
    # Vẽ countdown + GO! fade (kể cả khi ct=0 nhưng GO! vẫn fading)www
    if countdown_t > 0 or _go_elapsed < 1.3:
        hud.draw_countdown(countdown_t, _go_elapsed)

    pygame.display.flip()

pygame.quit(); sys.exit()
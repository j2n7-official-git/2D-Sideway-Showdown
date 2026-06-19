"""
track-dustfactory-circuit.py — The Dust Factory Circuit
2D Sideway Showdown | 1v1 hoặc 6 xe | 3 vòng

Điều khiển: W/S ga-phanh  A/D lái  SPACE drift  LCTRL (GIỮ) nitro  ESC thoát

GHI CHÚ KỸ THUẬT:
- Toạ độ WAYPOINT gốc (_WP_ORIG) được dò từ ảnh assets/track/the-dustfactory-circuit.png
  (3200x2728) bằng distance-transform trên road mask (pixel xám, low-saturation).
- Finish line: NGANG tại raw Y=972, X=180..610 (đường thẳng bên TRÁI).
  Gate được tính theo trục Y (xe cắt ngang gate từ dưới lên).
- Track bố cục: đoạn thẳng trái (2 làn song song) → cua trên-trái →
  đoạn ngang trên → S-curve section giữa → đoạn thẳng phải → hairpin dưới
  (3 U-turn lồng nhau) → trở về bên trái.
- MAP_SCALE=1.5: ảnh gốc 3200×2728, sau scale → 4800×4092.
  Tất cả raw coords nhân 1.5 trước khi dùng trong game.
- gate_safe: vùng an toàn gần gate để tránh phát hiện wall nhầm (do checker pattern).
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
TRACK_PATH = os.path.join(BASE_DIR,"assets","track","the-dustfactory-circuit.png")

# ── CONFIG ──────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1920, 1080
FPS             = 90
MAP_SCALE       = 1.5       # ảnh gốc 3200×2728, scale lên 4800×4092
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
pygame.display.set_caption("2D Sideway Showdown — The Dust Factory")
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

WALL_MASK_PATH=os.path.join(BASE_DIR,"assets","track","the-dustfactory-walls.png")
wall_mask=None
try:
    wraw=pygame.image.load(WALL_MASK_PATH).convert()
    # scale nearest thay smoothscale: tránh viền xám antialiased
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
# gate_safe: vùng an toàn quanh finish line (checker pattern gây nhiễu wall mask)
# Tính theo raw: gate Y=972, X=180..610 → cộng buffer ±80px mỗi chiều
physics.setup(
    track      = track,
    wall_mask  = wall_mask,
    map_w      = MAP_W,
    map_h      = MAP_H,
    move_scale = physics.MOVE_SCALE,
    gate_safe  = (
        int(150*MAP_SCALE), int(650*MAP_SCALE),   # X1, X2
        int(880*MAP_SCALE), int(1120*MAP_SCALE),  # Y1, Y2
    ),
)

# ── WAYPOINTS ───────────────────────────────────────────────────────
# Toạ độ gốc (raw, trước MAP_SCALE=1.5x).
# Thứ tự: bắt đầu từ dưới gate → đi LÊN đoạn trái → cua phải trên →
# ngang top → S-curve giữa → đoạn thẳng phải → hairpin dưới (3 U-turn)
# → trở về đoạn trái → qua gate.
#
# Đoạn thẳng trái: outer lane X=290 (đi lên, qua gate), inner lane X=488 (về).
# S-curve section trung tâm: col1 X=1320 (đi lên), col2 X=2084 (đi xuống).
# Đoạn thẳng phải: X=2788 (đi xuống).
# Hairpin 3 tầng dưới: right U (X~2420), mid U (X~1596), left U (X~900).
_WP_ORIG=[
    # ── OUTER LEFT STRAIGHT: đi lên, gate tại Y=972 ──────────────────
    (290,1150),(290,1050),(290,900),(290,750),
    # ── TOP-LEFT CURVE: rẽ phải vào đường ngang ──────────────────────
    (290,560),(380,430),(460,380),(560,300),
    # ── TOP SECTION NGANG ─────────────────────────────────────────────
    (660,280),(900,280),(1150,280),(1350,280),
    # ── VÀO INNER S-CURVE COL2 (X=2084, đi XUỐNG) ───────────────────
    # Từ top đi thẳng sang phải về x=1920 rồi vào col2
    (1340,340),(1920,360),(2700,360),
    # ── RIGHT OUTER STRAIGHT (X=2788, đi XUỐNG) ──────────────────────
    (2788,500),(2788,700),(2788,960),(2788,1200),
    (2788,1440),(2788,1700),(2788,1960),
    # ── ENTRY BOTTOM HAIRPIN ─────────────────────────────────────────
    (2596,2000),(2272,2040),(2100,2040),
    # ── RIGHT U-TURN HAIRPIN ─────────────────────────────────────────
    (2200,2160),(2340,2360),(2420,2440),
    # ── BACK UP AFTER RIGHT U → sang MID HAIRPIN ─────────────────────
    (2272,2280),(2100,2080),(1764,2080),
    # ── MID HAIRPIN ──────────────────────────────────────────────────
    (1596,2080),(1596,2200),(1596,2360),(1596,2440),
    # ── BACK UP AFTER MID → sang LEFT HAIRPIN ────────────────────────
    (1500,2300),(1040,2080),
    # ── LEFT U-TURN HAIRPIN ──────────────────────────────────────────
    (900,2160),(900,2360),(1000,2440),
    # ── TRỞ VỀ BÊN TRÁI ─────────────────────────────────────────────
    (900,2080),(576,1920),
    # ── INNER LEFT STRAIGHT: X=488, đi LÊN ───────────────────────────
    (510,1700),(500,1600),(488,1520),(488,1440),
    (488,1300),(488,1200),(488,1100),(488,950),(488,820),
    # Inner lane hội tụ về outer lane tại phía trên gate
    (390,720),(290,650),(290,520),
    # Quay lại top để hoàn chỉnh vòng (loop về WP[0])
]
WAYPOINTS=[(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in _WP_ORIG]

# ── DUAL-LANE WAYPOINTS cho grid 2×3 ─────────────────────────────────
# Xe cột trái (slot chẵn 0,2,4) → bắt đầu lệch về phía TRÁI đường trái outer
# Xe cột phải (slot lẻ 1,3,5) → bắt đầu lệch về phía PHẢI đường trái outer
# Outer left lane: X=290 raw, rộng ~92px → offset ±30px an toàn
_LANE_SPLIT  = 6     # WP đầu giữ offset làn, sau đó lerp về giữa
_LANE_OFFSET = int(30 * MAP_SCALE)   # 30px raw → 45px scaled

def _make_lane_wps(wps, offset_x):
    """
    Lệch offset_x px theo trục X cho _LANE_SPLIT WP đầu,
    sau đó lerp dần về WP gốc trong 5 WP tiếp theo.
    """
    result = list(wps)
    lerp_n = 5
    for i in range(len(wps)):
        if i < _LANE_SPLIT:
            ox = offset_x
        elif i < _LANE_SPLIT + lerp_n:
            t  = (i - _LANE_SPLIT) / lerp_n
            ox = int(offset_x * (1.0 - t))
        else:
            ox = 0
        result[i] = (wps[i][0] + ox, wps[i][1])
    return result

WAYPOINTS_LEFT  = _make_lane_wps(WAYPOINTS, -_LANE_OFFSET)
WAYPOINTS_RIGHT = _make_lane_wps(WAYPOINTS, +_LANE_OFFSET)

# ── WAYPOINT DENSIFICATION ────────────────────────────────────────────
# Nội suy WP thưa thành dày để xe bám đường mượt hơn ở các khúc cua.
WP_DENSE_STEP = 5   # px giữa 2 WP — 5px cân bằng giữa mượt và nhẹ

def _densify(wps, step=None):
    """Nội suy tuyến tính wps thành dày mỗi `step` px."""
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

WAYPOINTS_DENSE       = _densify(WAYPOINTS)
WAYPOINTS_LEFT_DENSE  = _densify(WAYPOINTS_LEFT)
WAYPOINTS_RIGHT_DENSE = _densify(WAYPOINTS_RIGHT)
print(f'[WP] sparse={len(WAYPOINTS)}  dense={len(WAYPOINTS_DENSE)}  step={WP_DENSE_STEP}px')

# ── GATE (FINISH LINE) ───────────────────────────────────────────────
# Gate NGANG tại raw Y=972, X=180..610.
# Xe đi theo chiều DỌC (Y giảm) cắt qua gate.
# GATE_Y   = trục Y của finish line (xe cross khi Y của xe = GATE_Y)
# GATE_X1..X2 = giới hạn X trong đó gate được tính là hợp lệ
GATE_Y  = int(972 * MAP_SCALE)
GATE_X1 = int(180 * MAP_SCALE)
GATE_X2 = int(610 * MAP_SCALE)

# ── RACER SETUP ──────────────────────────────────────────────────────
setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2,
          max_laps=MAX_LAPS, base_dir=BASE_DIR, map_scale=MAP_SCALE)

# ── GRID SPAWN ───────────────────────────────────────────────────────
# Slot layout: cột TRÁI (idx 0,2,4) và cột PHẢI (idx 1,3,5)
# Đặt ngay dưới gate: ROW_TOP = Y=1150 (raw, 178px dưới gate Y=972),
# cách nhau ROW_GAP=150px (raw) theo chiều dọc.
# Bề rộng cột: outer left lane rộng ~92px → offset ±30px an toàn.
# COL_L=260, COL_R=320 (center=290, offset ±30px raw)
# Để 2 cột nằm chính giữa lane: căn giữa tại X=290 raw
_ROW_GAP = 150    # raw px, 225px scaled
_COL_L   = 260   # raw px — offset -30 từ center 290
_COL_R   = 320   # raw px — offset +30 từ center 290
_ROW_TOP = 1150  # raw px — hàng đầu (50px sau checker zone kết thúc ở Y~1100)

_GRID_SLOTS=[
    (_COL_L, _ROW_TOP),              (_COL_R, _ROW_TOP),
    (_COL_L, _ROW_TOP+_ROW_GAP),    (_COL_R, _ROW_TOP+_ROW_GAP),
    (_COL_L, _ROW_TOP+_ROW_GAP*2),  (_COL_R, _ROW_TOP+_ROW_GAP*2),
]

def _slot_wp(slot_idx):
    """Waypoint dense cho slot (chẵn=lane trái, lẻ=lane phải)."""
    return WAYPOINTS_LEFT_DENSE if slot_idx % 2 == 0 else WAYPOINTS_RIGHT_DENSE

def _slot_pos(i):
    x,y=_GRID_SLOTS[i]; return x*MAP_SCALE, y*MAP_SCALE

_slots=list(range(6)); random.shuffle(_slots)

# ── TẠO XE ───────────────────────────────────────────────────────────
# Đổi NUM_BOTS=1 để 1v1, NUM_BOTS=5 để 6 xe
NUM_BOTS = 5

_p_slot = _slots[0]
px,py=_slot_pos(_p_slot)
player=Racer("ferrari_f430_2005", px, py, 270.0, is_player=True,
             waypoints=_slot_wp(_p_slot))

_other_cars=[c for c in CAR_STATS.keys() if c!="ferrari_f430_2005"]
_bot_ids=random.sample(_other_cars, min(NUM_BOTS,len(_other_cars)))

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
    print(f"[BOT {k+1}] {_bot_ids[k]}  driver={_name} ({_country})  "
          f"aggr={_aggr:.4f}  lane={'L' if _b_slot%2==0 else 'R'}")

all_racers=[player]+bots

# ── HELPERS ──────────────────────────────────────────────────────────
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
            pygame.draw.circle(skid_layer,(60,50,40,200),(ix,iy),3)

def render_world(player):
    # Màu nền: sa mạc/cát khô factory
    crop=pygame.Surface((CROP_SIZE,CROP_SIZE)); crop.fill((185,160,110))
    ox=CROP_SIZE//2-int(player.x); oy=CROP_SIZE//2-int(player.y)
    crop.blit(track,(ox,oy)); crop.blit(skid_layer,(ox,oy))
    for bot in bots:
        if not bot.visible:
            continue
        bx2=CROP_SIZE//2+int(bot.x-player.x)
        by2=CROP_SIZE//2+int(bot.y-player.y)
        if nitro_smoke_img is not None and bot.nitro_active:
            fx,fy=fwd_vec(bot.angle)
            sx2 = bx2 - fx*bot.car_h*0.5
            sy2 = by2 - fy*bot.car_h*0.5
            smoke=pygame.transform.rotate(nitro_smoke_img,270-bot.angle)
            crop.blit(smoke,smoke.get_rect(center=(sx2,sy2)))
        spr=pygame.transform.rotate(bot.sprite,270-bot.angle)
        crop.blit(spr,spr.get_rect(center=(bx2,by2)))
    rot=pygame.transform.rotate(crop,90.0+player.angle)
    screen.fill((0,0,0))
    screen.blit(rot,rot.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))
    if nitro_smoke_img is not None and player.nitro_active:
        sx = CAR_SCREEN_X
        sy = CAR_SCREEN_Y + player.car_h*0.5
        screen.blit(nitro_smoke_img, nitro_smoke_img.get_rect(center=(sx,sy)))
    screen.blit(player.sprite,player.sprite.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))

def update_positions():
    """
    Xếp hạng real-time: lap lớn hơn → trên; cùng lap → so progress.
    race_progress() trả tuple (lap, prog) — sort reverse là đúng.
    """
    progs=[(r,r.race_progress()) for r in all_racers]
    progs.sort(key=lambda x:x[1], reverse=True)
    for rank,(r,_) in enumerate(progs,1):
        r.pos=rank

# ── HUD ──────────────────────────────────────────────────────────────
hud=HUD(screen, total_racers=len(all_racers), max_laps=MAX_LAPS,
        base_dir=BASE_DIR, car_screen_x=CAR_SCREEN_X, car_screen_y=CAR_SCREEN_Y)
pause = PauseMenu(screen, BASE_DIR)

# ── MAIN LOOP ────────────────────────────────────────────────────────
running=True; race_clock=0.0
countdown_t=COUNTDOWN_START; _go_time=None; _go_shown=False
_go_appear_t  = None
_you_fade_t   = None

while running:
    dt=min(clock.tick(FPS)/1000.0, 1/30.0)
    now=time.monotonic()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT: running = False
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: running = False
        act = pause.handle_event(ev)
        if act == "restart":
            countdown_t = COUNTDOWN_START
            _go_shown = False
            _go_time = None
            _go_appear_t = None
            _you_fade_t = None
            for i, r in enumerate(all_racers):
                gx, gy = _slot_pos(_slots[i])
                r.x, r.y = gx, gy
                r.angle = 270.0
                r.velocity = 0.0
                r.wp_idx = 0
                r.finished = False
                if hasattr(r, '_finish_time'): del r._finish_time
        elif act == "quit_showroom":
            running = False

    keys=pygame.key.get_pressed()
    handbrake=keys[pygame.K_SPACE] if countdown_t<=1.0 else False
    want_nitro=keys[pygame.K_LCTRL] if countdown_t<=1.0 else False

    if countdown_t>0:
        countdown_t-=dt
        if countdown_t<0: countdown_t=0

    if countdown_t > 0 and countdown_t < 1.0 and _go_appear_t is None:
        _go_appear_t = now

    race_active=(countdown_t<=1.0)
    if race_active and not _go_shown:
        _go_time=now; _go_shown=True
    if race_active and _you_fade_t is None:
        _you_fade_t = now

    if race_active and not pause.open:
        player.update_player(dt,now,keys,handbrake,want_nitro)
        if not player.finished and handbrake and abs(player.velocity)>25:
            draw_skid(player,dt)
        for bot in bots:
            bot.update_bot(dt,now,all_racers)

    physics.handle_capsule_collisions(all_racers,dt)
    update_positions()

    if player.finished and not hasattr(player,'_finish_time'):
        player._finish_time = now

    render_world(player)

    if _go_shown:
        end_t   = getattr(player,'_finish_time', now)
        elapsed = end_t - _go_time
    else:
        elapsed = 0.0

    if _you_fade_t is None:
        _you_alpha = 255
    else:
        _fade_prog = (now - _you_fade_t) / 0.2
        _you_alpha = max(0, int(255 * (1.0 - _fade_prog)))

    _go_elapsed = (now - _go_appear_t) if _go_appear_t is not None else 0.0
    hud.draw(player, elapsed, you_alpha=_you_alpha)

    if getattr(player,'player_stuck_t',0) > 1.5:
        _f=pygame.font.SysFont("arial",42,bold=True)
        _t=_f.render("REVERSE TO ESCAPE  (S)",True,(255,220,60))
        screen.blit(_t,_t.get_rect(center=(SCREEN_W//2,SCREEN_H//2-160)))

    if player.finished:
        hud.draw_finish_overlay(player)

    if countdown_t > 0 or _go_elapsed < 1.3:
        hud.draw_countdown(countdown_t, _go_elapsed)

    pause.draw()
    pygame.display.flip()

pygame.quit(); sys.exit()

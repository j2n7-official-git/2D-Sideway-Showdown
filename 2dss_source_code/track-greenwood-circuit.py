"""
track-greenwood-circuit.py — Greenwood Circuit
2D Sideway Showdown | 1v1 hoặc 6 xe | 3 vòng

Điều khiển: W/S ga-phanh  A/D lái  SPACE drift  LCTRL (GIỮ) nitro  ESC quay lại showroom

=====================================================================
PHIÊN BẢN REFACTOR — BỌC THÀNH CLASS RaceScreen
=====================================================================
Thay đổi so với bản gốc (script độc lập):
    - KHÔNG còn tự pygame.init() / set_mode() / Clock riêng — dùng
      chung cửa sổ + clock đã có từ twodss_core_main.py.
    - KHÔNG còn while running riêng — core_main gọi handle_event(),
      update(dt), draw(screen) mỗi frame, giống ShowroomScreen/
      MapSelectScreen.
    - KHÔNG còn pygame.quit()/sys.exit() khi xong — set self.result
      để core_main tự quyết định chuyển state tiếp theo.
    - Toàn bộ biến module-level cũ (track, player, bots, hud...)
      chuyển thành self.xxx, gán trong __init__.
    - Nhận car_id của người chơi qua tham số __init__ thay vì
      hard-code "ferrari_f430_2005".
Mọi logic vật lý / AI / HUD / waypoint giữ nguyên 100% so với bản gốc.
=====================================================================
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

# ── CONFIG (giữ module-level vì không đổi theo instance) ───────────
SCREEN_W, SCREEN_H = 1920, 1080
FPS             = 90
MAP_SCALE       = 1.5
MAX_LAPS        = 3
CROP_SIZE       = 2250
CAR_SCREEN_X    = SCREEN_W//2
CAR_SCREEN_Y    = int(SCREEN_H*0.62)
COUNTDOWN_START = 6.0
DEFAULT_CAR_ID  = "ferrari_f430_2005"   # fallback nếu không truyền car_id


class RaceScreen:
    """
    Class quản lý 1 màn đua Greenwood Circuit, dùng chung pygame
    display + clock với core_main. Pattern gọi giống ShowroomScreen/
    MapSelectScreen:

        race = RaceScreen(screen, base_dir, car_id="toyota_ae86_1987")
        race.handle_event(event)   # trong event loop
        race.update(dt)            # mỗi frame
        race.draw(screen)          # mỗi frame, sau update

    self.result:
        None              -> đang đua, chưa làm gì cả
        "quit_showroom"   -> người chơi ESC hoặc bấm Quit ở Pause Menu
    """

    def __init__(self, screen, base_dir, car_id=DEFAULT_CAR_ID):
        self.screen   = screen
        self.base_dir = base_dir
        self.result   = None

        BASE_DIR   = base_dir
        TRACK_PATH = os.path.join(BASE_DIR,"assets","track","greenwood-circuit-track.png")
        self.BASE_DIR = BASE_DIR

        # ── TRACK + WALL MASK ────────────────────────────────────────
        if not os.path.exists(TRACK_PATH):
            print("[CRITICAL] Track PNG not found")
            self.result = "quit_showroom"
            return

        track_raw=pygame.image.load(TRACK_PATH).convert()
        track=pygame.transform.smoothscale(track_raw,
            (int(track_raw.get_width()*MAP_SCALE),
             int(track_raw.get_height()*MAP_SCALE))) if abs(MAP_SCALE-1)>0.001 else track_raw
        MAP_W,MAP_H=track.get_width(),track.get_height()
        print(f"[TRACK] {MAP_W}x{MAP_H}")

        self.track  = track
        self.MAP_W  = MAP_W
        self.MAP_H  = MAP_H
        self.skid_layer=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA)

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
        self.wall_mask = wall_mask

        # ── NITRO SMOKE FX ───────────────────────────────────────────
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
        self.nitro_smoke_img = nitro_smoke_img

        # ── PHYSICS SETUP ────────────────────────────────────────────
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

        # ── WAYPOINTS ────────────────────────────────────────────────
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

        # ── DUAL-LANE WAYPOINTS cho grid 2×3 ──────────────────────────
        _LANE_SPLIT   = 8
        _LANE_OFFSET  = int(50 * MAP_SCALE)

        def _make_lane_wps(wps, offset_x):
            result = list(wps)
            lerp_n = 6
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

        # ── WAYPOINT DENSIFICATION ────────────────────────────────────
        WP_DENSE_STEP = 5

        def _densify(wps, step=None):
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
        print(f'[WP] sparse={len(WAYPOINTS)}  dense={len(WAYPOINTS_DENSE)}  '
              f'step={WP_DENSE_STEP}px')

        GATE_Y  = int(1184*MAP_SCALE)
        GATE_X1 = int(190 *MAP_SCALE)
        GATE_X2 = int(410 *MAP_SCALE)

        # ── RACER SETUP ────────────────────────────────────────────────
        setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2,
                  max_laps=MAX_LAPS, base_dir=BASE_DIR, map_scale=MAP_SCALE)

        # ── GRID SPAWN ───────────────────────────────────────────────
        _ROW_GAP=160; _COL_L=240; _COL_R=360; _ROW_TOP=1263
        _GRID_SLOTS=[
            (_COL_L,_ROW_TOP),(_COL_R,_ROW_TOP),
            (_COL_L,_ROW_TOP+_ROW_GAP),(_COL_R,_ROW_TOP+_ROW_GAP),
            (_COL_L,_ROW_TOP+_ROW_GAP*2),(_COL_R,_ROW_TOP+_ROW_GAP*2),
        ]

        def _slot_wp(slot_idx):
            return WAYPOINTS_LEFT_DENSE if slot_idx % 2 == 0 else WAYPOINTS_RIGHT_DENSE

        def _slot_pos(i):
            x,y=_GRID_SLOTS[i]; return x*MAP_SCALE,y*MAP_SCALE

        # Lưu lại để dùng trong restart (pause menu)
        self._slot_wp  = _slot_wp
        self._slot_pos = _slot_pos

        _slots=list(range(6)); random.shuffle(_slots)
        self._slots = _slots

        # ── TẠO XE ───────────────────────────────────────────────────
        NUM_BOTS = 5
        self.NUM_BOTS = NUM_BOTS

        _p_slot = _slots[0]
        px,py=_slot_pos(_p_slot)
        player=Racer(car_id, px, py, 270.0, is_player=True,
                     waypoints=_slot_wp(_p_slot))

        # Bot có quyền random trùng xe người chơi — không loại trừ car_id
        _other_cars=list(CAR_STATS.keys())
        _bot_ids=random.sample(_other_cars, min(NUM_BOTS,len(_other_cars)))

        _drivers = pick_drivers(NUM_BOTS)

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

        self.player = player
        self.bots   = bots
        self.all_racers=[player]+bots

        # ── HUD ──────────────────────────────────────────────────────
        self.hud=HUD(screen, total_racers=len(self.all_racers), max_laps=MAX_LAPS,
                base_dir=BASE_DIR, car_screen_x=CAR_SCREEN_X, car_screen_y=CAR_SCREEN_Y)
        self.pause = PauseMenu(screen, BASE_DIR)

        # ── TRẠNG THÁI RACE ──────────────────────────────────────────
        self.race_clock=0.0
        self.countdown_t=COUNTDOWN_START
        self._go_time=None
        self._go_shown=False
        self._go_appear_t  = None
        self._you_fade_t   = None
        self._go_elapsed   = 0.0
        self._you_alpha    = 255

    # ─────────────────────────────────────────────────────────────────
    # HELPERS (trước đây là hàm module-level, giờ là method dùng self)
    # ─────────────────────────────────────────────────────────────────
    def _fwd_vec(self, a):
        r=math.radians(a); return math.cos(r),math.sin(r)

    def _draw_skid(self, racer, dt):
        if not racer.is_player: return
        hw,hh=racer.car_w//2,racer.car_h//2
        fx,fy=self._fwd_vec(racer.angle); px2,py2=-fy,fx
        for side in(-1,1):
            wx=racer.x-fx*hh*0.6+px2*hw*0.7*side
            wy=racer.y-fy*hh*0.6+py2*hw*0.7*side
            ix,iy=int(wx),int(wy)
            if 0<=ix<self.MAP_W and 0<=iy<self.MAP_H:
                pygame.draw.circle(self.skid_layer,(50,50,50,200),(ix,iy),3)

    def _render_world(self, screen, player):
        crop=pygame.Surface((CROP_SIZE,CROP_SIZE)); crop.fill((145,170,75))
        ox=CROP_SIZE//2-int(player.x); oy=CROP_SIZE//2-int(player.y)
        crop.blit(self.track,(ox,oy)); crop.blit(self.skid_layer,(ox,oy))
        for bot in self.bots:
            if not bot.visible:
                continue
            bx2=CROP_SIZE//2+int(bot.x-player.x)
            by2=CROP_SIZE//2+int(bot.y-player.y)
            if self.nitro_smoke_img is not None and bot.nitro_active:
                fx,fy=self._fwd_vec(bot.angle)
                sx2 = bx2 - fx*bot.car_h*0.5
                sy2 = by2 - fy*bot.car_h*0.5
                smoke=pygame.transform.rotate(self.nitro_smoke_img,270-bot.angle)
                crop.blit(smoke,smoke.get_rect(center=(sx2,sy2)))
            spr=pygame.transform.rotate(bot.sprite,270-bot.angle)
            crop.blit(spr,spr.get_rect(center=(bx2,by2)))
        rot=pygame.transform.rotate(crop,90.0+player.angle)
        screen.fill((0,0,0))
        screen.blit(rot,rot.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))
        if self.nitro_smoke_img is not None and player.nitro_active:
            sx = CAR_SCREEN_X
            sy = CAR_SCREEN_Y + player.car_h*0.5
            screen.blit(self.nitro_smoke_img, self.nitro_smoke_img.get_rect(center=(sx,sy)))
        screen.blit(player.sprite,player.sprite.get_rect(center=(CAR_SCREEN_X,CAR_SCREEN_Y)))

    def _update_positions(self):
        progs=[(r,r.race_progress()) for r in self.all_racers]
        progs.sort(key=lambda x:x[1], reverse=True)
        for rank,(r,_) in enumerate(progs,1):
            r.pos=rank

    def _do_restart(self):
        self.countdown_t = COUNTDOWN_START
        self._go_shown = False
        self._go_time = None
        self._go_appear_t = None
        self._you_fade_t = None
        for i, r in enumerate(self.all_racers):
            gx, gy = self._slot_pos(self._slots[i])
            r.x, r.y = gx, gy
            r.angle = 270.0
            r.velocity = 0.0
            r.wp_idx = 0
            r.finished = False
            if hasattr(r, '_finish_time'): del r._finish_time

    # ─────────────────────────────────────────────────────────────────
    # API GỌI TỪ CORE_MAIN
    # ─────────────────────────────────────────────────────────────────
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.result = "quit_showroom"
            return

        act = self.pause.handle_event(event)
        if act == "restart":
            self._do_restart()
        elif act == "quit_showroom":
            self.result = "quit_showroom"

    def update(self, dt):
        now=time.monotonic()
        keys=pygame.key.get_pressed()
        handbrake=keys[pygame.K_SPACE] if self.countdown_t<=1.0 else False
        want_nitro=keys[pygame.K_LCTRL] if self.countdown_t<=1.0 else False

        if self.countdown_t>0:
            self.countdown_t-=dt
            if self.countdown_t<0: self.countdown_t=0

        if self.countdown_t > 0 and self.countdown_t < 1.0 and self._go_appear_t is None:
            self._go_appear_t = now

        race_active=(self.countdown_t<=1.0)
        if race_active and not self._go_shown:
            self._go_time=now; self._go_shown=True
        if race_active and self._you_fade_t is None:
            self._you_fade_t = now

        if race_active and not self.pause.open:
            self.player.update_player(dt,now,keys,handbrake,want_nitro)
            if not self.player.finished and handbrake and abs(self.player.velocity)>25:
                self._draw_skid(self.player,dt)
            for bot in self.bots:
                bot.update_bot(dt,now,self.all_racers)

        physics.handle_capsule_collisions(self.all_racers,dt)
        self._update_positions()

        if self.player.finished and not hasattr(self.player,'_finish_time'):
            self.player._finish_time = now

        # Timer: dừng tại thời điểm finish, không chạy tiếp
        if self._go_shown:
            end_t   = getattr(self.player,'_finish_time', now)
            self._race_elapsed = end_t - self._go_time
        else:
            self._race_elapsed = 0.0

        if self._you_fade_t is None:
            self._you_alpha = 255
        else:
            _fade_prog = (now - self._you_fade_t) / 0.2
            self._you_alpha = max(0, int(255 * (1.0 - _fade_prog)))

        self._go_elapsed = (now - self._go_appear_t) if self._go_appear_t is not None else 0.0

    def draw(self, screen):
        self._render_world(screen, self.player)
        self.hud.draw(self.player, self._race_elapsed, you_alpha=self._you_alpha)

        if getattr(self.player,'player_stuck_t',0) > 1.5:
            _f=pygame.font.SysFont("arial",42,bold=True)
            _t=_f.render("REVERSE TO ESCAPE  (S)",True,(255,220,60))
            screen.blit(_t,_t.get_rect(center=(SCREEN_W//2,SCREEN_H//2-160)))

        # --- ĐOẠN KHÚC KẾT THÚC CUỘC ĐUA ---
        if self.player.finished:
            self.hud.draw_finish_overlay(self.player)

        if self.countdown_t > 0 or self._go_elapsed < 1.3:
            self.hud.draw_countdown(self.countdown_t, self._go_elapsed)

        self.pause.draw()


# =====================================================================
# CHẠY ĐỘC LẬP (DEV/TEST) — giữ khả năng test riêng file này bằng
# `python track-greenwood-circuit.py` không cần qua core_main.
# Khi chạy qua core_main, đoạn dưới đây KHÔNG được thực thi vì
# core_main chỉ import class RaceScreen, không chạy __main__.
# =====================================================================
if __name__ == "__main__":
    pygame.init()
    BASE_DIR = _base_dir()
    try:
        _screen=pygame.display.set_mode((SCREEN_W,SCREEN_H),
            pygame.FULLSCREEN|pygame.DOUBLEBUF|pygame.HWSURFACE)
    except Exception:
        _screen=pygame.display.set_mode((SCREEN_W,SCREEN_H),pygame.DOUBLEBUF)
    pygame.display.set_caption("2D Sideway Showdown — Greenwood Circuit (standalone test)")
    _clock=pygame.time.Clock()

    _car_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CAR_ID
    race = RaceScreen(_screen, BASE_DIR, car_id=_car_id)

    _running = True
    while _running and race.result is None:
        _dt = min(_clock.tick(FPS)/1000.0, 1/30.0)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                _running = False
            race.handle_event(ev)
        race.update(_dt)
        race.draw(_screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()
"""
track-sandy-circuit.py — Sandy Circuit (sa mạc)
2D Sideway Showdown | 1v1 hoặc 6 xe | 3 vòng

NGÃ RẼ (BRANCH): đường có 1 fork ở góc trên-phải. main = route chính
(đã trace pixel), loop = nhánh móng ngựa (ước lượng theo hình, nên
test kỹ). Mỗi Racer random chọn 1 route lúc spawn (_BRANCH_CHANCE=0.35).
TODO sau cùng: chặn đi ngược chiều — chưa code trong file này.

Refactor thành class RaceScreen, dùng chung display với core_main.
"""
import pygame, math, os, sys, time, random

from twodss_hud      import HUD, fmt_time, draw_shadow
from twodss_car_data import CAR_STATS
import twodss_physics as physics
from twodss_racer_v2  import Racer, setup_map, pick_drivers
from twodss_pause import PauseMenu

def _base_dir():
    if hasattr(sys,"_MEIPASS"): return sys._MEIPASS
    s=os.path.dirname(os.path.abspath(__file__))
    p=os.path.dirname(s)
    for c in [p,s,os.getcwd()]:
        if os.path.isdir(os.path.join(c,"assets")): return c
    return s

SCREEN_W, SCREEN_H = 1920, 1080
FPS             = 90
MAP_SCALE       = 1.45
MAX_LAPS        = 3
CROP_SIZE       = 2250
CAR_SCREEN_X    = SCREEN_W//2
CAR_SCREEN_Y    = int(SCREEN_H*0.62)
COUNTDOWN_START = 6.0
DEFAULT_CAR_ID  = "ferrari_f430_2005"


class RaceScreen:
    def __init__(self, screen, base_dir, car_id=DEFAULT_CAR_ID):
        self.screen = screen
        self.base_dir = base_dir
        self.result = None

        BASE_DIR = base_dir
        MOVE_SCALE = physics.MOVE_SCALE
        TRACK_PATH = os.path.join(BASE_DIR,"assets","track","sandy-circuit-track.png")

        if not os.path.exists(TRACK_PATH):
            print(f"[CRITICAL] Track PNG not found: {TRACK_PATH}")
            self.result = "quit_showroom"
            return

        track_raw=pygame.image.load(TRACK_PATH).convert()
        track=pygame.transform.smoothscale(track_raw,
            (int(track_raw.get_width()*MAP_SCALE),
             int(track_raw.get_height()*MAP_SCALE))) if abs(MAP_SCALE-1)>0.001 else track_raw
        MAP_W,MAP_H=track.get_width(),track.get_height()
        print(f"[TRACK] {MAP_W}x{MAP_H}")

        self.track = track
        self.MAP_W = MAP_W
        self.MAP_H = MAP_H
        self.skid_layer=pygame.Surface((MAP_W,MAP_H),pygame.SRCALPHA)

        WALL_MASK_PATH=os.path.join(BASE_DIR,"assets","track","sandy-circuit-walls.png")
        wall_mask=None
        try:
            wraw=pygame.image.load(WALL_MASK_PATH).convert()
            wall_mask=pygame.transform.scale(wraw,(MAP_W,MAP_H))
            print(f"[WALL MASK] {wall_mask.get_size()}")
        except FileNotFoundError:
            print(f"[WALL MASK] Not found: {WALL_MASK_PATH}")
        except Exception as e:
            print(f"[WALL MASK] {e}")
        self.wall_mask = wall_mask

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

        # ── WAYPOINTS + BRANCH ─────────────────────────────────────
        _WP_ORIG=[
            (317,1582),(310,1534),(285,1454),(266,1366),(258,1297),
            (260,1209),(287,1131),(297,1037),(322,936), (396,835),
            (459,762), (544,710), (647,680), (748,652), (850,631),
            (947,627), (1043,626),(1139,626),(1239,630),(1351,647),
            (1462,646),(1573,626),(1680,594),(1784,554),(1888,514),
            (1994,479),(2103,456),
            (2206,459),(2306,487),
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

        BRANCH_ENTRY_IDX = 26
        BRANCH_EXIT_IDX  = 28
        _BRANCH_LOOP_PTS = [
            (2150,330),(2260,255),(2420,235),(2580,265),(2700,345),
            (2740,430),
        ]

        def _build_route(use_branch_loop=False):
            if not use_branch_loop:
                return list(_WP_ORIG)
            return _WP_ORIG[:BRANCH_ENTRY_IDX+1] + _BRANCH_LOOP_PTS + _WP_ORIG[BRANCH_EXIT_IDX:]

        WAYPOINTS = _build_route(use_branch_loop=False)
        WAYPOINTS=[(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in WAYPOINTS]

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

        def _route_for(use_branch_loop):
            return [(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in _build_route(use_branch_loop)]

        WP_DENSE_STEP = 3

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

        def _make_dense_route(use_branch_loop, offset_x=0):
            base = _route_for(use_branch_loop)
            laned = _make_lane_wps(base, offset_x) if offset_x != 0 else base
            return _densify(laned)

        WAYPOINTS_DENSE = _densify(WAYPOINTS)
        print(f'[WP] sparse={len(WAYPOINTS)}  dense={len(WAYPOINTS_DENSE)}  '
              f'step={WP_DENSE_STEP}px  branch_entry_idx={BRANCH_ENTRY_IDX}')

        GATE_Y  = int(1324*MAP_SCALE)
        GATE_X1 = int(190 *MAP_SCALE)
        GATE_X2 = int(450 *MAP_SCALE)

        setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2,
                  max_laps=MAX_LAPS, base_dir=BASE_DIR, map_scale=MAP_SCALE,
                  car_display_w=97)

        # ── GRID SPAWN ───────────────────────────────────────────────
        _ROW_GAP = 180; _COL_L=250; _COL_R=380; _ROW_TOP=1450
        _GRID_SLOTS=[
            (_COL_L,_ROW_TOP),(_COL_R,_ROW_TOP),
            (_COL_L,_ROW_TOP+_ROW_GAP),(_COL_R,_ROW_TOP+_ROW_GAP),
            (_COL_L,_ROW_TOP+_ROW_GAP*2),(_COL_R,_ROW_TOP+_ROW_GAP*2),
        ]

        def _slot_pos(i):
            x,y=_GRID_SLOTS[i]; return x*MAP_SCALE,y*MAP_SCALE

        self._slot_pos = _slot_pos

        _slots=list(range(6)); random.shuffle(_slots)
        self._slots = _slots

        _BRANCH_CHANCE = 0.35

        def _slot_wp(slot_idx, use_branch_loop):
            offset = -_LANE_OFFSET if slot_idx % 2 == 0 else _LANE_OFFSET
            return _make_dense_route(use_branch_loop, offset)

        self._slot_wp = _slot_wp
        self._BRANCH_CHANCE = _BRANCH_CHANCE

        # ── TẠO XE ───────────────────────────────────────────────────
        NUM_BOTS = 5
        self.NUM_BOTS = NUM_BOTS

        _p_slot = _slots[0]
        _p_branch = random.random() < _BRANCH_CHANCE
        px,py=_slot_pos(_p_slot)
        player=Racer(car_id, px, py, 270.0, is_player=True,
                     waypoints=_slot_wp(_p_slot, _p_branch))
        print(f"[PLAYER] route={'BRANCH-LOOP' if _p_branch else 'MAIN'}  lane={'L' if _p_slot%2==0 else 'R'}  car={car_id}")

        _other_cars=list(CAR_STATS.keys())
        _bot_ids=random.sample(_other_cars, min(NUM_BOTS,len(_other_cars)))

        _drivers = pick_drivers(NUM_BOTS)

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

        self.player = player
        self.bots   = bots
        self.all_racers=[player]+bots

        self.hud=HUD(screen, total_racers=len(self.all_racers), max_laps=MAX_LAPS,
                base_dir=BASE_DIR, car_screen_x=CAR_SCREEN_X, car_screen_y=CAR_SCREEN_Y)
        self.pause = PauseMenu(screen, BASE_DIR)

        self.race_clock=0.0
        self.countdown_t=COUNTDOWN_START
        self._go_time=None
        self._go_shown=False
        self._go_appear_t  = None
        self._you_fade_t   = None
        self._go_elapsed   = 0.0
        self._you_alpha    = 255

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
        crop=pygame.Surface((CROP_SIZE,CROP_SIZE)); crop.fill((230,170,75))
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


if __name__ == "__main__":
    pygame.init()
    BASE_DIR = _base_dir()
    try:
        _screen=pygame.display.set_mode((SCREEN_W,SCREEN_H),
            pygame.FULLSCREEN|pygame.DOUBLEBUF|pygame.HWSURFACE)
    except Exception:
        _screen=pygame.display.set_mode((SCREEN_W,SCREEN_H),pygame.DOUBLEBUF)
    pygame.display.set_caption("2D Sideway Showdown — Sandy Circuit (standalone test)")
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
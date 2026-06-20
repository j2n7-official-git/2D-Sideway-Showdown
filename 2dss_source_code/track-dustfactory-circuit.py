"""
track-dustfactory-circuit.py — The Dust Factory Circuit
2D Sideway Showdown | 1v1 hoặc 6 xe | 3 vòng

Finish line ngang tại raw Y=972. Bố cục: thẳng trái (2 làn) → cua
trên-trái → ngang top → S-curve giữa → thẳng phải → hairpin dưới
(3 U-turn lồng) → về trái. MAP_SCALE=1.2.

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
MAP_SCALE       = 1.2
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
        TRACK_PATH = os.path.join(BASE_DIR,"assets","track","the-dustfactory-circuit.png")

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

        WALL_MASK_PATH=os.path.join(BASE_DIR,"assets","track","the-dustfactory-walls.png")
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
            move_scale = physics.MOVE_SCALE,
            gate_safe  = (
                int(150*MAP_SCALE), int(650*MAP_SCALE),
                int(880*MAP_SCALE), int(1120*MAP_SCALE),
            ),
        )

        # ── WAYPOINTS ────────────────────────────────────────────────
        _WP_ORIG=[
            (290,1150),(290,1050),(290,900),(290,750),
            (290,560),(380,430),(460,380),(560,300),
            (660,280),(900,280),(1150,280),(1350,280),
            (1340,340),(1920,360),(2700,360),
            (2788,500),(2788,700),(2788,960),(2788,1200),
            (2788,1440),(2788,1700),(2788,1960),
            (2596,2000),(2272,2040),(2100,2040),
            (2200,2160),(2340,2360),(2420,2440),
            (2272,2280),(2100,2080),(1764,2080),
            (1596,2080),(1596,2200),(1596,2360),(1596,2440),
            (1500,2300),(1040,2080),
            (900,2160),(900,2360),(1000,2440),
            (900,2080),(576,1920),
            (510,1700),(500,1600),(488,1520),(488,1440),
            (488,1300),(488,1200),(488,1100),(488,950),(488,820),
            (390,720),(290,650),(290,520),
        ]
        WAYPOINTS=[(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in _WP_ORIG]

        _LANE_SPLIT  = 6
        _LANE_OFFSET = int(30 * MAP_SCALE)

        def _make_lane_wps(wps, offset_x):
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

        GATE_Y  = int(972*MAP_SCALE)
        GATE_X1 = int(180*MAP_SCALE)
        GATE_X2 = int(610*MAP_SCALE)

        setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2,
                  max_laps=MAX_LAPS, base_dir=BASE_DIR, map_scale=MAP_SCALE)

        # ── GRID SPAWN ───────────────────────────────────────────────
        _ROW_GAP = 180
        _COL_L   = 280
        _COL_R   = 460
        _ROW_TOP = 1180

        _GRID_SLOTS=[
            (_COL_L, _ROW_TOP),              (_COL_R, _ROW_TOP),
            (_COL_L, _ROW_TOP+_ROW_GAP),    (_COL_R, _ROW_TOP+_ROW_GAP),
            (_COL_L, _ROW_TOP+_ROW_GAP*2),  (_COL_R, _ROW_TOP+_ROW_GAP*2),
        ]

        def _slot_wp(slot_idx):
            return WAYPOINTS_LEFT_DENSE if slot_idx % 2 == 0 else WAYPOINTS_RIGHT_DENSE

        def _slot_pos(i):
            x,y=_GRID_SLOTS[i]; return x*MAP_SCALE, y*MAP_SCALE

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
            print(f"[BOT {k+1}] {_bot_ids[k]}  driver={_name} ({_country})  "
                  f"aggr={_aggr:.4f}  lane={'L' if _b_slot%2==0 else 'R'}")

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
                pygame.draw.circle(self.skid_layer,(60,50,40,200),(ix,iy),3)

    def _render_world(self, screen, player):
        crop=pygame.Surface((CROP_SIZE,CROP_SIZE)); crop.fill((185,160,110))
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
    pygame.display.set_caption("2D Sideway Showdown — The Dust Factory Circuit (standalone test)")
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
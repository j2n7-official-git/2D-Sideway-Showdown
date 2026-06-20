"""
track-velodrama-circuit.py — Velodrama Circuit (2 TẦNG / OVERPASS)
Đã được REFACTOR thành CLASS RaceScreen để tích hợp với twodss_core_main.py
"""
import pygame, math, os, sys, time, random
from twodss_hud      import HUD, fmt_time, draw_shadow
from twodss_car_data import CAR_STATS
import twodss_physics as physics
from twodss_racer_v2  import Racer, setup_map, pick_drivers
from twodss_pause import PauseMenu

# ── CONFIG CHUNG ───────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1920, 1080
MAP_SCALE       = 1.5
MAX_LAPS        = 3
CROP_SIZE       = 2250
CAR_SCREEN_X    = SCREEN_W // 2
CAR_SCREEN_Y    = int(SCREEN_H * 0.62)
COUNTDOWN_START = 6.0

# ── WAYPOINTS & TẦNG (Giữ nguyên gốc để tối ưu, chỉ tính 1 lần) ───
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
_WP_LEVEL=[
    0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,1,1, 1,1,1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,0,0,0,0,0,0,
]

_WP_ORIG = [_WP_ORIG[0]] + _WP_ORIG[:0:-1]
_WP_LEVEL = [_WP_LEVEL[0]] + _WP_LEVEL[:0:-1]
WAYPOINTS=[(int(x*MAP_SCALE),int(y*MAP_SCALE)) for x,y in _WP_ORIG]

def _rect(x0,y0,x1,y1): return (int(x0*MAP_SCALE),int(y0*MAP_SCALE),int(x1*MAP_SCALE),int(y1*MAP_SCALE))
OCCLUDERS=[
    _rect(660, 1055, 950, 1305),    # ô vàng TRÁI  (gầm cầu trái)
    _rect(2160,1055, 2440,1305),    # ô vàng PHẢI (gầm cầu phải)
]
OCC_FADE = int(150*MAP_SCALE)

_LANE_SPLIT  = 8
_LANE_WIDEN  = 1.4
_LANE_OFFSET = int(55 * MAP_SCALE * _LANE_WIDEN)

def _make_lane_wps(wps, offset_x):
    result=list(wps); lerp_n=6
    for i in range(len(wps)):
        if i < _LANE_SPLIT:                 ox=offset_x
        elif i < _LANE_SPLIT+lerp_n:        ox=int(offset_x*(1.0-(i-_LANE_SPLIT)/lerp_n))
        else:                               ox=0
        result[i]=(wps[i][0]+ox, wps[i][1])
    return result

WAYPOINTS_LEFT  = _make_lane_wps(WAYPOINTS, -_LANE_OFFSET)
WAYPOINTS_RIGHT = _make_lane_wps(WAYPOINTS, +_LANE_OFFSET)

WP_DENSE_STEP = 5

def _densify(wps, levels, step=WP_DENSE_STEP):
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

GATE_Y  = int(1895*MAP_SCALE)
GATE_X1 = int(677 *MAP_SCALE)
GATE_X2 = int(912 *MAP_SCALE)

_FLAG_X, _FLAG_Y = 795, 1895
_COL_DX = int(50 * 1.4)
_ROW_TOP =400
_ROW_GAP  = int(160 * 1.3)
_GRID_SLOTS=[]
for r in range(3):
    y = _FLAG_Y + _ROW_TOP - r * _ROW_GAP
    _GRID_SLOTS.append((_FLAG_X-_COL_DX, y))
    _GRID_SLOTS.append((_FLAG_X+_COL_DX, y))

_SPAWN_ANGLE = 90

def _slot_wp(slot_idx):
    if slot_idx%2==0: return WAYPOINTS_LEFT_DENSE,  LEVEL_LEFT_DENSE
    else:             return WAYPOINTS_RIGHT_DENSE, LEVEL_RIGHT_DENSE

def _slot_pos(i):
    x,y=_GRID_SLOTS[i]; return x*MAP_SCALE, y*MAP_SCALE

def fwd_vec(a):
    r=math.radians(a); return math.cos(r),math.sin(r)


# ── MAIN CLASS (GIAO TIẾP VỚI CORE_MAIN) ───────────────────────────
class RaceScreen:
    def __init__(self, screen, base_dir, car_id="ferrari_f430_2005"):
        self.screen = screen
        self.base_dir = base_dir
        self.car_id = car_id
        self.result = None

        # 1. LOAD ASSETS
        TRACK_PATH       = os.path.join(self.base_dir, "assets", "track", "velodrama-track.png")
        WALL_MASK_PATH   = os.path.join(self.base_dir, "assets", "track", "velodrama-walls.png")
        NITRO_SMOKE_PATH = os.path.join(self.base_dir, "assets", "ui-race-mode", "2dss-nitrosmoke.png")

        track_raw = pygame.image.load(TRACK_PATH).convert()
        self.track = pygame.transform.smoothscale(track_raw,
            (int(track_raw.get_width()*MAP_SCALE), int(track_raw.get_height()*MAP_SCALE))) if abs(MAP_SCALE-1)>0.001 else track_raw
        self.MAP_W, self.MAP_H = self.track.get_width(), self.track.get_height()

        self.skid_layer = pygame.Surface((self.MAP_W, self.MAP_H), pygame.SRCALPHA)

        wraw = pygame.image.load(WALL_MASK_PATH).convert()
        self.wall_mask = pygame.transform.scale(wraw, (self.MAP_W, self.MAP_H)) if abs(MAP_SCALE-1)>0.001 else wraw

        self.nitro_smoke_img = None
        if os.path.exists(NITRO_SMOKE_PATH):
            _ns_raw = pygame.image.load(NITRO_SMOKE_PATH).convert_alpha()
            self.nitro_smoke_img = pygame.transform.smoothscale(_ns_raw,
                (int(_ns_raw.get_width()*0.4), int(_ns_raw.get_height()*0.4)))

        # 2. PHYSICS SETUP
        physics.setup(
            track      = self.track,
            wall_mask  = self.wall_mask,
            map_w      = self.MAP_W,
            map_h      = self.MAP_H,
            move_scale = physics.MOVE_SCALE,
            gate_safe  = (
                int(660*MAP_SCALE), int(930*MAP_SCALE),
                int(1820*MAP_SCALE),int(1970*MAP_SCALE),
            ),
        )

        setup_map(WAYPOINTS, GATE_Y, GATE_X1, GATE_X2, max_laps=MAX_LAPS, base_dir=self.base_dir, map_scale=MAP_SCALE)

        # 3. RACER SPAWN
        self._slots = list(range(6))
        random.shuffle(self._slots)
        NUM_BOTS = 5

        _p_slot = self._slots[0]
        px, py = _slot_pos(_p_slot)
        _p_wp, _p_lv = _slot_wp(_p_slot)
        self.player = Racer(self.car_id, px, py, _SPAWN_ANGLE, is_player=True, waypoints=_p_wp)
        self.player._levels = _p_lv

        _other_cars = list(CAR_STATS.keys())
        if self.car_id in _other_cars: _other_cars.remove(self.car_id)
        _bot_ids = random.sample(_other_cars, min(NUM_BOTS, len(_other_cars)))
        _drivers = pick_drivers(NUM_BOTS)

        self.bots = []
        for k in range(NUM_BOTS):
            _b_slot = self._slots[k+1]
            bx, by = _slot_pos(_b_slot)
            _b_wp, _b_lv = _slot_wp(_b_slot)
            _name, _country, _aggr = _drivers[k]
            bot = Racer(_bot_ids[k], bx, by, _SPAWN_ANGLE, waypoints=_b_wp,
                        driver_name=_name, driver_country=_country, composure=_aggr)
            bot._levels = _b_lv
            bot.wp_idx = min(range(len(_b_wp)), key=lambda i,bx=bx,by=by: math.hypot(_b_wp[i][0]-bx,_b_wp[i][1]-by))
            bot.velocity = k * 5.0
            self.bots.append(bot)

        self.all_racers = [self.player] + self.bots

        # 4. HUD & PAUSE
        self.hud = HUD(self.screen, total_racers=len(self.all_racers), max_laps=MAX_LAPS,
                       base_dir=self.base_dir, car_screen_x=CAR_SCREEN_X, car_screen_y=CAR_SCREEN_Y)
        self.pause = PauseMenu(self.screen, self.base_dir)

        self.reset_race()

    def reset_race(self):
        self.countdown_t = COUNTDOWN_START
        self.go_shown = False
        self.go_time = None
        self.go_appear_t = None
        self.you_fade_t = None
        for i, r in enumerate(self.all_racers):
            gx, gy = _slot_pos(self._slots[i])
            r.x, r.y = gx, gy
            r.angle = _SPAWN_ANGLE
            r.velocity = 0.0
            r.wp_idx = 0
            r.finished = False
            if hasattr(r, '_finish_time'):
                del r._finish_time

    def handle_event(self, event):
        act = self.pause.handle_event(event)
        if act == "restart":
            self.reset_race()
        elif act == "quit_showroom":
            self.result = "quit_showroom"

    def racer_alpha(self, racer):
        lv = 1
        levels = getattr(racer, '_levels', None)
        if levels:
            i = getattr(racer, 'wp_idx', 0)
            i = max(0, min(i, len(levels)-1))
            lv = levels[i]
        if lv == 1: return 255

        rx, ry = racer.x, racer.y
        a = 255
        for x0, y0, x1, y1 in OCCLUDERS:
            if x0 <= rx <= x1:
                if y0 <= ry <= y1: return 0
                if y1 < ry <= y1 + OCC_FADE:
                    a = min(a, int(255*(ry-y1)/OCC_FADE))
                elif y0 - OCC_FADE <= ry < y0:
                    a = min(a, int(255*(y0-ry)/OCC_FADE))
        return max(0, a)

    def draw_skid(self, racer, dt):
        if not racer.is_player: return
        hw, hh = racer.car_w // 2, racer.car_h // 2
        fx, fy = fwd_vec(racer.angle); px2, py2 = -fy, fx
        for side in (-1, 1):
            wx = racer.x - fx * hh * 0.6 + px2 * hw * 0.7 * side
            wy = racer.y - fy * hh * 0.6 + py2 * hw * 0.7 * side
            ix, iy = int(wx), int(wy)
            if 0 <= ix < self.MAP_W and 0 <= iy < self.MAP_H:
                pygame.draw.circle(self.skid_layer, (50, 50, 50, 200), (ix, iy), 3)

    def update(self, dt):
        now = time.monotonic()
        keys = pygame.key.get_pressed()
        handbrake = keys[pygame.K_SPACE] if self.countdown_t <= 1.0 else False
        want_nitro = keys[pygame.K_LCTRL] if self.countdown_t <= 1.0 else False

        if self.countdown_t > 0:
            self.countdown_t -= dt
            if self.countdown_t < 0: self.countdown_t = 0

        if self.countdown_t > 0 and self.countdown_t < 1.0 and self.go_appear_t is None:
            self.go_appear_t = now

        race_active = (self.countdown_t <= 1.0)
        if race_active and not self.go_shown:
            self.go_time = now
            self.go_shown = True
        if race_active and self.you_fade_t is None:
            self.you_fade_t = now

        if race_active and not self.pause.open:
            self.player.update_player(dt, now, keys, handbrake, want_nitro)
            if not self.player.finished and handbrake and abs(self.player.velocity) > 25:
                self.draw_skid(self.player, dt)
            for bot in self.bots:
                bot.update_bot(dt, now, self.all_racers)

        physics.handle_capsule_collisions(self.all_racers, dt)

        progs = [(r, r.race_progress()) for r in self.all_racers]
        progs.sort(key=lambda x: x[1], reverse=True)
        for rank, (r, _) in enumerate(progs, 1):
            r.pos = rank

        if self.player.finished and not hasattr(self.player, '_finish_time'):
            self.player._finish_time = now

    def draw(self, surface):
        now = time.monotonic()
        crop = pygame.Surface((CROP_SIZE, CROP_SIZE))
        crop.fill((26, 30, 42))
        ox = CROP_SIZE // 2 - int(self.player.x)
        oy = CROP_SIZE // 2 - int(self.player.y)

        crop.blit(self.track, (ox, oy))
        crop.blit(self.skid_layer, (ox, oy))

        for bot in self.bots:
            if not bot.visible: continue
            a = self.racer_alpha(bot)
            if a <= 0: continue

            bx2 = CROP_SIZE // 2 + int(bot.x - self.player.x)
            by2 = CROP_SIZE // 2 + int(bot.y - self.player.y)

            if self.nitro_smoke_img is not None and bot.nitro_active and a >= 255:
                fx, fy = fwd_vec(bot.angle)
                sx2 = bx2 - fx * bot.car_h * 0.5
                sy2 = by2 - fy * bot.car_h * 0.5
                smoke = pygame.transform.rotate(self.nitro_smoke_img, 270 - bot.angle)
                crop.blit(smoke, smoke.get_rect(center=(sx2, sy2)))

            spr = pygame.transform.rotate(bot.sprite, 270 - bot.angle)
            if a < 255:
                spr = spr.copy()
                spr.set_alpha(a)
            crop.blit(spr, spr.get_rect(center=(bx2, by2)))

        rot = pygame.transform.rotate(crop, 90.0 + self.player.angle)
        surface.fill((0, 0, 0))
        surface.blit(rot, rot.get_rect(center=(CAR_SCREEN_X, CAR_SCREEN_Y)))

        if self.nitro_smoke_img is not None and self.player.nitro_active:
            sx, sy = CAR_SCREEN_X, CAR_SCREEN_Y + self.player.car_h * 0.5
            surface.blit(self.nitro_smoke_img, self.nitro_smoke_img.get_rect(center=(sx, sy)))

        pa = self.racer_alpha(self.player)
        psp = self.player.sprite
        if pa < 255:
            psp = psp.copy()
            psp.set_alpha(max(70, pa))
        surface.blit(psp, psp.get_rect(center=(CAR_SCREEN_X, CAR_SCREEN_Y)))

        # HUD
        if self.go_shown:
            end_t = getattr(self.player, '_finish_time', now)
            elapsed = end_t - self.go_time
        else:
            elapsed = 0.0

        if self.you_fade_t is None:
            _you_alpha = 255
        else:
            _you_alpha = max(0, int(255 * (1.0 - (now - self.you_fade_t) / 0.2)))

        _go_elapsed = (now - self.go_appear_t) if self.go_appear_t is not None else 0.0
        self.hud.draw(self.player, elapsed, you_alpha=_you_alpha)

        if getattr(self.player, 'player_stuck_t', 0) > 1.5:
            _f = pygame.font.SysFont("arial", 42, bold=True)
            _t = _f.render("REVERSE TO ESCAPE  (S)", True, (255, 220, 60))
            surface.blit(_t, _t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 160)))

        # --- ĐOẠN KHÚC KẾT THÚC CUỘC ĐUA ---
        if self.player.finished:
            self.hud.draw_finish_overlay(self.player)

        if self.countdown_t > 0 or self._go_elapsed < 1.3:
            self.hud.draw_countdown(self.countdown_t, self._go_elapsed)

        self.pause.draw()
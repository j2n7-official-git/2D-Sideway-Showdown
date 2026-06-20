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
_wall_mask = None
_MAP_W = 0
_MAP_H = 0
MOVE_SCALE = 3.8
_MOVE_SCALE = MOVE_SCALE
_GATE_SAFE = (0, 0, 0, 0)

def setup(track, wall_mask, map_w: int, map_h: int,
          move_scale: float = MOVE_SCALE,
          gate_safe: tuple = (0, 0, 0, 0)):
    global _track, _wall_mask, _MAP_W, _MAP_H, _MOVE_SCALE, _GATE_SAFE
    _track      = track
    _wall_mask  = wall_mask
    _MAP_W      = map_w
    _MAP_H      = map_h
    _MOVE_SCALE = move_scale
    _GATE_SAFE  = gate_safe

def clamp(v, lo, hi):
    return max(lo, min(v, hi))

_NITRO_DECAY_SLOPE = 1.5

def step_nitro_bonus(current: float, target: float, dt: float,
                      full_boost: float = None, boost_time: float = None) -> float:
    if abs(target - current) < 0.01:
        return target
    if target >= current:
        return target
    if full_boost and boost_time:
        unit = full_boost / max(0.01, boost_time)
    else:
        unit = max(current, 1.0)
    rate = _NITRO_DECAY_SLOPE * unit
    new_val = current - rate * dt
    return max(target, new_val)

def fwd_vec(a: float):
    r = math.radians(a)
    return math.cos(r), math.sin(r)

def angle_diff(a: float, b: float) -> float:
    d = (a - b) % 360
    return d - 360 if d > 180 else d

def _in_gate_safe_zone(ix: int, iy: int) -> bool:
    x1, x2, y1, y2 = _GATE_SAFE
    return x1 <= ix <= x2 and y1 <= iy <= y2

def is_offroad(px: float, py: float) -> bool:
    ix, iy = int(px), int(py)
    if ix < 0 or iy < 0 or ix >= _MAP_W or iy >= _MAP_H:
        return True
    if _in_gate_safe_zone(ix, iy):
        return False
    try:
        c = _track.get_at((ix, iy))
    except:
        return True
    r, g, b = int(c[0]), int(c[1]), int(c[2])
    avg  = (r + g + b) / 3.0
    gdom = g > r + 10 and g > b + 10
    if gdom and avg > 55:                      return True
    if b > r + 18 and b > g + 8 and avg > 75: return True
    return False

def is_hard_wall(px: float, py: float) -> bool:
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

_THR_LOW_FRAC    = 0.25
_THR_HIGH_FRAC   = 0.75
_THR_LOW_MULT    = 0.55
_THR_MID_MULT    = 1.35
_THR_HIGH_MULT   = 0.18

def _throttle_mult(ratio: float) -> float:
    if ratio <= 0.0:
        return _THR_LOW_MULT
    if ratio < _THR_LOW_FRAC:
        t = ratio / _THR_LOW_FRAC
        return _THR_LOW_MULT + (_THR_MID_MULT - _THR_LOW_MULT) * t * 0.5
    if ratio < _THR_HIGH_FRAC:
        t = (ratio - _THR_LOW_FRAC) / (_THR_HIGH_FRAC - _THR_LOW_FRAC)
        peak = _THR_MID_MULT
        edge = _THR_MID_MULT * 0.78
        return edge + (peak - edge) * (1.0 - abs(t - 0.5) * 2.0)
    if ratio < 1.0:
        t = (ratio - _THR_HIGH_FRAC) / (1.0 - _THR_HIGH_FRAC)
        start = _THR_MID_MULT * 0.78
        return start + (_THR_HIGH_MULT - start) * t
    return _THR_HIGH_MULT

def apply_throttle(racer, dt: float, reverse: bool = False, mult: float = 1.0) -> None:
    top = max(racer.max_speed, 1.0)
    ratio = clamp(abs(racer.velocity) / top, 0.0, 1.0)
    m = _throttle_mult(ratio) * mult
    step = racer.acceleration * m * dt
    if reverse:
        racer.velocity -= step
    else:
        racer.velocity += step

def release_throttle_decay(racer, dt: float) -> None:
    top = max(racer.max_speed, 1.0)
    ratio = clamp(abs(racer.velocity) / top, 0.0, 1.0)
    decel_mult = 0.35 + 0.9 * math.sin(math.pi * ratio)
    d = racer.friction * decel_mult * dt
    if abs(racer.velocity) <= d:
        racer.velocity = 0.0
    else:
        sign = 1.0 if racer.velocity > 0 else -1.0
        racer.velocity -= sign * d

def steer(racer, steer_input: float, dt: float, handbrake: bool = False):
    v_px = racer.velocity * _MOVE_SCALE
    if abs(v_px) < 4.0 or abs(steer_input) < 0.01:
        return False
    top      = getattr(racer, '_cur_top', racer.max_speed)
    spd_r    = min(abs(racer.velocity) / max(top, 1), 1.0)
    delta_max = (38.0 - spd_r * 18.0) + (12.0 if handbrake else 0.0)
    delta     = math.radians(steer_input * delta_max)
    L = max(racer.car_h * 0.62, 8.0)
    omega_deg = math.degrees(v_px / L * math.tan(delta)) * dt
    if racer.velocity < 0:
        omega_deg = -omega_deg
    return _rotate_about_rear(racer, omega_deg)

def _rotate_about_rear(racer, d_ang: float) -> bool:
    r0 = math.radians(racer.angle)
    fx, fy = math.cos(r0), math.sin(r0)
    half = racer.car_h * 0.5
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

_POLY_N    = 30
_POLY_STEP = 1.5
_POLY_FLAT_FRONT = 0.55
_POLY_FLAT_REAR  = 0.80

def _poly_param_cosine(i, n):
    t = i / (n - 1)
    return -math.cos(t * math.pi)

def _car_width_profile(s, hw):
    a = abs(s)
    flat = _POLY_FLAT_REAR if s < 0 else _POLY_FLAT_FRONT
    if a <= flat:
        return hw
    t = (a - flat) / (1.0 - flat)
    return hw * math.sqrt(max(0.0, 1.0 - t*t))

def _car_polygon_world(racer, x, y):
    fx, fy = fwd_vec(racer.angle)
    px, py = -fy, fx
    L  = racer.car_h * 0.48
    hw = racer.car_w * 0.48
    half_n = _POLY_N // 2
    verts = []
    for i in range(half_n):
        s = _poly_param_cosine(i, half_n)
        w = _car_width_profile(s, hw)
        lx, ly = s * L, w
        verts.append((x + lx*fx + ly*px, y + lx*fy + ly*py))
    for i in range(half_n):
        s = -_poly_param_cosine(i, half_n)
        w = _car_width_profile(s, hw)
        lx, ly = s * L, -w
        verts.append((x + lx*fx + ly*px, y + lx*fy + ly*py))
    return verts

def _car_outline_clear(racer, x, y):
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

def _wall_normal(x, y, fx, fy, r=6):
    sx = sy = 0.0
    for a_deg in range(0, 360, 45):
        ar = math.radians(a_deg)
        dx, dy = math.cos(ar), math.sin(ar)
        if is_hard_wall(int(x + dx*r), int(y + dy*r)):
            sx -= dx; sy -= dy
    m = math.hypot(sx, sy)
    if m < 1e-3:
        return -fx, -fy
    return sx/m, sy/m

def resolve_wall_collision(racer, tx, ty, fx, fy, dt):
    racer.x, racer.y = tx, ty
    wnx, wny = _wall_normal(tx, ty, fx, fy)
    tang_x, tang_y = -wny, wnx

    mdx, mdy = fwd_vec(getattr(racer, '_move_dir', racer.angle))
    v_px = racer.velocity * _MOVE_SCALE
    vx, vy = mdx*v_px, mdy*v_px

    v_n = vx*wnx + vy*wny
    v_t = vx*tang_x + vy*tang_y
    RESTITUTION = 0.10
    new_vn = (-v_n*RESTITUTION) if v_n < 0 else v_n
    new_vx = wnx*new_vn + tang_x*v_t
    new_vy = wny*new_vn + tang_y*v_t

    new_spd = math.hypot(new_vx, new_vy)
    if new_spd > 1e-3:
        slide_dir = math.degrees(math.atan2(new_vy, new_vx))
        racer._move_dir = slide_dir
        _misalign  = abs(angle_diff(slide_dir, racer.angle)) / 180.0
        SLIP_DECEL = _misalign * 5.0
        racer.velocity = max(0.0, new_spd/_MOVE_SCALE - SLIP_DECEL*dt)
    else:
        racer.velocity = 0.0
    racer._cached_normal = (wnx, wny)

def drift_physics(car, dt=0.016):
    pass # Disabled intentionally

def move_car(racer, dt: float) -> None:
    fx, fy = fwd_vec(getattr(racer, '_move_dir', racer.angle))
    spd = racer.velocity * _MOVE_SCALE
    vx, vy = fx * spd, fy * spd

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
        resolve_wall_collision(racer, tx, ty, fx, fy, dt)


# =====================================================================
# CAR-TO-CAR COLLISION — OBB / SAT & CAPSULE
# =====================================================================

_COLL_E = 0.35
_COLL_ANG = 0.055
_COLL_ITERS = 5
_MAX_IMPULSE = 28.0


def _obb_sat(ax, ay, a_ang, a_hw, a_hh, bx, by, b_ang, b_hw, b_hh):
    afx = math.cos(math.radians(a_ang));
    afy = math.sin(math.radians(a_ang))
    arx = -afy;
    ary = afx
    bfx = math.cos(math.radians(b_ang));
    bfy = math.sin(math.radians(b_ang))
    brx = -bfy;
    bry = bfx
    ddx = bx - ax;
    ddy = by - ay
    min_depth = 1e9;
    best_nx = 1.0;
    best_ny = 0.0

    for (nx, ny) in [(afx, afy), (arx, ary), (bfx, bfy), (brx, bry)]:
        a_ext = abs(afx * nx + afy * ny) * a_hh + abs(arx * nx + ary * ny) * a_hw
        b_ctr = ddx * nx + ddy * ny
        b_ext = abs(bfx * nx + bfy * ny) * b_hh + abs(brx * nx + bry * ny) * b_hw
        sep = abs(b_ctr) - (a_ext + b_ext)
        if sep > 0:
            return False, 0.0, 0.0, 0.0
        depth = -sep
        if depth < min_depth:
            min_depth = depth
            sign = 1.0 if b_ctr >= 0 else -1.0
            best_nx = nx * sign
            best_ny = ny * sign

    return True, best_nx, best_ny, min_depth


def handle_car_collisions(racers: list, dt: float) -> None:
    # Hàm này dùng dự phòng cho OBB SAT (thường dùng hàm handle_capsule_collisions bên dưới)
    pass


def _closest_points_segments(p1, p2, q1, q2):
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = q2[0] - q1[0], q2[1] - q1[1]
    rx, ry = p1[0] - q1[0], p1[1] - q1[1]

    a = d1x * d1x + d1y * d1y
    e = d2x * d2x + d2y * d2y
    f = d2x * rx + d2y * ry

    if a < 1e-6 and e < 1e-6:
        return p1, q1

    if a < 1e-6:
        s = 0.0
        t = clamp(f / e, 0.0, 1.0)
    else:
        c = d1x * rx + d1y * ry
        if e < 1e-6:
            t = 0.0
            s = clamp(-c / a, 0.0, 1.0)
        else:
            b = d1x * d2x + d1y * d2y
            denom = a * e - b * b
            if denom > 1e-6:
                s = clamp((b * f - c * e) / denom, 0.0, 1.0)
            else:
                s = 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t = 0.0;
                s = clamp(-c / a, 0.0, 1.0)
            elif t > 1.0:
                t = 1.0;
                s = clamp((b - c) / a, 0.0, 1.0)

    cp = (p1[0] + s * d1x, p1[1] + s * d1y)
    cq = (q1[0] + t * d2x, q1[1] + t * d2y)
    return cp, cq


def handle_capsule_collisions(racers: list, dt: float) -> None:
    n = len(racers)
    for _ in range(_COLL_ITERS):
        for i in range(n):
            for j in range(i + 1, n):
                a, b = racers[i], racers[j]

                if getattr(a, "_no_collide_t", 0.0) > 0.0 or getattr(b, "_no_collide_t", 0.0) > 0.0:
                    continue

                if (b.x - a.x) ** 2 + (b.y - a.y) ** 2 > 220 * 220:
                    continue

                ra = a.car_w * 0.5 * 0.92
                rb = b.car_w * 0.5 * 0.92

                a_hlen = max(a.car_h * 0.5 - ra, 4.0)
                b_hlen = max(b.car_h * 0.5 - rb, 4.0)

                a_fx, a_fy = fwd_vec(a.angle)
                b_fx, b_fy = fwd_vec(b.angle)

                a_p1 = (a.x - a_fx * a_hlen, a.y - a_fy * a_hlen)
                a_p2 = (a.x + a_fx * a_hlen, a.y + a_fy * a_hlen)
                b_p1 = (b.x - b_fx * b_hlen, b.y - b_fy * b_hlen)
                b_p2 = (b.x + b_fx * b_hlen, b.y + b_fy * b_hlen)

                cp, cq = _closest_points_segments(a_p1, a_p2, b_p1, b_p2)

                sa = ((cp[0] - a.x) * a_fx + (cp[1] - a.y) * a_fy) / max(a_hlen, 1.0)
                sb = ((cq[0] - b.x) * b_fx + (cq[1] - b.y) * b_fy) / max(b_hlen, 1.0)
                sa = clamp(sa, -1.0, 1.0);
                sb = clamp(sb, -1.0, 1.0)

                _TAPER = 0.35
                sum_r_det = ra + rb
                ra_t = ra * (1.0 - _TAPER * sa * sa)
                rb_t = rb * (1.0 - _TAPER * sb * sb)
                sum_r_push = ra_t + rb_t

                dx = cp[0] - cq[0]
                dy = cp[1] - cq[1]
                d = math.hypot(dx, dy)

                if d >= sum_r_det or d < 0.01:
                    continue

                inv_d = 1.0 / d
                cnx = dx * inv_d
                cny = dy * inv_d

                depth = sum_r_push - d
                lat_a = a_fx * cny - a_fy * cnx
                lat_b = b_fx * cny - b_fy * cnx

                push = (depth * 0.52 + 0.8) if depth > 0.0 else 0.0

                rot_frac_a = abs(sa) * 0.65
                rot_frac_b = abs(sb) * 0.65

                trans_push_a = push * (1.0 - rot_frac_a)
                trans_push_b = push * (1.0 - rot_frac_b)

                a.x += cnx * trans_push_a
                a.y += cny * trans_push_a
                b.x -= cnx * trans_push_b
                b.y -= cny * trans_push_b

                if _ > 0:
                    continue

                a_rad = math.radians(getattr(a, '_move_dir', a.angle))
                b_rad = math.radians(getattr(b, '_move_dir', b.angle))

                v_ax = a.velocity * math.cos(a_rad)
                v_ay = a.velocity * math.sin(a_rad)
                v_bx = b.velocity * math.cos(b_rad)
                v_by = b.velocity * math.sin(b_rad)

                rel_vx = v_ax - v_bx
                rel_vy = v_ay - v_by
                v_normal = rel_vx * cnx + rel_vy * cny

                if v_normal < 0:
                    _CAPS_FRONTAL_THRESH = 0.40
                    approach_cos = abs(math.cos(a_rad) * cnx + math.sin(a_rad) * cny)

                    if approach_cos > _CAPS_FRONTAL_THRESH:
                        imp = -(1.0 + _COLL_E) * v_normal * 0.5
                        imp = min(imp, _MAX_IMPULSE)

                        v_ax += cnx * imp * 0.88
                        v_ay += cny * imp * 0.88
                        v_bx -= cnx * imp * 0.70
                        v_by -= cny * imp * 0.70

                        cross_a = a_fx * cny - a_fy * cnx
                        cross_b = b_fx * cny - b_fy * cnx

                        wall_damp_a = 0.30 if getattr(a, '_wall_contact_t', 0) > 0 else 1.0
                        wall_damp_b = 0.30 if getattr(b, '_wall_contact_t', 0) > 0 else 1.0

                        da = cross_a * imp * _COLL_ANG * wall_damp_a
                        db = cross_b * imp * _COLL_ANG * wall_damp_b

                        MAX_SPIN = 2.5
                        a.angle -= clamp(da, -MAX_SPIN, MAX_SPIN)
                        b.angle += clamp(db, -MAX_SPIN, MAX_SPIN)

                        a.velocity = math.hypot(v_ax, v_ay)
                        b.velocity = math.hypot(v_bx, v_by)
                        if a.velocity > 0.1:
                            a._move_dir = math.degrees(math.atan2(v_ay, v_ax))
                        if b.velocity > 0.1:
                            b._move_dir = math.degrees(math.atan2(v_by, v_bx))

                    else:
                        fric = min(0.08, max(0.0, depth) * 0.005)
                        a.velocity *= (1.0 - fric)
                        b.velocity *= (1.0 - fric)

                        rel_speed = math.hypot(rel_vx, rel_vy)
                        if rel_speed > 3.0:
                            g = min(rel_speed * 0.18, 8.0)
                            v_ax += cnx * g * 0.40
                            v_ay += cny * g * 0.40
                            v_bx -= cnx * g * 0.32
                            v_by -= cny * g * 0.32

                            a.velocity = math.hypot(v_ax, v_ay)
                            b.velocity = math.hypot(v_bx, v_by)
                            if a.velocity > 0.1:
                                a._move_dir = math.degrees(math.atan2(v_ay, v_ax))
                            if b.velocity > 0.1:
                                b._move_dir = math.degrees(math.atan2(v_by, v_bx))

                a.velocity = clamp(a.velocity, -a.max_speed * 0.35, a.max_speed * 1.05)
                b.velocity = clamp(b.velocity, -b.max_speed * 0.35, b.max_speed * 1.05)
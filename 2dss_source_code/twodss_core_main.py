"""
=====================================================================
TWODSS_CORE_MAIN.PY  —  Vòng lặp chính của 2D Sideway Showdown
=====================================================================
MỤC TIÊU:
    Điều phối toàn bộ luồng chạy của game: khởi tạo pygame, load
    resource, quản lý state machine, và gọi đúng module theo từng
    state trong main loop. File này là "nhạc trưởng".
=====================================================================
"""

import pygame
import sys
import os
import random
import time
import importlib
import importlib.util
import subprocess

# =====================================================================
# KÍCH HOẠT PYGAME NGAY LẬP TỨC (BẮT BUỘC ĐỂ TRÁNH LỖI SYSFONT KHI LOAD MODULE)
# =====================================================================
pygame.init()
pygame.font.init()

# =====================================================================
# 1. ĐƯỜNG DẪN GỐC
# =====================================================================
_THIS_DIR = os.path.dirname(__file__)
CURRENT_DIR = _THIS_DIR
BASE_DIR = os.path.dirname(CURRENT_DIR)


def get_asset(*paths):
    """Tạo đường dẫn tuyệt đối đến file trong assets/."""
    return os.path.join(BASE_DIR, "assets", *paths)


# =====================================================================
# 2. IMPORT CÁC MODULE MÀN HÌNH
# =====================================================================
def _load_module(alias, filename):
    """Helper load module từ file cùng thư mục theo tên file."""
    spec = importlib.util.spec_from_file_location(alias, os.path.join(_THIS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod_showroom = _load_module("twodss_showroom", "twodss_showroom.py")
_mod_mapselect = _load_module("twodss_mapselect", "twodss_mapselect.py")
_mod_loading = _load_module("twodss_loading", "twodss_loading.py")
_mod_leaderboard = _load_module("twodss_leaderboard", "twodss_leaderboard.py")

# ── Import 5 file track-*.py để lấy class RaceScreen của từng map ──
_mod_track_greenwood = _load_module("track_greenwood", "track-greenwood-circuit.py")
_mod_track_sportpit = _load_module("track_sportpit", "track-sportpit-circuit.py")
_mod_track_sandy = _load_module("track_sandy", "track-sandy-circuit.py")
_mod_track_velodrama = _load_module("track_velodrama", "track-velodrama-circuit.py")
_mod_track_dustfactory = _load_module("track_dustfactory", "track-dustfactory-circuit.py")

ShowroomScreen = _mod_showroom.ShowroomScreen
MapSelectScreen = _mod_mapselect.MapSelectScreen
LoadingScreen = _mod_loading.LoadingScreen
# CHỖ NÀY ĐÃ SỬA KHỚP VỚI CLASS CỦA ANH:
RaceLeaderboard = _mod_leaderboard.RaceLeaderboard

# Khởi tạo object bảng xếp hạng ngay
leaderboard = RaceLeaderboard(BASE_DIR)

# ── Bảng map_id -> class RaceScreen tương ứng ──
TRACK_CLASS_MAP = {
    "greenwood_circuit": _mod_track_greenwood.RaceScreen,
    "sportpit_track": _mod_track_sportpit.RaceScreen,
    "sandy_circuit": _mod_track_sandy.RaceScreen,
    "velodrama_track": _mod_track_velodrama.RaceScreen,
    "dustfactory_track": _mod_track_dustfactory.RaceScreen,
}

# =====================================================================
# 3. KHỞI TẠO CỬA SỔ
# =====================================================================
SCREEN_W, SCREEN_H = 1920, 1080

try:
    screen = pygame.display.set_mode(
        (SCREEN_W, SCREEN_H),
        pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
    )
except Exception as e:
    print(f"[DISPLAY ERROR] Fullscreen failed: {e}")
    print("[DISPLAY] Falling back to windowed mode...")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.DOUBLEBUF)

pygame.display.set_caption("2D Sideway Showdown")
clock = pygame.time.Clock()
FPS = 90

# =====================================================================
# 4. LOAD FONTS
# =====================================================================
font_path = get_asset("fonts", "SVN-New Athletic M54.ttf")
try:
    font_large = pygame.font.Font(font_path, 80)
    font_medium = pygame.font.Font(font_path, 45)
    font_small = pygame.font.Font(font_path, 25)
except:
    font_large = pygame.font.SysFont("impact", 80)
    font_medium = pygame.font.SysFont("impact", 45)
    font_small = pygame.font.SysFont("impact", 25)

# =====================================================================
# 5. LOAD IMAGES & AUDIO
# =====================================================================
try:
    img_intro_j4n3 = pygame.image.load(get_asset("background_game", "2dss_intro.PNG")).convert()
    img_intro_brands = pygame.image.load(get_asset("background_game", "2dss_introbrand.PNG")).convert()
    img_bg_standby = pygame.image.load(get_asset("background_game", "2dss_standby_bg.PNG")).convert()
    img_logo = pygame.image.load(get_asset("logo", "2dsidewayshowdown.png")).convert_alpha()
    img_bg_showroom = pygame.image.load(get_asset("background_game", "showroom-car-select.png")).convert()

    img_intro_j4n3 = pygame.transform.scale(img_intro_j4n3, (SCREEN_W, SCREEN_H))
    img_intro_brands = pygame.transform.scale(img_intro_brands, (SCREEN_W, SCREEN_H))
    img_bg_standby = pygame.transform.scale(img_bg_standby, (SCREEN_W, SCREEN_H))
    img_bg_showroom = pygame.transform.scale(img_bg_showroom, (SCREEN_W, SCREEN_H))

    LOGO_MAX_W = 1200
    orig_w, orig_h = img_logo.get_size()
    logo_h = int(orig_h * (LOGO_MAX_W / orig_w))
    img_logo = pygame.transform.smoothscale(img_logo, (LOGO_MAX_W, logo_h))
    logo_rect = img_logo.get_rect(center=(SCREEN_W // 2, 160))
except Exception as e:
    print(f"[CRITICAL IMAGE ERROR] {e}")
    pygame.quit()
    sys.exit()

pygame.mixer.init()
BGM_VOLUME = 0.6
music_on = True
sound_on = True
current_bgm_track = None


def play_state_bgm(state):
    global current_bgm_track
    if not music_on: return
    BGM_DICT = {
        STATE_MENU: "2dss-introbgm-hemispheres.mp3",
        STATE_SHOWROOM: "2dss_car-showroom-bgm.mp3",
        STATE_MAPSELECT: "2dss-track-selection-bgm.mp3"
    }
    filename = BGM_DICT.get(state)
    if filename:
        path = os.path.join(BASE_DIR, "assets", "audio", "bgm", filename)
        if path != current_bgm_track:
            if os.path.exists(path):
                pygame.mixer.music.stop()
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1)
                current_bgm_track = path


def apply_music_toggle():
    global current_bgm_track
    if music_on:
        current_bgm_track = None
        play_state_bgm(current_state)
    else:
        pygame.mixer.music.stop()
        current_bgm_track = None


# =====================================================================
# 6. LOADING PHRASES & TRANSITION
# =====================================================================
loading_phrases = [
    "Start the engine system...",
    "Welcome back... How was your day?",
    "Warm up the tires on the asphalt...",
    "Load race data at night...",
    "Brace yourself for an adrenaline-fueled race..."
]
PHRASE_MARGIN_BOTTOM = 35

FADE_DURATION = 0.6
fade_state = "in"
fade_alpha = 255
fade_start_time = time.time()
next_state = None
fade_surface = pygame.Surface((SCREEN_W, SCREEN_H))
fade_surface.fill((0, 0, 0))


def request_fade_to(target_state):
    global fade_state, fade_alpha, fade_start_time, next_state
    fade_state = "out"
    fade_alpha = 0
    fade_start_time = time.time()
    next_state = target_state


def update_fade():
    global fade_state, fade_alpha, fade_start_time, current_state, state_start_time
    if fade_state == "none": return False
    t = min((time.time() - fade_start_time) / FADE_DURATION, 1.0)
    if fade_state == "out":
        fade_alpha = int(t * 255)
        if t >= 1.0:
            current_state = next_state
            state_start_time = time.time()
            fade_state = "in"
            fade_alpha = 255
            fade_start_time = time.time()
    elif fade_state == "in":
        fade_alpha = int((1.0 - t) * 255)
        if t >= 1.0:
            fade_alpha = 0
            fade_state = "none"
    fade_surface.set_alpha(fade_alpha)
    screen.blit(fade_surface, (0, 0))
    return True


# Nút Menu Helper
def draw_gradient_button(surface, rect, text, font, is_hover=False):
    btn = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for y in range(rect.height):
        pos = y / rect.height
        if pos < 0.7:
            color = (255, 140, 0)
        elif pos < 0.85:
            color = (229, 126, 0)
        else:
            color = (178, 98, 0)
        if is_hover: color = tuple(min(255, int(c * 1.2)) for c in color)
        pygame.draw.line(btn, color, (0, y), (rect.width, y))
    pygame.draw.rect(btn, (255, 255, 255), btn.get_rect(), width=4)
    sh = font.render(text, True, (80, 40, 0))
    tx = font.render(text, True, (255, 255, 255))
    tr = tx.get_rect(center=(rect.width // 2, rect.height // 2))
    btn.blit(sh, (tr.x + 2, tr.y + 3))
    btn.blit(tx, tr)
    surface.blit(btn, rect.topleft)


def draw_icon_button(surface, rect, label, font, is_hover=False, active=True):
    btn = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for y in range(rect.height):
        pos = y / rect.height
        if active:
            base = (255, 140, 0) if pos < 0.7 else (229, 126, 0) if pos < 0.85 else (178, 98, 0)
        else:
            base = (110, 110, 110) if pos < 0.7 else (80, 80, 80) if pos < 0.85 else (55, 55, 55)
        color = tuple(min(255, int(c * 1.2)) for c in base) if is_hover else base
        pygame.draw.line(btn, color, (0, y), (rect.width, y))
    pygame.draw.rect(btn, (255, 255, 255), btn.get_rect(), width=4)
    ic = font.render(label, True, (255, 255, 255))
    btn.blit(ic, ic.get_rect(center=(rect.width // 2, rect.height // 2)))
    surface.blit(btn, rect.topleft)


btn_w, btn_h = 450, 100
center_x = SCREEN_W // 2
play_rect = pygame.Rect(center_x - btn_w // 2, 600, btn_w, btn_h)
quit_rect = pygame.Rect(center_x - btn_w // 2, 720, btn_w, btn_h)
small_w = (btn_w - 10) // 2
small_h = 80
sound_rect = pygame.Rect(center_x - btn_w // 2, 850, small_w, small_h)
music_rect = pygame.Rect(center_x - btn_w // 2 + small_w + 10, 850, small_w, small_h)

# =====================================================================
# 7. STATE MACHINE & MAIN LOOP
# =====================================================================
STATE_INTRO_J4N3 = 0
STATE_INTRO_BRANDS = 1
STATE_LOADING = 2
STATE_MENU = 3
STATE_SHOWROOM = 4
STATE_MAPSELECT = 5
STATE_RACE = 6
STATE_LOADING2 = 7
STATE_LEADERBOARD = 8

current_state = STATE_INTRO_J4N3
state_start_time = time.time()

_fonts = {"large": font_large, "medium": font_medium, "small": font_small}

showroom = ShowroomScreen(base_dir=BASE_DIR, fonts=_fonts, bg_image=img_bg_showroom)
mapselect = MapSelectScreen(base_dir=BASE_DIR, fonts=_fonts, bg_image=img_bg_showroom)
loading2 = LoadingScreen(BASE_DIR)

pending_race_class = None
pending_car_id = None
race_screen = None
current_phrase = random.choice(loading_phrases)
last_phrase_time = time.time()

running = True
while running:
    dt = clock.tick(FPS)
    now = time.time()
    elapsed = now - state_start_time

    # ── EVENT LOOP ──
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and current_state != STATE_RACE:
            running = False

        if current_state == STATE_SHOWROOM:
            result = showroom.handle_event(event)
            if result == "race":
                current_state = STATE_MAPSELECT
                state_start_time = time.time()
                play_state_bgm(STATE_MAPSELECT)
            elif result == "menu":
                current_state = STATE_MENU
                state_start_time = time.time()
                play_state_bgm(STATE_MENU)

        elif current_state == STATE_MAPSELECT:
            result = mapselect.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                current_state = STATE_MENU
                state_start_time = time.time()
                play_state_bgm(STATE_MENU)
            if result == "race":
                track_file_key = mapselect.selected_map_id
                RaceClass = TRACK_CLASS_MAP.get(track_file_key)
                if RaceClass:
                    pending_race_class = RaceClass

                    # Lấy xe từ showroom
                    car_id_found = "mazda_axela_2012"
                    if hasattr(showroom, 'selected_car_id'):
                        car_id_found = showroom.selected_car_id
                    elif hasattr(showroom, 'selected_car_name'):
                        try:
                            from twodss_car_data import CAR_LIST

                            for car in CAR_LIST:
                                if car.get("name") == showroom.selected_car_name:
                                    car_id_found = car.get("id")
                                    break
                        except:
                            car_id_found = showroom.selected_car_name

                    pending_car_id = car_id_found
                    loading2.reset()
                    current_state = STATE_LOADING2
                    state_start_time = time.time()
                else:
                    print(f"[RACE ERROR] Không tìm thấy class cho map: {track_file_key}")
            elif result == "garage":
                current_state = STATE_SHOWROOM
                state_start_time = time.time()
                play_state_bgm(STATE_SHOWROOM)

        elif current_state == STATE_RACE:
            if race_screen is not None:
                if hasattr(race_screen, 'handle_event'):
                    race_screen.handle_event(event)
                elif hasattr(race_screen, 'pause') and hasattr(race_screen.pause, 'handle_event'):
                    race_screen.pause.handle_event(event)

        elif current_state == STATE_LEADERBOARD:
            if leaderboard is not None:
                leaderboard.handle_event(event)
                if leaderboard.result == "back":
                    leaderboard.result = None
                    current_state = STATE_SHOWROOM
                    state_start_time = now
                    play_state_bgm(STATE_SHOWROOM)

        elif current_state == STATE_MENU and fade_state == "none":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mp = pygame.mouse.get_pos()
                if play_rect.collidepoint(mp):
                    current_state = STATE_SHOWROOM
                    state_start_time = time.time()
                    play_state_bgm(STATE_SHOWROOM)
                if quit_rect.collidepoint(mp):
                    running = False
                if sound_rect.collidepoint(mp):
                    sound_on = not sound_on
                if music_rect.collidepoint(mp):
                    music_on = not music_on
                    apply_music_toggle()

    mouse_pos = pygame.mouse.get_pos()

    # ── UPDATE & DRAW ──
    if current_state == STATE_INTRO_J4N3:
        screen.blit(img_intro_j4n3, (0, 0))
        if elapsed > 3.0 and fade_state == "none": request_fade_to(STATE_INTRO_BRANDS)

    elif current_state == STATE_INTRO_BRANDS:
        screen.blit(img_intro_brands, (0, 0))
        if elapsed > 3.0 and fade_state == "none": request_fade_to(STATE_LOADING)

    elif current_state == STATE_LOADING:
        screen.blit(img_bg_standby, (0, 0))
        dash = "────"
        decorated = f"{dash}  {current_phrase}  {dash}"
        tmp_surf = font_medium.render(decorated, True, (255, 255, 255))
        px = (SCREEN_W - tmp_surf.get_width()) // 2
        py = SCREEN_H - tmp_surf.get_height() - PHRASE_MARGIN_BOTTOM
        sh = font_medium.render(decorated, True, (0, 0, 0))
        sh.set_alpha(140)
        screen.blit(sh, (px + 3, py + 4))
        screen.blit(tmp_surf, (px, py))

        if now - last_phrase_time > 2.0:
            current_phrase = random.choice(loading_phrases)
            last_phrase_time = now
        if elapsed > 5.0 and fade_state == "none":
            current_state = STATE_MENU
            state_start_time = now
            play_state_bgm(STATE_MENU)

    elif current_state == STATE_MENU:
        play_state_bgm(STATE_MENU)
        screen.blit(img_bg_standby, (0, 0))
        screen.blit(img_logo, logo_rect)
        draw_gradient_button(screen, play_rect, "PLAY", font_medium, play_rect.collidepoint(mouse_pos))
        draw_gradient_button(screen, quit_rect, "QUIT", font_medium, quit_rect.collidepoint(mouse_pos))
        draw_icon_button(screen, sound_rect, "SFX ON" if sound_on else "SFX OFF", font_small,
                         sound_rect.collidepoint(mouse_pos), sound_on)
        draw_icon_button(screen, music_rect, "BGM ON" if music_on else "BGM OFF", font_small,
                         music_rect.collidepoint(mouse_pos), music_on)

    elif current_state == STATE_SHOWROOM:
        showroom.update(dt)
        showroom.draw(screen)

    elif current_state == STATE_MAPSELECT:
        mapselect.update(dt)
        mapselect.draw(screen)

    elif current_state == STATE_LOADING2:
        loading2.update(dt)
        loading2.draw(screen)
        if loading2.is_done:
            race_screen = pending_race_class(screen, BASE_DIR, car_id=pending_car_id)
            current_state = STATE_RACE
            state_start_time = now

    elif current_state == STATE_RACE:
        if race_screen is not None:
            race_screen.update(dt / 1000.0)
            race_screen.draw(screen)

            # Lấy dữ liệu đẩy qua bảng xếp hạng khi đua xong
            player_done = hasattr(race_screen.player, 'finished') and race_screen.player.finished
            if race_screen.result == "quit_showroom" or player_done:
                if player_done and race_screen.result != "quit_showroom":
                    final_results = []
                    if hasattr(race_screen, 'all_racers'):
                        sorted_racers = sorted(race_screen.all_racers, key=lambda r: r.race_progress(), reverse=True)
                    else:
                        sorted_racers = [race_screen.player]

                    from twodss_car_data import CAR_LIST


                    def fmt_t(secs):
                        m, s = int(secs // 60), int(secs % 60)
                        ms = int((secs - int(secs)) * 100)
                        return f"{m:02d}:{s:02d}.{ms:02d}"


                    start_time = getattr(race_screen, 'go_time', getattr(race_screen, '_go_time', now))

                    for r in sorted_racers:
                        real_car_name = r.car_id
                        for c in CAR_LIST:
                            if c["id"] == r.car_id:
                                real_car_name = c["name"]
                                break
                        if r.finished:
                            elapsed_time = getattr(r, '_finish_time', now) - start_time
                            time_str = fmt_t(max(0, elapsed_time))
                        else:
                            time_str = "DNF"

                        final_results.append({
                            "name": "YOU" if r.is_player else getattr(r, 'driver_name', "AI Bot"),
                            "car": real_car_name,
                            "time": time_str,
                            "is_player": r.is_player
                        })

                    leaderboard.set_data(final_results)
                    race_screen = None
                    current_state = STATE_LEADERBOARD
                    state_start_time = now
                else:
                    race_screen = None
                    current_state = STATE_SHOWROOM
                    state_start_time = now
                    play_state_bgm(STATE_SHOWROOM)

    elif current_state == STATE_LEADERBOARD:
        if leaderboard is not None:
            leaderboard.draw(screen)
            # handle_event đã xử lý tín hiệu 'back' ở phía trên

    update_fade()
    pygame.display.flip()

pygame.quit()
sys.exit()
"""
=====================================================================
TWODSS_CORE_MAIN.PY  —  Vòng lặp chính của 2D Sideway Showdown
=====================================================================

MỤC TIÊU:
    Điều phối toàn bộ luồng chạy của game: khởi tạo pygame, load
    resource, quản lý state machine, và gọi đúng module theo từng
    state trong main loop. File này là "nhạc trưởng" — chỉ điều
    phối, không chứa logic UI hay data game cụ thể.

TƯ DUY THIẾT KẾ:
    - State machine rõ ràng: mỗi STATE_xxx là 1 màn hình / giai đoạn
      riêng biệt. Thêm màn hình mới = thêm 1 state + 1 elif, không
      cần đụng vào phần còn lại của code.
    - Mỗi màn hình phức tạp (showroom, mapselect) được tách ra module
      riêng, core_main chỉ gọi 3 method: handle_event / update / draw.
    - Resource load 1 lần duy nhất khi khởi động, không load lại mỗi
      frame hay mỗi lần đổi state.

Ý ĐỊNH & SÁNG KIẾN:
    - Import module bằng importlib.util thay vì import thông thường
      vì tên file bắt đầu bằng chữ số là không hợp lệ trong Python —
      đây là workaround chuẩn cho dự án có naming convention đặc biệt.
    - bgm_started flag: nhạc chỉ play 1 lần khi vào menu, không bị
      restart mỗi khi quay lại STATE_MENU từ showroom hay mapselect.
    - Fade transition chỉ dùng cho intro screens (J4N3 → Brands →
      Loading), các màn hình gameplay chuyển thẳng để không mất thời
      gian người chơi.

STATE MACHINE:
    STATE_INTRO_J4N3   (0) → màn hình intro logo J4N3
    STATE_INTRO_BRANDS (1) → màn hình intro các thương hiệu
    STATE_LOADING      (2) → loading screen với loading phrases
    STATE_MENU         (3) → main menu (PLAY / QUIT / SFX / BGM)
    STATE_SHOWROOM     (4) → chọn xe
    STATE_MAPSELECT    (5) → chọn map đua  ← MỚI
    STATE_RACE         (6) → placeholder, sẽ phát triển sau
=====================================================================
"""

import pygame
import sys
import os
import random
import time
import importlib

# =====================================================================
# 1. IMPORT CÁC MODULE MÀN HÌNH
# =====================================================================
# Dùng importlib.util vì Python không cho import trực tiếp
# file có tên bắt đầu bằng chữ số (2dss_...).
# twodss_xxx là tên alias hợp lệ dùng trong project này.

_THIS_DIR = os.path.dirname(__file__)

def _load_module(alias, filename):
    """Helper load module từ file cùng thư mục theo tên file."""
    spec = importlib.util.spec_from_file_location(alias,
               os.path.join(_THIS_DIR, filename))
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_mod_showroom  = _load_module("twodss_showroom",  "twodss_showroom.py")
_mod_mapselect = _load_module("twodss_mapselect", "twodss_mapselect.py")

ShowroomScreen  = _mod_showroom.ShowroomScreen
MapSelectScreen = _mod_mapselect.MapSelectScreen

# =====================================================================
# 2. ĐƯỜNG DẪN GỐC
# =====================================================================
CURRENT_DIR = _THIS_DIR
BASE_DIR    = os.path.dirname(CURRENT_DIR)

def get_asset(*paths):
    """Tạo đường dẫn tuyệt đối đến file trong assets/."""
    return os.path.join(BASE_DIR, "assets", *paths)

# =====================================================================
# 3. KHỞI TẠO PYGAME & CỬA SỔ
# =====================================================================
pygame.init()
pygame.font.init()
pygame.mixer.init()

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
print(f"[INIT] Display OK: {screen.get_size()}")
sys.stdout.flush()

clock = pygame.time.Clock()
FPS   = 90

# =====================================================================
# 4. LOAD FONTS
# =====================================================================
font_path = get_asset("fonts", "SVN-New Athletic M54.ttf")
try:
    font_large  = pygame.font.Font(font_path, 80)
    font_medium = pygame.font.Font(font_path, 45)
    font_small  = pygame.font.Font(font_path, 25)
except Exception as e:
    print(f"[FONT WARNING] {e} — dùng fallback SysFont")
    font_large  = pygame.font.SysFont("impact", 80)
    font_medium = pygame.font.SysFont("impact", 45)
    font_small  = pygame.font.SysFont("impact", 25)

# =====================================================================
# 5. LOAD IMAGES
# =====================================================================
try:
    img_intro_j4n3   = pygame.image.load(get_asset("background_game", "2dss_intro.PNG")).convert()
    img_intro_brands = pygame.image.load(get_asset("background_game", "2dss_introbrand.PNG")).convert()
    img_bg_standby   = pygame.image.load(get_asset("background_game", "2dss_standby_bg.PNG")).convert()
    img_logo         = pygame.image.load(get_asset("logo", "2dsidewayshowdown.png")).convert_alpha()
    img_bg_showroom  = pygame.image.load(get_asset("background_game", "showroom-car-select.png")).convert()

    img_intro_j4n3   = pygame.transform.scale(img_intro_j4n3,   (SCREEN_W, SCREEN_H))
    img_intro_brands = pygame.transform.scale(img_intro_brands, (SCREEN_W, SCREEN_H))
    img_bg_standby   = pygame.transform.scale(img_bg_standby,   (SCREEN_W, SCREEN_H))
    img_bg_showroom  = pygame.transform.scale(img_bg_showroom,  (SCREEN_W, SCREEN_H))

    LOGO_MAX_W       = 1200
    orig_w, orig_h   = img_logo.get_size()
    logo_h           = int(orig_h * (LOGO_MAX_W / orig_w))
    img_logo         = pygame.transform.smoothscale(img_logo, (LOGO_MAX_W, logo_h))
    logo_rect        = img_logo.get_rect(center=(SCREEN_W // 2, 160))

except Exception as e:
    print(f"[CRITICAL IMAGE ERROR] {e}")
    pygame.quit()
    sys.exit()

# =====================================================================
# 6. AUDIO — BGM + SFX
# =====================================================================
# assets/audio/bgm/2dss-introbgm-hemispheres.mp3   ← nhạc nền menu
# assets/audio/sfx/                                 ← engine, click... (sau)

BGM_VOLUME  = 0.6
BGM_FADEIN  = 1500   # ms fade-in lúc phát lần đầu
BGM_FADEOUT = 600    # ms fade-out (dùng sau nếu cần)

bgm_loaded  = False
bgm_started = False  # chỉ play 1 lần, không restart mỗi lần vào menu

try:
    pygame.mixer.music.load(get_asset("audio", "bgm", "2dss-introbgm-hemispheres.mp3"))
    bgm_loaded = True
    pygame.mixer.music.set_volume(BGM_VOLUME)
except Exception as e:
    print(f"[AUDIO WARNING] BGM not found: {e}")

# =====================================================================
# 7. LOADING PHRASES
# =====================================================================
loading_phrases = [
    "Start the engine system...",
    "Welcome back... How was your day?",
    "Warm up the tires on the asphalt...",
    "Load race data at night...",
    "Brace yourself for an adrenaline-fueled race..."
]
PHRASE_MARGIN_BOTTOM = 35

# =====================================================================
# 8. FADE TRANSITION (chỉ dùng cho intro screens)
# =====================================================================
FADE_DURATION = 0.6

fade_state      = "in"
fade_alpha      = 255
fade_start_time = time.time()
next_state      = None
fade_surface    = pygame.Surface((SCREEN_W, SCREEN_H))
fade_surface.fill((0, 0, 0))

def request_fade_to(target_state):
    """Bắt đầu fade-out → chuyển state → fade-in."""
    global fade_state, fade_alpha, fade_start_time, next_state
    fade_state      = "out"
    fade_alpha      = 0
    fade_start_time = time.time()
    next_state      = target_state

def update_fade():
    """Cập nhật và vẽ overlay fade mỗi frame. Trả về True khi đang fade."""
    global fade_state, fade_alpha, fade_start_time, current_state, state_start_time
    if fade_state == "none":
        return False
    t = min((time.time() - fade_start_time) / FADE_DURATION, 1.0)
    if fade_state == "out":
        fade_alpha = int(t * 255)
        if t >= 1.0:
            current_state    = next_state
            state_start_time = time.time()
            fade_state       = "in"
            fade_alpha       = 255
            fade_start_time  = time.time()
    elif fade_state == "in":
        fade_alpha = int((1.0 - t) * 255)
        if t >= 1.0:
            fade_alpha = 0
            fade_state = "none"
    fade_surface.set_alpha(fade_alpha)
    screen.blit(fade_surface, (0, 0))
    return True

# =====================================================================
# 9. DRAW HELPERS — nút menu chính
# =====================================================================
def draw_gradient_button(surface, rect, text, font, is_hover=False):
    """Nút gradient cam/vàng cho PLAY / QUIT."""
    btn = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for y in range(rect.height):
        pos = y / rect.height
        if pos < 0.7:    color = (255, 140, 0)
        elif pos < 0.85: color = (229, 126, 0)
        else:            color = (178,  98, 0)
        if is_hover:
            color = tuple(min(255, int(c * 1.2)) for c in color)
        pygame.draw.line(btn, color, (0, y), (rect.width, y))
    pygame.draw.rect(btn, (255, 255, 255), btn.get_rect(), width=4)
    sh = font.render(text, True, (80, 40, 0))
    tx = font.render(text, True, (255, 255, 255))
    tr = tx.get_rect(center=(rect.width // 2, rect.height // 2))
    btn.blit(sh, (tr.x + 2, tr.y + 3))
    btn.blit(tx, tr)
    surface.blit(btn, rect.topleft)


def draw_icon_button(surface, rect, label, font, is_hover=False, active=True):
    """Nút gradient nhỏ cho SFX / BGM toggle."""
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

# =====================================================================
# 10. BUTTON LAYOUT — menu chính
# =====================================================================
btn_w, btn_h = 450, 100
center_x     = SCREEN_W // 2

play_rect  = pygame.Rect(center_x - btn_w // 2, 600, btn_w, btn_h)
quit_rect  = pygame.Rect(center_x - btn_w // 2, 720, btn_w, btn_h)

small_w    = (btn_w - 10) // 2
small_h    = 80
sound_rect = pygame.Rect(center_x - btn_w // 2,                850, small_w, small_h)
music_rect = pygame.Rect(center_x - btn_w // 2 + small_w + 10, 850, small_w, small_h)

# =====================================================================
# 11. AUDIO TOGGLE
# =====================================================================
sound_on = True
music_on = True

def apply_music_toggle():
    """Bật: unpause từ vị trí cũ | Tắt: pause giữ nguyên vị trí."""
    if not bgm_loaded:
        return
    if music_on:
        pygame.mixer.music.set_volume(BGM_VOLUME)
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()

# =====================================================================
# 12. STATE MACHINE
# =====================================================================
STATE_INTRO_J4N3   = 0
STATE_INTRO_BRANDS = 1
STATE_LOADING      = 2
STATE_MENU         = 3
STATE_SHOWROOM     = 4
STATE_MAPSELECT    = 5   # ← MỚI: màn hình chọn map
STATE_RACE         = 6   # ← placeholder, phát triển sau

current_state    = STATE_INTRO_J4N3
state_start_time = time.time()

# ── Khởi tạo các màn hình ────────────────────────────────────────────
_fonts = {"large": font_large, "medium": font_medium, "small": font_small}

showroom = ShowroomScreen(
    base_dir = BASE_DIR,
    fonts    = _fonts,
    bg_image = img_bg_showroom,
)

mapselect = MapSelectScreen(
    base_dir = BASE_DIR,
    fonts    = _fonts,
    bg_image = img_bg_showroom,   # dùng chung nền với showroom
)

# ── Loading phrase ────────────────────────────────────────────────────
current_phrase   = random.choice(loading_phrases)
last_phrase_time = time.time()

# =====================================================================
# 13. MAIN LOOP
# =====================================================================
running = True
while running:
    dt      = clock.tick(FPS)
    now     = time.time()
    elapsed = now - state_start_time

    # ── EVENT LOOP ────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

        # ── SHOWROOM ──────────────────────────────────────────────────
        if current_state == STATE_SHOWROOM:
            result = showroom.handle_event(event)
            if result == "race":
                # LET'S RACE → sang chọn map
                current_state    = STATE_MAPSELECT
                state_start_time = time.time()
            elif result == "menu":
                current_state    = STATE_MENU
                state_start_time = time.time()
            # Backspace dự phòng
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                current_state    = STATE_MENU
                state_start_time = time.time()

        # ── MAP SELECT ────────────────────────────────────────────────
        elif current_state == STATE_MAPSELECT:
            result = mapselect.handle_event(event)
            if result == "race":
                # TODO: truyền mapselect.selected_map_id vào game engine
                print(f"[RACE START] Map: {mapselect.selected_map_id} — {mapselect.selected_map_name}")
                # current_state = STATE_RACE
                # race_engine.load_map(mapselect.selected_map_id)
            elif result == "garage":
                current_state    = STATE_SHOWROOM
                state_start_time = time.time()

        # ── MENU ──────────────────────────────────────────────────────
        elif current_state == STATE_MENU and fade_state == "none":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mp = pygame.mouse.get_pos()
                if play_rect.collidepoint(mp):
                    current_state    = STATE_SHOWROOM
                    state_start_time = time.time()
                if quit_rect.collidepoint(mp):
                    running = False
                if sound_rect.collidepoint(mp):
                    sound_on = not sound_on
                if music_rect.collidepoint(mp):
                    music_on = not music_on
                    apply_music_toggle()

    mouse_pos = pygame.mouse.get_pos()

    # ── DRAW ──────────────────────────────────────────────────────────
    if current_state == STATE_INTRO_J4N3:
        screen.blit(img_intro_j4n3, (0, 0))
        if elapsed > 3.0 and fade_state == "none":
            request_fade_to(STATE_INTRO_BRANDS)

    elif current_state == STATE_INTRO_BRANDS:
        screen.blit(img_intro_brands, (0, 0))
        if elapsed > 3.0 and fade_state == "none":
            request_fade_to(STATE_LOADING)

    elif current_state == STATE_LOADING:
        screen.blit(img_bg_standby, (0, 0))

        dash      = "────"
        decorated = f"{dash}  {current_phrase}  {dash}"
        tmp_surf  = font_medium.render(decorated, True, (255, 255, 255))
        px = (SCREEN_W - tmp_surf.get_width())  // 2
        py = SCREEN_H - tmp_surf.get_height() - PHRASE_MARGIN_BOTTOM

        sh = font_medium.render(decorated, True, (0, 0, 0))
        sh.set_alpha(140)
        screen.blit(sh, (px + 3, py + 4))
        out = font_medium.render(decorated, True, (0, 0, 0))
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
            screen.blit(out, (px + dx, py + dy))
        screen.blit(tmp_surf, (px, py))

        if now - last_phrase_time > 2.0:
            current_phrase   = random.choice(loading_phrases)
            last_phrase_time = now
        if elapsed > 5.0 and fade_state == "none":
            current_state    = STATE_MENU
            state_start_time = now

    elif current_state == STATE_MENU:
        # Play BGM lần đầu khi vào menu
        if bgm_loaded and not bgm_started and music_on:
            pygame.mixer.music.play(loops=-1)
            bgm_started = True

        screen.blit(img_bg_standby, (0, 0))
        screen.blit(img_logo, logo_rect)
        draw_gradient_button(screen, play_rect, "PLAY", font_medium,
                             play_rect.collidepoint(mouse_pos))
        draw_gradient_button(screen, quit_rect, "QUIT", font_medium,
                             quit_rect.collidepoint(mouse_pos))
        draw_icon_button(screen, sound_rect,
                         "SFX ON" if sound_on else "SFX OFF",
                         font_small, sound_rect.collidepoint(mouse_pos), sound_on)
        draw_icon_button(screen, music_rect,
                         "BGM ON" if music_on else "BGM OFF",
                         font_small, music_rect.collidepoint(mouse_pos), music_on)

    elif current_state == STATE_SHOWROOM:
        showroom.update(dt)
        showroom.draw(screen)

    elif current_state == STATE_MAPSELECT:
        mapselect.update(dt)
        mapselect.draw(screen)

    elif current_state == STATE_RACE:
        # TODO: placeholder — vẽ màn hình đua khi game engine sẵn sàng
        screen.fill((0, 0, 0))
        t = font_large.render("RACE — COMING SOON", True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))

    # ── FADE OVERLAY (chỉ active khi đang trong intro) ────────────────
    update_fade()

    pygame.display.flip()

# =====================================================================
pygame.quit()
sys.exit()
"""
2D Sideway Showdown - Top-Down Racing Game
version: rd260415_0823
==========================================
Controls:
  W / S       - Accelerate / Brake+Reverse
  A / D       - Turn left / Turn right
  SPACE       - Drift mode (hold while turning for drift, reduces speed)
  ESC         - Quit

Assets (auto-detected or fallback to colored shapes):
  Track  : assets/track/track_demo.png        (relative to script)
  Car    : assets/car_model_topdown/
"""

import pygame
import math
import sys
import os

# ─── Constants ────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1400, 1000
FPS               = 70
CAR_W, CAR_H      = 100, 216      # display size of the car sprite

# Physics
MAX_SPEED         = 7.6
ACCELERATION      = 0.24
BRAKE_FORCE       = 0.26
FRICTION          = 0.96          # normal rolling friction
DRIFT_FRICTION    = 0.985         # less grip while drifting
TURN_SPEED        = 3.2           # degrees per frame
DRIFT_TURN_BONUS  = 1.6           # extra turn angle while drifting
DRIFT_SPEED_COST  = 0.025         # speed lost per frame while drifting
MIN_SPEED_TO_TURN = 0.3

# Colours (fallback rendering)
C_BG     = (45,  45,  45)
C_TRACK  = (80,  80,  80)
C_GRASS  = (45, 110,  55)
C_CAR    = (220,  60,  60)
C_WHEEL  = ( 30,  30,  30)
C_DRIFT  = (255, 220,  50, 160)   # drift trail colour (RGBA)

# ─── Asset Paths (cross-platform, international filenames) ──────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))

def find_asset(*rel_parts):
    """Try to locate an asset relative to the script; return None if missing."""
    path = os.path.join(SCRIPT_DIR, *rel_parts)
    return path if os.path.isfile(path) else None

TRACK_PATH = find_asset("assets", "track", "track_demo.png")
CAR_PATH   = find_asset("assets", "car_model_topdown", "toyota_altezza_gita.png")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def load_image(path, size=None):
    """Load image with alpha; scale if size given. Returns None on failure."""
    if path is None:
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        return None


def make_car_surface(w, h):
    """Draw a simple top-down car shape as a fallback Surface."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Body
    pygame.draw.rect(surf, C_CAR, (4, 6, w-8, h-12), border_radius=6)
    # Windshield
    pygame.draw.rect(surf, (180, 220, 255, 180), (8, 10, w-16, 14), border_radius=3)
    # Rear window
    pygame.draw.rect(surf, (180, 220, 255, 120), (8, h-22, w-16, 10), border_radius=3)
    # Wheels (4 corners)
    for wx, wy in [(1, 8), (w-9, 8), (1, h-20), (w-9, h-20)]:
        pygame.draw.rect(surf, C_WHEEL, (wx, wy, 8, 14), border_radius=2)
    return surf


def make_track_surface(w, h):
    """Draw a simple oval track as a fallback Surface."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill(C_GRASS)

    cx, cy   = w // 2, h // 2
    outer_rx, outer_ry = int(w * 0.45), int(h * 0.42)
    inner_rx, inner_ry = int(w * 0.28), int(h * 0.26)

    # Draw track (outer ellipse minus inner ellipse)
    # Outer ring
    pygame.draw.ellipse(surf, C_TRACK,
                        (cx - outer_rx, cy - outer_ry,
                         outer_rx*2, outer_ry*2))
    # Inner grass
    pygame.draw.ellipse(surf, C_GRASS,
                        (cx - inner_rx, cy - inner_ry,
                         inner_rx*2, inner_ry*2))

    # Start/finish line
    pygame.draw.rect(surf, (255, 255, 255), (cx - 4, cy - outer_ry - 2, 8, outer_ry - inner_ry + 4))
    return surf


# ─── Drift Trail ──────────────────────────────────────────────────────────────
class DriftTrail:
    def __init__(self):
        self.marks = []  # list of (world_x, world_y, alpha)

    def add(self, x, y):
        self.marks.append([x, y, 220])

    def update(self):
        # Đã sửa điều kiện thành a > 3 để alpha không bao giờ bị âm
        self.marks = [[x, y, a - 3] for x, y, a in self.marks if a > 3]

    def draw(self, surface, cam_x, cam_y, zoom_factor=1.0):
        for x, y, a in self.marks:
            # Tính toán khoảng cách tới camera nhân với hệ số zoom
            dx = (x - cam_x) * zoom_factor
            dy = (y - cam_y) * zoom_factor

            # Vị trí thực tế trên màn hình sau khi zoom
            sx = int(SCREEN_W // 2 + dx)
            sy = int(SCREEN_H // 2 + dy)

            # Thu phóng luôn cả độ to của vệt bánh xe (gốc là 6x6 pixel)
            mark_size = max(1, int(6 * zoom_factor))
            mark = pygame.Surface((mark_size, mark_size), pygame.SRCALPHA)

            # Khóa an toàn giá trị màu
            safe_alpha = max(0, min(255, int(a)))
            mark.fill((200, 180, 50, safe_alpha))

            # Canh giữa vệt bánh xe
            surface.blit(mark, (sx - mark_size // 2, sy - mark_size // 2))

# ─── Car ──────────────────────────────────────────────────────────────────────
class Car:
    def __init__(self, x, y, original_surf):
        self.x        = float(x)
        self.y        = float(y)
        self.angle    = 0.0      # degrees; 0 = pointing UP in world space
        self.speed    = 0.0
        self.drifting = False
        self.drift_angle = 0.0  # visual slip angle
        self._orig    = original_surf
        self.trail    = DriftTrail()

        # Collision half-sizes (smaller than sprite for fair gameplay)
        self.hw = CAR_W // 2 - 4
        self.hh = CAR_H // 2 - 8

    def change_image(self, new_surf):
        if new_surf is not None:
            self._orig = new_surf

    # ── Physics update ────────────────────────────────────────────────────
    def update(self, keys, track_mask, track_rect):
        was_drifting = self.drifting
        self.drifting = keys[pygame.K_SPACE]

        # --- Acceleration / Brake ---
        if keys[pygame.K_w]:
            self.speed += ACCELERATION
        if keys[pygame.K_s]:
            self.speed -= BRAKE_FORCE

        # Clamp speed
        self.speed = max(-MAX_SPEED * 0.5, min(MAX_SPEED, self.speed))

        # --- Turning (only when moving) ---
        if abs(self.speed) > MIN_SPEED_TO_TURN:
            turn = 0.0
            if keys[pygame.K_a]:
                turn = -TURN_SPEED
            if keys[pygame.K_d]:
                turn = TURN_SPEED

            # Reverse turning direction when going backwards
            if self.speed < 0:
                turn = -turn

            # Drift bonus turning
            if self.drifting and turn != 0:
                turn *= DRIFT_TURN_BONUS
                self.drift_angle = math.copysign(min(abs(self.drift_angle) + 1.2, 22), turn)
                # Vẫn giữ nguyên mức trừ tốc độ cost của em
                self.speed = max(abs(self.speed) - DRIFT_SPEED_COST, 0.0) * math.copysign(1, self.speed)
            else:
                self.drift_angle *= 0.88  # smoothly return drift slip

            self.angle += turn * (abs(self.speed) / MAX_SPEED)

        # --- SỬA LỖI DRIFT NITRO Ở ĐÂY ---
        if self.drifting:
            # Tôn trọng thông số, anh kết hợp FRICTION gốc và ép xe chậm đi 6%
            # để đảm bảo Drift LUÔN LUÔN bị mất tốc độ so với chạy thẳng
            friction = FRICTION * 0.94
        else:
            friction = FRICTION

        self.speed *= friction

        # --- Movement in heading direction ---
        rad = math.radians(self.angle)
        dx = math.sin(rad) * self.speed
        dy = -math.cos(rad) * self.speed

        new_x = self.x + dx
        new_y = self.y + dy

        # --- Boundary / collision with track --------------------------------
        if track_mask and track_rect:
            # Map world coords to mask coords
            mx = int(new_x - track_rect.x)
            my = int(new_y - track_rect.y)
            on_track = False
            if 0 <= mx < track_mask.get_size()[0] and 0 <= my < track_mask.get_size()[1]:
                on_track = bool(track_mask.get_at((mx, my)))

            if on_track:
                self.x = new_x
                self.y = new_y
            else:
                # Bounce / slow on grass
                self.speed *= 0.45
                # Try sliding along X only
                mx2 = int(new_x - track_rect.x)
                my2 = int(self.y - track_rect.y)
                if (0 <= mx2 < track_mask.get_size()[0] and
                    0 <= my2 < track_mask.get_size()[1] and
                    track_mask.get_at((mx2, my2))):
                        self.x = new_x
                else:
                    # Try sliding along Y only
                    mx3 = int(self.x - track_rect.x)
                    my3 = int(new_y - track_rect.y)
                    if (0 <= mx3 < track_mask.get_size()[0] and
                        0 <= my3 < track_mask.get_size()[1] and
                        track_mask.get_at((mx3, my3))):
                        self.y = new_y
        else:
            # No mask – simple world boundary clamp
            self.x = new_x
            self.y = new_y

        # --- Drift trail ---
        if self.drifting and abs(self.speed) > 1.5:
            self.trail.add(self.x, self.y)
        self.trail.update()

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self, surface, cam_x, cam_y, zoom_factor=1.0):
        # Cập nhật vẽ trail với zoom (nếu em vẫn dùng trail)
        self.trail.draw(surface, cam_x, cam_y, zoom_factor)

        # Rotate sprite
        total_angle = self.angle + self.drift_angle
        rotated = pygame.transform.rotate(self._orig, -total_angle)

        # Scale xe theo zoom
        if zoom_factor != 1.0:
            new_w = int(rotated.get_width() * zoom_factor)
            new_h = int(rotated.get_height() * zoom_factor)
            rotated = pygame.transform.smoothscale(rotated, (new_w, new_h))

        rect = rotated.get_rect()

        # Tính toán vị trí hiển thị trên màn hình
        # Lưu ý: Khi zoom, khoảng cách từ camera đến xe cũng bị scale
        dx = (self.x - cam_x) * zoom_factor
        dy = (self.y - cam_y) * zoom_factor

        sx = int(SCREEN_W // 2 + dx) - rect.width // 2
        sy = int(SCREEN_H // 2 + dy) - rect.height // 2
        surface.blit(rotated, (sx, sy))


# ─── Camera ───────────────────────────────────────────────────────────────────
class Camera:
    """Smooth follow camera that also rotates to match car heading and supports zoom."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0
        self.smooth = 0.12  # lerp factor

        # --- HỆ THỐNG ZOOM ---
        self.zoom_level = 0  # Cấp độ zoom mặc định khi khởi tạo (-5 đến 5)
        self.zoom_step = 0.15  # Mỗi cấp độ thay đổi 15%

    @property
    def zoom_factor(self):
        # Tính toán hệ số scale thực tế.
        # Level 0 = 1.0 (100%)
        # Level 1 = 1.15 (115%)
        # Level -1 = 0.85 (85%)
        return 1.0 + (self.zoom_level * self.zoom_step)

    def update(self, car):
        # Smoothly follow car position
        self.x += (car.x - self.x) * self.smooth
        self.y += (car.y - self.y) * self.smooth
        # Smoothly match car angle (for potential rotated-view extension)
        delta = (car.angle - self.angle + 180) % 360 - 180
        self.angle += delta * 0.1

    def handle_zoom(self, event):
        # Xử lý sự kiện cuộn chuột + Shift
        if event.type == pygame.MOUSEWHEEL:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                if event.y > 0:  # Cuộn lên -> Phóng to
                    self.zoom_level = min(self.zoom_level + 1, 5)
                elif event.y < 0:  # Cuộn xuống -> Thu nhỏ
                    self.zoom_level = max(self.zoom_level - 1, -5)

# ─── HUD ──────────────────────────────────────────────────────────────────────
def draw_hud(surface, car, font):
    spd_kmh = int(abs(car.speed) / MAX_SPEED * 360)
    gear_txt = "DRIFT" if car.drifting else ("REV" if car.speed < 0 else "FWD")
    color    = (255, 200, 50) if car.drifting else (200, 255, 200)

    lines = [
        f"Speed : {spd_kmh:3d} km/h",
        f"Mode  : {gear_txt}",
        "W/S - Accel/Brake",
        "A/D - Turn",
        "SPC - Drift",
    ]
    for i, line in enumerate(lines):
        c = color if i < 2 else (160, 160, 160)
        surf = font.render(line, True, c)
        surface.blit(surf, (14, 14 + i * 22))

    # Drift indicator bar
    if car.drifting:
        drift_pct = min(abs(car.drift_angle) / 22.0, 1.0)
        bar_w = int(180 * drift_pct)
        pygame.draw.rect(surface, (80, 60, 20), (14, 130, 180, 12), border_radius=4)
        pygame.draw.rect(surface, (255, 200, 50), (14, 130, bar_w, 12), border_radius=4)
        label = font.render("DRIFT ANGLE", True, (255, 200, 50))
        surface.blit(label, (14, 145))

# ─── UI Menu ──────────────────────────────────────────────────────────────────
def draw_car_menu(surface, title_font, font, car_names, mouse_pos):
    menu_w, menu_h = int(SCREEN_W * 0.8), int(SCREEN_H * 0.8)
    menu_x, menu_y = int(SCREEN_W * 0.1), int(SCREEN_H * 0.1)

    overlay = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
    overlay.fill((30, 30, 30, 190))
    pygame.draw.rect(overlay, (200, 200, 200), overlay.get_rect(), 4)

    title = title_font.render("CHOOSE YOUR CAR", True, (255, 255, 255))
    overlay.blit(title, (menu_w // 2 - title.get_width() // 2, 40))

    cols, rows = 3, 2
    pad_x, pad_y = 40, 40
    btn_w = (menu_w - pad_x * (cols + 1)) // cols
    btn_h = (menu_h - 120 - pad_y * (rows + 1)) // rows

    rects = []
    for i, name in enumerate(car_names):
        row, col = i // cols, i % cols
        bx = pad_x + col * (btn_w + pad_x)
        by = 120 + pad_y + row * (btn_h + pad_y)

        btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
        screen_rect = pygame.Rect(menu_x + bx, menu_y + by, btn_w, btn_h)
        rects.append(screen_rect)

        color = (100, 100, 100, 240) if screen_rect.collidepoint(mouse_pos) else (50, 50, 50, 200)
        pygame.draw.rect(overlay, color, btn_rect, border_radius=10)
        pygame.draw.rect(overlay, (180, 180, 180), btn_rect, 2, border_radius=10)

        text = font.render(name, True, (255, 255, 255))
        overlay.blit(text, (bx + btn_w // 2 - text.get_width() // 2, by + btn_h // 2 - text.get_height() // 2))

    surface.blit(overlay, (menu_x, menu_y))
    return rects

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("2D Sideway Showdown")
    clock  = pygame.font.SysFont(None, 22)  # reused as font below
    font   = pygame.font.SysFont("consolas", 18)
    timer  = pygame.time.Clock()

    # ── Load / create assets ──────────────────────────────────────────────
    # Track
    track_img = load_image(TRACK_PATH)
    if track_img is None:
        track_img = make_track_surface(1800, 1400)
        print("[INFO] Track image not found – using procedural track.")
    else:
        print(f"[INFO] Track loaded from: {TRACK_PATH}")

    WORLD_W = track_img.get_width()
    WORLD_H = track_img.get_height()

    # Build track collision mask (white/light pixels = driveable)
    # We define "on track" as any pixel that is NOT pure grass green.
    # A simpler approach: generate a dedicated mask surface matching track shape.
    # For the procedural track we do it directly; for a real PNG we threshold.
    mask_surf = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
    mask_surf.blit(track_img, (0, 0))

    # Create mask: pixels darker than grass OR with R>G considered track
    # (works for both grey asphalt and the procedural oval)
    raw = pygame.surfarray.pixels3d(mask_surf)   # shape (W, H, 3)
    import numpy as np
    # Grass detection: G much larger than R and B (greenish)
    is_grass = (raw[:,:,1].astype(int) - raw[:,:,0].astype(int) > 30) & \
               (raw[:,:,1].astype(int) - raw[:,:,2].astype(int) > 20)
    del raw

    # Build a bool mask Surface for fast lookup
    mask_bits = (~is_grass).T   # transpose to (H, W) for pygame y,x indexing
    track_mask_surf = pygame.Surface((WORLD_W, WORLD_H))
    px = pygame.surfarray.pixels2d(track_mask_surf)
    px[:] = 0
    # Mark track pixels white
    white = track_mask_surf.map_rgb(255, 255, 255)
    px[~is_grass] = white
    del px
    track_mask = pygame.mask.from_threshold(track_mask_surf, (255, 255, 255), (10, 10, 10))
    track_rect  = pygame.Rect(0, 0, WORLD_W, WORLD_H)

    # Car
    car_img = load_image(CAR_PATH, (CAR_W, CAR_H))
    # ── TÍNH NĂNG ĐỔI XE ──
    car_files = ["toyota_altezza_gita.png", "mclaren_600lt.png", "lamborghini_countach_lpi800-4.png",
                 "koenigsegg_gemera.png", "pagani_utopia.png", "lamborghini_murcielago_lp670-4_superveloce.png"]
    car_names = ["Toyota Altezza Gita", "McLaren 600LT", "Countach LPI800-4",
                 "Koenigsegg Gemera", "Pagani Utopia", "Murcielago LP670-4 SV"]

    car_images = []
    for f in car_files:
        img = load_image(find_asset("assets", "car_model_topdown", f), (CAR_W, CAR_H))
        car_images.append(img if img else make_car_surface(CAR_W, CAR_H))

    current_car_index = 0
    show_car_menu = False
    menu_title_font = pygame.font.SysFont("arial", 48, bold=True)
    menu_btn_font = pygame.font.SysFont("arial", 22, bold=True)
    menu_rects = []

    car = Car(720, 1700, car_images[current_car_index])
    camera = Camera()
    camera.x, camera.y = car.x, car.y

    # ── Main loop ─────────────────────────────────────────────────────────
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

            camera.handle_zoom(event)

            # Bật/Tắt Menu
            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                show_car_menu = not show_car_menu

            # Click chọn xe
            if show_car_menu and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(menu_rects):
                    if rect.collidepoint(mouse_pos):
                        current_car_index = i
                        car.change_image(car_images[i])
                        show_car_menu = False

        if not show_car_menu:
            car.update(pygame.key.get_pressed(), track_mask, track_rect)
            camera.update(car)

        # ── Render world ─────────────────────────────────────────────
        screen.fill(C_GRASS)
        zf = camera.zoom_factor

        scaled_track = pygame.transform.scale(track_img, (int(WORLD_W * zf), int(WORLD_H * zf)))
        screen.blit(scaled_track, (int(SCREEN_W // 2 - camera.x * zf), int(SCREEN_H // 2 - camera.y * zf)))

        car.draw(screen, camera.x, camera.y, zf)
        draw_hud(screen, car, font)

        zoom_text = font.render(f"Zoom  : Level {camera.zoom_level} ({int(zf * 100)}%)", True, (200, 255, 200))
        car_text = font.render(f"Car   : {car_names[current_car_index]} (Press C)", True, (150, 200, 255))
        screen.blit(zoom_text, (14, 125))
        screen.blit(car_text, (14, 145))

        if show_car_menu:
            menu_rects = draw_car_menu(screen, menu_title_font, menu_btn_font, car_names, mouse_pos)

        pygame.display.flip()
        timer.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    # numpy is needed for mask generation
    try:
        import numpy
    except ImportError:
        print("Installing numpy...")
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "--break-system-packages", "-q"])
    main()
"""
=====================================================================
TWODSS_LEADERBOARD.PY — MÀN HÌNH BẢNG XẾP HẠNG TỔNG KẾT TRẬN ĐẤU
=====================================================================
Module này chịu trách nhiệm hiển thị kết quả cuối cùng của trận đua,
cho phép người dùng xem vị trí, hãng xe và thời gian hoàn thành.

Cấu trúc:
    - Layout cột được định nghĩa bằng hằng số (Constants) dễ tùy chỉnh.
    - Dữ liệu được truyền từ engine thông qua `self.racers_data`.
=====================================================================
"""

import pygame
import os

SCREEN_W, SCREEN_H = 1920, 1080

# =====================================================================
# LAYOUT CONSTANTS (CHỈNH SỐ Ở ĐÂY ĐỂ XÍCH CÁC CỘT RỘNG/HẸP TÙY Ý)
# =====================================================================
TABLE_BASE_X = (SCREEN_W - 1300) // 2

# Tọa độ X cho các cột (Tăng số để đẩy sang phải, giảm để đẩy sang trái)
X_RANK = TABLE_BASE_X + 50
X_NAME = TABLE_BASE_X + 250
X_CAR  = TABLE_BASE_X + 1200  # Đã xích ra xa để không dính tên
X_TIME = TABLE_BASE_X + 1200 # Đã xích ra xa để tách biệt thời gian

ROW_HEIGHT = 80
START_Y = 300

class RaceLeaderboard:
    """Class quản lý hiển thị bảng xếp hạng."""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.result = None
        self.racers_data = [] # List dict: [{'name': '...', 'car': '...', 'time': '...'}]

        # Load font
        font_path = os.path.join(base_dir, "assets", "fonts", "Graduate-Regular.ttf")
        if not os.path.exists(font_path):
            font_path = r"E:\2D Sideway Showdown\assets\fonts\Graduate-Regular.ttf"

        try:
            self.font_title = pygame.font.Font(font_path, 60)
            self.font_rank  = pygame.font.Font(font_path, 38)
            self.font_text  = pygame.font.Font(font_path, 32)
            self.font_btn   = pygame.font.Font(font_path, 28)
        except:
            self.font_title = pygame.font.SysFont("impact", 60)
            self.font_rank  = pygame.font.SysFont("impact", 38)
            self.font_text  = pygame.font.SysFont("impact", 32)
            self.font_btn   = pygame.font.SysFont("impact", 28)

    def set_data(self, data):
        """Cập nhật dữ liệu tay đua cho bảng xếp hạng."""
        self.racers_data = data

    def handle_event(self, event):
        """Xử lý sự kiện nhấn phím/chuột."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Nếu cần nút CONTINUE, bạn kiểm tra tọa độ nút ở đây
            return "back"
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            return "back"
        return None

    def update(self, dt):
        pass

    def draw(self, screen):
        """Vẽ bảng xếp hạng với bố cục đã căn chỉnh lại khoảng cách."""
        # 1. Vẽ tiêu đề màn hình
        title_surf = self.font_title.render("RACE RESULTS", True, (255, 255, 255))
        screen.blit(title_surf, ((SCREEN_W - title_surf.get_width()) // 2, 100))

        # 2. Vẽ header cột (Tùy chọn, nếu bạn muốn ghi chữ 'Rank', 'Name'...)
        header_color = (200, 200, 200)
        screen.blit(self.font_text.render("POS", True, header_color), (X_RANK, START_Y - 50))
        screen.blit(self.font_text.render("DRIVER", True, header_color), (X_NAME, START_Y - 50))
        screen.blit(self.font_text.render("CAR", True, header_color), (X_CAR, START_Y - 50))
        screen.blit(self.font_text.render("TIME", True, header_color), (X_TIME, START_Y - 50))

        # 3. Vẽ dữ liệu các hàng
        for i, racer in enumerate(self.racers_data):
            current_y = START_Y + (i * ROW_HEIGHT)
            is_player = racer.get("is_player", False)
            text_color = (255, 235, 120) if is_player else (255, 255, 255)

            # Vẽ Rank
            screen.blit(self.font_rank.render(f"{i+1}", True, text_color), (X_RANK, current_y))

            # Vẽ Tên
            screen.blit(self.font_text.render(racer.get("name", "Unknown"), True, text_color), (X_NAME, current_y))

            # Vẽ Xe
            car_text = racer.get("car", "Vehicle")
            screen.blit(self.font_text.render(car_text, True, (180, 180, 180)), (X_CAR, current_y))

            # Vẽ Thời gian
            time_text = racer.get("time", "--:--.--")
            screen.blit(self.font_text.render(time_text, True, text_color), (X_TIME, current_y))

            # Đường kẻ ngang phân cách
            pygame.draw.line(screen, (60, 60, 60),
                             (TABLE_BASE_X, current_y + ROW_HEIGHT - 10),
                             (TABLE_BASE_X + 1300, current_y + ROW_HEIGHT - 10), width=1)

        # 4. Vẽ nút Continue (Giả lập vị trí dưới cùng)
        btn_rect = pygame.Rect((SCREEN_W - 200) // 2, 900, 200, 60)
        pygame.draw.rect(screen, (40, 100, 180), btn_rect, border_radius=10)
        lbl = self.font_btn.render("CONTINUE", True, (255, 255, 255))
        screen.blit(lbl, lbl.get_rect(center=btn_rect.center))
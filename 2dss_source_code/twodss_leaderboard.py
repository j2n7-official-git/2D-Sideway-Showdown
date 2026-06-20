"""
=====================================================================
TWODSS_LEADERBOARD.PY — MÀN HÌNH BẢNG XẾP HẠNG TỔNG KẾT TRẬN ĐẤU
=====================================================================
"""
import pygame
import os
import sys

SCREEN_W, SCREEN_H = 1920, 1080


class RaceLeaderboard:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.result = None  # Tín hiệu điều hướng hành động ("back")
        self.racers_data = []  # Danh sách tay đua nhận từ track sau trận

        # Khởi tạo Font Graduate-Regular chuẩn đường dẫn linh hoạt
        font_path = os.path.join(base_dir, "assets", "fonts", "Graduate-Regular.ttf")
        if not os.path.exists(font_path):
            # Fallback nếu chạy local ổ E tuyệt đối của bạn
            font_path = r"E:\2D Sideway Showdown\assets\fonts\Graduate-Regular.ttf"

        try:
            self.font_title = pygame.font.Font(font_path, 60)
            self.font_rank = pygame.font.Font(font_path, 38)
            self.font_text = pygame.font.Font(font_path, 32)
            self.font_btn = pygame.font.Font(font_path, 28)
        except:
            print("[FONT WARNING] Không tìm thấy Graduate-Regular.ttf, dùng font mặc định.")
            self.font_title = pygame.font.SysFont("impact", 60)
            self.font_rank = pygame.font.SysFont("arial", 38, bold=True)
            self.font_text = pygame.font.SysFont("arial", 32)
            self.font_btn = pygame.font.SysFont("impact", 28)

        # Tải các tài nguyên hình ảnh Huy chương và Background tổng kết
        self.img_bg = None
        self.medals = {}

        try:
            # Ảnh nền bảng điểm (Sử dụng lại background standby huyền thoại cho đồng bộ)
            bg_p = os.path.join(base_dir, "assets", "background_game", "2dss_standby_bg.PNG")
            if os.path.exists(bg_p):
                self.img_bg = pygame.transform.scale(pygame.image.load(bg_p).convert(), (SCREEN_W, SCREEN_H))

            # Nạp ảnh 3 huy chương đầu bảng từ assets ui-race-mode
            ui_dir = os.path.join(base_dir, "assets", "ui-race-mode")
            for rank, name in [(1, "1st_place.png"), (2, "2nd_place.png"), (3, "3rd_place.png")]:
                p = os.path.join(ui_dir, name)
                if os.path.exists(p):
                    img = pygame.image.load(p).convert_alpha()
                    # Scale kích thước huy chương cho vừa vặn bảng điểm (~60x60 px)
                    self.medals[rank] = pygame.transform.smoothscale(img, (60, 60))
        except Exception as e:
            print(f"[LEADERBOARD ASSETS ERROR] {e}")

        # Định nghĩa nút bấm Quay lại Showroom dưới đáy màn hình
        self.btn_rect = pygame.Rect((SCREEN_W - 400) // 2, SCREEN_H - 120, 400, 70)

    # ==========================================================
    # 2. DÁN HÀM set_data VÀO ĐÂY (Thẳng hàng chữ 'd' với def __init__)
    # ==========================================================
    def set_data(self, final_standings):
        """
        Nhận danh sách kết quả xếp hạng từ map đua truyền qua.
        """
        self.racers_data = final_standings
        self.result = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_BACKSPACE]:
                self.result = "back"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_rect.collidepoint(event.pos):
                self.result = "back"

    def update(self, dt):
        pass

    def draw(self, screen):
        # 1. Vẽ Ảnh nền
        if self.img_bg:
            screen.blit(self.img_bg, (0, 0))
        else:
            screen.fill((20, 20, 25))

        # Phủ một lớp bóng mờ đen ở giữa để làm nổi bật bảng điểm
        overlay = pygame.Surface((1400, 750), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, ((SCREEN_W - 1400) // 2, 100))

        # Vẽ viền cam bao quanh bảng điểm thể thao
        pygame.draw.rect(screen, (255, 140, 0), ((SCREEN_W - 1400) // 2, 100, 1400, 750), width=3)

        # 2. Tiêu đề bảng xếp hạng
        title_surf = self.font_title.render("RACE LEADERBOARD", True, (255, 140, 0))
        screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_W // 2, 150)))

        # Vẽ đường gạch ngang trang trí bên dưới tiêu đề
        pygame.draw.line(screen, (100, 100, 100), (SCREEN_W // 2 - 600, 200), (SCREEN_W // 2 + 600, 200), width=2)

        # 3. Duyệt danh sách hiển thị từng hàng kết quả (Tối đa 6 hàng tương ứng 6 xe)
        start_y = 240
        row_h = 85

        for i, racer in enumerate(self.racers_data[:6]):
            rank = i + 1
            current_y = start_y + (i * row_h)

            # Đổi màu chữ làm nổi bật dòng của Người chơi (Player) bằng màu vàng rực
            is_player = racer.get("is_player", False)
            text_color = (255, 215, 0) if is_player else (230, 230, 230)

            # Vẽ cột 1: Huy chương hoặc Số hạng định dạng bằng Font Graduate
            rank_x = (SCREEN_W - 1300) // 2 + 50
            if rank in self.medals:
                # Nếu là top 3, blit hình ảnh huy chương lung linh lên
                m_img = self.medals[rank]
                screen.blit(m_img, (rank_x, current_y - 10))
            else:
                # Nếu là hạng 4th, 5th, 6th -> Tạo text chuỗi theo yêu cầu
                rank_str = f"{rank}th"
                r_surf = self.font_rank.render(rank_str, True, (160, 160, 160))
                screen.blit(r_surf, (rank_x, current_y))

            # Vẽ cột 2: Tên tay đua (Driver Name)
            name_surf = self.font_text.render(racer.get("name", "Unknown"), True, text_color)
            screen.blit(name_surf, ((SCREEN_W - 1300) // 2 + 200, current_y))

            # Vẽ cột 3: Tên phương tiện (Car Model)
            car_surf = self.font_text.render(racer.get("car", "Vehicle"), True,
                                             (140, 140, 140) if not is_player else (255, 235, 120))
            screen.blit(car_surf, ((SCREEN_W - 1300) // 2 + 620, current_y))

            # Vẽ cột 4: Tổng thời gian hoàn thành cuộc đua (Total Time)
            time_surf = self.font_text.render(racer.get("time", "--:--.--"), True, text_color)
            screen.blit(time_surf, ((SCREEN_W - 1300) // 2 + 1050, current_y))

            # Vẽ đường kẻ mờ phân tách giữa các hàng
            pygame.draw.line(screen, (40, 40, 40), ((SCREEN_W - 1300) // 2, current_y + row_h - 20),
                             ((SCREEN_W + 1300) // 2, current_y + row_h - 20), width=1)

        # 4. Vẽ nút bấm Quay lại (CONTINUE BUTTON) dưới đáy
        mx, my = pygame.mouse.get_pos()
        btn_hover = self.btn_rect.collidepoint((mx, my))
        btn_bg_color = (255, 165, 0) if btn_hover else (200, 100, 0)

        pygame.draw.rect(screen, btn_bg_color, self.btn_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.btn_rect, width=2, border_radius=5)

        btn_txt = self.font_btn.render("CONTINUE", True, (255, 255, 255))
        screen.blit(btn_txt, btn_txt.get_rect(center=self.btn_rect.center))
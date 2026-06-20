# 🏁 2D Sideway Showdown

**2D Sideway Showdown** là một trò chơi đua xe góc nhìn từ trên xuống (Top-down 2D Racing Game) được phát triển hoàn toàn bằng ngôn ngữ Python (tối ưu hóa hiệu năng trên **Python 3.14.5**) kết hợp cùng thư viện Pygame. Dự án hướng tới một gameplay tốc độ cao, chân thực nhờ sự kết hợp chặt chẽ giữa mô phỏng vật lý trượt bánh (sideway) và hệ thống trí tuệ nhân tạo (AI Bot) thế hệ mới.

---

## 🚀 Tính Năng Cốt Lõi

- **Hệ Thống Vật Lý Nâng Cao (`twodss_physics.py`):** - *Chống xuyên tường tuyệt đối:* Áp dụng mô hình đa giác viền thực (Polygon Mesh từ 24–32 đỉnh kèm cosine-spacing) và thuật toán quét vị trí liên tục `_swept_advance()`.
  - *Trượt tiếp tuyến thông minh:* Xe tự động trượt mượt mà dọc theo vách đá hoặc rào chắn khi đâm lệch góc thay vì bị khựng đứng.
  - *Va chạm xe-xe không giật (No-knockback):* Thuật toán Capsule Collision khử hoàn toàn hiện tượng rung lắc/dội lực phi thực tế khi các xe xô xát, chèn ép nhau ở tốc độ cao.

- **Trí Tuệ Nhân Tạo Thông Minh v2 (`twodss_racer_v2.py`):** - Tích hợp bộ não điều phối ưu tiên (Priority Dispatcher). Bot tự động bám làn đua, chủ động lách tránh chướng ngại vật, né xe của người chơi và kích hoạt chế độ tự thoát kẹt thông minh khi gặp sự cố.
  - Quản lý danh sách 42 tay đua máy với các cấp độ hung hãn (Aggression) khác nhau từ 1.00 đến 1.35.

- **Showroom & Cân Bằng Chỉ Số (`twodss_car_data.py`):** - Dàn siêu xe đa dạng phân bổ từ xe phổ thông đến các phân khúc Hypercar cao cấp (Tier D). Mỗi dòng xe sở hữu bộ thông số độc lập về vận tốc tối đa, gia tốc, hiệu ứng Nitro Boost và độ ma sát bề mặt.

- **Kiến Trúc Module Hóa:**
  - Logic cốt lõi được tách rời hoàn toàn khỏi file bản đồ (Track). Cấu trúc code sạch giúp lập trình viên dễ dàng mở rộng, cấy thêm map mới hoặc tùy biến tính năng mà không lo xung đột mã nguồn.

---

## 🛠️ Công Nghệ Sử Dụng

- **Ngôn ngữ lập trình:** Python 3.14.5
- **Thư viện chính:** Pygame (Quản lý vòng lặp game, render đồ họa 2D, âm thanh và bắt sự kiện).
- **Thuật toán áp dụng:** Định lý trục phân tách (SAT), Dynamic Bicyle Model (Mô hình động lực học xe đạp) calib chuyển động và xử lý ma sát liên tục.

---

## 🎮 Hướng Dẫn Khởi Chạy

1. **Cài đặt môi trường:**
   ```bash
   pip install pygame

   Bước 2: Di chuyển vào đúng thư mục mã nguồn
Sử dụng lệnh cd để điều hướng Terminal đến folder chứa project (Ví dụ đường dẫn trên máy của bạn):

E:
cd "E:\2D Sideway Showdown\2dss_source_code"

chạy thông qua code
python twodss_core_main.py

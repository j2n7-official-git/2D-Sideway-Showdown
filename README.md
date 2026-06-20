<img width="1920" height="1080" alt="Screenshot (171)" src="https://github.com/user-attachments/assets/4a0135fa-3e6c-4381-8128-1f96919bf10d" /># 🏁 2D Sideway Showdown

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

E:\2D Sideway Showdown\2dss_source_code\twodss_core_main.py
một số lưu ý:
nên chạy trên nền tảng python 3.14.5 vì phiên bản đã hỗ trợ cập nhật nhiều thư viện thứ 3 đa dạng và phong phú
thư mục của file luôn đặt chuẩn chỉnh như này để chạy một cách ổn thỏa
<img width="729" height="385" alt="image" src="https://github.com/user-attachments/assets/488f24ff-0d17-4bf1-8c9f-740c4d0abcd5" />

cd "E:\2D Sideway Showdown\2dss_source_code"
<img width="1110" height="707" alt="image" src="https://github.com/user-attachments/assets/25f98966-23fa-4ce8-9985-0bc62b9eedbd" />

<img width="740" height="614" alt="image" src="https://github.com/user-attachments/assets/d800c35b-9c56-4188-9e47-8cf4a52dfbd7" />

------------
Dự án vẫn đang trong quá trình hoàn thiện (Work-in-Progress). Dev xin thành thật khai báo những "góc khuất" sau đây:

🤖 AI Bot "Tập Lái": Bot hiện tại chưa đủ thông minh. Chúng thường xuyên lái xe "lạng quạng", thiếu ổn định, và đôi khi... hơi quá nhiệt tình trong việc đâm vào người chơi hoặc tường. Đừng quá khắt khe, chúng chỉ đang học cách lái thôi!

📊 Leaderboard UI: Cột thông tin đã được dãn cách, nhưng do độ dài tên xe và tên người chơi khác nhau, đôi khi vẫn còn hiện tượng các dòng chữ "nhìn nhau đắm đuối" (hơi sát nhau). Đang tìm cách căn lề chuẩn xác nhất cho mọi trường hợp.

🗺️ Map Content: Game dự kiến có 5 bản đồ, nhưng hiện tại chỉ mới có 3 map hoạt động ổn định. 2 map còn lại đang được "xây dựng" và sẽ sớm cập nhật trong các phiên bản tới.

🧱 Bug Vật lý (Noclip): Đây là lỗi khó chịu nhất: xe đôi khi "đi xuyên tường" (noclip) hoặc bị kẹt cứng (softlock) trong các góc va chạm, khiến người chơi không thể di chuyển tiếp và buộc phải restart lại game. Dev đang cố gắng debug để không ai bị "giam giữ" bởi bức tường nữa.

Mọi đóng góp (pull request) để sửa lỗi hoặc cải thiện AI đều rất được hoan nghênh! Hãy giúp dự án này bớt "ngáo" hơn.

-------------
## 🛠️ Công Nghệ Sử Dụng

- **Ngôn ngữ lập trình:** Python 3.14.5
- **Thư viện chính:** Pygame (Quản lý vòng lặp game, render đồ họa 2D, âm thanh và bắt sự kiện).
- **Thuật toán áp dụng:** Định lý trục phân tách (SAT), Dynamic Bicycle Model (Mô hình động lực học xe đạp) calib chuyển động và xử lý ma sát liên tục.
- --------------

## 🎮 Hệ Thống Điều Khiển (Gameplay Controls)

Khi bước vào trận đua, bạn sẽ làm chủ siêu xe của mình thông qua tổ hợp phím tối ưu sau:
- **Cụm phím W-A-D:** Điều khiển hướng di chuyển chính của xe.
  - **Phím W:** Nhấn ga để tăng tốc tiến về phía trước.
  - **Phím A / D:** Đánh vô-lăng tương ứng sang bên Trái / bên Phải.
- **Phím S:** Phanh giảm tốc khi đang chạy tiến, đồng thời hỗ trợ **lùi xe khẩn cấp** linh hoạt trong các tình huống va chạm.
- **Phím L-Shift (Shift trái):** Kích hoạt hệ thống phản lực Nitro Boost nhằm bứt tốc xé gió vượt mặt đối thủ.
- **Phím Spacebar (Nhấn giữ):** Kích hoạt trạng thái phanh tay để chủ động kiểm soát các pha **Drift bó vỉa** ôm cua gắt ở tốc độ cao.
- **Phím P:** Tạm dừng (Pause) trận đấu để thiết lập hoặc nghỉ ngơi.

-----------------
Một số hình ảnh minh họa và qua quá trình lập trình và sửa chữa vẫn còn đang tiếp diễn
chạy thông qua code và đuộc thực nghiệm thường xuyên:
<img width="1920" height="1080" alt="Screenshot (160)" src="https://github.com/user-attachments/assets/d56f8892-983d-4834-90ac-2f0539ec3487" />
<img width="1920" height="1080" alt="Screenshot (159)" src="https://github.com/user-attachments/assets/e5e566c1-add9-4f17-9999-e3c9d8db390a" />
<img width="1920" height="1080" alt="Screenshot (158)" src="https://github.com/user-attachments/assets/98f2a8df-807a-4aa7-9650-abb45e3871ee" />
<img width="1920" height="1080" alt="Screenshot (157)" src="https://github.com/user-attachments/assets/aa555ea0-09dd-4eb7-858b-220e0ef12245" />
<img width="1920" height="1080" alt="Screenshot (156)" src="https://github.com/user-attachments/assets/dc714278-1308-409e-a6d9-13b4312747fd" />
<img width="1920" height="1200" alt="Screenshot (155)" src="https://github.com/user-attachments/assets/7ca388b9-4ee0-4689-ad18-672d9822f315" />
<img width="1920" height="1080" alt="Screenshot (154)" src="https://github.com/user-attachments/assets/da1e7490-abf2-48cc-8095-6bf082d74ccb" />
<img width="1920" height="1080" alt="Screenshot (153)" src="https://github.com/user-attachments/assets/b87797fb-3d84-4ee8-a360-29114fee1948" />
<img width="1920" height="1080" alt="Screenshot (139)" src="https://github.com/user-attachments/assets/870f7166-d070-4f8e-bf90-fc3e1849a80f" />
<img width="1920" height="1080" alt="Screenshot (138)" src="https://github.com/user-attachments/assets/36f8b609-da91-4a28-8d56-406f2a9b8a94" />
<img width="1920" height="1080" alt="Screenshot (137)" src="https://github.com/user-attachments/assets/b9de4b3b-da35-47e8-83da-15beb6f1bc47" />
<img width="1920" height="1080" alt="Screenshot (182)" src="https://github.com/user-attachments/assets/e84ea871-7a07-4000-9666-7c587470c440" />
<img width="1920" height="1080" alt="Screenshot (181)" src="https://github.com/user-attachments/assets/e55ade68-6d75-4362-82af-1004d34447e9" />
<img width="1920" height="1080" alt="Screenshot (180)" src="https://github.com/user-attachments/assets/627b46ce-53ab-42a9-b260-a21cf497b005" />
<img width="1920" height="1080" alt="Screenshot (179)" src="https://github.com/user-attachments/assets/a4127bbc-ad8d-423e-9f77-14b8288e218d" />
<img width="1920" height="1080" alt="Screenshot (178)" src="https://github.com/user-attachments/assets/ac9bbbff-3868-4f1a-9473-30bd36f9df18" />
<img width="1920" height="1080" alt="Screenshot (153)" src="https://github.com/user-attachments/assets/4060912f-a865-453f-9d74-920abd25e9a5" />
<img width="1920" height="1080" alt="Screenshot (177)" src="https://github.com/user-attachments/assets/31786365-f8e4-490d-a78c-6f3399469c2c" />
<img width="1920" height="1080" alt="Screenshot (176)" src="https://github.com/user-attachments/assets/73de59d7-ed0c-4940-a74c-723a86a73a8b" />
<img width="1920" height="1080" alt="Screenshot (175)" src="https://github.com/user-attachments/assets/5c9690ca-2b15-44da-b1b8-1299a6e83342" />
<img width="1920" height="1080" alt="Screenshot (174)" src="https://github.com/user-attachments/assets/c7b72049-453b-4ced-8c97-029ced3926ab" />

<img width="1920" height="1080" alt="Screenshot (161)" src="https://github.com/user-attachments/assets/d12817f7-3063-4414-8435-0594cc5ade57" />
<img width="1920" height="1080" alt="Screenshot (172)" src="https://github.com/user-attachments/assets/276257c0-5499-4211-9ddd-13a88bc39d65" />
<img width="1920" height="1080" alt="Screenshot (170)" src="https://github.com/user-attachments/assets/1390f992-b3f2-4f6a-9926-de5fb1b54088" />
<img width="1920" height="1080" alt="Screenshot (169)" src="https://github.com/user-attachments/assets/4800003e-6ddd-47b5-8480-ad89fe50d387" />
<img width="1920" height="1080" alt="Screenshot (168)" src="https://github.com/user-attachments/assets/05f4b0a1-ed7d-40ee-ab96-573d1d549d2a" />
<img width="1920" height="1080" alt="Screenshot (167)" src="https://github.com/user-attachments/assets/44e1d885-b5f1-496d-b453-65d8a3aba538" />
<img width="1920" height="1080" alt="Screenshot (166)" src="https://github.com/user-attachments/assets/e79d2fa0-24d5-4172-9484-0e0b6eb2893b" />
<img width="1920" height="1080" alt="Screenshot (165)" src="https://github.com/user-attachments/assets/a48452b2-5190-4add-92eb-383ee02211d4" />
<img width="1920" height="1080" alt="Screenshot (164)" src="https://github.com/user-attachments/assets/42079d37-76c9-446f-906e-f45d6a11394a" />
<img width="1920" height="1080" alt="Screenshot (163)" src="https://github.com/user-attachments/assets/7b35bb15-88fc-4064-9746-472d48048c29" />
<img width="1920" height="1080" alt="Screenshot (162)" src="https://github.com/user-attachments/assets/65131f9f-475e-4008-a51e-5f1b3be5c203" />

<img width="1920" height="1080" alt="Screenshot (173)" src="https://github.com/user-attachments/assets/ef39ed24-eaff-4638-9ea7-77000f5da11e" />


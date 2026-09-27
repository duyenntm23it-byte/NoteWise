# Prompt: Cập nhật UI/UX, Phân quyền Guest/Logged-in và Hoàn thiện Prototype NoteWise

Bạn là một Chuyên gia UI/UX và Kiến trúc sư Frontend. Hãy cập nhật bản Prototype NoteWise trong thư mục `prototype/` dựa trên các quy tắc phân quyền, sửa đổi giao diện và bổ sung các trạng thái tương tác chi tiết bên dưới.

## 1. Cơ chế Phân quyền Khách (Guest) vs Đã đăng nhập (Logged-in)

Mô phỏng trạng thái đăng nhập bằng `localStorage` (`isLoggedIn = true/false`) trong `script.js` mà không cần backend:

### Chế độ Khách (`isLoggedIn === false`):

- **Top Header**: Hiển thị nút [Đăng nhập] và [Đăng ký] ở góc phải (thay vì Avatar).
- **Trang chủ (Dashboard)**: Xem dữ liệu mẫu tĩnh.
- **Tài liệu (Materials)**: Chỉ xem 1–2 tài liệu mẫu; Ẩn/Khóa nút Tải lên file mới và nút Xóa file.
- **Q&A & Tóm tắt AI**: Cho phép hỏi đáp trên tài liệu mẫu (giới hạn lượt).
- **Làm Quiz**: Làm được 1 bài quiz demo. Khi nộp bài, hiển thị thông báo rõ ràng: _"⚠️ Kết quả không được lưu vì bạn chưa đăng nhập. [Đăng nhập ngay]"_.
- **Phân tích / Gợi ý / Lịch sử**: Hiển thị khung Empty State kèm hình minh họa và nút CTA _"Đăng nhập để xem tiến độ cá nhân"_ (không khóa im lặng).

### Chế độ Đã đăng nhập (`isLoggedIn === true`):

- **Top Header**: Hiển thị Avatar `AT` (An Ton) + Tên người dùng + Nút [Đăng xuất].
- Mở khóa toàn bộ tính năng: Tải tài liệu cá nhân, Lưu kết quả Quiz tự động, Xem biểu đồ Phân tích ma trận chủ đề yếu và nhận Gợi ý học tập cá nhân hóa.

---

## 2. Chi tiết Sửa đổi Giao diện theo Màn hình

### Màn hình 1: Xác thực (Auth)

- Tích hợp Form Auth dạng Tab: **[Đăng nhập]** và **[Đăng ký]**.
- Tab Đăng ký: Bổ sung trường "Xác nhận mật khẩu" và đổi tên nút Submit thành "Tạo tài khoản".
- Khi bấm Submit Đăng nhập/Đăng ký -> Đổi `isLoggedIn = true`, lưu `localStorage`, chuyển về Dashboard và đổi Header sang Avatar.

### Màn hình 2: Kho tài liệu (Materials)

- Rút gọn bộ lọc: Chỉ giữ lại **Bộ lọc Trạng thái** (Sẵn sàng / Đang xử lý / Thất bại). Bỏ bộ lọc Môn học và Thẻ.

### Màn hình 4: Quiz AI (Player & Kết quả)

- **Tự động lưu**: Bỏ nút [Lưu kết quả]. Thay bằng nhãn trạng thái tự động giả lập: _"Đang lưu..."_ -> _"Đã lưu"_.
- **Đa dạng dạng câu hỏi**:
  - Trắc nghiệm / Đúng-Sai: Sử dụng ô chọn Radio (`<input type="radio">`).
  - Điền từ: Sử dụng ô nhập Text (`<input type="text">`).
- **Màn hình Kết quả**: Hiển thị badge **[Bỏ qua]** riêng biệt cho các câu chưa làm, không gộp chung vào số câu "Sai".

### Màn hình 5: Phân tích (Analytics)

- Thay đổi chỉ số: Bỏ "Số tài liệu đã làm chủ", thay bằng **"Số chủ đề có đủ dữ liệu"**.
- Cảnh báo chủ đề yếu: Chỉ hiển thị thẻ cảnh báo nguy cơ khi chủ đề có lượt làm $\ge 2$ trong `mock-data.js`. Nếu chưa đủ lượt làm, hiển thị banner _"Chưa đủ bằng chứng phân tích"_.

### Màn hình 6: Gợi ý học tập (Recommendations)

- Mô phỏng 2 trạng thái:
  1. _Có tài liệu liên quan_: Hiển thị chính xác số trang/slide trích dẫn từ `mock-data.js`.
  2. _Không có tài liệu liên quan_: Hiển thị thông báo _"Bạn chưa có tài liệu về chủ đề này"_ kèm nút CTA _"Tải thêm tài liệu"_.

---

## 3. Bổ sung các Trạng thái Ngoại lệ (UI Edge Cases)

Tạo các Modal/Toast thông báo giả lập trong JS cho các trường hợp:

1. **Nội dung không đủ**: Thông báo khi tài liệu quá ngắn không thể tạo Quiz hoặc Tóm tắt.
2. **Đầu ra AI không hợp lệ**: Hiển thị nút "Thử lại (Retry)" khi AI gặp lỗi phản hồi.
3. **Truy cập trái phép / Phiên hết hạn**: Tự động chuyển về Chế độ Khách và bật Modal thông báo Đăng nhập lại.

---

## 4. Yêu cầu Đầu ra

- Tạo file `chapter-04-ai-for-product-design/prompts/04-auth-and-prototype-updates.prompt.md`.
- Cập nhật các file HTML/JS/CSS trong `chapter-04-ai-for-product-design/prototype/` đáp ứng đầy đủ các quy tắc trên.

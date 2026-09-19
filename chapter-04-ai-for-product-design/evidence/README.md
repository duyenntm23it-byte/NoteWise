# Chapter 04 Evidence

Thư mục này dùng để lưu ảnh chụp màn hình và ghi nhận kiểm thử giao diện của Chapter 04. Ảnh có thể được chụp từ hai concept trong `../design/concepts/` và prototype độc lập trong `../prototype/`.

## Đường dẫn xem artifact

- Prototype chính: mở `../prototype/index.html` trực tiếp bằng trình duyệt.
- Concept màn hình Q&A: mở `../design/concepts/screen-3-qa-concept.html`.
- Concept màn hình Quiz: mở `../design/concepts/screen-4-quiz-concept.html`.
- Sơ đồ user flow: mở `../design/user-flow.mmd` bằng Mermaid Live Editor hoặc extension Mermaid trong VS Code.

## Cách chụp evidence

1. Mở từng file HTML bằng trình duyệt hiện đại.
2. Chụp ít nhất viewport desktop và mobile cho các trạng thái chính.
3. Đặt ảnh vào thư mục này với tên dễ truy vết, ví dụ `prototype-dashboard-desktop.png`, `prototype-quiz-mobile.png`.
4. Ghi lại ngày chụp, viewport, trình duyệt và thao tác đã kiểm tra trong bảng dưới đây.

| Artifact     | Viewport       | Trạng thái cần kiểm tra             | Ảnh evidence |
| ------------ | -------------- | ----------------------------------- | ------------ |
| Prototype    | Desktop        | Dashboard ready, danh sách tài liệu | _chưa chụp_  |
| Prototype    | Mobile         | Sidebar thu gọn, layout responsive  | _chưa chụp_  |
| Prototype    | Desktop        | Quiz chọn đáp án và kết quả         | _chưa chụp_  |
| Q&A concept  | Desktop/mobile | Tài liệu, citation, input câu hỏi   | _chưa chụp_  |
| Quiz concept | Desktop/mobile | Cấu hình quiz và câu hỏi tương tác  | _chưa chụp_  |

Prototype không cần backend hoặc bước build; chỉ cần giữ nguyên cấu trúc tương đối giữa `index.html`, `styles.css` và `mock-data.js` khi mở trực tiếp.

# Prompt: NoteWise UI Design System

Bạn là product designer đang thiết kế hệ thống giao diện cho NoteWise, một web app học tập cá nhân hóa từ tài liệu PDF/PPTX. Hãy đề xuất một UI design system có thể triển khai cho web responsive, ưu tiên tính rõ ràng, tập trung và khả năng kiểm chứng câu trả lời AI.

## Yêu cầu thị giác

- Dùng bảng màu chủ đạo **Indigo/Purple** nhưng tiết chế, có màu trung tính sáng cho canvas đọc tài liệu và màu trạng thái riêng cho success, warning, error.
- Đề xuất màu nền, surface, border, text primary/secondary, accent, success, warning và error kèm mã hex và mục đích sử dụng.
- Font chữ sans-serif hiện đại, dễ đọc tiếng Việt; dùng một font cho UI và có thể dùng font monospace cho metadata/citation.
- Xác định scale typography, spacing, radius, shadow, icon style và quy tắc focus state.
- Không dùng gradient nặng, card lồng trong card hoặc trang trí làm giảm khả năng đọc.

## Bảy màn hình bắt buộc

1. **Dashboard tổng quan học tập.**
2. **Danh sách và upload tài liệu.**
3. **Màn hình đọc tài liệu chia đôi với trợ lý Q&A.**
4. **Trình tạo Quiz AI và giao diện làm bài.**
5. **Analytics chủ đề yếu.**
6. **Trang chi tiết/tóm tắt tài liệu.**
7. **Cài đặt tài khoản và tùy chọn học tập.**

Với mỗi màn hình, mô tả mục tiêu, primary action, cấu trúc layout, thành phần chính và responsive behavior. Sidebar cần có điều hướng tới Dashboard, Tài liệu, Quiz, Analytics và Cài đặt; top header có breadcrumb, tìm kiếm hoặc trạng thái phiên học.

## Trạng thái cần thiết

Mô tả component và copy cho bốn trạng thái của các màn hình dữ liệu:

- **Loading:** skeleton hoặc progress có giải thích ngắn, không gây hiểu nhầm rằng AI đã hoàn tất.
- **Empty:** hướng dẫn hành động đầu tiên, ví dụ chưa có tài liệu hoặc chưa có kết quả quiz.
- **Error:** thông báo nguyên nhân có thể hiểu, nút thử lại và bảo toàn dữ liệu người dùng.
- **Ready:** nội dung hoàn chỉnh, timestamp/trạng thái xử lý và hành động tiếp theo.

## Đầu ra

Trả về tài liệu design system có token rõ ràng, component inventory, guideline accessibility và ví dụ microcopy bằng tiếng Việt. Giữ giao diện mang cảm giác học tập hiện đại, yên tĩnh và đáng tin cậy; không biến sản phẩm thành dashboard phân tích doanh nghiệp nặng nề.

# NoteWise Product Design Brief

## 1. Tổng quan và triết lý

NoteWise là hệ thống học tập cá nhân hóa từ tài liệu bài giảng PDF, DOCX và PPTX. Người học tải tài liệu lên, đọc tóm tắt, hỏi đáp có trích dẫn, tạo quiz, xem chủ đề yếu và nhận gợi ý học tiếp theo. Mọi hoạt động AI phải truy nguyên được về tài liệu gốc; khi nguồn không đủ, hệ thống nói rõ rằng chưa thể trả lời thay vì suy đoán.

Trải nghiệm được thiết kế cho sinh viên đại học và người tự học: sạch, tập trung, ít gây xao nhãng, có một hành động chính rõ ràng trên mỗi màn hình. Phản hồi trực quan cần có cho xử lý AI ngầm, loading, empty, ready, error/retry và xác nhận hành động phá hủy.

## 2. Global layout và điều hướng

```text
┌ Sidebar thu gọn ┐ ┌ Top Header: breadcrumb | tài liệu | AI status | avatar ┐
│ NoteWise        │ ├───────────────────────────────────────────────────────┤
│ Dashboard       │ │ Main canvas: grid / card / split-screen / modal        │
│ My Materials    │ │                                                       │
│ Document Q&A    │ │                                                       │
│ Quiz            │ │                                                       │
│ Analytics       │ │                                                       │
│ Recommendations │ │                                                       │
│ Learning History│ │                                                       │
│ Profile / Setup │ │                                                       │
└─────────────────┘ └───────────────────────────────────────────────────────┘
```

Sidebar có logo, Dashboard, My Materials, Document Q&A, Quiz, Analytics & Weak Topics, Recommendations và Learning History; phía dưới có Profile, Settings, Logout. Top header có breadcrumb, global document selector, trạng thái AI, notification và avatar. Trên mobile sidebar chuyển thành thanh điều hướng ngang hoặc drawer.

## 3. Chi tiết 7 màn hình

### Màn hình 1 - Xác thực người dùng

**Wireframe:** canvas nền warm off-white -> card auth căn giữa -> logo -> tab `Đăng nhập | Đăng ký` -> Email -> Mật khẩu với nút ẩn/hiện -> Xác thực mật khẩu khi đăng ký -> inline validation -> primary submit -> security note.

Đăng nhập có email, mật khẩu, quên mật khẩu và trạng thái `Đang đăng nhập...`; đăng ký thêm xác thực mật khẩu và trạng thái `Đang tạo tài khoản...`. Tab đổi mode không làm mất dữ liệu không liên quan. Truy cập route nội bộ khi chưa đăng nhập hiển thị error rõ ràng, có nút `Đăng nhập để tiếp tục`. Focus ring phải nhìn thấy bằng bàn phím.

### Màn hình 2 - Kho tài liệu của tôi

**Wireframe:** page header với `+ Tải lên tài liệu`, search, filter Môn học/Thẻ/Trạng thái và toggle grid/list -> drag-and-drop zone -> document cards/list rows -> upload progress.

Hỗ trợ PDF, DOCX, PPTX và hiển thị giới hạn dung lượng. Mỗi tài liệu có tên, ngày tải, dung lượng, môn học, progress và badge `Sẵn sàng`, `Đang xử lý` hoặc `Thất bại`; failed luôn có `Thử lại`. Menu nhanh gồm xem tóm tắt, Q&A, tạo quiz và xóa. Xóa cần confirmation dialog.

### Màn hình 3 - Tài liệu, tóm tắt và Q&A

**Wireframe:** split screen 60/40 -> bên trái document selector + tabs `Tài liệu gốc | Tóm tắt AI` + reader/highlight/citation -> bên phải chat header + messages + composer.

Summary có bullet ý chính, công thức, concept chips. Câu trả lời AI có nội dung và citation dạng `[Trích dẫn: Trang 4, Mục 2.1]`; click citation highlight đoạn tương ứng ở reader. Khi nguồn không đề cập câu hỏi, hiển thị banner `Tài liệu chưa đủ thông tin để trả lời chính xác` và gợi ý câu hỏi khác.

### Màn hình 4 - Quiz AI và làm bài

**Wireframe setup modal:** tài liệu nguồn -> số câu 5-20 -> loại câu hỏi MCQ/Đúng-Sai/Điền từ -> độ khó -> chủ đề tùy chọn -> `Tạo Quiz` -> skeleton AI.

Player có progress `Câu X/Y`, timer tùy chọn, tài liệu, question card, topic tag, difficulty badge, radio/checkbox answer và điều hướng Trước/Bỏ qua/Nộp bài/Câu tiếp. Result có phần trăm, thời gian, đúng/sai, review từng câu, đáp án đã chọn/đúng, AI explanation có thể thu gọn, citation và các nút Làm lại, Phân tích chủ đề yếu, Lưu kết quả.

### Màn hình 5 - Analytics và chủ đề yếu

**Wireframe:** overview widgets -> line chart accuracy theo thời gian -> mastery bars/matrix theo chủ đề -> weak topic cards -> quick actions.

Widget gồm accuracy tổng thể, quiz đã hoàn thành và tài liệu đã làm chủ. Ví dụ mastery: Hồi quy 85%, Phân loại 78%, Cây quyết định 42%. Chủ đề dưới 60% có thẻ cảnh báo `Ưu tiên cao`, lý do từ 3 lần gần nhất, `Tạo Quiz ôn tập` và `Đọc lại tài liệu gốc`.

### Màn hình 6 - Gợi ý bài học cá nhân hóa

**Wireframe:** title `Hành động học tập được đề xuất cho bạn` -> recommendation cards -> context tag -> explanation -> source pages -> CTA `Mở Slide bài giảng` / `Làm Quiz ôn tập 5 câu`.

Mỗi gợi ý giải thích vì sao được chọn, ví dụ `Bạn thường trả lời sai các câu hỏi về cắt tỉa cây quyết định. Đọc lại Trang 12-15 và làm bài kiểm tra nhanh 5 câu.` Nếu chưa đủ lịch sử, banner empty/data-limited nói rõ `Hãy hoàn thành thêm các bài quiz để AI có đủ dữ liệu đưa ra gợi ý chính xác hơn`.

### Màn hình 7 - Lịch sử học tập

**Wireframe:** page header -> filter theo thời gian, tài liệu, hoạt động, điểm số, chủ đề -> table/timeline -> clickable row -> detail drawer.

Hàng lịch sử có timestamp, tên tài liệu, loại hoạt động Quiz/Tóm tắt/Q&A, điểm, thời lượng và weak topic phát hiện. Click mở lại chi tiết bài làm hoặc citation cũ; empty state hướng tới `Bắt đầu học`, loading dùng skeleton rows, error có `Thử lại`.

## 4. Design system tokens

| Token          | Giá trị                                        | Sử dụng                               |
| -------------- | ---------------------------------------------- | ------------------------------------- |
| Primary Indigo | `#4F46B5`                                      | CTA, active navigation, focus         |
| AI Purple      | `#7C5CFC`                                      | AI badge, recommendations, highlights |
| Electric Teal  | `#0F9F95`                                      | AI ready, positive insight            |
| Mint Success   | `#DDF7EA` / `#16845B`                          | Ready, correct                        |
| Amber Warning  | `#FFF1C7` / `#A76500`                          | Processing, attention                 |
| Rose Error     | `#FFE2E7` / `#B33A50`                          | Failed, validation                    |
| Warm canvas    | `#F7F7FB`                                      | App background                        |
| Ink            | `#20243A`                                      | Primary text                          |
| Font           | `Be Vietnam Pro`, fallback `Inter`, sans-serif | UI and Vietnamese body                |
| Spacing        | 4, 8, 12, 16, 24, 32, 48px                     | Consistent rhythm                     |
| Radius         | 8px controls, 12px cards, 16px hero panels     | Soft but restrained                   |
| Shadow         | `0 12px 30px rgba(37,35,80,.07)`               | Subtle elevation                      |

Typography: H1 32/40 700, H2 22/30 700, H3 16/24 700, body 14/22 400, caption 12/18 500. Contrast must meet WCAG AA. Buttons, inputs and icon actions have visible `:focus-visible` rings and labels; state is never communicated by color alone.

## 5. UI states and interactions

- **Loading/skeleton:** skeleton rows for data, progress for upload, pulsing AI skeleton while creating quiz; preserve surrounding layout.
- **Empty:** simple illustration/icon, concise reason, one CTA. Applies to no documents, no quiz history and insufficient recommendation data.
- **Ready:** data, timestamp, source, next action and status badge are visible.
- **Error/recovery:** inline error below the field or failed document row; explain cause, retain input, provide `Thử lại`.
- **Confirmation dialog:** required before deleting a document; name the document, state irreversibility and offer Cancel/Delete.
- **AI insufficient evidence:** never invent answer; show source limitation and link to related material.

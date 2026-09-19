# Prompt: Thiết kế toàn diện UI/UX NoteWise

Bạn là Chuyên gia UI/UX và Kiến trúc sư Frontend. Hãy thiết kế giao diện toàn diện cho NoteWise, hệ thống học tập cá nhân hóa dựa trên tài liệu bài giảng sinh viên tải lên.

## Triết lý

- Tóm tắt, quiz, analytics và recommendation phải gắn với nguồn tài liệu gốc.
- Không gian học sạch, tập trung, phù hợp sinh viên đại học và người tự học.
- Hiển thị rõ xử lý AI, loading, empty, ready, error/retry và confirmation dialog.
- Khi nguồn không đủ, AI phải nói rõ không thể trả lời chính xác, tuyệt đối không bịa.

## Global layout

Thiết kế sidebar có thể thu gọn với Logo/NoteWise, Dashboard, My Materials, Document Q&A, Quiz, Analytics & Weak Topics, Recommendations, Learning History; phía dưới có Profile, Settings, Logout. Top header gồm breadcrumb, global document selector, notification, AI processing status và user avatar. Main canvas hỗ trợ grid, card, split-screen và modal; responsive trên desktop/mobile.

## Bảy màn hình bắt buộc

1. **Auth:** card căn giữa, tab Đăng nhập/Đăng ký, Email, Mật khẩu, xác thực mật khẩu, inline error, show/hide password, loading button, protected-route security error.
2. **Materials:** upload button, search, subject/tag/status filters, grid/list toggle, drag-drop PDF/DOCX/PPTX, file limit, upload-processing-ready/failed progress, retry, quick menu và delete confirmation.
3. **Document Q&A:** 60/40 split, document selector, tabs tài liệu gốc/tóm tắt AI, bullets/formula/chips, chat, prompt, answer, page/section citation click để highlight, insufficient-evidence warning.
4. **Quiz:** setup modal với source, 5-20 questions, type, difficulty, optional topic, AI skeleton; player với progress/timer/document, topic/difficulty, options, previous/skip/submit/next; result score/time/correct-wrong, review, explanation/citation và actions.
5. **Analytics:** accuracy over time, completed quizzes, mastered documents, topic mastery bars/matrix, weak cards dưới 60%, priority reason, quick actions.
6. **Recommendations:** tiêu đề “Hành động học tập được đề xuất cho bạn”, context tag, explanation, source pages, open slide/5-question quiz CTAs và insufficient-data banner.
7. **Learning History:** filters time/document/activity/score/weak topic, table/timeline, clickable detail row and review drawer.

## Design tokens

Dùng Indigo `#4F46B5` làm primary, Purple `#7C5CFC` cho AI, Electric Teal `#0F9F95`, Mint success, Amber warning, Rose error, warm off-white canvas và Ink text. Dùng Be Vietnam Pro hoặc Inter; spacing 4/8/12/16/24/32/48px; radius 8/12/16px; subtle shadow; WCAG AA contrast; visible keyboard focus.

## Đầu ra

Trả về wireframe layout, component inventory, token table, interaction states và microcopy tiếng Việt cho cả bảy màn hình. Tạo HTML/Tailwind single-file concepts có thể mở trực tiếp và một prototype HTML/CSS/JS thuần mô phỏng các luồng chính.

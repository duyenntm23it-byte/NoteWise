# Prompt: Comprehensive NoteWise UI/UX Design

You are a UI/UX Expert and Frontend Architect. Design a comprehensive interface for NoteWise, a personalized learning system based on lecture materials uploaded by students.

## Philosophy

- Summaries, quizzes, analytics, and recommendations must be linked to the original source documents.
- The learning space should be clean, focused, and suitable for university students and self-learners.
- Clearly show AI processing, loading, empty, ready, error/retry, and confirmation-dialog states.
- When the source is insufficient, the AI must clearly state that it cannot answer accurately and must never fabricate information.

## Global Layout

Design a collapsible sidebar with Logo/NoteWise, Dashboard, My Materials, Document Q&A, Quiz, Analytics & Weak Topics, Recommendations, Learning History; place Profile, Settings, Logout. The top header includes breadcrumb, global document selector, notification, AI processing status và user avatar. The main canvas supports grid, card, split-screen và modal; responsive layouts on desktop/mobile.

## Seven Required Screens

1. **Auth:** card căn giữa, tab Sign In/Sign Up, Email, Password, xác thực mật khẩu, inline error, show/hide password, loading button, protected-route security error.
2. **Materials:** upload button, search, subject/tag/status filters, grid/list toggle, drag-drop PDF/DOCX/PPTX, file limit, upload-processing-ready/failed progress, retry, quick menu và delete confirmation.
3. **Document Q&A:** 60/40 split, document selector, tabs tài liệu gốc/tóm tắt AI, bullets/formula/chips, chat, prompt, answer, page/section citation click để highlight, insufficient-evidence warning.
4. **Quiz:** setup modal với source, 5-20 questions, type, difficulty, optional topic, AI skeleton; player với progress/timer/document, topic/difficulty, options, previous/skip/submit/next; result score/time/correct-wrong, review, explanation/citation và actions.
5. **Analytics:** accuracy over time, completed quizzes, mastered documents, topic mastery bars/matrix, weak cards dưới 60%, priority reason, quick actions.
6. **Recommendations:** tiêu đề “Learning Actions Recommended for You”, context tag, explanation, source pages, open slide/5-question quiz CTAs và insufficient-data banner.
7. **Learning History:** filters time/document/activity/score/weak topic, table/timeline, clickable detail row and review drawer.

## Design tokens

Dùng Indigo `#4F46B5` làm primary, Purple `#7C5CFC` cho AI, Electric Teal `#0F9F95`, Mint success, Amber warning, Rose error, warm off-white canvas và Ink text. Dùng Be Vietnam Pro hoặc Inter; spacing 4/8/12/16/24/32/48px; radius 8/12/16px; subtle shadow; WCAG AA contrast; visible keyboard focus.

## Output

Trả về wireframe layout, component inventory, token table, interaction states và microcopy tiếng Việt cho cả bảy màn hình. Tạo HTML/Tailwind single-file concepts có thể mở trực tiếp và một prototype HTML/CSS/JS thuần mô phỏng các luồng chính.

# Prompt: Comprehensive NoteWise UI/UX Design

You are a UI/UX Expert and Frontend Architect. Design a comprehensive interface for NoteWise, a personalized learning system based on lecture materials uploaded by students.

## Philosophy

- Summaries, quizzes, analytics, and recommendations must be linked to the original source documents.
- The learning space should be clean, focused, and suitable for university students and self-learners.
- Clearly show AI processing, loading, empty, ready, error/retry, and confirmation-dialog states.
- When the source is insufficient, the AI must clearly state that it cannot answer accurately and must never fabricate information.

## Global Layout

Design a collapsible sidebar with Logo/NoteWise, Dashboard, My Materials, Document Q&A, Quiz, Analytics & Weak Topics, Recommendations, and Learning History; place Profile, Settings, and Logout at the bottom.

The top header includes breadcrumbs, a global document selector, notifications, AI processing status, and the user avatar.

The main canvas supports grid, card, split-screen, and modal layouts and must be responsive on desktop and mobile.

## Seven Required Screens

### 1. Authentication

Centered card, Sign In/Sign Up tabs, Email, Password, password confirmation, inline errors, show/hide password, loading button, and protected-route security error.

### 2. Materials

Upload button, search, subject/tag/status filters, grid/list toggle, drag-and-drop PDF/DOCX/PPTX, file limit, upload-processing-ready/failed progress, retry, quick menu, and delete confirmation.

### 3. Document Q&A

60/40 split, document selector, Original Document/AI Summary tabs, bullets/formulas/chips, chat, prompt, answer, page/section citation that highlights the related passage, and insufficient-evidence warning.

### 4. Quiz

Setup modal with source, 5-20 questions, type, difficulty, optional topic, and AI skeleton; player with progress/timer/document, topic/difficulty, options, Previous/Skip/Submit/Next; result with score/time/correct-wrong, review, explanation/citation, and actions.

### 5. Analytics

Accuracy over time, completed quizzes, mastered documents, topic mastery bars/matrix, weak-topic cards below 60%, priority reason, and quick actions.

### 6. Recommendations

Title `Learning Actions Recommended for You`, context tag, explanation, source pages, Open Lecture Slides/Take 5-Question Review Quiz CTAs, and insufficient-data banner.

### 7. Learning History

Filters for time/document/activity/score/weak topic, table/timeline, clickable detail row, and review drawer.

## Design Tokens

Use Indigo `#4F46B5` as primary, Purple `#7C5CFC` for AI, Electric Teal `#0F9F95`, Mint success, Amber warning, Rose error, warm off-white canvas, and Ink text.

Use Be Vietnam Pro or Inter; spacing 4/8/12/16/24/32/48px; radius 8/12/16px; subtle shadow; WCAG AA contrast; and visible keyboard focus.

## Output

Return wireframe layouts, a component inventory, a token table, interaction states, and English microcopy for all seven screens.

Create HTML/Tailwind single-file concepts that can be opened directly and a pure HTML/CSS/JS prototype that simulates the main flows.

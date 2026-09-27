# NoteWise Product Design Brief

## 1. Overview and Design Philosophy

NoteWise is a personalized learning system based on lecture materials in PDF, DOCX, and PPTX formats. Learners upload materials, read summaries, ask questions with citations, generate quizzes, view weak topics, and receive next-step learning recommendations. All AI activities must be traceable to the original source documents; when the source is insufficient, the system must clearly state that it cannot answer rather than guess.

The experience is designed for university students and self-learners: clean, focused, low-distraction, with one clear primary action on each screen. Visual feedback is required for background AI processing, loading, empty, ready, error/retry, and destructive-action confirmation states.

## 2. Global Layout and Navigation

```text
┌ Collapsible Sidebar ┐ ┌ Top Header: breadcrumb | document | AI status | avatar ┐
│ NoteWise            │ ├────────────────────────────────────────────────────────┤
│ Dashboard           │ │ Main canvas: grid / card / split-screen / modal        │
│ My Materials        │ │                                                        │
│ Document Q&A        │ │                                                        │
│ Quiz                │ │                                                        │
│ Analytics           │ │                                                        │
│ Recommendations     │ │                                                        │
│ Learning History    │ │                                                        │
│ Profile / Setup     │ │                                                        │
└─────────────────────┘ └────────────────────────────────────────────────────────┘
```

The sidebar contains the NoteWise logo, Dashboard, My Materials, Document Q&A, Quiz, Analytics & Weak Topics, Recommendations, and Learning History. Profile, Settings, and Logout are placed at the bottom.

The top header contains breadcrumbs, a global document selector, AI status, notifications, and an avatar.

On mobile, the sidebar changes to a horizontal navigation bar or drawer.

## 3. Details of the 7 Screens

### Screen 1 - User Authentication

**Wireframe:** warm off-white canvas -> centered auth card -> logo -> `Sign In | Sign Up` tabs -> Email -> Password with show/hide control -> Confirm Password for registration -> inline validation -> primary submit -> security note.

Sign in includes email, password, forgot password, and `Signing in...` state.

Registration additionally includes password confirmation and `Creating account...` state.

Switching tabs must not lose unrelated input. Accessing an internal route while unauthenticated shows a clear error with `Sign in to continue`.

Focus rings must be visible for keyboard users.

### Screen 2 - My Materials

**Wireframe:** page header with `+ Upload Document`, search, Subject/Tag/Status filters, and grid/list toggle -> drag-and-drop zone -> document cards/list rows -> upload progress.

Support PDF, DOCX, and PPTX and display file-size limits.

Each document shows name, upload date, size, subject, progress, and a `Ready`, `Processing`, or `Failed` badge.

Failed documents always provide `Retry`.

Quick actions include View Summary, Q&A, Create Quiz, and Delete.

Deletion requires a confirmation dialog.

### Screen 3 - Document, Summary, and Q&A

**Wireframe:** 60/40 split screen -> left side document selector + `Original Document | AI Summary` tabs + reader/highlight/citation -> right side chat header + messages + composer.

The summary contains key-point bullets, formulas, and concept chips.

AI answers include content and citations such as:

`[Citation: Page 4, Section 2.1]`

Clicking a citation highlights the corresponding passage in the reader.

When the source does not address the question, show the banner:

`The document does not contain enough information to answer accurately`

and suggest alternative questions.

### Screen 4 - AI Quiz and Quiz Player

**Wireframe setup modal:** source document -> 5-20 questions -> question type MCQ/True-False/Fill-in-the-Blank -> difficulty -> optional topic -> `Create Quiz` -> AI skeleton.

The player includes `Question X/Y` progress, optional timer, document, question card, topic tag, difficulty badge, radio/checkbox answers, and Previous/Skip/Submit/Next navigation.

The result includes percentage, time, correct/incorrect answers, per-question review, selected/correct answers, collapsible AI explanations, citations, and actions for Retake, Analyze Weak Topics, and Save Result.

### Screen 5 - Analytics and Weak Topics

**Wireframe:** overview widgets -> accuracy line chart over time -> topic mastery bars/matrix -> weak-topic cards -> quick actions.

Widgets include overall accuracy, completed quizzes, and mastered documents.

Example mastery:

- Regression: 85%
- Classification: 78%
- Decision Trees: 42%

Topics below 60% receive a `High Priority` warning card, a reason based on the three most recent attempts, `Create Review Quiz`, and `Read Original Material`.

### Screen 6 - Personalized Learning Recommendations

**Wireframe:** title `Learning Actions Recommended for You` -> recommendation cards -> context tag -> explanation -> source pages -> CTA `Open Lecture Slides` / `Take 5-Question Review Quiz`.

Each recommendation explains why it was selected.

Example:

`You often answer questions about decision-tree pruning incorrectly. Review pages 12-15 and take a quick 5-question quiz.`

If there is not enough history, an empty/data-limited banner states:

`Complete more quizzes so the AI has enough data to provide more accurate recommendations.`

### Screen 7 - Learning History

**Wireframe:** page header -> filters by time, document, activity, score, and topic -> table/timeline -> clickable row -> detail drawer.

Each history row contains timestamp, document name, activity type Quiz/Summary/Q&A, score, duration, and detected weak topics.

Clicking a row reopens the quiz details or previous citation.

The empty state directs the user to `Start Learning`.

Loading uses skeleton rows, and errors provide `Retry`.

## 4. Design System Tokens

| Token | Value | Usage |
|---|---|---|
| Primary Indigo | `#4F46B5` | CTA, active navigation, focus |
| AI Purple | `#7C5CFC` | AI badge, recommendations, highlights |
| Electric Teal | `#0F9F95` | AI ready, positive insight |
| Mint Success | `#DDF7EA` / `#16845B` | Ready, correct |
| Amber Warning | `#FFF1C7` / `#A76500` | Processing, attention |
| Rose Error | `#FFE2E7` / `#B33A50` | Failed, validation |
| Warm Canvas | `#F7F7FB` | App background |
| Ink | `#20243A` | Primary text |
| Font | `Be Vietnam Pro`, fallback `Inter`, sans-serif | UI and body |
| Spacing | 4, 8, 12, 16, 24, 32, 48px | Consistent rhythm |
| Radius | 8px controls, 12px cards, 16px hero panels | Soft but restrained |
| Shadow | `0 12px 30px rgba(37,35,80,.07)` | Subtle elevation |

Typography:

- H1: 32/40 700
- H2: 22/30 700
- H3: 16/24 700
- Body: 14/22 400
- Caption: 12/18 500

Use WCAG AA contrast.

Buttons, inputs, and icon actions have visible `:focus-visible` rings and labels. State is never communicated by color alone.

## 5. UI States and Interactions

- **Loading/skeleton:** skeleton rows for data, progress for uploads, pulsing AI skeleton while creating a quiz; preserve the surrounding layout.
- **Empty:** simple illustration/icon, concise reason, and one CTA. Applies to no documents, no quiz history, and insufficient recommendation data.
- **Ready:** data, timestamp, source, next action, and status badge are visible.
- **Error/recovery:** inline error below the field or failed document row; explain the cause, retain input, and provide `Retry`.
- **Confirmation dialog:** required before deleting a document; name the document, state that the action is irreversible, and offer Cancel/Delete.
- **AI insufficient evidence:** never invent an answer; show the source limitation and link to related material.

# NoteWise product requirements

> **Provenance**
> - **Source prompts:** [P3.1 — Create product requirements](../prompts/create-product-requirements.prompt.md) and [P3.2 — Review product requirements](../prompts/review-product-requirements.prompt.md)
> - **Artifact status:** `Draft for review`
> - **Human action:** Scope and requirement corrections must be reviewed before acceptance.
> - **Reproduction note:** P3.2 produces findings; only accepted findings are reflected in the canonical PRD.

## Product Discovery

### Problem

Students have many digital lecture materials but often struggle to turn them into structured learning. They need to identify important concepts, prepare practice questions, understand their weak areas and decide what to study next.

Generic AI assistants can summarize or answer questions, but they do not necessarily connect the student's own materials with practice results, topic-level performance and personalized next actions.

### Target users

- University students.
- Students studying independently.
- Students preparing for exams.

### Product opportunity

NoteWise connects the student's own learning materials to a continuous learning loop:

```text
Materials → Analysis → Summary / Q&A / Quiz
→ Practice → Results → Performance Analysis
→ Weak Topics → Personalized Recommendation
→ Further Learning
```

### Goal

Enable students to transform their own learning materials into personalized learning activities and evidence-based next study actions.

## Functional requirements

### FR-01 — Manage learning documents

A student can upload, view and delete supported PDF, DOCX and PPTX learning documents.

**Acceptance criteria**
- Supported documents can be uploaded.
- Unsupported or invalid files are rejected with a clear message.
- Each document has a visible processing state.
- A student can access only their own documents.
- Deletion requires intentional confirmation.

### FR-02 — Process learning documents

The system processes an uploaded document into usable learning content.

**Acceptance criteria**
- Processing starts after a valid upload.
- The processing state is visible.
- Successful processing produces a `Ready` state.
- Failed processing produces a `Failed` state.
- A retry path is exposed when recovery is possible.

### FR-03 — Generate document summaries

A student can request a summary for a ready document.

**Acceptance criteria**
- Only a ready document can be summarized.
- The summary is based on the selected document.
- Main ideas and important concepts are presented.
- Invalid or empty AI output is not presented as a successful summary.

### FR-04 — Document-based Q&A

A student can ask a question about a ready document.

**Acceptance criteria**
- The question is associated with the selected document.
- Relevant document content is retrieved before answer generation.
- The answer is grounded in available document content.
- If evidence is insufficient, the system clearly says so.
- Source reference is shown where supported.

### FR-05 — Generate quizzes

A student can generate a quiz from a ready document.

**Acceptance criteria**
- The student selects a document.
- The student can configure question count, question type and difficulty.
- An optional topic can be selected.
- Generated questions are checked against source content.
- Invalid questions are rejected.
- A valid quiz is persisted.

### FR-06 — Complete and evaluate quizzes

A student can complete a generated quiz and submit an attempt.

**Acceptance criteria**
- Answers are captured.
- The score is calculated consistently.
- Correct/incorrect results are available.
- The attempt and result are persisted.
- The result is available for later performance analysis.

### FR-07 — Analyze learning performance

The system analyzes quiz performance at overall and topic level.

**Acceptance criteria**
- Overall performance is visible.
- Topic-level performance is available when sufficient data exists.
- Repeated attempts can be compared.
- Insufficient data is communicated instead of presenting false certainty.

### FR-08 — Identify weak topics

The system identifies topics requiring additional attention using learning evidence.

**Acceptance criteria**
- Topic-level evidence is considered.
- Recent or repeated performance can be considered.
- One incorrect answer alone does not define a weak topic.
- The student can understand why a topic requires attention.

### FR-09 — Personalized learning recommendation

The system recommends next learning actions based on the student's performance and available materials.

**Acceptance criteria**
- Quiz results and topic performance are considered.
- Learning history can influence the recommendation.
- Relevant available materials are linked where possible.
- The reason for the recommendation is displayed.
- The system does not fabricate unavailable materials.
- The student remains in control of the next action.

### FR-10 — Learning history

A student can review previous learning activities and results.

**Acceptance criteria**
- Quiz attempts and scores are persisted.
- Relevant topics are visible.
- History supports performance analysis.
- History can support later personalized recommendations.

## Non-functional expectations

- **Security:** students can access only their own learning records.
- **Reliability:** processing and AI failures are visible and recoverable where possible.
- **Usability:** primary learning actions and system states are understandable.
- **Performance:** long-running document/AI processing exposes progress or state rather than appearing frozen.
- **Maintainability:** product workflow, AI assistance, analytics and persistence remain separable.
- **Scalability:** the system can support additional learning documents and activities without changing the core learning model.

## Business and AI boundaries

The application, not the AI service, controls:
- document ownership,
- source selection,
- document processing state,
- content retrieval,
- AI-output validation,
- quiz configuration,
- quiz evaluation,
- persistence,
- performance analysis,
- weak-topic logic,
- recommendation logic,
- recovery.

AI must be grounded in the student's available learning materials. When evidence is insufficient, the product must communicate the limitation rather than inventing an answer.

## Requirements analysis

### Prioritization

**Must have**
- Document upload and processing.
- Summary.
- Document-based Q&A.
- Quiz generation.
- Quiz evaluation and persistence.
- Topic-level performance analysis.
- Weak-topic detection.
- Personalized recommendation.

**Should have**
- Rich learning history.
- Repeated-attempt comparison.
- Source references for supported Q&A responses.

### Dependencies

- Document content extraction.
- Persistent storage.
- AI assistance for summary/Q&A/quiz generation.
- Quiz evaluation.
- Topic performance calculation.
- Recommendation logic.

### Constraints

- Documents may contain insufficient extractable information.
- AI output may be incomplete or invalid.
- Recommendations depend on available student evidence and materials.
- Processing time can vary by document size and system load.

### Risks

| Risk | Impact | Response |
|---|---|---|
| Invalid AI output | Incorrect learning content | Validate before display or persistence |
| Insufficient document evidence | Unsupported answer | Show an insufficient-information state |
| Weak-topic misclassification | Poor recommendation | Use topic-level/repeated evidence |
| No relevant material | Weak next action | Recommend only available supported materials |
| Unauthorized access | Privacy issue | Enforce ownership and authorization |

## User stories & acceptance criteria

### US-01 — Upload learning material

**As a student, I want to upload my lecture material so that I can study from my own documents.**

**Acceptance criteria**
- Supported files can be uploaded.
- Unsupported files are rejected.
- Processing state is visible.
- The document belongs to the current student.

### US-02 — Understand learning material

**As a student, I want to view and manage my documents so that I can find useful learning material quickly.**

**Acceptance criteria**
- Owned documents are listed.
- Processing state is visible.
- A document can be deleted after confirmation.

### US-03 — View a summary

**As a student, I want to view a summary so that I can understand important concepts faster.**

**Acceptance criteria**
- A ready document is required.
- Summary content comes from the selected document.
- Invalid output is not presented as a valid summary.

### US-04 — Ask questions about a document

**As a student, I want to ask questions about my document so that I can clarify difficult content.**

**Acceptance criteria**
- The question is tied to a selected document.
- Relevant source content is used.
- Insufficient evidence is communicated.

### US-05 — Generate a quiz

**As a student, I want to generate a quiz from my material so that I can practice what I learned.**

**Acceptance criteria**
- Quiz configuration is available.
- Questions are related to the source material.
- Invalid generated questions are rejected.
- A valid quiz is stored.

### US-06 — Complete a quiz

**As a student, I want to complete a quiz and see my result so that I can evaluate my understanding.**

**Acceptance criteria**
- Answers are captured.
- Score is calculated.
- Result is stored.
- Result can be used in later analysis.

### US-07 — Understand performance

**As a student, I want to see my performance by topic so that I know where I need more practice.**

**Acceptance criteria**
- Topic performance is displayed when sufficient data exists.
- Repeated attempts can be compared.
- A single wrong answer does not automatically create a weak-topic classification.

### US-08 — Receive a personalized recommendation

**As a student, I want a recommendation based on my learning results so that I know what to study next.**

**Acceptance criteria**
- Recommendation uses student-specific evidence.
- The reason is displayed.
- Available relevant material is linked where possible.
- The student can choose whether to follow it.

### US-09 — Review learning history

**As a student, I want to review my learning history so that I can track my learning over time.**

**Acceptance criteria**
- Previous attempts and scores are visible.
- Relevant topics are visible.
- History supports later personalization.

## Non-goals

The current release does not include:
- teacher/admin management,
- social or collaborative learning,
- general-purpose chatbot functionality unrelated to the student's learning materials,
- guaranteed exam-score improvement,
- fabricated learning materials,
- uncontrolled AI recommendations,
- unsupported integrations or features not approved in project context.

## Acceptance signals

The main learning path is:

```text
Upload material
→ process successfully
→ view summary / ask Q&A
→ generate quiz
→ complete quiz
→ persist result
→ analyze topic performance
→ identify attention topics
→ receive an explained recommendation
→ continue learning
```

A successful product outcome is observable through document processing success, quiz completion, persisted results, recommendation usage and changes in topic-level performance across repeated attempts. These are product signals, not guarantees of academic improvement.

## Review status

`Draft for review`

P3.2 findings must be accepted, rejected or deferred by the human reviewer before the canonical PRD is marked `Accepted`.

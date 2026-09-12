# NoteWise feature specification

> **Provenance**
> - **Source prompt:** [P3.3 — Create feature specification](../prompts/create-feature-specification.prompt.md)
> - **Artifact status:** `Draft for review`
> - **Human action:** Approve success, failure, recovery, persistence, authorization and validation behavior before acceptance.
> - **Reproduction note:** This artifact is created only after the PRD review gate passes.

## Document lifecycle

A student uploads a supported learning document.

```text
Select File
   ↓
Validate
   ↓
Create Document
   ↓
Processing
   ↓
Ready / Failed
```

A document is associated with its owner. The student can view only owned documents.

### Success

After successful processing, the document becomes `Ready` and learning actions become available.

### Failure

If processing fails, the document becomes `Failed`, the failure state is visible and a retry path is provided when recovery is possible.

### Persistence

Document metadata, owner and processing state survive reload.

### Destructive action

Deleting a document requires intentional confirmation. Deleted content is no longer available through normal learning flows.

## Document summarization

### Main flow

```text
Select Ready Document
→ Request Summary
→ Retrieve Document Content
→ Generate Summary
→ Validate Output
→ Display Summary
```

### Rules

- Only a `Ready` document can be summarized.
- The selected document is the source.
- Empty or structurally invalid AI output is rejected.
- Unsupported information is not presented as a document fact.

### Failure/recovery

If generation fails, show a clear failure state and provide retry when possible. The document remains available.

## Document-based Q&A

### Main flow

```text
Select Ready Document
→ Enter Question
→ Retrieve Relevant Content
→ Generate Answer
→ Check Evidence
→ Display Answer
```

### Alternative flow

If the available content is insufficient, the system tells the student that the answer cannot be established from the current material instead of fabricating a response.

### Rules

- The question belongs to the selected document.
- Relevant content is retrieved before answer generation.
- Answers are grounded in available source content.
- Source references are shown where supported.

## Quiz generation

### Main flow

```text
Select Ready Document
→ Configure Quiz
→ Retrieve Content
→ Identify Relevant Topics
→ Generate Questions
→ Validate Questions
→ Create Quiz
```

### Inputs

- Document ID.
- Question count.
- Question type.
- Difficulty.
- Optional topic.

### Question data

A generated question contains, where applicable:
- question text,
- type,
- options,
- intended correct answer,
- explanation,
- topic,
- difficulty,
- source document association.

### Validation

A question is rejected when:
- question text is empty,
- options are invalid,
- there is no intended correct answer where required,
- it is unrelated to source content,
- required fields are missing,
- AI output does not match the expected structure.

Only valid questions can become part of a persisted quiz.

### Failure/recovery

If document content is insufficient, explain that a quiz cannot be generated reliably.

If AI generation fails, show a failure state and provide retry when possible.

If generated output fails validation, do not expose it as a valid quiz. Allow a safe retry path.

## Quiz completion and evaluation

### Main flow

```text
Open Quiz
→ Answer Questions
→ Submit
→ Evaluate
→ Store Attempt and Result
→ Display Result
```

### Persistence

The system stores the attempt, answers, score and relevant topic information so the result can later be used by performance analysis.

### Failure behavior

If result persistence fails, the system must not falsely report that the attempt was permanently saved. The student should receive a clear failure state and a safe retry path where possible.

## Learning performance analysis

### Main flow

```text
Quiz Results
→ Group Results by Topic
→ Calculate Performance
→ Compare Available Attempts
→ Identify Topics Requiring Attention
→ Display Performance
```

### Rules

- Overall performance is available from persisted results.
- Topic-level performance requires sufficient topic evidence.
- Repeated attempts may be compared.
- One incorrect answer alone does not define a weak topic.
- Insufficient evidence is communicated.

## Weak-topic detection

A topic requires attention when available evidence shows lower or consistently weak performance relative to the student's other available evidence.

Example:

```text
Regression       85%
Classification   78%
Decision Tree    42%
Clustering       55%
```

Possible result:

```text
Priority: High
Topic: Decision Tree
Why: Recent performance is lower than the student's performance on other topics.
```

The system must not claim certainty when the available evidence is insufficient.

## Personalized learning recommendation

### Main flow

```text
Quiz Results
→ Group by Topic
→ Calculate Performance
→ Analyze Learning History
→ Identify Topics Requiring Attention
→ Find Relevant Available Materials
→ Generate Recommendation
→ Explain Recommendation
→ Display Study Action
```

### Recommendation example

```text
Priority: High
Topic: Decision Tree
Why: Recent performance is lower than the student's performance on other topics.
Suggested next action: Review the relevant material and take a new quiz focused on Decision Tree.
```

### Rules

- Recommendation uses student-specific evidence.
- Quiz results and topic performance are considered.
- Learning history may influence priority.
- Relevant available materials are linked where possible.
- The reason is visible.
- Unavailable materials are never fabricated.
- Insufficient data produces an explicit limitation.
- The student remains in control of the next action.

## Learning history

Learning history includes, where applicable:
- uploaded learning documents,
- quiz attempts,
- scores,
- topics,
- performance information,
- learning actions and recommendations.

History persists across reload and supports later analysis and personalization.

## Authorization

- Protected learning features require an authenticated student session.
- A student can access only their own documents and learning records.
- Unauthorized access is rejected without exposing protected data.
- Ownership is enforced for document-based Q&A, summaries, quizzes, results and history.

## Required UI states

Design must account for:
- loading,
- empty state,
- ready/success state,
- validation error,
- processing failure,
- retry/recovery,
- insufficient information,
- unauthorized access,
- invalid AI output,
- destructive-action confirmation.

The visual design remains open; this specification defines behavior, not a fixed visual style.

## Terminology

The product consistently uses:
- **learning material/document** for uploaded source files,
- **quiz** for a generated practice set,
- **attempt** for one student submission,
- **result** for evaluated quiz outcome,
- **topic** for a learning subject area,
- **recommendation** for a proposed next learning action.

## Review status

`Draft for review`

Before acceptance, confirm success, failure, recovery, persistence, authorization, validation and destructive-action behavior with the human reviewer.

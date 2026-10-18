---
name: quiz-engine
description: "Design or implement grounded quiz generation from user documents, typed question schemas, answer validation, and automatic scoring for a learning application."
---

# Quiz Engine

## When to Use
- Generating multiple-choice or other supported quiz questions from notes or uploaded documents.
- Implementing quiz schemas, answer submission, automatic grading, or score summaries.
- Improving question quality, source grounding, or quiz-generation tests.

## Procedure
1. Inspect existing quiz routes, domain models, schemas, document/RAG retrieval, and scoring behavior before adding a parallel implementation.
2. Define explicit schemas for generated questions, choices, correct-answer representation, source references, submissions, and results. Validate choice counts, unique identifiers, answer membership, and score bounds.
3. Select source passages from the learner's authorized documents. Generate questions only from that evidence; retain document and page/slide references for every question.
4. Request unambiguous questions with one defensible correct answer, plausible but incorrect distractors, and explanations grounded in the cited source. Reject or regenerate malformed or unsupported model output; never silently accept invalid content.
5. Separate generation from grading. Grade submitted choice identifiers against the stored answer key on the server; do not trust client-supplied correct answers, per-question scores, or totals.
6. Define scoring rules explicitly, including unanswered items and any supported partial credit. Calculate totals deterministically and validate the result range.
7. Persist quiz attempts and answers using explicit SQLAlchemy session transactions. Keep transaction ownership consistent with the calling service and avoid exposing answer keys before submission.
8. Add tests for valid generation, malformed output, unsupported claims, answer tampering, correct/incorrect/unanswered responses, and score calculation. Run focused tests and backend checks.

## Quality and Safety
- Keep generated questions attributable to source passages; do not fabricate citations or claim coverage beyond available material.
- Respect document access controls during retrieval and result display.
- Do not log answer keys, private source content, or credentials unnecessarily.

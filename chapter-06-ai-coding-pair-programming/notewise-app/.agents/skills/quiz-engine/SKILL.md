---
name: quiz-engine
description: "Design or implement grounded quiz generation from user documents with Google Gemini, typed question schemas, answer validation, and automatic scoring for a learning application."
---

# Quiz Engine

## When to Use

- Generating multiple-choice or other supported quiz questions from notes or uploaded documents.
- Implementing quiz schemas, answer submission, automatic grading, or score summaries.
- Improving question quality, source grounding, or quiz-generation tests.

## Project Stack Overrides

- LLM calls use Google Gemini through `google-genai` and `GOOGLE_API_KEY`, following `GeminiAnswerService` in `backend/app/services/rag.py`. Reuse `CHAT_MODEL` and the `AnswerService*` error classes. Do not use OpenAI or LangChain.
- Use Gemini JSON mode: `GenerateContentConfig(response_mime_type="application/json", response_schema=<Pydantic model>)`, then validate the parsed result again on the server.
- Free-tier quota is small: one LLM call per quiz generation, plus at most one regeneration when the output is invalid.
- Quiz generation covers a whole document, so select chunks ordered by `chunk_index`, spread evenly across the document and capped by total length. Do not use top-k vector search for this.
- Write the quiz in the same language as the source document.

## Procedure

1. Inspect existing quiz routes, domain models, schemas, document/RAG retrieval, and scoring behavior before adding a parallel implementation.
2. Define explicit schemas for generated questions, choices, correct-answer representation, source references, submissions, and results. Choices are identified by index 0-3. Validate choice counts, unique choices, answer membership, and score bounds.
3. Select source passages from the learner's authorized documents (owned by the current user and in `ready` status). Generate questions only from that evidence. Ask the model to name the numbered excerpt each question is based on, and store the resulting `source_chunk_index` and `source_page_number` with every question.
4. Request unambiguous questions with one defensible correct answer, plausible but incorrect distractors, and explanations grounded in the cited source. Reject or regenerate malformed or unsupported model output (wrong question count, not exactly 4 distinct choices, correct index outside 0-3, duplicate questions, unknown source number); never silently accept invalid content.
5. Separate generation from grading. Grade submitted choice indexes against the stored answer key on the server; do not trust client-supplied correct answers, per-question scores, or totals.
6. Define scoring rules explicitly: one point per correct answer, unanswered items count as incorrect, no partial credit. Calculate totals deterministically and validate the result range.
7. Persist quiz attempts and answers using explicit SQLAlchemy session transactions. Keep transaction ownership consistent with the calling service. Never expose answer keys or explanations in any response before submission.
8. Add tests for valid generation, malformed output, unsupported source references, answer tampering, correct/incorrect/unanswered responses, and score calculation. Use fake generators through dependency overrides; never call Gemini in tests. Run focused tests and backend checks.

## Quality and Safety

- Keep generated questions attributable to source passages; do not fabricate citations or claim coverage beyond available material.
- Respect document access controls during retrieval and result display.
- Do not log answer keys, private source content, or credentials unnecessarily.

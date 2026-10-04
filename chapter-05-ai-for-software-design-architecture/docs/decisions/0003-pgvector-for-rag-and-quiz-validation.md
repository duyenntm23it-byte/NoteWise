# ADR 0003: PostgreSQL with pgvector for RAG and Quiz Validation

- **Status:** Accepted
- **Date:** 2026-10-04
- **Decision owners:** NoteWise architecture

## Context

Document Q&A and generated quizzes must be grounded in user-owned documents.
The application also stores document ownership, lifecycle state, chunks,
citations, quiz data, and learning activity. An external vector database
would add another service and another consistency/authorization boundary to
the MVP.

AI generation is not trusted evidence. Q&A must return `insufficient_evidence`
when retrieval cannot support an answer. Quiz generation uses a second
validation step before questions are made available to the learner.

## Decision

- Store document chunks and embeddings in PostgreSQL using pgvector.
- Use one configured embedding model and fixed vector dimension per schema
  version. A model/dimension change requires a versioned migration and
  re-embedding plan.
- Every retrieval query constrains `user_id`, selected `document_id`, and
  document state `READY`; retrieval never searches another user's content or
  a document being processed/deleted.
- Persist citations against retrieved chunk IDs and source page/section
  metadata. Verify citation IDs are a subset of retrieved evidence before
  returning generated output.
- Q&A with no supporting retrieved evidence returns an explicit
  `insufficient_evidence` outcome, no answer, and no citation.
- Quiz generation persists no quiz as `READY` until the validation step
  confirms schema, answer/explanation consistency, and citation grounding.
- Keep answer keys server-only; public quiz and attempt APIs return question
  content without answer keys.
- An AI timeout, provider outage, malformed output, or failed evidence
  validation is an explicit error or `FAILED` job state, not a fabricated
  success response.

## Consequences

### Positive

- Vectors and authorization metadata share one transactional database.
- Backups, migrations, and owner filters have fewer infrastructure boundaries.
- Citation validation and quiz persistence can be coordinated with ordinary
  database transactions.

### Negative

- Vector search competes with application transactions for PostgreSQL
  resources.
- Embedding dimension and model changes require explicit data migration.
- Provider quality and availability remain external dependencies.

## Revisit when

Load tests show vector-search resource contention or latency that cannot be
addressed by indexing, query tuning, and capacity changes; or an operational
requirement calls for independent vector-store scaling. Any replacement must
preserve owner-scoped retrieval and citation validation.

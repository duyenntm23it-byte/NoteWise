# NoteWise Software Architecture

**Status:** Approved design baseline
**Scope:** FR-01 through FR-11
**Target:** Next.js static SPA, FastAPI modular monolith, PostgreSQL + pgvector, Docker Compose

## 1. Architecture at a glance

NoteWise is a single-page learning application backed by a modular FastAPI
application. PostgreSQL stores account data, application records, processing
jobs, and document embeddings. Uploaded source files live in a persistent local
volume mounted by the API container. The API is the sole authority for
authentication, resource ownership, document processing state, and AI output
validation.

The browser is an untrusted client. It stores the short-lived JWT access token
in Local Storage as required by the target constraints and sends it as a Bearer
token. It never supplies an authoritative owner ID. The API derives `user_id`
from the verified token and scopes every resource query to that identity.

The AI provider is an external dependency, not a source of truth. Retrieval is
restricted to ready documents owned by the authenticated user. Generated
answers and quiz questions are validated against retrieved chunks before
publication. Provider errors and unsupported evidence remain explicit API
outcomes.

## 2. System context

See [system-context.mmd](./system-context.mmd).

### Runtime boundaries

- **Web client:** Next.js, TypeScript, Tailwind CSS, static export. Handles
  presentation, client-side navigation, and API calls only.
- **API:** FastAPI modular monolith. Owns validation, authorization,
  orchestration, persistence, retrieval, and response shaping.
- **PostgreSQL + pgvector:** Durable application data, job leases, and vector
  search. Every retrieval query filters by authenticated owner and document
  state.
- **File volume:** Persistent Docker volume accessible only to the API.
  Database rows store opaque storage keys, not client-provided filesystem paths.
- **AI provider:** Embedding and generation calls. Provider output is
  untrusted until validated. No provider receives another user's content.

The Compose MVP contains `frontend`, `api`, and `postgres`; the API runs a
database-backed job loop in its own process. There is no broker or separately
deployed worker in this scope.

## 3. Backend module boundaries

| Module | Owns | May depend on |
|---|---|---|
| `auth` | Registration, password hashing, login, JWT verification, current-user dependency | shared database and settings |
| `documents` | Upload validation, file storage adapter, ingestion, chunks, document state, retry and delete | `auth`, shared database, AI adapters |
| `learning` | Summaries, document Q&A, quiz generation/validation/player/submission | `auth`, `documents`, AI adapters |
| `analytics` | Accuracy, weak-topic calculation, recommendations, learning history | `auth`, `learning`, `documents` read interfaces |
| `jobs` | Durable job claiming, leases, retries, recovery and task dispatch | module service interfaces, shared database |
| `ai` | Embedding/generation provider adapters and output validation contracts | settings only; no direct ownership decisions |

Modules expose service functions and schemas rather than importing each other's
repositories. The API remains one deployable unit and one database transaction
boundary. Cross-module work is initiated through application services or
persisted jobs.

## 4. Architecture trade-offs

### Modular monolith rather than microservices

The current requirements do not justify independent service deployment. A
modular monolith reduces operational components, network failure modes, and
cross-service consistency work while preserving explicit domain boundaries.
Service extraction remains possible if independent scaling or team ownership
becomes a measured requirement.

### pgvector rather than an external vector database

Document metadata, owner IDs, lifecycle state, chunks, and embeddings remain
co-located in PostgreSQL. This simplifies backups and makes owner/state filters
part of the same retrieval query. The trade-off is shared database capacity for
transactional and vector workloads. Reconsider a separate vector store only
after retrieval latency or database resource measurements justify it.

### Database-backed jobs rather than a message broker

Document ingestion, summary generation, quiz generation, and deletion cleanup
are represented in `processing_jobs`. The API job loop claims rows inside a
short transaction using `FOR UPDATE SKIP LOCKED`, sets a lease, and performs
work outside the claim transaction. This keeps the MVP to the approved three
Compose services while making work durable across API restarts.

On startup and during polling, expired `RUNNING` leases become retryable. A
worker may claim a job only while its owner resource is still eligible and its
lease is current. Job handlers are idempotent: writes use stable resource/job
IDs and transactions; file writes use generated storage keys and replace
partial output safely. Retries use bounded exponential backoff and a maximum
attempt count. Exhausted jobs end in `FAILED` and retain a safe error code.

### Persistent local file volume

The MVP stores source files in a named Docker volume. The API generates storage
keys and never uses an uploaded filename as a path. A storage adapter isolates
the filesystem implementation so object storage can be introduced later
without changing domain/API contracts.

## 5. Data model and ownership invariants

See [data-model.mmd](./data-model.mmd) for the ERD. The model includes the
required entities plus `processing_jobs` for recoverable asynchronous work and
`learning_history` for durable activity snapshots.

### Ownership enforcement

1. `users.id` is the root ownership key. The API obtains it only from the
   verified JWT `sub` claim.
2. User-owned tables carry `user_id`. Unique keys `(id, user_id)` support
   composite foreign keys from child resources.
3. Children use composite ownership references: chunks to
   `(documents.id, documents.user_id)`, summaries/quizzes to documents and
   owners, questions to quizzes and owners, and answers to their attempt and
   question within the same quiz and owner.
4. Every API query still applies `user_id = current_user.id`; database
   constraints are a second line of defense, not a replacement for
   authorization.
5. An identifier belonging to another user returns `404 NOT_FOUND`, avoiding
   resource-existence disclosure. A valid owned resource in an invalid state
   returns `409 STATE_CONFLICT`.

### Important constraints

- `documents.status` is one of `PROCESSING`, `READY`, `FAILED`, `DELETING`,
  `DELETED`. Allowed transitions:
  `PROCESSING -> READY | FAILED | DELETING`,
  `FAILED -> PROCESSING | DELETING`,
  `READY -> DELETING`,
  `DELETING -> DELETED`. `DELETED` is terminal.
- `summaries.status` and `quizzes.status` are one of `QUEUED`, `PROCESSING`,
  `READY`, `FAILED`, `DELETED`. Allowed transitions:
  `QUEUED -> PROCESSING | DELETED`,
  `PROCESSING -> READY | FAILED | DELETED`,
  `READY -> DELETED`,
  `FAILED -> DELETED`. `DELETED` is terminal; generation failures require
  creating a new resource/job rather than mutating a failed result.
- `processing_jobs.status` is one of `QUEUED`, `RUNNING`, `RETRY_WAIT`,
  `SUCCEEDED`, `FAILED`, `CANCELLED`. Allowed transitions:
  `QUEUED -> RUNNING | CANCELLED`,
  `RUNNING -> SUCCEEDED | RETRY_WAIT | FAILED | CANCELLED`,
  `RETRY_WAIT -> RUNNING | CANCELLED`. Expired `RUNNING` leases are recovered
  to `RETRY_WAIT` (or `FAILED` when attempts are exhausted). Terminal states
  do not transition.
- A quiz attempt transitions once from `IN_PROGRESS` to `SUBMITTED`; submission
  and grading are atomic, and `SUBMITTED` is terminal.
- Unique constraints: `(document_id, chunk_index)`,
  `(quiz_id, position)`, `(attempt_id, question_id)`, and a unique non-null
  `(user_id, idempotency_key)` for job-producing requests.
- `document_chunks.embedding` uses one configured embedding model and fixed
  vector dimension per schema version. Changing model/dimension requires an
  explicit re-embedding migration.
- `quiz_questions.answer_key` and grading rubrics are server-only. They are
  never part of quiz, attempt, or question-list response schemas.
- `learning_history` contains display-safe snapshots (activity, title, score,
  timestamps) and never stores source-file contents or private answer keys.

### Document deletion and data retention

`DELETE /documents/{id}` immediately changes the owned document to
`DELETING`, hides it from normal document lists, cancels queued work, and
enqueues an idempotent cleanup job. The cleanup removes the source file,
embeddings/chunks, summary content, quiz questions, and submitted answer
details. It marks associated summaries/quizzes `DELETED`, preserves only
aggregate quiz-attempt results, and changes the document to `DELETED`.

The document row is retained as an owner-scoped tombstone so historical
references and audit records remain coherent. `learning_history` retains
non-content snapshots for the owner's history. Deleted content is not
retrievable, shown as a document, or sent to an AI provider. A repeated delete
is idempotent. The cleanup job reports failure for retry/operations; the API
does not claim file removal until cleanup succeeds.

## 6. Document and AI workflows

### Ingestion

1. Verify JWT, multipart size, extension and detected file type; enforce the
   configured limit and reject malformed/unsupported input.
2. In a transaction, create an owner-scoped `PROCESSING` document and
   `QUEUED` ingestion job. Return `202 Accepted` with resource and job IDs.
3. The job stores the uploaded file under an API-generated key, extracts
   content, chunks it, creates embeddings, and writes chunks/embeddings
   transactionally in bounded batches.
4. Mark `READY` only after usable chunks are committed. On a terminal
   extraction/embedding failure, mark `FAILED` with a safe reason code.
5. Retry creates/requeues a bounded job for an owned `FAILED` document. A
   duplicate idempotency key returns the original job outcome.

### Summary and document Q&A

- A summary job is allowed only for an owned `READY` document. The response
  remains `QUEUED`/`PROCESSING` until its status endpoint returns `READY` or
  `FAILED`.
- Q&A retrieves a bounded set of chunks for the selected owned `READY`
  document. The retrieval query includes both `user_id` and `document_id`.
- The API validates the generated answer shape and checks that each citation
  references a retrieved chunk. An unsupported question returns
  `insufficient_evidence` with no answer and no fabricated citations.
- Provider timeout/unavailability returns an explicit `AI_PROVIDER_UNAVAILABLE`
  or `AI_TIMEOUT`; malformed output returns `AI_OUTPUT_INVALID`. No
  success-shaped fallback is returned.

### Quiz generation, validation, and evaluation

1. Generate questions from retrieved chunks for an owned `READY` document.
2. Validate count, types, answer key, explanation, and citation grounding
   before persisting a quiz as `READY`. Invalid output is rejected; no
   unvalidated quiz is served.
3. `GET /quizzes/{id}` and `POST /quiz-attempts` return only public question
   fields (prompt/options/citation), never `answer_key`.
4. Submit accepts one answer per question at most. Server-side grading,
   correct count, score, skipped count, attempt, answers, and history event are
   written atomically. An identical duplicate submit returns the
   already-finalized result; a different payload after submission returns
   `409 ALREADY_SUBMITTED`. Neither creates a second attempt result.
5. After at least two submitted attempts for a topic, weak-topic analytics
   use accuracy over all non-skipped answers in the selected analysis window.
   A topic is weak below 60%. Skipped questions are excluded from the accuracy
   denominator and reported separately. Fewer than two attempts means
   `sufficient_data: false`; it is not labeled weak.

## 7. API strategy

All routes use `/api/v1`. JSON uses snake_case. Uploads use multipart
`multipart/form-data`. Protected routes require `Authorization: Bearer
<access_token>`, except registration and login. The complete operation and
schema contract is [openapi.yaml](./openapi.yaml).

| Requirement | API operations |
|---|---|
| FR-01 Auth | `POST /auth/register`, `POST /auth/login`, `GET /me` |
| FR-02/03 Documents | `POST/GET /documents`, `GET/DELETE /documents/{id}`, `POST /documents/{id}/retry` |
| FR-04 Summary | `POST /documents/{id}/summaries`, `GET /summaries/{id}` |
| FR-05 Q&A | `POST /documents/{id}/questions` |
| FR-06/07 Quiz | `POST /documents/{id}/quizzes`, `GET /quizzes/{id}`, `POST /quizzes/{id}/attempts`, `GET /quiz-attempts/{id}`, `POST /quiz-attempts/{id}/submit` |
| FR-08/09 Analytics | `GET /analytics/accuracy`, `GET /analytics/weak-topics` |
| FR-10 Recommendations | `GET /recommendations` |
| FR-11 History | `GET /learning-history` |

### Common error contract

Errors use `{"error":{"code":"...","message":"...","details":{},"request_id":"..."}}`.
`details` is optional and contains safe field-level validation information,
never stack traces, provider credentials, prompts, or another user's data.

| HTTP | Example codes | Use |
|---|---|---|
| 400 | `INVALID_REQUEST` | Malformed request not covered by schema validation |
| 401 | `UNAUTHENTICATED`, `TOKEN_EXPIRED`, `TOKEN_INVALID` | Missing or invalid Bearer token |
| 404 | `NOT_FOUND` | Missing or not-owned resource |
| 409 | `STATE_CONFLICT`, `ALREADY_SUBMITTED`, `IDEMPOTENCY_CONFLICT` | Owned resource cannot perform requested transition |
| 413 | `FILE_TOO_LARGE` | Upload exceeds configured size limit |
| 415 | `UNSUPPORTED_FILE_TYPE` | File type not supported or detected type does not match |
| 422 | `VALIDATION_ERROR` | Request fields fail schema validation |
| 429 | `RATE_LIMITED` | Per-user operation limit reached |
| 502 | `AI_OUTPUT_INVALID`, `AI_VALIDATION_FAILED` | Provider output fails required schema/evidence checks |
| 503 | `AI_PROVIDER_UNAVAILABLE`, `PROCESSING_UNAVAILABLE` | Dependency or processing capacity unavailable |
| 504 | `AI_TIMEOUT` | Provider call exceeded its deadline |

## 8. Authentication and security

- Passwords are hashed with Argon2id (or the maintained framework
  recommendation selected at implementation); plaintext passwords are never
  logged or persisted.
- JWT access tokens include `sub` (user UUID), `iss`, `aud`, `iat`, `exp`, and
  `jti`; signing keys come from deployment secrets, never source control.
- MVP access-token lifetime is 15 minutes. No refresh-token endpoint is in
  scope; expiration requires login again. Logout removes the client token.
- Local Storage has an accepted XSS exposure. Mitigations required before
  production include strict Content Security Policy, output escaping, no
  unsafe inline script, dependency review, HTTPS, and short token lifetime.
  Revisit HttpOnly secure cookies if the client/deployment constraints permit.
- Apply upload size limits, MIME plus signature checks, generated storage
  names, safe extraction limits, and protection against archive/path traversal
  and decompression bombs.
- Do not log JWTs, uploaded content, prompts containing document text, answer
  keys, or raw provider responses. Correlate logs with request/job IDs and safe
  error codes.

## 9. Deployment and operations

Docker Compose services:

1. `frontend`: Next.js static export served as SPA assets.
2. `api`: FastAPI application plus database-backed job loop.
3. `postgres`: PostgreSQL with pgvector extension and named persistent volume.

The API waits for database readiness, applies versioned migrations, and checks
the pgvector extension before accepting traffic. Readiness includes database
connectivity and job-loop health; liveness does not depend on an AI provider.
Secrets and provider keys are injected through environment/secret management.
Database and file-volume backups must be coordinated; restore procedures must
preserve storage keys and document metadata consistency.

## 10. Requirement traceability

| FR | Architecture element | Acceptance evidence |
|---|---|---|
| FR-01 | `auth`, JWT, `users` | Register/login/current-user operations; protected routes derive owner from token |
| FR-02 | `documents`, `processing_jobs` | Upload creates `PROCESSING` resource and durable job; status reaches `READY` or `FAILED` |
| FR-03 | `documents`, cleanup/retry jobs | Retry owned failure; delete hides content and cleans storage idempotently |
| FR-04 | `summaries`, `processing_jobs` | Summary lifecycle endpoint; only owned ready document accepted |
| FR-05 | RAG Q&A and citation schemas | Citations resolve to retrieved chunks; no evidence returns `insufficient_evidence` |
| FR-06 | Quiz setup/generation and validation | Only validated, cited questions become `READY` |
| FR-07 | Quiz attempts/answers | Public response excludes answer keys; submit grades server-side once |
| FR-08 | Accuracy analytics | Accuracy and counts derive from submitted attempts and non-skipped answers |
| FR-09 | Weak topics | Below 60% and at least two attempts; insufficient evidence is explicit |
| FR-10 | Recommendations | Owner-scoped action, reason, and optional supporting document/page |
| FR-11 | `learning_history` | Owner-scoped, paginated activity snapshots survive document content cleanup |

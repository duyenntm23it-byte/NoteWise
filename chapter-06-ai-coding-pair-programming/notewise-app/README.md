# NoteWise

NoteWise is an AI-powered study workspace with a Next.js frontend, a FastAPI
backend, and PostgreSQL with the `pgvector` extension.

## Run with Docker Compose

1. Copy `.env.example` to `.env` in this directory and replace
   `JWT_SECRET` with a random secret before exposing the application beyond
   local development.
2. Start the services:

   ```bash
   docker compose up --build
   ```

3. Open the frontend at <http://localhost:3000>. The API health check is at
   <http://localhost:8000/health>.

The Compose database uses the `pgvector/pgvector:pg16` image and enables the
`vector` extension on first initialization. The API applies the Alembic
database migrations before starting.

## Local development

Run these commands from this directory after PostgreSQL is available and
`.env` is configured:

```bash
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
python -m pytest tests
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm ci
npm test
npm run dev
```

Authentication endpoints follow the Chapter 5 OpenAPI contract:
`POST /api/v1/auth/register`, `POST /api/v1/auth/login`, and
`GET /api/v1/me`.

Registration and login are limited per client IP to 5 and 10 attempts,
respectively, per 60-second window in this single-process MVP.

Documents use the canonical Chapter 5 routes: `GET`/`POST
/api/v1/documents`, `GET`/`DELETE /api/v1/documents/{document_id}`, and
`POST /api/v1/documents/{document_id}/retry`. Upload accepts PDF, DOCX, and
PPTX up to `DOCUMENT_MAX_UPLOAD_BYTES` (25 MiB by default). Source files are
stored under a generated key in the persistent `document_files` volume. The API
process runs a database-backed job loop for extraction, retry, and deletion;
document text is chunked for later learning features before the document becomes
`READY`.

The frontend provides the protected Document Hub at `/documents`, including
multipart upload progress, lifecycle status, failed-document retry, and
confirmed deletion.

Document learning uses the canonical Chapter 5 routes:
`POST /api/v1/documents/{document_id}/summaries`,
`GET /api/v1/summaries/{summary_id}`, and
`POST /api/v1/documents/{document_id}/questions`. Set `OPENAI_API_KEY` in the
backend environment to enable AI. The configured defaults are
`text-embedding-3-small` with 1536 dimensions and `gpt-4o-mini`; retrieval uses
cosine similarity, an HNSW index, up to five chunks, and a 0.35 similarity
threshold. Documents are not `READY` until their extracted chunks have valid
embeddings. Existing chunks with null embeddings are backfilled by the worker.
An ungrounded or unsupported question returns the explicit
`insufficient_evidence` response. The protected study screen is available at
`/documents/{document_id}` and citation badges reveal the returned excerpt,
page, and section.

Quizzes follow the Chapter 5 lifecycle: create with
`POST /api/v1/documents/{document_id}/quizzes`, poll
`GET /api/v1/quizzes/{quiz_id}`, start an attempt with
`POST /api/v1/quizzes/{quiz_id}/attempts`, restore it with
`GET /api/v1/quiz-attempts/{attempt_id}`, and submit to
`POST /api/v1/quiz-attempts/{attempt_id}/submit`. Generation requires an owned
`READY` document and an AI provider configuration. The quiz setup supports
5–20 questions (default 10), multiple choice, true/false, and fill-in-the-blank.
Public quiz and in-progress attempt responses omit answer keys. Submitted
results include deterministic scoring (skipped questions count as incorrect,
rounded to two decimals), explanations, and source citations. Identical
submissions replay the stored result; a changed submission returns
`ALREADY_SUBMITTED`, while reusing its idempotency key with a changed body
returns `IDEMPOTENCY_CONFLICT`. The protected quiz player is available at
`/documents/{document_id}/quiz`.

Learning analytics use owner-scoped `GET /api/v1/analytics/overview`,
`GET /api/v1/analytics/accuracy`, and
`GET /api/v1/analytics/weak-topics`; personalized actions use the canonical
`GET /api/v1/recommendations` route. The overview score is the arithmetic mean
of submitted attempt scores, while accuracy is calculated from non-skipped
answers. A topic is classified as weak only after at least two submitted
attempts and accuracy strictly below 60%. The protected dashboard is available
at `/analytics`.

Recommendations may include a document and chunk ID. The document view reads
`GET /api/v1/documents/{document_id}/chunks/{chunk_id}` only for an owned,
ready document and focuses the returned passage; the response does not include
source text on the recommendation endpoint. Learning activity is available
through the owner-scoped, paginated `GET /api/v1/learning-history` endpoint and
the protected `/history` page. History retains safe title/detail snapshots,
including submitted quiz scores, and is not used to bypass document
authorization.

# NoteWise

Production-oriented starting point for NoteWise: a layered FastAPI API, a Next.js
frontend, and PostgreSQL with the `pgvector` extension available.

## Local setup

1. Copy `.env.example` to `.env` and set a strong `SECRET_KEY` and
   `POSTGRES_PASSWORD`.
2. Start PostgreSQL with `docker compose up -d db`.
3. Start the API:

   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Start the frontend in another terminal:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

The frontend runs at `http://localhost:3000`; the API health root and Swagger UI
are available at `http://localhost:8000/` and `http://localhost:8000/docs`.

## Authentication

- `POST /api/v1/auth/register` accepts a JSON email/password and returns a bearer
  token plus the public user profile.
- `POST /api/v1/auth/token` accepts OAuth2 form fields `username` (email) and
  `password`, returning a bearer token.
- `GET /api/v1/auth/me` returns the authenticated user's public profile.

Set `SECRET_KEY` to a unique random value of at least 32 characters before using
authentication. The frontend keeps the access token in per-tab `sessionStorage`
and sends it as a bearer token; logging out clears the local session.

## Material Hub

- `POST /api/v1/materials/upload` accepts a PDF or UTF-8 TXT file as multipart
  field `file`. Uploads are limited to 20 MiB by default and stored under
  `backend/storage/uploads/`.
- `GET /api/v1/materials/` lists only the signed-in user's documents.
- `DELETE /api/v1/materials/{id}` removes that user's document and stored file.
- PDF page references are retained on extracted chunks. Text is split into
  1000-character chunks with 200-character overlap and embedded using Gemini
  `gemini-embedding-001` at 768 dimensions before being stored in pgvector.

Set `GOOGLE_API_KEY` to enable processing. Without it, uploads are recorded as
failed and the API returns a clear service-unavailable response. Configure
`DOCUMENT_STORAGE_PATH` and `MAX_UPLOAD_SIZE_BYTES` for your deployment.
The Material Hub is available at `/dashboard/materials`.

## Document Q&A

- `POST /api/v1/rag/query` accepts a question and an optional `document_ids`
  filter, retrieves the four closest ready chunks for the signed-in user, and
  returns a grounded answer with citation references, document titles, chunk
  indexes, page numbers, and the cited excerpt text.
- The chat interface is available at `/dashboard/chat`. Select at least one
  ready document; clicking a citation opens its source excerpt.
- The RAG search and answer generation both use `GOOGLE_API_KEY`. The endpoint
  reports a service-unavailable response when a required provider is not
  configured and does not fabricate an answer when no chunks match.

## AI Quiz Player

- `POST /api/v1/quizzes/generate` creates a 5- or 10-question quiz from a
  selected ready document, sampling source chunks across the document and
  retaining each question's chunk and page citation.
- `GET /api/v1/quizzes/` lists the signed-in user's quizzes and latest scores.
  `GET /api/v1/quizzes/{id}` returns player-safe questions without answer keys.
- `POST /api/v1/quizzes/{id}/submit` grades answers on the server, persists an
  attempt, and returns explanations with source document and page details.
- The player is available at `/dashboard/quiz`. Configure `GOOGLE_API_KEY` for
  Gemini-powered question generation.

## Checks

Run backend tests from `backend/` with `pytest`. Create reviewed schema revisions
with `alembic revision --autogenerate -m "describe change"` and apply them with
`alembic upgrade head`.

Never commit `.env` or production credentials. Set `APP_ENV=production` and
provide a non-placeholder secret before deploying the API.

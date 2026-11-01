# AGENTS.md — NOTEWISE AI Agent Operational Rules

> **Project:** NoteWise — Modular Monolith RAG & AI Quiz Platform
> **Tech Stack:** FastAPI + PostgreSQL/pgvector + Google Gemini API + Next.js + Tailwind CSS

## 1. Core Principles

- **Strict Typing:** No `any` in TypeScript; explicit Pydantic schemas in FastAPI.
- **Transactional Safety:** All database writes must run in explicit SQLAlchemy session transactions.
- **Preserve Logic & UI:** Never overwrite whole layout files when fixing TDD logic. Retain Tailwind classes.
- **Preserve Working Slices:** Auth, Material Hub, RAG chat and their tests are working. Do not refactor or change their behavior unless the task explicitly requires it.

## 2. AI Provider Rules (Google Gemini)

- **Provider:** The project uses Google Gemini only, through the `google-genai` SDK (`from google import genai`) and `GOOGLE_API_KEY`. Do NOT use OpenAI or LangChain. Ignore any OpenAI, `OPENAI_API_KEY` or 1536-dimension reference found in older docs or skills.
- **Embeddings:** model `gemini-embedding-001`, 768 dimensions (`EMBEDDING_DIMENSIONS` in `backend/app/services/embeddings.py`). Documents use task type `RETRIEVAL_DOCUMENT`, questions use `RETRIEVAL_QUERY` via `embed_query`. All vector columns and test vectors must be `Vector(768)` / 768 floats. The legacy `notes` table (`app/models/note.py`, migration `0001_initial_notes.py`) intentionally stays at 1536 dimensions; do not modify it or its migration.
- **Text generation:** reuse the single `CHAT_MODEL` constant and the answer error classes (`AnswerServiceError`, `AnswerServiceUnavailable`, `AnswerProviderError`) in `backend/app/services/rag.py`. Never hard-code a model name elsewhere. Gemini model names change over time; if a call returns 404, list models that support `generateContent` instead of guessing a name.
- **Free-tier budget:** the free tier allows only a small number of requests per day. Use exactly one LLM call per user action. Retry only on 429/500/503 with backoff, and regenerate invalid model output at most once.
- **Tests:** never call the real Gemini API or the network in tests. Inject fakes with `app.dependency_overrides` (see `backend/tests/test_rag.py`).

## 3. Workflow & Safety

- Never read, print or modify `.env` or any secret.
- Create Alembic migrations but never run `alembic upgrade`; the developer runs it. Before writing a migration, check `alembic heads` and chain `down_revision` correctly.
- Run backend tests from `backend/` with `python -m pytest -q`, and lint with `ruff check`.
- Scope every query to the authenticated user. Return 404 (not 403) for resources owned by someone else so existence is not leaked.
- Never expose quiz answer keys or explanations before the user submits.

## 4. Specialized Roles

- **Backend Agent:** Focuses on `backend/app/`, FastAPI routers, JWT auth, and RAG pipelines.
- **Frontend Agent:** Focuses on `frontend/src/`, Next.js components, Zustand stores, and Tailwind styling.
- **Database Agent:** Focuses on Alembic migrations, SQLAlchemy models, and pgvector indexes.
- **Reviewer Agent:** Focuses on auditing security flaws, SQL injections, and code smells.

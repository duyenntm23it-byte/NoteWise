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

## Checks

Run backend tests from `backend/` with `pytest`. Create reviewed schema revisions
with `alembic revision --autogenerate -m "describe change"` and apply them with
`alembic upgrade head`.

Never commit `.env` or production credentials. Set `APP_ENV=production` and
provide a non-placeholder secret before deploying the API.

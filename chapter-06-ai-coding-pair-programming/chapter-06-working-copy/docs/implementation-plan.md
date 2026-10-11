# P6.1 — Slice 1: Student Authentication & Session Management

**Status:** Approved and implemented; local verification passed. A live
PostgreSQL/Docker run was unavailable in the implementation environment.

## 1. Goal and delivery boundary

Deliver student registration, password-based login, current-user lookup, and a
browser authentication session for NoteWise. The API is the authority for
identity and authorization; the frontend route guard is a usability layer and
must never be treated as a security boundary.

### Included

- `POST /api/v1/auth/register`: validate credentials, persist a password hash,
  and issue the contract-defined access-token response.
- `POST /api/v1/auth/login`: canonical Chapter 5 OpenAPI path selected when
  the user approved this plan; return the contract-defined token response.
- `GET /api/v1/me`: canonical Chapter 5 OpenAPI path selected when the user
  approved this plan; return the authenticated user's public profile from the
  verified Bearer-token subject.
- PostgreSQL-backed `users` persistence and a schema migration.
- Screen 1 Auth in the Next.js application: login/register modes, validation,
  accessible pending/error states, and success navigation.
- Store only the short-lived access token in LocalStorage, restore/check the
  session on reload, clear it on logout or an invalid/expired-token response,
  and guard internal routes.
- Unit, API integration, frontend, and contract-traceability tests described
  in §6.

### Excluded from this slice

Password reset, email verification, refresh tokens, social/SSO login, roles,
remember-me, account deletion, and learning-feature implementation are not
added. Learning endpoints introduced in later slices must use the same
verified-user dependency and owner-scoped query invariant; the frontend guard
alone does not satisfy authorization.

## 2. Approval gates and source-of-truth discrepancies

The implementation follows the Chapter 5 OpenAPI paths and schema as the
contract source of truth, as set out in the approved plan:

1. **Authentication route conflicts — resolved by approval.** The task requires
   `POST /api/v1/auth/token` and `GET /api/v1/auth/me`, while
   [Chapter 5 OpenAPI](../../chapter-05-ai-for-software-design-architecture/design/openapi.yaml)
   specifies `POST /api/v1/auth/login` (`operationId: login`) and
   `GET /api/v1/me` (`operationId: getCurrentUser`). The approved
   implementation preserves the reviewed OpenAPI paths: `/api/v1/auth/login` and
   `/api/v1/me`. No undocumented aliases are added.
2. **PRD approval status.** The supplied
   [Chapter 3 PRD](../../docs/NoteWise_Chapter3/docs/3.2-product-requirements.md)
   currently labels itself `Draft for review`. User approval of Slice 1 is the
   implementation authorization for this scope; it does not modify the PRD's
   recorded document status.
3. **Duplicate-email error detail.** OpenAPI declares registration `409
   Conflict`, but its shared `ErrorResponse` code enum has no
   `EMAIL_ALREADY_REGISTERED` code and the Conflict response description is
   generic. Use a safe `409` response with the existing `STATE_CONFLICT` code;
   do not add an undocumented error code.

These are explicit review items, not permission to change the approved
Chapter 3/5 artifacts during planning.

## 3. Design and API contract baseline

The contract base URL is `/api/v1`. Unless the login-path decision changes it,
implement the following contract without adding request or response fields:

| Operation | Request | Success response | Contract errors | Auth |
|---|---|---|---|---|
| `POST /auth/register` | JSON `RegisterRequest`: exactly `email` and `password`; email format, max 320 chars; password 12–128 chars | `201 AuthResponse` | `409 Conflict`, `422 ValidationError`, `429 RateLimited` | Public |
| `POST /auth/login` | JSON `LoginRequest`: exactly `email` and `password`; email format | `200 AuthResponse` | `401 Unauthorized`, `422 ValidationError`, `429 RateLimited` | Public |
| `GET /me` | No caller-supplied user ID | `200 User`: `id`, `email`, `created_at` | `401 Unauthorized` | Bearer required |

`AuthResponse` contains `access_token`, `token_type: "Bearer"`,
`expires_in: 900`, and `user`. Authentication endpoints are public; `/me` and
all future protected operations require `bearerAuth`. Follow the shared
`ErrorResponse` envelope (`error.code`, `error.message`, `error.request_id`)
and the status/schema declared by OpenAPI. Do not expose password hashes,
credentials, token values, or whether a login email exists.

### Persistence and security invariants

- Follow the approved Chapter 5 ERD: `users(id UUID, email UNIQUE,
  password_hash, created_at)`. No display name or client-chosen owner ID is
  introduced in this slice.
- Normalize email by trimming whitespace and case-folding before uniqueness
  checks and lookup. A database unique constraint remains the concurrency-safe duplicate
  registration check.
- Hash passwords with Passlib and bcrypt. To retain OpenAPI's 128-character
  maximum without bcrypt's 72-byte truncation behavior, use Passlib's
  `bcrypt_sha256` scheme (backed by bcrypt) and test long UTF-8 passwords.
  Never store or log plaintext passwords.
- Issue a signed JWT with a UUID `sub` and expiry matching the 900-second
  response contract. Keep the signing secret and algorithm in backend settings;
  require a non-placeholder secret outside development. Validate signature,
  expiry, and subject server-side on every protected request.
- Resolve the current user exclusively from the verified JWT `sub`. Never
  accept a request parameter/header/body value as the authoritative `user_id`.
- LocalStorage is required by the approved architecture, but is readable by
  same-origin JavaScript. Store no password or redundant sensitive profile
  data; do not log tokens; clear the token on logout, expiry, or authenticated
  `401`; render protected data only after session verification. The API remains
  the authorization boundary.

## 4. Implementation sequence (TDD)

### Phase A — Backend contract and persistence

1. Add failing security/service tests for password hash/verify, hash
   non-equivalence to plaintext, passwords at the OpenAPI length boundaries,
   JWT subject/expiry, and invalid/expired/signature-tampered tokens.
2. Add only required backend dependencies: Passlib with bcrypt support,
   a JWT library, email validation, Alembic, and the test stack
   (`pytest`, HTTPX/TestClient support). Keep dependency versions compatible
   with the existing FastAPI/Pydantic/SQLAlchemy baseline.
3. Add typed auth schemas matching `RegisterRequest`, `LoginRequest`,
   `AuthResponse`, and `User`; disallow extra request fields and exclude
   `password_hash` from every public schema.
4. Add `User` persistence model, database session/dependency, Alembic
   configuration, and an initial users-table migration matching the ERD.
5. Add focused auth service functions for registration, credential checking,
   token issue/verification, and current-user resolution. Map duplicate email
   to the approved `409` contract; use a generic `401` login message for
   unknown email and wrong password.
6. Add bounded per-IP rate limits for public auth operations, returning the
    contract `429 RATE_LIMITED` response.
7. Add the auth router and application-level error mapping so response codes,
   status codes, and body envelopes match OpenAPI. Mount it under `/api/v1`;
   make `/me` bearer-protected and leave register/login public.

### Phase B — Backend integration tests

Implement request-level tests against the real FastAPI application with an
isolated database fixture; run migration/constraint coverage against
PostgreSQL as well as fast unit tests. Cover all scenarios in §6 before moving
on. Tests must assert response shape/status and database side effects, not
merely that a handler returned without raising.

### Phase C — Frontend session and Screen 1 Auth

1. Add failing tests for login/register mode, input constraints, pending state,
   safe server-error rendering, success navigation, session restore, logout,
   and route redirects.
2. Add a typed API client and auth/session provider. Use the approved API
   origin configuration and the resolved login route; attach
   `Authorization: Bearer <access_token>` only to protected API calls.
3. On login/register success, persist only the access token; request `/me` on
   restoration before exposing protected content. Do not trust a
   client-decoded JWT as validation.
4. Implement the approved Screen 1 Auth based on the
   [Chapter 4 auth concept](../../chapter-04-ai-for-product-design/design/concepts/screen-1-auth-concept.html):
   login/register tabs, email/password inputs, password visibility control,
   clear inline validation and API feedback, loading/disabled submit state,
   and accessible labels/live errors. Show password confirmation only during
   registration if retained from the detailed prototype.
5. Add `/auth` and a protected route-group layout (with a minimal authenticated
   landing page for this slice). Redirect unauthenticated visits to `/auth`,
   retain a safe same-origin return path, and return authenticated users to
   their intended route. On `401`, clear session and redirect; do not redirect
   on unrelated network/server errors.
6. Ensure direct navigation, page refresh, logout, and an expired token all
   have deterministic UX. The client guard does not replace API auth.

### Phase D — Acceptance and contract verification

Run backend unit/API tests, PostgreSQL migration/integration tests, frontend
tests, frontend production build/type-check, and an OpenAPI conformance review.
Verify every implemented operation/method/path, request constraint, success
schema, authentication requirement, status code, and shared error envelope
against the approved OpenAPI. The login-path gate is resolved in favor of the
canonical contract paths.

## 5. Expected file touchpoints

| Area | Planned files (create/update as needed) |
|---|---|
| Backend dependency/config | `notewise-app/backend/requirements.txt`; `app/core/config.py`; database setup under `app/db/` |
| Backend auth | `app/models/user.py`; `app/schemas/auth.py`; `app/api/auth.py`; auth/security service under `app/services/` or `app/core/security.py`; `app/main.py` |
| Database migration | `backend/alembic.ini`; `backend/alembic/env.py`; `backend/alembic/versions/*_create_users.py` |
| Backend tests | `backend/tests/test_auth_api.py`; `backend/tests/test_security.py` |
| Frontend dependencies/config | `frontend/package.json`; test-runner config and test setup |
| Frontend auth/session | `frontend/src/app/auth/page.tsx`; `frontend/src/app/(protected)/layout.tsx`; `frontend/src/app/(protected)/dashboard/page.tsx`; session provider, API client, auth form and tests under `frontend/src/` |
| Environment/docs | `notewise-app/.env.example`; `notewise-app/README.md` for required JWT/database configuration and local run/test steps |

Keep the existing Docker Compose, Next.js, FastAPI, and pgvector setup intact
except for the minimal configuration required to run the migration and auth
tests. Do not implement later learning features as part of Slice 1.

## 6. Test intent and acceptance matrix

| ID | Requirement / contract | Test and required evidence |
|---|---|---|
| T1 | FR-01: register with valid credentials; OpenAPI `POST /auth/register` | API integration: valid request returns `201`; exact `AuthResponse` fields and values; user row exists; password column is a hash and does not equal submitted password; returned token authenticates `GET /me`. |
| T2 | FR-01: reject invalid registration credentials; `422` schema | Parametrized API tests for malformed email, missing fields, password below 12 or above 128 characters, and unexpected fields. Assert `422`, contract error envelope, and no user row created. |
| T3 | Unique user email / registration `409` | Register the same normalized email twice; assert second request is safe `409` in the approved error schema and only one user exists. Include a concurrent uniqueness test against PostgreSQL if feasible. |
| T4 | FR-01: registered student logs in | API integration: correct credentials return `200 AuthResponse`, bearer token resolves the matching UUID/email from `GET /me`, and no password/hash appears in either response. |
| T5 | FR-01: invalid credentials produce a clear and safe error | Wrong password and unknown email each return the same public `401` message/code shape; assert neither response reveals account existence. |
| T6 | FR-01: protected feature requires an authenticated session | `GET /me` without Authorization, malformed Bearer, invalid signature, or expired token returns `401` in the OpenAPI error envelope; valid token returns `200`. |
| T7 | FR-01: only the signed-in student's identity is used | Create two users; tokens return only their own profile. Supplying an unrelated `user_id` in an ignored query/body/header cannot switch identity. For future learning routes, each slice must add cross-user `404`/non-disclosure and owner-filter tests before that feature can be marked compliant. |
| T8 | Screen 1 Auth and session behavior | Frontend tests cover switching modes, email/password validation, pending/error/success states, token persistence/restore, `/me` verification, logout/401 clearing, protected-route redirect, and safe return path. |
| T9 | OpenAPI traceability | Contract test/review asserts registered paths/methods, request schemas, status codes, response fields, Bearer requirement, `token_type`, `expires_in`, and `User` shape. Uses canonical `/auth/login` and `/me`; no aliases are added. |

### FR-01 traceability

| FR-01 acceptance criterion (Chapter 3) | Slice 1 coverage | Evidence |
|---|---|---|
| Register using valid credentials | Direct | T1 |
| Registered student logs in successfully | Direct | T4 |
| Invalid credentials yield a clear, safe error | Direct | T2, T5 |
| Protected learning features require an authenticated session | Foundation in this slice; each feature endpoint is completed and tested by its owning later slice | T6, T7, future-slice gate |
| Student accesses only their own learning records | Identity/ownership invariant established here; data-level proof is required for every later user-owned resource | T7, future-slice gate |

Do not report FR-01 as fully accepted solely because `/me` is protected: the
last two criteria remain cross-slice obligations until protected learning
routes and owner-scoped queries exist and have tests.

## 7. Definition of done

- The user approved the plan on 2026-10-10; authentication uses the approved
  canonical OpenAPI routes and preserves the PRD's recorded draft status.
- Backend operations conform to the final approved OpenAPI contract and ERD.
- Passwords are safely hashed; JWTs are signed, short-lived, validated, and
  never logged; all protected identity derives from token `sub`.
- Screen 1 Auth works on direct navigation and refresh; session is restored
  only after `/me` succeeds, and invalid sessions are cleared.
- T1–T9 pass at the applicable test levels; frontend production build and
  type-check pass; migration succeeds on PostgreSQL.
- FR-01 cross-slice responsibilities are recorded and not overstated.

## 9. P6.2 verification evidence

- RED: before implementation, the backend auth tests could not import the
  missing persistence layer and the frontend suites could not resolve the
  missing auth/session components.
- GREEN: backend `pytest tests -q` — **22 passed**; frontend `npm test` —
  **10 passed** (auth screen, pending state, safe return paths, session restore/logout, bearer
  handling, protected route).
- Frontend `npm run build` — successful, including Next.js type validation and
  production static generation.
- Python `compileall` — successful for `app`, `tests`, and Alembic files.
- `alembic upgrade head --sql` — successful PostgreSQL-dialect SQL generation
  for the users migration. The migration was not applied to a live PostgreSQL
  service because Docker/PostgreSQL was unavailable in the environment.
- Frontend Problems check — no errors. Backend API integration tests used
  isolated SQLite; PostgreSQL runtime/constraint behavior remains unverified.
- OpenAPI conformance test asserts the canonical paths/operation IDs, request
  constraints, response codes, shared error model, and Bearer security. The
  implementation uses `/api/v1/auth/login` and `/api/v1/me`; it does not add
  the task's conflicting `/auth/token` or `/auth/me` aliases.

  ---

  # P6.1 — Slice 2: Document Management & Processing Lifecycle

  **Status:** Approved on 2026-10-10 and implemented. Local verification passed;
  live PostgreSQL migration and runtime verification remain outstanding.

  ## 1. Goal and delivery boundary

  Implement the authenticated Document Hub and the owned-document lifecycle for
  FR-02 and FR-03. A successful upload must be durably accepted, have a visible
  `PROCESSING` state, and reach `READY` only after usable extracted learning
  content is persisted; invalid or unprocessable content reaches `FAILED` with a
  safe failure code. This slice does not generate summaries, embeddings, quizzes,
  or AI responses.

  Source baseline: [Chapter 3 PRD](../../docs/NoteWise_Chapter3/docs/3.2-product-requirements.md),
  [Screen 2 design](../../chapter-04-ai-for-product-design/docs/product-design-brief.md),
  [Chapter 5 OpenAPI](../../chapter-05-ai-for-software-design-architecture/design/openapi.yaml),
  [data model](../../chapter-05-ai-for-software-design-architecture/design/data-model.mmd),
  and [architecture](../../chapter-05-ai-for-software-design-architecture/design/architecture.md).

  ### Included

  - Authenticated upload of PDF, DOCX, and PPTX; validate configured byte limit,
    extension, declared media type, and file signature before the document is
    exposed as accepted. Parseability is checked by the asynchronous processor.
  - Owner-scoped document listing/detail, processing retry, and asynchronous
    deletion using the canonical Chapter 5 OpenAPI contract.
  - PostgreSQL document/job persistence, a local persistent storage adapter,
    recoverable processing and deletion jobs, and deterministic text extraction
    and chunk persistence for the three supported formats.
  - Protected Screen 2 Document Hub: file picker and drag-and-drop, upload
    progress, document list/status badges, status filtering, retry for eligible
    failures, and deliberate delete confirmation.
  - Backend, lifecycle, ownership, migration, OpenAPI, and frontend tests written
    before their implementation in RED–GREEN–VERIFY order.

  ### Excluded from this slice

  AI embeddings, summaries, Q&A, quizzes, learning history, download/preview
  endpoints, subject/tag metadata and filters, and production object storage.
  Search and grid/list switching are deferred unless separately approved; the
  OpenAPI list operation currently defines paging and status filtering only.

  ## 2. Approval gates and source-of-truth discrepancies

  1. **Upload route — use canonical OpenAPI path.** The task names
     `POST /api/v1/documents/upload`; Chapter 5 defines multipart upload as
     `POST /api/v1/documents` (`operationId: uploadDocument`). Plan to implement
     the OpenAPI path and not add an undocumented alias.
  2. **Durable processing vs. an in-process mock.** The task allows a mock or
     background task, but the approved architecture specifies database-backed
     `processing_jobs`, recoverable leases, and asynchronous cleanup. Plan to
     implement the smallest database-backed job loop in the API process (no new
     broker/service), rather than FastAPI `BackgroundTasks`, so `202` means the
     job was durably accepted and the contract's `503 PROCESSING_UNAVAILABLE`
     remains meaningful.
  3. **Configured upload-size limit is not numeric in the PRD/OpenAPI.** The
     product design requires displaying the limit, while OpenAPI only refers to
     a configured maximum. Propose 25 MiB (26,214,400 bytes) as the initial
     `MAX_UPLOAD_BYTES`; confirm or replace this value before implementation.
     Use the approved cap consistently in backend settings, frontend display,
     boundary tests, and deployment configuration.
  4. **Persistent file size is absent from `Document`.** Screen 2 design asks
     each saved row to show file size, but the OpenAPI `Document` schema has no
     size field. The strict-contract proposal is to show the selected file's
     size during upload only and not add an undocumented response field. If size
     must remain visible after reload, amend and approve the Chapter 5 contract
     before implementation.
  5. **UI design items beyond this slice.** Search, subject/tag filters, grid/list
     switching, and View Summary/Q&A/Create Quiz actions have no supporting
     fields or feature endpoints in this slice. Keep the Hub focused on upload,
     status, retry, and delete; add those actions with their owning slices rather
     than presenting nonfunctional controls.

  These decisions preserve the source requirements; they do not authorize edits
  to the PRD, UI design, OpenAPI, or ERD during implementation without approval.

  ## 3. Design and API contract baseline

  Base path is `/api/v1`; every operation below requires the Slice 1 Bearer
  dependency. The server derives `user_id` only from the verified JWT subject.
  Every lookup and mutation is owner-scoped; another user's document ID returns
  `404 NOT_FOUND` rather than disclosing resource existence.

  | Operation | Request | Success response | Contract errors |
  |---|---|---|---|
  | `GET /documents` | `page` (default 1), `page_size` (default 20, range 1–100), optional `status` | `200 DocumentPage` | `401 Unauthorized` |
  | `POST /documents` | multipart field `file`; optional `Idempotency-Key` | `202 DocumentAccepted` containing `document` and `job_id` | `401`, `409`, `413`, `415`, `422`, `429`, `503` |
  | `GET /documents/{document_id}` | UUID path parameter | `200 Document` | `401`, `404` |
  | `POST /documents/{document_id}/retry` | optional `Idempotency-Key` | `202 JobAccepted` (`QUEUED` or `RETRY_WAIT`) | `401`, `404`, `409` |
  | `DELETE /documents/{document_id}` | UUID path parameter | `202 DocumentDeletion` (`DELETING` or `DELETED`) | `401`, `404`, `409` |

  Do not replace the `202` responses with synchronous `200/201` responses. Follow
  the shared `ErrorResponse` envelope and codes, including `FILE_TOO_LARGE`,
  `UNSUPPORTED_FILE_TYPE`, `PROCESSING_UNAVAILABLE`, `NOT_FOUND`, and
  `STATE_CONFLICT`; do not introduce undocumented error codes.

  The API's `Document` response remains the Chapter 5 schema: `id`, `filename`,
  `media_type`, `status`, nullable `failure_code`, nullable `page_count`,
  `created_at`, and `updated_at`. `DocumentPage` is `{items, page, page_size,
  total}`. The document state machine follows architecture: `PROCESSING` to
  `READY`, `FAILED`, or `DELETING`; `FAILED` to `PROCESSING` or `DELETING`;
  `READY` to `DELETING`; and `DELETING` to terminal `DELETED`. A valid owned
  document in a disallowed state returns `409 STATE_CONFLICT`.

  ### Persistence, storage, and processing invariants

  - Add migrations after the Slice 1 users migration for the ERD `documents`,
    `processing_jobs`, and `document_chunks` tables, ownership foreign keys,
    state checks, and owner/status/job indexes. Keep the ERD's fields and
    ownership relationships; do not store client-supplied paths. Embeddings
    remain nullable/unpopulated until the later AI-ingestion slice.
  - Store bytes below a configured root on a named Docker volume, using
    server-generated opaque storage keys. The existing Compose setup has no
    document volume yet; mount one into the backend and share the same configured
    root with the storage adapter. Never derive a path from the submitted
    filename.
  - Stream/count bytes and stop at the approved cap; validate extension, MIME,
    and signatures before queueing. Reject unsupported or mislabeled files with
    `415` and oversize input with `413`. Bound decompressed bytes, page/slide
    count, and processing time to mitigate archive/decompression exhaustion. A
    signature-valid but corrupt or unextractable file is accepted for
    processing, then reaches `FAILED` with a safe code. Rejected requests leave
    no document, job, or orphaned final file.
  - Persist the document row and ingestion job atomically. Only return `202` once
    the bytes are safely stored and the job is durable; clean up a staged file on
    transaction failure. Job handlers are idempotent and use generated storage
    keys. If durable acceptance fails, return `503 PROCESSING_UNAVAILABLE`.
  - Extract text/page metadata and persist bounded, ordered chunks for later
    learning features. Set `READY` only after extraction and chunk persistence
    commit; parser/empty-content failures set `FAILED` with a non-sensitive,
    contract-safe `failure_code`. Do not log source bytes or extracted text.
  - Retry only an owned recoverable `FAILED` document. Queue a new job and return
    `202`; reject a non-retryable state with `409`. Reprocessing must not leave
    duplicate chunks or stale failure state.
  - Deletion first makes content unavailable and transitions to `DELETING`,
    then queues cleanup of the source file, chunks, and eligible jobs; finalize
    as `DELETED`. Workers must re-check state/lease before publishing results so
    an in-flight processor cannot move a deleting document back to `READY`.
    Repeated deletion is safe/idempotent. A document with dependent records in
    a future slice must follow approved FK/cascade behavior, not silently
    orphan learning records.
  - Configure CORS for the required `DELETE` method and `Idempotency-Key`
    request header. Preserve Slice 1 auth behavior and API error handling.

  ## 4. Implementation sequence (TDD)

  ### Phase A — Backend contract and failing tests

  1. Add contract tests for the five canonical operations, exact status codes,
     response schemas, pagination defaults/bounds, status filter, UUID
     validation, Bearer requirement, and shared error envelope.
  2. Add upload tests for valid PDF/DOCX/PPTX, unsupported extension/MIME,
     mismatched signatures, and configured size limit at/over boundary. Verify
     rejected uploads leave no rows, job, or permanent file. Add processor tests
     showing signature-valid but malformed/empty content is durably accepted
     before reaching `FAILED` rather than being reported as a synchronous
     upload rejection.
  3. Add ownership tests with two authenticated users for list, detail, retry,
     and delete. Assert all cross-owner IDs are indistinguishable `404`s, and
     user-supplied owner IDs cannot select or mutate another user's records.
  4. Add lifecycle tests: durable upload job starts `PROCESSING`; successful
     extraction writes chunks then reaches `READY`; parser/worker failure reaches
     `FAILED`; eligible retry returns to `PROCESSING` and can recover; invalid
     retry returns `409`; delete queues cleanup and reaches `DELETED`; repeated
     deletion is idempotent; worker restart/lease recovery does not duplicate
     chunks or corrupt state.
  5. Add frontend failing tests for picker/drop upload and bearer header, visible
     upload progress/errors, list rendering and status badges, empty/loading
     states, retry eligibility, delete confirmation/cancel/confirm, and refreshed
     list after mutation.

  ### Phase B — Backend persistence, storage, and processing

  1. Add the minimum parser and upload dependencies after confirming maintained
     libraries for PDF, DOCX, and PPTX; add coverage for malformed inputs and
     extraction failure. Keep file-size and extraction limits configurable and
     bounded.
  2. Implement document/job ORM models and Alembic migration following the ERD
     and `20261010_0001_create_users` migration. Make `processing_jobs` durable;
     do not replace it with an in-memory task queue.
  3. Implement a storage adapter that stages and atomically places files under
     opaque generated keys, enforces the configured size limit while reading,
     and removes staged bytes on every explicit failure path.
  4. Implement MIME/signature/parser validation, extraction/chunk persistence,
     lifecycle transitions, owner-scoped service queries, retry rules, and
     asynchronous deletion cleanup. Keep failure responses/logging free of file
     content and filesystem paths.
  5. Wire authenticated routes and exact OpenAPI response/status models; ensure
     durable enqueue failure is surfaced as the contract `503`.
  6. Extend Compose with a persistent backend file volume and its configuration;
     extend CORS only for required methods/headers.

  ### Phase C — Frontend Document Hub

  1. Reuse Slice 1 LocalStorage JWT handling; add a typed XHR upload helper
     that sends the Bearer token, reports upload progress, clears the token on
     `401`, and lets the browser set the multipart boundary. Use an accessible
     file input alongside drag-and-drop.
  2. Add the protected Screen 2 page and typed `Document`/`DocumentPage` client
     models; display filename, upload date, media type, lifecycle badge, and
     locally available selected-file size. Use client-observed upload progress
     and status refresh/polling without inventing server response fields.
  3. Add status filter, retry action only for `FAILED`, and an accessible
     confirmation dialog for deletion. Refresh affected rows after accepted
     mutations and show actionable API errors.
  4. Preserve keyboard interaction, visible focus, responsive layout, pending
     states, and existing auth/session route protection. Do not show mock
     success states or enable actions in invalid lifecycle states.

  ### Phase D — Acceptance and contract verification

  Run focused backend and frontend tests first, then the complete Slice 1 + 2
  test suites, migration generation/application, OpenAPI conformance checks,
  frontend production build/type-check, and Compose health/storage smoke tests
  when Docker/PostgreSQL are available. Verify file-volume persistence across an
  API restart and delete/retry transitions end-to-end.

  ## 5. Expected file touchpoints

  | Area | Planned files (create/update as needed) |
  |---|---|
  | Backend documents module | `backend/app/api/documents.py`; `app/models/document.py` and job/chunk models; document schemas/services/storage/processor/worker modules under existing `app/` boundaries |
  | Backend integration | `backend/app/main.py` for router/lifespan; `app/core/config.py` for upload/storage/worker bounds; CORS methods/headers; `backend/requirements.txt` for multipart and maintained document parsers |
  | Persistence | New Alembic migration(s) after the users migration; preserve existing user migration and data |
  | Backend tests | `backend/tests/test_documents_api.py`; `test_document_processing.py`; `test_document_storage.py` as needed, reusing the existing auth test database/JWT setup |
  | Frontend | Protected route under `frontend/src/app/(protected)/documents/`; Hub components/tests; typed API models and upload helper in `src/lib/`; add document styles to existing `src/app/globals.css` without changing Auth styling |
  | Runtime/docs | `notewise-app/docker-compose.yml` for the persistent file volume; `.env.example` and `README.md` for approved byte cap, file storage, migration, processing and test commands |

  ## 6. Test intent and acceptance matrix

  | ID | Requirement / contract | Test and required evidence |
  |---|---|---|
  | D1 | FR-02: upload supported documents | Valid PDF/DOCX/PPTX return `202 DocumentAccepted`, `PROCESSING`, and durable job ID; stored file is under an opaque key; DB owner comes from JWT. |
  | D2 | FR-02: reject unsupported/mislabeled/oversize files | Extension/MIME/signature mismatch and size-boundary cases return contract `415`/`413`; no permanent file, document, or job remains; errors use safe contract codes. Signature-valid but unparseable content is covered by D8 and reaches `FAILED`. |
  | D3 | FR-02: list/detail and visible status | `DocumentPage` pagination/filter and detail schema match OpenAPI; status transitions are visible; only the authenticated owner sees records. |
  | D4 | FR-02: user can access only their own documents | Two-user tests cover list/detail/retry/delete; foreign IDs return `404`; forged owner IDs cannot bypass token ownership. |
  | D5 | FR-02: deletion requires intentional confirmation | Frontend cancel leaves record intact; confirm calls DELETE; API returns `202` and lifecycle becomes `DELETING` then `DELETED`; storage/chunks are cleaned idempotently. |
  | D6 | FR-03: processing starts and is visible | Valid accepted upload creates a durable ingestion job and remains `PROCESSING` until handler completion; upload acknowledgement never claims `READY`. |
  | D7 | FR-03: valid documents produce usable learning content | PDF/DOCX/PPTX fixtures yield ordered nonempty extracted chunks and applicable page metadata before transition to `READY`; assert persisted chunks are owner/document scoped. |
  | D8 | FR-03: failures and retry | Corrupt/empty fixtures or injected processing failure yield `FAILED` plus safe failure code; eligible retry returns `202`, queues once, and can reach `READY`; invalid states return contract `409`. |
  | D9 | OpenAPI traceability | Assert only canonical `/documents` upload route, all five operation IDs/methods, multipart field/header, pagination/status parameters, response status/schema refs, security, and error envelopes. |
  | D10 | Screen 2 design and Slice 1 session integration | Frontend tests verify Bearer token on multipart/list/retry/delete requests, upload progress/error, status rendering/filtering, retry control, confirmation flow, keyboard-friendly input, and protected navigation. |

  ### FR-02 / FR-03 traceability

  | PRD acceptance criterion | Slice 2 coverage | Evidence |
  |---|---|---|
  | Supported documents can be uploaded | Direct | D1, D2 |
  | Unsupported or invalid files are rejected clearly | Direct | D2 |
  | Each document has a visible processing state | Direct | D3, D6, D10 |
  | A student can access only their own documents | Direct | D3, D4 |
  | Deletion requires intentional confirmation | Direct | D5, D10 |
  | System processes a valid upload into usable learning content | Direct at extracted-text/chunk level; AI enrichment is later-slice scope | D7 |
  | Processing starts after a valid upload | Direct; durable job acceptance | D1, D6 |
  | Successful processing produces `Ready` | Direct, only after extracted content is committed | D7 |
  | Failed processing produces `Failed` | Direct with safe failure code | D2, D8 |
  | Retry is available when recovery is possible | Direct for owned recoverable failures | D8, D10 |

  Do not report FR-02/FR-03 complete if only the status field changes: ownership,
  durable jobs, usable extracted content, cleanup, and the corresponding tests are
  acceptance requirements.

  ## 7. Definition of done

  - Human approval resolves the upload-path, job-processing, and upload-size
    decisions; any change to OpenAPI for persistent file size is approved first.
  - All five document operations conform to the Chapter 5 OpenAPI contract with
    canonical paths, response codes, schemas, Bearer security, and errors.
  - Upload rejects invalid/oversize content safely, stores accepted bytes under
    opaque keys, and persists the document/job before returning `202`.
  - Ownership is enforced in every API query/mutation and cross-user IDs do not
    disclose document existence.
  - Processing reaches `READY` only after usable extracted chunks are committed;
    recoverable failures support retry; deletion is confirmed, asynchronous,
    idempotent, and cleans owned file/content.
  - Screen 2 is usable with authenticated upload, visible statuses, retry/delete,
    accessible confirmation, and explicit loading/error states.
  - D1–D10 pass; migration applies on PostgreSQL; persistent storage and worker
    recovery are smoke-tested; full frontend build/type-check passes.
  - No Slice 1 auth behavior is regressed; no summaries, embeddings, or later
    learning features are represented as implemented.

  **Approval recorded:** The user approved the database-backed worker, canonical
  `POST /api/v1/documents` route, 25 MiB upload cap, and keeping persistent file
  size out of the OpenAPI `Document` schema on 2026-10-10.

  ## 8. P6.2 implementation and verification evidence

  - RED: the initial Slice 2 tests failed because the document model/service
    modules and protected Documents Hub did not exist.
  - Backend: `python -m pytest -vv tests` — **36 passed**, with one existing
    Starlette/httpx deprecation warning. The suite covers the document API
    contract/security, upload validation and ownership, pagination, failure/
    retry/delete lifecycle, PDF/DOCX/PPTX extraction, and the existing auth
    behavior. Tests use isolated SQLite; PostgreSQL runtime behavior is not
    covered by this result.
  - Frontend: `npm test` — **16 passed** across five files, including the
    Document Hub rendering, upload, retry, deletion confirmation, and upload
    API bearer/progress behavior.
  - Frontend: `npm run build` — successful Next.js production build, lint and
    type validation, and static page generation.
  - Migration: `alembic upgrade head --sql` generated PostgreSQL-dialect SQL
    successfully. It has not been applied to a live PostgreSQL service.
  - Deployment verification still required: apply the migration on PostgreSQL
    and smoke-test document storage persistence plus worker lease/recovery
    across a service restart.

---

# P6.1 — Slice 3: RAG Engine, Summarization & Document Q&A

**Status:** Approved by the user and implemented. Backend/frontend automated
tests, the frontend production build, and offline Alembic SQL generation pass.
Live PostgreSQL/pgvector migration and configured-provider end-to-end
verification remain pending because Docker/PostgreSQL and provider
credentials were unavailable in the implementation environment.

## 1. Goal and delivery boundary

Deliver FR-04 document summaries and FR-05 document-grounded Q&A for owned,
`READY` documents. Ingestion must persist fixed-dimension embeddings for
retrieval; Q&A must retrieve only the selected owner's selected document
chunks, validate answer citations against retrieved evidence, and explicitly
abstain when the evidence is insufficient. Summary generation is asynchronous
and exposes its persisted lifecycle. The Screen 3 experience combines a
document context pane, summary view, and Q&A chat with page/section citation
badges.

Source baseline: [Chapter 3 PRD](../../docs/NoteWise_Chapter3/docs/3.2-product-requirements.md),
[Screen 3 design](../../chapter-04-ai-for-product-design/design/concepts/screen-3-qa-concept.html),
[Chapter 5 OpenAPI](../../chapter-05-ai-for-software-design-architecture/design/openapi.yaml),
[data model](../../chapter-05-ai-for-software-design-architecture/design/data-model.mmd),
and [architecture](../../chapter-05-ai-for-software-design-architecture/design/architecture.md).

### Included

- Provider-neutral embedding and text-generation interfaces, with configured
  production adapters; deterministic fakes for unit tests. Credentials remain
  backend-only environment secrets and provider failures are explicit.
- Update the Slice 2 ingestion pipeline so chunks receive embeddings before a
  document can become `READY`; add an idempotent backfill/re-embedding job for
  existing ready documents that have null embeddings. Do not silently expose a
  partially embedded document as searchable.
- Define and migrate one fixed embedding model/dimension for the pgvector
  column. Add a compatible vector index and owner/document-scoped similarity
  query; avoid cross-user or cross-document retrieval.
- Queue summary generation for owned `READY` documents, persist summary
  content/status/failure code, and return the accepted resource/job. Retrieve
  the summary through the contract's summary resource endpoint.
- Add synchronous, document-scoped Q&A using vector retrieval, a bounded and
  injection-resistant RAG prompt, structured generation, citation validation,
  and explicit insufficient-evidence abstention.
- Screen 3 protected document workspace with Summary and Q&A tabs, Markdown
  summary rendering, loading/error/empty states, chat history for the active
  page session, and accessible citation badges showing available page/section
  metadata and the cited excerpt.
- Preserve Slice 1/2 ownership, authentication, deletion/tombstone semantics,
  rate limits, and API error conventions. Deleted/deleting documents and their
  derived summary/embedding content must never be retrieved or sent to a
  provider.

### Explicitly out of scope

- Quiz generation/evaluation, analytics, recommendation, persistent chat
  history, streaming tokens, multi-document search, and provider fine-tuning.
- A new source-file download or full-document-content API. The Chapter 5
  contract exposes citations with excerpts/page/section but no chunk-read
  operation; a citation opens an in-context excerpt/details view unless an
  approved contract/UI change adds direct source navigation.
- AI-generated statements presented as factual without evidence references;
  no general-knowledge fallback when document evidence is insufficient.

## 2. Contract and design decisions

The task's example paths differ from the approved Chapter 5 OpenAPI. This plan
preserves the canonical contract rather than adding unapproved aliases:

| Capability | Canonical API path (including `/api/v1`) | Contract behavior |
|---|---|---|
| Request summary | `POST /api/v1/documents/{document_id}/summaries` | `202 SummaryAccepted` with summary and job IDs; optional `Idempotency-Key` |
| Poll summary | `GET /api/v1/summaries/{summary_id}` | `200 Summary` with `QUEUED`, `PROCESSING`, `READY`, `FAILED`, or `DELETED` |
| Ask question | `POST /api/v1/documents/{document_id}/questions` | `200 QuestionResponse`; `answered` with citations or `insufficient_evidence` with `answer: null`, no citations, and `INSUFFICIENT_EVIDENCE` |

Every operation is Bearer-authenticated and owner-scoped. Unknown and
foreign-owned resources use the contract's non-disclosing `404`; non-`READY`
documents use the contract conflict response. AI unavailability, timeout, and
invalid provider output use the defined `503`, `504`, and `502` responses
respectively. No `/summary` or `/qa` alias is added unless the OpenAPI is
explicitly revised and approved.

**Approved implementation decisions:** The user approved OpenAI
`text-embedding-3-small` (1536 dimensions) and `gpt-4o-mini`; cosine similarity
with an HNSW `vector_cosine_ops` index; at most five retrieved chunks; and a
0.35 similarity threshold. Citation excerpts are revealed in-context; no
source-content API was added. Tests use deterministic fake providers and do not
require network access.

## 3. Implementation phases

### Phase A — RED: contract-first test coverage

1. Add failing tests for the exact OpenAPI operation IDs, methods, paths,
   security, request/response schemas, status codes, idempotency header, and
   both Q&A response variants. Assert the `/summary` and `/qa` aliases are not
   introduced.
2. Add backend unit tests for text normalization/chunk metadata, embedding
   dimension validation, batched embedding persistence, similarity ranking,
   owner/document filtering, relevance-threshold abstention, provider timeout/
   invalid output, and citation membership in the retrieved chunk set.
3. Add API tests for auth, ownership/non-disclosure, non-`READY` conflicts,
   asynchronous summary acceptance/polling/failure/retry/idempotency, grounded
   Q&A, and insufficient evidence. Inject fake embedding and generation
   providers; never depend on an external AI service in the unit suite.
4. Add PostgreSQL/pgvector integration tests for migration, vector dimensions,
   index/query behavior, and owner/document-scoped similarity results. SQLite
   may continue to cover route/service behavior but is not evidence for
   pgvector semantics.
5. Add frontend tests for protected Screen 3 access, tab switching, Markdown
   summary rendering, summary polling and states, chat submission/pending and
   error states, insufficient-evidence messaging, and citation badges with
   page/section/excerpt. Assert citations are keyboard accessible.

### Phase B — Embedding and retrieval foundation

1. Select and record the production embedding provider/model, vector dimension,
   normalization, distance operator, relevance threshold, and index strategy.
   Add validated settings and update `.env.example`/README without exposing
   secrets.
2. Implement typed provider interfaces/adapters under the backend AI service
   boundary; batch requests within provider limits and reject empty, malformed,
   non-finite, or wrong-dimension vectors explicitly.
3. Add an Alembic migration to set the fixed pgvector dimension and create the
   selected ANN index (or retain exact search if the chosen corpus/index
   trade-off is approved). Document migration/backfill/rollback constraints;
   do not truncate or reinterpret existing vectors.
4. Extend the ingestion worker to persist embeddings atomically with each
   chunk batch and mark `READY` only after all required embeddings are
   committed. Fail with a safe terminal code on irrecoverable embedding errors.
5. Add an idempotent job to embed existing `READY` chunks with null embeddings;
   mark retrieval unavailable until the backfill completes, without deleting
   extracted text or changing document ownership/state.
6. Implement bounded pgvector similarity retrieval filtered by both
   `user_id` and `document_id`, excluding deleted content; return only chunk
   IDs, excerpts, page/section metadata, and similarity scores to the internal
   service.

### Phase C — Summary and Q&A services/APIs

1. Add the summary persistence model/schema and summary-generation job using
   existing durable job leases where compatible; otherwise add an explicit
   job type/model migration. Enforce owner + `READY` state and idempotency when
   accepting a request. Persist only validated non-empty Markdown content;
   terminal errors set a safe `failure_code`, never success-shaped content.
2. Implement summary resource polling with ownership checks and exact OpenAPI
   nullable/content fields and status values. Ensure document deletion cancels
   queued work and removes/hides derived summary content according to the
   existing deletion policy.
3. Implement Q&A orchestration: validate the question length/schema, retrieve
   bounded relevant chunks, abstain when no chunk clears the approved evidence
   threshold, then call the generator with only that document's excerpts and
   instructions to answer solely from supplied evidence.
4. Parse a structured answer; discard malformed output and any citation whose
   chunk ID was not in the retrieval result. Require at least one valid
   citation for an `answered` response. For insufficient evidence return the
   OpenAPI `200` union branch exactly: null answer, empty citation list, and
   `INSUFFICIENT_EVIDENCE`.
5. Add request limits/rate limits and bounded provider timeouts; log request/job
   identifiers and safe error codes only, never prompts, source text, tokens,
   or provider credentials.

### Phase D — Screen 3 integration

1. Add a protected document-learning route from the Document Hub, load only an
   owned document and render explicit loading/not-found/not-ready states.
2. Add the document-context pane and Summary/Q&A tabs consistent with Screen 3.
   Request summary once per user action with a fresh idempotency key, then poll
   the returned summary resource until `READY`/`FAILED`; do not duplicate
   requests during re-renders.
3. Render validated summary Markdown with safe rendering (no raw HTML by
   default); display retryable failures without presenting invalid output as a
   successful summary.
4. Implement Q&A form and in-page turn display. Render citations as buttons or
   links with page/section labels; activation reveals the exact cited excerpt
   in an accessible details/highlight panel without inventing a source route.
   Render insufficient evidence as a clear limitation, not an empty answer.
5. Handle `401`, `404`, `409`, `429`, `502`, `503`, and `504` explicitly, retain
   keyboard/screen-reader support, and verify responsive behavior at the
   Chapter 4 layout breakpoints.

### Phase E — Acceptance, migration, and operations verification

1. Run targeted backend unit/API tests, PostgreSQL pgvector integration tests,
   frontend tests, production build/type-check, and diff/format checks.
2. Apply the migration to PostgreSQL with pgvector enabled; verify dimension,
   index, ingestion embedding writes, vector ranking/filtering, summary worker
   restart recovery, and cleanup on document deletion.
3. Exercise one supported document end-to-end with the configured provider:
   ingest/extract/embed -> READY -> summary accepted/polled to READY -> grounded
   question with a resolvable citation -> unrelated question abstains.
4. Verify provider outage/timeout/invalid output produce explicit contract
   errors and no answer/citation fabrication; inspect logs for secret/content
   leakage.
5. Update README and this plan with exact commands/results, provider/model
   configuration, dimension and migration/backfill notes, plus any unverified
   environment limitation.

## 4. Test intent and acceptance matrix

| ID | Requirement / contract | Required evidence |
|---|---|---|
| S1 | FR-04 summary eligibility and ownership | Only an owned `READY` document accepts summary creation; foreign IDs return `404`, invalid state returns contract `409`. |
| S2 | FR-04 asynchronous summary lifecycle | `202 SummaryAccepted`, durable job, polling transitions, validated non-empty Markdown only on `READY`, safe failure code on `FAILED`, idempotency prevents duplicate work. |
| S3 | FR-05 embedding generation | Every searchable chunk has a finite vector matching the configured dimension; provider errors fail explicitly; no document reaches `READY` with missing embeddings. |
| S4 | FR-05 vector similarity and isolation | PostgreSQL pgvector integration proves nearest relevant chunks and enforces both `user_id` and `document_id` filters. |
| S5 | FR-05 grounded answer and citations | Answer uses retrieved context; every citation resolves to one of the retrieved chunks and returns its exact excerpt/page/section; fabricated IDs are rejected. |
| S6 | FR-05 insufficient evidence | Below-threshold/no-result retrieval returns `200` with `status=insufficient_evidence`, `answer=null`, `citations=[]`, and `code=INSUFFICIENT_EVIDENCE`. |
| S7 | AI error contract and privacy | Unavailable/timeout/malformed output map to defined `503`/`504`/`502`; no raw prompt, document text, token, or provider secret is logged or returned. |
| S8 | OpenAPI traceability | Assert canonical `/summaries`, `/summaries/{summary_id}`, and `/questions` paths/operation IDs, Bearer security, schemas, response codes, and no unapproved route aliases. |
| S9 | Screen 3 experience | Frontend tests verify protected navigation, Summary/Q&A tabs, Markdown, polling states, pending/error/abstain UI, citations and accessible excerpt reveal. |
| S10 | Existing behavior and deletion | Auth and Document Hub regressions stay green; deletion prevents retrieval, cancels queued derived work, and removes summary/embedding content per the deletion policy. |

### FR-04 / FR-05 traceability

| PRD acceptance criterion | Slice 3 coverage | Evidence |
|---|---|---|
| Only a ready document can be summarized | Direct | S1, S2 |
| Summary is based on selected document and contains key content | Direct; prompt context restricted to selected document and output validated | S2, S7 |
| Invalid or empty AI output is not successful | Direct | S2, S7 |
| Question is associated with selected document | Direct; document ID and owner scope the retrieval | S4, S5 |
| Relevant document content is used before generation | Direct | S3, S4 |
| Answer is grounded in available document content | Direct; valid citations must identify retrieved chunks | S5 |
| Insufficient evidence is clearly communicated | Direct and contract-shaped | S6, S9 |

Do not claim FR-04/FR-05 complete based solely on a successful provider call.
Readiness, ownership, persisted embeddings, citation grounding, abstention,
error handling, and the actual PostgreSQL retrieval path are acceptance
requirements.

## 5. Definition of done

- User approval resolved the canonical API route discrepancy, production AI
  provider/model, embedding dimension, vector metric/index, evidence threshold,
  and citation interaction boundary.
- Alembic migration and re-embedding/backfill strategy safely handle existing
  Slice 2 documents and fixed-dimension pgvector data.
- `READY` guarantees all chunks required for retrieval have valid embeddings;
  vector retrieval is bounded and scoped to the authenticated owner and
  selected document.
- Summary request/polling and Q&A response match the OpenAPI schemas and error
  codes; summaries are non-empty/validated and answers cite only retrieved
  evidence or abstain exactly as specified.
- Screen 3 supports summary and Q&A flows, accessible citation excerpt reveal,
  loading/failure/insufficient-evidence states, and responsive layout.
- S1-S10 pass; PostgreSQL/pgvector migration and integration checks pass; and
  the configured-provider end-to-end smoke test passes. Local automated tests
  pass, but live database/provider verification is still pending and is not
  claimed as complete.
- Slice 1/2 authentication, ownership, deletion, and frontend behavior remain
  covered and green; no later-slice quiz/analytics features are included.

## 6. P6.2 implementation and verification evidence

The user approved Slice 3 and selected the provider, model, vector dimension,
retrieval/index settings, and citation interaction recorded above. The
implementation uses the canonical Chapter 5 summary and question routes and
does not add `/summary` or `/qa` aliases. TDD was followed in RED-GREEN-VERIFY
order: backend and frontend tests were added and first confirmed failing
against the missing Slice 3 behavior, then implementation was added and the
suite rerun.

| Verification | Result |
|---|---|
| Backend full test suite (`python -m pytest tests`) | **48 passed**; one existing Starlette/httpx deprecation warning |
| Frontend full test suite (`npm test`) | **19 passed** |
| Frontend production build (`npm run build`) | **Passed**, including Next.js lint/type checks; dynamic `/documents/[documentId]` route emitted |
| Dependency install audit output | **8 reported vulnerabilities**: 4 moderate, 2 high, 2 critical; no automatic audit fix was applied |
| Offline migration generation (`alembic upgrade head --sql`) | **Passed** through migration `20261010_0003`; validates SQL generation only, not execution against PostgreSQL |
| Python syntax checks for new AI/API/service files | **Passed** |
| Live PostgreSQL/pgvector migration and retrieval integration | **Not run**: Docker is not installed in the environment |
| OpenAI-backed ingestion/summary/Q&A smoke test | **Not run**: no configured provider credentials were available |

The automated tests cover embedding validation and ranking, compiled cosine
query/filter behavior, endpoint authentication/ownership and response
contracts, summary jobs, citation validation, insufficient-evidence behavior,
and Screen 3 Markdown/citation/abstention states. They do not substitute for
executing the migration and pgvector query against a live PostgreSQL instance.
The editor's selected Python environment also lacks the backend dependencies,
so Pylance reports unresolved `httpx`, `sqlalchemy`, and `fastapi` imports;
this is an interpreter-environment limitation, not a successful project-wide
type-check claim.

---

# P6.1 — Slice 4: AI Quiz Engine & Quiz Player

**Status:** Approved and implemented. Mock-backed/local verification passed;
live PostgreSQL/provider verification remains outstanding.

## 1. Goal and delivery boundary

Deliver PRD FR-06 quiz generation and FR-07 quiz completion/evaluation for
authenticated students and their own `READY` documents. Quiz generation is a
durable asynchronous AI job. Generated questions must be grounded in the
selected document, structurally validated before persistence, and returned to
the player without answer keys. Starting and submitting attempts must be
owner-scoped, persisted, safely repeatable, and graded deterministically by the
server. Screen 4 provides setup, a navigable quiz player, and a reviewable
result with explanations and source citations.

Source baseline: [Chapter 3 PRD](../../docs/NoteWise_Chapter3/docs/3.2-product-requirements.md),
[Screen 4 design brief](../../chapter-04-ai-for-product-design/docs/product-design-brief.md),
[Screen 4 concept](../../chapter-04-ai-for-product-design/design/concepts/screen-4-quiz-concept.html),
[Chapter 5 OpenAPI](../../chapter-05-ai-for-software-design-architecture/design/openapi.yaml),
and [data model](../../chapter-05-ai-for-software-design-architecture/design/data-model.mmd).

### Included

- Generate quizzes from an owned, `READY` document using the configured
  generation provider and the existing chunk, citation, and AI-provider
  boundaries from Slice 3.
- Queue generation and validation using the existing database-backed
  processing-job/lease/retry system. Persist quiz status and safe failure code;
  persist only a complete, validated quiz.
- Support the approved Screen 4 question types: multiple choice, true/false,
  and fill-in-the-blank. Each persisted question includes its private answer
  key, explanation, position, and source chunk reference. Public quiz/attempt
  responses never disclose answer keys or grading rubrics.
- Add an owner-scoped quiz fetch, attempt creation and retrieval, and
  single-submission grading flow. Repeated identical submission returns its
  original result; a different submission after completion returns
  `ALREADY_SUBMITTED`.
- Persist each attempt and each submitted/skipped answer. Calculate score and
  return correct/incorrect feedback, explanations, and source citations from
  the stored quiz content; do not ask the AI to grade a submitted answer.
- Add protected Screen 4 setup/player/result experience with question
  navigation, selection persistence while the attempt is active, progress,
  submit confirmation, result percentage, skipped/correct/incorrect counts,
  and per-question answer/explanation/citation review.
- Preserve Slice 1–3 authentication, user/document ownership, deletion policy,
  rate-limiting/error conventions, and document source privacy.

### Explicitly out of scope

- FR-08 analytics/weak-topic analysis and later recommendation/history
  dashboards. A result may be persisted for later analysis, but Screen 4 will
  not implement the “Analyze Weak Topics” action as if that later slice exists.
- Persistent timer enforcement, retake-history UI, quiz editing/sharing,
  multi-document quizzes, streaming generation, teacher/administrator
  controls, and AI-based grading.
- Returning answer keys before submission or exposing document chunks beyond
  citations already selected for a question.

## 2. Contract and design decisions

The task's example endpoints differ from the approved Chapter 5 OpenAPI. This
plan treats the OpenAPI as the route/schema source of truth and proposes no
undocumented route aliases:

| Capability | Canonical OpenAPI operation | Contract behavior |
|---|---|---|
| Request generation | `POST /api/v1/documents/{document_id}/quizzes` (`createQuiz`) | Bearer-authenticated, optional `Idempotency-Key`, `QuizCreateRequest`, `202 QuizAccepted` with `quiz_id`, status, and `job_id` |
| Read quiz | `GET /api/v1/quizzes/{quiz_id}` (`getQuiz`) | `200 Quiz`; only public question fields, never `answer_key` or grading rubrics |
| Start player attempt | `POST /api/v1/quizzes/{quiz_id}/attempts` (`startQuizAttempt`) | `201 QuizAttempt`; creates an `IN_PROGRESS` attempt and returns public questions |
| Restore/read attempt | `GET /api/v1/quiz-attempts/{attempt_id}` (`getQuizAttempt`) | `200 QuizAttempt`; owner-scoped, answer-key-free, with nullable result |
| Submit and grade | `POST /api/v1/quiz-attempts/{attempt_id}/submit` (`submitQuizAttempt`) | Optional `Idempotency-Key`; `200 QuizResult`; same replay returns same result, different replay returns `ALREADY_SUBMITTED` |

The requested `/api/v1/quizzes/generate` and
`POST /api/v1/quizzes/{id}/submit` do not exist in the contract. The canonical
flow also requires an explicit attempt resource before submission; do not
collapse quiz and attempt IDs or bypass that lifecycle.

The following contract changes and behavior decisions were approved before
implementation:

| Difference | PRD / Screen 4 | Approved contract / behavior |
|---|---|---|---|
| Question type configuration | FR-06 requires the student to configure type; Screen 4 offers MCQ, True/False, and Fill-in-the-Blank | `QuizCreateRequest.question_types` is a required, non-empty unique list of the three supported types |
| Minimum question count | Screen 4 shows 5–20 | `question_count` is constrained to 5–20; setup defaults to 10 |
| Score denominator/precision | FR-07 requires a consistent percentage | `correct_count / total quiz question count * 100`, including skipped items as incorrect, rounded to two decimal places |
| Fill-in-the-blank grading | Screen 4 includes this question type | Deterministic exact match after Unicode NFC normalization, trimming/collapsing whitespace, and case-folding; no semantic/AI grading |
| Timer and elapsed time | Screen 4 marks timer optional and result includes time | Timer/elapsed-time UI is deferred because the result contract does not expose duration |

The source design's “Save Result” action is redundant with the OpenAPI's
persisted submit result; submitting saves automatically. Question citations
must resolve to chunks from the selected document. The result view may show
the source citation and excerpt returned for each question but must not reveal
answers until the attempt has been submitted.

## 3. Implementation phases (TDD)

### Phase A — RED: contract-first tests

1. Add API contract tests for the canonical paths and operation IDs,
   authentication, idempotency headers, request/response schemas/statuses,
   and the exact quiz → attempt → submit lifecycle. Assert the task's
   non-contract aliases are not accidentally introduced unless OpenAPI is
   explicitly revised and approved.
2. Add failing service/API tests for quiz generation acceptance, document
   ownership and `READY` enforcement, worker completion/failure, and
   idempotency/retry behavior. Stub the provider and never call an external AI
   service in automated tests.
3. Add validation tests for every question type: required prompt/options,
   option uniqueness and correct-option membership, true/false answer shape,
   fill-blank accepted answers, non-empty explanation, citation membership in
   source chunks, and rejection of unsupported/duplicate/malformed questions.
   Invalid output must not be partially persisted or reported as `READY`.
4. Add security tests proving `GET Quiz`, start/read attempt, and submit all
   return non-disclosing `404` for another user's resources. Assert neither
   quiz nor attempt responses reveal `answer_key`, accepted fill-blank
   answers, or grading rubrics before a submitted result.
5. Add grading tests for all question types, correct/wrong/skipped answers,
   denominator and rounding boundaries, duplicate/foreign question IDs,
   invalid answer types, all-skipped and empty-quiz rejection, persisted
   answer rows, and score/result consistency.
6. Add submission state/idempotency tests: first submission persists exactly
   one attempt result; identical replay returns the stored result; conflicting
   replay returns `409 ALREADY_SUBMITTED`; concurrent submissions cannot
   grade or persist twice.
7. Add frontend tests first for setup validation/configuration, generation
   processing/failure, player navigation and answer selection, attempt
   restore, submit confirmation/pending/errors, and result rendering including
   explanations and citations. Verify no correct answer is shown before
   submission and keyboard/screen-reader controls are usable.
8. Add PostgreSQL migration/integration coverage for new quiz tables,
   uniqueness/check constraints, foreign keys, deletion behavior, concurrent
   submission protection, and transactionally persisted grading. SQLite
   route tests alone are not evidence for those database guarantees.

### Phase B — Models, migration, and durable generation

1. Inspect current migration head, `ProcessingJob` job types/lease recovery,
   document deletion cleanup, and SQLAlchemy model conventions. Reuse these
   facilities; do not add a second worker or duplicate persistence framework.
2. Add `Quiz`, `QuizQuestion`, `QuizAttempt`, and `QuizAnswer` models matching
   Chapter 5's `quizzes`, `quiz_questions`, `quiz_attempts`, and `quiz_answers`
   entities, with user/document ownership, question positions, private answer
   keys, explanation, citation chunk, attempt counts/score/timestamps, and
   submitted answers.
3. Add an Alembic migration with appropriate FK/index/unique/check
   constraints, job-type linkage/idempotency, and an explicit policy for
   document deletion. Deleting a source document must prevent quiz access or
   generation/retrieval of derived source content; preserve attempt history
   only when consistent with the approved data model and privacy policy.
4. On create, validate owned document status `READY` and request fields,
   apply rate limits, use a request hash with the existing idempotency
   mechanism, and atomically create a `QUEUED` quiz plus durable job before
   returning `202`.
5. In the worker, collect bounded, representative source chunks from only
   that document and user; call the configured generation provider with
   strict structured output; validate every generated question and citation;
   persist all questions and set `READY` atomically only after the full quiz
   passes validation. Provider outage, timeout, invalid output, and insufficient
   usable source must set an explicit safe terminal status/code without
   exposing prompts or document text in logs/errors.
6. Make repeated accepted requests idempotent and worker retries safe. Ensure
   partial question sets cannot appear as usable quizzes; worker lease
   recovery must not duplicate or reorder question positions.

### Phase C — Public quiz, attempt, and grading APIs

1. Implement `GET Quiz` with stable question ordering and only
   `PublicQuizQuestion` fields plus citation metadata. Explicitly exclude
   answer keys in schemas and serialization.
2. Implement attempt creation after verifying quiz ownership and `READY`
   state. Persist `IN_PROGRESS`, return only public question data, and make
   attempt creation semantics explicit if the caller retries (idempotency or
   client-generated request key only if approved by the contract).
3. Implement owner-scoped attempt read for reload/recovery. Return submitted
   `result` only after `SUBMITTED`; never expose private grading material
   through ORM serialization or error details.
4. Implement strict submit validation: each supplied question ID must belong
   to the attempt's quiz, appear once, and carry an answer type allowed by
   that question. Omitted questions become skipped; reject invalid payloads
   without changing attempt state.
5. Grade exclusively against stored answer keys using the approved
   deterministic per-type rules. Persist each submitted/skipped answer and
   the final attempt counts, score, `submitted_at`, and result feedback in one
   transaction. Use row locking/conditional state transitions to prevent
   double submission under concurrency.
6. Enforce replay semantics and idempotency exactly as the OpenAPI contract
   specifies. For every result citation, resolve only the question's persisted
   source chunk from the same document; do not trust client-supplied citations.
7. Return explicit contract errors for unauthorized, foreign/nonexistent,
   non-ready, duplicate, invalid, or already-submitted requests. Do not return
   success-shaped partial results or use AI to assign the score.

### Phase D — Screen 4 Quiz Setup, Player, and Results

1. Add protected navigation from the owned Document Hub/document learning
   page into quiz setup with the selected document context.
2. Provide setup fields for approved question count, supported question
   type(s), difficulty, and optional topic. Validate before request; retain
   settings on recoverable failure. Show AI skeleton/queued/processing states
   and poll the quiz resource until `READY`/`FAILED`, with retry messaging that
   does not duplicate a quiz.
3. Once ready, create an attempt and render question progress, prompt, type-
   appropriate radio/checkbox/text input, and Previous/Skip/Next controls.
   Preserve answers across navigation and reload through the attempt resource;
   show submit confirmation and prevent duplicate in-flight submissions.
4. Render result percentage, correct/answered/skipped counts and per-question
   review. Reveal selected and correct answers, explanations, and citations
   only from the submitted result. Citation controls reveal an accessible
   source excerpt/page/section. Clearly distinguish skipped from incorrect.
5. Handle `401`, `404`, `409`, `422`, `429`, AI/processing errors, network
   retry, empty/failed generation, and already-submitted state without losing
   user answers or disguising failure as success.
6. Keep “Analyze Weak Topics” outside this slice; persisted attempts/results
   provide the foundation for the later analytics slice. Ensure responsive
   layout, keyboard operation, focus management, and non-color-only feedback.

### Phase E — Acceptance and operations verification

1. Run targeted backend tests, frontend tests, frontend production
   build/type-check, Python lint/type checks available in the configured
   environment, migration generation, and diff/format checks.
2. Apply migrations to PostgreSQL and test quiz/job persistence, transaction
   rollback on invalid generation, worker restart/lease recovery, uniqueness,
   and source-document deletion behavior.
3. Exercise configured-provider generation from a ready fixture/document,
   verify all questions/citations map to that source, start an attempt, submit
   correct/incorrect/skipped answers, then read the persisted identical result.
4. Test malformed/out-of-source AI output, provider outage/timeout, duplicate
   submit race, cross-user access, and answer-key exposure; verify safe error
   codes and that logs contain no prompts, source text, answer keys, or
   provider credentials.
5. Update README and this plan with the final approved contract decisions,
   migration/provider configuration, exact commands/results, and any live
   environment limitation. Do not mark FR-06/FR-07 complete on mocked tests
   alone.

## 4. Test intent and acceptance matrix

| ID | Requirement / contract | Required evidence |
|---|---|---|
| Q1 | FR-06 document eligibility and ownership | Only an owned `READY` document accepts generation; foreign IDs return non-disclosing `404`; invalid state returns contract `409`. |
| Q2 | FR-06 generation lifecycle | Canonical create operation returns `202` with durable `quiz_id`/`job_id`; polling reaches `READY` or explicit `FAILED`; retries do not create duplicate questions/jobs. |
| Q3 | FR-06 grounding and validation | Each accepted question is structurally valid, has a source-grounded explanation/citation from the selected document, and all invalid/unsupported output is rejected before `READY`. |
| Q4 | Public/private quiz contract | Quiz and in-progress-attempt responses include required public fields but never answer keys, accepted answers, or grading rubrics. |
| Q5 | FR-07 answer capture and ownership | An owned `IN_PROGRESS` attempt accepts each own quiz question at most once; foreign IDs, duplicate IDs, and malformed answer values fail without partial mutation; omitted questions are skipped. |
| Q6 | FR-07 deterministic grading | Correct, incorrect, and skipped answers produce exact counts and the approved percentage/rounding; grading uses persisted server-side keys, never provider/client scoring. |
| Q7 | FR-07 attempt/result persistence | Attempt and answer rows plus score/submission timestamp are committed atomically and survive reload; DB constraints/state transition prevent duplicate grading. |
| Q8 | Submit idempotency/state | Identical replay returns the original result; a changed payload after submission returns `409 ALREADY_SUBMITTED`; concurrent submissions persist one result. |
| Q9 | OpenAPI traceability | Assert operation IDs, canonical paths, security, idempotency, validation, status codes, schemas, quiz states, public question fields, result shape, and no unapproved aliases. |
| Q10 | Screen 4 user journey | Frontend tests cover setup, processing, player navigation/answers, reload, submit, result explanation/citation, errors, accessibility, and no pre-submit answer leakage. |
| Q11 | Existing behavior/data privacy | Slice 1–3 auth, document ownership/deletion, summaries/Q&A regressions remain green; deleting a source does not leave accessible quiz source content. |

### FR-06 / FR-07 traceability

| PRD acceptance criterion | Slice 4 coverage | Evidence |
|---|---|---|
| Student selects a document | Direct: setup starts from an owned Document Hub/learning context | Q1, Q10 |
| Question count, question type, and difficulty configurable | Direct only after the request-schema discrepancy is resolved | Q2, Q9, Q10 |
| Optional topic selectable | Direct through `QuizCreateRequest.topic` | Q2, Q10 |
| Generated questions checked against source content | Structural validation, same-document citations, and rejection of unsupported output before `READY` | Q3 |
| Invalid questions rejected; valid quiz persisted | Atomic full-set validation and durable quiz/job lifecycle | Q2, Q3, Q7 |
| Answers captured | Owner-scoped persisted `QuizAnswer` records; omitted questions recorded as skipped | Q5, Q7 |
| Score calculated consistently | Deterministic server-side per-type comparison and approved denominator/rounding | Q6 |
| Correct/incorrect results available | Submitted `QuizResult` feedback with correctness, explanation and citation | Q6, Q10 |
| Attempt and result persisted | Atomic transaction, reloadable result, PostgreSQL integration evidence | Q7 |
| Results available for later analysis | Persisted attempts/results; analytics implementation remains later-slice scope | Q7, Q11 |

The approved schema changes close the question-type and question-count gaps.
Do not expose correct answers before submission or mark a quiz ready when any
persisted question lacks a validated answer key, explanation, or source
citation. FR-06/FR-07 live integration acceptance remains outstanding until
PostgreSQL and configured-provider verification can be performed.

## 5. Definition of done

- Human approval on 2026-10-11 resolves canonical route use, question-type and
  question-count schema changes, deterministic grading rules, timer scope, and
  source-content deletion behavior.
- A valid quiz is generated only from an owned `READY` document, grounded in
  that document, fully validated, persisted atomically, and retrievable without
  answer keys.
- Attempts are owner-scoped, resumable, and submitted once; grading is
  deterministic, transactionally persisted, and replay-safe.
- Result feedback includes accurate score/counts, explanations, and citations;
  no AI-generated grading or unsupported question claims are presented as
  verified.
- Screen 4 supports accessible setup/player/result and explicit lifecycle,
  validation, and recovery states.
- Focused backend/frontend tests, the full suites, frontend production build,
  OpenAPI validation, offline PostgreSQL migration generation, and diff checks
  are recorded below. PostgreSQL runtime/concurrency/deletion checks and a
  configured-provider generation smoke test remain outstanding.
- Slice 1–3 regression tests pass in the full backend and frontend suites; no
  analytics/recommendation behavior is implemented ahead of its slice.

## 6. P6.2 verification evidence

- RED: backend quiz tests initially failed because the quiz routes and workflow
  were absent; the frontend quiz test could not resolve the not-yet-created
  Screen 4 page.
- Focused backend workflow and contract tests:
  `python -m pytest tests\test_quiz_workflows.py -q` — **6 passed**.
- Full backend suite:
  `python -m pytest tests -q` — **54 passed**.
- Full frontend suite: `npm test` — **22 passed** across 7 test files,
  including quiz setup/player/results, saved-attempt restoration, and Document
  Hub quiz navigation.
- Frontend production build: `npm run build` — successful, including Next.js
  type validation and static generation of `/documents/[documentId]/quiz`.
- `python -m alembic upgrade 20261011_0004 --sql` — successful
  PostgreSQL-dialect SQL generation through the quiz migration. The migration
  was not applied to a live PostgreSQL service; composite-FK, locking, and
  concurrency behavior remain unverified against PostgreSQL.
- The Chapter 5 OpenAPI YAML parsed as OpenAPI 3.1.0 with 18 paths. The backend
  contract test checks quiz operation IDs, canonical paths, bearer security,
  idempotency headers, question-count/type constraints, and result schema.
- `git diff --check` — clean. SQLite-backed API tests use mocked providers;
  no configured-provider smoke test was run. Thus provider-grounding quality
  and live PostgreSQL runtime acceptance remain unverified.
- The frontend build emitted only the existing Vite CJS Node API deprecation
  notice in test runs; backend tests emitted a Starlette/httpx deprecation
  warning. Neither caused a test/build failure.

# P6.1 — Slice 5: Analytics, Weak Topics & Personalized Recommendations

**Status:** Approved on 2026-10-11 and implemented; local verification passed.
Live PostgreSQL migration application remains unverified.

## 1. Goal and delivery boundary

Give an authenticated student a reliable view of learning performance,
evidence-qualified weak topics, and actionable recommendations grounded in
their own available materials. Preserve the completed Slice 1–4 behavior,
including server-side authorization, submitted-attempt grading, and private
document content.

### Included scope

- Add overview metrics for a student's mean submitted quiz score, owned
  document count, and submitted quiz-attempt count.
- Analyze submitted `quiz_attempts` and their `quiz_answers` to calculate
  topic accuracy, expose insufficient evidence, and label a topic weak only
  when it has at least two submitted attempts and its non-skipped answer
  accuracy is strictly below 60%.
- Generate owner-scoped, explainable study actions from that evidence and
  link an action to an available source location. Do not fabricate a source
  when no eligible owned material is available.
- Build protected Screen 5 Analytics with KPI cards, accessible weak-topic
  severity indicators, recommendation action cards, loading/error/empty/
  insufficient-evidence states, and a direct action to open its cited source.
- Cover FR-11 by exposing the existing canonical paginated history operation
  and adding the corresponding minimal protected history list UI (Screen 7).
  This additional UI is required for the student to review prior activity;
  durable attempt/history records alone do not provide that user capability.
- Add backend service/API/contract and frontend component/API tests before
  implementation, then validate the approved OpenAPI baseline and regressions.

### Explicitly out of scope

- AI-generated diagnoses, AI grading, ungrounded suggestions, or external
  provider calls to compute analytics or recommendations.
- Changing how Slice 4 calculates and persists an individual quiz result.
- Trends, date-range controls, cohort comparisons, exports, dismiss/feedback
  actions for recommendations, and a new recommendation-generation job.
- Any access to another student's attempts, documents, topics, chunks, or
  recommendations.

## 2. Source baseline and approval gates

Use the [Chapter 3 PRD](../../docs/NoteWise_Chapter3/docs/3.2-product-requirements.md),
[feature specification](../../docs/NoteWise_Chapter3/docs/3.5-feature-specification.md),
[Screen 5 Analytics concept](../../chapter-04-ai-for-product-design/design/concepts/screen-5-analytics-concept.html),
[Screen 6 Recommendations concept](../../chapter-04-ai-for-product-design/design/concepts/screen-6-recommendations-concept.html),
[Screen 7 History concept](../../chapter-04-ai-for-product-design/design/concepts/screen-7-history-concept.html),
[Chapter 5 OpenAPI](../../chapter-05-ai-for-software-design-architecture/design/openapi.yaml),
[Chapter 5 architecture](../../chapter-05-ai-for-software-design-architecture/design/architecture.md),
and [Chapter 5 data model](../../chapter-05-ai-for-software-design-architecture/design/data-model.mmd)
as the source baseline. The approved additive OpenAPI changes bring the
contract to 20 paths while preserving the existing canonical
`/analytics/accuracy`, `/analytics/weak-topics`, `/recommendations`, and
`/learning-history` operations.

| Concern | Current source contract / implementation | Approved resolution |
|---|---|---|
| Overview endpoint and KPI fields | Existing `/analytics/accuracy` returns accuracy and answer counts; it has no overview operation or document/quiz counts. | Added `GET /api/v1/analytics/overview`; `average_score` is the nullable arithmetic mean of submitted attempt scores, `document_count` excludes deleting/deleted documents, and `completed_quiz_count` counts submitted attempts including retakes. `/analytics/accuracy` remains the separate answer-weighted accuracy contract. |
| Weak-topic algorithm | OpenAPI `GET /api/v1/analytics/weak-topics` returns `WeakTopicPage`; the PRD/architecture require at least two submitted attempts per topic, exclude skipped answers from accuracy, and require accuracy `<60%`. | Preserve this canonical route/schema and test every threshold/evidence boundary. `is_weak` is false and `sufficient_data` false below the two-attempt minimum; exactly 60% is not weak. |
| Recommendation route | OpenAPI uses `GET /api/v1/recommendations` (`listRecommendations`), not `/api/v1/analytics/recommendations`. | Preserve `/recommendations`, add no alias, and wire Screen 5 to the canonical route. |
| Source deep-link | The previous `Recommendation` schema had page references but no chunk identifier. | Added nullable `chunk_id` and `GET /api/v1/documents/{document_id}/chunks/{chunk_id}`; the source response is owner-scoped and only available for a ready document. |
| FR-11 history | OpenAPI has `GET /api/v1/learning-history` with pagination and optional `event_type`; the data model defines `learning_history`. | Added the owner-scoped history API and protected Screen 7 list. The migration snapshots existing uploads, summaries, and submitted quiz attempts; new Q&A events record safe status/length metadata without saving prompt text. |
| Topic attribution | Slice 4's `Quiz` has one optional `topic`; `QuizQuestion` has no per-question topic. | Group evidence by the quiz's normalized topic. Untagged quizzes do not create a topic classification. Show the evidence limitation when a topic has fewer than two submitted attempts; do not infer question-level topics. |
| Persisted analytics entities | The Chapter 5 ERD includes `weak_topics`, `recommendations`, and `learning_history`; these were not implemented before this slice. | Added the three owner-scoped tables and deterministic snapshot refresh in the quiz-submission transaction and analytics read path. |

**Approval record:** the user approved the plan on 2026-10-11, including the
additive overview/chunk deep-link contract changes, canonical
`/recommendations` route, Screen 7 history support, and metric definitions.

## 3. Metric and recommendation rules

### Overview

- `average_score`: arithmetic mean of `QuizAttempt.score` for attempts whose
  status is `SUBMITTED` and whose score is present; use `null` when no
  submitted score exists. Each submitted attempt has equal weight. This is
  intentionally distinct from `/analytics/accuracy`, whose contract is based
  on correct versus answered non-skipped answers.
- `document_count`: count all documents owned by the current user that remain
  in the database, regardless of processing status. Do not include another
  user's records or soft-deleted records if the implementation has such a
  state.
- `completed_quiz_count`: count submitted quiz attempts (not distinct quiz
  definitions); a retake is another completed learning activity.
- Compute aggregates from database records and return stable numeric/count
  values; avoid deriving these KPIs from client-side document/quiz lists.

### Weak topics

- Use only `SUBMITTED` attempts and associate an attempt with its quiz topic.
- Normalize topic labels by trimming and collapsing whitespace, then
  case-folding for grouping; retain a deterministic display label from stored
  quiz data. Do not merge semantically similar but differently named topics.
- Count distinct submitted attempts per topic. `attempts >= 2` is necessary
  for `sufficient_data: true`; one wrong answer or one attempt never labels a
  topic weak.
- Define `answered_count` as the number of non-skipped answers. Calculate
  accuracy as `correct non-skipped answers / answered non-skipped answers *
  100`; skipped answers do not dilute this percentage and remain separately
  reported where the response schema supports them.
- A topic is weak only when there is sufficient evidence and accuracy `< 60`.
  At exactly `60`, it is not weak. If there are no answered responses,
  accuracy is null and the topic is not weak.
- Return the canonical `WeakTopicPage` shape, including evidence sufficiency
  and a human-readable reason where supported. Sort weak topics deterministically
  by ascending accuracy then normalized topic.

### Recommendations and source navigation

- Generate deterministic, rule-based action text and reason from the student's
  weak-topic evidence and recent submitted activity; show the evidence (topic,
  accuracy, attempts) behind each weak-topic action.
- Link only to a `READY` document owned by the current user and a persisted
  chunk from that document. Prefer the citation chunk(s) of incorrect answers
  for the topic; if no safe relevant chunk exists, return an action without a
  source link and state why no source is available.
- Never return chunk text or document content in a recommendation payload.
  Return IDs and page metadata only; the protected document route must resolve
  ownership before showing the passage and highlight/scroll to the selected
  chunk.
- Define stable ordering and avoid duplicate recommendations for the same
  user/topic/action evidence snapshot. Persist only the metadata required by
  the approved schema and do not retain copied chunk content.

### Learning history

- Return the contract's paginated `LearningHistoryPage`; enforce ownership
  from the verified user on every query and allow only the documented event
  type filter.
- Include submitted quiz attempts/scores/topics and the already-defined
  document/summary/Q&A activity where records exist; use immutable title/detail
  snapshots where document deletion must not erase history.
- Do not fabricate prior events from current state. Empty history is a valid
  successful response and must have a clear UI state.

## 4. Implementation phases (TDD)

### Phase A — RED: contract and behavior tests

1. Add contract tests for the approved operation IDs, canonical paths,
   bearer security, query parameters, response schemas, and status codes.
   Assert no `/analytics/recommendations` alias is introduced unless the
   OpenAPI decision explicitly changes.
2. Add overview service/API tests for no records, one and multiple submitted
   attempts, a retake, in-progress attempts, null score, mixed document states,
   and cross-user isolation. Assert exact mean score, document count, and
   completed-attempt count.
3. Add weak-topic tests for `0/1/2` submitted attempts, no answers, skipped
   answers, all-correct/all-incorrect, below/equal/above 60%, duplicate topic
   labels after normalization, missing topic, and in-progress attempts.
4. Add recommendation tests proving relevance to a weak topic, deterministic
   ordering/deduplication, safe behavior without relevant material, no
   unowned/deleted/non-ready document or chunk links, and no source text in
   payloads.
5. Add history tests for pagination/filtering/order, empty history, correct
   event details, owner isolation, and document cleanup/title snapshots.
6. Add frontend tests before page implementation for the KPI cards, loading,
   partial/API failure, no-data states, weak-topic warning thresholds,
   insufficient evidence, recommendation source links, safe navigation, and
   paginated history.
7. Add PostgreSQL migration/integration tests for owner-scoped foreign keys,
   indexes, uniqueness/snapshot refresh, and transactional attempt-to-history/
   recommendation updates. SQLite tests alone are not evidence of these DB
   guarantees.

### Phase B — Persistence and query foundation

1. Review Slice 4 attempt submission transaction, document deletion behavior,
   migration head, ownership constraints, and existing test fixtures. Reuse
   the current SQLAlchemy/session/error/auth patterns.
2. Add the approved migration and typed models for any missing
   `learning_history` and `recommendations` entities; add or reconcile
   `weak_topics` with the approved ERD/persistence decision. Include
   owner-safe foreign keys, uniqueness, indexes, and deletion/snapshot
   semantics. Do not duplicate existing tables or rewrite prior migrations.
3. Add repository/service queries over submitted attempts, answers, quizzes,
   documents, and citation chunks. Always bind records to `current_user.id`;
   keep aggregation in SQL where practical and never load another user's
   rows for later in-memory filtering.
4. Extend the quiz submission transaction only for approved durable
   history/recommendation snapshots; ensure failed snapshot persistence
   cannot report a successful submission with inconsistent derived state.

### Phase C — Analytics and recommendation APIs

1. Add typed schemas matching the approved OpenAPI exactly, with no
   undocumented fields or error codes.
2. Implement the approved overview route, the canonical
   `/analytics/accuracy` and `/analytics/weak-topics` routes, and
   `/recommendations`; use the shared verified-user dependency and error
   envelope. Treat a user's empty dataset as a valid `200`, not an error.
3. Implement the canonical paginated `/learning-history` route with only
   contract-supported filters and stable pagination.
4. Keep weak-topic math in a pure unit-testable service. Keep recommendation
   selection deterministic and evidence-driven; validate every selected
   document/chunk against current ownership/readiness before responding.
5. Add no external AI provider dependency and no client-supplied owner ID.
   Return non-disclosing `404` for foreign resource-specific deep links.

### Phase D — Screen 5 and history UI

1. Add typed frontend clients for approved analytics, recommendations, and
   history operations using the existing authenticated API helper and
   established error/session behavior.
2. Add the protected Screen 5 route in the existing `(protected)` App Router
   group. Render three KPI cards (average score, owned documents, completed
   attempts), a weak-topic list with textual and color severity, and
   personalized action cards with visible reasons and source metadata.
3. Add an accessible deep-link flow to the document page: resolve the
   document first, identify the authorized chunk, scroll/focus it, and
   highlight it. Preserve a usable page-level link if the approved contract
   falls back to page ranges. Never put private chunk text in URL parameters.
4. Add a protected Screen 7 history list with pagination, quiz score/topic
   details, event type/date, loading/error/empty states, matching the supplied
   history concept. If the user declines this addition, record FR-11 UI as
   explicitly deferred rather than claiming complete FR-11 traceability.
5. Use semantic headings, keyboard-operable links, screen-reader labels for
   accuracy/severity, and non-color text labels. Avoid showing a weak label
   when evidence is insufficient.

### Phase E — Acceptance and regression verification

1. Validate the revised OpenAPI document and test generated/runtime schemas
   against the approved contract; assert all canonical routes and no aliases.
2. Run focused backend tests, focused frontend tests, migration SQL
   generation, full backend/frontend suites, frontend production build, and
   `git diff --check`.
3. Run PostgreSQL-backed migration/integration tests for database constraints,
   transaction behavior, and cleanup when the local environment supports
   PostgreSQL; record any unavailable live verification explicitly.
4. Confirm Slice 1–4 authentication, document ownership/deletion, RAG,
   summaries/Q&A, quiz generation, attempt submission, and result behavior
   remain unchanged.

## 5. Expected file touchpoints

- OpenAPI, only after separate approval: `chapter-05-ai-for-software-design-architecture/design/openapi.yaml`.
- Backend API: `notewise-app/backend/app/api/analytics.py` (or the existing
  router module if project conventions favor consolidation), registered in
  `app/main.py`.
- Backend models/schemas/services: `app/models/`, `app/schemas/`,
  `app/services/`; reuse `Quiz`, `QuizAttempt`, `QuizAnswer`, `QuizQuestion`,
  `Document`, `DocumentChunk`, `User`, `get_current_user`, and `get_db`.
- Database: next Alembic revision under `notewise-app/backend/alembic/versions/`;
  do not edit already-applied prior revisions.
- Backend tests: focused `tests/test_analytics_api.py`,
  `tests/test_analytics_services.py`, history coverage, contract tests, and
  PostgreSQL migration/integration coverage following existing naming.
- Frontend API/types: `notewise-app/frontend/src/lib/` and focused tests.
- Protected UI: `notewise-app/frontend/src/app/(protected)/analytics/` and
  `.../(protected)/history/`, with page/component tests; document deep-link
  handling belongs with the existing protected document detail route.
- Update the application README and this plan with approved decisions,
  migration details, exact validation commands/results, and outstanding
  environment limits after implementation.

## 6. Test intent and traceability

| ID | Requirement | Acceptance evidence |
|---|---|---|
| A1 | FR-08 overview | Exact owned-document count, submitted-attempt count, and mean submitted score; no in-progress attempt included; no-data score is null. The answer-weighted accuracy route retains its independent OpenAPI semantics. |
| A2 | FR-08 data privacy | All analytics queries use verified owner identity; foreign users' documents/attempts/answers cannot affect counts or response content. |
| A3 | FR-09 weak-topic qualification | Only submitted attempts; per-quiz topic grouping; at least two attempts; skipped answers excluded; accuracy strictly `<60%`; insufficient evidence and exact-60 boundary tested. |
| A4 | FR-09 explainability | Each weak result displays accuracy, evidence count/attempts, reason, and accessible severity; no unsupported diagnosis from one error. |
| A5 | FR-10 recommendation | Stable rule-based actions trace to student performance and show their reason; no hallucinated/unavailable material; source IDs/pages are validated and owner-scoped. |
| A6 | Source deep-link | Approved contract source identifier navigates to the correct authorized document passage/chunk and handles missing/deleted/unavailable sources safely. |
| A7 | FR-11 history | Paginated, owner-scoped history includes available quiz attempts/results/topics and documented activity snapshots; UI displays prior activities and empty/loading/error states. |
| A8 | OpenAPI | Runtime route, operation ID, security, parameter, response/status and error shape match the human-approved OpenAPI; no route aliases without approval. |
| A9 | Screen 5 | Frontend tests verify all three KPI cards, weak-topic colors plus text, recommendations and accessible links/states. |
| A10 | Persistence/integrity | Migration constraints, indexes, snapshot consistency, quiz-submission transaction and cleanup behavior verified against PostgreSQL where available. |
| A11 | Regression | Slice 1–4 backend/frontend tests and build continue to pass; no unauthorized data or answer keys are exposed. |

### FR-08 / FR-09 / FR-10 / FR-11 traceability

| PRD requirement | Planned coverage | Evidence |
|---|---|---|
| FR-08 overall performance visible | Screen 5 overview KPI; preserve `/analytics/accuracy` for non-skipped answer accuracy | A1, A2, A8, A9 |
| FR-08 topic performance when evidence is sufficient | Aggregate submitted answers by stored quiz topic and return evidence status | A3, A4 |
| FR-08 compare repeated attempts | Count submitted attempts and retain attempt-level scores/history | A1, A3, A7 |
| FR-08 communicate insufficient data | Explicit API `sufficient_data`/null accuracy and UI state | A3, A4, A9 |
| FR-09 one error is not enough | Require two submitted attempts per topic before weak classification | A3 |
| FR-09 explain why a topic needs attention | Return and render deterministic reason and evidence | A4 |
| FR-10 use results/topic performance/history | Derive deterministic recommendation from persisted student evidence | A5, A7 |
| FR-10 link relevant available materials | Return validated document/chunk reference and navigate to it | A5, A6 |
| FR-10 no fabricated material; reason shown; student chooses | Omit unsupported links, explain unavailable sources, make actions user-controlled | A5, A6, A9 |
| FR-11 preserve and review attempts/scores/topics | Paginated history endpoint and protected Screen 7 UI | A7 |
| FR-11 support later analytics/recommendations | Keep owner-scoped source records and durable snapshots | A2, A5, A7, A10 |

## 7. Definition of done

- The user approves this plan and resolves the listed OpenAPI, metric,
  source-link, persistence, and FR-11 UI decisions before implementation.
- All analytics and history routes enforce server-side owner scope and match
  the approved OpenAPI schemas exactly.
- Weak-topic classification follows the PRD/architecture evidence minimum
  and strict 60% threshold; skipped answers and in-progress attempts do not
  create false weak-topic labels.
- Screen 5 renders correct KPI values, explainable warnings, and actionable,
  owner-safe recommendation links with accessible loading/empty/error states.
- FR-11 has a working user-visible history view, or its deferral is explicitly
  approved and the traceability claim is narrowed accordingly.
- Focused tests, regressions, production build, OpenAPI validation, migration
  generation, and `git diff --check` pass; PostgreSQL limitations are stated
  accurately.
- No implementation has started until the human approval gate is complete.

## 8. P6.2 implementation and verification evidence

- TDD RED: the first focused backend run failed collection because the
  analytics model/API did not exist. The frontend tests failed to resolve the
  unimplemented analytics/history pages. The deep-link test failed because
  the document view did not read a `chunk_id`.
- Focused backend analytics, AI workflow, documents, and quiz workflow tests:
  `python -m pytest tests\test_analytics_api.py tests\test_ai_workflows.py tests\test_documents_api.py tests\test_quiz_workflows.py -q`
  — **34 passed** at the focused integration checkpoint.
- Full backend suite:
  `python -m pytest tests -q` — **60 passed**; one existing Starlette/httpx
  deprecation warning.
- Full frontend suite: `npm test` — **27 passed** across 9 test files.
- Frontend production build: `npm run build` — successful; Next.js type
  validation completed and `/analytics`, `/history`, and the dynamic
  document view were generated.
- `python -m alembic upgrade 20261011_0005 --sql` — successful PostgreSQL
  dialect SQL generation through analytics/history migration `20261011_0005`,
  including upload/summary/submitted-attempt history backfill. The migration
  was not applied to a live PostgreSQL instance.
- The updated Chapter 5 OpenAPI parsed as OpenAPI 3.1.0 with 20 paths,
  including overview, accuracy, weak topics, recommendations, learning
  history, and source-chunk navigation. Runtime contract tests assert the
  approved operation IDs, paths, security, and `chunk_id` response field.
- `git diff --check` — clean. PostgreSQL constraint, backfill, and concurrency
  behavior remain unverified against a live database.
- The frontend test runner emitted the existing Vite CJS Node API deprecation
  notice. Backend tests emitted the existing Starlette/httpx deprecation
  warning. Neither caused validation failure.
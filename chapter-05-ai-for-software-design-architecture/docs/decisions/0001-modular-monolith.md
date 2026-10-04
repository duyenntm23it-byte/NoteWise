# ADR 0001: Modular Monolith for the NoteWise API

- **Status:** Accepted
- **Date:** 2026-10-04
- **Decision owners:** NoteWise architecture

## Context

NoteWise has related capabilities for authentication, document ingestion,
retrieval-augmented Q&A, summaries, quizzes, analytics, recommendations, and
learning history. The target MVP deploys a Next.js static SPA, a FastAPI API,
and PostgreSQL with pgvector through Docker Compose. There is no current
requirement for independent deployment, independent team ownership, or
service-specific scaling.

Microservices would introduce network boundaries, distributed failure and
consistency handling, additional deployment configuration, and likely
messaging/observability infrastructure before those needs are demonstrated.

## Decision

Implement the backend as one FastAPI modular monolith with explicit modules:

- `auth`
- `documents`
- `learning`
- `analytics`
- `jobs`
- `ai` provider adapters and output validation

Modules own their schemas and persistence operations. Cross-module use occurs
through service interfaces/application orchestration rather than direct
repository imports. PostgreSQL is the shared transactional source of truth.
The API process runs a database-backed job loop; a separate broker and worker
service are not part of the MVP.

## Consequences

### Positive

- One API deployment and one database simplify local Compose, migrations, and
  transactions.
- The design has fewer network failure modes and operational dependencies.
- Domain module boundaries leave a path to extract services if measurements
  later justify it.

### Negative

- Modules share a release cycle and API process resources.
- A slow AI or ingestion workload can compete with request handling unless
  timeouts, bounded concurrency, and job isolation are enforced.
- The team must actively preserve module boundaries to avoid a coupled
  monolith.

## Guardrails

- Use durable `processing_jobs` rows with leases; never rely on an in-memory
  task as the sole record of work.
- Claim jobs transactionally with `FOR UPDATE SKIP LOCKED`, process outside
  the claim transaction, and recover expired leases.
- Make handlers idempotent, use bounded retries/backoff, and record safe
  terminal error codes.
- Keep provider calls behind `ai` adapters with explicit timeouts and schemas.
- Revisit service extraction only when operational metrics or team structure
  demonstrate a concrete benefit.

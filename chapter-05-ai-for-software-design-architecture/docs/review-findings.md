# P5.2 Review Gate — Findings and Resolutions

**Review status:** Accepted and incorporated into the architecture package
**Date:** 2026-10-04

| # | Priority | Finding | Resolution in approved package | Status |
|---|---|---|---|---|
| 1 | High | Quiz answer keys could leak through public quiz endpoints. | OpenAPI public quiz/attempt schemas omit `answer_key`; grading occurs server-side after submission. | Resolved |
| 2 | High | Ownership was not guaranteed across parent/child database records. | User-owned tables carry `user_id`; composite `(resource_id, user_id)` foreign keys and owner-scoped queries are required. Foreign and missing IDs both return `404`. | Resolved |
| 3 | High | In-process background work could disappear on API restart or be duplicated on retry. | Added durable `processing_jobs`, leases, startup recovery, `FOR UPDATE SKIP LOCKED`, idempotent handlers, bounded retries/backoff, and terminal error states. | Resolved |
| 4 | High | Local Storage JWT has an XSS exposure and token lifetime/revocation were unspecified. | ADR 0002 sets 15-minute access tokens, no refresh-token flow in MVP, HTTPS, CSP/XSS mitigations, and documents the accepted residual risk. | Resolved |
| 5 | Medium | AI errors, insufficient evidence, and citation validation lacked a consistent contract. | OpenAPI defines `insufficient_evidence`, citation structures, a common error envelope, and explicit provider/timeout/invalid-output errors. | Resolved |
| 6 | Medium | Summary, quiz, and document state transitions were incomplete. | Architecture defines allowed state transitions and terminal states; OpenAPI exposes lifecycle states. | Resolved |
| 7 | Medium | Weak-topic accuracy denominator and minimum evidence were unspecified. | Accuracy uses non-skipped answers; weak means strictly below 60%; at least two submitted attempts are required; insufficient data is explicit. | Resolved |
| 8 | Medium | Delete behavior for files, vectors, generated content, jobs, and history was unclear. | Delete enters `DELETING`, hides content, cancels work, and queues cleanup. Cleanup removes source/chunks/generated content, retains aggregate attempt/history snapshots, and marks an owner-scoped tombstone `DELETED`. | Resolved |
| 9 | Low | Vector dimension, retrieval filters, and model migration were unspecified. | ADR 0003 requires one configured fixed dimension per schema version, an explicit re-embedding migration, and owner/document/`READY` filters for retrieval. | Resolved |

## Residual implementation gates

These are implementation-time controls, not open architecture findings:

- Select and pin the embedding model/dimension before the first production
  migration.
- Set actual upload byte/page limits and AI provider deadlines in deployment
  configuration.
- Add integration tests that attempt cross-owner access and verify that quiz
  answer keys never appear before submission.
- Test job recovery by terminating the API while a lease is active, then
  verifying bounded retry and idempotent completion.
- Test deletion cleanup and confirm no file, chunk, summary content, question,
  or answer detail remains retrievable after completion.

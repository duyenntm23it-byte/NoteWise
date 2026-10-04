# ADR 0002: JWT Bearer Authentication with Owner-Scoped Resources

- **Status:** Accepted
- **Date:** 2026-10-04
- **Decision owners:** NoteWise architecture

## Context

The Next.js client is a static SPA and the target architecture specifies JWT
Bearer authentication stored in Local Storage. All personal documents,
learning records, quiz results, analytics, and recommendations must be
isolated by owner. A client-supplied `user_id` cannot be trusted for
authorization.

Local Storage is readable by JavaScript and therefore exposes tokens to
successful cross-site scripting (XSS). HttpOnly cookies reduce that exposure
but would change the specified client authentication mechanism and introduce
cookie/CSRF considerations.

## Decision

- `POST /api/v1/auth/register` and `/auth/login` issue a signed JWT access
  token.
- The token includes `sub` (UUID user ID), `iss`, `aud`, `iat`, `exp`, and
  `jti`. Signing secrets are deployment secrets and are never stored in source
  control.
- Access-token lifetime is 15 minutes for the MVP. Refresh tokens are out of
  scope; an expired session requires login again. Client logout deletes its
  stored token.
- The client stores the token in Local Storage and sends it only over HTTPS in
  `Authorization: Bearer <token>`.
- FastAPI verifies signature, issuer, audience, expiry, and required claims.
  The authenticated `sub` is the only source of `user_id` for authorization.
- Every resource query applies the authenticated `user_id`. Composite
  `(resource_id, user_id)` foreign keys enforce ownership across parent/child
  records. Requests for missing and not-owned IDs both return `404 NOT_FOUND`.

## Consequences

### Positive

- Stateless Bearer authentication fits the approved SPA/API boundary.
- The API owns identity derivation; changing request payloads cannot change
  resource ownership.
- Short access-token lifetime limits the useful lifetime of a stolen token.

### Negative and accepted risk

- A successful XSS can read and exfiltrate a Local Storage token before it
  expires. Short expiry does not prevent immediate token misuse.
- There is no server-side refresh or revocation list in this MVP; logout
  removes the browser copy but does not invalidate a copied token.

## Required mitigations

- HTTPS in every non-local deployment.
- Strict Content Security Policy; avoid unsafe inline script and unsafe HTML
  insertion; escape user/document-derived content.
- No JWTs in logs, analytics, URLs, or error messages.
- Rate-limit login and registration; use a modern password-hashing algorithm
  such as Argon2id.
- Reassess HttpOnly secure cookies and token revocation before production if
  the security requirements or client constraints change.

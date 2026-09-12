# P3.3 — Create feature specification

> - **Role:** PRIMARY
> - **Skills:** `$prd-generator` (required), `$brainstorm` (conditional: behavior conflict or ambiguity)
> - **Interaction mode:** plan-then-approve
> - **Output mode:** interactive draft → approved artifact
> - **Approval gate:** approve behavior before saving
> - **Canonical output:** `chapter-03-ai-for-requirements-product-analysis/docs/feature-specification.md`
> - **Run context:** fresh session; attach or provide every input below.

## Use this when

The PRD has passed review and designers or developers need detailed behavior without guessing core rules.

## Inputs

- Accepted product requirements: `../docs/product-requirements.md`
- Project context: `../../chapter-02-prompt-engineering/docs/project-context.md`
- Any newer human-approved decision.

## Task

Use `$prd-generator` to specify document management, processing, summarization, document-based Q&A, quiz generation, quiz completion/evaluation, performance analysis, weak-topic detection, personalized recommendations and learning history.

Specify:
- business rules,
- main flows,
- alternative flows,
- error flows,
- validation,
- persistent data,
- authorization,
- required UI states,
- recovery behavior.

Reference `FR-*` and `US-*` identifiers where they clarify traceability.

## Constraints and source precedence

1. Newer human-approved decisions.
2. Accepted PRD.
3. Project context.
4. AI suggestions.

- Stay solution-light except where an accepted product decision fixes behavior.
- AI output must be validated before being treated as valid product data.
- Recommendations must use student-specific evidence.
- Do not fabricate unavailable learning materials.
- Report contradictions rather than resolving them silently.

## Expected output

A design- and implementation-ready feature specification.

## Save or update

After human approval, write `chapter-03-ai-for-requirements-product-analysis/docs/feature-specification.md`; otherwise return complete Markdown for manual saving.

## Human review required

Confirm success, failure, recovery, persistence, authorization, validation and destructive-action behavior before accepting the artifact.

## Validation checklist

- Every primary action has success and failure behavior.
- Invalid AI output has a rejection path.
- Data survives reload.
- Unauthorized users cannot access unrelated documents or learning records.
- Recommendations explain their basis.

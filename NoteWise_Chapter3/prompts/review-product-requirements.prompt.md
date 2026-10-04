# P3.2 — Review product requirements

> - **Role:** REVIEW GATE
> - **Skills:** `$prd-generator` (required: PRD completeness and structure), `$brainstorm` (conditional: a finding needs a product decision)
> - **Interaction mode:** inspect-and-report
> - **Output mode:** review findings
> - **Approval gate:** accept findings before changing the canonical PRD
> - **Updates:** `chapter-03-ai-for-requirements-product-analysis/docs/product-requirements.md` after human review
> - **Run context:** fresh session; attach or provide every input below.

## Use this when

You have a PRD draft and need to decide whether it is ready to drive a feature specification.

## Inputs

- PRD draft: `../docs/product-requirements.md`
- Project context: `../../chapter-02-prompt-engineering/docs/project-context.md`
- Any newer human-approved product decision.

## Task

Use `$prd-generator` to inspect requirement completeness and testability. Review product value, source support, document ownership, authentication, authorization, validation, error recovery, persistence, terminology, AI boundaries and exclusions.

Return findings first. For every confirmed issue, give the smallest correction and distinguish it from an open human question. Use `$brainstorm` only to resolve a material product choice with the human. Do not rewrite the canonical PRD until the human accepts the findings.

## Constraints and source precedence

1. Newer human-approved decisions.
2. Project context.
3. PRD draft.
4. AI suggestions.

- Do not reward document length or add features while reviewing.
- Preserve accepted exclusions.
- Do not infer unsupported capabilities.
- Confirm that NoteWise is a complete learning workflow, not only an AI API wrapper.

## Expected output

A prioritized findings list containing:
- evidence,
- impact,
- target section,
- smallest correction,
- status (`confirmed issue` or `human decision needed`).

## Save or update

Do not create a separate canonical review document. After human approval, apply accepted corrections to `product-requirements.md`; leave rejected or deferred findings out of the PRD.

## Human review required

The human accepts, rejects or defers each finding before the PRD changes.

## Validation checklist

- No requirement depends on MCP.
- No planned feature is presented as delivered.
- Main and failure journeys are testable.
- Terminology is consistent.
- Scope does not expand during review.

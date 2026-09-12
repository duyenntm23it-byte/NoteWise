# P3.1 — Create product requirements

> - **Role:** PRIMARY
> - **Skills:** `$prd-generator` (required), `$brainstorm` (conditional: scope or success criteria remain unclear)
> - **Interaction mode:** plan-then-approve
> - **Output mode:** interactive draft → approved artifact
> - **Approval gate:** approve the PRD before saving
> - **Canonical output:** `chapter-03-ai-for-requirements-product-analysis/docs/product-requirements.md`
> - **Run context:** fresh session; attach or provide every input below.

## Use this when

The project brief and portable project context are approved, and you need a small, testable product boundary for NoteWise.

## Inputs

- Project brief from Chapter 1.
- Project context from Chapter 2.
- Any newer human-approved product decision.

If a linked artifact is unavailable, ask for it. Do not infer product scope from the filename.

## Task

Use `$prd-generator` to draft a focused PRD for NoteWise. Include product discovery, product goal, target users, learning journey, functional requirements, requirements analysis, user stories, observable acceptance criteria, non-functional expectations, success signals, assumptions and exclusions.

Use `$brainstorm` before drafting only when an unresolved choice materially changes scope. Present the PRD as a draft and wait for human approval; do not save a canonical PRD during the first response.

## NoteWise context

NoteWise helps students transform their own PDF, DOCX and PPTX learning materials into:
- document summaries,
- document-grounded Q&A,
- AI-assisted quizzes,
- quiz results,
- topic-level performance insights,
- weak-topic detection,
- personalized learning recommendations,
- learning history.

The product loop is:

```text
Materials → Analysis → Summary/Q&A/Quiz → Practice
→ Results → Performance Analysis → Weak Topics
→ Personalized Recommendation → Further Learning
```

## Constraints and source precedence

1. Newer human-approved decisions.
2. Project context.
3. Project brief.
4. AI suggestions.

- Describe product behavior, not implementation tasks.
- Use `FR-*` and `US-*` identifiers where they improve traceability.
- Keep AI behavior grounded in the student's materials.
- Make persistence, authorization, validation and recovery observable.
- Do not present an AI API call as the complete product.
- Do not invent unsupported features.

## Expected output

A concise, testable PRD that product, design, engineering and testing can review.

## Save or update

After human approval, write `chapter-03-ai-for-requirements-product-analysis/docs/product-requirements.md`; otherwise return complete Markdown for manual saving.

## Human review required

Approve:
- scope,
- exclusions,
- success signals,
- functional requirements,
- assumptions,
- acceptance criteria.

## Validation checklist

- Each requirement supports the core learning journey.
- Acceptance criteria are observable.
- Authentication/authorization are explicit where applicable.
- Persistence is explicit.
- AI boundaries are explicit.
- Exclusions prevent feature expansion.

# Chapter 3 — AI for Requirements & Product Analysis

> **Project:** NoteWise — Hệ thống học tập cá nhân hóa từ tài liệu bài giảng
>
> This chapter follows the P3.1 → P3.2 → P3.3 workflow from the course guideline.

## Recommended path

1. **P3.1 — Create product requirements:** create a focused PRD.
2. **P3.2 — Review product requirements:** inspect the PRD and record findings before changing the canonical artifact.
3. **P3.3 — Create feature specification:** after PRD approval, specify core behavior for design and engineering.

## Canonical artifacts

- `docs/product-requirements.md`
- `docs/feature-specification.md`

P3.2 is a review gate and does not create a separate canonical review document.

## NoteWise product boundary

NoteWise uses AI as a component inside a complete learning product. The application controls document management, document processing, source selection, AI-output validation, quiz evaluation, persistence, performance analysis, weak-topic detection, recommendation logic and learning history.

## Core learning loop

```text
Learning Materials
      ↓
Document Analysis
      ↓
Summary / Q&A / Quiz
      ↓
Student Practice
      ↓
Quiz Results
      ↓
Performance Analysis
      ↓
Weak Topic Detection
      ↓
Personalized Recommendation
      ↓
Further Learning
```

## Source precedence

1. Newer human-approved decisions.
2. Project context.
3. Project brief.
4. AI suggestions.

## Handoff

The PRD and Feature Specification should be kept in `Accepted` status after human review. They are the artifacts for design and engineering handoff. No task breakdown is created at this stage.

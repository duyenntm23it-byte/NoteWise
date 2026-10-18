# AGENTS.md — NOTEWISE AI Agent Operational Rules

> **Project:** NoteWise — Modular Monolith RAG & AI Quiz Platform
> **Tech Stack:** FastAPI + PostgreSQL/pgvector + Next.js + Tailwind CSS

## 1. Core Principles
- **Strict Typing:** No `any` in TypeScript; explicit Pydantic schemas in FastAPI.
- **Transactional Safety:** All database writes must run in explicit SQLAlchemy session transactions.
- **Preserve Logic & UI:** Never overwrite whole layout files when fixing TDD logic. Retain Tailwind classes.

## 2. Specialized Roles
- **Backend Agent:** Focuses on `backend/app/`, FastAPI routers, JWT auth, and RAG pipelines.
- **Frontend Agent:** Focuses on `frontend/src/`, Next.js components, Zustand stores, and Tailwind styling.
- **Database Agent:** Focuses on Alembic migrations, SQLAlchemy models, and pgvector indexes.
- **Reviewer Agent:** Focuses on auditing security flaws, SQL injections, and code smells.

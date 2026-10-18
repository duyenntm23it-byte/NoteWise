---
name: rag-pgvector
description: "Implement or debug retrieval-augmented generation with document text chunking, 1536-dimensional embeddings, PostgreSQL pgvector similarity search, and grounded citations."
---

# RAG with pgvector

## When to Use
- Building document ingestion, chunking, embedding, retrieval, or grounded answering.
- Adding or changing pgvector columns, indexes, similarity queries, or migrations.
- Debugging missing, irrelevant, or incorrectly attributed citations.

## Procedure
1. Trace the current ingestion and query pipeline, embedding provider, model version, database schema, and citation format before changing behavior.
2. Extract text with its source metadata intact. Normalize only what is safe: retain page/slide boundaries, document identity, and offsets or equivalent locators required for citations.
3. Split text into bounded, overlapping chunks at useful semantic boundaries. Store stable document and chunk identifiers plus source locators with every chunk; avoid empty or whitespace-only chunks.
4. Generate embeddings through the configured provider. Enforce the schema's **1536-dimensional** vector contract at ingestion and query time; reject mismatches explicitly rather than truncating, padding, or silently changing dimensions.
5. Persist document/chunk records and vectors transactionally. Ensure migrations enable pgvector before creating vector columns or indexes. Choose and verify an index/operator-class and distance metric that match the actual query operator and workload.
6. Retrieve with parameterized SQLAlchemy queries, filtering by the appropriate tenant/document permissions before returning context. Apply deliberate top-k and similarity thresholds only where configured and testable.
7. Build the answer context from retrieved chunks and require citations to reference those exact chunk/document locators. Do not invent sources, page numbers, or support absent from retrieved material; state when evidence is insufficient.
8. Test chunk boundary/metadata retention, embedding dimension validation, retrieval ranking/filtering, and citation mapping. Include empty input, duplicate ingestion, and unavailable-provider behavior where applicable.

## Reliability and Safety
- Keep embedding model, dimension, distance metric, and index configuration in agreement; changing them requires a reviewed migration and re-embedding plan.
- Avoid logging raw document text, credentials, or complete prompts containing private content.
- Surface provider, database, and parsing failures explicitly. Never return fabricated answers or citations as a fallback.

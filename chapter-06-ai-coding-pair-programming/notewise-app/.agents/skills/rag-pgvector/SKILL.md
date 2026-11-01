---
name: rag-pgvector
description: "Implement or debug retrieval-augmented generation with document text chunking, Google Gemini 768-dimensional embeddings, PostgreSQL pgvector similarity search, and grounded citations."
---

# RAG with pgvector

## When to Use

- Building document ingestion, chunking, embedding, retrieval, or grounded answering.
- Adding or changing pgvector columns, indexes, similarity queries, or migrations.
- Debugging missing, irrelevant, or incorrectly attributed citations.

## Project Stack Overrides

- Embedding provider: Google Gemini through `google-genai` and `GOOGLE_API_KEY`. Model `gemini-embedding-001` with `output_dimensionality=768`. Do not use OpenAI or LangChain.
- The single source of truth for the dimension is `EMBEDDING_DIMENSIONS = 768` in `backend/app/services/embeddings.py`. All pgvector columns (`Vector(768)`), migrations, and test vectors must use 768. Never use 1536.
- Gemini does not normalize vectors below 3072 dimensions, so every vector is L2-normalized before storage and before querying (already done in `embeddings.py`).
- Task types: documents are embedded with `RETRIEVAL_DOCUMENT` (`embed_documents`), user questions with `RETRIEVAL_QUERY` (`embed_query`). Never embed a question with `embed_documents`.
- Embeddings are sent in batches of about 50 texts with retry and backoff on 429/500/503, because the free tier is rate limited.
- Text generation uses Gemini through the `CHAT_MODEL` constant and the `AnswerService*` classes in `backend/app/services/rag.py`. Do not hard-code model names elsewhere.

## Procedure

1. Trace the current ingestion and query pipeline, embedding provider, model version, database schema, and citation format before changing behavior.
2. Extract text with its source metadata intact. Normalize only what is safe: retain page/slide boundaries, document identity, and offsets or equivalent locators required for citations.
3. Split text into bounded, overlapping chunks at useful semantic boundaries. Store stable document and chunk identifiers plus source locators with every chunk; avoid empty or whitespace-only chunks.
4. Generate embeddings through the configured provider. Enforce the schema's **768-dimensional** vector contract at ingestion and query time (`validate_embedding_dimensions`); reject mismatches explicitly rather than truncating, padding, or silently changing dimensions.
5. Persist document/chunk records and vectors transactionally. Ensure migrations enable pgvector before creating vector columns or indexes. Choose and verify an index/operator-class and distance metric that match the actual query operator and workload (HNSW with `vector_cosine_ops` and the cosine distance operator).
6. Retrieve with parameterized SQLAlchemy queries, filtering by the appropriate tenant/document permissions before returning context. Apply deliberate top-k (currently `RAG_TOP_K = 4`) and similarity thresholds only where configured and testable.
7. Build the answer context from retrieved chunks and require citations to reference those exact chunk/document locators. Do not invent sources, page numbers, or support absent from retrieved material; state when evidence is insufficient.
8. Test chunk boundary/metadata retention, embedding dimension validation, retrieval ranking/filtering, and citation mapping. Include empty input, duplicate ingestion, and unavailable-provider behavior where applicable. Tests use fake embedding and answer services injected with `app.dependency_overrides`; they never call Gemini or the network. Fake embedding services must provide both `embed_documents` and `embed_query`.

## Reliability and Safety

- Keep embedding model, dimension, distance metric, and index configuration in agreement. Changing any of them requires a reviewed Alembic migration (create it, do not run it) plus a plan to delete and re-embed existing chunks, because vectors from different models or dimensions are not comparable.
- Avoid logging raw document text, credentials, or complete prompts containing private content.
- Surface provider, database, and parsing failures explicitly. Never return fabricated answers or citations as a fallback.

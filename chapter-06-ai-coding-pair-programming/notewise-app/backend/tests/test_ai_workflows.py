from collections.abc import Generator
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from types import SimpleNamespace

from app.core.security import create_access_token
from app.core.rate_limit import DocumentRateLimiter
from app.db.session import Base, get_db
from app.main import app
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.services.ai import (
    AIProviderError,
    EMBEDDING_DIMENSION,
    OpenAIProvider,
    cosine_similarity,
    embed_document_chunks,
    select_relevant_chunks,
)
from app.services.documents import process_next_job


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    app.state.testing_session_factory = session_factory
    app.state.disable_document_worker = True
    app.state.ai_rate_limiter = DocumentRateLimiter()

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    for state_key in (
        "testing_session_factory",
        "disable_document_worker",
        "ai_rate_limiter",
    ):
        if hasattr(app.state, state_key):
            delattr(app.state, state_key)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _ready_document(client: TestClient) -> tuple[dict[str, str], UUID, UUID]:
    user_id = uuid4()
    document_id = uuid4()
    with app.state.testing_session_factory() as db:
        db.add(
            User(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="unused",
            )
        )
        db.add(
            Document(
                id=document_id,
                user_id=user_id,
                filename="lecture.pdf",
                storage_key=f"{document_id}.pdf",
                media_type="application/pdf",
                status="READY",
            )
        )
        db.add(
            DocumentChunk(
                id=uuid4(),
                user_id=user_id,
                document_id=document_id,
                chunk_index=0,
                content="A test document with usable learning content.",
                embedding=None,
            )
        )
        db.commit()
    return (
        {"Authorization": f"Bearer {create_access_token(user_id)}"},
        user_id,
        document_id,
    )


def test_openai_embedding_response_is_dimension_checked() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [0.1] * EMBEDDING_DIMENSION},
                ],
            },
        )
    )
    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://openai.test/v1",
        transport=transport,
    )

    embeddings = provider.embed_texts(["document text"])

    assert len(embeddings) == 1
    assert len(embeddings[0]) == EMBEDDING_DIMENSION


def test_openai_embedding_rejects_wrong_vector_dimension() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
        )
    )
    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://openai.test/v1",
        transport=transport,
    )

    with pytest.raises(AIProviderError, match="AI_OUTPUT_INVALID"):
        provider.embed_texts(["document text"])


def test_similarity_selection_is_ranked_bounded_and_thresholded() -> None:
    candidates = [
        {"chunk_id": "far", "embedding": [0.0, 1.0]},
        {"chunk_id": "near", "embedding": [1.0, 0.0]},
        {"chunk_id": "below", "embedding": [0.3, 0.95]},
    ]

    selected = select_relevant_chunks(
        candidates,
        [1.0, 0.0],
        threshold=0.35,
        limit=1,
    )

    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert [item["chunk_id"] for item in selected] == ["near"]


def test_chunk_embedding_generation_persists_fixed_dimension_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = SimpleNamespace(content="study content", embedding=None)
    flushed = False

    class FakeProvider:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["study content"]
            return [[0.25] * EMBEDDING_DIMENSION]

    class FakeSession:
        def flush(self) -> None:
            nonlocal flushed
            flushed = True

    monkeypatch.setattr("app.services.ai.provider", FakeProvider())

    embed_document_chunks(FakeSession(), [chunk])

    assert len(chunk.embedding) == EMBEDDING_DIMENSION
    assert chunk.embedding[0] == pytest.approx(0.25)
    assert flushed


def test_vector_search_uses_postgres_cosine_operator_and_owner_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.dialects import postgresql

    from app.services.ai import retrieve_relevant_chunks

    user_id = uuid4()
    document_id = uuid4()
    chunk_id = uuid4()
    stored_chunk = SimpleNamespace(
        id=chunk_id,
        content="Relevant text",
        page_number=3,
        section="Topic",
    )

    class FakeResult:
        def all(self):
            return [(stored_chunk, 0.1)]

    class FakeSession:
        bind = None

        def __init__(self):
            self.scalar_values = [
                SimpleNamespace(status="READY"),
                1,
                1,
            ]
            self.statement = None

        def scalar(self, _statement):
            return self.scalar_values.pop(0)

        def execute(self, statement):
            self.statement = statement
            return FakeResult()

    class FakeProvider:
        def embed_texts(self, _texts):
            return [[0.0] * EMBEDDING_DIMENSION]

    db = FakeSession()
    monkeypatch.setattr("app.services.ai.provider", FakeProvider())

    results = retrieve_relevant_chunks(db, user_id, document_id, "a question")
    sql = str(db.statement.compile(dialect=postgresql.dialect()))
    params = db.statement.compile(dialect=postgresql.dialect()).params

    assert " <=> " in sql
    assert "document_chunks.user_id" in sql
    assert "document_chunks.document_id" in sql
    assert user_id in params.values()
    assert document_id in params.values()
    assert results[0]["chunk_id"] == chunk_id
    assert results[0]["score"] == pytest.approx(0.9)


def test_learning_routes_match_openapi_contract() -> None:
    paths = app.openapi()["paths"]

    summary_post = paths["/api/v1/documents/{document_id}/summaries"]["post"]
    summary_get = paths["/api/v1/summaries/{summary_id}"]["get"]
    question_post = paths["/api/v1/documents/{document_id}/questions"]["post"]
    assert summary_post["operationId"] == "createSummary"
    assert summary_get["operationId"] == "getSummary"
    assert question_post["operationId"] == "askDocumentQuestion"
    assert summary_post["security"] == [{"bearerAuth": []}]
    assert summary_get["security"] == [{"bearerAuth": []}]
    assert question_post["security"] == [{"bearerAuth": []}]
    assert "202" in summary_post["responses"]
    assert {"502", "503", "504"}.issubset(question_post["responses"])
    question_schema = question_post["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert len(question_schema["oneOf"]) == 2
    assert "/api/v1/documents/{document_id}/summary" not in paths
    assert "/api/v1/documents/{document_id}/qa" not in paths


def test_learning_endpoints_require_authentication(client: TestClient) -> None:
    document_id = uuid4()
    assert client.post(
        f"/api/v1/documents/{document_id}/summaries",
    ).status_code == 401
    assert client.get(
        f"/api/v1/summaries/{uuid4()}",
    ).status_code == 401
    assert client.post(
        f"/api/v1/documents/{document_id}/questions",
        json={"question": "Question?"},
    ).status_code == 401


def test_summary_request_is_durable_and_owner_scoped(client: TestClient) -> None:
    headers, _, document_id = _ready_document(client)

    response = client.post(
        f"/api/v1/documents/{document_id}/summaries",
        headers={**headers, "Idempotency-Key": "summary-key-0001"},
    )
    assert response.status_code == 202
    accepted = response.json()
    assert accepted["summary"]["status"] == "QUEUED"
    assert accepted["job_id"]
    assert client.get(
        f"/api/v1/summaries/{accepted['summary']['id']}",
        headers=headers,
    ).json()["status"] == "QUEUED"

    other_headers, _, _ = _ready_document(client)
    assert client.get(
        f"/api/v1/summaries/{accepted['summary']['id']}",
        headers=other_headers,
    ).status_code == 404
    history = client.get("/api/v1/learning-history", headers=headers).json()
    assert history["total"] == 1
    assert history["items"][0]["event_type"] == "SUMMARY_CREATED"


def test_question_returns_only_retrieved_chunk_citations(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id = _ready_document(client)
    chunk_id = uuid4()
    monkeypatch.setattr(
        "app.api.learning.retrieve_relevant_chunks",
        lambda *_args, **_kwargs: [
            {
                "chunk_id": chunk_id,
                "content": "A requirement is testable and traceable.",
                "page_number": 12,
                "section": "Requirements",
                "score": 0.91,
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.learning.generate_grounded_answer",
        lambda *_args, **_kwargs: {
            "status": "answered",
            "answer": "A requirement should be testable.",
            "citations": [str(chunk_id)],
        },
    )

    response = client.post(
        f"/api/v1/documents/{document_id}/questions",
        headers=headers,
        json={"question": "What should a requirement be?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "answered",
        "answer": "A requirement should be testable.",
        "citations": [
            {
                "chunk_id": str(chunk_id),
                "page_number": 12,
                "section": "Requirements",
                "excerpt": "A requirement is testable and traceable.",
            }
        ],
    }
    history = client.get("/api/v1/learning-history", headers=headers).json()
    assert history["total"] == 1
    assert history["items"][0]["event_type"] == "QUESTION_ASKED"
    assert history["items"][0]["details"] == {
        "status": "ANSWERED",
        "question_length": len("What should a requirement be?"),
    }


def test_question_with_no_relevant_evidence_abstains(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id = _ready_document(client)
    monkeypatch.setattr(
        "app.api.learning.retrieve_relevant_chunks",
        lambda *_args, **_kwargs: [],
    )

    response = client.post(
        f"/api/v1/documents/{document_id}/questions",
        headers=headers,
        json={"question": "What is the capital of Mars?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "insufficient_evidence",
        "answer": None,
        "citations": [],
        "code": "INSUFFICIENT_EVIDENCE",
    }


def test_question_rejects_citation_outside_retrieved_evidence(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id = _ready_document(client)
    monkeypatch.setattr(
        "app.api.learning.retrieve_relevant_chunks",
        lambda *_args, **_kwargs: [
            {
                "chunk_id": uuid4(),
                "content": "Evidence from this document.",
                "page_number": 1,
                "section": None,
                "score": 0.8,
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.learning.generate_grounded_answer",
        lambda *_args, **_kwargs: {
            "status": "answered",
            "answer": "A fabricated answer.",
            "citations": [str(uuid4())],
        },
    )

    response = client.post(
        f"/api/v1/documents/{document_id}/questions",
        headers=headers,
        json={"question": "What does this document say?"},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_OUTPUT_INVALID"


def test_summary_job_persists_generated_markdown(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id = _ready_document(client)
    monkeypatch.setattr(
        "app.services.learning.generate_summary",
        lambda _content: "## Key idea\n\nUse verified evidence.",
    )
    accepted = client.post(
        f"/api/v1/documents/{document_id}/summaries",
        headers=headers,
    )
    assert accepted.status_code == 202

    with app.state.testing_session_factory() as db:
        assert process_next_job(db) is True

    summary_response = client.get(
        f"/api/v1/summaries/{accepted.json()['summary']['id']}",
        headers=headers,
    )
    assert summary_response.status_code == 200
    assert summary_response.json()["status"] == "READY"
    assert summary_response.json()["content"] == (
        "## Key idea\n\nUse verified evidence."
    )

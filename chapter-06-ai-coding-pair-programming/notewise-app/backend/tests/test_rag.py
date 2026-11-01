# from collections.abc import AsyncIterator
# from uuid import UUID, uuid4

# import pytest
# import pytest_asyncio
# from httpx import ASGITransport, AsyncClient
# from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
# from sqlalchemy.pool import StaticPool

# from app.api.v1.auth import get_current_user
# from app.core.db import get_db_session
# from app.main import app
# from app.models.base import Base
# from app.models.document import Document, DocumentChunk
# from app.models.user import User
# from app.services.embeddings import get_embedding_service
# from app.services.rag import get_answer_service


# class FakeEmbeddingService:
#     async def embed_documents(self, texts: list[str]) -> list[list[float]]:
#         return [[1.0] + [0.0] * 767 for _ in texts]


# class FakeAnswerService:
#     def __init__(self) -> None:
#         self.context: list[dict[str, object]] = []
#         self.called = False

#     async def answer(self, question: str, context: list[dict[str, object]]) -> str:
#         self.called = True
#         self.context = context
#         return "The notes describe active recall. [1]"


# @pytest_asyncio.fixture
# async def rag_client() -> AsyncIterator[tuple[AsyncClient, UUID, UUID, FakeAnswerService]]:
#     engine = create_async_engine(
#         "sqlite+aiosqlite://",
#         connect_args={"check_same_thread": False},
#         poolclass=StaticPool,
#     )
#     async with engine.begin() as connection:
#         await connection.run_sync(Base.metadata.create_all)

#     session_factory = async_sessionmaker(engine, expire_on_commit=False)
#     user_id = uuid4()
#     other_user_id = uuid4()
#     selected_document_id = uuid4()
#     other_document_id = uuid4()
#     private_document_id = uuid4()
#     answer_service = FakeAnswerService()
#     async with session_factory() as session:
#         async with session.begin():
#             session.add_all(
#                 [
#                     User(id=user_id, email="rag@example.com", hashed_password="unused"),
#                     User(
#                         id=other_user_id,
#                         email="another-rag@example.com",
#                         hashed_password="unused",
#                     ),
#                 ]
#             )
#             session.add_all(
#                 [
#                     Document(
#                         id=selected_document_id,
#                         user_id=user_id,
#                         title="Study guide.pdf",
#                         file_path="unused",
#                         file_type="pdf",
#                         status="ready",
#                     ),
#                     Document(
#                         id=other_document_id,
#                         user_id=user_id,
#                         title="Other notes.txt",
#                         file_path="unused",
#                         file_type="txt",
#                         status="ready",
#                     ),
#                     Document(
#                         id=private_document_id,
#                         user_id=other_user_id,
#                         title="Private notes.txt",
#                         file_path="unused",
#                         file_type="txt",
#                         status="ready",
#                     ),
#                 ]
#             )
#             await session.flush()
#             session.add_all(
#                 [
#                     DocumentChunk(
#                         document_id=selected_document_id,
#                         content=f"Relevant study note {index}",
#                         embedding=[1.0, float(index + 1)] + [0.0] * 766,
#                         chunk_index=index,
#                         page_number=index + 1,
#                     )
#                     for index in range(5)
#                 ]
#                 + [
#                     DocumentChunk(
#                         document_id=other_document_id,
#                         content="A different document must be filtered out.",
#                         embedding=[1.0] + [0.0] * 767,
#                         chunk_index=0,
#                     )
#                 ]
#                 + [
#                     DocumentChunk(
#                         document_id=private_document_id,
#                         content="This private source must never be retrieved.",
#                         embedding=[1.0] + [0.0] * 767,
#                         chunk_index=0,
#                     )
#                 ]
#             )

#     async def override_db_session() -> AsyncIterator[AsyncSession]:
#         async with session_factory() as session:
#             yield session

#     async def override_current_user() -> User:
#         return User(id=user_id, email="rag@example.com", hashed_password="unused")

#     app.dependency_overrides[get_db_session] = override_db_session
#     app.dependency_overrides[get_current_user] = override_current_user
#     app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()
#     app.dependency_overrides[get_answer_service] = lambda: answer_service
#     try:
#         async with AsyncClient(
#             transport=ASGITransport(app=app),
#             base_url="http://testserver",
#         ) as client:
#             yield client, user_id, selected_document_id, answer_service
#     finally:
#         app.dependency_overrides.pop(get_db_session, None)
#         app.dependency_overrides.pop(get_current_user, None)
#         app.dependency_overrides.pop(get_embedding_service, None)
#         app.dependency_overrides.pop(get_answer_service, None)
#         await engine.dispose()


# @pytest.mark.asyncio
# async def test_query_retrieves_top_four_filtered_chunks_and_citations(rag_client) -> None:
#     client, _, document_id, answer_service = rag_client

#     response = await client.post(
#         "/api/v1/rag/query",
#         json={"question": "How should I study?", "document_ids": [str(document_id)]},
#     )

#     assert response.status_code == 200, response.text
#     payload = response.json()
#     assert payload["answer"] == "The notes describe active recall. [1]"
#     assert len(payload["citations"]) == 4
#     assert [citation["chunk_index"] for citation in payload["citations"]] == [0, 1, 2, 3]
#     assert all(citation["document_title"] == "Study guide.pdf" for citation in payload["citations"])
#     assert payload["citations"][0] == {
#         "reference": 1,
#         "document_id": str(document_id),
#         "document_title": "Study guide.pdf",
#         "chunk_index": 0,
#         "page_number": 1,
#         "content": "Relevant study note 0",
#     }
#     assert len(answer_service.context) == 4
#     assert answer_service.context[0]["content"] == "Relevant study note 0"


# @pytest.mark.asyncio
# async def test_query_without_document_filter_still_scopes_to_current_user(rag_client) -> None:
#     client, _, _, _ = rag_client

#     response = await client.post("/api/v1/rag/query", json={"question": "Question?"})

#     assert response.status_code == 200
#     assert all(
#         citation["document_title"] != "Private notes.txt"
#         for citation in response.json()["citations"]
#     )


# @pytest.mark.asyncio
# async def test_query_without_matching_chunks_does_not_call_answer_provider(rag_client) -> None:
#     client, _, _, answer_service = rag_client

#     response = await client.post(
#         "/api/v1/rag/query",
#         json={"question": "Question?", "document_ids": []},
#     )

#     assert response.status_code == 200
#     assert response.json()["citations"] == []
#     assert response.json()["answer"]
#     assert answer_service.called is False


# @pytest.mark.asyncio
# async def test_query_rejects_empty_question(rag_client) -> None:
#     client, _, _, _ = rag_client

#     response = await client.post("/api/v1/rag/query", json={"question": "  "})

#     assert response.status_code == 422


# @pytest.mark.asyncio
# async def test_query_rejects_document_ids_not_owned_by_user(rag_client) -> None:
#     client, _, _, _ = rag_client

#     response = await client.post(
#         "/api/v1/rag/query",
#         json={"question": "Question?", "document_ids": [str(uuid4())]},
#     )

#     assert response.status_code == 404

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.auth import get_current_user
from app.core.db import get_db_session
from app.main import app
from app.models.base import Base
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.services.embeddings import get_embedding_service
from app.services.rag import get_answer_service


class FakeEmbeddingService:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Câu hỏi phải được embed bằng embed_query (task type RETRIEVAL_QUERY).
        # Nếu code lỡ gọi embed_documents cho câu hỏi thì test sẽ fail ở đây.
        raise AssertionError("Questions must be embedded with embed_query")

    async def embed_query(self, text: str) -> list[float]:
        return [1.0] + [0.0] * 767


class FakeAnswerService:
    def __init__(self) -> None:
        self.context: list[dict[str, object]] = []
        self.called = False

    async def answer(self, question: str, context: list[dict[str, object]]) -> str:
        self.called = True
        self.context = context
        return "The notes describe active recall. [1]"


@pytest_asyncio.fixture
async def rag_client() -> AsyncIterator[tuple[AsyncClient, UUID, UUID, FakeAnswerService]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid4()
    other_user_id = uuid4()
    selected_document_id = uuid4()
    other_document_id = uuid4()
    private_document_id = uuid4()
    answer_service = FakeAnswerService()
    async with session_factory() as session:
        async with session.begin():
            session.add_all(
                [
                    User(id=user_id, email="rag@example.com", hashed_password="unused"),
                    User(
                        id=other_user_id,
                        email="another-rag@example.com",
                        hashed_password="unused",
                    ),
                ]
            )
            session.add_all(
                [
                    Document(
                        id=selected_document_id,
                        user_id=user_id,
                        title="Study guide.pdf",
                        file_path="unused",
                        file_type="pdf",
                        status="ready",
                    ),
                    Document(
                        id=other_document_id,
                        user_id=user_id,
                        title="Other notes.txt",
                        file_path="unused",
                        file_type="txt",
                        status="ready",
                    ),
                    Document(
                        id=private_document_id,
                        user_id=other_user_id,
                        title="Private notes.txt",
                        file_path="unused",
                        file_type="txt",
                        status="ready",
                    ),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    DocumentChunk(
                        document_id=selected_document_id,
                        content=f"Relevant study note {index}",
                        embedding=[1.0, float(index + 1)] + [0.0] * 766,
                        chunk_index=index,
                        page_number=index + 1,
                    )
                    for index in range(5)
                ]
                + [
                    DocumentChunk(
                        document_id=other_document_id,
                        content="A different document must be filtered out.",
                        embedding=[1.0] + [0.0] * 767,
                        chunk_index=0,
                    )
                ]
                + [
                    DocumentChunk(
                        document_id=private_document_id,
                        content="This private source must never be retrieved.",
                        embedding=[1.0] + [0.0] * 767,
                        chunk_index=0,
                    )
                ]
            )

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_current_user() -> User:
        return User(id=user_id, email="rag@example.com", hashed_password="unused")

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()
    app.dependency_overrides[get_answer_service] = lambda: answer_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client, user_id, selected_document_id, answer_service
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_embedding_service, None)
        app.dependency_overrides.pop(get_answer_service, None)
        await engine.dispose()


@pytest.mark.asyncio
async def test_query_retrieves_top_four_filtered_chunks_and_citations(rag_client) -> None:
    client, _, document_id, answer_service = rag_client

    response = await client.post(
        "/api/v1/rag/query",
        json={"question": "How should I study?", "document_ids": [str(document_id)]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"] == "The notes describe active recall. [1]"
    assert len(payload["citations"]) == 4
    assert [citation["chunk_index"] for citation in payload["citations"]] == [0, 1, 2, 3]
    assert all(citation["document_title"] == "Study guide.pdf" for citation in payload["citations"])
    assert payload["citations"][0] == {
        "reference": 1,
        "document_id": str(document_id),
        "document_title": "Study guide.pdf",
        "chunk_index": 0,
        "page_number": 1,
        "content": "Relevant study note 0",
    }
    assert len(answer_service.context) == 4
    assert answer_service.context[0]["content"] == "Relevant study note 0"


@pytest.mark.asyncio
async def test_query_without_document_filter_still_scopes_to_current_user(rag_client) -> None:
    client, _, _, _ = rag_client

    response = await client.post("/api/v1/rag/query", json={"question": "Question?"})

    assert response.status_code == 200
    assert all(
        citation["document_title"] != "Private notes.txt"
        for citation in response.json()["citations"]
    )


@pytest.mark.asyncio
async def test_query_without_matching_chunks_does_not_call_answer_provider(rag_client) -> None:
    client, _, _, answer_service = rag_client

    response = await client.post(
        "/api/v1/rag/query",
        json={"question": "Question?", "document_ids": []},
    )

    assert response.status_code == 200
    assert response.json()["citations"] == []
    assert response.json()["answer"]
    assert answer_service.called is False


@pytest.mark.asyncio
async def test_query_rejects_empty_question(rag_client) -> None:
    client, _, _, _ = rag_client

    response = await client.post("/api/v1/rag/query", json={"question": "  "})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_rejects_document_ids_not_owned_by_user(rag_client) -> None:
    client, _, _, _ = rag_client

    response = await client.post(
        "/api/v1/rag/query",
        json={"question": "Question?", "document_ids": [str(uuid4())]},
    )

    assert response.status_code == 404
# 
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.db import get_db_session
from app.core.security import create_access_token
from app.main import app
from app.models.base import Base
from app.models.document import Document
from app.models.user import User
from app.services.embeddings import get_embedding_service


class FakeEmbeddingService:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(index % 7) for index in range(768)] for _ in texts]


class WrongDimensionEmbeddingService:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]


async def create_other_users_document() -> UUID:
    dependency = app.dependency_overrides[get_db_session]
    sessions = dependency()
    session = await anext(sessions)
    user_id = uuid4()
    document_id = uuid4()
    try:
        async with session.begin():
            session.add(
                User(id=user_id, email=f"{user_id.hex}@example.com", hashed_password="unused")
            )
            await session.flush()
            session.add(
                Document(
                    id=document_id,
                    user_id=user_id,
                    title="private.txt",
                    file_path="not-stored",
                    file_type="txt",
                    status="ready",
                )
            )
    finally:
        await sessions.aclose()
    return document_id


@pytest_asyncio.fixture
async def material_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[AsyncClient, UUID, Path]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(id=user_id, email="materials@example.com", hashed_password="not-used")
            )

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    monkeypatch.setattr(
        settings,
        "secret_key",
        SecretStr("test-materials-jwt-secret-32-bytes"),
    )
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()
    previous_storage_path = settings.document_storage_path
    settings.document_storage_path = tmp_path

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            client.headers["Authorization"] = f"Bearer {create_access_token(user_id)}"
            yield client, user_id, tmp_path
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_embedding_service, None)
        settings.document_storage_path = previous_storage_path
        await engine.dispose()


@pytest.mark.asyncio
async def test_upload_txt_chunks_and_embeds_material(material_client) -> None:
    client, _, _ = material_client
    content = ("This is a useful learning note. " * 100).encode()

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("lecture.txt", content, "text/plain")},
    )

    assert response.status_code == 201, response.text
    document = response.json()
    assert document["title"] == "lecture.txt"
    assert document["file_type"] == "txt"
    assert document["status"] == "ready"
    assert document["chunk_count"] >= 2


@pytest.mark.asyncio
async def test_material_list_contains_only_owner_documents(material_client) -> None:
    client, _, _ = material_client
    await client.post(
        "/api/v1/materials/upload",
        files={"file": ("owned.txt", b"My private class notes.", "text/plain")},
    )
    await create_other_users_document()

    response = await client.get("/api/v1/materials/")

    assert response.status_code == 200
    assert [document["title"] for document in response.json()] == ["owned.txt"]
    assert "file_path" not in response.json()[0]


@pytest.mark.asyncio
async def test_delete_removes_owner_document_and_file(material_client) -> None:
    client, _, storage_path = material_client
    upload = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("to-delete.txt", b"Delete these notes.", "text/plain")},
    )
    assert upload.status_code == 201

    response = await client.delete(f"/api/v1/materials/{upload.json()['id']}")

    assert response.status_code == 204
    assert (await client.get("/api/v1/materials/")).json() == []
    assert list(storage_path.rglob("*.txt")) == []


@pytest.mark.asyncio
async def test_delete_does_not_remove_another_users_document(material_client) -> None:
    client, _, _ = material_client
    document_id = await create_other_users_document()

    response = await client.delete(f"/api/v1/materials/{document_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_file_type(material_client) -> None:
    client, _, _ = material_client

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("notes.docx", b"not supported", "application/octet-stream")},
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_pdf_with_invalid_signature(material_client) -> None:
    client, _, _ = material_client

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("lecture.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_marks_unreadable_pdf_failed(material_client) -> None:
    client, _, _ = material_client

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("broken.pdf", b"%PDF-not-a-real-document", "application/pdf")},
    )

    assert response.status_code == 422
    listed = await client.get("/api/v1/materials/")
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(material_client) -> None:
    client, _, _ = material_client

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_files_over_configured_limit(
    material_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = material_client
    monkeypatch.setattr(settings, "max_upload_size_bytes", 10)

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("oversized.txt", b"x" * 11, "text/plain")},
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_rejects_invalid_utf8_text(material_client) -> None:
    client, _, _ = material_client

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("invalid.txt", b"\xff\xfe\xfa", "text/plain")},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_failed_embedding_marks_document_failed(material_client) -> None:
    client, _, _ = material_client
    app.dependency_overrides[get_embedding_service] = lambda: WrongDimensionEmbeddingService()

    response = await client.post(
        "/api/v1/materials/upload",
        files={"file": ("notes.txt", b"A note for embedding.", "text/plain")},
    )

    assert response.status_code == 502
    listed = await client.get("/api/v1/materials/")
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_upload_requires_authenticated_user() -> None:
    response_transport = ASGITransport(app=app)
    async with AsyncClient(transport=response_transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/materials/")

    assert response.status_code == 401


def test_chunk_text_uses_configured_size_and_overlap() -> None:
    from app.services.documents import chunk_text

    text = "0123456789" * 180
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)

    assert len(chunks) == 2
    assert len(chunks[0]) <= 1000
    assert len(chunks[1]) <= 1000
    assert chunks[0][-200:] == chunks[1][:200]


def test_document_chunks_preserve_pdf_page_citations() -> None:
    from app.services.documents import build_chunks

    chunks = build_chunks([(1, "first page"), (2, "second page")])

    assert [(chunk.chunk_index, chunk.page_number) for chunk in chunks] == [(0, 1), (1, 2)]


@pytest.mark.asyncio
async def test_google_embedding_provider_fails_clearly_without_api_key() -> None:
    from app.services.embeddings import (
        EmbeddingServiceUnavailable,
        GoogleGeminiEmbeddingService,
    )

    with pytest.raises(EmbeddingServiceUnavailable, match="GOOGLE_API_KEY"):
        await GoogleGeminiEmbeddingService(None).embed_documents(["test"])
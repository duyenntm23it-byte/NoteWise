from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.rate_limit import AuthRateLimiter, DocumentRateLimiter
from app.db.session import Base, get_db
from app.main import app
from app.models.document import Document, DocumentChunk, ProcessingJob
from app.services.documents import process_next_job


@pytest.fixture
def client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        settings,
        "document_storage_dir",
        str(tmp_path / "documents"),
        raising=False,
    )
    monkeypatch.setattr(
        settings,
        "document_max_upload_bytes",
        25 * 1024 * 1024,
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.documents.embed_document_chunks",
        lambda _db, chunks: [
            setattr(chunk, "embedding", [0.0] * 1536) for chunk in chunks
        ],
    )
    app.state.testing_session_factory = test_session_factory
    app.state.disable_document_worker = True
    app.state.auth_rate_limiter = AuthRateLimiter()
    app.state.document_rate_limiter = DocumentRateLimiter(upload_limit=1000)

    def override_get_db() -> Generator[Session, None, None]:
        db = test_session_factory()
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
        "auth_rate_limiter",
        "document_rate_limiter",
        "ai_rate_limiter",
    ):
        if hasattr(app.state, state_key):
            delattr(app.state, state_key)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _pdf_with_text() -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length 58 >>\nstream\n"
            b"BT /F1 12 Tf 72 720 Td (NoteWise learning content) Tj ET\n"
            b"endstream"
        ),
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode())
        data.extend(body)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010} 00000 n \n".encode())
    data.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(data)


def _upload(
    client: TestClient,
    headers: dict[str, str],
    *,
    filename: str = "lecture.pdf",
    content: bytes | None = None,
    media_type: str = "application/pdf",
):
    return client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                filename,
                _pdf_with_text() if content is None else content,
                media_type,
            )
        },
    )


def test_document_routes_match_openapi_contract() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert {
        "/api/v1/documents",
        "/api/v1/documents/{document_id}",
        "/api/v1/documents/{document_id}/retry",
    }.issubset(paths)
    assert paths["/api/v1/documents"]["post"]["operationId"] == "uploadDocument"
    assert paths["/api/v1/documents"]["get"]["operationId"] == "listDocuments"
    assert (
        paths["/api/v1/documents/{document_id}"]["get"]["operationId"]
        == "getDocument"
    )
    assert (
        paths["/api/v1/documents/{document_id}"]["delete"]["operationId"]
        == "deleteDocument"
    )
    assert (
        paths["/api/v1/documents/{document_id}/retry"]["post"]["operationId"]
        == "retryDocumentProcessing"
    )
    upload_operation = paths["/api/v1/documents"]["post"]
    assert set(upload_operation["responses"]) >= {
        "202",
        "401",
        "409",
        "413",
        "415",
        "422",
        "429",
        "503",
    }
    request_body = upload_operation["requestBody"]
    assert request_body["required"] is True
    body_schema_ref = request_body["content"]["multipart/form-data"]["schema"]["$ref"]
    body_schema_name = body_schema_ref.rsplit("/", maxsplit=1)[-1]
    assert app.openapi()["components"]["schemas"][body_schema_name]["required"] == [
        "file"
    ]
    assert paths["/api/v1/documents"]["get"]["parameters"]
    assert (
        paths["/api/v1/documents/{document_id}"]["delete"]["responses"]["202"][
            "content"
        ]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DocumentDeletion"
    )
    for operation in (
        paths["/api/v1/documents"]["get"],
        upload_operation,
        paths["/api/v1/documents/{document_id}"]["get"],
        paths["/api/v1/documents/{document_id}"]["delete"],
        paths["/api/v1/documents/{document_id}/retry"]["post"],
    ):
        assert operation["security"] == [{"bearerAuth": []}]


def test_all_document_operations_require_bearer_token(client: TestClient) -> None:
    document_id = "00000000-0000-0000-0000-000000000001"
    responses = [
        client.get("/api/v1/documents"),
        client.post(
            "/api/v1/documents",
            files={"file": ("lecture.pdf", _pdf_with_text(), "application/pdf")},
        ),
        client.get(f"/api/v1/documents/{document_id}"),
        client.post(f"/api/v1/documents/{document_id}/retry"),
        client.delete(f"/api/v1/documents/{document_id}"),
    ]

    assert [response.status_code for response in responses] == [401] * 5


def test_upload_returns_durable_processing_document(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "owner@example.com")

    response = _upload(client, headers, filename="../../lecture.pdf")

    assert response.status_code == 202
    payload = response.json()
    assert set(payload) == {"document", "job_id"}
    assert payload["document"]["status"] == "PROCESSING"
    assert set(payload["document"]) == {
        "id",
        "filename",
        "media_type",
        "status",
        "failure_code",
        "page_count",
        "created_at",
        "updated_at",
    }
    document_id = payload["document"]["id"]
    with app.state.testing_session_factory() as db:
        document = db.get(Document, UUID(document_id))
        job = db.get(ProcessingJob, UUID(payload["job_id"]))
        assert document is not None
        assert job is not None
        assert document.user_id == job.user_id
        assert document.storage_key != "../../lecture.pdf"
        assert (Path(settings.document_storage_dir) / document.storage_key).is_file()
    history = client.get("/api/v1/learning-history", headers=headers).json()
    assert history["total"] == 1
    assert history["items"][0]["event_type"] == "DOCUMENT_UPLOADED"
    assert history["items"][0]["document_id"] == document_id


@pytest.mark.parametrize(
    ("filename", "content", "media_type", "status_code", "error_code"),
    [
        (
            "lecture.txt",
            b"not a supported document",
            "text/plain",
            415,
            "UNSUPPORTED_FILE_TYPE",
        ),
        (
            "lecture.pdf",
            b"not a PDF",
            "application/pdf",
            415,
            "UNSUPPORTED_FILE_TYPE",
        ),
        (
            "lecture.pdf",
            b"%PDF-1.4\n",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            415,
            "UNSUPPORTED_FILE_TYPE",
        ),
    ],
)
def test_upload_rejects_unsupported_or_mislabeled_content(
    client: TestClient,
    filename: str,
    content: bytes,
    media_type: str,
    status_code: int,
    error_code: str,
) -> None:
    headers = _auth_headers(client, "validation@example.com")

    response = _upload(
        client,
        headers,
        filename=filename,
        content=content,
        media_type=media_type,
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == error_code
    with app.state.testing_session_factory() as db:
        assert db.scalar(select(Document)) is None
        assert db.scalar(select(ProcessingJob)) is None


def test_upload_enforces_configured_size_limit_without_persisting(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(client, "large@example.com")
    monkeypatch.setattr(settings, "document_max_upload_bytes", 64, raising=False)

    response = _upload(client, headers, content=b"%PDF-1.4\n" + b"x" * 64)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
    with app.state.testing_session_factory() as db:
        assert db.scalar(select(Document)) is None
        assert db.scalar(select(ProcessingJob)) is None


def test_documents_are_paginated_and_owner_scoped(client: TestClient) -> None:
    owner_headers = _auth_headers(client, "owner@example.com")
    other_headers = _auth_headers(client, "other@example.com")
    uploaded = _upload(client, owner_headers)
    document_id = uploaded.json()["document"]["id"]

    owner_page = client.get("/api/v1/documents", headers=owner_headers)
    other_page = client.get("/api/v1/documents", headers=other_headers)
    own_document = client.get(
        f"/api/v1/documents/{document_id}",
        headers=owner_headers,
    )
    other_document = client.get(
        f"/api/v1/documents/{document_id}",
        headers=other_headers,
    )

    assert owner_page.status_code == 200
    assert owner_page.json()["total"] == 1
    assert set(owner_page.json()) == {"items", "page", "page_size", "total"}
    assert len(owner_page.json()["items"]) == 1
    assert other_page.status_code == 200
    assert other_page.json()["total"] == 0
    assert own_document.status_code == 200
    assert other_document.status_code == 404
    assert other_document.json()["error"]["code"] == "NOT_FOUND"


def test_processing_failure_retry_and_delete_lifecycle(client: TestClient) -> None:
    headers = _auth_headers(client, "lifecycle@example.com")
    failed_upload = _upload(
        client,
        headers,
        filename="corrupt.pdf",
        content=b"%PDF-1.4\ncorrupt",
    )
    failed_id = failed_upload.json()["document"]["id"]

    assert failed_upload.status_code == 202
    with app.state.testing_session_factory() as db:
        assert process_next_job(db) is True
        failed_document = db.get(Document, UUID(failed_id))
        assert failed_document is not None
        assert failed_document.status == "FAILED"
        assert failed_document.failure_code

    retry = client.post(
        f"/api/v1/documents/{failed_id}/retry",
        headers=headers,
    )
    assert retry.status_code == 202
    assert retry.json()["status"] in {"QUEUED", "RETRY_WAIT"}
    assert client.post(
        f"/api/v1/documents/{failed_id}/retry",
        headers=headers,
    ).status_code == 409

    with app.state.testing_session_factory() as db:
        retry_document = db.get(Document, UUID(failed_id))
        assert retry_document is not None
        (Path(settings.document_storage_dir) / retry_document.storage_key).write_bytes(
            _pdf_with_text()
        )
        assert process_next_job(db) is True
        ready_document = db.get(Document, UUID(failed_id))
        assert ready_document is not None
        assert ready_document.status == "READY"
        assert ready_document.page_count == 1
        chunks = db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == UUID(failed_id)
            )
        ).all()
        assert chunks
        assert "NoteWise learning content" in chunks[0].content

    assert client.post(
        f"/api/v1/documents/{failed_id}/retry",
        headers=headers,
    ).status_code == 409
    deletion = client.delete(
        f"/api/v1/documents/{failed_id}",
        headers=headers,
    )
    assert deletion.status_code == 202
    assert deletion.json()["document_id"] == failed_id
    assert deletion.json()["status"] == "DELETING"
    assert client.get("/api/v1/documents", headers=headers).json()["total"] == 0
    with app.state.testing_session_factory() as db:
        assert process_next_job(db) is True
        deleted_document = db.get(Document, UUID(failed_id))
        assert deleted_document is not None
        assert deleted_document.status == "DELETED"
        assert db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == UUID(failed_id)
            )
        ).all() == []
        assert not (Path(settings.document_storage_dir) / deleted_document.storage_key).exists()

    repeated_delete = client.delete(
        f"/api/v1/documents/{failed_id}",
        headers=headers,
    )
    assert repeated_delete.status_code == 202
    assert repeated_delete.json()["status"] == "DELETED"


def test_foreign_owner_cannot_retry_or_delete_document(client: TestClient) -> None:
    owner_headers = _auth_headers(client, "owner@example.com")
    other_headers = _auth_headers(client, "other@example.com")
    document_id = _upload(client, owner_headers).json()["document"]["id"]

    retry = client.post(
        f"/api/v1/documents/{document_id}/retry",
        headers=other_headers,
    )
    deletion = client.delete(
        f"/api/v1/documents/{document_id}",
        headers=other_headers,
    )

    assert retry.status_code == 404
    assert deletion.status_code == 404

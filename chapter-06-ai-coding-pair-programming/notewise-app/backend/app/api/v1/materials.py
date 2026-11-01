import asyncio
import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.db import get_db_session
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.material import DocumentRead
from app.services.documents import (
    DocumentEmbeddingError,
    DocumentEmbeddingUnavailable,
    DocumentProcessingError,
    DocumentStorageCleanupError,
    create_processing_document,
    delete_user_document,
    list_user_documents,
    process_document,
    remove_stored_file,
    set_document_status,
)
from app.services.embeddings import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["materials"])


def _safe_upload_title(filename: str | None) -> tuple[str, str]:
    if not filename:
        raise HTTPException(
            status_code=422,
            detail="A filename is required.",
        )
    name = Path(filename.replace("\\", "/")).name.strip()
    suffix = Path(name).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and TXT files are supported.",
        )
    title = name[:255]
    return title, suffix[1:]


def _validate_upload_signature(file_type: str, content: bytes) -> None:
    if file_type == "pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=422,
            detail="The uploaded file is not a valid PDF.",
        )
    if file_type == "txt":
        if b"\x00" in content:
            raise HTTPException(
                status_code=422,
                detail="Text files must contain UTF-8 text.",
            )
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail="Text files must use UTF-8 encoding.",
            ) from exc


def _document_read(document: Document, chunk_count: int) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        title=document.title,
        file_type=document.file_type,
        status=document.status,
        created_at=document.created_at,
        chunk_count=chunk_count,
    )


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_material(
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> DocumentRead:
    title, file_type = _safe_upload_title(file.filename)
    content = await file.read(settings.max_upload_size_bytes + 1)
    await file.close()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail="The uploaded file exceeds the configured size limit.",
        )
    if not content:
        raise HTTPException(
            status_code=422,
            detail="The uploaded file is empty.",
        )
    _validate_upload_signature(file_type, content)

    storage_root = settings.document_storage_path.resolve()
    user_storage = storage_root / str(current_user.id)
    file_path = user_storage / f"{uuid4()}.{file_type}"
    document = await create_processing_document(
        session,
        user_id=current_user.id,
        title=title,
        file_type=file_type,
        file_path=file_path,
    )
    try:
        await asyncio.to_thread(user_storage.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(file_path.write_bytes, content)
    except OSError as exc:
        logger.exception("Could not store uploaded document for user %s", current_user.id)
        await set_document_status(session, document, DocumentStatus.FAILED.value)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is unavailable.",
        ) from exc

    try:
        chunks = await process_document(session, document, content, embedding_service)
    except DocumentEmbeddingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except DocumentEmbeddingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return _document_read(document, len(chunks))


@router.get("/", response_model=list[DocumentRead])
async def list_materials(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DocumentRead]:
    documents = await list_user_documents(session, current_user.id)
    return [_document_read(document, chunk_count) for document, chunk_count in documents]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    file_path = await delete_user_document(session, current_user.id, document_id)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    try:
        await remove_stored_file(file_path)
    except DocumentStorageCleanupError as exc:
        logger.exception("Could not remove stored document %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

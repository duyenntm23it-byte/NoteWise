from __future__ import annotations

import asyncio
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.embeddings import (
    EmbeddingDimensionError,
    EmbeddingProviderError,
    EmbeddingService,
    EmbeddingServiceUnavailable,
    validate_embedding_dimensions,
)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_CHUNK_BOUNDARY_BACKTRACK = 150


class DocumentProcessingError(Exception):
    pass


class DocumentTextError(DocumentProcessingError):
    pass


class DocumentEmbeddingError(DocumentProcessingError):
    pass


class DocumentEmbeddingUnavailable(DocumentProcessingError):
    pass


class DocumentStorageCleanupError(Exception):
    pass


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None
    chunk_index: int


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            lower_bound = max(start + chunk_size // 2, end - MAX_CHUNK_BOUNDARY_BACKTRACK)
            boundary = text.rfind(" ", lower_bound, end)
            if boundary > start:
                end = boundary

        content = text[start:end].strip()
        if content:
            chunks.append(content)
        if end >= len(text):
            break
        next_start = end - chunk_overlap
        if next_start <= start:
            raise ValueError("Chunk settings did not advance the input window")
        start = next_start
    return chunks


def extract_document_pages(file_type: str, content: bytes) -> list[tuple[int | None, str]]:
    if file_type == "txt":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentTextError("Text files must use UTF-8 encoding.") from exc
        pages = [(None, text)]
    elif file_type == "pdf":
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            pages = [
                (index + 1, page.extract_text() or "")
                for index, page in enumerate(reader.pages)
            ]
        except (PdfReadError, ValueError, OSError) as exc:
            raise DocumentTextError("The uploaded PDF could not be read.") from exc
    else:
        raise DocumentTextError("Only PDF and TXT files are supported.")

    if not any(text.strip() for _, text in pages):
        raise DocumentTextError("The document contains no extractable text.")
    return pages


def build_chunks(pages: list[tuple[int | None, str]]) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page_number, text in pages:
        for chunk in chunk_text(text):
            chunks.append(
                TextChunk(content=chunk, page_number=page_number, chunk_index=len(chunks))
            )
    return chunks


async def create_processing_document(
    session: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    file_type: str,
    file_path: Path,
) -> Document:
    document = Document(
        user_id=user_id,
        title=title,
        file_type=file_type,
        file_path=str(file_path),
        status=DocumentStatus.PROCESSING.value,
    )
    async with session.begin():
        session.add(document)
        await session.flush()
    return document


async def process_document(
    session: AsyncSession,
    document: Document,
    file_content: bytes,
    embedding_service: EmbeddingService,
) -> list[DocumentChunk]:
    try:
        pages = extract_document_pages(document.file_type, file_content)
        chunks = build_chunks(pages)
        embeddings = await embedding_service.embed_documents([chunk.content for chunk in chunks])
        validate_embedding_dimensions(embeddings, len(chunks))
    except EmbeddingServiceUnavailable as exc:
        await set_document_status(session, document, DocumentStatus.FAILED.value)
        raise DocumentEmbeddingUnavailable(str(exc)) from exc
    except (EmbeddingProviderError, EmbeddingDimensionError) as exc:
        await set_document_status(session, document, DocumentStatus.FAILED.value)
        raise DocumentEmbeddingError(str(exc)) from exc
    except DocumentTextError:
        await set_document_status(session, document, DocumentStatus.FAILED.value)
        raise

    document_chunks = [
        DocumentChunk(
            document_id=document.id,
            content=chunk.content,
            embedding=embedding,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    async with session.begin():
        session.add_all(document_chunks)
        document.status = DocumentStatus.READY.value
        await session.flush()
    return document_chunks


async def set_document_status(
    session: AsyncSession, document: Document, status: str
) -> None:
    async with session.begin():
        document.status = status
        await session.flush()


async def list_user_documents(
    session: AsyncSession, user_id: UUID
) -> list[tuple[Document, int]]:
    statement = (
        select(Document, func.count(DocumentChunk.id).label("chunk_count"))
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .where(Document.user_id == user_id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
    )
    result = await session.execute(statement)
    return [(document, count) for document, count in result.all()]


async def delete_user_document(
    session: AsyncSession, user_id: UUID, document_id: UUID
) -> Path | None:
    async with session.begin():
        document = await session.scalar(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
            .with_for_update()
        )
        if document is None:
            return None
        file_path = Path(document.file_path)
        await session.delete(document)
        await session.flush()
    return file_path


async def remove_stored_file(file_path: Path) -> None:
    try:
        await asyncio.to_thread(file_path.unlink, missing_ok=True)
    except OSError as exc:
        raise DocumentStorageCleanupError(
            "The document record was deleted, but its stored file could not be removed."
        ) from exc
import uuid
import math

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models.document import Document, DocumentChunk, ProcessingJob, Summary
from app.services.ai import (
    AIProviderError,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIMENSION,
    generate_summary,
    provider,
)
from app.services.analytics import record_learning_event

SUMMARY_JOB = "SUMMARY_GENERATE"


def create_summary_job(
    db: Session,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    idempotency_key: str | None,
) -> tuple[Summary, ProcessingJob]:
    request_hash = f"summary:{document_id}"
    if idempotency_key:
        existing = db.scalar(
            select(ProcessingJob).where(
                ProcessingJob.user_id == user_id,
                ProcessingJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if (
                existing.job_type != SUMMARY_JOB
                or existing.request_hash != request_hash
                or existing.summary_id is None
            ):
                raise ApiError(
                    409,
                    "IDEMPOTENCY_CONFLICT",
                    "The idempotency key was already used for a different request.",
                )
            summary = db.get(Summary, existing.summary_id)
            if summary is not None:
                return summary, existing

    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
            Document.status == "READY",
        )
    )
    if document is None:
        owned_document = db.scalar(
            select(Document.id).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        if owned_document is None:
            raise ApiError(404, "NOT_FOUND", "Document not found.")
        raise ApiError(
            409,
            "STATE_CONFLICT",
            "Only a ready document can be summarized.",
        )

    chunks = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.user_id == user_id,
            DocumentChunk.document_id == document_id,
        )
        .order_by(DocumentChunk.chunk_index)
    ).all()
    if not chunks:
        raise ApiError(409, "STATE_CONFLICT", "The document has no usable content.")
    summary = Summary(
        id=uuid.uuid4(),
        user_id=user_id,
        document_id=document_id,
        status="QUEUED",
    )
    db.add(summary)
    db.flush()
    job = ProcessingJob(
        user_id=user_id,
        document_id=document_id,
        summary_id=summary.id,
        job_type=SUMMARY_JOB,
        status="QUEUED",
        max_attempts=settings.document_job_max_attempts,
        idempotency_key=idempotency_key,
        request_hash=request_hash if idempotency_key else None,
    )
    db.add(job)
    record_learning_event(
        db,
        user_id,
        "SUMMARY_CREATED",
        document_id=document.id,
        document_title=document.filename,
        details={"summary_id": str(summary.id)},
    )
    try:
        db.commit()
        db.refresh(summary)
        db.refresh(job)
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "The idempotency key was already used for a different request.",
        ) from exc
    return summary, job


def get_summary(db: Session, user_id: uuid.UUID, summary_id: uuid.UUID) -> Summary:
    summary = db.scalar(
        select(Summary).where(
            Summary.id == summary_id,
            Summary.user_id == user_id,
        )
    )
    if summary is None:
        raise ApiError(404, "NOT_FOUND", "Summary not found.")
    return summary


def process_summary_job(db: Session, job: ProcessingJob) -> None:
    summary = db.get(Summary, job.summary_id)
    document = db.get(Document, job.document_id)
    if summary is None or document is None or document.status != "READY":
        if summary is not None:
            summary.status = "DELETED" if document is None else "FAILED"
            summary.failure_code = None if document is None else "STATE_CONFLICT"
        job.status = "CANCELLED" if document is None else "FAILED"
        job.last_error_code = None if document is None else "STATE_CONFLICT"
        job.lease_expires_at = None
        db.commit()
        return
    summary.status = "PROCESSING"
    db.commit()
    chunks = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.user_id == job.user_id,
            DocumentChunk.document_id == job.document_id,
        )
        .order_by(DocumentChunk.chunk_index)
    ).all()
    content = "\n\n".join(chunk.content for chunk in chunks)
    try:
        result = generate_summary(content)
    except AIProviderError as exc:
        summary.status = "FAILED"
        summary.failure_code = exc.code
        job.status = "FAILED"
        job.last_error_code = exc.code
    else:
        summary.content = result
        summary.status = "READY"
        summary.failure_code = None
        job.status = "SUCCEEDED"
        job.last_error_code = None
    document_status = db.scalar(
        select(Document.status).where(
            Document.id == job.document_id,
            Document.user_id == job.user_id,
        )
    )
    if document_status != "READY":
        summary.content = None
        summary.status = "DELETED"
        summary.failure_code = None
        job.status = "CANCELLED"
        job.last_error_code = None
    job.lease_expires_at = None
    db.commit()


def process_embedding_backfill(
    db: Session,
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> int:
    chunks = db.scalars(
        select(DocumentChunk)
        .join(
            Document,
            (Document.id == DocumentChunk.document_id)
            & (Document.user_id == DocumentChunk.user_id),
        )
        .where(
            Document.status == "READY",
            DocumentChunk.embedding.is_(None),
        )
        .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        .limit(batch_size)
    ).all()
    if not chunks:
        return 0
    vectors = provider.embed_texts([chunk.content for chunk in chunks])
    if len(vectors) != len(chunks) or any(
        len(vector) != EMBEDDING_DIMENSION
        or any(not math.isfinite(value) for value in vector)
        for vector in vectors
    ):
        raise AIProviderError("AI_OUTPUT_INVALID")
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk.embedding = vector
    db.commit()
    return len(chunks)

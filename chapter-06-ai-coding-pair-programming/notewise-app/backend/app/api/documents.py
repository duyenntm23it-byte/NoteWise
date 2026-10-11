from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import DocumentRateLimiter
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import (
    DocumentAccepted,
    DocumentDeletion,
    DocumentPage,
    DocumentResponse,
    DocumentStatus,
    JobAccepted,
)
from app.schemas.errors import ErrorResponse
from app.services.documents import (
    create_document,
    create_retry_job,
    request_document_deletion,
)

router = APIRouter(prefix="/documents", tags=["Documents"])
document_rate_limiter = DocumentRateLimiter()


def enforce_document_upload_limit(request: Request) -> None:
    limiter: DocumentRateLimiter = getattr(
        request.app.state,
        "document_rate_limiter",
        document_rate_limiter,
    )
    limiter.check_upload(request.client.host if request.client else "unknown")


@router.get(
    "",
    operation_id="listDocuments",
    response_model=DocumentPage,
    responses={401: {"model": ErrorResponse, "description": "Authentication required"}},
)
def list_documents(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    document_status: Annotated[
        DocumentStatus | None,
        Query(alias="status"),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentPage:
    filters = [Document.user_id == current_user.id]
    if document_status is None:
        filters.append(Document.status.not_in(("DELETING", "DELETED")))
    else:
        filters.append(Document.status == document_status)
    total = db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    items = db.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc(), Document.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentPage(
        items=[DocumentResponse.model_validate(document) for document in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    operation_id="uploadDocument",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentAccepted,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        409: {"model": ErrorResponse, "description": "Idempotency conflict"},
        413: {"model": ErrorResponse, "description": "Uploaded file is too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        429: {"model": ErrorResponse, "description": "Upload rate limit exceeded"},
        503: {"model": ErrorResponse, "description": "Processing unavailable"},
    },
    dependencies=[Depends(enforce_document_upload_limit)],
)
def upload_document(
    file: UploadFile = File(...),
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentAccepted:
    if file.filename is None:
        raise ApiError(422, "VALIDATION_ERROR", "A filename is required.")
    document, job = create_document(
        db,
        current_user.id,
        file.filename,
        file.content_type or "",
        file.file,
        idempotency_key,
    )
    return DocumentAccepted(
        document=DocumentResponse.model_validate(document),
        job_id=job.id,
    )


@router.get(
    "/{document_id}",
    operation_id="getDocument",
    response_model=DocumentResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    if document is None:
        raise ApiError(404, "NOT_FOUND", "Document not found.")
    return DocumentResponse.model_validate(document)


@router.post(
    "/{document_id}/retry",
    operation_id="retryDocumentProcessing",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobAccepted,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        409: {"model": ErrorResponse, "description": "Document state conflict"},
    },
)
def retry_document(
    document_id: UUID,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobAccepted:
    job = create_retry_job(
        db,
        current_user.id,
        document_id,
        idempotency_key,
    )
    return JobAccepted(job_id=job.id, status="QUEUED")


@router.delete(
    "/{document_id}",
    operation_id="deleteDocument",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentDeletion,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        409: {"model": ErrorResponse, "description": "Document state conflict"},
    },
)
def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDeletion:
    document, _ = request_document_deletion(db, current_user.id, document_id)
    return DocumentDeletion(
        document_id=document.id,
        status=document.status,
    )

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import DocumentRateLimiter
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.errors import ErrorResponse
from app.schemas.learning import (
    AnsweredResponse,
    Citation,
    InsufficientEvidenceResponse,
    QuestionRequest,
    QuestionResponse,
    SummaryAccepted,
    SummaryResponse,
)
from app.services.ai import AIProviderError, generate_grounded_answer, retrieve_relevant_chunks
from app.services.learning import create_summary_job, get_summary
from app.services.analytics import record_learning_event

router = APIRouter(tags=["Learning"])
ai_rate_limiter = DocumentRateLimiter()


def enforce_ai_rate_limit(request: Request) -> None:
    limiter: DocumentRateLimiter = getattr(
        request.app.state,
        "ai_rate_limiter",
        ai_rate_limiter,
    )
    limiter.check_ai(request.client.host if request.client else "unknown")


def _raise_provider_error(error: AIProviderError) -> None:
    status_code = {
        "AI_OUTPUT_INVALID": 502,
        "AI_PROVIDER_UNAVAILABLE": 503,
        "AI_TIMEOUT": 504,
    }.get(error.code)
    if status_code is None:
        raise error
    raise ApiError(status_code, error.code, "The AI service could not complete this request.")


@router.post(
    "/documents/{document_id}/summaries",
    operation_id="createSummary",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SummaryAccepted,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    dependencies=[Depends(enforce_ai_rate_limit)],
)
def request_summary(
    document_id: UUID,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryAccepted:
    summary, job = create_summary_job(
        db,
        current_user.id,
        document_id,
        idempotency_key,
    )
    return SummaryAccepted(
        summary=SummaryResponse.model_validate(summary),
        job_id=job.id,
    )


@router.get(
    "/summaries/{summary_id}",
    operation_id="getSummary",
    response_model=SummaryResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def read_summary(
    summary_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    return SummaryResponse.model_validate(get_summary(db, current_user.id, summary_id))


@router.post(
    "/documents/{document_id}/questions",
    operation_id="askDocumentQuestion",
    response_model=QuestionResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
    dependencies=[Depends(enforce_ai_rate_limit)],
)
def ask_question(
    document_id: UUID,
    payload: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnsweredResponse | InsufficientEvidenceResponse:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    if document is None:
        raise ApiError(404, "NOT_FOUND", "Document not found.")
    if document.status != "READY":
        raise ApiError(
            409,
            "STATE_CONFLICT",
            "Only a ready document can answer questions.",
        )
    try:
        evidence = retrieve_relevant_chunks(
            db,
            current_user.id,
            document_id,
            payload.question,
        )
    except AIProviderError as exc:
        _raise_provider_error(exc)
    if not evidence:
        record_learning_event(
            db,
            current_user.id,
            "QUESTION_ASKED",
            document_id=document.id,
            document_title=document.filename,
            details={"status": "INSUFFICIENT_EVIDENCE", "question_length": len(payload.question)},
        )
        db.commit()
        return InsufficientEvidenceResponse(citations=[])
    try:
        generated = generate_grounded_answer(payload.question, evidence)
    except AIProviderError as exc:
        _raise_provider_error(exc)
    if generated.get("status") == "insufficient_evidence":
        record_learning_event(
            db,
            current_user.id,
            "QUESTION_ASKED",
            document_id=document.id,
            document_title=document.filename,
            details={"status": "INSUFFICIENT_EVIDENCE", "question_length": len(payload.question)},
        )
        db.commit()
        return InsufficientEvidenceResponse(citations=[])
    answer = generated.get("answer")
    raw_citations = generated.get("citations")
    if (
        generated.get("status") != "answered"
        or not isinstance(answer, str)
        or not answer.strip()
        or not isinstance(raw_citations, list)
        or not raw_citations
    ):
        raise ApiError(502, "AI_OUTPUT_INVALID", "The AI service returned an invalid answer.")
    chunks_by_id = {str(item["chunk_id"]): item for item in evidence}
    citations: list[Citation] = []
    seen: set[str] = set()
    for raw_id in raw_citations:
        chunk_id = str(raw_id)
        item = chunks_by_id.get(chunk_id)
        if item is None:
            raise ApiError(
                502,
                "AI_OUTPUT_INVALID",
                "The AI service returned an ungrounded citation.",
            )
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        citations.append(
            Citation(
                chunk_id=UUID(chunk_id),
                page_number=item["page_number"],
                section=item["section"],
                excerpt=str(item["content"])[:1200],
            )
        )
    record_learning_event(
        db,
        current_user.id,
        "QUESTION_ASKED",
        document_id=document.id,
        document_title=document.filename,
        details={"status": "ANSWERED", "question_length": len(payload.question)},
    )
    db.commit()
    return AnsweredResponse(answer=answer.strip(), citations=citations)

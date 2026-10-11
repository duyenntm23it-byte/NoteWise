from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.errors import ErrorResponse
from app.schemas.learning import (
    AccuracyAnalytics,
    AnalyticsOverview,
    DocumentChunkResponse,
    LearningEventType,
    LearningHistoryPage,
    RecommendationPage,
    WeakTopicPage,
)
from app.services.analytics import (
    get_analytics_overview,
    get_accuracy_analytics,
    get_learning_history,
    get_recommendations,
    get_weak_topics,
)

router = APIRouter()


@router.get(
    "/analytics/overview",
    operation_id="getAnalyticsOverview",
    tags=["Analytics"],
    response_model=AnalyticsOverview,
    responses={401: {"model": ErrorResponse}},
)
def read_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsOverview:
    return get_analytics_overview(db, current_user.id)


@router.get(
    "/analytics/accuracy",
    operation_id="getAccuracyAnalytics",
    tags=["Analytics"],
    response_model=AccuracyAnalytics,
    responses={401: {"model": ErrorResponse}},
)
def read_accuracy_analytics(
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccuracyAnalytics:
    return get_accuracy_analytics(db, current_user.id, from_=from_, to=to)


@router.get(
    "/analytics/weak-topics",
    operation_id="getWeakTopics",
    tags=["Analytics"],
    response_model=WeakTopicPage,
    responses={401: {"model": ErrorResponse}},
)
def read_weak_topics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeakTopicPage:
    return get_weak_topics(db, current_user.id)


@router.get(
    "/recommendations",
    operation_id="listRecommendations",
    tags=["Recommendations"],
    response_model=RecommendationPage,
    responses={401: {"model": ErrorResponse}},
)
def read_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationPage:
    return get_recommendations(db, current_user.id)


@router.get(
    "/learning-history",
    operation_id="listLearningHistory",
    tags=["History"],
    response_model=LearningHistoryPage,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def read_learning_history(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    event_type: LearningEventType | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningHistoryPage:
    return get_learning_history(
        db,
        current_user.id,
        page,
        page_size,
        event_type,
    )


@router.get(
    "/documents/{document_id}/chunks/{chunk_id}",
    operation_id="getDocumentChunk",
    tags=["Documents"],
    response_model=DocumentChunkResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def read_document_chunk(
    document_id: UUID,
    chunk_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentChunkResponse:
    chunk = db.scalar(
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.document_id == document_id,
            DocumentChunk.user_id == current_user.id,
            Document.user_id == current_user.id,
            Document.status == "READY",
        )
    )
    if chunk is None:
        raise ApiError(404, "NOT_FOUND", "Document passage not found.")
    return DocumentChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        content=chunk.content,
        page_number=chunk.page_number,
        section=chunk.section,
    )

import re
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.analytics import (
    LearningHistory,
    Recommendation as RecommendationRecord,
    WeakTopicSnapshot,
)
from app.models.document import Document, DocumentChunk
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion
from app.schemas.learning import (
    AccuracyAnalytics,
    AnalyticsOverview,
    LearningEventType,
    LearningHistoryItem,
    LearningHistoryPage,
    Recommendation,
    RecommendationPage,
    WeakTopic,
    WeakTopicPage,
)

WEAK_TOPIC_THRESHOLD = Decimal("60")
MIN_TOPIC_ATTEMPTS = 2


def _normalize_topic(topic: str) -> tuple[str, str]:
    display = re.sub(r"\s+", " ", topic).strip()
    return display.casefold(), display


def get_analytics_overview(db: Session, user_id: uuid.UUID) -> AnalyticsOverview:
    average_score = db.scalar(
        select(func.avg(QuizAttempt.score)).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == "SUBMITTED",
            QuizAttempt.score.is_not(None),
        )
    )
    document_count = db.scalar(
        select(func.count())
        .select_from(Document)
        .where(
            Document.user_id == user_id,
            Document.status.not_in(("DELETING", "DELETED")),
        )
    )
    completed_quiz_count = db.scalar(
        select(func.count())
        .select_from(QuizAttempt)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == "SUBMITTED",
        )
    )
    return AnalyticsOverview(
        average_score=(
            float(Decimal(str(average_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            if average_score is not None
            else None
        ),
        document_count=document_count or 0,
        completed_quiz_count=completed_quiz_count or 0,
    )


def get_accuracy_analytics(
    db: Session,
    user_id: uuid.UUID,
    *,
    from_: datetime | None = None,
    to: datetime | None = None,
) -> AccuracyAnalytics:
    filters = [
        QuizAttempt.user_id == user_id,
        QuizAttempt.status == "SUBMITTED",
    ]
    if from_ is not None:
        filters.append(QuizAttempt.submitted_at >= from_)
    if to is not None:
        filters.append(QuizAttempt.submitted_at < to)
    answers = db.execute(
        select(QuizAnswer.is_correct, QuizAnswer.answered_at)
        .join(QuizAttempt, QuizAttempt.id == QuizAnswer.attempt_id)
        .where(*filters)
    ).all()
    answered = [is_correct for is_correct, answered_at in answers if answered_at is not None]
    correct_count = sum(is_correct is True for is_correct in answered)
    skipped_count = len(answers) - len(answered)
    accuracy = (
        float(
            (Decimal(correct_count) * Decimal(100) / Decimal(len(answered))).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        )
        if answered
        else None
    )
    return AccuracyAnalytics(
        accuracy=accuracy,
        correct_count=correct_count,
        answered_count=len(answered),
        skipped_count=skipped_count,
    )


def _calculate_weak_topics(db: Session, user_id: uuid.UUID) -> list[WeakTopic]:
    rows = db.execute(
        select(
            QuizAttempt.id,
            QuizAttempt.submitted_at,
            Quiz.topic,
            QuizAnswer.is_correct,
            QuizAnswer.answered_at,
        )
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .join(QuizAnswer, QuizAnswer.attempt_id == QuizAttempt.id)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.status == "SUBMITTED",
            Quiz.topic.is_not(None),
        )
        .order_by(Quiz.topic, QuizAttempt.submitted_at, QuizAttempt.id)
    ).all()
    grouped: dict[str, dict[str, Any]] = {}
    for attempt_id, _, raw_topic, is_correct, answered_at in rows:
        if not raw_topic:
            continue
        topic_key, display_topic = _normalize_topic(raw_topic)
        current = grouped.setdefault(
            topic_key,
            {
                "topic": display_topic,
                "attempt_ids": set(),
                "answered_count": 0,
                "correct_count": 0,
                "skipped_count": 0,
            },
        )
        current["attempt_ids"].add(attempt_id)
        if answered_at is None:
            current["skipped_count"] += 1
        else:
            current["answered_count"] += 1
            current["correct_count"] += int(is_correct is True)

    result: list[WeakTopic] = []
    for topic_key, values in grouped.items():
        attempts = len(values["attempt_ids"])
        answered_count = values["answered_count"]
        accuracy = (
            float(
                (Decimal(values["correct_count"]) * Decimal(100) / Decimal(answered_count))
                .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
            if answered_count
            else None
        )
        sufficient_data = attempts >= MIN_TOPIC_ATTEMPTS and accuracy is not None
        is_weak = (
            sufficient_data
            and accuracy is not None
            and Decimal(str(accuracy)) < WEAK_TOPIC_THRESHOLD
        )
        if attempts < MIN_TOPIC_ATTEMPTS:
            reason = f"At least {MIN_TOPIC_ATTEMPTS} submitted attempts are needed."
        elif accuracy is None:
            reason = "No non-skipped answers are available."
        elif is_weak:
            reason = f"Accuracy is below 60% across {attempts} submitted attempts."
        else:
            reason = None
        result.append(
            WeakTopic(
                topic=values["topic"],
                accuracy=accuracy,
                attempts=attempts,
                answered_count=answered_count,
                skipped_count=values["skipped_count"],
                sufficient_data=sufficient_data,
                is_weak=is_weak,
                reason=reason,
            )
        )
    return sorted(
        result,
        key=lambda item: (
            not item.is_weak,
            item.accuracy if item.accuracy is not None else 101,
            _normalize_topic(item.topic)[0],
        ),
    )


def _recommendations_for_weak_topics(
    db: Session,
    user_id: uuid.UUID,
    weak_topics: list[WeakTopic],
) -> list[Recommendation]:
    items: list[Recommendation] = []
    for weak_topic in weak_topics:
        if not weak_topic.is_weak:
            continue
        topic_key, _ = _normalize_topic(weak_topic.topic)
        evidence = db.execute(
            select(
                Quiz.topic,
                func.max(QuizAttempt.submitted_at),
                Document.id,
                Document.filename,
                DocumentChunk.id,
                DocumentChunk.page_number,
                func.count(QuizAnswer.id),
            )
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .join(QuizAnswer, QuizAnswer.attempt_id == QuizAttempt.id)
            .join(QuizQuestion, QuizQuestion.id == QuizAnswer.question_id)
            .join(DocumentChunk, DocumentChunk.id == QuizQuestion.citation_chunk_id)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.status == "SUBMITTED",
                QuizAnswer.answered_at.is_not(None),
                QuizAnswer.is_correct.is_(False),
                Quiz.topic.is_not(None),
                Document.user_id == user_id,
                Document.status == "READY",
                DocumentChunk.user_id == user_id,
            )
            .group_by(
                Quiz.topic,
                Document.id,
                Document.filename,
                DocumentChunk.id,
                DocumentChunk.page_number,
            )
            .order_by(
                func.count(QuizAnswer.id).desc(),
                DocumentChunk.page_number,
                DocumentChunk.id,
            )
        ).all()
        # Match normalized labels in Python so grouping behaves identically in
        # PostgreSQL and SQLite.
        topic_evidence = [
            row for row in evidence if _normalize_topic(row[0])[0] == topic_key
        ]
        selected = topic_evidence[0] if topic_evidence else None
        latest_submitted = selected[1] if selected else None
        document_id = selected[2] if selected else None
        document_name = selected[3] if selected else None
        chunk_id = selected[4] if selected else None
        page_number = selected[5] if selected else None
        action = (
            f"Review {weak_topic.topic} in {document_name}"
            if document_name
            else f"Review {weak_topic.topic} using your learning materials"
        )
        reason = (
            weak_topic.reason
            or f"Your accuracy for {weak_topic.topic} requires more attention."
        )
        recommendation_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{user_id}:{topic_key}:{chunk_id or 'no-source'}",
        )
        items.append(
            Recommendation(
                id=recommendation_id,
                topic=weak_topic.topic,
                action=action,
                reason=reason,
                document_id=document_id,
                chunk_id=chunk_id,
                page_start=page_number,
                page_end=page_number,
                created_at=latest_submitted or datetime.now().astimezone(),
            )
        )
    return items


def refresh_analytics_snapshots(
    db: Session,
    user_id: uuid.UUID,
) -> tuple[list[WeakTopic], list[Recommendation]]:
    db.flush()
    topics = _calculate_weak_topics(db, user_id)
    recommendations = _recommendations_for_weak_topics(db, user_id, topics)
    db.execute(delete(WeakTopicSnapshot).where(WeakTopicSnapshot.user_id == user_id))
    db.execute(
        delete(RecommendationRecord).where(RecommendationRecord.user_id == user_id)
    )
    db.add_all(
        WeakTopicSnapshot(
            user_id=user_id,
            topic=item.topic,
            topic_key=_normalize_topic(item.topic)[0],
            accuracy=item.accuracy,
            attempts=item.attempts,
            answered_count=item.answered_count,
            skipped_count=item.skipped_count,
            sufficient_data=item.sufficient_data,
            is_weak=item.is_weak,
            reason=item.reason,
            evidence=(
                f"{item.attempts} submitted attempts; "
                f"{item.answered_count} non-skipped answers; "
                f"{item.skipped_count} skipped"
            ),
        )
        for item in topics
    )
    db.add_all(
        RecommendationRecord(
            id=item.id,
            user_id=user_id,
            topic=item.topic,
            action=item.action,
            reason=item.reason,
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            page_start=item.page_start,
            page_end=item.page_end,
            created_at=item.created_at,
        )
        for item in recommendations
    )
    return topics, recommendations


def get_weak_topics(db: Session, user_id: uuid.UUID) -> WeakTopicPage:
    items, _ = refresh_analytics_snapshots(db, user_id)
    db.commit()
    return WeakTopicPage(items=items)


def get_recommendations(db: Session, user_id: uuid.UUID) -> RecommendationPage:
    _, items = refresh_analytics_snapshots(db, user_id)
    db.commit()
    return RecommendationPage(items=items)


def record_learning_event(
    db: Session,
    user_id: uuid.UUID,
    event_type: LearningEventType,
    *,
    document_id: uuid.UUID | None = None,
    document_title: str | None = None,
    details: dict[str, Any] | None = None,
) -> LearningHistory:
    event = LearningHistory(
        user_id=user_id,
        event_type=event_type,
        document_id=document_id,
        document_title=document_title,
        details=details or {},
    )
    db.add(event)
    return event


def get_learning_history(
    db: Session,
    user_id: uuid.UUID,
    page: int,
    page_size: int,
    event_type: LearningEventType | None,
) -> LearningHistoryPage:
    filters = [LearningHistory.user_id == user_id]
    if event_type is not None:
        filters.append(LearningHistory.event_type == event_type)
    total = db.scalar(
        select(func.count()).select_from(LearningHistory).where(*filters)
    ) or 0
    rows = db.scalars(
        select(LearningHistory)
        .where(*filters)
        .order_by(LearningHistory.occurred_at.desc(), LearningHistory.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return LearningHistoryPage(
        items=[LearningHistoryItem.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )

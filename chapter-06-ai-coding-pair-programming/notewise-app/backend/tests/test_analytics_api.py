from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import DocumentRateLimiter
from app.core.security import create_access_token
from app.db.session import Base, get_db
from app.main import app
from app.models.document import Document, DocumentChunk
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion
from app.models.user import User
from app.models.analytics import LearningHistory


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    app.state.testing_session_factory = session_factory
    app.state.disable_document_worker = True
    app.state.ai_rate_limiter = DocumentRateLimiter()

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
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
        "ai_rate_limiter",
    ):
        if hasattr(app.state, state_key):
            delattr(app.state, state_key)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed_learning_data() -> tuple[dict[str, str], UUID, UUID, UUID]:
    user_id = uuid4()
    foreign_user_id = uuid4()
    document_id = uuid4()
    chunk_id = uuid4()
    headers = {"Authorization": f"Bearer {create_access_token(str(user_id))}"}

    with app.state.testing_session_factory() as db:
        db.add(
            User(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="unused",
            )
        )
        db.add(
            User(
                id=foreign_user_id,
                email=f"{foreign_user_id}@example.com",
                password_hash="unused",
            )
        )
        db.add_all(
            [
                Document(
                    id=document_id,
                    user_id=user_id,
                    filename="Decision Trees.pdf",
                    storage_key=f"{document_id}.pdf",
                    media_type="application/pdf",
                    status="READY",
                    page_count=20,
                ),
                Document(
                    id=uuid4(),
                    user_id=user_id,
                    filename="Other notes.pdf",
                    storage_key=f"{uuid4()}.pdf",
                    media_type="application/pdf",
                    status="PROCESSING",
                ),
                Document(
                    id=uuid4(),
                    user_id=foreign_user_id,
                    filename="Private.pdf",
                    storage_key=f"{uuid4()}.pdf",
                    media_type="application/pdf",
                    status="READY",
                ),
                DocumentChunk(
                    id=chunk_id,
                    user_id=user_id,
                    document_id=document_id,
                    chunk_index=0,
                    content="Private passage that must not be included in analytics.",
                    page_number=12,
                    section="Pruning",
                    embedding=None,
                ),
            ]
        )

        quiz_id = uuid4()
        question_ids = [uuid4() for _ in range(5)]
        db.add(
            Quiz(
                id=quiz_id,
                user_id=user_id,
                document_id=document_id,
                title="Decision Trees",
                status="READY",
                question_count=5,
                question_types=["multiple_choice"],
                difficulty="medium",
                topic="  Decision   Trees ",
            )
        )
        db.add_all(
            [
                QuizQuestion(
                    id=question_id,
                    user_id=user_id,
                    quiz_id=quiz_id,
                    document_id=document_id,
                    position=index,
                    question=f"Question {index}",
                    question_type="multiple_choice",
                    options=["correct", "incorrect"],
                    answer_key={"answer": "correct"},
                    explanation="Answer evidence.",
                    citation_chunk_id=chunk_id,
                )
                for index, question_id in enumerate(question_ids, start=1)
            ]
        )
        attempts = [
            (uuid4(), 0.0, [False, None, None, None, None]),
            (uuid4(), 50.0, [True, False, None, None, None]),
        ]
        for attempt_id, score, correctness in attempts:
            db.add(
                QuizAttempt(
                    id=attempt_id,
                    user_id=user_id,
                    quiz_id=quiz_id,
                    status="SUBMITTED",
                    score=score,
                    correct_count=sum(answer is True for answer in correctness),
                    answered_count=sum(answer is not None for answer in correctness),
                    skipped_count=sum(answer is None for answer in correctness),
                    submitted_at=datetime.now(UTC),
                )
            )
            db.add_all(
                QuizAnswer(
                    user_id=user_id,
                    attempt_id=attempt_id,
                    quiz_id=quiz_id,
                    question_id=question_id,
                    submitted_answer="wrong" if is_correct is False else (
                        "correct" if is_correct else None
                    ),
                    is_correct=is_correct,
                    answered_at=datetime.now(UTC) if is_correct is not None else None,
                )
                for question_id, is_correct in zip(question_ids, correctness)
            )
        db.add(
            QuizAttempt(
                id=uuid4(),
                user_id=user_id,
                quiz_id=quiz_id,
                status="IN_PROGRESS",
                score=None,
                correct_count=None,
                answered_count=None,
                skipped_count=None,
            )
        )
        db.add(
            LearningHistory(
                id=uuid4(),
                user_id=user_id,
                event_type="QUIZ_SUBMITTED",
                document_id=document_id,
                document_title="Decision Trees.pdf",
                occurred_at=datetime.now(UTC),
                details={"topic": "Decision Trees", "score": 50.0},
            )
        )
        db.commit()
    return headers, user_id, document_id, chunk_id


def _add_topic_attempts(
    user_id: UUID,
    document_id: UUID,
    chunk_id: UUID,
    topic: str,
    attempts: list[list[bool | None]],
) -> None:
    with app.state.testing_session_factory() as db:
        quiz_id = uuid4()
        question_ids = [uuid4() for _ in range(5)]
        db.add(
            Quiz(
                id=quiz_id,
                user_id=user_id,
                document_id=document_id,
                title=topic,
                status="READY",
                question_count=5,
                question_types=["multiple_choice"],
                difficulty="medium",
                topic=topic,
            )
        )
        db.add_all(
            QuizQuestion(
                id=question_id,
                user_id=user_id,
                quiz_id=quiz_id,
                document_id=document_id,
                position=position,
                question=f"{topic} question {position}",
                question_type="multiple_choice",
                options=["correct", "incorrect"],
                answer_key={"answer": "correct"},
                explanation="Supported by source.",
                citation_chunk_id=chunk_id,
            )
            for position, question_id in enumerate(question_ids, start=1)
        )
        for correctness in attempts:
            attempt_id = uuid4()
            db.add(
                QuizAttempt(
                    id=attempt_id,
                    user_id=user_id,
                    quiz_id=quiz_id,
                    status="SUBMITTED",
                    score=Decimal(sum(answer is True for answer in correctness) * 20),
                    correct_count=sum(answer is True for answer in correctness),
                    answered_count=sum(answer is not None for answer in correctness),
                    skipped_count=sum(answer is None for answer in correctness),
                    submitted_at=datetime.now(UTC),
                )
            )
            db.add_all(
                QuizAnswer(
                    user_id=user_id,
                    attempt_id=attempt_id,
                    quiz_id=quiz_id,
                    question_id=question_id,
                    submitted_answer=(
                        "correct" if is_correct is True else
                        "incorrect" if is_correct is False else None
                    ),
                    is_correct=is_correct,
                    answered_at=datetime.now(UTC) if is_correct is not None else None,
                )
                for question_id, is_correct in zip(question_ids, correctness)
            )
        db.commit()


def test_analytics_routes_match_approved_openapi_contract() -> None:
    paths = app.openapi()["paths"]
    assert paths["/api/v1/analytics/overview"]["get"]["operationId"] == "getAnalyticsOverview"
    assert paths["/api/v1/analytics/accuracy"]["get"]["operationId"] == "getAccuracyAnalytics"
    assert paths["/api/v1/analytics/weak-topics"]["get"]["operationId"] == "getWeakTopics"
    assert paths["/api/v1/recommendations"]["get"]["operationId"] == "listRecommendations"
    assert paths["/api/v1/learning-history"]["get"]["operationId"] == "listLearningHistory"
    for path in (
        "/api/v1/analytics/overview",
        "/api/v1/analytics/accuracy",
        "/api/v1/analytics/weak-topics",
        "/api/v1/recommendations",
        "/api/v1/learning-history",
    ):
        assert paths[path]["get"]["security"] == [{"bearerAuth": []}]
    assert "/api/v1/analytics/recommendations" not in paths
    assert "chunk_id" in app.openapi()["components"]["schemas"]["Recommendation"]["properties"]
    assert paths["/api/v1/documents/{document_id}/chunks/{chunk_id}"]["get"][
        "operationId"
    ] == "getDocumentChunk"


def test_overview_and_accuracy_are_based_only_on_owned_submitted_data(
    client: TestClient,
) -> None:
    headers, _, _, _ = _seed_learning_data()

    overview = client.get("/api/v1/analytics/overview", headers=headers)
    accuracy = client.get("/api/v1/analytics/accuracy", headers=headers)

    assert overview.status_code == 200
    assert overview.json() == {
        "average_score": 25.0,
        "document_count": 2,
        "completed_quiz_count": 2,
    }
    assert accuracy.status_code == 200
    assert accuracy.json() == {
        "accuracy": pytest.approx(33.33),
        "correct_count": 1,
        "answered_count": 3,
        "skipped_count": 7,
    }


def test_weak_topics_exclude_skipped_and_in_progress_attempts(
    client: TestClient,
) -> None:
    headers, _, _, _ = _seed_learning_data()

    response = client.get("/api/v1/analytics/weak-topics", headers=headers)

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "topic": "Decision Trees",
            "accuracy": pytest.approx(33.33),
            "attempts": 2,
            "answered_count": 3,
            "sufficient_data": True,
            "is_weak": True,
            "reason": "Accuracy is below 60% across 2 submitted attempts.",
            "skipped_count": 7,
        }
    ]


def test_weak_topic_threshold_is_strict_and_requires_two_attempts(
    client: TestClient,
) -> None:
    headers, user_id, document_id, chunk_id = _seed_learning_data()
    _add_topic_attempts(
        user_id,
        document_id,
        chunk_id,
        "Boundary",
        [
            [True, True, True, False, False],
            [True, True, True, False, False],
        ],
    )
    _add_topic_attempts(
        user_id,
        document_id,
        chunk_id,
        "Single attempt",
        [[False, False, True, None, None]],
    )

    response = client.get("/api/v1/analytics/weak-topics", headers=headers)

    assert response.status_code == 200
    topics = {item["topic"]: item for item in response.json()["items"]}
    assert topics["Boundary"]["accuracy"] == 60.0
    assert topics["Boundary"]["sufficient_data"] is True
    assert topics["Boundary"]["is_weak"] is False
    assert topics["Single attempt"]["attempts"] == 1
    assert topics["Single attempt"]["sufficient_data"] is False
    assert topics["Single attempt"]["is_weak"] is False


def test_recommendations_link_to_owned_source_chunk_without_excerpt(
    client: TestClient,
) -> None:
    headers, _, document_id, chunk_id = _seed_learning_data()

    response = client.get("/api/v1/recommendations", headers=headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["topic"] == "Decision Trees"
    assert item["document_id"] == str(document_id)
    assert item["chunk_id"] == str(chunk_id)
    assert item["page_start"] == item["page_end"] == 12
    assert "below 60%" in item["reason"]
    assert "Private passage" not in response.text
    passage = client.get(
        f"/api/v1/documents/{document_id}/chunks/{chunk_id}",
        headers=headers,
    )
    assert passage.status_code == 200
    assert passage.json()["page_number"] == 12
    assert passage.json()["content"].startswith("Private passage")
    assert client.get(
        f"/api/v1/documents/{document_id}/chunks/{uuid4()}",
        headers=headers,
    ).status_code == 404


def test_learning_history_is_paginated_and_owner_scoped(client: TestClient) -> None:
    headers, _, _, _ = _seed_learning_data()

    response = client.get("/api/v1/learning-history?page=1&page_size=10", headers=headers)
    unauthorized = client.get("/api/v1/learning-history")

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 10
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["event_type"] == "QUIZ_SUBMITTED"
    assert response.json()["items"][0]["details"]["score"] == 50.0
    assert unauthorized.status_code == 401

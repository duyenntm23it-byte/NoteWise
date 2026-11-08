from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.auth import get_current_user
from app.core.db import get_db_session
from app.main import app
from app.models.base import Base
from app.models.document import Document
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion
from app.models.user import User


@pytest_asyncio.fixture
async def analytics_client() -> AsyncIterator[
    tuple[AsyncClient, UUID, UUID, UUID, UUID, UUID, async_sessionmaker[AsyncSession]]
]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id, other_user_id = uuid4(), uuid4()
    document_id, second_document_id, foreign_document_id = uuid4(), uuid4(), uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add_all(
                [
                    User(id=user_id, email="analytics@example.com", hashed_password="unused"),
                    User(
                        id=other_user_id,
                        email="other-analytics@example.com",
                        hashed_password="unused",
                    ),
                ]
            )

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_current_user() -> User:
        return User(id=user_id, email="analytics@example.com", hashed_password="unused")

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield (
                client,
                user_id,
                other_user_id,
                document_id,
                second_document_id,
                foreign_document_id,
                session_factory,
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user, None)
        await engine.dispose()


async def add_quiz(
    session: AsyncSession,
    *,
    user_id: UUID,
    document_id: UUID,
    question_count: int,
    title: str,
    page_numbers: list[int | None] | None = None,
    chunk_indexes: list[int | None] | None = None,
) -> tuple[Quiz, list[QuizQuestion]]:
    quiz = Quiz(
        user_id=user_id,
        document_id=document_id,
        title=title,
        total_questions=question_count,
    )
    session.add(quiz)
    await session.flush()
    pages = page_numbers or [None] * question_count
    chunks = chunk_indexes or [None] * question_count
    questions = [
        QuizQuestion(
            quiz_id=quiz.id,
            position=index,
            question_text=f"{title} question {index + 1}",
            options=["A", "B", "C", "D"],
            correct_answer=0,
            explanation=f"Secret explanation {index + 1}",
            source_page_number=pages[index],
            source_chunk_index=chunks[index],
        )
        for index in range(question_count)
    ]
    session.add_all(questions)
    await session.flush()
    return quiz, questions


async def add_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    user_id: UUID,
    title: str,
    status: str = "ready",
) -> None:
    session.add(
        Document(
            id=document_id,
            user_id=user_id,
            title=title,
            file_path="unused",
            file_type="pdf",
            status=status,
        )
    )
    await session.flush()


async def add_attempt(
    session: AsyncSession,
    *,
    user_id: UUID,
    quiz: Quiz,
    questions: list[QuizQuestion],
    selected_indexes: list[int | None],
    completed_at: datetime | None = None,
    extra_answers: list[dict[str, Any]] | None = None,
) -> None:
    answers: list[dict[str, Any]] = [
        {"question_id": str(question.id), "selected_index": selected}
        for question, selected in zip(questions, selected_indexes, strict=True)
    ]
    if extra_answers:
        answers.extend(extra_answers)
    session.add(
        QuizAttempt(
            quiz_id=quiz.id,
            user_id=user_id,
            score=sum(selected == 0 for selected in selected_indexes if selected is not None),
            answers=answers,
            completed_at=completed_at or datetime.now(UTC),
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_new_user_has_empty_analytics(analytics_client) -> None:
    client, *_ = analytics_client

    response = await client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_documents": 0,
        "ready_documents": 0,
        "total_quizzes": 0,
        "total_attempts": 0,
        "average_score_percent": None,
        "overall_accuracy_percent": None,
        "documents": [],
        "weak_areas": [],
    }


@pytest.mark.asyncio
async def test_summary_uses_percentage_scores_and_per_document_accuracy(analytics_client) -> None:
    client, user_id, _, document_id, second_document_id, _, session_factory = analytics_client
    async with session_factory() as session:
        async with session.begin():
            await add_document(
                session, document_id=document_id, user_id=user_id, title="Biology"
            )
            await add_document(
                session,
                document_id=second_document_id,
                user_id=user_id,
                title="History",
                status="processing",
            )
            quiz_five, questions_five = await add_quiz(
                session,
                user_id=user_id,
                document_id=document_id,
                question_count=5,
                title="Five",
            )
            quiz_ten, questions_ten = await add_quiz(
                session,
                user_id=user_id,
                document_id=document_id,
                question_count=10,
                title="Ten",
            )
            quiz_other_document, questions_other_document = await add_quiz(
                session,
                user_id=user_id,
                document_id=second_document_id,
                question_count=5,
                title="Other",
            )
            await add_attempt(
                session,
                user_id=user_id,
                quiz=quiz_five,
                questions=questions_five,
                selected_indexes=[0, 0, 1, 1, 1],
            )
            await add_attempt(
                session,
                user_id=user_id,
                quiz=quiz_ten,
                questions=questions_ten,
                selected_indexes=[0] * 8 + [1, 1],
            )
            await add_attempt(
                session,
                user_id=user_id,
                quiz=quiz_other_document,
                questions=questions_other_document,
                selected_indexes=[0, 1, 1, 1, 1],
            )

    response = await client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_documents"] == 2
    assert summary["ready_documents"] == 1
    assert summary["total_quizzes"] == 3
    assert summary["total_attempts"] == 3
    assert summary["average_score_percent"] == pytest.approx((40 + 80 + 20) / 3)
    assert summary["overall_accuracy_percent"] == pytest.approx(11 / 20 * 100)
    documents = {item["document_id"]: item for item in summary["documents"]}
    biology = documents[str(document_id)]
    history = documents[str(second_document_id)]
    assert biology["quiz_count"] == 2
    assert biology["attempt_count"] == 2
    assert biology["average_score_percent"] == 60
    assert biology["accuracy_percent"] == pytest.approx(10 / 15 * 100)
    assert history["quiz_count"] == 1
    assert history["attempt_count"] == 1
    assert history["average_score_percent"] == 20
    assert history["accuracy_percent"] == 20


@pytest.mark.asyncio
async def test_unanswered_is_wrong_and_weak_areas_use_latest_attempt(
    analytics_client,
) -> None:
    client, user_id, _, document_id, _, _, session_factory = analytics_client
    async with session_factory() as session:
        async with session.begin():
            await add_document(
                session, document_id=document_id, user_id=user_id, title="Biology"
            )
            quiz, questions = await add_quiz(
                session,
                user_id=user_id,
                document_id=document_id,
                question_count=5,
                title="Latest",
                page_numbers=[4, 4, None, None, None],
                chunk_indexes=[0, 1, 2, 2, None],
            )
            earlier = datetime.now(UTC) - timedelta(days=1)
            later = datetime.now(UTC)
            await add_attempt(
                session,
                user_id=user_id,
                quiz=quiz,
                questions=questions,
                selected_indexes=[1, 1, 1, 1, None],
                completed_at=earlier,
            )
            await add_attempt(
                session,
                user_id=user_id,
                quiz=quiz,
                questions=questions,
                selected_indexes=[1, 0, None, 1, 0],
                completed_at=later,
            )

    response = await client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_attempts"] == 2
    assert summary["overall_accuracy_percent"] == 20
    assert summary["weak_areas"] == [
        {
            "document_id": str(document_id),
            "document_title": "Biology",
            "topic_label": "Passage 3",
            "wrong_count": 2,
            "total_count": 2,
            "sample_questions": ["Latest question 3", "Latest question 4"],
        },
        {
            "document_id": str(document_id),
            "document_title": "Biology",
            "topic_label": "Page 4",
            "wrong_count": 1,
            "total_count": 2,
            "sample_questions": ["Latest question 1"],
        },
    ]
    assert "correct_answer" not in response.text
    assert "explanation" not in response.text


@pytest.mark.asyncio
async def test_weak_areas_group_general_and_limit_sample_questions(analytics_client) -> None:
    client, user_id, _, document_id, _, _, session_factory = analytics_client
    async with session_factory() as session:
        async with session.begin():
            await add_document(
                session, document_id=document_id, user_id=user_id, title="Biology"
            )
            quiz, questions = await add_quiz(
                session,
                user_id=user_id,
                document_id=document_id,
                question_count=5,
                title="General",
            )
            await add_attempt(
                session,
                user_id=user_id,
                quiz=quiz,
                questions=questions,
                selected_indexes=[1, 1, 1, 1, 0],
            )

    response = await client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    assert response.json()["weak_areas"] == [
        {
            "document_id": str(document_id),
            "document_title": "Biology",
            "topic_label": "General",
            "wrong_count": 4,
            "total_count": 5,
            "sample_questions": [
                "General question 1",
                "General question 2",
                "General question 3",
            ],
        }
    ]


@pytest.mark.asyncio
async def test_foreign_user_data_and_unknown_answer_question_ids_are_ignored(
    analytics_client,
) -> None:
    (
        client,
        user_id,
        other_user_id,
        document_id,
        _,
        foreign_document_id,
        session_factory,
    ) = analytics_client
    async with session_factory() as session:
        async with session.begin():
            await add_document(
                session,
                document_id=foreign_document_id,
                user_id=other_user_id,
                title="Private document",
            )
            foreign_quiz, foreign_questions = await add_quiz(
                session,
                user_id=other_user_id,
                document_id=foreign_document_id,
                question_count=5,
                title="Private quiz",
            )
            await add_attempt(
                session,
                user_id=other_user_id,
                quiz=foreign_quiz,
                questions=foreign_questions,
                selected_indexes=[1] * 5,
            )
            await add_document(
                session, document_id=document_id, user_id=user_id, title="Biology"
            )
            user_quiz, questions = await add_quiz(
                session,
                user_id=user_id,
                document_id=document_id,
                question_count=5,
                title="Owned",
            )
            await add_attempt(
                session,
                user_id=user_id,
                quiz=user_quiz,
                questions=questions,
                selected_indexes=[1, 0, 0, 0, 0],
                extra_answers=[{"question_id": str(uuid4()), "selected_index": 0}],
            )

    response = await client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    assert response.json()["total_quizzes"] == 1
    assert response.json()["total_attempts"] == 1
    assert response.json()["overall_accuracy_percent"] == 80
    assert "Private" not in response.text


@pytest.mark.asyncio
async def test_summary_requires_authentication() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/analytics/summary")

    assert response.status_code == 401

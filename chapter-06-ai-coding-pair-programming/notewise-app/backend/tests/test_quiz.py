from collections.abc import AsyncIterator
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
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.services.quizzes import GeminiQuizGenerator, QuizExcerpt, get_quiz_generator
from app.services.rag import AnswerProviderError

import json

from app.schemas.quiz import (
    GeminiQuestionSchema,
    GeminiQuizSchema,
    GeneratedQuestion,
)

def generated_quiz(
    count: int = 5,
    *,
    options: list[str] | None = None,
    correct_answer: int = 0,
    source_excerpt: int = 1,
) -> dict[str, Any]:
    return {
        "questions": [
            {
                "question_text": f"Question {index + 1}?",
                "options": (
                    options if options is not None else [f"Choice {letter}" for letter in "ABCD"]
                ),
                "correct_answer": correct_answer,
                "explanation": f"Explanation {index + 1}.",
                "source_excerpt": source_excerpt,
            }
            for index in range(count)
        ]
    }


class FakeQuizGenerator:
    def __init__(self, outputs: list[object] | None = None) -> None:
        self.outputs = outputs or []
        self.call_count = 0
        self.contexts: list[list[QuizExcerpt]] = []

    async def generate(self, context: list[QuizExcerpt], num_questions: int) -> object:
        self.call_count += 1
        self.contexts.append(context)
        if self.outputs:
            return self.outputs.pop(0)
        return generated_quiz(num_questions)


class FailingQuizGenerator:
    async def generate(self, context: list[QuizExcerpt], num_questions: int) -> object:
        raise AnswerProviderError("The quiz provider could not generate this quiz.")


@pytest_asyncio.fixture
async def quiz_client() -> AsyncIterator[
    tuple[AsyncClient, UUID, UUID, UUID, FakeQuizGenerator, UUID, UUID]
]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid4()
    other_user_id = uuid4()
    document_id = uuid4()
    processing_document_id = uuid4()
    empty_document_id = uuid4()
    foreign_document_id = uuid4()
    generator = FakeQuizGenerator()
    async with session_factory() as session:
        async with session.begin():
            session.add_all(
                [
                    User(id=user_id, email="quiz@example.com", hashed_password="unused"),
                    User(
                        id=other_user_id,
                        email="other-quiz@example.com",
                        hashed_password="unused",
                    ),
                ]
            )
            session.add_all(
                [
                    Document(
                        id=document_id,
                        user_id=user_id,
                        title="Biology notes.pdf",
                        file_path="unused",
                        file_type="pdf",
                        status="ready",
                    ),
                    Document(
                        id=processing_document_id,
                        user_id=user_id,
                        title="Processing notes.txt",
                        file_path="unused",
                        file_type="txt",
                        status="processing",
                    ),
                    Document(
                        id=empty_document_id,
                        user_id=user_id,
                        title="Empty notes.txt",
                        file_path="unused",
                        file_type="txt",
                        status="ready",
                    ),
                    Document(
                        id=foreign_document_id,
                        user_id=other_user_id,
                        title="Private notes.pdf",
                        file_path="unused",
                        file_type="pdf",
                        status="ready",
                    ),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    DocumentChunk(
                        document_id=document_id,
                        content=f"Passage {index:02d}: " + "evidence " * 120,
                        chunk_index=index,
                        page_number=index + 1,
                    )
                    for index in range(15)
                ]
            )

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_current_user() -> User:
        return User(id=user_id, email="quiz@example.com", hashed_password="unused")

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_quiz_generator] = lambda: generator
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield (
                client,
                user_id,
                document_id,
                foreign_document_id,
                generator,
                processing_document_id,
                empty_document_id,
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_quiz_generator, None)
        await engine.dispose()


async def create_quiz(client: AsyncClient, document_id: UUID) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(document_id), "num_questions": 5},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_generate_quiz_uses_spread_context_and_hides_answer_key(quiz_client) -> None:
    client, _, document_id, _, generator, _, _ = quiz_client

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(document_id), "num_questions": 5},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["total_questions"] == 5
    assert len(payload["questions"]) == 5
    assert all(
        set(question) == {"id", "position", "question_text", "options"}
        for question in payload["questions"]
    )
    assert all(
        "correct_answer" not in question and "explanation" not in question
        for question in payload["questions"]
    )
    assert generator.call_count == 1
    context = generator.contexts[0]
    assert sum(len(excerpt.content) for excerpt in context) <= 12_000
    assert context[0].chunk_index == 0
    assert context[-1].chunk_index == 14
    assert len({excerpt.chunk_index for excerpt in context}) == len(context)


@pytest.mark.asyncio
async def test_generate_quiz_hides_foreign_document(quiz_client) -> None:
    client, _, _, foreign_document_id, generator, _, _ = quiz_client

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(foreign_document_id), "num_questions": 5},
    )

    assert response.status_code == 404
    assert generator.call_count == 0


@pytest.mark.asyncio
async def test_generate_quiz_rejects_document_not_ready(quiz_client) -> None:
    client, _, _, _, generator, processing_document_id, _ = quiz_client

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(processing_document_id), "num_questions": 5},
    )
    assert response.status_code == 409
    assert generator.call_count == 0


@pytest.mark.asyncio
async def test_generate_quiz_rejects_empty_document_without_calling_generator(quiz_client) -> None:
    client, _, _, _, generator, _, empty_document_id = quiz_client

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(empty_document_id), "num_questions": 5},
    )

    assert response.status_code == 422
    assert generator.call_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_output",
    [
        generated_quiz(options=["Only", "three", "choices"]),
        generated_quiz(correct_answer=4),
        generated_quiz(count=4),
        generated_quiz(source_excerpt=99),
        generated_quiz(options=["Same", "Same", "Other", "Last"]),
        {
            "questions": [
                {
                    "question_text": "Repeated?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0,
                    "explanation": "Reason",
                    "source_excerpt": 1,
                },
                {
                    "question_text": " repeated? ",
                    "options": ["E", "F", "G", "H"],
                    "correct_answer": 0,
                    "explanation": "Reason",
                    "source_excerpt": 1,
                },
                *generated_quiz(count=3)["questions"],
            ]
        },
        {"questions": [{"question_text": "Missing choices"}]},
    ],
)
async def test_invalid_quiz_output_regenerates_once_then_returns_502(
    quiz_client, invalid_output: object
) -> None:
    client, _, document_id, _, generator, _, _ = quiz_client
    generator.outputs = [invalid_output, invalid_output]

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(document_id), "num_questions": 5},
    )

    assert response.status_code == 502
    assert generator.call_count == 2


@pytest.mark.asyncio
async def test_generate_quiz_requires_five_or_ten_questions(quiz_client) -> None:
    client, _, document_id, _, generator, _, _ = quiz_client

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(document_id), "num_questions": 7},
    )

    assert response.status_code == 422
    assert generator.call_count == 0


@pytest.mark.asyncio
async def test_generate_ten_questions_after_one_invalid_output(quiz_client) -> None:
    client, _, document_id, _, generator, _, _ = quiz_client
    generator.outputs = [generated_quiz(count=4), generated_quiz(count=10)]

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(document_id), "num_questions": 10},
    )

    assert response.status_code == 201, response.text
    assert response.json()["total_questions"] == 10
    assert len(response.json()["questions"]) == 10
    assert generator.call_count == 2


@pytest.mark.asyncio
async def test_generate_quiz_returns_503_without_google_key(quiz_client) -> None:
    client, _, document_id, _, generator, _, _ = quiz_client
    app.dependency_overrides[get_quiz_generator] = lambda: GeminiQuizGenerator(None)

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(document_id), "num_questions": 5},
    )

    assert response.status_code == 503
    assert "GOOGLE_API_KEY" in response.json()["detail"]
    assert generator.call_count == 0


@pytest.mark.asyncio
async def test_quiz_provider_failure_returns_502(quiz_client) -> None:
    client, _, document_id, _, _, _, _ = quiz_client
    app.dependency_overrides[get_quiz_generator] = lambda: FailingQuizGenerator()

    response = await client.post(
        "/api/v1/quizzes/generate",
        json={"document_id": str(document_id), "num_questions": 5},
    )

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_get_quiz_and_quiz_list_never_return_answer_keys(quiz_client) -> None:
    client, _, document_id, _, _, _, _ = quiz_client
    quiz = await create_quiz(client, document_id)

    detail = await client.get(f"/api/v1/quizzes/{quiz['id']}")
    listing = await client.get("/api/v1/quizzes/")

    assert detail.status_code == 200
    assert listing.status_code == 200
    for question in detail.json()["questions"]:
        assert "correct_answer" not in question
        assert "explanation" not in question
        assert "source_chunk_index" not in question
    assert listing.json()[0]["latest_score"] is None


@pytest.mark.asyncio
async def test_submit_scores_correct_wrong_and_unanswered_answers(quiz_client) -> None:
    client, _, document_id, _, _, _, _ = quiz_client
    quiz = await create_quiz(client, document_id)
    questions = quiz["questions"]

    response = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/submit",
        json={
            "answers": [
                {
                    "question_id": questions[0]["id"],
                    "selected_index": 0,
                    "correct_answer": 3,
                    "is_correct": False,
                },
                {"question_id": questions[1]["id"], "selected_index": 1},
            ],
            "score": 5,
        },
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["score"] == 1
    assert result["total"] == 5
    assert result["results"][0]["is_correct"] is True
    assert result["results"][0]["correct_answer"] == 0
    assert result["results"][1]["is_correct"] is False
    assert result["results"][1]["selected_index"] == 1
    assert result["results"][2]["selected_index"] is None
    assert result["results"][2]["is_correct"] is False
    assert result["results"][0]["source_document_title"] == "Biology notes.pdf"
    assert result["results"][0]["source_page_number"] == 1


@pytest.mark.asyncio
async def test_submit_rejects_invalid_selected_index(quiz_client) -> None:
    client, _, document_id, _, _, _, _ = quiz_client
    quiz = await create_quiz(client, document_id)

    response = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/submit",
        json={"answers": [{"question_id": quiz["questions"][0]["id"], "selected_index": 4}]},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_rejects_question_id_not_in_quiz(quiz_client) -> None:
    client, _, document_id, _, _, _, _ = quiz_client
    quiz = await create_quiz(client, document_id)

    response = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/submit",
        json={"answers": [{"question_id": str(uuid4()), "selected_index": 0}]},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_rejects_duplicate_question_ids(quiz_client) -> None:
    client, _, document_id, _, _, _, _ = quiz_client
    quiz = await create_quiz(client, document_id)
    first_question_id = quiz["questions"][0]["id"]

    response = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/submit",
        json={
            "answers": [
                {"question_id": first_question_id, "selected_index": 0},
                {"question_id": first_question_id, "selected_index": 1},
            ]
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_hides_foreign_quiz(quiz_client) -> None:
    client, _, document_id, foreign_document_id, _, _, _ = quiz_client
    quiz = await create_quiz(client, document_id)
    session_dependency = app.dependency_overrides[get_db_session]
    session_generator = session_dependency()
    session = await anext(session_generator)
    try:
        from sqlalchemy import select, update

        from app.models.quiz import Quiz

        foreign_user_id = await session.scalar(
            select(Document.user_id).where(Document.id == foreign_document_id)
        )
        assert foreign_user_id is not None
        await session.execute(
            update(Quiz).where(Quiz.id == UUID(quiz["id"])).values(user_id=foreign_user_id)
        )
        await session.commit()
    finally:
        await session_generator.aclose()

    detail = await client.get(f"/api/v1/quizzes/{quiz['id']}")
    response = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/submit",
        json={"answers": []},
    )

    assert detail.status_code == 404
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generation_read_then_write_persists_quiz_and_attempt(quiz_client) -> None:
    client, _, document_id, _, _, _, _ = quiz_client
    quiz = await create_quiz(client, document_id)
    response = await client.post(
        f"/api/v1/quizzes/{quiz['id']}/submit",
        json={"answers": []},
    )

    assert response.status_code == 200
    assert response.json()["score"] == 0
    listing = await client.get("/api/v1/quizzes/")
    assert listing.json()[0]["latest_score"] == 0

def test_gemini_response_schema_has_no_unsupported_keywords() -> None:
    # Gemini trả 400 nếu schema chứa additionalProperties
    schema_text = json.dumps(GeminiQuizSchema.model_json_schema())
    assert "additionalProperties" not in schema_text


def test_gemini_schema_matches_strict_schema_fields() -> None:
    # Hai schema phải luôn có cùng các trường, tránh lệch khi sửa một bên
    assert set(GeminiQuestionSchema.model_fields) == set(GeneratedQuestion.model_fields)
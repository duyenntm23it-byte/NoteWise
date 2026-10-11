from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import DocumentRateLimiter
from app.core.security import create_access_token
from app.db.session import Base, get_db
from app.main import app
from app.models.document import Document, DocumentChunk
from app.models.quiz import QuizAnswer, QuizAttempt
from app.models.user import User
from app.services.documents import process_next_job


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


def _ready_document(
    client: TestClient,
) -> tuple[dict[str, str], UUID, UUID, UUID]:
    user_id = uuid4()
    document_id = uuid4()
    chunk_id = uuid4()
    with app.state.testing_session_factory() as db:
        db.add(
            User(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="unused",
            )
        )
        db.add(
            Document(
                id=document_id,
                user_id=user_id,
                filename="lecture.pdf",
                storage_key=f"{document_id}.pdf",
                media_type="application/pdf",
                status="READY",
            )
        )
        db.add(
            DocumentChunk(
                id=chunk_id,
                user_id=user_id,
                document_id=document_id,
                chunk_index=0,
                content="A test document with grounded quiz material.",
                page_number=7,
                section="Testing",
                embedding=None,
            )
        )
        db.commit()
    return (
        {"Authorization": f"Bearer {create_access_token(user_id)}"},
        user_id,
        document_id,
        chunk_id,
    )


def _generated_questions(chunk_id: UUID) -> list[dict[str, object]]:
    citation = str(chunk_id)
    return [
        {
            "position": 1,
            "question": "Which option is correct?",
            "question_type": "multiple_choice",
            "options": ["A", "B", "C"],
            "answer_key": {"answer": "B"},
            "explanation": "The cited material identifies B.",
            "citation_chunk_id": citation,
        },
        {
            "position": 2,
            "question": "Is the statement true?",
            "question_type": "true_false",
            "options": ["True", "False"],
            "answer_key": {"answer": "TRUE"},
            "explanation": "The cited material supports the statement.",
            "citation_chunk_id": citation,
        },
        {
            "position": 3,
            "question": "Complete the key term.",
            "question_type": "fill_blank",
            "options": [],
            "answer_key": {"answers": ["Café"]},
            "explanation": "This is the term used in the cited material.",
            "citation_chunk_id": citation,
        },
        {
            "position": 4,
            "question": "Choose the second correct item.",
            "question_type": "multiple_choice",
            "options": ["A", "B"],
            "answer_key": {"answer": "A"},
            "explanation": "The excerpt supports A.",
            "citation_chunk_id": citation,
        },
        {
            "position": 5,
            "question": "Is this statement true?",
            "question_type": "true_false",
            "options": ["True", "False"],
            "answer_key": {"answer": "false"},
            "explanation": "The excerpt indicates this is false.",
            "citation_chunk_id": citation,
        },
    ]


def test_quiz_routes_match_approved_openapi_contract() -> None:
    paths = app.openapi()["paths"]
    generation = paths["/api/v1/documents/{document_id}/quizzes"]["post"]
    read_quiz = paths["/api/v1/quizzes/{quiz_id}"]["get"]
    start_attempt = paths["/api/v1/quizzes/{quiz_id}/attempts"]["post"]
    read_attempt = paths["/api/v1/quiz-attempts/{attempt_id}"]["get"]
    submit = paths["/api/v1/quiz-attempts/{attempt_id}/submit"]["post"]

    assert generation["operationId"] == "createQuiz"
    assert read_quiz["operationId"] == "getQuiz"
    assert start_attempt["operationId"] == "startQuizAttempt"
    assert read_attempt["operationId"] == "getQuizAttempt"
    assert submit["operationId"] == "submitQuizAttempt"
    assert generation["security"] == [{"bearerAuth": []}]
    assert "Idempotency-Key" in {
        parameter["name"] for parameter in generation["parameters"]
    }
    assert "Idempotency-Key" in {
        parameter["name"] for parameter in submit["parameters"]
    }
    assert "/api/v1/quizzes/generate" not in paths
    assert "/api/v1/quizzes/{quiz_id}/submit" not in paths
    create_schema = generation["requestBody"]["content"]["application/json"]["schema"]
    assert create_schema["$ref"].endswith("/QuizCreateRequest")
    create_schema = app.openapi()["components"]["schemas"]["QuizCreateRequest"]
    assert set(create_schema["required"]) == {
        "question_count",
        "question_types",
        "difficulty",
    }
    assert create_schema["properties"]["question_count"]["minimum"] == 5
    assert create_schema["properties"]["question_count"]["maximum"] == 20
    assert create_schema["properties"]["question_types"]["uniqueItems"] is True
    result_schema = paths["/api/v1/quiz-attempts/{attempt_id}/submit"]["post"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert result_schema["$ref"].endswith("/QuizResult")


def test_quiz_generation_attempt_scoring_and_replay(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id, chunk_id = _ready_document(client)

    class FakeProvider:
        def generate_json(self, _system_prompt: str, _user_prompt: str):
            if "Independently validate" in _system_prompt:
                return {"supported": True}
            return {
                "title": "Grounded review",
                "questions": _generated_questions(chunk_id),
            }

    monkeypatch.setattr("app.services.ai.provider", FakeProvider())
    response = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers={**headers, "Idempotency-Key": "quiz-request-0001"},
        json={
            "question_count": 5,
            "question_types": ["multiple_choice", "true_false", "fill_blank"],
            "difficulty": "medium",
            "topic": "Testing",
        },
    )

    assert response.status_code == 202
    accepted = response.json()
    assert accepted["status"] == "QUEUED"
    assert accepted["job_id"]
    replayed_generation = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers={**headers, "Idempotency-Key": "quiz-request-0001"},
        json={
            "question_count": 5,
            "question_types": ["multiple_choice", "true_false", "fill_blank"],
            "difficulty": "medium",
            "topic": "Testing",
        },
    )
    assert replayed_generation.status_code == 202
    assert replayed_generation.json() == accepted
    changed_generation = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers={**headers, "Idempotency-Key": "quiz-request-0001"},
        json={
            "question_count": 6,
            "question_types": ["multiple_choice", "true_false", "fill_blank"],
            "difficulty": "medium",
            "topic": "Testing",
        },
    )
    assert changed_generation.status_code == 409
    assert changed_generation.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

    with app.state.testing_session_factory() as db:
        assert process_next_job(db) is True

    quiz_id = accepted["quiz_id"]
    quiz_response = client.get(f"/api/v1/quizzes/{quiz_id}", headers=headers)
    assert quiz_response.status_code == 200
    quiz = quiz_response.json()
    assert quiz["status"] == "READY"
    assert len(quiz["questions"]) == 5
    assert all("answer_key" not in question for question in quiz["questions"])
    assert quiz["questions"][0]["citation"]["page_number"] == 7

    attempt_response = client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        headers=headers,
    )
    assert attempt_response.status_code == 201
    attempt = attempt_response.json()
    questions = attempt["questions"]
    assert all("answer_key" not in question for question in questions)

    submission = {
        "answers": [
            {"question_id": questions[0]["id"], "answer": "B"},
            {"question_id": questions[1]["id"], "answer": "false"},
            {"question_id": questions[2]["id"], "answer": " cafe\u0301 "},
            {"question_id": questions[3]["id"], "answer": "A"},
        ]
    }
    submitted = client.post(
        f"/api/v1/quiz-attempts/{attempt['id']}/submit",
        headers={**headers, "Idempotency-Key": "attempt-submit-0001"},
        json=submission,
    )
    assert submitted.status_code == 200
    result = submitted.json()
    assert result["score"] == 60.0
    assert result["correct_count"] == 3
    assert result["answered_count"] == 4
    assert result["skipped_count"] == 1
    assert len(result["feedback"]) == 5
    assert result["feedback"][2]["is_correct"] is True
    assert result["feedback"][2]["explanation"]
    assert result["feedback"][2]["citation"]["chunk_id"] == str(chunk_id)

    replay = client.post(
        f"/api/v1/quiz-attempts/{attempt['id']}/submit",
        headers={**headers, "Idempotency-Key": "attempt-submit-0001"},
        json=submission,
    )
    assert replay.status_code == 200
    assert replay.json() == result

    conflict = client.post(
        f"/api/v1/quiz-attempts/{attempt['id']}/submit",
        headers=headers,
        json={"answers": []},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "ALREADY_SUBMITTED"
    reused_key_conflict = client.post(
        f"/api/v1/quiz-attempts/{attempt['id']}/submit",
        headers={**headers, "Idempotency-Key": "attempt-submit-0001"},
        json={"answers": []},
    )
    assert reused_key_conflict.status_code == 409
    assert reused_key_conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

    restored = client.get(
        f"/api/v1/quiz-attempts/{attempt['id']}",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "SUBMITTED"
    assert restored.json()["result"] == result
    with app.state.testing_session_factory() as db:
        assert db.scalar(
            select(func.count()).select_from(QuizAttempt).where(
                QuizAttempt.id == UUID(attempt["id"]),
                QuizAttempt.status == "SUBMITTED",
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(QuizAnswer).where(
                QuizAnswer.attempt_id == UUID(attempt["id"]),
            )
        ) == 5
    history = client.get("/api/v1/learning-history", headers=headers).json()
    assert history["total"] == 1
    assert history["items"][0]["event_type"] == "QUIZ_SUBMITTED"
    assert history["items"][0]["details"]["attempt_id"] == attempt["id"]


def test_quiz_generation_rejects_unowned_citations(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id, _ = _ready_document(client)

    class InvalidProvider:
        def generate_json(self, _system_prompt: str, _user_prompt: str):
            if "Independently validate" in _system_prompt:
                return {"supported": False}
            return {
                "title": "Ungrounded quiz",
                "questions": _generated_questions(uuid4()),
            }

    monkeypatch.setattr("app.services.ai.provider", InvalidProvider())
    accepted = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers=headers,
        json={
            "question_count": 5,
            "question_types": ["multiple_choice", "true_false", "fill_blank"],
            "difficulty": "medium",
        },
    )
    assert accepted.status_code == 202
    with app.state.testing_session_factory() as db:
        assert process_next_job(db) is True

    quiz = client.get(
        f"/api/v1/quizzes/{accepted.json()['quiz_id']}",
        headers=headers,
    ).json()
    assert quiz["status"] == "FAILED"
    assert quiz["failure_code"] == "AI_VALIDATION_FAILED"
    assert quiz["questions"] == []


def test_quiz_and_attempt_are_owner_scoped(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id, chunk_id = _ready_document(client)

    class FakeProvider:
        def generate_json(self, system_prompt: str, _user_prompt: str):
            if "Independently validate" in system_prompt:
                return {"supported": True}
            return {
                "title": "Grounded review",
                "questions": _generated_questions(chunk_id),
            }

    monkeypatch.setattr("app.services.ai.provider", FakeProvider())
    accepted = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers=headers,
        json={
            "question_count": 5,
            "question_types": ["multiple_choice", "true_false", "fill_blank"],
            "difficulty": "easy",
        },
    )
    with app.state.testing_session_factory() as db:
        assert process_next_job(db) is True
    quiz_id = accepted.json()["quiz_id"]
    attempt = client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        headers=headers,
    ).json()
    other_headers, _, _, _ = _ready_document(client)

    assert client.get(
        f"/api/v1/quizzes/{quiz_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/quiz-attempts/{attempt['id']}",
        headers=other_headers,
    ).status_code == 404


def test_quiz_request_rejects_out_of_contract_configuration(
    client: TestClient,
) -> None:
    headers, _, document_id, _ = _ready_document(client)
    below_minimum = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers=headers,
        json={
            "question_count": 4,
            "question_types": ["multiple_choice"],
            "difficulty": "easy",
        },
    )
    assert below_minimum.status_code == 422

    duplicate_types = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers=headers,
        json={
            "question_count": 5,
            "question_types": ["multiple_choice", "multiple_choice"],
            "difficulty": "easy",
        },
    )
    assert duplicate_types.status_code == 422


def test_quiz_generation_rejects_ai_validator_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _, document_id, chunk_id = _ready_document(client)

    class UnsupportedProvider:
        def generate_json(self, system_prompt: str, _user_prompt: str):
            if "Independently validate" in system_prompt:
                return {"supported": False}
            return {
                "title": "Unsupported quiz",
                "questions": _generated_questions(chunk_id),
            }

    monkeypatch.setattr("app.services.ai.provider", UnsupportedProvider())
    accepted = client.post(
        f"/api/v1/documents/{document_id}/quizzes",
        headers=headers,
        json={
            "question_count": 5,
            "question_types": ["multiple_choice", "true_false", "fill_blank"],
            "difficulty": "easy",
        },
    )
    with app.state.testing_session_factory() as db:
        assert process_next_job(db) is True
    quiz = client.get(
        f"/api/v1/quizzes/{accepted.json()['quiz_id']}",
        headers=headers,
    ).json()
    assert quiz["status"] == "FAILED"
    assert quiz["failure_code"] == "AI_VALIDATION_FAILED"
    assert quiz["questions"] == []

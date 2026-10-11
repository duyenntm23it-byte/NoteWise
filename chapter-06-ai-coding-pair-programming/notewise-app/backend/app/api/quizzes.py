from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.learning import enforce_ai_rate_limit
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.quiz import Quiz
from app.models.user import User
from app.schemas.errors import ErrorResponse
from app.schemas.learning import (
    QuizAccepted,
    QuizAttemptResponse,
    QuizCreateRequest,
    QuizResponse,
    QuizResult,
    QuizSubmitRequest,
)
from app.services.quizzes import (
    create_quiz_job,
    get_quiz,
    get_quiz_attempt,
    public_questions,
    start_quiz_attempt,
    stored_result,
    submit_quiz_attempt,
)

router = APIRouter(tags=["Learning"])


@router.post(
    "/documents/{document_id}/quizzes",
    operation_id="createQuiz",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=QuizAccepted,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    dependencies=[Depends(enforce_ai_rate_limit)],
)
def request_quiz(
    document_id: UUID,
    payload: QuizCreateRequest,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAccepted:
    quiz, job = create_quiz_job(
        db,
        current_user.id,
        document_id,
        payload,
        idempotency_key,
    )
    return QuizAccepted(quiz_id=quiz.id, status=quiz.status, job_id=job.id)


def _public_quiz_response(db: Session, quiz: Quiz) -> QuizResponse:
    questions = public_questions(db, quiz) if quiz.status == "READY" else []
    return QuizResponse(
        id=quiz.id,
        title=quiz.title,
        status=quiz.status,
        questions=questions,
        failure_code=quiz.failure_code,
    )


@router.get(
    "/quizzes/{quiz_id}",
    operation_id="getQuiz",
    response_model=QuizResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def read_quiz(
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizResponse:
    return _public_quiz_response(db, get_quiz(db, current_user.id, quiz_id))


def _attempt_response(
    db: Session,
    attempt_id: UUID,
    user_id: UUID,
) -> QuizAttemptResponse:
    attempt, quiz = get_quiz_attempt(db, user_id, attempt_id)
    result = stored_result(db, attempt, quiz) if attempt.status == "SUBMITTED" else None
    return QuizAttemptResponse(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        status=attempt.status,
        questions=public_questions(db, quiz),
        result=result,
    )


@router.post(
    "/quizzes/{quiz_id}/attempts",
    operation_id="startQuizAttempt",
    status_code=status.HTTP_201_CREATED,
    response_model=QuizAttemptResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def create_attempt(
    quiz_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptResponse:
    attempt = start_quiz_attempt(db, current_user.id, quiz_id)
    return _attempt_response(db, attempt.id, current_user.id)


@router.get(
    "/quiz-attempts/{attempt_id}",
    operation_id="getQuizAttempt",
    response_model=QuizAttemptResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def read_attempt(
    attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptResponse:
    return _attempt_response(db, attempt_id, current_user.id)


@router.post(
    "/quiz-attempts/{attempt_id}/submit",
    operation_id="submitQuizAttempt",
    response_model=QuizResult,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def submit_attempt(
    attempt_id: UUID,
    payload: QuizSubmitRequest,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizResult:
    return submit_quiz_attempt(
        db,
        current_user.id,
        attempt_id,
        [answer.model_dump(mode="json") for answer in payload.answers],
        idempotency_key,
    )

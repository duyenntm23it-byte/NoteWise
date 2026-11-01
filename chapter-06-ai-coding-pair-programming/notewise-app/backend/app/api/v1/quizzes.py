from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.db import get_db_session
from app.models.user import User
from app.schemas.quiz import (
    QuizAttemptRead,
    QuizGenerateRequest,
    QuizRead,
    QuizSubmitRequest,
    QuizSummary,
)
from app.services.quizzes import (
    InvalidQuizOutput,
    QuizDocumentEmpty,
    QuizDocumentNotReady,
    QuizGenerator,
    QuizQuestionNotInQuiz,
    generate_document_quiz,
    get_quiz_generator,
    get_user_quiz,
    list_user_quizzes,
    submit_quiz_answers,
)
from app.services.rag import AnswerProviderError, AnswerServiceUnavailable

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post(
    "/generate",
    response_model=QuizRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_quiz(
    payload: QuizGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    generator: Annotated[QuizGenerator, Depends(get_quiz_generator)],
) -> QuizRead:
    try:
        return await generate_document_quiz(
            session,
            user_id=current_user.id,
            document_id=payload.document_id,
            num_questions=payload.num_questions,
            generator=generator,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except QuizDocumentNotReady as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except QuizDocumentEmpty as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except AnswerServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (AnswerProviderError, InvalidQuizOutput) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/", response_model=list[QuizSummary])
async def list_quizzes(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[QuizSummary]:
    return await list_user_quizzes(session, current_user.id)


@router.get("/{quiz_id}", response_model=QuizRead)
async def read_quiz(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuizRead:
    quiz = await get_user_quiz(session, user_id=current_user.id, quiz_id=quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    return quiz


@router.post("/{quiz_id}/submit", response_model=QuizAttemptRead)
async def submit_quiz(
    quiz_id: UUID,
    payload: QuizSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuizAttemptRead:
    try:
        return await submit_quiz_answers(
            session,
            user_id=current_user.id,
            quiz_id=quiz_id,
            answers=payload.answers,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except QuizQuestionNotInQuiz as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

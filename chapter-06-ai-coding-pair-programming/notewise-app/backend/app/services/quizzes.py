import hashlib
import json
import unicodedata
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models.document import Document, DocumentChunk, ProcessingJob
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion
from app.schemas.learning import QuizCreateRequest, QuizResult, PublicQuizQuestion
from app.services.ai import AIProviderError, generate_quiz, validate_quiz_grounding
from app.services.analytics import record_learning_event, refresh_analytics_snapshots

QUIZ_GENERATE_JOB = "QUIZ_GENERATE"
MAX_QUIZ_CONTEXT_CHUNKS = 40
MAX_QUIZ_CONTEXT_CHARACTERS = 100_000


class QuizValidationError(ValueError):
    pass


def _request_hash(document_id: uuid.UUID, payload: QuizCreateRequest) -> str:
    request = {
        "document_id": str(document_id),
        **payload.model_dump(mode="json"),
    }
    encoded = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_quiz_job(
    db: Session,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: QuizCreateRequest,
    idempotency_key: str | None,
) -> tuple[Quiz, ProcessingJob]:
    request_hash = _request_hash(document_id, payload)
    if idempotency_key:
        existing_job = db.scalar(
            select(ProcessingJob).where(
                ProcessingJob.user_id == user_id,
                ProcessingJob.idempotency_key == idempotency_key,
            )
        )
        if existing_job is not None:
            if (
                existing_job.job_type != QUIZ_GENERATE_JOB
                or existing_job.request_hash != request_hash
                or existing_job.quiz_id is None
            ):
                raise ApiError(
                    409,
                    "IDEMPOTENCY_CONFLICT",
                    "The idempotency key was already used for a different request.",
                )
            quiz = db.scalar(
                select(Quiz).where(
                    Quiz.id == existing_job.quiz_id,
                    Quiz.user_id == user_id,
                )
            )
            if quiz is not None:
                return quiz, existing_job

    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    if document is None:
        raise ApiError(404, "NOT_FOUND", "Document not found.")
    if document.status != "READY":
        raise ApiError(
            409,
            "STATE_CONFLICT",
            "Only a ready document can generate a quiz.",
        )
    if not db.scalar(
        select(DocumentChunk.id)
        .where(
            DocumentChunk.user_id == user_id,
            DocumentChunk.document_id == document_id,
        )
        .limit(1)
    ):
        raise ApiError(
            409,
            "STATE_CONFLICT",
            "The document has no usable learning content.",
        )

    quiz = Quiz(
        id=uuid.uuid4(),
        user_id=user_id,
        document_id=document_id,
        title=f"Quiz: {document.filename}",
        status="QUEUED",
        question_count=payload.question_count,
        question_types=payload.question_types,
        difficulty=payload.difficulty,
        topic=payload.topic,
    )
    db.add(quiz)
    db.flush()
    job = ProcessingJob(
        user_id=user_id,
        document_id=document_id,
        quiz_id=quiz.id,
        job_type=QUIZ_GENERATE_JOB,
        status="QUEUED",
        max_attempts=settings.document_job_max_attempts,
        idempotency_key=idempotency_key,
        request_hash=request_hash if idempotency_key else None,
    )
    db.add(job)
    try:
        db.commit()
        db.refresh(quiz)
        db.refresh(job)
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "The idempotency key was already used for a different request.",
        ) from exc
    return quiz, job


def _source_context(
    db: Session,
    quiz: Quiz,
) -> list[dict[str, Any]]:
    chunks = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.user_id == quiz.user_id,
            DocumentChunk.document_id == quiz.document_id,
        )
        .order_by(DocumentChunk.chunk_index)
    ).all()
    if not chunks:
        raise AIProviderError("AI_VALIDATION_FAILED")
    stride = max(1, (len(chunks) + MAX_QUIZ_CONTEXT_CHUNKS - 1) // MAX_QUIZ_CONTEXT_CHUNKS)
    selected = chunks[::stride][:MAX_QUIZ_CONTEXT_CHUNKS]
    context: list[dict[str, Any]] = []
    characters = 0
    for chunk in selected:
        excerpt = chunk.content[: min(4000, MAX_QUIZ_CONTEXT_CHARACTERS - characters)]
        if not excerpt:
            break
        context.append(
            {
                "chunk_id": chunk.id,
                "content": excerpt,
                "page_number": chunk.page_number,
                "section": chunk.section,
            }
        )
        characters += len(excerpt)
        if characters >= MAX_QUIZ_CONTEXT_CHARACTERS:
            break
    return context


def _normalize_answer(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


def _validate_generated_question(
    raw: Any,
    position: int,
    quiz: Quiz,
    context_by_id: dict[str, dict[str, Any]],
) -> QuizQuestion:
    if not isinstance(raw, dict):
        raise QuizValidationError("question is not an object")
    question = raw.get("question")
    question_type = raw.get("question_type")
    options = raw.get("options")
    answer_key = raw.get("answer_key")
    explanation = raw.get("explanation")
    citation_chunk_id = raw.get("citation_chunk_id")
    if (
        not isinstance(question, str)
        or not question.strip()
        or len(question) > 2000
        or raw.get("position") != position
        or question_type not in quiz.question_types
        or not isinstance(options, list)
        or any(not isinstance(option, str) or not option.strip() for option in options)
        or not isinstance(answer_key, dict)
        or not isinstance(explanation, str)
        or not explanation.strip()
        or len(explanation) > 4000
    ):
        raise QuizValidationError("question fields are invalid")
    citation_id = str(citation_chunk_id)
    context = context_by_id.get(citation_id)
    if context is None:
        raise QuizValidationError("question citation is outside the selected document")
    if question_type == "multiple_choice":
        normalized_options = [_normalize_answer(option) for option in options]
        answer = answer_key.get("answer")
        if (
            not 2 <= len(options) <= 6
            or len(normalized_options) != len(set(normalized_options))
            or not isinstance(answer, str)
            or answer not in options
        ):
            raise QuizValidationError("multiple-choice question is invalid")
    elif question_type == "true_false":
        answer = answer_key.get("answer")
        if (
            options != ["True", "False"]
            or not (
                isinstance(answer, bool)
                or (
                    isinstance(answer, str)
                    and answer.casefold() in {"true", "false"}
                )
            )
        ):
            raise QuizValidationError("true/false question is invalid")
        is_true = answer if isinstance(answer, bool) else answer.casefold() == "true"
        answer_key = {"answer": "true" if is_true else "false"}
    else:
        answers = answer_key.get("answers")
        if (
            options
            or not isinstance(answers, list)
            or not answers
            or any(not isinstance(answer, str) or not answer.strip() for answer in answers)
        ):
            raise QuizValidationError("fill-in-the-blank question is invalid")
        answer_key = {
            "answers": list(dict.fromkeys(answer.strip() for answer in answers))
        }

    return QuizQuestion(
        id=uuid.uuid4(),
        user_id=quiz.user_id,
        quiz_id=quiz.id,
        document_id=quiz.document_id,
        position=position,
        question=question.strip(),
        question_type=question_type,
        options=[option.strip() for option in options],
        answer_key=answer_key,
        explanation=explanation.strip(),
        citation_chunk_id=context["chunk_id"],
    )


def process_quiz_job(db: Session, job: ProcessingJob) -> None:
    quiz = db.get(Quiz, job.quiz_id)
    document = db.get(Document, job.document_id)
    if (
        quiz is None
        or document is None
        or document.user_id != job.user_id
        or document.status != "READY"
        or quiz.status == "DELETED"
    ):
        if quiz is not None:
            quiz.status = "DELETED" if document is None else "FAILED"
            quiz.failure_code = None if document is None else "STATE_CONFLICT"
        job.status = "CANCELLED" if document is None else "FAILED"
        job.last_error_code = None if document is None else "STATE_CONFLICT"
        job.lease_expires_at = None
        db.commit()
        return

    quiz.status = "PROCESSING"
    db.commit()
    context = _source_context(db, quiz)
    context_by_id = {str(chunk["chunk_id"]): chunk for chunk in context}
    try:
        generated = generate_quiz(
            title=quiz.title,
            question_count=quiz.question_count,
            question_types=quiz.question_types,
            difficulty=quiz.difficulty,
            topic=quiz.topic,
            chunks=context,
        )
        title = generated.get("title")
        raw_questions = generated.get("questions")
        if (
            not isinstance(title, str)
            or not title.strip()
            or len(title) > 255
            or not isinstance(raw_questions, list)
            or len(raw_questions) != quiz.question_count
        ):
            raise QuizValidationError("generated quiz has an invalid title or count")
        questions = [
            _validate_generated_question(raw, position, quiz, context_by_id)
            for position, raw in enumerate(raw_questions, start=1)
        ]
        validate_quiz_grounding(generated, context)
    except QuizValidationError:
        db.rollback()
        quiz = db.get(Quiz, job.quiz_id)
        job = db.get(ProcessingJob, job.id)
        if quiz is not None:
            quiz.status = "FAILED"
            quiz.failure_code = "AI_VALIDATION_FAILED"
        if job is not None:
            job.status = "FAILED"
            job.last_error_code = "AI_VALIDATION_FAILED"
            job.lease_expires_at = None
        db.commit()
        return
    except AIProviderError as exc:
        db.rollback()
        quiz = db.get(Quiz, job.quiz_id)
        job = db.get(ProcessingJob, job.id)
        if quiz is not None:
            quiz.status = "FAILED"
            quiz.failure_code = exc.code
        if job is not None:
            job.status = "FAILED"
            job.last_error_code = exc.code
            job.lease_expires_at = None
        db.commit()
        return

    quiz = db.get(Quiz, job.quiz_id)
    job = db.get(ProcessingJob, job.id)
    document = db.get(Document, job.document_id) if job is not None else None
    if quiz is None or job is None or document is None or document.status != "READY":
        if quiz is not None:
            quiz.status = "DELETED" if document is None else "FAILED"
            quiz.failure_code = None if document is None else "STATE_CONFLICT"
        if job is not None:
            job.status = "CANCELLED" if document is None else "FAILED"
            job.last_error_code = None if document is None else "STATE_CONFLICT"
            job.lease_expires_at = None
        db.commit()
        return
    quiz.title = title.strip()
    quiz.status = "READY"
    quiz.failure_code = None
    db.add_all(questions)
    job.status = "SUCCEEDED"
    job.last_error_code = None
    job.lease_expires_at = None
    db.commit()


def public_questions(
    db: Session,
    quiz: Quiz,
) -> list[PublicQuizQuestion]:
    questions = db.scalars(
        select(QuizQuestion)
        .where(
            QuizQuestion.quiz_id == quiz.id,
            QuizQuestion.user_id == quiz.user_id,
        )
        .order_by(QuizQuestion.position)
    ).all()
    chunks = {
        chunk.id: chunk
        for chunk in db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == quiz.document_id,
                DocumentChunk.user_id == quiz.user_id,
            )
        ).all()
    }
    result = []
    for question in questions:
        chunk = chunks.get(question.citation_chunk_id)
        if chunk is None:
            raise ApiError(
                409,
                "STATE_CONFLICT",
                "Quiz source content is no longer available.",
            )
        result.append(
            PublicQuizQuestion(
                id=question.id,
                position=question.position,
                question=question.question,
                question_type=question.question_type,
                options=question.options,
                citation={
                    "chunk_id": chunk.id,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "excerpt": chunk.content[:1200],
                },
            )
        )
    return result


def get_quiz(db: Session, user_id: uuid.UUID, quiz_id: uuid.UUID) -> Quiz:
    quiz = db.scalar(
        select(Quiz).where(
            Quiz.id == quiz_id,
            Quiz.user_id == user_id,
            Quiz.status != "DELETED",
        )
    )
    if quiz is None:
        raise ApiError(404, "NOT_FOUND", "Quiz not found.")
    return quiz


def start_quiz_attempt(
    db: Session,
    user_id: uuid.UUID,
    quiz_id: uuid.UUID,
) -> QuizAttempt:
    quiz = get_quiz(db, user_id, quiz_id)
    if quiz.status != "READY":
        raise ApiError(409, "STATE_CONFLICT", "This quiz is not ready to start.")
    attempt = QuizAttempt(
        id=uuid.uuid4(),
        user_id=user_id,
        quiz_id=quiz.id,
        status="IN_PROGRESS",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def stored_result(
    db: Session,
    attempt: QuizAttempt,
    quiz: Quiz,
) -> QuizResult:
    questions = db.scalars(
        select(QuizQuestion)
        .where(
            QuizQuestion.quiz_id == quiz.id,
            QuizQuestion.user_id == attempt.user_id,
        )
        .order_by(QuizQuestion.position)
    ).all()
    answers = {
        answer.question_id: answer
        for answer in db.scalars(
            select(QuizAnswer).where(
                QuizAnswer.attempt_id == attempt.id,
                QuizAnswer.user_id == attempt.user_id,
            )
        ).all()
    }
    chunks = {
        chunk.id: chunk
        for chunk in db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == quiz.document_id,
                DocumentChunk.user_id == quiz.user_id,
            )
        ).all()
    }
    feedback = []
    for question in questions:
        answer = answers.get(question.id)
        chunk = chunks.get(question.citation_chunk_id)
        if chunk is None:
            raise ApiError(409, "STATE_CONFLICT", "Quiz source content is unavailable.")
        feedback.append(
            {
                "question_id": question.id,
                "is_correct": bool(answer and answer.is_correct),
                "explanation": question.explanation,
                "citation": {
                    "chunk_id": chunk.id,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "excerpt": chunk.content[:1200],
                },
                "submitted_answer": None if answer is None else answer.submitted_answer,
                "correct_answer": question.answer_key.get(
                    "answers",
                    question.answer_key.get("answer"),
                ),
            }
        )
    return QuizResult(
        attempt_id=attempt.id,
        score=float(attempt.score or 0),
        correct_count=attempt.correct_count or 0,
        answered_count=attempt.answered_count or 0,
        skipped_count=attempt.skipped_count or 0,
        submitted_at=attempt.submitted_at,
        feedback=feedback,
    )


def get_quiz_attempt(
    db: Session,
    user_id: uuid.UUID,
    attempt_id: uuid.UUID,
) -> tuple[QuizAttempt, Quiz]:
    attempt = db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.user_id == user_id,
        )
    )
    if attempt is None:
        raise ApiError(404, "NOT_FOUND", "Quiz attempt not found.")
    quiz = get_quiz(db, user_id, attempt.quiz_id)
    return attempt, quiz


def _answer_is_correct(question: QuizQuestion, submitted: str | int) -> bool:
    if not isinstance(submitted, str):
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Answers must be strings for the selected question type.",
        )
    if question.question_type in {"multiple_choice", "true_false"}:
        expected = question.answer_key["answer"]
        return _normalize_answer(submitted) == _normalize_answer(str(expected))
    accepted = question.answer_key["answers"]
    return any(
        _normalize_answer(submitted) == _normalize_answer(expected)
        for expected in accepted
    )


def submit_quiz_attempt(
    db: Session,
    user_id: uuid.UUID,
    attempt_id: uuid.UUID,
    answers_payload: list[dict[str, Any]],
    idempotency_key: str | None = None,
) -> QuizResult:
    attempt = db.scalar(
        select(QuizAttempt)
        .where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.user_id == user_id,
        )
        .with_for_update()
    )
    if attempt is None:
        raise ApiError(404, "NOT_FOUND", "Quiz attempt not found.")
    quiz = get_quiz(db, user_id, attempt.quiz_id)
    normalized_payload = sorted(
        answers_payload,
        key=lambda item: str(item.get("question_id", "")),
    )
    submission_hash = hashlib.sha256(
        json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if attempt.status == "SUBMITTED":
        if attempt.submission_hash == submission_hash:
            return stored_result(db, attempt, quiz)
        if (
            idempotency_key is not None
            and idempotency_key == attempt.submission_idempotency_key
        ):
            raise ApiError(
                409,
                "IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used for a different request.",
            )
        raise ApiError(
            409,
            "ALREADY_SUBMITTED",
            "This quiz attempt has already been submitted.",
        )
    if attempt.status != "IN_PROGRESS" or quiz.status != "READY":
        raise ApiError(409, "STATE_CONFLICT", "This quiz attempt cannot be submitted.")

    questions = db.scalars(
        select(QuizQuestion)
        .where(
            QuizQuestion.quiz_id == quiz.id,
            QuizQuestion.user_id == user_id,
        )
        .order_by(QuizQuestion.position)
    ).all()
    if not questions:
        raise ApiError(409, "STATE_CONFLICT", "This quiz has no questions.")
    questions_by_id = {question.id: question for question in questions}
    answers_by_id: dict[uuid.UUID, str | int] = {}
    for item in answers_payload:
        try:
            question_id = uuid.UUID(str(item.get("question_id")))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                "Each submitted question ID must be a valid UUID.",
            ) from exc
        if question_id not in questions_by_id or question_id in answers_by_id:
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                "Each submitted question must belong to this quiz and appear once.",
            )
        submitted = item.get("answer")
        answers_by_id[question_id] = submitted

    correct_count = 0
    answer_rows = []
    answered_at = datetime.now(timezone.utc)
    for question in questions:
        submitted = answers_by_id.get(question.id)
        is_answered = question.id in answers_by_id
        is_correct = (
            _answer_is_correct(question, submitted)
            if is_answered and submitted is not None
            else False
        )
        correct_count += int(is_correct)
        answer_rows.append(
            QuizAnswer(
                id=uuid.uuid4(),
                user_id=user_id,
                attempt_id=attempt.id,
                quiz_id=quiz.id,
                question_id=question.id,
                submitted_answer=submitted,
                is_correct=is_correct,
                answered_at=answered_at if is_answered else None,
            )
        )
    answered_count = len(answers_by_id)
    skipped_count = len(questions) - answered_count
    score = (
        (Decimal(correct_count) * Decimal(100) / Decimal(len(questions))).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )
    attempt.status = "SUBMITTED"
    attempt.score = score
    attempt.correct_count = correct_count
    attempt.answered_count = answered_count
    attempt.skipped_count = skipped_count
    attempt.submission_hash = submission_hash
    attempt.submission_idempotency_key = idempotency_key
    attempt.submitted_at = answered_at
    db.add_all(answer_rows)
    document = db.scalar(
        select(Document).where(
            Document.id == quiz.document_id,
            Document.user_id == user_id,
        )
    )
    record_learning_event(
        db,
        user_id,
        "QUIZ_SUBMITTED",
        document_id=quiz.document_id,
        document_title=document.filename if document is not None else None,
        details={
            "attempt_id": str(attempt.id),
            "quiz_id": str(quiz.id),
            "topic": quiz.topic,
            "score": float(score),
        },
    )
    refresh_analytics_snapshots(db, user_id)
    db.commit()
    db.refresh(attempt)
    return stored_result(db, attempt, quiz)

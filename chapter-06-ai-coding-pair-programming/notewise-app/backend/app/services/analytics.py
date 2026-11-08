from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion
from app.schemas.analytics import (
    AnalyticsSummary,
    DocumentAnalytics,
    WeakArea,
)


def _percentage(numerator: int | float, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator * 100


def _selected_answers(answers: Any) -> dict[str, int | None]:
    selected: dict[str, int | None] = {}
    if not isinstance(answers, list):
        return selected
    for answer in answers:
        if not isinstance(answer, dict):
            continue
        question_id = answer.get("question_id")
        selected_index = answer.get("selected_index")
        if not isinstance(question_id, str):
            continue
        if selected_index is not None and (
            not isinstance(selected_index, int) or isinstance(selected_index, bool)
        ):
            continue
        selected[question_id] = selected_index
    return selected


async def get_analytics_summary(
    session: AsyncSession,
    user_id: UUID,
) -> AnalyticsSummary:
    documents = list(
        (
            await session.scalars(
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(Document.created_at, Document.id)
            )
        ).all()
    )
    quizzes = list(
        (
            await session.scalars(
                select(Quiz).where(Quiz.user_id == user_id).order_by(Quiz.created_at, Quiz.id)
            )
        ).all()
    )
    quiz_by_id = {quiz.id: quiz for quiz in quizzes}
    quiz_ids = list(quiz_by_id)
    attempts = list(
        (
            await session.scalars(
                select(QuizAttempt)
                .where(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.quiz_id.in_(quiz_ids),
                )
                .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
            )
        ).all()
    )
    questions = list(
        (
            await session.scalars(
                select(QuizQuestion)
                .where(QuizQuestion.quiz_id.in_(quiz_ids))
                .order_by(QuizQuestion.position, QuizQuestion.id)
            )
        ).all()
    )

    questions_by_quiz: dict[UUID, list[QuizQuestion]] = defaultdict(list)
    for question in questions:
        questions_by_quiz[question.quiz_id].append(question)

    attempts_by_quiz: dict[UUID, list[QuizAttempt]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_quiz[attempt.quiz_id].append(attempt)

    total_correct = 0
    total_questions_answered = 0
    score_percentages: list[float] = []
    document_quiz_counts: dict[UUID, int] = defaultdict(int)
    document_attempt_count: dict[UUID, int] = defaultdict(int)
    document_score_percentages: dict[UUID, list[float]] = defaultdict(list)
    document_correct: dict[UUID, int] = defaultdict(int)
    document_question_count: dict[UUID, int] = defaultdict(int)

    latest_attempts: list[QuizAttempt] = []
    for quiz in quizzes:
        quiz_questions = questions_by_quiz[quiz.id]
        document_quiz_counts[quiz.document_id] += 1
        quiz_attempts = attempts_by_quiz[quiz.id]
        if quiz_attempts:
            latest_attempts.append(quiz_attempts[0])
        for attempt in quiz_attempts:
            score_percentages.append(attempt.score / quiz.total_questions * 100)
            document_score_percentages[quiz.document_id].append(
                attempt.score / quiz.total_questions * 100
            )
            document_attempt_count[quiz.document_id] += 1
            total_questions_answered += quiz.total_questions
            document_question_count[quiz.document_id] += quiz.total_questions
            selected = _selected_answers(attempt.answers)
            correct_count = sum(
                selected.get(str(question.id)) == question.correct_answer
                for question in quiz_questions
            )
            total_correct += correct_count
            document_correct[quiz.document_id] += correct_count

    document_by_id = {document.id: document for document in documents}
    weak_groups: dict[tuple[UUID, str, str | int | None], dict[str, Any]] = {}
    for attempt in latest_attempts:
        quiz = quiz_by_id[attempt.quiz_id]
        document = document_by_id.get(quiz.document_id)
        if document is None:
            continue
        selected = _selected_answers(attempt.answers)
        for question in questions_by_quiz[quiz.id]:
            key_value: str | int | None
            if question.source_page_number is not None:
                group_type = "page"
                key_value = question.source_page_number
                topic_label = f"Page {question.source_page_number}"
            elif question.source_chunk_index is not None:
                group_type = "chunk"
                key_value = question.source_chunk_index
                topic_label = f"Passage {question.source_chunk_index + 1}"
            else:
                group_type = "general"
                key_value = None
                topic_label = "General"
            group_key = (document.id, group_type, key_value)
            group = weak_groups.setdefault(
                group_key,
                {
                    "document": document,
                    "topic_label": topic_label,
                    "wrong_count": 0,
                    "total_count": 0,
                    "sample_questions": [],
                },
            )
            group["total_count"] += 1
            if selected.get(str(question.id)) != question.correct_answer:
                group["wrong_count"] += 1
                if len(group["sample_questions"]) < 3:
                    group["sample_questions"].append(question.question_text)

    weak_areas = [
        WeakArea(
            document_id=group["document"].id,
            document_title=group["document"].title,
            topic_label=group["topic_label"],
            wrong_count=group["wrong_count"],
            total_count=group["total_count"],
            sample_questions=group["sample_questions"],
        )
        for group in weak_groups.values()
        if group["wrong_count"] > 0
    ]
    weak_areas.sort(
        key=lambda area: (
            -area.wrong_count,
            area.document_title.casefold(),
            area.topic_label,
        )
    )

    document_stats = [
        DocumentAnalytics(
            document_id=document.id,
            document_title=document.title,
            quiz_count=document_quiz_counts[document.id],
            attempt_count=document_attempt_count[document.id],
            average_score_percent=(
                sum(document_score_percentages[document.id])
                / len(document_score_percentages[document.id])
                if document_score_percentages[document.id]
                else None
            ),
            accuracy_percent=_percentage(
                document_correct[document.id],
                document_question_count[document.id],
            ),
        )
        for document in documents
    ]
    return AnalyticsSummary(
        total_documents=len(documents),
        ready_documents=sum(document.status == "ready" for document in documents),
        total_quizzes=len(quizzes),
        total_attempts=len(attempts),
        average_score_percent=(
            sum(score_percentages) / len(score_percentages) if score_percentages else None
        ),
        overall_accuracy_percent=_percentage(total_correct, total_questions_answered),
        documents=document_stats,
        weak_areas=weak_areas[:10],
    )

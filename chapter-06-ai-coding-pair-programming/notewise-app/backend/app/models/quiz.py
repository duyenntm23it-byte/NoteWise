import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_quizzes_id_user"),
        UniqueConstraint(
            "id",
            "user_id",
            "document_id",
            name="uq_quizzes_id_user_document",
        ),
        ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["documents.id", "documents.user_id"],
            ondelete="CASCADE",
            name="fk_quizzes_document_owner",
        ),
        CheckConstraint(
            "status IN ('QUEUED', 'PROCESSING', 'READY', 'FAILED', 'DELETED')",
            name="ck_quizzes_status",
        ),
        CheckConstraint(
            "question_count BETWEEN 5 AND 20",
            name="ck_quizzes_question_count",
        ),
        CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')",
            name="ck_quizzes_difficulty",
        ),
        Index("ix_quizzes_user_document_created", "user_id", "document_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    question_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_quiz_questions_id_user"),
        UniqueConstraint(
            "id",
            "user_id",
            "quiz_id",
            name="uq_quiz_questions_id_user_quiz",
        ),
        ForeignKeyConstraint(
            ["quiz_id", "user_id", "document_id"],
            ["quizzes.id", "quizzes.user_id", "quizzes.document_id"],
            ondelete="CASCADE",
            name="fk_quiz_questions_quiz_owner",
        ),
        ForeignKeyConstraint(
            ["citation_chunk_id", "document_id", "user_id"],
            [
                "document_chunks.id",
                "document_chunks.document_id",
                "document_chunks.user_id",
            ],
            ondelete="CASCADE",
            name="fk_quiz_questions_citation_owner",
        ),
        UniqueConstraint("quiz_id", "position", name="uq_quiz_questions_position"),
        CheckConstraint("position > 0", name="ck_quiz_questions_position"),
        CheckConstraint(
            "question_type IN ('multiple_choice', 'true_false', 'fill_blank')",
            name="ck_quiz_questions_type",
        ),
        Index("ix_quiz_questions_quiz_user", "quiz_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    citation_chunk_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_quiz_attempts_id_user"),
        UniqueConstraint(
            "id",
            "user_id",
            "quiz_id",
            name="uq_quiz_attempts_id_user_quiz",
        ),
        ForeignKeyConstraint(
            ["quiz_id", "user_id"],
            ["quizzes.id", "quizzes.user_id"],
            ondelete="CASCADE",
            name="fk_quiz_attempts_quiz_owner",
        ),
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'SUBMITTED')",
            name="ck_quiz_attempts_status",
        ),
        Index("ix_quiz_attempts_user_quiz", "user_id", "quiz_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    correct_count: Mapped[int | None] = mapped_column(Integer)
    answered_count: Mapped[int | None] = mapped_column(Integer)
    skipped_count: Mapped[int | None] = mapped_column(Integer)
    submission_hash: Mapped[str | None] = mapped_column(String(64))
    submission_idempotency_key: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["attempt_id", "user_id", "quiz_id"],
            ["quiz_attempts.id", "quiz_attempts.user_id", "quiz_attempts.quiz_id"],
            ondelete="CASCADE",
            name="fk_quiz_answers_attempt_owner",
        ),
        ForeignKeyConstraint(
            ["question_id", "user_id", "quiz_id"],
            ["quiz_questions.id", "quiz_questions.user_id", "quiz_questions.quiz_id"],
            ondelete="CASCADE",
            name="fk_quiz_answers_question_owner",
        ),
        UniqueConstraint("attempt_id", "question_id", name="uq_quiz_answers_attempt_question"),
        Index("ix_quiz_answers_user_attempt", "user_id", "attempt_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    submitted_answer: Mapped[str | int | None] = mapped_column(JSON)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

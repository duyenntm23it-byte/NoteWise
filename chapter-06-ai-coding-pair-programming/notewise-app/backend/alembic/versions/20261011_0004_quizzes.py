"""Add AI quizzes and persisted attempts.

Revision ID: 20261011_0004
Revises: 20261010_0003
Create Date: 2026-10-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261011_0004"
down_revision: Union[str, None] = "20261010_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_document_chunks_id_document_user",
        "document_chunks",
        ["id", "document_id", "user_id"],
    )
    op.create_table(
        "quizzes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("question_types", postgresql.JSONB(), nullable=False),
        sa.Column("difficulty", sa.String(16), nullable=False),
        sa.Column("topic", sa.String(200)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'PROCESSING', 'READY', 'FAILED', 'DELETED')",
            name="ck_quizzes_status",
        ),
        sa.CheckConstraint(
            "question_count BETWEEN 5 AND 20",
            name="ck_quizzes_question_count",
        ),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')",
            name="ck_quizzes_difficulty",
        ),
        sa.UniqueConstraint("id", "user_id", name="uq_quizzes_id_user"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            "document_id",
            name="uq_quizzes_id_user_document",
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["documents.id", "documents.user_id"],
            ondelete="CASCADE",
            name="fk_quizzes_document_owner",
        ),
    )
    op.create_index(
        "ix_quizzes_user_document_created",
        "quizzes",
        ["user_id", "document_id", "created_at"],
    )

    op.create_table(
        "quiz_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(32), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=False),
        sa.Column("answer_key", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("citation_chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "question_type IN ('multiple_choice', 'true_false', 'fill_blank')",
            name="ck_quiz_questions_type",
        ),
        sa.CheckConstraint("position > 0", name="ck_quiz_questions_position"),
        sa.UniqueConstraint("id", "user_id", name="uq_quiz_questions_id_user"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            "quiz_id",
            name="uq_quiz_questions_id_user_quiz",
        ),
        sa.UniqueConstraint(
            "quiz_id",
            "position",
            name="uq_quiz_questions_position",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id", "user_id", "document_id"],
            ["quizzes.id", "quizzes.user_id", "quizzes.document_id"],
            ondelete="CASCADE",
            name="fk_quiz_questions_quiz_owner",
        ),
        sa.ForeignKeyConstraint(
            ["citation_chunk_id", "document_id", "user_id"],
            [
                "document_chunks.id",
                "document_chunks.document_id",
                "document_chunks.user_id",
            ],
            ondelete="CASCADE",
            name="fk_quiz_questions_citation_owner",
        ),
    )
    op.create_index(
        "ix_quiz_questions_quiz_user",
        "quiz_questions",
        ["quiz_id", "user_id"],
    )

    op.create_table(
        "quiz_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("correct_count", sa.Integer()),
        sa.Column("answered_count", sa.Integer()),
        sa.Column("skipped_count", sa.Integer()),
        sa.Column("submission_hash", sa.String(64)),
        sa.Column("submission_idempotency_key", sa.String(128)),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'SUBMITTED')",
            name="ck_quiz_attempts_status",
        ),
        sa.UniqueConstraint("id", "user_id", name="uq_quiz_attempts_id_user"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            "quiz_id",
            name="uq_quiz_attempts_id_user_quiz",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id", "user_id"],
            ["quizzes.id", "quizzes.user_id"],
            ondelete="CASCADE",
            name="fk_quiz_attempts_quiz_owner",
        ),
    )
    op.create_index(
        "ix_quiz_attempts_user_quiz",
        "quiz_attempts",
        ["user_id", "quiz_id"],
    )

    op.create_table(
        "quiz_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_answer", postgresql.JSONB()),
        sa.Column("is_correct", sa.Boolean()),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["attempt_id", "user_id", "quiz_id"],
            [
                "quiz_attempts.id",
                "quiz_attempts.user_id",
                "quiz_attempts.quiz_id",
            ],
            ondelete="CASCADE",
            name="fk_quiz_answers_attempt_owner",
        ),
        sa.ForeignKeyConstraint(
            ["question_id", "user_id", "quiz_id"],
            [
                "quiz_questions.id",
                "quiz_questions.user_id",
                "quiz_questions.quiz_id",
            ],
            ondelete="CASCADE",
            name="fk_quiz_answers_question_owner",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.id"],
            ondelete="CASCADE",
            name="fk_quiz_answers_quiz",
        ),
        sa.UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_quiz_answers_attempt_question",
        ),
    )
    op.create_index(
        "ix_quiz_answers_user_attempt",
        "quiz_answers",
        ["user_id", "attempt_id"],
    )
    op.create_foreign_key(
        "fk_processing_jobs_quiz",
        "processing_jobs",
        "quizzes",
        ["quiz_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_processing_jobs_quiz",
        "processing_jobs",
        type_="foreignkey",
    )
    op.drop_index("ix_quiz_answers_user_attempt", table_name="quiz_answers")
    op.drop_table("quiz_answers")
    op.drop_index("ix_quiz_attempts_user_quiz", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index("ix_quiz_questions_quiz_user", table_name="quiz_questions")
    op.drop_table("quiz_questions")
    op.drop_index("ix_quizzes_user_document_created", table_name="quizzes")
    op.drop_table("quizzes")
    op.drop_constraint(
        "uq_document_chunks_id_document_user",
        "document_chunks",
        type_="unique",
    )

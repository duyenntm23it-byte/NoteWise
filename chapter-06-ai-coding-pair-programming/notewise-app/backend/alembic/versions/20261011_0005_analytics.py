"""Add analytics snapshots and learning history.

Revision ID: 20261011_0005
Revises: 20261011_0004
Create Date: 2026-10-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261011_0005"
down_revision: Union[str, None] = "20261011_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("document_title", sa.String(length=255)),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('DOCUMENT_UPLOADED', 'SUMMARY_CREATED', "
            "'QUESTION_ASKED', 'QUIZ_SUBMITTED')",
            name="ck_learning_history_event_type",
        ),
    )
    op.create_index(
        "ix_learning_history_user_occurred",
        "learning_history",
        ["user_id", "occurred_at"],
    )
    op.create_index(
        "ix_learning_history_user_type_occurred",
        "learning_history",
        ["user_id", "event_type", "occurred_at"],
    )

    op.create_table(
        "weak_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("topic_key", sa.String(length=200), nullable=False),
        sa.Column("accuracy", sa.Numeric(5, 2)),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("answered_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("sufficient_data", sa.Boolean(), nullable=False),
        sa.Column("is_weak", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("evidence", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "topic_key",
            name="uq_weak_topics_user_topic",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_weak_topics_attempts"),
        sa.CheckConstraint("answered_count >= 0", name="ck_weak_topics_answered"),
        sa.CheckConstraint("skipped_count >= 0", name="ck_weak_topics_skipped"),
        sa.CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 100)",
            name="ck_weak_topics_accuracy",
        ),
    )
    op.create_index(
        "ix_weak_topics_user_weak",
        "weak_topics",
        ["user_id", "is_weak"],
    )

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_chunks.id", ondelete="SET NULL"),
        ),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "topic",
            name="uq_recommendations_user_topic",
        ),
    )
    op.create_index(
        "ix_recommendations_user_created",
        "recommendations",
        ["user_id", "created_at"],
    )
    op.execute(
        """
        INSERT INTO learning_history (
            id, user_id, event_type, document_id, document_title,
            occurred_at, details
        )
        SELECT
            md5('DOCUMENT_UPLOADED:' || id::text)::uuid,
            user_id,
            'DOCUMENT_UPLOADED',
            id,
            filename,
            created_at,
            jsonb_build_object('status', status)
        FROM documents
        """
    )
    op.execute(
        """
        INSERT INTO learning_history (
            id, user_id, event_type, document_id, document_title,
            occurred_at, details
        )
        SELECT
            md5('SUMMARY_CREATED:' || summaries.id::text)::uuid,
            summaries.user_id,
            'SUMMARY_CREATED',
            summaries.document_id,
            documents.filename,
            summaries.created_at,
            jsonb_build_object('summary_id', summaries.id::text)
        FROM summaries
        JOIN documents ON documents.id = summaries.document_id
        """
    )
    op.execute(
        """
        INSERT INTO learning_history (
            id, user_id, event_type, document_id, document_title,
            occurred_at, details
        )
        SELECT
            md5('QUIZ_SUBMITTED:' || quiz_attempts.id::text)::uuid,
            quiz_attempts.user_id,
            'QUIZ_SUBMITTED',
            quizzes.document_id,
            documents.filename,
            COALESCE(quiz_attempts.submitted_at, quiz_attempts.started_at),
            jsonb_build_object(
                'attempt_id', quiz_attempts.id::text,
                'quiz_id', quizzes.id::text,
                'topic', quizzes.topic,
                'score', quiz_attempts.score
            )
        FROM quiz_attempts
        JOIN quizzes ON quizzes.id = quiz_attempts.quiz_id
        JOIN documents ON documents.id = quizzes.document_id
        WHERE quiz_attempts.status = 'SUBMITTED'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_user_created", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_weak_topics_user_weak", table_name="weak_topics")
    op.drop_table("weak_topics")
    op.drop_index("ix_learning_history_user_type_occurred", table_name="learning_history")
    op.drop_index("ix_learning_history_user_occurred", table_name="learning_history")
    op.drop_table("learning_history")

"""Create document, chunk, and processing-job tables.

Revision ID: 20261010_0002
Revises: 20261010_0001
Create Date: 2026-10-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20261010_0002"
down_revision: Union[str, None] = "20261010_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("failure_code", sa.String(length=64)),
        sa.Column("page_count", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'READY', 'FAILED', 'DELETING', 'DELETED')",
            name="ck_documents_status",
        ),
        sa.UniqueConstraint("id", "user_id", name="uq_documents_id_user"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index(
        "ix_documents_user_status_created",
        "documents",
        ["user_id", "status", "created_at"],
    )

    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(), nullable=True),
        sa.Column("page_number", sa.Integer()),
        sa.Column("section", sa.Text()),
        sa.ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["documents.id", "documents.user_id"],
            name="fk_document_chunks_document_owner",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_user_document",
        "document_chunks",
        ["user_id", "document_id"],
    )

    op.create_table(
        "processing_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
        ),
        sa.Column("summary_id", postgresql.UUID(as_uuid=True)),
        sa.Column("quiz_id", postgresql.UUID(as_uuid=True)),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "run_after",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(length=128)),
        sa.Column("request_hash", sa.String(length=64)),
        sa.Column("last_error_code", sa.String(length=64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'RETRY_WAIT', 'SUCCEEDED', "
            "'FAILED', 'CANCELLED')",
            name="ck_processing_jobs_status",
        ),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_processing_jobs_user_idempotency",
        ),
    )
    op.create_index(
        "ix_processing_jobs_status_run_after",
        "processing_jobs",
        ["status", "run_after"],
    )
    op.create_index(
        "ix_processing_jobs_user_document",
        "processing_jobs",
        ["user_id", "document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_user_document", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_status_run_after", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index(
        "ix_document_chunks_user_document",
        table_name="document_chunks",
    )
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_user_status_created", table_name="documents")
    op.drop_table("documents")

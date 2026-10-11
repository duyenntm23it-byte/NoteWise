"""Add fixed-dimension embeddings and summaries.

Revision ID: 20261010_0003
Revises: 20261010_0002
Create Date: 2026-10-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20261010_0003"
down_revision: Union[str, None] = "20261010_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM document_chunks
                WHERE embedding IS NOT NULL AND vector_dims(embedding) <> 1536
            ) THEN
                RAISE EXCEPTION
                    'Existing embeddings must be re-generated as 1536-dimensional vectors';
            END IF;
        END $$;
        """
    )
    op.alter_column(
        "document_chunks",
        "embedding",
        existing_type=Vector(),
        type_=Vector(1536),
        postgresql_using="embedding::vector(1536)",
        existing_nullable=True,
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=sa.text("embedding IS NOT NULL"),
    )
    op.create_table(
        "summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("failure_code", sa.String(length=64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'PROCESSING', 'READY', 'FAILED', 'DELETED')",
            name="ck_summaries_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["documents.id", "documents.user_id"],
            name="fk_summaries_document_owner",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_summaries_user_created",
        "summaries",
        ["user_id", "created_at"],
    )
    op.create_foreign_key(
        "fk_processing_jobs_summary",
        "processing_jobs",
        "summaries",
        ["summary_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_processing_jobs_summary",
        "processing_jobs",
        type_="foreignkey",
    )
    op.drop_index("ix_summaries_user_created", table_name="summaries")
    op.drop_table("summaries")
    op.drop_index(
        "ix_document_chunks_embedding_hnsw",
        table_name="document_chunks",
    )
    op.alter_column(
        "document_chunks",
        "embedding",
        existing_type=Vector(1536),
        type_=Vector(),
        postgresql_using="embedding::vector",
        existing_nullable=True,
    )

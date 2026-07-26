"""create knowledge documents

Revision ID: 0001
Revises:
Create Date: 2026-07-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_filename", sa.String(), nullable=False),
        sa.Column("storage_filename", sa.String(), nullable=False),
        sa.Column("document_type", sa.String(length=48), nullable=False),
        sa.Column("extracted_text", sa.String(), nullable=True),
        sa.Column("detected_topics", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "UPLOADED",
                "PROCESSING",
                "VALIDATING",
                "APPROVED",
                "CONTRIBUTOR_REVIEW_REQUIRED",
                "ADMIN_REVIEW_REQUIRED",
                "REJECTED",
                "FAILED",
                name="documentstatus",
                native_enum=False,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("validation_findings", sa.JSON(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256"),
    )
    op.create_index("ix_knowledge_documents_sha256", "knowledge_documents", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_sha256", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

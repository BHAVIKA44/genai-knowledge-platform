"""add document analysis

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_documents", sa.Column("analysis_summary", sa.String(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("analysis_topics", sa.JSON(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("analysis_claims", sa.JSON(), nullable=True))
    op.add_column(
        "knowledge_documents", sa.Column("analysis_proposed_title", sa.String(), nullable=True)
    )
    op.add_column("knowledge_documents", sa.Column("analysis_model", sa.String(), nullable=True))
    op.add_column(
        "knowledge_documents", sa.Column("analysis_prompt_version", sa.String(), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "analyzed_at")
    op.drop_column("knowledge_documents", "analysis_prompt_version")
    op.drop_column("knowledge_documents", "analysis_model")
    op.drop_column("knowledge_documents", "analysis_proposed_title")
    op.drop_column("knowledge_documents", "analysis_claims")
    op.drop_column("knowledge_documents", "analysis_topics")
    op.drop_column("knowledge_documents", "analysis_summary")

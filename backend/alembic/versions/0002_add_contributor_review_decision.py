"""add contributor review decision

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-26
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents", sa.Column("contributor_review_decision", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "contributor_review_decision")

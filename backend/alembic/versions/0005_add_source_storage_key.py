"""add source storage key

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents", sa.Column("source_storage_key", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "source_storage_key")

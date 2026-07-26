"""add grounded claim verifications

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents",
        sa.Column("grounded_claim_verifications", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "grounded_claim_verifications")

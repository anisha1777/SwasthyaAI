"""add patient timestamp defaults

Revision ID: 7f93ab179eed
Revises: e5790b2a415a
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7f93ab179eed"
down_revision = "e5790b2a415a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "patients",
        "created_at",
        existing_type=sa.DateTime(),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        existing_nullable=False,
    )

    op.alter_column(
        "patients",
        "updated_at",
        existing_type=sa.DateTime(),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "patients",
        "created_at",
        existing_type=sa.DateTime(),
        server_default=None,
        existing_nullable=False,
    )

    op.alter_column(
        "patients",
        "updated_at",
        existing_type=sa.DateTime(),
        server_default=None,
        existing_nullable=False,
    )

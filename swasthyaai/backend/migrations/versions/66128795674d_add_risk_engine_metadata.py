"""add risk engine metadata

Revision ID: 66128795674d
Revises: 536451624b87
Create Date: 2026-09-20 18:50:58.180215

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "66128795674d"
down_revision: Union[str, Sequence[str], None] = "536451624b87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add risk engine metadata to screening results."""

    op.add_column(
        "screening_results",
        sa.Column(
            "risk_engine_version",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.add_column(
        "screening_results",
        sa.Column(
            "risk_reason",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove risk engine metadata."""

    op.drop_column(
        "screening_results",
        "risk_reason",
    )

    op.drop_column(
        "screening_results",
        "risk_engine_version",
    )

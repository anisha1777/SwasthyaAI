"""create health cards

Revision ID: 536451624b87
Revises: ad999416af16
Create Date: 2026-09-20 18:15:09.387368

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "536451624b87"
down_revision: Union[str, Sequence[str], None] = "ad999416af16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create health_cards table."""
    op.create_table(
        "health_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("qr_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id"),
        sa.UniqueConstraint("token"),
    )

    op.create_index(
        "ix_health_cards_id",
        "health_cards",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_health_cards_patient_id",
        "health_cards",
        ["patient_id"],
        unique=True,
    )

    op.create_index(
        "ix_health_cards_token",
        "health_cards",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass

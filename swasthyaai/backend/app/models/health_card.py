from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class HealthCard(Base):
    __tablename__ = "health_cards"

    __table_args__ = (
        UniqueConstraint(
            "patient_id",
            name="health_cards_patient_id_key",
        ),
        UniqueConstraint(
            "token",
            name="health_cards_token_key",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
        unique=True,
    )

    token: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        unique=True,
    )

    qr_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

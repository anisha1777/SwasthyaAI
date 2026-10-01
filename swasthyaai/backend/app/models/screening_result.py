from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.database import Base


class ScreeningResult(Base):

    __tablename__ = "screening_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    screening_id: Mapped[int] = mapped_column(
        ForeignKey("screenings.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    prediction: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="LOW",
    )

    risk_engine_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    risk_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    gradcam_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    screening = relationship(
        "Screening",
        foreign_keys=[screening_id],
    )

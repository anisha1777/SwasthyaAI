from datetime import datetime

from sqlalchemy import (
    DateTime,
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


class FollowUp(Base):
    __tablename__ = "followups"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # PATIENT
    # ========================================================

    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )

    # ========================================================
    # SCREENING
    # ========================================================

    screening_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("screenings.id"),
        nullable=True,
        index=True,
    )

    # ========================================================
    # ASSIGNED WORKER
    # ========================================================

    assigned_to_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    # ========================================================
    # STATUS
    # ========================================================

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
        index=True,
    )

    # ========================================================
    # PRIORITY
    # ========================================================

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NORMAL",
        index=True,
    )

    # ========================================================
    # SCHEDULED / DUE DATE
    # ========================================================

    scheduled_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    # ========================================================
    # COMPLETION DATE
    # ========================================================

    completed_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # ========================================================
    # NOTES
    # ========================================================

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ========================================================
    # CREATED AT
    # ========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    patient = relationship(
        "Patient",
        foreign_keys=[patient_id],
    )

    screening = relationship(
        "Screening",
        foreign_keys=[screening_id],
    )

    assigned_to = relationship(
        "User",
        foreign_keys=[assigned_to_user_id],
    )

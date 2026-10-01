from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Screening(Base):
    __tablename__ = "screenings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        index=True
    )

    created_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    screening_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    symptoms: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
        index=True
    )

    screening_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    # --------------------------------------------------
    # IMAGE INFORMATION
    # --------------------------------------------------

    image_reference: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    image_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    image_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    image_width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    image_height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

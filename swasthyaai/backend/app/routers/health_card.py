from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db

from app.models.health_card import HealthCard
from app.models.patient import Patient
from app.models.screening import Screening
from app.models.screening_result import ScreeningResult
from app.models.followup import FollowUp
from app.models.user import User

from app.services.health_card import (
    generate_health_card_token,
    generate_qr_code,
)


# ============================================================
# ROUTERS
# ============================================================

# Used for:
# POST /api/healthcard/{patient_id}
router = APIRouter(
    tags=["Health Card"]
)


# Used for:
# GET /api/health-card/{token}
health_card_access_router = APIRouter(
    tags=["Health Card"]
)


# ============================================================
# CREATE HEALTH CARD
# ============================================================

@router.post(
    "/{patient_id}",
    status_code=201,
)
def create_health_card(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Generate a QR health card for a patient.

    Authorized roles:
        ADMIN
        ANM
        ASHA
    """

    # --------------------------------------------------------
    # RBAC
    # --------------------------------------------------------

    if user.role not in {
        "ADMIN",
        "ANM",
        "ASHA",
    }:
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized "
                "to generate health cards."
            ),
        )

    # --------------------------------------------------------
    # Find patient
    # --------------------------------------------------------

    patient = db.get(
        Patient,
        patient_id,
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    # --------------------------------------------------------
    # Check existing health card
    # --------------------------------------------------------

    existing_card = db.scalar(
        select(HealthCard)
        .where(
            HealthCard.patient_id
            == patient_id
        )
    )

    if existing_card is not None:

        return {
            "message": (
                "Health card already exists."
            ),
            "health_card": {
                "id": existing_card.id,
                "patient_id": (
                    existing_card.patient_id
                ),
                "token": existing_card.token,
                "qr_path": existing_card.qr_path,
                "created_at": (
                    existing_card.created_at
                ),
            },
        }

    # --------------------------------------------------------
    # Generate secure opaque token
    # --------------------------------------------------------

    token = generate_health_card_token()

    # --------------------------------------------------------
    # Create health card record
    # --------------------------------------------------------

    health_card = HealthCard(
        patient_id=patient_id,
        token=token,
    )

    db.add(health_card)

    try:
        db.commit()
        db.refresh(health_card)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to create health "
                "card record."
            ),
        )

    # --------------------------------------------------------
    # Generate QR image
    # --------------------------------------------------------

    try:

        qr_path = generate_qr_code(
            token=token,
            card_id=health_card.id,
        )

        health_card.qr_path = qr_path

        db.commit()
        db.refresh(health_card)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate QR code: "
                f"{str(exc)}"
            ),
        )

    # --------------------------------------------------------
    # Return response
    # --------------------------------------------------------

    return {
        "message": (
            "Health card created successfully."
        ),
        "health_card": {
            "id": health_card.id,
            "patient_id": (
                health_card.patient_id
            ),
            "token": health_card.token,
            "qr_path": health_card.qr_path,
            "created_at": (
                health_card.created_at
            ),
        },
    }


# ============================================================
# GET HEALTH CARD USING QR TOKEN
# ============================================================

@health_card_access_router.get(
    "/{token}"
)
def get_health_card(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve a patient's health information
    using the opaque QR token.

    No JWT authentication is required here because
    the QR token itself is the access credential.
    """

    # --------------------------------------------------------
    # Find health card using token
    # --------------------------------------------------------

    health_card = db.scalar(
        select(HealthCard)
        .where(
            HealthCard.token == token
        )
    )

    if health_card is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid health card token.",
        )

    # --------------------------------------------------------
    # Find patient
    # --------------------------------------------------------

    patient = db.get(
        Patient,
        health_card.patient_id,
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    # ========================================================
    # GET PATIENT SCREENINGS
    # ========================================================

    screenings = db.scalars(
        select(Screening)
        .where(
            Screening.patient_id
            == patient.id
        )
        .order_by(
            Screening.created_at.desc()
        )
    ).all()

    screening_data = []

    for screening in screenings:

        result = db.scalar(
            select(ScreeningResult)
            .where(
                ScreeningResult.screening_id
                == screening.id
            )
        )

        screening_data.append(
            {
                "id": screening.id,

                "screening_type": (
                    screening.screening_type
                ),

                "status": (
                    screening.status
                ),

                "screening_date": (
                    screening.screening_date
                ),

                "prediction": (
                    result.prediction
                    if result
                    else None
                ),

                "confidence": (
                    result.confidence
                    if result
                    else None
                ),

                "risk_level": (
                    result.risk_level
                    if result
                    else None
                ),

                "model_version": (
                    result.model_version
                    if result
                    else None
                ),
            }
        )

    # ========================================================
    # GET PATIENT FOLLOW-UPS
    # ========================================================

    followups = db.scalars(
        select(FollowUp)
        .where(
            FollowUp.patient_id
            == patient.id
        )
        .order_by(
            FollowUp.scheduled_date.desc()
        )
    ).all()

    followup_data = []

    for followup in followups:

        followup_data.append(
            {
                "id": followup.id,

                "screening_id": (
                    followup.screening_id
                ),

                "assigned_to_user_id": (
                    followup.assigned_to_user_id
                ),

                "status": (
                    followup.status
                ),

                "priority": (
                    followup.priority
                ),

                "scheduled_date": (
                    followup.scheduled_date
                ),

                "completed_date": (
                    followup.completed_date
                ),

                "notes": (
                    followup.notes
                ),
            }
        )

    # ========================================================
    # RETURN HEALTH CARD
    # ========================================================

    return {
        "health_card": {
            "id": health_card.id,
            "created_at": (
                health_card.created_at
            ),
        },

        "patient": {
            "id": patient.id,

            "patient_code": (
                patient.patient_code
            ),

            "name": patient.name,

            "age": patient.age,

            "gender": patient.gender,

            "village": patient.village,

            "guardian_name": (
                patient.guardian_name
            ),
        },

        "screenings": screening_data,

        "followups": followup_data,
    }

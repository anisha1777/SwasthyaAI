from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db

from app.models.followup import FollowUp
from app.models.patient import Patient
from app.models.screening import Screening
from app.models.screening_result import ScreeningResult
from app.models.user import User


router = APIRouter(
    tags=["Dashboard"]
)


# ============================================================
# COMMON HELPERS
# ============================================================

def refresh_followup_status(followup: FollowUp) -> str:
    """
    Automatically calculate PENDING / DUE / OVERDUE.

    COMPLETED and CANCELLED are final states and
    are not changed automatically.
    """

    if followup.status in {
        "COMPLETED",
        "CANCELLED",
    }:
        return followup.status

    today = datetime.utcnow().date()

    if followup.scheduled_date.date() < today:
        return "OVERDUE"

    if followup.scheduled_date.date() == today:
        return "DUE"

    return "PENDING"


def screening_result_data(
    db: Session,
    screening: Screening,
):
    """
    Get the result associated with a screening.
    """

    result = db.scalar(
        select(ScreeningResult)
        .where(
            ScreeningResult.screening_id
            == screening.id
        )
    )

    if result is None:
        return {
            "prediction": None,
            "confidence": None,
            "risk_level": None,
        }

    return {
        "prediction": result.prediction,
        "confidence": result.confidence,
        "risk_level": result.risk_level,
    }


# ============================================================
# ANM DASHBOARD
# ============================================================

@router.get("/anm")
def get_anm_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    ANM dashboard.

    ADMIN is also allowed to access this dashboard for
    administrative/testing purposes.
    """

    # --------------------------------------------------------
    # RBAC
    # --------------------------------------------------------

    if user.role not in {
        "ANM",
        "ADMIN",
    }:
        raise HTTPException(
            status_code=403,
            detail=(
                "Only ANM or ADMIN users can "
                "view the ANM dashboard."
            ),
        )

    # ========================================================
    # PATIENT COUNTS
    # ========================================================

    total_patients = db.scalar(
        select(func.count(Patient.id))
    ) or 0

    # ========================================================
    # SCREENING COUNTS
    # ========================================================

    total_screenings = db.scalar(
        select(func.count(Screening.id))
    ) or 0

    pending_screenings = db.scalar(
        select(func.count(Screening.id))
        .where(
            Screening.status == "PENDING"
        )
    ) or 0

    analyzed_screenings = db.scalar(
        select(func.count(Screening.id))
        .where(
            Screening.status == "ANALYZED"
        )
    ) or 0

    quality_failed_screenings = db.scalar(
        select(func.count(Screening.id))
        .where(
            Screening.status == "QUALITY_FAILED"
        )
    ) or 0

    # ========================================================
    # SCREENING TYPE COUNTS
    # ========================================================

    jaundice_screenings = db.scalar(
        select(func.count(Screening.id))
        .where(
            Screening.screening_type == "JAUNDICE"
        )
    ) or 0

    skin_screenings = db.scalar(
        select(func.count(Screening.id))
        .where(
            Screening.screening_type == "SKIN"
        )
    ) or 0

    anemia_screenings = db.scalar(
        select(func.count(Screening.id))
        .where(
            Screening.screening_type == "ANEMIA"
        )
    ) or 0

    # ========================================================
    # RISK COUNTS
    # ========================================================

    high_risk_results = db.scalar(
        select(func.count(ScreeningResult.id))
        .where(
            ScreeningResult.risk_level == "HIGH"
        )
    ) or 0

    moderate_risk_results = db.scalar(
        select(func.count(ScreeningResult.id))
        .where(
            ScreeningResult.risk_level == "MODERATE"
        )
    ) or 0

    low_risk_results = db.scalar(
        select(func.count(ScreeningResult.id))
        .where(
            ScreeningResult.risk_level == "LOW"
        )
    ) or 0

    # ========================================================
    # FOLLOW-UPS
    # ========================================================

    all_followups = db.scalars(
        select(FollowUp)
        .order_by(
            FollowUp.scheduled_date.asc()
        )
    ).all()

    # Refresh dynamic statuses first.
    followup_status_changed = False

    for followup in all_followups:

        old_status = followup.status

        new_status = refresh_followup_status(
            followup
        )

        if (
            old_status != new_status
            and old_status not in {
                "COMPLETED",
                "CANCELLED",
            }
        ):
            followup.status = new_status
            followup_status_changed = True

    # --------------------------------------------------------
    # Follow-up counts AFTER status refresh
    # --------------------------------------------------------

    total_followups = len(all_followups)

    pending_followups = sum(
        1
        for followup in all_followups
        if followup.status == "PENDING"
    )

    due_followups = sum(
        1
        for followup in all_followups
        if followup.status == "DUE"
    )

    overdue_followups = sum(
        1
        for followup in all_followups
        if followup.status == "OVERDUE"
    )

    completed_followups = sum(
        1
        for followup in all_followups
        if followup.status == "COMPLETED"
    )

    cancelled_followups = sum(
        1
        for followup in all_followups
        if followup.status == "CANCELLED"
    )

    # ========================================================
    # RECENT SCREENINGS
    # ========================================================

    recent_screenings = db.scalars(
        select(Screening)
        .order_by(
            Screening.created_at.desc()
        )
        .limit(10)
    ).all()

    recent_screening_data = []

    for screening in recent_screenings:

        result_data = screening_result_data(
            db,
            screening,
        )

        recent_screening_data.append(
            {
                "id": screening.id,
                "patient_id": screening.patient_id,
                "screening_type": (
                    screening.screening_type
                ),
                "status": screening.status,
                "screening_date": (
                    screening.screening_date
                ),
                "prediction": (
                    result_data["prediction"]
                ),
                "confidence": (
                    result_data["confidence"]
                ),
                "risk_level": (
                    result_data["risk_level"]
                ),
            }
        )

    # ========================================================
    # RECENT FOLLOW-UPS
    # ========================================================

    recent_followups = all_followups[:10]

    recent_followup_data = []

    for followup in recent_followups:

        recent_followup_data.append(
            {
                "id": followup.id,
                "patient_id": followup.patient_id,
                "screening_id": followup.screening_id,
                "assigned_to_user_id": (
                    followup.assigned_to_user_id
                ),
                "status": followup.status,
                "priority": followup.priority,
                "scheduled_date": (
                    followup.scheduled_date
                ),
                "completed_date": (
                    followup.completed_date
                ),
                "notes": followup.notes,
            }
        )

    # ========================================================
    # SAVE REFRESHED FOLLOW-UP STATUS
    # ========================================================

    if followup_status_changed:

        try:
            db.commit()

        except Exception:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to update "
                    "follow-up statuses."
                ),
            )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "dashboard": "ANM",

        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },

        "summary": {
            "total_patients": total_patients,
            "total_screenings": total_screenings,
            "total_followups": total_followups,
        },

        "screenings": {
            "total": total_screenings,
            "pending": pending_screenings,
            "analyzed": analyzed_screenings,
            "quality_failed": (
                quality_failed_screenings
            ),
            "jaundice": jaundice_screenings,
            "skin": skin_screenings,
            "anemia": anemia_screenings,
        },

        "risk": {
            "high": high_risk_results,
            "moderate": moderate_risk_results,
            "low": low_risk_results,
        },

        "followups": {
            "total": total_followups,
            "pending": pending_followups,
            "due": due_followups,
            "overdue": overdue_followups,
            "completed": completed_followups,
            "cancelled": cancelled_followups,
        },

        "recent_screenings": (
            recent_screening_data
        ),

        "recent_followups": (
            recent_followup_data
        ),
    }


# ============================================================
# ASHA DASHBOARD
# ============================================================

@router.get("/asha")
def get_asha_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    ASHA dashboard.

    ASHA sees follow-ups assigned to their user ID
    and screenings created by their user ID.

    ADMIN is allowed for testing/administrative purposes.
    """

    # --------------------------------------------------------
    # RBAC
    # --------------------------------------------------------

    if user.role not in {
        "ASHA",
        "ADMIN",
    }:
        raise HTTPException(
            status_code=403,
            detail=(
                "Only ASHA or ADMIN users can "
                "view the ASHA dashboard."
            ),
        )

    # ========================================================
    # MY FOLLOW-UPS
    # ========================================================

    my_followups = db.scalars(
        select(FollowUp)
        .where(
            FollowUp.assigned_to_user_id
            == user.id
        )
        .order_by(
            FollowUp.scheduled_date.asc()
        )
    ).all()

    # ========================================================
    # REFRESH FOLLOW-UP STATUS
    # ========================================================

    followup_status_changed = False

    for followup in my_followups:

        old_status = followup.status

        new_status = refresh_followup_status(
            followup
        )

        if (
            old_status != new_status
            and old_status not in {
                "COMPLETED",
                "CANCELLED",
            }
        ):
            followup.status = new_status
            followup_status_changed = True

    # ========================================================
    # FOLLOW-UP COUNTS
    # ========================================================

    total_followups = len(
        my_followups
    )

    pending_followups = sum(
        1
        for followup in my_followups
        if followup.status == "PENDING"
    )

    due_followups = sum(
        1
        for followup in my_followups
        if followup.status == "DUE"
    )

    overdue_followups = sum(
        1
        for followup in my_followups
        if followup.status == "OVERDUE"
    )

    completed_followups = sum(
        1
        for followup in my_followups
        if followup.status == "COMPLETED"
    )

    cancelled_followups = sum(
        1
        for followup in my_followups
        if followup.status == "CANCELLED"
    )

    # ========================================================
    # MY SCREENINGS
    # ========================================================

    my_screenings = db.scalars(
        select(Screening)
        .where(
            Screening.created_by == user.id
        )
        .order_by(
            Screening.created_at.desc()
        )
    ).all()

    # ========================================================
    # SCREENING COUNTS
    # ========================================================

    total_screenings = len(
        my_screenings
    )

    pending_screenings = sum(
        1
        for screening in my_screenings
        if screening.status == "PENDING"
    )

    analyzed_screenings = sum(
        1
        for screening in my_screenings
        if screening.status == "ANALYZED"
    )

    quality_failed_screenings = sum(
        1
        for screening in my_screenings
        if screening.status
        == "QUALITY_FAILED"
    )

    # ========================================================
    # SCREENING TYPE COUNTS
    # ========================================================

    jaundice_screenings = sum(
        1
        for screening in my_screenings
        if screening.screening_type
        == "JAUNDICE"
    )

    skin_screenings = sum(
        1
        for screening in my_screenings
        if screening.screening_type
        == "SKIN"
    )

    anemia_screenings = sum(
        1
        for screening in my_screenings
        if screening.screening_type
        == "ANEMIA"
    )

    # ========================================================
    # MY RISK COUNTS
    # ========================================================

    high_risk = 0
    moderate_risk = 0
    low_risk = 0

    # ========================================================
    # RECENT SCREENINGS
    # ========================================================

    recent_screenings = []

    for screening in my_screenings[:10]:

        result_data = screening_result_data(
            db,
            screening,
        )

        risk_level = (
            result_data["risk_level"]
        )

        if risk_level == "HIGH":
            high_risk += 1

        elif risk_level == "MODERATE":
            moderate_risk += 1

        elif risk_level == "LOW":
            low_risk += 1

        recent_screenings.append(
            {
                "id": screening.id,
                "patient_id": screening.patient_id,
                "screening_type": (
                    screening.screening_type
                ),
                "status": screening.status,
                "screening_date": (
                    screening.screening_date
                ),
                "prediction": (
                    result_data["prediction"]
                ),
                "confidence": (
                    result_data["confidence"]
                ),
                "risk_level": risk_level,
            }
        )

    # ========================================================
    # RECENT FOLLOW-UPS
    # ========================================================

    recent_followups = []

    for followup in my_followups[:10]:

        recent_followups.append(
            {
                "id": followup.id,
                "patient_id": followup.patient_id,
                "screening_id": followup.screening_id,
                "assigned_to_user_id": (
                    followup.assigned_to_user_id
                ),
                "status": followup.status,
                "priority": followup.priority,
                "scheduled_date": (
                    followup.scheduled_date
                ),
                "completed_date": (
                    followup.completed_date
                ),
                "notes": followup.notes,
            }
        )

    # ========================================================
    # SAVE STATUS CHANGES
    # ========================================================

    if followup_status_changed:

        try:
            db.commit()

        except Exception:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to update "
                    "follow-up statuses."
                ),
            )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "dashboard": "ASHA",

        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },

        "summary": {
            "my_screenings": total_screenings,
            "my_followups": total_followups,
        },

        "screenings": {
            "total": total_screenings,
            "pending": pending_screenings,
            "analyzed": analyzed_screenings,
            "quality_failed": (
                quality_failed_screenings
            ),
            "jaundice": jaundice_screenings,
            "skin": skin_screenings,
            "anemia": anemia_screenings,
        },

        "risk": {
            "high": high_risk,
            "moderate": moderate_risk,
            "low": low_risk,
        },

        "followups": {
            "total": total_followups,
            "pending": pending_followups,
            "due": due_followups,
            "overdue": overdue_followups,
            "completed": completed_followups,
            "cancelled": cancelled_followups,
        },

        "recent_screenings": (
            recent_screenings
        ),

        "recent_followups": (
            recent_followups
        ),
    }

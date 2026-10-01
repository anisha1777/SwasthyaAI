from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db

from app.models.followup import FollowUp
from app.models.patient import Patient
from app.models.screening import Screening
from app.models.user import User

from app.services.audit_service import create_audit_log


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    tags=["Follow-ups"]
)


# ============================================================
# CONSTANTS
# ============================================================

VALID_STATUSES = {
    "PENDING",
    "DUE",
    "OVERDUE",
    "COMPLETED",
    "CANCELLED",
}

VALID_PRIORITIES = {
    "LOW",
    "NORMAL",
    "HIGH",
    "URGENT",
}


# ============================================================
# ACCESS CONTROL
# ============================================================

def can_access_followup(
    user: User,
    followup: FollowUp,
) -> bool:

    # ADMIN and ANM can access all follow-ups
    if user.role in {
        "ADMIN",
        "ANM",
    }:
        return True

    # If assigned to a specific worker,
    # only that worker can access it.
    if followup.assigned_to_user_id is not None:
        return followup.assigned_to_user_id == user.id

    # Current project Patient model does not yet
    # have assigned_worker_id, so unassigned follow-ups
    # remain accessible to ASHA.
    return True


# ============================================================
# CALCULATE CURRENT STATUS
# ============================================================

def calculate_followup_status(
    followup: FollowUp,
) -> str:

    # Completed and cancelled are final states.
    if followup.status in {
        "COMPLETED",
        "CANCELLED",
    }:
        return followup.status

    now = datetime.utcnow()

    # Due date has passed.
    if now.date() > followup.scheduled_date.date():
        return "OVERDUE"

    # Due today.
    if now.date() == followup.scheduled_date.date():
        return "DUE"

    # Future date.
    return "PENDING"


# ============================================================
# UPDATE STORED STATUS
# ============================================================

def refresh_followup_status(
    followup: FollowUp,
) -> str:

    new_status = calculate_followup_status(
        followup
    )

    if followup.status not in {
        "COMPLETED",
        "CANCELLED",
    }:
        followup.status = new_status

    return followup.status


# ============================================================
# CREATE FOLLOW-UP
# ============================================================

@router.post(
    "",
    status_code=201,
)
def create_followup(
    patient_id: int,
    scheduled_date: datetime,
    screening_id: int | None = None,
    assigned_to_user_id: int | None = None,
    priority: str = "NORMAL",
    notes: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

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
    # Validate screening
    # --------------------------------------------------------

    if screening_id is not None:

        screening = db.get(
            Screening,
            screening_id,
        )

        if screening is None:
            raise HTTPException(
                status_code=404,
                detail="Screening not found.",
            )

        if screening.patient_id != patient_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Screening does not belong "
                    "to the specified patient."
                ),
            )

    # --------------------------------------------------------
    # Validate assigned worker
    # --------------------------------------------------------

    assigned_user = None

    if assigned_to_user_id is not None:

        assigned_user = db.get(
            User,
            assigned_to_user_id,
        )

        if assigned_user is None:
            raise HTTPException(
                status_code=404,
                detail="Assigned user not found.",
            )

        if assigned_user.role not in {
            "ASHA",
            "ANM",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Follow-ups can only be "
                    "assigned to ASHA or ANM users."
                ),
            )

    # --------------------------------------------------------
    # Validate priority
    # --------------------------------------------------------

    priority = priority.strip().upper()

    if priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid priority.",
                "allowed_priorities": sorted(
                    VALID_PRIORITIES
                ),
            },
        )

    # --------------------------------------------------------
    # Determine initial status
    # --------------------------------------------------------

    if scheduled_date.date() < datetime.utcnow().date():
        initial_status = "OVERDUE"

    elif scheduled_date.date() == datetime.utcnow().date():
        initial_status = "DUE"

    else:
        initial_status = "PENDING"

    # --------------------------------------------------------
    # Create follow-up
    # --------------------------------------------------------

    followup = FollowUp(
        patient_id=patient_id,
        screening_id=screening_id,
        assigned_to_user_id=assigned_to_user_id,
        status=initial_status,
        priority=priority,
        scheduled_date=scheduled_date,
        notes=notes,
    )

    db.add(
        followup
    )

    try:

        db.flush()

        # ----------------------------------------------------
        # Audit log
        # ----------------------------------------------------

        create_audit_log(
            db=db,
            action="FOLLOWUP_CREATED",
            user_id=user.id,
            entity_type="FOLLOWUP",
            entity_id=followup.id,
            details={
                "patient_id": patient_id,
                "screening_id": screening_id,
                "assigned_to_user_id": (
                    assigned_to_user_id
                ),
                "priority": priority,
                "scheduled_date": scheduled_date,
                "status": initial_status,
            },
        )

        db.commit()

        db.refresh(
            followup
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to create follow-up.",
        )

    return {
        "message": (
            "Follow-up created successfully."
        ),
        "followup": {
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
            "created_at": followup.created_at,
        },
    }


# ============================================================
# GET FOLLOW-UPS
# ============================================================

@router.get("")
def get_followups(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    query = select(
        FollowUp
    ).order_by(
        FollowUp.scheduled_date.asc()
    )

    # --------------------------------------------------------
    # ADMIN / ANM
    # --------------------------------------------------------

    if user.role in {
        "ADMIN",
        "ANM",
    }:

        if status:

            status = status.strip().upper()

            if status not in VALID_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Invalid status.",
                        "allowed_statuses": sorted(
                            VALID_STATUSES
                        ),
                    },
                )

            query = query.where(
                FollowUp.status == status
            )

    # --------------------------------------------------------
    # ASHA
    # --------------------------------------------------------

    else:

        query = query.where(
            (
                FollowUp.assigned_to_user_id
                == user.id
            )
            |
            (
                FollowUp.assigned_to_user_id
                .is_(None)
            )
        )

        if status:

            status = status.strip().upper()

            if status not in VALID_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Invalid status.",
                        "allowed_statuses": sorted(
                            VALID_STATUSES
                        ),
                    },
                )

            query = query.where(
                FollowUp.status == status
            )

    followups = db.scalars(
        query
    ).all()

    # --------------------------------------------------------
    # Refresh dynamic statuses
    # --------------------------------------------------------

    changed = False

    for followup in followups:

        old_status = followup.status

        new_status = refresh_followup_status(
            followup
        )

        if old_status != new_status:
            changed = True

    if changed:

        try:
            db.commit()

        except Exception:
            db.rollback()

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "count": len(followups),
        "followups": [
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
                "created_at": (
                    followup.created_at
                ),
            }
            for followup in followups
        ],
    }


# ============================================================
# GET SINGLE FOLLOW-UP
# ============================================================

@router.get(
    "/{followup_id}"
)
def get_followup(
    followup_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    followup = db.get(
        FollowUp,
        followup_id,
    )

    if followup is None:
        raise HTTPException(
            status_code=404,
            detail="Follow-up not found.",
        )

    # --------------------------------------------------------
    # Access
    # --------------------------------------------------------

    if not can_access_followup(
        user,
        followup,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this follow-up."
            ),
        )

    # --------------------------------------------------------
    # Refresh status
    # --------------------------------------------------------

    old_status = followup.status

    new_status = refresh_followup_status(
        followup
    )

    if old_status != new_status:

        try:
            db.commit()

        except Exception:
            db.rollback()

    return {
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
        "created_at": followup.created_at,
    }


# ============================================================
# UPDATE FOLLOW-UP
# ============================================================

@router.put(
    "/{followup_id}"
)
def update_followup(
    followup_id: int,
    status: str | None = None,
    scheduled_date: datetime | None = None,
    assigned_to_user_id: int | None = None,
    priority: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    followup = db.get(
        FollowUp,
        followup_id,
    )

    if followup is None:
        raise HTTPException(
            status_code=404,
            detail="Follow-up not found.",
        )

    # --------------------------------------------------------
    # Access
    # --------------------------------------------------------

    if not can_access_followup(
        user,
        followup,
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this follow-up."
            ),
        )

    # ========================================================
    # STATUS UPDATE
    # ========================================================

    if status is not None:

        status = status.strip().upper()

        if status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid status.",
                    "allowed_statuses": sorted(
                        VALID_STATUSES
                    ),
                },
            )

        # DUE and OVERDUE are automatically derived
        # from the scheduled date.
        if status in {
            "DUE",
            "OVERDUE",
        }:

            raise HTTPException(
                status_code=400,
                detail=(
                    "DUE and OVERDUE are automatically "
                    "calculated from the scheduled date."
                ),
            )

        # ----------------------------------------------------
        # Completed
        # ----------------------------------------------------

        if status == "COMPLETED":

            followup.status = "COMPLETED"

            if followup.completed_date is None:
                followup.completed_date = (
                    datetime.utcnow()
                )

        # ----------------------------------------------------
        # Cancelled
        # ----------------------------------------------------

        elif status == "CANCELLED":

            followup.status = "CANCELLED"

        # ----------------------------------------------------
        # Pending
        # ----------------------------------------------------

        elif status == "PENDING":

            followup.status = "PENDING"

            followup.completed_date = None

    # ========================================================
    # DATE UPDATE
    # ========================================================

    if scheduled_date is not None:

        followup.scheduled_date = (
            scheduled_date
        )

        # Recalculate status only when not completed/cancelled
        if followup.status not in {
            "COMPLETED",
            "CANCELLED",
        }:

            followup.status = (
                calculate_followup_status(
                    followup
                )
            )

    # ========================================================
    # ASSIGNED USER
    # ========================================================

    if assigned_to_user_id is not None:

        assigned_user = db.get(
            User,
            assigned_to_user_id,
        )

        if assigned_user is None:
            raise HTTPException(
                status_code=404,
                detail="Assigned user not found.",
            )

        if assigned_user.role not in {
            "ASHA",
            "ANM",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Follow-ups can only be "
                    "assigned to ASHA or ANM users."
                ),
            )

        followup.assigned_to_user_id = (
            assigned_to_user_id
        )

    # ========================================================
    # PRIORITY
    # ========================================================

    if priority is not None:

        priority = priority.strip().upper()

        if priority not in VALID_PRIORITIES:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid priority.",
                    "allowed_priorities": sorted(
                        VALID_PRIORITIES
                    ),
                },
            )

        followup.priority = priority

    # ========================================================
    # NOTES
    # ========================================================

    if notes is not None:
        followup.notes = notes

    # ========================================================
    # AUDIT
    # ========================================================

    create_audit_log(
        db=db,
        action="FOLLOWUP_UPDATED",
        user_id=user.id,
        entity_type="FOLLOWUP",
        entity_id=followup.id,
        details={
            "status": followup.status,
            "priority": followup.priority,
            "scheduled_date": (
                followup.scheduled_date
            ),
            "assigned_to_user_id": (
                followup.assigned_to_user_id
            ),
        },
    )

    # ========================================================
    # SAVE
    # ========================================================

    try:

        db.commit()

        db.refresh(
            followup
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to update follow-up.",
        )

    return {
        "message": (
            "Follow-up updated successfully."
        ),
        "followup": {
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
            "created_at": followup.created_at,
        },
    }

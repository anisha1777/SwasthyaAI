from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db

from app.models.audit_log import AuditLog
from app.models.user import User


router = APIRouter(
    tags=["Audit Logs"]
)


# ============================================================
# GET AUDIT LOGS
# ============================================================

@router.get("")
def get_audit_logs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Return audit logs.

    Only ADMIN users can access the audit log endpoint.
    """

    if user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only ADMIN users can view audit logs.",
        )

    logs = db.scalars(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
    ).all()

    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


# ============================================================
# GET SINGLE AUDIT LOG
# ============================================================

@router.get("/{audit_id}")
def get_audit_log(
    audit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Return a single audit log.

    Only ADMIN users can access audit logs.
    """

    if user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only ADMIN users can view audit logs.",
        )

    log = db.get(
        AuditLog,
        audit_id,
    )

    if log is None:
        raise HTTPException(
            status_code=404,
            detail="Audit log not found.",
        )

    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "details": log.details,
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }

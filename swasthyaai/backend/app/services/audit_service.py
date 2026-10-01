import json

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def create_audit_log(
    db: Session,
    action: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Create an audit log entry.

    This function records metadata about an action.
    It does not store uploaded image contents.
    """

    details_text = None

    if details is not None:
        details_text = json.dumps(
            details,
            default=str,
        )

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details_text,
        ip_address=ip_address,
    )

    db.add(audit_log)

    return audit_log

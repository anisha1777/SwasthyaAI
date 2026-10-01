from app.db.database import SessionLocal
from app.services.audit_service import create_audit_log
from app.models.audit_log import AuditLog


def test_create_audit_log():
    db = SessionLocal()

    try:
        log = create_audit_log(
            db=db,
            action="TEST_AUDIT",
            user_id=1,
            entity_type="TEST",
            entity_id=999,
            details={
                "message": "Audit system test"
            },
        )

        db.flush()

        assert log.id is not None
        assert log.action == "TEST_AUDIT"
        assert log.user_id == 1
        assert log.entity_type == "TEST"
        assert log.entity_id == 999

        db.commit()

        saved_log = db.get(AuditLog, log.id)

        assert saved_log is not None
        assert saved_log.action == "TEST_AUDIT"
        assert saved_log.user_id == 1

    finally:
        db.close()

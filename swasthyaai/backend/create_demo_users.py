from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password


def create_user(db, name, email, password, role, village=None, phone=None):
    existing = db.query(User).filter(User.email == email).first()

    if existing:
        print(f"Already exists: {email} ({existing.role})")
        return

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        village=village,
        phone=phone,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"Created: {email} | Role: {role} | ID: {user.id}")


db = SessionLocal()

try:
    create_user(
        db,
        name="Demo ASHA",
        email="asha@swasthyaai.com",
        password="Asha@12345",
        role="ASHA",
        village="Demo Village",
        phone="9000000001",
    )

    create_user(
        db,
        name="Demo ANM",
        email="anm@swasthyaai.com",
        password="Anm@12345",
        role="ANM",
        village="Demo Village",
        phone="9000000002",
    )

    create_user(
        db,
        name="Demo Admin",
        email="admin@swasthyaai.com",
        password="Admin@12345",
        role="ADMIN",
        village="Demo Village",
        phone="9000000003",
    )

finally:
    db.close()

from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password


db = SessionLocal()

try:
    # Check whether ANM already exists
    existing_user = (
        db.query(User)
        .filter(User.email == "anm@swasthyaai.com")
        .first()
    )

    if existing_user:
        print("ANM user already exists.")
        print("ID:", existing_user.id)
        print("Name:", existing_user.name)
        print("Email:", existing_user.email)
        print("Role:", existing_user.role)

    else:
        anm_user = User(
            name="Demo ANM",
            email="anm@swasthyaai.com",
            password_hash=hash_password("anm12345"),
            role="ANM",
            village="Demo Village",
            phone="9999999999"
        )

        db.add(anm_user)
        db.commit()
        db.refresh(anm_user)

        print("ANM user created successfully!")
        print("ID:", anm_user.id)
        print("Name:", anm_user.name)
        print("Email:", anm_user.email)
        print("Role:", anm_user.role)

finally:
    db.close()
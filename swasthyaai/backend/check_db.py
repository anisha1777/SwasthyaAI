from app.db.database import engine
from sqlalchemy import text

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT current_database(), current_user")
    )
    print(result.fetchone())

    result = connection.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'users'
            ORDER BY ordinal_position
        """)
    )

    print(result.fetchall())

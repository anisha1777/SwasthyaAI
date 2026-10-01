from sqlalchemy import text

from app.db.database import engine


try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database();")
        )

        database_name = result.scalar()

        print(f"Connected to database: {database_name}")

except Exception as e:
    print("Database connection failed:")
    print(e)

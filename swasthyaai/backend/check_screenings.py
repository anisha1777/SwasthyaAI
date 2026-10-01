from app.db.database import engine
from sqlalchemy import text

with engine.connect() as connection:
    result = connection.execute(
        text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'screenings'
            ORDER BY ordinal_position
        """)
    )

    for row in result:
        print(row)
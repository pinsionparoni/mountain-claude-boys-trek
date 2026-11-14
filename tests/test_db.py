
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")

if not url:
    print("ERROR: DATABASE_URL not found. Check your .env file.")
    raise SystemExit(1)

try:
    with psycopg.connect(url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            database, user = cur.fetchone()

            print(f"Connected to database: {database}")
            print(f"Database user: {user}")

            cur.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('customers', 'transactions')
                ORDER BY table_name, ordinal_position
            """)

            print("\nTable columns:")
            for table, column, data_type in cur.fetchall():
                print(f"{table}.{column} ({data_type})")

    print("\nSUCCESS: Database connection works!")

except Exception as error:
    print(f"\nCONNECTION FAILED: {error}")

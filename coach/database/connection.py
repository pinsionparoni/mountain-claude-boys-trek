
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def get_connection():
    """Create a connection to the configured PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Check your .env file."
        )

    return psycopg.connect(
        database_url,
        connect_timeout=10,
        row_factory=dict_row,
    )

import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

# One connection for the whole process. Opening a new TLS connection to Aiven
# in Frankfurt costs about half a second per query; reusing one keeps tool
# calls around 50-100 ms and stays well inside Aiven's 15-connection limit.
_connection = None


def _connect():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Check your .env file."
        )

    return psycopg.connect(
        database_url,
        connect_timeout=10,
        row_factory=dict_row,
        autocommit=True,
        # The coach only ever reads; the database rejects any write.
        options="-c default_transaction_read_only=on",
    )


@contextmanager
def get_connection():
    """Yield the shared read-only connection, reconnecting if it has dropped."""
    global _connection

    if _connection is None or _connection.closed or _connection.broken:
        _connection = _connect()

    try:
        yield _connection
    except psycopg.OperationalError:
        # The connection is probably gone; start fresh on the next call.
        _connection.close()
        _connection = None
        raise

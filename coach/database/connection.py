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
        # A long-lived connection can die silently (an idle network path dropped
        # without either end being told). Then every query waited forever: the
        # hosted demo hung for its full 10-minute limit. Keepalive probes find a
        # dead connection within about a minute, unacknowledged data counts as a
        # broken connection after 30 s, and get_connection() opens a new one.
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
        tcp_user_timeout=30_000,
        # The coach only ever reads; the database rejects any write. No query
        # may run past 2 minutes (the slowest, the peer population, takes 7-28 s).
        options="-c default_transaction_read_only=on -c statement_timeout=120000",
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

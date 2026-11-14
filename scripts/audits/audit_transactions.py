
from coach.database.connection import get_connection

CUSTOMER_ID = "CUST00001"

query = """
    SELECT
        category,
        transaction_type,
        CASE
            WHEN tx_amount_eur < 0 THEN 'negative'
            WHEN tx_amount_eur > 0 THEN 'positive'
            ELSE 'zero'
        END AS amount_direction,
        COUNT(*) AS transaction_count,
        SUM(ABS(tx_amount_eur)) AS total_amount_eur
    FROM transactions
    WHERE customer_id = %s
    GROUP BY
        category,
        transaction_type,
        amount_direction
    ORDER BY category, transaction_type, amount_direction;
"""

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(query, (CUSTOMER_ID,))

        for row in cur.fetchall():
            print(row)

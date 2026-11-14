
from coach.database.connection import get_connection

# monthly_balance_trend takes the last balance_after_eur of each month across
# all of a customer's rows. That is only a true "account balance" if each
# customer has a single bank account. This audit counts accounts per customer.

query = """
    SELECT
        accounts_per_customer,
        COUNT(*) AS customers
    FROM (
        SELECT
            customer_id,
            COUNT(DISTINCT bank_account_id) AS accounts_per_customer
        FROM transactions
        GROUP BY customer_id
    ) AS per_customer
    GROUP BY accounts_per_customer
    ORDER BY accounts_per_customer;
"""

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(query)

        print("accounts_per_customer | customers")
        for row in cur.fetchall():
            print(row)

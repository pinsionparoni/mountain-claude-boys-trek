
from datetime import date

from coach.database.connection import get_connection


def spending_by_category(
    customer_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Return a customer's spending grouped by category.

    Only negative transactions are counted as spending.
    Dates are inclusive.
    """
    if not customer_id:
        raise ValueError("customer_id is required")

    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    query = """
        SELECT
            COALESCE(category, 'Uncategorized') AS category,
            SUM(-tx_amount_eur) AS total_spending_eur,
            COUNT(*) AS transaction_count
        FROM transactions
        WHERE customer_id = %s
          AND tx_date >= %s
          AND tx_date <= %s
          AND tx_amount_eur < 0
          AND transaction_type != 'investment_deposit'
        GROUP BY category
        ORDER BY total_spending_eur DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (customer_id, start_date, end_date),
            )
            return cur.fetchall()


def monthly_balance_trend(
    customer_id: str,
    months: int = 6,
) -> list[dict]:
    """
    Return the latest recorded transaction balance
    for each month, for one customer.

    Includes the current month and previous months.
    """
    if not customer_id:
        raise ValueError("customer_id is required")

    if not 1 <= months <= 24:
        raise ValueError("months must be between 1 and 24")

    query = """
        SELECT DISTINCT ON (
            DATE_TRUNC('month', tx_timestamp)
        )
            DATE_TRUNC('month', tx_timestamp)::date AS month,
            balance_after_eur AS balance_eur
        FROM transactions
        WHERE customer_id = %s
          AND tx_date >= (
              DATE_TRUNC('month', CURRENT_DATE)
              - (%s - 1) * INTERVAL '1 month'
          )
        ORDER BY
            DATE_TRUNC('month', tx_timestamp),
            tx_timestamp DESC,
            id DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id, months))
            return cur.fetchall()

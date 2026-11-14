
from datetime import date

from coach.database.connection import get_connection
from coach.spending_baskets import (
    CONSUMPTION_TRANSACTION_TYPES,
    EXCLUDED_FROM_CONSUMPTION,
    UNCLASSIFIED_FINANCIAL_FLOW_NOTES,
    salary_sweep_info,
    summarize_baskets,
)


def _validate_customer_and_dates(
    customer_id: str,
    start_date: date,
    end_date: date,
) -> None:
    if not customer_id:
        raise ValueError("customer_id is required")

    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")


def spending_by_category(
    customer_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Return a customer's spending grouped by category.

    Only consumption counts as spending: rows whose transaction_type is in
    CONSUMPTION_TRANSACTION_TYPES. Salary sweeps and investment flows are
    never included (see financial_flows for those).
    Dates are inclusive.
    """
    _validate_customer_and_dates(customer_id, start_date, end_date)

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
          AND transaction_type = ANY(%s)
        GROUP BY category
        ORDER BY total_spending_eur DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    customer_id,
                    start_date,
                    end_date,
                    CONSUMPTION_TRANSACTION_TYPES,
                ),
            )
            return cur.fetchall()


def financial_flows(
    customer_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Return money moving in and out that is not consumption, per type.

    Covers salary, other income, salary sweeps and investment deposits and
    withdrawals. ``net_amount_eur`` is signed: positive is money in, negative
    is money out. Dates are inclusive.
    """
    _validate_customer_and_dates(customer_id, start_date, end_date)

    query = """
        SELECT
            transaction_type,
            SUM(tx_amount_eur) AS net_amount_eur,
            COUNT(*) AS transaction_count
        FROM transactions
        WHERE customer_id = %s
          AND tx_date >= %s
          AND tx_date <= %s
          AND transaction_type = ANY(%s)
        GROUP BY transaction_type
        ORDER BY transaction_type;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    customer_id,
                    start_date,
                    end_date,
                    EXCLUDED_FROM_CONSUMPTION,
                ),
            )
            return cur.fetchall()


def basket_summary(
    customer_id: str,
    start_date: date,
    end_date: date,
    essentiality_by_category: dict | None = None,
) -> dict:
    """
    Return a customer's consumption grouped into the spending baskets.

    The result has ``baskets`` (with totals, shares and per-category
    breakdown), ``total_spending_eur``, and ``financial_flows``: income,
    salary sweeps and investment movements, reported separately so they are
    visible but never counted as spending. ``has_salary_sweep``,
    ``swept_share_of_salary_pct`` and ``salary_sweep_note`` warn when salary
    leaves the account, which can hide mandatory costs.
    """
    category_rows = spending_by_category(customer_id, start_date, end_date)
    flow_rows = financial_flows(customer_id, start_date, end_date)

    summary = summarize_baskets(category_rows, essentiality_by_category)
    summary["financial_flows"] = [
        {
            "transaction_type": row["transaction_type"],
            "net_amount_eur": round(float(row["net_amount_eur"]), 2),
            "transaction_count": row["transaction_count"],
            "note": UNCLASSIFIED_FINANCIAL_FLOW_NOTES.get(
                row["transaction_type"]
            ),
        }
        for row in flow_rows
    ]
    summary.update(salary_sweep_info(flow_rows))
    summary["period"] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    return summary


def monthly_balance_trend(
    customer_id: str,
    months: int = 6,
) -> list[dict]:
    """
    Return the latest recorded transaction balance
    for each month, for one customer.

    The window ends at the customer's most recent transaction month, not
    today's date, so it still works when the data stops before the present
    (the dataset ends in September 2026). It covers that month and the
    ``months - 1`` months before it; months with no transactions are omitted.
    """
    if not customer_id:
        raise ValueError("customer_id is required")

    if not 1 <= months <= 24:
        raise ValueError("months must be between 1 and 24")

    query = """
        WITH latest AS (
            SELECT DATE_TRUNC('month', MAX(tx_date))::date AS latest_month
            FROM transactions
            WHERE customer_id = %s
        )
        SELECT DISTINCT ON (
            DATE_TRUNC('month', t.tx_timestamp)
        )
            DATE_TRUNC('month', t.tx_timestamp)::date AS month,
            t.balance_after_eur AS balance_eur
        FROM transactions AS t
        CROSS JOIN latest
        WHERE t.customer_id = %s
          AND t.tx_date >= (
              latest.latest_month
              - (%s - 1) * INTERVAL '1 month'
          )
        ORDER BY
            DATE_TRUNC('month', t.tx_timestamp),
            t.tx_timestamp DESC,
            t.id DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id, customer_id, months))
            return cur.fetchall()

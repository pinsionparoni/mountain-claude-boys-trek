
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


def consumption_transactions(
    customer_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Return a customer's individual consumption transactions in a period.

    Rows have ``tx_date``, ``category``, ``mcc_code`` (None for non-card
    payments) and ``amount_eur``: money out as a positive number. Only
    CONSUMPTION_TRANSACTION_TYPES count. A customer has about 30 a month, so
    fetching them lets coach/spending_baskets.py classify each one by merchant
    type and size. Dates are inclusive.
    """
    _validate_customer_and_dates(customer_id, start_date, end_date)

    query = """
        SELECT
            tx_date,
            COALESCE(category, 'Uncategorized') AS category,
            mcc_code,
            -tx_amount_eur AS amount_eur
        FROM transactions
        WHERE customer_id = %s
          AND tx_date >= %s
          AND tx_date <= %s
          AND tx_amount_eur < 0
          AND transaction_type = ANY(%s)
        ORDER BY tx_date, id;
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


def list_transactions(
    customer_id: str,
    start_date: date,
    end_date: date,
    category: str | None = None,
    order: str = "largest",
    limit: int = 20,
) -> list[dict]:
    """
    Return a customer's individual transactions: the largest money out first,
    or the latest first (``order="latest"``). Optionally one category only.

    Rows have ``tx_timestamp``, ``category``, ``transaction_type``,
    ``mcc_code``, ``amount_eur`` (signed, negative is money out) and
    ``balance_after_eur``. Dates are inclusive; ``limit`` is 1 to 50.
    """
    _validate_customer_and_dates(customer_id, start_date, end_date)

    if order not in ("largest", "latest"):
        raise ValueError('order must be "largest" or "latest"')
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")

    # Both ORDER BY clauses are fixed strings, never user input.
    order_by = "tx_amount_eur ASC" if order == "largest" else "tx_timestamp DESC, id DESC"
    query = f"""
        SELECT
            tx_timestamp,
            category,
            transaction_type,
            mcc_code,
            tx_amount_eur AS amount_eur,
            balance_after_eur
        FROM transactions
        WHERE customer_id = %s
          AND tx_date >= %s
          AND tx_date <= %s
          AND (%s::text IS NULL OR category = %s)
        ORDER BY {order_by}
        LIMIT %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (customer_id, start_date, end_date, category, category, limit),
            )
            return cur.fetchall()


def basket_summary(
    customer_id: str,
    start_date: date,
    end_date: date,
    basket_overrides: dict | None = None,
) -> dict:
    """
    Return a customer's consumption grouped into the spending baskets.

    The result has ``baskets`` (with labels, totals, shares and a
    per-category, per-merchant-type breakdown), ``total_spending_eur``,
    ``unusual_purchases`` and ``financial_flows``: income,
    salary sweeps and investment movements, reported separately so they are
    visible but never counted as spending. ``has_salary_sweep``,
    ``swept_share_of_salary_pct`` and ``salary_sweep_note`` warn when salary
    leaves the account, which can hide mandatory costs.
    """
    transactions = consumption_transactions(customer_id, start_date, end_date)
    flow_rows = financial_flows(customer_id, start_date, end_date)

    summary = summarize_baskets(transactions, basket_overrides)
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
    as_of: date | None = None,
) -> list[dict]:
    """
    Return the latest recorded transaction balance
    for each month, for one customer.

    The window ends at the customer's most recent transaction month, not
    today's date, so it still works when the data stops before the present
    (the dataset ends in September 2026). It covers that month and the
    ``months - 1`` months before it; months with no transactions are omitted.
    With ``as_of``, transactions after that date are ignored (the coach's
    "today" in a demo).
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
              AND (%s::date IS NULL OR tx_date <= %s)
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
          AND (%s::date IS NULL OR t.tx_date <= %s)
        ORDER BY
            DATE_TRUNC('month', t.tx_timestamp),
            t.tx_timestamp DESC,
            t.id DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (customer_id, as_of, as_of, customer_id, months, as_of, as_of),
            )
            return cur.fetchall()


def customer_profile(customer_id: str) -> dict:
    """
    Return the facts the coach's system prompt needs about one customer.

    ``age``, ``postal_code``, ``data_from`` / ``data_to`` (first and last
    transaction date, ISO strings) and ``balance_eur``: the balance after
    the customer's most recent transaction.
    """
    if not customer_id:
        raise ValueError("customer_id is required")

    query = """
        SELECT
            c.age,
            c.postal_code,
            MIN(t.tx_date) AS data_from,
            MAX(t.tx_date) AS data_to,
            (
                SELECT balance_after_eur
                FROM transactions
                WHERE customer_id = %s
                ORDER BY tx_timestamp DESC, id DESC
                LIMIT 1
            ) AS balance_eur
        FROM customers AS c
        JOIN transactions AS t USING (customer_id)
        WHERE c.customer_id = %s
        GROUP BY c.age, c.postal_code;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id, customer_id))
            row = cur.fetchone()

    if row is None:
        raise ValueError(f"Unknown customer {customer_id}")

    return {
        "customer_id": customer_id,
        "age": row["age"],
        "postal_code": row["postal_code"],
        "data_from": row["data_from"].isoformat(),
        "data_to": row["data_to"].isoformat(),
        "balance_eur": round(float(row["balance_eur"]), 2),
    }


def monthly_flows(
    customer_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Return non-consumption money movements per calendar month and type.

    Rows have ``month`` (first day of the month), ``transaction_type`` and
    ``net_amount_eur`` (signed: positive is money in). Covers the same types
    as ``financial_flows``: salary, other income, salary sweeps and
    investments. Dates are inclusive.
    """
    _validate_customer_and_dates(customer_id, start_date, end_date)

    query = """
        SELECT
            DATE_TRUNC('month', tx_date)::date AS month,
            transaction_type,
            SUM(tx_amount_eur) AS net_amount_eur
        FROM transactions
        WHERE customer_id = %s
          AND tx_date >= %s
          AND tx_date <= %s
          AND transaction_type = ANY(%s)
        GROUP BY 1, 2
        ORDER BY 1, 2;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (customer_id, start_date, end_date, EXCLUDED_FROM_CONSUMPTION),
            )
            return cur.fetchall()


def salary_dates(
    customer_id: str,
    start_date: date,
    end_date: date,
) -> list[date]:
    """Return the dates the customer was paid salary, oldest first. Dates are inclusive."""
    _validate_customer_and_dates(customer_id, start_date, end_date)

    query = """
        SELECT tx_date
        FROM transactions
        WHERE customer_id = %s
          AND tx_date >= %s
          AND tx_date <= %s
          AND transaction_type = 'salary'
        ORDER BY tx_date;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id, start_date, end_date))
            return [row["tx_date"] for row in cur.fetchall()]


def balance_as_of(customer_id: str, day: date) -> float | None:
    """
    Return the account balance at the end of ``day``: the balance after the
    customer's last transaction on or before it, or None if there is none.
    """
    if not customer_id:
        raise ValueError("customer_id is required")

    query = """
        SELECT balance_after_eur
        FROM transactions
        WHERE customer_id = %s
          AND tx_date <= %s
        ORDER BY tx_timestamp DESC, id DESC
        LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id, day))
            row = cur.fetchone()

    return round(float(row["balance_after_eur"]), 2) if row else None

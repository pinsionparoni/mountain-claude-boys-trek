
import json
from datetime import date
from functools import lru_cache

from coach.database.connection import get_connection
from coach.spending_baskets import (
    ANY_CATEGORY,
    CONSUMPTION_TRANSACTION_TYPES,
    EXCLUDED_FROM_CONSUMPTION,
    UNCLASSIFIED,
    UNCLASSIFIED_FINANCIAL_FLOW_NOTES,
    basket_lookup,
    classify_purchase,
    is_large_purchase,
    large_purchase_thresholds,
    merchant_type,
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


def recent_purchases(
    customer_id: str,
    until: date,
    limit: int = 30,
) -> list[dict]:
    """
    Return a customer's latest card purchases up to ``until``, newest first:
    the "receipts" in the app.

    Only ``purchase`` transactions (shops, restaurants, travel...), not rent
    or utility bills. Each row has ``timestamp`` (ISO), ``category``,
    ``merchant_type`` (as in spending_baskets.MERCHANT_TYPES, "other" when
    unknown), ``basket`` (by the same rules as basket_summary),
    ``amount_eur`` (money out, positive) and ``unusual`` (a large one-off
    purchase). ``limit`` is 1 to 100.
    """
    if not customer_id:
        raise ValueError("customer_id is required")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    query = """
        SELECT
            tx_timestamp,
            COALESCE(category, 'Uncategorized') AS category,
            mcc_code,
            -tx_amount_eur AS amount_eur
        FROM transactions
        WHERE customer_id = %s
          AND tx_date <= %s
          AND transaction_type = 'purchase'
          AND tx_amount_eur < 0
        ORDER BY tx_timestamp DESC, id DESC
        LIMIT %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (customer_id, until, limit))
            rows = cur.fetchall()

    return [
        {
            "timestamp": row["tx_timestamp"].isoformat(),
            "category": row["category"],
            "merchant_type": merchant_type(row["mcc_code"], row["category"]),
            "basket": classify_purchase(row["category"], row["mcc_code"], row["amount_eur"]),
            "amount_eur": round(float(row["amount_eur"]), 2),
            "unusual": is_large_purchase(row["category"], row["amount_eur"]),
        }
        for row in rows
    ]


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


# Memory for the population query's sort; the server has 1 GB in all and is
# shared by the team, so this stays modest.
POPULATION_WORK_MEM = "32MB"


@lru_cache(maxsize=4)
def population_spending(
    start_date: date,
    end_date: date,
) -> tuple[dict, ...]:
    """
    Return every customer's age and spending in a period, per category and
    per basket: the peer population for "what kind of spender am I?".

    One row per customer (all 5,100), as ``{"customer_id", "age",
    "spending": {category: total_eur}, "baskets": {basket_key: total_eur}}``.
    A category or basket the customer did not spend on is absent: callers
    must count it as 0 EUR, not leave the customer out, or the peer medians
    come out too high. Spending means the same as in ``spending_by_category``
    (consumption only), and each purchase is placed in a basket by the same
    rules as ``basket_summary`` (via ``spending_baskets.basket_lookup``,
    without any customer's own overrides). Dates are inclusive.

    This scans the whole population (a 12-month period takes several
    seconds against Aiven), so results are cached per period: the dataset never
    changes while the app runs. Treat the result as read-only.

    Privacy: this is other customers' data. Only aggregates computed from it
    (medians, percentile ranks) may reach the coach, never these rows.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    # The basket rules arrive as a lookup table generated from
    # coach/spending_baskets.py, so SQL holds no copy of them. A purchase's
    # key is category|mcc|L or S (large or not); an MCC missing from the table
    # falls back to the key without one, as classify_purchase does.
    # Results are packed into JSON, one row per customer, to keep the
    # transfer small.
    query = """
        WITH lookup AS (
            SELECT key, value AS basket FROM jsonb_each_text(%(lookup)s::jsonb)
        ),
        thresholds AS (
            SELECT key AS category, value::numeric AS large_from
            FROM jsonb_each_text(%(thresholds)s::jsonb)
        ),
        grouped AS (
            -- Add up first, classify after: every purchase with the same
            -- customer, category, MCC and size lands in the same basket, and
            -- ~200k groups fit the server's small work_mem where 1.7M
            -- individual purchases spilled to disk (20 s instead of 7 s).
            SELECT
                t.customer_id,
                COALESCE(t.category, 'Uncategorized') AS category,
                COALESCE(t.mcc_code, '') AS mcc_code,
                CASE WHEN -t.tx_amount_eur >= th.large_from THEN 'L' ELSE 'S' END AS size,
                SUM(-t.tx_amount_eur) AS amount_eur
            FROM transactions AS t
            LEFT JOIN thresholds AS th ON th.category = t.category
            WHERE t.tx_date >= %(start)s
              AND t.tx_date <= %(end)s
              AND t.tx_amount_eur < 0
              AND t.transaction_type = ANY(%(types)s)
            GROUP BY 1, 2, 3, 4
        ),
        classified AS (
            SELECT
                g.customer_id,
                g.category,
                g.amount_eur,
                COALESCE(exact.basket, no_mcc.basket, any_category.basket, %(unclassified)s) AS basket
            FROM grouped AS g
            LEFT JOIN lookup AS exact
                ON exact.key = g.category || '|' || g.mcc_code || '|' || g.size
            LEFT JOIN lookup AS no_mcc
                ON no_mcc.key = g.category || '||' || g.size
            LEFT JOIN lookup AS any_category
                ON any_category.key = %(any_category)s || '|' || g.mcc_code || '|' || g.size
        ),
        by_category AS (
            SELECT customer_id, jsonb_object_agg(category, total) AS spending
            FROM (
                SELECT customer_id, category, ROUND(SUM(amount_eur), 2) AS total
                FROM classified GROUP BY 1, 2
            ) AS t
            GROUP BY customer_id
        ),
        by_basket AS (
            SELECT customer_id, jsonb_object_agg(basket, total) AS baskets
            FROM (
                SELECT customer_id, basket, ROUND(SUM(amount_eur), 2) AS total
                FROM classified GROUP BY 1, 2
            ) AS t
            GROUP BY customer_id
        )
        SELECT
            c.customer_id,
            c.age,
            COALESCE(bc.spending, '{}'::jsonb) AS spending,
            COALESCE(bb.baskets, '{}'::jsonb) AS baskets
        FROM customers AS c
        LEFT JOIN by_category AS bc USING (customer_id)
        LEFT JOIN by_basket AS bb USING (customer_id)
        ORDER BY c.customer_id;
    """
    params = {
        "start": start_date,
        "end": end_date,
        "types": CONSUMPTION_TRANSACTION_TYPES,
        "lookup": json.dumps(basket_lookup()),
        "thresholds": json.dumps(
            {k: str(v) for k, v in large_purchase_thresholds().items()}
        ),
        "unclassified": UNCLASSIFIED,
        "any_category": ANY_CATEGORY,
    }

    with get_connection() as conn:
        # Aiven's default work_mem (2 MB) makes the grouping sort spill to
        # disk: ~17 s instead of ~8 s. SET LOCAL raises it for this one
        # transaction only; the session and the server keep their settings.
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(f"SET LOCAL work_mem = '{POPULATION_WORK_MEM}'")
            cur.execute(query, params)
            rows = cur.fetchall()

    def floats(totals):
        return {key: round(float(total), 2) for key, total in totals.items()}

    return tuple(
        {
            "customer_id": row["customer_id"],
            "age": row["age"],
            "spending": floats(row["spending"]),
            "baskets": floats(row["baskets"]),
        }
        for row in rows
    )

"""Read-only queries over one customer's transactions, exposed to the coach as tools.

Every tool is bound to a single customer_id chosen by the app, never by the model,
so the model can only ever see the current customer's data.
"""

import json
import os
from datetime import date

import psycopg

# Draft mapping of categories to the three baskets from the S-Pankki brief.
# Category-level, so e.g. all of Transportation counts as regular even though
# taxis are arguably everyday spending. Revisit with the team / S-Bank mentors.
BASKETS = {
    "Housing": "mandatory_regular",
    "Utilities": "mandatory_regular",
    "Groceries": "mandatory_regular",
    "Transportation": "mandatory_regular",
    "Health": "mandatory_irregular",
    "Home & Tech": "mandatory_irregular",
    "Restaurants": "everyday",
    "Entertainment": "everyday",
    "Lifestyle": "everyday",
    "Travel": "everyday",
}
# Not spending: money in, money set aside, or moved between accounts.
NON_SPENDING = {
    "Salary": "income",
    "Other Income": "income",
    "Invest Withdraw": "income",
    "Invest Deposit": "savings",
    "Salary Sweep": "transfer",
}
# Merchant category codes (ISO 18245) that appear in the dataset.
MERCHANT_TYPES = {
    "4111": "public transport", "4121": "taxi", "4511": "airline", "4722": "travel agency",
    "5200": "home supply store", "5251": "hardware store", "5411": "supermarket",
    "5422": "butcher", "5451": "dairy shop", "5499": "convenience / specialty food",
    "5541": "service station", "5542": "fuel", "5651": "clothing", "5691": "clothing",
    "5712": "furniture", "5732": "electronics", "5734": "software", "5812": "restaurant",
    "5813": "bar", "5814": "fast food", "5912": "pharmacy", "5941": "sporting goods",
    "5942": "bookstore", "5945": "hobby / toys", "5999": "other retail", "7011": "hotel",
    "7512": "car rental", "7523": "parking", "7832": "cinema", "7922": "tickets / events",
    "7991": "attractions", "7996": "amusement park", "7999": "recreation", "8011": "doctor",
    "8021": "dentist", "8099": "medical services",
}

_conn = None


def _query(sql, params):
    """Run a read-only query, reconnecting once if the connection dropped."""
    global _conn
    for attempt in range(2):
        try:
            if _conn is None or _conn.closed:
                _conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True,
                                        options="-c default_transaction_read_only=on")
            with _conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        except psycopg.OperationalError:
            _conn = None
            if attempt:
                raise


def _eur(value):
    return round(float(value or 0), 2)


def _date(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a date like 2026-09-01, got {value!r}")


def customer_profile(customer_id):
    """Facts for the system prompt: age, data range and current balance."""
    rows = _query(
        """SELECT c.age, c.postal_code, min(t.tx_date), max(t.tx_date),
                  (SELECT balance_after_eur FROM transactions
                   WHERE customer_id = %(c)s ORDER BY tx_timestamp DESC, id DESC LIMIT 1)
           FROM customers c JOIN transactions t USING (customer_id)
           WHERE c.customer_id = %(c)s GROUP BY c.age, c.postal_code""",
        {"c": customer_id})
    if not rows:
        raise ValueError(f"Unknown customer {customer_id}")
    age, postal_code, first, last, balance = rows[0]
    return {"customer_id": customer_id, "age": age, "postal_code": postal_code,
            "data_from": first.isoformat(), "data_to": last.isoformat(), "balance_eur": _eur(balance)}


def spending_summary(customer_id, args):
    start, end = _date(args.get("start_date"), "start_date"), _date(args.get("end_date"), "end_date")
    category = args.get("category")
    if category:
        rows = _query(
            """SELECT mcc_code, count(*), -sum(tx_amount_eur) FROM transactions
               WHERE customer_id = %s AND tx_date BETWEEN %s AND %s AND category = %s
               GROUP BY mcc_code ORDER BY 3 DESC""",
            (customer_id, start, end, category))
        by_type = [{"merchant_type": MERCHANT_TYPES.get(mcc, "other") if mcc else "direct payment",
                    "transactions": n, "spent_eur": _eur(total)} for mcc, n, total in rows]
        return {"period": [start.isoformat(), end.isoformat()], "category": category,
                "basket": BASKETS.get(category, NON_SPENDING.get(category)),
                "spent_eur": _eur(sum(r["spent_eur"] for r in by_type)), "by_merchant_type": by_type}

    rows = _query(
        """SELECT category, count(*), sum(tx_amount_eur) FROM transactions
           WHERE customer_id = %s AND tx_date BETWEEN %s AND %s GROUP BY category""",
        (customer_id, start, end))
    baskets = {b: {"spent_eur": 0.0, "categories": {}} for b in set(BASKETS.values())}
    other = {"income": 0.0, "savings": 0.0, "transfer": 0.0}
    for cat, n, total in rows:
        if cat in BASKETS:
            basket = baskets[BASKETS[cat]]
            basket["spent_eur"] = _eur(basket["spent_eur"] - float(total))
            basket["categories"][cat] = {"transactions": n, "spent_eur": _eur(-total)}
        else:
            kind = NON_SPENDING.get(cat, "transfer")
            other[kind] = _eur(other[kind] + abs(float(total)))
    return {"period": [start.isoformat(), end.isoformat()],
            "total_spent_eur": _eur(sum(b["spent_eur"] for b in baskets.values())),
            "baskets": baskets,
            "income_eur": other["income"], "moved_to_savings_eur": other["savings"],
            "transfers_out_eur": other["transfer"]}


def monthly_overview(customer_id, args):
    months = max(1, min(int(args.get("months", 6)), 24))
    rows = _query(
        """WITH last AS (SELECT date_trunc('month', max(tx_date)) m FROM transactions WHERE customer_id = %(c)s)
           SELECT date_trunc('month', tx_date)::date AS month, category, sum(tx_amount_eur)
           FROM transactions, last
           WHERE customer_id = %(c)s AND tx_date >= last.m - make_interval(months => %(n)s - 1)
           GROUP BY 1, 2 ORDER BY 1""",
        {"c": customer_id, "n": months})
    out = {}
    for month, cat, total in rows:
        m = out.setdefault(month.isoformat()[:7], {"income_eur": 0.0, "spent_eur": 0.0,
                                                   "mandatory_regular_eur": 0.0, "mandatory_irregular_eur": 0.0,
                                                   "everyday_eur": 0.0, "moved_to_savings_eur": 0.0,
                                                   "end_balance_eur": None})
        if cat in BASKETS:
            m[f"{BASKETS[cat]}_eur"] = _eur(m[f"{BASKETS[cat]}_eur"] - float(total))
            m["spent_eur"] = _eur(m["spent_eur"] - float(total))
        elif NON_SPENDING.get(cat) == "income":
            m["income_eur"] = _eur(m["income_eur"] + float(total))
        elif NON_SPENDING.get(cat) == "savings":
            m["moved_to_savings_eur"] = _eur(m["moved_to_savings_eur"] - float(total))
    # End-of-month balance: the balance after the month's last transaction.
    balances = _query(
        """SELECT DISTINCT ON (date_trunc('month', tx_date)) date_trunc('month', tx_date)::date, balance_after_eur
           FROM transactions WHERE customer_id = %s
           ORDER BY date_trunc('month', tx_date), tx_timestamp DESC, id DESC""",
        (customer_id,))
    for month, balance in balances:
        key = month.isoformat()[:7]
        if key in out:
            out[key]["end_balance_eur"] = _eur(balance)
    return {"months": out}


def list_transactions(customer_id, args):
    start, end = _date(args.get("start_date"), "start_date"), _date(args.get("end_date"), "end_date")
    order = "tx_amount_eur ASC" if args.get("order", "largest") == "largest" else "tx_timestamp DESC"
    limit = max(1, min(int(args.get("limit", 20)), 50))
    params = [customer_id, start, end]
    where = ""
    if args.get("category"):
        where = "AND category = %s"
        params.append(args["category"])
    rows = _query(
        f"""SELECT tx_date, category, mcc_code, tx_amount_eur, balance_after_eur FROM transactions
            WHERE customer_id = %s AND tx_date BETWEEN %s AND %s {where}
            ORDER BY {order} LIMIT {limit}""",
        params)
    return {"transactions": [
        {"date": d.isoformat(), "category": cat,
         "merchant_type": MERCHANT_TYPES.get(mcc) if mcc else None,
         "amount_eur": _eur(amount), "balance_after_eur": _eur(balance)}
        for d, cat, mcc, amount, balance in rows]}


CATEGORIES = sorted([*BASKETS, *NON_SPENDING])
_PERIOD = {
    "start_date": {"type": "string", "description": "First day, inclusive, as YYYY-MM-DD."},
    "end_date": {"type": "string", "description": "Last day, inclusive, as YYYY-MM-DD."},
}
_CATEGORY = {"type": "string", "enum": CATEGORIES}


def load_tools(customer_id):
    """Database tools bound to one customer."""
    from coach.tools import Tool

    def wrap(fn):
        def run(args):
            try:
                return json.dumps(fn(customer_id, args or {}), ensure_ascii=False)
            except ValueError as e:
                return f"Error: {e}"
        return run

    return [
        Tool(
            name="spending_summary",
            description=(
                "The customer's spending for a date range, split into the three baskets "
                "(mandatory_regular, mandatory_irregular, everyday) with per-category totals, plus income, "
                "money moved to savings and transfers. Pass a category to instead get that category broken "
                "down by merchant type (e.g. Transportation -> taxi, fuel, parking, public transport)."),
            parameters={"type": "object", "properties": {**_PERIOD, "category": _CATEGORY},
                        "required": ["start_date", "end_date"]},
            run=wrap(spending_summary),
        ),
        Tool(
            name="monthly_overview",
            description=(
                "Month-by-month income, spending per basket, money moved to savings and end-of-month balance "
                "for the customer's most recent months. Use for trends, averages, and what is safe to spend."),
            parameters={"type": "object", "properties": {
                "months": {"type": "integer", "minimum": 1, "maximum": 24,
                           "description": "How many recent months, default 6."}}},
            run=wrap(monthly_overview),
        ),
        Tool(
            name="list_transactions",
            description="Individual transactions in a date range, optionally for one category: the largest or the latest.",
            parameters={"type": "object", "properties": {
                **_PERIOD, "category": _CATEGORY,
                "order": {"type": "string", "enum": ["largest", "latest"], "description": "Default largest."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Default 20."}},
                "required": ["start_date", "end_date"]},
            run=wrap(list_transactions),
        ),
    ]

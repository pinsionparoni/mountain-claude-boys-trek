"""
Tests for coach/database/queries.py that need no real database.

A fake connection records the SQL and parameters and returns canned rows, so
these tests check what is asked of the database (and how results are shaped),
not what PostgreSQL returns. Confirm the SQL itself with the live check in
scripts/audits/check_queries.py.

    python -m pytest tests/test_database_queries.py
"""

import types
from datetime import date
from decimal import Decimal

import pytest

# tests/conftest.py stubs psycopg and dotenv if they are not installed.
from coach.database import queries
from coach.spending_baskets import (
    CONSUMPTION_TRANSACTION_TYPES,
    EXCLUDED_FROM_CONSUMPTION,
)

START = date(2026, 1, 1)
END = date(2026, 3, 31)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        self.calls.append((query, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self._cursor


@pytest.fixture
def fake_db(monkeypatch):
    """Queue canned row sets; each get_connection() call uses the next one."""
    cursors = []
    queued = []

    def queue(*row_sets):
        queued.extend(row_sets)

    def get_connection():
        cursor = FakeCursor(queued.pop(0))
        cursors.append(cursor)
        return FakeConnection(cursor)

    monkeypatch.setattr(queries, "get_connection", get_connection)
    return types.SimpleNamespace(queue=queue, cursors=cursors)


# --------------------------------------------------------------------------
# spending_by_category
# --------------------------------------------------------------------------

def test_spending_only_counts_known_consumption_types(fake_db):
    fake_db.queue([])
    queries.spending_by_category("CUST1", START, END)

    sql, params = fake_db.cursors[0].calls[0]
    assert "transaction_type = ANY(%s)" in sql
    assert params == ("CUST1", START, END, list(CONSUMPTION_TRANSACTION_TYPES))
    # Regression: salary sweeps were once counted as spending.
    assert "salary_sweep" not in params[3]
    assert "investment_deposit" not in params[3]


def test_spending_returns_rows_unchanged(fake_db):
    rows = [{"category": "Groceries", "total_spending_eur": 10, "transaction_count": 2}]
    fake_db.queue(rows)
    assert queries.spending_by_category("CUST1", START, END) == rows


@pytest.mark.parametrize(
    "customer_id, start, end",
    [("", START, END), (None, START, END), ("CUST1", END, START)],
)
def test_spending_validates_input(fake_db, customer_id, start, end):
    with pytest.raises(ValueError):
        queries.spending_by_category(customer_id, start, end)
    assert fake_db.cursors == []  # rejected before touching the database


# --------------------------------------------------------------------------
# financial_flows
# --------------------------------------------------------------------------

def test_financial_flows_asks_only_for_non_consumption_types(fake_db):
    fake_db.queue([])
    queries.financial_flows("CUST1", START, END)

    sql, params = fake_db.cursors[0].calls[0]
    assert "transaction_type = ANY(%s)" in sql
    assert params == ("CUST1", START, END, list(EXCLUDED_FROM_CONSUMPTION))
    assert not set(params[3]) & set(CONSUMPTION_TRANSACTION_TYPES)


def test_financial_flows_validates_input(fake_db):
    with pytest.raises(ValueError):
        queries.financial_flows("", START, END)
    with pytest.raises(ValueError):
        queries.financial_flows("CUST1", END, START)


# --------------------------------------------------------------------------
# basket_summary
# --------------------------------------------------------------------------

def test_basket_summary_separates_spending_from_flows(fake_db):
    fake_db.queue(
        [
            {"tx_date": date(2026, 1, 5), "category": "Housing", "mcc_code": None, "amount_eur": 900},
            {"tx_date": date(2026, 1, 9), "category": "Restaurants", "mcc_code": "5812", "amount_eur": 100},
        ],
        [
            {"transaction_type": "salary", "net_amount_eur": 3000, "transaction_count": 3},
            {"transaction_type": "salary_sweep", "net_amount_eur": -250.456, "transaction_count": 3},
        ],
    )

    result = queries.basket_summary("CUST1", START, END)

    # Spending baskets hold consumption only; flows never leak in.
    assert result["total_spending_eur"] == 1000.0
    assert result["baskets"]["regular_essentials"]["total_eur"] == 900.0
    assert result["baskets"]["everyday_spending"]["total_eur"] == 100.0
    assert result["unusual_purchases"] == []

    flows = {f["transaction_type"]: f for f in result["financial_flows"]}
    assert flows["salary"]["net_amount_eur"] == 3000.0
    assert flows["salary"]["note"] is None
    assert flows["salary_sweep"]["net_amount_eur"] == -250.46
    assert "purpose unknown" in flows["salary_sweep"]["note"]

    # 250.456 swept out of 3000 salary = 8.3%.
    assert result["has_salary_sweep"] is True
    assert result["swept_share_of_salary_pct"] == 8.3
    assert "8.3% of salary" in result["salary_sweep_note"]

    assert result["period"] == {"start_date": "2026-01-01", "end_date": "2026-03-31"}


def test_basket_summary_passes_customer_overrides_through(fake_db):
    fake_db.queue(
        [{"tx_date": date(2026, 2, 1), "category": "Health", "mcc_code": "8021", "amount_eur": 300}],
        [],
    )
    result = queries.basket_summary(
        "CUST1", START, END, basket_overrides={"Health": "regular_essentials"}
    )
    assert result["baskets"]["regular_essentials"]["total_eur"] == 300.0
    assert result["baskets"]["unexpected_necessities"]["total_eur"] == 0.0
    assert result["financial_flows"] == []
    assert result["has_salary_sweep"] is False
    assert result["salary_sweep_note"] is None


# --------------------------------------------------------------------------
# monthly_balance_trend
# --------------------------------------------------------------------------

def test_balance_trend_is_anchored_to_the_customers_data_not_today(fake_db):
    fake_db.queue([])
    queries.monthly_balance_trend("CUST1", months=6)

    sql, params = fake_db.cursors[0].calls[0]
    assert "MAX(tx_date)" in sql
    assert "CURRENT_DATE" not in sql
    assert params == ("CUST1", None, None, "CUST1", 6, None, None)


def test_balance_trend_can_stop_at_a_demo_date(fake_db):
    fake_db.queue([])
    queries.monthly_balance_trend("CUST1", months=3, as_of=date(2026, 9, 18))
    _, params = fake_db.cursors[0].calls[0]
    assert params == ("CUST1", date(2026, 9, 18), date(2026, 9, 18), "CUST1", 3,
                      date(2026, 9, 18), date(2026, 9, 18))


@pytest.mark.parametrize("months", [0, 25, -1])
def test_balance_trend_validates_months(fake_db, months):
    with pytest.raises(ValueError):
        queries.monthly_balance_trend("CUST1", months=months)


def test_balance_trend_requires_customer(fake_db):
    with pytest.raises(ValueError):
        queries.monthly_balance_trend("", months=6)


# --------------------------------------------------------------------------
# consumption_transactions, list_transactions, customer_profile
# --------------------------------------------------------------------------

def test_consumption_transactions_only_counts_known_consumption_types(fake_db):
    fake_db.queue([])
    queries.consumption_transactions("CUST1", START, END)
    query, params = fake_db.cursors[0].calls[0]
    assert params == ("CUST1", START, END, CONSUMPTION_TRANSACTION_TYPES)
    assert "-tx_amount_eur AS amount_eur" in query
    assert "mcc_code" in query


def test_consumption_transactions_validates_input(fake_db):
    with pytest.raises(ValueError):
        queries.consumption_transactions("", START, END)
    with pytest.raises(ValueError):
        queries.consumption_transactions("CUST1", END, START)


@pytest.mark.parametrize("order, clause", [("largest", "tx_amount_eur ASC"), ("latest", "tx_timestamp DESC")])
def test_list_transactions_orders_and_filters(fake_db, order, clause):
    fake_db.queue([])
    queries.list_transactions("CUST1", START, END, category="Travel", order=order, limit=5)
    query, params = fake_db.cursors[0].calls[0]
    assert clause in query
    assert params == ("CUST1", START, END, "Travel", "Travel", 5)


@pytest.mark.parametrize("kwargs", [{"order": "random"}, {"limit": 0}, {"limit": 51}])
def test_list_transactions_validates_input(fake_db, kwargs):
    with pytest.raises(ValueError):
        queries.list_transactions("CUST1", START, END, **kwargs)


def test_customer_profile(fake_db):
    fake_db.queue([{"age": 63, "postal_code": "00990", "data_from": date(2024, 10, 3),
                    "data_to": date(2026, 9, 30), "balance_eur": 4723.581}])
    assert queries.customer_profile("CUST00001") == {
        "customer_id": "CUST00001", "age": 63, "postal_code": "00990",
        "data_from": "2024-10-03", "data_to": "2026-09-30", "balance_eur": 4723.58,
    }


def test_customer_profile_unknown_customer(fake_db):
    fake_db.queue([])
    with pytest.raises(ValueError, match="Unknown customer"):
        queries.customer_profile("CUST99999")


def test_monthly_flows_groups_by_month_and_type(fake_db):
    fake_db.queue([])
    queries.monthly_flows("CUST1", START, END)
    query, params = fake_db.cursors[0].calls[0]
    assert "DATE_TRUNC('month', tx_date)" in query
    assert params == ("CUST1", START, END, EXCLUDED_FROM_CONSUMPTION)


def test_salary_dates_returns_plain_dates(fake_db):
    fake_db.queue([{"tx_date": date(2026, 1, 15)}, {"tx_date": date(2026, 2, 27)}])
    assert queries.salary_dates("CUST1", START, END) == [date(2026, 1, 15), date(2026, 2, 27)]


def test_balance_as_of(fake_db):
    fake_db.queue([{"balance_after_eur": Decimal("812.349")}], [])
    assert queries.balance_as_of("CUST1", date(2026, 9, 18)) == 812.35
    assert fake_db.cursors[0].calls[0][1] == ("CUST1", date(2026, 9, 18))
    assert queries.balance_as_of("CUST1", date(2020, 1, 1)) is None


# --- Peer population -------------------------------------------------------


@pytest.fixture
def fresh_population_cache():
    queries.population_spending_by_category.cache_clear()
    yield
    queries.population_spending_by_category.cache_clear()


def test_population_counts_only_consumption_in_the_period(fake_db, fresh_population_cache):
    fake_db.queue([])

    queries.population_spending_by_category(START, END)

    query, params = fake_db.cursors[0].calls[0]
    assert params == (START, END, CONSUMPTION_TRANSACTION_TYPES)
    assert "tx_amount_eur < 0" in query
    # Every customer is returned, including ones with no spending at all.
    assert "FROM customers AS c" in query
    assert "LEFT JOIN spending" in query


def test_population_rows_are_shaped_with_float_totals(fake_db, fresh_population_cache):
    fake_db.queue([
        {"customer_id": "CUST00001", "age": 63,
         "spending": {"Groceries": Decimal("812.40"), "Travel": 99}},
        {"customer_id": "CUST00002", "age": 21, "spending": {}},
    ])

    rows = queries.population_spending_by_category(START, END)

    assert rows == (
        {"customer_id": "CUST00001", "age": 63,
         "spending": {"Groceries": 812.4, "Travel": 99.0}},
        {"customer_id": "CUST00002", "age": 21, "spending": {}},
    )
    assert isinstance(rows[0]["spending"]["Groceries"], float)


def test_population_is_cached_per_period(fake_db, fresh_population_cache):
    fake_db.queue([], [])

    first = queries.population_spending_by_category(START, END)
    again = queries.population_spending_by_category(START, END)
    queries.population_spending_by_category(START, date(2026, 6, 30))

    assert first is again
    assert len(fake_db.cursors) == 2  # one database call per distinct period


def test_population_rejects_reversed_dates(fake_db, fresh_population_cache):
    with pytest.raises(ValueError):
        queries.population_spending_by_category(END, START)
    assert fake_db.cursors == []

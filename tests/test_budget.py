"""
Tests for coach/budget.py (no database: the queries are replaced with fakes).

The fake customer, with today = 2026-03-18:

- Every month Sep 2025 - Feb 2026: rent 900 on the 3rd, utilities 60 on the
  10th, groceries 300, restaurants 200; salary 2000 on the 15th; 100 to
  investments. One dentist bill of 240 in November.
- March so far: rent paid on the 3rd, restaurants 150, groceries 100.
- Balance today: 1500.

Monthly budget: 2000 - 1260 (rent + utilities + groceries) - 20 (240 / 12)
- 100 savings = 620 for everyday spending.

    python -m pytest tests/test_budget.py
"""

from datetime import date
from decimal import Decimal

import pytest

from coach import budget
from coach.database import queries

TODAY = date(2026, 3, 18)
HISTORY = [date(2025, m, 1) for m in (9, 10, 11, 12)] + [date(2026, m, 1) for m in (1, 2)]


def tx(day, category, mcc, amount):
    return {"tx_date": day, "category": category, "mcc_code": mcc, "amount_eur": Decimal(str(amount))}


def customer(today=TODAY, march=None, flows_extra=(), salary_days=None, balance=1500):
    rows = []
    for m in HISTORY:
        rows += [
            tx(m.replace(day=3), "Housing", None, 900),
            tx(m.replace(day=10), "Utilities", None, 60),
            tx(m.replace(day=12), "Groceries", "5411", 300),
            tx(m.replace(day=20), "Restaurants", "5812", 200),
        ]
    rows.append(tx(date(2025, 11, 7), "Health", "8021", 240))
    rows += march if march is not None else [
        tx(date(2026, 3, 3), "Housing", None, 900),
        tx(date(2026, 3, 5), "Restaurants", "5812", 150),
        tx(date(2026, 3, 6), "Groceries", "5411", 100),
    ]
    rows = [r for r in rows if r["tx_date"] <= today]
    flows = [{"month": m, "transaction_type": "salary", "net_amount_eur": Decimal(2000)} for m in HISTORY]
    flows += [{"month": m, "transaction_type": "investment_deposit", "net_amount_eur": Decimal(-100)} for m in HISTORY]
    flows += list(flows_extra)
    paid = salary_days or [date(2025, m, 15) for m in range(3, 13)] + [date(2026, m, 15) for m in (1, 2, 3)]
    return rows, flows, [d for d in paid if d <= today], balance


@pytest.fixture
def fake(monkeypatch):
    def install(rows, flows, paid, balance):
        monkeypatch.setattr(queries, "consumption_transactions",
                            lambda c, start, end: [r for r in rows if start <= r["tx_date"] <= end])
        monkeypatch.setattr(queries, "monthly_flows",
                            lambda c, start, end: [f for f in flows if start <= f["month"] <= end])
        monkeypatch.setattr(queries, "salary_dates", lambda c, start, end: paid)
        monkeypatch.setattr(queries, "balance_as_of", lambda c, day: balance)
    return install


# --------------------------------------------------------------------------
# Monthly budget and this month
# --------------------------------------------------------------------------

def test_monthly_budget_from_the_last_six_months(fake):
    fake(*customer())
    result = budget.safe_to_spend("CUST1", TODAY)

    assert result["history"] == {
        "months": 6, "from": "2025-09-01", "to": "2026-02-28",
        "unexpected_reserve_months": 12, "usual_everyday_spending": 200.0,
    }
    assert result["monthly_budget"] == {
        "monthly_income": 2000.0,
        "regular_essentials": 1260.0,
        "unexpected_reserve": 20.0,
        "savings": 100.0,
        "everyday_budget": 620.0,
        "shortfall": 0.0,
    }


def test_this_month_spreads_the_rest_of_the_everyday_budget(fake):
    fake(*customer())
    month = budget.safe_to_spend("CUST1", TODAY)["this_month"]

    # 620 - 150 = 470 over the 14 days 18-31 March.
    assert month["everyday_spent"] == 150.0
    assert month["remaining"] == 470.0
    assert month["days_left_in_month"] == 14
    assert month["per_week"] == 235.0
    assert month["regular_essentials_spent"] == 1000.0


# --------------------------------------------------------------------------
# Cash check
# --------------------------------------------------------------------------

def test_cash_check_reserves_rent_due_before_payday(fake):
    fake(*customer())
    result = budget.safe_to_spend("CUST1", TODAY)
    cash = result["cash_check"]

    # Next salary 15 April; April's rent (3 April) falls before it.
    assert cash["next_payday"] == "2026-04-15"
    assert cash["usual_payday_of_month"] == 15
    assert cash["days_to_payday"] == 28
    assert cash["rent_due_before_payday"] == 900.0
    # Utilities 60 + other essentials 300 a month, spread over 28 days.
    assert cash["other_essentials_before_payday"] == 331.17
    # 1500 - 900 - 331.17 = 268.83 for 28 days, 67.21 a week.
    assert cash["left_for_everyday_until_payday"] == 268.83
    assert cash["per_week"] == 67.21
    assert cash["enough_cash"] is False

    # The budget would allow 235 this week, but the account only allows 67.21.
    assert result["safe_to_spend_this_week"] == 67.21
    assert result["limited_by"] == "cash"


def test_rent_already_paid_this_month_is_not_reserved_again(fake):
    today = date(2026, 3, 10)
    fake(*customer(today=today))
    cash = budget.safe_to_spend("CUST1", today)["cash_check"]
    assert cash["next_payday"] == "2026-03-15"
    assert cash["rent_due_before_payday"] == 0.0


def test_unpaid_rent_this_month_is_reserved(fake):
    today = date(2026, 3, 2)
    fake(*customer(today=today, march=[]))
    cash = budget.safe_to_spend("CUST1", today)["cash_check"]
    assert cash["next_payday"] == "2026-03-15"
    assert cash["rent_due_before_payday"] == 900.0


def test_plenty_of_cash_means_the_budget_decides(fake):
    fake(*customer(balance=20000))
    result = budget.safe_to_spend("CUST1", TODAY)
    assert result["cash_check"]["enough_cash"] is True
    assert result["safe_to_spend_this_week"] == 235.0
    assert result["limited_by"] == "budget"


def test_without_salary_history_there_is_no_cash_check(fake):
    rows, flows, _, balance = customer()
    fake(rows, flows, [], balance)
    result = budget.safe_to_spend("CUST1", TODAY)
    assert result["cash_check"] is None
    assert result["safe_to_spend_this_week"] == 235.0


def test_salary_sweeps_are_not_available_for_the_budget(fake):
    sweeps = [{"month": m, "transaction_type": "salary_sweep", "net_amount_eur": Decimal(-1500)} for m in HISTORY]
    fake(*customer(flows_extra=sweeps))
    result = budget.safe_to_spend("CUST1", TODAY)
    assert result["has_salary_sweep"] is True
    assert result["monthly_budget"]["monthly_income"] == 500.0
    assert result["monthly_budget"]["everyday_budget"] == 0.0
    assert result["monthly_budget"]["shortfall"] == 880.0


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def test_next_payday_uses_the_most_common_day_and_clamps_to_month_end():
    paid = [date(2026, 1, 31), date(2025, 12, 31), date(2025, 11, 15)]
    assert budget.next_payday(paid, date(2026, 2, 10)) == (date(2026, 2, 28), 31)
    assert budget.next_payday(paid, date(2026, 2, 28)) == (date(2026, 3, 31), 31)
    assert budget.next_payday([], TODAY) == (None, None)


def test_coach_today(monkeypatch):
    data_to = date(2026, 9, 30)
    monkeypatch.delenv("COACH_TODAY", raising=False)
    assert budget.coach_today(data_to) == data_to
    monkeypatch.setenv("COACH_TODAY", "2026-09-18")
    assert budget.coach_today(data_to) == date(2026, 9, 18)
    monkeypatch.setenv("COACH_TODAY", "2027-01-01")  # never after the data ends
    assert budget.coach_today(data_to) == data_to
    monkeypatch.setenv("COACH_TODAY", "18.9.2026")
    with pytest.raises(ValueError, match="COACH_TODAY"):
        budget.coach_today(data_to)

"""
Unit tests for coach/calculations.py.

These need no database, no network and no AI model. Run them with:

    python -m pytest tests/test_calculations.py

(Run this file by name: other files in tests/ are audit scripts that query
the live database when imported.)

Expected values are worked out by hand in the comments.
"""

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from coach import calculations
from coach.calculations import (
    average_monthly,
    prorate_monthly,
    safe_to_save,
    safe_to_spend,
    what_if_reduce,
    what_if_reduce_many,
)


# --------------------------------------------------------------------------
# Independence from the database and AI clients
# --------------------------------------------------------------------------

def test_module_imports_only_standard_library():
    source = Path(calculations.__file__).read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])

    assert imported <= {"decimal", "typing"}


# --------------------------------------------------------------------------
# average_monthly / prorate_monthly
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "totals, expected",
    [
        ([100, 200, 300], 200.0),
        ([100, 101], 100.5),
        ([0.1, 0.2], 0.15),
        ([1, 2, 2], 1.67),  # 5 / 3 = 1.666...
        ([Decimal("10.50")], 10.5),
    ],
)
def test_average_monthly(totals, expected):
    assert average_monthly(totals) == expected


def test_average_monthly_rejects_empty():
    with pytest.raises(ValueError):
        average_monthly([])


@pytest.mark.parametrize(
    "monthly, days, days_in_month, expected",
    [
        (300, 10, 30, 100.0),
        (100, 7, 30, 23.33),  # 700 / 30 = 23.333...
        (100, 0, 30, 0.0),
        (100, 15, 31, 48.39),  # 1500 / 31 = 48.387...
    ],
)
def test_prorate_monthly(monthly, days, days_in_month, expected):
    assert prorate_monthly(monthly, days, days_in_month) == expected


def test_prorate_monthly_rejects_bad_input():
    with pytest.raises(ValueError):
        prorate_monthly(-1, 5)
    with pytest.raises(ValueError):
        prorate_monthly(100, -1)
    with pytest.raises(ValueError):
        prorate_monthly(100, 5, days_in_month=0)


# --------------------------------------------------------------------------
# safe_to_spend
# --------------------------------------------------------------------------

def test_safe_to_spend_basic():
    # 1000 + 0 - 400 - 100 - 100 = 400 available over 10 days.
    result = safe_to_spend(
        current_balance=1000,
        days_remaining=10,
        committed_expenses=400,
        irregular_reserve=100,
        buffer=100,
    )
    assert result["safe_total"] == 400.0
    assert result["per_day"] == 40.0
    assert result["per_week"] == 280.0  # 7 days * 40
    assert result["shortfall"] == 0.0


def test_safe_to_spend_counts_income_inside_horizon():
    # 100 + 1500 - 600 = 1000 over 5 days -> 200/day, 5 days in the week.
    result = safe_to_spend(
        current_balance=100,
        days_remaining=5,
        expected_income=1500,
        committed_expenses=600,
    )
    assert result["safe_total"] == 1000.0
    assert result["per_day"] == 200.0
    assert result["per_week"] == 1000.0


def test_safe_to_spend_week_is_capped_by_horizon():
    # 400 over 3 days: the "week" allowance is just the 3 days = 400.
    result = safe_to_spend(
        current_balance=500,
        days_remaining=3,
        committed_expenses=100,
    )
    assert result["per_day"] == 133.33
    assert result["per_week"] == 400.0


def test_safe_to_spend_reports_shortfall_instead_of_negative():
    # 100 - 300 = -200: nothing safe to spend, 200 short.
    result = safe_to_spend(
        current_balance=100,
        days_remaining=5,
        committed_expenses=300,
    )
    assert result["safe_total"] == 0.0
    assert result["per_day"] == 0.0
    assert result["per_week"] == 0.0
    assert result["shortfall"] == 200.0


def test_safe_to_spend_overdrawn_account():
    result = safe_to_spend(current_balance=-50, days_remaining=7)
    assert result["safe_total"] == 0.0
    assert result["shortfall"] == 50.0


def test_safe_to_spend_echoes_components():
    result = safe_to_spend(
        current_balance=1000,
        days_remaining=10,
        expected_income=50,
        committed_expenses=400,
        irregular_reserve=100,
        buffer=100,
    )
    assert result["components"] == {
        "current_balance": 1000.0,
        "expected_income": 50.0,
        "committed_expenses": 400.0,
        "irregular_reserve": 100.0,
        "buffer": 100.0,
    }


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"current_balance": 100, "days_remaining": 0}, ValueError),
        ({"current_balance": 100, "days_remaining": -3}, ValueError),
        ({"current_balance": 100, "days_remaining": 1.5}, TypeError),
        ({"current_balance": 100, "days_remaining": 5, "committed_expenses": -1}, ValueError),
        ({"current_balance": 100, "days_remaining": 5, "buffer": -1}, ValueError),
        ({"current_balance": "100", "days_remaining": 5}, TypeError),
        ({"current_balance": True, "days_remaining": 5}, TypeError),
        ({"current_balance": float("nan"), "days_remaining": 5}, ValueError),
    ],
)
def test_safe_to_spend_rejects_bad_input(kwargs, error):
    with pytest.raises(error):
        safe_to_spend(**kwargs)


# --------------------------------------------------------------------------
# safe_to_save
# --------------------------------------------------------------------------

def test_safe_to_save_default_cushion():
    # Spending 1200 + 200 + 800 = 2200; surplus 800; keep 20% -> save 640.
    result = safe_to_save(
        monthly_income=3000,
        monthly_mandatory_regular=1200,
        monthly_mandatory_irregular=200,
        monthly_everyday=800,
    )
    assert result["total_monthly_spending"] == 2200.0
    assert result["surplus"] == 800.0
    assert result["safe_to_save_monthly"] == 640.0
    assert result["safe_to_save_yearly"] == 7680.0
    assert result["savings_rate"] == 0.2133  # 640 / 3000
    assert result["shortfall"] == 0.0


def test_safe_to_save_cushion_extremes():
    base = dict(
        monthly_income=3000,
        monthly_mandatory_regular=1200,
        monthly_mandatory_irregular=200,
        monthly_everyday=800,
    )
    assert safe_to_save(**base, cushion_fraction=0)["safe_to_save_monthly"] == 800.0
    assert safe_to_save(**base, cushion_fraction=1)["safe_to_save_monthly"] == 0.0


def test_safe_to_save_deficit():
    # Spending 2500 against income 2000: nothing to save, 500 short.
    result = safe_to_save(
        monthly_income=2000,
        monthly_mandatory_regular=1500,
        monthly_mandatory_irregular=300,
        monthly_everyday=700,
    )
    assert result["safe_to_save_monthly"] == 0.0
    assert result["safe_to_save_yearly"] == 0.0
    assert result["surplus"] == 0.0
    assert result["shortfall"] == 500.0
    assert result["savings_rate"] == 0.0


def test_safe_to_save_break_even_and_zero_income():
    even = safe_to_save(
        monthly_income=2000,
        monthly_mandatory_regular=1000,
        monthly_mandatory_irregular=500,
        monthly_everyday=500,
    )
    assert even["safe_to_save_monthly"] == 0.0
    assert even["shortfall"] == 0.0

    no_income = safe_to_save(
        monthly_income=0,
        monthly_mandatory_regular=0,
        monthly_mandatory_irregular=0,
        monthly_everyday=0,
    )
    assert no_income["savings_rate"] == 0.0  # no division by zero


@pytest.mark.parametrize("cushion", [-0.1, 1.5])
def test_safe_to_save_rejects_bad_cushion(cushion):
    with pytest.raises(ValueError):
        safe_to_save(
            monthly_income=3000,
            monthly_mandatory_regular=1000,
            monthly_mandatory_irregular=0,
            monthly_everyday=500,
            cushion_fraction=cushion,
        )


def test_safe_to_save_rejects_negative_spending():
    with pytest.raises(ValueError):
        safe_to_save(
            monthly_income=3000,
            monthly_mandatory_regular=-1,
            monthly_mandatory_irregular=0,
            monthly_everyday=0,
        )


# --------------------------------------------------------------------------
# what_if_reduce
# --------------------------------------------------------------------------

def test_what_if_reduce_matches_the_brief_example():
    # "Cut dining out by 20%": 235 -> saves 47/month, 564/year.
    result = what_if_reduce(monthly_spending=235, reduction_pct=20)
    assert result["monthly_saving"] == 47.0
    assert result["yearly_saving"] == 564.0
    assert result["current_monthly_spending"] == 235.0
    assert result["new_monthly_spending"] == 188.0


def test_what_if_reduce_rounds_half_up_to_cents():
    # 19.99 * 10% = 1.999 -> 2.00; yearly 23.988 -> 23.99 (exact, not 2.00 * 12).
    result = what_if_reduce(monthly_spending=19.99, reduction_pct=10)
    assert result["monthly_saving"] == 2.0
    assert result["yearly_saving"] == 23.99


def test_what_if_reduce_accepts_decimal():
    result = what_if_reduce(
        monthly_spending=Decimal("235.50"), reduction_pct=Decimal("20")
    )
    assert result["monthly_saving"] == 47.1
    assert result["yearly_saving"] == 565.2
    assert result["new_monthly_spending"] == 188.4


def test_what_if_reduce_boundaries():
    assert what_if_reduce(monthly_spending=100, reduction_pct=0)["monthly_saving"] == 0.0
    full = what_if_reduce(monthly_spending=100, reduction_pct=100)
    assert full["monthly_saving"] == 100.0
    assert full["new_monthly_spending"] == 0.0


@pytest.mark.parametrize("pct", [-5, 120])
def test_what_if_reduce_rejects_bad_percent(pct):
    with pytest.raises(ValueError):
        what_if_reduce(monthly_spending=100, reduction_pct=pct)


def test_what_if_reduce_rejects_negative_spending():
    with pytest.raises(ValueError):
        what_if_reduce(monthly_spending=-100, reduction_pct=10)


# --------------------------------------------------------------------------
# what_if_reduce_many
# --------------------------------------------------------------------------

def test_what_if_reduce_many_combines_only_named_categories():
    # Restaurants 20% of 235 = 47; Entertainment 50% of 100 = 50; Groceries untouched.
    result = what_if_reduce_many(
        monthly_by_category={
            "Restaurants": 235,
            "Entertainment": 100,
            "Groceries": 400,
        },
        reductions_pct={"Restaurants": 20, "Entertainment": 50},
    )
    assert result["monthly_saving"] == 97.0
    assert result["yearly_saving"] == 1164.0
    assert set(result["by_category"]) == {"Restaurants", "Entertainment"}
    assert result["by_category"]["Restaurants"]["monthly_saving"] == 47.0


def test_what_if_reduce_many_totals_are_exact_not_sums_of_rounded_values():
    # Each line saves 1.005 (shown as 1.01). Exact total 2.01/month, 24.12/year;
    # summing the rounded lines would wrongly give 2.02 and 24.24.
    result = what_if_reduce_many(
        monthly_by_category={"A": 10.05, "B": 10.05},
        reductions_pct={"A": 10, "B": 10},
    )
    assert result["by_category"]["A"]["monthly_saving"] == 1.01
    assert result["monthly_saving"] == 2.01
    assert result["yearly_saving"] == 24.12


def test_what_if_reduce_many_rejects_unknown_category():
    with pytest.raises(ValueError, match="Dining"):
        what_if_reduce_many(
            monthly_by_category={"Restaurants": 235},
            reductions_pct={"Dining": 20},
        )


def test_what_if_reduce_many_rejects_bad_percent():
    with pytest.raises(ValueError):
        what_if_reduce_many(
            monthly_by_category={"Restaurants": 235},
            reductions_pct={"Restaurants": 150},
        )

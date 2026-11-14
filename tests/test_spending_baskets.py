"""
Unit tests for coach/spending_baskets.py (no database needed).

    python -m pytest tests/test_spending_baskets.py
"""

from decimal import Decimal

import pytest

from coach.spending_baskets import (
    BASKET_KEYS,
    CONSUMPTION_TRANSACTION_TYPES,
    EXCLUDED_FROM_CONSUMPTION,
    classify_category,
    classify_transaction,
    is_consumption_transaction,
    salary_sweep_info,
    summarize_baskets,
)

# Every (category, transaction_type) pair found in the full-dataset audit
# (3,626,755 rows, Oct 2024 - Sep 2026).
AUDITED_PAIRS = [
    ("Entertainment", "purchase"),
    ("Groceries", "purchase"),
    ("Health", "purchase"),
    ("Home & Tech", "purchase"),
    ("Housing", "housing_payment"),
    ("Invest Deposit", "investment_deposit"),
    ("Invest Withdraw", "investment_withdrawal"),
    ("Lifestyle", "purchase"),
    ("Other Income", "other_income"),
    ("Restaurants", "purchase"),
    ("Salary", "salary"),
    ("Salary Sweep", "salary_sweep"),
    ("Transportation", "purchase"),
    ("Travel", "purchase"),
    ("Utilities", "utilities_payment"),
]

NON_CONSUMPTION_TYPES = [
    "salary",
    "other_income",
    "investment_deposit",
    "investment_withdrawal",
    "salary_sweep",
]


# --------------------------------------------------------------------------
# What counts as consumption
# --------------------------------------------------------------------------

@pytest.mark.parametrize("transaction_type", CONSUMPTION_TRANSACTION_TYPES)
def test_known_spending_types_are_consumption(transaction_type):
    assert is_consumption_transaction(transaction_type)


@pytest.mark.parametrize(
    "transaction_type", NON_CONSUMPTION_TYPES + [None, "", "brand_new_type"]
)
def test_everything_else_is_not_consumption(transaction_type):
    # Unknown or missing types must never be counted as spending.
    assert not is_consumption_transaction(transaction_type)


def test_allowlist_and_exclusion_list_do_not_overlap():
    assert not set(CONSUMPTION_TRANSACTION_TYPES) & set(EXCLUDED_FROM_CONSUMPTION)


def test_exclusion_list_covers_every_audited_non_consumption_type():
    assert set(NON_CONSUMPTION_TYPES) <= set(EXCLUDED_FROM_CONSUMPTION)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "category, expected",
    [
        ("Housing", "mandatory_regular"),
        ("Utilities", "mandatory_regular"),
        ("Groceries", "everyday_flexible"),
        ("Restaurants", "everyday_flexible"),
        ("Transportation", "everyday_flexible"),
        ("Entertainment", "everyday_flexible"),
        ("Lifestyle", "everyday_flexible"),
        ("Travel", "everyday_flexible"),
        ("Health", "needs_review"),
        ("Home & Tech", "needs_review"),
        ("Uncategorized", "needs_review"),
        ("Brand New Category", "needs_review"),
    ],
)
def test_classify_category_defaults(category, expected):
    assert classify_category(category) == expected


@pytest.mark.parametrize("category", ["Health", "Home & Tech"])
def test_customer_confirmation_places_health_and_home_tech(category):
    assert classify_category(category, "essential") == "mandatory_irregular"
    assert classify_category(category, "optional") == "everyday_flexible"
    assert classify_category(category, "needs_review") == "needs_review"
    assert classify_category(category, None) == "needs_review"


def test_customer_confirmation_cannot_move_fixed_categories():
    assert classify_category("Restaurants", "essential") == "everyday_flexible"
    assert classify_category("Housing", "optional") == "mandatory_regular"


def test_classify_transaction_skips_financial_flows():
    assert classify_transaction("Salary Sweep", "salary_sweep") is None
    assert classify_transaction("Invest Deposit", "investment_deposit") is None
    assert classify_transaction("Invest Withdraw", "investment_withdrawal") is None
    assert classify_transaction("Salary", "salary") is None
    assert classify_transaction("Other Income", "other_income") is None


def test_classify_transaction_places_consumption():
    assert classify_transaction("Housing", "housing_payment") == "mandatory_regular"
    assert classify_transaction("Groceries", "purchase") == "everyday_flexible"
    assert classify_transaction("Health", "purchase") == "needs_review"


def test_every_audited_pair_is_handled_deliberately():
    # No audited row may fall through: it is either a known basket or not
    # consumption at all.
    for category, transaction_type in AUDITED_PAIRS:
        basket = classify_transaction(category, transaction_type)
        if transaction_type in NON_CONSUMPTION_TYPES:
            assert basket is None, (category, transaction_type)
        else:
            assert basket in BASKET_KEYS, (category, transaction_type)


# --------------------------------------------------------------------------
# summarize_baskets
# --------------------------------------------------------------------------

ROWS = [
    {"category": "Housing", "total_spending_eur": Decimal("1000.00"), "transaction_count": 10},
    {"category": "Utilities", "total_spending_eur": Decimal("200.00"), "transaction_count": 5},
    {"category": "Groceries", "total_spending_eur": Decimal("400.50"), "transaction_count": 20},
    {"category": "Restaurants", "total_spending_eur": Decimal("99.50"), "transaction_count": 8},
    {"category": "Health", "total_spending_eur": Decimal("300.00"), "transaction_count": 3},
]


def test_summarize_baskets_totals_and_shares():
    # Total 2000: regular 1200 (60%), everyday 500 (25%), review 300 (15%).
    result = summarize_baskets(ROWS)
    baskets = result["baskets"]

    assert result["total_spending_eur"] == 2000.0
    assert baskets["mandatory_regular"]["total_eur"] == 1200.0
    assert baskets["mandatory_regular"]["share_pct"] == 60.0
    assert baskets["mandatory_regular"]["transaction_count"] == 15
    assert baskets["everyday_flexible"]["total_eur"] == 500.0
    assert baskets["everyday_flexible"]["share_pct"] == 25.0
    assert baskets["everyday_flexible"]["transaction_count"] == 28
    assert baskets["needs_review"]["total_eur"] == 300.0
    assert baskets["needs_review"]["share_pct"] == 15.0


def test_summarize_baskets_always_has_every_basket():
    baskets = summarize_baskets(ROWS)["baskets"]
    assert set(baskets) == set(BASKET_KEYS)
    assert baskets["mandatory_irregular"] == {
        "total_eur": 0.0,
        "share_pct": 0.0,
        "transaction_count": 0,
        "categories": [],
    }


def test_summarize_baskets_orders_categories_by_amount():
    categories = summarize_baskets(ROWS)["baskets"]["mandatory_regular"]["categories"]
    assert categories == [
        {"category": "Housing", "total_eur": 1000.0},
        {"category": "Utilities", "total_eur": 200.0},
    ]


def test_summarize_baskets_with_no_spending():
    result = summarize_baskets([])
    assert result["total_spending_eur"] == 0.0
    assert all(b["share_pct"] == 0.0 for b in result["baskets"].values())


def test_summarize_baskets_applies_customer_confirmation():
    result = summarize_baskets(ROWS, {"Health": "essential"})
    baskets = result["baskets"]
    assert baskets["mandatory_irregular"]["total_eur"] == 300.0
    assert baskets["needs_review"]["total_eur"] == 0.0
    assert result["total_spending_eur"] == 2000.0  # total never changes


def test_summarize_baskets_accepts_plain_floats():
    rows = [{"category": "Groceries", "total_spending_eur": 19.99, "transaction_count": 1}]
    result = summarize_baskets(rows)
    assert result["total_spending_eur"] == 19.99
    assert result["baskets"]["everyday_flexible"]["share_pct"] == 100.0


# --------------------------------------------------------------------------
# salary_sweep_info
# --------------------------------------------------------------------------

def _flow(transaction_type, net, count):
    return {
        "transaction_type": transaction_type,
        "net_amount_eur": net,
        "transaction_count": count,
    }


def test_salary_sweep_info_without_sweeps():
    for rows in ([], [_flow("salary", Decimal("3000"), 3)]):
        info = salary_sweep_info(rows)
        assert info == {
            "has_salary_sweep": False,
            "swept_share_of_salary_pct": None,
            "salary_sweep_note": None,
        }


def test_salary_sweep_info_ignores_a_zero_count_sweep_row():
    assert salary_sweep_info([_flow("salary_sweep", 0, 0)])["has_salary_sweep"] is False


def test_salary_sweep_info_matches_the_real_customer_cust00080():
    # Real audit figures: 76,885.91 swept out of 81,268.98 salary = 94.6%.
    info = salary_sweep_info(
        [
            _flow("salary", Decimal("81268.98"), 24),
            _flow("salary_sweep", Decimal("-76885.91"), 24),
        ]
    )
    assert info["has_salary_sweep"] is True
    assert info["swept_share_of_salary_pct"] == 94.6
    assert "94.6% of salary" in info["salary_sweep_note"]
    assert "minimum" in info["salary_sweep_note"]


def test_salary_sweep_info_without_salary_has_no_percentage():
    info = salary_sweep_info([_flow("salary_sweep", Decimal("-500"), 2)])
    assert info["has_salary_sweep"] is True
    assert info["swept_share_of_salary_pct"] is None
    assert "%" not in info["salary_sweep_note"]


def test_salary_sweep_note_does_not_claim_to_know_the_destination():
    note = salary_sweep_info(
        [_flow("salary", 1000, 1), _flow("salary_sweep", -900, 1)]
    )["salary_sweep_note"]
    assert "do not know" in note

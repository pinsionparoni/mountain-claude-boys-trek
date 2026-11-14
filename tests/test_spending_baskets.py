"""
Unit tests for coach/spending_baskets.py (no database needed).

    python -m pytest tests/test_spending_baskets.py
"""

from datetime import date
from decimal import Decimal

import pytest

from coach.spending_baskets import (
    CATEGORY_BASKETS,
    BASKET_KEYS,
    CATEGORY_MEDIAN_EUR,
    CONSUMPTION_TRANSACTION_TYPES,
    EXCLUDED_FROM_CONSUMPTION,
    OTHER_BASKETS,
    classify_purchase,
    classify_transaction,
    is_consumption_transaction,
    merchant_breakdown,
    merchant_type,
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
    "category, mcc, amount, expected",
    [
        # Bills go by category.
        ("Housing", None, 900, "regular_essentials"),
        ("Utilities", None, 60, "regular_essentials"),
        # Card purchases go by merchant type.
        ("Groceries", "5411", 60, "regular_essentials"),
        ("Groceries", "5499", 60, "everyday_spending"),        # convenience / specialty food
        ("Transportation", "5542", 40, "regular_essentials"),  # fuel
        ("Transportation", "4111", 40, "regular_essentials"),  # public transport
        ("Transportation", "4121", 40, "everyday_spending"),   # taxi
        ("Health", "5912", 50, "regular_essentials"),          # pharmacy
        ("Health", "8021", 50, "unexpected_necessities"),      # dentist
        ("Home & Tech", "5732", 100, "unexpected_necessities"),
        ("Restaurants", "5814", 20, "everyday_spending"),
        ("Travel", "4511", 130, "everyday_spending"),
        # No MCC: the category's majority basket.
        ("Transportation", None, 40, "regular_essentials"),
        ("Health", None, 50, "regular_essentials"),
        ("Home & Tech", None, 100, "unexpected_necessities"),
        ("Restaurants", None, 20, "everyday_spending"),
        # A category the rules don't know is never guessed.
        ("Brand New Category", None, 10, "unclassified"),
    ],
)
def test_classify_purchase(category, mcc, amount, expected):
    assert classify_purchase(category, mcc, amount) == expected


def test_large_health_and_home_tech_purchases_are_unexpected():
    # 10x the median: Health 53.85 -> 538.50, Home & Tech 111.08 -> 1110.80.
    assert classify_purchase("Health", "5912", Decimal("538.49")) == "regular_essentials"
    assert classify_purchase("Health", "5912", Decimal("538.50")) == "unexpected_necessities"
    assert classify_purchase("Health", None, 2000) == "unexpected_necessities"
    assert classify_purchase("Home & Tech", "5732", 5000) == "unexpected_necessities"


def test_large_purchases_elsewhere_keep_their_basket():
    assert classify_purchase("Restaurants", "5812", 3000) == "everyday_spending"
    assert classify_purchase("Groceries", "5411", 3000) == "regular_essentials"


def test_customer_override_wins():
    assert classify_purchase("Restaurants", "5812", 20, {"Restaurants": "regular_essentials"}) == "regular_essentials"
    assert classify_purchase("Health", "8021", 2000, {"Health": "everyday_spending"}) == "everyday_spending"
    # An unknown basket name is ignored.
    assert classify_purchase("Restaurants", "5812", 20, {"Restaurants": "needs_review"}) == "everyday_spending"


def test_merchant_type_labels():
    assert merchant_type("4121", "Transportation") == "taxi"
    assert merchant_type(None, "Transportation") == "other"
    assert merchant_type("9999", "Transportation") == "other"
    assert merchant_type(None, "Housing") == "bill"


def test_classify_transaction_skips_financial_flows():
    assert classify_transaction("Salary Sweep", "salary_sweep") is None
    assert classify_transaction("Invest Deposit", "investment_deposit") is None
    assert classify_transaction("Invest Withdraw", "investment_withdrawal") is None
    assert classify_transaction("Salary", "salary") is None
    assert classify_transaction("Other Income", "other_income") is None


def test_classify_transaction_places_consumption():
    assert classify_transaction("Housing", "housing_payment") == "regular_essentials"
    assert classify_transaction("Groceries", "purchase", "5411", 50) == "regular_essentials"
    assert classify_transaction("Health", "purchase", "8011", 50) == "unexpected_necessities"


def test_every_audited_pair_is_handled_deliberately():
    # No audited row may fall through: it is either a known basket or not
    # consumption at all, even without an MCC.
    for category, transaction_type in AUDITED_PAIRS:
        basket = classify_transaction(category, transaction_type)
        if transaction_type in NON_CONSUMPTION_TYPES:
            assert basket is None, (category, transaction_type)
        else:
            assert basket in BASKET_KEYS, (category, transaction_type)


def test_every_purchase_category_has_an_other_basket_and_a_median():
    purchase_categories = {c for c, t in AUDITED_PAIRS if t == "purchase"}
    assert set(OTHER_BASKETS) == purchase_categories
    assert set(CATEGORY_MEDIAN_EUR) == purchase_categories


# --------------------------------------------------------------------------
# summarize_baskets
# --------------------------------------------------------------------------

D = date(2026, 9, 1)
TRANSACTIONS = [
    {"tx_date": D, "category": "Housing", "mcc_code": None, "amount_eur": Decimal("1000.00")},
    {"tx_date": D, "category": "Groceries", "mcc_code": "5411", "amount_eur": Decimal("300.50")},
    {"tx_date": D, "category": "Transportation", "mcc_code": "4121", "amount_eur": Decimal("40.00")},
    {"tx_date": D, "category": "Transportation", "mcc_code": None, "amount_eur": Decimal("60.00")},
    {"tx_date": D, "category": "Restaurants", "mcc_code": "5812", "amount_eur": Decimal("99.50")},
    {"tx_date": D, "category": "Health", "mcc_code": "8021", "amount_eur": Decimal("800.00")},  # large
]


def test_summarize_baskets_totals_and_shares():
    # Total 2300: regular 1360.50, unexpected 800, everyday 139.50.
    result = summarize_baskets(TRANSACTIONS)
    baskets = result["baskets"]

    assert result["total_spending_eur"] == 2300.0
    assert baskets["regular_essentials"]["total_eur"] == 1360.5
    assert baskets["regular_essentials"]["share_pct"] == 59.2
    assert baskets["regular_essentials"]["transaction_count"] == 3
    assert baskets["unexpected_necessities"]["total_eur"] == 800.0
    assert baskets["everyday_spending"]["total_eur"] == 139.5
    assert baskets["everyday_spending"]["transaction_count"] == 2
    assert baskets["regular_essentials"]["label"] == "🏠 Regular essentials"


def test_summarize_baskets_splits_categories_by_merchant_type():
    regular = summarize_baskets(TRANSACTIONS)["baskets"]["regular_essentials"]["categories"]
    assert regular[0] == {
        "category": "Housing",
        "total_eur": 1000.0,
        "merchant_types": [{"merchant_type": "bill", "total_eur": 1000.0, "transaction_count": 1}],
    }
    transport_regular = next(c for c in regular if c["category"] == "Transportation")
    assert transport_regular["merchant_types"] == [
        {"merchant_type": "other", "total_eur": 60.0, "transaction_count": 1},
    ]
    everyday = summarize_baskets(TRANSACTIONS)["baskets"]["everyday_spending"]["categories"]
    assert [c["category"] for c in everyday] == ["Restaurants", "Transportation"]


def test_summarize_baskets_reports_unusual_purchases():
    unusual = summarize_baskets(TRANSACTIONS)["unusual_purchases"]
    assert unusual == [{
        "date": "2026-09-01",
        "category": "Health",
        "merchant_type": "dentist",
        "amount_eur": 800.0,
        "times_usual": 14.9,  # 800 / 53.85
        "basket": "unexpected_necessities",
    }]


def test_summarize_baskets_always_has_the_three_baskets():
    baskets = summarize_baskets([])["baskets"]
    assert set(baskets) == set(BASKET_KEYS)
    assert baskets["unexpected_necessities"]["total_eur"] == 0.0
    assert all(b["share_pct"] == 0.0 for b in baskets.values())


def test_summarize_baskets_shows_unclassified_only_when_needed():
    assert "unclassified" not in summarize_baskets(TRANSACTIONS)["baskets"]
    rows = [{"tx_date": D, "category": "Brand New Category", "mcc_code": None, "amount_eur": 5}]
    assert summarize_baskets(rows)["baskets"]["unclassified"]["total_eur"] == 5.0


def test_summarize_baskets_applies_customer_overrides():
    result = summarize_baskets(TRANSACTIONS, {"Restaurants": "regular_essentials"})
    assert result["baskets"]["everyday_spending"]["total_eur"] == 40.0
    assert result["total_spending_eur"] == 2300.0  # total never changes


def test_summarize_baskets_accepts_plain_floats():
    rows = [{"tx_date": D, "category": "Groceries", "mcc_code": "5411", "amount_eur": 19.99}]
    result = summarize_baskets(rows)
    assert result["total_spending_eur"] == 19.99
    assert result["baskets"]["regular_essentials"]["share_pct"] == 100.0


def test_merchant_breakdown():
    types = merchant_breakdown(TRANSACTIONS, "Transportation")
    assert types == [
        {"merchant_type": "other", "total_eur": 60.0, "transaction_count": 1, "baskets": ["regular_essentials"]},
        {"merchant_type": "taxi", "total_eur": 40.0, "transaction_count": 1, "baskets": ["everyday_spending"]},
    ]
    assert merchant_breakdown(TRANSACTIONS, "Travel") == []


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
            "salary_sweep_note_fi": None,
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


# --------------------------------------------------------------------------
# Rules as data (for classifying the whole population in SQL)
# --------------------------------------------------------------------------

from coach.spending_baskets import (  # noqa: E402
    ANY_CATEGORY,
    CATEGORY_MEDIAN_EUR,
    MERCHANT_TYPES,
    basket_lookup,
    basket_lookup_key,
    classify_purchase,
    large_purchase_thresholds,
)


def _sql_lookup(lookup, category, mcc_code, amount):
    """What the SQL does: exact key, then the key without MCC, else unclassified."""
    threshold = large_purchase_thresholds().get(category)
    large = threshold is not None and Decimal(str(amount)) >= threshold
    return (lookup.get(basket_lookup_key(category, mcc_code, large))
            or lookup.get(basket_lookup_key(category, None, large))
            or lookup.get(basket_lookup_key(ANY_CATEGORY, mcc_code, large))
            or "unclassified")


@pytest.mark.parametrize("category", sorted({*CATEGORY_MEDIAN_EUR, "Housing", "Utilities", "Uncategorized"}))
@pytest.mark.parametrize("mcc_code", [None, "9999", *MERCHANT_TYPES])
@pytest.mark.parametrize("times_median", [0.5, 9.99, 10, 40])
def test_lookup_agrees_with_classify_purchase(category, mcc_code, times_median):
    # Every category x MCC (known, unknown, none) x size, just below and at
    # the large-purchase line: the lookup used in SQL gives the same basket.
    amount = CATEGORY_MEDIAN_EUR.get(category, Decimal(50)) * Decimal(str(times_median))
    assert _sql_lookup(basket_lookup(), category, mcc_code, amount) == classify_purchase(
        category, mcc_code, amount
    )


def test_large_purchase_threshold_is_ten_times_the_median():
    assert large_purchase_thresholds()["Home & Tech"] == Decimal("1110.80")


def test_every_category_and_merchant_type_has_a_finnish_name():
    from coach.spending_baskets import (
        CATEGORY_LABELS_FI, INCOME_TYPES, INVESTMENT_TYPES, MERCHANT_TYPES,
        MERCHANT_TYPE_LABELS_FI, OTHER_MERCHANT_TYPE, TRANSACTION_TYPE_LABELS_FI, UNCLASSIFIED,
    )
    spending_categories = {*CATEGORY_BASKETS, *OTHER_BASKETS}
    flow_categories = {"Salary", "Other Income", "Salary Sweep", "Invest Deposit", "Invest Withdraw"}
    assert spending_categories | flow_categories <= set(CATEGORY_LABELS_FI)
    types = {entry[0] for entry in MERCHANT_TYPES.values()} | {OTHER_MERCHANT_TYPE, UNCLASSIFIED, "bill"}
    assert types <= set(MERCHANT_TYPE_LABELS_FI)
    assert {*INCOME_TYPES, *INVESTMENT_TYPES, "salary_sweep"} <= set(TRANSACTION_TYPE_LABELS_FI)


def test_salary_sweep_note_has_a_finnish_version():
    info = salary_sweep_info([_flow("salary", Decimal("3000"), 1), _flow("salary_sweep", Decimal("-1500"), 1)])
    assert "50,0 %" in info["salary_sweep_note_fi"]

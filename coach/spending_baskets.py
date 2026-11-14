"""
Spending basket definitions and evidence-based classification signals.

Important:
- Transaction type determines whether a row is consumption, income, investment,
  or an unresolved financial flow.
- Category/MCC behavior is a descriptive signal, not proof that a purchase is
  essential or discretionary.
- Health and Home & Tech remain unassigned until the customer or a trusted
  business rule confirms their purpose.
"""

from decimal import ROUND_HALF_UP, Decimal

# The three product baskets. These lists intentionally contain only categories
# that can be assigned from the available transaction data with reasonable
# confidence. Health and Home & Tech are handled separately below.
SPENDING_BASKETS = {
    "mandatory_regular": [
        "Housing",
        "Utilities",
    ],
    "mandatory_irregular": [],
    "everyday_flexible": [
        "Groceries",
        "Restaurants",
        "Transportation",
        "Entertainment",
        "Lifestyle",
        "Travel",
    ],
}

# Preserve the existing exclusion constant for current query code.
# These transaction types are not ordinary consumption.
INCOME_TYPES = [
    "salary",
    "other_income",
]

INVESTMENT_TYPES = [
    "investment_deposit",
    "investment_withdrawal",
]

UNCLASSIFIED_FINANCIAL_FLOWS = [
    "salary_sweep",
]

EXCLUDED_FROM_CONSUMPTION = (
    INCOME_TYPES
    + INVESTMENT_TYPES
    + UNCLASSIFIED_FINANCIAL_FLOWS
)

# Transaction types that are real consumption. The audit of all 3.6M rows
# (Oct 2024-Sep 2026) shows every spending row has exactly one of these types
# and that no purchase has a positive amount (no refunds). Every other
# negative type (investment_deposit, salary_sweep) is a financial flow.
# Queries use this allowlist rather than EXCLUDED_FROM_CONSUMPTION so that a
# transaction type we have never seen is never counted as spending.
CONSUMPTION_TRANSACTION_TYPES = [
    "purchase",
    "housing_payment",
    "utilities_payment",
]

# Categories where category-level data does not establish whether a purchase
# is essential. Do not silently force these into mandatory or flexible baskets.
NEEDS_CONFIRMATION_CATEGORIES = [
    "Health",
    "Home & Tech",
]

# Behavioral evidence from the 24-month dataset audit (Oct 2024-Sep 2026).
# These are recurrence signals only. They must not be used as essentiality
# labels or as automatic spending-basket assignments.
#
# "strong_recurring_candidate":
#   Relatively frequent repeat purchases and stronger recurrence/streak evidence.
# "moderate_recurring_candidate":
#   Some repeat behavior, but weaker or more mixed recurrence evidence.
# "mostly_episodic":
#   Longer median gaps and predominantly short active-month streaks.
#
# MCC codes are strings because the database column is text and may be NULL.
MCC_BEHAVIORAL_SIGNALS = {
    "Health": {
        "5912": "strong_recurring_candidate",
        "8011": "moderate_recurring_candidate",
        "8021": "mostly_episodic",
        "8099": "mostly_episodic",
        None: "unclassified_missing_mcc",
    },
    "Home & Tech": {
        "5200": "strong_recurring_candidate",
        "5251": "moderate_recurring_candidate",
        "5712": "moderate_recurring_candidate",
        "5732": "moderate_recurring_candidate",
        "5734": "mostly_episodic",
        None: "unclassified_missing_mcc",
    },
}

# Customer-confirmed purpose should take precedence over behavioral signals.
# Suggested values for a future customer profile / transaction annotation:
CUSTOMER_ESSENTIALITY_VALUES = [
    "essential",
    "optional",
    "needs_review",
]

# Salary Sweep is a distinct recurring outgoing flow closely associated with
# salary, but its destination/purpose is unknown. Do not classify it as
# consumption, savings, an internal transfer, or investment without evidence.
UNCLASSIFIED_FINANCIAL_FLOW_NOTES = {
    "salary_sweep": (
        "Recurring salary-linked outgoing flow; destination and purpose unknown."
    ),
}


def get_mcc_behavioral_signal(category, mcc_code):
    """Return a descriptive recurrence signal, or None if no rule exists."""
    category_signals = MCC_BEHAVIORAL_SIGNALS.get(category, {})
    return category_signals.get(mcc_code)


def is_consumption_transaction(transaction_type):
    """Return True only for known consumption transaction types."""
    return transaction_type in CONSUMPTION_TRANSACTION_TYPES


# Keys of the baskets reported to the customer. "needs_review" holds spending
# we cannot honestly place yet (Health, Home & Tech, unknown categories).
BASKET_KEYS = (
    "mandatory_regular",
    "mandatory_irregular",
    "everyday_flexible",
    "needs_review",
)


def classify_category(category, customer_essentiality=None):
    """
    Return the basket key for a consumption category.

    Categories listed in SPENDING_BASKETS map directly. Health and Home & Tech
    follow the customer's confirmed purpose ("essential" -> mandatory_irregular,
    "optional" -> everyday_flexible). Without that confirmation, and for any
    category we do not recognise, the answer is "needs_review" rather than a
    guess. Customer confirmation is ignored for categories that already have a
    fixed basket.
    """
    for basket, categories in SPENDING_BASKETS.items():
        if category in categories:
            return basket

    if category in NEEDS_CONFIRMATION_CATEGORIES:
        if customer_essentiality == "essential":
            return "mandatory_irregular"
        if customer_essentiality == "optional":
            return "everyday_flexible"

    return "needs_review"


def classify_transaction(category, transaction_type, customer_essentiality=None):
    """Return the basket key for one transaction, or None if it is not consumption."""
    if not is_consumption_transaction(transaction_type):
        return None
    return classify_category(category, customer_essentiality)


def _eur(value):
    """Round a Decimal half-up to whole cents and return a plain float."""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def summarize_baskets(category_rows, essentiality_by_category=None):
    """
    Group per-category spending rows into the product baskets.

    ``category_rows`` are rows shaped like the output of
    ``spending_by_category`` (``category``, ``total_spending_eur``,
    ``transaction_count``) and must already be consumption-only.
    ``essentiality_by_category`` optionally maps a category name to
    "essential" or "optional" (see CUSTOMER_ESSENTIALITY_VALUES).

    Every basket key is always present, with zeros when empty.
    """
    overrides = essentiality_by_category or {}
    totals = {
        key: {"total": Decimal(0), "count": 0, "categories": []}
        for key in BASKET_KEYS
    }

    for row in category_rows:
        category = row["category"]
        amount = Decimal(str(row["total_spending_eur"]))
        entry = totals[classify_category(category, overrides.get(category))]
        entry["total"] += amount
        entry["count"] += row["transaction_count"]
        entry["categories"].append(
            {"category": category, "total_eur": _eur(amount)}
        )

    grand_total = sum((e["total"] for e in totals.values()), Decimal(0))

    baskets = {}
    for key, entry in totals.items():
        share = entry["total"] / grand_total * 100 if grand_total else Decimal(0)
        baskets[key] = {
            "total_eur": _eur(entry["total"]),
            "share_pct": float(share.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "transaction_count": entry["count"],
            "categories": sorted(
                entry["categories"], key=lambda c: c["total_eur"], reverse=True
            ),
        }

    return {"baskets": baskets, "total_spending_eur": _eur(grand_total)}

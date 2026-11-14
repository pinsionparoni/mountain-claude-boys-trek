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
    """Return True only for transaction types not explicitly excluded."""
    return transaction_type not in EXCLUDED_FROM_CONSUMPTION

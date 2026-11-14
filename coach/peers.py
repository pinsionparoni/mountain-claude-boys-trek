"""
"What kind of spender am I?": one customer's spending against their peers.

Fetches every customer's spending for the period through
coach/database/queries.py (cached: the first call takes several seconds) and
leaves the comparison to coach/calculations.py. The model only explains the
result.

The period is the last 12 complete months before the coach's "today", so
seasonal spending (holidays, Christmas) is counted the same for everyone.
Bills (Housing, Utilities) reflect living situation more than habits, so they
stay in the comparison and the total but are kept out of the profile.

The same comparison is made for S-Bank's three baskets, placed by the same
rules as the basket summary (coach/spending_baskets.py).
"""

from datetime import date, timedelta

from coach import calculations
from coach.database import queries
from coach.spending_baskets import BASKET_LABELS, BASKET_LABELS_FI, CATEGORY_BASKETS

PERIOD_MONTHS = 12
BILL_CATEGORIES = tuple(CATEGORY_BASKETS)  # Housing, Utilities: placed by category, not habit


def peer_period(today: date) -> tuple[date, date]:
    """The last ``PERIOD_MONTHS`` complete months before ``today``'s month."""
    end = today.replace(day=1) - timedelta(days=1)
    start_month = end.month - PERIOD_MONTHS + 1
    start_year = end.year + (start_month - 1) // 12
    start = date(start_year, (start_month - 1) % 12 + 1, 1)
    return start, end


def warm_up(today: date) -> None:
    """Load the peer population into the cache, so the first question is fast."""
    queries.population_spending(*peer_period(today))


def compare(customer_id: str, today: date) -> dict:
    """The customer's spending compared with people their age and with everyone."""
    start, end = peer_period(today)
    population = queries.population_spending(start, end)

    me = next((row for row in population if row["customer_id"] == customer_id), None)
    if me is None:
        raise ValueError(f"Unknown customer {customer_id}")

    others = [row for row in population if row["customer_id"] != customer_id]
    result = calculations.compare_with_peers(
        customer_spending=me["spending"],
        customer_age=me["age"],
        peers=others,
        months=PERIOD_MONTHS,
        exclude_from_profile=BILL_CATEGORIES,
    )
    baskets = calculations.compare_with_peers(
        customer_spending=me["baskets"],
        customer_age=me["age"],
        peers=[{"age": row["age"], "spending": row["baskets"]} for row in others],
        months=PERIOD_MONTHS,
    )["by_category"]
    result["by_basket"] = {
        key: {"label": BASKET_LABELS.get(key, key), "label_fi": BASKET_LABELS_FI.get(key, key), **row}
        for key, row in baskets.items()
    }
    result["period"] = {"start_date": start.isoformat(), "end_date": end.isoformat()}
    result["customer_age"] = me["age"]
    result["not_in_profile"] = list(BILL_CATEGORIES)
    return result

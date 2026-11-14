"""
Charts the coach can show in the chat: the model picks WHAT to show, this module
computes every number from the customer's own data, and the app draws it.

Each function returns a plain JSON-ready "chart spec" with a ``type`` and the data
the app needs; titles and labels are written by the app in the user's language.
Sums are done here (Decimal, rounded to cents at the end), never by the model.

- ``categories``: spending per category in a period, largest first
- ``trend``: spending per month for one category, one basket or everything
- ``balance``: the account balance at the end of each month
- ``budget``: each basket this month against what the monthly budget expects
- ``peers``: the customer's monthly spending per category against people their age;
  with a category, ``peer_range``: that one category against the typical range
  and median of people their age and of everyone
"""

from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal

from coach import budget as budget_module
from coach import peers as peers_module
from coach.database import queries
from coach.spending_baskets import BASKET_KEYS, classify_purchase

KINDS = ("categories", "trend", "balance", "budget", "peers")
MAX_BARS = 6  # more categories than this fold into "Other"
OTHER = "Other"


def _eur(value) -> float:
    return round(float(value), 2)


def _month_start(day: date, months_back: int = 0) -> date:
    month = day.month - 1 - months_back
    return date(day.year + month // 12, month % 12 + 1, 1)


def categories(customer_id: str, start: date, end: date) -> dict:
    rows = queries.spending_by_category(customer_id, start, end)
    items = [{"category": r["category"], "value": Decimal(str(r["total_spending_eur"]))} for r in rows]
    items.sort(key=lambda i: i["value"], reverse=True)
    if len(items) > MAX_BARS:
        rest = sum((i["value"] for i in items[MAX_BARS - 1:]), Decimal(0))
        items = items[:MAX_BARS - 1] + [{"category": OTHER, "value": rest}]
    return {
        "type": "categories",
        "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "items": [{"category": i["category"], "value": _eur(i["value"])} for i in items],
        "total": _eur(sum((i["value"] for i in items), Decimal(0))),
    }


def trend(customer_id: str, today: date, months: int = 6,
          category: str | None = None, basket: str | None = None) -> dict:
    """Spending per calendar month; the last month is this month so far (``partial``)."""
    if category and basket:
        raise ValueError("give a category or a basket, not both")
    if basket and basket not in BASKET_KEYS:
        raise ValueError(f"basket must be one of: {', '.join(BASKET_KEYS)}")
    first = _month_start(today, months - 1)
    totals = OrderedDict((_month_start(today, back).isoformat()[:7], Decimal(0))
                         for back in range(months - 1, -1, -1))
    for tx in queries.consumption_transactions(customer_id, first, today):
        if category and tx["category"] != category:
            continue
        if basket and classify_purchase(tx["category"], tx["mcc_code"], tx["amount_eur"]) != basket:
            continue
        totals[tx["tx_date"].isoformat()[:7]] += Decimal(str(tx["amount_eur"]))
    return {
        "type": "trend",
        "subject": {"category": category, "basket": basket},
        "months": [{"month": m, "value": _eur(v), "partial": m == today.isoformat()[:7]}
                   for m, v in totals.items()],
        "today": today.isoformat(),
    }


def balance(customer_id: str, today: date, months: int = 6) -> dict:
    rows = queries.monthly_balance_trend(customer_id, months, as_of=today)
    return {
        "type": "balance",
        "points": [{"month": r["month"].isoformat()[:7], "value": _eur(r["balance_eur"])} for r in rows],
        "today": today.isoformat(),
    }


def budget(customer_id: str, today: date) -> dict:
    result = budget_module.safe_to_spend(customer_id, today)
    monthly, month = result["monthly_budget"], result["this_month"]
    return {
        "type": "budget",
        "today": today.isoformat(),
        "baskets": [
            {"basket": "regular_essentials", "spent": month["regular_essentials_spent"],
             "reference": monthly["regular_essentials"]},
            {"basket": "unexpected_necessities", "spent": month["unexpected_spent"],
             "reference": monthly["unexpected_reserve"]},
            {"basket": "everyday_spending", "spent": month["everyday_spent"],
             "reference": month["everyday_budget"]},
        ],
    }


def peers(customer_id: str, today: date, category: str | None = None) -> dict:
    """Monthly averages per category against the age group's median (bills left out),
    or with ``category`` that one category in detail (``peer_range``)."""
    result = peers_module.compare(customer_id, today)
    if category:
        row = result["by_category"].get(category)
        if row is None:
            raise ValueError(f"no spending data for {category}")

        def group(g):
            low, high = g["peer_typical_range_monthly"]
            return {"median": g["peer_median_monthly"], "typical_low": low, "typical_high": high,
                    "spends_more_than_pct": g["spends_more_than_pct_of_peers"],
                    "spends_less_than_pct": g["spends_less_than_pct_of_peers"]}

        return {
            "type": "peer_range",
            "category": category,
            "age_group": result["age_group"],
            "period": result["period"],
            "me": row["my_monthly"],
            "age": group(row["age_group"]),
            "everyone": group(row["everyone"]),
        }
    rows = [
        {"category": c, "me": r["my_monthly"], "peer_median": r["age_group"]["peer_median_monthly"]}
        for c, r in result["by_category"].items()
        if c not in result["not_in_profile"]
    ]
    rows.sort(key=lambda r: max(r["me"], r["peer_median"]), reverse=True)
    return {
        "type": "peers",
        "age_group": result["age_group"],
        "period": result["period"],
        "items": rows[:MAX_BARS],
        "left_out": result["not_in_profile"],
    }


def this_month(today: date) -> tuple[date, date]:
    return today.replace(day=1), today


def last_month(today: date) -> tuple[date, date]:
    end = today.replace(day=1) - timedelta(days=1)
    return end.replace(day=1), end

"""
The home screen's money-coaching tip ("Talousneuvoja"): one tip per customer,
picked by fixed rules from their own data. No AI: instant, free, and every number
comes from coach/budget.py, coach/peers.py and coach/calculations.py.

The first rule that applies wins:

1. ``cash_tight``: safe to spend this week is limited by the cash before payday
2. ``over_budget``: everyday spending this month is over the everyday budget
3. ``above_finland``: an everyday category (restaurants, entertainment) clearly
   above Statistics Finland's average for the customer's age (at least 25 % and
   15 EUR a month), with what a 20 % cut would save in a year. Never food,
   health or transport: those are necessities, and an account that pays for a
   family's food is not comparable with the per-person average
4. ``nearly_used``: 80 % or more of the everyday budget used with over a week left
5. ``on_track``: what's left this month, a nudge towards saving

Each tip has ``kind``, ``facts`` (the numbers the app writes into its sentence),
a ``chart`` (as coach/charts.py builds them) and nothing else: the app words the
tip and the follow-up question it asks the coach in the customer's language.
"""

from datetime import date

from coach import budget as budget_module
from coach import calculations, charts, peers

FINLAND_MIN_PCT = 25       # "clearly above" the Finnish average...
FINLAND_MIN_EUR = 15       # ...and by enough euros to matter
CUT_PCT = 20               # the what-if saving the tip suggests
# Only spending that slips through your fingers gets "cut it" advice.
DISCRETIONARY = {"Restaurants", "Entertainment"}
NEARLY_USED_SHARE = 0.8
NEARLY_USED_MIN_DAYS = 7


def _budget_chart(result: dict, today: date) -> dict:
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


def _above_finland(customer_id: str, today: date) -> dict | None:
    """The category with the most euros above the Finnish average, if any is clearly above."""
    result = peers.compare(customer_id, today)
    best = None
    for category, row in result["by_category"].items():
        if category not in DISCRETIONARY:
            continue
        finland = row.get("finland")
        if not finland or finland["difference_from_age_group_pct"] is None:
            continue
        excess = row["my_monthly"] - finland["age_group_monthly"]
        if finland["difference_from_age_group_pct"] >= FINLAND_MIN_PCT and excess >= FINLAND_MIN_EUR:
            if best is None or excess > best[1]:
                best = (category, excess, row, finland)
    if best is None:
        return None
    category, _, row, finland = best
    saving = calculations.what_if_reduce(monthly_spending=row["my_monthly"], reduction_pct=CUT_PCT)
    return {
        "kind": "above_finland",
        "facts": {
            "category": category,
            "age_group": result["age_group"],
            "my_monthly": row["my_monthly"],
            "finland_monthly": finland["age_group_monthly"],
            "difference_pct": finland["difference_from_age_group_pct"],
            "cut_pct": CUT_PCT,
            "yearly_saving": saving["yearly_saving"],
        },
        "chart": charts.peers(customer_id, today, category=category),
    }


def pick(customer_id: str, today: date) -> dict:
    """The one tip to show on the home screen for this customer today."""
    result = budget_module.safe_to_spend(customer_id, today)
    month, cash = result["this_month"], result["cash_check"]
    budget_chart = _budget_chart(result, today)

    if result["limited_by"] == "cash" and cash:
        return {"kind": "cash_tight", "chart": budget_chart, "facts": {
            "safe_this_week": result["safe_to_spend_this_week"],
            "next_payday": cash["next_payday"],
            "days_to_payday": cash["days_to_payday"],
        }}

    if month["over_budget"] > 0:
        return {"kind": "over_budget", "chart": budget_chart, "facts": {
            "over": month["over_budget"],
            "everyday_budget": month["everyday_budget"],
        }}

    tip = _above_finland(customer_id, today)
    if tip:
        return tip

    used = month["everyday_spent"] / month["everyday_budget"] if month["everyday_budget"] > 0 else 0
    if used >= NEARLY_USED_SHARE and month["days_left_in_month"] > NEARLY_USED_MIN_DAYS:
        return {"kind": "nearly_used", "chart": budget_chart, "facts": {
            "remaining": month["remaining"],
            "per_week": month["per_week"],
            "days_left": month["days_left_in_month"],
        }}

    return {"kind": "on_track", "chart": budget_chart, "facts": {
        "remaining": month["remaining"],
        "per_week": month["per_week"],
        "savings_per_month": result["monthly_budget"]["savings"],
    }}

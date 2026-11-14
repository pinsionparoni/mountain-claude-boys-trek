"""
The customer's monthly budget and what is safe to spend this week.

Fetches the customer's history through coach/database/queries.py, places each
purchase in a basket with coach/spending_baskets.py, and leaves every sum to
coach/calculations.py. The model only explains the result.

1. Monthly budget, from the customer's last complete months:
   typical income - regular essentials - unexpected reserve - savings
   = everyday ("Arjen kulutus") budget.
2. This month: everyday budget - everyday spending so far, spread over the
   days left in the month.
3. Cash check: the current balance must also cover the bills and other
   essentials due before the next salary. Safe to spend this week is the
   smaller of the budget amount and the cash amount.

"Today" is ``COACH_TODAY`` (an ISO date, for demos) or else the customer's
last transaction date: the data ends in September 2026.
"""

import calendar
import os
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from coach import calculations
from coach.database import queries
from coach.spending_baskets import classify_purchase

HISTORY_MONTHS = 6    # income, essentials, everyday and savings habits
RESERVE_MONTHS = 12   # surprise costs are lumpy, so average them over a year
BILL_CATEGORIES = ("Housing", "Utilities")
_DAYS_PER_AVERAGE_MONTH = Decimal("30.4375")


def coach_today(data_to):
    """The coach's "today": COACH_TODAY if set (never after the data ends), else the last data date."""
    value = os.getenv("COACH_TODAY")
    if not value:
        return data_to
    try:
        today = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"COACH_TODAY must be a date like 2026-09-18, got {value!r}") from None
    return min(today, data_to)


def _add_months(day, months):
    """The first day of the month ``months`` after ``day``'s month (negative goes back)."""
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _on_day(month_start, day_of_month):
    """``day_of_month`` in that month, clamped to its last day (the 31st in February is the 28th/29th)."""
    last = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start.replace(day=min(day_of_month, last))


def _mean(values):
    values = list(values)
    return sum(values, Decimal(0)) / len(values) if values else Decimal(0)


def next_payday(salary_days, today):
    """
    The next date after ``today`` on the customer's most common salary day of
    month, and that day. None when there is no salary history.
    """
    if not salary_days:
        return None, None
    usual = Counter(d.day for d in salary_days).most_common(1)[0][0]
    month = today.replace(day=1)
    payday = _on_day(month, usual)
    if payday <= today:
        payday = _on_day(_add_months(month, 1), usual)
    return payday, usual


def safe_to_spend(customer_id, today):
    """Monthly budget, this month's progress and the cash check, as one JSON-friendly dict."""
    month_start = today.replace(day=1)
    last_complete = month_start - timedelta(days=1)
    history_start = _add_months(month_start, -HISTORY_MONTHS)
    reserve_start = _add_months(month_start, -RESERVE_MONTHS)

    transactions = queries.consumption_transactions(customer_id, reserve_start, today)
    flows = queries.monthly_flows(customer_id, history_start, last_complete)
    paid = queries.salary_dates(customer_id, reserve_start, today)
    balance = queries.balance_as_of(customer_id, today)

    # ---- spending per complete month and basket ------------------------------
    per_month = {}          # month start -> basket -> amount
    bills = {c: [] for c in BILL_CATEGORIES}   # (date, amount) per bill category
    this_month = Counter()  # basket -> amount spent so far this month
    for row in transactions:
        amount = Decimal(str(row["amount_eur"]))
        basket = classify_purchase(row["category"], row["mcc_code"], amount)
        if row["tx_date"] >= month_start:
            this_month[basket] += amount
        else:
            per_month.setdefault(row["tx_date"].replace(day=1), Counter())[basket] += amount
        if row["category"] in bills:
            bills[row["category"]].append((row["tx_date"], amount))

    recent = [_add_months(month_start, -i) for i in range(1, HISTORY_MONTHS + 1)]
    year = [_add_months(month_start, -i) for i in range(1, RESERVE_MONTHS + 1)]
    regular = _mean(per_month.get(m, {}).get("regular_essentials", Decimal(0)) for m in recent)
    everyday_usual = _mean(per_month.get(m, {}).get("everyday_spending", Decimal(0)) for m in recent)
    reserve = _mean(per_month.get(m, {}).get("unexpected_necessities", Decimal(0)) for m in year)

    # ---- income and savings per complete month -------------------------------
    by_month = {m: Counter() for m in recent}
    for row in flows:
        if row["month"] in by_month:
            by_month[row["month"]][row["transaction_type"]] += Decimal(str(row["net_amount_eur"]))
    # Salary sweeps leave the account right after salary, so they are not
    # available for the budget (see spending_baskets.salary_sweep_info).
    income = median(
        f["salary"] + f["other_income"] + f["salary_sweep"] for f in by_month.values()
    ) if by_month else Decimal(0)
    savings = _mean(
        max(-(f["investment_deposit"] + f["investment_withdrawal"]), Decimal(0)) for f in by_month.values()
    )
    has_salary_sweep = any(f["salary_sweep"] for f in by_month.values())

    budget = calculations.monthly_budget(
        monthly_income=max(income, Decimal(0)),
        monthly_regular_essentials=regular,
        monthly_unexpected_reserve=reserve,
        monthly_savings=savings,
    )

    # ---- this month -----------------------------------------------------------
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    progress = calculations.budget_progress(
        everyday_budget=budget["everyday_budget"],
        everyday_spent=this_month["everyday_spending"],
        days_left_in_month=days_in_month - today.day + 1,
    )

    result = {
        "today": today.isoformat(),
        "history": {
            "months": HISTORY_MONTHS,
            "from": history_start.isoformat(),
            "to": last_complete.isoformat(),
            "unexpected_reserve_months": RESERVE_MONTHS,
            "usual_everyday_spending": float(round(everyday_usual, 2)),
        },
        "monthly_budget": budget,
        "this_month": {
            **progress,
            "regular_essentials_spent": float(round(this_month["regular_essentials"], 2)),
            "unexpected_spent": float(round(this_month["unexpected_necessities"], 2)),
        },
        "has_salary_sweep": has_salary_sweep,
    }

    # ---- cash check until the next salary -------------------------------------
    payday, usual_day = next_payday(paid, today)
    if payday is None or balance is None:
        result["cash_check"] = None
        result["safe_to_spend_this_week"] = progress["per_week"]
        result["limited_by"] = "budget"
        return result

    days_to_payday = (payday - today).days
    window_months = {today.replace(day=1), payday.replace(day=1)}

    # Rent: one payment a month on the customer's usual day; due if that day
    # falls after today and before payday, and this month's isn't paid yet.
    rent_due = Decimal(0)
    housing = [(d, a) for d, a in bills["Housing"] if d >= history_start]
    if housing:
        rent = Decimal(str(median(a for _, a in housing)))
        rent_day = int(median(d.day for d, _ in housing))
        paid_this_month = any(d >= month_start for d, _ in housing)
        for m in sorted(window_months):
            due = _on_day(m, rent_day)
            if today < due < payday and not (m == month_start and paid_this_month):
                rent_due += rent

    # Utilities come several times a month and other essentials (groceries,
    # transport, pharmacy) all month, so both are spread over the days.
    utilities = _mean(
        sum((a for d, a in bills["Utilities"] if d.replace(day=1) == m), Decimal(0)) for m in recent
    )
    housing_monthly = _mean(
        sum((a for d, a in bills["Housing"] if d.replace(day=1) == m), Decimal(0)) for m in recent
    )
    other_essentials = max(regular - utilities - housing_monthly, Decimal(0))
    spread = (utilities + other_essentials) * days_to_payday / _DAYS_PER_AVERAGE_MONTH

    cash = calculations.safe_to_spend(
        current_balance=balance,
        days_remaining=days_to_payday,
        committed_expenses=rent_due + spread,
    )
    result["cash_check"] = {
        "current_balance": balance,
        "next_payday": payday.isoformat(),
        "usual_payday_of_month": usual_day,
        "days_to_payday": days_to_payday,
        "rent_due_before_payday": float(round(rent_due, 2)),
        "other_essentials_before_payday": float(round(spread, 2)),
        "left_for_everyday_until_payday": cash["safe_total"],
        "per_week": cash["per_week"],
        "shortfall": cash["shortfall"],
        "enough_cash": cash["per_week"] >= progress["per_week"],
    }
    result["safe_to_spend_this_week"] = min(progress["per_week"], cash["per_week"])
    result["limited_by"] = "budget" if progress["per_week"] <= cash["per_week"] else "cash"
    return result

"""
Deterministic financial calculations for the coach.

Pure Python, standard library only: no database, no network, no AI model.
Every function takes plain euro amounts that the data layer already fetched
and returns JSON-friendly dicts, so the same code can be tested on its own
and later run unchanged inside a Modal sandbox.

Conventions
-----------
- All amounts are euros. Spending, income and reserves are passed as
  positive numbers; only ``current_balance`` may be negative (overdrawn).
- Arithmetic is done in ``Decimal`` and rounded half-up to whole cents only
  at the end, so the numbers shown to a customer are exact.
- Results are never negative where "safe" is meant: if the customer cannot
  afford anything, the safe amount is 0 and the gap is reported separately
  as ``shortfall``.
- Callers are responsible for passing *consumption only* amounts, i.e.
  with salary sweeps, investment flows and income already excluded
  (see ``coach/spending_baskets.py``).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Mapping

Number = int | float | Decimal

_CENT = Decimal("0.01")
_DAYS_PER_WEEK = 7
_MONTHS_PER_YEAR = 12
_DAYS_PER_AVERAGE_MONTH = Decimal("30.4375")  # 365.25 / 12


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _d(name: str, value: Number) -> Decimal:
    """Convert a number to a finite Decimal, rejecting bools and NaN/inf."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{name} must be a finite number")
    return result


def _non_negative(name: str, value: Number) -> Decimal:
    result = _d(name, value)
    if result < 0:
        raise ValueError(f"{name} cannot be negative")
    return result


def _fraction(name: str, value: Number) -> Decimal:
    result = _d(name, value)
    if not Decimal(0) <= result <= Decimal(1):
        raise ValueError(f"{name} must be between 0 and 1")
    return result


def _percent(name: str, value: Number) -> Decimal:
    result = _d(name, value)
    if not Decimal(0) <= result <= Decimal(100):
        raise ValueError(f"{name} must be between 0 and 100")
    return result


def _money(value: Decimal) -> float:
    """Round half-up to whole cents and return a plain float."""
    return float(value.quantize(_CENT, rounding=ROUND_HALF_UP))


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------

def average_monthly(monthly_totals: Iterable[Number]) -> float:
    """
    Mean of monthly totals.

    Pass complete months only; a partial current month would drag the
    average down.
    """
    values = [_d("monthly_totals item", v) for v in monthly_totals]
    if not values:
        raise ValueError("monthly_totals must contain at least one month")
    return _money(sum(values) / len(values))


def prorate_monthly(
    monthly_amount: Number,
    days: int,
    days_in_month: int = 30,
) -> float:
    """Share of a monthly amount that falls in ``days`` days."""
    amount = _non_negative("monthly_amount", monthly_amount)
    if not isinstance(days, int) or days < 0:
        raise ValueError("days must be a non-negative whole number")
    if not isinstance(days_in_month, int) or days_in_month < 1:
        raise ValueError("days_in_month must be a positive whole number")
    return _money(amount * days / days_in_month)


def monthly_equivalent(total: Number, days: int) -> float:
    """
    Convert a total over ``days`` days into an average monthly amount.

    Uses an average month of 30.4375 days (365.25 / 12), so a 90-day total of
    900 EUR is 304.38 EUR per month. ``total`` may be negative (money out).
    """
    amount = _d("total", total)
    if not isinstance(days, int) or isinstance(days, bool) or days < 1:
        raise ValueError("days must be a positive whole number")
    return _money(amount * _DAYS_PER_AVERAGE_MONTH / days)


# --------------------------------------------------------------------------
# Safe to spend
# --------------------------------------------------------------------------

def safe_to_spend(
    *,
    current_balance: Number,
    days_remaining: int,
    expected_income: Number = 0,
    committed_expenses: Number = 0,
    irregular_reserve: Number = 0,
    buffer: Number = 0,
) -> dict:
    """
    How much the customer can spend on everyday things until the horizon ends.

    The horizon is usually "until the next salary" or "until month end".

        available = current_balance
                    + expected_income        (arrives inside the horizon)
                    - committed_expenses     (mandatory regular bills still due)
                    - irregular_reserve      (set aside for surprise costs)
                    - buffer                 (minimum balance to keep)

    ``safe_total`` is ``available`` floored at 0; any gap goes to ``shortfall``.
    ``per_week`` is the allowance for the next 7 days (or fewer if the
    horizon is shorter).
    """
    balance = _d("current_balance", current_balance)
    income = _non_negative("expected_income", expected_income)
    committed = _non_negative("committed_expenses", committed_expenses)
    reserve = _non_negative("irregular_reserve", irregular_reserve)
    keep = _non_negative("buffer", buffer)

    if not isinstance(days_remaining, int) or isinstance(days_remaining, bool):
        raise TypeError("days_remaining must be a whole number")
    if days_remaining < 1:
        raise ValueError("days_remaining must be at least 1")

    available = balance + income - committed - reserve - keep
    safe_total = max(available, Decimal(0))
    shortfall = max(-available, Decimal(0))
    per_day = safe_total / days_remaining
    per_week = per_day * min(_DAYS_PER_WEEK, days_remaining)

    return {
        "safe_total": _money(safe_total),
        "per_day": _money(per_day),
        "per_week": _money(per_week),
        "shortfall": _money(shortfall),
        "days_remaining": days_remaining,
        "components": {
            "current_balance": _money(balance),
            "expected_income": _money(income),
            "committed_expenses": _money(committed),
            "irregular_reserve": _money(reserve),
            "buffer": _money(keep),
        },
    }


# --------------------------------------------------------------------------
# Monthly budget
# --------------------------------------------------------------------------

def monthly_budget(
    *,
    monthly_income: Number,
    monthly_regular_essentials: Number,
    monthly_unexpected_reserve: Number,
    monthly_savings: Number = 0,
) -> dict:
    """
    The customer's everyday-spending budget for a month.

        everyday_budget = income
                          - regular essentials   (rent, bills, groceries, transport)
                          - unexpected reserve   (their average surprise costs)
                          - savings              (what they usually set aside)

    Inputs are typical monthly amounts. ``everyday_budget`` is floored at 0;
    if essentials, reserve and savings exceed income the gap is ``shortfall``.
    """
    income = _non_negative("monthly_income", monthly_income)
    regular = _non_negative("monthly_regular_essentials", monthly_regular_essentials)
    reserve = _non_negative("monthly_unexpected_reserve", monthly_unexpected_reserve)
    savings = _non_negative("monthly_savings", monthly_savings)

    everyday = income - regular - reserve - savings

    return {
        "monthly_income": _money(income),
        "regular_essentials": _money(regular),
        "unexpected_reserve": _money(reserve),
        "savings": _money(savings),
        "everyday_budget": _money(max(everyday, Decimal(0))),
        "shortfall": _money(max(-everyday, Decimal(0))),
    }


def budget_progress(
    *,
    everyday_budget: Number,
    everyday_spent: Number,
    days_left_in_month: int,
) -> dict:
    """
    How much of this month's everyday budget is left, and what that allows per week.

    ``days_left_in_month`` counts today. With a week or less left, ``per_week``
    is the whole remainder.
    """
    budget = _non_negative("everyday_budget", everyday_budget)
    spent = _non_negative("everyday_spent", everyday_spent)

    if not isinstance(days_left_in_month, int) or isinstance(days_left_in_month, bool):
        raise TypeError("days_left_in_month must be a whole number")
    if days_left_in_month < 1:
        raise ValueError("days_left_in_month must be at least 1")

    remaining = budget - spent
    left = max(remaining, Decimal(0))
    per_day = left / days_left_in_month
    per_week = per_day * min(_DAYS_PER_WEEK, days_left_in_month)

    return {
        "everyday_budget": _money(budget),
        "everyday_spent": _money(spent),
        "remaining": _money(left),
        "over_budget": _money(max(-remaining, Decimal(0))),
        "days_left_in_month": days_left_in_month,
        "per_day": _money(per_day),
        "per_week": _money(per_week),
    }


# --------------------------------------------------------------------------
# Safe to save
# --------------------------------------------------------------------------

def safe_to_save(
    *,
    monthly_income: Number,
    monthly_mandatory_regular: Number,
    monthly_mandatory_irregular: Number,
    monthly_everyday: Number,
    cushion_fraction: Number = Decimal("0.2"),
) -> dict:
    """
    How much the customer can move to savings each month.

        surplus = income - (mandatory regular + mandatory irregular + everyday)
        safe_to_save = surplus * (1 - cushion_fraction)

    ``cushion_fraction`` is the share of the surplus deliberately left alone,
    because real spending varies from month to month. Inputs should be
    monthly averages over complete months.
    """
    income = _non_negative("monthly_income", monthly_income)
    regular = _non_negative("monthly_mandatory_regular", monthly_mandatory_regular)
    irregular = _non_negative(
        "monthly_mandatory_irregular", monthly_mandatory_irregular
    )
    everyday = _non_negative("monthly_everyday", monthly_everyday)
    cushion = _fraction("cushion_fraction", cushion_fraction)

    total_spending = regular + irregular + everyday
    surplus = income - total_spending

    if surplus > 0:
        monthly_save = surplus * (1 - cushion)
        shortfall = Decimal(0)
    else:
        monthly_save = Decimal(0)
        shortfall = -surplus

    savings_rate = monthly_save / income if income > 0 else Decimal(0)

    return {
        "safe_to_save_monthly": _money(monthly_save),
        "safe_to_save_yearly": _money(monthly_save * _MONTHS_PER_YEAR),
        "savings_rate": float(savings_rate.quantize(Decimal("0.0001"))),
        "surplus": _money(max(surplus, Decimal(0))),
        "shortfall": _money(shortfall),
        "total_monthly_spending": _money(total_spending),
    }


# --------------------------------------------------------------------------
# What-if scenarios
# --------------------------------------------------------------------------

def what_if_reduce(
    *,
    monthly_spending: Number,
    reduction_pct: Number,
) -> dict:
    """
    What cutting one spending line by ``reduction_pct`` percent would save.

    Example: 235 EUR/month of dining out cut by 20% saves 47 EUR/month,
    564 EUR/year.
    """
    spending = _non_negative("monthly_spending", monthly_spending)
    pct = _percent("reduction_pct", reduction_pct)

    saving = spending * pct / 100

    return {
        "monthly_saving": _money(saving),
        "yearly_saving": _money(saving * _MONTHS_PER_YEAR),
        "current_monthly_spending": _money(spending),
        "new_monthly_spending": _money(spending - saving),
        "reduction_pct": float(pct),
    }


def what_if_reduce_many(
    *,
    monthly_by_category: Mapping[str, Number],
    reductions_pct: Mapping[str, Number],
) -> dict:
    """
    Combined effect of cutting several categories at once.

    ``reductions_pct`` maps category -> percent cut; every category in it
    must exist in ``monthly_by_category``.
    """
    unknown = sorted(set(reductions_pct) - set(monthly_by_category))
    if unknown:
        raise ValueError(f"No spending data for: {', '.join(unknown)}")

    per_category = {}
    total_monthly = Decimal(0)  # exact, unrounded

    for category, pct in reductions_pct.items():
        per_category[category] = what_if_reduce(
            monthly_spending=monthly_by_category[category],
            reduction_pct=pct,
        )
        total_monthly += (
            _non_negative(category, monthly_by_category[category])
            * _percent(f"{category} reduction", pct)
            / 100
        )

    return {
        "monthly_saving": _money(total_monthly),
        "yearly_saving": _money(total_monthly * _MONTHS_PER_YEAR),
        "by_category": per_category,
    }

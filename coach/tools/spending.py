"""
Customer-scoped tools that let the coach read one customer's money data.

The customer is fixed when the tools are created: ``load_tools(customer_id)``.
No tool accepts a customer ID, and unexpected arguments are rejected, so the
model can never read another customer's data, even if it tries.

Seven tools:

- Data (PostgreSQL): ``get_spending_by_category``, ``get_basket_summary``,
  ``get_monthly_balance_trend``.
- Calculations (plain Python, see ``coach/calculations.py``):
  ``calculate_prorated_amount``, ``calculate_safe_to_spend``,
  ``calculate_safe_to_save``, ``calculate_what_if``.

Data tools return monthly averages already computed, and the calculation tools
do the maths, so the model never has to do money arithmetic itself.

Each tool object is a dict (the Anthropic tool definition) with a ``name``
property and a ``run(input)`` method, which is what ``coach/agent.py`` expects.
``run`` returns a JSON string and raises ``ValueError``/``TypeError`` with a
readable message on bad input; the agent passes that message back to the model.
"""

import json
from datetime import date
from decimal import Decimal

from coach import calculations
from coach.database import queries

# First and last day of the S-Pankki dataset, from the full-table audit.
DATA_START = date(2024, 10, 1)
DATA_END = date(2026, 9, 30)

PROMPT = f"""

Customer data tools (the customer is already identified; never ask for or use an ID):
- For anything about the customer's own money, call the tools instead of guessing. \
Use get_spending_by_category for category questions and get_basket_summary for "where does my money go".
- The customer's data runs from {DATA_START.isoformat()} to {DATA_END.isoformat()}. Treat the end of the data as "now": \
"last month" means the last full month in the data and "recently" means the last few months before {DATA_END.isoformat()}. \
Always say which dates you used.
- Never do money arithmetic yourself. Use the monthly_average_eur values the tools return, and use the calculate_* tools \
for safe-to-spend, safe-to-save and what-if questions. Report their numbers exactly as given.
- Baskets: Housing and Utilities are mandatory and regular. Groceries, Restaurants, Transportation, Entertainment, \
Lifestyle and Travel are everyday spending. Health and Home & Tech land in "needs_review": the data cannot tell \
whether they were essential, so ask the customer rather than assuming. Mandatory and irregular stays empty until the \
customer confirms something belongs there.
- Salary, other income, salary sweeps and investments are money movements, not spending. They are never in the baskets.
- If get_basket_summary says has_salary_sweep is true, tell the customer that their mandatory totals may be incomplete, \
using salary_sweep_note.
- For safe-to-spend: the current balance is the latest balance from get_monthly_balance_trend with months=1. \
Turn monthly averages into amounts for the period with calculate_prorated_amount before passing them on."""


class CoachTool(dict):
    """An Anthropic tool definition that can also run itself."""

    def __init__(self, name, description, properties, required, handler):
        super().__init__(
            name=name,
            description=description,
            input_schema={
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        )
        self._handler = handler

    @property
    def name(self):
        return self["name"]

    def run(self, tool_input):
        tool_input = dict(tool_input or {})
        schema = self["input_schema"]

        unexpected = sorted(set(tool_input) - set(schema["properties"]))
        if unexpected:
            raise ValueError(f"unexpected argument(s): {', '.join(unexpected)}")

        missing = [key for key in schema["required"] if key not in tool_input]
        if missing:
            raise ValueError(f"missing required argument(s): {', '.join(missing)}")

        return json.dumps(self._handler(tool_input))


# --------------------------------------------------------------------------
# Input and output helpers
# --------------------------------------------------------------------------

def _parse_date(name, value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a date in YYYY-MM-DD format") from None


def _whole_number(name, value):
    """Accept 7 or 7.0 (models sometimes send floats); reject 7.5 and bools."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"{name} must be a whole number")


def _period(args):
    start = _parse_date("start_date", args["start_date"])
    end = _parse_date("end_date", args["end_date"])
    if start > end:
        raise ValueError("start_date cannot be after end_date")
    return start, end, (end - start).days + 1


def _eur(value):
    return round(float(value), 2)


_DATE_PROPERTIES = {
    "start_date": {
        "type": "string",
        "description": "First day of the period, YYYY-MM-DD (inclusive).",
    },
    "end_date": {
        "type": "string",
        "description": "Last day of the period, YYYY-MM-DD (inclusive).",
    },
}


def _number(description):
    return {"type": "number", "description": description}


# --------------------------------------------------------------------------
# Tool factory
# --------------------------------------------------------------------------

def load_tools(customer_id):
    """Return the coach's spending tools, all scoped to ``customer_id``."""
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise ValueError("customer_id is required")

    # ---- data tools -------------------------------------------------------

    def spending_by_category(args):
        start, end, days = _period(args)
        rows = queries.spending_by_category(customer_id, start, end)

        total = Decimal(0)
        categories = []
        for row in rows:
            amount = Decimal(str(row["total_spending_eur"]))
            total += amount
            categories.append(
                {
                    "category": row["category"],
                    "total_eur": _eur(amount),
                    "monthly_average_eur": calculations.monthly_equivalent(amount, days),
                    "transaction_count": row["transaction_count"],
                }
            )

        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "days": days,
            },
            "categories": categories,
            "total_eur": _eur(total),
            "monthly_average_eur": calculations.monthly_equivalent(total, days),
        }

    def basket_summary(args):
        start, end, days = _period(args)
        summary = queries.basket_summary(customer_id, start, end)

        summary["period"]["days"] = days
        summary["monthly_average_eur"] = calculations.monthly_equivalent(
            summary["total_spending_eur"], days
        )
        for basket in summary["baskets"].values():
            basket["monthly_average_eur"] = calculations.monthly_equivalent(
                basket["total_eur"], days
            )
            for category in basket["categories"]:
                category["monthly_average_eur"] = calculations.monthly_equivalent(
                    category["total_eur"], days
                )
        for flow in summary["financial_flows"]:
            flow["monthly_average_eur"] = calculations.monthly_equivalent(
                flow["net_amount_eur"], days
            )
        return summary

    def monthly_balance_trend(args):
        months = _whole_number("months", args.get("months", 6))
        rows = queries.monthly_balance_trend(customer_id, months)
        return {
            "balances": [
                {
                    "month": row["month"].isoformat()[:7],
                    "balance_eur": _eur(row["balance_eur"]),
                }
                for row in rows
            ],
            "note": (
                "balance_eur is the account balance after the customer's last "
                "transaction in that month."
            ),
        }

    # ---- calculation tools ------------------------------------------------

    def prorated_amount(args):
        days_in_month = _whole_number("days_in_month", args.get("days_in_month", 30))
        return {
            "amount_eur": calculations.prorate_monthly(
                args["monthly_amount"],
                _whole_number("days", args["days"]),
                days_in_month,
            )
        }

    def safe_to_spend(args):
        optional = ("expected_income", "committed_expenses", "irregular_reserve", "buffer")
        return calculations.safe_to_spend(
            current_balance=args["current_balance"],
            days_remaining=_whole_number("days_remaining", args["days_remaining"]),
            **{key: args[key] for key in optional if key in args},
        )

    def safe_to_save(args):
        optional = {"cushion_fraction": args["cushion_fraction"]} if "cushion_fraction" in args else {}
        return calculations.safe_to_save(
            monthly_income=args["monthly_income"],
            monthly_mandatory_regular=args["monthly_mandatory_regular"],
            monthly_mandatory_irregular=args["monthly_mandatory_irregular"],
            monthly_everyday=args["monthly_everyday"],
            **optional,
        )

    def what_if(args):
        return calculations.what_if_reduce_many(
            monthly_by_category=args["monthly_by_category"],
            reductions_pct=args["reductions_pct"],
        )

    return [
        CoachTool(
            name="get_spending_by_category",
            description=(
                "The customer's real spending per category over a period, largest first, with totals, "
                "monthly averages and transaction counts. Only consumption counts: salary, income, "
                "salary sweeps and investments are excluded."
            ),
            properties=dict(_DATE_PROPERTIES),
            required=["start_date", "end_date"],
            handler=spending_by_category,
        ),
        CoachTool(
            name="get_basket_summary",
            description=(
                "The customer's spending grouped into the three baskets (mandatory regular, mandatory "
                "irregular, everyday) plus needs_review for spending whose purpose is unknown. Includes "
                "shares, per-category breakdown, monthly averages, and separately the money movements "
                "(income, salary sweeps, investments) with has_salary_sweep and a caveat when salary "
                "leaves the account."
            ),
            properties=dict(_DATE_PROPERTIES),
            required=["start_date", "end_date"],
            handler=basket_summary,
        ),
        CoachTool(
            name="get_monthly_balance_trend",
            description=(
                "The customer's account balance at the end of each of the last N months of their data "
                "(oldest first). Use months=1 to get the current balance."
            ),
            properties={
                "months": {
                    "type": "integer",
                    "description": "How many months back to include, 1 to 24. Default 6.",
                    "minimum": 1,
                    "maximum": 24,
                }
            },
            required=[],
            handler=monthly_balance_trend,
        ),
        CoachTool(
            name="calculate_prorated_amount",
            description=(
                "Share of a monthly amount that falls in a number of days, for example the part of a "
                "monthly bill budget that is due in the next 10 days."
            ),
            properties={
                "monthly_amount": _number("The monthly amount in EUR, not negative."),
                "days": {"type": "integer", "description": "Number of days."},
                "days_in_month": {
                    "type": "integer",
                    "description": "Days in the month used for the share. Default 30.",
                },
            },
            required=["monthly_amount", "days"],
            handler=prorated_amount,
        ),
        CoachTool(
            name="calculate_safe_to_spend",
            description=(
                "How much the customer can spend on everyday things until the end of a period (for "
                "example until the next salary). Returns safe_total, per_day, per_week and any shortfall. "
                "All amounts are for the period, in EUR, and not negative except current_balance."
            ),
            properties={
                "current_balance": _number("Current account balance in EUR. May be negative."),
                "days_remaining": {
                    "type": "integer",
                    "description": "Days left in the period, at least 1.",
                    "minimum": 1,
                },
                "expected_income": _number("Income arriving inside the period. Default 0."),
                "committed_expenses": _number(
                    "Mandatory regular bills still due inside the period. Default 0."
                ),
                "irregular_reserve": _number(
                    "Amount set aside for surprise costs in the period. Default 0."
                ),
                "buffer": _number("Minimum balance the customer wants to keep. Default 0."),
            },
            required=["current_balance", "days_remaining"],
            handler=safe_to_spend,
        ),
        CoachTool(
            name="calculate_safe_to_save",
            description=(
                "How much the customer can move to savings each month: monthly income minus all monthly "
                "spending, keeping a cushion of the surplus. Returns monthly and yearly amounts, the "
                "savings rate and any shortfall. All inputs are monthly averages in EUR, not negative."
            ),
            properties={
                "monthly_income": _number("Average monthly income (salary plus other income)."),
                "monthly_mandatory_regular": _number("Average monthly mandatory regular spending."),
                "monthly_mandatory_irregular": _number("Average monthly mandatory irregular spending."),
                "monthly_everyday": _number("Average monthly everyday spending."),
                "cushion_fraction": {
                    "type": "number",
                    "description": "Share of the surplus to leave untouched, 0 to 1. Default 0.2.",
                    "minimum": 0,
                    "maximum": 1,
                },
            },
            required=[
                "monthly_income",
                "monthly_mandatory_regular",
                "monthly_mandatory_irregular",
                "monthly_everyday",
            ],
            handler=safe_to_save,
        ),
        CoachTool(
            name="calculate_what_if",
            description=(
                "What cutting one or more spending categories by a percentage would save, per month and "
                "per year. Use monthly averages from the data tools."
            ),
            properties={
                "monthly_by_category": {
                    "type": "object",
                    "description": "Category name to average monthly spending in EUR.",
                    "additionalProperties": {"type": "number"},
                },
                "reductions_pct": {
                    "type": "object",
                    "description": "Category name to percent cut, 0 to 100. Every name must be in monthly_by_category.",
                    "additionalProperties": {"type": "number"},
                },
            },
            required=["monthly_by_category", "reductions_pct"],
            handler=what_if,
        ),
    ]

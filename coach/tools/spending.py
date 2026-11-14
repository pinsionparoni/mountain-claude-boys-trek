"""
Customer-scoped tools that let the coach read one customer's money data.

The customer is fixed when the tools are created: ``load_tools(customer_id)``.
No tool accepts a customer ID, and unexpected arguments are rejected, so the
model can never read another customer's data, even if it tries.

Eight tools:

- Data (PostgreSQL): ``get_spending_by_category``, ``get_basket_summary``,
  ``get_monthly_balance_trend``, ``get_transactions``.
- Budget (``coach/budget.py``): ``get_safe_to_spend``: the monthly budget,
  this month's progress and a cash check until payday, all computed in Python.
- Peers (``coach/peers.py``): ``compare_with_peers``: the customer's spending
  against people their age and everyone, as medians and ranks only.
- Calculations (plain Python, see ``coach/calculations.py``):
  ``calculate_safe_to_save``, ``calculate_what_if``.

Data never goes past the coach's "today" (``load_tools(customer_id, today)``),
so a demo date set with COACH_TODAY behaves like the real present.

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

from coach import budget, calculations, peers, spending_baskets
from coach.database import queries

# First and last day of the S-Pankki dataset, from the full-table audit.
DATA_START = date(2024, 10, 1)
DATA_END = date(2026, 9, 30)

PROMPT = f"""

Customer data tools (the customer is already identified; never ask for or use an ID):
- For anything about the customer's own money, call the tools instead of guessing. \
Use get_spending_by_category for category questions and get_basket_summary for "where does my money go".
- Dates are relative to "today" (given above): "this month" is today's month, "last month" the month before it. \
The tools never return anything after today. Always say which dates you used.
- Never do money arithmetic yourself. Use the numbers the tools return and report them as given.
- For "what can I spend", "how much is left" or anything about a budget, call get_safe_to_spend. It returns the \
monthly budget (income minus regular essentials, an unexpected-costs reserve and usual savings), how much of the \
everyday budget is left this month, and a cash check until the next salary. Lead with safe_to_spend_this_week, \
explain it from the monthly budget, and if limited_by is "cash" or this_month.over_budget is above 0, say so kindly. \
Use calculate_safe_to_save and calculate_what_if for saving and what-if questions.
- Baskets: in English use S-Bank's names: "🏠 Regular essentials", "🔧 Unexpected necessities" and \
"☕ Everyday spending". In Finnish use: "🏠 Välttämättömät menot", "🔧 Yllättävät menot" and "☕ Arjen kulutus". get_basket_summary places every purchase by merchant type: e.g. fuel, parking and public \
transport are regular essentials, taxis are everyday spending, doctors and dentists are unexpected necessities, and \
large one-off Health or Home & Tech purchases are unexpected necessities. Purchases without a merchant type are \
"other". Explain the placement when it matters and that the customer can see things differently.
- For questions about one kind of merchant (taxis, fuel, pharmacies, cafés), call get_spending_by_category with \
that category to get its merchant types. Mention unusual_purchases when they explain a month.
- For "what kind of spender am I?", "is my spending normal?" or comparisons with other people, call compare_with_peers. \
Lead with profile.overall_level and the total against people their age, then the categories in profile.above_peers and \
profile.below_peers. For above_peers use spends_more_than_pct_of_peers ("you spend more on restaurants than 80% of \
people aged 18–24"); for below_peers use spends_less_than_pct_of_peers ("you spend less on travel than 77% of people \
your age"). Report these numbers as given; never subtract them yourself. \
Name the age group and the period. Describe habits kindly and without judging; spending less is not always better. \
Rent and utilities are left out of the profile because they reflect living situation; mention them only if asked. \
Spending less than peers does not mean the customer has money to spare: before suggesting they have room to spend, \
save or treat themselves, call get_safe_to_spend and base the suggestion on it.
- Salary, other income, salary sweeps and investments are money movements, not spending. They are never in the baskets.
- If get_basket_summary says has_salary_sweep is true, tell the customer that their mandatory totals may be incomplete, \
using salary_sweep_note."""


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


def _period(args, today=None):
    """Parse the period; with ``today``, an end date after today is moved back to today."""
    start = _parse_date("start_date", args["start_date"])
    end = _parse_date("end_date", args["end_date"])
    if today is not None:
        if start > today:
            raise ValueError(f"start_date is after today ({today.isoformat()}); there is no data yet")
        end = min(end, today)
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


_CATEGORY_PROPERTY = {
    "type": "string",
    "description": "One spending category.",
    "enum": sorted([*spending_baskets.CATEGORY_BASKETS, *spending_baskets.OTHER_BASKETS]),
}


def _category(args):
    """The optional category argument, checked so a typo gets a helpful error instead of no data."""
    category = args.get("category")
    if category is not None and category not in _CATEGORY_PROPERTY["enum"]:
        raise ValueError(
            f"unknown category {category!r}; use one of: {', '.join(_CATEGORY_PROPERTY['enum'])}. "
            "For merchant types such as taxis, pass their category (Transportation)."
        )
    return category


def _number(description):
    return {"type": "number", "description": description}


# --------------------------------------------------------------------------
# Tool factory
# --------------------------------------------------------------------------

def load_tools(customer_id, today=None):
    """
    Return the coach's spending tools, all scoped to ``customer_id``.

    ``today`` is the coach's "today" (see coach/budget.py): tools never return
    data after it. None means the end of the dataset.
    """
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise ValueError("customer_id is required")
    today = today or DATA_END

    # ---- data tools -------------------------------------------------------

    def spending_by_category(args):
        start, end, days = _period(args, today)
        category = _category(args)
        if category is not None:
            transactions = queries.consumption_transactions(customer_id, start, end)
            types = spending_baskets.merchant_breakdown(transactions, category)
            total = sum((Decimal(str(m["total_eur"])) for m in types), Decimal(0))
            for m in types:
                m["monthly_average_eur"] = calculations.monthly_equivalent(m["total_eur"], days)
            return {
                "period": {"start_date": start.isoformat(), "end_date": end.isoformat(), "days": days},
                "category": category,
                "merchant_types": types,
                "total_eur": _eur(total),
                "monthly_average_eur": calculations.monthly_equivalent(total, days),
            }

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
        start, end, days = _period(args, today)
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
        rows = queries.monthly_balance_trend(customer_id, months, as_of=today)
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

    def transactions(args):
        start, end, _ = _period(args, today)
        limit = _whole_number("limit", args.get("limit", 20))
        rows = queries.list_transactions(
            customer_id, start, end,
            category=_category(args), order=args.get("order", "largest"), limit=limit,
        )
        return {
            "transactions": [
                {
                    "timestamp": row["tx_timestamp"].isoformat(timespec="minutes"),
                    "category": row["category"],
                    "merchant_type": (spending_baskets.merchant_type(row["mcc_code"], row["category"])
                                      if spending_baskets.is_consumption_transaction(row["transaction_type"])
                                      else None),
                    "amount_eur": _eur(row["amount_eur"]),
                    "balance_after_eur": _eur(row["balance_after_eur"]),
                }
                for row in rows
            ],
            "note": "amount_eur is signed: negative is money out.",
        }

    # ---- calculation tools ------------------------------------------------

    def safe_to_spend(args):
        return budget.safe_to_spend(customer_id, today)

    def safe_to_save(args):
        optional = {"cushion_fraction": args["cushion_fraction"]} if "cushion_fraction" in args else {}
        return calculations.safe_to_save(
            monthly_income=args["monthly_income"],
            monthly_mandatory_regular=args["monthly_mandatory_regular"],
            monthly_mandatory_irregular=args["monthly_mandatory_irregular"],
            monthly_everyday=args["monthly_everyday"],
            **optional,
        )

    def peer_comparison(args):
        return peers.compare(customer_id, today)

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
                "salary sweeps and investments are excluded. With a category, that category split by merchant "
                "type instead (e.g. Transportation -> fuel, parking, public transport, taxi, other), each with "
                "the basket(s) it counts in."
            ),
            properties={**_DATE_PROPERTIES, "category": _CATEGORY_PROPERTY},
            required=["start_date", "end_date"],
            handler=spending_by_category,
        ),
        CoachTool(
            name="get_basket_summary",
            description=(
                "The customer's spending grouped into S-Bank's three baskets (regular_essentials, "
                "unexpected_necessities, everyday_spending), each with its label, share, monthly average and "
                "categories split by merchant type, plus unusual_purchases (large one-off purchases). "
                "Separately the money movements (income, salary sweeps, investments) with has_salary_sweep and "
                "a caveat when salary leaves the account."
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
            name="get_transactions",
            description=(
                "Individual transactions in a period: the largest money out first, or the latest first. "
                "Optionally one category. Use for 'what were my biggest purchases' or to explain a total."
            ),
            properties={
                **_DATE_PROPERTIES,
                "category": _CATEGORY_PROPERTY,
                "order": {"type": "string", "enum": ["largest", "latest"],
                          "description": "Default largest."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50,
                          "description": "How many transactions, default 20."},
            },
            required=["start_date", "end_date"],
            handler=transactions,
        ),
        CoachTool(
            name="get_safe_to_spend",
            description=(
                "What the customer can safely spend this week, from a monthly budget. Returns "
                "monthly_budget (typical income minus regular essentials, an unexpected-costs reserve and "
                "usual savings, leaving the everyday budget), this_month (everyday budget left, per week and "
                "per day, over_budget), cash_check (balance, next payday, rent and essentials still due before "
                "it) and safe_to_spend_this_week: the smaller of the budget and cash amounts, with limited_by "
                "saying which. Everything is computed; just explain it."
            ),
            properties={},
            required=[],
            handler=safe_to_spend,
        ),
        CoachTool(
            name="compare_with_peers",
            description=(
                "How the customer's spending compares with people their age (Statistics Finland age bands) "
                "and with all customers, over the last 12 complete months. Per category and in total: "
                "my_monthly, the peer median and typical range, difference_from_median_pct, "
                "spends_more_than_pct_of_peers and a level (above_peers, typical, below_peers). profile lists "
                "the habits that stand out against the age group, largest first; rent and utilities are left "
                "out of it. Only aggregates; no other customer's data. Everything is computed; just explain it."
            ),
            properties={},
            required=[],
            handler=peer_comparison,
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

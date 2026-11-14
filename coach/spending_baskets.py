"""
What counts as spending, and which of S-Bank's three baskets it belongs to.

Rules (see BASKETS.md for the reasoning and open questions):

1. Only consumption transaction types are spending. Salary, other income,
   investments and salary sweeps are money movements, never in a basket.
2. Bills (Housing, Utilities) go by category.
3. Large one-off purchases in Health and Home & Tech are unexpected
   necessities, whatever the merchant type. Large purchases elsewhere keep
   their basket but are reported as unusual.
4. Card purchases go by merchant type (MCC).
5. Purchases without an MCC are "other" within their category and go to the
   basket most of that category's known merchant types belong to.

A customer's own choice (``basket_overrides``) wins over all of these.
"""

from decimal import ROUND_HALF_UP, Decimal

# The three baskets, with S-Bank's names from the challenge brief.
BASKET_LABELS = {
    "regular_essentials": "🏠 Regular essentials",
    "unexpected_necessities": "🔧 Unexpected necessities",
    "everyday_spending": "☕ Everyday spending",
}
BASKET_KEYS = tuple(BASKET_LABELS)
BASKET_LABELS_FI = {
    "regular_essentials": "🏠 Välttämättömät menot",
    "unexpected_necessities": "🔧 Yllättävät menot",
    "everyday_spending": "☕ Arjen kulutus",
}

# Spending we cannot place (a category the rules don't know). Shown only when
# non-empty, never silently put into a basket.
UNCLASSIFIED = "unclassified"

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

UNCLASSIFIED_FINANCIAL_FLOW_NOTES = {
    "salary_sweep": (
        "Recurring salary-linked outgoing flow; destination and purpose unknown."
    ),
}

_R, _U, _E = BASKET_KEYS

# Bills and other non-card spending: placed by category.
CATEGORY_BASKETS = {
    "Housing": _R,
    "Utilities": _R,
}

# Card purchases: placed by merchant category code. MCC codes are strings
# because the database column is text. Labels are what the customer sees.
MERCHANT_TYPES = {
    # Groceries
    "5411": ("supermarket", _R),
    "5422": ("butcher", _R),
    "5451": ("dairy shop", _R),
    "5499": ("convenience / specialty food", _E),
    # Transportation
    "5542": ("fuel", _R),
    "5541": ("service station", _R),
    "7523": ("parking", _R),
    "4111": ("public transport", _R),
    "4121": ("taxi", _E),
    # Health
    "5912": ("pharmacy", _R),
    "8011": ("doctor", _U),
    "8021": ("dentist", _U),
    "8099": ("medical services", _U),
    # Home & Tech
    "5200": ("home supply store", _U),
    "5251": ("hardware store", _U),
    "5732": ("electronics", _U),
    "5712": ("furniture", _U),
    "5734": ("software", _U),
    # Restaurants
    "5812": ("restaurant", _E),
    "5813": ("bar", _E),
    "5814": ("fast food / café", _E),
    # Entertainment
    "7922": ("tickets / events", _E),
    "7999": ("recreation", _E),
    "7832": ("cinema", _E),
    "7991": ("attractions", _E),
    "7996": ("amusement park", _E),
    # Lifestyle
    "5941": ("sporting goods", _E),
    "5651": ("clothing", _E),
    "5691": ("clothing", _E),
    "5999": ("other retail", _E),
    "5942": ("bookstore", _E),
    "5945": ("hobby / toys", _E),
    # Travel
    "4722": ("travel agency", _E),
    "4511": ("airline", _E),
    "7011": ("hotel", _E),
    "7512": ("car rental", _E),
}

OTHER_MERCHANT_TYPE = "other"
BILL = "bill"  # non-card spending (Housing, Utilities): there is no merchant

# Card purchases without an MCC: the basket most of the category's known
# merchant types belong to (shares from DATA.md).
OTHER_BASKETS = {
    "Groceries": _R,
    "Transportation": _R,   # ~89% of known transport is fuel, parking, public transport
    "Health": _R,           # pharmacy is ~62% of known health purchases
    "Home & Tech": _U,
    "Restaurants": _E,
    "Entertainment": _E,
    "Lifestyle": _E,
    "Travel": _E,
}

# Median purchase per category across all customers (DATA.md, Oct 2024 - Sep
# 2026). A purchase of LARGE_PURCHASE_FACTOR times the median or more is large.
CATEGORY_MEDIAN_EUR = {
    "Groceries": Decimal("64.06"),
    "Restaurants": Decimal("23.49"),
    "Transportation": Decimal("41.26"),
    "Entertainment": Decimal("35.20"),
    "Health": Decimal("53.85"),
    "Home & Tech": Decimal("111.08"),
    "Lifestyle": Decimal("103.31"),
    "Travel": Decimal("129.66"),
}
LARGE_PURCHASE_FACTOR = 10

# Categories where a large purchase is an unexpected necessity (a dentist
# bill, a new washing machine). Elsewhere a large purchase is only "unusual".
LARGE_IS_UNEXPECTED = {"Health", "Home & Tech"}


def is_consumption_transaction(transaction_type):
    """Return True only for known consumption transaction types."""
    return transaction_type in CONSUMPTION_TRANSACTION_TYPES


def merchant_type(mcc_code, category=None):
    """Customer-facing merchant type: "bill" for bill categories, "other" when the MCC is missing or unknown."""
    if category in CATEGORY_BASKETS:
        return BILL
    entry = MERCHANT_TYPES.get(mcc_code)
    return entry[0] if entry else OTHER_MERCHANT_TYPE


def times_usual(category, amount_eur):
    """How many times the category's median purchase this amount is, or None if unknown."""
    median = CATEGORY_MEDIAN_EUR.get(category)
    if not median:
        return None
    return Decimal(str(amount_eur)) / median


def is_large_purchase(category, amount_eur):
    ratio = times_usual(category, amount_eur)
    return ratio is not None and ratio >= LARGE_PURCHASE_FACTOR


def classify_purchase(category, mcc_code, amount_eur, basket_overrides=None):
    """Return the basket key for one consumption transaction (rules 2-5 above)."""
    override = (basket_overrides or {}).get(category)
    if override in BASKET_KEYS:
        return override

    if category in CATEGORY_BASKETS:
        return CATEGORY_BASKETS[category]

    if category in LARGE_IS_UNEXPECTED and is_large_purchase(category, amount_eur):
        return _U

    entry = MERCHANT_TYPES.get(mcc_code)
    if entry:
        return entry[1]

    return OTHER_BASKETS.get(category, UNCLASSIFIED)


def classify_transaction(category, transaction_type, mcc_code=None, amount_eur=0, basket_overrides=None):
    """Return the basket key for any transaction, or None if it is not consumption."""
    if not is_consumption_transaction(transaction_type):
        return None
    return classify_purchase(category, mcc_code, amount_eur, basket_overrides)


def _eur(value):
    """Round a Decimal half-up to whole cents and return a plain float."""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def summarize_baskets(transactions, basket_overrides=None):
    """
    Group consumption transactions into the baskets.

    ``transactions`` are rows shaped like the output of
    ``queries.consumption_transactions``: ``tx_date``, ``category``,
    ``mcc_code`` and ``amount_eur`` (money out as a positive number).
    ``basket_overrides`` optionally maps a category to the basket key the
    customer chose for it.

    Each basket has its label, total, share, count and categories, each
    category broken down by merchant type. The three baskets are always
    present; "unclassified" only when something could not be placed.
    ``unusual_purchases`` lists large one-off purchases, largest first.
    """
    totals = {}
    unusual = []

    for row in transactions:
        category = row["category"]
        amount = Decimal(str(row["amount_eur"]))
        basket = classify_purchase(category, row["mcc_code"], amount, basket_overrides)

        b = totals.setdefault(basket, {"total": Decimal(0), "count": 0, "categories": {}})
        b["total"] += amount
        b["count"] += 1
        c = b["categories"].setdefault(category, {"total": Decimal(0), "types": {}})
        c["total"] += amount
        mtype = merchant_type(row["mcc_code"], category)
        t = c["types"].setdefault(mtype, [Decimal(0), 0])
        t[0] += amount
        t[1] += 1

        if is_large_purchase(category, amount):
            unusual.append({
                "date": row["tx_date"].isoformat(),
                "category": category,
                "merchant_type": mtype,
                "amount_eur": _eur(amount),
                "times_usual": float(times_usual(category, amount).quantize(Decimal("0.1"))),
                "basket": basket,
            })

    grand_total = sum((b["total"] for b in totals.values()), Decimal(0))
    keys = list(BASKET_KEYS) + ([UNCLASSIFIED] if UNCLASSIFIED in totals else [])

    baskets = {}
    for key in keys:
        b = totals.get(key, {"total": Decimal(0), "count": 0, "categories": {}})
        share = b["total"] / grand_total * 100 if grand_total else Decimal(0)
        categories = [
            {
                "category": name,
                "total_eur": _eur(c["total"]),
                "merchant_types": sorted(
                    ({"merchant_type": m, "total_eur": _eur(v[0]), "transaction_count": v[1]}
                     for m, v in c["types"].items()),
                    key=lambda m: m["total_eur"], reverse=True,
                ),
            }
            for name, c in b["categories"].items()
        ]
        baskets[key] = {
            "label": BASKET_LABELS.get(key, "Unclassified"),
            "label_fi": BASKET_LABELS_FI.get(key, "Luokittelematon"),
            "total_eur": _eur(b["total"]),
            "share_pct": float(share.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "transaction_count": b["count"],
            "categories": sorted(categories, key=lambda c: c["total_eur"], reverse=True),
        }

    return {
        "baskets": baskets,
        "total_spending_eur": _eur(grand_total),
        "unusual_purchases": sorted(unusual, key=lambda u: u["amount_eur"], reverse=True),
    }


def merchant_breakdown(transactions, category):
    """Spending in one category per merchant type, with each type's basket, largest first."""
    types = {}
    for row in transactions:
        if row["category"] != category:
            continue
        amount = Decimal(str(row["amount_eur"]))
        mtype = merchant_type(row["mcc_code"], category)
        t = types.setdefault(mtype, {"total": Decimal(0), "count": 0, "baskets": set()})
        t["total"] += amount
        t["count"] += 1
        t["baskets"].add(classify_purchase(category, row["mcc_code"], amount))
    return sorted(
        ({"merchant_type": m, "total_eur": _eur(t["total"]), "transaction_count": t["count"],
          "baskets": sorted(t["baskets"])}
         for m, t in types.items()),
        key=lambda m: m["total_eur"], reverse=True,
    )


def salary_sweep_info(flow_rows):
    """
    Describe a customer's salary sweeps from ``financial_flows`` rows.

    A salary sweep moves money out of the account to a destination we do not
    know. If it pays rent or bills, those costs never appear in this account's
    baskets, so the mandatory totals can be incomplete. Returns:

    - ``has_salary_sweep``: True when the period contains any sweep.
    - ``swept_share_of_salary_pct``: swept amount as a percentage of salary
      received in the period, or None when there is no salary to compare to.
    - ``salary_sweep_note``: a plain-language caveat, or None without sweeps.
    """
    by_type = {row["transaction_type"]: row for row in flow_rows}
    sweep = by_type.get("salary_sweep")

    if not sweep or not sweep["transaction_count"]:
        return {
            "has_salary_sweep": False,
            "swept_share_of_salary_pct": None,
            "salary_sweep_note": None,
        }

    swept = abs(Decimal(str(sweep["net_amount_eur"])))
    salary = Decimal(0)
    if "salary" in by_type:
        salary = Decimal(str(by_type["salary"]["net_amount_eur"]))

    share = None
    if salary > 0:
        share = (swept / salary * 100).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    share_text = f" ({share}% of salary in this period)" if share is not None else ""
    note = (
        f"Salary sweeps{share_text} leave this account for a destination we "
        "do not know. If that money pays rent, bills or other regular costs, "
        "those costs are missing here, so treat the mandatory totals as a "
        "minimum."
    )

    return {
        "has_salary_sweep": True,
        "swept_share_of_salary_pct": float(share) if share is not None else None,
        "salary_sweep_note": note,
    }

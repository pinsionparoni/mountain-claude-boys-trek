"""
Tests for coach/tools/spending.py (no database, no AI model).

The data functions in coach.database.queries are replaced with fakes, so
these tests check the tool layer: customer scoping, input checking, monthly
averages, and that the calculation tools return the tested numbers.

    python -m pytest tests/test_spending_tools.py
"""

import json
from datetime import date
from decimal import Decimal

import pytest

# tests/conftest.py stubs psycopg and dotenv if they are not installed.
from coach.database import queries
from coach.tools import spending

EXPECTED_TOOLS = {
    "get_spending_by_category",
    "get_basket_summary",
    "get_monthly_balance_trend",
    "get_transactions",
    "get_safe_to_spend",
    "calculate_safe_to_save",
    "calculate_what_if",
    "compare_with_peers",
    "show_chart",
}

Q1 = {"start_date": "2026-01-01", "end_date": "2026-03-31"}  # 90 days


@pytest.fixture
def tools():
    return {tool.name: tool for tool in spending.load_tools("CUST42")}


def run(tools, name, arguments):
    return json.loads(tools[name].run(arguments))


# --------------------------------------------------------------------------
# Definitions and customer scoping
# --------------------------------------------------------------------------

def test_load_tools_creates_every_tool(tools):
    assert set(tools) == EXPECTED_TOOLS


@pytest.mark.parametrize("customer_id", ["", "   ", None, 123])
def test_load_tools_requires_a_customer(customer_id):
    with pytest.raises(ValueError):
        spending.load_tools(customer_id)


def test_tool_definitions_are_valid_json_for_the_api(tools):
    for tool in tools.values():
        definition = json.loads(json.dumps(tool))  # plain, serialisable dict
        assert set(definition) == {"name", "description", "input_schema"}
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) <= set(schema["properties"])


def test_no_tool_lets_the_model_choose_a_customer(tools):
    for tool in tools.values():
        assert not any("customer" in key for key in tool["input_schema"]["properties"])


@pytest.mark.parametrize("name", sorted(EXPECTED_TOOLS))
def test_a_customer_id_argument_is_rejected(tools, name):
    with pytest.raises(ValueError, match="unexpected argument"):
        tools[name].run({"customer_id": "SOMEONE_ELSE"})


def test_tools_query_only_the_loaded_customer(tools, monkeypatch):
    seen = []

    def fake_spending(customer_id, start, end):
        seen.append((customer_id, start, end))
        return []

    monkeypatch.setattr(queries, "spending_by_category", fake_spending)
    run(tools, "get_spending_by_category", Q1)

    assert seen == [("CUST42", date(2026, 1, 1), date(2026, 3, 31))]


def test_missing_required_arguments_are_reported(tools):
    with pytest.raises(ValueError, match="missing required argument"):
        tools["get_spending_by_category"].run({"start_date": "2026-01-01"})


def test_prompt_names_the_baskets_in_english_and_finnish():
    for name in ("Regular essentials", "Unexpected necessities", "Everyday spending",
                 "Välttämättömät menot", "Yllättävät menot", "Arjen kulutus"):
        assert name in spending.PROMPT
    assert "get_safe_to_spend" in spending.PROMPT


def test_tools_default_to_the_end_of_the_data():
    assert spending.DATA_END == date(2026, 9, 30)


def test_periods_stop_at_today(monkeypatch):
    seen = []
    monkeypatch.setattr(queries, "spending_by_category",
                        lambda customer_id, start, end: seen.append((start, end)) or [])
    tools = {t.name: t for t in spending.load_tools("CUST42", today=date(2026, 9, 18))}

    result = run(tools, "get_spending_by_category", {"start_date": "2026-09-01", "end_date": "2026-09-30"})

    assert seen == [(date(2026, 9, 1), date(2026, 9, 18))]
    assert result["period"]["end_date"] == "2026-09-18"
    with pytest.raises(ValueError, match="after today"):
        tools["get_spending_by_category"].run({"start_date": "2026-09-20", "end_date": "2026-09-30"})


# --------------------------------------------------------------------------
# get_spending_by_category
# --------------------------------------------------------------------------

def test_spending_tool_adds_monthly_averages(tools, monkeypatch):
    monkeypatch.setattr(
        queries,
        "spending_by_category",
        lambda *args: [
            {"category": "Groceries", "total_spending_eur": Decimal("900.00"), "transaction_count": 9},
            {"category": "Travel", "total_spending_eur": Decimal("90.00"), "transaction_count": 1},
        ],
    )

    result = run(tools, "get_spending_by_category", Q1)

    assert result["period"] == {"start_date": "2026-01-01", "end_date": "2026-03-31", "days": 90}
    assert result["categories"][0] == {
        "category": "Groceries",
        "total_eur": 900.0,
        "monthly_average_eur": 304.38,  # 900 * 30.4375 / 90 = 304.375
        "transaction_count": 9,
    }
    assert result["categories"][1]["monthly_average_eur"] == 30.44
    assert result["total_eur"] == 990.0
    assert result["monthly_average_eur"] == 334.81  # 990 * 30.4375 / 90 = 334.8125


@pytest.mark.parametrize(
    "arguments",
    [
        {"start_date": "01/01/2026", "end_date": "2026-03-31"},
        {"start_date": "2026-01-01", "end_date": "not a date"},
        {"start_date": "2026-03-31", "end_date": "2026-01-01"},
    ],
)
def test_spending_tool_rejects_bad_dates(tools, monkeypatch, arguments):
    monkeypatch.setattr(queries, "spending_by_category", lambda *args: [])
    with pytest.raises(ValueError):
        tools["get_spending_by_category"].run(arguments)


def test_spending_tool_breaks_a_category_down_by_merchant_type(tools, monkeypatch):
    monkeypatch.setattr(
        queries,
        "consumption_transactions",
        lambda *args: [
            {"tx_date": date(2026, 1, 5), "category": "Transportation", "mcc_code": "4121", "amount_eur": Decimal("90.00")},
            {"tx_date": date(2026, 1, 6), "category": "Transportation", "mcc_code": "4111", "amount_eur": Decimal("45.00")},
            {"tx_date": date(2026, 1, 7), "category": "Restaurants", "mcc_code": "5812", "amount_eur": Decimal("20.00")},
        ],
    )

    result = run(tools, "get_spending_by_category", {**Q1, "category": "Transportation"})

    assert result["category"] == "Transportation"
    assert result["total_eur"] == 135.0
    assert result["merchant_types"][0] == {
        "merchant_type": "taxi",
        "total_eur": 90.0,
        "transaction_count": 1,
        "baskets": ["everyday_spending"],
        "monthly_average_eur": 30.44,
    }
    assert result["merchant_types"][1]["baskets"] == ["regular_essentials"]


def test_spending_tool_rejects_an_unknown_category(tools):
    with pytest.raises(ValueError):
        tools["get_spending_by_category"].run({**Q1, "category": "Taxis"})


# --------------------------------------------------------------------------
# get_basket_summary
# --------------------------------------------------------------------------

def test_basket_tool_adds_averages_and_sweep_warning(tools, monkeypatch):
    monkeypatch.setattr(
        queries,
        "consumption_transactions",
        lambda *args: [
            {"tx_date": date(2026, 1, 5), "category": "Housing", "mcc_code": None, "amount_eur": Decimal("900.00")},
            {"tx_date": date(2026, 1, 9), "category": "Restaurants", "mcc_code": "5812", "amount_eur": Decimal("90.00")},
        ],
    )
    monkeypatch.setattr(
        queries,
        "financial_flows",
        lambda *args: [
            {"transaction_type": "salary", "net_amount_eur": Decimal("3000.00"), "transaction_count": 3},
            {"transaction_type": "salary_sweep", "net_amount_eur": Decimal("-250.456"), "transaction_count": 3},
        ],
    )

    result = run(tools, "get_basket_summary", Q1)

    assert result["period"]["days"] == 90
    assert result["total_spending_eur"] == 990.0
    assert result["monthly_average_eur"] == 334.81
    assert result["baskets"]["regular_essentials"]["monthly_average_eur"] == 304.38
    assert result["baskets"]["everyday_spending"]["monthly_average_eur"] == 30.44
    assert result["baskets"]["regular_essentials"]["categories"][0]["monthly_average_eur"] == 304.38
    assert result["baskets"]["regular_essentials"]["label"] == "🏠 Regular essentials"

    flows = {f["transaction_type"]: f for f in result["financial_flows"]}
    assert flows["salary"]["monthly_average_eur"] == 1014.58  # 3000 * 30.4375 / 90
    assert flows["salary_sweep"]["monthly_average_eur"] == -84.7

    assert result["has_salary_sweep"] is True
    assert result["swept_share_of_salary_pct"] == 8.3
    assert "minimum" in result["salary_sweep_note"]


def test_basket_tool_without_sweeps_has_no_warning(tools, monkeypatch):
    monkeypatch.setattr(queries, "consumption_transactions", lambda *args: [])
    monkeypatch.setattr(queries, "financial_flows", lambda *args: [])

    result = run(tools, "get_basket_summary", Q1)

    assert result["has_salary_sweep"] is False
    assert result["salary_sweep_note"] is None
    assert result["total_spending_eur"] == 0.0


# --------------------------------------------------------------------------
# get_monthly_balance_trend
# --------------------------------------------------------------------------

def test_balance_tool_formats_months_and_defaults_to_six(tools, monkeypatch):
    seen = []

    def fake_trend(customer_id, months, as_of=None):
        seen.append((customer_id, months, as_of))
        return [
            {"month": date(2026, 8, 1), "balance_eur": Decimal("4390.15")},
            {"month": date(2026, 9, 1), "balance_eur": Decimal("4723.58")},
        ]

    monkeypatch.setattr(queries, "monthly_balance_trend", fake_trend)

    result = run(tools, "get_monthly_balance_trend", {})

    assert seen == [("CUST42", 6, date(2026, 9, 30))]
    assert result["balances"] == [
        {"month": "2026-08", "balance_eur": 4390.15},
        {"month": "2026-09", "balance_eur": 4723.58},
    ]


def test_balance_tool_accepts_a_float_month_count_and_rejects_fractions(tools, monkeypatch):
    seen = []
    monkeypatch.setattr(
        queries, "monthly_balance_trend", lambda customer_id, months, as_of=None: seen.append(months) or []
    )

    run(tools, "get_monthly_balance_trend", {"months": 1.0})
    assert seen == [1]

    with pytest.raises(ValueError, match="whole number"):
        tools["get_monthly_balance_trend"].run({"months": 2.5})


# --------------------------------------------------------------------------
# Calculation tools
# --------------------------------------------------------------------------

def test_safe_to_spend_tool_returns_the_budget_for_today(monkeypatch):
    from coach import budget
    seen = []
    monkeypatch.setattr(budget, "safe_to_spend",
                        lambda customer_id, today: seen.append((customer_id, today)) or {"safe_to_spend_this_week": 91.27})
    tools = {t.name: t for t in spending.load_tools("CUST42", today=date(2026, 9, 10))}

    assert run(tools, "get_safe_to_spend", {}) == {"safe_to_spend_this_week": 91.27}
    assert seen == [("CUST42", date(2026, 9, 10))]


def test_safe_to_save_tool_matches_the_tested_calculation(tools):
    result = run(
        tools,
        "calculate_safe_to_save",
        {
            "monthly_income": 3000,
            "monthly_mandatory_regular": 1200,
            "monthly_mandatory_irregular": 200,
            "monthly_everyday": 800,
        },
    )
    assert result["safe_to_save_monthly"] == 640.0
    assert result["safe_to_save_yearly"] == 7680.0

    no_cushion = run(
        tools,
        "calculate_safe_to_save",
        {
            "monthly_income": 3000,
            "monthly_mandatory_regular": 1200,
            "monthly_mandatory_irregular": 200,
            "monthly_everyday": 800,
            "cushion_fraction": 0,
        },
    )
    assert no_cushion["safe_to_save_monthly"] == 800.0


def test_what_if_tool_matches_the_brief_example(tools):
    result = run(
        tools,
        "calculate_what_if",
        {"monthly_by_category": {"Restaurants": 235}, "reductions_pct": {"Restaurants": 20}},
    )
    assert result["monthly_saving"] == 47.0
    assert result["yearly_saving"] == 564.0


def test_what_if_tool_rejects_unknown_category(tools):
    with pytest.raises(ValueError, match="Dining"):
        tools["calculate_what_if"].run(
            {"monthly_by_category": {"Restaurants": 235}, "reductions_pct": {"Dining": 20}}
        )


# --------------------------------------------------------------------------
# get_transactions
# --------------------------------------------------------------------------

def test_transactions_tool_formats_rows(tools, monkeypatch):
    from datetime import datetime
    seen = []

    def fake(customer_id, start, end, category=None, order="largest", limit=20):
        seen.append((customer_id, category, order, limit))
        return [
            {"tx_timestamp": datetime(2026, 3, 2, 18, 30, 5), "category": "Transportation",
             "transaction_type": "purchase", "mcc_code": "4121",
             "amount_eur": Decimal("-41.27"), "balance_after_eur": Decimal("1200.00")},
            {"tx_timestamp": datetime(2026, 3, 1, 8, 0), "category": "Housing",
             "transaction_type": "housing_payment", "mcc_code": None,
             "amount_eur": Decimal("-900.00"), "balance_after_eur": Decimal("1241.27")},
            {"tx_timestamp": datetime(2026, 3, 15, 9, 0), "category": "Salary",
             "transaction_type": "salary", "mcc_code": None,
             "amount_eur": Decimal("3000.00"), "balance_after_eur": Decimal("4241.27")},
        ]

    monkeypatch.setattr(queries, "list_transactions", fake)
    result = run(tools, "get_transactions", {**Q1, "order": "latest", "limit": 3.0})

    assert seen == [("CUST42", None, "latest", 3)]
    assert result["transactions"][0] == {
        "timestamp": "2026-03-02T18:30",
        "category": "Transportation",
        "merchant_type": "taxi",
        "amount_eur": -41.27,
        "balance_after_eur": 1200.0,
    }
    assert result["transactions"][1]["merchant_type"] == "bill"
    assert result["transactions"][2]["merchant_type"] is None  # income, not spending


# --------------------------------------------------------------------------
# compare_with_peers
# --------------------------------------------------------------------------


from coach import peers  # noqa: E402


@pytest.mark.parametrize(
    "today, start, end",
    [
        (date(2026, 9, 10), date(2025, 9, 1), date(2026, 8, 31)),
        (date(2026, 9, 30), date(2025, 9, 1), date(2026, 8, 31)),  # current month never counts
        (date(2026, 1, 5), date(2025, 1, 1), date(2025, 12, 31)),
    ],
)
def test_peer_period_is_the_last_12_complete_months(today, start, end):
    assert peers.peer_period(today) == (start, end)


def _population():
    me = {"customer_id": "CUST00001", "age": 22,
          "spending": {"Restaurants": 3600, "Housing": 1200},
          "baskets": {"everyday_spending": 3600, "regular_essentials": 1200}}
    others = [{"customer_id": f"CUST1{i:04d}", "age": 21,
               "spending": {"Restaurants": 1200, "Housing": 12000},
               "baskets": {"everyday_spending": 1200, "regular_essentials": 12000}} for i in range(40)]
    return (me, *others)


def test_compare_with_peers_tool_takes_no_arguments_and_uses_today(monkeypatch):
    asked = []

    def fake_population(start, end):
        asked.append((start, end))
        return _population()

    monkeypatch.setattr(queries, "population_spending", fake_population)
    tool = {t.name: t for t in spending.load_tools("CUST00001", date(2026, 9, 10))}["compare_with_peers"]

    with pytest.raises(ValueError, match="unexpected"):
        tool.run({"customer_id": "CUST00002"})  # can't pick another customer

    result = json.loads(tool.run({}))
    assert asked == [(date(2025, 9, 1), date(2026, 8, 31))]
    assert result["age_group"] == "18–24"
    assert result["peers_in_age_group"] == 40  # the customer is not their own peer
    # 300 a month vs peers' 100: top of the group.
    assert result["by_category"]["Restaurants"]["my_monthly"] == 300.0
    assert [r["category"] for r in result["profile"]["above_peers"]] == ["Restaurants"]
    # Very low rent stays in the comparison but is not called a habit.
    assert result["by_category"]["Housing"]["age_group"]["level"] == "below_peers"
    assert result["profile"]["below_peers"] == []
    assert result["not_in_profile"] == ["Housing", "Utilities"]
    # Baskets are compared the same way, with S-Bank's names.
    everyday = result["by_basket"]["everyday_spending"]
    assert everyday["label"] == "☕ Everyday spending"
    assert everyday["label_fi"] == "☕ Arjen kulutus"
    assert everyday["my_monthly"] == 300.0
    assert everyday["age_group"]["peer_median_monthly"] == 100.0
    assert result["by_basket"]["regular_essentials"]["age_group"]["level"] == "below_peers"


def test_compare_with_peers_returns_no_other_customer_ids(monkeypatch):
    monkeypatch.setattr(queries, "population_spending", lambda s, e: _population())
    tool = {t.name: t for t in spending.load_tools("CUST00001", date(2026, 9, 10))}["compare_with_peers"]
    assert "CUST1" not in tool.run({})


def test_compare_with_peers_unknown_customer(monkeypatch):
    monkeypatch.setattr(queries, "population_spending", lambda s, e: _population())
    tool = {t.name: t for t in spending.load_tools("CUST09999", date(2026, 9, 10))}["compare_with_peers"]
    with pytest.raises(ValueError, match="Unknown customer"):
        tool.run({})

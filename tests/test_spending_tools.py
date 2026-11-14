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
    "calculate_prorated_amount",
    "calculate_safe_to_spend",
    "calculate_safe_to_save",
    "calculate_what_if",
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


def test_prompt_states_the_end_of_the_data():
    assert "2026-09-30" in spending.PROMPT
    assert spending.DATA_END == date(2026, 9, 30)


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


# --------------------------------------------------------------------------
# get_basket_summary
# --------------------------------------------------------------------------

def test_basket_tool_adds_averages_and_sweep_warning(tools, monkeypatch):
    monkeypatch.setattr(
        queries,
        "spending_by_category",
        lambda *args: [
            {"category": "Housing", "total_spending_eur": Decimal("900.00"), "transaction_count": 3},
            {"category": "Groceries", "total_spending_eur": Decimal("90.00"), "transaction_count": 9},
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
    assert result["baskets"]["mandatory_regular"]["monthly_average_eur"] == 304.38
    assert result["baskets"]["everyday_flexible"]["monthly_average_eur"] == 30.44
    assert result["baskets"]["mandatory_regular"]["categories"][0]["monthly_average_eur"] == 304.38

    flows = {f["transaction_type"]: f for f in result["financial_flows"]}
    assert flows["salary"]["monthly_average_eur"] == 1014.58  # 3000 * 30.4375 / 90
    assert flows["salary_sweep"]["monthly_average_eur"] == -84.7

    assert result["has_salary_sweep"] is True
    assert result["swept_share_of_salary_pct"] == 8.3
    assert "minimum" in result["salary_sweep_note"]


def test_basket_tool_without_sweeps_has_no_warning(tools, monkeypatch):
    monkeypatch.setattr(queries, "spending_by_category", lambda *args: [])
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

    def fake_trend(customer_id, months):
        seen.append((customer_id, months))
        return [
            {"month": date(2026, 8, 1), "balance_eur": Decimal("4390.15")},
            {"month": date(2026, 9, 1), "balance_eur": Decimal("4723.58")},
        ]

    monkeypatch.setattr(queries, "monthly_balance_trend", fake_trend)

    result = run(tools, "get_monthly_balance_trend", {})

    assert seen == [("CUST42", 6)]
    assert result["balances"] == [
        {"month": "2026-08", "balance_eur": 4390.15},
        {"month": "2026-09", "balance_eur": 4723.58},
    ]


def test_balance_tool_accepts_a_float_month_count_and_rejects_fractions(tools, monkeypatch):
    seen = []
    monkeypatch.setattr(
        queries, "monthly_balance_trend", lambda customer_id, months: seen.append(months) or []
    )

    run(tools, "get_monthly_balance_trend", {"months": 1.0})
    assert seen == [1]

    with pytest.raises(ValueError, match="whole number"):
        tools["get_monthly_balance_trend"].run({"months": 2.5})


# --------------------------------------------------------------------------
# Calculation tools
# --------------------------------------------------------------------------

def test_prorated_amount_tool(tools):
    assert run(tools, "calculate_prorated_amount", {"monthly_amount": 300, "days": 10}) == {
        "amount_eur": 100.0
    }
    assert run(
        tools,
        "calculate_prorated_amount",
        {"monthly_amount": 100, "days": 15, "days_in_month": 31},
    ) == {"amount_eur": 48.39}


def test_safe_to_spend_tool_matches_the_tested_calculation(tools):
    result = run(
        tools,
        "calculate_safe_to_spend",
        {
            "current_balance": 1000,
            "days_remaining": 10,
            "committed_expenses": 400,
            "irregular_reserve": 100,
            "buffer": 100,
        },
    )
    assert result["safe_total"] == 400.0
    assert result["per_day"] == 40.0
    assert result["per_week"] == 280.0
    assert result["shortfall"] == 0.0


def test_safe_to_spend_tool_accepts_a_float_day_count(tools):
    result = run(tools, "calculate_safe_to_spend", {"current_balance": 500, "days_remaining": 5.0})
    assert result["per_day"] == 100.0


@pytest.mark.parametrize(
    "arguments, error",
    [
        ({"current_balance": 100, "days_remaining": 0}, ValueError),
        ({"current_balance": 100, "days_remaining": 2.5}, ValueError),
        ({"current_balance": "100", "days_remaining": 5}, TypeError),
        ({"current_balance": 100, "days_remaining": 5, "buffer": -1}, ValueError),
    ],
)
def test_safe_to_spend_tool_rejects_bad_input(tools, arguments, error):
    with pytest.raises(error):
        tools["calculate_safe_to_spend"].run(arguments)


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

"""
Charts in the chat (coach/charts.py, the show_chart tool, the agent's chart event).
No database, no model: the query layer is replaced with fixed rows.
"""

import json
from datetime import date
from decimal import Decimal

import pytest

from coach import agent, charts
from coach.database import queries
from coach.tools import spending

TODAY = date(2026, 9, 10)


def tool(name="show_chart"):
    return {t.name: t for t in spending.load_tools("CUST00001", TODAY)}[name]


def test_categories_largest_first_and_folds_the_tail_into_other(monkeypatch):
    rows = [{"category": c, "total_spending_eur": Decimal(v)} for c, v in
            [("Travel", "5"), ("Groceries", "300.10"), ("Restaurants", "120"), ("Health", "40"),
             ("Lifestyle", "30"), ("Entertainment", "20"), ("Transportation", "10")]]
    monkeypatch.setattr(queries, "spending_by_category", lambda c, s, e: rows)
    chart = charts.categories("CUST00001", date(2026, 9, 1), TODAY)
    assert [i["category"] for i in chart["items"]] == ["Groceries", "Restaurants", "Health", "Lifestyle", "Entertainment", "Other"]
    assert chart["items"][-1]["value"] == 15.0          # Transportation 10 + Travel 5
    assert chart["total"] == 525.1                       # every euro still counted


def test_trend_sums_per_month_and_marks_this_month_partial(monkeypatch):
    tx = [
        {"tx_date": date(2026, 7, 3), "category": "Restaurants", "mcc_code": "5812", "amount_eur": Decimal("10.10")},
        {"tx_date": date(2026, 7, 20), "category": "Restaurants", "mcc_code": "5812", "amount_eur": Decimal("5.20")},
        {"tx_date": date(2026, 9, 2), "category": "Restaurants", "mcc_code": "5814", "amount_eur": Decimal("7")},
        {"tx_date": date(2026, 8, 5), "category": "Groceries", "mcc_code": "5411", "amount_eur": Decimal("99")},
    ]
    asked = []
    monkeypatch.setattr(queries, "consumption_transactions", lambda c, s, e: asked.append((s, e)) or tx)
    chart = charts.trend("CUST00001", TODAY, 3, category="Restaurants")
    assert asked == [(date(2026, 7, 1), TODAY)]
    assert chart["months"] == [
        {"month": "2026-07", "value": 15.3, "partial": False},
        {"month": "2026-08", "value": 0.0, "partial": False},   # a month without spending still shows
        {"month": "2026-09", "value": 7.0, "partial": True},
    ]
    everyday = charts.trend("CUST00001", TODAY, 3, basket="everyday_spending")
    assert [m["value"] for m in everyday["months"]] == [15.3, 0.0, 7.0]   # the groceries are 🏠, not ☕


def test_trend_across_a_year_boundary(monkeypatch):
    monkeypatch.setattr(queries, "consumption_transactions", lambda c, s, e: [])
    chart = charts.trend("CUST00001", date(2026, 2, 14), 4)
    assert [m["month"] for m in chart["months"]] == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_trend_rejects_category_and_basket_together():
    with pytest.raises(ValueError):
        charts.trend("CUST00001", TODAY, 3, category="Travel", basket="everyday_spending")


def test_peers_chart_leaves_bills_out_and_keeps_only_aggregates(monkeypatch):
    monkeypatch.setattr(charts.peers_module, "compare", lambda c, t: {
        "age_group": "18–24", "period": {"start_date": "2025-09-01", "end_date": "2026-08-31"},
        "not_in_profile": ["Housing", "Utilities"],
        "by_category": {
            "Housing": {"my_monthly": 900.0, "age_group": {"peer_median_monthly": 950.0}},
            "Groceries": {"my_monthly": 200.0, "age_group": {"peer_median_monthly": 260.0}},
            "Travel": {"my_monthly": 10.0, "age_group": {"peer_median_monthly": 25.0}},
        },
    })
    chart = charts.peers("CUST00001", TODAY)
    assert chart["items"] == [
        {"category": "Groceries", "me": 200.0, "peer_median": 260.0, "finland": None},
        {"category": "Travel", "me": 10.0, "peer_median": 25.0, "finland": None},
    ]
    assert chart["finland_source"] is None


def test_tool_picks_the_period_and_returns_the_chart(monkeypatch):
    asked = []
    monkeypatch.setattr(charts, "categories", lambda c, s, e: asked.append((s, e)) or {"type": "categories"})
    out = json.loads(tool().run({"kind": "categories", "period": "last_month"}))
    assert asked == [(date(2026, 8, 1), date(2026, 8, 31))]
    assert out["chart"] == {"type": "categories"} and "note" in out
    tool().run({"kind": "categories"})
    assert asked[-1] == (date(2026, 9, 1), TODAY)       # default: this month so far


@pytest.mark.parametrize("args", [
    {"kind": "pie"}, {"kind": "trend", "months": 30}, {"kind": "trend", "category": "Taxis"},
    {"kind": "balance", "customer_id": "CUST00002"},
])
def test_tool_rejects_bad_arguments(args):
    with pytest.raises(ValueError):
        tool().run(args)


def test_agent_passes_on_only_successful_show_chart_results():
    good = json.dumps({"chart": {"type": "budget"}, "note": "…"})
    assert agent._chart("show_chart", good, False) == {"type": "budget"}
    assert agent._chart("show_chart", "Error: kind must be …", True) is None
    assert agent._chart("get_transactions", good, False) is None
    assert agent._chart("show_chart", "not json", False) is None


def _compare_result():
    group = lambda m, lo, hi, more: {"peer_median_monthly": m, "peer_typical_range_monthly": [lo, hi],
                                     "spends_more_than_pct_of_peers": more, "spends_less_than_pct_of_peers": 100 - more}
    return {
        "age_group": "18–24", "period": {"start_date": "2025-09-01", "end_date": "2026-08-31"},
        "not_in_profile": ["Housing", "Utilities"],
        "by_category": {"Groceries": {"my_monthly": 206.86, "age_group": group(262.3, 171.74, 377.46, 36.1),
                                      "everyone": group(467.64, 279.63, 664.55, 16.7)}},
    }


def test_peers_with_a_category_gives_its_range_against_age_group_and_everyone(monkeypatch):
    monkeypatch.setattr(charts.peers_module, "compare", lambda c, t: _compare_result())
    chart = charts.peers("CUST00001", TODAY, category="Groceries")
    assert chart["type"] == "peer_range" and chart["category"] == "Groceries" and chart["me"] == 206.86
    assert chart["age"] == {"median": 262.3, "typical_low": 171.74, "typical_high": 377.46,
                            "spends_more_than_pct": 36.1, "spends_less_than_pct": 63.9}
    assert chart["everyone"]["median"] == 467.64


def test_peers_with_an_unknown_category_is_an_error(monkeypatch):
    monkeypatch.setattr(charts.peers_module, "compare", lambda c, t: _compare_result())
    with pytest.raises(ValueError):
        charts.peers("CUST00001", TODAY, category="Travel")


def test_tool_passes_the_category_to_the_peers_chart(monkeypatch):
    asked = []
    monkeypatch.setattr(charts, "peers", lambda c, t, category=None: asked.append(category) or {"type": "peers"})
    tool().run({"kind": "peers"})
    tool().run({"kind": "peers", "category": "Groceries"})
    assert asked == [None, "Groceries"]


# --------------------------------------------------------------------------
# Offering a chart when the coach didn't pick one
# --------------------------------------------------------------------------

@pytest.mark.parametrize("calls, expected", [
    ([("get_spending_by_category", {"start_date": "2026-08-01", "end_date": "2026-08-31"})],
     {"kind": "categories", "start_date": "2026-08-01", "end_date": "2026-08-31"}),
    ([("get_spending_by_category", {"start_date": "2026-03-01", "end_date": "2026-08-31", "category": "Restaurants"})],
     {"kind": "trend", "category": "Restaurants"}),
    ([("get_basket_summary", {"start_date": "2026-08-01", "end_date": "2026-08-31"})],
     {"kind": "categories", "start_date": "2026-08-01", "end_date": "2026-08-31"}),
    ([("get_monthly_balance_trend", {"months": 1})], {"kind": "balance", "months": 2}),
    ([("get_monthly_balance_trend", {})], {"kind": "balance", "months": 6}),
    ([("get_safe_to_spend", {})], {"kind": "budget"}),
    ([("compare_with_peers", {})], {"kind": "peers"}),
    # the last lookup that has a chart decides
    ([("get_safe_to_spend", {}), ("get_transactions", {}), ("compare_with_peers", {})], {"kind": "peers"}),
    ([("compare_with_peers", {}), ("calculate_what_if", {})], {"kind": "peers"}),
])
def test_offer_matches_the_lookup(calls, expected):
    assert charts.offer_args(calls) == expected


@pytest.mark.parametrize("calls", [[], [("calculate_what_if", {})], [("get_transactions", {})],
                                   [("calculate_safe_to_save", {})]])
def test_no_offer_when_no_chart_fits(calls):
    assert charts.offer_args(calls) is None


def test_agent_offers_a_chart_from_the_lookups(monkeypatch):
    monkeypatch.setattr(charts, "budget", lambda c, t: {"type": "budget"})
    tools = {t.name: t for t in spending.load_tools("CUST00001", TODAY)}
    assert agent._offered_chart(tools, [("get_safe_to_spend", {})]) == {"type": "budget"}
    assert agent._offered_chart(tools, [("calculate_what_if", {})]) is None

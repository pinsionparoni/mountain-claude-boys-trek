"""coach/explore.py: the customer's table, the tool's checks and the runner."""

import json
import subprocess
import sys
from datetime import date, datetime

import pytest

from coach import agent, explore

TODAY = date(2026, 9, 10)

ROWS = [
    # Friday evening restaurant, Saturday groceries, salary, savings, a refund
    {"tx_timestamp": datetime(2026, 9, 4, 18, 30), "category": "Restaurants", "transaction_type": "purchase",
     "mcc_code": "5812", "amount_eur": -30.0, "balance_after_eur": 1000.0},
    {"tx_timestamp": datetime(2026, 9, 5, 11, 0), "category": "Groceries", "transaction_type": "purchase",
     "mcc_code": "5411", "amount_eur": -50.0, "balance_after_eur": 950.0},
    {"tx_timestamp": datetime(2026, 9, 1, 6, 0), "category": "Salary", "transaction_type": "salary",
     "mcc_code": None, "amount_eur": 2500.0, "balance_after_eur": 3000.0},
    {"tx_timestamp": datetime(2026, 9, 2, 6, 0), "category": "Invest Deposit", "transaction_type": "investment_deposit",
     "mcc_code": None, "amount_eur": -200.0, "balance_after_eur": 2800.0},
    {"tx_timestamp": datetime(2026, 9, 6, 12, 0), "category": "Groceries", "transaction_type": "purchase",
     "mcc_code": "5411", "amount_eur": 10.0, "balance_after_eur": 960.0},
]


@pytest.fixture
def data(monkeypatch):
    calls = []

    def fake(customer_id, start, end):
        calls.append((customer_id, start, end))
        return ROWS

    monkeypatch.setattr(explore.queries, "account_transactions", fake)
    return explore.table("CUST00001", TODAY), calls


def _row(data, category, amount):
    cols = data["columns"]
    for r in data["rows"]:
        row = dict(zip(cols, r))
        if row["category"] == category and row["amount_eur"] == amount:
            return row
    raise AssertionError((category, amount))


def test_table_covers_one_year_for_this_customer_only(data):
    table, calls = data
    assert calls == [("CUST00001", date(2025, 9, 11), TODAY)]
    assert (table["from"], table["to"]) == ("2025-09-11", "2026-09-10")
    assert len(table["rows"]) == len(ROWS)


def test_table_kinds_baskets_and_signs(data):
    table, _ = data
    food = _row(table, "Restaurants", 30.0)       # money out is positive
    assert (food["kind"], food["weekday"], food["hour"], food["month"]) == ("spending", 4, 18, "2026-09")
    assert food["basket"] and food["merchant_type"] and food["category_fi"]
    assert _row(table, "Salary", -2500.0)["kind"] == "income"
    assert _row(table, "Salary", -2500.0)["basket"] is None
    assert _row(table, "Invest Deposit", 200.0)["kind"] == "transfer"
    assert _row(table, "Groceries", -10.0)["kind"] == "refund"


def _run_locally(code, table, tmp_path):
    """The sandbox's runner, run here on our own test code (the sandbox adds the isolation)."""
    path = tmp_path / "data.json"
    path.write_text(json.dumps({**table, "code": code}))
    out = subprocess.run([sys.executable, "-c", explore.RUNNER, "10", str(path)],
                         capture_output=True, text=True, timeout=60)
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_runner_gives_days_and_months_for_averages(data, tmp_path):
    table, _ = data
    code = ('w = days[days.weekday >= 5]\n'
            's = df[(df.kind == "spending") & (df.weekday >= 5)].amount_eur.sum()\n'
            'result = {"weekend_days": len(w), "per_weekend_day": round(s / len(w), 2), '
            '"n_days": n_days, "n_months": n_months}')
    out = _run_locally(code, table, tmp_path)["result"]
    assert out["n_days"] == 365
    assert out["n_months"] == pytest.approx(11.99, abs=0.01)
    assert out["weekend_days"] in (104, 105, 106)
    assert out["per_weekend_day"] == round(50 / out["weekend_days"], 2)


def test_runner_reports_errors(data, tmp_path):
    table, _ = data
    assert "must assign" in _run_locally("x = 1", table, tmp_path)["error"]
    assert "ZeroDivisionError" in _run_locally("result = 1 / 0", table, tmp_path)["error"]


def _tool(monkeypatch, runner):
    monkeypatch.setattr(explore.queries, "account_transactions", lambda *a: ROWS)
    (tool,) = explore.load_tools("CUST00001", TODAY, runner=runner)
    return tool


def test_tool_returns_result_and_period(monkeypatch):
    seen = {}

    def runner(code, data):
        seen["code"], seen["rows"] = code, len(data["rows"])
        return {"result": {"total_eur": 30.0}}

    tool = _tool(monkeypatch, runner)
    out = json.loads(tool.run({"code": "result = 1"}))
    assert out == {"result": {"total_eur": 30.0},
                   "period": {"start_date": "2025-09-11", "end_date": "2026-09-10"}, "transactions": len(ROWS)}
    assert seen == {"code": "result = 1", "rows": len(ROWS)}


@pytest.mark.parametrize("args, message", [
    ({"code": " "}, "code is required"),
    ({"code": "x" * (explore.MAX_CODE_CHARS + 1)}, "too long"),
])
def test_tool_rejects_bad_input(monkeypatch, args, message):
    tool = _tool(monkeypatch, lambda code, data: pytest.fail("should not run"))
    with pytest.raises(ValueError, match=message):
        tool.run(args)


def test_tool_passes_code_errors_back_to_the_model(monkeypatch):
    tool = _tool(monkeypatch, lambda code, data: {"error": "KeyError: 'x'"})
    with pytest.raises(ValueError, match="KeyError"):
        tool.run({"code": "result = df['x']"})


def test_tool_rejects_huge_results(monkeypatch):
    tool = _tool(monkeypatch, lambda code, data: {"result": list(range(5000))})
    with pytest.raises(ValueError, match="too large"):
        tool.run({"code": "result = 1"})


def test_tool_rejects_customer_id(monkeypatch):
    tool = _tool(monkeypatch, lambda code, data: {"result": 1})
    with pytest.raises((ValueError, TypeError)):
        tool.run({"code": "result = 1", "customer_id": "CUST00002"})


def test_nothing_about_the_calculation_reaches_the_app():
    """The agent only streams text, tool names and charts: the code stays on the server."""
    assert not hasattr(agent, "_calculation")


def test_off_switch(monkeypatch):
    monkeypatch.setenv("COACH_SANDBOX", "0")
    assert not explore.enabled()
    monkeypatch.delenv("COACH_SANDBOX")
    assert explore.enabled()

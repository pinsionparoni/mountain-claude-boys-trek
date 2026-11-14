"""
The home screen's money-coaching tip (coach/tips.py): which rule wins, and that
savings advice is only ever about everyday spending. No database, no model.
"""

from datetime import date

import pytest

from coach import tips

TODAY = date(2026, 9, 10)


def budget(limited_by="budget", over=0.0, spent=100.0, everyday=500.0, days_left=20):
    return {
        "limited_by": limited_by,
        "safe_to_spend_this_week": 68.23,
        "monthly_budget": {"regular_essentials": 900.0, "unexpected_reserve": 100.0, "savings": 50.0},
        "this_month": {"over_budget": over, "everyday_spent": spent, "everyday_budget": everyday,
                       "remaining": max(everyday - spent, 0), "per_week": 120.0, "days_left_in_month": days_left,
                       "regular_essentials_spent": 700.0, "unexpected_spent": 0.0},
        "cash_check": {"next_payday": "2026-09-15", "days_to_payday": 5},
    }


def comparison(**categories):
    """by_category rows with a Finnish average: name=(my_monthly, finland_monthly)."""
    rows = {}
    for name, (mine, finland) in categories.items():
        rows[name] = {"my_monthly": mine, "finland": {
            "age_group_monthly": finland, "all_ages_monthly": finland,
            "difference_from_age_group_pct": round((mine - finland) / finland * 100)}}
    return {"age_group": "18–24", "by_category": rows}


@pytest.fixture
def data(monkeypatch):
    state = {"budget": budget(), "compare": comparison()}
    monkeypatch.setattr(tips.budget_module, "safe_to_spend", lambda c, t: state["budget"])
    monkeypatch.setattr(tips.peers, "compare", lambda c, t: state["compare"])
    monkeypatch.setattr(tips.charts, "peers", lambda c, t, category=None: {"type": "peer_range", "category": category})
    return state


def test_cash_tight_wins_first(data):
    data["budget"] = budget(limited_by="cash", over=50)
    data["compare"] = comparison(Restaurants=(200, 73))
    tip = tips.pick("C", TODAY)
    assert tip["kind"] == "cash_tight"
    assert tip["facts"] == {"safe_this_week": 68.23, "next_payday": "2026-09-15", "days_to_payday": 5}
    assert tip["chart"]["type"] == "budget"


def test_over_budget_before_savings_advice(data):
    data["budget"] = budget(over=40.5)
    data["compare"] = comparison(Restaurants=(200, 73))
    tip = tips.pick("C", TODAY)
    assert tip["kind"] == "over_budget" and tip["facts"]["over"] == 40.5


def test_above_finland_picks_the_largest_excess_and_prices_a_20_percent_cut(data):
    data["compare"] = comparison(Restaurants=(132.51, 73.26), Entertainment=(80, 33))
    tip = tips.pick("C", TODAY)
    assert tip["kind"] == "above_finland"
    assert tip["facts"]["category"] == "Restaurants"           # 59 EUR over beats 47
    assert tip["facts"]["yearly_saving"] == 318.02             # 132.51 x 20 % x 12
    assert tip["chart"] == {"type": "peer_range", "category": "Restaurants"}


@pytest.mark.parametrize("category", ["Groceries", "Health", "Transportation"])
def test_necessities_never_get_cut_it_advice(data, category):
    data["compare"] = comparison(**{category: (900, 300)})
    assert tips.pick("C", TODAY)["kind"] == "on_track"


@pytest.mark.parametrize("mine, finland", [(90, 80), (40, 30)])   # +12 %; +33 % but only 10 EUR
def test_small_differences_are_not_worth_a_tip(data, mine, finland):
    data["compare"] = comparison(Restaurants=(mine, finland))
    assert tips.pick("C", TODAY)["kind"] == "on_track"


def test_nearly_used_needs_a_week_left(data):
    data["budget"] = budget(spent=420, everyday=500, days_left=12)
    assert tips.pick("C", TODAY)["kind"] == "nearly_used"
    data["budget"] = budget(spent=420, everyday=500, days_left=4)
    assert tips.pick("C", TODAY)["kind"] == "on_track"


def test_on_track_carries_whats_left(data):
    tip = tips.pick("C", TODAY)
    assert tip["kind"] == "on_track"
    assert tip["facts"] == {"remaining": 400.0, "per_week": 120.0, "savings_per_month": 50.0}

"""
Statistics Finland's open benchmark (coach/statfin.py, coach/statfin_data.py) and how
the peer comparison and charts use it. No network: the generated data is in the repo.
"""

from datetime import date

import pytest

from coach import calculations, charts, peers, statfin, statfin_data
from coach.calculations import AGE_GROUPS


def test_generated_data_covers_every_age_group_and_the_mapped_categories():
    ours = {label for _, _, label in AGE_GROUPS} | {"all"}
    assert set(statfin_data.SPENDING_PER_MONTH) == ours
    for row in statfin_data.SPENDING_PER_MONTH.values():
        assert set(row) == {"Groceries", "Restaurants", "Transportation", "Health", "Entertainment"}
        assert all(0 < v < 2000 for v in row.values())


def test_the_source_is_recorded_with_its_licence():
    s = statfin_data.SOURCE
    assert s["publisher"] == "Statistics Finland" and s["licence"] == "CC BY 4.0"
    assert s["survey_year"] == 2022 and "per consumption unit" in s["measure"]
    assert statfin.source()["price_level"] == "2025M09–2026M08 average"


def test_lookup_returns_none_for_categories_that_dont_map():
    assert statfin.monthly("Groceries", "18–24") == statfin_data.SPENDING_PER_MONTH["18–24"]["Groceries"]
    assert statfin.monthly("Travel", "18–24") is None
    assert statfin.monthly("Groceries", "17–24") is None


@pytest.mark.parametrize("value, reference, expected", [
    (132.51, 73.26, 81.0), (206.86, 229.61, -10.0), (50, 50, 0.0), (10, 0, None),
])
def test_difference_pct(value, reference, expected):
    assert calculations.difference_pct(value, reference) == expected


def _fake_compare_inputs(monkeypatch):
    population = (
        {"customer_id": "ME", "age": 21, "spending": {"Groceries": 2400, "Travel": 120},
         "baskets": {"regular_essentials": 2400, "everyday_spending": 120}},
        *({"customer_id": f"P{i}", "age": 22, "spending": {"Groceries": 3000, "Travel": 300},
           "baskets": {"regular_essentials": 3000, "everyday_spending": 300}} for i in range(40)),
    )
    monkeypatch.setattr(peers.queries, "population_spending", lambda s, e: population)


def test_compare_adds_finland_where_the_category_maps(monkeypatch):
    _fake_compare_inputs(monkeypatch)
    result = peers.compare("ME", date(2026, 9, 10))
    finland = result["by_category"]["Groceries"]["finland"]
    expected = statfin_data.SPENDING_PER_MONTH["18–24"]["Groceries"]
    assert finland["age_group_monthly"] == expected
    assert finland["all_ages_monthly"] == statfin_data.SPENDING_PER_MONTH["all"]["Groceries"]
    assert finland["difference_from_age_group_pct"] == calculations.difference_pct(200.0, expected)  # 2400 / 12
    assert "finland" not in result["by_category"]["Travel"]
    assert result["finland_source"]["licence"] == "CC BY 4.0"


def test_peer_range_chart_carries_the_finnish_averages(monkeypatch):
    _fake_compare_inputs(monkeypatch)
    chart = charts.peers("ME", date(2026, 9, 10), category="Groceries")
    assert chart["finland"] == {"age": statfin_data.SPENDING_PER_MONTH["18–24"]["Groceries"],
                                "all": statfin_data.SPENDING_PER_MONTH["all"]["Groceries"]}
    assert chart["finland_source"]["publisher"] == "Statistics Finland"
    travel = charts.peers("ME", date(2026, 9, 10), category="Travel")
    assert travel["finland"] is None and travel["finland_source"] is None

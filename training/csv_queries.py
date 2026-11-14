"""In-memory CSV adapter matching coach.database.queries cent-for-cent.

Loads data/tx_customers_junction.csv and data/tx_junction_transactions.csv once
(~8 seconds) and patches coach.database.queries so coach.agent._prepare and
coach.tools.spending.load_tools run offline with zero network or GPU latency.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from coach.database import queries
from coach.spending_baskets import (
    ANY_CATEGORY,
    CONSUMPTION_TRANSACTION_TYPES,
    EXCLUDED_FROM_CONSUMPTION,
    UNCLASSIFIED,
    basket_lookup,
    large_purchase_thresholds,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CONSUMPTION_SET = frozenset(CONSUMPTION_TRANSACTION_TYPES)
_EXCLUDED_SET = frozenset(EXCLUDED_FROM_CONSUMPTION)
_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _parse_ts(raw: str) -> datetime:
    """Fast parser for '03OCT24:09:04:04'."""
    day = int(raw[0:2])
    mon = _MONTHS[raw[2:5].upper()]
    year = 2000 + int(raw[5:7])
    hour = int(raw[8:10])
    minute = int(raw[11:13])
    sec = int(raw[14:16])
    return datetime(year, mon, day, hour, minute, sec)


class _Store:
    def __init__(self) -> None:
        self.customers: dict[str, tuple[str, int]] = {}
        # Per customer list of tuples:
        # (row_id, tx_date, tx_ts_raw, category, amount_dec, balance_dec, tx_type, mcc_or_none)
        self.tx_by_customer: dict[str, list[tuple]] = defaultdict(list)
        self._load()

    def _load(self) -> None:
        with (DATA_DIR / "tx_customers_junction.csv").open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader)
            for cid, postal, age in reader:
                self.customers[cid] = (postal, int(age))

        fromisoformat = date.fromisoformat
        dec = Decimal
        tx_map = self.tx_by_customer
        with (DATA_DIR / "tx_junction_transactions.csv").open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader)
            for idx, row in enumerate(reader, start=1):
                cid, _acc, d_str, ts_str, cat, amt_str, bal_str, tx_type, _mid, mcc = row
                tx_map[cid].append((
                    idx,
                    fromisoformat(d_str),
                    ts_str,
                    cat or None,
                    dec(amt_str),
                    dec(bal_str),
                    tx_type,
                    mcc or None,
                ))


_STORE: _Store | None = None


def store() -> _Store:
    global _STORE
    if _STORE is None:
        _STORE = _Store()
    return _STORE


def _validate(customer_id: str, start_date: date, end_date: date) -> None:
    if not customer_id:
        raise ValueError("customer_id is required")
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")


def spending_by_category(customer_id: str, start_date: date, end_date: date) -> list[dict]:
    _validate(customer_id, start_date, end_date)
    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    for _id, d, _ts, cat, amt, _bal, tx_type, _mcc in store().tx_by_customer.get(customer_id, ()):
        if start_date <= d <= end_date and amt < 0 and tx_type in _CONSUMPTION_SET:
            key = cat or "Uncategorized"
            totals[key] += -amt
            counts[key] += 1
    rows = [
        {"category": k, "total_spending_eur": totals[k], "transaction_count": counts[k]}
        for k in totals
    ]
    rows.sort(key=lambda r: r["total_spending_eur"], reverse=True)
    return rows


def financial_flows(customer_id: str, start_date: date, end_date: date) -> list[dict]:
    _validate(customer_id, start_date, end_date)
    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    for _id, d, _ts, _cat, amt, _bal, tx_type, _mcc in store().tx_by_customer.get(customer_id, ()):
        if start_date <= d <= end_date and tx_type in _EXCLUDED_SET:
            totals[tx_type] += amt
            counts[tx_type] += 1
    return [
        {"transaction_type": k, "net_amount_eur": totals[k], "transaction_count": counts[k]}
        for k in sorted(totals)
    ]


def consumption_transactions(customer_id: str, start_date: date, end_date: date) -> list[dict]:
    _validate(customer_id, start_date, end_date)
    rows = []
    for row_id, d, _ts, cat, amt, _bal, tx_type, mcc in store().tx_by_customer.get(customer_id, ()):
        if start_date <= d <= end_date and amt < 0 and tx_type in _CONSUMPTION_SET:
            rows.append((d, row_id, {
                "tx_date": d,
                "category": cat or "Uncategorized",
                "mcc_code": mcc,
                "amount_eur": -amt,
            }))
    rows.sort(key=lambda item: (item[0], item[1]))
    return [r[2] for r in rows]


def list_transactions(
    customer_id: str,
    start_date: date,
    end_date: date,
    category: str | None = None,
    order: str = "largest",
    limit: int = 20,
) -> list[dict]:
    _validate(customer_id, start_date, end_date)
    if order not in ("largest", "latest"):
        raise ValueError('order must be "largest" or "latest"')
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    matched = []
    for row_id, d, ts_str, cat, amt, bal, tx_type, mcc in store().tx_by_customer.get(customer_id, ()):
        if start_date <= d <= end_date and (category is None or cat == category):
            matched.append((row_id, _parse_ts(ts_str), cat, tx_type, mcc, amt, bal))
    if order == "largest":
        matched.sort(key=lambda r: (r[5], r[0]))
    else:
        matched.sort(key=lambda r: (r[1], r[0]), reverse=True)
    return [
        {
            "tx_timestamp": r[1],
            "category": r[2],
            "transaction_type": r[3],
            "mcc_code": r[4],
            "amount_eur": r[5],
            "balance_after_eur": r[6],
        }
        for r in matched[:limit]
    ]


def monthly_balance_trend(customer_id: str, months: int = 6, as_of: date | None = None) -> list[dict]:
    if not customer_id:
        raise ValueError("customer_id is required")
    if not 1 <= months <= 24:
        raise ValueError("months must be between 1 and 24")
    txs = [
        r for r in store().tx_by_customer.get(customer_id, ())
        if as_of is None or r[1] <= as_of
    ]
    if not txs:
        return []
    latest_d = max(r[1] for r in txs)
    y, m = latest_d.year, latest_d.month - (months - 1)
    while m <= 0:
        y -= 1
        m += 12
    cutoff = date(y, m, 1)

    by_month: dict[date, tuple[datetime, int, Decimal]] = {}
    for row_id, d, ts_str, _cat, _amt, bal, _tx_type, _mcc in txs:
        if d < cutoff:
            continue
        ts = _parse_ts(ts_str)
        m_start = date(ts.year, ts.month, 1)
        prev = by_month.get(m_start)
        if prev is None or (ts, row_id) > (prev[0], prev[1]):
            by_month[m_start] = (ts, row_id, bal)

    return [
        {"month": m_start, "balance_eur": by_month[m_start][2]}
        for m_start in sorted(by_month)
    ]


def customer_profile(customer_id: str) -> dict:
    if not customer_id:
        raise ValueError("customer_id is required")
    s = store()
    if customer_id not in s.customers or not s.tx_by_customer.get(customer_id):
        raise ValueError(f"Unknown customer {customer_id}")
    postal, age = s.customers[customer_id]
    txs = s.tx_by_customer[customer_id]
    data_from = min(r[1] for r in txs)
    data_to = max(r[1] for r in txs)
    latest = max(txs, key=lambda r: (_parse_ts(r[2]), r[0]))
    return {
        "customer_id": customer_id,
        "age": age,
        "postal_code": postal,
        "data_from": data_from.isoformat(),
        "data_to": data_to.isoformat(),
        "balance_eur": round(float(latest[5]), 2),
    }


def monthly_flows(customer_id: str, start_date: date, end_date: date) -> list[dict]:
    _validate(customer_id, start_date, end_date)
    totals: dict[tuple[date, str], Decimal] = defaultdict(Decimal)
    for _id, d, _ts, _cat, amt, _bal, tx_type, _mcc in store().tx_by_customer.get(customer_id, ()):
        if start_date <= d <= end_date and tx_type in _EXCLUDED_SET:
            m_start = date(d.year, d.month, 1)
            totals[(m_start, tx_type)] += amt
    return [
        {"month": k[0], "transaction_type": k[1], "net_amount_eur": totals[k]}
        for k in sorted(totals)
    ]


def salary_dates(customer_id: str, start_date: date, end_date: date) -> list[date]:
    _validate(customer_id, start_date, end_date)
    dates = [
        d for _id, d, _ts, _cat, _amt, _bal, tx_type, _mcc in store().tx_by_customer.get(customer_id, ())
        if start_date <= d <= end_date and tx_type == "salary"
    ]
    dates.sort()
    return dates


def balance_as_of(customer_id: str, day: date) -> float | None:
    if not customer_id:
        raise ValueError("customer_id is required")
    best: tuple[datetime, int, Decimal] | None = None
    for row_id, d, ts_str, _cat, _amt, bal, _tx_type, _mcc in store().tx_by_customer.get(customer_id, ()):
        if d <= day:
            ts = _parse_ts(ts_str)
            if best is None or (ts, row_id) > (best[0], best[1]):
                best = (ts, row_id, bal)
    return round(float(best[2]), 2) if best else None


@lru_cache(maxsize=4)
def population_spending(start_date: date, end_date: date) -> tuple[dict, ...]:
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    s = store()
    lookup = basket_lookup()
    thresholds = large_purchase_thresholds()
    out = []
    for cid in sorted(s.customers):
        _postal, age = s.customers[cid]
        cat_totals: dict[str, Decimal] = defaultdict(Decimal)
        bsk_totals: dict[str, Decimal] = defaultdict(Decimal)
        for _id, d, _ts, cat, amt, _bal, tx_type, mcc in s.tx_by_customer.get(cid, ()):
            if start_date <= d <= end_date and amt < 0 and tx_type in _CONSUMPTION_SET:
                c = cat or "Uncategorized"
                pos_amt = -amt
                th = thresholds.get(c)
                size = "L" if (th is not None and pos_amt >= th) else "S"
                m = mcc or ""
                bsk = (
                    lookup.get(f"{c}|{m}|{size}")
                    or lookup.get(f"{c}||{size}")
                    or lookup.get(f"{ANY_CATEGORY}|{m}|{size}")
                    or UNCLASSIFIED
                )
                cat_totals[c] += pos_amt
                bsk_totals[bsk] += pos_amt
        out.append({
            "customer_id": cid,
            "age": age,
            "spending": {k: round(float(v), 2) for k, v in cat_totals.items()},
            "baskets": {k: round(float(v), 2) for k, v in bsk_totals.items()},
        })
    return tuple(out)


def install() -> None:
    """Monkeypatch coach.database.queries to use the local CSV store."""
    queries.spending_by_category = spending_by_category
    queries.financial_flows = financial_flows
    queries.consumption_transactions = consumption_transactions
    queries.list_transactions = list_transactions
    queries.monthly_balance_trend = monthly_balance_trend
    queries.customer_profile = customer_profile
    queries.monthly_flows = monthly_flows
    queries.salary_dates = salary_dates
    queries.balance_as_of = balance_as_of
    queries.population_spending = population_spending

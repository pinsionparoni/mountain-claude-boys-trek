# Data audits

One-off scripts that read the **live database** (`DATABASE_URL`) to check assumptions about the data, for example which transaction types count as spending or how regular salary sweeps are. Their findings are behind the rules in `coach/spending_baskets.py` and [BASKETS.md](../../BASKETS.md).

They're scripts, not tests, so `pytest` never runs them. Run one from the repo root:

```bash
PYTHONPATH=. .venv/bin/python scripts/audits/audit_financial_flows.py
```

- `check_connection.py`: can we reach the database, and what tables and columns does it have?
- `check_queries.py`: runs the query layer against a real customer.
- `audit_*.py`: the individual audits.

Some audits scan all 3.6M rows; run them sparingly against the shared Aiven database.

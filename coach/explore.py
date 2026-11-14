"""
"Explore my data": open questions about the customer's own money that no fixed
tool answers ("would skipping Friday takeaways save much?", "do I spend more at
weekends?", "what does one coffee cost me on average?").

The model writes a few lines of pandas over one table of **this customer's**
transactions, with a plain-language note on how it calculated. The code runs
in a **Modal Sandbox**: a fresh, short-lived container in Modal's EU region with
no network, no secrets and no other customer's data, so whatever the model
writes can't reach anything but that one table. The model never does the
arithmetic; the computer does, and the answer says in a sentence what was
counted and over which period. The code stays on the server.

The fixed tools stay first for everything they cover (safe to spend, what-if
cuts, comparisons): they are tested formulas. This tool is for the rest.

On when ``COACH_SANDBOX`` isn't "0" (default on). Needs Modal credentials:
``modal setup`` locally; automatic in the hosted demo, which runs on Modal.
"""

import json
import os
from datetime import date

from coach.database import queries
from coach.spending_baskets import (
    CATEGORY_LABELS_FI,
    CONSUMPTION_TRANSACTION_TYPES,
    MERCHANT_TYPE_LABELS_FI,
    classify_transaction,
    merchant_type,
)

APP_NAME = "financial-coach-sandbox"
REGION = "eu"                  # next to the database (Frankfurt) and Verda (Finland)
PANDAS = "pandas==3.1.1"       # same as requirements.txt
TIMEOUT_S = 30                 # the whole sandbox, including start-up
CODE_TIMEOUT_S = 15            # the model's code
MAX_CODE_CHARS = 4000
MAX_RESULT_CHARS = 4000
HISTORY_DAYS = 365             # one year of transactions up to "today"

COLUMNS = """\
- time (datetime, local time), date (datetime, midnight), weekday (0 = Monday … 6 = Sunday), hour (0-23), month ("2026-08")
- amount_eur (float): money out is positive, money in is negative
- kind: "spending" (purchases and bills), "refund" (money back from a shop), "income" (salary, other income) or \
"transfer" (savings, investments, salary sweeps)
- category: Groceries, Restaurants, Transportation, Utilities, Entertainment, Health, Home & Tech, Housing, Lifestyle, \
Travel, Salary, Other Income, Invest Deposit, Invest Withdraw, Salary Sweep; category_fi: its Finnish name
- merchant_type (spending only): e.g. "fast food / café", "restaurant", "bar", "supermarket", "taxi", "fuel", \
"public transport", "parking", "pharmacy", "cinema", "clothing", "bill" (rent, utilities), "other"; \
merchant_type_fi: its Finnish name. None for income and transfers
- basket (spending only): "regular_essentials", "unexpected_necessities", "everyday_spending", or None
- balance_after_eur (float): the account balance after the transaction

Also ready for you (use them for every average, never divide by a number you picked yourself):
- `days`: DataFrame with one row per calendar day of the period (date, weekday 0-6, month): \
days[days.weekday >= 5] are the weekend days, so "per weekend day" = weekend total / len(days[days.weekday >= 5])
- `n_days` (int, days in the period) and `n_months` (float, n_days / 30.44, about 12): "per month" = total / n_months
- The period is exactly one year, so "per year" is the period's total itself: never per month × 12"""

PROMPT = f"""
- explore_my_data: for questions about the customer's own money that no other tool answers (a time of day or \
weekday, a habit, "when would I reach…", "how much does one … cost me"), write a few lines of \
pandas. Always prefer the other tools when they fit: spending on one category or one kind of merchant (bars, \
taxis, cafés, alcohol) over a period is get_spending_by_category, never this one; nor is safe to spend, what-if cuts \
by category, comparisons with other people, or charts. Report the numbers in `result` as given. In your answer, \
say in one plain sentence what you counted, over which period and what an average is per ("Laskin kahvila- ja \
pikaruokaostosi viimeisten 12 kuukauden ajalta: ostat niitä keskimäärin 3 kertaa viikossa."). Never mention code, \
pandas, a sandbox or tables. Answer in the language of the customer's question."""

TOOL_DESCRIPTION = f"""Run a short pandas calculation over the customer's own transactions from the last 12 months \
(up to today), in an isolated sandbox. `df` is a pandas DataFrame with one row per transaction:
{COLUMNS}
`pd` is pandas. Assign `result` a small dict of named numbers or short lists, money rounded to 2 decimals, \
naming what each number is (e.g. result = {{"total_eur": 495.6, "per_month_eur": 41.3, "purchases": 38, \
"months_counted": 12.0}}). Every average must say what it is per and how many it was divided by: \
"per day" divides by the number of calendar days of that kind (from `days`), not by 5 or 2; "per purchase" by the \
number of purchases. Spending questions use kind == "spending" only. Don't print, read files or use the network. \
Afterwards, tell the customer in one plain sentence what you counted and over which period, in the language \
of their question."""

# Runs inside the sandbox: loads the table, runs the model's code, prints `result` as JSON.
RUNNER = r"""
import json, signal, sys
import pandas as pd

def _timeout(*_):
    raise TimeoutError("the calculation took too long")

signal.signal(signal.SIGALRM, _timeout)
signal.alarm(int(sys.argv[1]))
rows = json.load(open(sys.argv[2]))
df = pd.DataFrame(rows["rows"], columns=rows["columns"])
code = rows["code"]
for col in ("time", "date"):
    df[col] = pd.to_datetime(df[col])
dates = pd.date_range(rows["from"], rows["to"], freq="D")
days = pd.DataFrame({"date": dates, "weekday": dates.day_of_week, "month": dates.strftime("%Y-%m")})
n_days = len(days)
n_months = round(n_days / 30.44, 2)
scope = {"df": df, "pd": pd, "days": days, "n_days": n_days, "n_months": n_months}
try:
    exec(compile(code, "calculation", "exec"), scope)
    if "result" not in scope:
        raise ValueError("the code must assign `result`")
    out = {"result": scope["result"]}
except Exception as e:
    out = {"error": f"{type(e).__name__}: {e}"}

def _plain(value):
    if hasattr(value, "item"):         # numpy / pandas scalars
        return value.item()
    if hasattr(value, "to_dict"):      # Series, DataFrame
        return value.to_dict()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

print(json.dumps(out, default=_plain, ensure_ascii=False))
"""


def enabled():
    return os.environ.get("COACH_SANDBOX", "1") != "0"


def table(customer_id: str, today: date) -> dict:
    """The customer's transactions of the last 12 months as columns and rows, ready for the sandbox."""
    start = date.fromordinal(today.toordinal() - HISTORY_DAYS + 1)
    rows = []
    for r in queries.account_transactions(customer_id, start, today):
        amount = float(r["amount_eur"])
        category, mcc, ttype = r["category"], r["mcc_code"], r["transaction_type"]
        basket = None
        if ttype in CONSUMPTION_TRANSACTION_TYPES:
            kind = "spending" if amount < 0 else "refund"
            if amount < 0:
                basket = classify_transaction(category, ttype, mcc, -amount)
        elif category in ("Salary", "Other Income"):
            kind = "income"
        else:
            kind = "transfer"
        mtype = merchant_type(mcc, category) if kind in ("spending", "refund") else None
        t = r["tx_timestamp"]
        rows.append([
            t.isoformat(), t.date().isoformat(), t.weekday(), t.hour, t.strftime("%Y-%m"),
            round(-amount, 2), kind, category, CATEGORY_LABELS_FI.get(category),
            mtype, MERCHANT_TYPE_LABELS_FI.get(mtype) if mtype else None,
            basket, float(r["balance_after_eur"]) if r["balance_after_eur"] is not None else None,
        ])
    columns = ["time", "date", "weekday", "hour", "month", "amount_eur", "kind", "category", "category_fi",
               "merchant_type", "merchant_type_fi", "basket", "balance_after_eur"]
    return {"columns": columns, "rows": rows, "from": start.isoformat(), "to": today.isoformat()}


def _image():
    import modal
    return modal.Image.debian_slim(python_version="3.12").pip_install(PANDAS)


def _run_once(code: str, data: dict) -> dict:
    import modal

    app = modal.App.lookup(APP_NAME, create_if_missing=True)
    sb = modal.Sandbox.create(
        app=app, image=_image(), region=REGION, block_network=True,
        timeout=TIMEOUT_S, cpu=1, memory=512,
    )
    try:
        # One file with the table and the code; the runner itself goes on the command line.
        sb.filesystem.write_text(json.dumps({**data, "code": code}), "/tmp/data.json")
        proc = sb.exec("python", "-c", RUNNER, str(CODE_TIMEOUT_S), "/tmp/data.json", timeout=CODE_TIMEOUT_S + 5)
        out = proc.stdout.read().strip()
        proc.wait()
        if not out:
            raise RuntimeError(f"the calculation failed: {proc.stderr.read().strip()[-300:]}")
        return json.loads(out.splitlines()[-1])
    finally:
        sb.terminate()


def run_in_sandbox(code: str, data: dict) -> dict:
    """Run ``code`` over ``data`` in a fresh Modal Sandbox (EU, no network) and return its JSON output.

    A sandbox that goes away before it starts (rare) is retried once with a new one.
    """
    import modal

    try:
        return _run_once(code, data)
    except modal.exception.NotFoundError:
        return _run_once(code, data)


def load_tools(customer_id: str, today: date, runner=run_in_sandbox):
    """The explore tool for one customer. ``runner`` is swapped out in tests."""
    from coach.tools.spending import CoachTool

    def explore(args):
        code = args["code"]
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code is required")
        if len(code) > MAX_CODE_CHARS:
            raise ValueError(f"code is too long (max {MAX_CODE_CHARS} characters); keep it to a few lines")
        data = table(customer_id, today)
        out = runner(code, data)
        if "error" in out:
            raise ValueError(f"{out['error']}. Fix the code and try again, or tell the customer you can't calculate that.")
        result = json.dumps(out["result"], ensure_ascii=False)
        if len(result) > MAX_RESULT_CHARS:
            raise ValueError("the result is too large: return a few named numbers, not whole tables")
        return {"result": out["result"], "period": {"start_date": data["from"], "end_date": data["to"]},
                "transactions": len(data["rows"])}

    return [CoachTool(
        name="explore_my_data",
        description=TOOL_DESCRIPTION,
        properties={
            "code": {"type": "string", "description": "Python using `df` and `pd` that assigns `result`."},
        },
        required=["code"],
        handler=explore,
    )]

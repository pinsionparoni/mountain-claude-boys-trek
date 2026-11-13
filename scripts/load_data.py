"""Load the S-Pankki CSVs from data/ into PostgreSQL.

Usage:
    python scripts/load_data.py            # fails if the tables already exist
    python scripts/load_data.py --replace  # drops and reloads them

Connects to DATABASE_URL from .env (local PostgreSQL or Aiven).
"""

import argparse
import os
import sys
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TABLES = ["mortgage_events", "mortgage_outcomes", "transactions", "customers"]

# The CSVs are loaded into all-text staging tables with COPY, then converted with SQL.
# Timestamps look like 03OCT24:09:04:04, hence the to_timestamp format.
SCHEMA = """
CREATE TABLE customers (
    customer_id  text PRIMARY KEY,
    postal_code  text,
    age          integer
);

CREATE TABLE transactions (
    id                 bigserial PRIMARY KEY,
    customer_id        text NOT NULL REFERENCES customers,
    bank_account_id    text,
    tx_date            date NOT NULL,
    tx_timestamp       timestamp,
    category           text,
    tx_amount_eur      numeric(12, 2) NOT NULL,
    balance_after_eur  numeric(14, 2),
    transaction_type   text,
    merchant_id        text,
    mcc_code           text
);

CREATE TABLE mortgage_outcomes (
    mortgage_customer_id         text PRIMARY KEY,
    customer_id                  text REFERENCES customers,
    final_decision               text,
    rejection_reason             text,
    final_property_price_eur     numeric,
    final_requested_loan_eur     numeric,
    final_equity_amount_eur      numeric,
    final_collateral_value_eur   numeric,
    required_monthly_income_eur  numeric,
    final_loan_to_value          numeric
);

CREATE TABLE mortgage_events (
    id                       bigserial PRIMARY KEY,
    mortgage_customer_id     text NOT NULL,
    event_time               timestamp,
    event_type               text,
    property_id              text,
    property_type            text,
    property_price_estimate  numeric,
    loan_amount              numeric,
    equity_amount            numeric,
    collateral_type          text,
    collateral_value         numeric,
    collateral_status        text,
    decision                 text,
    rejection_reason         text,
    expense_type             text,
    expense_amount           numeric,
    note                     text
);
"""

TS = "'DDMONYY:HH24:MI:SS'"

LOADS = [
    (
        "customers",
        "tx_customers_junction.csv",
        ["customer_id", "postal_code", "age"],
        "INSERT INTO customers SELECT customer_id, postal_code, age::integer FROM {staging}",
    ),
    (
        "transactions",
        "tx_junction_transactions.csv",
        ["customer_id", "bank_account_id", "tx_date", "tx_timestamp", "category", "tx_amount_eur",
         "balance_after_eur", "transaction_type", "merchant_id", "mcc_code"],
        f"""INSERT INTO transactions (customer_id, bank_account_id, tx_date, tx_timestamp, category,
                tx_amount_eur, balance_after_eur, transaction_type, merchant_id, mcc_code)
            SELECT customer_id, bank_account_id, tx_date::date, to_timestamp(tx_timestamp, {TS}),
                category, tx_amount_eur::numeric, balance_after_eur::numeric, transaction_type,
                merchant_id, mcc_code
            FROM {{staging}}""",
    ),
    (
        "mortgage_outcomes",
        "mtg_tx_customer_link_and_final_mtg_infio.csv",
        ["mortgage_customer_id", "customer_id", "final_decision", "rejection_reason",
         "final_property_price_eur", "final_requested_loan_eur", "final_equity_amount_eur",
         "final_collateral_value_eur", "required_monthly_income_eur", "final_loan_to_value"],
        """INSERT INTO mortgage_outcomes
            SELECT mortgage_customer_id, customer_id, final_decision, rejection_reason,
                final_property_price_eur::numeric, final_requested_loan_eur::numeric,
                final_equity_amount_eur::numeric, final_collateral_value_eur::numeric,
                required_monthly_income_eur::numeric, final_loan_to_value::numeric
            FROM {staging}""",
    ),
    (
        "mortgage_events",
        "mtg_negotiation_history.csv",
        ["mortgage_customer_id", "event_time", "event_type", "property_id", "property_type",
         "property_price_estimate", "loan_amount", "equity_amount", "collateral_type",
         "collateral_value", "collateral_status", "decision", "rejection_reason", "expense_type",
         "expense_amount", "note"],
        f"""INSERT INTO mortgage_events (mortgage_customer_id, event_time, event_type, property_id,
                property_type, property_price_estimate, loan_amount, equity_amount, collateral_type,
                collateral_value, collateral_status, decision, rejection_reason, expense_type,
                expense_amount, note)
            SELECT mortgage_customer_id, to_timestamp(event_time, {TS}), event_type, property_id,
                property_type, property_price_estimate::numeric, loan_amount::numeric,
                equity_amount::numeric, collateral_type, collateral_value::numeric,
                collateral_status, decision, rejection_reason, expense_type,
                expense_amount::numeric, note
            FROM {{staging}}""",
    ),
]

INDEXES = """
CREATE INDEX transactions_customer_date ON transactions (customer_id, tx_date);
CREATE INDEX transactions_customer_category ON transactions (customer_id, category);
CREATE INDEX mortgage_events_customer ON mortgage_events (mortgage_customer_id, event_time);
CREATE INDEX mortgage_outcomes_customer ON mortgage_outcomes (customer_id);
"""


def copy_csv(cur, table, path):
    # HEADER skips the first line, which also carries the UTF-8 BOM.
    with path.open("rb") as f, cur.copy(f"COPY {table} FROM STDIN (FORMAT csv, HEADER true)") as copy:
        while chunk := f.read(1 << 20):
            copy.write(chunk)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replace", action="store_true", help="drop and reload existing tables")
    args = parser.parse_args()

    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Add it to .env (see .env.example).")

    missing = [name for _, name, _, _ in LOADS if not (DATA_DIR / name).exists()]
    if missing:
        sys.exit(f"Missing files in {DATA_DIR}: {', '.join(missing)}. See SETUP.md for how to download them.")

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('transactions') IS NOT NULL")
        if cur.fetchone()[0] and not args.replace:
            sys.exit("Tables already exist. Re-run with --replace to drop and reload them.")

        cur.execute("DROP TABLE IF EXISTS " + ", ".join(TABLES) + " CASCADE")
        cur.execute(SCHEMA)

        for table, filename, columns, insert in LOADS:
            start = time.monotonic()
            staging = f"staging_{table}"
            cur.execute(f"CREATE TEMP TABLE {staging} (" + ", ".join(f"{c} text" for c in columns) + ")")
            copy_csv(cur, staging, DATA_DIR / filename)
            cur.execute(insert.format(staging=staging))
            print(f"{table}: {cur.rowcount:,} rows ({time.monotonic() - start:.0f}s)")
            cur.execute(f"DROP TABLE {staging}")

        print("Creating indexes...")
        cur.execute(INDEXES)
        cur.execute("ANALYZE")
    print("Done.")


if __name__ == "__main__":
    main()

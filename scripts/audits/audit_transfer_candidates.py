
from coach.database.connection import get_connection


def show(title, rows):
    print(f"\n{'=' * 90}")
    print(title)
    print("=" * 90)

    if not rows:
        print("No results.")
        return

    print(" | ".join(rows[0].keys()))
    print("-" * 90)

    for row in rows:
        print(" | ".join(str(v) for v in row.values()))


def main():
    conn = get_connection()

    try:
        conn.execute("SET TRANSACTION READ ONLY")

        # 1. How many bank accounts do flow customers have?
        rows = conn.execute("""
            WITH flow_customers AS (
                SELECT DISTINCT customer_id
                FROM transactions
                WHERE transaction_type IN (
                    'salary_sweep',
                    'investment_deposit',
                    'investment_withdrawal'
                )
            ),
            account_counts AS (
                SELECT
                    f.customer_id,
                    COUNT(DISTINCT t.bank_account_id) AS accounts
                FROM flow_customers f
                JOIN transactions t
                    ON t.customer_id = f.customer_id
                GROUP BY f.customer_id
            )
            SELECT
                accounts,
                COUNT(*) AS customers
            FROM account_counts
            GROUP BY accounts
            ORDER BY accounts;
        """).fetchall()

        show("1. ACCOUNTS PER FINANCIAL-FLOW CUSTOMER", rows)

        # 2. Look for matching positive transactions.
        # Same customer, amount, and within +/- 3 calendar days.
        rows = conn.execute("""
            SELECT
                f.transaction_type,
                COUNT(*) AS outgoing_transactions,

                COUNT(*) FILTER (
                    WHERE EXISTS (
                        SELECT 1
                        FROM transactions p
                        WHERE p.customer_id = f.customer_id
                          AND p.id <> f.id
                          AND p.tx_amount_eur > 0
                          AND p.tx_date BETWEEN
                              f.tx_date - 3 AND f.tx_date + 3
                          AND ABS(p.tx_amount_eur + f.tx_amount_eur)
                              <= 0.01
                    )
                ) AS any_account_match,

                COUNT(*) FILTER (
                    WHERE EXISTS (
                        SELECT 1
                        FROM transactions p
                        WHERE p.customer_id = f.customer_id
                          AND p.id <> f.id
                          AND p.tx_amount_eur > 0
                          AND p.tx_date BETWEEN
                              f.tx_date - 3 AND f.tx_date + 3
                          AND ABS(p.tx_amount_eur + f.tx_amount_eur)
                              <= 0.01
                          AND p.bank_account_id
                              IS DISTINCT FROM f.bank_account_id
                    )
                ) AS different_account_match

            FROM transactions f
            WHERE f.transaction_type IN (
                'salary_sweep',
                'investment_deposit'
            )
              AND f.tx_amount_eur < 0
            GROUP BY f.transaction_type
            ORDER BY f.transaction_type;
        """).fetchall()

        show("2. POTENTIAL MATCHING POSITIVE TRANSACTIONS", rows)

        # 3. Inspect individual matching examples.
        rows = conn.execute("""
            SELECT
                f.customer_id,
                f.transaction_type AS outgoing_type,
                f.tx_date AS outgoing_date,
                f.bank_account_id AS outgoing_account,
                f.tx_amount_eur AS outgoing_amount,

                p.transaction_type AS incoming_type,
                p.tx_date AS incoming_date,
                p.bank_account_id AS incoming_account,
                p.tx_amount_eur AS incoming_amount

            FROM transactions f
            JOIN transactions p
              ON p.customer_id = f.customer_id
             AND p.id <> f.id
             AND p.tx_amount_eur > 0
             AND p.tx_date BETWEEN f.tx_date - 3 AND f.tx_date + 3
             AND ABS(p.tx_amount_eur + f.tx_amount_eur) <= 0.01
             AND p.bank_account_id
                 IS DISTINCT FROM f.bank_account_id

            WHERE f.transaction_type IN (
                'salary_sweep',
                'investment_deposit'
            )
              AND f.tx_amount_eur < 0

            ORDER BY f.transaction_type, f.tx_date
            LIMIT 50;
        """).fetchall()

        show("3. EXAMPLES OF POTENTIAL CROSS-ACCOUNT MATCHES", rows)

        conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    main()

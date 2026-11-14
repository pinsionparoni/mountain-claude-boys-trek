
from collections import defaultdict

from coach.database.connection import get_connection


def show(title, rows):
    print(f"\n{'=' * 100}")
    print(title)
    print("=" * 100)

    if not rows:
        print("No results.")
        return

    headers = list(rows[0].keys())
    print(" | ".join(headers))
    print("-" * 100)

    for row in rows:
        print(" | ".join(str(row[h]) for h in headers))


def main():
    conn = get_connection()

    try:
        # Enforce read-only access for this audit transaction.
        conn.execute("SET TRANSACTION READ ONLY")

        # 1. Financial flow overview by category and customer coverage.
        rows = conn.execute("""
            SELECT
                category,
                transaction_type,
                COUNT(*) AS transactions,
                COUNT(DISTINCT customer_id) AS customers,
                ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_eur,
                ROUND(AVG(ABS(tx_amount_eur)), 2) AS average_eur
            FROM transactions
            WHERE transaction_type IN (
                'salary_sweep',
                'investment_deposit',
                'investment_withdrawal',
                'salary',
                'other_income'
            )
            GROUP BY category, transaction_type
            ORDER BY category;
        """).fetchall()

        show("1. FINANCIAL FLOWS OVERVIEW", rows)

        # 2. Salary Sweep monthly patterns.
        rows = conn.execute("""
            SELECT
                DATE_TRUNC('month', tx_date)::date AS month,
                COUNT(*) AS transactions,
                COUNT(DISTINCT customer_id) AS customers,
                ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_eur,
                ROUND(AVG(ABS(tx_amount_eur)), 2) AS average_eur
            FROM transactions
            WHERE transaction_type = 'salary_sweep'
            GROUP BY 1
            ORDER BY 1;
        """).fetchall()

        show("2. SALARY SWEEP MONTHLY PATTERNS", rows)

        # 3. Customers with the largest Salary Sweep activity.
        rows = conn.execute("""
            SELECT
                customer_id,
                COUNT(*) AS transactions,
                COUNT(DISTINCT bank_account_id) AS accounts,
                ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_eur,
                ROUND(AVG(ABS(tx_amount_eur)), 2) AS average_eur
            FROM transactions
            WHERE transaction_type = 'salary_sweep'
            GROUP BY customer_id
            ORDER BY total_eur DESC
            LIMIT 25;
        """).fetchall()

        show("3. TOP CUSTOMERS BY SALARY SWEEP", rows)

        # 4. Health and Home & Tech merchant patterns.
        rows = conn.execute("""
            SELECT
                category,
                COALESCE(merchant_id, 'NULL') AS merchant_id,
                COALESCE(mcc_code, 'NULL') AS mcc_code,
                COUNT(*) AS transactions,
                COUNT(DISTINCT customer_id) AS customers,
                COUNT(DISTINCT DATE_TRUNC('month', tx_date)) AS active_months,
                ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_eur,
                ROUND(AVG(ABS(tx_amount_eur)), 2) AS average_eur
            FROM transactions
            WHERE category IN ('Health', 'Home & Tech')
            GROUP BY category, merchant_id, mcc_code
            ORDER BY category, total_eur DESC
            LIMIT 100;
        """).fetchall()

        show("4. HEALTH AND HOME & TECH MERCHANTS", rows)

        # 5. Merchant patterns in everyday categories.
        rows = conn.execute("""
            SELECT
                category,
                COALESCE(merchant_id, 'NULL') AS merchant_id,
                COALESCE(mcc_code, 'NULL') AS mcc_code,
                COUNT(*) AS transactions,
                COUNT(DISTINCT customer_id) AS customers,
                COUNT(DISTINCT DATE_TRUNC('month', tx_date)) AS active_months,
                ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_eur
            FROM transactions
            WHERE category IN (
                'Groceries',
                'Transportation',
                'Lifestyle',
                'Restaurants'
            )
            GROUP BY category, merchant_id, mcc_code
            ORDER BY category, transactions DESC
            LIMIT 100;
        """).fetchall()

        show("5. EVERYDAY SPENDING MERCHANT PATTERNS", rows)

        # 6. MCC-level patterns across ambiguous categories.
        rows = conn.execute("""
            SELECT
                category,
                COALESCE(mcc_code, 'NULL') AS mcc_code,
                COUNT(*) AS transactions,
                COUNT(DISTINCT customer_id) AS customers,
                COUNT(DISTINCT merchant_id) AS merchants,
                ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_eur
            FROM transactions
            WHERE category IN (
                'Health',
                'Home & Tech',
                'Lifestyle',
                'Transportation'
            )
            GROUP BY category, mcc_code
            ORDER BY category, total_eur DESC;
        """).fetchall()

        show("6. MCC CODE BREAKDOWN", rows)

        # 7. Investment activity by month.
        rows = conn.execute("""
            SELECT
                DATE_TRUNC('month', tx_date)::date AS month,
                transaction_type,
                COUNT(*) AS transactions,
                COUNT(DISTINCT customer_id) AS customers,
                ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_eur
            FROM transactions
            WHERE transaction_type IN (
                'investment_deposit',
                'investment_withdrawal'
            )
            GROUP BY 1, 2
            ORDER BY 1, 2;
        """).fetchall()

        show("7. INVESTMENT FLOWS BY MONTH", rows)

        conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    main()

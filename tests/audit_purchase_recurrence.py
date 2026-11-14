
from coach.database.connection import get_connection


CATEGORIES = ["Health", "Home & Tech"]


def print_section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_rows(rows):
    if not rows:
        print("No results.")
        return

    for row in rows:
        print(" | ".join(f"{key}: {value}" for key, value in row.items()))


def main():
    with get_connection() as conn:
        with conn.transaction():
            # Explicitly prohibit database modifications.
            conn.execute("SET TRANSACTION READ ONLY")

            # ---------------------------------------------------------
            # 1. Customer recurrence by category and MCC
            # ---------------------------------------------------------
            print_section("1. CUSTOMER RECURRENCE BY MCC")

            rows = conn.execute("""
                WITH customer_monthly AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date AS month,
                        COUNT(*) AS transaction_count,
                        SUM(ABS(tx_amount_eur)) AS monthly_spending
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                    GROUP BY
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date
                ),
                customer_summary AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        COUNT(*) AS active_months,
                        SUM(transaction_count) AS total_transactions,
                        SUM(monthly_spending) AS total_spending,
                        AVG(monthly_spending) AS avg_active_month_spending,
                        STDDEV_SAMP(monthly_spending)
                            AS monthly_spending_stddev
                    FROM customer_monthly
                    GROUP BY customer_id, category, mcc_code
                )
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS customers,
                    ROUND(AVG(active_months), 2) AS avg_active_months,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY active_months
                    ) AS median_active_months,
                    COUNT(*) FILTER (
                        WHERE active_months = 1
                    ) AS one_month_customers,
                    COUNT(*) FILTER (
                        WHERE active_months BETWEEN 2 AND 3
                    ) AS two_to_three_month_customers,
                    COUNT(*) FILTER (
                        WHERE active_months BETWEEN 4 AND 6
                    ) AS four_to_six_month_customers,
                    COUNT(*) FILTER (
                        WHERE active_months BETWEEN 7 AND 12
                    ) AS seven_to_twelve_month_customers,
                    COUNT(*) FILTER (
                        WHERE active_months >= 13
                    ) AS thirteen_plus_month_customers,
                    ROUND(AVG(total_spending), 2)
                        AS avg_customer_total_spending_eur
                FROM customer_summary
                GROUP BY category, mcc_code
                ORDER BY category, mcc_code NULLS LAST;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 2. Transaction frequency per active customer-month
            # ---------------------------------------------------------
            print_section("2. TRANSACTIONS PER CUSTOMER-MONTH")

            rows = conn.execute("""
                WITH customer_monthly AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date AS month,
                        COUNT(*) AS transaction_count
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                    GROUP BY
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date
                )
                SELECT
                    category,
                    mcc_code,
                    transaction_count,
                    COUNT(*) AS customer_months,
                    COUNT(DISTINCT customer_id) AS customers
                FROM customer_monthly
                GROUP BY category, mcc_code, transaction_count
                ORDER BY
                    category,
                    mcc_code NULLS LAST,
                    transaction_count;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 3. Transaction amount distribution
            # ---------------------------------------------------------
            print_section("3. TRANSACTION AMOUNT DISTRIBUTION")

            rows = conn.execute("""
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS transaction_count,
                    ROUND(AVG(ABS(tx_amount_eur)), 2) AS avg_eur,
                    ROUND(
                        PERCENTILE_CONT(0.25) WITHIN GROUP (
                            ORDER BY ABS(tx_amount_eur)
                        )::numeric,
                        2
                    ) AS p25_eur,
                    ROUND(
                        PERCENTILE_CONT(0.50) WITHIN GROUP (
                            ORDER BY ABS(tx_amount_eur)
                        )::numeric,
                        2
                    ) AS median_eur,
                    ROUND(
                        PERCENTILE_CONT(0.75) WITHIN GROUP (
                            ORDER BY ABS(tx_amount_eur)
                        )::numeric,
                        2
                    ) AS p75_eur,
                    ROUND(
                        PERCENTILE_CONT(0.90) WITHIN GROUP (
                            ORDER BY ABS(tx_amount_eur)
                        )::numeric,
                        2
                    ) AS p90_eur,
                    ROUND(
                        PERCENTILE_CONT(0.95) WITHIN GROUP (
                            ORDER BY ABS(tx_amount_eur)
                        )::numeric,
                        2
                    ) AS p95_eur,
                    ROUND(MAX(ABS(tx_amount_eur)), 2) AS max_eur
                FROM transactions
                WHERE category = ANY(%s)
                  AND transaction_type = 'purchase'
                GROUP BY category, mcc_code
                ORDER BY category, mcc_code NULLS LAST;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 4. Monthly spending patterns
            # ---------------------------------------------------------
            print_section("4. MONTHLY SPENDING PATTERNS")

            rows = conn.execute("""
                WITH customer_monthly AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date AS month,
                        COUNT(*) AS transaction_count,
                        SUM(ABS(tx_amount_eur)) AS monthly_spending
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                    GROUP BY
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date
                )
                SELECT
                    category,
                    mcc_code,
                    month,
                    COUNT(*) AS active_customers,
                    SUM(transaction_count) AS transactions,
                    ROUND(SUM(monthly_spending), 2)
                        AS total_spending_eur,
                    ROUND(AVG(monthly_spending), 2)
                        AS avg_customer_month_spending_eur,
                    ROUND(
                        PERCENTILE_CONT(0.5) WITHIN GROUP (
                            ORDER BY monthly_spending
                        )::numeric,
                        2
                    ) AS median_customer_month_spending_eur
                FROM customer_monthly
                GROUP BY category, mcc_code, month
                ORDER BY category, mcc_code NULLS LAST, month;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 5. Merchant recurrence per customer
            # ---------------------------------------------------------
            print_section("5. CUSTOMER-MERCHANT RECURRENCE")

            rows = conn.execute("""
                WITH customer_merchant AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        merchant_id,
                        COUNT(DISTINCT
                            DATE_TRUNC('month', tx_date)
                        ) AS active_months,
                        COUNT(*) AS transaction_count,
                        SUM(ABS(tx_amount_eur)) AS total_spending
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                      AND merchant_id IS NOT NULL
                    GROUP BY
                        customer_id,
                        category,
                        mcc_code,
                        merchant_id
                )
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS customer_merchant_pairs,
                    COUNT(*) FILTER (
                        WHERE active_months = 1
                    ) AS one_month_pairs,
                    COUNT(*) FILTER (
                        WHERE active_months BETWEEN 2 AND 3
                    ) AS two_to_three_month_pairs,
                    COUNT(*) FILTER (
                        WHERE active_months BETWEEN 4 AND 6
                    ) AS four_to_six_month_pairs,
                    COUNT(*) FILTER (
                        WHERE active_months >= 7
                    ) AS seven_plus_month_pairs,
                    ROUND(AVG(active_months), 2)
                        AS avg_active_months,
                    ROUND(AVG(transaction_count), 2)
                        AS avg_transactions_per_pair,
                    ROUND(AVG(total_spending), 2)
                        AS avg_pair_spending_eur
                FROM customer_merchant
                GROUP BY category, mcc_code
                ORDER BY category, mcc_code NULLS LAST;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 6. Merchant-level concentration and repeat usage
            # ---------------------------------------------------------
            print_section("6. MERCHANT RECURRENCE AND CONCENTRATION")

            rows = conn.execute("""
                WITH merchant_summary AS (
                    SELECT
                        category,
                        mcc_code,
                        merchant_id,
                        COUNT(*) AS transaction_count,
                        COUNT(DISTINCT customer_id) AS customers,
                        COUNT(DISTINCT
                            DATE_TRUNC('month', tx_date)
                        ) AS active_months,
                        ROUND(
                            SUM(ABS(tx_amount_eur)),
                            2
                        ) AS total_spending_eur,
                        ROUND(
                            AVG(ABS(tx_amount_eur)),
                            2
                        ) AS avg_transaction_eur
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                      AND merchant_id IS NOT NULL
                    GROUP BY category, mcc_code, merchant_id
                ),
                ranked AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY category, mcc_code
                            ORDER BY total_spending_eur DESC
                        ) AS merchant_rank
                    FROM merchant_summary
                )
                SELECT
                    category,
                    mcc_code,
                    merchant_rank,
                    merchant_id,
                    transaction_count,
                    customers,
                    active_months,
                    total_spending_eur,
                    avg_transaction_eur
                FROM ranked
                WHERE merchant_rank <= 10
                ORDER BY category, mcc_code NULLS LAST, merchant_rank;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

    print("\nAudit completed. No database records were modified.")


if __name__ == "__main__":
    main()

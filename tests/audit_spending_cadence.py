from coach.database.connection import get_connection


CATEGORIES = ["Health", "Home & Tech"]


def print_section(title):
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def print_rows(rows):
    if not rows:
        print("No results.")
        return

    for row in rows:
        print(" | ".join(f"{key}: {value}" for key, value in row.items()))


def run_query(conn, title, sql, params=(CATEGORIES,)):
    print_section(title)
    rows = conn.execute(sql, params).fetchall()
    print_rows(rows)


def main():
    with get_connection() as conn:
        with conn.transaction():
            # This transaction cannot modify database records.
            conn.execute("SET TRANSACTION READ ONLY")

            # ---------------------------------------------------------
            # 1. Time between purchases by customer and MCC
            # ---------------------------------------------------------
            run_query(
                conn,
                "1. INTER-PURCHASE GAPS BY CUSTOMER AND MCC",
                """
                WITH purchases AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        tx_date,
                        LAG(tx_date) OVER (
                            PARTITION BY customer_id, category, mcc_code
                            ORDER BY tx_date, tx_timestamp, id
                        ) AS previous_tx_date
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                ),
                gaps AS (
                    SELECT
                        category,
                        mcc_code,
                        customer_id,
                        (tx_date - previous_tx_date) AS gap_days
                    FROM purchases
                    WHERE previous_tx_date IS NOT NULL
                )
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS observed_purchase_gaps,
                    COUNT(DISTINCT customer_id) AS customers_with_gaps,
                    ROUND(AVG(gap_days)::numeric, 1) AS avg_gap_days,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY gap_days
                    ) AS median_gap_days,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (
                        ORDER BY gap_days
                    ) AS p25_gap_days,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (
                        ORDER BY gap_days
                    ) AS p75_gap_days,
                    COUNT(*) FILTER (WHERE gap_days <= 7) AS gaps_0_to_7_days,
                    COUNT(*) FILTER (
                        WHERE gap_days BETWEEN 8 AND 30
                    ) AS gaps_8_to_30_days,
                    COUNT(*) FILTER (
                        WHERE gap_days BETWEEN 31 AND 90
                    ) AS gaps_31_to_90_days,
                    COUNT(*) FILTER (WHERE gap_days > 90) AS gaps_over_90_days
                FROM gaps
                GROUP BY category, mcc_code
                ORDER BY category, mcc_code NULLS LAST;
                """,
            )

            # ---------------------------------------------------------
            # 2. Consecutive active-month patterns
            # ---------------------------------------------------------
            run_query(
                conn,
                "2. CONSECUTIVE ACTIVE-MONTH PATTERNS",
                """
                WITH customer_months AS (
                    SELECT DISTINCT
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date AS month
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                ),
                numbered AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        month,
                        month - (
                            ROW_NUMBER() OVER (
                                PARTITION BY customer_id, category, mcc_code
                                ORDER BY month
                            )::integer * INTERVAL '1 month'
                        ) AS streak_group
                    FROM customer_months
                ),
                streaks AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        streak_group,
                        COUNT(*) AS streak_months
                    FROM numbered
                    GROUP BY
                        customer_id,
                        category,
                        mcc_code,
                        streak_group
                ),
                customer_streaks AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        MAX(streak_months) AS longest_streak_months,
                        COUNT(*) AS separate_streaks
                    FROM streaks
                    GROUP BY customer_id, category, mcc_code
                )
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS customers,
                    ROUND(AVG(longest_streak_months), 2)
                        AS avg_longest_streak_months,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY longest_streak_months
                    ) AS median_longest_streak_months,
                    COUNT(*) FILTER (
                        WHERE longest_streak_months = 1
                    ) AS longest_streak_1_month,
                    COUNT(*) FILTER (
                        WHERE longest_streak_months BETWEEN 2 AND 3
                    ) AS longest_streak_2_to_3_months,
                    COUNT(*) FILTER (
                        WHERE longest_streak_months BETWEEN 4 AND 6
                    ) AS longest_streak_4_to_6_months,
                    COUNT(*) FILTER (
                        WHERE longest_streak_months >= 7
                    ) AS longest_streak_7_plus_months,
                    ROUND(AVG(separate_streaks), 2)
                        AS avg_separate_streaks_per_customer
                FROM customer_streaks
                GROUP BY category, mcc_code
                ORDER BY category, mcc_code NULLS LAST;
                """,
            )

            # ---------------------------------------------------------
            # 3. Monthly spending volatility per customer
            # ---------------------------------------------------------
            run_query(
                conn,
                "3. MONTHLY SPENDING VOLATILITY PER CUSTOMER",
                """
                WITH customer_monthly AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        DATE_TRUNC('month', tx_date)::date AS month,
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
                customer_volatility AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        COUNT(*) AS active_months,
                        AVG(monthly_spending) AS avg_monthly_spending,
                        STDDEV_SAMP(monthly_spending) AS monthly_spending_sd,
                        CASE
                            WHEN AVG(monthly_spending) > 0
                            THEN STDDEV_SAMP(monthly_spending)
                                 / AVG(monthly_spending)
                        END AS monthly_spending_cv
                    FROM customer_monthly
                    GROUP BY customer_id, category, mcc_code
                    HAVING COUNT(*) >= 2
                )
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS customers_with_2plus_active_months,
                    ROUND(AVG(active_months), 2) AS avg_active_months,
                    ROUND(AVG(avg_monthly_spending), 2)
                        AS avg_customer_monthly_spending_eur,
                    ROUND(AVG(monthly_spending_sd), 2)
                        AS avg_customer_monthly_spending_sd_eur,
                    ROUND(AVG(monthly_spending_cv)::numeric, 3)
                        AS avg_customer_monthly_spending_cv,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY monthly_spending_cv
                    ) AS median_customer_monthly_spending_cv,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (
                        ORDER BY monthly_spending_cv
                    ) AS p75_customer_monthly_spending_cv
                FROM customer_volatility
                WHERE monthly_spending_cv IS NOT NULL
                GROUP BY category, mcc_code
                ORDER BY category, mcc_code NULLS LAST;
                """,
            )

            # ---------------------------------------------------------
            # 4. Transaction amount predictability per customer
            # ---------------------------------------------------------
            run_query(
                conn,
                "4. TRANSACTION AMOUNT VARIABILITY PER CUSTOMER",
                """
                WITH customer_amounts AS (
                    SELECT
                        customer_id,
                        category,
                        mcc_code,
                        COUNT(*) AS transaction_count,
                        AVG(ABS(tx_amount_eur)) AS avg_transaction_amount,
                        STDDEV_SAMP(ABS(tx_amount_eur)) AS amount_sd,
                        MIN(ABS(tx_amount_eur)) AS min_amount,
                        MAX(ABS(tx_amount_eur)) AS max_amount
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                    GROUP BY customer_id, category, mcc_code
                    HAVING COUNT(*) >= 2
                ),
                customer_amount_variability AS (
                    SELECT
                        *,
                        CASE
                            WHEN avg_transaction_amount > 0
                            THEN amount_sd / avg_transaction_amount
                        END AS amount_cv
                    FROM customer_amounts
                )
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS customers_with_2plus_transactions,
                    ROUND(AVG(transaction_count), 2)
                        AS avg_transactions_per_customer,
                    ROUND(AVG(avg_transaction_amount), 2)
                        AS avg_customer_avg_transaction_eur,
                    ROUND(AVG(amount_cv)::numeric, 3)
                        AS avg_customer_amount_cv,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY amount_cv
                    ) AS median_customer_amount_cv,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (
                        ORDER BY amount_cv
                    ) AS p75_customer_amount_cv,
                    COUNT(*) FILTER (
                        WHERE amount_cv < 0.25
                    ) AS customers_low_amount_variability,
                    COUNT(*) FILTER (
                        WHERE amount_cv BETWEEN 0.25 AND 0.75
                    ) AS customers_medium_amount_variability,
                    COUNT(*) FILTER (
                        WHERE amount_cv > 0.75
                    ) AS customers_high_amount_variability
                FROM customer_amount_variability
                WHERE amount_cv IS NOT NULL
                GROUP BY category, mcc_code
                ORDER BY category, mcc_code NULLS LAST;
                """,
            )

            # ---------------------------------------------------------
            # 5. Customers active in both categories in the same month
            # ---------------------------------------------------------
            run_query(
                conn,
                "5. CROSS-CATEGORY OVERLAP BY MONTH",
                """
                WITH customer_category_months AS (
                    SELECT DISTINCT
                        customer_id,
                        category,
                        DATE_TRUNC('month', tx_date)::date AS month
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                ),
                customer_month_flags AS (
                    SELECT
                        customer_id,
                        month,
                        BOOL_OR(category = 'Health') AS has_health,
                        BOOL_OR(category = 'Home & Tech') AS has_home_tech
                    FROM customer_category_months
                    GROUP BY customer_id, month
                )
                SELECT
                    month,
                    COUNT(*) FILTER (
                        WHERE has_health
                    ) AS health_customers,
                    COUNT(*) FILTER (
                        WHERE has_home_tech
                    ) AS home_tech_customers,
                    COUNT(*) FILTER (
                        WHERE has_health AND has_home_tech
                    ) AS customers_in_both_categories,
                    ROUND(
                        100.0 * COUNT(*) FILTER (
                            WHERE has_health AND has_home_tech
                        ) / NULLIF(
                            COUNT(*) FILTER (WHERE has_health OR has_home_tech),
                            0
                        ),
                        2
                    ) AS overlap_pct_of_either_category
                FROM customer_month_flags
                GROUP BY month
                ORDER BY month;
                """,
            )

            # ---------------------------------------------------------
            # 6. MCC overlap within each customer
            # ---------------------------------------------------------
            run_query(
                conn,
                "6. CUSTOMER MCC BREADTH WITHIN EACH CATEGORY",
                """
                WITH customer_mcc AS (
                    SELECT
                        customer_id,
                        category,
                        COUNT(DISTINCT mcc_code) FILTER (
                            WHERE mcc_code IS NOT NULL
                        ) AS distinct_known_mccs,
                        COUNT(*) FILTER (
                            WHERE mcc_code IS NULL
                        ) AS transactions_without_mcc,
                        COUNT(*) AS total_transactions
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                    GROUP BY customer_id, category
                )
                SELECT
                    category,
                    distinct_known_mccs,
                    COUNT(*) AS customers,
                    ROUND(AVG(total_transactions), 2)
                        AS avg_transactions_per_customer,
                    COUNT(*) FILTER (
                        WHERE transactions_without_mcc > 0
                    ) AS customers_with_missing_mcc_transactions
                FROM customer_mcc
                GROUP BY category, distinct_known_mccs
                ORDER BY category, distinct_known_mccs;
                """,
            )

    print("\nAudit completed. Database transaction was read-only.")
    print("No customer IDs were printed and no records were modified.")


if __name__ == "__main__":
    main()

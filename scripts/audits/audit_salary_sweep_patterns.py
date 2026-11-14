
from collections import defaultdict

from coach.database.connection import get_connection


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
        # All statements in this transaction are read-only.
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")

            # ---------------------------------------------------------
            # 1. Customer recurrence across the observed months
            # ---------------------------------------------------------
            print_section("1. SALARY SWEEP CUSTOMER RECURRENCE")

            rows = conn.execute("""
                WITH monthly AS (
                    SELECT
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date AS month,
                        COUNT(*) AS sweep_count,
                        SUM(ABS(tx_amount_eur)) AS sweep_amount
                    FROM transactions
                    WHERE transaction_type = 'salary_sweep'
                    GROUP BY
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date
                ),
                per_customer AS (
                    SELECT
                        customer_id,
                        COUNT(*) AS active_months,
                        SUM(sweep_count) AS total_sweep_transactions,
                        COUNT(*) FILTER (
                            WHERE sweep_count = 1
                        ) AS months_with_one_sweep,
                        COUNT(*) FILTER (
                            WHERE sweep_count > 1
                        ) AS months_with_multiple_sweeps,
                        MIN(month) AS first_active_month,
                        MAX(month) AS last_active_month
                    FROM monthly
                    GROUP BY customer_id
                )
                SELECT
                    active_months,
                    COUNT(*) AS customers,
                    COUNT(*) FILTER (
                        WHERE months_with_one_sweep = active_months
                    ) AS customers_with_one_sweep_each_active_month,
                    COUNT(*) FILTER (
                        WHERE active_months = 24
                    ) AS customers_active_all_24_months,
                    COUNT(*) FILTER (
                        WHERE active_months = 24
                          AND months_with_one_sweep = 24
                    ) AS customers_with_exactly_one_each_of_24_months
                FROM per_customer
                GROUP BY active_months
                ORDER BY active_months;
            """).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 2. Transaction count per customer per active month
            # ---------------------------------------------------------
            print_section("2. MONTHLY TRANSACTION FREQUENCY")

            rows = conn.execute("""
                WITH monthly AS (
                    SELECT
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date AS month,
                        COUNT(*) AS sweep_count
                    FROM transactions
                    WHERE transaction_type = 'salary_sweep'
                    GROUP BY
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date
                )
                SELECT
                    sweep_count,
                    COUNT(*) AS customer_months,
                    COUNT(DISTINCT customer_id) AS customers
                FROM monthly
                GROUP BY sweep_count
                ORDER BY sweep_count;
            """).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 3. Monthly totals and relationship to salary amounts
            # ---------------------------------------------------------
            print_section("3. MONTHLY SALARY VS SALARY SWEEP AMOUNTS")

            rows = conn.execute("""
                WITH sweep_monthly AS (
                    SELECT
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date AS month,
                        SUM(ABS(tx_amount_eur)) AS sweep_amount,
                        COUNT(*) AS sweep_count
                    FROM transactions
                    WHERE transaction_type = 'salary_sweep'
                    GROUP BY
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date
                ),
                salary_monthly AS (
                    SELECT
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date AS month,
                        SUM(tx_amount_eur) AS salary_amount
                    FROM transactions
                    WHERE transaction_type = 'salary'
                    GROUP BY
                        customer_id,
                        DATE_TRUNC('month', tx_date)::date
                ),
                paired AS (
                    SELECT
                        s.customer_id,
                        s.month,
                        s.sweep_amount,
                        s.sweep_count,
                        sal.salary_amount,
                        s.sweep_amount / NULLIF(sal.salary_amount, 0)
                            AS sweep_to_salary_ratio
                    FROM sweep_monthly s
                    JOIN salary_monthly sal
                      ON sal.customer_id = s.customer_id
                     AND sal.month = s.month
                )
                SELECT
                    COUNT(*) AS matched_customer_months,
                    COUNT(DISTINCT customer_id) AS matched_customers,
                    ROUND(AVG(sweep_amount), 2) AS avg_monthly_sweep_eur,
                    ROUND(AVG(salary_amount), 2) AS avg_monthly_salary_eur,
                    ROUND(AVG(sweep_to_salary_ratio), 4)
                        AS avg_sweep_to_salary_ratio,
                    ROUND(
                        CORR(sweep_amount, salary_amount)::numeric,
                        4
                    ) AS amount_correlation
                FROM paired;
            """).fetchall()

            print_rows(rows)


            # ---------------------------------------------------------
            # 4. Date proximity to the nearest salary payment
            # ---------------------------------------------------------
            print_section("4. DATE PROXIMITY TO NEAREST SALARY PAYMENT")

            rows = conn.execute("""
                WITH sweep_dates AS (
                    SELECT
                        id,
                        customer_id,
                        tx_date
                    FROM transactions
                    WHERE transaction_type = 'salary_sweep'
                ),
                nearest_salary AS (
                    SELECT
                        s.id AS sweep_id,
                        s.customer_id,
                        s.tx_date AS sweep_date,
                        sal.tx_date AS salary_date,
                        ABS(s.tx_date - sal.tx_date) AS day_gap
                    FROM sweep_dates s
                    LEFT JOIN LATERAL (
                        SELECT
                            tx_date
                        FROM transactions sal
                        WHERE sal.customer_id = s.customer_id
                          AND sal.transaction_type = 'salary'
                          AND sal.tx_date BETWEEN
                              s.tx_date - 14 AND s.tx_date + 14
                        ORDER BY
                            ABS(sal.tx_date - s.tx_date),
                            sal.tx_timestamp
                        LIMIT 1
                    ) sal ON TRUE
                ),
                classified AS (
                    SELECT
                        CASE
                            WHEN salary_date IS NULL
                                THEN 'No salary within 14 days'
                            WHEN day_gap <= 3 THEN '0-3 days'
                            WHEN day_gap <= 7 THEN '4-7 days'
                            ELSE '8-14 days'
                        END AS date_gap_group,
                        customer_id,
                        day_gap
                    FROM nearest_salary
                )
                SELECT
                    date_gap_group,
                    COUNT(*) AS sweep_transactions,
                    COUNT(DISTINCT customer_id) AS customers,
                    ROUND(AVG(day_gap)::numeric, 2) AS avg_day_gap
                FROM classified
                GROUP BY 1
                ORDER BY 1;
            """).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 5. Monthly customer coverage
            # ---------------------------------------------------------
            print_section("5. MONTHLY SALARY SWEEP COVERAGE")

            rows = conn.execute("""
                SELECT
                    DATE_TRUNC('month', tx_date)::date AS month,
                    COUNT(*) AS sweep_transactions,
                    COUNT(DISTINCT customer_id) AS sweep_customers,
                    ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_sweep_eur,
                    ROUND(AVG(ABS(tx_amount_eur)), 2) AS avg_sweep_eur
                FROM transactions
                WHERE transaction_type = 'salary_sweep'
                GROUP BY DATE_TRUNC('month', tx_date)::date
                ORDER BY month;
            """).fetchall()

            print_rows(rows)

    print("\nAudit completed. No database records were modified.")


if __name__ == "__main__":
    main()

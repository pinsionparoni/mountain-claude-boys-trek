
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
            # Explicitly prohibit writes in this transaction.
            conn.execute("SET TRANSACTION READ ONLY")

            # ---------------------------------------------------------
            # 1. MCC-level spending distribution
            # ---------------------------------------------------------
            print_section("1. MCC-LEVEL SPENDING DISTRIBUTION")

            rows = conn.execute("""
                SELECT
                    category,
                    mcc_code,
                    COUNT(*) AS transaction_count,
                    COUNT(DISTINCT customer_id) AS customers,
                    COUNT(DISTINCT merchant_id) AS merchants,
                    ROUND(SUM(ABS(tx_amount_eur)), 2) AS total_spending_eur,
                    ROUND(AVG(ABS(tx_amount_eur)), 2) AS avg_transaction_eur,
                    ROUND(
                        PERCENTILE_CONT(0.5) WITHIN GROUP (
                            ORDER BY ABS(tx_amount_eur)
                        )::numeric,
                        2
                    ) AS median_transaction_eur
                FROM transactions
                WHERE category = ANY(%s)
                  AND transaction_type = 'purchase'
                GROUP BY category, mcc_code
                ORDER BY category, total_spending_eur DESC;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 2. Top merchants within each category and MCC
            # ---------------------------------------------------------
            print_section("2. TOP MERCHANTS WITHIN EACH MCC")

            rows = conn.execute("""
                WITH merchant_totals AS (
                    SELECT
                        category,
                        mcc_code,
                        merchant_id,
                        COUNT(*) AS transaction_count,
                        COUNT(DISTINCT customer_id) AS customers,
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
                    FROM merchant_totals
                )
                SELECT
                    category,
                    mcc_code,
                    merchant_rank,
                    merchant_id,
                    transaction_count,
                    customers,
                    total_spending_eur,
                    avg_transaction_eur
                FROM ranked
                WHERE merchant_rank <= 10
                ORDER BY category, mcc_code, merchant_rank;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 3. Missing classification and merchant data
            # ---------------------------------------------------------
            print_section("3. DATA QUALITY AND MISSING CLASSIFICATION")

            rows = conn.execute("""
                SELECT
                    category,
                    COUNT(*) AS total_transactions,

                    COUNT(*) FILTER (
                        WHERE mcc_code IS NULL
                    ) AS missing_mcc_transactions,

                    COUNT(*) FILTER (
                        WHERE merchant_id IS NULL
                    ) AS missing_merchant_transactions,

                    COUNT(*) FILTER (
                        WHERE mcc_code IS NULL
                          AND merchant_id IS NULL
                    ) AS missing_both_transactions,

                    COUNT(*) FILTER (
                        WHERE mcc_code IS NOT NULL
                          AND merchant_id IS NOT NULL
                    ) AS fully_classified_transactions,

                    ROUND(
                        100.0 * COUNT(*) FILTER (
                            WHERE mcc_code IS NULL
                        ) / NULLIF(COUNT(*), 0),
                        2
                    ) AS missing_mcc_pct,

                    ROUND(
                        100.0 * COUNT(*) FILTER (
                            WHERE merchant_id IS NULL
                        ) / NULLIF(COUNT(*), 0),
                        2
                    ) AS missing_merchant_pct,

                    ROUND(
                        SUM(ABS(tx_amount_eur)) FILTER (
                            WHERE mcc_code IS NULL
                        ),
                        2
                    ) AS spending_without_mcc_eur,

                    ROUND(
                        SUM(ABS(tx_amount_eur)) FILTER (
                            WHERE merchant_id IS NULL
                        ),
                        2
                    ) AS spending_without_merchant_eur

                FROM transactions
                WHERE category = ANY(%s)
                  AND transaction_type = 'purchase'
                GROUP BY category
                ORDER BY category;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

            # ---------------------------------------------------------
            # 4. Spending concentration by MCC
            # ---------------------------------------------------------
            print_section("4. MCC SPENDING CONCENTRATION")

            rows = conn.execute("""
                WITH mcc_totals AS (
                    SELECT
                        category,
                        mcc_code,
                        SUM(ABS(tx_amount_eur)) AS spending_eur
                    FROM transactions
                    WHERE category = ANY(%s)
                      AND transaction_type = 'purchase'
                    GROUP BY category, mcc_code
                ),
                category_totals AS (
                    SELECT
                        category,
                        SUM(spending_eur) AS category_spending_eur
                    FROM mcc_totals
                    GROUP BY category
                )
                SELECT
                    m.category,
                    m.mcc_code,
                    ROUND(m.spending_eur, 2) AS spending_eur,
                    ROUND(
                        100.0 * m.spending_eur
                        / NULLIF(c.category_spending_eur, 0),
                        2
                    ) AS category_spending_pct
                FROM mcc_totals m
                JOIN category_totals c
                  ON c.category = m.category
                ORDER BY m.category, m.spending_eur DESC;
            """, (CATEGORIES,)).fetchall()

            print_rows(rows)

    print("\nAudit completed. No database records were modified.")


if __name__ == "__main__":
    main()

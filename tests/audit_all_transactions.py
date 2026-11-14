
from coach.database.connection import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Overall database coverage
            cur.execute("""
                SELECT
                    COUNT(*) AS transaction_rows,
                    COUNT(DISTINCT customer_id) AS customers,
                    MIN(tx_date) AS first_transaction,
                    MAX(tx_date) AS last_transaction
                FROM transactions;
            """)
            overview = cur.fetchone()

            print("\n=== DATABASE OVERVIEW ===")
            print(f"Transaction rows: {overview['transaction_rows']:,}")
            print(f"Customers:        {overview['customers']:,}")
            print(f"First date:       {overview['first_transaction']}")
            print(f"Last date:        {overview['last_transaction']}")

            # Every category, transaction type, and amount direction
            cur.execute("""
                SELECT
                    COALESCE(category, 'Uncategorized') AS category,
                    COALESCE(transaction_type, 'Unspecified') AS transaction_type,
                    CASE
                        WHEN tx_amount_eur < 0 THEN 'negative'
                        WHEN tx_amount_eur > 0 THEN 'positive'
                        ELSE 'zero'
                    END AS amount_direction,
                    COUNT(*) AS transaction_count,
                    SUM(ABS(tx_amount_eur)) AS total_amount_eur
                FROM transactions
                GROUP BY 1, 2, 3
                ORDER BY 1, 2, 3;
            """)
            rows = cur.fetchall()

            print("\n=== CATEGORY / TYPE / AMOUNT AUDIT ===")
            print(
                f"{'CATEGORY':<22} "
                f"{'TRANSACTION TYPE':<25} "
                f"{'DIRECTION':<10} "
                f"{'COUNT':>12} "
                f"{'TOTAL EUR':>16}"
            )
            print("-" * 90)

            for row in rows:
                print(
                    f"{row['category']:<22} "
                    f"{row['transaction_type']:<25} "
                    f"{row['amount_direction']:<10} "
                    f"{row['transaction_count']:>12,} "
                    f"{row['total_amount_eur']:>16,.2f}"
                )


if __name__ == "__main__":
    main()

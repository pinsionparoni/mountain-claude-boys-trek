
from datetime import date

from coach.database.queries import (
    spending_by_category,
    monthly_balance_trend,
)

# Replace this with a real customer ID from your database.
TEST_CUSTOMER_ID = "CUST00001"


print("\n--- Spending by category ---")

spending = spending_by_category(
    customer_id=TEST_CUSTOMER_ID,
    start_date=date(2026, 1, 1),
    end_date=date(2026, 12, 31),
)

for row in spending:
    print(row)


print("\n--- Monthly balance trend ---")

balances = monthly_balance_trend(
    customer_id=TEST_CUSTOMER_ID,
    months=6,
)

for row in balances:
    print(row)

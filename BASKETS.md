# Spending baskets

**Status: implemented** in `coach/spending_baskets.py` (tests in `tests/test_spending_baskets.py`). The ⚠️ questions below are still open; changing a rule means changing one table there. Data facts behind it: [DATA.md](DATA.md).

S-Bank's three baskets ([CHALLENGE.md](CHALLENGE.md#summary-brief-s-pankki-pdf)). All spending goes into one of them:

| Basket | S-Bank's example |
|---|---|
| 🏠 **Regular essentials** | rent |
| 🔧 **Unexpected necessities** | a broken washing machine |
| ☕ **Everyday spending** | coffees |

## Rules, in order

1. **Not spending stays out of the baskets.** Salary, Other Income and Invest Withdraw are money in; Invest Deposit is savings; Salary Sweep is money moved out to an unknown destination (shown with a caveat, never as spending).
2. **Bills by category.** Housing and Utilities → 🏠.
3. **Large one-off purchases in Health and Home & Tech → 🔧**, whatever the merchant type: a purchase at least **10× the category's median** (Health ≥ ~540 €, Home & Tech ≥ ~1 110 €). Large purchases in other categories keep their basket but are flagged as *unusual* for the coach to mention.
4. **Card purchases by merchant type** (table below).
5. **No merchant type → "Other [category]"**, in the basket most of that category's known merchant types belong to (table below). Shown to the user as "Other", never guessed.
6. *Later:* the user can move a category or merchant type to another basket for themselves.

## Merchant types

| Category | 🏠 Regular essentials | 🔧 Unexpected necessities | ☕ Everyday spending | "Other" goes to |
|---|---|---|---|---|
| Groceries | supermarkets, butchers, dairy shops | | convenience / specialty food ⚠️ | 🏠 |
| Transportation | fuel, service stations ⚠️, parking ⚠️, public transport | | taxis | 🏠 (~89% of known) |
| Health | pharmacies | doctors, dentists, medical services | | 🏠 (pharmacy ~62% of known) |
| Home & Tech | | home supply, hardware, electronics, furniture, software ⚠️ | | 🔧 |
| Restaurants | | | restaurants, fast food & cafés, bars | ☕ |
| Entertainment | | | tickets & events, recreation, cinemas, attractions, amusement parks | ☕ |
| Lifestyle | | | sporting goods, clothing, misc retail, books, hobby & toys | ☕ |
| Travel | | | travel agencies, airlines, hotels, car rental | ☕ (planned extras) |

Merchant codes per type are in [DATA.md](DATA.md#merchant-types-mcc-per-category).

## Open questions ⚠️

- **Convenience / specialty food** (11% of groceries): everyday snacks and coffee, or groceries?
- **Service stations and parking**: essential driving, or partly coffee and convenience? Amounts in the data don't tell them apart.
- **Software** in Home & Tech: unexpected necessity or everyday?
- **Large-purchase threshold**: 10× the category median marks 0.7% of all purchases (see [DATA.md](DATA.md#large-one-off-purchases)). Use the category median or each customer's own usual amount?
- **Travel**: everyday is the closest of the three, but holidays are planned, not money that slips through your fingers.

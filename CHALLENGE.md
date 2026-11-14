# Personal Economic Trainer

*Junction 2026 challenge by S-Pankki (S-Bank)*

## The Challenge

Explore how AI can turn personal banking data into a trusted financial coach for everyday life.

S-Bank is Finland’s fourth-largest bank, with 3.5 million customers, and its S-mobiili app is used weekly by one in three Finnish adults. We want to reimagine personal finance by letting people talk with their own financial data through AI. Banking today often stops at statements and transaction lists. We want to make it conversational, insightful, and personalised. At Junction, we invite you to help us build the next generation of AI-driven personal economic trainers that make money matters simple and engaging for everyone.

Using a large synthetic transaction dataset modelled on real S-Bank data, build an AI experience that lets people chat with their own money, from simple questions like “How much did I spend on taxis last month?” to deeper ones like “What kind of spender am I?”, “What is safe for me to spend this week?” or “How much could I save if I reduced dining out by 20%?”.

We value a pedagogical angle: everyone’s spending falls into three baskets:

1. **Mandatory and regular** (e.g. rent)
2. **Mandatory and irregular** (e.g. a broken washing machine)
3. **Everyday spending that slips through your fingers** (e.g. coffees)

Solutions that help people understand where their money really goes will go far with us.

Think in the spirit of MyData: let users explore their own data freely rather than showing fixed charts the bank has picked for them. You can enhance these insights with open data sources (e.g., Statistics Finland) to offer meaningful benchmarks.

**Recommended output:** a mobile app, or a web app that can be embedded in a mobile app — our customers are on mobile.

## Extra details

To our knowledge, no Finnish bank yet lets customers chat with their own financial data, making this a first-of-its-kind opportunity in Finnish banking. The challenge ties directly to S-Bank’s strategy of serving customers increasingly digitally and to our vision for S-mobiili, one of the top-rated finance apps on both Google Play and the App Store, so a winning idea could reach millions of people. Money matters touch everyone, and we believe AI can play a key role in improving financial literacy — especially among young adults.

## About the Company

S-Bank is Finland’s fourth-largest bank, serving 3.5 million customers nationwide. Our mission is to make everyday banking simple, rewarding, and accessible to everyone. We believe in combining strong financial expertise with innovative technology to create solutions that genuinely improve people’s lives. Junction offers us a unique opportunity to co-create with some of the world’s brightest developers and to explore new ways AI can reshape personal finance.

## Insight

We are especially interested in conversational AI that:

- explains financial concepts in plain language,
- simulates “what if” scenarios, and
- guides users toward healthier money habits, for example through **safe-to-spend** and **safe-to-save** guidance.

Benchmarking personal data against open population data is encouraged but not mandatory.

### Optional bonus angle

*Not required; the challenge is fully solvable with the provided data and open data.*

**Multi-bank view:** under PSD2, customers can let their bank fetch account data from other banks. How could an AI coach use the customer’s full financial picture?

## Resources

### Data

A large synthetic transaction dataset modelled on the structure of S-Bank data: [hackjunction/Junction-2026-S-pankki](https://github.com/hackjunction/Junction-2026-S-pankki). See [SETUP.md](SETUP.md) for how we load it.

### Mentors

- **Carl-Edvard (Calle) Holmberg** – Chief Innovation Officer (main contact)
- Representative from S-Bank IT / AI development
- Data Scientist (transaction data expert)
- 1–2 business representatives who own the customer problem

## Company Info

**S-Pankki** – [www.s-pankki.fi](https://www.s-pankki.fi/)

Booth on the **5th floor**. The challenge was posted on Discord by Mikko Leinonen (S-Pankki).

## Summary brief (S-Pankki PDF)

*From `s-pankki_junction_2026_brief.pdf`, shared on the Junction Discord.*

**How could AI turn personal banking data into practical guidance for everyday life?**

Build a **mobile-first AI financial coach** that lets people talk with their own money and turns transaction data into **personalised, actionable insights**.

**Ask your money:**

- *Where did my money go?*
- *What kind of spender am I?*
- *What can I safely spend this week?*
- *How could I save more?*

**Make spending easy to understand:**

🏠 **Regular essentials** · 🔧 **Unexpected necessities** · ☕ **Everyday spending**

Think your own data: let users freely explore their own finances instead of limiting them to predefined charts. Enrich insights with open data and meaningful benchmarks.

### Transaction data (10 fields)

| Field | Meaning |
|---|---|
| `customer_id` | Unique identifier for the customer |
| `bank_account_id` | Unique identifier for the customer's bank account |
| `tx_date` | Calendar date on which the transaction occurred |
| `tx_timestamp` | Exact transaction date and time |
| `category` | Business or cash-flow category assigned to the transaction |
| `tx_amount_eur` | Signed amount in euros: negative for outflows, positive for inflows |
| `balance_after_eur` | Account balance immediately after the transaction |
| `transaction_type` | Economic purpose of the transaction, such as purchase or housing payment |
| `merchant_id` | Synthetic merchant identifier for card purchases; missing for transfers |
| `mcc_code` | Four-digit Merchant Category Code for card purchases; missing for transfers |

Example: `CUST00001 • ACC000001 • 05 Oct 2024 17:51:20 • Groceries • −€32.51 • Balance €3,080.70 • purchase • MRC-GRO-0035 • MCC 5411`

Negative amounts are money leaving the account; "." or blank merchant/MCC values indicate a non-card transfer.

### Customer data (3 fields)

| Field | Meaning |
|---|---|
| `customer_id` | Unique identifier for the customer |
| `customer_postal_code` | Five-digit postal code; leading zeros are significant (store as text, e.g. 00990) |
| `customer_age` | Customer age in completed years |

Example: `CUST00001 • 00990 • 63 years`

### Mortgage event data (16 fields)

Event-level view of a mortgage application and negotiation process.

| Field | Meaning |
|---|---|
| `mortgage_customer_id` | Unique identifier for the mortgage customer |
| `timestamp` | Exact date and time of the mortgage-process event |
| `event_type` | Process step, such as expense recording, collateral addition or valuation |
| `property_id` | Identifier for the property linked to the application |
| `property_type` | Property classification, for example apartment or detached house |
| `property_price_estimate` | Current estimated property price in euros |
| `loan_amount` | Requested mortgage amount in euros |
| `equity_amount` | Customer-funded equity contribution in euros |
| `collateral_type` | Type of collateral offered for the mortgage |
| `collateral_value` | Assessed collateral value in euros |
| `collateral_status` | Collateral assessment status, such as pending or approved |
| `decision` | Final lending decision when available: approved or rejected |
| `rejection_reason` | Reason for rejection when the application is declined |
| `expense_type` | Type of mortgage-related expense, such as existing loan or transfer tax |
| `expense_amount` | Recorded mortgage-related expense amount in euros |
| `note` | English description of the event and its business context |

Example event sequence: `expense_recorded → collateral_added → collateral_valuation`

## Judging Criteria

Each criterion counts equally.

| Criterion | Weight |
|---|---|
| Impact on financial literacy (including the pedagogical angle) | 20% |
| Originality of AI integration | 20% |
| Clarity of the mobile user experience | 20% |
| Feasibility | 20% |
| Potential to integrate into S-mobiili | 20% |

## Prizes

| Place | Prize |
|---|---|
| 1st | €2,000 Airbnb gift card |
| 2nd | €1,000 Airbnb gift card |
| 3rd | €500 Airbnb gift card |

# Financial model plan

## Purpose

Extend the existing synthetic user and transaction dataset so that
Python, SQL, Power BI, and the future web dashboard can share the
same financial data model.

The account registry is implemented and validated: each existing
user receives one synthetic CASH account and one synthetic
INVESTMENT account.

Account IDs are derived deterministically from user ID and account
type, so this generator needs no random seed. All other extension
tables remain planned.

## Existing foundation

- `users`: one row per user, identified by `user_id`.
- `transactions`: one row per transaction, identified by
  `transaction_id` and connected to its owner through `user_id`.

The original exports remain unchanged.

## Planned extension tables

| Table | What one row represents | Main relationship |
|---|---|---|
| `accounts` | One cash or investment account | Belongs to a user through `user_id` |
| `cash_balance_snapshots` | Cash held in one account on one date | Connects to `accounts` through `account_id` |
| `assets` | One investment instrument, such as a stock, ETF, or cryptocurrency | Identified by `asset_id` |
| `asset_prices` | One asset's unit price on one date in one currency | Connects to `assets` through `asset_id` |
| `holding_snapshots` | Quantity of one asset held in one account on one date | Connects to an account and an asset |
| `liability_snapshots` | Outstanding balance of one debt on one date | Belongs to a user through `user_id` |
| `goal_snapshots` | One savings goal's target and allocated cash on one date | Connects to its user and funding account |
| `scheduled_payments` | One planned future payment occurrence | Connects to its user and funding account |
| `portfolio_events` | One investment event, such as a contribution, trade, dividend, or fee | Connects to an investment account and, when applicable, an asset |

## Initial reporting choices

- Use 2024-12-28 as the first snapshot date, matching the last
  observed transaction date.
- Treat snapshot amounts as end-of-day values.
- Use USD as an explicit demonstration assumption.
- Mark generated extension data as `synthetic_extension`.
- Record generation rules and a fixed random seed when implementing
  the generator so that the same inputs reproduce the same outputs.
- Clearly label simulated asset prices; do not describe them as
  historical market quotes.

The dated snapshot design can support additional dates later.
A single snapshot does not provide a historical trend.

## Relationship rules

- Every account must belong to an existing user.
- Every holding must reference an existing account and asset.
- A holding's valuation must use a price with a matching asset,
  date, and currency.
- A goal or scheduled payment must reference an account belonging
  to the same user.
- Source transactions have no account identifier. Any later
  assignment to synthetic accounts must be documented as an
  assumption and performed in a derived table.

## Calculation boundaries

- Cash balances contain cash only, excluding the value of holdings.
- Investment value comes from holding quantities and asset prices.
- Net worth combines cash and investment values, then subtracts
  outstanding liabilities, using the same reporting date.
- Goal allocations are portions of existing cash, not extra assets.
  Combined allocations must not exceed the funding account's cash.
- Scheduled payments are plans. They do not change historical
  cash flow until represented as actual transactions.
- Investment returns require suitable price history and investment
  events. A change in portfolio value alone is insufficient.
- The original `source_balance` remains excluded from these metrics.

## Implementation order

1. Create and validate the account registry.
2. Add consistent balance, investment, debt, goal, and payment data
   in small increments.
3. Add the history and investment events needed for performance
   calculations.
4. Load validated tables into SQL and implement shared metrics.
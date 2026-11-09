# Financial model plan

## Purpose

Extend the existing synthetic user and transaction dataset so that
Python, SQL, Power BI, and the future web dashboard can share the
same financial data model.

The account registry is implemented and validated: each existing
user receives one synthetic CASH account and one synthetic
INVESTMENT account.

Account IDs are derived deterministically from user ID and account
type, so this generator needs no random seed. 

Cash-balance snapshots are also implemented for 2024-12-28.

The cash generator uses base seed 42, combined with each account ID
and snapshot date. CASH account balances range from USD 500 to
25,000; INVESTMENT account cash ranges from USD 0 to 3,000.

These are arbitrary demonstration ranges. Investment-account cash
excludes holdings. The simulated balances have not been reconciled
to historical source transactions.

The asset catalog is implemented with six fictional instruments:
two stocks, two ETFs, and two cryptocurrencies.

Stable asset IDs will link future price and holding tables.
USD is the assumed quote currency. The DEMO_ symbols are fictional
display labels.

Simulated asset prices are implemented for 2024-12-28.
Each of the six fictional assets has one end-of-day USD unit price.
Prices are fixed demonstration values with cent precision.
They are not historical market quotes, and this single-date table
cannot establish investment returns.

Holding snapshots are implemented for 2024-12-28.
Each investment account has three distinct fictional assets,
with 1 to 100 whole units per holding.

The generator uses base seed 42 with each account ID and snapshot
date. Every holding connects to an existing investment account,
asset, and price for the same date and currency.

These positions are demonstration assumptions and have not been
reconstructed from purchases or historical source transactions.
Cash snapshots remain separate from holdings.

Holding valuations are implemented for 2024-12-28.
Each holding is matched to a price using asset ID, snapshot date,
and account currency. Its value is quantity multiplied by unit price.

Calculations use Decimal arithmetic with ROUND_HALF_UP to two
decimal places per holding. Individual values and the combined
total are reconciled using integer cents.

The valuation table preserves one row per holding and excludes
cash and liabilities. Purchase costs and investment returns
have not yet been calculated.

Liability snapshots are implemented for 2024-12-28.
Each user receives zero, one, or two simulated debts: a credit card
balance and/or a personal loan.

Credit card balances range from USD 200 to 8,000.
Personal loan balances range from USD 1,000 to 30,000.
These are arbitrary demonstration ranges.

The generator uses base seed 42 with each user ID and snapshot date.
All input users are processed. Users without generated debt records
have zero modeled debt in this complete synthetic snapshot.

Outstanding balances are stored as positive amounts owed.
They are not inferred from or reconciled to source transactions.

Goals, scheduled payments, and portfolio events remain planned.

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
# Portfolio event plan

## Purpose

Extend the existing financial model with reproducible, simulated
investment activity and portfolio valuations over time.

This will support portfolio history and investment-performance
calculations in both the traditional reports and the future dashboard.

## Simulation period

- Opening position: end of day on 2024-12-28.
- First simulation day: 2024-12-29.
- Last simulation day: 2025-01-27.
- Reporting currency: USD, following the existing demonstration assumption.
- Generated records use data_origin = synthetic_extension.

Prices and events are fictional demonstration data.
Daily prices are simulated calendar-day values, not historical
market quotes or a representation of exchange trading calendars.

## Opening balances

Each investment account begins with:

1. Its uninvested cash from cash_balance_snapshots.
2. Its asset quantities from holding_snapshots.
3. Matching asset prices for 2024-12-28.

Opening portfolio value equals investment-account cash plus
the value of its holdings.

Opening balances initialize the simulation. They are not new
contributions, income, or investment gains.

Opening holding values are market-value assumptions.
They do not establish purchase costs or tax cost basis.

Opening portfolio balances are implemented in
`data/processed/portfolio_opening_balances.csv`.

The table contains one row per investment account for 2024-12-28.
Each row combines that account's uninvested cash and validated
holdings value. Holdings are aggregated before adding cash once.

Validation evidence:
[Portfolio opening validation report](portfolio_opening_validation.json).

## Planned event types

All event amounts are stored as positive magnitudes.
The event type determines whether cash or units increase or decrease.

| Event type | Investment-account cash | Asset units |
|---|---|---|
| CONTRIBUTION | Increases by the transferred amount | No change |
| WITHDRAWAL | Decreases by the transferred amount | No change |
| BUY | Decreases by the trade amount | Increases |
| SELL | Increases by the trade amount | Decreases |
| DIVIDEND | Increases by the payment amount | No change |
| FEE | Decreases by the fee amount | No change |

Trade amount equals quantity multiplied by execution price.
Any transaction fee is recorded separately as a FEE event.

## Transfers and performance

Contributions and withdrawals move money between the user's
CASH account and INVESTMENT account.

Each transfer must have equal and opposite cash movements
in accounts owned by the same user, linked by one transfer_id.

These transfers are external cash flows when measuring the
investment portfolio's performance. They are internal transfers
when considering the user's combined accounts.

Buys and sells exchange investment cash for assets or vice versa.
They are not portfolio contributions or withdrawals.

Dividends and fees affect investment performance.

## Event timing

Events have a stable event_id, event_date, and event_sequence.
The sequence defines the processing order within each account and day.

For the initial simulation, contributions and withdrawals occur
at the end of the day, after other investment activity.

Closing portfolio value is calculated after all events for that day.
The later return calculation must use this same cash-flow timing.

## Processing and validation rules

- Start each day from the previous day's closing balances.
- Require existing accounts and, where applicable, existing assets.
- Require matching dates and currencies for prices and valuations.
- Use whole asset units in the initial version.
- Calculate money using Decimal arithmetic and round trade amounts
  to cents with ROUND_HALF_UP.
- Require sufficient investment cash before a buy, withdrawal, or fee.
- Require sufficient asset units before a sale.
- Validate funding-account cash and documented reservations
  before generating a contribution.
- Validate both sides of each transfer together.
- Preserve event order and reject duplicate event IDs.
- Reconcile closing cash to opening cash plus signed cash movements.
- Reconcile closing units to opening units plus signed unit movements.

Generated events must pass these checks before their results
are used in reports.

## Reproducibility

Use base seed 42 with a documented generator version and stable
account, asset, date, and event identifiers.

The same inputs and settings must reproduce the same outputs.

## Reporting boundaries

This stage extends investment history beyond the opening snapshot.

The existing net-worth and cash-coverage reports describe
2024-12-28. A later-date personal net-worth report will require
matching-date balances for all included assets and liabilities.

Investment returns require dated portfolio valuations and
cash-flow adjustments. A change in portfolio value alone
will not be labeled an investment return.

## Implemented daily price history

Daily simulated prices are stored in
`data/processed/asset_price_history.csv`.

The table contains 186 rows: six assets across 31 calendar dates,
from 2024-12-28 through 2025-01-27.

Opening prices match the existing `asset_prices.csv` snapshot.
Each later price is calculated from the previous day's rounded price.

Generation uses base seed 42 with the generator version,
asset ID, and price date.

Daily changes are drawn as whole basis points:
- EQUITY: -150 to +150 basis points.
- FIXED_INCOME: -30 to +30 basis points.
- CRYPTO: -400 to +400 basis points.

One basis point equals 0.01 percent.
These ranges are arbitrary demonstration assumptions and apply
before rounding.

Prices use ROUND_HALF_UP to cents, with a minimum of USD 0.01.
The series includes weekends and holidays as simulated calendar days.

These are fictional unit prices. Portfolio performance will require
holdings, cash movements, dividends, and fees to be processed separately.

Validation evidence:
[Daily price-history report](price_history_validation.json).

## Implemented buy and sell events

The portfolio_trade_events table contains 2,000 simulated trades across
500 investment accounts.

Each account has one SELL followed by one BUY on 2025-01-03 and
2025-01-17. Event sequence 1 is the sale; sequence 2 is the purchase.

Quantities range from one to five whole units, capped by units owned
for sales and available investment-account cash for purchases.
A purchase may select the same asset that was sold.

Trades use the same-date simulated USD price with immediate cash and
unit settlement. Amounts are positive; event type determines direction.
Generation uses base seed 42, account ID, trade date, and generator version.

Validation replays the events from the opening snapshots and checks
ownership, prices, amounts, available cash, available units, and closing
balances. Buying or selling at the execution price preserves portfolio
value at that instant before fees.

The opening snapshots remain the starting point for subsequent replay.
This first trade scenario excludes dividends, fees, transfers, taxes,
spreads, and slippage.

Trade amounts represent gross purchases and sales, not investment
profits or household spending.

Validation: [Portfolio trade report](portfolio_trade_validation.json).

## Implemented dividends and fees

The portfolio_cash_events table contains simulated DIVIDEND and FEE
events linked to existing investment accounts.

Dividends are paid on 2025-01-24 using positive units held after the
validated buy and sell events. Fixed demonstration payments per unit are:

- demo_stock_01: USD 0.50
- demo_stock_02: USD 0.35
- demo_etf_01: USD 0.20
- demo_etf_02: USD 0.15

Crypto assets receive no distributions in this scenario.
Dividend eligibility uses holdings at payment time. Ex-dividend dates,
record dates, taxes, and dividend-related price adjustments are not modeled.

An account fee is charged on 2025-01-27. The charge is the lesser of
USD 5.00 and available investment cash after dividends. Zero charges
are omitted, and any uncharged portion is waived rather than recorded
as debt.

Amounts are positive: DIVIDEND adds cash and FEE subtracts cash.
These events do not change asset quantities. Fee rows leave the
asset-specific fields blank.

Generation uses fixed rules with no additional randomness.
Validation checks ownership, event coverage, dividend quantities and
rates, fees, sequencing, and cash reconciliation.

Validation: [Portfolio cash-event report](portfolio_cash_event_validation.json).
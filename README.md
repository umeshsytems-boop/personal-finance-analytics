# Personal Finance & Investment Analytics

An independent portfolio project by Umesh Chandra Bandla, being developed step by step with Python, SQL, and Power BI. A later custom web dashboard will reuse the validated data model and business calculations.

**Status: Step 1 - source selection and project setup.** The source file has been obtained and inspected. Pipelines, database tables, financial measures, tests, and dashboards are planned work, not completed features.

## Business question

How can a person understand money coming in, money going out, and changes in their financial position through one consistent analytics system?

## Current data

The starter source is the synthetic banking snapshot from [The Artha Personal-Finance Reasoning Benchmark](https://huggingface.co/datasets/Tej-Katika/artha-benchmark), created by Tejashwar Reddy Katika. It contains 500 fictional users and 120,817 transactions dated January 1 through December 28, 2024.

The data is externally sourced and synthetic. The analytics implementation will be developed in this repository. This project is independent of the Artha benchmark and does not reproduce its AI evaluation system.

See [data sources](docs/data_sources.md), [source inspection](docs/source_inspection.md), and [source attribution](docs/third_party/ARTHA_ATTRIBUTION.md).

## Planned implementation

1. Preserve and inspect source data.
2. Read the JSON with Python and produce documented tables.
3. Validate types, identifiers, transaction direction, and data relationships.
4. Load a SQL database and define reusable financial calculations.
5. Build and reconcile a conventional Power BI report.
6. Add documented portfolio, goals, and balance inputs where the source lacks them.
7. Add scheduling, tests, and an API for a custom dashboard.

Market prices, synthetic holdings, and banking transactions will have explicit provenance. Unrelated customer datasets will not be joined as if they describe the same people.

## Repository organization

| Location | Purpose |
|---|---|
| `README.md` | Project introduction, current status, and links |
| `docs/project_brief.md` | Scope, business questions, and boundaries |
| `docs/data_sources.md` | Source links, license notes, and download instructions |
| `docs/source_inspection.md` | Observed source structure and limitations |
| `docs/step_01_setup.md` | Beginner instructions for the first learning step |
| `docs/third_party/` | Original source license and citation details |
| `data/raw/artha/` | Unchanged source JSON, kept locally and ignored by Git |

Code and report directories will be added when their corresponding work begins.

## Reproduce the starting point

Follow [Step 1](docs/step_01_setup.md). The raw file is intentionally excluded from Git. Its exact download URL and SHA-256 are recorded in [data sources](docs/data_sources.md).

## Current limitations

This is a learning and demonstration project. The source is a synthetic transaction history, not an audited bank ledger. The supplied balance values and merchant/category assignments need further validation. The file does not contain a complete account, liability, holdings, or savings-goal model. No net-worth or investment-return result is claimed at this stage.

Status: Step 2 — Python environment created and source inspection script running locally.

Status: Step 3 — Source profiling completed: 500 users, 120,817 transactions, and no duplicate user or transaction IDs found.

**Status: Step 5A — source profiling and user extraction complete.**

Extracted 500 synthetic users into `data/interim/users.csv`.
Run `.\.venv\Scripts\python.exe .\src\extract_users.py` to recreate the table.

Next: extract transactions and connect them to users.

**Status: Step 5B — user and transaction extraction complete.**

Extracted 500 users and 120,817 transactions from the synthetic source.
The tables connect through `user_id`.

Recreate the tables by running:
- `.\.venv\Scripts\python.exe .\src\extract_users.py`
- `.\.venv\Scripts\python.exe .\src\extract_transactions.py`

Next: validate the extracted tables.

**Status: Step 7O — 186 daily simulated asset prices generated and validated.**

Recreate the account registry:
`.\.venv\Scripts\python.exe .\src\generate_accounts.py`

Recreate the cash-balance snapshots:
`.\.venv\Scripts\python.exe .\src\generate_cash_balances.py`

Recreate the asset catalog:
`.\.venv\Scripts\python.exe .\src\generate_assets.py`

Recreate the simulated asset prices:
`.\.venv\Scripts\python.exe .\src\generate_asset_prices.py`

Recreate the simulated holdings:
`.\.venv\Scripts\python.exe .\src\generate_holdings.py`

Recalculate holding values:
`.\.venv\Scripts\python.exe .\src\value_holdings.py`

Recreate the simulated liability snapshots:
`.\.venv\Scripts\python.exe .\src\generate_liabilities.py`

Recalculate modeled net worth:
`.\.venv\Scripts\python.exe .\src\calculate_net_worth.py`

Recreate the savings goals:
`.\.venv\Scripts\python.exe .\src\generate_goals.py`

Recreate the scheduled payments:
`.\.venv\Scripts\python.exe .\src\generate_scheduled_payments.py`

Recalculate cash coverage:
`.\.venv\Scripts\python.exe .\src\calculate_cash_coverage.py`

Recalculate portfolio opening balances:
`.\.venv\Scripts\python.exe .\src\calculate_portfolio_opening.py`

Recreate the simulated daily price history:
`.\.venv\Scripts\python.exe .\src\generate_price_history.py`

Validation evidence:
- [Table validation report](docs/table_validation.json)
- [Source reconciliation report](docs/source_reconciliation.json)
- [Account validation report](docs/account_validation.json)
- [Cash-balance validation report](docs/cash_balance_validation.json)
- [Asset validation report](docs/asset_validation.json)
- [Asset price validation report](docs/asset_price_validation.json)
- [Holding validation report](docs/holding_validation.json)
- [Holding valuation report](docs/valuation_report.json)
- [Liability validation report](docs/liability_validation.json)
- [Net-worth validation report](docs/net_worth_validation.json)
- [Savings-goal validation report](docs/goal_validation.json)
- [Scheduled-payment validation report](docs/scheduled_payment_validation.json)
- [Cash-coverage validation report](docs/cash_coverage_validation.json)
- [Portfolio opening validation report](docs/portfolio_opening_validation.json)
- [Daily price-history validation report](docs/price_history_validation.json)

Project decisions:
- [Data quality and handling decisions](docs/data_quality_decisions.md)
- [Financial model plan](docs/financial_model_plan.md)
- [Portfolio event plan](docs/portfolio_event_plan.md)

Next: generate and validate simulated buy and sell events.
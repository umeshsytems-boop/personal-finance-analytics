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

**Status: Step 6C — exported user and transaction records reconciled with the source JSON.**

Validation results: [Count and ID report](docs/table_validation.json).

Source comparison: [Reconciliation report](docs/source_reconciliation.json).

Next: document source limitations and cleaning decisions.

**Status: Step 6D — source limitations and data handling decisions documented.**

Validation evidence:
- [Table validation report](docs/table_validation.json)
- [Source reconciliation report](docs/source_reconciliation.json)

Project decisions:
- [Data quality and handling decisions](docs/data_quality_decisions.md)

Next: define the missing financial entities and plan their synthetic extensions.